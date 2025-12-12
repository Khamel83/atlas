# Atlas - Personal Knowledge Ingestion System

**Status**: Production
**Current Tier**: SQLite + systemd timers on homelab
**Upgrade Trigger**: Multi-user access or heavy concurrent writes

## What This Does

Content is scattered across the internet - podcast transcripts on various sites, articles saved in Instapaper, newsletters in Gmail. Atlas automatically ingests everything into a searchable archive.

**Current coverage**: 4,445 podcast transcripts (66% of 6,729 target), running 24/7

## MVP: Always-Running Fetchers

Two simple services that run forever, slowly fetching content. No rush, just reliable.

### URL Fetcher
```bash
# Add URLs to queue (that's it)
echo "https://example.com/article" >> data/url_queue.txt

# Check status
journalctl -u atlas-url-fetcher -f
cat data/url_fetcher_state.json
```
- Checks queue every 60 seconds
- 10 second delay between fetches
- Saves to `data/articles/{domain}/{date}_{title}.md`
- Uses trafilatura for clean extraction

### Transcript Fetcher
```bash
# Just runs - checks RSS feeds for new episodes
journalctl -u atlas-simple-fetcher -f
cat data/fetcher_state.json
```
- 15 podcasts configured (expand in script)
- Fetches from Podscripts.co and direct sources
- Saves to `data/podcasts/{slug}/transcripts/`

### Services
```bash
# Both run as systemd services
sudo systemctl status atlas-url-fetcher
sudo systemctl status atlas-simple-fetcher

# View logs
journalctl -u atlas-url-fetcher --since today
journalctl -u atlas-simple-fetcher --since today
```

## Quick Start

```bash
# Setup
./scripts/setup.sh

# Check status
./venv/bin/python -m modules.podcasts.cli status

# Start API
./venv/bin/uvicorn api.main:app --port 7444

# Run tests
./venv/bin/pytest tests/ -v
```

## Features

### Automated Ingestion (7 systemd timers)
- **Podcast transcripts**: Discovers from RSS, fetches from 7 resolvers (every 4 hours)
- **Gmail newsletters**: Watches for labeled emails (every 5 min)
- **Manual inbox**: Process URLs dropped in `data/inbox/` (every 5 min)
- **Cookie monitoring**: Alerts before auth cookies expire (daily)

### Bulk Import
```bash
# Import messy folder of Instapaper/Pocket exports
python -m modules.ingest.bulk_import ~/Downloads/exports --dry-run
python -m modules.ingest.bulk_import ~/Downloads/exports
```

### Robust URL Fetching
Cascading fallbacks: Direct HTTP → Playwright → Archive.is → Wayback Machine → URL resurrection

### Podcast Sources (All 46 podcasts validated)
| Source | Coverage |
|--------|----------|
| Website (direct HTML) | 6 podcasts (Stratechery, Acquired, NPR, Lex Fridman, etc.) |
| Podscripts.co | 40 podcasts (AI transcripts) |
| YouTube | Fallback (via VPN proxy) |

## Configuration

| File | Purpose |
|------|---------|
| `config/mapping.yml` | Podcast resolver configuration |
| `config/podcast_limits.json` | Per-podcast episode limits |
| `secrets.env.encrypted` | API keys (SOPS + Age encrypted) |
| `~/.config/atlas/stratechery_cookies.json` | Authenticated access |

## API Endpoints

```bash
curl http://localhost:7444/health
curl http://localhost:7444/api/podcasts/stats
curl http://localhost:7444/api/podcasts/1/episodes/42        # Get episode detail
curl http://localhost:7444/api/podcasts/1/episodes/42/transcript  # Get transcript
curl http://localhost:7444/api/content/abc123/text            # Get content text
curl http://localhost:7444/api/dashboard/status
```

Interactive docs: http://localhost:7444/docs

## Architecture

```
modules/
├── podcasts/      # RSS discovery, 7 transcript resolvers
├── ingest/        # Gmail, bulk import, robust fetcher
├── storage/       # File store + SQLite index
├── pipeline/      # Content processing
├── ask/           # Semantic search (ready, not enabled)
└── notifications/ # Telegram/ntfy alerts

api/               # FastAPI REST API (34 tests passing)
scripts/           # Validation, crawlers, utilities
systemd/           # 7 timers for automation
config/            # YAML configs + encrypted secrets (SOPS + Age)
data/
├── podcasts/{slug}/transcripts/  # Podcast transcripts
├── content/article/              # Fetched articles
├── content/newsletter/           # Processed emails
└── stratechery/                  # Ben Thompson archive
```

## Known Limitations

- YouTube transcripts require VPN proxy (cloud IPs blocked)
- Stratechery requires authenticated cookies (6-month refresh)
- Some podcasts only have audio (no transcript source exists)

## Documentation

- **CLAUDE.md** - Detailed CLI reference and operations
- **LLM-OVERVIEW.md** - Full project context for AI assistants
- **TODO.md** - Current task status

---

*ONE_SHOT v4.0 enabled. 22 skills available in `.claude/skills/`*
