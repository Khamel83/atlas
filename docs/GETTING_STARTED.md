# Getting Started with Atlas

## 🚀 Quick Start Guide

This guide will help you get Atlas up and running in minutes. Atlas automatically ingests content from Gmail, RSS feeds, and YouTube, making it searchable and accessible through CLI and Telegram.

## 📋 Prerequisites

- Python 3.11+
- Git
- (Optional) Gmail API access
- (Optional) YouTube Data API key
- (Optional) Telegram bot token

## 🔧 Installation

### 1. Clone Atlas

```bash
git clone https://github.com/Khamel83/atlas.git
cd atlas
```

### 2. Set Up Python Environment

```bash
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Create Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit the configuration
nano .env
```

Add your API keys to `.env`:

```bash
# Required for Telegram bot (if you want bot features)
ATLAS_BOT_TOKEN=your_telegram_bot_token_here
ATLAS_BOT_ALLOWED_USERS=123456789,987654321  # Your Telegram user IDs

# Required for YouTube ingestion
YOUTUBE_API_KEY=your_youtube_api_key_here

# Required for Gmail ingestion
GMAIL_CREDENTIALS_FILE=/path/to/gmail-credentials.json

# Optional: Custom vault location
ATLAS_VAULT=/path/to/your/obsidian/vault
```

## 🔑 API Setup

### Gmail API (Optional but Recommended)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable "Gmail API"
4. Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client ID"
5. Select "Desktop application"
6. Download the JSON file and save it as `gmail-credentials.json`
7. Add path to `.env`: `GMAIL_CREDENTIALS_FILE=/path/to/gmail-credentials.json`

### YouTube Data API (Optional but Recommended)

1. In Google Cloud Console, enable "YouTube Data API v3"
2. Go to "Credentials" → "Create Credentials" → "API Key"
3. Create API key (restrict to your server IP if possible)
4. Add to `.env`: `YOUTUBE_API_KEY=your_api_key_here`

### Telegram Bot (Optional but Recommended)

1. Message [@BotFather](https://t.me/botfather) on Telegram
2. `/newbot` → Follow prompts to create your bot
3. Copy the bot token
4. Add to `.env`: `ATLAS_BOT_TOKEN=your_token_here`
5. Get your user ID by messaging [@userinfobot](https://t.me/userinfobot)
6. Add to `.env`: `ATLAS_BOT_ALLOWED_USERS=your_user_id`

## 🏃‍♂️ Run Atlas

### Option 1: CLI Mode

```bash
# Initialize your vault
python -m atlas init --vault /path/to/your/vault

# Ingest content from all sources
python -m atlas ingest --all

# Search your content
python -m atlas search "machine learning"

# See recent content
python -m atlas recent
```

### Option 2: Telegram Bot

```bash
# Start the bot
python -m atlas bot

# Or use the run script
./scripts/run-bot.py --token YOUR_BOT_TOKEN
```

Then in Telegram:
- `/start` - Setup and welcome message
- `/ingest gmail` - Ingest Gmail messages
- `/search AI` - Search for AI-related content
- `/recent` - Show recent items
- `/status` - System status

### Option 3: Production Deployment

```bash
# Deploy as services (requires sudo)
sudo ./scripts/deploy.sh

# Start services
sudo systemctl start atlas-ingest atlas-bot atlas-monitor

# Check status
sudo systemctl status atlas-*
```

## 📁 Your First Content

### Ingest from RSS

Create a simple RSS feed file:

```bash
# Add RSS feeds
echo "https://feeds.simplecast.com/your-podcast" >> feeds.txt
echo "https://blog.example.com/rss" >> feeds.txt

# Ingest RSS content
python -m atlas ingest rss --feeds feeds.txt
```

### Search Your Content

```bash
# Search by keyword
python -m atlas search "your search term"

# Search by tag
python -m atlas search --tag research

# See recent items
python -m atlas recent --days 7
```

## 📚 Find Your Content

Atlas stores content in your vault in Obsidian-compatible format:

```
your-vault/
├── inbox/
│   ├── rss/2025/10/
│   │   ├── article-title-2025-10-16.md
│   │   └── podcast-episode-2025-10-16.md
│   └── gmail/2025/10/
│       └── important-email-2025-10-16.md
└── processed/
    └── (processed content)
```

Each file contains:
- YAML frontmatter with metadata
- Full content in markdown format
- Tags and links for easy searching

## 🔍 Search Examples

```bash
# Basic search
python -m atlas search "python programming"

# Search by source
python -m atlas search --source-type gmail

# Search by tag
python -m atlas search --tag research

# Recent content
python -m atlas recent --days 7 --source-type rss

# Advanced search
python -m atlas search "machine learning" --tag research --source-type youtube
```

## 📊 Check Status

```bash
# System overview
python -m atlas status

# Database statistics
python -m atlas stats

# Vault information
python -m atlas vault info
```

## 🤖 Telegram Bot Commands

Once your bot is running, you can use these commands:

```
/start              # Setup and welcome message
/ingest all          # Ingest from all sources
/ingest gmail        # Ingest Gmail messages
/ingest rss          # Ingest RSS feeds
/ingest youtube      # Ingest YouTube content
/search <query>      # Search your knowledge base
/recent              # Show recent items
/status              # System status
/help                # Show all commands
```

## 🔧 Configuration

### Basic Configuration

Edit `.env` to customize:

```bash
# Vault location
ATLAS_VAULT=/path/to/your/obsidian/vault

# Logging level
ATLAS_LOG_LEVEL=INFO

# Ingestion settings
INGESTION_MAX_CONCURRENT=3
INGESTION_RATE_LIMIT=60
```

### Advanced Configuration

Edit `config/production.yaml` for advanced settings:

```yaml
vault:
  root: "/path/to/vault"

ingestion:
  max_concurrent: 3
  rate_limit: 60
  timeout: 30

logging:
  level: "INFO"
  file: "/path/to/logs/atlas.log"

gmail:
  polling_interval: 300
  batch_size: 50

youtube:
  max_concurrent: 2
  timeout: 30
```

## 🚨 Troubleshooting

### Common Issues

**Python version error:**
```bash
# Make sure you have Python 3.11+
python3.11 --version
```

**Import errors:**
```bash
# Install dependencies
pip install -r requirements.txt
```

**API key errors:**
```bash
# Check your .env file
cat .env

# Verify API keys are correct
python -m atlas validate --api-keys
```

**Permission errors:**
```bash
# Fix vault permissions
chmod -R 755 /path/to/your/vault
```

### Get Help

- Check logs: `tail -f logs/atlas.log`
- Run health check: `python -m atlas health`
- Check status: `python -m atlas status`
- See documentation: `docs/` folder

## 🎯 Next Steps

1. **Set up your APIs** if you haven't already
2. **Configure your vault** location
3. **Ingest some content** to test it out
4. **Explore the search** functionality
5. **Set up the Telegram bot** for mobile access
6. **Configure automated ingestion** for continuous updates

## 📚 More Documentation

- [Deployment Guide](DEPLOYMENT_GUIDE.md) - Production deployment
- [Configuration Guide](docs/configuration.md) - Advanced configuration
- [API Documentation](docs/api.md) - Complete API reference
- [Troubleshooting](docs/troubleshooting.md) - Common issues

---

**Happy knowledge management!** 🧠✨