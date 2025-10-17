# Atlas User Guide

Atlas is a comprehensive personal content ingestion, processing, and search system designed to help you capture, organize, and discover insights from various content sources including articles, podcasts, documents, and more.

## Table of Contents

1. [Quick Start](#quick-start)
2. [System Overview](#system-overview)
3. [Content Processing](#content-processing)
4. [Search & Discovery](#search--discovery)
5. [Analytics Dashboard](#analytics-dashboard)
6. [API Usage](#api-usage)
7. [Configuration](#configuration)
8. [Troubleshooting](#troubleshooting)

## Quick Start

### Prerequisites
- Python 3.8+
- 4GB+ RAM recommended
- 10GB+ storage space

### Installation
1. Clone the repository and navigate to the Atlas directory
2. Copy `env.template` to `.env` and configure your settings
3. Install dependencies: `pip install -r requirements.txt`
4. Start the system: `./start_work.sh`

### First Steps
1. **Add content**: Place URLs in `inputs/articles.txt` or upload documents to `inputs/`
2. **Start processing**: The background service automatically processes new content every 30 minutes
3. **Access dashboard**: Open `https://atlas.khamel.com/api/v1/dashboard/` in your browser
4. **Search content**: Use the search API or dashboard interface

## System Overview

### Architecture Components

Atlas consists of several integrated components:

- **Content Ingestors**: Process articles, documents, podcasts, YouTube videos
- **Search Engine**: Full-text search with ranking and filtering
- **Analytics Engine**: Content consumption patterns and insights
- **API Framework**: RESTful API for all system operations
- **Dashboard**: Web interface for monitoring and interaction
- **Background Service**: Automated content processing and maintenance

### Content Types Supported

- **Articles**: Web articles, blog posts, news content
- **Documents**: PDF, TXT, Markdown files
- **Podcasts**: RSS feeds with transcript extraction
- **YouTube**: Videos with automatic transcript download
- **Instapaper**: CSV exports from Instapaper service

## Content Processing

### Automatic Processing

Atlas runs a unified background service that automatically processes:

- New articles every 30 minutes
- Document uploads every 30 minutes
- YouTube videos daily at 3 AM
- Podcast episodes every 4 hours
- Failed content retry every 8 hours

### Manual Processing

You can also trigger processing manually:

```bash
# Process specific content types
python process_articles.py
python process_podcasts.py
python helpers/youtube_processor.py

# Process all content
python run.py --all
```

### Content Sources

#### Articles
Place URLs in text files within the `inputs/` directory:
- `inputs/articles.txt` - General articles
- `inputs/tech.txt` - Technology articles
- Any `*.txt` file with one URL per line

#### Documents
Upload files directly to the `inputs/` directory:
- Supported formats: PDF, TXT, MD, DOCX
- Files are automatically detected and processed

#### Podcasts
Configure podcasts in `config/podcasts_full.csv`:
- RSS feed URL
- Podcast name and category
- Processing preferences

#### YouTube
Add video URLs to `inputs/youtube.txt` or enable daily sync:
- Automatic transcript download
- Metadata extraction
- Chapter detection

## Search & Discovery

### Search Interface

Access search through:
- **API**: `GET /api/v1/search/?q=your+query`
- **Dashboard**: Built-in search interface
- **Command line**: Using search scripts

### Search Features

- **Full-text search**: Search across all content
- **Content filtering**: Filter by type (article, document, podcast)
- **Date filtering**: Search within specific time ranges
- **Relevance ranking**: Results ranked by relevance and quality

### Search Examples

```bash
# Search for technology articles
curl "https://atlas.khamel.com/api/v1/search/?q=technology&type=article"

# Search with date filter
curl "https://atlas.khamel.com/api/v1/search/?q=AI&after=2024-01-01"

# Search specific content types
curl "https://atlas.khamel.com/api/v1/search/?q=python&type=document"
```

## Analytics Dashboard

### Accessing the Dashboard

Open your browser to: `https://atlas.khamel.com/api/v1/dashboard/`

### Dashboard Features

- **Content Statistics**: Total items, processing rates, storage usage
- **Processing Metrics**: Success rates, error tracking, performance data
- **Search Analytics**: Popular queries, search patterns
- **System Health**: Service status, database performance, error logs

### Dashboard Sections

1. **Overview**: Key metrics and system status
2. **Content**: Breakdown by type, processing statistics
3. **Search**: Search usage patterns and popular queries
4. **Performance**: System performance metrics and health checks

### Mobile Support

The dashboard is fully responsive and works on:
- Desktop browsers (Chrome, Firefox, Safari, Edge)
- Tablets (iPad, Android tablets)
- Mobile phones (iOS, Android)

## API Usage

### Base URL
`https://atlas.khamel.com/api/v1/`

### Available Endpoints

#### Health Check
```bash
GET /health
Response: {"status": "healthy"}
```

#### Search Content
```bash
GET /search/?q={query}&type={type}&limit={limit}
Parameters:
- q: Search query (required)
- type: Content type filter (optional)
- limit: Number of results (default: 10)
```

#### Get Content
```bash
GET /content/?type={type}&limit={limit}
Parameters:
- type: Content type (optional)
- limit: Number of items (default: 10)
```

#### Analytics
```bash
GET /analytics/
Response: Comprehensive analytics data
```

#### Dashboard
```bash
GET /dashboard/
Response: HTML dashboard interface
```

### Authentication

Currently, Atlas runs in single-user mode without authentication. For production deployment, consider implementing API key authentication.

### Rate Limiting

Default rate limits:
- 100 requests per minute per IP
- 1000 requests per hour per IP

## Configuration

### Environment Variables

Key configuration options in `.env`:

```bash
# Database Configuration
DATABASE_URL=sqlite:///atlas.db

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Processing Configuration
MAX_CONCURRENT_DOWNLOADS=5
RETRY_ATTEMPTS=3
RETRY_DELAY=300

# Content Processing
ENABLE_TRANSCRIPT_FIRST=true
PROCESS_ARTICLES_INTERVAL=30
PROCESS_PODCASTS_INTERVAL=240

# Search Configuration
SEARCH_RESULTS_LIMIT=100
ENABLE_CONTENT_RANKING=true
```

### Content Processing Settings

```bash
# Article Processing
ARTICLE_TIMEOUT=30
ENABLE_PAYWALL_BYPASS=false
USER_AGENT_ROTATION=true

# Podcast Processing
PODCAST_TRANSCRIPT_PRIORITY=high
MAX_PODCAST_FILE_SIZE=100MB

# Document Processing
MAX_DOCUMENT_SIZE=50MB
EXTRACT_IMAGES=false
```

### Search Configuration

```bash
# Search Engine Settings
INDEX_UPDATE_INTERVAL=60
ENABLE_FUZZY_SEARCH=true
SEARCH_CACHE_SIZE=1000

# Ranking Configuration
CONTENT_WEIGHT=0.7
TITLE_WEIGHT=0.3
RECENCY_WEIGHT=0.2
```

## Troubleshooting

### Common Issues

#### Atlas Won't Start

**Symptoms**: Error messages during startup, services not responding

**Solutions**:
1. Check Python version: `python --version` (requires 3.8+)
2. Install dependencies: `pip install -r requirements.txt`
3. Check port availability: `sudo netstat -tlnp | grep 8000`
4. Review logs: `tail -f logs/atlas.log`

#### Content Not Processing

**Symptoms**: Files in `inputs/` directory not being processed

**Solutions**:
1. Check background service: `./scripts/start_atlas_service.sh status`
2. Manual processing: `python run.py --all`
3. Check file permissions: `ls -la inputs/`
4. Review processing logs: `tail -f logs/processing.log`

#### Search Not Working

**Symptoms**: Search returns no results or errors

**Solutions**:
1. Check search index: `python scripts/populate_enhanced_search.py`
2. Verify database: `sqlite3 atlas.db ".tables"`
3. Test API: `curl https://atlas.khamel.com/api/v1/health`
4. Check search logs: `tail -f logs/search.log`

#### Dashboard Not Loading

**Symptoms**: Dashboard shows errors or doesn't display data

**Solutions**:
1. Clear browser cache and cookies
2. Check API server: `curl https://atlas.khamel.com/api/v1/analytics/`
3. Try different browser
4. Check dashboard logs in browser developer tools

### Performance Issues

#### Slow Processing

**Solutions**:
1. Reduce concurrent downloads: Set `MAX_CONCURRENT_DOWNLOADS=3` in `.env`
2. Increase processing intervals for less frequent updates
3. Monitor system resources: `top` or `htop`
4. Check disk space: `df -h`

#### High Memory Usage

**Solutions**:
1. Restart background services periodically
2. Reduce cache sizes in configuration
3. Process content in smaller batches
4. Monitor memory with: `free -h`

#### Database Performance

**Solutions**:
1. Run database optimization: `python scripts/optimize_database.py`
2. Check database integrity: `sqlite3 atlas.db "PRAGMA integrity_check"`
3. Rebuild search index: `python scripts/populate_enhanced_search.py`

### Getting Help

1. **Check logs**: Review log files in `logs/` directory
2. **Run diagnostics**: Use `python atlas_status.py --detailed`
3. **Test components**: Run individual test suites in `tests/`
4. **System status**: Check `./scripts/start_atlas_service.sh status`

### Log Files

- `logs/atlas.log` - Main application logs
- `logs/processing.log` - Content processing logs
- `logs/search.log` - Search engine logs
- `logs/api.log` - API request logs
- `logs/errors.log` - Error and exception logs

### Diagnostic Commands

```bash
# System status
python atlas_status.py --detailed

# Test all components
python -m pytest tests/ -v

# Check database integrity
sqlite3 atlas.db "PRAGMA integrity_check"

# Verify API endpoints
curl -s https://atlas.khamel.com/api/v1/health | jq

# Monitor processing
python3 monitor_atlas.py
```

For additional support or feature requests, refer to the project documentation or create an issue in the project repository.