# Gmail-Atlas Setup Checklist

## 🎯 What We're Building

**One-click iOS shortcut that emails to `khamel83+atlas@gmail.com` → Automatic Gmail labeling → Atlas processes content in 5 seconds**

---

## ✅ REQUIRED: Gmail API Setup (10 minutes)

### 1. Google Cloud Console
- [ ] Go to https://console.cloud.google.com/
- [ ] Select/create a project
- [ ] Enable Gmail API
- [ ] Enable Pub/Sub API

### 2. Create OAuth2 Credentials
- [ ] Go to "APIs & Services" → "Credentials"
- [ ] "Create Credentials" → "OAuth client ID"
- [ ] Application type: "Desktop app"
- [ ] Download JSON file
- [ ] Save as: `config/gmail_credentials.json`

### 3. GCP Pub/Sub (for real-time push notifications)
- [ ] Set project ID: `export PROJECT_ID="your-gcp-project-id"`
- [ ] Create topic: `gcloud pubsub topics create gmail-notifications --project=$PROJECT_ID`
- [ ] Create subscription:
  ```bash
  gcloud pubsub subscriptions create gmail-push-subscription \
      --topic=gmail-notifications \
      --push-endpoint=https://your-domain.com:7444/gmail/webhook \
      --project=$PROJECT_ID
  ```

---

## ✅ REQUIRED: Gmail Filter Setup (2 minutes)

### Create Gmail Filter
- [ ] Open Gmail desktop
- [ ] Settings → See all settings
- [ ] Filters and Blocked Addresses → Create new filter
- [ ] **To**: `khamel83+atlas@gmail.com`
- [ ] **Actions**: Apply label "Atlas" (create if needed)
- [ ] Check: "Mark as read" (optional)
- [ ] Save

---

## ✅ REQUIRED: Atlas Configuration (2 minutes)

### 1. Copy Configuration Template
- [ ] Copy `config/gmail_config.example.json` to `config/gmail_config.json`

### 2. Update Configuration
Edit `config/gmail_config.json`:
```json
{
  "gmail": {
    "credentials_path": "config/gmail_credentials.json",
    "token_path": "data/gmail_token.json",
    "watch_labels": ["Atlas", "Newsletter"],
    "webhook_secret": "your-webhook-secret-key-here"
  },
  "server": {
    "host": "localhost",
    "port": 7444
  }
}
```

### 3. Update .env File
Add to existing `.env`:
```env
GMAIL_ENABLED=true
GMAIL_CREDENTIALS_PATH=config/gmail_credentials.json
GMAIL_TOKEN_PATH=data/gmail_token.json
GMAIL_WATCH_LABELS=["Atlas", "Newsletter"]
GCP_PROJECT_ID=your-gcp-project-id
PUBSUB_TOPIC=gmail-notifications
PUBSUB_SUBSCRIPTION=gmail-push-subscription
GMAIL_WEBHOOK_SECRET=your-webhook-secret-key
```

---

## ✅ REQUIRED: iOS Shortcut Setup (3 minutes)

### Create "Atlas Bookmark" Shortcut
1. [ ] Open Shortcuts app
2. [ ] Tap "+" to create new shortcut
3. [ ] Tap "Share Sheet" (ensure selected)
4. [ ] Accept Content Types: Text, URLs, Images
5. [ ] Add "Send Email" action:
   - **Recipients**: `khamel83+atlas@gmail.com`
   - **Subject**: `Atlas: {ShortcutInput}`
   - **Body**: `{ShortcutInput}`
6. [ ] Name: "Atlas Bookmark"
7. [ ] Add to Share Sheet

### Optional: Multiple Shortcuts
- [ ] "Atlas with Notes" - Add prompt for additional notes
- [ ] "Save Newsletter" - For newsletter content
- [ ] "Quick Atlas" - Simple text input

---

## ✅ REQUIRED: Deploy Atlas (1 minute)

### Start Atlas API
- [ ] Run: `python api.py`
- [ ] Verify server starts: "Atlas API starting up..."
- [ ] Test basic functionality: `curl http://localhost:7444/`

---

## 🧪 TESTING CHECKLIST

### Test Gmail Authentication
- [ ] Run: `curl http://localhost:7444/gmail/auth/status`
- [ ] Should return authentication status
- [ ] If not authenticated: `curl -X POST http://localhost:7444/gmail/auth`
- [ ] Follow browser authentication flow

### Test Gmail Statistics
- [ ] Run: `curl http://localhost:7444/gmail/stats`
- [ ] Should return Gmail integration statistics

### Test iOS Shortcut
- [ ] Share a URL from Safari using "Atlas Bookmark"
- [ ] Check email arrives at `khamel83+atlas@gmail.com`
- [ ] Verify "Atlas" label is applied automatically
- [ ] Check Atlas database for new content within 5 seconds

### Test Attachment Support
- [ ] Share an image using "Atlas Bookmark"
- [ ] Verify email includes attachment
- [ ] Check Atlas processes attachment correctly

### Test Multiple URLs
- [ ] Share text with multiple URLs
- [ ] Verify all URLs are extracted and stored separately
- [ ] Check each appears as individual Atlas content records

---

## 📊 SUCCESS VERIFICATION

### ✅ Success Indicators
- [ ] Gmail credentials file exists at `config/gmail_credentials.json`
- [ ] Atlas API starts without errors
- [ ] Gmail authentication succeeds
- [ ] iOS shortcut sends emails to `khamel83+atlas@gmail.com`
- [ ] Gmail automatically applies "Atlas" label
- [ ] URLs appear in Atlas database within 5 seconds
- [ ] Attachments are downloaded and stored
- [ ] Content appears with `content_type: gmail_atlas`

### 🔍 Atlas Database Queries
Verify Gmail content in Atlas:
```sql
-- Check Gmail content count
SELECT COUNT(*) FROM content WHERE content_type = 'gmail_atlas';

-- See recent Gmail content
SELECT title, url, created_at FROM content
WHERE content_type = 'gmail_atlas'
ORDER BY created_at DESC LIMIT 10;
```

### 📱 iOS Shortcuts
- [ ] "Atlas Bookmark" appears in Share Sheet
- [ ] Works from Safari, Notes, Photos, Reddit, Twitter, etc.
- [ ] Handles URLs, text content, and images
- [ ] One-click operation from any app

---

## 🚨 TROUBLESHOOTING

### Gmail Issues
- [ ] **Authentication fails**: Delete `data/gmail_token.json` and re-authenticate
- [ ] **No push notifications**: Check Pub/Sub subscription endpoint URL
- [ ] **Labels not applied**: Manually create "Atlas" label in Gmail first

### Atlas Issues
- [ ] **API won't start**: Check Python dependencies with `pip install -r requirements.txt`
- [ ] **Gmail endpoints return errors**: Check Atlas logs for import issues
- [ ] **Content not in database**: Verify Gmail processing logs

### iOS Shortcut Issues
- [ ] **Shortcut not in Share Sheet**: Check shortcut's Content Types settings
- [ ] **Email not sending**: Verify recipient email address: `khamel83+atlas@gmail.com`
- [ ] **Attachments not included**: Check iOS app permissions for photos/files

---

## 📚 REFERENCE DOCUMENTS

### Setup Guides
- `SIMPLE_SHORTCUT_GUIDE.md` - Quick iOS shortcut setup
- `GMAIL_INTEGRATION.md` - Complete technical setup
- `IOS_SHORTCUT_SETUP.md` - Detailed iOS instructions

### Files Created
- `config/gmail_config.json` - Gmail configuration
- `modules/gmail/` - Gmail integration code
- `simple_gmail_test.py` - Test script

### API Endpoints
- `GET /gmail/auth/status` - Check authentication
- `POST /gmail/auth` - Start authentication
- `POST /gmail/webhook` - Gmail webhook (internal)
- `GET /gmail/stats` - Gmail statistics

---

## ⚡ QUICK START SUMMARY

1. **Get Gmail API credentials** → `config/gmail_credentials.json`
2. **Set Gmail filter** → `khamel83+atlas@gmail.com` → "Atlas" label
3. **Create iOS shortcut** → "Atlas Bookmark" in Share Sheet
4. **Start Atlas API** → `python api.py`
5. **Test workflow** → Share content → Check Atlas database

**Result**: One-click bookmarking that processes in under 5 seconds! 🚀