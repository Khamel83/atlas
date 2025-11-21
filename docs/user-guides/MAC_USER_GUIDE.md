# Mac User Guide

## Installation (5 steps)

1. **Clone the Repository**
   ```bash
   git clone https://github.com/your-username/atlas.git
   cd atlas
   ```

2. **Set Up Virtual Environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment**
   ```bash
   cp .env.template .env
   # Edit .env with your API keys and preferences
   ```

5. **Start Atlas Service**
   ```bash
   python atlas_service_manager.py start
   ```

## Apple Shortcuts Setup

### Quick Installation (Recommended)

**🚀 Pre-built Shortcuts - Install in 30 Seconds:**

```bash
# Option 1: Install from computer
./install_shortcuts.sh

# Option 2: Get mobile installation URL
./get_mobile_url.sh
# Then open the URL on your iPhone to install
```

The pre-built shortcuts include:
- **Capture Thought** - "Hey Siri, save to Atlas"
- **Capture Evening Thought** - Evening reflections
- **Log Meal** - Track meals
- **Log Mood** - Emotional state tracking
- **Start Focus** - Begin focus sessions
- **Log Home Activity Context** - Home activity tracking
- **Log Work Task Context** - Work productivity tracking

### Custom Shortcuts (Advanced)

### Save to Atlas Shortcut

1. Open the Shortcuts app on your Mac
2. Create a new shortcut
3. Add a "Text" action with the following JavaScript code:

```javascript
// Save to Atlas bookmarklet
javascript:(function(){
    var title = document.title;
    var url = window.location.href;
    var xhr = new XMLHttpRequest();
    xhr.open("POST", "https://atlas.khamel.com/api/v1/content/save", true);
    xhr.setRequestHeader("Content-Type", "application/json");
    xhr.send(JSON.stringify({
        title: title,
        url: url,
        content: document.body.innerText
    }));
})();
```

### Voice Memo to Atlas Shortcut

1. Open the Shortcuts app on your Mac
2. Create a new shortcut
3. Add a "Record Audio" action
4. Add a "Run Script Over SSH" action with the following code:

```bash
# Transcribe and save voice memo
whisper /path/to/voice/memo.wav --model base --output_dir /tmp/
python /path/to/atlas/scripts/transcribe_and_save.py /tmp/voice_memo.txt
```

### Screenshot to Atlas Shortcut

1. Open the Shortcuts app on your Mac
2. Create a new shortcut
3. Add a "Take Screenshot" action
4. Add a "Run Shell Script" action with the following code:

```bash
# OCR and save screenshot
tesseract /path/to/screenshot.png /tmp/screenshot_text
python /path/to/atlas/scripts/process_screenshot.py /tmp/screenshot_text.txt
```

### Current Page to Atlas Shortcut

1. Open the Shortcuts app on your Mac
2. Create a new shortcut
3. Add a "Get Contents of Web Page" action
4. Add a "Run Shell Script" action with the following code:

```bash
# Save current page content
python /path/to/atlas/scripts/save_web_page.py --url "$1" --title "$2"
```

## Browser Bookmarklets (JavaScript code included)

### Browser Bookmarklet - One-Click Web Saving

**📖 Save Any Web Page to Atlas**

1. **Open the installer:**
   ```bash
   open browser_bookmarklet/install_bookmarklet.html
   ```

2. **Drag the blue "Save to Atlas" button** to your bookmarks bar

3. **Use it anywhere:** Click the bookmark on any web page to save it to Atlas

**Features:**
- ✅ Saves title, URL, and page text automatically
- ✅ Works with any website
- ✅ Smart port detection (prompts for Atlas URL)
- ✅ Success confirmation when saved
- ✅ Perfect complement to voice capture

## 🌐 Remote Access (Phone/Laptop → VM)

**Atlas running on VM, accessed from your phone/devices:**

### 📱 **Mobile Web Access** (Primary Method)
- **URL**: `https://atlas.khamel.com/mobile`
- **Features**: Full content management, search, mobile-optimized interface
- **Works from**: Any device with browser (phone, laptop, tablet)

### 🎤 **Apple Shortcuts** (Voice Capture)
- **"Hey Siri, save to Atlas"** - Works from iPhone/Mac
- **Sends to**: `https://atlas.khamel.com/api/v1/content/save`
- **Perfect for**: Voice memos, quick thoughts while mobile

### 🖱️ **Browser Extensions** (Laptop/Desktop)
- **Right-click "Send to Atlas"** on any web page
- **Install once per device** where you browse
- **Points to**: `https://atlas.khamel.com/api/v1/content/save`

**To install on your actual browsing devices:**
1. Download extension files from VM: `browser_extension/build/`
2. Install on each laptop/desktop where you browse
3. Extensions will save to your VM-hosted Atlas

### 📖 **Browser Bookmarklet** (Universal)
- **Works on any device** - just create bookmark manually
- **JavaScript**: Points to `https://atlas.khamel.com/api/v1/content/save`
- **Perfect for**: Devices where you can't install extensions

**Alternative manual setup (bookmarklet):**

```javascript
javascript:(function(){
    var title = document.title;
    var url = window.location.href;
    var xhr = new XMLHttpRequest();
    xhr.open("POST", "https://atlas.khamel.com/api/v1/content/save", true);
    xhr.setRequestHeader("Content-Type", "application/json");
    xhr.send(JSON.stringify({
        title: title,
        url: url,
        content: document.body.innerText
    }));
})();
```

### Process Selection Bookmarklet

```javascript
javascript:(function(){
    var selection = window.getSelection().toString();
    if (selection) {
        var xhr = new XMLHttpRequest();
        xhr.open("POST", "https://atlas.khamel.com/api/v1/content/process", true);
        xhr.setRequestHeader("Content-Type", "application/json");
        xhr.send(JSON.stringify({
            content: selection,
            source: window.location.href
        }));
    } else {
        alert("Please select some text first");
    }
})();
```

### Save Article with Summary Bookmarklet

```javascript
javascript:(function(){
    var title = document.title;
    var url = window.location.href;
    var content = document.body.innerText;

    // Generate summary using Atlas AI
    var xhr = new XMLHttpRequest();
    xhr.open("POST", "https://atlas.khamel.com/api/v1/cognitive/summarize", true);
    xhr.setRequestHeader("Content-Type", "application/json");
    xhr.onreadystatechange = function() {
        if (xhr.readyState === 4 && xhr.status === 200) {
            var summary = JSON.parse(xhr.responseText).summary;
            // Save with summary
            var saveXhr = new XMLHttpRequest();
            saveXhr.open("POST", "https://atlas.khamel.com/api/v1/content/save", true);
            saveXhr.setRequestHeader("Content-Type", "application/json");
            saveXhr.send(JSON.stringify({
                title: title,
                url: url,
                content: content,
                summary: summary
            }));
        }
    };
    xhr.send(JSON.stringify({
        content: content
    }));
})();
```

## File Drop Workflows (directory locations)

### Input Directories

1. **Articles**: Place text files with URLs in `/home/ubuntu/dev/atlas/inputs/articles.txt`
2. **Podcasts**: Place OPML files in `/home/ubuntu/dev/atlas/inputs/podcasts.opml`
3. **YouTube**: Place video URLs in `/home/ubuntu/dev/atlas/inputs/youtube.txt`
4. **Documents**: Place PDFs and documents in `/home/ubuntu/dev/atlas/inputs/documents/`
5. **Instapaper**: Place Instapaper CSV exports in `/home/ubuntu/dev/atlas/inputs/instapaper.csv`
6. **RSS Feeds**: Place RSS feed URLs in `/home/ubuntu/dev/atlas/inputs/rss_feeds.txt`

### Output Directories

1. **Processed Content**: `/home/ubuntu/dev/atlas/output/`
2. **Transcriptions**: `/home/ubuntu/dev/atlas/output/transcriptions/`
3. **Search Index**: `/home/ubuntu/dev/atlas/output/search_index/`
4. **Cognitive Insights**: `/home/ubuntu/dev/atlas/output/insights/`
5. **Recall Items**: `/home/ubuntu/dev/atlas/output/recall/`
6. **Proactive Content**: `/home/ubuntu/dev/atlas/output/proactive/`

### Automated Processing

Files placed in the input directories are automatically processed by Atlas:

- Articles are fetched and cleaned every 10 minutes
- Podcasts are checked for new episodes hourly
- YouTube videos are transcribed every 30 minutes
- Documents are processed as they're added

## Advanced Configuration

### Environment Variables

Configure Atlas behavior through the `.env` file:

```bash
# API Keys
OPENROUTER_API_KEY=your_openrouter_api_key
OPENAI_API_KEY=your_openai_api_key

# Processing Settings
MAX_ARTICLE_LENGTH=10000
TRANSCRIPTION_MODEL=base
SEARCH_INDEX_REFRESH_INTERVAL=3600

# Storage Settings
OUTPUT_FORMAT=markdown
BACKUP_ENABLED=true
RETENTION_DAYS=365
```

### Custom Processing Scripts

Create custom processing scripts in `/home/ubuntu/dev/atlas/scripts/custom/`:

```python
#!/usr/bin/env python3
# custom_processor.py
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

## Mobile Integration

### iOS Shortcuts

Atlas integrates with iOS Shortcuts for mobile content capture:

1. Share sheet integration for web pages
2. Siri voice commands for quick capture
3. Background processing of shared content

### Share Sheet Configuration

1. Open Settings > Atlas > Share Sheet
2. Enable "Show in Share Sheet"
3. Configure which content types to process automatically

### Siri Commands

Use these Siri commands with Atlas:

- "Save this page to Atlas"
- "Process this document with Atlas"
- "Add to my reading list in Atlas"

## Troubleshooting (common error messages)

### "Connection refused" when accessing Atlas

**Solution**: Make sure the Atlas service is running:
```bash
python atlas_service_manager.py status
# If not running:
python atlas_service_manager.py start
```

### "Module not found" errors

**Solution**: Make sure you've activated the virtual environment:
```bash
source venv/bin/activate
```

### "Permission denied" when running scripts

**Solution**: Make sure the scripts have execute permissions:
```bash
chmod +x /path/to/script.py
```

### Large log files

**Solution**: Atlas automatically rotates logs, but you can manually clean them:
```bash
find logs/ -name "*.log" -size +100M -exec mv {} {}.old \;
```

### API key issues

**Solution**: Check your `.env` file for correct API key configuration:
```bash
cat .env
# Make sure OPENROUTER_API_KEY is set correctly
```

### Memory issues during processing

**Solution**: Reduce batch sizes in configuration:
```bash
# In .env file
MAX_CONCURRENT_PROCESSES=2
ARTICLE_BATCH_SIZE=5
```

### Transcription failures

**Solution**: Check that Whisper is properly installed:
```bash
whisper --version
# If not installed:
pip install openai-whisper
```

### Search index corruption

**Solution**: Rebuild the search index:
```bash
python scripts/rebuild_search_index.py
```

## Performance Optimization

### System Requirements

Minimum system requirements for Atlas:
- RAM: 8GB
- Storage: 50GB free space
- CPU: 2 cores
- OS: Ubuntu 20.04+ or macOS 12+

### Resource Monitoring

Monitor Atlas resource usage:
```bash
python atlas_status.py --detailed
htop  # View system resource usage
```

### Log Analysis

Analyze Atlas logs for performance issues:
```bash
# View recent errors
tail -f logs/atlas_service.log | grep ERROR

# Analyze processing times
grep "Processing completed" logs/atlas_service.log | tail -20
```

## Security Best Practices

### API Key Management

Never commit API keys to version control:
```bash
# Use .env file for API keys
echo "OPENROUTER_API_KEY=your_key_here" >> .env
echo ".env" >> .gitignore
```

### Network Security

Configure firewall rules for Atlas:
```bash
# Only allow local access to API
sudo ufw allow from 127.0.0.1 to any port 8000
```

### Data Encryption

Enable encryption for sensitive data:
```bash
# In .env file
ENCRYPTION_ENABLED=true
ENCRYPTION_KEY=your_encryption_key_here
```

## Backup and Recovery

### Automated Backups

Atlas automatically backs up data:
```bash
# Configure backup schedule in .env
BACKUP_SCHEDULE="0 2 * * *"  # Daily at 2 AM
BACKUP_RETENTION_DAYS=30
```

### Manual Backup

Create a manual backup:
```bash
python scripts/backup_atlas.py --output /path/to/backup/
```

### Restore from Backup

Restore Atlas from a backup:
```bash
python scripts/restore_atlas.py --input /path/to/backup/
```

## Frequently Asked Questions

### How do I update Atlas?

Update Atlas to the latest version:
```bash
git pull origin main
pip install -r requirements.txt
python atlas_service_manager.py restart
```

### Can I run multiple instances?

Yes, configure different ports in `.env`:
```bash
API_PORT=8001
```

### How do I add custom content processors?

Create a new processor in `/helpers/custom_processors/`:
```python
# custom_processor.py
def process(content, metadata):
    # Your processing logic
    return processed_content
```

### What file formats are supported?

Atlas supports these file formats:
- Web pages (HTML)
- Documents (PDF, DOCX, TXT)
- Audio (MP3, WAV, M4A)
- Video (MP4, MOV)
- Images (JPG, PNG, GIF)

### How do I customize the web dashboard?

Modify templates in `/web/templates/`:
- `base.html` - Main layout
- `dashboard.html` - Dashboard page
- `content.html` - Content display
- `settings.html` - Configuration page

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