# Plan: Atlas Codebase Rationalization

**Created**: 2025-12-23
**Status**: Draft
**Ticket**: N/A (Technical Debt Cleanup)

## Summary

With the content archive 95%+ complete (6,512/6,825 podcast transcripts, 28k articles), the Atlas codebase has accumulated significant technical debt from rapid iteration. This plan identifies and prioritizes cleanup of dead code, duplicate systems, and unnecessary complexity.

## Problem Statement

The codebase grew organically with multiple competing approaches:
- **18 podcast resolvers** but only 11 are actively used
- **146 archived scripts** (42k LOC) alongside 21 active scripts
- **Two transcript discovery systems** (podcasts/ vs transcript_discovery/)
- **Three quality verification systems** with overlapping functionality
- **CLAUDE.md references scripts that are in archive** (documentation drift)

This complexity makes the codebase harder to maintain and understand.

## Goals

- [ ] Remove ~60k lines of dead/duplicate code
- [ ] Consolidate overlapping systems into single implementations
- [ ] Fix CLAUDE.md documentation drift
- [ ] Reduce cognitive load for future development
- [ ] Maintain all production functionality

## Non-Goals

- Adding new features
- Changing the core architecture
- Modifying the data model
- Breaking existing systemd timers

---

## Decisions Needed

> **USER ACTION REQUIRED**: Answer these questions before implementation

| # | Question | Options | Decision | Rationale |
|---|----------|---------|----------|-----------|
| 1 | What to do with `modules/transcript_discovery/` (16 files, 0 usage)? | A) Delete entirely, B) Move to `_archive/modules/`, C) Keep but mark deprecated | _pending_ | Contains hardcoded API keys |
| 2 | What to do with `modules/content_extraction/` (3 files, 0 usage)? | A) Delete entirely, B) Move to `_archive/modules/` | _pending_ | Superseded by quality module |
| 3 | Should we delete `scripts/_archive/` entirely? | A) Delete all 146 files, B) Keep for reference, C) Move to separate repo | _pending_ | 42k LOC, well-organized |
| 4 | What to do with unused resolvers (`google_search.py`, `smart_discovery.py`)? | A) Delete, B) Move to archive | _pending_ | 1,086 lines combined |
| 5 | Should we consolidate the 3 quality systems? | A) Merge into `modules/quality/`, B) Keep separate | _pending_ | Overlapping functionality |

---

## Technical Approach

### Architecture (Current State)

```
ACTIVE (Keep)                    DEAD/DUPLICATE (Remove)
─────────────────────────────    ─────────────────────────────
modules/podcasts/        28 files │ modules/transcript_discovery/ 16 files
modules/ingest/           7 files │ modules/content_extraction/    3 files
modules/storage/          6 files │ modules/analysis/              1 file
modules/pipeline/         4 files │ modules/wormhole/              2 files
modules/quality/          2 files │
modules/enrich/           8 files │ scripts/_archive/            146 files
modules/links/            7 files │ resolvers/google_search.py     1 file
modules/ask/              9 files │ resolvers/smart_discovery.py   1 file
modules/status/           3 files │
modules/browser/          2 files │
modules/notifications/    2 files │
                                  │
scripts/ (active)        21 files │
                                  │
TOTAL ACTIVE: ~100 files         │ TOTAL DEAD: ~170 files (~60k LOC)
```

### Key Findings

#### 1. Dead Modules (19 files, ~8k LOC)

| Module | Files | Lines | Why Dead |
|--------|-------|-------|----------|
| `transcript_discovery/` | 16 | ~6k | Zero imports in production code. Superseded by `podcasts/resolvers/`. Contains hardcoded API keys (security risk). |
| `content_extraction/` | 3 | ~1.5k | Zero imports. Superseded by `modules/quality/verifier.py`. |
| `analysis/` | 1 | ~500 | Zero imports. Unused analytics module. |
| `wormhole/` | 2 | ~300 | Only self-imports. Magic Wormhole integration never used. |

#### 2. Dead/Unused Resolvers (2 files, 1,086 LOC)

| Resolver | Lines | Why Dead |
|----------|-------|----------|
| `google_search.py` | 508 | Not imported in CLI or orchestrator. Legacy from older system. |
| `smart_discovery.py` | 578 | Experimental pattern learning. Never integrated. |

#### 3. Archived Scripts (146 files, 41,909 LOC)

Well-organized in `scripts/_archive/` but some are still referenced in CLAUDE.md:

| Script | CLAUDE.md Status | Action Needed |
|--------|------------------|---------------|
| `validate_podcast_sources.py` | Referenced | Restore to main |
| `analyze_link_queue.py` | Referenced | Restore to main |
| `analyze_ads.py` | Referenced | Restore to main |
| `enrich_improve_loop.py` | Referenced | Restore to main |
| `recover_marginal_tiered.py` | Referenced | Restore to main |
| `stratechery_crawler.py` | Referenced | Restore to main |
| `retry_failed_urls.py` | Referenced | Restore to main |
| `fix_episode_urls.py` | Referenced | Restore to main |
| `parallel_youtube_worker.py` | Referenced | Evaluate if needed |
| Other 137 scripts | Not referenced | Safe to delete |

#### 4. Overlapping Quality Systems

Three systems doing similar things:

| System | Location | Purpose | Status |
|--------|----------|---------|--------|
| **Quality Verifier** | `modules/quality/verifier.py` | File size, word count, paywall patterns | **PRIMARY** |
| **Content Validator** | `modules/pipeline/content_validator.py` | Stub detection, JS-blocked retry | **COMPLEMENTARY** |
| **Atlas Content Validator** | `modules/content_extraction/atlas_content_validator.py` | Old quality scoring (1-10 scale) | **OBSOLETE** |

Recommendation: Keep first two (they're complementary), delete third.

#### 5. Resolver Consolidation

Current CLI resolver chain (11 active):
```python
ACTIVE = [
    'rss_link',           # Priority 1: Direct RSS links
    'nyt',                # Priority 2: NYT official
    'network_transcripts', # Priority 3: NPR, Slate, WNYC
    'podscripts',         # Priority 4: AI transcripts
    'podscribe',          # Priority 5: AI transcripts
    'happyscribe',        # Priority 6: AI transcripts
    'tapesearch',         # Priority 7: AI transcripts
    'generic_html',       # Priority 8: Website scraping
    'playwright',         # Priority 9: JS rendering
    'youtube_transcript', # Priority 10: Auto-captions
    'pattern'             # Priority 11: URL patterns
]

UNUSED = [
    'google_search',      # DELETE: Never integrated
    'smart_discovery',    # DELETE: Experimental only
]

BULK_CRAWLERS = [        # Used by orchestrator, not CLI
    'bulk_crawler',
    'npr_crawler',
    'podscripts_crawler',
    'headless_crawler',
]
```

---

## Implementation Steps

### Phase 1: Fix Documentation Drift (Low Risk)

Restore scripts referenced in CLAUDE.md from archive:

- [ ] `mv scripts/_archive/validate_podcast_sources.py scripts/`
- [ ] `mv scripts/_archive/analyze_link_queue.py scripts/`
- [ ] `mv scripts/_archive/analyze_ads.py scripts/`
- [ ] `mv scripts/_archive/enrich_improve_loop.py scripts/`
- [ ] `mv scripts/_archive/recover_marginal_tiered.py scripts/`
- [ ] `mv scripts/_archive/stratechery_crawler.py scripts/`
- [ ] `mv scripts/_archive/retry_failed_urls.py scripts/`
- [ ] `mv scripts/_archive/fix_episode_urls.py scripts/`
- [ ] Verify each script still works after restore
- [ ] Update any imports if module paths changed

### Phase 2: Remove Dead Modules (Medium Risk)

- [ ] Delete `modules/transcript_discovery/` (16 files)
  - First: Grep for any imports across codebase
  - Remove hardcoded API keys before deletion (security)
- [ ] Delete `modules/content_extraction/` (3 files)
  - First: Verify quality module covers all functionality
- [ ] Delete `modules/analysis/` (1 file)
- [ ] Delete `modules/wormhole/` (2 files)
- [ ] Update `modules/__init__.py` if it imports deleted modules

### Phase 3: Remove Unused Resolvers (Low Risk)

- [ ] Delete `modules/podcasts/resolvers/google_search.py`
- [ ] Delete `modules/podcasts/resolvers/smart_discovery.py`
- [ ] Update `resolvers/__init__.py` to not reference them

### Phase 4: Archive Cleanup (Pending Decision)

Based on decision #3:

**Option A: Delete all archived scripts**
- [ ] `rm -rf scripts/_archive/`
- [ ] Remove 41,909 lines of code

**Option B: Keep for reference**
- [ ] Create `scripts/_archive/README.md` documenting contents
- [ ] No code changes

**Option C: Move to separate repo**
- [ ] Create `atlas-archive` repo
- [ ] Move `scripts/_archive/` there
- [ ] Add submodule reference if needed

### Phase 5: Consolidate Quality Systems (Medium Risk)

- [ ] Review `modules/pipeline/content_validator.py` for unique functionality
- [ ] Merge any unique checks into `modules/quality/verifier.py`
- [ ] Update imports across codebase
- [ ] Delete redundant file if fully merged

### Phase 6: Documentation Update (Low Risk)

- [ ] Update CLAUDE.md to reflect new structure
- [ ] Create `modules/README.md` documenting active vs deprecated
- [ ] Create `scripts/README.md` listing active scripts and their timers
- [ ] Remove documentation of deleted functionality

---

## Testing Strategy

- **Before each deletion**: Grep entire codebase for imports
- **After Phase 1**: Run `./venv/bin/pytest tests/ -v`
- **After Phase 2**: Run all systemd timers manually, verify no import errors
- **After Phase 3**: Test podcast fetch pipeline end-to-end
- **Final**: Run `./venv/bin/python scripts/atlas_status.py` to verify system health

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Delete module that's actually used | Low | High | Grep for imports before every deletion |
| Break systemd timer | Medium | Medium | Test each timer after changes |
| Lose useful archived script | Low | Low | Git history preserves everything |
| Documentation becomes stale | Medium | Low | Update docs in same PR as code changes |

---

## Dependencies

- Git for version control (rollback if needed)
- All systemd timers should be stopped during deletion phases
- No active fetching during changes

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Total Python files in modules/ | ~100 | ~78 (-22) |
| Total Python files in scripts/ | 167 | ~30 (-137) |
| Lines of code (modules/) | ~25k | ~20k |
| Lines of code (scripts/) | ~48k | ~7k |
| CLAUDE.md accuracy | ~85% | 100% |
| pytest pass rate | 100% | 100% |

---

## Summary by Phase

| Phase | Files Affected | LOC Removed | Risk | Time |
|-------|----------------|-------------|------|------|
| 1. Fix Doc Drift | 9 scripts moved | 0 | Low | 30 min |
| 2. Dead Modules | 22 files deleted | ~8k | Medium | 1 hour |
| 3. Unused Resolvers | 2 files deleted | ~1k | Low | 15 min |
| 4. Archive Cleanup | 146 files (pending) | ~42k | Low | 30 min |
| 5. Quality Consolidation | 1-2 files | ~500 | Medium | 1 hour |
| 6. Documentation | 3 files updated | 0 | Low | 30 min |
| **TOTAL** | ~180 files | **~51k LOC** | | ~4 hours |

---

## Revision History

| Date | Author | Changes |
|------|--------|---------|
| 2025-12-23 | Claude Code | Initial draft based on deep exploration |

---

## Appendix: Full File Lists

### A. Dead Modules to Delete

```
modules/transcript_discovery/
├── __init__.py
├── api_transcript_finder.py      # SECURITY: Contains hardcoded API keys!
├── archive_org_scraper.py
├── community_scraper.py
├── crawl4ai_podcast_scraper.py
├── podcast_transcript_scraper.py
├── tapesearch_transcript_finder.py  # Duplicate of resolvers/tapesearch.py
├── transcript_fetchers.py
├── transcript_scrapers.py
├── ultimate_podcast_transcript_scraper.py
├── youtube_caption_scraper.py
└── ... (16 files total)

modules/content_extraction/
├── __init__.py
├── atlas_content_validator.py    # Superseded by modules/quality/
└── transcript_quality.py         # Superseded by modules/quality/

modules/analysis/
└── atlas_analytics.py            # Zero usage

modules/wormhole/
├── __init__.py
└── receiver.py                   # Zero usage
```

### B. Scripts to Restore from Archive

```
scripts/_archive/ → scripts/
├── validate_podcast_sources.py   # Referenced in CLAUDE.md
├── analyze_link_queue.py         # Referenced in CLAUDE.md
├── analyze_ads.py                # Referenced in CLAUDE.md
├── enrich_improve_loop.py        # Referenced in CLAUDE.md
├── recover_marginal_tiered.py    # Referenced in CLAUDE.md
├── stratechery_crawler.py        # Referenced in CLAUDE.md
├── retry_failed_urls.py          # Referenced in CLAUDE.md
└── fix_episode_urls.py           # Referenced in CLAUDE.md
```

### C. Resolvers to Delete

```
modules/podcasts/resolvers/
├── google_search.py              # 508 lines, unused
└── smart_discovery.py            # 578 lines, experimental only
```
