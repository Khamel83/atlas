# Atlas Deployment Guide

## Overview

Atlas is a personal knowledge automation system that ingests content from Gmail, RSS feeds, and YouTube, stores it in Obsidian-compatible format, and provides access via CLI and Telegram bot interfaces.

## System Architecture

```
Atlas Architecture
├── Content Sources
│   ├── Gmail API Integration
│   ├── RSS Feed Processing
│   └── YouTube Data API
├── Core Components
│   ├── Storage Manager (Markdown+YAML)
│   ├── Ingestion Engine (with deduplication)
│   ├── Search & Query System
│   └── Configuration Management
├── Interfaces
│   ├── CLI Interface (atlas command)
│   ├── Telegram Bot (polling/webhook)
│   └── REST API (future)
└── Operations
    ├── Performance Monitoring
    ├── Backup & Recovery
    └── Health Checks
```

## Prerequisites

### System Requirements
- **OS**: Ubuntu 20.04+ or CentOS 8+ (or equivalent)
- **Python**: 3.11+ with virtual environment support
- **Memory**: Minimum 2GB RAM (4GB+ recommended)
- **Storage**: Minimum 10GB free space (50GB+ recommended for growth)
- **Network**: Internet access for content ingestion APIs

### Required APIs
- **Gmail API**: For email ingestion
- **YouTube Data API v3**: For video metadata and captions
- **Telegram Bot API**: For bot functionality

### Software Dependencies
```bash
# Core Python packages (automatically installed)
- python-telegram-bot
- feedparser
- requests
- pyyaml
- sqlite3 (built-in)

# System packages
- python3.11-venv
- python3-pip
- sqlite3
- curl
- wget
```

## Installation Methods

### Method 1: Automated Deployment (Recommended)

1. **Clone Repository**
   ```bash
   git clone https://github.com/your-org/atlas.git /opt/atlas
   cd /opt/atlas
   ```

2. **Run Deployment Script**
   ```bash
   sudo ./scripts/deploy.sh
   ```

   This script:
   - Creates `atlas` system user
   - Sets up directory structure
   - Installs Python virtual environment
   - Configures systemd services
   - Creates default configuration files
   - Sets up log rotation

3. **Configure Environment**
   ```bash
   sudo cp /opt/atlas/.env.example /opt/atlas/.env
   sudo nano /opt/atlas/.env
   ```

   Update with your API keys and preferences.

4. **Start Services**
   ```bash
   sudo systemctl enable atlas-ingest atlas-bot atlas-monitor
   sudo systemctl start atlas-ingest atlas-bot atlas-monitor
   ```

### Method 2: Manual Installation

1. **Create User and Directories**
   ```bash
   sudo useradd --system --home-dir /opt/atlas atlas
   sudo mkdir -p /opt/atlas/{src,config,data,logs,vault,monitoring}
   sudo chown -R atlas:atlas /opt/atlas
   ```

2. **Setup Python Environment**
   ```bash
   cd /opt/atlas
   sudo -u atlas python3.11 -m venv venv
   sudo -u atlas ./venv/bin/pip install -r requirements.txt
   ```

3. **Install Systemd Services**
   ```bash
   sudo cp systemd/*.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable atlas-ingest atlas-bot atlas-monitor
   ```

4. **Configure Services**
   ```bash
   sudo -u atlas cp config/production-examples.yaml config/production.yaml
   sudo -u atlas nano config/production.yaml
   ```

## Configuration

### Environment Variables

Create `/opt/atlas/.env`:

```bash
# Core Configuration
ATLAS_CONFIG=/opt/atlas/config/production.yaml
ATLAS_VAULT=/opt/atlas/vault
ATLAS_LOG_LEVEL=INFO

# Gmail Integration
GMAIL_CREDENTIALS_FILE=/opt/atlas/config/gmail-credentials.json
GMAIL_TOKEN_FILE=/opt/atlas/config/gmail-token.json

# YouTube Integration
YOUTUBE_API_KEY=your_youtube_api_key_here

# Telegram Bot
ATLAS_BOT_TOKEN=your_telegram_bot_token_here
ATLAS_BOT_ALLOWED_USERS=123456789,987654321
ATLAS_BOT_ADMIN_CHAT=-1001234567890

# Database
ATLAS_DB_PATH=/opt/atlas/data/atlas.db
```

### Production Configuration

Edit `/opt/atlas/config/production.yaml`:

```yaml
# Atlas Production Configuration
vault:
  root: "/opt/atlas/vault"

ingestion:
  max_concurrent: 3
  rate_limit: 60  # requests per minute
  timeout: 30
  retry_attempts: 3
  retry_delay: 5

database:
  type: "sqlite"
  path: "/opt/atlas/data/atlas.db"
  journal_mode: "WAL"
  synchronous: "NORMAL"

logging:
  level: "INFO"
  format: "json"
  file: "/opt/atlas/logs/atlas.log"
  max_size: "100MB"
  backup_count: 5

monitoring:
  enabled: true
  metrics_path: "/opt/atlas/monitoring/metrics"
  health_check_interval: 60

gmail:
  scopes:
    - "https://www.googleapis.com/auth/gmail.readonly"
    - "https://www.googleapis.com/auth/gmail.modify"
  batch_size: 50
  polling_interval: 300

youtube:
  api_key: "${YOUTUBE_API_KEY}"
  timeout: 30
  max_concurrent: 2

rss:
  user_agent: "Atlas/4.0 (Knowledge Management Bot)"
  timeout: 30
  max_feeds: 1000
```

### Bot Configuration

Create `/opt/atlas/config/bot.yaml`:

```yaml
name: "atlas-bot"
token: "${ATLAS_BOT_TOKEN}"
webhooks: false
allowed_users: ["123456789"]
allowed_chats: ["-1001234567890"]
log_level: "INFO"
log_file: "/opt/atlas/logs/bot/bot.log"
vault_root: "/opt/atlas/vault"
max_inline_results: 10
admin_chat_id: "${ATLAS_BOT_ADMIN_CHAT}"
```

## API Setup

### Gmail API

1. **Enable Gmail API**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create/select project
   - Enable Gmail API

2. **Create Credentials**
   - Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client ID"
   - Select "Desktop application"
   - Download JSON credentials file
   - Save as `/opt/atlas/config/gmail-credentials.json`

3. **Authorize Atlas**
   ```bash
   sudo -u atlas /opt/atlas/venv/bin/python -m atlas.ingestion.gmail authenticate
   ```

### YouTube Data API

1. **Enable YouTube API**
   - In Google Cloud Console, enable "YouTube Data API v3"
   - Create API key (restricted to your server IP if possible)

2. **Configure API Key**
   - Add to `/opt/atlas/.env` as `YOUTUBE_API_KEY`

### Telegram Bot

1. **Create Bot**
   - Message [@BotFather](https://t.me/botfather) on Telegram
   - `/newbot` → Follow prompts
   - Copy bot token

2. **Configure Bot**
   - Add token to `/opt/atlas/.env`
   - Get your user ID: message [@userinfobot](https://t.me/userinfobot)
   - Update `ATLAS_BOT_ALLOWED_USERS`

## Service Management

### Starting Services

```bash
# Start all services
sudo systemctl start atlas-ingest atlas-bot atlas-monitor

# Start individual services
sudo systemctl start atlas-ingest    # Content ingestion
sudo systemctl start atlas-bot       # Telegram bot
sudo systemctl start atlas-monitor   # Monitoring
```

### Stopping Services

```bash
# Stop all services
sudo systemctl stop atlas-ingest atlas-bot atlas-monitor

# Graceful stop (allows current operations to complete)
sudo systemctl kill -s SIGTERM atlas-ingest
```

### Service Status

```bash
# Check all Atlas services
sudo systemctl status atlas-ingest atlas-bot atlas-monitor

# Check individual service
sudo systemctl status atlas-ingest
```

### Viewing Logs

```bash
# Real-time logs
sudo journalctl -u atlas-ingest -f
sudo journalctl -u atlas-bot -f
sudo journalctl -u atlas-monitor -f

# Recent logs (last 100 lines)
sudo journalctl -u atlas-ingest -n 100

# Service-specific log files
sudo tail -f /opt/atlas/logs/ingest/atlas-ingest.log
sudo tail -f /opt/atlas/logs/bot/bot.log
```

## Operations

### Content Ingestion

**CLI Usage:**
```bash
# Ingest from all configured sources
/opt/atlas/venv/bin/python -m atlas.cli ingest --all

# Ingest specific source
/opt/atlas/venv/bin/python -m atlas.cli ingest gmail
/opt/atlas/venv/bin/python -m atlas.cli ingest rss --config config/rss-feeds.yaml
/opt/atlas/venv/bin/python -m atlas.cli ingest youtube --channel-id UC1234567890

# Continuous ingestion mode
/opt/atlas/venv/bin/python -m atlas.cli ingest --continuous --interval 300
```

**Telegram Bot:**
```
/ingest gmail        # Ingest Gmail messages
/ingest rss          # Ingest RSS feeds
/ingest youtube      # Ingest YouTube content
/ingest all          # Ingest from all sources
```

### Search and Query

**CLI Usage:**
```bash
# Search content
/opt/atlas/venv/bin/python -m atlas.cli search "machine learning"

# Search by tag
/opt/atlas/venv/bin/python -m atlas.cli search --tag "research"

# Recent content
/opt/atlas/venv/bin/python -m atlas.cli recent --days 7

# Content by source
/opt/atlas/venv/bin/python -m atlas.cli list --source-type gmail
```

**Telegram Bot:**
```
/search machine learning    # Search content
/recent                    # Recent items
/status                    # System status
/help                      # All commands
@atlas_bot ml              # Inline search
```

### System Monitoring

**Health Checks:**
```bash
# System health report
/opt/atlas/scripts/monitor.py --health-check

# Service status
/opt/atlas/scripts/monitor.py --status

# Performance metrics
/opt/atlas/scripts/monitor.py --metrics
```

**Manual Monitoring:**
```bash
# Check service health
curl http://localhost:8080/health

# View metrics
/opt/atlas/venv/bin/python -c "
from atlas.monitoring.performance import PerformanceMonitor
monitor = PerformanceMonitor()
print(monitor.get_system_summary())
"
```

## Backup and Recovery

### Automated Backups

Backups run automatically via logrotate. Configure retention in `/etc/logrotate.d/atlas`.

### Manual Backup

```bash
# Create full backup
sudo /opt/atlas/scripts/backup.sh backup

# Create backup with custom retention
sudo /opt/atlas/scripts/backup.sh backup --retention 90

# List available backups
sudo /opt/atlas/scripts/backup.sh list

# Restore from backup
sudo /opt/atlas/scripts/backup.sh restore /opt/atlas/backups/atlas_backup_20251016_120000.tar.gz
```

### Disaster Recovery

```bash
# System health assessment
sudo /opt/atlas/scripts/disaster_recovery.sh health-assessment

# Emergency backup
sudo /opt/atlas/scripts/disaster_recovery.sh emergency-backup

# Emergency service restart
sudo /opt/atlas/scripts/disaster_recovery.sh emergency-restart

# Database repair
sudo /opt/atlas/scripts/disaster_recovery.sh repair-database

# Generate disaster recovery report
sudo /opt/atlas/scripts/disaster_recovery.sh dr-report
```

## Maintenance

### Regular Tasks

**Daily:**
- Check service status: `systemctl status atlas-*`
- Review logs for errors: `journalctl -u atlas-* --since "24 hours ago"`
- Monitor disk space: `df -h /opt/atlas`

**Weekly:**
- Review backup logs: `tail /var/log/atlas_backup.log`
- Check ingestion metrics: `/opt/atlas/scripts/monitor.py --metrics`
- Update RSS feed configurations if needed

**Monthly:**
- Review and rotate API keys
- Update Atlas version: `git pull && systemctl restart atlas-*`
- Archive old logs: `find /opt/atlas/logs -name "*.log" -mtime +30 -delete`

### Performance Optimization

**Database Maintenance:**
```bash
# Optimize database
sudo -u atlas sqlite3 /opt/atlas/data/atlas.db "VACUUM; ANALYZE;"

# Check database integrity
sudo -u atlas sqlite3 /opt/atlas/data/atlas.db "PRAGMA integrity_check;"
```

**Log Rotation:**
Configuration in `/etc/logrotate.d/atlas`:
```bash
/opt/atlas/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 atlas atlas
    postrotate
        systemctl reload atlas-ingest atlas-bot atlas-monitor || true
    endscript
}
```

## Troubleshooting

### Common Issues

**Service Won't Start:**
```bash
# Check logs
sudo journalctl -u atlas-ingest -n 50

# Check configuration
sudo -u atlas /opt/atlas/venv/bin/python -c "
import yaml
with open('/opt/atlas/config/production.yaml') as f:
    print(yaml.safe_load(f))
"

# Check permissions
ls -la /opt/atlas/
```

**Ingestion Failures:**
```bash
# Check API credentials
sudo -u atlas /opt/atlas/venv/bin/python -c "
from atlas.ingestion.gmail import GmailIngestor
ingestor = GmailIngestor('/opt/atlas/config/gmail-credentials.json')
print('Gmail credentials valid:', ingestor.authenticate())
"

# Check quotas
/opt/atlas/venv/bin/python -m atlas.cli status --detailed
```

**Search Issues:**
```bash
# Rebuild search index
sudo -u atlas /opt/atlas/venv/bin/python -c "
from atlas.storage import StorageManager
storage = StorageManager('/opt/atlas/vault')
storage.rebuild_search_index()
"
```

**Telegram Bot Not Responding:**
```bash
# Check bot token
curl -X GET "https://api.telegram.org/bot${ATLAS_BOT_TOKEN}/getMe"

# Check webhook status (if using webhooks)
curl -X GET "https://api.telegram.org/bot${ATLAS_BOT_TOKEN}/getWebhookInfo"
```

### Performance Issues

**High Memory Usage:**
```bash
# Monitor memory
top -p $(pgrep -f atlas)

# Restart services if needed
sudo systemctl restart atlas-ingest
```

**Slow Search:**
```bash
# Check database size
sudo -u atlas sqlite3 /opt/atlas/data/atlas.db "
SELECT COUNT(*) FROM content;
SELECT COUNT(*) FROM search_index;
"

# Optimize database
sudo -u atlas sqlite3 /opt/atlas/data/atlas.db "REINDEX;"
```

### Getting Help

**Logs:**
```bash
# All Atlas logs
sudo journalctl -u atlas-* --since "1 hour ago"

# Specific component logs
sudo tail -f /opt/atlas/logs/ingest/atlas-ingest.log
```

**System Information:**
```bash
# System status
/opt/atlas/scripts/monitor.py --health-check

# Service status
systemctl status atlas-ingest atlas-bot atlas-monitor
```

**Support:**
- Check [GitHub Issues](https://github.com/your-org/atlas/issues)
- Review [Documentation](https://github.com/your-org/atlas/wiki)
- Check log files for specific error messages

## Security

### API Key Management

- Store API keys in `/opt/atlas/.env` with appropriate permissions (600)
- Rotate API keys regularly
- Use IP restrictions where possible
- Monitor API usage for anomalies

### File Permissions

```bash
# Verify secure permissions
sudo find /opt/atlas -type f -exec ls -la {} \; | grep -v "^-rw-------"

# Fix permissions if needed
sudo chown -R atlas:atlas /opt/atlas
sudo chmod 600 /opt/atlas/.env
sudo chmod 644 /opt/atlas/config/*.yaml
```

### Network Security

- Use HTTPS for webhooks
- Restrict API access to server IP
- Monitor network traffic for anomalies
- Use firewall to restrict access

## Scaling

### Horizontal Scaling

For high-volume deployments:

1. **Multiple Ingestion Workers**
   ```yaml
   ingestion:
     max_concurrent: 10
     workers: 3
   ```

2. **Database Optimization**
   ```bash
   # Move to PostgreSQL for high volume
   # Configure connection pooling
   # Enable read replicas
   ```

3. **Load Balancing**
   ```bash
   # Configure nginx for webhook load balancing
   # Use HAProxy for multiple bot instances
   ```

### Performance Tuning

**Ingestion Optimization:**
```yaml
ingestion:
  rate_limit: 120  # Increase for high-volume sources
  batch_size: 100   # Process in larger batches
  timeout: 60       # Longer timeout for slow sources
```

**Search Optimization:**
```bash
# Enable full-text search
sudo -u atlas sqlite3 /opt/atlas/data/atlas.db "
CREATE VIRTUAL TABLE content_fts USING fts5(title, content);
INSERT INTO content_fts(rowid, title, content)
SELECT rowid, title, content FROM content;
"
```

## Upgrade Path

### Minor Version Updates

```bash
# Backup current installation
sudo /opt/atlas/scripts/backup.sh backup

# Update code
cd /opt/atlas
sudo -u atlas git pull origin main

# Restart services
sudo systemctl restart atlas-ingest atlas-bot atlas-monitor

# Verify functionality
/opt/atlas/scripts/monitor.py --health-check
```

### Major Version Updates

1. **Review Release Notes**
2. **Full Backup**
3. **Test in Staging**
4. **Update Configuration**
5. **Migrate Data if Needed**
6. **Update Services**
7. **Verify All Functionality**

## Appendices

### Environment Variables Reference

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `ATLAS_CONFIG` | Main configuration file path | No | `./config/production.yaml` |
| `ATLAS_VAULT` | Vault root directory | No | `./vault` |
| `ATLAS_LOG_LEVEL` | Logging level | No | `INFO` |
| `ATLAS_BOT_TOKEN` | Telegram bot token | Yes | - |
| `ATLAS_BOT_ALLOWED_USERS` | Allowed user IDs | Yes | - |
| `YOUTUBE_API_KEY` | YouTube API key | No | - |
| `GMAIL_CREDENTIALS_FILE` | Gmail credentials path | No | - |

### Configuration File Reference

See `/opt/atlas/config/production-examples.yaml` for comprehensive configuration examples.

### Service Dependencies

```
atlas-ingest (Content Ingestion)
├── Gmail API
├── YouTube Data API
├── RSS Feed Access
└── Database (SQLite)

atlas-bot (Telegram Interface)
├── Telegram Bot API
├── Storage Access
└── Search Index

atlas-monitor (Monitoring)
├── System Metrics
├── Service Health
└── Performance Data
```

### Default Ports

| Service | Port | Protocol | Description |
|---------|------|----------|-------------|
| Telegram Bot (Polling) | N/A | HTTPS | Outbound to Telegram API |
| Telegram Bot (Webhook) | 8443 | HTTPS | Inbound webhook (optional) |
| Monitoring Dashboard | 8080 | HTTP | Local metrics dashboard |

### File Locations

| Type | Location | Description |
|------|----------|-------------|
| Application Code | `/opt/atlas/src/` | Atlas source code |
| Configuration | `/opt/atlas/config/` | YAML configuration files |
| Data | `/opt/atlas/data/` | SQLite database, queue files |
| Logs | `/opt/atlas/logs/` | Application and service logs |
| Vault | `/opt/atlas/vault/` | Obsidian-compatible content storage |
| Monitoring | `/opt/atlas/monitoring/` | Metrics and health data |
| Backups | `/opt/atlas/backups/` | System backups |
| Scripts | `/opt/atlas/scripts/` | Management and maintenance scripts |