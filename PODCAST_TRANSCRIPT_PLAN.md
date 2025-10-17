# Podcast Transcript Extraction Plan

## Overview
Systematic, episode-by-episode extraction for all 68 user podcasts with granular tracking and quality validation.

## Key Principle
- **Episode-level processing**: Each episode = 1 queue row, individual processing
- **Source context preservation**: Same source may handle multiple episodes of same podcast
- **Exact scope clarity**: Know exactly how many transcripts we're looking for across all podcasts

## Step 1: Build Complete Episode Queue

### 1.1 Read User's Podcast Requirements
- Load `config/podcast_config.csv`
- Extract all 68 podcasts where Exclude = 0
- For each podcast, note requested episode count

### 1.2 Pull RSS Feeds for All 68 Podcasts
- Load RSS mappings from `config/podcast_rss_feeds.csv`
- For each podcast, fetch RSS feed
- Extract ALL available episodes from RSS
- **Critical**: If user wants 1000 but RSS only has 250, queue 250 episodes (actual available)

### 1.3 Create Episode Queue Table
```sql
CREATE TABLE episode_queue (
    id INTEGER PRIMARY KEY,
    podcast_name TEXT,
    episode_title TEXT,
    episode_url TEXT,
    rss_url TEXT,
    status TEXT DEFAULT 'pending',  -- pending, processing, found, not_found, error
    transcript_source TEXT,
    transcript_url TEXT,
    content_length INTEGER,
    quality_score INTEGER,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### 1.4 Populate Queue
- Insert each episode as individual row
- Total rows = sum of actual available episodes across all 68 podcasts
- This gives us exact target: "Processing X episodes from Y podcasts"

## Step 2: Systematic Episode Processing

### 2.1 Queue Processor Architecture
```python
class EpisodeProcessor:
    def process_episode(self, episode_id):
        # For each episode individually:
        # 1. Mark as processing
        # 2. Try multiple extraction strategies
        # 3. Validate quality
        # 4. Store result
        # 5. Update status
```

### 2.2 Extraction Strategies (per episode)
1. **Direct source scraping** - Check podcast's official website
2. **Google search** - "Episode title + transcript"
3. **Community sources** - GitHub, Medium, Archive.org
4. **RSS content extraction** - Full text from RSS feed
5. **YouTube transcripts** - If video version exists

### 2.3 Source Context Optimization
- **Cache successful sources per podcast**: If Recipe Club episodes found at source X, try source X first for other Recipe Club episodes
- **Source success tracking**: Maintain success rate per source per podcast
- **Batch requests**: When same source handles multiple episodes, optimize request timing

### 2.4 Quality Validation
- **Minimum length**: 1000+ characters
- **Content analysis**: Check for actual transcript vs show notes/ads
- **Format validation**: Proper dialogue structure, speaker labels
- **Duplicate detection**: Avoid storing same transcript multiple times

## Step 3: Database Schema Integration

### 3.1 Queue Management
```sql
-- Get next episode to process
SELECT * FROM episode_queue
WHERE status = 'pending'
ORDER BY created_at ASC
LIMIT 1;

-- Update episode status
UPDATE episode_queue
SET status = 'found', transcript_url = ?, content_length = ?, quality_score = ?
WHERE id = ?;
```

### 3.2 Results Storage
- Found transcripts stored in `content` table with `content_type = 'podcast_transcript'`
- Queue maintains processing status and source information
- Enable real-time progress tracking

## Step 4: Progress Tracking & Reporting

### 4.1 Real-time Status
```sql
SELECT
    podcast_name,
    COUNT(*) as total_episodes,
    SUM(CASE WHEN status = 'found' THEN 1 ELSE 0 END) as found,
    SUM(CASE WHEN status = 'not_found' THEN 1 ELSE 0 END) as not_found,
    SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as errors
FROM episode_queue
GROUP BY podcast_name;
```

### 4.2 Final Report
- **Total scope**: "Processing X episodes from Y podcasts"
- **Success rate**: "Found A transcripts, B not found, C errors"
- **Per-podcast breakdown**: Individual podcast results
- **Source analysis**: Which sources worked best for which podcasts

## Step 5: Implementation Priority

### 5.1 Phase 1: Queue Building
1. Parse podcast_config.csv for 68 target podcasts
2. Fetch RSS feeds and extract available episodes
3. Populate episode_queue table
4. **Output**: Exact count of episodes we're processing

### 5.2 Phase 2: Queue Processing
1. Build episode processor with multiple extraction strategies
2. Implement source context optimization
3. Add quality validation
4. Start systematic processing

### 5.3 Phase 3: Results & Analysis
1. Monitor progress in real-time
2. Generate final completion report
3. Provide detailed breakdown per podcast
4. Document successful sources/methods

## Success Metrics
- **100% coverage**: All requested episodes processed
- **Quality threshold**: Only verified transcripts count as "found"
- **Clear reporting**: Exact numbers, no ambiguity
- **Scalability**: System can handle any number of episodes

## Key Advantages Over Current Approach
1. **Granular tracking**: Know exactly which episodes succeed/fail
2. **No assumptions**: Process everything, let results guide understanding
3. **Source optimization**: Learn what works for each podcast
4. **Clear scope**: Exact numbers, not estimates
5. **Quality focus**: Validate each transcript individually

## Expected Timeline
- **Queue building**: 1-2 hours
- **Processing**: 4-8 hours (depending on volume)
- **Results**: Immediate upon completion

**Bottom line**: We'll know exactly how many transcripts exist across all your podcasts, with detailed status for each episode.