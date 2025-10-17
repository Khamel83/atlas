# Podcast Transcript Discovery Scaling

**Date**: August 17, 2025
**Status**: 🎯 PLANNED
**Priority**: HIGH - Content Scaling

## Executive Summary

Current podcast transcript discovery has a **0.7% success rate** (221 transcripts from 31,000+ episodes). We have **13 podcasts with existing transcripts** including high-value shows like Lex Fridman, This American Life, and Acquired. Need to scale discovery by learning from successful sources and checking for more episodes.

## Current Status Analysis

### ✅ What We Have
- **31,023 episodes** discovered across 73 podcasts
- **221 transcripts found** (0.7% success rate - TERRIBLE)
- **13 podcasts with existing transcripts** (high-quality sources)
- **Working discovery framework** with HTML parsing and pattern detection

### 🚨 The Problem
- **Only checking episode pages themselves** - missing external transcript sources
- **Not learning from successful sources** - each transcript source could have hundreds more episodes
- **No systematic exploration** of known transcript providers (Rev, Otter, fan sites)

### 📊 High-Value Target Podcasts
- **Lex Fridman Podcast** - 91 transcripts found, likely hundreds more available
- **This American Life** - 10 transcripts found, massive archive exists
- **Acquired** - Business podcast with detailed transcripts
- **Conversations with Tyler** - Academic interviews, likely full transcripts
- **The Ezra Klein Show** - NYTimes podcast, likely has transcript archive

## Implementation Strategy

### Phase 1: Simple Source Discovery (Week 1)
**Objective**: Check existing transcript sources for more episodes

**Tasks**:
1. **Fix and optimize simple discovery script** (2-3 hours)
   - Add proper rate limiting and error handling
   - Focus on 13 podcasts with existing transcripts
   - Extract source patterns from successful finds

2. **Manual validation on top podcast** (1 hour)
   - Test on Lex Fridman to validate approach
   - Check if we can find more from same sources
   - Document successful patterns

3. **Batch processing setup** (1-2 hours)
   - Run discovery on all 13 podcasts with transcripts
   - Save results and patterns for reuse
   - Schedule weekly runs

### Phase 2: Pattern Learning (Week 2)
**Objective**: Learn from successful sources and apply patterns

**Tasks**:
1. **Pattern extraction** (3-4 hours)
   - Analyze successful transcript sources by domain
   - Build reusable URL patterns for each source
   - Create source-specific extraction rules

2. **Cross-podcast application** (2-3 hours)
   - Apply successful patterns to similar podcasts
   - Check Rev.com, Otter.ai for other shows
   - Validate pattern success rates

3. **Source database** (1-2 hours)
   - Track which sources work for which podcasts
   - Build confidence scoring for sources
   - Enable incremental discovery

### Phase 3: Automated Scaling (Week 3)
**Objective**: Deploy automated weekly discovery

**Tasks**:
1. **Weekly automation** (2-3 hours)
   - Add to Atlas background service
   - Schedule source checking every Sunday
   - Monitor and report discovery rates

2. **Success rate monitoring** (1-2 hours)
   - Track transcripts found per week
   - Measure improvement from 0.7% baseline
   - Alert when new sources are discovered

3. **Integration with main pipeline** (1-2 hours)
   - Ensure discovered transcripts get processed
   - Add to existing Atlas ingestion workflow
   - Update daily reporting with transcript stats

## Expected Outcomes

### Success Metrics
- **Target**: Increase transcript success rate from 0.7% to 5%+
- **Baseline**: 221 transcripts → **Target**: 1,500+ transcripts
- **Focus**: High-value podcasts (Lex Fridman could go from 91 to 400+ transcripts)

### Key Sources to Explore
- **Rev.com** - Professional transcription service
- **Otter.ai** - AI transcription platform
- **Fan transcript sites** - Reddit, Medium, Substack posts
- **Podcast websites** - Many hosts publish their own transcripts
- **News organization podcasts** - NYTimes, NPR likely have archives

### Implementation Complexity
- **Simple** - Only 13 podcasts to start with
- **Proven** - We already found transcripts, just need to find more from same sources
- **Incremental** - Can test on one podcast before scaling
- **Weekly runs** - Not constant processing, just periodic discovery

## Technical Architecture

### Core Components
1. **Simple Discovery Script** (`scripts/simple_transcript_discovery.py`)
   - Focus on known successful podcasts
   - Extract and generalize source patterns
   - Rate-limited source checking

2. **Pattern Database** (`data/podcasts/transcript_patterns.json`)
   - Store successful URL patterns by podcast
   - Track source reliability and success rates
   - Enable pattern reuse across similar podcasts

3. **Weekly Scheduler** (Integration with Atlas background service)
   - Run discovery every Sunday
   - Process results and update database
   - Generate reports on discovery success

### Database Schema Enhancement
```sql
-- Add transcript source tracking
ALTER TABLE episodes ADD COLUMN transcript_source TEXT;
ALTER TABLE episodes ADD COLUMN transcript_confidence REAL DEFAULT 0.0;

-- Track discovery patterns
CREATE TABLE transcript_patterns (
    id INTEGER PRIMARY KEY,
    podcast_id INTEGER,
    source_domain TEXT,
    url_pattern TEXT,
    success_count INTEGER DEFAULT 0,
    last_success TIMESTAMP
);
```

## Risk Assessment

### Low Risk
- **Proven approach** - We already found 221 transcripts successfully
- **Limited scope** - Only 13 podcasts to start with
- **Incremental** - Can validate before scaling

### Medium Risk
- **Rate limiting** - Need to be respectful to transcript sources
- **Pattern changes** - Sources might change URL structures
- **Quality variation** - Not all sources have consistent quality

### Mitigation Strategies
- **Rate limiting** - 2-5 second delays between requests
- **Source validation** - Check content quality before storing
- **Pattern flexibility** - Support multiple URL patterns per source
- **Graceful degradation** - Continue with current discovery if new methods fail

## Next Actions

### Immediate (This Week)
1. **Test current script** on Lex Fridman podcast
2. **Optimize for speed** and add proper error handling
3. **Run on all 13 podcasts** with existing transcripts

### Short Term (Next 2 Weeks)
1. **Extract successful patterns** from discovery results
2. **Apply patterns** to similar podcasts without transcripts
3. **Schedule weekly runs** in background service

### Long Term (Month)
1. **Monitor success rates** and optimize patterns
2. **Expand to more podcast sources** as patterns prove successful
3. **Consider premium transcript services** if ROI is good

---

**Expected Impact**: 5-10x increase in transcript discovery rate, focusing on high-value content that's already proven to have transcripts available.

*This is a high-value, low-risk improvement that scales our existing successful discovery methods.*