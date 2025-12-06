# Atlas - Product Requirements Document

**Version**: 1.0
**Created**: 2025-12-06
**ONE_SHOT Version**: 3.0
**Status**: Approved (existing system retrofit)

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

**Problem**: Podcast transcripts exist but are fragmented across dozens of sources (official sites, Podscribe, Rev.com, HappyScribe, RSS feeds, etc.). Manually finding and organizing them is:
- Time-consuming (hours per podcast)
- Error-prone (missing episodes, duplicates)
- Unsustainable (new episodes constantly added)

**Solution**: Atlas automates the entire workflow:
1. Tracks 73 curated podcasts (2,373 episodes)
2. Discovers transcript sources automatically
3. Downloads and processes content
4. Stores in searchable, file-based format
5. Runs continuously without intervention

### Q2.5: Reality Check

**Is this being used?** Yes - actively processing transcripts daily.
**Evidence**: 750 transcripts found (31% completion), continuous processor running.

### Q3: Philosophy / Constraints

1. **File-first storage**: Content in files, database for tracking only
2. **$0 infrastructure**: Homelab-only, no cloud costs
3. **Graceful degradation**: If one source fails, try others
4. **Non-destructive**: Never delete source content
5. **Respect rate limits**: Be a good citizen to external APIs

### Q4: Features (Prioritized)

#### P0 - Must Have (Done)
- [x] RSS feed parsing for episode discovery
- [x] SQLite episode tracking database
- [x] Multi-strategy transcript discovery
- [x] REST API for external integrations
- [x] Health endpoints (`/health`, `/metrics`)
- [x] Continuous background processing
- [x] TrojanHorse note ingestion

#### P1 - Should Have (Partial)
- [x] Email ingestion (Gmail integration)
- [ ] YouTube transcript extraction (TODO)
- [x] Fallback strategies for failed extractions
- [x] Processing queue with retry logic

#### P2 - Nice to Have (Future)
- [ ] Full-text search UI
- [ ] Podcast recommendation engine
- [ ] Auto-categorization of content
- [ ] Multi-user support

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

v1.0 is **COMPLETE**. Current state:

- [x] Process 70+ podcasts automatically
- [x] Find transcripts from multiple sources
- [x] Store in searchable format
- [x] REST API for integrations
- [x] Health monitoring
- [x] Continuous operation without intervention
- [x] Documentation for operations

**v1.1 targets**:
- [ ] YouTube transcript extraction
- [ ] 50% transcript coverage (currently 31%)
- [ ] Consolidated processor codebase (135 files → ~20)

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

---

## Approval

**PRD Status**: Approved (existing system - documenting current state)

This PRD documents Atlas as it exists today. Future changes requiring PRD updates:
- Storage tier upgrade (SQLite → PostgreSQL)
- New major feature (P2 items)
- Architecture changes

---

*Generated as part of ONE_SHOT v3.0 retrofit*
