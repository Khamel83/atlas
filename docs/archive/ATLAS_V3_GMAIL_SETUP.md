# Atlas v3 Gmail Integration Setup

Complete setup guide for integrating Gmail bookmark processing into Atlas v3.

## 🎯 Overview

Atlas v3 + Gmail provides real-time processing of emails with:
- **khamel83+atlas@gmail.com** → "Atlas" label processing
- **Newsletter** label processing
- Real-time webhook notifications
- URL and attachment extraction
- SQLite database integration

## 📋 Prerequisites

1. **Gmail API Access**
   - Google Cloud Console account
   - Gmail API enabled
   - OAuth2 credentials

2. **Python Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## 🚀 Setup Steps

### 1. Gmail API Configuration

1. **Go to Google Cloud Console**
   - Visit https://console.cloud.google.com/
   - Create/select your project
   - Enable Gmail API

2. **Create OAuth2 Credentials**
   - Go to "APIs & Services" → "Credentials"
   - "Create Credentials" → "OAuth client ID"
   - Application type: "Desktop app"
   - Download JSON file

3. **Store Credentials**
   ```bash
   mkdir -p config
   cp downloaded_credentials.json config/gmail_credentials.json
   ```

### 2. Gmail Label Setup

Create filters in Gmail to automatically label messages:

1. **Atlas Label Filter**
   - From: any email to `khamel83+atlas@gmail.com`
   - Apply label: "Atlas"

2. **Newsletter Label Filter**
   - Existing newsletters or specific senders
   - Apply label: "Newsletter"

### 3. Configuration

1. **Copy configuration template**
   ```bash
   cp config/gmail_config.example.json config/gmail_config.json
   ```

2. **Edit configuration**
   ```json
   {
     "gmail": {
       "credentials_path": "config/gmail_credentials.json",
       "token_path": "config/gmail_token.json",
       "watch_labels": ["Atlas", "Newsletter"],
       "webhook_secret": "your-secret-here"
     },
     "server": {
       "host": "localhost",
       "port": 8080
     }
   }
   ```

### 4. Run Atlas v3 Gmail

```bash
python3 atlas_v3_gmail.py
```

**First Run**: Will open browser for OAuth authentication

## 📱 iOS Shortcut Setup

### Create "Send to Atlas" Shortcut

1. **Open Shortcuts app** on iOS
2. **Create New Shortcut**
3. **Add Actions**:

   1. **Share Input** (or get text from input)
   2. **Get URL from Input** (extract URLs if present)
   3. **Send Email**:
      - To: `khamel83+atlas@gmail.com`
      - Subject: `Atlas Bookmark: [Title from URL or input]`
      - Body: `[URL]` + any additional notes

4. **Add to Share Sheet** for easy access from any app

### Alternative: Manual Email

Simply email any content to `khamel83+atlas@gmail.com` with:
- Subject: `Atlas Bookmark: [Description]`
- Body: `[URL]` + notes

## 🔧 API Endpoints

### URL Ingestion (Original v3)
```bash
# GET
curl "http://localhost:8080/ingest?url=https://example.com"

# POST
curl -X POST http://localhost:8080/ingest \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

### Gmail Webhook
```bash
# Automatically called by Gmail push notifications
curl -X POST http://localhost:8080/webhook/gmail \
  -H "Content-Type: application/json" \
  -d '{"message": {"data": "base64_encoded_data"}}'
```

### Status & Stats
```bash
curl http://localhost:8080/
curl http://localhost:8080/stats
```

## 🗄️ Database Schema

### Enhanced SQLite Database

**Tables:**
- `ingested_urls` - All URLs with source tracking
- `gmail_messages` - Gmail message metadata
- `processing_state` - Gmail watch state
- `failed_messages` - Error tracking

**Sample Queries:**
```sql
-- Get all Gmail-processed URLs
SELECT * FROM ingested_urls WHERE source = 'gmail';

-- Get recent Gmail messages
SELECT * FROM gmail_messages ORDER BY gmail_timestamp DESC LIMIT 10;

-- Get processing statistics
SELECT source, COUNT(*) FROM ingested_urls GROUP BY source;
```

## 📊 Real-time Processing

### How It Works

1. **Email Sent** → `khamel83+atlas@gmail.com`
2. **Gmail Filter** → Applies "Atlas" label
3. **Gmail Watch** → Sends push notification
4. **Atlas Webhook** → Receives notification
5. **Message Processing** → Extracts URLs/attachments
6. **Database Storage** → Stores URLs with Gmail context
7. **Sub-5 Second Latency** → From email to database

### Labels Processed

- **"Atlas"** - Manual iOS shortcut emails
- **"Newsletter"** - Existing newsletter subscriptions

## 🔍 Troubleshooting

### Gmail Authentication Issues

```bash
# Check credentials file
ls -la config/gmail_credentials.json

# Remove and re-authenticate
rm config/gmail_token.json
python3 atlas_v3_gmail.py
```

### Port Already in Use

```bash
# Change port in atlas_v3_gmail.py
# Or kill existing process
lsof -ti:8080 | xargs kill
```

### Gmail API Quota

- Standard Gmail API quota: 1 billion requests/day
- Push notifications: Unlimited within Gmail API limits
- Rate limiting handled automatically

### Database Issues

```bash
# Check database
sqlite3 data/atlas_v3_gmail.db ".schema"

# Reset database
rm data/atlas_v3_gmail.db
```

## 🚀 Production Deployment

### Security

1. **Use HTTPS** in production
2. **Secure credentials file** with proper permissions
3. **Validate webhook signatures**
4. **Monitor API usage**

### Scaling

1. **Database backup**: Regular SQLite backups
2. **Log rotation**: Configure log rotation
3. **Process monitoring**: Use systemd or similar
4. **Health checks**: Monitor /stats endpoint

## 📈 Monitoring

### Metrics Available

```json
{
  "total_urls": 1234,
  "gmail_messages": 567,
  "gmail_enabled": true
}
```

### Logging

- Console output: Real-time status
- File logs: `logs/atlas_v3_gmail.log`
- Error tracking: Failed messages table

## 🎉 Success Indicators

✅ **Gmail authenticated** - "Gmail authenticated successfully"
✅ **Server running** - "Atlas v3 + Gmail server running"
✅ **iOS shortcut working** - Email arrives with Atlas label
✅ **URLs extracted** - URLs appear in database
✅ **Real-time processing** - Sub-5 second processing time

## 📞 Support

For issues:
1. Check logs: `tail -f logs/atlas_v3_gmail.log`
2. Verify configuration: `cat config/gmail_config.json`
3. Test Gmail API: Check authentication flow
4. Database status: Check SQLite file integrity

---

**Result**: Complete Gmail integration with Atlas v3 for real-time bookmark processing from `khamel83+atlas@gmail.com` and "Newsletter" labeled emails.