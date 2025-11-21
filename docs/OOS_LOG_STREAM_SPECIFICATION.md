# OOS Log-Stream Event Format Specification

## Universal Event Format

```
timestamp|event_type|content_type|source|item_id|data
```

### Field Definitions

#### timestamp (ISO 8601 UTC)
- Format: `2025-09-29T01:08:38.246Z`
- Precision: Millisecond precision
- Timezone: Always UTC
- Purpose: Exact event timing for analytics and debugging

#### event_type (ENUM)
Core lifecycle events:
- `DISCOVER` - New content discovered
- `PROCESS` - Processing started
- `COMPLETE` - Processing successful
- `FAIL` - Processing failed
- `SKIP` - Content skipped (duplicate, invalid, etc.)
- `RETRY` - Retrying failed processing
- `METRICS` - System metrics and statistics

#### content_type (ENUM)
All supported OOS content types:
- `podcast` - Podcast episodes and transcripts
- `article` - Web articles and documents
- `email` - Email messages and attachments
- `video` - Video content and metadata
- `documentation` - Technical documentation
- `url` - Generic URL processing
- `audio` - Audio file processing

#### source (STRING)
Source system or feed identifier:
- Podcasts: `Asianometry`, `This American Life`, `Lex Fridman`, etc.
- Articles: `TechCrunch`, `Stratechery`, `Hacker News`, etc.
- Emails: `gmail`, `protonmail`, etc.
- Videos: `YouTube`, `Vimeo`, etc.
- Generic: `web_crawler`, `rss_feed`, `api`

#### item_id (STRING)
Unique identifier for content item:
- Format: `{source}_{unique_hash}` or `{source}_{timestamp}`
- Purpose: Track content through processing pipeline
- Example: `Asianometry_20250929_010838`, `TechCrunch_abc123`

#### data (JSON string)
Flexible payload with event-specific data:
- Discovery events: URLs, metadata
- Processing events: Status, progress
- Completion events: Results, file paths
- Failure events: Error details, retry info

## Event Examples

### Podcast Processing Pipeline

```
# Episode discovery
2025-09-29T01:08:38.246Z|DISCOVER|podcast|Asianometry|Asianometry_20250929_010838|{"url":"https://feeds.simplecast.com/ABC123","title":"Episode 123: AI Revolution","rss_url":"https://feeds.simplecast.com/ABC123"}

# Start processing
2025-09-29T01:08:45.123Z|PROCESS|podcast|Asianometry|Asianometry_20250929_010838|{"source":"atp","transcript_url":"https://atp.fm/transcript/123"}

# Successful completion
2025-09-29T01:09:15.789Z|COMPLETE|podcast|Asianometry|Asianometry_20250929_010838|{"transcript_file":"data/transcripts/asianometry_123.txt","word_count":2540,"duration":1872}

# Processing failure
2025-09-29T01:09:20.456Z|FAIL|podcast|ThisAmericanLife|ThisAmericanLife_20250929_010920|{"error":"network_timeout","retry_count":3,"last_attempt":"2025-09-29T01:09:18.123Z"}
```

### Article Processing

```
# Article discovery
2025-09-29T01:10:01.234Z|DISCOVER|article|TechCrunch|TechCrunch_20250929_011001|{"url":"https://techcrunch.com/ai-breakthrough","title":"Major AI Breakthrough Announced","source_feed":"techcrunch_main"}

# Content extraction
2025-09-29T01:10:15.678Z|PROCESS|article|TechCrunch|TechCrunch_20250929_011001|{"method":"web_scraper","content_type":"html"}

# Completion with AI processing
2025-09-29T01:11:30.987Z|COMPLETE|article|TechCrunch|TechCrunch_20250929_011001|{"file":"data/articles/techcrunch_ai_breakthrough.json","word_count":1847,"ai_summary":"Researchers announced...","ai_tags":["ai","breakthrough","research"]}
```

### System Metrics

```
# Processing statistics
2025-09-29T01:15:00.000Z|METRICS|system|oos|oos_20250929_011500|{"processed_last_hour":45,"failed_last_hour":3,"pending_queue":124,"active_processes":3,"memory_usage":"2.1GB","disk_usage":"45.2GB"}

# Source reliability
2025-09-29T01:15:05.123Z|METRICS|source|atp|atp_20250929_011505|{"success_rate":0.94,"avg_processing_time":45.2,"total_processed":1256,"last_error":"2025-09-29T00:45:23Z"}
```

## Analytics Views

### Virtual Views from Log Events

Instead of database tables, we derive state from log events:

```python
class LogViews:
    def podcast_status_view(self):
        """Current podcast processing status"""
        return {
            'discovered': count_events('DISCOVER', 'podcast'),
            'processing': count_events('PROCESS', 'podcast') - count_events('COMPLETE', 'podcast'),
            'completed': count_events('COMPLETE', 'podcast'),
            'failed': count_events('FAIL', 'podcast'),
            'pending': count_events('DISCOVER', 'podcast') - count_events('COMPLETE', 'podcast') - count_events('FAIL', 'podcast')
        }

    def throughput_view(self, timeframe='1h'):
        """Processing throughput over time"""
        return calculate_events_per_timeframe('COMPLETE', timeframe)

    def error_analysis_view(self):
        """Error patterns and analysis"""
        return analyze_error_patterns()

    def source_reliability_view(self):
        """Source system reliability metrics"""
        return calculate_source_reliability()
```

### Query Examples

```bash
# Current status
cat oos.log | log_query --view podcast_status

# Hourly throughput
cat oos.log | log_query --view hourly_throughput --last 24h

# Error analysis
cat oos.log | log_query --view errors --last 6h

# Source reliability
cat oos.log | log_query --view source_reliability
```

## Implementation Requirements

### Core Logger
- Thread-safe append-only writes
- Both stdout (for piping) and file output
- Automatic timestamp generation
- Event validation and formatting

### Event Parser
- Parse log lines into structured data
- Handle malformed entries gracefully
- Support filtering and searching
- Efficient log scanning for views

### Analytics Engine
- Virtual view implementations
- Caching for frequent queries
- Real-time and historical analysis
- Performance optimization for large log files

## File Organization

```
oos/
├── oos.log              # Main event log (append-only)
├── oos_logger.py        # Core logging framework
├── log_views.py         # Analytics views implementation
├── log_query.py         # Query and filtering utilities
├── event_parser.py      # Log parsing and validation
└── views/
    ├── podcast_status.py
    ├── throughput.py
    ├── errors.py
    └── reliability.py
```

## Migration Strategy

### Phase 1: Core Implementation
- Implement basic event format and logger
- Create essential analytics views
- Test with sample data

### Phase 2: Tool Integration
- Wrap existing OOS tools with log output
- Maintain backward compatibility
- Validate functionality preservation

### Phase 3: Production Deployment
- Replace database-driven components
- Deploy log-stream architecture
- Monitor and validate performance

## Benefits

1. **Simplicity**: Append-only operations are inherently reliable
2. **Performance**: No database locks or contention
3. **Debugging**: Complete audit trail of all operations
4. **Analytics**: Rich event history for analysis
5. **Reliability**: Survives crashes and power loss
6. **Scalability**: Easy to distribute and parallelize