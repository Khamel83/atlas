# Atlas Content Ingestion User Guide

This guide provides step-by-step instructions for every way to get content into Atlas. Whether you're saving web articles, processing documents, or capturing voice memos, this guide will help you successfully ingest content into your Atlas system.

## Table of Contents

0. [Setup: Install iOS Shortcuts](#setup-install-ios-shortcuts)
1. [Articles](#articles)
2. [Documents](#documents)
3. [Podcasts](#podcasts)
4. [YouTube Videos](#youtube-videos)
5. [Email Integration](#email-integration)
6. [Voice Memos](#voice-memos)
7. [Screenshots](#screenshots)
8. [Quick Start: Add Your First Content](#quick-start-add-your-first-content)

## Setup: Install iOS Shortcuts

**📱 For Mobile Content Capture:**

Many of the methods in this guide use iOS shortcuts. Install them first:

```bash
# Get mobile installation URL
./get_mobile_url.sh

# Or install from computer
./install_shortcuts.sh
```

Then open the URL on your iPhone and tap each shortcut to install.

**Available Shortcuts:**
- **Capture Thought** - "Hey Siri, save to Atlas"
- **Voice Memo to Atlas** - Audio transcription
- **Screenshot to Atlas** - OCR text extraction
- **Save to Atlas** - Web page capture

## Articles

### How to save web articles

Atlas supports multiple ways to save web articles:

#### Method 1: URL List File
1. Create a text file with one URL per line
2. Save the file as `inputs/articles.txt`
3. Run article ingestion:
   ```bash
   python run.py --articles
   ```

#### Method 2: Instapaper CSV
1. Export your Instapaper library as CSV
2. Save the file as `inputs/instapaper_export.csv`
3. Run article ingestion:
   ```bash
   python run.py --articles
   ```

#### Method 3: Browser Extension
1. Install the Atlas browser extension
2. Click the Atlas icon while browsing any webpage
3. Select "Save Current Page" or "Save Article Content"

#### Method 4: Apple Shortcuts
1. Use the "Save to Atlas" iOS shortcut
2. Share any webpage to the shortcut
3. Content is automatically sent to Atlas

### Supported Article Sources
- Any public webpage URL
- RSS feeds
- News sites
- Blogs
- Research papers
- Documentation

### Troubleshooting Article Ingestion
- **"Failed to fetch" errors**: Try again later or use a different fetching strategy
- **"Content too long"**: Article may be too large for processing
- **"Duplicate content"**: Article has already been processed
- **"Unsupported format"**: URL may not be a standard article

## Documents

### How to process PDFs, Word docs, and text files

Atlas can process various document formats:

#### Method 1: File Drop
1. Place documents in `inputs/New Docs/`
2. Atlas automatically processes new files

#### Method 2: Direct Processing
```bash
python run.py --urls path/to/document_list.txt
```

### Supported Document Formats
- PDF (.pdf)
- Word Documents (.docx)
- Text Files (.txt)
- Markdown (.md)
- HTML (.html)

### Document Processing Features
- Text extraction
- Metadata analysis
- Content categorization
- Search indexing
- Cognitive insights

### Troubleshooting Document Processing
- **"Unsupported format"**: File extension may not be recognized
- **"Corrupted file"**: Document may be damaged
- **"Extraction failed"**: OCR may be needed for scanned documents
- **"Too large"**: Document exceeds size limits

## Podcasts & PODEMOS Personal Ad-Free Feeds

### PODEMOS Personal Ad-Free Podcast System

Atlas includes PODEMOS, a comprehensive personal podcast processing system that removes advertisements and provides clean RSS feeds:

#### Setting Up PODEMOS Personal Feeds

1. **Import Your Podcast Subscriptions:**
   ```bash
   # Export OPML from your podcast app (Overcast, Pocket Casts, etc.)
   # Save as inputs/podcast_subscriptions.opml

   # Import subscriptions to PODEMOS
   python3 podemos_opml_parser.py inputs/podcast_subscriptions.opml
   ```

2. **Configure PODEMOS Processing:**
   ```bash
   # Add to .env file
   PODEMOS_ENABLED=true
   PODEMOS_PROCESSING_TIME="02:00"  # 2 AM daily processing
   PODEMOS_RSS_HOST=your_domain.com
   PODEMOS_AUTH_TOKEN=your_secure_token

   # Oracle OCI configuration for RSS hosting
   OCI_BUCKET_NAME=your_bucket_name
   OCI_REGION=your_region
   ```

3. **Start PODEMOS Services:**
   ```bash
   # Start feed monitoring (runs continuously)
   python3 podemos_feed_monitor.py --daemon

   # Start RSS server for private feeds
   python3 podemos_rss_server.py --daemon

   # Or use unified service manager
   python3 unified_service_manager.py start --podemos
   ```

#### PODEMOS Features

**🎯 Ultra-Fast Ad Removal:**
- **19-Minute Processing**: From episode release to clean feed availability
- **Real-Time Monitoring**: Detects new episodes within 1-2 minutes
- **AI-Powered Ad Detection**: 8 different pattern recognition algorithms
- **Mac Mini Integration**: Leverages dedicated Whisper transcription hardware

**📻 Private RSS Feeds:**
- **Clean Episode Delivery**: Ad-free audio with preserved quality
- **Podcast App Compatible**: Works with Overcast, Pocket Casts, Apple Podcasts
- **Authenticated Access**: Secure token-based private feed access
- **Oracle OCI Hosting**: Scalable, reliable cloud infrastructure

**🔄 Automated Processing Pipeline:**
- **Daily 2 AM Processing**: Scheduled processing for overnight episode releases
- **Continuous Monitoring**: Real-time detection of new episodes
- **Atlas Integration**: Shared processing queue prevents resource conflicts
- **Failure Recovery**: Automatic retry logic for failed processing

#### Using Your Private PODEMOS Feeds

1. **Get Your Private Feed URLs:**
   ```bash
   # List all your private feeds
   python3 -c "
   from podemos_rss_server import PodmosRSSServer
   server = PodmosRSSServer()
   feeds = server.list_private_feeds()
   for feed in feeds:
       print(f'{feed.title}: {feed.private_url}')
   "
   ```

2. **Add to Your Podcast App:**
   - Copy the private RSS URL for each podcast
   - Add as a "Custom RSS Feed" in your podcast app
   - Authentication token is embedded in the URL
   - Episodes will appear ad-free within 20 minutes of release

3. **Monitor Processing Status:**
   ```bash
   # Check PODEMOS processing status
   python3 podemos_monitor.py --status

   # View recent processing activity
   python3 podemos_monitor.py --recent-activity
   ```

### Standard Podcast Processing (Without Ad Removal)

For podcasts not in your PODEMOS subscription list, Atlas still provides comprehensive podcast processing:

#### Method 1: OPML Import
1. Export your podcast subscriptions as OPML
2. Save the file as `inputs/podcasts.opml`
3. Run podcast ingestion:
   ```bash
   python run.py --podcasts
   ```

#### Method 2: Direct RSS Feed Processing
```bash
# Process a single podcast feed
python3 helpers/podcast_ingestor.py "https://feeds.example.com/podcast.rss"

# Process with Mac Mini transcription
python3 helpers/podcast_ingestor.py "https://feeds.example.com/podcast.rss" --use-mac-mini
```

#### Method 3: Historical Episode Import
```bash
# Import entire podcast history
python3 -c "
from helpers.podcast_ingestor import PodcastIngestor
ingestor = PodcastIngestor()
ingestor.import_full_history('https://feeds.example.com/podcast.rss', max_episodes=100)
"
```

### Podcast Processing Features

**🎙️ Comprehensive Transcription:**
- Mac Mini Whisper integration for high-quality transcription
- Multiple model sizes (base, small, medium) for speed/quality optimization
- Fallback transcription methods for maximum coverage
- Support for multiple audio formats (MP3, M4A, WAV, FLAC)

**🔍 Atlas Integration:**
- Episode metadata stored in Atlas database
- Transcripts indexed for semantic search
- Content available in cognitive feature analysis
- Mobile-friendly podcast content management

**📊 Quality Analysis:**
- Content quality scoring with 6 analysis dimensions
- Automatic reprocessing of failed or low-quality content
- Duplicate detection and deduplication
- Performance monitoring and optimization

### Supported Podcast Sources

✅ **Fully Supported:**
- Standard RSS feeds (RSS 2.0, Atom)
- Apple Podcasts feeds
- Podcast hosting platforms (Libsyn, Anchor, etc.)
- Direct audio file URLs

⚠️ **Limited Support:**
- Spotify podcast URLs (metadata only, no audio)
- Premium/paid podcast feeds
- Feeds requiring authentication

❌ **Not Supported:**
- Proprietary platform-locked content
- DRM-protected audio files
- Live streaming (only after episodes are published)

### Troubleshooting Podcast Processing

**PODEMOS Issues:**
```bash
# Check PODEMOS service status
python3 podemos_monitor.py --health-check

# View processing logs
tail -f logs/podemos_processing.log

# Restart PODEMOS services
python3 unified_service_manager.py restart --podemos
```

**Transcription Issues:**
- **"Mac Mini unavailable"**: Processing falls back to local transcription
- **"Whisper model loading failed"**: Check Mac Mini setup and model installation
- **"Audio format not supported"**: Convert to MP3/M4A using FFmpeg

**Feed Processing Issues:**
- **"Feed not found"**: RSS URL may be invalid or moved
- **"No episodes"**: Feed may be empty, private, or require authentication
- **"Download failed"**: Audio file may be unavailable or geoblocked
- **"Processing timeout"**: Large episodes may need extended timeout settings

**Performance Optimization:**
```bash
# Enable Mac Mini for faster processing
PODCAST_USE_MAC_MINI=true

# Adjust processing concurrency
PODCAST_MAX_CONCURRENT=3

# Configure transcription model
PODCAST_WHISPER_MODEL=base  # Options: tiny, base, small, medium, large
```
- Independent podcasters
- Internal company podcasts

### Troubleshooting Podcast Processing
- **"Feed not found"**: RSS URL may be incorrect
- **"No episodes"**: Feed may be empty or private
- **"Download failed"**: Audio file may be unavailable
- **"Transcription failed"**: Audio quality may be poor

## YouTube Videos

### Automated YouTube Content Processing

Atlas features a comprehensive YouTube processing system that automatically monitors and processes your YouTube content:

#### Method 1: Automated Subscription Processing (Recommended)
Atlas automatically discovers and processes videos from your YouTube subscriptions:

1. **Setup YouTube API Access:**
   ```bash
   # Configure YouTube API credentials in .env
   YOUTUBE_API_KEY=your_api_key_here
   YOUTUBE_CHANNEL_ID=your_channel_id_here
   ```

2. **Enable Automated Processing:**
   - YouTube processing runs automatically every 5 hours
   - Discovers new videos from subscriptions and history
   - Processes video metadata and extracts transcripts
   - Integrates with Atlas semantic search and cognitive features

3. **Monitor Processing:**
   ```bash
   # Check YouTube processing status
   python3 atlas_status.py --detailed
   ```

#### Method 2: Manual Video URL Processing
For specific videos or one-time processing:

1. **Single Video Processing:**
   ```bash
   # Process a specific YouTube video
   python3 -c "
   from helpers.youtube_ingestor import YouTubeIngestor
   ingestor = YouTubeIngestor()
   ingestor.process_video_url('https://youtube.com/watch?v=VIDEO_ID')
   "
   ```

2. **Batch URL Processing:**
   ```bash
   # Create file with YouTube URLs (one per line)
   echo "https://youtube.com/watch?v=VIDEO_ID_1" > inputs/youtube_urls.txt
   echo "https://youtube.com/watch?v=VIDEO_ID_2" >> inputs/youtube_urls.txt

   # Process batch
   python3 scripts/atlas_scheduler.py --youtube-batch inputs/youtube_urls.txt
   ```

#### Method 3: YouTube History Import
Process your entire YouTube watch history:

1. **Export YouTube History:**
   - Go to [Google Takeout](https://takeout.google.com)
   - Select "YouTube and YouTube Music" > "history"
   - Download as JSON format

2. **Import History:**
   ```bash
   # Place downloaded file as inputs/youtube_history.json
   python3 -c "
   from automation.youtube_history_scraper import YouTubeHistoryProcessor
   processor = YouTubeHistoryProcessor()
   processor.process_history_file('inputs/youtube_history.json')
   "
   ```

### YouTube Processing Features

**🤖 Automated Discovery:**
- Monitors YouTube subscriptions via YouTube Data API v3
- Discovers new videos every 5 hours automatically
- Respects API rate limits with intelligent caching
- Prevents duplicate processing with content fingerprinting

**📝 Transcript Processing:**
- Extracts official captions when available
- Falls back to auto-generated captions
- Supports multiple language transcripts
- Integrates with Mac Mini Whisper for audio transcription fallback

**🔍 Atlas Integration:**
- Video metadata stored in Atlas database
- Transcripts indexed for semantic search
- Content available in cognitive feature analysis
- Mobile-friendly video content management

**⚡ Smart Rate Limiting:**
- Respects YouTube API quotas (10,000 units/day default)
- Implements exponential backoff for rate limit handling
- Caches results to minimize API calls
- Graceful degradation when API limits reached

### Supported YouTube Content

✅ **Fully Supported:**
- Public videos with official captions
- Videos with auto-generated captions
- Educational content and lectures
- Podcast episodes uploaded to YouTube
- Conference talks and presentations

⚠️ **Limited Support:**
- Private videos (if you have access)
- Unlisted videos (with direct URL)
- Videos without captions (audio-only processing via Mac Mini)

❌ **Not Supported:**
- Age-restricted content requiring login
- Copyright-protected content with disabled embedding
- Live streams (only after they become VODs)

### Troubleshooting YouTube Processing

**Authentication Issues:**
```bash
# Verify YouTube API credentials
python3 -c "
from integrations.youtube_api_client import YouTubeAPIClient
client = YouTubeAPIClient()
print('API Status:', client.test_connection())
"
```

**Rate Limiting:**
- **"Quota exceeded"**: Wait 24 hours for quota reset or upgrade API limits
- **"Too many requests"**: Processing will resume automatically with backoff
- **Check current usage**: Monitor API usage in Google Cloud Console

**Transcript Issues:**
- **"No captions available"**: Video may not have captions enabled
- **"Transcript extraction failed"**: Try audio processing via Mac Mini integration
- **"Language not supported"**: Only English transcripts fully supported currently

**Processing Failures:**
```bash
# Check failed YouTube processing jobs
python3 -c "
from universal_processing_queue import UniversalQueue
queue = UniversalQueue()
failed_jobs = queue.get_failed_jobs(job_type='youtube')
print(f'Failed YouTube jobs: {len(failed_jobs)}')
"

# Retry failed jobs
python3 scripts/atlas_scheduler.py --retry-failed-youtube
```

**Performance Optimization:**
- Enable Mac Mini integration for faster audio processing
- Adjust processing frequency in `.env` (YOUTUBE_PROCESSING_INTERVAL)
- Configure video quality preferences (YOUTUBE_QUALITY_PREFERENCE)

## Email Integration

### How to forward emails to Atlas

Atlas can process emails sent to a dedicated address:

#### Method 1: IMAP Integration
1. Configure email account in Atlas settings
2. Atlas automatically checks for new emails
3. Emails are processed and indexed

#### Method 2: Forwarding
1. Forward emails to your Atlas email address
2. Atlas processes incoming emails automatically

### Email Processing Features
- Content extraction
- Attachment processing
- Metadata analysis
- Search indexing
- Categorization

### Supported Email Providers
- Gmail
- Outlook/Hotmail
- Yahoo Mail
- Custom IMAP servers
- Corporate email systems

### Troubleshooting Email Processing
- **"Authentication failed"**: Check email credentials
- **"Connection timeout"**: Network or server issues
- **"Attachment too large"**: File exceeds size limits
- **"Unsupported format"**: Email format may not be recognized

## Voice Memos

### How to record and transcribe audio notes

Atlas can process voice memos and transcribe them to text:

#### Method 1: Apple Shortcuts
1. Use the "Voice Memo to Atlas" iOS shortcut
2. Record your voice memo
3. Atlas automatically transcribes and processes

#### Method 2: File Upload
1. Record audio and save as WAV, MP3, or M4A
2. Place file in `inputs/voice_memos/`
3. Atlas processes new files automatically

### Voice Memo Processing Features
- Speech-to-text transcription
- Content analysis
- Metadata extraction
- Search indexing
- Categorization

### Supported Audio Formats
- WAV (.wav)
- MP3 (.mp3)
- M4A (.m4a)
- FLAC (.flac)
- OGG (.ogg)

### Troubleshooting Voice Memo Processing
- **"Transcription failed"**: Audio quality may be poor
- **"Unsupported format"**: File extension may not be recognized
- **"Too long"**: Audio file exceeds duration limits
- **"No speech detected"**: Recording may be empty or silent

## Screenshots

### How to OCR and save image text

Atlas can extract text from screenshots and images:

#### Method 1: Apple Shortcuts
1. Use the "Screenshot to Atlas" iOS shortcut
2. Take a screenshot
3. Atlas automatically OCRs and processes

#### Method 2: File Upload
1. Save images as JPG or PNG
2. Place files in `inputs/screenshots/`
3. Atlas processes new files automatically

### Screenshot Processing Features
- Optical character recognition (OCR)
- Content analysis
- Metadata extraction
- Search indexing
- Categorization

### Supported Image Formats
- JPEG (.jpg, .jpeg)
- PNG (.png)
- GIF (.gif)
- BMP (.bmp)
- TIFF (.tiff)

### Troubleshooting Screenshot Processing
- **"OCR failed"**: Image quality may be poor
- **"Unsupported format"**: File extension may not be recognized
- **"No text detected"**: Image may not contain readable text
- **"Too large"**: Image file exceeds size limits

## Quick Start: Add Your First Content

### 5-Minute Setup

1. **Create your first article list**:
   ```bash
   echo "https://example.com/article1" > inputs/articles.txt
   echo "https://example.com/article2" >> inputs/articles.txt
   ```

2. **Process your articles**:
   ```bash
   python run.py --articles
   ```

3. **View your content**:
   - Open your web browser to `https://atlas.khamel.com`
   - Navigate to the content management section
   - Browse your processed articles

4. **Try cognitive features**:
   - Visit `https://atlas.khamel.com/ask/html`
   - Explore the Proactive Surfacer, Pattern Detector, and other features

5. **Set up automation**:
   - Create a cron job to run ingestion daily:
     ```bash
     crontab -e
     # Add this line to run daily at 2 AM:
     # 0 2 * * * cd /home/ubuntu/dev/atlas && python run.py --all
     ```

### Next Steps

After your first content is processed:
- Configure email integration for automatic email processing
- Set up podcast feeds for regular episode processing
- Install the browser extension for one-click web capture
- Try the iOS shortcuts for mobile content capture
- Explore cognitive features in the web dashboard

## Troubleshooting Common Ingestion Failures

### General Troubleshooting Steps

1. **Check logs**:
   ```bash
   tail -f logs/atlas_service.log
   ```

2. **Verify Atlas is running**:
   ```bash
   python atlas_service_manager.py status
   ```

3. **Check disk space**:
   ```bash
   df -h
   ```

4. **Restart services**:
   ```bash
   python atlas_service_manager.py restart
   ```

### Common Error Messages and Solutions

- **"Connection refused"**: Atlas service may not be running
- **"Permission denied"**: Check file permissions
- **"File not found"**: Verify file paths and names
- **"Invalid format"**: File may be corrupted or in unsupported format
- **"Rate limited"**: Too many requests - wait and try again
- **"Out of memory"**: System may need more RAM or processing should be reduced

## File Size Limits and Supported Formats

### File Size Limits

- **Articles**: No specific limit (content is fetched from web)
- **Documents**: 100MB maximum
- **Podcasts**: 500MB maximum per episode
- **YouTube Videos**: Transcripts only (no file size limit)
- **Emails**: 25MB maximum including attachments
- **Voice Memos**: 100MB maximum
- **Screenshots**: 50MB maximum

### Supported Formats Summary

| Content Type | Supported Formats |
|--------------|-------------------|
| Articles | Any web URL |
| Documents | PDF, DOCX, TXT, MD, HTML |
| Podcasts | Any RSS feed with audio |
| YouTube | Videos with captions |
| Email | IMAP-compatible providers |
| Voice Memos | WAV, MP3, M4A, FLAC, OGG |
| Screenshots | JPG, PNG, GIF, BMP, TIFF |

## Advanced Ingestion Configuration

### Environment Variables

Configure ingestion behavior through the `.env` file:

```bash
# Article processing
MAX_ARTICLE_RETRIES=3
ARTICLE_TIMEOUT=300
ARTICLE_STRATEGIES=direct,12ft,archive,googlebot,playwright,wayback

# Podcast processing
PODCAST_DOWNLOAD_TIMEOUT=600
PODCAST_MAX_SIZE=524288000  # 500MB in bytes
PODCAST_TRANSCRIPTION_MODEL=base

# YouTube processing
YOUTUBE_TRANSCRIPTION_MODEL=base
YOUTUBE_TIMEOUT=300

# Document processing
DOCUMENT_MAX_SIZE=104857600  # 100MB in bytes
OCR_ENABLED=true
```

### Custom Processing Scripts

Create custom processing scripts in `/scripts/custom_ingestion/`:

```python
#!/usr/bin/env python3
# custom_ingestor.py
from helpers.metadata_manager import MetadataManager
from helpers.config import load_config

def process_custom_content(content, metadata):
    """Custom processing logic"""
    config = load_config()
    manager = MetadataManager(config)

    # Your custom processing logic here
    processed_content = content.upper()  # Example transformation

    return processed_content
```

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
- Issue Template: Include logs and reproduction steps