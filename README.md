# Atlas - Podcast Transcript Discovery System

**Atlas discovers and processes podcast transcripts from 73 curated podcasts (2,373 episodes).**

## 🚀 Quick Start

### Using Makefile (Recommended)
```bash
make setup    # First time: create venv and install dependencies
make status   # Check system status
make run      # Start Atlas processor
make api      # Start REST API server
make test     # Run test suite
```

### Traditional Commands
```bash
./atlas_status.sh           # Check status
./start_atlas.sh            # Start processing (if script exists)
python3 processors/atlas_manager.py  # Run processor directly
```

### REST API
```bash
# Using Makefile
make api

# Or directly
atlas api                    # Default: localhost:7444
atlas api --host 0.0.0.0 --port 8787    # Custom host/port
atlas api --reload           # Auto-reload for development
```

---

## 📊 System Status

**Current Progress:** 750 transcripts found (31% of 2,373 episodes)

**To check real-time status:** Run `./atlas_status.sh` for:
- ✅ Processing status and uptime
- 📊 Transcript discovery progress
- ⚡ Recent activity (5 min window)
- 🌐 External API issues
- 🚀 Quick commands

---

## 🎯 What Atlas Does

1. **Discovers podcast transcripts** from defined sources per podcast
2. **Processes content** through quality assurance pipeline
3. **Stores results** in searchable database
4. **Continues processing** until target transcripts per podcast reached

### Transcript Sources (Per Podcast)
- **First-party sites** (99% Invisible, Acquired, etc.)
- **Third-party aggregators** (Podscribe, HappyScribe, etc.)
- **RSS feeds** (working reliably)
- **Direct crawling** (when defined source available)

---

## 🛡️ Status Check Command

**Atlas provides a single command to check system health:**

```bash
./atlas_status.sh
```

**This shows:**
- 🔥 Process status and runtime
- 📊 Current transcript counts
- ⏳ Episodes pending/processing/completed
- ⚡ Recent activity (last 5 minutes)
- 🌐 External API issues
- 📊 Overall progress percentage

**Example output:**
```
🎯 ATLAS PODCAST PROCESSING STATUS
==================================
📅 2025-11-21 13:34:29

🔥 PROCESS STATUS:
  ✅ Atlas Manager: RUNNING (PID: 130330, Uptime: 01:50:15)

📊 TRANSCRIPT DISCOVERY:
  📈 Total Episodes: 2373
  ✅ Completed: 746
  🎯 Transcripts Found: 750
  ⏳ Pending: 1472
  📊 Progress: 31% (transcripts found)
```

---

## 🔧 Architecture

**System Components:**
- `atlas_manager.py` - Main processing loop
- `data/databases/` - SQLite databases for episode tracking
- `config/` - Transcript source mappings per podcast
- `processors/` - Content discovery and extraction modules
- `logs/` - Real-time processing logs

**Processing Strategy:**
1. Uses defined transcript sources per podcast
2. Falls back to multiple discovery methods
3. Stores all results for quality analysis
4. Continues processing until targets reached

---

## 🌐 REST API Integration

Atlas includes a comprehensive REST API that enables integration with external systems like TrojanHorse, web applications, and automation scripts.

### Start API Server

```bash
atlas api                              # Default: localhost:7444
atlas api --host 0.0.0.0 --port 8787  # Custom host/port
atlas api --reload                     # Auto-reload for development
atlas api --workers 4                  # Multiple workers
```

### API Endpoints

#### Core API (prefix: `/api/v1/`)
- **Health Check**: `GET /api/v1/health`
- **Content Search**: `GET /api/v1/search`
- **Content Management**: `/api/v1/content/*`
- **Analytics**: `/api/v1/dashboard/*`

#### TrojanHorse Integration (prefix: `/trojanhorse/`)
- **Health**: `GET /trojanhorse/health`
- **Ingest Single**: `POST /trojanhorse/ingest`
- **Ingest Batch**: `POST /trojanhorse/ingest/batch`
- **Statistics**: `GET /trojanhorse/stats`

### TrojanHorse Integration

Atlas provides dedicated endpoints for ingesting notes from TrojanHorse:

```bash
# Check Atlas health
curl http://localhost:7444/trojanhorse/health

# Ingest single note (with authentication)
curl -X POST http://localhost:7444/trojanhorse/ingest \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-atlas-api-key" \
  -d '{
    "id": "note-123",
    "title": "Meeting about Project X",
    "body": "Discussed timeline and deliverables...",
    "category": "meeting",
    "project": "project-x"
  }'

# Ingest batch notes
curl -X POST http://localhost:7444/trojanhorse/ingest/batch \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-atlas-api-key" \
  -d '{
    "notes": [
      {"id": "note-1", "title": "Idea 1", "body": "..."},
      {"id": "note-2", "title": "Task 2", "body": "..."}
    ]
  }'
```

#### Environment Configuration

For TrojanHorse integration, set these environment variables:

```bash
# Required for TrojanHorse to find Atlas
export ATLAS_API_URL="http://localhost:7444"

# Optional (if Atlas requires authentication)
export ATLAS_API_KEY="your-secret-api-key"
```

#### Workflow Example

```bash
# 1. Start Atlas API
atlas api --host 0.0.0.0 --port 8787

# 2. Configure TrojanHorse (in separate terminal)
export ATLAS_API_URL="http://localhost:8787"
export ATLAS_API_KEY="your-key"

# 3. Promote TrojanHorse notes to Atlas
th promote-to-atlas "note1,note2,note3"
```

### API Documentation

- **Interactive Docs**: http://localhost:7444/docs
- **TrojanHorse Integration**: http://localhost:7444/trojanhorse/docs
- **OpenAPI Schema**: http://localhost:7444/openapi.json

### Authentication

Atlas supports API key authentication for secure integrations:

```bash
# Set API key in Atlas environment
export ATLAS_API_KEY="your-secure-api-key"

# Use in requests
curl -H "X-API-Key: your-secure-api-key" http://localhost:7444/api/v1/...
```

### Rate Limiting & Security

- Localhost-only binding by default (127.0.0.1)
- API key authentication for cross-origin requests
- Request validation and sanitization
- Error handling and logging

## 📝 Quick Reference

| Command | Purpose |
|---------|---------|
| `make setup` | **First-time setup** (create venv, install deps) |
| `make status` | **Check system status** |
| `make run` | Start Atlas processing |
| `make api` | Start REST API server |
| `make test` | Run test suite |
| `make clean` | Remove generated files |
| `curl http://localhost:7444/health` | Check API health |
| `tail -f logs/atlas_manager.log` | View live processing logs |

**See `Makefile` for all available commands.**

---

## 🎯 Target

**Goal:** Discover transcripts for all defined episodes across 73 curated podcasts
**Method:** Direct crawling of defined transcript sources per podcast
**Status:** Active processing with 750 transcripts discovered

---

## 📚 Documentation

- **[Setup Guide](docs/SETUP.md)** - First-time setup and configuration
- **[Architecture](docs/CURRENT_ARCHITECTURE.md)** - System design and components
- **[Configuration](docs/CONFIGURATION.md)** - Environment variables and settings
- **[Operations Runbook](docs/RUNBOOK.md)** - Day-to-day operations and troubleshooting
- **[Testing Guide](docs/TESTING.md)** - Running and writing tests
- **[API Documentation](API_DOCUMENTATION.md)** - REST API reference
- **[Migration History](docs/migrations/)** - Historical migration reports

**Current Tier**: SQLite + File-based processing
**Upgrade Trigger**: > 500K episodes OR multi-instance coordination needed
**Next Tier**: PostgreSQL + connection pooling

---

*For detailed documentation, see `docs/` directory.*