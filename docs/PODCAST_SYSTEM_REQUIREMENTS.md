# Atlas Podcast System Requirements

**Date:** September 5, 2025
**Source:** User specifications and analysis

## 📋 Podcast Requirements Summary

**Total Podcasts:** 37 prioritized (from 72 total available)
**Current Status:** 39 episodes in database, 0 transcriptions
**Processing Approach:** Selective based on user flags and requirements

## 🎯 Podcast Categories and Processing Rules

### Archive-Worthy Podcasts (Transcript_Only=0)
**Download audio + generate transcripts:**
- Accidental Tech Podcast (10 episodes) ✅ **COMPLETE**
- ACQ2 by Acquired (1000 episodes)
- Acquired (1000 episodes)
- 99% Invisible (10 episodes)
- Radiolab (100 episodes)
- This American Life (100 episodes)

### Transcript-Only Podcasts (Transcript_Only=1)
**Find transcripts elsewhere first, download audio only if transcript unavailable:**
- Political Gabfest (4 episodes)
- The NPR Politics Podcast (2 episodes)
- Today, Explained (1 episode)
- The Cognitive Revolution (1 episode)
- Against the Rules with Michael Lewis (100 episodes)
- Decoder with Nilay Patel (2 episodes)
- Greatest Of All Talk (2 episodes)
- Plain English with Derek Thompson (20 episodes)
- Practical AI (2 episodes)
- Sharp Tech with Ben Thompson (1000 episodes)
- Stratechery (1000 episodes)
- The Trojan Horse Affair (100 episodes)
- The Vergecast (5 episodes)
- Planet Money (100 episodes)
- Slate Money (5 episodes)
- Slate Culture (10 episodes)
- The Prestige TV Podcast (10 episodes)
- The Rewatchables (100 episodes)
- Recipe Club (5 episodes)
- The Recipe with Kenji and Deb (100 episodes)
- Conversations with Tyler (100 episodes)
- EconTalk (10 episodes)
- Hard Fork (100 episodes)
- Lex Fridman Podcast (100 episodes)
- The Ezra Klein Show (100 episodes)
- The Journal. (10 episodes)
- The Knowledge Project with Shane Parrish (100 episodes)

### Future-Only Podcasts (Count=0)
**Only process new episodes going forward:**
- The Indicator from Planet Money
- Ringer Food
- Planet Money (duplicate entry)
- Radiolab (duplicate entry)

## 🔧 Processing Requirements

### Content Acquisition Strategy:
1. **Check user prioritization** - Only process 37 specified podcasts
2. **Respect episode counts** - Download exactly specified number OR all available if fewer exist
3. **Transcript-first approach** - For transcript-only shows, search for existing transcripts before audio download
4. **Archive management** - Only download audio for shows marked for archival

### Technical Processing:
- **Mac Mini Processing** - All transcription happens locally
- **Universal Queue** - Single processing system, no competing parallel processes
- **whisper.cpp Integration** - Fast local transcription
- **Database Storage** - All content stored in Atlas SQLite database
- **Search Integration** - Transcripts indexed for semantic search

### Quality Requirements:
- **Exact Episode Counts** - Respect user-specified numbers per podcast
- **No Unnecessary Downloads** - Don't download audio for transcript-only shows if transcript available
- **Resource Efficiency** - Use universal queue to prevent resource conflicts
- **User Prioritization** - Follow user specifications, not AI recommendations

## 📊 Current Gap Analysis

**Major Missing Content:**
- **Acquired ecosystem**: 0/2000 episodes (Acquired + ACQ2)
- **High-value interviews**: 0/700 episodes (Lex Fridman, Ezra Klein, etc.)
- **Tech analysis**: 0/2000 episodes (Stratechery, Sharp Tech)
- **Business education**: 0/300 episodes (Planet Money, EconTalk, etc.)

**Existing Content:**
- **ATP**: 10/10 episodes ✅ **COMPLETE**
- **Other podcasts**: 29 miscellaneous episodes needing classification

## 🎯 Implementation Priorities

### High Priority (Immediate):
1. **Fix Search API** - Enable content searchability
2. **Build Transcription Pipeline** - Mac Mini integration with universal queue
3. **Content Acquisition** - Begin downloading priority shows (Acquired, Lex Fridman, etc.)

### Medium Priority:
4. **Search UI** - Web interface for transcript exploration
5. **Progress Dashboard** - Track acquisition and processing status

### Integration Requirements:
- **PODEMOS Coordination** - Some podcasts may be processed by both systems
- **Resource Sharing** - Universal queue prevents conflicts
- **Configuration Management** - Single .env file for all settings

---

**Note:** This represents the authoritative podcast system requirements based on user specifications in `config/podcasts_prioritized.csv`. All development should follow these exact requirements without modification.