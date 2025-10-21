# Atlas User Guide - Adding Content to Atlas

**Last Updated**: 2025-10-21
**Audience**: Atlas users (you!)
**System Status**: ✅ Working - Ready to use

---

## 🎯 What This Guide Covers

This guide shows you **5 ways to add content to Atlas**:
1. Gmail / Email (newsletters, labeled emails)
2. RSS Feeds (podcasts, blogs)
3. YouTube Videos
4. Web Articles (URLs)
5. Documents (PDFs, text files)

Plus troubleshooting tips and verification steps.

---

## 📧 Method 1: Gmail / Email Content

**What it does**: Automatically imports newsletters, important emails, and labeled messages as markdown notes.

### Setup (One-Time)

Follow `GMAIL_SETUP_GUIDE.md` to:
1. Generate Gmail app password (5 minutes)
2. Add credentials to `.env`
3. Configure which labels to watch

### Adding Content

**Option A: Label Existing Emails**
1. Open Gmail
2. Select emails you want in Atlas
3. Apply label: "Atlas" (or your configured label)
4. Wait for next Gmail check (default: every 15 minutes)

**Option B: Auto-Label with Filters**
1. In Gmail: Settings → Filters
2. Create filter (e.g., "from:newsletter@example.com")
3. Apply label: "Atlas"
4. Future emails auto-labeled and imported

### Verify It's Working

```bash
# Check Gmail logs
tail -f logs/gmail.log

# Look for:
# "Connected to Gmail via IMAP"
# "Processing email: [subject]"
# "Extracted X URLs from email"

# Check vault
ls -lt vault/inbox/emails/ | head -10
```

---

## 📻 Method 2: RSS Feeds (Podcasts, Blogs)

**What it does**: Monitors RSS feeds and downloads podcast transcripts or article content.

### Adding a Feed

```bash
# Add RSS feed URL to config
echo "https://example.com/podcast/feed.xml" >> config/rss_feeds.txt

# Or edit directly
nano config/podcasts_full.csv
```

### How Often It Checks

- Feeds checked: Every 4 hours (default)
- Configurable in `.env`: `RSS_CHECK_INTERVAL=14400`

### Verify It's Working

```bash
# Check RSS logs
tail -f logs/rss.log

# Check database for new podcast entries
sqlite3 data/atlas.db "SELECT title FROM content WHERE source='rss' ORDER BY created_at DESC LIMIT 10;"
```

---

## 📺 Method 3: YouTube Videos

**What it does**: Downloads transcripts and metadata from YouTube videos.

### Adding Videos

```bash
# Single video
echo "https://www.youtube.com/watch?v=VIDEO_ID" >> inputs/youtube.txt

# Multiple videos
cat << EOF >> inputs/youtube.txt
https://www.youtube.com/watch?v=VIDEO_ID_1
https://www.youtube.com/watch?v=VIDEO_ID_2
https://www.youtube.com/watch?v=VIDEO_ID_3
EOF
```

### How Often It Processes

- Videos processed: Daily at 3 AM (default)
- Or manually: `python -m atlas.ingest.youtube --force`

### Verify It's Working

```bash
# Check YouTube logs
tail -f logs/youtube.log

# Check vault
ls -lt vault/inbox/youtube/ | head -10
```

---

## 📰 Method 4: Web Articles

**What it does**: Downloads and extracts article content from URLs.

### Adding Articles

```bash
# Simple method: Add to file
echo "https://example.com/article" >> inputs/articles.txt

# Multiple at once
cat << EOF >> inputs/articles.txt
https://example.com/article1
https://example.com/article2
https://example.com/article3
EOF

# Or use the API (if web interface is running)
curl -X POST http://localhost:7444/api/ingest/article \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/article"}'
```

### Bulk Import (1,000+ URLs)

For large backlogs, use the bulk sender:
```bash
# See BULK_INGESTION_PLAN.md for details
python scripts/atlas_bulk_sender.py ~/backlog.txt
```

### How Often It Processes

- Articles processed: Every 30 minutes (default)
- Configurable in `.env`: `ARTICLE_CHECK_INTERVAL=1800`

### Verify It's Working

```bash
# Check processing logs
tail -f logs/processing.log

# Check vault
ls -lt vault/inbox/articles/ | head -10

# Check database
sqlite3 data/atlas.db "SELECT COUNT(*) FROM content WHERE source='article';"
```

---

## 📄 Method 5: Documents (PDF, TXT, Markdown)

**What it does**: Extracts text from uploaded documents.

### Adding Documents

```bash
# Copy document to inputs directory
cp ~/Downloads/report.pdf inputs/

# Or move it
mv my-notes.md inputs/

# Supported formats:
# - PDF (.pdf)
# - Text (.txt)
# - Markdown (.md)
# - Word (.docx) - if configured
```

### How Often It Processes

- Documents processed: Every 30 minutes (default)
- Or manually: `python -m atlas.ingest.documents --force`

### Verify It's Working

```bash
# Check document processing logs
tail -f logs/documents.log

# Check vault
ls -lt vault/inbox/documents/ | head -10
```

---

## ✅ How to Check If Atlas Is Working

### Quick Checks

```bash
# 1. Check Atlas is running
ps aux | grep atlas_manager

# 2. Check recent activity in logs
tail -f logs/atlas.log

# 3. Check database is growing
sqlite3 data/atlas.db "SELECT COUNT(*) FROM content;"

# 4. Check vault has new files
ls -lt vault/inbox/ | head -20
```

### Detailed Monitoring

```bash
# Watch database grow in real-time
watch -n 10 "sqlite3 data/atlas.db 'SELECT COUNT(*) FROM content;'"

# Monitor processing
tail -f logs/processing.log

# Check for errors
tail -f logs/errors.log
```

---

## 🎯 Complete Workflow Example

**Scenario**: I want to import my "AI News" newsletter

### Step-by-Step

```bash
# 1. Set up Gmail (one-time, 5 minutes)
# Follow GMAIL_SETUP_GUIDE.md

# 2. Create "AI News" label in Gmail
# Done via Gmail web interface

# 3. Add label to .env watch list
nano .env
# Update line:
# GMAIL_LABEL="AI News"
# Or watch multiple labels (if supported):
# GMAIL_WATCH_LABELS=["Atlas", "Newsletter", "AI News"]

# 4. Apply label to emails
# In Gmail, select emails → Apply "AI News" label

# 5. Wait for next check (or force it)
# Atlas checks every 15 minutes by default
# Or manually: python -m atlas.ingest.gmail --force

# 6. Verify emails were imported
ls -lt vault/inbox/emails/ | grep -i "ai news"

# 7. Check database
sqlite3 data/atlas.db "SELECT title FROM content WHERE source='gmail' ORDER BY created_at DESC LIMIT 10;"
```

---

## 🆘 Troubleshooting

### "I added content but nothing happened"

**Check if Atlas is running:**
```bash
ps aux | grep atlas_manager
# Should see at least one process
```

**If not running:**
```bash
# Start Atlas
python atlas_manager.py
```

**Check logs for errors:**
```bash
tail -f logs/atlas.log
tail -f logs/processing.log
```

**Force manual processing:**
```bash
# For Gmail
python -m atlas.ingest.gmail --force

# For articles
python -m atlas.ingest.articles --force

# For YouTube
python -m atlas.ingest.youtube --force
```

---

### "Gmail emails aren't being imported"

**Check Gmail configuration:**
```bash
# Verify credentials in .env
grep GMAIL .env

# Should see:
# GMAIL_ENABLED=true
# GMAIL_EMAIL_ADDRESS=your-email@gmail.com
# GMAIL_APP_PASSWORD=your-16-char-password
# GMAIL_LABEL="Atlas"
```

**Test IMAP connection:**
```bash
python test_gmail_imap.py

# Should see:
# "✅ Connected to Gmail"
# "Found X emails with label 'Atlas'"
```

**Check Gmail logs:**
```bash
tail -f logs/gmail.log

# Look for:
# "Connected to Gmail via IMAP"
# "Processing email: [subject]"
```

**See GMAIL_SETUP_GUIDE.md** for detailed troubleshooting

---

### "Content appears but isn't in vault/searchable"

**Check processing completed:**
```bash
# Look for processed content in database
sqlite3 data/atlas.db "SELECT title, vault_path FROM content ORDER BY created_at DESC LIMIT 10;"
```

**Rebuild search index (if needed):**
```bash
python scripts/populate_enhanced_search.py
```

**Check vault permissions:**
```bash
# Ensure vault directory is writable
ls -ld vault/
ls -ld vault/inbox/
```

---

### "System is slow / too much content processing"

**Reduce concurrent processing:**
```bash
# Edit .env
nano .env

# Reduce these values:
MAX_CONCURRENT_ARTICLES=2  # Default is usually 5-10
MAX_CONCURRENT_PODCASTS=1

# Restart Atlas
pkill -f atlas_manager && python atlas_manager.py
```

**Check system resources:**
```bash
# Check disk space
df -h

# Check memory
free -h

# Check CPU
top
```

---

### "Bulk import isn't working"

**For bulk URL import via email**, see `BULK_INGESTION_PLAN.md`

**Quick test:**
```bash
# Create test file with 5 URLs
cat > /tmp/test_urls.txt << EOF
https://example.com/1
https://example.com/2
https://example.com/3
https://example.com/4
https://example.com/5
EOF

# Run bulk sender (dry-run first)
python scripts/atlas_bulk_sender.py /tmp/test_urls.txt --dry-run

# If that works, send for real
python scripts/atlas_bulk_sender.py /tmp/test_urls.txt
```

---

## 📊 Configuration Quick Reference

### Key .env Variables

```bash
# === REQUIRED ===
OPENROUTER_API_KEY=sk-or-...  # For AI processing

# === GMAIL (Optional but Recommended) ===
GMAIL_ENABLED=true
GMAIL_EMAIL_ADDRESS=your-email@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
GMAIL_LABEL="Atlas"
GMAIL_CHECK_INTERVAL=900  # 15 minutes

# === PROCESSING INTERVALS ===
ARTICLE_CHECK_INTERVAL=1800    # 30 minutes
RSS_CHECK_INTERVAL=14400       # 4 hours
YOUTUBE_CHECK_INTERVAL=86400   # Daily

# === PERFORMANCE ===
MAX_CONCURRENT_ARTICLES=5
MAX_CONCURRENT_PODCASTS=2
```

### Processing Schedules (Defaults)

| Content Type | Check Frequency | Configurable? |
|--------------|-----------------|---------------|
| Gmail        | Every 15 min    | Yes (GMAIL_CHECK_INTERVAL) |
| Articles     | Every 30 min    | Yes (ARTICLE_CHECK_INTERVAL) |
| RSS Feeds    | Every 4 hours   | Yes (RSS_CHECK_INTERVAL) |
| YouTube      | Daily at 3 AM   | Yes (YOUTUBE_CHECK_INTERVAL) |
| Documents    | Every 30 min    | Yes (DOCUMENT_CHECK_INTERVAL) |

---

## 📖 Next Steps

Now that you know how to add content:

1. **Set up Gmail** (recommended): Follow `GMAIL_SETUP_GUIDE.md`
2. **Add your first content**: Try one method above
3. **Verify it works**: Check logs and vault
4. **Bulk import** (if needed): See `BULK_INGESTION_PLAN.md`
5. **Configure sources**: Add your RSS feeds, labels, etc.

---

## 📚 Related Documentation

- **GMAIL_SETUP_GUIDE.md** - Detailed Gmail/IMAP setup (5-10 minutes)
- **BULK_INGESTION_PLAN.md** - Import 1,000+ URLs via email
- **CLAUDE.md** - Current system status and overview
- **.env.template** - All configuration options explained

---

## ✨ Pro Tips

1. **Use Gmail filters** to auto-label incoming emails with "Atlas"
2. **Start small** - test with 1-2 items before bulk importing
3. **Monitor logs** - they tell you exactly what's happening
4. **Check database counts** - quick way to see if content is being added
5. **Bookmark this guide** - you'll reference it often at first!

---

**Questions?** Check `CLAUDE.md` for system status or troubleshooting sections above.

**Happy Atlas-ing! 🚀**
