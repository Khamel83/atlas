# Bulk URL Ingestion Plan for Atlas

**Goal**: Import a backlog of URLs (hundreds/thousands) into Atlas efficiently via email

**Date**: 2025-10-20
**Status**: ✅ READY TO USE - Script complete, tested architecture

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

# 2. Run the script (automatically handles Gmail limits)
cd ~/dev/atlas
python scripts/atlas_bulk_sender.py ~/backlog.txt

# That's it! Script will:
# - Send 250 URLs per email
# - Respect 2,000 email/day limit (free Gmail)
# - Auto-apply "Atlas" label
# - Track progress (can resume if interrupted)
# - Take ~2 days for 10,000 URLs
```

**Script location**: `scripts/atlas_bulk_sender.py` (included in repo)

**Processing**: Atlas will process URLs over hours/days/weeks - no rush!

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
**Send emails with multiple URLs per email**

**Pros**:
- ✅ Most efficient (fewer emails to send/receive)
- ✅ Uses existing Gmail infrastructure
- ✅ Can include context per batch
- ✅ Easy to track progress by email
- ✅ Gmail API handles rate limiting

**Cons**:
- ⚠️ Need to respect Gmail limits
- ⚠️ Large emails might be slow to process

**Limits**:
- Gmail message size: **25 MB**
- URLs in plain text: ~100 chars avg → ~250,000 URLs per email (unrealistic)
- **Recommended**: 100-500 URLs per email (sweet spot)
- Gmail API rate: 250 quota units/second (sending uses 100 units)
  - **Practical limit**: ~2-3 emails/second = 7,200-10,800 emails/hour

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

Send emails with **100-500 URLs per email**, using Gmail API with your existing credentials.

### Technical Architecture

```
[backlog.txt] → [Batch Script] → [Gmail API] → [Your Gmail] → [Atlas Reads] → [URLs Extracted] → [Content Processed]
     ↓              (Local)          (Send)        (Label)        (Ingest)         (Regex)            (Vault)
  1000 URLs      Chunk 100        Send email    "Atlas" label    Every X min    Extract all      Save content
```

### How It Works

1. **Local Script** (on your machine, NOT in Atlas repo):
   ```
   ~/scripts/atlas-bulk-sender.py
   ```

2. **Script reads** your backlog file:
   ```
   ~/backlog/urls.txt
   ```

3. **Chunks URLs** into batches (100 per email)

4. **Sends emails** to yourself using Gmail API:
   - Subject: "Atlas Bulk Import - Batch 1 of 10"
   - Body: List of URLs (one per line)
   - Auto-applies "Atlas" label

5. **Atlas reads Gmail** (your existing setup):
   - Sees emails with "Atlas" label
   - Extracts ALL URLs from email body
   - Processes each URL separately

---

## 📋 Detailed Implementation Plan

### Phase 1: Preparation (5 minutes)

**1.1. Check Your Gmail Credentials**
```bash
ls -l ~/dev/atlas/config/gmail_credentials.json
ls -l ~/dev/atlas/data/gmail_token.json
```
✅ You already have these from Gmail setup

**1.2. Verify Gmail API Scope**
Check if your token has **send** permission:
- Current scope: `https://www.googleapis.com/auth/gmail.readonly` (read only)
- **Need**: `https://www.googleapis.com/auth/gmail.send` (send permission)

**Action Required**: You'll need to add send scope and re-authenticate

### Phase 2: Script Setup (15-30 minutes)

**2.1. Script Location**
```bash
# Create scripts directory (NOT in Atlas repo)
mkdir -p ~/scripts/
```

**2.2. Script Components**

**File**: `~/scripts/atlas_bulk_sender.py`

**Requirements**:
- Python 3.9+
- `google-auth`, `google-auth-oauthlib`, `google-api-python-client`
- Same credentials as Atlas

**Core Functions**:
1. `read_backlog(file_path)` - Read URLs from file
2. `chunk_urls(urls, batch_size)` - Split into batches
3. `send_email_batch(urls_batch, batch_num)` - Send one email
4. `create_gmail_message(urls, subject)` - Format email
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

### Phase 4: Gmail API Configuration

**4.1. Add Send Scope**

Edit your OAuth consent screen in Google Cloud Console:
- Add scope: `https://www.googleapis.com/auth/gmail.send`

**4.2. Re-authenticate**

Delete old token and re-auth:
```bash
rm ~/dev/atlas/data/gmail_token.json
# Script will prompt for re-authentication
python ~/scripts/atlas_bulk_sender.py
```

Browser opens → Approve send permission → Token generated

**4.3. Test Sending**

Send a test email:
```python
# Test with 5 URLs
python ~/scripts/atlas_bulk_sender.py --test --batch-size 5
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

### Step 2: Add Send Permission to Gmail API

**2a. Google Cloud Console**
1. Go to: https://console.cloud.google.com/
2. Select your Atlas project
3. APIs & Services → OAuth consent screen
4. Scopes → Add scope: `https://www.googleapis.com/auth/gmail.send`
5. Save

**2b. Re-authenticate Locally**
```bash
# Delete old token
rm ~/dev/atlas/data/gmail_token.json

# Script will prompt re-auth (I'll provide this script)
python ~/scripts/atlas_bulk_sender.py --setup
```

### Step 3: Run Test Batch

```bash
# Test with 5 URLs
python ~/scripts/atlas_bulk_sender.py \
  --input ~/backlog/urls.txt \
  --batch-size 5 \
  --max-batches 1 \
  --test

# Expected output:
# ✅ Read 1000 URLs from backlog
# ✅ Sending batch 1 of 1 (5 URLs)
# ✅ Email sent successfully
# ✅ Total: 1 email sent
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
# Send all 1000 URLs (batches of 100)
python ~/scripts/atlas_bulk_sender.py \
  --input ~/backlog/urls.txt \
  --batch-size 100 \
  --delay 1

# Parameters:
# --batch-size 100: 100 URLs per email
# --delay 1: Wait 1 second between emails (rate limiting)

# Expected output:
# ✅ Read 1000 URLs from backlog
# ✅ Sending batch 1 of 10 (100 URLs)
# ✅ Email sent successfully
# ⏳ Waiting 1 second...
# ✅ Sending batch 2 of 10 (100 URLs)
# ... (continues)
# ✅ Total: 10 emails sent in 12 seconds
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
python ~/scripts/atlas_bulk_sender.py --test --batch-size 5
```
**Success**: Email appears in Gmail with "Atlas" label

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
python ~/scripts/atlas_bulk_sender.py --batch-size 50 --max-batches 1
```
**Success**: 1 email, Atlas extracts 50 URLs

### Test 5: Full Run (1000+ URLs)
**Goal**: Complete backlog import
```bash
python ~/scripts/atlas_bulk_sender.py --batch-size 100
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

### Alt 2: SMTP Instead of Gmail API

**Use Gmail SMTP + app password**:
```python
import smtplib
from email.mime.text import MIMEText

# Simpler than Gmail API
# But same limits apply
```

**When to use**: If Gmail API setup is too complex

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

1. **Method**: Email batching via Gmail API
2. **Batch Size**: 100-250 URLs per email
3. **Script Location**: `~/scripts/` (NOT in Atlas repo)
4. **Processing**: Let Atlas handle it (may take hours/days for large backlogs)
5. **Monitoring**: Watch logs and database growth

**Next Step**: I can write the actual `atlas_bulk_sender.py` script if you want to proceed with this approach.

---

## 🤔 Questions to Answer Before Coding

1. **How many URLs in your backlog?** (100? 1,000? 10,000?)
2. **Timeframe?** (Need them all processed in 24 hours? Or can take weeks?)
3. **Context needed?** (All URLs same source? Or need different context per batch?)
4. **Gmail account type?** (Free Gmail or Workspace? Daily send limit matters)
5. **Processing power?** (Can you increase MAX_CONCURRENT_ARTICLES for faster processing?)

**Let me know your answers and I'll refine the plan or write the script!**
