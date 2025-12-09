# Atlas TODO List

**Last Updated**: 2025-12-09
**Status**: Podcast transcript system operational - limits enforced

---

## Current Focus: Robust Content Fetcher

### Goal: "Never Fail" URL → Content System

Build a content fetcher that guarantees one of:
1. ✅ Full content saved (HTML + images + markdown)
2. ⚠️ Archived version found (with note about source)
3. ❌ Truly unavailable (with explanation of what was tried)

### Fetching Strategy (Cascading Fallbacks)

```
1. Direct fetch (Trafilatura)
   ↓ if 403/paywall
2. Fetch with browser cookies
   ↓ if still blocked
3. Headless browser (Playwright)
   ↓ if still blocked
4. Archive.is lookup
   ↓ if not archived
5. Wayback Machine lookup
   ↓ if not there
6. URL Resurrection: Parse slug → Google search → find alternative
```

### Storage Format

```
data/content/article/2025/12/09/{content_id}/
├── metadata.json     # Title, URL, dates, status
├── content.md        # Clean markdown (searchable)
├── article.html      # Readability-cleaned HTML
├── raw.html          # Original HTML (backup)
└── images/           # Downloaded images
    ├── img_001.jpg
    └── img_002.png
```

### Tasks

| Task | Status |
|------|--------|
| Create `modules/ingest/robust_fetcher.py` | ✅ Done |
| Add Wayback/archive.is integration | ✅ Done |
| Add Playwright for JS/paywall | ✅ Done |
| Add image downloading | ✅ Done |
| Add cookie support | ✅ Done |
| Create URL resurrector | ✅ Done |
| Update storage format | ✅ Done |
| Process 850 failed URLs | ✅ Running (via `scripts/retry_failed_urls.py`) |
| Soft 404 detection | ✅ Done |
| Integrate into content pipeline | ✅ Done |

### Usage

```bash
# Fetch a single URL
python -m modules.ingest.robust_fetcher "https://example.com/article"

# From Python
from modules.ingest.robust_fetcher import RobustFetcher
fetcher = RobustFetcher()
result = fetcher.fetch("https://example.com/article")
```

---

## Podcast Transcripts (Automated) ✅

**Status**: Running via systemd timers. Backlog processing.

### Current Stats

| Metric | Count | Notes |
|--------|-------|-------|
| Total (in scope) | 6,716 | Per-podcast limits applied |
| Fetched | ~4,350 | 64.7% coverage |
| Pending | ~2,360 | Being processed |
| Failed | ~9 | YouTube-only, retry weekly |

### Systemd Timers (Installed)

| Timer | Schedule | Purpose |
|-------|----------|---------|
| `atlas-podcast-discovery` | 6am & 6pm | Find new episodes |
| `atlas-transcripts` | Every 4 hours | Fetch transcripts |
| `atlas-youtube-retry` | Weekly (Sun 3am) | Retry YouTube w/VPN |

### Episode Limits

Per-podcast limits defined in `config/podcast_limits.json`:
- High priority (1000): Acquired, Conversations with Tyler, Hard Fork, Stratechery
- Medium priority (100): Planet Money, Dwarkesh, Ezra Klein, This American Life
- Regular (10-20): ATP, 99% Invisible, Lex Fridman, EconTalk
- Low priority (1-5): Political Gabfest, NPR Politics, Vergecast

### Working Resolvers

| Resolver | Coverage | Status |
|----------|----------|--------|
| Podscripts | 47 popular shows | ✅ Working |
| NPR Crawler | NPR shows | ✅ Working |
| Network Transcripts | NPR, Slate, WNYC | ✅ Working |
| Generic HTML | Sites with transcripts | ✅ Working |
| YouTube | Any with YouTube | ⚠️ IP blocked from cloud |

### CLI Commands

```bash
# Discover episodes (respects limits from config)
python -m modules.podcasts.cli discover --all

# Fetch transcripts (auto-respects limits per podcast)
python -m modules.podcasts.cli fetch-transcripts --all

# Prune excess episodes beyond limits
python -m modules.podcasts.cli prune --apply

# Status
python -m modules.podcasts.cli status
```

---

## Remaining Work

### P1 - Should Fix

| Task | Status |
|------|--------|
| YouTube proxy setup for cloud IP | ✅ Done (NordVPN @ 100.112.130.100:8118) |
| Site-specific scrapers for non-Podscripts shows | ✅ Done (network_transcripts, generic_html) |
| Stratechery full archive | 🔄 Running |

### P2 - Nice to Have

| Task | Status |
|------|--------|
| Systemd timers for automated runs | ✅ Done (7 timers installed) |
| Progress dashboard | ✅ Done (API + web endpoints) |
| Parallel YouTube workers | ✅ Done (3 workers) |
| Cookie expiration alerts | ✅ Done (daily check + ntfy) |

---

## Stratechery Full Archive

**Status**: 🔄 Running (started 2025-12-09)

### What's Being Crawled

| Content Type | Source | Status |
|--------------|--------|--------|
| Podcasts (Sharp Tech, Interviews) | `modules.podcasts.cli` | 🔄 290 episodes |
| Daily Updates | `stratechery_crawler.py` | 🔄 Crawling |
| Weekly Articles | `stratechery_crawler.py` | 🔄 Crawling |
| All subscriber content | Authenticated via cookies | 🔄 Active |

### Authentication

- **Cookies**: `~/.config/atlas/stratechery_cookies.json`
- **Email**: stratecheryusc@khamel.com
- **Expires**: ~6 months (refresh via magic link when needed)

### Rate Limiting

- 5 second delay between requests (very conservative)
- Exponential backoff on errors
- Progress saved to `data/stratechery/crawl_progress.json`

### Output

```
data/stratechery/
├── podcasts/          # Podcast episodes with transcripts
├── articles/          # Daily Updates and Weekly Articles
└── crawl_progress.json  # Resume state
```

### Commands

```bash
# Check progress
tail -f /tmp/stratechery-archive.log
tail -f /tmp/stratechery-fetch.log

# Resume if interrupted
python scripts/stratechery_crawler.py --type all --delay 5 --resume

# Crawl specific type
python scripts/stratechery_crawler.py --type articles --since 2024-01-01
```

---

## Architecture Status: HEALTHY

| Component | Status | Tests |
|-----------|--------|-------|
| `modules/` | Working | 34 passing |
| `api/` | Working | 11 passing |
| `tests/` | Clean | 34 total |

### Core Modules (`modules/`)
- **podcasts/** - Podcast management with 7 transcript resolvers
- **storage/** - File-based content storage with SQLite index
- **pipeline/** - Content processing pipeline
- **ingest/** - Gmail, YouTube, newsletter ingestion
- **notifications/** - Telegram/ntfy alerts

### API (`api/`)
Clean FastAPI application:
- `GET /health` - Health check
- `GET /metrics` - System metrics
- `GET /api/podcasts/` - List podcasts
- `GET /api/podcasts/stats` - Podcast statistics
- `GET /api/content/` - List content
- `GET /api/search/?q=` - Search content

---

## Quick Reference

```bash
# Run tests
./venv/bin/pytest tests/ -v

# Start API
./venv/bin/uvicorn api.main:app --port 7444

# Process podcasts
./venv/bin/python -m modules.podcasts.cli --help
```

---

## Completed (2025-12-09 Session - Part 3)

1. **Parallel YouTube Workers**
   - [x] Created `scripts/parallel_youtube_worker.py`
   - [x] 3 workers: direct, proxy-1, proxy-2
   - [x] Automatic podcast assignment by worker
   - [x] Run with `--parallel` or `--sequential`

2. **Progress Dashboard**
   - [x] Added `/api/dashboard/status` endpoint
   - [x] Real-time podcast stats, process status, timer status
   - [x] Stratechery archive progress tracking
   - [x] Log viewing endpoint `/api/dashboard/logs/{name}`

3. **Cookie Expiration Alerts**
   - [x] Created `scripts/check_cookies.py`
   - [x] Monitors Stratechery + YouTube cookies
   - [x] Alerts via ntfy.sh (and Telegram optional)
   - [x] Daily check via systemd timer (9am)
   - [x] Warning at 7 days, Critical at 2 days

4. **Episode URL Fixer**
   - [x] Created `scripts/fix_episode_urls.py`
   - [x] Fixed 848 episode URLs for Acquired, CWT, EconTalk, etc.
   - [x] Enables generic_html resolver to find transcripts

## Completed (2025-12-09 Session - Part 2)

1. **YouTube Rate Limiting**
   - [x] Researched safe rate limits (1-2s often safe, we use 15s)
   - [x] Lowered from 30s to 15s in `systemd/atlas-podcasts.env`
   - [x] Added early-stop logic when >5000 chars content found

2. **Stratechery Full Archive**
   - [x] Set up cookie-based authentication
   - [x] Created `scripts/stratechery_crawler.py` for full site archive
   - [x] Updated generic_html resolver with cookie support
   - [x] Prioritized generic_html before YouTube for sites with transcripts
   - [x] Started full archive crawl (podcasts + articles)

3. **URL Retry Batch**
   - [x] Completed processing 767 failed URLs
   - [x] 524 success (68%), 243 still failed
   - [x] Added soft 404 detection
   - [x] Added URL skip patterns for marketing/tracking URLs

4. **Resolver Priority Improvements**
   - [x] generic_html now runs before youtube_transcript for configured podcasts
   - [x] Early-stop when substantial content found (avoids wasted YouTube calls)

## Completed (2025-12-09 Session - Part 1)

1. **Podcast Limits System**
   - [x] Created `config/podcast_limits.json` from user spreadsheet
   - [x] Modified `cmd_discover()` to respect limits
   - [x] Added `cmd_prune()` to exclude excess episodes
   - [x] Modified `cmd_fetch_transcripts()` for smart limit-aware fetching
   - [x] Enabled WAL mode on SQLite for better concurrency

2. **Data Cleanup**
   - [x] Pruned 85k episodes down to ~6.7k active
   - [x] Preserved all 4,341 already-fetched transcripts

## Completed (2025-12-06 Session)

1. **Architecture Cleanup**
   - [x] Archived broken `web/api/` routers (12 files)
   - [x] Archived broken tests (79 files)
   - [x] Created clean `api/` module with working routers
   - [x] Created clean `tests/` with 34 passing tests

---

*Clean architecture. Working podcast system. Limits enforced.*
