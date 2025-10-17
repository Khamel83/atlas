# Technical Specification

This is the technical specification for the spec detailed in @.agent-os/specs/2025-07-30-system-completion/spec.md

## Technical Requirements

### Recording Reliability Foundation
- Fix LaunchAgent service paths to point to workspace/ directory structure
- Consolidate all configuration into single config.json with proper fallbacks
- Implement process monitoring with automatic restart on failure
- Add disk space monitoring with automatic cleanup of old files
- Implement permission checking with clear error messages for missing mic/disk access
- Add network connectivity checking for cloud-dependent features
- Create graceful degradation when cloud services unavailable

### Analysis Architecture Unification
- Create single analysis_router.py that replaces complex existing implementations
- Maintain simple interface: analyze_router.route(transcript_file, choice="local"|"cloud"|"both")
- Preserve all existing functionality but through simplified, unified interface
- Update transcribe.py to use new router instead of direct imports
- Retire analyze_local.py and process_gemini.py complexity while preserving features
- Maintain backward compatibility with existing analysis files and formats

### Search & Memory System
- Implement search_engine.py using SQLite with FTS5 extension for full-text search
- Create semantic_search.py using sentence-transformers for vector embeddings
- Design schema: transcripts table (id, file_path, content, date, analysis_summary)
- Add embeddings table (transcript_id, embedding_vector) for semantic search
- Implement batch_indexer.py to retroactively index all existing transcripts
- Create search ranking combining keyword relevance + semantic similarity + recency

### Web Interface
- Build simple Flask-based web interface for search and browsing
- Implement search results pagination with transcript snippet previews
- Add date range filtering and analysis type filtering
- Create timeline view showing conversation patterns over time
- Implement simple authentication (basic auth) for security
- Design responsive interface that works on mobile devices

### Testing & Validation
- Create comprehensive test suite for recording reliability scenarios
- Add integration tests that simulate service failures and recovery
- Implement load testing for search performance with large transcript volumes
- Create test data generators for various transcript formats and sizes
- Add monitoring tests that validate system health over extended periods

## External Dependencies

- **sentence-transformers** - For semantic search vector embeddings
- **flask** - For web interface
- **sqlite3** - Built into Python, for search database
- All existing dependencies (requests, ollama, etc.) maintained