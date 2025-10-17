# Atlas Numeric Stage System (0-599)

## Complete Content Processing Lifecycle

This document defines the complete numeric stage system for Atlas content processing from 0-599.

### Stage Philosophy
- **Each 100-point range = Major phase** (Acquisition, Validation, Processing, Enhancement, Finalization)
- **Each 10-point range = Medium step** within each phase
- **Single digit increments = Fine-grained progress** within steps
- **Terminal stages ≥ 590** mean "done" (no further processing needed)
- **599 = Duplicate** (special terminal status for re-imported content)

## Stage Breakdown

### 000-099: System & Initialization
- **0**: SYSTEM_INIT - System initialization
- **10**: CONTENT_DISCOVERED - Content discovered but not queued
- **20**: BATCH_RECEIVED - Batch file received (CSV, etc.)
- **50**: QUEUE_PENDING - Pending queue placement

### 100-199: Content Acquisition Phase
- **100**: CONTENT_RECEIVED - URL/file received, no processing
- **110**: CONTENT_QUEUED - Queued for processing
- **120**: FETCH_ATTEMPTING - Actively trying to fetch content
- **130**: FETCH_FAILED - Initial fetch failed
- **140**: FALLBACK_ATTEMPTING - Trying fallback strategies
- **150**: CONTENT_RETRIEVED - Successfully retrieved raw content
- **160**: CONTENT_ARCHIVED - Archived version found/retrieved
- **190**: ACQUISITION_COMPLETE - All acquisition steps complete

### 200-299: Content Validation Phase
- **200**: VALIDATION_STARTED - Starting validation process
- **210**: QUALITY_CHECK - Checking content quality
- **220**: AUTHENTICITY_VERIFY - Verifying content is authentic
- **230**: COMPLETENESS_CHECK - Verifying content is complete
- **240**: FORMAT_VALIDATE - Validating content format
- **250**: VALIDATION_PASSED - All validation checks passed
- **280**: VALIDATION_FAILED - Validation failed
- **299**: VALIDATION_COMPLETE - Validation phase complete

### 300-399: Content Processing Phase
- **300**: PROCESSING_STARTED - Starting content processing
- **310**: EXTRACTION_CLEAN - Extract and clean main content
- **320**: TRANSCRIPT_EXTRACTION - Extract transcripts (YouTube fallback available)
- **330**: STRUCTURE_ANALYSIS - Analyze document structure
- **340**: CONTENT_TRANSFORMED - Transformed to standard formats
- **350**: METADATA_EXTRACTED - Extract basic metadata
- **360**: CONTENT_FORMATTED - Formatted for storage
- **390**: PROCESSING_COMPLETE - Core processing complete

### 400-499: Content Enhancement Phase
- **400**: ENHANCEMENT_STARTED - Starting AI enhancement
- **410**: CONTENT_ANALYZED - AI analysis complete
- **420**: CONTENT_SUMMARIZED - AI summaries generated
- **430**: TOPICS_EXTRACTED - Topics and keywords extracted
- **440**: ENTITIES_IDENTIFIED - Entities and relationships found
- **450**: SEMANTIC_ANALYSIS - Semantic analysis complete
- **490**: ENHANCEMENT_COMPLETE - AI enhancement complete

### 500-599: Content Finalization Phase
- **500**: FINALIZATION_STARTED - Starting finalization
- **510**: CROSS_REFERENCES - Add cross-references
- **520**: QUALITY_FINAL - Final quality assessment
- **530**: METADATA_FINAL - Final metadata updates
- **540**: CONTENT_INDEXED - Content indexed for search
- **590**: FINALIZATION_COMPLETE - All processing complete (terminal)
- **595**: CONTENT_ARCHIVED_FINAL - Final archival state (terminal)
- **599**: CONTENT_DUPLICATE - Duplicate content (terminal)

### Special Error States
- **666**: RATE_LIMITED - Rate limited, will retry
- **777**: PERMANENT_ERROR - Permanent failure, no retry
- **888**: SYSTEM_ERROR - System error, may retry

## YouTube Module Integration

### Module Types (Not Stages)
The YouTube system consists of **utility modules** that can be called from different stages:

**YouTube History Scraper** (`helpers/youtube_modules_integration`):
- **Purpose**: Collect videos you've watched on YouTube
- **When to call**: Content acquisition stages (100-199)
- **Stage integration**: `collect_youtube_history()` can be called from stage 110-150
- **Output**: Stores YouTube videos as `youtube_video` content type

**YouTube Podcast Fallback** (`helpers/youtube_podcast_fallback`):
- **Purpose**: Get podcast transcripts when other sources fail
- **When to call**: Transcript extraction stages (300-399)
- **Stage integration**: `get_youtube_podcast_transcript()` can be called from stage 320
- **Output**: Provides transcripts and metadata for podcast processing

### Integration Points

**Stage 110-150 (Content Discovery)**: Call YouTube history scraper
```python
from helpers.youtube_modules_integration import collect_youtube_history
result = collect_youtube_history(max_videos=100, days_back=7)
```

**Stage 320 (Transcript Extraction)**: Call YouTube podcast fallback
```python
from helpers.youtube_modules_integration import get_youtube_podcast_transcript
transcript_result = get_youtube_podcast_transcript(podcast_name, episode_title)
```

## Terminal Status Logic

### What makes a stage "terminal"?
- **≥ 590**: Content is complete and no further processing needed
- **599**: Special duplicate status for re-imported content
- **666/777/888**: Error states that may or may not be terminal

### Backward Compatibility
When stages are refined (e.g., splitting 199 into 198+199):
- New content uses the refined stages
- Old content is migrated to the closest equivalent
- Terminal statuses (≥590) remain terminal
- The system only cares about current stage values, not historical changes

### Example Evolution
**Before**: Stage 199 = "Acquisition Complete"
**After**: Stage 198 = "Pre-final checks", Stage 199 = "Acquisition Complete"
**Migration**: Content at 199 stays at 199, new content can go to 198→199
**Result**: Both are considered "acquisition complete" for deduplication purposes

## Usage Examples

### 1. CSV Re-import Scenario
```
Original content: https://example.com/article1 → Stage 590 (complete)
Re-import same URL: https://example.com/article1 → Stage 599 (duplicate)
```

### 2. Batch Processing
```
CSV file "batch_123.csv" with 100 URLs:
- 60 new URLs → Process through stages 100-590
- 30 existing URLs → Marked as stage 599 (duplicates)
- 10 failed URLs → Stage 777 (permanent error)
```

### 3. Stage Evolution
```
Current: Stage 590 = "Complete"
Future: Stage 585 = "Pre-archive checks", Stage 590 = "Complete"
Result: Both 585 and 590 are considered "complete enough" for deduplication
```

## Implementation Notes

### Single Source of Truth
All stage information is stored in the `content_transactions` table with:
- `stage`: Current numeric stage (0-599)
- `previous_stage`: Previous stage for progression tracking
- `metadata`: Additional context including terminal status

### Deduplication Logic
Content is considered a duplicate if existing content is at stage ≥ 590.
Duplicates get stage 599 and track the original content ID.

### Batch Processing
CSV files get unique batch IDs and process in series.
Each batch can be queried for completion status and statistics.

## Migration Strategy

When stage definitions change:
1. New content uses new stage definitions
2. Old content keeps existing stage values
3. Terminal stage logic (≥590) remains consistent
4. Migration scripts handle bulk updates if needed

This ensures the system is forward and backward compatible while maintaining clear terminal status definitions.