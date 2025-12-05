# Atlas Diagnostic Report (Phase 1)

**Generated:** 2025-12-05
**Repository:** git@github.com:Khamel83/atlas.git
**Working Directory:** /home/khamel83/github/atlas
**Branch:** main

---

## 1. Repository Layout

**Root Directory Summary:**
- 26 primary directories covering processors, modules, integrations, API, tools, tests, and documentation
- Well-organized with clear module separation for different concerns
- Contains both active code and archived/migration content

**Key Directories:**

| Directory | Purpose |
|-----------|---------|
| `processors/` | Core processing logic including `atlas_manager.py`, transcript discovery, and batch processing |
| `modules/` | Modular components: ingestion, podcasts, transcript_discovery, content_extraction, analysis |
| `integrations/` | External service integrations: email, telegram, velja, YouTube API client |
| `web/api/` | FastAPI REST API server with routers for content, search, TrojanHorse, podcasts |
| `config/` | Configuration files including `podcast_sources.json` |
| `tools/` | Utilities for ingest, backup, development, maintenance, monitoring |
| `tests/` | Test suite with unit and integration tests (currently broken due to import issues) |
| `systemd/` | 25+ systemd service and timer unit files for scheduling |
| `vos/` | Virtual Operating System integration layer with API, ingestion, search, storage |
| `scripts/` | Operational scripts including OPML parser, transcription, deployment |
| `docs/` | 200+ documentation files covering architecture, operations, integrations |

**Ingestion-Related Modules Found:**
- `integrations/email/` - Email bridge (SMTP receiver) and webhook bridge
- `integrations/youtube_*.py` - YouTube API client, content processor, history importer
- `modules/ingestion/` - Email ingestion services, URL ingestion, newsletter processing
- `scripts/podemos_opml_parser.py` - Overcast OPML parser
- `scripts/podemos_transcription.py` - Whisper-based transcription system

---

## 2. Environment & Dependencies

**Python Version:** 3.12.3

**Virtual Environment:** Created at `.venv/`

**Dependencies Installation:** Successfully installed via `pip install -r requirements.txt`

**Top Installed Packages:**
- `fastapi 0.123.9` - REST API framework
- `uvicorn 0.38.0` - ASGI server
- `google-api-python-client 2.187.0` - Google API (Gmail, YouTube)
- `google-auth 2.41.1` / `google-auth-oauthlib 1.2.3` - OAuth support
- `beautifulsoup4 4.14.3` - HTML parsing
- `feedparser 6.0.12` - RSS/Atom feed parsing
- `whoosh 2.7.4` - Full-text search indexing
- `httpx 0.28.1` - Async HTTP client
- `pytest 9.0.1` - Testing framework

**Notable Dependency Issues:**
- `python-magic` was missing, required by web/api/main.py (installed manually)
- Multiple module import issues exist throughout the test suite

---

## 3. Tests & Status

### Atlas Status Script Output (`./atlas_status.sh`)
```
🎯 ATLAS PODCAST PROCESSING STATUS
==================================
📅 2025-12-05 05:31:12

🔥 PROCESS STATUS:
  ❌ Atlas Manager: NOT RUNNING

📊 TRANSCRIPT DISCOVERY:
  📈 Total Episodes: 0
  ✅ Completed: 0
  🎯 Transcripts Found: 0
  ⏳ Pending: 0
  🔄 Processing: 0
  ❌ Failed: 0

⚡ RECENT ACTIVITY (5 min):
  🎯 New transcripts (5 min): 0

🚀 QUICK START: ./start_atlas.sh
📋 FULL LOGS: tail -f logs/atlas_manager.log
==================================
```

### Test Suite Status

**Test Execution:** FAILED - Tests cannot be collected due to widespread import errors

**Root Cause:** Module import structure is fragmented:
- Tests expect imports from `helpers.config`, `api.main`, `core.database` etc.
- These modules exist but Python path is not properly configured
- `conftest.py` only adds `web/api` to path, not the root or other modules

**Key Import Errors:**
1. `ModuleNotFoundError: No module named 'helpers.config'`
2. `ModuleNotFoundError: No module named 'api'`
3. `ModuleNotFoundError: No module named 'core'`
4. `tests/comprehensive_feature_test.py` calls `sys.exit(1)` on import failure

**Test Files Found:** 100+ test files across `tests/`, `tests/unit/`, `tests/integration/`

**Recommendation:** Fix PYTHONPATH configuration and test imports before Phase 2

---

## 4. Data & Databases

### Database Files Found

| Database | Path | Size |
|----------|------|------|
| podcast_processing.db | `./podcast_processing.db` | 45KB |
| atlas_content_before_reorg.db | `./data/databases/atlas_content_before_reorg.db` | 14MB |
| atlas_unified.db | `./data/databases/atlas_unified.db` | 2.1MB |
| atlas_index.db | `./atlas_content/atlas_index.db` | Empty |
| enhanced_search.db | `./web/api/data/enhanced_search.db` | - |

### Primary Podcast Database (`atlas_content_before_reorg.db`)

**Tables:**
- `podcasts` - 73 rows (podcast configurations)
- `episodes` - 2,373 rows (episode metadata)
- `processing_queue` - 2,373 rows (all queued status)
- `processing_log` - 24 rows
- `module_execution_log` - 0 rows

**Schema (podcasts):**
```
id, name, rss_feed, target_transcripts, processing_strategy,
priority, status, episodes_found, episodes_processed,
created_at, started_at, completed_at
```

**Top Podcasts by Episode Count:**
- Stratechery: 300 episodes
- Sharp Tech with Ben Thompson: 252 episodes
- Acquired: 208 episodes
- ACQ2 by Acquired: 111 episodes
- The Rewatchables: 100 episodes

**Processing Queue Status:**
- `queued`: 2,373 episodes (100% pending)

### Unified Content Database (`atlas_unified.db`)

**Tables:**
- `content_items` - 4,739 rows
- `system_metadata` - 4 rows
- `podcast_episodes` - 0 rows
- `processing_jobs` - 0 rows
- `content_analysis` - 0 rows
- `content_tags` - 0 rows

**Note:** The podcasts data has not been imported into the `podcast_processing.db` used by `atlas_status.sh`. The main data resides in `atlas_content_before_reorg.db`.

---

## 5. Existing Ingestion & API

### 5.1 Podcast Transcript System

**Architecture:** Log-stream based continuous processing

**Main Files:**
- `processors/atlas_manager.py` - Main processing loop manager
- `processors/atlas_log_processor.py` - Log-stream based batch processor

**Processing Loop:**
1. RSS Discovery (every 5 minutes) - discovers new episodes
2. Batch Processing (every 1 minute) - processes transcripts
3. Metrics Generation (every 5 minutes) - performance reporting

**Schedule Intervals:**
- RSS discovery: 300 seconds (5 min)
- Batch processing: 60 seconds (1 min)
- Metrics: 300 seconds (5 min)

### 5.2 Podcast Configuration (`config/podcast_sources.json`)

**Configured Sources (sample):**
- ATP (Accidental Tech Podcast) - `helpers.atp_transcript_scraper.ATPTranscriptScraper`
- This American Life - `helpers.tal_transcript_scraper.TALTranscriptScraper`
- 99% Invisible - `helpers.ninety_nine_pi_scraper.NinetyNinePiTranscriptScraper`
- Huberman Lab - `helpers.huberman_scraper.HubermanScraper`
- Lex Fridman Podcast - `helpers.lex_fridman_scraper.LexFridmanScraper`

**Fields per source:**
- `scraper_class`, `enabled`, `priority`, `requires_auth`, `success_rate`

### 5.3 API Endpoints

**API Server:** FastAPI at `web/api/main.py`
**Default Port:** 7444

**Core Endpoints:**
- `GET /health`, `GET /api/v1/health` - Health check
- `GET /api/v1/search` - Content search
- `POST /api/v1/content/submit-url` - URL submission
- `GET /api/v1/content/{id}` - Content retrieval
- `GET /api/v1/content/html` - HTML content browser

**TrojanHorse Integration:**
- `GET /trojanhorse/health` - Health check
- `POST /trojanhorse/ingest` - Single note ingest
- `POST /trojanhorse/ingest/batch` - Batch note ingest
- `GET /trojanhorse/stats` - Statistics

**API Routers (`web/api/routers/`):**
- `content.py`, `search.py`, `auth.py`, `dashboard.py`
- `podcast_progress.py`, `transcript_search.py`, `transcript_stats.py`
- `trojanhorse.py`, `worker.py`, `shortcuts.py`

### 5.4 Existing Integrations

**Email Integration (`integrations/email/`):**
- `email_bridge.py` - SMTP server on port 2525 that receives emails, extracts URLs, and sends to Atlas ingest endpoint
- `webhook_bridge.py` - Webhook-based email forwarding
- Status: **IMPLEMENTED** but uses hardcoded paths (`/home/ubuntu/dev/atlas/`)

**YouTube Integration (`integrations/`):**
- `youtube_api_client.py` - YouTube Data API v3 client with OAuth support
- `youtube_content_processor.py` - Video content processing
- `youtube_history_importer.py` - Watch history import
- Status: **IMPLEMENTED** but not fully wired into processing pipeline

**Email Ingestion Modules (`modules/ingestion/`):**
- `simple_email_ingester.py` - Email ingestion
- `simple_email_ingestion.py` - Alternative email processing
- `newsletter_processor.py` - Newsletter-specific processing
- `url_ingestion_service.py` - URL processing service
- `email_alerts.py` - Alert notifications
- Status: **IMPLEMENTED** but scattered implementations

**OPML/Overcast Support (`scripts/`):**
- `podemos_opml_parser.py` - Parses Overcast OPML exports to extract RSS feeds
- `podemos_feed_monitor.py` - Feed monitoring
- `podemos_episode_discovery.py` - Episode discovery
- Status: **IMPLEMENTED** - Ready for use

**Transcription (`scripts/`):**
- `podemos_transcription.py` - Whisper-based transcription with CLI and Python package support
- Status: **IMPLEMENTED** but requires Whisper installation

---

## 6. Scheduling & Operations

### Systemd Units (25+ files in `systemd/`)

**Core Services:**
| Service | Description |
|---------|-------------|
| `atlas-manager.service` | Main continuous processing loop |
| `atlas-api.service` | FastAPI server |
| `atlas-ingest.service` | Content ingestion (continuous mode) |
| `atlas-processor.service` | Batch processor |
| `atlas-worker.service` | Background worker |

**Scheduled Timers:**
| Timer | Schedule |
|-------|----------|
| `atlas-discovery.timer` | Periodic RSS discovery |
| `atlas-backup.timer` | Periodic backups |
| `atlas-scheduler.timer` | General scheduling |
| `atlas-watchdog.timer` | Health monitoring |

**Other Services:**
- `atlas-bot.service` - Bot interface
- `atlas-web.service` - Web dashboard
- `atlas-monitoring.service` - Monitoring
- `atlas-transcribe@.service` - Transcription (template unit)
- `oos.service` - Out-of-scope service

**Configuration Issue:** All services reference `/home/ubuntu/dev/atlas` which doesn't match current location (`/home/khamel83/github/atlas`)

---

## 7. Documentation & TODOs

### Documentation (200+ files in `docs/`)

**Key Documentation:**
| Document | Purpose |
|----------|---------|
| `README.md` | Project overview |
| `API_DOCUMENTATION.md` | REST API reference |
| `ATLAS_DATA_IMPORT_GUIDE.md` | Data migration guide |
| `GMAIL_SETUP_GUIDE.md` | Gmail integration setup |
| `GMAIL_INTEGRATION.md` | Gmail integration details |
| `EMAIL_INTEGRATION.md` | General email integration |
| `INGESTION_ARCHITECTURE.md` | Ingestion system design |
| `PODCAST_PROCESSING_MASTER_PLAN.md` | Podcast system plan |
| `OPERATIONS_GUIDE.md` | Operations runbook |
| `vos_spec.md` | VOS specification |

### TODOs in Codebase

**Key TODOs Found:**
1. `modules/transcript_discovery/podcast_transcript_scraper.py:238` - "Add more podcast-specific scrapers"
2. `processors/optimized_transcript_discovery.py:69` - "Replace with actual Google Custom Search API"
3. `processors/simple_working_processor.py:184` - "Add YouTube transcript extraction"
4. `scripts/run-bot.py:286` - "Implement daemon mode"

**TODO Management:**
- `scripts/todo_api.py` - CLI for managing TODOs
- `scripts/todo_helpers.py` - TODO helper functions
- `docs/TODO_MANAGEMENT.md` - TODO system documentation

---

## 8. Gaps & Extension Points

### What EXISTS Today

| Capability | Status | Files |
|------------|--------|-------|
| Podcast transcripts | ✅ Implemented | `processors/atlas_manager.py`, `config/podcast_sources.json` |
| URL/content submit API | ✅ Implemented | `web/api/routers/content.py` (POST `/api/v1/content/submit-url`) |
| TrojanHorse ingest | ✅ Implemented | `web/api/routers/trojanhorse.py` |
| Email ingestion (SMTP) | ⚠️ Exists, needs wiring | `integrations/email/email_bridge.py` |
| YouTube API client | ⚠️ Exists, needs wiring | `integrations/youtube_api_client.py` |
| YouTube history import | ⚠️ Exists, needs wiring | `integrations/youtube_history_importer.py` |
| OPML/Overcast parser | ✅ Implemented | `scripts/podemos_opml_parser.py` |
| Whisper transcription | ⚠️ Exists, needs integration | `scripts/podemos_transcription.py` |
| Google OAuth | ⚠️ Deps installed, partial impl | `google-auth-oauthlib` in requirements |

### What is MISSING or STUBBED

| Gap | Files to Extend/Create | Dependencies |
|-----|------------------------|--------------|
| Gmail API integration (label-based) | `integrations/email/gmail_api_client.py` | google-api-python-client (installed) |
| Email→Pipeline wiring | Wire `email_bridge.py` to content ingest | None |
| YouTube→Pipeline wiring | Wire YouTube modules to content ingest | None |
| Show-notes link expansion | `modules/ingestion/link_expander.py` | crawl4ai, playwright |
| MacWhisper watch folder | `integrations/macwhisper_watcher.py` | watchdog (to add) |
| OPML→Podcast pipeline | Wire `podemos_opml_parser.py` to podcast config | None |
| Transcription fallback | Connect `podemos_transcription.py` to episode processor | whisper-cli (to install) |
| External docs snapshots | `tools/snapshot_docs.py` | crawl4ai, playwright |
| Crawl4AI integration | `modules/content_extraction/crawl4ai_extractor.py` | crawl4ai (to add) |
| Playwright scraping | `modules/content_extraction/playwright_scraper.py` | playwright (to add) |
| Test suite fixes | Fix PYTHONPATH, conftest.py | None |
| Systemd path updates | Update all service files | None |

### Extension Points by Workstream

**1. Email Ingest:**
- Extend: `integrations/email/email_bridge.py` (currently SMTP-only)
- Create: `integrations/email/gmail_api_client.py` for Gmail API access
- Wire to: `modules/ingestion/url_ingestion_service.py`

**2. URL/File Ingest Hardening:**
- Extend: `web/api/routers/content.py` for file upload support
- Create: `modules/content_extraction/crawl4ai_extractor.py`
- Add: PDF/DOCX parsing (using `readability-lxml` or similar)

**3. Podcast Pipeline + OPML:**
- Wire: `scripts/podemos_opml_parser.py` → podcast configuration
- Extend: Episode discovery to use imported OPML feeds
- Fallback: Connect `scripts/podemos_transcription.py` to episode processor

**4. YouTube Ingest:**
- Wire: `integrations/youtube_history_importer.py` to content pipeline
- Extend: Show-notes link extraction in `integrations/youtube_content_processor.py`
- Add: Link expansion for embedded URLs

**5. Scheduling:**
- Update: All systemd files in `systemd/` with correct paths
- Add: Timer for email polling if using Gmail API

**6. External Docs Snapshots:**
- Create: `tools/snapshot_docs.py`
- Target docs: Crawl4AI, Playwright, Google OAuth, MacWhisper

---

## 9. Summary for Next Phase

Based on this diagnostic, the following major workstreams should be implemented in Phase 2:

1. **Fix Test Infrastructure** - Update PYTHONPATH configuration, fix imports in conftest.py, get core tests passing. This is a prerequisite for safe development.

2. **Wire Email Ingest to Pipeline** - The SMTP email bridge exists but needs to be connected to the content ingestion pipeline. Optionally add Gmail API support for label-based monitoring.

3. **Wire YouTube to Pipeline** - The YouTube API client and history importer exist but are not connected to content processing. Add show-notes link expansion.

4. **Connect OPML to Podcast Config** - The Overcast OPML parser exists. Wire it to dynamically configure podcasts from OPML exports.

5. **Implement Transcription Fallback** - Connect the existing Whisper transcription system to the episode processor as a fallback when transcripts aren't found. Add optional MacWhisper watch folder integration.

6. **Update Systemd Paths** - All systemd service files reference `/home/ubuntu/dev/atlas`. Update to current location for deployment.

7. **Add External Docs Snapshots** - Create a tool to fetch and cache documentation for Crawl4AI, Playwright, Google OAuth, and MacWhisper for offline reference and LLM context.

---

**Report Generated Successfully**

File: `docs/ATLAS_DIAGNOSTIC_REPORT.md`
