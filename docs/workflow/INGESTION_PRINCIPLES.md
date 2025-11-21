# Atlas Ingestion Principles

## FUNDAMENTAL RULE #1: PRESERVE ALL DATA

**NEVER DISCARD ANY METADATA OR DATA DURING INGESTION**

### Core Principle
Every piece of information available from any source (RSS feeds, APIs, web scraping, etc.) MUST be captured and preserved. We err on the side of capturing too much rather than too little.

### Why This Matters
- **Future-proofing**: What seems unimportant today may be critical tomorrow
- **Search quality**: More metadata = better search and discovery
- **Data loss is irreversible**: Once lost during ingestion, it's gone forever
- **Unknown use cases**: We can't predict all future analysis needs

### Implementation Requirements

#### For ALL Ingestors:
1. **Capture raw source data** - Save the complete, unprocessed response
2. **Extract ALL available fields** - Every field from APIs, feeds, scraping
3. **Preserve original formats** - HTML, JSON, XML structures intact
4. **Save redundant data** - If multiple fields contain similar info, save all
5. **Document unknown fields** - Log any fields we don't explicitly handle

#### Specific Examples:

**Podcast Feeds (RSS/Atom):**
- `title`, `summary`, `content`, `description`
- `author`, `authors`, `creator`, `publisher`
- `published`, `updated`, `pubDate`
- `guid`, `id`, `link`, `links`
- `itunes_duration`, `itunes_episode`, `itunes_season`
- `itunes_explicit`, `itunes_episodetype`
- `tags`, `categories`, `keywords`
- `image`, `thumbnail`, `enclosures`
- `subtitle`, `language`, `copyright`
- **ALL custom namespaced fields** (spotify:, google:, etc.)

**YouTube/Video:**
- All metadata from API responses
- Comments, likes, view counts
- Channel information, playlists
- Captions, subtitles in all languages
- Thumbnails, timestamps, chapters

**Articles/Web:**
- Meta tags, Open Graph, Schema.org markup
- Author info, publication dates
- Social sharing data, comments
- All header information, canonical URLs

### Storage Strategy
1. **Primary metadata**: Structured fields in our metadata system
2. **Raw backup**: Complete original response as JSON/XML
3. **Processing logs**: What we extracted vs what was available

### Quality Assurance
- Log warnings when fields are empty or missing
- Regular audits to ensure no data loss
- Automated checks for new fields in source APIs

## Remember: STORAGE IS CHEAP, DATA LOSS IS EXPENSIVE

Better to save 10x more data than we need than to lose 1 critical piece of information.