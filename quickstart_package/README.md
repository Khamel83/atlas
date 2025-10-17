# Atlas Quick Start Package

Welcome to Atlas! This package contains everything you need to quickly get started with Atlas, your personal cognitive amplification platform.

## What's Included

1. **Quick Start Guide** - This document
2. **Installation Script** - Automated setup script
3. **Sample Configuration** - Basic configuration template
4. **First Content Sample** - Example content to process
5. **Quick Launch Script** - Easy way to start Atlas services

## System Requirements

- **Operating System**: Ubuntu 20.04+, macOS 12+, or Windows 10/11 with WSL2
- **Python**: 3.9 or higher
- **RAM**: 8GB minimum (16GB recommended)
- **Disk Space**: 50GB free space minimum
- **Internet Connection**: Required for initial setup and content ingestion

## Quick Installation

### Option 1: Automated Installation (Recommended)

```bash
# Download and run the automated installation script
curl -O https://raw.githubusercontent.com/your-username/atlas/main/quickstart_package/install_atlas.sh
chmod +x install_atlas.sh
./install_atlas.sh
```

### Option 2: Manual Installation

```bash
# Clone the repository
git clone https://github.com/your-username/atlas.git
cd atlas

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run setup wizard
python scripts/setup_wizard.py
```

## First-Time Setup

### 1. Configure Environment

Copy the sample configuration and customize it:

```bash
cp quickstart_package/.env.sample .env
# Edit .env with your API keys and preferences
nano .env
```

### 2. Verify Installation

Run the diagnostic script to verify your installation:

```bash
python scripts/diagnose_environment.py
```

### 3. Start Atlas Services

Start all Atlas services:

```bash
# Start services in background
python atlas_service_manager.py start

# Check status
python atlas_service_manager.py status
```

## Processing Your First Content

### 1. Add Content to Process

Create a list of articles to process:

```bash
echo "https://example.com/article1" > inputs/articles.txt
echo "https://example.com/article2" >> inputs/articles.txt
```

### 2. Process Content

Run the content processing pipeline:

```bash
python run.py --articles
```

### 3. View Results

Check the output directory for processed content:

```bash
ls output/articles/markdown/
```

## Accessing the Web Dashboard

Atlas includes a web dashboard for accessing cognitive features:

```bash
# Start the web server
python web/app.py

# Open your browser to:
# http://localhost:8000
```

Navigate to the "Cognitive Amplification Dashboard" to explore features like:
- Proactive Content Surfacer
- Temporal Relationships
- Socratic Questions
- Active Recall System
- Pattern Detector

## Mobile Integration

### iOS Shortcuts

Atlas includes Apple Shortcuts for mobile content capture:

1. Install the shortcuts from `dist/shortcuts/`
2. Open the Shortcuts app on your iOS device
3. Import the `.shortcut` files
4. Use voice commands or manual execution to capture content

### Share Extensions

Use the share extension to capture content from any app:

1. Open any webpage in Safari
2. Tap the share button
3. Select "Save to Atlas"
4. Content is automatically processed and indexed

## Next Steps

### Explore Documentation

- **User Guides**: Detailed guides in `docs/user-guides/`
- **Setup Guide**: Complete setup instructions in `docs/user-guides/SETUP_GUIDE.md`
- **Ingestion Guide**: Content ingestion methods in `docs/user-guides/INGESTION_GUIDE.md`
- **Mobile Guide**: Mobile usage in `docs/user-guides/MOBILE_GUIDE.md`

### Advanced Features

1. **Automation**: Set up automated content ingestion with cron jobs
2. **API Access**: Use the REST API for programmatic access
3. **Custom Processing**: Extend Atlas with custom content processors
4. **Search**: Use advanced search features to find content

### Join the Community

- **Discord**: https://discord.gg/atlas
- **GitHub Discussions**: https://github.com/your-username/atlas/discussions
- **Reddit**: r/AtlasPlatform

## Troubleshooting

### Common Issues

1. **Services won't start**:
   ```bash
   # Check system resources
   python helpers/resource_monitor.py

   # Check logs
   tail -f logs/atlas_service.log
   ```

2. **Content processing fails**:
   ```bash
   # Check processing logs
   tail -f logs/article_fetcher.log

   # Verify URLs are accessible
   curl -I https://example.com/article1
   ```

3. **Web dashboard not accessible**:
   ```bash
   # Check if web server is running
   ps aux | grep web/app.py

   # Check for port conflicts
   lsof -i :8000
   ```

### Getting Help

For additional help:
1. Check the documentation in `docs/`
2. Run diagnostic scripts in `scripts/`
3. Join the community Discord
4. File issues on GitHub

## Package Contents

This quick start package includes:

```
quickstart_package/
├── README.md                 # This guide
├── install_atlas.sh          # Automated installation script
├── .env.sample               # Sample configuration
├── sample_content.txt        # Example content to process
├── launch_atlas.sh           # Quick launch script
└── shortcuts/                 # iOS shortcuts for mobile capture
    ├── save_to_atlas.shortcut
    ├── voice_memo_to_atlas.shortcut
    └── screenshot_to_atlas.shortcut
```

Enjoy your journey with Atlas! 🚀🧠