# Atlas Project Instructions

## Quick Reference

```bash
# Check podcast transcript coverage
./venv/bin/python -m modules.podcasts.cli status

# Check with per-podcast breakdown
./venv/bin/python -m modules.podcasts.cli status -v

# Run transcript fetch manually
./venv/bin/python -m modules.podcasts.cli fetch-transcripts --all

# Run tests
./venv/bin/pytest tests/ -v
```

## Architecture

```
atlas/
├── modules/
│   ├── podcasts/         # Podcast transcript system
│   │   ├── cli.py        # Main CLI interface
│   │   ├── store.py      # SQLite database
│   │   ├── rss.py        # RSS feed parsing
│   │   └── resolvers/    # Transcript sources (7 resolvers)
│   ├── storage/          # Content storage with SQLite index
│   ├── ingest/           # Gmail, YouTube, robust URL fetcher
│   │   └── robust_fetcher.py  # Cascading fallback fetcher
│   └── pipeline/         # Content processing pipeline
├── api/                  # FastAPI REST API
│   └── routers/
│       └── dashboard.py  # Progress monitoring endpoints
├── scripts/              # Utility scripts
│   ├── stratechery_crawler.py    # Full Stratechery archive
│   ├── parallel_youtube_worker.py # Multi-worker YouTube fetch
│   ├── check_cookies.py          # Cookie expiration alerts
│   ├── fix_episode_urls.py       # Fix bad episode URLs
│   └── retry_failed_urls.py      # Batch URL retry
├── config/
│   ├── mapping.yml           # Podcast resolver config
│   └── podcast_limits.json   # Per-podcast episode limits
├── systemd/              # 7 systemd timer services
│   └── atlas-podcasts.env    # Environment for services
└── data/
    ├── podcasts/         # Transcript storage
    │   └── {slug}/transcripts/*.md
    ├── content/          # URL content storage
    └── stratechery/      # Stratechery archive
```

---

## Systemd Services (7 Timers)

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

## YouTube Proxy Setup

YouTube blocks cloud IPs. We use NordVPN proxy via Tailscale.

**Proxy:** `http://100.112.130.100:8118`

**Config:** `systemd/atlas-podcasts.env`
```bash
YOUTUBE_PROXY_URL=http://100.112.130.100:8118
YOUTUBE_RATE_LIMIT_SECONDS=15  # Safe with proxy
```

**If blocked:** Reconnect NordVPN to get new IP

**Parallel workers:** Run multiple fetchers with staggered timing:
```bash
python scripts/parallel_youtube_worker.py --parallel
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

**Output:** `data/stratechery/{articles,podcasts}/*.md`

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

# From Python
from modules.ingest.robust_fetcher import RobustFetcher
fetcher = RobustFetcher()
result = fetcher.fetch("https://example.com/article")
```

**Output:** `data/content/article/{date}/{content_id}/`
- `content.md` - Clean markdown
- `article.html` - Readability-cleaned HTML
- `raw.html` - Original HTML
- `images/` - Downloaded images

---

## Dashboard API

**Endpoints:**

```
GET /api/dashboard/status    # Full system status (coverage, processes, timers)
GET /api/dashboard/podcasts  # All podcast stats
GET /api/dashboard/logs/{name}  # View logs (transcripts, stratechery, retry)
```

**Start API:**
```bash
./venv/bin/uvicorn api.main:app --port 7444
```

---

## Cookie Expiration Alerts

Daily check (9am) for expiring authentication cookies.

**Check manually:**
```bash
python scripts/check_cookies.py
```

**With alerts:**
```bash
python scripts/check_cookies.py --alert --ntfy
```

**Alerts sent to:** `ntfy.sh/atlas-khamel-alerts`

**Subscribe on phone:** Install ntfy app, subscribe to `atlas-khamel-alerts`

---

## Configuration Files

| File | Purpose |
|------|---------|
| `config/podcast_limits.json` | Per-podcast episode limits (source of truth) |
| `config/mapping.yml` | Resolver configuration per podcast |
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

Some RSS feeds have bad URLs. Fix with:
```bash
python scripts/fix_episode_urls.py --all --apply
```

### Debug Transcript Issues

```bash
# Check status
python -m modules.podcasts.cli status -v

# Check logs
tail -f /tmp/atlas-batch.log
journalctl -u atlas-transcripts -f

# Test specific resolver
python -c "
from modules.podcasts.resolvers.generic_html import GenericHTMLResolver
resolver = GenericHTMLResolver()
# ... test specific episode
"
```

---

## Database

SQLite at `data/podcasts/atlas_podcasts.db` (WAL mode enabled).

**Tables:**
- `podcasts` - Podcast metadata
- `episodes` - Episode records with transcript status
- `transcript_sources` - Discovered transcript URLs
- `discovery_runs` - Run history

**Quick queries:**
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
python -m modules.podcasts.cli status
systemctl list-timers | grep atlas
ps aux | grep python.*atlas
```
