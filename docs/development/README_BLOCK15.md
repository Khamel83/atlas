# Atlas Block 15: Intelligent Metadata Discovery & Code Repository Mining

This module implements Atlas Block 15, which extends Atlas with intelligent metadata discovery and code repository mining capabilities. This block automatically extracts, crawls, and indexes related repositories, code examples, and technical resources mentioned in content.

## Overview

Block 15 enhances the Atlas personal knowledge management system by:

1. **YouTube Integration** - Import watch history and process videos through the Atlas pipeline
2. **GitHub Detection** - Identify and extract metadata from GitHub repositories mentioned in content
3. **Technical Resource Crawling** - Discover documentation, API references, and tutorials
4. **Content Enhancement** - Automatically enrich content with discovered metadata and cross-references

## Components

### YouTube Integration
- `integrations/youtube_history_importer.py` - Parses Google Takeout JSON for YouTube watch history
- `integrations/youtube_api_client.py` - YouTube Data API v3 client
- `integrations/youtube_content_processor.py` - Processes YouTube videos through Atlas pipeline

### GitHub Repository Detection
- `crawlers/github_detector.py` - Detects GitHub URLs and extracts repository metadata

### Technical Resource Crawling
- `crawlers/tech_resource_crawler.py` - Crawls documentation and extracts technical resources

### Content Enhancement
- `crawlers/content_enhancer.py` - Enhances content with discovered metadata

## Features

### YouTube Integration
- ✅ Google Takeout import for watch history
- ✅ YouTube Data API v3 integration
- ✅ Transcript extraction for videos
- ✅ Content processing through Atlas pipeline
- ✅ Watch pattern analytics

### GitHub Repository Detection
- ✅ GitHub URL pattern detection
- ✅ Repository metadata extraction
- ✅ README file parsing
- ✅ Code example identification
- ✅ Repository activity tracking

### Technical Resource Crawling
- ✅ Documentation link detection
- ✅ API reference extraction
- ✅ Dependency identification
- ✅ Tutorial crawling
- ✅ Technology stack mapping

### Content Enhancement
- ✅ Metadata enhancement
- ✅ GitHub repository linking
- ✅ Code example integration
- ✅ Cross-reference system
- ✅ Searchable index building

## Installation

1. Install dependencies:
   ```bash
   pip install -r requirements-block15.txt
   ```

2. Set up API keys (if using YouTube or GitHub APIs):
   - YouTube Data API v3 key
   - GitHub personal access token (optional but recommended)

## Usage

### Running Tests
```bash
python tests/test_block15.py
```

### Running Demo
```bash
python scripts/demo_block15.py
```

### Using Individual Components

#### YouTube History Importer
```python
from integrations.youtube_history_importer import YouTubeHistoryImporter

importer = YouTubeHistoryImporter("path/to/YouTube/history.json")
videos = importer.parse_history_file()
importer.integrate_with_atlas_pipeline()
```

#### GitHub Detector
```python
from crawlers.github_detector import GitHubDetector

detector = GitHubDetector()
content = "Check out https://github.com/python/cpython"
urls = detector.detect_github_urls(content)
repositories = detector.extract_repository_metadata(urls)
```

#### Technical Resource Crawler
```python
from crawlers.tech_resource_crawler import TechResourceCrawler

crawler = TechResourceCrawler()
content = "See https://docs.python.org/3/ for documentation"
urls = crawler.detect_documentation_links(content)
api_refs = crawler.extract_api_references(urls)
```

#### Content Enhancer
```python
from crawlers.content_enhancer import ContentEnhancer

enhancer = ContentEnhancer()
articles = [{"title": "Python Tutorial", "content": "Learn Python programming"}]
metadata = {"github_repos": [...], "api_references": [...]}
enhanced_articles = enhancer.enhance_content_with_metadata(articles, metadata)
```

## Testing

All components have been thoroughly tested with unit tests. Run the tests with:

```bash
python tests/test_block15.py
```

## Documentation

See `BLOCK15_IMPLEMENTATION_SUMMARY.md` for detailed implementation information.

## Files

```
├── integrations/
│   ├── youtube_history_importer.py
│   ├── youtube_api_client.py
│   └── youtube_content_processor.py
├── crawlers/
│   ├── github_detector.py
│   ├── tech_resource_crawler.py
│   └── content_enhancer.py
├── tests/
│   └── test_block15.py
├── scripts/
│   └── demo_block15.py
├── requirements-block15.txt
├── BLOCK15_IMPLEMENTATION_SUMMARY.md
└── README.md
```

## Dependencies

- requests
- beautifulsoup4
- google-api-python-client
- google-auth
- google-auth-oauthlib
- google-auth-httplib2
- python-dateutil

## License

This implementation is part of the Atlas project and follows the same license as the main project.