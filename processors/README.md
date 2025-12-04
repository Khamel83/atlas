# Atlas Processors

**Status**: 🔄 Architecture Cleanup in Progress
**Last Updated**: 2025-12-04

## Overview

Atlas uses a processor-based architecture for content discovery and ingestion. Processors handle:
- Podcast transcript discovery and extraction
- Content ingestion from various sources (email, web, APIs)
- Continuous processing and monitoring
- Quality validation and retry logic

## Active Processors (Production)

### Core Management
- **`atlas_manager.py`** - Main coordinator using log-stream architecture
  - Referenced by: `scripts/start/start_atlas.sh`, `systemd/atlas-manager.service`
  - Manages continuous processing loop
  - **Status**: ✅ Active (primary coordinator)

### Content Processing
- **`atlas_processor.py`** - Core content processor
  - Handles transcript discovery and validation
  - **Status**: ⏳ Needs verification

- **`atlas_log_processor.py`** - Log-stream based processing (if exists)
  - Imported by `atlas_manager.py`
  - **Status**: ⏳ Needs verification

### Specialized Processors
- **`atlas_continuous_processor.py`** - Continuous operation mode
- **`atlas_email_processor.py`** - Email-based content ingestion
- **`atlas_telegram_monitor.py`** - Telegram integration
- **`atlas_universal_bookmarker.py`** - Universal URL handling

**TODO**: Verify which of these are actually in active use vs. experimental.

## Archived/Deprecated (processors/archive/)

### Experimental Versions
Files moved to `processors/archive/experimental/`:
- `atlas_v2_*.py` - Version 2 experiments
- `atlas_v3*.py` - Version 3 experiments
- `atlas_*_fixed.py` - Patch attempts (replaced by canonical versions)
- `atlas_*_backup.py` - Backup copies (superseded)

### Test/Demo Files
Files moved to `processors/archive/test/`:
- `*_test.py` - Test scripts
- `*_demo.py` - Demo/proof-of-concept scripts
- `*_validation.py` - One-time validation scripts

## Architecture Patterns

### Log-Stream Architecture
Atlas uses a log-stream architecture (as of `atlas_manager.py`):
- Fast file-based operations instead of database locking
- Event-driven processing
- High-performance continuous operation

### Processing Flow
```
1. Content Discovery (RSS, web scraping, APIs)
   ↓
2. Quality Validation (transcript quality checks)
   ↓
3. Storage (file-based + SQLite tracking)
   ↓
4. Monitoring (health checks, status reporting)
```

## Usage

### Start Main Processor
```bash
# Via startup script (recommended)
./scripts/start/start_atlas.sh

# Via systemd (production)
sudo systemctl start atlas-manager

# Direct (development)
python3 processors/atlas_manager.py
```

### Check Status
```bash
./atlas_status.sh
```

## File Organization Rules

**Active files stay in `processors/`**:
- Production-ready processors
- Currently referenced by scripts/services
- Maintained and updated

**Deprecated files go to `processors/archive/`**:
- Experimental versions (`v2`, `v3`, etc.)
- Fixed/backup variants
- Test/demo scripts
- Superseded implementations

## Maintenance Notes

### How to Add a New Processor
1. Create in `processors/` with clear docstring
2. Document purpose in this README
3. Update relevant startup scripts
4. Add health checks and logging
5. Test before deployment

### How to Deprecate a Processor
1. Verify nothing references it (grep codebase)
2. Move to `processors/archive/[category]/`
3. Update this README
4. Update any affected documentation

### Cleanup Guidelines
- Keep only 1 canonical version of each processor
- Archive experiments and prototypes
- Remove unused imports and dead code
- Document "why" for non-obvious decisions

## Known Issues & TODOs

- [ ] Verify which processors are truly active vs. experimental
- [ ] Consolidate duplicate functionality
- [ ] Add health checks to all active processors
- [ ] Document processor dependencies and initialization order
- [ ] Create processor testing framework

## Upgrade Triggers

**Current Tier**: File-based processing with SQLite tracking
**Upgrade Trigger**:
- > 500K episodes OR
- Multi-instance coordination needed OR
- Current architecture hits performance limits

**Next Tier**: PostgreSQL with connection pooling, separate processing workers

---

**For questions about processor architecture, see `docs/CURRENT_ARCHITECTURE.md` (TODO: create)**
