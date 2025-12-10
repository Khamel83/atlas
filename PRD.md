# Atlas - Product Requirements Document

**Version**: 1.1
**Created**: 2025-12-06
**Updated**: 2025-12-10
**ONE_SHOT Version**: 4.0
**Status**: Approved - Production

---

## ONE_SHOT Core Questions (Q0-Q13)

### Q0: Mode
**Answer**: `heavy`

Atlas is a multi-service system with:
- Continuous background processor
- REST API server
- Database layer
- Multiple content ingestion strategies
- External API integrations

### Q1: What Are We Building?

**Atlas** - An automated podcast transcript discovery and content ingestion system.

**One-liner**: Atlas finds podcast transcripts scattered across the internet and organizes them into a searchable local database.

### Q2: What Problem Does It Solve?

**Problem**: Content is scattered across the internet - podcast transcripts on various sites, articles saved in Instapaper, newsletters in Gmail. Manually organizing this is tedious and unsearchable.

**Solution**: Atlas automates the entire workflow:
1. Tracks 46 curated podcasts (6,729 episodes in scope)
2. Discovers transcripts from 6 sources (website HTML, Podscripts, YouTube, etc.)
3. Ingests articles via Gmail labels, inbox folder, or bulk import
4. Stores in searchable, file-based format
5. Runs 24/7 via systemd timers

### Q2.5: Reality Check

**Is this being used?** Yes - running 24/7 on homelab.
**Evidence**: 4,367 transcripts fetched (65% of 6,729), 7 systemd timers active.

### Q3: Philosophy / Constraints

1. **File-first storage**: Content in files, database for tracking only
2. **$0 infrastructure**: Homelab-only, no cloud costs
3. **Graceful degradation**: If one source fails, try others
4. **Non-destructive**: Never delete source content
5. **Respect rate limits**: Be a good citizen to external APIs

### Q4: Features (Prioritized)

#### P0 - Must Have (Done)
- [x] RSS feed parsing for episode discovery
- [x] SQLite episode tracking with WAL mode
- [x] 7 transcript resolvers (generic_html, podscripts, youtube, etc.)
- [x] REST API for external integrations
- [x] Health endpoints (`/health`, `/metrics`)
- [x] 7 systemd timers for automation
- [x] Per-podcast episode limits

#### P1 - Should Have (Done)
- [x] Gmail ingestion (label watching)
- [x] YouTube transcript extraction (via VPN proxy)
- [x] Cascading fallback strategies (5 levels)
- [x] Bulk import for Instapaper/Pocket exports
- [x] Cookie-based auth for Stratechery
- [x] Cookie expiration monitoring with alerts
- [x] Podcast source validation script

#### P2 - Nice to Have (Ready, Not Enabled)
- [x] Semantic search (Atlas Ask module built)
- [ ] Full-text search UI
- [ ] Auto-categorization of content

### Q5: Non-Goals (Explicitly Out of Scope)

- **Audio processing**: No speech-to-text, transcripts must already exist
- **Podcast hosting**: No serving audio files
- **User accounts**: Single-user system
- **Mobile app**: API-only, no native apps
- **Real-time sync**: Batch processing is fine (hourly/daily)

### Q6: Project Type

**Type**: `service` (long-running background process + API)

- Background processor runs continuously
- REST API serves external requests
- Database persists state across restarts

### Q7: Data Shape

```yaml
entities:
  podcast:
    fields: [id, name, rss_url, transcript_source, status, created_at]
    relationships: [has_many: episodes]

  episode:
    fields: [id, podcast_id, title, url, published_at,
             transcript_status, transcript_url, processed_at]
    relationships: [belongs_to: podcast]

  processing_queue:
    fields: [id, episode_id, priority, status, attempts, next_attempt]

  content_file:
    fields: [path, type, source_url, extracted_at]
    storage: filesystem (not database)
```

### Q8: Data Scale

**Answer**: `B` (Medium - 10K-500K records)

- Current: 2,373 episodes, 750 transcripts
- Projected: 50K episodes over 2 years
- Comfortable in SQLite range

### Q9: Storage Tier

**Current**: `sqlite` (with file-based content storage)

**Upgrade trigger**: > 500K records OR multi-instance coordination

**Upgrade path**: PostgreSQL with connection pooling

### Q10: External Dependencies

| Dependency | Purpose | Required? |
|------------|---------|-----------|
| Python 3.8+ | Runtime | Yes |
| SQLite | Database | Yes |
| FastAPI | REST API | Yes |
| BeautifulSoup | HTML parsing | Yes |
| Tavily API | Transcript search | No (fallback exists) |
| Gmail API | Email ingestion | No |
| YouTube API | Video transcripts | No |

### Q11: Interface

**Primary interfaces**:
1. **CLI**: `make run`, `make status`, `./atlas_status.sh`
2. **REST API**: FastAPI on port 7444
3. **Direct database**: SQLite queries for debugging

**No web UI** - API-driven only.

### Q12: Definition of Done (v1.0)

v1.0 is **COMPLETE**. v1.1 is **IN PROGRESS**:

- [x] Process 46 podcasts automatically
- [x] Find transcripts from 6 sources
- [x] Store in searchable format
- [x] REST API for integrations
- [x] Health monitoring
- [x] 7 systemd timers for automation
- [x] Documentation (CLAUDE.md, LLM-OVERVIEW.md, TODO.md)

**v1.1 targets (current)**:
- [x] YouTube transcript extraction (via VPN proxy)
- [ ] 100% transcript coverage (currently 65%)
- [x] Clean architecture (archived 300+ legacy files)
- [ ] Enable Atlas Ask semantic search

### Q13: Naming Conventions

```yaml
naming:
  project: atlas
  database: podcast_processing.db
  main_process: atlas_manager
  api_prefix: /api/v1/
  config_files: snake_case.yaml
  python_modules: snake_case
  classes: PascalCase
  constants: SCREAMING_SNAKE_CASE
```

---

## Technical Specifications

### Performance Requirements

| Metric | Target | Current |
|--------|--------|---------|
| Episodes processed/hour | 100+ | ~150 |
| API response time | < 500ms | ~100ms |
| Memory usage | < 500MB | ~200MB |
| Database size | < 1GB | ~50MB |

### Reliability Requirements

- **Uptime**: 95%+ (homelab acceptable)
- **Data durability**: File-based, easy backup
- **Recovery**: < 5 min from restart
- **Graceful shutdown**: Handle SIGTERM

### Security Requirements

- API key authentication (optional)
- Localhost binding by default
- No secrets in code
- `.env` for configuration

---

## Infrastructure

### Current Deployment

```
Homelab (Ubuntu)
├── Atlas Processor (systemd service)
├── Atlas API (port 7444)
├── SQLite database
└── File storage (markdown/, html/, metadata/)
```

### Deployment Commands

```bash
# Development
make run      # Start processor
make api      # Start API
make status   # Check health

# Production (systemd)
sudo systemctl start atlas-manager
sudo systemctl status atlas-manager
```

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-06 | Initial PRD (retrofit from existing system) |
| 1.1 | 2025-12-10 | Updated with completed features, current stats |

---

## Approval

**PRD Status**: Approved - Production

This PRD documents Atlas as it exists today. Future changes requiring PRD updates:
- Storage tier upgrade (SQLite → PostgreSQL)
- Enable Atlas Ask (after ingestion stabilizes)
- New major feature (P2 items)

---

*ONE_SHOT v4.0 enabled. 22 skills available.*
