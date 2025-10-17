# Atlas External Requirements Setup Guide

This guide covers all external services, APIs, and optional integrations required for Atlas to function fully. Follow this guide to configure Atlas for complete functionality.

## Table of Contents

1. [Required Services](#required-services)
2. [Optional Services](#optional-services)
3. [Configuration Summary](#configuration-summary)
4. [Validation and Testing](#validation-and-testing)
5. [Troubleshooting](#troubleshooting)

## Required Services

### 1. OpenRouter API (AI Processing)

**Purpose**: Powers all Atlas cognitive features using Gemini 2.5 Flash Lite
**Cost**: ~$0.05 per 1M tokens (very affordable)
**Setup Time**: 5 minutes

#### Setup Steps:
1. **Create Account:**
   - Visit [OpenRouter.ai](https://openrouter.ai)
   - Sign up with your email address
   - Verify email and complete account setup

2. **Generate API Key:**
   - Go to "API Keys" in your dashboard
   - Click "Create New Key"
   - Name it "Atlas Personal Knowledge System"
   - Copy the key (starts with `sk-or-v1-`)

3. **Configure Atlas:**
   ```bash
   # Add to your .env file
   OPENROUTER_API_KEY=sk-or-v1-your-key-here
   DEFAULT_LLM_PROVIDER=openrouter
   DEFAULT_MODEL=google/gemini-2.5-flash-lite
   ```

4. **Test Configuration:**
   ```bash
   python3 -c "
   from helpers.ai_interface import get_ai_response
   response = get_ai_response('Hello, test message')
   print('API Status: Working' if response else 'API Status: Failed')
   "
   ```

#### Cost Estimation:
- **Light Usage**: $1-3/month (personal notes, some articles)
- **Medium Usage**: $5-10/month (active content processing)
- **Heavy Usage**: $15-25/month (full podcast/video transcription)

## Optional Services

### 2. YouTube Data API v3 (Video Processing)

**Purpose**: Automated YouTube video discovery and processing
**Cost**: Free (10,000 API units/day)
**Setup Time**: 10 minutes

#### Setup Steps:
1. **Create Google Cloud Project:**
   - Visit [Google Cloud Console](https://console.cloud.google.com)
   - Create new project: "Atlas YouTube Integration"
   - Enable YouTube Data API v3

2. **Generate API Key:**
   - Go to "Credentials" → "Create Credentials" → "API Key"
   - Restrict key to YouTube Data API v3
   - Copy the API key

3. **Configure Atlas:**
   ```bash
   # Add to your .env file
   YOUTUBE_API_KEY=your-youtube-api-key-here
   YOUTUBE_ENABLED=true
   YOUTUBE_PROCESSING_INTERVAL=300  # 5 hours
   ```

4. **Test Configuration:**
   ```bash
   python3 -c "
   from integrations.youtube_api_client import YouTubeAPIClient
   client = YouTubeAPIClient()
   print('YouTube API Status:', client.test_connection())
   "
   ```

#### Usage Limits:
- **10,000 units/day** (free tier)
- **Search query**: 100 units
- **Video details**: 1 unit
- **Typical daily usage**: 500-2000 units

### 3. Oracle Cloud Infrastructure (PODEMOS RSS Hosting)

**Purpose**: Private RSS feed hosting for ad-free podcasts
**Cost**: Free tier available
**Setup Time**: 20 minutes

#### Setup Steps:
1. **Create OCI Account:**
   - Visit [Oracle Cloud](https://cloud.oracle.com)
   - Sign up for free tier account
   - Complete identity verification

2. **Create Object Storage Bucket:**
   - Navigate to Object Storage & Archive Storage
   - Create bucket: "atlas-podemos-feeds"
   - Set visibility to "Public"
   - Note region and bucket name

3. **Generate Access Keys:**
   - Go to Identity & Security → Users
   - Select your user → Customer Secret Keys
   - Generate new secret key pair
   - Download credentials

4. **Configure Atlas:**
   ```bash
   # Add to your .env file
   PODEMOS_ENABLED=true
   OCI_BUCKET_NAME=atlas-podemos-feeds
   OCI_REGION=us-ashburn-1
   OCI_ACCESS_KEY=your-access-key
   OCI_SECRET_KEY=your-secret-key
   PODEMOS_RSS_HOST=yourdomain.com  # Optional custom domain
   ```

### 4. Mac Mini Integration (Enhanced Audio Processing)

**Purpose**: Dedicated Whisper transcription processing
**Cost**: Hardware cost only
**Setup Time**: 30 minutes

#### Requirements:
- Mac Mini with macOS 12+
- 8GB+ RAM (16GB recommended)
- SSH access from Atlas server

#### Setup Steps:
1. **Configure Mac Mini:**
   ```bash
   # Run on Mac Mini
   curl -O https://raw.githubusercontent.com/your-username/atlas/main/scripts/install_mac_mini_software.sh
   chmod +x install_mac_mini_software.sh
   ./install_mac_mini_software.sh
   ```

2. **Setup SSH Access:**
   ```bash
   # Run on Atlas server
   curl -O https://raw.githubusercontent.com/your-username/atlas/main/scripts/setup_mac_mini_ssh.sh
   chmod +x setup_mac_mini_ssh.sh
   ./setup_mac_mini_ssh.sh
   ```

3. **Configure Atlas:**
   ```bash
   # Add to your .env file
   MAC_MINI_ENABLED=true
   MAC_MINI_SSH_HOST=macmini  # or IP address
   MAC_MINI_WHISPER_MODEL=base
   MAC_MINI_TIMEOUT=300
   ```

4. **Test Integration:**
   ```bash
   python3 -c "
   from helpers.mac_mini_client import MacMiniClient
   client = MacMiniClient()
   print('Mac Mini Status:', client.test_connection())
   "
   ```

### 5. Email Integration (IMAP)

**Purpose**: Email content processing
**Cost**: Free (uses existing email)
**Setup Time**: 10 minutes

#### Supported Providers:
- Gmail (recommended)
- Outlook/Hotmail
- Yahoo Mail
- Custom IMAP servers

#### Setup Steps (Gmail Example):
1. **Enable App Passwords:**
   - Go to Google Account Security
   - Enable 2-Factor Authentication
   - Generate App Password for "Atlas"

2. **Configure Atlas:**
   ```bash
   # Add to your .env file
   EMAIL_ENABLED=true
   EMAIL_IMAP_HOST=imap.gmail.com
   EMAIL_IMAP_PORT=993
   EMAIL_USERNAME=your-email@gmail.com
   EMAIL_PASSWORD=your-app-password
   EMAIL_FOLDER=Atlas  # Folder to monitor
   ```

### 6. Backup Services (Optional)

**Purpose**: Automated system backups
**Cost**: Storage costs only
**Setup Time**: 15 minutes

#### Local Backup:
```bash
# Add to your .env file
BACKUP_ENABLED=true
BACKUP_SCHEDULE=daily
BACKUP_RETENTION_DAYS=30
```

#### Remote Backup:
```bash
# Add to your .env file
BACKUP_REMOTE_ENABLED=true
BACKUP_REMOTE_HOST=backup-server.com
BACKUP_REMOTE_USER=atlas-backup
BACKUP_REMOTE_PATH=/backups/atlas
```

## Configuration Summary

### Complete .env Template

```bash
# === CORE ATLAS CONFIGURATION ===
DATABASE_URL=sqlite:///atlas.db
API_HOST=localhost
API_PORT=7444
API_DEBUG=false

# === REQUIRED: AI PROCESSING ===
OPENROUTER_API_KEY=sk-or-v1-your-key-here
DEFAULT_LLM_PROVIDER=openrouter
DEFAULT_MODEL=google/gemini-2.5-flash-lite

# === OPTIONAL: YOUTUBE INTEGRATION ===
YOUTUBE_API_KEY=your-youtube-api-key-here
YOUTUBE_ENABLED=true
YOUTUBE_PROCESSING_INTERVAL=300

# === OPTIONAL: PODEMOS RSS HOSTING ===
PODEMOS_ENABLED=true
OCI_BUCKET_NAME=atlas-podemos-feeds
OCI_REGION=us-ashburn-1
OCI_ACCESS_KEY=your-access-key
OCI_SECRET_KEY=your-secret-key
PODEMOS_RSS_HOST=yourdomain.com

# === OPTIONAL: MAC MINI INTEGRATION ===
MAC_MINI_ENABLED=true
MAC_MINI_SSH_HOST=macmini
MAC_MINI_WHISPER_MODEL=base
MAC_MINI_TIMEOUT=300

# === OPTIONAL: EMAIL INTEGRATION ===
EMAIL_ENABLED=true
EMAIL_IMAP_HOST=imap.gmail.com
EMAIL_IMAP_PORT=993
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
EMAIL_FOLDER=Atlas

# === OPTIONAL: BACKUP CONFIGURATION ===
BACKUP_ENABLED=true
BACKUP_SCHEDULE=daily
BACKUP_RETENTION_DAYS=30
BACKUP_REMOTE_ENABLED=false
```

## Validation and Testing

### System Health Check

Run comprehensive validation:

```bash
# Check all external service configurations
python3 scripts/validate_config.py

# Test all API connections
python3 scripts/validate_dependencies.py --test-apis

# Verify complete system health
python3 atlas_status.py --detailed
```

### Individual Service Tests

```bash
# Test OpenRouter API
python3 -c "
from helpers.ai_interface import get_ai_response
print('OpenRouter:', 'OK' if get_ai_response('test') else 'FAILED')
"

# Test YouTube API
python3 -c "
from integrations.youtube_api_client import YouTubeAPIClient
print('YouTube:', YouTubeAPIClient().test_connection())
"

# Test Mac Mini Connection
python3 -c "
from helpers.mac_mini_client import MacMiniClient
print('Mac Mini:', MacMiniClient().test_connection())
"

# Test Email Connection
python3 -c "
from helpers.email_integration import test_email_connection
print('Email:', test_email_connection())
"
```

## Troubleshooting

### Common Issues

#### "OpenRouter API key invalid"
- Verify key starts with `sk-or-v1-`
- Check for extra spaces or characters
- Regenerate key in OpenRouter dashboard

#### "YouTube API quota exceeded"
- Check Google Cloud Console quota usage
- Wait 24 hours for reset
- Consider upgrading quota if needed

#### "Mac Mini connection failed"
- Test SSH manually: `ssh macmini`
- Check Mac Mini is powered on and connected
- Verify SSH key configuration

#### "Email authentication failed"
- Ensure app password is used (not regular password)
- Check IMAP settings for your provider
- Verify 2FA is enabled for Gmail

#### "OCI bucket access denied"
- Verify bucket name and region
- Check access key permissions
- Ensure bucket has correct visibility settings

### Service Status Dashboard

Monitor all external services:

```bash
# Real-time service monitoring
python3 helpers/service_monitor.py --real-time

# Generate service status report
python3 helpers/service_monitor.py --report
```

### Cost Monitoring

Track API usage and costs:

```bash
# Check OpenRouter usage
python3 scripts/usage_monitor.py --openrouter

# Check YouTube API quota
python3 scripts/usage_monitor.py --youtube

# Generate cost estimate
python3 scripts/cost_estimator.py
```

## Quick Setup Checklist

- [ ] **OpenRouter API** - Get API key and test connection
- [ ] **YouTube API** - Enable API and test (optional)
- [ ] **OCI Setup** - Create bucket for PODEMOS (optional)
- [ ] **Mac Mini** - Configure SSH and Whisper (optional)
- [ ] **Email IMAP** - Setup app password (optional)
- [ ] **Backup Config** - Configure local/remote backup (optional)
- [ ] **Test All Services** - Run validation scripts
- [ ] **Monitor Setup** - Verify service monitoring works

## Getting Help

- **Configuration Issues**: Run `python3 scripts/diagnose_environment.py`
- **API Troubleshooting**: Check `logs/api_errors.log`
- **Service Status**: Monitor via `python3 atlas_status.py --detailed`
- **Community Support**: See main README for support channels

---

**💡 Pro Tip**: Start with just OpenRouter API for core functionality, then add optional services as needed. Atlas will work perfectly with just the required service configured.