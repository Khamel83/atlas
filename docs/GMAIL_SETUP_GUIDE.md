# Gmail Integration Setup Guide

**Last Updated**: 2025-10-20
**Difficulty**: Moderate (20-30 minutes)
**Prerequisites**: Google account, basic command line knowledge

---

## 🎯 What You'll Achieve

After this setup, Atlas will:
- ✅ Automatically check your Gmail every X minutes
- ✅ Import emails with specific labels (e.g., "Newsletter", "Atlas")
- ✅ Convert emails to markdown files in your vault
- ✅ Extract links, attachments, and key information
- ✅ Deduplicate so you never process the same email twice

---

## 📋 Overview: Two Methods

### Method A: Gmail API (Recommended)
**Pros**: More reliable, higher rate limits, better metadata
**Cons**: Requires Google Cloud setup (15 min)
**Best for**: Long-term use, multiple labels, high volume

### Method B: IMAP (Simple)
**Pros**: 5-minute setup, no Google Cloud needed
**Cons**: Slower, fewer features, less reliable
**Best for**: Quick testing, single folder

---

## 🔐 Method A: Gmail API Setup (Recommended)

### Step 1: Create Google Cloud Project (5 minutes)

1. **Go to Google Cloud Console**: https://console.cloud.google.com/

2. **Create new project**:
   - Click "Select a project" → "New Project"
   - Name: "Atlas Personal Knowledge"
   - Click "Create"

3. **Enable Gmail API**:
   - Go to "APIs & Services" → "Library"
   - Search for "Gmail API"
   - Click "Enable"

### Step 2: Create OAuth Credentials (5 minutes)

1. **Configure OAuth consent screen**:
   ```
   Go to: APIs & Services → OAuth consent screen
   User Type: External (if personal Gmail)
   App name: Atlas
   User support email: your-email@gmail.com
   Developer contact: your-email@gmail.com
   Scopes: Leave default
   Test users: Add your-email@gmail.com
   ```

2. **Create credentials**:
   ```
   Go to: APIs & Services → Credentials
   Click: "+ CREATE CREDENTIALS" → "OAuth client ID"
   Application type: Desktop app
   Name: Atlas Desktop Client
   Click: "Create"
   ```

3. **Download credentials**:
   - Click the download icon next to your new OAuth 2.0 Client ID
   - Save as `gmail_credentials.json`

### Step 3: Install Credentials in Atlas (2 minutes)

```bash
# Navigate to Atlas directory
cd /path/to/atlas

# Create config directory if it doesn't exist
mkdir -p config

# Copy your downloaded credentials
cp ~/Downloads/gmail_credentials.json config/gmail_credentials.json

# Set correct permissions
chmod 600 config/gmail_credentials.json
```

### Step 4: Configure Environment Variables

Edit your `.env` file:

```bash
nano .env
```

Add/update these lines:

```bash
# === GMAIL API INTEGRATION ===
GMAIL_ENABLED=true
GMAIL_CREDENTIALS_PATH=config/gmail_credentials.json
GMAIL_TOKEN_PATH=data/gmail_token.json
GMAIL_WATCH_LABELS=["Atlas", "Newsletter"]

# Optional: Google Cloud Pub/Sub for real-time notifications
GCP_PROJECT_ID=your-project-id
PUBSUB_TOPIC=gmail-notifications
PUBSUB_SUBSCRIPTION=gmail-push-subscription
GMAIL_WEBHOOK_SECRET=generate-random-secret-here
```

**Important Notes**:
- `GMAIL_CREDENTIALS_PATH`: Path to the credentials file you downloaded
- `GMAIL_TOKEN_PATH`: Where Atlas will store the access token (auto-generated)
- `GMAIL_WATCH_LABELS`: Which Gmail labels to monitor (JSON array format)

### Step 5: Initial Authentication (5 minutes)

**First time only**, you need to authenticate:

```bash
# Run Atlas with Gmail enabled
python atlas_manager.py

# OR if you want to test Gmail specifically:
python -c "from gmail_integration import authenticate; authenticate()"
```

**What happens**:
1. Browser opens automatically
2. Google asks you to sign in
3. Google asks permission for Atlas to read Gmail
4. Click "Allow"
5. Browser shows "Authentication successful"
6. Token saved to `data/gmail_token.json`

**⚠️  IMPORTANT**: The `gmail_token.json` file is auto-generated during this process. DO NOT create it manually!

### Step 6: Verify It Works

```bash
# Check token was created
ls -lh data/gmail_token.json
# Should show a file (~1-2 KB)

# Test Gmail connection
python -c "
from gmail_integration import list_labels
labels = list_labels()
print(f'Found {len(labels)} labels:', [l['name'] for l in labels])
"

# Should output your Gmail labels
```

---

## 🔧 Method B: IMAP Setup (Simple Alternative)

### Step 1: Enable IMAP in Gmail

1. Go to Gmail Settings → "Forwarding and POP/IMAP"
2. Enable IMAP
3. Save changes

### Step 2: Generate App Password

**Important**: You CANNOT use your regular Gmail password!

1. **Go to**: https://myaccount.google.com/apppasswords
2. **Sign in** with your Gmail account
3. **Select app**: Choose "Mail"
4. **Select device**: Choose "Other" → Type "Atlas"
5. **Generate**: Click "Generate"
6. **Copy** the 16-character password (looks like: `xxxx xxxx xxxx xxxx`)

**⚠️  Save this password immediately!** You won't see it again.

### Step 3: Configure Environment Variables

Edit your `.env` file:

```bash
nano .env
```

Add these lines:

```bash
# === EMAIL INTEGRATION (IMAP) ===
EMAIL_ENABLED=true
EMAIL_IMAP_HOST=imap.gmail.com
EMAIL_IMAP_PORT=993
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=xxxx xxxx xxxx xxxx   # App password from Step 2
EMAIL_FOLDER=Atlas                    # Which folder to monitor
```

### Step 4: Create Gmail Folder/Label

1. In Gmail, create a new label called "Atlas"
2. Apply this label to emails you want Atlas to process
3. Atlas will check this folder periodically

### Step 5: Test Connection

```bash
# Test IMAP connection
python -c "
import imaplib
mail = imaplib.IMAP4_SSL('imap.gmail.com', 993)
mail.login('your-email@gmail.com', 'your-app-password')
mail.select('Atlas')
print('✅ IMAP connection successful')
mail.logout()
"
```

---

## 🎨 Configuration Options

### How Often Does Atlas Check Gmail?

In `.env`, you can control the frequency:

```bash
# Check Gmail every 5 minutes (300 seconds)
GMAIL_CHECK_INTERVAL=300

# Or every hour
GMAIL_CHECK_INTERVAL=3600

# Or every 15 minutes (good balance)
GMAIL_CHECK_INTERVAL=900
```

### Which Labels to Monitor

**Gmail API** (Method A):
```bash
# Single label
GMAIL_WATCH_LABELS=["Atlas"]

# Multiple labels
GMAIL_WATCH_LABELS=["Atlas", "Newsletter", "AI News", "Research"]

# All labels (not recommended)
GMAIL_WATCH_LABELS=["INBOX"]
```

**IMAP** (Method B):
```bash
# One folder only
EMAIL_FOLDER=Atlas

# To monitor multiple folders, you need multiple instances
```

### What to Do with Processed Emails

```bash
# Mark as read after processing
GMAIL_MARK_READ=true

# Archive after processing
GMAIL_ARCHIVE_PROCESSED=true

# Move to specific label
GMAIL_PROCESSED_LABEL=AtlasProcessed

# Delete after processing (NOT recommended)
GMAIL_DELETE_PROCESSED=false
```

---

## 🔍 Troubleshooting

### "Token file not found"

**Problem**: Atlas can't find `data/gmail_token.json`

**Solution**:
```bash
# The token is auto-generated during first auth
# Just run Atlas and it will prompt you to authenticate
python atlas_manager.py

# Browser will open for authentication
# After you approve, token is created automatically
```

### "Authentication failed"

**Problem**: Google won't let Atlas access Gmail

**For Gmail API (Method A)**:
```bash
# 1. Check credentials file exists
ls -lh config/gmail_credentials.json

# 2. Check you added yourself as test user in Google Cloud Console
# Go to: APIs & Services → OAuth consent screen → Test users

# 3. Delete old token and re-authenticate
rm data/gmail_token.json
python atlas_manager.py
```

**For IMAP (Method B)**:
```bash
# 1. Verify you're using APP PASSWORD, not regular password
echo "Check: $EMAIL_PASSWORD"

# 2. Verify IMAP is enabled in Gmail settings
# Go to: Gmail Settings → Forwarding and POP/IMAP

# 3. Test connection manually
python -c "
import imaplib
try:
    mail = imaplib.IMAP4_SSL('imap.gmail.com', 993)
    mail.login('YOUR_EMAIL', 'YOUR_APP_PASSWORD')
    print('✅ Success')
except Exception as e:
    print(f'❌ Error: {e}')
"
```

### "No emails being processed"

```bash
# 1. Check Atlas is actually running
ps aux | grep atlas_manager

# 2. Check logs for errors
tail -f logs/gmail.log
tail -f logs/atlas.log

# 3. Manually trigger Gmail check
python -c "from gmail_integration import process_gmail; process_gmail()"

# 4. Verify labels are correct
python -c "from gmail_integration import list_labels; print(list_labels())"
```

### "Rate limit exceeded"

**Problem**: Too many API calls to Gmail

**Solution**:
```bash
# In .env, reduce check frequency
GMAIL_CHECK_INTERVAL=900  # Check every 15 min instead of 5

# Reduce batch size
GMAIL_BATCH_SIZE=50  # Process 50 emails at a time instead of 100
```

---

## 🎯 Quick Reference: Environment Variables

### Gmail API (Method A)
```bash
GMAIL_ENABLED=true
GMAIL_CREDENTIALS_PATH=config/gmail_credentials.json
GMAIL_TOKEN_PATH=data/gmail_token.json
GMAIL_WATCH_LABELS=["Atlas", "Newsletter"]
GMAIL_CHECK_INTERVAL=900
GMAIL_MARK_READ=true
GMAIL_ARCHIVE_PROCESSED=false
GMAIL_PROCESSED_LABEL=AtlasProcessed
GMAIL_BATCH_SIZE=100
```

### IMAP (Method B)
```bash
EMAIL_ENABLED=true
EMAIL_IMAP_HOST=imap.gmail.com
EMAIL_IMAP_PORT=993
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=your-app-password-here
EMAIL_FOLDER=Atlas
EMAIL_CHECK_INTERVAL=900
EMAIL_MARK_READ=true
EMAIL_SSL=true
```

---

## ✅ Verification Checklist

Before you're done, verify:

- [ ] Credentials file in place: `config/gmail_credentials.json` (Method A) or app password in `.env` (Method B)
- [ ] Token generated: `data/gmail_token.json` exists (Method A)
- [ ] Environment variables set in `.env`
- [ ] Atlas can authenticate without errors
- [ ] Test email with correct label appears in vault
- [ ] No errors in `logs/gmail.log`

---

## 🚀 Next Steps

Once Gmail is working:

1. **Add more labels**: Update `GMAIL_WATCH_LABELS` in `.env`
2. **Set up filters**: Create Gmail filters to auto-label newsletters
3. **Monitor**: Check `logs/gmail.log` periodically
4. **Optimize**: Adjust `GMAIL_CHECK_INTERVAL` based on your needs

---

## 📖 Related Documentation

- `ATLAS_USER_GUIDE.md` - How to use Atlas
- `.env.template` - All configuration options
- `CLAUDE.md` - Current system status

---

**Pro Tip**: Start with IMAP for quick testing, then migrate to Gmail API once you're happy with the setup!
