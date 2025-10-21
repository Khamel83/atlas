# Gmail Integration Setup Guide

**Last Updated**: 2025-10-21
**Difficulty**: Easy (5-10 minutes)
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

## 🔐 IMAP Setup with App Password

Atlas uses IMAP (for reading emails) and SMTP (for sending emails) with Gmail app passwords. This is simpler and more reliable than OAuth.

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
# === GMAIL INTEGRATION (IMAP/SMTP) ===
GMAIL_ENABLED=true
GMAIL_EMAIL_ADDRESS=your-email@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx   # App password from Step 2

# IMAP settings (for reading emails)
GMAIL_IMAP_HOST=imap.gmail.com
GMAIL_IMAP_PORT=993
GMAIL_FOLDER=INBOX
GMAIL_LABEL="Atlas"

# SMTP settings (for sending emails, e.g., bulk URL import)
GMAIL_SMTP_HOST=smtp.gmail.com
GMAIL_SMTP_PORT=587

# Optional: Processing settings
GMAIL_CHECK_INTERVAL=900          # Check every 15 minutes
GMAIL_MARK_READ=true              # Mark as read after processing
GMAIL_ARCHIVE_PROCESSED=false     # Archive after processing
```

**Configuration Notes**:
- `GMAIL_EMAIL_ADDRESS`: Your Gmail address
- `GMAIL_APP_PASSWORD`: 16-character app password from Step 2
- `GMAIL_LABEL`: Which Gmail label to monitor (default: "Atlas")
- `GMAIL_CHECK_INTERVAL`: How often to check for new emails (in seconds)

### Step 4: Create Gmail Label

1. In Gmail, create a new label called "Atlas" (or whatever you specified in GMAIL_LABEL)
2. Apply this label to emails you want Atlas to process
3. Atlas will check this label periodically

### Step 5: Test Connection

```bash
# Test IMAP connection
python -c "
import imaplib
mail = imaplib.IMAP4_SSL('imap.gmail.com', 993)
mail.login('your-email@gmail.com', 'your-app-password')
mail.select('INBOX')
print('✅ IMAP connection successful')
mail.logout()
"

# Test SMTP connection
python -c "
import smtplib
server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
server.login('your-email@gmail.com', 'your-app-password')
print('✅ SMTP connection successful')
server.quit()
"
```

---

## 🎨 Configuration Options

### Which Labels to Monitor

```bash
# Single label
GMAIL_LABEL="Atlas"

# To monitor multiple labels, you need to run multiple instances
# or modify the code to support multiple labels
```

### How Often Does Atlas Check Gmail?

```bash
# Check Gmail every 5 minutes (300 seconds)
GMAIL_CHECK_INTERVAL=300

# Or every hour
GMAIL_CHECK_INTERVAL=3600

# Or every 15 minutes (good balance)
GMAIL_CHECK_INTERVAL=900
```

### What to Do with Processed Emails

```bash
# Mark as read after processing
GMAIL_MARK_READ=true

# Archive after processing
GMAIL_ARCHIVE_PROCESSED=true

# Delete after processing (NOT recommended)
GMAIL_DELETE_PROCESSED=false
```

---

## 🔍 Troubleshooting

### "Authentication failed"

**Problem**: Atlas can't connect to Gmail

**Solution**:
```bash
# 1. Verify you're using APP PASSWORD, not regular password
echo "Check: $GMAIL_APP_PASSWORD"

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

### Required Variables
```bash
GMAIL_ENABLED=true
GMAIL_EMAIL_ADDRESS=your-email@gmail.com
GMAIL_APP_PASSWORD=your-16-char-app-password
```

### IMAP Settings (Reading Emails)
```bash
GMAIL_IMAP_HOST=imap.gmail.com
GMAIL_IMAP_PORT=993
GMAIL_FOLDER=INBOX
GMAIL_LABEL="Atlas"
```

### SMTP Settings (Sending Emails)
```bash
GMAIL_SMTP_HOST=smtp.gmail.com
GMAIL_SMTP_PORT=587
```

### Optional Settings
```bash
GMAIL_CHECK_INTERVAL=900
GMAIL_MARK_READ=true
GMAIL_ARCHIVE_PROCESSED=false
GMAIL_BATCH_SIZE=100
```

---

## ✅ Verification Checklist

Before you're done, verify:

- [ ] App password generated at https://myaccount.google.com/apppasswords
- [ ] Environment variables set in `.env`
- [ ] IMAP enabled in Gmail settings
- [ ] "Atlas" label created in Gmail
- [ ] IMAP connection test passes
- [ ] SMTP connection test passes (if using bulk sender)
- [ ] Test email with "Atlas" label appears in Atlas

---

## 🚀 Next Steps

Once Gmail is working:

1. **Add more labels**: Create Gmail filters to auto-label newsletters, important emails, etc.
2. **Set up bulk import**: Use `scripts/atlas_bulk_sender.py` to import thousands of URLs
3. **Monitor**: Check `logs/gmail.log` periodically
4. **Optimize**: Adjust `GMAIL_CHECK_INTERVAL` based on your needs

---

## 📖 Related Documentation

- `ATLAS_USER_GUIDE.md` - How to use Atlas
- `BULK_INGESTION_PLAN.md` - Bulk URL import guide
- `.env.template` - All configuration options
- `CLAUDE.md` - Current system status

---

## 💡 Why IMAP Instead of Gmail API?

**IMAP with App Password is simpler**:
- No Google Cloud Console setup required
- No OAuth consent screen configuration
- No redirect URI management
- Works immediately with just an app password
- Same reliability and features for Atlas's use case

**Gmail API was considered but**:
- Requires Google Cloud project setup
- OAuth 2.0 flow is complex for desktop apps
- Redirect URI issues with local applications
- More overhead for no significant benefit

For Atlas's use case (reading labeled emails), IMAP is the perfect solution.

---

**Pro Tip**: Set up Gmail filters to automatically apply the "Atlas" label to specific emails (newsletters, certain senders, etc.), and Atlas will automatically process them!
