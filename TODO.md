# Atlas TODO List (Rationalized)

**Last Updated**: 2025-12-06
**Total Items**: 13 actionable TODOs

---

## Code TODOs (5 items)

### P1 - Should Fix

| File | Line | TODO | Status |
|------|------|------|--------|
| `processors/simple_working_processor.py` | 184 | Add YouTube transcript extraction | Pending |
| `processors/optimized_transcript_discovery.py` | 69 | Replace with actual Google Custom Search API | Pending - has fallback |
| `modules/transcript_discovery/podcast_transcript_scraper.py` | 238 | Add more podcast-specific scrapers | Pending |

### P2 - Nice to Have

| File | Line | TODO | Status |
|------|------|------|--------|
| `scripts/run-bot.py` | 286 | Implement daemon mode | Pending |
| `scripts/podemos_rss_server.py` | 241 | Configure base_url from env | Pending |

---

## Documentation TODOs (8 items)

### P1 - Should Fix

| File | Line | TODO | Status |
|------|------|------|--------|
| `docs/CURRENT_ARCHITECTURE.md` | 71 | Document full database schema | Pending |
| `docs/CURRENT_ARCHITECTURE.md` | 118 | Verify systemd service configuration for current paths | Pending |
| `docs/TESTING.md` | 121 | Measure current test coverage | Pending |
| `processors/README.md` | 37 | Verify which processors are active vs experimental | Pending |

### P2 - Nice to Have

| File | Line | TODO | Status |
|------|------|------|--------|
| `docs/CURRENT_ARCHITECTURE.md` | 198 | Verify /metrics endpoint exists | Pending |
| `docs/RUNBOOK.md` | 260 | Create TROUBLESHOOTING.md | Pending |
| `docs/SETUP.md` | 106 | Link to architecture details | Pending |
| `processors/README.md` | 146 | Create processor architecture doc | Pending |

---

## Completed (Removed from codebase TODOs)

These were implicit TODOs addressed by the ONE_SHOT retrofit:

- [x] Create LLM-OVERVIEW.md for project context
- [x] Create PRD.md for requirements
- [x] Standardize operational scripts (setup/start/stop/status)
- [x] Document current architecture status

---

## Recommended Cleanup

### Remove Unused TODO Infrastructure

The following files comprise 2,717 lines of TODO management code that **is not being used** (no `master_todos.json` exists):

```
scripts/unified_todo_manager.py   # 1,052 lines - unused
scripts/todo_consolidator.py      #   686 lines - unused
scripts/rationalize_todos.py      #   370 lines - unused
scripts/todo_api.py               #   224 lines - unused
scripts/todo_helpers.py           #   385 lines - unused
docs/TODO_MANAGEMENT.md           #   404 lines - documents unused system
```

**Recommendation**: Delete these files and use this simple TODO.md instead.

---

## Next Actions

1. **YouTube transcript extraction** - Biggest impact on transcript coverage
2. **Google Search API integration** - Currently has fallback, not urgent
3. **Document database schema** - Helps future development
4. **Processor consolidation** - 135 files → ~20 core files

---

*This file replaces the 2,717-line unused TODO management system with a simple, maintainable list.*
