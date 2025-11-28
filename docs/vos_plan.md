# Atlas vOS – Ingestion-First Plan

This document captures the upfront thinking for rebuilding Atlas around the file-based ingestion pipeline ("vOS") before we start coding. Nothing from the legacy podcast system is sacred—we will replace it in-place on `main` once the scaffolding below is in.

---

## 1. Goals & Non-Goals
- **Goal:** Single ingestion + storage path for *every* blob (emails, RSS, Instapaper exports, CSVs, DBs, manual URLs) with zero manual babysitting once configured.
- **Goal:** All complexity lives in job creation; the worker simply executes queued jobs serially with predictable file moves.
- **Goal:** Break the historical bottleneck by treating every row/file as an immutable object with a UUID + provenance trail.
- **Non-Goal (for vOS launch):** AI summarization, categorization, embeddings, Redis/RQ, multi-user auth. We only fetch → archive → store → index.

---

## 2. Data Intake & Provenance Tracking
- Added `data/backlog/source_drops/` where we copy every upstream file. We already staged the desktop assets and logged provenance in `data/backlog/source_manifest.jsonl` with fields `{id, original_path, relative_path, copied_at, status}`.
- Keep the absolute macOS path in the manifest so we always know the source of truth, even after moving hardware.
- Future backlog drops: copy into `source_drops/`, append manifest entry with status `queued`. Once we build processors, they will move file-specific checkpoints into `data/backlog/processed/` but the source copy stays immutable.
- Queue layout now exists under `data/queue/{inbox,processing,completed,failed}`; jobs are JSON envelopes so other agents can reason over them without SQLite access.

---

## 3. Directory & Module Layout
```
vos/
  __init__.py
  cli.py
  models/
    content.py       # ContentRecord (metadata, paths, hashes)
    queue.py         # QueueJob schema, manifest helpers
    stats.py         # Snapshot builder for dashboard/API
  storage/
    database.py      # SQLite schema + migrations
    archive.py       # HTML/text/image persistence helpers
    queue.py         # File move helpers, validation, locking
  ingestion/
    gmail.py         # Label-based IMAP polling (Atlas + Newsletter)
    rss.py           # feedparser-based poller, state recorded in DB
    url.py           # On-demand URL fetch/extract service
    backlog.py       # Parsers for Instapaper, CSVs, JSON batches, sqlite dumps
    trojanhorse.py   # Existing API entrypoint → queue job
  worker/
    processor.py     # While loop, 60s cadence, dispatch by job type
  search/
    whoosh_search.py # Index + query wrappers
  api/
    routes.py        # FastAPI router (ingest/search/status)
    dashboard.py     # Templated HTML dashboard (real stats only)
```
Supporting config + data roots:
```
data/
  atlas_vos.db          # Single SQLite DB
  queue/
  backlog/
    source_drops/
    processed/
    logs/
  archives/YYYY-MM/
  raw/{emails,feeds,transcripts}
  search_index/
config/
  feeds.yaml            # Podcast + misc RSS definitions
  backlog_sources.yaml  # Parser instructions for staged files
  requirements-vos.txt  # Dependencies to install up front
```

---

## 4. Dependencies to Preload
Listed in `config/requirements-vos.txt` so we can `pip install -r config/requirements-vos.txt` and be ready for everything we scoped:
- API/CLI: `fastapi`, `uvicorn[standard]`, `typer`
- Validation & config: `pydantic`, `python-dotenv`, `pyyaml`
- Fetch/extract: `requests`, `httpx`, `lxml`, `readability-lxml`, `beautifulsoup4`, `feedparser`
- Search: `whoosh`
- Utilities: `python-slugify`, `tenacity`
- Tests: `pytest`, `pytest-asyncio`

Additions later (e.g., Gmail API client, OpenRouter SDK) plug cleanly into this list.

---

## 5. Configuration & Secrets
Environment variables to establish before coding the worker:
| Variable | Purpose |
| --- | --- |
| `GMAIL_USERNAME` | `zoheri+atlas@gmail.com` |
| `GMAIL_APP_PASSWORD` | Provided app password (`ekgy yvgg wsrz uyeo`) |
| `GMAIL_LABELS` | JSON/CSV list → default `["Atlas", "Newsletter"]` (case-insensitive match) |
| `QUEUE_ROOT` | `data/queue` |
| `BACKLOG_ROOT` | `data/backlog` |
| `ARCHIVE_ROOT` | `data/archives` |
| `DATABASE_PATH` | `data/atlas_vos.db` |
| `WHOOSH_INDEX_PATH` | `data/search_index` |
| `RSS_CONFIG_PATH` | `config/feeds.yaml` |
| `ATLAS_API_KEY` | Optional API auth for FastAPI/TrojanHorse |

`.env.example` will hold templates for all of the above so the system "just works" after `cp .env.example .env`.

---

## 6. Queue & Worker Contract
- Jobs are JSON files named `<uuid>.json` with top-level keys: `id`, `type`, `payload`, `source`, `created_at`, `origin_manifest_id` (link back to the file we staged), `notes`.
- Validation happens before moving into `data/queue/inbox`. Invalid envelopes stay beside `source_drops/` with error logs until fixed.
- Worker loop:
  1. If `processing/` is non-empty, resume that job (enables crash-safe restarts).
  2. Otherwise, pop the lexicographically oldest file in `inbox/` and move to `processing/`.
  3. Dispatch to handler modules (URL/email/rss/backlog/trojanhorse).
  4. Archive HTML/text/images → `data/archives/YYYY-MM/uuid/` while storing metadata + storage paths in SQLite.
  5. Index canonical text via Whoosh.
  6. Move job JSON to `completed/` and append an audit row in SQLite. On exception, move to `failed/` and emit `.error.txt` with stack trace for later replay.

This keeps processing trivial; sophistication happens upstream when we convert raw files into job envelopes.

---

## 7. Ingestion Surface
- **Gmail:** Poll labels `Atlas` + `Newsletter`, parse inline URLs, attachments, multi-part HTML, and create jobs with payloads referencing archived raw `.eml` copies in `data/raw/emails/YYYY-MM/`.
- **RSS:** `config/feeds.yaml` will enumerate podcast + article feeds. Poll hourly, compute fingerprint `hash(link + published)` to avoid duplicates, and queue new stories.
- **Backlog:** `config/backlog_sources.yaml` maps staged files to parser functions (`instapaper_csv`, `newsletter_batch`, `atlas_unified_db`, `articles_directory`). Each parser emits `QueueJob`s referencing the `source_manifest` ID to guarantee provenance.
- **TrojanHorse & Manual URLs:** FastAPI + CLI endpoints simply validate + drop job files—no direct DB writes outside the worker.

---

## 8. Migration Strategy
1. **Record provenance** (already done) so we have a checklist of assets staged inside the repo.
2. Build backlog parsers per file type—each parser will update an auxiliary log under `data/backlog/logs/` indicating rows converted to queue jobs.
3. Feed queue gradually to avoid overwhelming the worker; once a staged dataset is fully converted, write a marker file `processed/<dataset>.done` and set the manifest `status` to `processed`.
4. For `atlas_unified.db`, we will write a dedicated migration script that reads existing tables, emits queue jobs (or direct DB inserts if already fully normalized) while keeping exported data in `source_drops/` unchanged.

---

## 9. Dashboard & Status Surfaces
- FastAPI will expose `/vos/status` JSON and `/vos/dashboard` HTML (no fake data).
- `scripts/status_vos.sh` will print queue counts, last 10 ingestions, failure tally, and Gmail/RSS poll timestamps so we can trust the headless worker.

---

## 10. Next Actions
1. Wire `.env.example` with every variable listed above.
2. Scaffold `vos/` modules with dataclasses + stub functions so we can iterate source-by-source.
3. Implement backlog parser for Instapaper CSV + newsletter JSON to validate job flow before touching Gmail/RSS.
4. Replace old CLI entrypoints with Typer commands under `vos/cli.py` and deprecate the podcast-specific scripts once new pipeline is stable.

With the staging + manifest in place and dependencies captured, we can start coding without revisiting foundational decisions.
