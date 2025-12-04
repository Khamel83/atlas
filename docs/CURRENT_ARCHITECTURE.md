# Atlas Current Architecture

**Last Updated**: 2025-12-04
**Status**: 🔄 In Transition (Homelab Migration)

## Executive Summary

Atlas is a podcast transcript discovery and content ingestion system using a file-first architecture with SQLite for tracking. Currently processing 2,373 episodes across 73 podcasts with 750 transcripts found (31% completion).

## Active Components

### Production Processor
**`processors/atlas_manager.py`** - Primary coordinator
- **Status**: ✅ Active
- **Started by**: `scripts/start/start_atlas.sh`
- **Systemd**: `systemd/atlas-manager.service`
- **Architecture**: Log-stream based processing
- **Function**: Continuous transcript discovery and processing

### REST API
**Location**: `web/api/` or `api/main.py`
- **Port**: 7444 (default)
- **Endpoints**: `/health`, `/api/v1/*`, `/trojanhorse/*`
- **Systemd**: `systemd/atlas-api.service`
- **Function**: REST API for external integrations (TrojanHorse, etc.)

### Content Processing
**Recently Active**: `atlas_simple_processor.py` (root level)
- **Purpose**: One-time bulk content processing
- **Status**: ⏳ Used for migrations
- **Last Run**: Nov 30, 2025 (Mac archive migration)

## Data Flow

```
1. Content Sources
   ├── RSS Feeds (config/feeds.yaml)
   ├── Email (Gmail integration)
   ├── Web APIs (YouTube, etc.)
   └── Manual imports

2. Processing Pipeline
   ├── Discovery (find transcripts)
   ├── Extraction (download/parse)
   ├── Validation (quality checks)
   └── Storage (files + SQLite tracking)

3. Storage Layer
   ├── Files: markdown/, html/, metadata/
   ├── Database: podcast_processing.db (SQLite)
   └── Tracking: content_tracker.json

4. Access Layer
   ├── REST API (port 7444)
   ├── CLI (atlas status, etc.)
   └── Direct database queries
```

## Database Schema

**Primary Database**: `podcast_processing.db` (SQLite)

**Key Tables**:
- `podcasts` - Podcast metadata
- `episodes` - Episode tracking (2,373 records)
- `processing_queue` - Work queue
- `processing_log` - Execution history

**Location**: `data/databases/` or root level

**TODO**: Document full schema

## File Architecture

### File-First Principle
Atlas prioritizes file-based storage over database:
- **Raw content**: Files in native format
- **Database**: Tracking, metadata, relationships only
- **Benefits**: IO-throttled (not database-locked), portable, scalable

### Directory Structure
```
atlas/
├── processors/          # Processing code (147 active after cleanup)
│   ├── atlas_manager.py # Main coordinator ✅
│   └── archive/         # Deprecated processors
├── data/                # Runtime data (NOT in git)
│   ├── databases/       # SQLite databases
│   ├── queue/           # Processing queues
│   └── archives/        # Archived content
├── html/                # Generated HTML (NOT in git)
├── markdown/            # Generated markdown (NOT in git)
├── metadata/            # Generated metadata (NOT in git)
├── config/              # YAML/JSON configuration
├── api/                 # REST API code
└── scripts/             # Automation scripts
```

## Deployment

### Current: Development/Manual
- **Start**: `./scripts/start/start_atlas.sh` or `make run`
- **Status**: `./atlas_status.sh` or `make status`
- **Stop**: `pkill -f atlas_manager.py` or `make stop`

### Available: Systemd
```bash
# Install service
sudo cp systemd/atlas-manager.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable atlas-manager
sudo systemctl start atlas-manager

# Check status
sudo systemctl status atlas-manager
```

**TODO**: Verify systemd service configuration for current paths

## Key Technologies

| Component | Technology | Why |
|-----------|-----------|-----|
| **Language** | Python 3.8+ | Ecosystem, libraries |
| **Database** | SQLite | Single-file, no server, < 500K records |
| **Web API** | FastAPI | Modern, async, auto-docs |
| **Search** | Whoosh | Pure Python, file-based |
| **Content Parse** | BeautifulSoup, lxml | Robust HTML/XML parsing |

## Integration Points

### TrojanHorse Integration
- **Endpoints**: `/trojanhorse/ingest`, `/trojanhorse/stats`
- **Function**: Ingest notes from TrojanHorse system
- **Auth**: Optional API key via `X-API-Key` header

### Email Integration
- **Gmail API**: Fetch emails with specific labels
- **Config**: `GMAIL_USERNAME`, `GMAIL_APP_PASSWORD` in `.env`

### YouTube Integration
- **YouTube API**: Fetch video transcripts
- **Config**: `YOUTUBE_API_KEY` (optional)

## Current Tier & Upgrade Path

### Current Tier: SQLite + Files
- **Episodes**: 2,373 (31% with transcripts)
- **Storage**: Mixed (files + SQLite tracking)
- **Deployment**: Single-machine
- **Performance**: Adequate for current scale

### Upgrade Trigger
Move to next tier when:
- **> 500K episodes** OR
- **Multi-instance coordination needed** OR
- **Current architecture hits performance limits**

### Next Tier: PostgreSQL + Workers
- **Database**: PostgreSQL with connection pooling
- **Processing**: Multiple worker processes
- **Coordination**: Distributed task queue

## Known Issues & TODOs

### Immediate
- [ ] Verify active processor (atlas_manager.py vs others)
- [ ] Document complete database schema
- [ ] Consolidate processor duplicates (147 → ~20 core files)
- [ ] Update systemd services for current paths

### Migration Context
- Recent Mac → Ubuntu homelab migration
- 29,417 content files processed
- 352MB+ data migrated
- Migration docs in root (need to move to `docs/migrations/`)

## Monitoring & Observability

### Health Checks
```bash
# System status
./atlas_status.sh

# API health
curl http://localhost:7444/health

# Database check
sqlite3 podcast_processing.db "SELECT COUNT(*) FROM episodes"
```

### Logs
- **Manager**: `logs/atlas_manager.log`
- **Systemd**: `journalctl -u atlas-manager`
- **API**: stdout/journald

### Metrics
- **Endpoint**: `/metrics` (TODO: verify)
- **Database**: Episode counts, transcript discovery rates
- **Processing**: Items processed per minute

## Architecture Decisions & Rationale

### Why SQLite?
- **Single-file portability** (easy backup)
- **No server overhead**
- **Sufficient for < 500K records** (currently 2,373)
- **Upgrade path clear** (→ PostgreSQL when needed)

### Why File-First?
- **Avoid database locking** (IO-throttled instead)
- **Content in native format** (markdown, HTML)
- **Easy to inspect/debug** (just read files)
- **Portable** (tar/zip entire directory)

### Why Log-Stream Architecture?
- **High-performance** (as per atlas_manager.py)
- **Event-driven** (not polling)
- **Fast file operations** (vs database bottlenecks)

## Development

See `docs/SETUP.md` for setup instructions.
See `README.md` for quick start guide.
See `Makefile` for common tasks.

---

**Questions?** Check `processors/README.md` for processor details.
