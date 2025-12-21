# Atlas Transcript Systems - Path to 100%

## Current State (2025-12-21)
- **4,614 / 6,982 episodes** (66%)
- **2,368 remaining** across 4 distinct pathways

---

## The Four Systems

### 1. ✅ AUTOMATED ONLINE (86% of remaining)
**Episodes:** 1,393 pending
**System:** Systemd timers run every 4 hours
**Resolvers:** Website → NYT → Network → Podscripts → YouTube

| Source | Podcasts | Pending | Timer |
|--------|----------|---------|-------|
| Website Direct | 3 | 707 | atlas-transcripts |
| Network (NPR) | 12 | 102 | atlas-transcripts |
| NYT | 1 | 151 | atlas-transcripts |
| Podscripts | 22 | 433 | atlas-transcripts |

**Action Required:** None - runs automatically
**ETA to Complete:** 1-2 weeks at current rate (50/run × 4hr intervals)

---

### 2. 🎙️ LOCAL WHISPER (30% of remaining)
**Episodes:** 704 pending
**System:** Mac Mini M4 with WhisperX
**Pipeline:** Download → Transcribe → Import

| Stage | Timer | Frequency |
|-------|-------|-----------|
| Download audio | atlas-whisper-download | Every 2 hours |
| Transcribe (Mac) | whisperx_watcher.py | Continuous |
| Import transcripts | atlas-whisper-import | Hourly |

**Action Required:** Keep Mac Mini running
**Bottleneck:** Transcription speed (~20 min/episode)
**ETA:** 2-3 weeks for 704 episodes

**Podcasts in this path:**
- Dithering (97 pending) - paywalled
- Asianometry (90 pending) - paywalled
- The Rewatchables (100 pending) - Ringer network
- Against the Rules (47 pending) - Pushkin network
- + 20 more

---

### 3. ❓ NEEDS INVESTIGATION (3% of remaining)
**Episodes:** 75 pending across 138 podcasts
**Issue:** Missing from mapping.yml or no known source

**Top candidates to fix:**
| Podcast | Pending | Likely Solution |
|---------|---------|-----------------|
| the-recipe-with-kenji-and-deb | 38 | Check podscripts |
| 99-invisible | 10 | Should be 99-percent-invisible |
| bad-bets | 10 | Check podscripts |
| the-trojan-horse-affair | 10 | Serial/NYT - check network |

**Action Required:**
1. Check podscripts.co for coverage
2. Add to mapping.yml with correct resolver
3. Re-run discovery

---

### 4. 🔴 FAILED (edge cases)
**Episodes:** 15 total
**System:** Weekly retry via atlas-content-retry
**Cause:** Temporary failures, rate limits, network issues

**Action Required:** None - auto-retries weekly

---

## System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     TRANSCRIPT INGESTION                         │
└─────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
    ┌──────────┐        ┌──────────┐        ┌──────────┐
    │  ONLINE  │        │  LOCAL   │        │ UNKNOWN  │
    │ SOURCES  │        │ WHISPER  │        │  (FIX)   │
    └────┬─────┘        └────┬─────┘        └────┬─────┘
         │                   │                   │
    ┌────┴────┐         ┌────┴────┐         ┌────┴────┐
    │ Timers  │         │Mac Mini │         │ Manual  │
    │ (auto)  │         │ (auto)  │         │ Config  │
    └────┬────┘         └────┬────┘         └────┬────┘
         │                   │                   │
         ▼                   ▼                   ▼
    ┌─────────────────────────────────────────────────┐
    │              data/podcasts/{slug}/              │
    │                 transcripts/*.md                 │
    └─────────────────────────────────────────────────┘
                              │
                              ▼
    ┌─────────────────────────────────────────────────┐
    │              ENRICHMENT (weekly)                 │
    │         Ad removal → Clean versions             │
    └─────────────────────────────────────────────────┘
```

---

## Decision Tree: New Podcast

```
Is transcript available online?
├── YES: Check source
│   ├── Podcast website → generic_html resolver
│   ├── NPR/Slate/WNYC → network_transcripts resolver
│   ├── NYT → nyt resolver
│   ├── Podscripts.co → podscripts resolver (default)
│   └── YouTube → youtube_transcript resolver
│
└── NO: Is audio accessible?
    ├── YES (public RSS) → Mark as 'local', Whisper pipeline
    └── NO (paywalled) → Download manually, then Whisper
```

---

## Weekly Health Check

Run this to verify all systems working:

```bash
# 1. Overall status
./venv/bin/python scripts/atlas_status.py

# 2. Transcript coverage by pathway
./venv/bin/python scripts/atlas_status.py --podcasts

# 3. Whisper pipeline health
ls -la data/whisper_queue/audio/      # Pending downloads
ls -la data/whisper_queue/transcripts/ # Waiting for import

# 4. Timer status
systemctl list-timers | grep atlas

# 5. Failed episodes (should be <20)
sqlite3 data/podcasts/atlas_podcasts.db \
  "SELECT COUNT(*) FROM episodes WHERE transcript_status='failed'"
```

---

## Path to 100%

| Week | Automated | Whisper | Investigation | Total |
|------|-----------|---------|---------------|-------|
| Now  | 4,362     | 250     | 2             | 4,614 (66%) |
| +1   | 5,100     | 400     | 50            | 5,550 (79%) |
| +2   | 5,500     | 600     | 75            | 6,175 (88%) |
| +3   | 5,755     | 850     | 75            | 6,680 (96%) |
| +4   | 5,819     | 954     | 209           | 6,982 (100%) |

**Key milestones:**
- Week 1: Fix "unknown" podcasts (add to mapping.yml)
- Week 2: Automated should be >90% complete
- Week 3: Whisper backlog cleared
- Week 4: 100% coverage

---

## Appendix: Systemd Timers

| Timer | Purpose | Frequency |
|-------|---------|-----------|
| atlas-podcast-discovery | Find new episodes | 6am/6pm |
| atlas-transcripts | Fetch via online resolvers | Every 4h |
| atlas-whisper-download | Download audio for local | Every 2h |
| atlas-whisper-import | Import Whisper results | Hourly |
| atlas-enrich | Clean ads, generate reports | Weekly |
| atlas-content-retry | Retry failed fetches | Weekly |
