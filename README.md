# Atlas - Personal Knowledge Ingestion System

**Status**: Production
**Current Tier**: SQLite + systemd timers on homelab
**Upgrade Trigger**: Multi-user access or heavy concurrent writes

## What This Does

Content is scattered across the internet - podcast transcripts on various sites, articles saved in Instapaper, newsletters in Gmail. Atlas automatically ingests everything into a searchable archive with semantic search.

## Quick Start

```bash
# Setup
./scripts/setup.sh

# Check status (shows everything)
./venv/bin/python scripts/atlas_status.py

# Run tests
./venv/bin/pytest tests/ -v

# Start API
./venv/bin/uvicorn api.main:app --port 7444
```

---

## Architecture

```
atlas/
├── modules/              # 11 active modules
│   ├── podcasts/         # Podcast transcript system
│   │   ├── cli.py        # Main CLI interface
│   │   ├── store.py      # SQLite database
│   │   ├── rss.py        # RSS feed parsing
│   │   ├── speaker_mapper.py  # Map speaker labels to names
│   │   └── resolvers/    # 16 transcript resolvers
│   ├── quality/          # Content verification system
│   │   ├── verifier.py   # Core verification logic + is_garbage_content()
│   │   └── __init__.py   # verify_file(), verify_content()
│   ├── storage/          # Content storage with SQLite index
│   ├── ingest/           # Gmail, YouTube, robust URL fetcher
│   │   └── robust_fetcher.py  # Cascading fallback fetcher
│   ├── pipeline/         # Content processing pipeline
│   ├── enrich/           # Ad removal, URL sanitization, link extraction
│   ├── links/            # Link discovery and approval pipeline
│   ├── ask/              # Semantic search & Q&A
│   ├── status/           # Unified status reporting
│   ├── browser/          # Playwright headless browser wrapper
│   └── notifications/    # Alert system (Telegram, ntfy)
├── api/                  # FastAPI REST API
│   └── routers/
│       ├── dashboard.py  # Progress monitoring endpoints
│       └── notes.py      # Notes API endpoints
├── scripts/              # Utility scripts
├── config/
│   ├── mapping.yml           # Podcast resolver config
│   ├── podcast_limits.json   # Per-podcast episode limits
│   └── podcast_hosts.json    # Known hosts per podcast
├── systemd/              # 13 systemd timer services
└── data/
    ├── podcasts/         # Transcript storage
    │   └── {slug}/transcripts/*.md
    ├── content/          # URL content storage
    │   ├── article/      # Articles from URLs
    │   ├── newsletter/   # Newsletters from Gmail
    │   └── note/         # User notes
    ├── clean/            # Ad-stripped versions (for indexing)
    ├── indexes/          # Vector embeddings database
    └── stratechery/      # Stratechery archive
```

---

## Systemd Services (13 Timers)

All timers are installed and running. Check with: `systemctl list-timers | grep atlas`

| Timer | Schedule | Purpose |
|-------|----------|---------|
| `atlas-podcast-discovery` | 6am & 6pm | Find new episodes from RSS |
| `atlas-transcripts` | Every 4 hours | Fetch pending transcripts |
| `atlas-youtube-retry` | Sunday 3am | Retry YouTube with VPN proxy |
| `atlas-gmail` | Every 5 min | Check Gmail for newsletters |
| `atlas-inbox` | Every 5 min | Process inbox queue |
| `atlas-content-retry` | Weekly | Retry failed URL fetches |
| `atlas-cookie-check` | Daily 9am | Check cookie expiration → ntfy alert |
| `atlas-backlog-fetcher` | Every 30min | Fetch 50 transcripts with proxy health check |
| `atlas-enrich` | Sunday 4am | Clean ads from content, generate reports |
| `atlas-link-pipeline` | Every 2 hours | Approve and ingest extracted links |
| `atlas-verify` | Daily 5am | Content quality verification report |
| `atlas-whisper-download` | Every 2 hours | Download audio for local transcription |
| `atlas-whisper-import` | Hourly | Import completed Whisper transcripts |

**Install all:**
```bash
sudo ./systemd/install.sh --all
```

**Check logs:**
```bash
journalctl -u atlas-transcripts -f
journalctl -u atlas-cookie-check --since today
```

---

## MVP: Simple Always-Running Fetchers

Two dead-simple scripts that run forever. No complexity, just reliable slow fetching.

### URL Fetcher (`scripts/simple_url_fetcher.py`)

Always-running service that watches a queue file for URLs.

**How it works:**
1. Watches `data/url_queue.txt` for new URLs
2. Fetches content using trafilatura (with BeautifulSoup fallback)
3. Saves markdown to `data/articles/{domain}/{date}_{title}.md`
4. Tracks state in `data/url_fetcher_state.json`

**Usage:**
```bash
# Add URLs to queue
echo "https://example.com/article" >> data/url_queue.txt

# Service handles the rest - checks every 60 seconds
# 10 second delay between fetches (polite)

# Check what's been fetched
cat data/url_fetcher_state.json | jq '.fetched | keys | length'

# Check failures
cat data/url_fetcher_state.json | jq '.failed'

# View logs
journalctl -u atlas-url-fetcher -f
```

### Transcript Fetcher (`scripts/simple_transcript_fetcher.py`)

Always-running service that fetches podcast transcripts.

**How it works:**
1. Checks RSS feeds for new episodes
2. Fetches transcripts from Podscripts.co or direct sources
3. Saves markdown to `data/podcasts/{slug}/transcripts/`
4. Tracks state in `data/fetcher_state.json`

### Key Design Principles

1. **Simple queue files** - Just append URLs to a text file
2. **State tracking** - JSON files track what's been fetched/failed
3. **Slow and polite** - 10+ second delays, no rushing
4. **Always running** - systemd restarts on failure
5. **No dependencies** - Works standalone, no complex orchestration

---

## VPN Proxy (Gluetun)

All YouTube and some web requests use the Gluetun VPN proxy for IP rotation.

**Configuration:**
- Container: `gluetun` with NordVPN WireGuard
- HTTP Proxy: `localhost:8118`
- Config: `/home/khamel83/github/homelab/services/gluetun/docker-compose.yml`

**Health Check:**
```bash
# Check proxy health
./venv/bin/python scripts/check_proxy_health.py

# Force VPN rotation
./venv/bin/python scripts/check_proxy_health.py --rotate

# Check and auto-fix if needed
./venv/bin/python scripts/check_proxy_health.py --fix
```

**Manual VPN rotation:**
```bash
docker restart gluetun
# Wait 30 seconds for reconnect
docker logs gluetun --tail 5  # Check new IP
```

---

## Podcast Transcript System

### How It Works

1. **Discovery** (6am & 6pm): RSS feeds → new episodes marked `unknown`
2. **Fetch** (every 4 hours): Process `unknown` episodes → `fetched`
3. **Retry** (weekly): Re-attempt `failed` episodes with YouTube proxy

### Resolvers (Priority Order)

| Resolver | Source | Notes |
|----------|--------|-------|
| `rss_link` | Direct link in RSS | Best quality |
| `generic_html` | Scrape episode pages | Uses cookies for Stratechery |
| `network_transcripts` | NPR, Slate, WNYC | Official transcripts |
| `podscripts` | AI transcripts (47 shows) | Good coverage |
| `youtube_transcript` | Auto-captions | Needs proxy from cloud |
| `pattern` | URL pattern matching | Last resort |

### Episode Statuses

- `unknown` - New, needs fetching
- `found` - URL found, needs content
- `fetched` - Complete, transcript on disk
- `failed` - All resolvers failed (retry weekly)
- `excluded` - Beyond per-podcast limit
- `local` - Needs local Whisper transcription

### CLI Commands

```bash
# Status
python -m modules.podcasts.cli status
python -m modules.podcasts.cli status -v  # per-podcast breakdown

# Discovery
python -m modules.podcasts.cli discover --all
python -m modules.podcasts.cli discover --slug acquired

# Fetch transcripts
python -m modules.podcasts.cli fetch-transcripts --all
python -m modules.podcasts.cli fetch-transcripts --slug stratechery
python -m modules.podcasts.cli fetch-transcripts --slug acquired --limit 10

# Maintenance
python -m modules.podcasts.cli prune --apply  # Mark excess as excluded
python -m modules.podcasts.cli doctor         # Check health
```

---

## Stratechery Full Archive

Stratechery requires authentication (magic link). Cookies stored at `~/.config/atlas/stratechery_cookies.json`.

### Refresh Cookies

1. Log into Stratechery in browser (email: stratecheryusc@khamel.com)
2. Export cookies using browser extension
3. Save to `~/.config/atlas/stratechery_cookies.json`

### Run Archive Crawler

```bash
# Full archive (articles + podcasts)
python scripts/stratechery_crawler.py --type all --delay 5

# Just articles since 2024
python scripts/stratechery_crawler.py --type articles --since 2024-01-01

# Resume interrupted crawl
python scripts/stratechery_crawler.py --type all --resume

# Monitor progress
tail -f /tmp/stratechery-archive.log
cat data/stratechery/crawl_progress.json
```

---

## Bulk Import (Messy Folder Processing)

Drop any folder of mixed files and it auto-detects and processes everything:

```bash
# Dry run - see what would be imported
python -m modules.ingest.bulk_import /path/to/messy/folder --dry-run

# Actually import
python -m modules.ingest.bulk_import /path/to/messy/folder
```

**Supported file types (auto-detected):**
- Instapaper HTML exports
- Pocket JSON exports
- URL lists (`.txt`, one per line)
- CSV files with URL columns
- Markdown files (extracts `[text](url)` links)
- HTML articles (extracts canonical URL)

---

## URL Content Fetcher (Robust)

The robust fetcher uses cascading fallbacks:

```
1. Direct HTTP (Trafilatura)
   ↓ if blocked
2. Playwright headless browser
   ↓ if blocked
3. Archive.is lookup
   ↓ if not archived
4. Wayback Machine lookup
   ↓ if not there
5. URL Resurrection (search for alternatives)
```

### Usage

```bash
# Fetch single URL
python -m modules.ingest.robust_fetcher "https://example.com/article"

# Retry all failed URLs
python scripts/retry_failed_urls.py
```

---

## Dashboard API

**Endpoints:**

```
GET /api/dashboard/status    # Full system status
GET /api/dashboard/podcasts  # All podcast stats
GET /api/dashboard/logs/{name}  # View logs
```

**Start API:**
```bash
./venv/bin/uvicorn api.main:app --port 7444
```

---

## Notes System

Notes are short-form user-curated content (selections, quotes, highlights).

**Storage:** `data/content/note/{YYYY/MM/DD}/{content_id}/`

### API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/notes/` | Create note from text |
| POST | `/api/notes/url` | Create note from URL + selection |
| GET | `/api/notes/` | List notes |
| GET | `/api/notes/{id}` | Get specific note |
| DELETE | `/api/notes/{id}` | Delete note |

---

## Mac Mini Local Whisper Transcription

For podcasts that can't be fetched online (paywalled, no transcript source), we download audio and transcribe locally on Mac Mini M4.

### Episode Status: `local`

Episodes marked with `transcript_status = 'local'` need local transcription:
- Dithering - paywalled
- Asianometry - paywalled
- Against the Rules - no online source

### Fully Automated Pipeline

The Whisper pipeline is **fully automated** via systemd timers:

1. **Download** (`atlas-whisper-download.timer` - every 2 hours): Downloads audio for `local` episodes
2. **WhisperX** (Mac Mini): Watches folder, transcribes with speaker diarization → JSON output
3. **Import** (`atlas-whisper-import.timer` - hourly): Imports transcripts, maps speakers to names
4. **Enrich** (`atlas-enrich.timer` - Sunday 4am): Removes ads using standard patterns

### Speaker Mapping

Speakers are automatically mapped from labels (SPEAKER_00) to names:

1. **Known hosts** from `config/podcast_hosts.json` (60+ podcasts configured)
2. **Guests** extracted from episode title ("with Guest Name") or description
3. **Fallback** to "Speaker 1", "Speaker 2" if no match

### Mac Mini Setup

**SMB Mount (Automatic):**
- LaunchAgent: `~/Library/LaunchAgents/com.atlas.smb-mount.plist`
- Mount script: `scripts/mac_mini/mount_atlas_whisper.sh`
- Runs every 5 minutes to ensure mount is active

**WhisperX Watcher:**
- LaunchAgent: `~/Library/LaunchAgents/com.atlas.whisperx.plist`
- Watcher script: `scripts/mac_mini/whisperx_watcher.py`
- Watchdog features (added 2025-12-23):
  - Kills hung processes (<5% CPU for 10 minutes)
  - Hard timeout: 90 minutes per file
  - Auto-recovery on next file

**Check Status:**
```bash
# From homelab
ssh macmini "ps aux | grep whisperx | grep -v grep"
ssh macmini "ls /Volumes/atlas-whisper/transcripts/ | wc -l"
```

---

## Content Enrichment (Ad Removal, URL Cleanup, Link Queue)

Multi-stage content enrichment pipeline:
1. **Ad Removal**: Strip sponsor/ad content
2. **URL Sanitization**: Remove tracking params (utm_, fbclid, etc.)
3. **Link Extraction**: Queue high-value URLs for potential ingestion

### Architecture

```
data/
├── podcasts/             # ORIGINALS (never modified)
├── content/              # ORIGINALS (never modified)
├── clean/                # CLEANED VERSIONS (for indexing)
│   ├── podcasts/{slug}/transcripts/*.md
│   ├── article/*.md
│   ├── newsletter/*.md
│   └── stratechery/{articles,podcasts}/*.md
└── enrich/
    ├── enrich.db         # SQLite tracking database
    ├── link_queue.db     # URLs queued for potential ingestion
    ├── changes/*.json    # Detailed removal records
    └── reports/*.md      # Weekly reports
```

### Commands

```bash
# Full enrichment workflow
./venv/bin/python scripts/run_enrichment.py

# Dry run
./venv/bin/python scripts/run_enrichment.py --dry-run

# Force re-clean everything
./venv/bin/python scripts/run_enrichment.py --force

# Analyze ad detection
./venv/bin/python scripts/analyze_ads.py
```

### Current Stats

- **15,116 files** processed
- **7,063 ads** removed (~3MB of ad content)
- **0% false positive rate** (after pattern tuning)

---

## Content Quality Verification

Unified system to verify ALL content is real and valuable.

### Quality Levels

- **GOOD**: Passed all checks, verified quality content
- **MARGINAL**: Borderline, passed critical checks but missing some
- **BAD**: Failed critical checks, needs action

### Commands

```bash
# Full verification scan
./venv/bin/python scripts/verify_content.py --report

# Quick scan of specific content type
./venv/bin/python scripts/verify_content.py --type podcasts

# JSON output for scripting
./venv/bin/python scripts/verify_content.py --json
```

### Python API

```python
from modules.quality import verify_file, verify_content, is_garbage_content

# Verify a file
result = verify_file("/path/to/content.md")
if result.is_good:
    print("Content verified!")

# Quick garbage check before saving
is_bad, reason = is_garbage_content(text_content)
if is_bad:
    return  # Don't save
```

---

## Link Discovery & Ingestion Pipeline

Unified system for extracting, approving, and ingesting URLs from any content source.

### CLI Commands

```bash
# Extract from podcast show notes
./venv/bin/python -m modules.links.cli extract-shownotes --all

# Run approval workflow
./venv/bin/python -m modules.links.cli approve --apply

# Bridge approved links to URL queue
./venv/bin/python -m modules.links.cli ingest --drip

# Pipeline status
./venv/bin/python -m modules.links.cli status
```

### Approval Rules

Configuration in `config/link_approval_rules.yml`:
- **Trusted domains**: Auto-approve (stratechery, nytimes, arxiv, etc.)
- **Score threshold**: Auto-approve >= 0.85
- **Reject threshold**: Auto-reject < 0.40
- **Blocked domains**: Always reject (bit.ly, twitter, etc.)

---

## Atlas Ask (Semantic Search & Q&A)

Semantic search and LLM-powered Q&A over all indexed content.

### Architecture

```
modules/ask/
├── config.py         # Loads config/ask_config.yml
├── embeddings.py     # OpenRouter embeddings (openai/text-embedding-3-small)
├── chunker.py        # Tiktoken chunking (512 tokens, 50 overlap)
├── vector_store.py   # SQLite-vec storage
├── retriever.py      # Hybrid search (vector + FTS5 + RRF fusion)
├── synthesizer.py    # LLM answers (google/gemini-2.5-flash-lite)
├── indexer.py        # Content discovery and indexing
└── cli.py            # CLI for testing
```

### CLI Commands

```bash
# Ask a question (retrieves + synthesizes answer)
./scripts/run_with_secrets.sh python -m modules.ask.cli ask "What is AI?"

# Search without synthesis
./scripts/run_with_secrets.sh python -m modules.ask.cli search "nuclear power" --limit 10

# Index all content
./scripts/run_with_secrets.sh python -m modules.ask.indexer --all

# Index specific type
./scripts/run_with_secrets.sh python -m modules.ask.indexer --type podcasts

# Show stats
./scripts/run_with_secrets.sh python -m modules.ask.cli stats
```

### Python Usage

```python
from modules.ask import ask, retrieve, index_single

# Full Q&A
answer = ask("What are the implications of AI for jobs?")
print(answer.answer)
print(f"Confidence: {answer.confidence}")
print(f"Sources: {answer.sources}")

# Just retrieval
results = retrieve("nuclear energy", limit=10)
for r in results:
    print(f"{r.score:.3f} - {r.metadata.get('title')}")
```

### Database

Vector store at `data/indexes/atlas_vectors.db`:
- `chunks` - Text chunks with metadata
- `chunk_vectors` - SQLite-vec embeddings (1536 dimensions)
- `chunks_fts` - FTS5 table for keyword search

### Current Stats (2025-12-23)
- **440,030 chunks** indexed
- **339M tokens** embedded via Voyage AI
- **6,869 episodes** total, 4,874 fetched (71%)

### When Embeddings Are Complete

Once all transcripts are fetched and indexed, Atlas Ask enables:

1. **Query anything**: "What did Ben Thompson say about Apple's AI strategy?"
2. **Cross-reference**: Find connections across podcasts, articles, newsletters
3. **Research mode**: Deep dive on topics with full source attribution
4. **Export**: Generate reports from semantic search results

The 339M tokens represent ~5+ years of curated content, fully searchable.

---

## Database

SQLite at `data/podcasts/atlas_podcasts.db` (WAL mode enabled).

**Tables:**
- `podcasts` - Podcast metadata
- `episodes` - Episode records with transcript status
- `transcript_sources` - Discovered transcript URLs
- `discovery_runs` - Run history
- `podcast_speakers` - Known hosts/co-hosts per podcast
- `episode_speakers` - Per-episode speaker mappings

### Quick Queries

```bash
# Pending by podcast
sqlite3 data/podcasts/atlas_podcasts.db "
SELECT p.slug, COUNT(*) FROM episodes e
JOIN podcasts p ON e.podcast_id = p.id
WHERE e.transcript_status = 'unknown'
GROUP BY p.slug ORDER BY COUNT(*) DESC"

# Recent fetches
sqlite3 data/podcasts/atlas_podcasts.db "
SELECT title, transcript_status, updated_at
FROM episodes ORDER BY updated_at DESC LIMIT 10"

# Episodes with speaker mappings
sqlite3 data/podcasts/atlas_podcasts.db "
SELECT e.title, es.speaker_label, es.speaker_name, es.confidence
FROM episode_speakers es JOIN episodes e ON es.episode_id = e.id
ORDER BY es.created_at DESC LIMIT 20"
```

---

## Tests

```bash
# Run all tests
./venv/bin/pytest tests/ -v

# Run specific module
./venv/bin/pytest tests/test_podcasts.py -v
./venv/bin/pytest tests/test_storage.py -v
./venv/bin/pytest tests/test_api.py -v
```

**34 tests passing** across api, podcasts, storage modules.

---

## Logs & Monitoring

| Log | Location |
|-----|----------|
| Transcript fetch | `/tmp/atlas-batch.log` |
| Stratechery archive | `/tmp/stratechery-archive.log` |
| URL retry | `/tmp/atlas-retry.log` |
| Systemd services | `journalctl -u atlas-*` |

**Quick status:**
```bash
./venv/bin/python scripts/atlas_status.py
systemctl list-timers | grep atlas
ps aux | grep python.*atlas
```

---

## Configuration Files

| File | Purpose |
|------|---------|
| `config/podcast_limits.json` | Per-podcast episode limits (source of truth) |
| `config/mapping.yml` | Resolver configuration per podcast |
| `config/ask_config.yml` | Embeddings and LLM settings |
| `config/link_approval_rules.yml` | Link approval thresholds |
| `systemd/atlas-podcasts.env` | Environment for systemd services |
| `~/.config/atlas/stratechery_cookies.json` | Stratechery auth cookies |

---

## Common Operations

### Add New Podcast

1. Add to `config/podcast_limits.json`:
   ```json
   "new-podcast": {"limit": 100, "exclude": false}
   ```

2. Add to `config/mapping.yml` if custom resolver needed

3. Register and discover:
   ```bash
   python -m modules.podcasts.cli register --csv config/podcasts_to_register.csv
   python -m modules.podcasts.cli discover --slug new-podcast
   python -m modules.podcasts.cli fetch-transcripts --slug new-podcast
   ```

### Fix Bad Episode URLs

```bash
python scripts/fix_episode_urls.py --all --apply
```

### Validate Transcript Sources

```bash
python scripts/validate_podcast_sources.py
python scripts/validate_podcast_sources.py --slug acquired
```

---

## Known Limitations

- YouTube transcripts require VPN proxy (cloud IPs blocked)
- Stratechery requires authenticated cookies (6-month refresh)
- Some podcasts only have audio (no transcript source exists)

---

*ONE_SHOT v5.5 enabled. Skills available in `.claude/skills/`*
