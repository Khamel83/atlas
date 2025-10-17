# Tasks: Podcast Transcript Bulk Discovery Integration

## Phase 1: Background Service Integration (2 hours)

### Task 1.1: Modify Atlas Background Service
- [ ] Add transcript discovery to weekly schedule in `scripts/atlas_background_service.py`
- [ ] Configure Sunday 2 AM weekly discovery runs
- [ ] Integrate with existing podcast processing cycle
- [ ] Add error handling and retry logic for discovery failures

### Task 1.2: Scale Bulk Discovery Capability
- [ ] Remove 5-10 episode testing limits from `scripts/generic_transcript_discovery.py`
- [ ] Add batch processing for all episodes without transcripts
- [ ] Implement progress tracking for long-running discovery (progress bars, ETA)
- [ ] Add database transaction handling for bulk updates

### Task 1.3: Add Reporting Integration
- [ ] Include transcript discovery stats in `scripts/daily_report.sh`
- [ ] Track success rates by podcast and source domain
- [ ] Add alerts when high-value transcripts are discovered
- [ ] Create weekly transcript growth summary

## Phase 2: Bulk Processing Optimization (1 hour)

### Task 2.1: Lex Fridman Bulk Discovery
- [ ] Process all 387 episodes missing transcripts
- [ ] Use learned `lexfridman.com/{guest-name}-transcript` pattern
- [ ] Implement guest name extraction optimization
- [ ] Track and report discovery yield (target: 50-100 transcripts)

### Task 2.2: This American Life Systematic Check
- [ ] Use `thisamericanlife.org/{episode-number}/transcript` pattern
- [ ] Check all episodes in database against transcript availability
- [ ] Leverage high existing success rate (83%) for bulk discovery
- [ ] Extract episode numbers from titles systematically

### Task 2.3: Cross-Podcast Pattern Application
- [ ] Apply successful patterns from one podcast to similar shows
- [ ] Test Dwarkesh patterns on other interview-style podcasts
- [ ] Expand discovery beyond original source podcasts
- [ ] Document pattern effectiveness across podcast types

## Phase 3: Production Monitoring (1 hour)

### Task 3.1: Success Rate Tracking
- [ ] Monitor discovery rates by podcast and pattern in real-time
- [ ] Identify which patterns work best across different shows
- [ ] Optimize rate limiting based on source response patterns
- [ ] Create pattern effectiveness dashboard

### Task 3.2: Weekly Reporting Enhancement
- [ ] Add transcript discovery section to daily reports
- [ ] Show weekly growth in transcript collection
- [ ] Track success rate improvement over baseline (0.7%)
- [ ] Include top discoveries and new sources found

### Task 3.3: Pattern Learning Automation
- [ ] Automatically learn new patterns from successful discoveries
- [ ] Update pattern database when new transcript sources are found
- [ ] Enable adaptive discovery that improves over time
- [ ] Implement pattern confidence scoring and optimization

## Acceptance Criteria

### Functional Requirements
- [ ] Weekly automated transcript discovery runs without manual intervention
- [ ] Bulk processing handles 100+ episodes per podcast efficiently
- [ ] Success rate improves from 0.7% baseline to 3%+ within first month
- [ ] Daily reports include comprehensive transcript discovery statistics

### Performance Requirements
- [ ] Discovery processing completes within 4-hour window
- [ ] Rate limiting prevents service bans (2-5 second delays)
- [ ] Database updates handle bulk transcript additions efficiently
- [ ] Memory usage remains stable during bulk processing

### Quality Requirements
- [ ] Pattern accuracy verified before bulk processing
- [ ] Graceful error handling for failed discoveries
- [ ] Source website respect through conservative rate limiting
- [ ] Pattern learning improves discovery over time

### Integration Requirements
- [ ] Seamless integration with existing Atlas background service
- [ ] Compatible with current podcast processing workflow
- [ ] Maintains existing database schema and relationships
- [ ] Preserves all existing podcast functionality

## Success Metrics

### Immediate (Week 1)
- [ ] 50+ new transcripts discovered from Lex Fridman backlog
- [ ] 10+ new transcripts from This American Life archive
- [ ] Weekly automation operational and reporting

### Short-term (Month 1)
- [ ] 100+ total new transcripts across all podcasts
- [ ] Success rate improvement to 3%+ demonstrated
- [ ] Pattern learning showing optimization trends

### Long-term (Month 3)
- [ ] 200+ total new transcripts with continued weekly growth
- [ ] Cross-podcast pattern application yielding discoveries
- [ ] Fully automated system requiring minimal maintenance

---

**Total Estimated Time**: 4 hours across 3 phases
**Dependencies**: Generic discovery system (completed), Atlas background service (operational)
**Risk Level**: Low (building on proven components)