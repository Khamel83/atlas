# ONE_SHOT Retrofit Runbook for Atlas

**Date:** 2025-12-04
**Objective:** Apply ONE_SHOT principles to existing Atlas codebase (§5.5 progressive adoption)

## Principles
- Do NOT rewrite from scratch; this is a retrofit
- Focus on observability, docs, scripts, and structure
- Don't touch core business logic unless necessary
- Prefer documentation + scripts over clever refactors
- Keep changes small, explicit, and testable

## Task Checklist

### 1. processors/ cleanup + documentation
- [x] Identify active vs deprecated processors
- [x] Create processors/README.md with architecture overview
- [x] Move dead/experimental processors to processors/archive/ (63 files archived)
- [x] Do NOT change logic of active processors

### 2. Root-level dependency manifest
- [x] Create requirements.txt at repo root
- [x] Pull from existing requirements files
- [x] Update README.md with Quick Start instructions

### 3. Data and DB hygiene (.gitignore)
- [x] Add *.db, *.sqlite to .gitignore
- [x] Decide on html/, markdown/, metadata/ directories (excluded as runtime)
- [x] Create docs/SETUP.md explaining data layout

### 4. Makefile for common tasks
- [x] Create root Makefile with: setup, test, run, status, api, clean, deploy
- [x] Update README.md to reference Makefile targets

### 5. Env templates and secrets
- [x] Consolidate to single .env.template (removed .env.example)
- [x] Remove real credentials
- [x] Create docs/CONFIGURATION.md

### 6. Current architecture doc
- [x] Create docs/CURRENT_ARCHITECTURE.md
- [x] Document active processor, components, databases
- [x] Explain startup mechanisms

### 7. Migration docs
- [x] Move migration docs to docs/migrations/ (5 files moved)
- [x] Link from docs/RUNBOOK.md

### 8. Basic CI skeleton
- [x] Create .github/workflows/test.yml
- [x] Create docs/TESTING.md

## Execution Log

Started: 2025-12-04
Completed: 2025-12-04

### Summary of Changes

**Files Created (10)**:
- `requirements.txt` - Consolidated dependencies
- `Makefile` - Common tasks automation
- `.env.template` - Unified environment template
- `docs/SETUP.md` - Setup guide
- `docs/CONFIGURATION.md` - Configuration reference
- `docs/CURRENT_ARCHITECTURE.md` - Architecture documentation
- `docs/RUNBOOK.md` - Operations runbook
- `docs/TESTING.md` - Testing guide
- `processors/README.md` - Processor documentation
- `.github/workflows/test.yml` - CI pipeline

**Files Modified (3)**:
- `.gitignore` - Added runtime data exclusions
- `README.md` - Added Makefile references and documentation links
- `docs/RUNBOOK_ONESHOT_RETROFIT.md` - This file

**Files Archived (63)**:
- Moved to `processors/archive/experimental/` (8 files)
- Moved to `processors/archive/test/` (55 files)

**Files Moved to docs/migrations/ (5)**:
- `MIGRATION_REPORT.md`
- `ATLAS_CONTENT_PROCESSING_STATUS.md`
- `ATLAS_CONTENT_INGESTION_PLAN.md`
- `MAC_ARCHIVE_TRANSFER_PLAN.md`
- `QUICK_MAC_TRANSFER_COMMANDS.md`

**Files Removed (1)**:
- `.env.example` - Consolidated into `.env.template`

### Metrics

- **Processors cleaned**: 210 → 147 active (63 archived)
- **Documentation added**: 10 new files
- **Project structure**: Clearer, more navigable
- **Automation**: Makefile with 10+ targets

### Outstanding TODOs

See individual documentation files for specific TODOs:
- Verify active processor (atlas_manager.py confirmed, others need verification)
- Document complete database schema
- Further processor consolidation possible (147 → ~20 core files)
- Update systemd services for current paths
- Measure test coverage

