# Gmail API Setup Guide for Atlas Block 16

## Overview
This guide covers the manual steps you need to complete to enable Gmail newsletter integration in Atlas. The code will handle the technical implementation, but you need to set up Google Cloud credentials and configure your Gmail account.

---

## 🚨 MANUAL STEPS REQUIRED (Outside of Code)

### Step 1: Google Cloud Console Setup (10-15 minutes)

1. **Go to Google Cloud Console**: https://console.cloud.google.com/
2. **Create or Select Project**:
   - Create new project: "Atlas Email Integration"
   - Or use existing project if you have one
3. **Enable Gmail API**:
   - Go to APIs & Services > Library
   - Search for "Gmail API"
   - Click "Enable"
4. **Create OAuth 2.0 Credentials**:
   - Go to APIs & Services > Credentials
   - Click "Create Credentials" > "OAuth 2.0 Client IDs"
   - Choose "Desktop Application"
   - Name: "Atlas Gmail Access"
   - Download the JSON file
5. **Set up OAuth Consent Screen**:
   - Go to APIs & Services > OAuth consent screen
   - Choose "External" (unless you have Google Workspace)
   - Fill in required fields:
     - App name: "Atlas Personal Email Integration"
     - User support email: your email
     - Developer contact: your email
   - Add your email as test user in "Test users" section

### Step 2: Gmail Account Configuration (2-3 minutes)

1. **Create "Newsletter" Label**:
   - Open Gmail in your browser
   - Go to Settings (gear icon) > Labels
   - Create new label called "Newsletter" (exactly this name)
   - Or use existing label and update `GMAIL_LABEL_NAME` in .env

2. **Label Your Newsletters**:
   - Go through your existing newsletters
   - Apply "Newsletter" label to emails you want Atlas to process
   - Set up Gmail filters to auto-label future newsletters

### Step 3: File Setup in Atlas (2-3 minutes)

1. **Place Credentials File**:
   ```bash
   # Copy downloaded OAuth JSON file to Atlas
   cp ~/Downloads/credentials.json /home/ubuntu/dev/atlas/email_download_historical/
   ```

2. **Update .env Configuration** (add Gmail variable definitions):
   ```bash
   # Edit your .env file and add these Gmail variables:
   nano .env

   # Add these lines to .env:
   GMAIL_ENABLED=${GMAIL_ENABLED:-false}
   GMAIL_CREDENTIALS_PATH=${GMAIL_CREDENTIALS_PATH:-email_download_historical/credentials.json}
   GMAIL_TOKEN_PATH=${GMAIL_TOKEN_PATH:-email_download_historical/token.json}
   GMAIL_LABEL_NAME=${GMAIL_LABEL_NAME:-Newsletter}
   GMAIL_SYNC_FREQUENCY=${GMAIL_SYNC_FREQUENCY:-30}
   GMAIL_MAX_EMAILS_PER_SYNC=${GMAIL_MAX_EMAILS_PER_SYNC:-100}
   GMAIL_SAVE_FOLDER=${GMAIL_SAVE_FOLDER:-output/emails}
   GMAIL_HTML_FOLDER=${GMAIL_HTML_FOLDER:-output/emails/html}
   ```

3. **Enable Gmail in Secrets File** (when ready to activate):
   ```bash
   # Edit your secrets file
   nano ~/.secrets/atlas.env

   # Add this line to enable Gmail:
   export GMAIL_ENABLED=true

   # Optional: Override any defaults (usually not needed)
   # export GMAIL_LABEL_NAME=MyCustomLabel
   ```

---

## 🔧 CONFIGURATION OPTIONS

### Required .env Variables (Variable Definitions)
```bash
# Gmail integration toggle (references secrets file)
GMAIL_ENABLED=${GMAIL_ENABLED:-false}

# Path to Google OAuth credentials (downloaded from Cloud Console)
GMAIL_CREDENTIALS_PATH=${GMAIL_CREDENTIALS_PATH:-email_download_historical/credentials.json}

# Path where OAuth token will be stored (auto-generated)
GMAIL_TOKEN_PATH=${GMAIL_TOKEN_PATH:-email_download_historical/token.json}

# Gmail label to sync (must match exactly)
GMAIL_LABEL_NAME=${GMAIL_LABEL_NAME:-Newsletter}
```

### Required Secrets File Variables (~/.secrets/atlas.env)
```bash
# Enable Gmail integration (set to true when ready)
export GMAIL_ENABLED=true

# Optional: Override defaults if needed
# export GMAIL_LABEL_NAME=MyCustomLabel
```

### Optional .env Variables (Usually defaults are fine)
```bash
# How often to sync emails (minutes) - defaults to 30
GMAIL_SYNC_FREQUENCY=${GMAIL_SYNC_FREQUENCY:-30}

# Maximum emails to download per sync - defaults to 100
GMAIL_MAX_EMAILS_PER_SYNC=${GMAIL_MAX_EMAILS_PER_SYNC:-100}

# Where to save downloaded emails - defaults to output/emails
GMAIL_SAVE_FOLDER=${GMAIL_SAVE_FOLDER:-output/emails}

# Where to save converted HTML files - defaults to output/emails/html
GMAIL_HTML_FOLDER=${GMAIL_HTML_FOLDER:-output/emails/html}
```

---

## 🚀 FIRST RUN AUTHENTICATION

### What Happens on First Run
1. **Atlas will open your browser automatically**
2. **Google OAuth flow will start**:
   - Login to your Google account
   - Grant Atlas permission to read Gmail
   - Atlas will show "Authentication successful"
3. **Token saved automatically** to `email_download_historical/token.json`
4. **Future runs use saved token** (no browser needed)

### If Authentication Fails
1. **Check credentials.json exists** in correct location
2. **Verify Gmail API is enabled** in Google Cloud Console
3. **Check OAuth consent screen** is configured
4. **Ensure your email is added** as test user
5. **Delete token.json** and try again for fresh authentication

---

## 🔍 TESTING YOUR SETUP

### Verify Gmail Integration
```bash
# Test Gmail authentication
python -c "from helpers.email_auth_manager import test_gmail_auth; test_gmail_auth()"

# Test email download (downloads 5 emails max)
python -c "from helpers.email_ingestor import test_email_download; test_email_download(limit=5)"

# Check if emails were processed
ls output/emails/
ls output/emails/html/
```

### Common Issues & Solutions

**Issue**: "access_denied" error
- **Solution**: Add your email as test user in OAuth consent screen

**Issue**: "invalid_grant" error
- **Solution**: Delete token.json and re-authenticate

**Issue**: "Label 'Newsletter' not found"
- **Solution**: Create the label in Gmail or update GMAIL_LABEL_NAME in .env

**Issue**: No emails downloading
- **Solution**: Apply "Newsletter" label to some emails in Gmail first

---

## 🔐 SECURITY NOTES

### Credential Security
- **credentials.json**: Contains OAuth client info (not secret, but keep private)
- **token.json**: Contains your personal access token (keep secure)
- **Both files**: Already in .gitignore, won't be committed to Git
- **Permissions**: Atlas only requests read-only Gmail access

### Revoke Access
If you want to revoke Atlas access to Gmail:
1. Go to https://myaccount.google.com/permissions
2. Find "Atlas Personal Email Integration"
3. Click "Remove access"
4. Delete token.json from Atlas directory

---

## 📊 WHAT TO EXPECT AFTER SETUP

### Automatic Processing
- **Every 30 minutes**: Atlas checks for new newsletters
- **Downloads new emails**: Only emails you haven't processed
- **Converts to HTML**: For Atlas content processing
- **Indexes content**: Searchable through Atlas search
- **Background processing**: No manual intervention needed

### Monitoring
- **Atlas dashboard**: Shows email sync status
- **Logs**: Email processing tracked in atlas logs
- **Status command**: `python atlas_status.py` includes email stats

---

## 🎯 SUMMARY CHECKLIST

### Before Running Block 16 Implementation:
- [ ] Google Cloud project created with Gmail API enabled
- [ ] OAuth 2.0 credentials downloaded as credentials.json
- [ ] OAuth consent screen configured with your email as test user
- [ ] "Newsletter" label created in Gmail
- [ ] Some newsletters tagged with "Newsletter" label
- [ ] credentials.json placed in email_download_historical/ folder
- [ ] Gmail variables added to .env file (variable definitions)
- [ ] GMAIL_ENABLED=true set in ~/.secrets/atlas.env (when ready to enable)

### After Block 16 Implementation:
- [ ] Run first authentication test (browser will open)
- [ ] Verify token.json was created successfully
- [ ] Test email download with small batch
- [ ] Check Atlas background service includes email sync
- [ ] Verify emails appear in Atlas search results

This setup enables Atlas to seamlessly integrate your newsletter content into your personal knowledge management system!