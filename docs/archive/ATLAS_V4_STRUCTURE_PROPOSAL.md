# Atlas v4 Project Structure Proposal

## Overview
Simple, modular architecture following the "tools, not frameworks" philosophy. Each component is a standalone tool that does one thing well.

## Directory Structure

```
atlas/
├── src/                           # Source code (main package)
│   └── atlas/
│       ├── __init__.py            # Package initialization
│       ├── cli.py                 # CLI entry point (argparse)
│       ├── config.py              # Configuration loader
│       ├── logging.py             # Logging setup and utilities
│       │
│       ├── core/                  # Core utilities (shared)
│       │   ├── __init__.py
│       │   ├── content_hash.py    # SHA256 content hashing
│       │   ├── url_normalizer.py  # URL normalization rules
│       │   ├── validator.py       # Content validation engine
│       │   └── deduplicator.py    # Deduplication logic
│       │
│       ├── ingest/                # Ingestion modules (independent)
│       │   ├── __init__.py
│       │   ├── base.py           # BaseIngestor interface
│       │   ├── gmail.py          # Gmail IMAP ingestor
│       │   ├── rss.py            # RSS feed ingestor
│       │   └── youtube.py        # YouTube ingestor
│       │
│       ├── storage/               # File persistence
│       │   ├── __init__.py
│       │   ├── writer.py         # Markdown+YAML file writer
│       │   └── organizer.py      # Directory structure manager
│       │
│       ├── retry/                 # Error handling
│       │   ├── __init__.py
│       │   ├── classifier.py     # Failure taxonomy
│       │   └── engine.py         # Retry with backoff
│       │
│       └── interface/             # External interfaces
│           ├── __init__.py
│           └── telegram_bot.py   # Telegram bot
│
├── config/                        # Configuration files
│   ├── config.yaml              # Main configuration
│   ├── sources/                 # Source definitions
│   │   ├── gmail.yaml          # Gmail account configs
│   │   ├── rss_feeds.yaml      # RSS feed configs
│   │   └── youtube.yaml        # YouTube channel configs
│   └── systemd/                 # Systemd service files
│       ├── atlas-ingest.service
│       └── atlas-ingest.timer
│
├── vault/                        # Content storage (obsidian format)
│   ├── inbox/                  # Main content directory
│   │   ├── newsletters/        # Newsletter content
│   │   ├── podcasts/          # Podcast episodes
│   │   ├── articles/          # Web articles
│   │   ├── youtube/           # YouTube videos
│   │   └── emails/            # Email archives
│   ├── logs/                  # Processing logs
│   └── failures/              # Failed items for retry
│
├── tests/                       # Test suite
│   ├── unit/                  # Unit tests
│   │   ├── test_content_hash.py
│   │   ├── test_url_normalizer.py
│   │   ├── test_validator.py
│   │   └── test_deduplicator.py
│   ├── integration/           # Integration tests
│   │   ├── test_ingest_pipeline.py
│   │   └── test_full_workflow.py
│   └── test_data/            # Sample data for testing
│       ├── sample_rss.xml
│       ├── sample_email.eml
│       └── sample_content.md
│
├── scripts/                     # Utility scripts
│   ├── install.sh             # Installation script
│   ├── setup_vault.sh         # Initialize vault structure
│   └── backup.sh              # Backup utility
│
├── docs/                       # Documentation
│   ├── CONFIGURATION.md       # Configuration guide
│   ├── DEPLOYMENT.md          # Deployment instructions
│   └── API.md                 # API reference
│
├── requirements.txt            # Python dependencies
├── pyproject.toml             # Project configuration
├── README.md                  # Project documentation
├── LICENSE                    # License file
└── .gitignore                # Git ignore patterns
```

## Module Design Philosophy

### 1. Simple Functions Over Classes
Each ingestor is a simple Python script that can run independently:

```python
# src/atlas/ingest/gmail.py
def ingest_gmail(source_config: dict) -> List[dict]:
    """Ingest Gmail messages and return content items."""
    # Simple, direct implementation
    # < 300 lines total
    pass

if __name__ == "__main__":
    # Can run standalone: python -m atlas.ingest.gmail
    config = load_config("config/sources/gmail.yaml")
    results = ingest_gmail(config)
    print(f"Processed {len(results)} messages")
```

### 2. Stateless Operations
Each run is independent and idempotent:

```python
# src/atlas/ingest/rss.py
def ingest_rss(feed_url: str, since_date: datetime = None) -> List[dict]:
    """Ingest RSS feed items since given date."""
    # No complex state management
    # Each call produces the same result for same inputs
    pass
```

### 3. File-Based Persistence
All data stored as Markdown+YAML files:

```python
# src/atlas/storage/writer.py
def write_content(item: dict, vault_path: str) -> Path:
    """Write content item as Markdown+YAML file."""
    # Direct file operations
    # No database dependencies
    # Obsidian-native format
    pass
```

## Key Architectural Decisions

### 1. Package Structure
- **`src/atlas/`**: Main package following modern Python standards
- **No complex import hierarchies**: Flat structure where possible
- **Clear separation**: Core utilities vs ingestion vs storage vs interfaces

### 2. Configuration Management
```yaml
# config/config.yaml - Simple, readable YAML
vault:
  root: "./vault"

logging:
  level: INFO
  file: "vault/logs/atlas.log"

telegram:
  bot_token: "${TELEGRAM_BOT_TOKEN}"  # Environment variable support
  allowed_user_id: 123456789
```

### 3. Source Configuration
```yaml
# config/sources/gmail.yaml - Per-source configs
sources:
  - name: "personal-gmail"
    type: "gmail"
    connection:
      imap_host: "imap.gmail.com"
      email: "omar.personal@gmail.com"
      app_password: "${GMAIL_APP_PASSWORD}"
    filters:
      subject_contains: ["[Newsletter]", "Digest"]
      since_days: 7
    validation:
      min_length: 300
      require_fields: ["subject", "from", "date"]
```

### 4. Content Data Model
```yaml
# Standard frontmatter for all content
---
id: "newsletter-2024-10-16-tech-deals"
type: "newsletter"
source: "gmail-newsletters"
title: "Best Tech Deals This Week"
date: "2024-10-16T06:00:00Z"
author: "Tech Deals Editor"
url: "https://mail.google.com/mail/u/0/#inbox/abc123"
content_hash: "sha256hash..."
tags: ["tech", "deals", "shopping"]
ingested_at: "2024-10-16T06:15:01Z"
---

## Summary
[Extracted summary here...]

## Main Content
[Full content in markdown...]
```

## CLI Interface Design

Simple, direct CLI commands following Unix philosophy:

```bash
# Ingestion commands
atlas ingest newsletters    # Ingest from all newsletter sources
atlas ingest rss            # Ingest from all RSS feeds
atlas ingest youtube        # Ingest from YouTube sources
atlas ingest all            # Ingest from all sources

# Management commands
atlas validate              # Validate all content
atlas status                # Show system status
atlas list-failures         # Show failed items
atlas retry                 # Retry failed items
atlas prune-logs            # Clean old logs

# Output formats
atlas status --json         # JSON output for scripts
atlas ingest newsletters --verbose  # Detailed output
```

## Module Dependencies (Minimal)

### Required Dependencies
```
feedparser>=6.0.0           # RSS parsing
readability-lxml>=0.8.1     # Article extraction
yt-dlp>=2023.10.0           # YouTube processing
python-telegram-bot>=20.0   # Telegram interface
pyyaml>=6.0                 # YAML handling
requests>=2.31.0            # HTTP requests
```

### Standard Library Only
- `sqlite3` (built-in, optional for search index)
- `argparse` (CLI - built-in)
- `logging` (built-in)
- `pathlib` (built-in)
- `hashlib` (built-in)
- `datetime` (built-in)

## Testing Strategy

### Unit Tests
```python
# tests/unit/test_content_hash.py
def test_content_hash_consistency():
    """Test content hash produces same result for same content."""
    content = "Test title and first 500 characters of content body"
    hash1 = generate_content_hash("Test Title", content)
    hash2 = generate_content_hash("Test Title", content)
    assert hash1 == hash2

def test_content_hash_uniqueness():
    """Test different content produces different hashes."""
    hash1 = generate_content_hash("Title 1", "Content 1")
    hash2 = generate_content_hash("Title 2", "Content 2")
    assert hash1 != hash2
```

### Integration Tests
```python
# tests/integration/test_ingest_pipeline.py
def test_end_to_end_rss_ingestion():
    """Test complete RSS ingestion pipeline."""
    # Setup test feed
    # Run ingestion
    # Verify output files
    # Check deduplication
    pass
```

## Deployment Structure

### Systemd Integration
```ini
# config/systemd/atlas-ingest.service
[Unit]
Description=Atlas Content Ingestion
After=network.target

[Service]
Type=oneshot
WorkingDirectory=/opt/atlas
ExecStart=/opt/atlas/.venv/bin/python -m atlas.cli ingest all
User=atlas
Environment=ATLAS_CONFIG=/opt/atlas/config/config.yaml

[Install]
WantedBy=multi-user.target
```

```ini
# config/systemd/atlas-ingest.timer
[Unit]
Description=Daily Atlas Content Ingestion
Requires=atlas-ingest.service

[Timer]
OnCalendar=*-*-* 06:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

## Benefits of This Structure

### 1. Simplicity
- Each module < 300 lines
- Clear, direct implementations
- Minimal dependencies
- No complex abstractions

### 2. Modularity
- Each ingestor works independently
- Can test components in isolation
- Easy to modify or replace individual parts
- Clear separation of concerns

### 3. Reliability
- Stateless operations
- File-based persistence
- Simple error handling
- No complex state management

### 4. Maintainability
- Clear file organization
- Standard Python packaging
- Comprehensive test coverage
- Good documentation

### 5. Agent-Friendly
- Simple CLI interface
- JSON output for scripting
- Clear error messages
- Predictable behavior

## Implementation Phases

### Phase 1: Core Setup (Day 1)
1. Create directory structure
2. Setup logging and configuration
3. Implement basic CLI
4. Create core utilities (hash, validator, deduplicator)

### Phase 2: Ingestion (Days 2-4)
1. Implement base ingestor interface
2. Build Gmail ingestor
3. Build RSS ingestor
4. Build YouTube ingestor

### Phase 3: Storage & Validation (Days 5-6)
1. Implement Markdown+YAML writer
2. Add validation engine
3. Add deduplication logic
4. Test with real data

### Phase 4: Interfaces (Days 7-8)
1. Complete CLI commands
2. Add Telegram bot
3. Add retry and error handling
4. Systemd integration

### Phase 5: Testing & Deployment (Days 9-10)
1. Comprehensive testing
2. Documentation
3. Deployment scripts
4. Production validation

## Success Metrics

- All modules < 300 lines of code
- 100% test coverage for core logic
- End-to-end ingestion works with real data
- Can run unattended for 7 days
- All CLI commands work correctly
- Telegram bot responds to all commands
- Systemd timer runs reliably

---

**Next Step**: This structure provides a solid foundation for building Atlas v4. Should we proceed with implementation starting with Phase 1: Project Structure & Core Setup?