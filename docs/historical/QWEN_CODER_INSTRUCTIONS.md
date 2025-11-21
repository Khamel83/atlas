# 🤖 Qwen-Coder Autonomous Atlas Development Instructions

## 🎯 Mission: Complete Atlas Implementation Blocks 7-14

You are an autonomous coding agent tasked with implementing the remaining Atlas development blocks. Work systematically through each task until you run out of tokens or complete all work.

### **Repository Context:**
- **Project**: Atlas - Personal Content Ingestion & Cognitive Amplification Platform
- **Location**: `/home/ubuntu/dev/atlas/`
- **Language**: Python 3.12+ with virtual environment `atlas_venv/`
- **Status**: Blocks 1-6 complete, Blocks 7-14 need implementation

---

## 🚀 STARTUP PROTOCOL

### **1. Environment Setup (CRITICAL FIRST STEPS)**
```bash
# Navigate to project
cd /home/ubuntu/dev/atlas

# Run startup script to understand current state
./start_work.sh

# Check detailed status
python atlas_status.py --detailed

# Load secrets and activate environment
source load_secrets.sh
source atlas_venv/bin/activate
```

### **2. Read Project Context**
- **PRIMARY**: Study `CLAUDE.md` thoroughly - contains current status and instructions
- **SPECS**: Read all files in `docs/specs/` for implementation details
  - `BLOCKS_7-10_IMPLEMENTATION.md` - iOS, Analytics, Search, AI Processing
  - `BLOCKS_11-13_IMPLEMENTATION.md` - Autonomous Discovery, Intelligence, Self-Optimization
  - `BLOCK_14_IMPLEMENTATION.md` - Production Hardening (Monitoring, SSL, Backups)
- **WORKFLOW**: Review `docs/workflow/` for processes and standards

### **3. Architecture Understanding**
- **Core modules**: `helpers/` directory contains main functionality
- **Background service**: `scripts/atlas_background_service.py` runs continuously
- **Processing pipeline**: `run.py` is main execution script
- **Testing**: `tests/` directory has comprehensive test suites

---

## 🎯 IMPLEMENTATION BLOCKS (Execute in Order)

### **BLOCK 7: Enhanced Apple Features (50-65 hours)**
**Priority**: HIGH - iOS integration and voice processing
**Location**: `docs/specs/BLOCKS_7-10_IMPLEMENTATION.md` (lines 1-180)

**Key Components to Build:**
1. **Advanced Siri Shortcuts** (`apple_shortcuts/siri_shortcuts.py`)
   - Multi-step automation workflows
   - Context-aware shortcuts with location/activity detection
   - Dynamic shortcut generation based on usage patterns

2. **Voice Processing Engine** (`apple_shortcuts/voice_processing.py`)
   - Multi-engine transcription (Whisper + OpenRouter)
   - Speaker diarization and voice activity detection
   - Smart audio preprocessing and enhancement

3. **Reading List Import** (`apple_shortcuts/reading_list_import.py`)
   - Bulk Safari Reading List extraction
   - Multi-format parsing (plist, HTML, JSON)
   - Intelligent deduplication and metadata enrichment

4. **iOS Share Extension** (`ios/` directory)
   - Swift code generation for iOS app
   - Offline queue management and background sync
   - Deep linking and app integration

**Acceptance Criteria:**
- [ ] Siri shortcuts work with voice commands
- [ ] Voice transcription supports multiple engines
- [ ] Reading List import processes 1000+ items efficiently
- [ ] iOS extension captures content from any app
- [ ] All components integrate with existing Atlas pipeline

### **BLOCK 8: Personal Analytics Dashboard (45-60 hours)**
**Priority**: HIGH - Web dashboard and insights
**Location**: `docs/specs/BLOCKS_7-10_IMPLEMENTATION.md` (lines 181-350)

**Key Components to Build:**
1. **Analytics Engine** (`analytics/analytics_engine.py`)
   - Content consumption pattern analysis
   - Reading velocity and engagement metrics
   - Topic clustering and interest mapping
   - Learning progress tracking

2. **Web Dashboard** (`web/` directory)
   - React-based modern interface
   - Real-time data visualization with D3.js
   - Interactive knowledge graphs
   - Responsive design for mobile/desktop

3. **Insight Generation** (`analytics/insight_generator.py`)
   - Automated pattern detection in content
   - Personalized recommendations engine
   - Progress reports and goal tracking
   - Trend analysis over time

4. **Data Export** (`analytics/export_manager.py`)
   - Multi-format export (PDF, CSV, JSON)
   - Scheduled report generation
   - Custom dashboard creation tools

**Acceptance Criteria:**
- [ ] Web dashboard loads in <2 seconds
- [ ] Analytics process 10,000+ content items efficiently
- [ ] Insights are actionable and personalized
- [ ] Exports work in multiple formats
- [ ] Dashboard updates in real-time

### **BLOCK 9: Enhanced Search & Indexing (40-55 hours)**
**Priority**: MEDIUM - Advanced search capabilities
**Location**: `docs/specs/BLOCKS_7-10_IMPLEMENTATION.md` (lines 351-520)

**Key Components to Build:**
1. **Semantic Search Engine** (`search/semantic_search.py`)
   - Vector embeddings with FAISS/ChromaDB
   - Semantic similarity matching
   - Multi-modal search (text, audio, images)
   - Contextual query understanding

2. **Advanced Indexing** (`search/advanced_indexer.py`)
   - Real-time incremental indexing
   - Content relationship mapping
   - Tag-based hierarchical organization
   - Cross-reference detection

3. **Search Interface** (`search/search_api.py`)
   - RESTful API endpoints
   - Query suggestion and autocomplete
   - Faceted search with filters
   - Search result ranking and personalization

4. **Knowledge Graph** (`search/knowledge_graph.py`)
   - Entity extraction and linking
   - Relationship mapping between content
   - Graph-based navigation
   - Visualization integration

**Acceptance Criteria:**
- [ ] Search responds in <500ms for 10,000+ items
- [ ] Semantic search finds conceptually related content
- [ ] Knowledge graph visualizes content relationships
- [ ] API supports complex queries and filters
- [ ] Search accuracy >90% for user queries

### **BLOCK 10: Advanced Content Processing (35-50 hours)**
**Priority**: MEDIUM - AI-powered content enhancement
**Location**: `docs/specs/BLOCKS_7-10_IMPLEMENTATION.md` (lines 521-680)

**Key Components to Build:**
1. **AI Summarization** (`processing/ai_summarizer.py`)
2. **Content Enhancement** (`processing/content_enhancer.py`)
3. **Smart Clustering** (`processing/smart_clustering.py`)
4. **Recommendation Engine** (`processing/recommender.py`)

### **BLOCK 11: Autonomous Discovery Engine (25-35 hours)**
**Priority**: HIGH - AI-powered content discovery
**Location**: `docs/specs/BLOCKS_11-13_IMPLEMENTATION.md`

**Key Components to Build:**
1. **AI Source Discovery** (`discovery/source_analyzer.py`)
2. **Quality Filtering** (`discovery/quality_assessor.py`)
3. **Discovery Automation** (`discovery/discovery_scheduler.py`)
4. **Cross-Platform Discovery** (`discovery/cross_platform.py`)

### **BLOCK 12: Enhanced Content Intelligence (25-35 hours)**
**Priority**: MEDIUM - Advanced AI analysis
**Location**: `docs/specs/BLOCKS_11-13_IMPLEMENTATION.md`

**Key Components to Build:**
1. **Multi-Perspective Summarization** (`intelligence/multi_perspective_summarizer.py`)
2. **Content Relationship Analysis** (`intelligence/relationship_analyzer.py`)
3. **Intelligent Insights** (`intelligence/insight_generator.py`)
4. **Predictive Intelligence** (`intelligence/relevance_predictor.py`)

### **BLOCK 13: Self-Optimizing Intelligence (25-35 hours)**
**Priority**: LOW - System optimization
**Location**: `docs/specs/BLOCKS_11-13_IMPLEMENTATION.md`

**Key Components to Build:**
1. **Performance Optimization** (`optimization/performance_monitor.py`)
2. **Adaptive Learning** (`optimization/behavior_learner.py`)
3. **Self-Healing System** (`optimization/error_detector.py`)
4. **Intelligence Amplification** (`optimization/cognitive_optimizer.py`)

### **BLOCK 14: Personal Production Hardening (30-40 hours)**
**Priority**: HIGH - Production deployment
**Location**: `docs/specs/BLOCK_14_IMPLEMENTATION.md`

**Key Components to Build:**
1. **Monitoring System** (`monitoring/prometheus_setup.py`)
2. **SSL + Authentication** (`ssl/ssl_setup.sh`)
3. **Backup System** (`backup/database_backup.py`)
4. **Maintenance Automation** (`maintenance/atlas_maintenance.py`)
5. **DevOps Tools** (`devops/git_deploy.py`)
6. **OCI Optimizations** (`oci/free_tier_monitor.py`)
7. **Convenience Features** (`lazy/mobile_dashboard.py`)

**Acceptance Criteria:**
- [ ] atlas.khamel.com works with HTTPS and authentication
- [ ] Daily backups work automatically
- [ ] Monitoring alerts work via email
- [ ] System maintains itself automatically
- [ ] Mobile dashboard is fully functional

---

## 🔧 DEVELOPMENT STANDARDS

### **Code Quality Requirements:**
- **Type hints**: All functions must have complete type annotations
- **Documentation**: Comprehensive docstrings using Google style
- **Error handling**: Robust exception handling with logging
- **Testing**: Unit tests for all major functionality
- **Performance**: Optimize for processing 10,000+ content items

### **Architecture Patterns:**
- **Dependency injection**: Use configuration-based setup
- **Event-driven**: Emit events for processing pipeline
- **Modular design**: Components should be loosely coupled
- **Async support**: Use asyncio for I/O operations where beneficial

### **Integration Requirements:**
- **Background service**: All new features must integrate with `atlas_background_service.py`
- **Database**: Use existing metadata management system
- **API consistency**: Follow existing endpoint patterns
- **Configuration**: Use environment variables and config files

---

## 🧪 TESTING STRATEGY

### **Test Coverage Requirements:**
```bash
# Run comprehensive test suite
python -m pytest tests/ -v --cov=. --cov-report=term-missing

# Target: >90% coverage for new code
# All tests must pass before moving to next component
```

### **Integration Testing:**
- Test with real data from existing Atlas pipeline
- Verify performance with large datasets (1000+ items)
- Test all API endpoints with various inputs
- Validate mobile responsiveness and cross-browser compatibility

### **Performance Benchmarks:**
- Search: <500ms response time
- Analytics: Process 1000 items in <10 seconds
- Dashboard: Load in <2 seconds
- Background processing: No memory leaks over 24+ hours

---

## 🚀 EXECUTION STRATEGY

### **Multi-Turn Workflow:**
1. **Read task** (max 1 turn) - NO over-analysis
2. **Code immediately** - Start with working skeleton
3. **Test + fix** - Run, see errors, fix quickly
4. **Move on** - If stuck >5min, skip to next task
5. **Compress context** - After each component, summarize progress only
6. **NEVER block** - Every task can work independently

### **Priority Order (if token-limited):**
1. **Block 7.1**: Advanced Siri Shortcuts (highest user value)
2. **Block 8.1**: Analytics Engine (enables dashboard)
3. **Block 8.2**: Web Dashboard (visible user interface)
4. **Block 7.2**: Voice Processing (unique Atlas capability)
5. **Block 9.1**: Semantic Search (core functionality)
6. **Continue systematically** through remaining components

### **Error Recovery:**
- **5-minute rule**: If stuck >5min, skip and continue
- **Log and move**: Note the issue, continue to next task
- **No blocking**: Every component works independently
- **Ship working code**: Partial implementation > no implementation

### **Token Management:**
- **SKIP-AND-CONTINUE**: If stuck >5min on any task, skip it and move on
- **Minimal context**: After each component, compress context to essentials only
- **Core functionality first** before optimization
- **Working code > perfect code** - ship it, fix later
- **No analysis paralysis** - start coding within 2 prompts max

---

## 📋 SUCCESS METRICS

### **Completion Targets:**
- **Minimum viable**: Block 7.1 + Block 8.1 (Siri shortcuts + Analytics)
- **Good progress**: 2 complete blocks (50%+ of remaining work)
- **Excellent**: 3+ blocks with integration testing
- **Outstanding**: All 4 blocks with comprehensive testing

### **Quality Indicators:**
- [ ] All implemented code has tests
- [ ] No breaking changes to existing functionality
- [ ] Performance benchmarks met
- [ ] Documentation updated for new features
- [ ] Background service continues running throughout development

---

## 🎯 FINAL INSTRUCTIONS

**Your goal is to write production-ready code that extends Atlas into a complete cognitive amplification platform. Work systematically, test frequently, and maintain the existing system's reliability.**

**Start with Block 7.1 (Advanced Siri Shortcuts) and work through the specification methodically. The Atlas team trusts you to make architectural decisions that align with the existing codebase patterns.**

**Remember: Atlas processes real user content and must never lose data. Prioritize robustness over features, and ensure all new code integrates seamlessly with the background ingestion system.**

**BEGIN IMPLEMENTATION NOW. Good luck! 🚀**