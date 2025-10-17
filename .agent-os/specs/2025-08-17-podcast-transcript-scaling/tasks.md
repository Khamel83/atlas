# Podcast Transcript Scaling - Task Breakdown

## Phase 1: Simple Source Discovery ⏳ IN PROGRESS

### Task 1.1: Fix and Optimize Discovery Script ⏳ ACTIVE
**Status**: IN PROGRESS
**Timeline**: 2-3 hours
**Current State**: Script created but needs optimization for speed and reliability

**Implementation Steps**:
- [x] Create simple discovery script framework
- [x] Fix database schema queries (name vs title)
- [x] Add BeautifulSoup warning suppression
- [ ] Add proper rate limiting (2-5 seconds between requests)
- [ ] Optimize for speed - focus on high-confidence sources first
- [ ] Add detailed logging and progress tracking
- [ ] Test on single high-value podcast (Lex Fridman)

### Task 1.2: Manual Validation on Lex Fridman ⏳ PENDING
**Status**: PENDING
**Timeline**: 1 hour
**Objective**: Validate approach on known successful podcast

**Implementation Steps**:
- [ ] Run discovery script specifically on Lex Fridman podcast
- [ ] Manually verify 2-3 discovered transcript sources
- [ ] Document successful patterns and source types
- [ ] Measure time to find transcripts vs current method
- [ ] Calculate potential scale (if we find 10 more, likely 100+ available)

### Task 1.3: Batch Processing Setup ⏳ PENDING
**Status**: PENDING
**Timeline**: 1-2 hours
**Objective**: Process all 13 podcasts with existing transcripts

**Implementation Steps**:
- [ ] Create batch runner for all 13 podcasts
- [ ] Add results collection and pattern extraction
- [ ] Save successful patterns to reusable database
- [ ] Generate summary report of discoveries
- [ ] Set up weekly scheduling framework

## Phase 2: Pattern Learning 📋 PLANNED

### Task 2.1: Pattern Extraction 📋 PLANNED
**Status**: PLANNED
**Timeline**: 3-4 hours
**Objective**: Learn reusable patterns from successful discoveries

**Implementation Steps**:
- [ ] Analyze successful transcript sources by domain
- [ ] Extract URL patterns (e.g., rev.com/{podcast-slug}/{episode-slug})
- [ ] Create domain-specific extraction rules
- [ ] Build confidence scoring for each pattern
- [ ] Test patterns on episodes we haven't processed yet

### Task 2.2: Cross-Podcast Application 📋 PLANNED
**Status**: PLANNED
**Timeline**: 2-3 hours
**Objective**: Apply successful patterns to similar podcasts

**Implementation Steps**:
- [ ] Identify podcasts similar to successful ones
- [ ] Apply proven patterns to new podcasts
- [ ] Validate pattern success rates across podcasts
- [ ] Document which patterns work for which podcast types
- [ ] Build recommendation engine for new podcasts

### Task 2.3: Source Database Creation 📋 PLANNED
**Status**: PLANNED
**Timeline**: 1-2 hours
**Objective**: Create persistent storage for successful patterns

**Implementation Steps**:
- [ ] Design transcript_patterns table schema
- [ ] Create pattern storage and retrieval system
- [ ] Add confidence tracking and success rate monitoring
- [ ] Enable incremental pattern learning
- [ ] Add pattern expiry for outdated sources

## Phase 3: Automated Scaling 📋 PLANNED

### Task 3.1: Weekly Automation 📋 PLANNED
**Status**: PLANNED
**Timeline**: 2-3 hours
**Objective**: Deploy automated weekly discovery

**Implementation Steps**:
- [ ] Integrate with Atlas background service
- [ ] Schedule discovery runs every Sunday morning
- [ ] Add discovery to daily reporting system
- [ ] Monitor and alert on discovery failures
- [ ] Track weekly discovery metrics

### Task 3.2: Success Rate Monitoring 📋 PLANNED
**Status**: PLANNED
**Timeline**: 1-2 hours
**Objective**: Track improvement and optimize

**Implementation Steps**:
- [ ] Add transcript discovery metrics to daily reports
- [ ] Track success rate improvement from 0.7% baseline
- [ ] Alert when new high-value sources are found
- [ ] Generate weekly discovery summary reports
- [ ] Monitor source reliability over time

### Task 3.3: Main Pipeline Integration 📋 PLANNED
**Status**: PLANNED
**Timeline**: 1-2 hours
**Objective**: Ensure discovered transcripts get processed

**Implementation Steps**:
- [ ] Add discovered transcripts to main ingestion queue
- [ ] Update podcast transcript processing workflow
- [ ] Ensure new transcripts appear in Atlas search
- [ ] Add transcript source attribution in metadata
- [ ] Update CLAUDE.md with new transcript numbers

## Current Data Summary

### Target Podcasts (13 with existing transcripts)
1. **Lex Fridman Podcast** - 91 transcripts (HIGH PRIORITY)
2. **This American Life** - 10 transcripts (NPR archive potential)
3. **Acquired** - Business podcast with detailed show notes
4. **Conversations with Tyler** - Academic interviews
5. **The Ezra Klein Show** - NYTimes podcast
6. **Dwarkesh Podcast** - Technical interviews
7. **Lenny's Podcast** - Product/growth content
8. **Odd Lots** - Financial journalism
9. **The Knowledge Project** - Shane Parrish interviews
10. **The NPR Politics Podcast** - News transcripts
11. **The Indicator from Planet Money** - Economic stories
12. **Accidental Tech Podcast** - Tech discussion
13. **ACQ2 by Acquired** - Acquired spinoff

### Success Metrics
- **Current**: 221 transcripts from 31,023 episodes (0.7%)
- **Target Phase 1**: 500+ transcripts (2.3% success rate)
- **Target Phase 2**: 1,000+ transcripts (4.6% success rate)
- **Target Phase 3**: 1,500+ transcripts (6.9% success rate)

### Implementation Complexity: LOW
- **Only 13 podcasts** to start with (not 73)
- **Proven sources** - we already found transcripts from these
- **Weekly runs** - not constant processing
- **Incremental** - can test and validate before scaling

### Expected ROI: HIGH
- **Lex Fridman alone** - could go from 91 to 400+ transcripts
- **NPR shows** - likely have comprehensive archives
- **Business podcasts** - often publish transcripts for SEO
- **Quality content** - these are all high-value shows

## Next Immediate Action

**PRIORITY 1**: Complete Task 1.1 (Fix and optimize discovery script)
- Focus on speed optimization and rate limiting
- Test on Lex Fridman podcast specifically
- Validate we can find additional transcripts from same sources

**Timeline**: Complete Phase 1 this week, then evaluate for Phase 2

---

**Note**: This is a high-value, low-risk scaling opportunity that leverages our existing successful discoveries rather than trying to discover completely new sources.