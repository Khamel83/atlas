# Atlas - LLM Overview

**Last Updated**: 2025-12-06
**ONE_SHOT Mode**: Heavy (multi-service with full ops)
**Status**: Production-ready, active development

---

## What Is This Project?

Atlas is a **podcast transcript discovery and content ingestion system** that automatically finds, downloads, processes, and stores transcripts from 73 curated podcasts. It runs on homelab infrastructure with $0 cloud costs.

### The Problem It Solves

Podcast transcripts are scattered across the internet - some on official sites, others on third-party services like Podscribe, HappyScribe, Rev.com, etc. Manually finding and organizing transcripts is tedious. Atlas automates this entire workflow.

### Current State

- **2,373 total episodes** tracked across 73 podcasts
- **750 transcripts found** (31% completion)
- **SQLite database** for tracking, files for content
- **REST API** running on port 7444
- **Continuous processing** via `atlas_manager.py`

---

## Architecture Overview

```
atlas/
├── processors/           # Core processing engines (135 Python files)
│   └── atlas_manager.py  # PRIMARY - log-stream processor
├── modules/              # Feature modules
│   ├── transcripts/      # Transcript discovery strategies
│   ├── podcasts/         # Podcast/episode management
│   └── ingestion/        # URL/content ingestion
├── web/                  # FastAPI REST API
│   └── api.py            # Main API (34K lines)
├── config/               # YAML/JSON configuration
│   └── feeds.yaml        # Podcast RSS feeds
├── scripts/              # Operational scripts
├── data/                 # Runtime data (not in git)
│   └── databases/        # SQLite databases
└── tests/                # Test suite (19K+ lines)
```

### Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| **Main Processor** | `processors/atlas_manager.py` | Continuous transcript discovery |
| **REST API** | `web/api.py` | External integrations (TrojanHorse) |
| **Database** | `podcast_processing.db` | Episode tracking, processing state |
| **Transcript Discovery** | `modules/transcript_discovery/` | Multi-strategy transcript finding |
| **URL Ingestion** | `modules/ingestion/` | Content classification and routing |

### Data Flow

```
1. Sources → 2. Discovery → 3. Extraction → 4. Storage → 5. Access

1. RSS feeds, Gmail, YouTube, manual imports
2. Find transcript URLs (Tavily, crawlers, direct links)
3. Download and parse content
4. Store files + update SQLite tracking
5. REST API, CLI, direct queries
```

---

## Tech Stack

| Layer | Technology | Why |
|-------|------------|-----|
| **Language** | Python 3.8+ | Ecosystem, async support |
| **Database** | SQLite | Single-file, no server, < 500K records |
| **API** | FastAPI + Uvicorn | Modern, async, auto-docs |
| **Search** | Whoosh | Pure Python full-text search |
| **HTTP** | Requests, HTTPX | Sync and async clients |
| **Parsing** | BeautifulSoup, lxml | HTML/XML parsing |
| **Scheduling** | APScheduler | Background job scheduling |

---

## Running Atlas

### Quick Start

```bash
make setup    # Create venv, install deps
make run      # Start processor
make api      # Start REST API (port 7444)
make status   # Check system health
```

### Manual Commands

```bash
# Processor
python3 processors/atlas_manager.py

# API
uvicorn api.main:app --host 0.0.0.0 --port 7444

# Status
./atlas_status.sh
```

### Health Checks

```bash
curl http://localhost:7444/health        # API health
curl http://localhost:7444/api/v1/health # Core API
sqlite3 podcast_processing.db "SELECT COUNT(*) FROM episodes"
```

---

## Database Schema (Key Tables)

```sql
-- Podcasts being tracked
podcasts (id, name, rss_url, transcript_source, status)

-- Individual episodes
episodes (id, podcast_id, title, url, transcript_status,
          transcript_url, processed_at)

-- Processing queue
processing_queue (id, episode_id, priority, status, attempts)

-- Execution history
processing_log (id, episode_id, action, result, timestamp)
```

---

## Configuration

### Environment Variables (.env)

```bash
# Database
DATABASE_URL=sqlite:///podcast_processing.db

# API
ATLAS_API_PORT=7444
ATLAS_API_KEY=your-secret-key  # Optional auth

# External APIs (optional)
TAVILY_API_KEY=...             # Web search for transcripts
YOUTUBE_API_KEY=...            # YouTube integration
GMAIL_USERNAME=...             # Email ingestion
GMAIL_APP_PASSWORD=...
```

### Podcast Configuration (config/feeds.yaml)

```yaml
podcasts:
  - name: "99% Invisible"
    rss: "https://feeds.99percentinvisible.org/99percentinvisible"
    transcript_source: "https://99percentinvisible.org/episodes/"
  # ... 73 podcasts total
```

---

## Integrations

### TrojanHorse (Note Ingestion)

```bash
# Ingest notes
POST /trojanhorse/ingest
{
  "id": "note-123",
  "title": "Meeting Notes",
  "body": "Content...",
  "category": "meeting"
}

# Check stats
GET /trojanhorse/stats
```

### Email (Gmail)

- Fetches emails with specific labels
- Extracts content for ingestion
- Configured via `GMAIL_*` env vars

### YouTube

- Fetches video transcripts
- Optional YouTube API integration

---

## Development

### Testing

```bash
make test                    # Run full suite
pytest tests/ -v             # Verbose
pytest tests/unit/ -k "test_" # Specific tests
```

### Code Quality

```bash
make lint    # Ruff linting
make format  # Black formatting
```

### Adding a New Podcast

1. Add entry to `config/feeds.yaml`
2. Define transcript source pattern
3. Run processor to discover episodes

---

## Current Limitations & TODOs

### Known Gaps

- [ ] ~98 TODO comments across codebase (mostly optional features)
- [ ] YouTube transcript extraction not fully implemented
- [ ] Google Custom Search API integration pending (has fallback)
- [ ] Multiple processor variants need consolidation (135 files)

### Upgrade Triggers

Move to PostgreSQL when:
- Episodes > 500K
- Multi-instance coordination needed
- Current architecture hits limits

---

## File Locations Quick Reference

| What | Where |
|------|-------|
| Main processor | `processors/atlas_manager.py` |
| REST API | `web/api.py` or `api/main.py` |
| Database | `podcast_processing.db` (root or `data/databases/`) |
| Logs | `logs/atlas_manager.log` |
| Config | `config/feeds.yaml`, `.env` |
| Tests | `tests/` |

---

## ONE_SHOT Compliance

This project follows ONE_SHOT v3.0 patterns:

- **AGENTS.md**: Present (governing spec)
- **LLM-OVERVIEW.md**: This file
- **PRD.md**: Project requirements document
- **Scripts**: `scripts/setup.sh`, `start.sh`, `stop.sh`, `status.sh`
- **Health endpoints**: `/health`, `/metrics`
- **Storage tier**: SQLite (upgrade path to PostgreSQL documented)

---

*For detailed API docs, see `/docs` endpoint when API is running.*
*For architecture details, see `docs/CURRENT_ARCHITECTURE.md`.*
