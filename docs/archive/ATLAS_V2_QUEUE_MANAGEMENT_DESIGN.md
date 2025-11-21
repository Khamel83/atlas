# Atlas v2 Bulletproof Queue Management System

**Date**: October 1, 2025
**Status**: 🔄 DESIGN IN PROGRESS
**Priority**: CRITICAL - Addresses 37% queue pollution issue

## Executive Summary

The current Atlas v2 queue system has a critical reliability gap: **19,589 `file://` URLs** that will always fail with HTTP-based processing, consuming 37% of processing capacity. This design eliminates queue pollution, implements robust deduplication, and provides production-grade queue management.

## Current Problem Analysis

### Queue Pollution Issue
```
Current Queue Composition:
├── Total Items: 52,372
├── Completed: 32,793 (62.6%)
├── Pending: 19,572 (37.4%)
└── Failed: 7 (0.01%)

Critical Issue:
├── document: 19,589 (37.4%) - LOCAL FILES (WILL FAIL)
├── podcast_transcript: 19,121 (36.5%) - PROCESSED CONTENT
├── article: 5,229 (10.0%) - NEWS/ARTICLES
└── url_processing: 2,879 (5.5%) - WEB URLs
```

**Root Cause**: Local `file://` URLs from migrated data cannot be processed by HTTP-based extractor, causing infinite retry loops.

## Enhanced Queue Management Design

### 1. URL Classification and Routing

```python
class URLClassifier:
    """Intelligently classify URLs for appropriate processing routing"""

    URL_PATTERNS = {
        'http_processable': r'^https?://',
        'file_local': r'^file://',
        'invalid_scheme': r'^(?!https?://)(?!file://)',
        'unsupported_extension': r'\.(zip|tar|gz|pdf|exe|dmg)$',
        'social_media': r'(facebook\.com|twitter\.com|instagram\.com|linkedin\.com)',
        'video_platform': r'(youtube\.com|youtu\.be|vimeo\.com)',
    }

    def classify_url(self, url: str) -> URLClassification:
        """Classify URL for appropriate processing strategy"""
        # Returns classification with processing strategy
```

### 2. Enhanced Database Schema

```sql
-- Enhanced content metadata with URL classification
ALTER TABLE content_metadata ADD COLUMN url_scheme TEXT;
ALTER TABLE content_metadata ADD COLUMN url_domain TEXT;
ALTER TABLE content_metadata ADD COLUMN processing_strategy TEXT;
ALTER TABLE content_metadata ADD COLUMN is_processable BOOLEAN DEFAULT TRUE;
ALTER TABLE content_metadata ADD COLUMN failure_reason TEXT;

-- Dead letter queue for permanently failed items
CREATE TABLE dead_letter_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_id TEXT UNIQUE,
    source_url TEXT NOT NULL,
    original_error TEXT,
    failure_classification TEXT,
    retry_count INTEGER,
    quarantined_at TEXT,
    notes TEXT
);

-- URL deduplication index
CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_source_url
ON content_metadata(source_url) WHERE is_processable = TRUE;

-- Processing strategy routing
CREATE INDEX IF NOT EXISTS idx_processing_strategy
ON processing_queue(status, processing_strategy, priority DESC);
```

### 3. Deduplication System

```python
class ContentDeduplicator:
    """Prevent duplicate content processing"""

    async def check_duplicate(self, url: str, content_hash: str = None) -> DeduplicationResult:
        """Check if URL/content already processed"""

    async def generate_content_id(self, url: str, content_type: str) -> str:
        """Generate deterministic content ID for deduplication"""

    async def mark_processed(self, content_id: str, processing_metadata: dict):
        """Mark content as successfully processed"""
```

### 4. Intelligent Retry Logic

```python
class RetryManager:
    """Exponential backoff with jitter and intelligent retry strategies"""

    RETRY_STRATEGIES = {
        'network_timeout': {'max_retries': 3, 'backoff': 'exponential', 'base_delay': 60},
        'rate_limit': {'max_retries': 5, 'backoff': 'exponential', 'base_delay': 300},
        'not_found': {'max_retries': 1, 'backoff': 'none'},
        'server_error': {'max_retries': 2, 'backoff': 'linear', 'base_delay': 120},
        'parse_error': {'max_retries': 1, 'backoff': 'none'},
        'file_not_found': {'max_retries': 0, 'backoff': 'none'},  # Don't retry file:// failures
    }

    async def should_retry(self, error: Exception, retry_count: int, strategy: str) -> bool:
        """Determine if item should be retried based on error type"""
```

### 5. Queue Prioritization and Backpressure

```python
class QueueManager:
    """Intelligent queue management with priorities and backpressure"""

    PRIORITY_LEVELS = {
        'critical': 100,    # User-submitted, high-value content
        'high': 80,         # Recent podcast episodes
        'normal': 50,       # Regular article processing
        'low': 20,          # Bulk ingestion, backlog items
        'cleanup': 10,      # Queue maintenance tasks
    }

    async def get_next_batch(self, limit: int = 50) -> List[QueueItem]:
        """Get next batch with intelligent prioritization"""

    async def apply_backpressure(self) -> bool:
        """Check if system should apply backpressure"""
```

## Implementation Components

### Phase 1: URL Classification and Cleanup (IMMEDIATE)

**Objective**: Eliminate queue pollution by identifying and quarantining non-processable URLs

1. **URL Classification Service**
   - Scan all existing queue items
   - Classify URLs by processing feasibility
   - Mark `file://` URLs as non-processable
   - Move to dead letter queue with reason

2. **Database Migration**
   - Add classification columns to existing tables
   - Create dead letter queue
   - Update indexes for performance

3. **Queue Cleanup Script**
   ```python
   async def cleanup_polluted_queue():
       """Move non-processable URLs to dead letter queue"""
       # Identify file:// URLs
       # Move to dead_letter_queue
       # Update processing status
       # Log cleanup actions
   ```

### Phase 2: Deduplication System (HIGH PRIORITY)

**Objective**: Prevent duplicate URL submissions and processing

1. **URL Hash Generation**
   - Create deterministic content IDs from URLs
   - Store URL hashes for fast lookup
   - Implement canonical URL normalization

2. **Duplicate Detection**
   - Check duplicates before enqueueing
   - Handle URL variants (tracking parameters, http/https)
   - Provide duplicate reporting

3. **Idempotent Processing**
   - Ensure re-processing same URL doesn't create duplicates
   - Maintain processing history

### Phase 3: Enhanced Retry Logic (MEDIUM PRIORITY)

**Objective**: Implement intelligent retry strategies with exponential backoff

1. **Error Classification**
   - Categorize errors by type and recovery potential
   - Assign appropriate retry strategies
   - Implement permanent failure detection

2. **Exponential Backoff**
   - Calculate retry delays with jitter
   - Implement circuit breaker pattern
   - Handle rate limiting gracefully

3. **Retry State Management**
   - Track retry attempts and timing
   - Implement retry budgets
   - Monitor retry success rates

### Phase 4: Queue Prioritization (MEDIUM PRIORITY)

**Objective**: Implement intelligent queue ordering and backpressure

1. **Priority Scoring**
   - Calculate content priority based on multiple factors
   - Implement dynamic priority adjustment
   - Handle urgent content processing

2. **Backpressure Handling**
   - Monitor system resource utilization
   - Implement adaptive batch sizing
   - Handle high-volume input scenarios

3. **Queue Monitoring**
   - Real-time queue metrics
   - Processing velocity tracking
   - Bottleneck identification

## Success Metrics

### Baseline vs Target Performance

| Metric | Current | Target | Improvement |
|--------|---------|--------|-------------|
| Queue Efficiency | 63% | 95%+ | +32% |
| Duplicate Processing | Unknown | 0% | 100% reduction |
| Retry Success Rate | Basic | 85%+ | +35% |
| Processing Rate | 600/hr | 1,200/hr | 2x |
| Queue Pollution | 37% | 0% | Complete elimination |

### Quality Gates

1. **Zero Queue Pollution**: All non-processable URLs identified and quarantined
2. **Complete Deduplication**: No duplicate URLs processed
3. **Intelligent Retry**: Permanent failures detected immediately
4. **Backpressure Handling**: System remains responsive under high load
5. **Queue Persistence**: No data loss during service restarts

## Implementation Plan

### Week 1: Critical Cleanup
- [ ] Implement URL classification service
- [ ] Create dead letter queue
- [ ] Clean up existing `file://` URL pollution
- [ ] Add URL classification to new submissions

### Week 2: Deduplication
- [ ] Implement content ID generation
- [ ] Add duplicate detection API
- [ ] Create URL normalization logic
- [ ] Test duplicate prevention

### Week 3: Enhanced Retry
- [ ] Implement error classification
- [ ] Add exponential backoff with jitter
- [ ] Create retry strategies per error type
- [ ] Test retry logic under failure conditions

### Week 4: Queue Prioritization
- [ ] Implement priority scoring
- [ ] Add backpressure handling
- [ ] Create queue monitoring dashboard
- [ ] Performance testing and optimization

## Risk Mitigation

### Technical Risks
1. **Data Loss**: Implement comprehensive backup before schema changes
2. **Performance Degradation**: Add indexes incrementally and monitor query performance
3. **Processing Stalls**: Implement fallback mechanisms and manual override capabilities

### Operational Risks
1. **Extended Downtime**: Perform migrations in stages with rollback capability
2. **Queue Starvation**: Monitor processing rates and adjust batch sizes dynamically
3. **Resource Exhaustion**: Implement resource monitoring and automatic throttling

## Testing Strategy

### Unit Tests
- URL classification accuracy
- Deduplication logic correctness
- Retry calculation verification
- Queue priority ordering

### Integration Tests
- End-to-end processing flow
- Database migration validation
- API integration testing
- Error scenario handling

### Load Tests
- High-volume input processing
- Concurrent request handling
- Resource utilization under load
- Long-running stability validation

## Monitoring and Alerting

### Key Metrics
1. **Queue Health**: Depth, processing velocity, error rates
2. **Deduplication**: Duplicate detection rate, false positive/negative rates
3. **Retry Performance**: Retry success rates, backoff effectiveness
4. **System Resources**: CPU, memory, disk, network utilization

### Alerting Rules
- Queue depth exceeding thresholds
- Processing rate drops below minimum
- Error rate spikes above baseline
- Resource utilization approaching limits

## Next Steps

This design provides the foundation for transforming Atlas v2's queue management from a basic processing system into a bulletproof, production-grade content ingestion engine capable of handling high-volume inputs with complete reliability.

**Ready for Implementation** ✅

*Immediate priority: Clean up the 19,589 `file://` URLs causing 37% queue pollution.*