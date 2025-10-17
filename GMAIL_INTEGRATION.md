# Atlas Gmail Integration

Real-time Gmail-to-Atlas integration using push notifications for automated content ingestion.

## 🚀 Overview

This integration allows Atlas to automatically process Gmail messages in real-time, extracting URLs, attachments, and content to store in your Atlas knowledge base. Perfect for the `khamel83+atlas@gmail.com` workflow!

## ✨ Features

- **Real-time Processing**: Gmail Push Notifications with sub-5-second processing
- **Dual Label Support**: Processes both "Atlas" and "Newsletter" labels
- **URL Extraction**: Automatically extracts all URLs from email content
- **Attachment Support**: Downloads and stores email attachments (up to 25MB)
- **Deduplication**: Prevents processing the same message multiple times
- **iOS Shortcut Ready**: Perfect integration with iOS sharing shortcuts
- **Atlas Integration**: Content stored directly in your existing Atlas database

## 🏗️ Architecture

```
Gmail → Pub/Sub → Atlas API → Gmail Processor → Atlas Database
                    ↓
            Real-time Processing:
            - khamel83+atlas@gmail.com → "Atlas" label
            - Newsletters → "Newsletter" label
```

## 📋 Setup Guide

### 1. Gmail API Configuration

1. **Create Google Cloud Project**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one

2. **Enable APIs**
   - Enable Gmail API
   - Enable Pub/Sub API

3. **Create OAuth2 Credentials**
   - Go to "APIs & Services" → "Credentials"
   - "Create Credentials" → "OAuth client ID"
   - Application type: "Desktop app"
   - Download JSON file as `config/gmail_credentials.json`

### 2. GCP Pub/Sub Setup

```bash
# Set your project ID
export PROJECT_ID="your-gcp-project-id"

# Create topic
gcloud pubsub topics create gmail-notifications --project=$PROJECT_ID

# Create push subscription
gcloud pubsub subscriptions create gmail-push-subscription \
    --topic=gmail-notifications \
    --push-endpoint=https://your-domain.com:7444/gmail/webhook \
    --ack-deadline=600 \
    --project=$PROJECT_ID
```

### 3. Atlas Configuration

1. **Update your `.env` file**:
   ```env
   # Enable Gmail integration
   GMAIL_ENABLED=true

   # Gmail API Configuration
   GMAIL_CREDENTIALS_PATH=config/gmail_credentials.json
   GMAIL_TOKEN_PATH=data/gmail_token.json
   GMAIL_WATCH_LABELS=["Atlas", "Newsletter"]

   # GCP Configuration
   GCP_PROJECT_ID=your-gcp-project-id
   PUBSUB_TOPIC=gmail-notifications
   PUBSUB_SUBSCRIPTION=gmail-push-subscription
   GMAIL_WEBHOOK_SECRET=your-webhook-secret-key
   ```

2. **Create config directory**:
   ```bash
   mkdir -p config
   # Place your gmail_credentials.json here
   ```

### 4. Gmail Filter Setup

Set up Gmail filters to automatically apply labels:

**Filter for khamel83+atlas@gmail.com:**
- From: Any
- To: khamel83+atlas@gmail.com
- Action: Apply label "Atlas"

**Filter for Newsletters:**
- From: [newsletter sources]
- Action: Apply label "Newsletter"

### 5. Start Atlas

```bash
# Start Atlas API with Gmail integration
python api.py

# Or use the existing Atlas startup script
./start_atlas.sh
```

## 📱 iOS Shortcut Setup

### Create the iOS Shortcut:

1. **Create New Shortcut**
2. **Add "Share Content" Action**
3. **Add "Send Email" Action** with:
   - To: `khamel83+atlas@gmail.com`
   - Subject: `Atlas Bookmark: [Title]` (auto-generated)
   - Body: [URL + any notes]
4. **Save as "Atlas Bookmark"**

### Usage:
- In any app, use Share → "Atlas Bookmark"
- Automatically emails to `khamel83+atlas@gmail.com`
- Gmail applies "Atlas" label
- Atlas processes within 5 seconds
- Content appears in your Atlas knowledge base

## 🔧 Atlas API Endpoints

### Gmail Webhook
- `POST /gmail/webhook` - Receives Gmail Pub/Sub notifications
- **Internal use only** - called by Google Pub/Sub

### Authentication
- `GET /gmail/auth/status` - Check Gmail authentication status
- `POST /gmail/auth` - Start Gmail OAuth2 authentication flow

### Statistics
- `GET /gmail/stats` - Get Gmail integration statistics

## 📊 Monitoring

### Check Gmail Status:
```bash
curl http://localhost:7444/gmail/auth/status
```

### Check Gmail Statistics:
```bash
curl http://localhost:7444/gmail/stats
```

### Atlas API Documentation:
- Visit `http://localhost:7444/docs` for full API documentation
- Gmail endpoints are listed under "Gmail Integration"

## 🗄️ Database Schema

Gmail content is stored in the existing Atlas `content` table with:

- `content_type`: `gmail_atlas` or `gmail_newsletter`
- `title`: Email subject or generated title
- `url`: Extracted URLs (one content record per URL)
- `content`: Full email content
- `metadata`: JSON with Gmail-specific data:
  ```json
  {
    "source": "gmail",
    "gmail_message_id": "12345",
    "gmail_thread_id": "67890",
    "sender_email": "sender@example.com",
    "sender_name": "Sender Name",
    "gmail_timestamp": "2025-01-13T10:30:00Z",
    "labels": ["Atlas"],
    "attachments": [...],
    "url_count": 3
  }
  ```

## 🔍 Content Discovery

### Find Gmail Content in Atlas:

1. **Via Atlas Search**:
   - Search for `content_type:gmail_atlas` for Atlas emails
   - Search for `content_type:gmail_newsletter` for newsletters

2. **Via Atlas API**:
   ```bash
   curl "http://localhost:7444/content?q=content_type:gmail_atlas"
   ```

3. **Via Database**:
   ```sql
   SELECT * FROM content
   WHERE content_type IN ('gmail_atlas', 'gmail_newsletter')
   ORDER BY created_at DESC;
   ```

## 🚨 Troubleshooting

### Gmail Authentication Issues:
```bash
# Check authentication status
curl http://localhost:7444/gmail/auth/status

# Re-authenticate if needed
curl -X POST http://localhost:7444/gmail/auth
```

### Webhook Issues:
- Check Pub/Sub subscription endpoint URL
- Verify Atlas API is accessible from the internet
- Check Atlas logs for Gmail webhook errors

### Missing Content:
- Verify Gmail labels are applied correctly
- Check Pub/Sub notifications are being received
- Look in Atlas logs for processing errors

## 🔒 Security

- Gmail credentials stored securely in `config/gmail_credentials.json`
- OAuth2 tokens automatically refresh
- Webhook signature verification (basic implementation)
- No sensitive data logged in production

## 📈 Performance

- **Processing Speed**: Sub-5 second processing from email to Atlas
- **Scalability**: Handles multiple concurrent messages
- **Storage**: Efficient storage with attachment size limits
- **Reliability**: Automatic retry on failed processing

## 🔄 Real-time Workflow

1. **User Action**: iOS Shortcut → Email to `khamel83+atlas@gmail.com`
2. **Gmail Filter**: Automatically applies "Atlas" label
3. **Gmail Push**: Sends notification to Pub/Sub
4. **Pub/Sub**: Pushes to Atlas webhook endpoint
5. **Atlas Processing**: Extracts URLs/attachments, creates content records
6. **Result**: Content available in Atlas within seconds

## 📚 Additional Resources

- [Atlas Main Documentation](README.md)
- [Atlas API Documentation](http://localhost:7444/docs)
- [Google Cloud Console](https://console.cloud.google.com/)
- [Gmail API Documentation](https://developers.google.com/gmail/api)

---

## 🎯 Quick Start Summary

1. **Set up Gmail API credentials** → `config/gmail_credentials.json`
2. **Configure GCP Pub/Sub** → Create topic and subscription
3. **Update Atlas `.env`** → Enable Gmail integration
4. **Create Gmail filters** → Auto-label emails
5. **Start Atlas** → Real-time processing begins

Your Gmail content will now flow into Atlas automatically in real-time!