# Atlas Project - Qwen Context Document

This document provides essential context about the Atlas project for Qwen Code, an interactive CLI agent. It covers the project's purpose, structure, key components, and development guidelines.

## Project Overview

**Atlas** is a **successful local-first content ingestion platform** that has achieved comprehensive content processing with 3,495+ articles, 951+ podcasts, and advanced recovery systems. The platform provides a solid foundation for knowledge management with various cognitive amplification modules at different implementation stages.

### Core Philosophy

Atlas provides **reliable content processing** with **future cognitive amplification potential**:

- **Local-First**: All data stored locally on your machine. No cloud dependencies for core features.
- **Core Complete**: Content ingestion mission achieved with 3,495+ articles and 951+ podcasts processed.
- **Resilient Processing**: 68% recovery success rate with comprehensive retry mechanisms.
- **Structured Output**: Clean, portable Markdown ready for any knowledge management system.
- **Privacy-Preserving**: Optional AI features with user-controlled API usage.

### Key Features

1. **Content Ingestion Pipeline**
   - Article Processing: 6-strategy fallback system (Direct HTTP → 12ft.io → Archive.today → Googlebot → Playwright → Wayback)
   - YouTube Integration: Transcript extraction with multi-language support
   - Podcast Processing: OPML parsing and episode download with transcription
   - Robust Retry System: Comprehensive failure handling with persistent queues

2. **Enhancement Modules** (Various implementation stages)
   - Basic Search Engine: Full-text search with SQLite persistence
   - Analytics Dashboard: Core structure with metrics collection framework
   - Content Processing: Summarization and classification capabilities
   - Metadata Discovery: YouTube history and GitHub repository detection (Complete)
   - Email Integration: Complete IMAP pipeline with authentication (Complete)

3. **Web Dashboard & API**
   - Interactive web interface for accessing cognitive features
   - RESTful API for programmatic access to all features

## Project Structure

```
Atlas/
├── run.py                    # Main CLI entry point
├── helpers/                  # Core processing modules
│   ├── article_fetcher.py   # Article ingestion (929 lines)
│   ├── youtube_ingestor.py  # YouTube processing (545 lines)
│   ├── podcast_ingestor.py  # Podcast processing (267 lines)
│   ├── metadata_manager.py  # Content metadata management
│   ├── path_manager.py      # File system organization
│   └── ...                  # 19 supporting modules
├── ask/                      # Cognitive amplification features
│   ├── proactive/           # Content surfacing
│   ├── temporal/            # Time relationships
│   ├── socratic/            # Question generation
│   ├── recall/              # Spaced repetition
│   └── insights/            # Pattern detection
├── web/                      # Web interface
│   ├── app.py               # FastAPI application
│   └── templates/           # HTML templates
├── ingest/                   # Advanced processing pipeline
├── process/                  # Content analysis
├── tests/                    # Comprehensive test suite
├── inputs/                   # Input files (articles.txt, etc.)
└── output/                   # Processed content storage
```

## Development Environment

### Prerequisites

- Python 3.9+
- Git
- Virtual environment (recommended)

### Setup

1. Clone the repository
2. Set up a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure the environment:
   ```bash
   cp .env.template .env
   ```

### Configuration

The minimum `.env` setup:
```env
# No mandatory configuration needed to run the application
# but for full AI features, you'll need an OpenRouter API key
OPENROUTER_API_KEY=your_api_key_here
```

For full AI features:
```env
OPENROUTER_API_KEY=your_api_key_here
MODEL=google/gemini-2.0-flash-lite-001
```

## Core Components

### Main Entry Point (`run.py`)

This is the primary CLI interface for running Atlas pipelines. It supports various commands for processing different content types:

- `--articles`: Run article ingestion
- `--podcasts`: Run podcast ingestion
- `--youtube`: Run YouTube ingestion
- `--instapaper-csv`: Process Instapaper CSV file
- `--recategorize`: Run recategorization
- `--all`: Run all ingestion types
- `--urls`: Process URLs from a file

### Helpers

The `helpers/` directory contains core modules for content processing:

- `article_fetcher.py`: Implements the 6-strategy article fetching system
- `podcast_ingestor.py`: Handles podcast feed parsing and episode processing
- `youtube_ingestor.py`: Manages YouTube video ingestion and transcript extraction
- `metadata_manager.py`: Centralized metadata handling for all content types
- `path_manager.py`: Standardized path creation and management
- `config.py`: Configuration loading and management

### Cognitive Features (`ask/`)

The `ask/` directory implements the cognitive amplification features:

- `proactive/`: Proactive content surfacing
- `temporal/`: Time-aware content relationships
- `socratic/`: Socratic question generation
- `recall/`: Spaced repetition scheduling
- `insights/`: Pattern detection and content analysis

### Web Interface (`web/`)

The web interface is built with FastAPI and provides:

- A dashboard for accessing cognitive features
- RESTful API endpoints for all functionality
- HTML templates for rendering the UI

## Development Guidelines

### Code Quality

- Follow existing code patterns and conventions
- Use type hints for all functions
- Write comprehensive docstrings
- Implement robust error handling with logging

### Configuration Management Rule

**ALL user-configurable values MUST be in `.env`** - Never hardcode:
- File paths, directories, URLs
- API keys, credentials, tokens
- Timeouts, retry counts, limits
- Feature flags, toggles
- Any value that might need adjustment

Always use `os.environ.get()` with sensible defaults and update `env.template` for new options.

### Automated Block Execution (YOLO Mode)

Atlas supports automated execution of Blocks 8-16 in sequence:

```bash
# Run automated block execution
python scripts/automated_block_executor.py
```

**Strategic Commit Pattern**: For each block implementation:
1. **Start commit**: Beginning of block implementation
2. **Component commits**: After each major component (every 4-6 tasks)
3. **Completion commit**: Block finished with context compacting
4. **Push to branch**: `feat/automated-blocks` for automated execution

**Context Management**: Systematically compact context between blocks to maintain focus and prevent token overflow during automated execution.

### Testing

Atlas includes a comprehensive testing infrastructure:

- Unit tests for individual modules
- Integration tests for end-to-end pipelines
- Run tests with `pytest`
- Aim for high test coverage

### Contributing

All development should be done in feature branches with Pull Requests. Never push directly to `main`.

## Current Status

**IMPORTANT**: See `ATLAS_IMPLEMENTATION_STATUS.md` for the authoritative current status.

As of August 2025, Atlas has achieved its core content processing mission with:

- ✅ **Core content ingestion complete**: 3,495+ articles, 951+ podcasts processed
- ✅ **Background service operational**: Continuous processing with auto-restart
- ✅ **Advanced features complete**: Blocks 15-16 fully implemented
- 🔧 **Enhancement modules**: Basic implementations of analytics, search, processing
- 📝 **Framework components**: Various deployment and integration frameworks ready

**Current Focus**: Validate and enhance existing framework components rather than build entirely new features.

## Implementation Reality

### ✅ **FULLY WORKING**
- **Core Platform (Blocks 1-3)**: Content ingestion pipeline
- **Block 15**: Intelligent metadata discovery (YouTube, GitHub, tech crawling)
- **Block 16**: Email integration pipeline
- **Background Service**: Unified processing with monitoring

### 🔧 **BASIC IMPLEMENTATION**
- **Block 8**: Analytics dashboard framework
- **Block 9**: Enhanced search engine basics
- **Block 10**: Content processing summarizer

### 📝 **FRAMEWORK/STUBS**
- **Blocks 4-7**: Export, Apple integration, Docker deployment
- **Block 14**: Production hardening scripts

### ❌ **NOT IMPLEMENTED**
- **Blocks 11-13**: Cognitive features, social integration (documentation only)

## Useful Commands

### Running Atlas

```bash
# Process articles from inputs/articles.txt
python run.py --articles

# Process YouTube videos from inputs/youtube.txt
python run.py --youtube

# Process podcasts from inputs/podcasts.opml
python run.py --podcasts

# Process everything
python run.py --all
```

### Background Service

```bash
# Start the background service
./scripts/start_atlas_service.sh start

# Check service status
./scripts/start_atlas_service.sh status
```

### Testing

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
```

### Status Check

```bash
# Quick status
python atlas_status.py

# Detailed status
python atlas_status.py --detailed
```