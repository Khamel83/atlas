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
│   ├── stratechery_crawler.py       # Full Stratechery archive
│   ├── parallel_youtube_worker.py   # Multi-worker YouTube fetch
│   ├── check_cookies.py             # Cookie expiration alerts
│   ├── fix_episode_urls.py          # Fix bad episode URLs
│   ├── retry_failed_urls.py         # Batch URL retry
│   └── validate_podcast_sources.py  # Verify transcript availability
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
| `atlas-backlog-fetcher` | Every 30min | Fetch 50 transcripts with proxy health check |

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

**Service:** `systemd/atlas-url-fetcher.service`
```bash
sudo systemctl status atlas-url-fetcher
sudo systemctl restart atlas-url-fetcher
```

### Transcript Fetcher (`scripts/simple_transcript_fetcher.py`)

Always-running service that fetches podcast transcripts.

**How it works:**
1. Checks RSS feeds for new episodes
2. Fetches transcripts from Podscripts.co or direct sources
3. Saves markdown to `data/podcasts/{slug}/transcripts/`
4. Tracks state in `data/fetcher_state.json`

**Configuration:**
Edit the `PODCASTS` dict in the script to add/remove podcasts:
```python
PODCASTS = {
    'acquired': {
        'rss': 'https://feeds.acquired.fm/acquired',
        'source': 'podscripts',
        'podscripts_slug': 'acquired'
    },
    # ... more podcasts
}
```

**Service:** `systemd/atlas-simple-fetcher.service`
```bash
sudo systemctl status atlas-simple-fetcher
sudo systemctl restart atlas-simple-fetcher
journalctl -u atlas-simple-fetcher -f
```

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

**Auto-rotation:**
The `atlas-backlog-fetcher` timer runs every 30 minutes and:
1. Checks proxy health first
2. Rotates VPN if YouTube is blocked
3. Fetches 50 transcripts per run

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

### Transcript Source Coverage (Validated)

**All 46 podcasts have confirmed transcript sources.** Run `scripts/validate_podcast_sources.py` to verify.

| Source Type | Podcasts | How It Works |
|-------------|----------|--------------|
| Website (direct HTML) | 6 | Scrape transcript from episode page using CSS selectors |
| Podscripts.co | 40 | AI-generated transcripts, good quality, covers most shows |

**Podcasts with direct website transcripts (highest quality):**
- `stratechery` → `.entry-content` (requires auth cookies)
- `acquired` → `.transcript-container`
- `planet-money` → `.storytext` (NPR)
- `the-npr-politics-podcast` → `.storytext` (NPR)
- `lex-fridman-podcast` → `.entry-content`
- `conversations-with-tyler` → `.generic__content`

**Why this works:**
1. Major podcasts publish transcripts on their websites (accessibility, SEO)
2. Podscripts.co uses AI transcription and covers 40+ shows we follow
3. YouTube auto-captions serve as fallback for shows with video versions
4. The resolver chain tries sources in priority order until one succeeds

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

**Deduplication:**
- URLs are hashed for dedup (normalized, tracking params stripped)
- Safe to re-run on same folder - duplicates are skipped
- Checks both in-memory (this batch) and database (previously processed)

**Example:**
```
$ python -m modules.ingest.bulk_import ~/Downloads/instapaper-exports --dry-run

BULK IMPORT RESULTS
============================================================
Files scanned:    47
URLs found:       1,234
  New:            892
  Duplicate:      342

By file type:
  instapaper_html: 12
  url_list: 8
  markdown: 27
```

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

### Validate Transcript Sources

Before bulk fetching, verify all podcasts have working transcript sources:

```bash
# Check all pending podcasts
python scripts/validate_podcast_sources.py

# Check specific podcast
python scripts/validate_podcast_sources.py --slug acquired

# Output as JSON for scripting
python scripts/validate_podcast_sources.py --json
```

The script checks each podcast for:
- **Website transcripts** - Tests configured CSS selectors against sample episode
- **Podscripts.co** - Checks if podcast is available on podscripts.co
- **YouTube** - Checks if podcast is known to have YouTube versions

Output shows ✅ (can fetch) or ❌ (no known source) for each podcast.

---

## Mac Mini Local Whisper Transcription

For podcasts that can't be fetched online (paywalled, no transcript source), we download audio and transcribe locally using MacWhisper Pro.

### Episode Status: `local`

Episodes marked with `transcript_status = 'local'` need local transcription:
- Dithering (101) - paywalled
- Asianometry (100) - paywalled
- Against the Rules (94) - no online source
- CWT old episodes (187) - no transcripts on website

### Server Side (Homelab)

```bash
# Download audio for local transcription (runs every 2 hours via timer)
python scripts/download_for_whisper.py --limit 10

# Download all at once
python scripts/download_for_whisper.py --all

# Check what's queued
ls -la data/whisper_queue/audio/

# Import completed transcripts back (runs hourly via timer)
python scripts/import_whisper_transcripts.py
```

**Timers:**
```bash
sudo cp systemd/atlas-whisper-*.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now atlas-whisper-download.timer
sudo systemctl enable --now atlas-whisper-import.timer
```

### Mac Mini Setup

1. **Mount SMB share:**
   ```bash
   # One-time mount
   mount_smbfs //khamel83@homelab/atlas /Volumes/atlas

   # Or add to Finder: Cmd+K -> smb://homelab/atlas
   ```

2. **Configure MacWhisper Pro:**
   - Open MacWhisper Pro preferences
   - Set Watch Folder: `/Volumes/atlas/data/whisper_queue/audio`
   - Set Output Folder: `/Volumes/atlas/data/whisper_queue/transcripts`
   - Output Format: TXT (plain text)
   - Model: Large v3 (or whatever fits your RAM)
   - Enable "Auto-transcribe files in watch folder"

3. **That's it!** MacWhisper watches the folder and transcribes automatically.

### Workflow

```
Server downloads audio -> SMB share -> Mac Mini MacWhisper watches
                                              |
                                              v
                                       Transcribes to TXT
                                              |
                                              v
Server imports transcripts <- SMB share <- Output folder
```

### File Naming

- Audio: `{podcast_slug}_{episode_id}_{date}_{title}.mp3`
- Transcript: MacWhisper outputs same name with `.txt`
- Import script matches by episode ID in filename

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

---

## Atlas Ask (Semantic Search & Q&A)

**Status**: Built, NOT ENABLED. Ready to activate after ingestion is finalized.

Atlas Ask provides semantic search and LLM-powered Q&A over all your indexed content.

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

### Configuration

All settings in `config/ask_config.yml`:
- **Embeddings**: `openai/text-embedding-3-small` via OpenRouter
- **LLM**: `google/gemini-2.5-flash-lite` via OpenRouter
- **Chunking**: 512 tokens max, 50 token overlap
- **Retrieval**: 70% vector weight, 30% keyword weight

### Content Sources (Auto-discovered)

| Source | Path |
|--------|------|
| Podcasts | `data/podcasts/{slug}/transcripts/*.md` |
| Articles | `data/content/article/{date}/{id}/content.md` |
| Newsletters | `data/content/newsletter/{date}/{id}/content.md` |
| Stratechery | `data/stratechery/{articles,podcasts}/*.md` |

### CLI Commands

```bash
# Ask a question (retrieves + synthesizes answer)
./scripts/run_with_secrets.sh python -m modules.ask.cli ask "What is AI?"

# Search without synthesis
./scripts/run_with_secrets.sh python -m modules.ask.cli search "nuclear power" --limit 10

# Index all content (one-time bulk)
./scripts/run_with_secrets.sh python -m modules.ask.indexer --all

# Index specific type
./scripts/run_with_secrets.sh python -m modules.ask.indexer --type podcasts

# Dry run (see what would be indexed)
./scripts/run_with_secrets.sh python -m modules.ask.indexer --all --dry-run

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

# Index single item (call from ingest pipeline)
index_single(
    content_id="podcast:acquired:episode-123",
    text="transcript text...",
    title="Episode Title",
    content_type="podcast",
    metadata={"slug": "acquired"}
)
```

### Systemd Timer (DISABLED by default)

```bash
# Install (but don't enable)
sudo cp systemd/atlas-ask-indexer.* /etc/systemd/system/
sudo systemctl daemon-reload

# Enable when ready (runs every 6 hours)
sudo systemctl enable --now atlas-ask-indexer.timer

# Check status
systemctl status atlas-ask-indexer.timer
journalctl -u atlas-ask-indexer -f
```

### Activation Checklist

When ready to enable Atlas Ask:

1. **Bulk index existing content:**
   ```bash
   ./scripts/run_with_secrets.sh python -m modules.ask.indexer --all
   ```

2. **Enable the timer:**
   ```bash
   sudo systemctl enable --now atlas-ask-indexer.timer
   ```

3. **Verify:**
   ```bash
   ./scripts/run_with_secrets.sh python -m modules.ask.cli stats
   ./scripts/run_with_secrets.sh python -m modules.ask.cli ask "test question"
   ```

### Database

Vector store at `data/indexes/atlas_vectors.db`:
- `chunks` - Text chunks with metadata
- `chunk_vectors` - SQLite-vec embeddings (1536 dimensions)
- `chunks_fts` - FTS5 table for keyword search
- `enrichments` - LLM-generated summaries and tags (future)
