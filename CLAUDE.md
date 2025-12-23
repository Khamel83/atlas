<!-- ONE_SHOT v5.5 -->
# IMPORTANT: Read AGENTS.md - it contains skill and agent routing rules.
#
# Skills (synchronous, shared context):
#   "build me..."     → oneshot-core
#   "plan..."         → create-plan
#   "implement..."    → implement-plan
#   "debug/fix..."    → debugger
#   "deploy..."       → push-to-cloud
#   "ultrathink..."   → thinking-modes
#   "beads/ready..."  → beads (persistent tasks)
#
# Agents (isolated context, background):
#   "security audit..." → security-auditor
#   "explore/find all..." → deep-research
#   "background/parallel..." → background-worker
#   "coordinate agents..." → multi-agent-coordinator
#
# Always update TODO.md as you work.
<!-- /ONE_SHOT -->

# Atlas - Claude Instructions

## Status Check (Do This First)

When user asks "how are we doing?", "status?", "how is atlas running?", or any variant:
**Immediately run** `./venv/bin/python scripts/atlas_status.py` - no questions, no preamble.

## Essential Commands

```bash
# Status
./venv/bin/python scripts/atlas_status.py           # Everything at once
./venv/bin/python scripts/atlas_status.py --podcasts  # Per-podcast breakdown

# Quality
./venv/bin/python scripts/verify_content.py --report

# Tests
./venv/bin/pytest tests/ -v

# Podcast CLI
python -m modules.podcasts.cli status
python -m modules.podcasts.cli fetch-transcripts --all
python -m modules.podcasts.cli discover --all

# Embeddings/Search
./scripts/run_with_secrets.sh python -m modules.ask.indexer --all
./scripts/run_with_secrets.sh python -m modules.ask.cli ask "question"

# Enrichment (ad removal)
./venv/bin/python scripts/run_enrichment.py

# API
./venv/bin/uvicorn api.main:app --port 7444
```

## Key Paths

| Path | Purpose |
|------|---------|
| `data/podcasts/{slug}/transcripts/` | Podcast transcripts |
| `data/content/article/` | Fetched articles |
| `data/content/newsletter/` | Gmail newsletters |
| `data/stratechery/` | Stratechery archive |
| `data/clean/` | Ad-stripped versions (for indexing) |
| `data/indexes/atlas_vectors.db` | Embeddings vector store |
| `data/podcasts/atlas_podcasts.db` | Podcast/episode database |

## Active Modules (11)

```
modules/
├── podcasts/       # Transcript sourcing (16 resolvers)
├── ingest/         # URL/Gmail ingestion
├── storage/        # File storage + SQLite
├── pipeline/       # Content orchestration
├── quality/        # Content verification
├── enrich/         # Ad removal, URL cleanup
├── links/          # Link discovery pipeline
├── ask/            # Semantic search & Q&A
├── status/         # Unified monitoring
├── browser/        # Playwright wrapper
└── notifications/  # Alerts (Telegram, ntfy)
```

## Systemd Timers (13)

Check with: `systemctl list-timers | grep atlas`

- `atlas-podcast-discovery` - Find new episodes (6am/6pm)
- `atlas-transcripts` - Fetch transcripts (every 4h)
- `atlas-gmail` - Check newsletters (every 5min)
- `atlas-enrich` - Ad removal (Sunday 4am)
- `atlas-verify` - Quality check (daily 5am)
- `atlas-whisper-download` - Audio for local transcription (every 2h)
- `atlas-whisper-import` - Import Whisper transcripts (hourly)

## Configuration

| File | Purpose |
|------|---------|
| `config/podcast_limits.json` | Per-podcast episode limits |
| `config/mapping.yml` | Resolver config per podcast |
| `config/ask_config.yml` | Embeddings/LLM settings |
| `~/.config/atlas/stratechery_cookies.json` | Stratechery auth |

## Common Operations

**Add new podcast:**
1. Add to `config/podcast_limits.json`
2. Add to `config/mapping.yml` if custom resolver needed
3. Run: `python -m modules.podcasts.cli discover --slug new-podcast`

**Refresh Stratechery cookies:**
1. Log into Stratechery in browser
2. Export cookies → `~/.config/atlas/stratechery_cookies.json`

**Re-index embeddings:**
```bash
./scripts/run_with_secrets.sh python -m modules.ask.indexer --all
```

## Database Quick Queries

```bash
# Pending transcripts by podcast
sqlite3 data/podcasts/atlas_podcasts.db "
SELECT p.slug, COUNT(*) FROM episodes e
JOIN podcasts p ON e.podcast_id = p.id
WHERE e.transcript_status = 'unknown'
GROUP BY p.slug ORDER BY COUNT(*) DESC"

# Quality breakdown
sqlite3 data/quality/verification.db "
SELECT quality, COUNT(*) FROM verifications GROUP BY quality"
```

## Full Documentation

See **README.md** for complete documentation including:
- Architecture details
- All CLI commands
- VPN proxy setup
- Mac Mini Whisper transcription
- Content enrichment pipeline
- Link discovery system
- Atlas Ask semantic search
