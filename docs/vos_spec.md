# Atlas vOS – Product Requirements & Execution Plan

_Last updated: 2025-11-28_

## 1. Vision & Constraints
- **Objective:** Rebuild Atlas around a modular ingestion engine (“vOS”) that reliably hoovers every artifact (emails, RSS, Instapaper dumps, CSVs, SQLite exports, TrojanHorse notes, manual URLs) and stores canonical HTML/text plus searchable metadata.
- **Privacy:** All ingested artifacts remain on disk and SQLite; repo contains only code/config. `data/` is git-ignored. Provenance tracking (manifest + DB) preserves absolute source paths without exposing data publicly.
- **Non-Goals:** AI summarization, embeddings, Redis/RQ, multi-user auth, UI polish. vOS v1 is ingestion + storage + search + basic dashboard.

## 2. Success Criteria
1. Every staged backlog file produces queue jobs referencing its manifest ID; worker processes them without manual intervention.
2. Gmail labels `Atlas` & `Newsletter` and podcast/article RSS feeds produce new jobs hourly (configurable) with dedupe by URL.
3. Each job ends with:
   - Archived HTML (with downloaded assets) under `data/archives/YYYY-MM/<uuid>/`
   - Raw source stored (emails → `.eml`, feeds → JSON snapshot, backlog rows → normalized JSON) under `data/raw/...`
   - Metadata row in `data/atlas_vos.db` and Whoosh index entry.
4. Dashboard + `scripts/status_vos.sh` show real queue stats, ingestion velocity, failure counts.
5. Migration tools import the legacy SQLite/CSV files you provided without hand-editing code per dataset.
6. MCP checks/tests cover queue integrity, parsers, worker, API routes, search queries, and privacy guardrails (no tracked data files).

## 3. Architecture Overview
```
vos/
  cli.py (Typer)
  api/{routes.py,dashboard.py}
  worker/processor.py
  ingestion/{gmail,rss,url,backlog,trojanhorse}.py
  storage/{database,archive,queue}.py
  models/{content,queue,stats}.py
  search/whoosh_search.py
config/{feeds.yaml,backlog_sources.yaml,requirements-vos.txt}
data/{atlas_vos.db,queue,backlog,archives,raw,search_index}
logs/{vos_processor.log}
web/dashboard.html
scripts/{setup_vos.sh,start_vos.sh,stop_vos.sh,status_vos.sh,migrate_vos_data.py}
```
- Worker is single-process loop; sophistication lives in ingestion modules that craft well-formed queue jobs.

## 4. Data & Provenance
- `data/backlog/source_drops/` stores immutable copies of upstream files; `source_manifest.jsonl` logs `{id, original_path, relative_path, copied_at, status}`.
- Parsers append processing checkpoints under `data/backlog/logs/<dataset>.log` and mark `status=processed` when fully converted.
- Queue jobs include `origin_manifest_id` so we can trace each item back to its raw source.

## 5. Queue Contract
- File-based queue under `data/queue/{inbox,processing,completed,failed}`.
- Job schema (JSON):
```json
{
  "id": "uuid",
  "type": "url|email|rss_item|backlog|trojanhorse",
  "source": "gmail|rss|instapaper|newsletter|manual|trojanhorse|migration",
  "payload": {...},
  "origin_manifest_id": "optional",
  "created_at": "ISO8601Z",
  "notes": "optional context"
}
```
- Only validated jobs reach `inbox/`. Worker always finishes `processing/` before grabbing new work. Failures drop `.error.txt` with stack traces and DB audit row.

## 6. Storage & Search
- SQLite schema (`data/atlas_vos.db`): tables for `content`, `queue_audit`, `feed_state`, `gmail_messages`, indexes on URL, content hash, created_at.
- `vos/storage/archive.py`: writes HTML, extracted text, image assets; returns relative paths stored in DB.
- Whoosh index stored under `data/search_index/`; `vos/search/whoosh_search.py` exposes `index_content(record)` + `search(query, filters)`.

## 7. Ingestion Surfaces
### 7.1 Gmail
- IMAP login via `imap.gmail.com` using `GMAIL_USERNAME` + `GMAIL_APP_PASSWORD`.
- Search labels `Atlas` and `Newsletter` (case-insensitive); support alias `zoheri+atlas`.
- Save raw `.eml` to `data/raw/emails/YYYY-MM/` before parsing.
- Extract URLs, attachments, inline text; create queue job per unique URL/body chunk.

### 7.2 RSS
- Config-driven feeds (`config/feeds.yaml`) including all podcasts + additional article feeds.
- Poll interval default 1 hour; last processed GUID stored in SQLite to prevent duplicates.
- Save raw feed entry JSON to `data/raw/feeds/YYYY-MM/<uuid>.json` for auditing.

### 7.3 Backlog
- `config/backlog_sources.yaml` maps each staged dataset to a parser type (`instapaper_csv`, `newsletter_json`, `missing_content_csv`, `atlas_unified_db`, `manual_articles_dir`, etc.).
- Parsers emit queue jobs referencing manifest IDs. Completed rows logged; dataset flagged `processed` once fully converted.

### 7.4 Manual / TrojanHorse
- FastAPI routes + Typer CLI accept ad-hoc URLs or TrojanHorse payloads; they simply drop queue jobs.

## 8. Worker Lifecycle
1. `vos worker run` (Typer) starts the loop.
2. Loop behavior:
   - Resume any job in `processing/` (crash-safe).
   - Move next `inbox/` job to `processing/` atomically.
   - Dispatch by type; handlers call storage/archive/search modules.
   - On success, move job JSON to `completed/` with `.done.json` copy; insert queue audit row.
   - On failure, move to `failed/`, emit `.error.txt`, update DB.
   - Sleep `PROCESSOR_SLEEP_SECONDS` (default 60) when idle.

## 9. API & Dashboard
- FastAPI endpoints (prefixed `/vos`):
  - `POST /vos/ingest/url`
  - `POST /vos/trojanhorse/ingest`
  - `GET /vos/search?q=&type=&limit=`
  - `GET /vos/status`
  - `GET /vos/dashboard` (serves HTML with real data)
- Authentication optional via `ATLAS_API_KEY` header.
- Dashboard shows totals, queue counts, ingestion rate (past 24h), failure list, Gmail/RSS last poll timestamps.

## 10. CLI & Scripts
- `atlas vos ...` commands powered by Typer:
  - `atlas vos worker` (start loop)
  - `atlas vos poll-gmail`
  - `atlas vos poll-rss`
  - `atlas vos backlog` (convert staged datasets)
  - `atlas vos ingest-url <url>`
  - `atlas vos status`
- Shell helpers: `scripts/setup_vos.sh`, `start_vos.sh`, `stop_vos.sh`, `status_vos.sh`, `migrate_vos_data.py` (Python script).

## 11. Configuration & Secrets
`.env.example` must include:
```
GMAIL_USERNAME=zoheri+atlas@gmail.com
GMAIL_APP_PASSWORD="ekgy yvgg wsrz uyeo"
GMAIL_LABELS=Atlas,Newsletter
QUEUE_ROOT=data/queue
BACKLOG_ROOT=data/backlog
ARCHIVE_ROOT=data/archives
RAW_ROOT=data/raw
DATABASE_PATH=data/atlas_vos.db
WHOOSH_INDEX_PATH=data/search_index
RSS_CONFIG_PATH=config/feeds.yaml
BACKLOG_CONFIG_PATH=config/backlog_sources.yaml
ATLAS_API_KEY=change-me
PROCESSOR_SLEEP_SECONDS=60
```
- Use relative paths so the entire system is relocatable.

## 12. Testing & MCP Checks
- **Unit Tests:** Queue file moves, manifest readers, backlog parsers (Instapaper, newsletter, CSVs), Gmail label filtering, RSS dedupe, archive writer, Whoosh indexer.
- **Integration Tests:** Worker processes sample jobs end-to-end; FastAPI routes hit in-memory DB; CLI commands spawn temporary queue directories.
- **Privacy Tests:** CI script ensures `data/` paths remain git-ignored; run `git status --short data` to confirm clean tree.
- **MCP Hooks:**
  - `mcp check queue` – validate queue directories + JSON schema
  - `mcp check gmail` – simulate label polling (mock IMAP)
  - `mcp check rss` – load sample feed file and ensure dedupe
  - `mcp check backlog` – dry-run parser against staged manifests
  - `mcp check worker` – run worker against fixture queue and assert DB inserts
  - `mcp check api` – start FastAPI (uvicorn) and run health/search tests
- All checks run before each push.
 - **New CLI check scripts:** 
   - `scripts/mcp_check_queue.sh` runs `pytest tests/test_queue.py`
   - `scripts/mcp_check_worker.sh` executes `python3 -m vos.cli worker --max-iterations 5`
   - `scripts/mcp_check_ingest.sh` polls RSS + Gmail (if creds provided) and confirms new jobs
   - `scripts/mcp_check_status.sh` reports queue summary, Whoosh docs, and SQLite content count
   These scripts are lightweight self-checks you can wrap into MCP tooling or cron jobs for automated reliability scans.

## 13. Rollout Plan
1. Finish spec (this doc) and commit.
2. Add `.env.example` + `.gitignore` updates.
3. Scaffold `vos/` modules with stubs + Typer/FastAPI entrypoints.
4. Implement backlog parser + queue validation; feed a subset of staged data to prove architecture.
5. Layer Gmail + RSS ingestion.
6. Wire worker, archive, DB, Whoosh.
7. Build dashboard + CLI scripts.
8. Implement migration script for legacy DBs.
9. Run MCP test suite, process backlog fully, monitor `status_vos.sh`.
10. Archive legacy podcast pipeline, keep vOS as default entrypoint on `main`.

---

This PRD doubles as our checklist; we’ll tick items off in GitHub issues or commit messages as we proceed.
