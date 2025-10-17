# Spec Tasks

## Tasks

- [x] 1. **Recording Reliability Foundation**
  - [x] 1.1 Fix LaunchAgent service configuration paths to point to workspace/ directory
  - [x] 1.2 Test and verify audio recording service starts correctly on boot
  - [x] 1.3 Implement automatic restart on service failure with exponential backoff
  - [x] 1.4 Add disk space monitoring with automatic cleanup of audio files older than 30 days
  - [x] 1.5 Implement permission verification with clear error messages for mic/disk access
  - [x] 1.6 Test service reliability under various failure scenarios
  - [x] 1.7 Verify all recording reliability tests pass

- [ ] 2. **Analysis Architecture Unification**
  - [x] 2.1 Create analysis_router.py with unified interface for local/cloud/both analysis
  - [x] 2.2 Clean rebuild with markdown output (no backward compatibility per user preference)
  - [ ] 2.3 Update transcribe.py to use analysis_router instead of direct imports
  - [ ] 2.4 Test analysis router with existing transcript files to ensure compatibility
  - [ ] 2.5 Migrate complex features from analyze_local.py and process_gemini.py to router
  - [ ] 2.6 Remove deprecated analysis files after confirming feature parity
  - [ ] 2.7 Verify all analysis functionality works through unified interface

- [ ] 3. **Search Engine Foundation**
  - [ ] 3.1 Design SQLite database schema for transcripts and analysis storage
  - [ ] 3.2 Implement search_engine.py with SQLite + FTS5 for full-text search
  - [ ] 3.3 Create batch_indexer.py to retroactively index existing transcripts
  - [ ] 3.4 Test search performance with large volumes of transcript data
  - [ ] 3.5 Implement search result ranking algorithm combining relevance + recency
  - [ ] 3.6 Add date range and content type filtering capabilities
  - [ ] 3.7 Verify search engine handles all existing transcript formats correctly

- [ ] 4. **Semantic Search Implementation**
  - [ ] 4.1 Install and configure sentence-transformers for vector embeddings
  - [ ] 4.2 Implement semantic_search.py with embedding generation and similarity search
  - [ ] 4.3 Create embeddings database table and storage optimization
  - [ ] 4.4 Implement hybrid search combining keyword + semantic results
  - [ ] 4.5 Test semantic search with various query types and transcript content
  - [ ] 4.6 Optimize embedding generation for batch processing of existing transcripts
  - [ ] 4.7 Verify semantic search performance meets usability requirements

- [ ] 5. **Web Interface Development**
  - [ ] 5.1 Create Flask-based web application structure with basic routing
  - [ ] 5.2 Implement search interface with query input and results display
  - [ ] 5.3 Add pagination for search results with transcript snippet previews
  - [ ] 5.4 Create timeline view showing conversation patterns over time
  - [ ] 5.5 Implement basic authentication for security
  - [ ] 5.6 Design responsive interface that works on mobile devices
  - [ ] 5.7 Test web interface with various search scenarios and data volumes

- [ ] 6. **System Integration & Testing**
  - [ ] 6.1 Create comprehensive integration tests for end-to-end system functionality
  - [ ] 6.2 Implement recording reliability test suite with failure simulation
  - [ ] 6.3 Test batch processing of all existing transcripts through new analysis pipeline
  - [ ] 6.4 Verify search system can handle retroactive indexing of historical data
  - [ ] 6.5 Load test system with realistic usage patterns and data volumes
  - [ ] 6.6 Create monitoring and health check endpoints for system status
  - [ ] 6.7 Verify all tests pass and system meets reliability requirements

- [ ] 7. **Documentation & Deployment**
  - [ ] 7.1 Update system documentation with new architecture and capabilities
  - [ ] 7.2 Create deployment guide for setting up complete system from scratch
  - [ ] 7.3 Document search interface usage and advanced query capabilities
  - [ ] 7.4 Create troubleshooting guide for common issues and recovery procedures
  - [ ] 7.5 Update README with current system status and capabilities
  - [ ] 7.6 Commit all changes to GitHub with comprehensive commit messages
  - [ ] 7.7 Update CLAUDE.md with final system status and handoff information