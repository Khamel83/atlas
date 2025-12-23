# LLM-OVERVIEW: Atlas

> Complete context for any LLM to understand this project.
> **Last Updated**: 2025-12-23
> **ONE_SHOT Version**: 5.5

## 1. WHAT IS THIS PROJECT?

### One-Line Description
Personal knowledge ingestion system that collects podcast transcripts, articles, and newsletters into a searchable semantic archive.

### The Problem It Solves
Content is scattered across the internet - podcast transcripts on various sites, articles in Instapaper, newsletters in Gmail. Finding something you heard or read months ago is nearly impossible. Atlas automatically ingests everything into a unified, semantically searchable archive.

### Current State
- **Status**: Production (running 24/7 on homelab)
- **Version**: 1.0
- **Transcripts**: 4,874 fetched / 6,869 total (71%)
- **Embeddings**: 440,030 chunks indexed
- **Last Milestone**: Fixed podcast resolvers, added WhisperX watchdog
- **Next Milestone**: Clear ~2,000 pending transcripts, complete embeddings

---

## 2. ARCHITECTURE OVERVIEW

### Tech Stack
```
Language:    Python 3.11
Framework:   FastAPI (API), Click (CLI)
Database:    SQLite (podcasts, embeddings via sqlite-vec)
Search:      Voyage AI embeddings + FTS5 hybrid search
Deployment:  systemd timers on Ubuntu homelab
Transcription: WhisperX on Mac Mini M4 (via SMB mount)
```

### Key Components

| Component | Purpose | Location |
|-----------|---------|----------|
| Podcast CLI | Episode discovery, transcript fetching | `modules/podcasts/cli.py` |
| 16 Resolvers | Source transcripts from various providers | `modules/podcasts/resolvers/` |
| WhisperX Pipeline | Local transcription for paywalled podcasts | Mac Mini + `scripts/mac_mini/` |
| Atlas Ask | Semantic search & Q&A | `modules/ask/` |
| Indexer | Generate and store embeddings | `modules/ask/indexer.py` |
| Content Storage | File-based markdown with SQLite index | `modules/storage/` |
| Quality Verifier | Detect garbage/truncated content | `modules/quality/` |

### Data Flow

```
RSS Feeds → Discovery → Episode DB → Resolvers → Transcripts → Clean → Embeddings
                                          ↓
                                   WhisperX (fallback)
                                          ↓
Gmail/URLs → Ingest → Content Storage → Clean → Embeddings → Atlas Ask (query)
```

---

## 3. PODCAST RESOLVER CHAIN

Resolvers try in priority order until one succeeds:

| Priority | Resolver | Source | Notes |
|----------|----------|--------|-------|
| 1 | `rss_link` | Direct link in RSS | Best quality |
| 2 | `playwright` | Scrape with browser | Stratechery, Dithering |
| 3 | `nyt` | NY Times with cookies | Hard Fork |
| 4 | `network_transcripts` | NPR, Slate, WNYC | Official transcripts |
| 5 | `podscripts` | AI transcripts | 47 shows covered |
| 6 | `generic_html` | Scrape episode pages | Tyler, Acquired |
| 7 | `youtube_transcript` | Auto-captions | Rate-limited from cloud |
| 8 | `pattern` | URL pattern matching | Last resort before Whisper |

### Podcasts Requiring WhisperX (Paywalled)
- **Dithering** (411 episodes) - No online transcripts
- **Asianometry** (350 episodes) - No online transcripts
- **Against the Rules** (284 episodes) - Partial YouTube coverage

---

## 4. MAC MINI WHISPERX PIPELINE

### Architecture
```
Linux Homelab                    Mac Mini M4
┌─────────────────┐              ┌─────────────────┐
│ data/whisper_   │──── SMB ────▶│ /Volumes/atlas- │
│ queue/audio/    │              │ whisper/audio/  │
│                 │◀── SMB ──────│                 │
│ queue/transcripts│             │ whisperx_watcher│
└─────────────────┘              └─────────────────┘
```

### Key Files
- `scripts/mac_mini/whisperx_watcher.py` - Watches for audio, transcribes
- `scripts/mac_mini/mount_atlas_whisper.sh` - Mounts SMB share
- `scripts/mac_mini/com.atlas.smb-mount.plist` - LaunchAgent for auto-mount
- `scripts/download_for_whisper.py` - Downloads audio for queue
- `scripts/import_whisper_transcripts.py` - Imports completed transcripts

### Watchdog Features (Added 2025-12-23)
- **CPU Monitoring**: Kills process if <5% CPU for 10 minutes
- **Hard Timeout**: 90 minutes max per file
- **Auto-Recovery**: Watcher restarts transcription on next file

---

## 5. ATLAS ASK (SEMANTIC SEARCH)

### How It Works
1. **Indexer** chunks all content (transcripts, articles, newsletters)
2. **Voyage AI** generates embeddings for each chunk
3. **sqlite-vec** stores embeddings with metadata
4. **Hybrid search** combines vector similarity + FTS5 keyword matching
5. **LLM synthesis** answers questions from retrieved context

### Key Files
- `modules/ask/indexer.py` - Chunk content, generate embeddings
- `modules/ask/retriever.py` - Hybrid search (vector + keyword)
- `modules/ask/cli.py` - Query interface
- `config/ask_config.yml` - Model settings, chunk sizes

### Usage
```bash
# Re-index all content
./scripts/run_with_secrets.sh python -m modules.ask.indexer --all

# Query
./scripts/run_with_secrets.sh python -m modules.ask.cli ask "What did Tyler Cowen say about AI?"
```

### Current Stats
- **440,030 chunks** indexed
- **339M tokens** embedded (Voyage AI)
- **Database**: `data/indexes/atlas_vectors.db`

---

## 6. SYSTEMD TIMERS (13 Services)

| Timer | Schedule | Purpose |
|-------|----------|---------|
| `atlas-podcast-discovery` | 6am & 6pm | Find new episodes |
| `atlas-transcripts` | Every 4 hours | Fetch pending transcripts |
| `atlas-whisper-download` | Every 2 hours | Queue audio for WhisperX |
| `atlas-whisper-import` | Hourly | Import completed transcripts |
| `atlas-gmail` | Every 5 min | Check newsletters |
| `atlas-enrich` | Sunday 4am | Ad removal pipeline |
| `atlas-verify` | Daily 5am | Quality check report |

---

## 7. CURRENT WORK IN PROGRESS

### What Works
- [x] Podcast discovery and fetching (57 podcasts)
- [x] 16 resolvers for various transcript sources
- [x] Mac Mini WhisperX with watchdog
- [x] Semantic search with 440K chunks
- [x] Content enrichment (ad removal)
- [x] Quality verification

### What's In Progress
- [ ] Clearing ~2,000 pending transcripts
- [ ] WhisperX processing 1,045 files (~2-3 weeks)
- [ ] Tyler (270 episodes being fetched)

### Known Issues
- YouTube transcript API rate-limited from homelab IP
- Some podcast URLs in DB point to libsyn (fixed for Tyler)

---

## 8. HOW TO WORK ON THIS PROJECT

### Setup
```bash
git clone git@github.com:Khamel83/atlas.git
cd atlas
./scripts/setup.sh  # Creates venv, installs deps
```

### Common Commands
```bash
# Status check (always start here)
./venv/bin/python scripts/atlas_status.py

# Run tests
./venv/bin/pytest tests/ -v

# Fetch transcripts for specific podcast
python -m modules.podcasts.cli fetch-transcripts --slug acquired --limit 10

# Re-index embeddings
./scripts/run_with_secrets.sh python -m modules.ask.indexer --all

# Ask a question
./scripts/run_with_secrets.sh python -m modules.ask.cli ask "question here"
```

### Database Queries
```bash
# Pending transcripts by podcast
sqlite3 data/podcasts/atlas_podcasts.db "
SELECT p.slug, COUNT(*) FROM episodes e
JOIN podcasts p ON e.podcast_id = p.id
WHERE e.transcript_status = 'unknown'
GROUP BY p.slug ORDER BY COUNT(*) DESC"

# Embedding stats
sqlite3 data/indexes/atlas_vectors.db "SELECT COUNT(*) FROM chunks"
```

---

## 9. CONFIGURATION FILES

| File | Purpose |
|------|---------|
| `config/mapping.yml` | Per-podcast resolver config |
| `config/podcast_limits.json` | Episode limits per podcast |
| `config/ask_config.yml` | Embeddings/LLM settings |
| `config/whisper_podcasts.json` | Podcasts requiring WhisperX |
| `~/.config/atlas/stratechery_cookies.json` | Stratechery auth |
| `~/.config/atlas/nyt_cookies.json` | NY Times auth |

---

## 10. WHEN EMBEDDINGS ARE COMPLETE

Once all transcripts are fetched and indexed:

1. **Query anything**: "What did Ben Thompson say about Apple's AI strategy?"
2. **Cross-reference**: Find connections across podcasts, articles, newsletters
3. **Research mode**: Deep dive on topics with full source attribution
4. **Export**: Generate reports from semantic search results

The 339M tokens represent ~5+ years of curated content, fully searchable.
