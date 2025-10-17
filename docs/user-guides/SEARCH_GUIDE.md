# Atlas Search and Discovery User Guide

This guide covers all search and discovery features in Atlas, helping you find and explore content in your knowledge base effectively.

## Table of Contents

1. [Basic Search](#basic-search)
2. [Advanced Filters](#advanced-filters)
3. [Semantic Search](#semantic-search)
4. [Cognitive Features](#cognitive-features)
5. [Export Options](#export-options)
6. [Mobile Search](#mobile-search)

## Basic Search

### Text Search with Examples

Atlas provides powerful full-text search capabilities across all your content:

#### Simple Search
Enter keywords in the search box to find content containing those terms:
```
machine learning
```

#### Phrase Search
Use quotes to search for exact phrases:
```
"artificial intelligence"
```

#### Boolean Operators
- AND: `machine learning AND healthcare`
- OR: `python OR javascript`
- NOT: `programming NOT java`

#### Wildcard Search
Use `*` for partial matching:
```
program*  # matches program, programs, programming, etc.
```

#### Field-Specific Search
Search within specific fields:
- `title:python` - Search only in titles
- `content:algorithm` - Search only in content
- `tags:technology` - Search only in tags

### Search Examples

1. **Finding specific content**:
   ```
   "climate change" AND solutions
   ```

2. **Searching by date**:
   ```
   artificial intelligence published:2023
   ```

3. **Finding content by type**:
   ```
   content_type:article machine learning
   ```

4. **Searching tags**:
   ```
   tags:programming OR tags:development
   ```

## Advanced Filters

### Date Ranges

Filter content by date ranges:
- Last 24 hours: `date:>now-1d`
- Last week: `date:>now-7d`
- Last month: `date:>now-1M`
- Custom range: `date:[2023-01-01 TO 2023-12-31]`

### Content Types

Filter by specific content types:
- Articles: `content_type:article`
- Podcasts: `content_type:podcast`
- Documents: `content_type:document`
- YouTube videos: `content_type:youtube`
- Emails: `content_type:email`

### Sources

Filter by content sources:
- Specific websites: `source:nytimes.com`
- Domain patterns: `source:*.edu`
- Multiple sources: `source:github.com OR source:stackoverflow.com`

### Tags

Filter by tags:
- Single tag: `tags:python`
- Multiple tags: `tags:python AND tags:django`
- Tag groups: `tags:(python OR javascript) AND tags:web`

## Semantic Search

### How to find related concepts

Atlas's semantic search goes beyond keyword matching to understand the meaning and context of your content:

#### Concept-Based Search
Instead of exact keywords, search for related concepts:
```
natural language processing
```
This will find content about NLP, text analysis, language models, etc.

#### Similar Content Discovery
Find content similar to a specific piece:
1. Open a content item
2. Click "Find Similar Content"
3. Atlas will show semantically related items

#### Intent-Based Search
Search by what you want to accomplish:
```
how to set up a python web server
```

### Semantic Search Examples

1. **Finding related research**:
   ```
   neural networks applications
   ```

2. **Discovering learning resources**:
   ```
   beginner tutorials for data science
   ```

3. **Finding expert opinions**:
   ```
   expert views on remote work productivity
   ```

4. **Identifying trends**:
   ```
   emerging technologies in healthcare
   ```

## Cognitive Features

### When and how to use each AI feature

Atlas's cognitive features enhance your search and discovery experience:

#### Proactive Content Surfacer
- **When to use**: When you want to rediscover forgotten but relevant content
- **How to use**: Visit the dashboard and review surfacing suggestions
- **Best for**: Weekly or monthly content reviews

#### Temporal Relationships
- **When to use**: To understand how topics have evolved over time
- **How to use**: Explore the timeline view in the dashboard
- **Best for**: Research projects and trend analysis

#### Socratic Question Generator
- **When to use**: When studying or preparing for discussions
- **How to use**: Select content and generate thought-provoking questions
- **Best for**: Deep learning and critical thinking

#### Active Recall System
- **When to use**: For memorizing important information
- **How to use**: Review items due for recall in the dashboard
- **Best for**: Language learning and factual knowledge retention

#### Pattern Detector
- **When to use**: To discover themes and connections in your content
- **How to use**: Analyze patterns in the dashboard
- **Best for**: Research synthesis and knowledge organization

#### Recommendation Engine
- **When to use**: When looking for new content to explore
- **How to use**: Browse recommendations in the dashboard
- **Best for**: Expanding your knowledge base

## Export Options

### How to get content out of Atlas

Atlas provides several ways to export your content:

#### Individual Content Export
1. Open any content item
2. Click the "Export" button
3. Choose export format:
   - Markdown (.md)
   - Plain text (.txt)
   - PDF (.pdf)
   - HTML (.html)

#### Search Results Export
1. Perform a search
2. Click "Export Results"
3. Choose format and options:
   - All results or selected items
   - Include metadata
   - Format selection

#### Bulk Export
1. Navigate to the Export section in the dashboard
2. Select content types and filters
3. Choose export format
4. Download the archive

#### API Export
For programmatic access:
```bash
# Export all articles
curl "https://atlas.khamel.com/api/v1/content/export?type=article" > articles.json

# Export search results
curl "https://atlas.khamel.com/api/v1/search/export?query=machine-learning" > ml_content.json
```

### Supported Export Formats

- **Markdown**: Best for editing and version control
- **Plain Text**: Simple and universally compatible
- **PDF**: Printable and presentation-ready
- **HTML**: Web-ready with formatting
- **JSON**: For programmatic processing
- **CSV**: For spreadsheet analysis

## Mobile Search

### Using Atlas cognitive features on phone

Atlas is fully responsive and works great on mobile devices:

#### Mobile-Specific Features

1. **Voice Search**
   - Tap the microphone icon in the search bar
   - Speak your query naturally
   - Atlas will transcribe and search automatically

2. **Camera Integration**
   - Use the camera to scan documents
   - OCR will extract text for searching
   - Content is automatically processed and indexed

3. **Share Sheet Integration**
   - Share web pages directly to Atlas
   - Content is saved and processed automatically
   - Available for search immediately

#### Mobile Search Workflow Examples

1. **Quick Research**:
   - Use voice search while commuting
   - Save interesting articles to read later
   - Find related content with semantic search

2. **Learning on the Go**:
   - Review active recall items during breaks
   - Generate questions for evening study sessions
   - Discover new content through recommendations

3. **Content Capture**:
   - Scan documents with camera
   - Record voice memos with dictation
   - Save web articles from mobile browsers

### Mobile Search Tips

- Use voice search for hands-free operation
- Enable push notifications for proactive content surfacing
- Create reading lists for offline access
- Use widgets for quick access to recent searches

## Keyboard Shortcuts and Power User Features

### Search Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+K` or `/` | Focus search input |
| `Ctrl+Enter` | Search with current filters |
| `Esc` | Clear search and filters |
| `↑`/`↓` | Navigate search suggestions |
| `Enter` | Select search suggestion |

### Power User Features

#### Saved Searches
- Save complex search queries for reuse
- Create shortcuts for frequent searches
- Share saved searches with team members

#### Search History
- Access recent searches from dropdown
- Re-run previous searches with one click
- Clear history when needed

#### Custom Filters
- Create reusable filter combinations
- Apply to any search query
- Save as bookmarks for quick access

#### Advanced Query Syntax
For users familiar with search syntax:
- Range queries: `date:[2023-01-01 TO 2023-12-31]`
- Fuzzy matching: `program~2` (matches similar terms)
- Proximity search: `"machine learning"~5` (terms within 5 words)

## Finding Your Needle in the Haystack

### Search Strategy Tutorial

#### Step 1: Define Your Goal
Before searching, be clear about what you're looking for:
- Specific information
- General topic exploration
- Related content discovery
- Trend analysis

#### Step 2: Start Broad, Then Narrow
1. Begin with general terms
2. Review initial results
3. Add filters and refine query
4. Use semantic search for related concepts

#### Step 3: Use Multiple Approaches
- Traditional keyword search
- Semantic search for concepts
- Filter by content type, date, or source
- Leverage cognitive features

#### Step 4: Save and Organize
- Bookmark important searches
- Create collections of related content
- Export for offline use

## Troubleshooting Common Search Issues

### Search Not Returning Expected Results

1. **Check spelling**: Atlas has typo tolerance, but major errors may affect results
2. **Try synonyms**: Use semantic search for related concepts
3. **Broaden filters**: Remove restrictive filters to see more results
4. **Check content types**: Ensure you're searching the right content types

### Slow Search Performance

1. **Simplify queries**: Complex boolean queries may slow performance
2. **Use filters**: Date and content type filters can speed up searches
3. **Check system resources**: Monitor Atlas performance
4. **Rebuild index**: If consistently slow, rebuild the search index

### No Results Found

1. **Verify content exists**: Check that relevant content has been ingested
2. **Try broader terms**: Use more general keywords
3. **Check filters**: Ensure filters aren't too restrictive
4. **Use semantic search**: Try concept-based search instead of exact terms

## Getting Help

### Community Support

Join the Atlas community:
- Discord: https://discord.gg/atlas
- Reddit: r/AtlasPlatform
- GitHub Discussions: https://github.com/your-username/atlas/discussions

### Professional Support

For enterprise support:
- Email: support@atlas-platform.com
- Phone: +1 (555) 123-4567
- SLA: 24-hour response time

### Reporting Issues

Report bugs and issues on GitHub:
- Repository: https://github.com/your-username/atlas
- Issue Template: Include search queries and expected results