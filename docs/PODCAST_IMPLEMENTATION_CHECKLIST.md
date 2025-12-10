# Podcast Transcript Crawling - Implementation Checklist

## Pre-Implementation Research (COMPLETE)

- [x] Research PodScripts.co availability and coverage
  - 559,673 episodes transcribed
  - 300+ podcasts available
  - Free, no authentication required
  - URL pattern: podscripts.co/podcasts/{slug}

- [x] Research TranscriptForest.com availability
  - 73+ podcasts with full transcripts verified
  - Free public access
  - URL pattern: transcriptforest.com/en/channel/{slug}
  - No authentication required

- [x] Research HappyScribe public library
  - 15+ podcasts confirmed available
  - Free public library at podcasts.happyscribe.com
  - ⚠️ Initial 403 error - needs investigation

- [x] Research NPR transcript pattern
  - NPR podcasts: 99% Invisible, Planet Money, Radiolab, Hidden Brain, Throughline, TED Radio Hour, Fresh Air
  - Pattern: npr.org/transcripts/{episode-id}
  - ~2,450 total episodes
  - No authentication required

- [x] Research official podcast sites
  - ATP (atp.fm): 700+ episodes with transcripts
  - Conversations with Tyler (conversationswithtyler.com): 250+ episodes
  - Lex Fridman (lexfridman.com): 500+ episodes with dedicated transcript section
  - EconTalk (econtalk.org): 900+ episodes
  - Dwarkesh (dwarkesh.com/podcast): 150+ episodes in archive
  - Masters of Scale (mastersofscale.com): 300+ episodes
  - Huberman Lab (hubermanlab.com): 200+ episodes

- [x] Research NYT podcasts
  - The Daily: 1,200+ episodes, transcripts on nytimes.com (subscription) + HappyScribe + TranscriptForest
  - The Ezra Klein Show: 600+ episodes, transcripts on nytimes.com + aggregators
  - Hard Fork: 300+ episodes, available via Metacast and PodScribe

- [x] Document all 73 podcasts with sources
  - Completed inventory in PODCAST_CRAWL_SCOPE.md
  - Estimated 15,000+ total episodes
  - ~90% coverage achievable with free sources

---

## Phase 1: Foundation Setup (Week 1)

### Database & Configuration

- [ ] Create SQLite/PostgreSQL database schema
  - [ ] podcasts table (id, name, slug, source, episodes, enabled)
  - [ ] sources table (id, name, base_url, priority, enabled)
  - [ ] episodes table (id, podcast_id, title, url, publish_date, status)
  - [ ] transcripts table (id, episode_id, source_id, content, url, quality_score)
  - [ ] crawl_log table (id, podcast_id, source_id, status, counts, timestamps)

- [ ] Create configuration file (YAML/JSON)
  - [ ] Podcast registry with all 73 podcasts
  - [ ] Source definitions (PodScripts, TranscriptForest, NPR, Official)
  - [ ] Crawl parameters (rate limiting, retries, user agents)
  - [ ] Quality thresholds (minimum length, formats)

- [ ] Set up project structure
  - [ ] /src/crawlers/ (method-specific crawlers)
  - [ ] /src/parsers/ (transcript parsing)
  - [ ] /src/utils/ (common utilities)
  - [ ] /config/ (podcast and source configs)
  - [ ] /logs/ (crawl logs and debug info)

### Core Infrastructure

- [ ] Implement base crawler class
  - [ ] HTTP session management
  - [ ] Error handling and retries
  - [ ] Rate limiting (exponential backoff)
  - [ ] User agent rotation
  - [ ] Logging framework

- [ ] Implement transcript parser/normalizer
  - [ ] HTML to text extraction
  - [ ] Timestamp parsing
  - [ ] Speaker label detection
  - [ ] Quality scoring
  - [ ] Duplicate detection (fuzzy matching)

- [ ] Create progress tracking system
  - [ ] Database status updates
  - [ ] Real-time logging
  - [ ] Summary statistics (crawled, found, failed, skipped)
  - [ ] Per-source performance metrics

### Testing Infrastructure

- [ ] Unit tests for core functions
- [ ] Integration tests for database operations
- [ ] Sample crawls on 3-5 podcasts
- [ ] Verify logging output
- [ ] Benchmark initial crawl speed

**Success Criteria**: Database ready, base crawler working, can crawl 1 test podcast end-to-end

---

## Phase 2: Official Sites & NPR (Week 1-2)

### Implement Official Site Crawlers

- [ ] ATP Crawler (atp.fm)
  - [ ] Parse episode list from /episodes
  - [ ] Extract transcript links
  - [ ] Download transcripts
  - [ ] Test: Should find 700+ episodes
  - [ ] Target: 699 transcripts (99% coverage)

- [ ] Conversations with Tyler (conversationswithtyler.com)
  - [ ] Parse episode archive
  - [ ] Extract transcript links
  - [ ] Download transcripts
  - [ ] Test: Should find 250+ episodes
  - [ ] Target: 245 transcripts (98% coverage)

- [ ] Lex Fridman (lexfridman.com)
  - [ ] Parse /category/transcripts/ page
  - [ ] Extract linked episodes
  - [ ] Download transcripts
  - [ ] Test: Should find 500+ episodes
  - [ ] Target: 495 transcripts (99% coverage)

- [ ] EconTalk (econtalk.org)
  - [ ] Parse episode archive
  - [ ] Extract transcript links
  - [ ] Download transcripts
  - [ ] Test: Should find 900+ episodes
  - [ ] Target: 855 transcripts (95% coverage)

- [ ] Dwarkesh Podcast (dwarkesh.com/podcast)
  - [ ] Parse archive page
  - [ ] Extract links to Substack/official episodes
  - [ ] Download transcripts
  - [ ] Test: Should find 150+ episodes
  - [ ] Target: 150 transcripts (100% coverage)

- [ ] Masters of Scale (mastersofscale.com)
  - [ ] Parse /episodes/ page
  - [ ] Extract transcript links
  - [ ] Download transcripts
  - [ ] Test: Should find 300+ episodes
  - [ ] Target: 300 transcripts (100% coverage)

- [ ] Huberman Lab (hubermanlab.com)
  - [ ] Parse /all-episodes page
  - [ ] Extract transcript links or API endpoints
  - [ ] Download transcripts
  - [ ] Test: Should find 200+ episodes
  - [ ] Target: 200 transcripts (100% coverage)

### Implement NPR Pattern Crawler

- [ ] Create NPR transcript URL generator
  - [ ] Parse RSS feeds for 7 NPR podcasts
  - [ ] Extract episode IDs from URLs
  - [ ] Generate transcript URLs (npr.org/transcripts/{id})
  - [ ] Fetch and parse transcripts

- [ ] 99% Invisible
  - [ ] Test RSS parsing
  - [ ] Test URL construction
  - [ ] Target: 475 transcripts (95% coverage)

- [ ] Planet Money
  - [ ] Test RSS parsing
  - [ ] Test URL construction
  - [ ] Target: 665 transcripts (95% coverage)

- [ ] Radiolab
  - [ ] Test RSS parsing
  - [ ] Test URL construction
  - [ ] Target: 285 transcripts (95% coverage)

- [ ] Hidden Brain
  - [ ] Test RSS parsing
  - [ ] Test URL construction
  - [ ] Target: 190 transcripts (95% coverage)

- [ ] Throughline
  - [ ] Test RSS parsing
  - [ ] Test URL construction
  - [ ] Target: 142 transcripts (95% coverage)

- [ ] TED Radio Hour
  - [ ] Test RSS parsing
  - [ ] Test URL construction
  - [ ] Target: 190 transcripts (95% coverage)

- [ ] Fresh Air
  - [ ] Test RSS parsing
  - [ ] Test URL construction
  - [ ] Target: 380 transcripts (95% coverage)

**Phase 2 Success Criteria**: 
- All official site crawlers implemented and tested
- NPR pattern crawler working for all 7 podcasts
- 3,500+ transcripts collected
- <2% error rate
- Comprehensive logging of results

---

## Phase 3: PodScripts.co Aggregator (Week 2)

### PodScripts Implementation

- [ ] Create PodScripts base crawler
  - [ ] Podcast index fetcher
  - [ ] Episode list parser
  - [ ] Transcript HTML scraper
  - [ ] Content quality validation

- [ ] Implement for all PodScripts-hosted podcasts (15+ total)
  - [ ] All-In Podcast (target: 380 transcripts)
  - [ ] Modern Wisdom (target: 475 transcripts)
  - [ ] The Tim Ferriss Show (target: 570 transcripts)
  - [ ] Jordan Peterson Podcast (target: 570 transcripts)
  - [ ] Armchair Expert (target: 665 transcripts)
  - [ ] Joe Rogan Experience (target: 1,900 transcripts)
  - [ ] Huberman Lab (target: 190 transcripts)
  - [ ] Stuff You Should Know (target: 760 transcripts)
  - [ ] Knowledge Fight (target: 380 transcripts)
  - [ ] Decoding the Gurus (target: 95 transcripts)
  - [ ] Behind the Bastards (target: 285 transcripts)
  - [ ] Rotten Mango (target: 285 transcripts)
  - [ ] Bad Friends (target: 237 transcripts)
  - [ ] Kill Tony (target: 332 transcripts)
  - [ ] Conan O'Brien Needs A Friend (target: 190 transcripts)

- [ ] Testing
  - [ ] Test 3 large shows (Joe Rogan, Tim Ferriss, Jordan Peterson)
  - [ ] Verify episode counts match estimates
  - [ ] Check for rate limiting
  - [ ] Verify transcript quality
  - [ ] Test pagination handling

**Phase 3 Success Criteria**:
- 4,000+ transcripts from PodScripts
- All 15 podcasts crawled
- <2% error rate
- Proper duplicate detection if episodes exist in multiple sources

---

## Phase 4: TranscriptForest.com Aggregator (Week 2)

### TranscriptForest Implementation

- [ ] Create TranscriptForest base crawler
  - [ ] Channel list fetcher
  - [ ] Episode parser
  - [ ] Transcript extractor
  - [ ] Pagination handler

- [ ] Implement for all TranscriptForest podcasts (25+ total)
  - [ ] Lex Fridman (target: 475 transcripts)
  - [ ] Huberman Lab (target: 190 transcripts)
  - [ ] My First Million (target: 380 transcripts)
  - [ ] All-In Podcast (target: 380 transcripts)
  - [ ] Making Sense with Sam Harris (target: 285 transcripts)
  - [ ] Freakonomics (target: 380 transcripts)
  - [ ] How I Built This (target: 285 transcripts)
  - [ ] Stuff You Should Know (target: 760 transcripts)
  - [ ] TED Radio Hour (target: 190 transcripts)
  - [ ] The Ezra Klein Show (target: 540 transcripts)
  - [ ] The Tim Ferriss Show (target: 570 transcripts)
  - [ ] The Jordan B Peterson Podcast (target: 570 transcripts)
  - [ ] Masters of Scale (target: 285 transcripts)
  - [ ] Modern Wisdom (target: 475 transcripts)
  - [ ] The Talk Show with John Gruber (target: 380 transcripts)
  - [ ] This American Life (target: 665 transcripts)
  - [ ] The Lunar Society (target: 95 transcripts)
  - [ ] Exponent (target: 190 transcripts)
  - [ ] Newcomer Podcast (target: 190 transcripts)
  - [ ] Odd Lots (target: 285 transcripts)
  - [ ] On with Kara Swisher (target: 190 transcripts)
  - [ ] Naval (target: 190 transcripts)
  - [ ] Acquired (target: 190 transcripts)
  - [ ] The Vergecast (target: 475 transcripts)
  - [ ] This Week in Startups (target: 570 transcripts)

- [ ] Testing
  - [ ] Test 3 large shows
  - [ ] Verify pagination works
  - [ ] Check for dynamic content loading (may need headless browser)
  - [ ] Verify transcript quality
  - [ ] Handle duplicates from other sources

**Phase 4 Success Criteria**:
- 4,500+ transcripts from TranscriptForest
- All 25+ podcasts crawled
- Proper pagination handling
- Duplicate detection working with other sources

---

## Phase 5: HappyScribe & NYT (Week 3)

### HappyScribe Public Library

- [ ] Investigate 403 access issue
  - [ ] Test different User-Agent headers
  - [ ] Try session-based access
  - [ ] Research HappyScribe access requirements
  - [ ] Contact HappyScribe if needed

- [ ] Implement HappyScribe crawler (if access resolved)
  - [ ] The Daily (target: 1,000 transcripts)
  - [ ] Making Sense with Sam Harris (target: 255 transcripts)
  - [ ] All-In Podcast (target: 340 transcripts)
  - [ ] The Prof G Pod (target: 425 transcripts)
  - [ ] Pivot (target: 340 transcripts)
  - [ ] The Talk Show with John Gruber (target: 340 transcripts)
  - [ ] TED Radio Hour (target: 170 transcripts)
  - [ ] Stuff You Should Know (target: 680 transcripts)
  - [ ] Reply All (target: 170 transcripts)
  - [ ] Serial (target: 42 transcripts)
  - [ ] Revisionist History (target: 127 transcripts)
  - [ ] Slow Burn (target: 68 transcripts)
  - [ ] This American Life (target: 595 transcripts)
  - [ ] No Such Thing As A Fish (target: 340 transcripts)
  - [ ] My Brother My Brother And Me (target: 510 transcripts)

### NYT Podcasts (Fallback Strategy)

- [ ] The Daily
  - [ ] Primary: HappyScribe (1,000+ transcripts)
  - [ ] Secondary: TranscriptForest (1,000+ transcripts)
  - [ ] Fallback: Metacast (searchable index)
  - [ ] Target: 1,200 transcripts

- [ ] The Ezra Klein Show
  - [ ] Primary: TranscriptForest (540+ transcripts)
  - [ ] Secondary: HappyScribe (255+ transcripts)
  - [ ] Fallback: Metacast
  - [ ] Target: 600 transcripts

- [ ] Hard Fork
  - [ ] Primary: Metacast scraping
  - [ ] Secondary: PodScribe scraping
  - [ ] Target: 250 transcripts

**Phase 5 Success Criteria**:
- HappyScribe access resolved or workaround found
- 1,200+ Daily transcripts
- 600+ Ezra Klein transcripts
- 250+ Hard Fork transcripts
- Fallback sources working

---

## Phase 6: Remaining & Special Cases (Week 3)

### Research & Implement Remaining Podcasts

- [ ] Stratechery/Exponent (200+ episodes)
  - [ ] Check official site (stratechery.com)
  - [ ] Check TranscriptForest
  - [ ] Estimated source: TranscriptForest or official

- [ ] Y Combinator Startup Podcast (400+ episodes)
  - [ ] Check TranscriptForest
  - [ ] Check official YC site
  - [ ] Estimated source: TranscriptForest

- [ ] Lenny's Podcast (300+ episodes)
  - [ ] Check Substack (lennysnewsletter.com)
  - [ ] Check Metacast
  - [ ] Estimated source: Substack official

- [ ] Invest Like the Best (250+ episodes)
  - [ ] Check TranscriptForest
  - [ ] Check Patrick O'Shaughnessy site
  - [ ] Estimated source: TranscriptForest or Podcast Notes

- [ ] The Twenty Minute VC (500+ episodes)
  - [ ] Check TranscriptForest
  - [ ] Check official site
  - [ ] Estimated source: TranscriptForest

- [ ] Village Global Venture Stories (200+ episodes)
  - [ ] Check TranscriptForest
  - [ ] Check official VG site
  - [ ] Estimated source: TranscriptForest

- [ ] Additional 2-8 podcasts from original list
  - [ ] Research each for transcript availability
  - [ ] Prioritize by episode count and availability
  - [ ] Assign to appropriate crawl method

**Phase 6 Success Criteria**:
- All 73 podcasts have implementation plan
- 12-15 remaining podcasts added to crawl queue
- 3,000+ additional transcripts identified

---

## Phase 7: Quality & Deduplication (Week 4)

### Quality Scoring & Filtering

- [ ] Implement quality scoring system
  - [ ] Minimum length validation (1000+ characters)
  - [ ] Speaker label detection scoring
  - [ ] Timestamp marker scoring
  - [ ] Format consistency scoring
  - [ ] Grammar/text quality assessment

- [ ] Filter low-quality transcripts
  - [ ] Mark suspicious entries
  - [ ] Create review queue for borderline cases
  - [ ] Flag incomplete transcripts
  - [ ] Flag ad-only or show-notes-only content

- [ ] Implement deduplication
  - [ ] Exact match detection (MD5/SHA256 hashing)
  - [ ] Fuzzy matching (cosine similarity)
  - [ ] Source priority ranking
  - [ ] Keep highest quality version
  - [ ] Track alternate sources in metadata

- [ ] Data normalization
  - [ ] Consistent timestamp format
  - [ ] Standardized speaker labels
  - [ ] Clean HTML/markup artifacts
  - [ ] Consistent line breaks and spacing

**Phase 7 Success Criteria**:
- Quality score calculated for all transcripts
- Duplicates identified and merged (keep best version)
- 14,000+ high-quality unique transcripts
- <5% quality review queue

---

## Phase 8: YouTube Fallback (Week 4)

### Implement YouTube Transcript Fallback

- [ ] Set up YouTube API access (if needed)
  - [ ] Get API key
  - [ ] Test API access
  - [ ] Implement quota management

- [ ] Implement yt-dlp fallback
  - [ ] Search YouTube for podcast videos
  - [ ] Extract video IDs
  - [ ] Fetch auto-generated captions
  - [ ] Parse WebVTT/SRT format
  - [ ] Convert to standard transcript format

- [ ] Quality assessment
  - [ ] Mark YouTube transcripts with quality flag
  - [ ] Lower quality scores for auto-generated content
  - [ ] Only use if no official transcript available

- [ ] Test on 5-10 popular podcasts with video versions
  - [ ] Lex Fridman (high video availability)
  - [ ] Huberman Lab (high video availability)
  - [ ] Joe Rogan (very high video availability)
  - [ ] Test coverage increase

**Phase 8 Success Criteria**:
- YouTube fallback implemented
- 500-1,000 additional transcripts from YouTube
- <1,000 episodes still missing transcripts
- Proper quality flagging

---

## Phase 9: Testing & Validation (Week 4)

### Comprehensive Testing

- [ ] Unit test coverage
  - [ ] Test all crawlers individually
  - [ ] Test parser functions
  - [ ] Test duplicate detection
  - [ ] Test quality scoring

- [ ] Integration tests
  - [ ] End-to-end crawl of 3 podcasts
  - [ ] Database persistence verification
  - [ ] Error handling and recovery

- [ ] Spot-check validation
  - [ ] Manual review of 20-30 transcripts
  - [ ] Verify accuracy vs. original sources
  - [ ] Check for missing content
  - [ ] Validate metadata

- [ ] Performance testing
  - [ ] Measure crawl speed
  - [ ] Identify bottlenecks
  - [ ] Optimize rate limiting
  - [ ] Test database query performance

- [ ] Error handling
  - [ ] Test rate limit handling
  - [ ] Test 404 page handling
  - [ ] Test timeout handling
  - [ ] Test malformed content handling

**Phase 9 Success Criteria**:
- 95%+ test pass rate
- <1% data loss or corruption
- <2% invalid transcripts
- Crawl speed: 6+ episodes/second average

---

## Phase 10: Reporting & Deployment (Week 5)

### Final Reporting

- [ ] Generate summary statistics
  - [ ] Total podcasts: 73
  - [ ] Total episodes found: 14,500+
  - [ ] Episodes by source breakdown
  - [ ] Success rates per source
  - [ ] Quality distribution

- [ ] Generate per-podcast reports
  - [ ] Episodes found vs. estimated
  - [ ] Coverage percentage
  - [ ] Quality scores
  - [ ] Source attribution

- [ ] Generate performance report
  - [ ] Crawl time breakdown
  - [ ] Success/failure statistics
  - [ ] Error frequency
  - [ ] Optimization recommendations

- [ ] Create visual dashboard
  - [ ] Coverage bar chart
  - [ ] Source distribution pie chart
  - [ ] Quality metrics
  - [ ] Real-time crawl status

### Documentation

- [ ] Document all scrapers
  - [ ] Code comments
  - [ ] Architecture diagrams
  - [ ] Maintenance guide
  - [ ] Troubleshooting guide

- [ ] Create user guide
  - [ ] How to query transcripts
  - [ ] Search examples
  - [ ] Quality filtering options
  - [ ] Source attribution

- [ ] Document known issues
  - [ ] Sources with low coverage
  - [ ] Blocked/unavailable podcasts
  - [ ] Quality concerns
  - [ ] Rate limiting notes

### Deployment

- [ ] Set up scheduled crawling
  - [ ] Daily incremental crawls
  - [ ] Weekly full refreshes
  - [ ] Monthly de-duplication
  - [ ] Quarterly quality review

- [ ] Set up monitoring
  - [ ] Error alerting
  - [ ] Success rate monitoring
  - [ ] Rate limit monitoring
  - [ ] Data quality monitoring

- [ ] Set up backup strategy
  - [ ] Database backups (daily)
  - [ ] Archive old versions
  - [ ] Disaster recovery plan

**Phase 10 Success Criteria**:
- Comprehensive documentation complete
- Dashboard deployed and functional
- Scheduled crawling operational
- Monitoring alerts configured
- All 14,500+ transcripts accessible

---

## Success Metrics

### Minimum Success (MVP)
- [x] 60/73 podcasts identified
- [ ] 10,000+ transcripts crawled
- [ ] 85%+ average coverage per podcast
- [ ] Working database backend
- [ ] Basic error logging

### Target Success
- [ ] 70/73 podcasts crawled
- [ ] 14,000+ transcripts crawled
- [ ] 90%+ average coverage per podcast
- [ ] Complete deduplication
- [ ] Quality scoring implemented
- [ ] Comprehensive logging
- [ ] Performance dashboard

### Stretch Goals
- [ ] 73/73 podcasts crawled
- [ ] 15,000+ transcripts
- [ ] 95%+ average coverage
- [ ] YouTube fallback fully integrated
- [ ] Real-time search API
- [ ] NLP-based features (summary, keywords)

---

## Risk Mitigation

### Identified Risks

1. **HappyScribe 403 Error** - MEDIUM
   - Mitigation: Use TranscriptForest as primary fallback
   - Timeline: Week 3 - resolve or confirm workaround

2. **Rate Limiting** - MEDIUM
   - Mitigation: Implement exponential backoff, delays, proxies
   - Timeline: Ongoing, monitor during Phase 2-4

3. **Dynamic Content** - MEDIUM
   - Mitigation: Use Playwright fallback for JavaScript-heavy sites
   - Timeline: Implement during Phase 2-3, use as needed

4. **Incomplete Transcripts** - LOW
   - Mitigation: Flag with quality score, use YouTube fallback
   - Timeline: Phase 8, ongoing validation

5. **Access Restrictions** - LOW
   - Mitigation: Identify and skip if unresolvable, document
   - Timeline: Phase 3-6, per-podcast basis

---

## Timeline Summary

| Week | Phase | Deliverables | Episodes |
|------|-------|--------------|----------|
| 1 | Foundation + Official + NPR | DB, crawlers, 4 official + 7 NPR | 3,500+ |
| 2 | PodScripts + TranscriptForest | 15 PodScripts + 25 TranscriptForest | 8,000+ |
| 2-3 | HappyScribe + NYT | 15 HappyScribe + 3 NYT + remaining | 3,000+ |
| 4 | Dedup + YouTube + Testing | Quality, fallback, validation | - |
| 5 | Reporting + Deployment | Dashboard, docs, scheduled crawling | - |
| **TOTAL** | **5 weeks** | **73 podcasts** | **~14,500 episodes** |

---

**Checklist Version:** 1.0  
**Last Updated:** 2025-12-06  
**Status:** Ready for Implementation
