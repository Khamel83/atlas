# LLM-OVERVIEW: Atlas

> Complete context for any LLM to understand this project.
> **Last Updated**: 2025-12-15
> **ONE_SHOT Version**: 4.0
> **Status**: Production - Fully automated ingestion running

---

## 1. WHAT IS THIS PROJECT?

### One-Line Description
Personal knowledge system that automatically ingests podcasts, articles, and newsletters into a searchable archive.

### The Problem It Solves
Content is scattered across the internet - podcast transcripts on various sites, articles saved in Instapaper, newsletters in Gmail. Manually organizing this is tedious and unsearchable. Atlas automates ingestion and makes everything queryable.

### Current State
- **Status**: Production (ingestion running 24/7)
- **Content Quality**: 35,385 good (80.1%), 8,002 marginal (18.1%), 800 bad (1.8%)
- **Coverage**: 4,445 podcast transcripts fetched (66% of 6,729 target)
- **Automation**: 9 systemd timers handling discovery, fetching, retries
- **Tests**: 34 passing (api, podcasts, storage)
- **Security**: All OWASP issues fixed, secrets encrypted with SOPS + Age
- **Next Milestone**: Complete marginal recovery, enable Atlas Ask

---

## 2. ARCHITECTURE OVERVIEW

### Tech Stack
```
Language:    Python 3.12
Framework:   FastAPI (API), Click (CLI)
Database:    SQLite (WAL mode) + files
Deployment:  systemd timers on homelab
```

### System Architecture
```
┌─────────────────────────────────────────────────────────────────┐
│                        INGESTION SOURCES                        │
├─────────────────┬─────────────────┬─────────────────────────────┤
│ Podcast RSS     │ Gmail Labels    │ Manual Inbox               │
│ (6am & 6pm)     │ (every 5 min)   │ (every 5 min)              │
└────────┬────────┴────────┬────────┴─────────────┬───────────────┘
         │                 │                      │
         ▼                 ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                      CONTENT PIPELINE                           │
├─────────────────────────────────────────────────────────────────┤
│ Resolvers:           Robust Fetcher:        Bulk Import:        │
│ • generic_html       • Direct HTTP          • Instapaper HTML   │
│ • podscripts         • Playwright           • Pocket JSON       │
│ • youtube_transcript • Archive.is           • URL lists         │
│ • network_transcripts• Wayback Machine      • CSV files         │
│ • rss_link           • URL resurrection     • Markdown          │
└────────┬────────────────────┬───────────────────────┬───────────┘
         │                    │                       │
         ▼                    ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                         STORAGE                                 │
├─────────────────────────────────────────────────────────────────┤
│ data/podcasts/{slug}/transcripts/*.md   (podcast transcripts)  │
│ data/content/article/{date}/{id}/       (articles)             │
│ data/content/newsletter/{date}/{id}/    (newsletters)          │
│ data/stratechery/{articles,podcasts}/   (Ben Thompson archive) │
└────────────────────────────────────────────────────┬────────────┘
                                                     │
                                                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                     ATLAS ASK (Ready, Not Enabled)              │
├─────────────────────────────────────────────────────────────────┤
│ Embeddings → Vector Store → Hybrid Search → LLM Synthesis       │
│ (openai/text-embedding-3-small)          (gemini-2.5-flash-lite)│
└─────────────────────────────────────────────────────────────────┘
```

### Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| **Podcast System** | `modules/podcasts/` | RSS discovery, transcript resolvers, CLI |
| **Content Pipeline** | `modules/pipeline/` | URL processing with fallbacks |
| **Robust Fetcher** | `modules/ingest/robust_fetcher.py` | Cascading fallback fetcher |
| **Bulk Import** | `modules/ingest/bulk_import.py` | Messy folder processor |
| **Gmail Ingester** | `modules/ingest/gmail_ingester.py` | Email label watcher |
| **File Store** | `modules/storage/file_store.py` | Content storage |
| **Index Manager** | `modules/storage/index_manager.py` | SQLite index + dedup |
| **Atlas Ask** | `modules/ask/` | Semantic search (not enabled) |
| **REST API** | `api/` | FastAPI endpoints |

---

## 3. INGESTION PIPELINES

### Pipeline 1: Podcasts (Fully Automated)

```
RSS Feeds → Discovery (6am/6pm) → Fetch (4-hourly) → Markdown files
```

**Transcript Sources (All 46 podcasts validated):**
- 6 podcasts: Direct website scraping (Stratechery, Acquired, NPR, etc.)
- 40 podcasts: Podscripts.co (AI transcripts)
- Fallback: YouTube auto-captions (via VPN proxy)

**Commands:**
```bash
python -m modules.podcasts.cli status           # Check coverage
python -m modules.podcasts.cli fetch-transcripts --all  # Manual run
python scripts/validate_podcast_sources.py      # Verify sources work
```

### Pipeline 2: Articles/URLs (Fully Automated)

```
Gmail label "atlas" OR data/inbox/urls/ → Robust Fetcher → Storage
```

**Fetching Strategy (Cascading Fallbacks):**
1. Direct HTTP (Trafilatura)
2. Playwright headless browser
3. Archive.is lookup
4. Wayback Machine lookup
5. URL Resurrection (search for alternatives)

**Commands:**
```bash
python -m modules.ingest.robust_fetcher "https://example.com"
python scripts/retry_failed_urls.py
```

### Pipeline 3: Bulk Import (Manual)

```
Drop folder anywhere → Auto-detect file types → Dedupe → Process
```

**Supported:** Instapaper HTML, Pocket JSON, URL lists, CSV, Markdown, HTML

**Commands:**
```bash
python -m modules.ingest.bulk_import /path/to/folder --dry-run
python -m modules.ingest.bulk_import /path/to/folder
```

### Pipeline 4: Stratechery Archive (Running)

```
Cookie-authenticated crawler → All articles + podcasts since 2013
```

**Commands:**
```bash
python scripts/stratechery_crawler.py --type all --delay 5
tail -f /tmp/stratechery-archive.log
```

### Pipeline 5: Content Quality Verification (Automated)

```
All content files → Verifier checks → Good/Marginal/Bad classification
```

**Checks performed:**
- Minimum file size (500 bytes)
- Word count thresholds (100 for articles, 500 for transcripts)
- Paywall pattern detection (2+ patterns required)
- Soft-404 detection
- JS-blocked content detection (exempt if >5000 words)
- Paragraph structure

**Commands:**
```bash
# Verify all content
./venv/bin/python scripts/verify_content.py --report

# Check stats
sqlite3 data/quality/verification.db "SELECT quality, COUNT(*) FROM verifications GROUP BY quality"
```

---

## 4. KEY FILES

| What | Where |
|------|-------|
| Podcast CLI | `modules/podcasts/cli.py` |
| Transcript resolvers | `modules/podcasts/resolvers/` |
| Robust URL fetcher | `modules/ingest/robust_fetcher.py` |
| Bulk folder import | `modules/ingest/bulk_import.py` |
| Gmail ingester | `modules/ingest/gmail_ingester.py` |
| Content pipeline | `modules/pipeline/content_pipeline.py` |
| Content verifier | `modules/quality/verifier.py` |
| Marginal recovery | `scripts/recover_marginal_tiered.py` |
| Podcast config | `config/mapping.yml` |
| Podcast limits | `config/podcast_limits.json` |
| API entry | `api/main.py` |
| Atlas Ask | `modules/ask/` |

---

## 5. SYSTEMD TIMERS (7 Running)

| Timer | Schedule | Purpose |
|-------|----------|---------|
| `atlas-podcast-discovery` | 6am & 6pm | Find new episodes from RSS |
| `atlas-transcripts` | Every 4 hours | Fetch pending transcripts |
| `atlas-youtube-retry` | Sunday 3am | Retry YouTube with VPN proxy |
| `atlas-gmail` | Every 5 min | Check Gmail for labeled emails |
| `atlas-inbox` | Every 5 min | Process manual inbox folder |
| `atlas-content-retry` | Weekly | Retry failed URL fetches |
| `atlas-cookie-check` | Daily 9am | Alert on expiring cookies |

**Check status:**
```bash
systemctl list-timers | grep atlas
journalctl -u atlas-transcripts -f
```

---

## 6. CURRENT STATE

### What Works
- Podcast transcript discovery and fetching (66% complete, automated)
- Article/URL ingestion with cascading fallbacks
- Bulk import from messy folders with deduplication
- Gmail label watching for newsletters
- Stratechery authenticated archive crawl
- Cookie expiration monitoring with alerts (Telegram + ntfy)
- REST API with health/metrics/episode/transcript endpoints
- Secrets management (SOPS + Age encryption)

### What's In Progress
- Completing podcast backlog (~2,200 remaining, ~7 hours)
- Stratechery full archive crawl (running in background)

### What's Ready But Not Enabled
- Atlas Ask semantic search (waiting for ingestion to stabilize)

---

## 7. ARCHITECTURE DECISIONS

### Why SQLite?
**Decision**: SQLite with WAL mode instead of PostgreSQL
**Reason**: Single-user, homelab deployment. SQLite handles 100K+ records fine.
**Upgrade Trigger**: Multi-user access or heavy concurrent writes

### Why File-Based Content Storage?
**Decision**: Store content as files, SQLite only for index/metadata
**Reason**: Files are portable, git-friendly, easy to backup
**Upgrade Trigger**: Need transactional content updates

### Why Multiple Transcript Resolvers?
**Decision**: Chain of 6 resolvers tried in priority order
**Reason**: No single source covers all podcasts. Fallback chain maximizes coverage.
**Upgrade Trigger**: N/A - this is the right design

### Why Podscripts over YouTube?
**Decision**: Prefer Podscripts.co transcripts over YouTube auto-captions
**Reason**: Podscripts uses Whisper AI, higher quality than YouTube's ASR
**Upgrade Trigger**: Podscripts becomes unavailable/paid

---

## 8. HOW TO WORK ON THIS PROJECT

### Quick Start
```bash
./scripts/setup.sh                    # Create venv, install deps
./venv/bin/pytest tests/ -v           # Run tests (34 passing)
./venv/bin/uvicorn api.main:app --port 7444  # Start API
```

### Common Operations
```bash
# Check podcast status
python -m modules.podcasts.cli status

# Fetch transcripts manually
python -m modules.podcasts.cli fetch-transcripts --all

# Import a folder of old bookmarks
python -m modules.ingest.bulk_import ~/Downloads/instapaper --dry-run

# Check system health
curl http://localhost:7444/health
```

---

## 9. CONTEXT FOR AI ASSISTANTS

### DO
- Check CLAUDE.md for operational commands
- Use existing resolvers before creating new ones
- Update docs when adding features
- Run tests after changes

### DON'T
- Add PostgreSQL (SQLite is fine for this scale)
- Add abstraction "for flexibility"
- Create new files when editing existing ones works
- Skip the validation script when adding podcast sources

### Key Patterns
- **Deduplication**: URL hash-based, checked in `index_manager.lookup_url()`
- **Rate limiting**: Built into all fetchers (2-5 second delays)
- **Fallbacks**: Always have a fallback strategy (archive.is, wayback)
- **Cookies**: Stored in `~/.config/atlas/` for authenticated sites

---

## 10. RECENT CHANGES

| Date | Change | Impact |
|------|--------|--------|
| 2025-12-15 | Content Quality Verification | 44K files classified: 80.1% good, 18.1% marginal, 1.8% bad |
| 2025-12-15 | Fixed verifier false positives | JS check exempts >5000 words, smarter paragraph check |
| 2025-12-15 | Marginal recovery scripts | Tiered approach to re-fetch failed scrapes |
| 2025-12-10 | Security audit complete | Fixed command injection, CORS, SSRF, SQL injection |
| 2025-12-10 | N+1 query fix | Dashboard queries: 50+ → 2 |
| 2025-12-10 | API endpoints added | Episode detail, transcript, content text endpoints |
| 2025-12-10 | Module consolidation | Archived unused modules/ingestion/ |
| 2025-12-10 | Code quality fixes | All bare except clauses fixed (17 → 0) |
| 2025-12-10 | Added bulk_import.py | Can now import messy folders of Instapaper exports |
| 2025-12-10 | Added validate_podcast_sources.py | Verify all podcasts have working sources |
| 2025-12-10 | Fixed recursive link spider bug | generic_html no longer chases Wikipedia links |
| 2025-12-09 | Added Stratechery crawler | Full Ben Thompson archive in progress |
| 2025-12-09 | Cookie expiration alerts | Daily check, ntfy/Telegram notifications |
| 2025-12-06 | Architecture cleanup | Archived 300+ legacy files, 34 tests passing |

---

*For detailed CLI reference, see `CLAUDE.md`*
*For task status, see `TODO.md`*
