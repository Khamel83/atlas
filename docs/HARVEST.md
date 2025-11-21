# Atlas v4 Harvest Document

## Overview
This document analyzes the existing Atlas v3 codebase (archived in `archive` branch) for salvageable patterns, working code, and lessons learned before building v4 from scratch.

## What's in the Archive
- **Database**: `data/atlas.db` with 25,831 content records (15,977 substantial)
- **RSS Parsing**: Working feedparser implementations
- **Gmail Integration**: IMAP and OAuth2 attempts
- **YouTube Integration**: yt-dlp wrappers and transcript extraction
- **Configuration Systems**: YAML-based source configs
- **Monitoring**: Multiple health check and logging systems
- **Test Data**: Real RSS feeds, emails, and content samples

## Salvageable Patterns & Code

### ✅ Working RSS Processing
**Location**: `src/ingest/rss_ingestor.py`, `podcast_processor.py`
**What Works**:
- feedparser handles malformed feeds reliably
- Content extraction with readability-lxml
- Episode deduplication by GUID
- Show notes extraction

**Harvest for v4**:
- Use feedparser for all RSS processing
- Keep content hash deduplication logic
- Use readability-lxml for article extraction

### ✅ YouTube Metadata Extraction
**Location**: `simple_youtube_integration.py`, `youtube_ingestor.py`
**What Works**:
- yt-dlp for video info and transcripts
- Transcript download and parsing
- Chapter extraction

**Harvest for v4**:
- Use yt-dlp wrapper pattern
- Keep transcript extraction logic
- Use video metadata format

### ✅ Configuration Management
**Location**: `config/`, `src/config.py`
**What Works**:
- YAML source definitions
- Per-source validation rules
- Fallback chain configuration

**Harvest for v4**:
- Use identical YAML structure
- Keep validation rule format
- Use fallback chain pattern

### ✅ Content Hash Logic
**Location**: Various deduplication files
**What Works**:
- SHA256 hash of normalized content
- URL normalization rules
- Collision detection

**Harvest for v4**:
- Use exact same hash algorithm
- Keep URL normalization rules
- Use same collision handling

### ✅ File Storage Patterns
**Location**: `storage.py`, output directories
**What Works**:
- Directory structure: source/year/month/
- Markdown+YAML format
- Filename collision handling with -2, -3 suffix

**Harvest for v4**:
- Use identical storage structure
- Keep same filename format
- Use same collision handling

### ✅ Error Classification
**Location**: `retry_handler.py`, failure analysis files
**What Works**:
- Transient vs permanent error classification
- Exponential backoff for retries
- Dead letter queue for failed items

**Harvest for v4**:
- Use same error taxonomy
- Keep retry intervals (1m, 5m, 30m, 2h, 6h)
- Use DLQ pattern

## ❌ Brittle Patterns to Avoid

### Over-Engineered Architecture
**Problems**:
- Complex class hierarchies for simple ingestion
- Multiple abstraction layers
- Unused "flexibility" features

**Lesson**: Use simple functions, direct implementations

### Complex State Management
**Problems**:
- Database locks and concurrent processing
- Queue systems that added complexity
- Multiple process coordination

**Lesson**: Stateless operations, file-based persistence

### Framework Dependencies
**Problems**:
- Custom ORMs and data models
- Complex dependency injection
- Unused "enterprise" patterns

**Lesson**: Use standard library, direct file operations

### Multi-Process Coordination
**Problems**:
- systemd services interfering with each other
- Process death spirals
- Complex health monitoring

**Lesson**: Single process, systemd timer for scheduling

## Test Data to Preserve

### RSS Feeds
**Location**: `test_data/`, various config files
- Real podcast feeds (Acquired, My First Million)
- Newsletter RSS feeds
- YouTube channel RSS

### Gmail Integration
**Location**: `gmail_*` files
- OAuth2 flow examples
- IMAP connection patterns
- Email parsing samples

### Content Samples
**Location**: `content/markdown/`, output directories
- Real extracted content in various formats
- Validation examples
- Deduplication test cases

## Configuration Structures to Keep

### Source Configuration
```yaml
source: gmail-newsletters
type: email
connection:
  imap_host: imap.gmail.com
  imap_port: 993
  email: omar.personal@gmail.com
  app_password: "APP_PASS"
filters:
  subject_contains: "[Newsletter]"
  since_days: 3
validation:
  min_length: 300
  require_fields: [subject, from, date]
fallback_chain:
  - parse_html_body
  - parse_plain_body
  - archive_header_only
```

### YAML Frontmatter Format
```yaml
---
id: "newsletter-2024-06-16-wirecutter"
type: "newsletter"
source: "gmail-newsletters"
title: "Best Tech Deals This Week"
date: "2024-06-16T06:00:00Z"
author: "Wirecutter Editors"
url: "https://mail.google.com/mail/u/0/#inbox/abcdef"
content_hash: "d1b8d49e86ecad4e79d5b8d63b281701d9dc9a2db66062901e65a953acd26d94"
tags: ["tech", "deals"]
ingested_at: "2024-06-16T06:10:15Z"
---
```

## Key Learnings for v4

### What Worked Well
1. **Simple RSS ingestion** - feedparser + readability = reliable
2. **File-based storage** - Markdown+YAML = Obsidian compatible
3. **Content hash deduplication** - SHA256 = effective
4. **YAML configuration** - human readable and flexible
5. **Exponential backoff retry** - handles transient failures

### What Failed Completely
1. **Multi-process architecture** - too complex, unreliable
2. **Database-driven processing** - unnecessary complexity
3. **Complex monitoring systems** - added overhead, little value
4. **Framework over-engineering** - reduced maintainability
5. **Multiple ingress points** - confused, hard to debug

### Golden Rules for v4
1. **One script = one function** - Keep it simple
2. **Files over databases** - Use Markdown+YAML
3. **Functions over classes** - Prefer simple functions
4. **Direct over abstract** - No unnecessary layers
5. **Working over flexible** - Build what works now

## Database Content
The `data/atlas.db` contains:
- **25,831 content records** - Preserved for reference
- **15,977 substantial content** - Valid extraction samples
- **RSS source metadata** - Working feed configurations
- **Processing history** - What worked and what didn't

**Decision**: Keep database for reference but build v4 to work with files only.

## Next Steps for v4
1. Harvest the working patterns listed above
2. Implement simple, direct versions
3. Test with real data continuously
4. Avoid the anti-patterns documented here
5. Build incrementally, test each phase completely

---

**Remember**: The archive contains years of experimentation and learning.
Use the wisdom, discard the complexity, build something simple that works.