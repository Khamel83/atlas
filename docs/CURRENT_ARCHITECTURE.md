# Atlas Current Architecture

**Last Updated**: 2025-12-06
**Status**: Clean Architecture Implemented

## Executive Summary

Atlas is a podcast transcript discovery and content ingestion system. The codebase has been cleaned up with:
- 34 passing tests
- Clean FastAPI REST API
- Modular structure in `modules/`

## Active Components

### REST API
**Location**: `api/main.py`
- **Port**: 7444 (default)
- **Routers**: health, podcasts, content, search
- **Function**: REST API for external integrations

### Core Modules
**Location**: `modules/`
- **podcasts/**: Podcast management with PodcastStore
- **storage/**: FileStore + IndexManager
- **pipeline/**: Content processing
- **ingest/**: Gmail, YouTube ingestion
- **notifications/**: Telegram/ntfy alerts

## Data Flow

```
1. Content Sources
   ├── RSS Feeds (config/feeds.yaml)
   ├── Email (Gmail integration)
   ├── YouTube
   └── Manual imports

2. Processing Pipeline
   ├── Discovery (find transcripts)
   ├── Extraction (download/parse)
   ├── Validation (quality checks)
   └── Storage (files + SQLite tracking)

3. Storage Layer
   ├── Files: data/content/ (organized by type/date)
   ├── Podcasts: data/podcasts/atlas_podcasts.db
   └── Index: data/indexes/atlas_index.db

4. Access Layer
   ├── REST API (port 7444)
   ├── CLI (python -m modules.podcasts.cli)
   └── Direct database queries
```

## Database Schema

### Podcast Store (`modules/podcasts/store.py`)

**Location**: `data/podcasts/atlas_podcasts.db`

```sql
-- Podcast metadata
CREATE TABLE podcasts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    rss_url TEXT NOT NULL,
    site_url TEXT,
    resolver TEXT DEFAULT 'generic_html',
    episode_selector TEXT,
    transcript_selector TEXT,
    config TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Episode tracking
CREATE TABLE episodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    podcast_id INTEGER NOT NULL,
    guid TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    publish_date TIMESTAMP,
    transcript_url TEXT,
    transcript_status TEXT DEFAULT 'unknown',
    transcript_path TEXT,
    metadata TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (podcast_id) REFERENCES podcasts (id),
    UNIQUE (podcast_id, guid)
);

-- Transcript sources discovered
CREATE TABLE transcript_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    episode_id INTEGER NOT NULL,
    resolver TEXT NOT NULL,
    url TEXT NOT NULL,
    confidence REAL DEFAULT 0.0,
    metadata TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (episode_id) REFERENCES episodes (id)
);

-- Discovery run tracking
CREATE TABLE discovery_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    podcast_id INTEGER NOT NULL,
    resolver TEXT NOT NULL,
    episodes_found INTEGER DEFAULT 0,
    transcripts_found INTEGER DEFAULT 0,
    errors INTEGER DEFAULT 0,
    duration_seconds REAL DEFAULT 0.0,
    status TEXT DEFAULT 'running',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (podcast_id) REFERENCES podcasts (id)
);
```

### Content Index (`modules/storage/index_manager.py`)

**Location**: `data/indexes/atlas_index.db`

```sql
CREATE TABLE content_index (
    content_id TEXT PRIMARY KEY,
    content_type TEXT NOT NULL,
    source_type TEXT NOT NULL,
    title TEXT NOT NULL,
    source_url TEXT,
    status TEXT DEFAULT 'pending',
    file_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Transcript Status Values

| Status | Description |
|--------|-------------|
| `unknown` | Not yet processed |
| `found` | Transcript URL discovered |
| `missing` | No transcript available |
| `fetched` | Transcript downloaded |
| `failed` | Processing error |

## File Architecture

### Directory Structure
```
atlas/
├── api/                 # REST API
│   ├── main.py         # FastAPI app entry
│   └── routers/        # Endpoint routers
├── modules/            # Core business logic
│   ├── podcasts/       # Podcast management
│   ├── storage/        # File/index storage
│   ├── pipeline/       # Content processing
│   ├── ingest/         # Ingestion handlers
│   └── notifications/  # Alerts
├── tests/              # Test suite (34 tests)
├── scripts/            # Operational scripts
├── config/             # Configuration
├── data/               # Runtime data (gitignored)
└── archive/            # Archived legacy code
```

## Running Atlas

### Quick Start
```bash
./scripts/setup.sh          # Create venv, install deps
./scripts/status.sh         # Check system health
./venv/bin/uvicorn api.main:app --port 7444  # Start API
./venv/bin/pytest tests/ -v # Run tests
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/metrics` | GET | System metrics |
| `/api/podcasts/` | GET | List podcasts |
| `/api/podcasts/stats` | GET | Statistics |
| `/api/content/` | GET | List content |
| `/api/search/?q=` | GET | Search |

## Key Technologies

| Component | Technology | Why |
|-----------|-----------|-----|
| **Language** | Python 3.12+ | Modern async |
| **Database** | SQLite | Single-file, no server |
| **Web API** | FastAPI | Modern, async, auto-docs |
| **Search** | Whoosh | Pure Python, file-based |
| **Testing** | pytest | Clean, simple |

## Current Tier & Upgrade Path

### Current Tier: SQLite + Files
- **Tests**: 34 passing
- **API Routers**: 4
- **Modules**: 5 core
- **Deployment**: Single-machine

### Upgrade Trigger
Move to PostgreSQL when:
- > 500K episodes OR
- Multi-instance coordination needed

## Archived Code

Legacy code is preserved but not used:
- `archive/legacy_api/` - 12 broken API routers
- `archive/legacy_tests/` - 79 broken test files
- `archive/legacy_processors/` - 216 old processors

---

*For API docs, run the API and visit `/docs`*
