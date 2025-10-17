# Atlas Core Instructions

## Mission Statement
Atlas is a personal content management and cognitive amplification system that ingests, processes, and provides intelligent access to articles, podcasts, YouTube videos, and other digital content.

## Core Principles
1. **Never lose data** - All content must be preserved and recoverable
2. **Intelligent processing** - Leverage AI for summarization, analysis, and insights
3. **Unified interface** - Single system for all content types
4. **Production ready** - Reliable, scalable, and maintainable architecture

## System Architecture
- **Content Ingestion**: Multi-source ingestion (RSS, web articles, YouTube, podcasts)
- **Processing Pipeline**: AI-powered summarization and metadata extraction
- **Search & Discovery**: Full-text search with semantic capabilities
- **Analytics Dashboard**: Personal consumption insights and patterns
- **API Layer**: FastAPI-based REST API for all functionality
- **Cognitive Modules**: Proactive surfacing, temporal analysis, question generation

## Key Technologies
- Python 3.9+ with FastAPI
- SQLite databases (main content + search index)
- Background service automation with APScheduler
- AI integration (OpenAI, Anthropic, Hugging Face)
- Web scraping with Playwright and BeautifulSoup
- Audio processing with Whisper and youtube-transcript-api

## Development Workflow
1. Always check `ATLAS_COMPONENT_INDEX.md` before building new functionality
2. Use environment variables in `.env` for all configuration
3. Maintain comprehensive test coverage with pytest
4. Document all public APIs and architectural decisions
5. Follow semantic versioning for releases