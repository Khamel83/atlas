# Bulletproof Capture Architecture

## Critical Problem Statement

**Current Issue**: Atlas currently conflates data capture with processing. When a user sends a URL, the system immediately tries to fetch/parse/process it. If ANY step fails (network issues, parsing errors, disk space), the user's original input may be lost forever.

**Impact**: Users cannot trust the system with their valuable data because failure at any processing step means complete loss of input.

**Solution Required**: Two-stage architecture separating bulletproof capture (never fails) from processing (can fail safely and retry).

## Architecture Overview

### Current Flow (Problematic)
```
URL → immediate processing → success OR total failure
```

### Required Flow (Bulletproof)
```
URL → bulletproof capture (always succeeds) → processing queue → eventual processing
```

### Core Principles

1. **Capture Never Fails**: Capture functions must NEVER raise unhandled exceptions
2. **Atomic Operations**: Use atomic file operations (write to temp, then rename)
3. **Redundant Storage**: Create backup copies of all captured data immediately
4. **Comprehensive Logging**: Log everything with JSON format for easy LLM parsing
5. **Restartable Processing**: Make processing queue restartable and handle interruptions gracefully
6. **Preserve Originals**: Never modify captured items, only create processed versions

## Implementation Plan

### Priority 1: Bulletproof Capture Foundation

#### Create `ingest/capture/bulletproof_capture.py`

**Core Functions:**
```python
def capture_url(url: str, user_context: dict = None) -> dict:
    """NEVER FAILS. Immediately saves URL with metadata to multiple locations."""
    # Generate unique capture_id with timestamp
    # Save to primary + backup locations atomically
    # Return capture confirmation with tracking info

def capture_file(file_path: str, user_context: dict = None) -> dict:
    """NEVER FAILS. Immediately copies file to secure storage."""
    # Copy to primary + backup locations
    # Generate comprehensive metadata
    # Return capture tracking information

def get_capture_status(capture_id: str) -> dict:
    """Return current status of any captured item."""
```

**Key Requirements:**
- Must handle ALL exceptions internally
- Must create atomic file operations
- Must provide immediate user feedback
- Must generate unique tracking IDs
- Must save to multiple locations simultaneously

#### Create `ingest/capture/failure_notifier.py`

```python
def notify_capture_failure(item: str, error: Exception):
    """Immediate notification when capture fails."""
    # Write to CAPTURE_FAILURES.log
    # Console + desktop notification
    # Never let notification failure break capture
```

#### Create `ingest/capture/capture_validator.py`

```python
def validate_capture(capture_id: str) -> dict:
    """Verify capture integrity and completeness."""
    # Check primary and backup locations
    # Validate metadata consistency
    # Return validation status
```

### Priority 2: Processing Queue System

#### Create `ingest/queue/processing_queue.py`

```python
class ProcessingQueue:
    def add_to_queue(self, capture_id: str, item_type: str, priority: int = 0):
        """Add captured item to processing queue."""

    def get_next_item(self) -> dict:
        """Get next item for processing."""

    def mark_complete(self, capture_id: str, result_paths: dict):
        """Mark item as successfully processed."""

    def mark_failed(self, capture_id: str, error: str, retry_count: int):
        """Mark item as failed, handle retry logic."""

    def get_queue_status(self) -> dict:
        """Return comprehensive queue statistics."""
```

#### Create `ingest/queue/queue_processor.py`

```python
class QueueProcessor:
    def process_next_batch(self, batch_size: int = 5) -> dict:
        """Process next batch of items from queue."""

    def retry_failed_items(self, max_retries: int = 3) -> dict:
        """Retry processing for failed items."""

    def cleanup_completed_items(self, older_than_days: int = 30) -> dict:
        """Clean up old completed items."""
```

### Priority 3: Update Existing Ingestors

#### Modify `helpers/article_fetcher.py`
- Add `process_captured_article(capture_id)` function
- Modify existing logic to read from captured URL instead of input file
- Update capture metadata throughout processing
- Maintain existing processing logic but with capture-aware status updates

#### Modify `helpers/podcast_ingestor.py`
- Add `process_captured_podcast(capture_id)` function
- Process captured OPML files from queue
- Same pattern as articles

#### Modify `helpers/youtube_ingestor.py` and `helpers/instapaper_ingestor.py`
- Same pattern - work from captured items instead of direct input
- Preserve existing processing logic
- Add capture-aware error handling

### Priority 4: Comprehensive Logging System

#### Create `helpers/logging_config.py`

```python
def setup_comprehensive_logging():
    """Set up logging optimized for LLM debugging."""
    # JSON-formatted logs for easy parsing
    # Multiple log files: capture.log, processing.log, errors.log
    # Performance timing throughout
    # Full context on all errors
```

**Logging Requirements:**
- Log function entry/exit with parameters
- Log all errors with full context and stack traces
- Log performance timing for slow operations
- Log user actions and system state changes
- Use structured JSON format for easy parsing

### Priority 5: Monitoring and Management

#### Create `scripts/ingest_status.py`

```python
def show_capture_status():
    """Display all captured items and processing status."""

def show_failed_items():
    """Show items that failed processing and why."""

def retry_failed_items():
    """Retry processing for failed items."""

def show_queue_statistics():
    """Display comprehensive queue and processing statistics."""
```

#### Create `scripts/retry_failed.py`

```python
def retry_specific_item(capture_id: str):
    """Retry processing for specific failed item."""

def retry_all_failed(max_age_hours: int = 24):
    """Retry all failed items within time window."""
```

#### Create `scripts/queue_manager.py`

```python
def pause_processing():
    """Pause queue processing."""

def resume_processing():
    """Resume queue processing."""

def clear_queue(confirm: bool = False):
    """Clear processing queue (with confirmation)."""
```

### Priority 6: Directory Structure Update

#### New File Organization

```
output/
├── captured/              # NEW: Raw captured items (never deleted)
│   ├── urls/             # Captured URLs with metadata
│   ├── files/            # Captured files with metadata
│   ├── metadata/         # Comprehensive metadata for all captures
│   └── backups/          # Backup copies of all captured data
├── processing_queue/      # NEW: Queue state and management
│   ├── pending/          # Items waiting to be processed
│   ├── in_progress/      # Items currently being processed
│   ├── completed/        # Successfully processed items
│   └── failed/           # Failed items with error details
├── processed/             # EXISTING: Final processed content
│   ├── articles/
│   ├── podcasts/
│   └── youtube/
└── logs/                  # NEW: Comprehensive logging
    ├── capture.log       # All capture operations
    ├── processing.log    # All processing operations
    ├── errors.log        # All errors with full context
    └── performance.log   # Performance timing data
```

### Priority 7: Legal Framework

#### Create `LEGAL/` Directory Structure

```
LEGAL/
├── LICENSE.md           # MIT license with disclaimers
├── PRIVACY_POLICY.md    # Local-first processing guarantees
├── TERMS_OF_USE.md      # Use at own risk disclaimers
└── COMPLIANCE_NOTES.md  # Development compliance requirements
```

**Legal Integration:**
- Basic compliance checks in capture functions
- User consent tracking for data processing
- Clear data retention policies
- Local-first processing guarantees

### Priority 8: Integration Updates

#### Rewrite `ingest/ingest_main.py`

```python
def ingest_item(item: str) -> dict:
    """Main entry point. NEVER FAILS to capture."""
    # Bulletproof capture first
    # Add to processing queue
    # Return capture confirmation

def process_queue(max_items: int = None) -> dict:
    """Process items from queue separately."""
    # Process using existing logic
    # Handle retries and failures gracefully

def get_ingest_status() -> dict:
    """Return comprehensive ingest system status."""
```

#### Update `run.py`

**New Capabilities:**
- Support capture-only mode and process-only mode
- Show capture and processing statistics
- Add queue processing step
- Provide detailed status reporting

#### Update `run_atlas.sh`

**Enhanced Workflow:**
1. Pre-run capture system validation
2. Capture phase (bulletproof)
3. Processing phase (with retries)
4. Post-run status reporting
5. Cleanup and maintenance

## Success Criteria

After implementation, users should be able to:

1. **Immediate Capture Confirmation**: Send URL to Atlas and get immediate capture confirmation
2. **Background Processing**: Have processing happen in background with full retry logic
3. **Zero Data Loss**: Never lose any input data even if processing fails completely
4. **Easy Debugging**: Debug any issues by feeding structured logs to LLM
5. **Reliable Deployment**: Deploy on Pi and run reliably for months without intervention

## Implementation Notes

### Error Handling Strategy

1. **Capture Functions**: Must catch ALL exceptions, log them, and return status
2. **Processing Functions**: Can fail safely, will be retried automatically
3. **Queue Management**: Must handle interruptions and restarts gracefully
4. **User Feedback**: Always provide immediate feedback on capture success

### Performance Considerations

1. **Capture Speed**: Must be near-instantaneous for user experience
2. **Processing Throughput**: Can be slower, optimized for reliability
3. **Storage Efficiency**: Balance redundancy with disk space usage
4. **Memory Usage**: Process items in batches to avoid memory issues

### Testing Strategy

1. **Capture Testing**: Test all failure scenarios for capture functions
2. **Queue Testing**: Test queue persistence across restarts
3. **Integration Testing**: Test entire capture-to-processing flow
4. **Stress Testing**: Test with large volumes of concurrent captures

## Migration Strategy

### Phase 1: Parallel Implementation
- Build new capture system alongside existing code
- Test thoroughly with sample data
- Validate all capture and processing scenarios

### Phase 2: Gradual Migration
- Update one ingestor at a time to use capture system
- Maintain backward compatibility during transition
- Monitor system behavior closely

### Phase 3: Full Deployment
- Switch all ingestors to capture-based processing
- Remove old direct-processing code
- Update all documentation and user guides

## Risk Assessment

### High Risk Areas
1. **File System Operations**: Atomic operations critical for data integrity
2. **Queue Persistence**: Must survive system restarts and crashes
3. **Error Handling**: Comprehensive exception handling required
4. **Performance Impact**: Capture overhead must be minimal

### Mitigation Strategies
1. **Extensive Testing**: Test all failure scenarios thoroughly
2. **Gradual Rollout**: Implement and test one component at a time
3. **Monitoring**: Comprehensive logging and monitoring from day one
4. **Rollback Plan**: Maintain ability to revert to current system

## Future Enhancements

### Planned Improvements
1. **Distributed Processing**: Support for multiple processing nodes
2. **Priority Queues**: Advanced prioritization for different content types
3. **Batch Processing**: Optimized batch processing for similar items
4. **Machine Learning**: Intelligent retry strategies based on failure patterns

### Integration Opportunities
1. **Cognitive Amplification**: Capture system enables proactive intelligence
2. **Real-time Processing**: Foundation for real-time content analysis
3. **Collaborative Features**: Multi-user capture and processing support
4. **API Integration**: RESTful API for external system integration

---

**This architecture change is foundational** - every other Atlas feature depends on users trusting the system with their data. Focus on reliability over features to enable everything else to be built safely on top.