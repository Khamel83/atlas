# LLM-OVERVIEW: Atlas

> Complete context for any LLM to understand this project.
> **Last Updated**: 2025-12-24
> **ONE_SHOT Version**: 5.5

## 1. WHAT IS THIS PROJECT?

### One-Line Description
Personal knowledge ingestion system that collects podcast transcripts, articles, and newsletters into a searchable semantic archive.

### The Problem It Solves
Content is scattered across the internet - podcast transcripts on various sites, articles in Instapaper, newsletters in Gmail. Finding something you heard or read months ago is nearly impossible. Atlas automatically ingests everything into a unified, semantically searchable archive.

### Current State
- **Status**: Production (running 24/7 on homelab)
- **Version**: 2.0 (Intelligence Layer)
- **Transcripts**: 5,741 fetched / 6,869 total (83.6%)
- **Embeddings**: 440,030 chunks indexed
- **Last Milestone**: MacWhisper Pro pipeline for local transcription
- **Next Milestone**: Complete remaining 1,045 transcripts, re-index embeddings

---

## 2. ARCHITECTURE OVERVIEW

### Tech Stack
```
Language:    Python 3.11
Framework:   FastAPI (API), Click (CLI)
Database:    SQLite (podcasts, embeddings via sqlite-vec)
Search:      Voyage AI embeddings + FTS5 hybrid search
Deployment:  systemd timers on Ubuntu homelab
Transcription: MacWhisper Pro on Mac Mini M4 (Parakeet v3)
```

### Key Components

| Component | Purpose | Location |
|-----------|---------|----------|
| Podcast CLI | Episode discovery, transcript fetching | `modules/podcasts/cli.py` |
| 16 Resolvers | Source transcripts from various providers | `modules/podcasts/resolvers/` |
| WhisperX Pipeline | Local transcription for paywalled podcasts | Mac Mini + `scripts/mac_mini/` |
| Atlas Ask | Semantic search & Q&A | `modules/ask/` |
| Multi-Source Synthesis | Compare/contrast across sources | `modules/ask/synthesis.py` |
| Annotations | Personal notes & importance weighting | `modules/ask/annotations.py` |
| Output Formats | Briefing, email, markdown export | `modules/ask/output_formats.py` |
| Capture Inbox | Save now, process later | `modules/capture/` |
| Weekly Digest | Topic clustering & summaries | `modules/digest/` |
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

## 4. MAC MINI TRANSCRIPTION PIPELINE

### Architecture (MacWhisper Pro + Local Storage)
```
Linux Homelab                    Mac Mini M4
┌─────────────────┐              ┌─────────────────┐
│ staging/        │              │                 │
│ (1035 mp3s)     │──── rsync ──▶│ ~/atlas-whisper/│
│                 │              │   audio/ (10)   │
│                 │              │      ↓          │
│                 │              │ MacWhisper Pro  │
│                 │              │ (Parakeet v3)   │
│                 │              │      ↓          │
│ transcripts/    │◀── rsync ────│   *.txt output  │
│      ↓          │              │      ↓          │
│ [import]        │              │ [delete mp3]    │
└─────────────────┘              └─────────────────┘
```

### Key Files
- `scripts/whisper_local.sh` - Main pipeline (push/pull/import)
- `scripts/whisper_sweep.sh` - Queue management
- `scripts/import_whisper_transcripts.py` - Imports completed transcripts

### Pipeline Features
- **Batch processing**: 10 files at a time (minimal Mac storage)
- **Local transcription**: Faster than SMB mount
- **Failure handling**: Stuck files (>30min) → retry queue
- **Auto-cleanup**: Deletes mp3 after successful transcription
- **Systemd timer**: Runs every 5 minutes

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
- [x] **Multi-source synthesis** (compare, timeline, summarize, contradict modes)
- [x] **Capture inbox** (save URLs/text/files for later processing)
- [x] **Weekly digest** (topic clustering and summaries)
- [x] **Personal annotations** (notes, reactions, importance weighting)
- [x] **Output formats** (briefing, email draft, markdown)

### What's In Progress
- [ ] WhisperX processing 1,045 files (~2-3 weeks)
- [ ] Clearing ~1,600 pending transcripts
- [ ] Re-index embeddings after transcripts complete

### Known Issues
- YouTube transcript API rate-limited from homelab IP
- Digest clustering requires scikit-learn (optional dep)

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

# Multi-source synthesis
./scripts/run_with_secrets.sh python -m modules.ask.cli synthesize "AI regulation" --mode compare

# Capture for later
python -m modules.capture.cli url "https://example.com" --tags ai,work

# Weekly digest
./scripts/run_with_secrets.sh python -m modules.digest.cli generate --save
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
