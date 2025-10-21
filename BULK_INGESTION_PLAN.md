# Bulk URL Ingestion Plan for Atlas

**Goal**: Import a backlog of URLs (hundreds/thousands) into Atlas efficiently via email

**Date**: 2025-10-21
**Status**: ✅ READY TO USE - SMTP version complete

---

## 🚀 QUICK START (TL;DR)

**You have 10,000 URLs and want to get them into Atlas?**

```bash
# 1. Create your backlog file (one URL per line)
cat > ~/backlog.txt << 'EOF'
https://example.com/article1
https://example.com/article2
...
EOF

# 2. Set up your .env with Gmail credentials (see GMAIL_SETUP_GUIDE.md)
# GMAIL_EMAIL_ADDRESS=your-email@gmail.com
# GMAIL_APP_PASSWORD=your-16-char-app-password

# 3. Run the script (automatically handles Gmail limits)
cd ~/dev/atlas
python scripts/atlas_bulk_sender.py ~/backlog.txt

# That's it! Script will:
# - Send 250 URLs per email using SMTP
# - Respect 2,000 email/day limit (free Gmail)
# - Track progress (can resume if interrupted)
# - Take ~2 days for 10,000 URLs
```

**Script location**: `scripts/atlas_bulk_sender.py` (included in repo)

**Processing**: Atlas will process URLs over hours/days/weeks - no rush!

**Note**: You'll need to manually apply the "Atlas" label to received emails, or set up a Gmail filter to do it automatically.

---

## 🔍 Key Discovery

**Atlas DOES extract URLs from email content automatically!**

Looking at `helpers/content_processor.py:121`:
```python
urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', content)
```

This means:
- ✅ You can put **multiple URLs** in a single email
- ✅ Atlas will extract **ALL URLs** from the email body
- ✅ Each URL will be processed as separate content

---

## 📊 Approach Comparison

### Option A: Email Batching (RECOMMENDED)
**Send emails with multiple URLs per email via SMTP**

**Pros**:
- ✅ Most efficient (fewer emails to send/receive)
- ✅ Uses existing Gmail infrastructure with app password
- ✅ Can include context per batch
- ✅ Easy to track progress by email
- ✅ Simple setup (no OAuth required)

**Cons**:
- ⚠️ Need to respect Gmail limits
- ⚠️ Large emails might be slow to process
- ⚠️ Need to manually label emails (or use Gmail filters)

**Limits**:
- Gmail message size: **25 MB**
- URLs in plain text: ~100 chars avg → ~250,000 URLs per email (unrealistic)
- **Recommended**: 100-500 URLs per email (sweet spot)
- SMTP rate limiting: ~2-3 emails/second recommended (self-imposed for safety)
  - **Daily limit**: 2,000 emails/day (free Gmail) or 10,000/day (Workspace)

### Option B: Single URL Per Email
**One URL per email**

**Pros**:
- ✅ Simple to implement
- ✅ Easy to track individual failures
- ✅ Can add unique context per URL

**Cons**:
- ❌ Extremely slow (1000 URLs = 1000 emails)
- ❌ Hits rate limits quickly
- ❌ Inefficient use of Gmail quota
- ❌ Clutters inbox unnecessarily

**Not recommended** for bulk import.

### Option C: Direct File Import (Alternative)
**Skip email, write directly to `inputs/articles.txt`**

**Pros**:
- ✅ Fastest method
- ✅ No email overhead
- ✅ Simple text file append

**Cons**:
- ❌ Bypasses your "email pipeline" preference
- ❌ Less flexible (no context per URL)
- ❌ Harder to track what was imported when

---

## 🎯 RECOMMENDED APPROACH: Email Batching

Send emails with **100-500 URLs per email**, using SMTP with your Gmail app password.

### Technical Architecture

```
[backlog.txt] → [Batch Script] → [SMTP] → [Your Gmail] → [Atlas Reads] → [URLs Extracted] → [Content Processed]
     ↓              (Local)        (Send)    (Label manually)  (Ingest)        (Regex)            (Vault)
  1000 URLs      Chunk 100      Send email   or use filter    Every X min   Extract all      Save content
```

### How It Works

1. **Bulk sender script** (in Atlas repo):
   ```
   ~/dev/atlas/scripts/atlas_bulk_sender.py
   ```

2. **Script reads** your backlog file:
   ```
   ~/backlog.txt
   ```

3. **Chunks URLs** into batches (250 per email)

4. **Sends emails** to yourself using SMTP:
   - Subject: "Atlas Bulk Import - Batch 1 of 10"
   - Body: List of URLs (one per line)
   - Uses app password from .env

5. **Apply "Atlas" label** (two options):
   - Manually apply label in Gmail
   - OR create Gmail filter to auto-label emails with subject "Atlas Bulk Import"

6. **Atlas reads Gmail** (your existing IMAP setup):
   - Sees emails with "Atlas" label
   - Extracts ALL URLs from email body
   - Processes each URL separately

---

## 📋 Detailed Implementation Plan

### Phase 1: Preparation (5 minutes)

**1.1. Check Your .env Configuration**
```bash
# Verify these are set in .env:
grep GMAIL_EMAIL_ADDRESS .env
grep GMAIL_APP_PASSWORD .env
```

**Required Variables**:
- `GMAIL_EMAIL_ADDRESS`: Your Gmail address
- `GMAIL_APP_PASSWORD`: 16-character app password

**If missing**: Follow `GMAIL_SETUP_GUIDE.md` to set up IMAP/SMTP with app password

### Phase 2: Script Setup (Already Done!)

**2.1. Script Location**
```bash
# Script is already included in Atlas repo
ls -l ~/dev/atlas/scripts/atlas_bulk_sender.py
```

**2.2. Script Components**

**File**: `scripts/atlas_bulk_sender.py` (included)

**Requirements**:
- Python 3.9+ (already installed)
- Built-in libraries only: `smtplib`, `email`, `json`
- No external dependencies needed!

**Core Functions**:
1. `read_urls(file_path)` - Read URLs from file
2. `chunk_urls(urls, batch_size)` - Split into batches
3. `send_email_smtp(message)` - Send one email via SMTP
4. `create_email_message(urls, batch_num, total)` - Format email
5. `track_progress(batch_num)` - Save progress
6. `main()` - Orchestrate the process

### Phase 3: Email Format Design

**Subject Line**:
```
Atlas Bulk Import - Batch {current} of {total}
```

**Email Body** (Plain Text):
```
Atlas Bulk Import - Batch 1 of 10

The following URLs are queued for processing:

https://example.com/article1
https://example.com/article2
https://example.com/article3
... (up to 100 URLs)

---
Auto-generated by atlas_bulk_sender.py
Sent: 2025-10-20 14:30:00
```

**Why This Format**:
- ✅ One URL per line (easy to parse visually)
- ✅ Clear subject for tracking
- ✅ Context for debugging
- ✅ Atlas regex will extract all URLs

### Phase 4: Gmail Filter Setup (Optional but Recommended)

**4.1. Create Gmail Filter for Auto-Labeling**

This saves you from manually labeling thousands of emails:

1. In Gmail, click the search box dropdown
2. Set filter criteria:
   - From: your-email@gmail.com
   - Subject: "Atlas Bulk Import"
3. Click "Create filter"
4. Check "Apply label: Atlas"
5. Save filter

Now all bulk import emails will automatically get the "Atlas" label!

**4.2. Test SMTP Connection**

Test sending before running full import:
```bash
# Create test file
echo "https://example.com/test" > /tmp/test_url.txt

# Run dry-run (doesn't actually send)
cd ~/dev/atlas
python scripts/atlas_bulk_sender.py /tmp/test_url.txt --dry-run

# If that works, try sending one real email
python scripts/atlas_bulk_sender.py /tmp/test_url.txt
```

### Phase 5: Execution Strategy

**5.1. Start Small**
```bash
# Test with 10 URLs first
head -10 ~/backlog/urls.txt > ~/backlog/test_10.txt
python ~/scripts/atlas_bulk_sender.py ~/backlog/test_10.txt
```

**5.2. Monitor Atlas**
```bash
# Watch Atlas process them
tail -f ~/dev/atlas/logs/atlas.log
tail -f ~/dev/atlas/logs/processing.log

# Check database
watch -n 5 "sqlite3 ~/dev/atlas/data/atlas.db 'SELECT COUNT(*) FROM content;'"
```

**5.3. Full Import**
```bash
# Once test works, run full backlog
python ~/scripts/atlas_bulk_sender.py ~/backlog/urls.txt --batch-size 100
```

---

## 🔢 Limits & Constraints

### Gmail Limits

| Limit | Value | Impact |
|-------|-------|--------|
| **Message size** | 25 MB | ~250K URLs max (unrealistic) |
| **Daily send limit** | 2,000/day (free) or 10,000/day (Workspace) | Can send all at once if < limit |
| **API quota** | 250 units/sec | ~2-3 emails/sec = 7,200/hour |
| **Burst limit** | 100 emails/batch | Use exponential backoff |

### Recommended Batch Sizes

| Backlog Size | Batch Size | # Emails | Time to Send |
|--------------|------------|----------|--------------|
| 100 URLs | 100 | 1 email | < 1 second |
| 500 URLs | 100 | 5 emails | 2-3 seconds |
| 1,000 URLs | 100 | 10 emails | 5 seconds |
| 5,000 URLs | 250 | 20 emails | 10 seconds |
| 10,000 URLs | 500 | 20 emails | 10 seconds |

**Recommended**: **100-250 URLs per email**
- Large enough to be efficient
- Small enough to process quickly
- Easy to debug if something fails

### Atlas Processing

**How fast can Atlas process?**

From `.env.template`:
```bash
MAX_CONCURRENT_ARTICLES=5  # Process 5 at once
ARTICLE_TIMEOUT=300        # 5 min per article max
```

**Calculation**:
- 5 concurrent × 1 article/min avg = **~5 articles/min** = **300 articles/hour**
- For 1,000 URLs: **~3-4 hours** to process all
- For 10,000 URLs: **~30-40 hours** (1-2 days)

**Consider**:
- Increase `MAX_CONCURRENT_ARTICLES` to 10 or 20 for faster processing
- Some articles will fail (paywalls, 404s, etc.) - that's normal

---

## 🎬 Step-by-Step Execution

### Step 1: Prepare Backlog File

```bash
# Your backlog (one URL per line)
cat > ~/backlog/urls.txt << 'EOF'
https://example.com/article1
https://example.com/article2
https://example.com/article3
...
EOF

# Check URL count
wc -l ~/backlog/urls.txt
```

### Step 2: Verify Gmail Configuration

**2a. Check .env File**
```bash
cd ~/dev/atlas
cat .env | grep GMAIL
```

**Should see**:
```
GMAIL_EMAIL_ADDRESS=your-email@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
```

**If missing**: Follow `GMAIL_SETUP_GUIDE.md` to generate app password

**2b. Test SMTP Connection**
```bash
# Quick SMTP test
python -c "
import smtplib
from os import getenv
server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
# Replace with your actual email and app password
server.login('your-email@gmail.com', 'your-app-password')
print('✅ SMTP works!')
server.quit()
"
```

### Step 3: Run Test Batch

```bash
# Create small test file
head -5 ~/backlog/urls.txt > ~/test_5_urls.txt

# Test with dry-run first (doesn't send)
cd ~/dev/atlas
python scripts/atlas_bulk_sender.py ~/test_5_urls.txt --dry-run

# If that works, send for real
python scripts/atlas_bulk_sender.py ~/test_5_urls.txt --batch-size 5

# Expected output:
# 🔌 Testing SMTP connection...
# ✅ SMTP connection successful
# 📖 Reading URLs from file...
# ✅ Read 5 URLs from file
# 📦 Split into 1 batches
# 🚀 Starting bulk send...
# 📧 Batch 1/1 (5 URLs)
# ✅ Sent successfully
```

### Step 4: Check Atlas Received It

```bash
# Check Gmail (web UI)
# Look for email with "Atlas" label

# Check Atlas logs
tail -f ~/dev/atlas/logs/gmail.log

# Should see:
# "Processing email: Atlas Bulk Import - Batch 1 of 1"
# "Extracted 5 URLs from email"
```

### Step 5: Run Full Import

```bash
# Send all 1000 URLs (batches of 250)
cd ~/dev/atlas
python scripts/atlas_bulk_sender.py ~/backlog/urls.txt --batch-size 250 --delay 0.5

# Parameters:
# --batch-size 250: 250 URLs per email (default)
# --delay 0.5: Wait 0.5 seconds between emails (default)

# Expected output:
# 🔌 Testing SMTP connection...
# ✅ SMTP connection successful
# 📖 Reading URLs from: ~/backlog/urls.txt
# ✅ Read 1000 URLs from file
# 📦 Split into 4 batches of 250 URLs each
# 🚀 Starting bulk send...
# 📧 Batch 1/4 (250 URLs)
#    ✅ Sent successfully
# 📧 Batch 2/4 (250 URLs)
#    ✅ Sent successfully
# ... (continues)
# ✅ Bulk send complete!
#    Total URLs sent: 1000
#    Total emails sent: 4
```

### Step 6: Monitor Atlas Processing

```bash
# Watch processing
tail -f ~/dev/atlas/logs/processing.log

# Watch database grow
watch -n 10 "sqlite3 ~/dev/atlas/data/atlas.db 'SELECT COUNT(*) FROM content;'"

# Should see count increase every few minutes as articles process
```

---

## 🧪 Testing Strategy

### Test 1: Single Email (5 URLs)
**Goal**: Verify email sending works
```bash
cd ~/dev/atlas
head -5 ~/backlog/urls.txt > /tmp/test_5.txt
python scripts/atlas_bulk_sender.py /tmp/test_5.txt --batch-size 5
```
**Success**: Email appears in Gmail (manually apply "Atlas" label or use filter)

### Test 2: URL Extraction (5 URLs)
**Goal**: Verify Atlas extracts URLs
```bash
# After Test 1, check logs
grep "Extracted.*URLs" ~/dev/atlas/logs/gmail.log
```
**Success**: Log shows "Extracted 5 URLs from email"

### Test 3: Processing (5 URLs)
**Goal**: Verify URLs get processed
```bash
# Wait 10-15 minutes
sqlite3 ~/dev/atlas/data/atlas.db "SELECT COUNT(*) FROM content WHERE source='gmail';"
```
**Success**: Count shows 5 new entries

### Test 4: Medium Batch (50 URLs)
**Goal**: Verify batch processing works
```bash
cd ~/dev/atlas
head -50 ~/backlog/urls.txt > /tmp/test_50.txt
python scripts/atlas_bulk_sender.py /tmp/test_50.txt --batch-size 50
```
**Success**: 1 email, Atlas extracts 50 URLs

### Test 5: Full Run (1000+ URLs)
**Goal**: Complete backlog import
```bash
cd ~/dev/atlas
python scripts/atlas_bulk_sender.py ~/backlog/urls.txt --batch-size 250
```
**Success**: All emails sent, Atlas processes over hours/days

---

## 💡 Alternative Approaches

### Alt 1: Direct File Method (Fastest)

**Skip email entirely**:
```bash
# Just append to inputs/articles.txt
cat ~/backlog/urls.txt >> ~/dev/atlas/inputs/articles.txt

# Atlas processes this file automatically every 30 min
```

**Pros**:
- ✅ Instant (no email sending)
- ✅ Simple
- ✅ No rate limits

**Cons**:
- ❌ Doesn't use your "email pipeline" preference
- ❌ Less flexible
- ❌ No batch tracking

### Alt 2: Gmail API Instead of SMTP

**Use Gmail API + OAuth credentials** (not recommended):
```python
from googleapiclient.discovery import build

# More complex than SMTP
# Requires OAuth setup
# Same limits apply
```

**When to use**: If you need additional Gmail API features beyond sending emails (e.g., auto-labeling sent emails)

### Alt 3: Third-Party Email Client

**Use Thunderbird or similar**:
- Compose email with URLs
- Send to yourself
- Apply "Atlas" label
- Atlas processes normally

**When to use**: If you prefer manual control

---

## 📊 Recommended Configuration

Based on your needs:

### For 1,000 URLs:
```bash
--batch-size 100      # 10 emails total
--delay 1             # 1 second between emails
--total-time: 12 sec  # Very fast
--processing: 3-4 hrs # Atlas processes all
```

### For 10,000 URLs:
```bash
--batch-size 250      # 40 emails total
--delay 2             # 2 seconds between emails
--total-time: 90 sec  # Still fast
--processing: 1-2 days # Atlas processes all
```

### For 100,000 URLs:
```bash
--batch-size 500      # 200 emails total
--delay 3             # 3 seconds between emails
--total-time: 10 min  # Reasonable
--processing: 2-3 weeks # Long processing time
```

---

## 🚨 Important Considerations

### 1. Gmail Daily Limit
- Free Gmail: 2,000 emails/day
- Google Workspace: 10,000 emails/day
- **Plan**: If backlog > daily limit, split across multiple days

### 2. Atlas Processing Speed
- Atlas processes ~5-10 articles/min
- **Plan**: Don't send more than Atlas can handle in reasonable time
- **Consider**: Increasing `MAX_CONCURRENT_ARTICLES` in `.env`

### 3. Failed URLs
- Some URLs will fail (404, paywall, timeout)
- **Plan**: Script tracks failures, can retry later

### 4. Deduplication
- Atlas uses SHA256 content hash
- **Good**: Won't re-process duplicates
- **Plan**: Safe to re-run script if needed

### 5. Progress Tracking
- Script saves progress after each batch
- **Plan**: Can resume if interrupted

---

## 📁 File Structure

```
Your Machine:
~/scripts/
  atlas_bulk_sender.py       # Main script (I'll provide)
  sender_config.yaml          # Configuration
  progress_tracker.json       # Auto-generated

~/backlog/
  urls.txt                    # Your full backlog
  test_10.txt                 # Test file (10 URLs)
  failed_urls.txt             # URLs that failed to send

Atlas Machine:
~/dev/atlas/
  config/gmail_credentials.json   # Already exists
  data/gmail_token.json            # Already exists
  logs/gmail.log                   # Atlas logs
  logs/processing.log              # Processing logs
  data/atlas.db                    # Database grows
```

---

## ✅ Decision Matrix

| Scenario | Recommended Approach |
|----------|---------------------|
| **< 100 URLs** | Email batching (1-2 emails) |
| **100-1,000 URLs** | Email batching (10-20 emails) |
| **1,000-10,000 URLs** | Email batching (20-100 emails) |
| **> 10,000 URLs** | Consider direct file import OR split into weekly batches |
| **Need context per URL** | Single URL per email (slow but detailed) |
| **Speed is critical** | Direct file import (skip email) |
| **Want email pipeline** | Email batching (recommended) |

---

## 🎯 FINAL RECOMMENDATION

**For your use case** (backlog import via email):

1. **Method**: Email batching via SMTP with app password
2. **Batch Size**: 250 URLs per email (default)
3. **Script Location**: `scripts/atlas_bulk_sender.py` (included in repo)
4. **Setup**: Just need .env with GMAIL_EMAIL_ADDRESS and GMAIL_APP_PASSWORD
5. **Labeling**: Use Gmail filter to auto-apply "Atlas" label to bulk import emails
6. **Processing**: Let Atlas handle it (may take hours/days for large backlogs)
7. **Monitoring**: Watch logs and database growth

**The script is ready to use!** Just follow the steps above.

---

## 🤔 Quick Start Checklist

Before running the bulk sender:

- [ ] **App password generated** at https://myaccount.google.com/apppasswords
- [ ] **.env configured** with GMAIL_EMAIL_ADDRESS and GMAIL_APP_PASSWORD
- [ ] **Gmail filter created** to auto-label "Atlas Bulk Import" emails
- [ ] **Backlog file created** with one URL per line
- [ ] **Test run completed** with 5 URLs to verify everything works
- [ ] **Atlas is running** and processing emails with "Atlas" label

**Then just run**: `python scripts/atlas_bulk_sender.py ~/backlog.txt`

---

**Happy bulk importing! 🚀**
