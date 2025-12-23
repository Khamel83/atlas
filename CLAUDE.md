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
# Atlas Project Instructions

## Status Check (Do This First)

When user asks "how are we doing?", "status?", "how is atlas running?", or any variant:
**Immediately run** `./venv/bin/python scripts/atlas_status.py` - no questions, no preamble.

This single command shows everything: services, podcasts, content, URL queue, quality.

## Quick Reference

```bash
# UNIFIED STATUS - shows everything at once
./venv/bin/python scripts/atlas_status.py

# PER-PODCAST STATUS - shows each podcast's transcript coverage
./venv/bin/python scripts/atlas_status.py --podcasts

# Brief summary only
./venv/bin/python scripts/atlas_status.py --podcasts --brief

# Detailed quality report (slower, scans all files)
./venv/bin/python scripts/verify_content.py --report

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
│   │   ├── speaker_mapper.py  # Map speaker labels to names
│   │   └── resolvers/    # Transcript sources (7 resolvers)
│   ├── quality/          # Content verification system
│   │   ├── verifier.py   # Core verification logic
│   │   └── __init__.py   # verify_file(), verify_content()
│   ├── storage/          # Content storage with SQLite index
│   ├── ingest/           # Gmail, YouTube, robust URL fetcher
│   │   └── robust_fetcher.py  # Cascading fallback fetcher
│   └── pipeline/         # Content processing pipeline
├── api/                  # FastAPI REST API
│   └── routers/
│       ├── dashboard.py  # Progress monitoring endpoints
│       └── notes.py      # Notes API endpoints
├── scripts/              # Utility scripts
│   ├── verify_content.py            # Content quality verification
│   ├── run_enrichment.py            # Full ad removal workflow
│   ├── analyze_ads.py               # Ad detection analysis
│   ├── enrich_improve_loop.py       # FP detection and fixing
│   ├── stratechery_crawler.py       # Full Stratechery archive
│   ├── parallel_youtube_worker.py   # Multi-worker YouTube fetch
│   ├── check_cookies.py             # Cookie expiration alerts
│   ├── fix_episode_urls.py          # Fix bad episode URLs
│   ├── retry_failed_urls.py         # Batch URL retry
│   ├── validate_podcast_sources.py  # Verify transcript availability
│   ├── download_for_whisper.py      # Download audio for local transcription
│   ├── import_whisper_transcripts.py    # Import completed Whisper transcripts
│   ├── preprocess_whisper_transcript.py # Format Whisper output (paragraphs)
│   ├── backfill_episode_metadata.py     # Update episodes from RSS metadata
│   └── mac_mini/                    # Mac Mini WhisperX scripts
│       ├── whisperx_watcher.py      # Watch folder, auto-transcribe
│       └── com.atlas.whisperx.plist # LaunchAgent for auto-start
├── config/
│   ├── mapping.yml           # Podcast resolver config
│   ├── podcast_limits.json   # Per-podcast episode limits
│   └── podcast_hosts.json    # Known hosts per podcast (for speaker mapping)
├── systemd/              # 13 systemd timer services
│   └── atlas-podcasts.env    # Environment for services
└── data/
    ├── podcasts/         # Transcript storage
    │   └── {slug}/transcripts/*.md
    ├── content/          # URL content storage
    │   ├── article/      # Articles from URLs
    │   ├── newsletter/   # Newsletters from Gmail
    │   └── note/         # User notes (selections, highlights)
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

## Notes System

Notes are short-form user-curated content (selections, quotes, highlights). They are exempt from quality verification.

**Storage:** `data/content/note/{YYYY/MM/DD}/{content_id}/`

**Note Types:**
- `selection` - Highlighted text from webpages (migrated from Instapaper)
- `text` - Plain text notes

### API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/notes/` | Create note from text |
| POST | `/api/notes/url` | Create note from URL + selection (for iOS Shortcut) |
| GET | `/api/notes/` | List notes |
| GET | `/api/notes/{id}` | Get specific note |
| DELETE | `/api/notes/{id}` | Delete note |
| GET | `/api/notes/stats/summary` | Notes statistics |

### Create Note from Selection (iOS Shortcut)

```bash
curl -X POST http://localhost:7444/api/notes/url \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/article",
    "selection": "The highlighted text",
    "title": "Optional title",
    "fetch_full_article": true
  }'
```

When `fetch_full_article` is true, the URL is also queued for full article fetch.

### Migration Script

786 old Instapaper selections were migrated to notes:

```bash
# Dry run
python scripts/migrate_selections_to_notes.py --dry-run

# Apply migration
python scripts/migrate_selections_to_notes.py --apply
```

### Integration with Atlas Ask

Notes are included in the semantic search index:

```bash
# Index notes
./scripts/run_with_secrets.sh python -m modules.ask.indexer --type notes

# Notes are also indexed with --all
./scripts/run_with_secrets.sh python -m modules.ask.indexer --all
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

For podcasts that can't be fetched online (paywalled, no transcript source), we download audio and transcribe locally on Mac Mini M4.

### Episode Status: `local`

Episodes marked with `transcript_status = 'local'` need local transcription:
- Dithering - paywalled
- Asianometry - paywalled
- Against the Rules - no online source
- CWT old episodes - no transcripts on website

### Transcription Options

**Option 1: WhisperX with Speaker Diarization (Recommended)**

WhisperX = Whisper large-v3 + pyannote speaker diarization. Outputs JSON with speaker labels.

Setup: See `scripts/mac_mini/README.md` for full instructions:
1. Install WhisperX: `pip install whisperx pyannote.audio`
2. Get HuggingFace token (free) and accept pyannote license
3. Install LaunchAgent for auto-start

**Option 2: MacWhisper Pro (Legacy)**

GUI app, simpler setup, but no speaker labels. Outputs plain text.

### Fully Automated Pipeline

The Whisper pipeline is **fully automated** via systemd timers:

1. **Download** (`atlas-whisper-download.timer` - every 2 hours): Downloads audio for `local` episodes
2. **WhisperX** (Mac Mini): Watches folder, transcribes with speaker diarization → JSON output
3. **Import** (`atlas-whisper-import.timer` - hourly): Imports transcripts, maps speakers to names
4. **Enrich** (`atlas-enrich.timer` - Sunday 4am): Removes ads using standard patterns

### Processing Pipeline Detail

```
Audio file (.mp3)              Downloaded to data/whisper_queue/audio/
         |
         v
WhisperX (Mac Mini)            Transcribes with speaker diarization
         |
         v
JSON output                    Contains segments with SPEAKER_00, SPEAKER_01, etc.
         |
         v
import_whisper_transcripts.py  Maps speakers to names using config + metadata
         |                     Outputs: **Michael Lewis:** Hello...
         v
data/podcasts/{slug}/          Markdown with speaker attribution
         |
         v
run_enrichment.py (weekly)     Removes ads using ad_stripper.py patterns
         |
         v
data/clean/podcasts/           Clean version for indexing
```

### Speaker Mapping

Speakers are automatically mapped from labels (SPEAKER_00) to names:

1. **Known hosts** from `config/podcast_hosts.json` (60+ podcasts configured)
2. **Guests** extracted from episode title ("with Guest Name") or description
3. **Fallback** to "Speaker 1", "Speaker 2" if no match

**Database tables:**
- `podcast_speakers` - Known hosts/co-hosts per podcast
- `episode_speakers` - Per-episode speaker mappings with confidence scores

### Server Side Scripts

```bash
# Check what's queued for download
ls -la data/whisper_queue/audio/

# Check what's been transcribed (waiting for import)
ls -la data/whisper_queue/transcripts/

# Manual import (normally runs automatically)
python scripts/import_whisper_transcripts.py

# Backfill metadata for all episodes (one-time, already done)
python scripts/backfill_episode_metadata.py
```

### Mac Mini Setup (WhisperX)

Full setup instructions: `scripts/mac_mini/README.md`

**Quick start:**
1. Mount SMB share: `mount_smbfs //khamel83@homelab/atlas /Volumes/atlas`
2. Install WhisperX virtual environment
3. Get HuggingFace token and accept pyannote license
4. Copy `whisperx_watcher.py` to `~/scripts/`
5. Install LaunchAgent for auto-start

**Files:**
- `scripts/mac_mini/whisperx_watcher.py` - Watch folder script
- `scripts/mac_mini/com.atlas.whisperx.plist` - LaunchAgent for auto-start
- `scripts/mac_mini/README.md` - Detailed setup instructions

### File Naming

- Audio: `{podcast_slug}_{episode_id}_{date}_{title}.mp3`
- WhisperX JSON: Same name with `.json` (contains speaker labels)
- MacWhisper TXT: Same name with `.txt` (no speakers, legacy)
- Import script matches by episode ID in filename

### Ad Patterns (iHeart/Pushkin Networks)

Whisper transcripts from iHeart/Pushkin podcasts contain network-wide ads. These patterns are in `modules/enrich/ad_stripper.py`:

- T-Mobile/Supermobile business plans
- Coca-Cola HBCU promotions
- EBCLIS/Evglyss medication (Eli Lilly)
- Bosch home appliances
- Earsay audiobook promos
- "This is an iHeart podcast" / "Guaranteed human" tags
- Pushkin Plus subscription pitches

**Typical ad content**: 20-25% of raw Whisper output is ads (removed by enrichment)

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
- `podcast_speakers` - Known hosts/co-hosts per podcast
- `episode_speakers` - Per-episode speaker mappings (SPEAKER_00 → "Michael Lewis")

### Database Sync (Automatic)

All crawlers now automatically sync to the database after saving transcripts:
- `bulk_crawler.py` - Syncs after `save_transcripts()`
- `podscripts_crawler.py` - Syncs after each crawl
- `npr_crawler.py` - Syncs after each crawl
- `import_whisper_transcripts.py` - Syncs during import

**How it works:**
1. Crawler saves transcript file to disk
2. Crawler matches transcript title to episode in DB (fuzzy matching, 70% threshold)
3. Updates `transcript_status = 'fetched'` and sets `transcript_path`

**Reconciliation (for legacy data):**
If DB/disk get out of sync (e.g., manual file copies), run:
```bash
python scripts/reconcile_transcripts.py --apply
```
This scans disk for transcript files and updates DB to match.

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

# Episodes with speaker mappings
sqlite3 data/podcasts/atlas_podcasts.db "
SELECT e.title, es.speaker_label, es.speaker_name, es.confidence
FROM episode_speakers es JOIN episodes e ON es.episode_id = e.id
ORDER BY es.created_at DESC LIMIT 20"

# Podcasts with configured hosts
sqlite3 data/podcasts/atlas_podcasts.db "
SELECT p.slug, ps.name, ps.role FROM podcast_speakers ps
JOIN podcasts p ON ps.podcast_id = p.id ORDER BY p.slug"
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

## Content Enrichment (Ad Removal, URL Cleanup, Link Queue)

Multi-stage content enrichment pipeline:
1. **Ad Removal**: Strip sponsor/ad content
2. **URL Sanitization**: Remove tracking params (utm_, fbclid, etc.)
3. **Link Extraction**: Queue high-value URLs for potential ingestion

### Architecture

```
modules/enrich/
├── ad_stripper.py        # Pattern-based ad detection
├── content_cleaner.py    # Orchestration + quality scoring
├── versioned_cleaner.py  # Non-destructive versioning
├── url_sanitizer.py      # Strip tracking params from URLs
├── link_extractor.py     # Extract and score URLs for ingestion
├── review.py             # False positive tracking
└── cli.py                # Command-line interface

data/
├── podcasts/             # ORIGINALS (never modified)
├── content/              # ORIGINALS (never modified)
├── clean/                # CLEANED VERSIONS (for indexing)
│   ├── podcasts/{slug}/transcripts/*.md
│   ├── article/*.md
│   ├── newsletter/*.md
│   ├── youtube/*.md
│   └── stratechery/{articles,podcasts}/*.md
└── enrich/
    ├── enrich.db         # SQLite tracking database
    ├── link_queue.db     # URLs queued for potential ingestion
    ├── changes/*.json    # Detailed removal records
    └── reports/*.md      # Weekly reports
```

### Commands

```bash
# Full enrichment workflow (ads, FPs, URL cleanup, link extraction, report)
./venv/bin/python scripts/run_enrichment.py

# Dry run
./venv/bin/python scripts/run_enrichment.py --dry-run

# Specific content type
./venv/bin/python scripts/run_enrichment.py --type podcasts

# Skip URL sanitization or link extraction
./venv/bin/python scripts/run_enrichment.py --skip-sanitize
./venv/bin/python scripts/run_enrichment.py --skip-links

# Force re-clean everything
./venv/bin/python scripts/run_enrichment.py --force

# Just generate report
./venv/bin/python scripts/run_enrichment.py --report
```

### URL Sanitization

Strips tracking parameters while preserving content and auth params:

```bash
# Standalone sanitization
./venv/bin/python -m modules.enrich.url_sanitizer --clean-dir

# Preview changes
./venv/bin/python -m modules.enrich.url_sanitizer --clean-dir --dry-run
```

**Removed**: `utm_*`, `fbclid`, `gclid`, `ref`, `affiliate`, etc.
**Kept**: `token`, `key`, `auth`, `page`, `id`, `q`, etc.

### Link Extraction

Extracts URLs from content, scores them, and queues high-value ones for review:

```bash
# Extract links from all clean content
./venv/bin/python -m modules.enrich.link_extractor --extract

# View queue stats
./venv/bin/python -m modules.enrich.link_extractor --stats

# View pending high-value links
./venv/bin/python -m modules.enrich.link_extractor --pending --min-score 0.7
```

**Scoring**: Domain reputation, context words, anchor text, URL structure
**Skipped**: Social media, URL shorteners, ads/commerce, podcast platforms
**High-value**: Tech news, research, business news, substacks

### Link Queue Analysis

Analyze extracted URLs to decide what to ingest:

```bash
# Quick summary
./venv/bin/python scripts/analyze_link_queue.py --summary

# Full domain analysis
./venv/bin/python scripts/analyze_link_queue.py --domains

# See which content links the most
./venv/bin/python scripts/analyze_link_queue.py --sources

# Sample high-value URLs (score >= 0.8)
./venv/bin/python scripts/analyze_link_queue.py --samples

# URLs mentioned in multiple sources (consensus = valuable)
./venv/bin/python scripts/analyze_link_queue.py --duplicates

# Analyze specific domain
./venv/bin/python scripts/analyze_link_queue.py --domain nytimes.com

# Export high-value to CSV for review
./venv/bin/python scripts/analyze_link_queue.py --export --min-score 0.7
```

**Current Stats** (as of initial extraction):
- 30k+ URLs extracted
- ~34% high-value (score >= 0.8)
- 4,400+ unique domains
- Top sources: NPR, Stratechery, Substack, NYTimes, The Atlantic

### Analysis & Improvement

```bash
# Analyze ad detection patterns
./venv/bin/python scripts/analyze_ads.py

# Focus on false positives
./venv/bin/python scripts/analyze_ads.py --fp

# Analyze specific pattern
./venv/bin/python scripts/analyze_ads.py --pattern "Squarespace"

# Improvement loop (analyze → fix → repeat)
./venv/bin/python scripts/enrich_improve_loop.py
./venv/bin/python scripts/enrich_improve_loop.py --fix
```

### How It Works

1. **Ad Detection**: Regex patterns for sponsor phrases, advertiser names, URL patterns
2. **Confidence tiers**: HIGH (>0.9) auto-remove, MEDIUM (0.7-0.9) review, LOW skip
3. **Negative patterns**: Prevent false positives (e.g., "notion of" vs Notion app)
4. **URL Sanitization**: Strip tracking params from all URLs in clean files
5. **Link Extraction**: Score and queue URLs for potential ingestion
6. **Feedback loop**: Analyze removals, add negative patterns, re-clean

### Current Stats

- **15,116 files** processed
- **7,063 ads** removed (~3MB of ad content)
- **0% false positive rate** (after pattern tuning)
- Top advertisers: Squarespace, Betterment, Casper, ExpressVPN

### Systemd Timer

Runs weekly (Sunday 4am) via `atlas-enrich.timer`:
```bash
systemctl status atlas-enrich.timer
journalctl -u atlas-enrich -f
```

---

## Content Quality Verification

Unified system to verify ALL content is real and valuable before reporting it as "done".

### How It Works

Every piece of content is validated with these checks:
- **File size** >= 500 bytes
- **Word count** >= 100 (articles) or 500 (transcripts)
- **No paywall patterns** ("subscribe to continue", "sign in to read", etc.)
- **No soft-404 patterns** ("page not found", "content unavailable")
- **No JS-blocked content** ("enable javascript")
- **Has actual paragraphs** (not just metadata)

### Quality Levels

- **GOOD**: Passed all checks, verified quality content
- **MARGINAL**: Borderline, passed critical checks but missing some
- **BAD**: Failed critical checks, needs action

### Commands

```bash
# Full verification scan (generates report)
./venv/bin/python scripts/verify_content.py --report

# Quick scan of specific content type
./venv/bin/python scripts/verify_content.py --type podcasts

# JSON output for scripting
./venv/bin/python scripts/verify_content.py --json

# Show more problem files
./venv/bin/python scripts/verify_content.py --problems 50
```

### Integration

Quality gates are integrated into fetchers:
- `simple_url_fetcher.py` - validates before marking "fetched"
- `fetch_paywalled.py` - validates after Playwright fetch

**New content is automatically verified before being counted as success.**

### Reports

Daily reports saved to: `data/reports/quality_YYYY-MM-DD.md`

Nightly timer runs at 5am: `atlas-verify.timer`

### Python API

```python
from modules.quality import verify_file, verify_content, is_garbage_content, QualityLevel

# Verify a file
result = verify_file("/path/to/content.md")
if result.is_good:
    print("Content verified!")
else:
    print(f"Issues: {result.issues}")

# Quick garbage check before saving (use in fetchers)
is_bad, reason = is_garbage_content(text_content)
if is_bad:
    logger.warning(f"Skipping garbage: {reason}")
    return  # Don't save
# Save content...

# Verify content string (before saving)
result = verify_content(content_text, 'article')
if result.quality == QualityLevel.BAD:
    # Don't save, mark as failed
    pass
```

### Database

Verification results stored in: `data/quality/verification.db`

```sql
-- Get quality breakdown
SELECT quality, COUNT(*) FROM verifications GROUP BY quality;

-- Find all bad files
SELECT file_path, issues FROM verifications WHERE quality = 'bad';
```

### Current Stats (2025-12-23)

| Quality | Count | Percentage |
|---------|-------|------------|
| Good | 75,572 | 88.3% |
| Marginal | 8,531 | 10.0% |
| Bad | 994 | 1.2% |

### Marginal Cleanup

Many "marginal" files are actually **failed fetches** - nav pages, footers, index pages that got saved as content. Run cleanup to delete garbage and re-queue URLs:

```bash
# Preview cleanup
./venv/bin/python scripts/cleanup_marginal_garbage.py --dry-run

# Apply cleanup (deletes garbage, re-queues URLs)
./venv/bin/python scripts/cleanup_marginal_garbage.py --apply
```

**What it does:**
- Deletes files matching garbage patterns (YouTube footers, index pages)
- Re-queues article URLs for refetch
- Keeps legitimately short content (>150 words for podcasts, >100 for articles)

### Marginal Recovery (Legacy)

For remaining marginal content, use tiered recovery to re-fetch:

```bash
# Run tiered recovery (Tier 1 = high-value articles)
./venv/bin/python scripts/recover_marginal_tiered.py --tier 1

# Run all tiers in order
./venv/bin/python scripts/recover_marginal_tiered.py --tier 1 2 3

# Full background pipeline
nohup ./scripts/run_full_marginal_recovery.sh > /tmp/full_recovery.log 2>&1 &

# Monitor progress
tail -f /tmp/full_recovery.log

# Check recovery database
sqlite3 data/quality/marginal_recovery.db "SELECT tier, status, COUNT(*) FROM marginal_recovery GROUP BY tier, status"
```

**Tier priorities:**
- **Tier 1** (HIGH): `content/article`, `clean/article`, `stratechery`
- **Tier 2** (MEDIUM): Major news sites (washingtonpost, nytimes, bloomberg)
- **Tier 3** (LOW): Podcasts, newsletters, youtube (often legitimately short)

### False Positive Prevention

The verifier has smart exemptions to prevent false positives:
- Files >5000 words are exempt from JS-blocked, paywall, and soft-404 checks
- Only header/footer regions checked (first/last 1000 chars)
- Files with 300+ words don't need 3 paragraphs
- Paywall/404 requires 2+ pattern matches (single match = likely false positive)

---

## Link Discovery & Ingestion Pipeline

Unified system for extracting, approving, and ingesting URLs from any content source.

### Architecture

```
modules/links/
├── __init__.py      # Package exports
├── models.py        # Link, LinkSource, ApprovalResult
├── extractor.py     # Extract & score links from text
├── approval.py      # YAML-based approval engine
├── bridge.py        # link_queue.db → url_queue.txt
├── shownotes.py     # Extract from podcast RSS descriptions
└── cli.py           # Unified CLI

Data Flow:
  Sources → LinkExtractor → link_queue.db → ApprovalEngine → url_queue.txt → URL Fetcher
```

### CLI Commands

```bash
# Extract from podcast show notes (no HTTP - uses cached RSS data)
./venv/bin/python -m modules.links.cli extract-shownotes --all
./venv/bin/python -m modules.links.cli extract-shownotes --slug acquired

# Extract from any text file
./venv/bin/python -m modules.links.cli extract --file article.md --source article

# Run approval workflow (uses config/link_approval_rules.yml)
./venv/bin/python -m modules.links.cli approve --dry-run
./venv/bin/python -m modules.links.cli approve --apply

# Bridge approved links to URL queue (drip mode: 50 urls/run)
./venv/bin/python -m modules.links.cli ingest --dry-run
./venv/bin/python -m modules.links.cli ingest --drip

# Pipeline status
./venv/bin/python -m modules.links.cli status
./venv/bin/python -m modules.links.cli stats --by-domain
./venv/bin/python -m modules.links.cli stats --by-source
```

### Approval Rules

Configuration in `config/link_approval_rules.yml`:
- **Trusted domains**: Auto-approve (stratechery, nytimes, arxiv, etc.)
- **Score threshold**: Auto-approve >= 0.85
- **Reject threshold**: Auto-reject < 0.40
- **Blocked domains**: Always reject (bit.ly, twitter, etc.)
- **Drip settings**: 50 urls/run, 10 sec delay

### Systemd Timer

Runs every 2 hours via `atlas-link-pipeline.timer`:
1. Run approval on pending links
2. Bridge approved links to url_queue.txt (drip mode)

```bash
# Install
sudo cp systemd/atlas-link-pipeline.* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now atlas-link-pipeline.timer

# Check
systemctl status atlas-link-pipeline.timer
journalctl -u atlas-link-pipeline -f
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
