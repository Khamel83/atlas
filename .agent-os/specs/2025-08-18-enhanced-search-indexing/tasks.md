# Tasks: Enhanced Search Indexing for Transcript Content

## Phase 1: Transcript Content Parser (2 hours)

### Task 1.1: Create Transcript Parser Module
**File**: `helpers/transcript_parser.py`

**Atomic Implementation**:
```python
class TranscriptParser:
    def parse_transcript(self, raw_text, metadata):
        # Extract speaker names using common patterns
        # Identify dialogue segments and Q&A structure
        # Handle timestamps and topic transitions
        # Return structured JSON: {speakers, segments, topics}

    def extract_speakers(self, text):
        # Regex patterns for "Speaker:", "Host:", "[Name]:" formats
        # Return list of unique speakers

    def segment_by_speaker(self, text, speakers):
        # Split transcript into speaker segments
        # Include start/end positions and timestamps

    def extract_topics(self, segments):
        # Simple keyword extraction for topic identification
        # Group related segments by topic similarity
```

**Acceptance Criteria**:
- [ ] Handles common transcript formats (Lex Fridman, This American Life, etc.)
- [ ] Extracts speaker names with 90%+ accuracy
- [ ] Segments dialogue with proper attribution
- [ ] Identifies topic transitions and key discussion points

### Task 1.2: Integrate Parser with Ingestion Pipeline
**Files**: `helpers/podcast_transcript_ingestor.py`, `process_podcasts.py`

**Atomic Implementation**:
```python
# Add to existing ingestor
from helpers.transcript_parser import TranscriptParser

def process_transcript_content(self, transcript_text, metadata):
    parser = TranscriptParser()
    structured_data = parser.parse_transcript(transcript_text, metadata)

    # Store structured data in database
    self.store_transcript_segments(structured_data)

    # Maintain backward compatibility
    return structured_data
```

**Acceptance Criteria**:
- [ ] All new transcripts automatically parsed during ingestion
- [ ] Existing transcripts can be reprocessed with parser
- [ ] No breaking changes to current ingestion workflow
- [ ] Structured data stored alongside raw transcript content

## Phase 2: Enhanced Search Indexing (2 hours)

### Task 2.1: Create Enhanced Search Indexer
**File**: `helpers/transcript_search_indexer.py`

**Atomic Implementation**:
```python
class TranscriptSearchIndexer:
    def index_transcript_segments(self, structured_transcript):
        # Create searchable index for each segment
        # Build speaker-specific search terms
        # Generate topic clusters and tags
        # Store in search database with metadata

    def build_topic_clusters(self, all_segments):
        # Group segments by topic similarity
        # Create cross-episode topic connections
        # Generate topic-based recommendations

    def create_speaker_index(self, segments, speaker_name):
        # Build speaker-specific search index
        # Weight Q&A patterns appropriately
        # Enable "what did X say about Y" queries
```

**Acceptance Criteria**:
- [ ] Segments indexed with speaker, topic, and content metadata
- [ ] Topic clustering works across multiple episodes
- [ ] Speaker-specific search indexes created
- [ ] Search performance remains fast with enhanced indexing

### Task 2.2: Update Search API for Transcript Queries
**File**: `api/search.py` (or create new transcript search module)

**Atomic Implementation**:
```python
def search_transcripts(query, speaker=None, topic=None, episode_id=None):
    # Enhanced search with transcript-specific filters
    # Return results with speaker attribution and context
    # Include conversation flow around relevant segments

def get_speaker_topics(speaker_name):
    # Return all topics discussed by specific speaker
    # Enable "what topics did X discuss" queries

def find_related_segments(segment_id, limit=5):
    # Topic-based content recommendations
    # Cross-episode related content discovery
```

**Acceptance Criteria**:
- [ ] API supports speaker-filtered searches
- [ ] Topic-based search and recommendations work
- [ ] Results include conversation context (before/after segments)
- [ ] Backward compatibility with existing search API

## Phase 3: Search Quality Enhancement (1 hour)

### Task 3.1: Implement Conversation-Aware Ranking
**File**: `helpers/transcript_search_ranking.py`

**Atomic Implementation**:
```python
class ConversationRanking:
    def rank_transcript_results(self, results, query_type):
        # Weight Q&A segments higher for questions
        # Boost topic transitions and key insights
        # Prioritize guest responses over host questions

    def calculate_relevance_score(self, segment, query):
        # Enhanced scoring for conversational content
        # Consider speaker importance and segment type
        # Factor in topic clustering and context
```

**Acceptance Criteria**:
- [ ] Q&A segments ranked appropriately for question queries
- [ ] Topic transitions weighted higher for discovery
- [ ] Guest insights prioritized over host questions
- [ ] Overall search relevance improved for conversational content

### Task 3.2: Add Structured Search Result Formatting
**File**: `api/search_results_formatter.py`

**Atomic Implementation**:
```python
def format_transcript_results(results):
    # Include speaker attribution in results
    # Show conversation context around matches
    # Add timestamp links for audio/video content
    # Format for both API and web interface consumption

def generate_conversation_context(segment_id, context_lines=3):
    # Return surrounding dialogue for context
    # Include speaker transitions and topic flow
```

**Acceptance Criteria**:
- [ ] Search results show speaker and conversation context
- [ ] Timestamp links included when available
- [ ] Results formatted for both API and UI consumption
- [ ] Context provides meaningful dialogue flow

## Database Schema Updates

### Task: Add Transcript Segment Tables
**File**: `migrations/add_transcript_segments.sql`

**Atomic Implementation**:
```sql
-- Create transcript segments table
CREATE TABLE IF NOT EXISTS transcript_segments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    episode_id INTEGER NOT NULL,
    speaker TEXT,
    content TEXT NOT NULL,
    start_timestamp REAL,
    end_timestamp REAL,
    topic_tags TEXT, -- JSON array
    segment_type TEXT, -- question, answer, transition, discussion
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (episode_id) REFERENCES episodes(id)
);

-- Create topic clusters table
CREATE TABLE IF NOT EXISTS topic_clusters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_name TEXT UNIQUE NOT NULL,
    related_segments TEXT, -- JSON array of segment IDs
    episode_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for search performance
CREATE INDEX idx_transcript_segments_speaker ON transcript_segments(speaker);
CREATE INDEX idx_transcript_segments_episode ON transcript_segments(episode_id);
CREATE INDEX idx_transcript_segments_content ON transcript_segments(content);
CREATE INDEX idx_topic_clusters_name ON topic_clusters(topic_name);
```

## Acceptance Criteria

### Functional Requirements
- [ ] Transcript parser extracts speakers and segments accurately
- [ ] Enhanced search supports speaker and topic filtering
- [ ] Search results include conversation context and attribution
- [ ] Topic clustering enables cross-episode content discovery

### Performance Requirements
- [ ] Search performance remains under 500ms for typical queries
- [ ] Indexing processes transcripts without blocking ingestion
- [ ] Database queries optimized with proper indexes
- [ ] Memory usage reasonable during bulk processing

### Quality Requirements
- [ ] Speaker extraction accuracy >90% for well-formatted transcripts
- [ ] Topic clustering produces meaningful content groupings
- [ ] Search relevance improved for conversational content
- [ ] Backward compatibility maintained with existing search

### Integration Requirements
- [ ] Seamless integration with existing ingestion pipeline
- [ ] Compatible with current database schema (additive changes only)
- [ ] API maintains existing endpoints while adding new functionality
- [ ] No breaking changes to current search functionality

## Success Metrics

### Immediate
- [ ] Parser processes existing 221+ transcripts successfully
- [ ] Enhanced search API operational with new endpoints
- [ ] Topic clustering identifies meaningful content groups

### Short-term
- [ ] Search relevance measurably improved for transcript content
- [ ] Speaker-specific queries return accurate, contextual results
- [ ] Cross-episode topic discovery working effectively

### Long-term
- [ ] Enhanced search becomes primary interface for transcript content
- [ ] Topic clustering enables content recommendation features
- [ ] System scales to handle 400+ transcripts after bulk discovery

---

**Total Estimated Time**: 5 hours across 3 phases
**Dependencies**: Transcript content from discovery systems
**Risk Level**: Medium (text processing complexity, search performance)
**Output**: Production-ready transcript search with speaker awareness and topic clustering