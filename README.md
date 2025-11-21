# Atlas - Podcast Transcript Discovery System

**Atlas discovers and processes podcast transcripts from 73 curated podcasts (2,373 episodes).**

## 🚀 Quick Start

**Check Status Anytime:**
```bash
./atlas_status.sh
```

**Start Processing:**
```bash
./start_atlas.sh
```

---

## 📊 System Status

**Current Progress:** 750 transcripts found (31% of 2,373 episodes)

**To check real-time status:** Run `./atlas_status.sh` for:
- ✅ Processing status and uptime
- 📊 Transcript discovery progress
- ⚡ Recent activity (5 min window)
- 🌐 External API issues
- 🚀 Quick commands

---

## 🎯 What Atlas Does

1. **Discovers podcast transcripts** from defined sources per podcast
2. **Processes content** through quality assurance pipeline
3. **Stores results** in searchable database
4. **Continues processing** until target transcripts per podcast reached

### Transcript Sources (Per Podcast)
- **First-party sites** (99% Invisible, Acquired, etc.)
- **Third-party aggregators** (Podscribe, HappyScribe, etc.)
- **RSS feeds** (working reliably)
- **Direct crawling** (when defined source available)

---

## 🛡️ Status Check Command

**Atlas provides a single command to check system health:**

```bash
./atlas_status.sh
```

**This shows:**
- 🔥 Process status and runtime
- 📊 Current transcript counts
- ⏳ Episodes pending/processing/completed
- ⚡ Recent activity (last 5 minutes)
- 🌐 External API issues
- 📊 Overall progress percentage

**Example output:**
```
🎯 ATLAS PODCAST PROCESSING STATUS
==================================
📅 2025-11-21 13:34:29

🔥 PROCESS STATUS:
  ✅ Atlas Manager: RUNNING (PID: 130330, Uptime: 01:50:15)

📊 TRANSCRIPT DISCOVERY:
  📈 Total Episodes: 2373
  ✅ Completed: 746
  🎯 Transcripts Found: 750
  ⏳ Pending: 1472
  📊 Progress: 31% (transcripts found)
```

---

## 🔧 Architecture

**System Components:**
- `atlas_manager.py` - Main processing loop
- `data/databases/` - SQLite databases for episode tracking
- `config/` - Transcript source mappings per podcast
- `processors/` - Content discovery and extraction modules
- `logs/` - Real-time processing logs

**Processing Strategy:**
1. Uses defined transcript sources per podcast
2. Falls back to multiple discovery methods
3. Stores all results for quality analysis
4. Continues processing until targets reached

---

## 📝 Quick Reference

| Command | Purpose |
|---------|---------|
| `./atlas_status.sh` | **Check system status** |
| `./start_atlas.sh` | Start Atlas processing |
| `tail -f logs/atlas_manager.log` | View live processing logs |
| `sqlite3 data/databases/atlas_content_before_reorg.db "SELECT COUNT(*) FROM episodes WHERE transcript_found = 1;"` | Quick transcript count |

---

## 🎯 Target

**Goal:** Discover transcripts for all defined episodes across 73 curated podcasts
**Method:** Direct crawling of defined transcript sources per podcast
**Status:** Active processing with 750 transcripts discovered

---

*For detailed documentation, see `docs/` directory.*