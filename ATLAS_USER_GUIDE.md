# Atlas Quick Start - Getting Content IN

**Last Updated**: 2025-10-20
**Audience**: You (Developer + User)
**Current Status**: ⚠️  System requires rebuild (see CLAUDE.md)

---

## 📍 WHERE ARE YOU NOW?

According to `CLAUDE.md`, Atlas is currently not processing new content. You have:
- ✅ **25,831 content records** in database (data/atlas.db)
- ✅ **15,977 substantial pieces** of content
- ❌ **Processing broken** - needs rebuild

**Before adding new content, you need to get Atlas running again.**

---

## 🔧 FOR DEVELOPERS: Getting Atlas Running

### Current Problem
Multiple competing processes (atlas_manager.py, systemd services) are interfering with each other.

### Quick Fix (Option A - Recommended)
```bash
# 1. Kill all competing processes
pkill -f atlas_manager
pkill -f monitoring_service
sudo systemctl stop atlas-* 2>/dev/null

# 2. Check database is intact
ls -lh data/atlas.db
# Should show your database file

# 3. Run single process WITHOUT systemd
python atlas_manager.py --no-daemon

# 4. Monitor logs
tail -f logs/atlas.log
```

### What You're Looking For
✅ **Success signs**:
- "Atlas manager started"
- "Processing content..."
- No SIGTERM messages
- Content actually gets processed

❌ **Failure signs**:
- "SIGTERM received" every 30 seconds
- Multiple atlas processes running
- Nothing happening in database

---

## 👤 FOR USERS: How to Add Content (When Working)

### 1. Gmail / Email Content 📧

**What it does**: Automatically imports newsletters, important emails, and labeled messages.

**How to add**:
1. **Label emails** in Gmail with labels you're watching (default: "Atlas", "Newsletter")
2. **That's it!** Atlas checks Gmail every X minutes (configured)
3. **Emails appear** as markdown files in your vault

**Manual trigger**:
```bash
# Force immediate Gmail sync
python -m atlas.ingest.gmail --force
```

### 2. RSS Feeds (Podcasts, Blogs) 📻

**What it does**: Monitors RSS feeds and downloads podcast transcripts or article content.

**How to add**:
```bash
# Add RSS feed to config
echo "https://example.com/podcast/feed.xml" >> config/rss_feeds.txt

# Or edit the config file
nano config/podcasts_full.csv
```

**Feeds are checked**: Every 4 hours automatically

### 3. YouTube Videos 📺

**What it does**: Downloads transcripts and metadata from YouTube videos.

**How to add**:
```bash
# Add YouTube URL
echo "https://www.youtube.com/watch?v=VIDEO_ID" >> inputs/youtube.txt

# Multiple at once
cat << EOF >> inputs/youtube.txt
https://www.youtube.com/watch?v=VIDEO_ID_1
https://www.youtube.com/watch?v=VIDEO_ID_2
EOF
```

**Videos are processed**: Daily at 3 AM automatically

### 4. Web Articles 📰

**What it does**: Downloads and extracts article content from URLs.

**How to add**:
```bash
# Add article URL
echo "https://example.com/article" >> inputs/articles.txt

# Or use the API (if running)
curl -X POST http://localhost:7444/api/ingest/article \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/article"}'
```

**Articles are processed**: Every 30 minutes automatically

### 5. Documents (PDF, TXT, Markdown) 📄

**What it does**: Extracts text from uploaded documents.

**How to add**:
```bash
# Copy file to inputs directory
cp my-document.pdf inputs/

# Or move it
mv ~/Downloads/report.pdf inputs/
```

**Documents are processed**: Every 30 minutes automatically

---

## 🔍 Check If It's Working

### As a User
```bash
# Check recent content
ls -lt vault/inbox/ | head -20

# Check database
sqlite3 data/atlas.db "SELECT COUNT(*) FROM content;"

# View processing logs
tail -f logs/processing.log
```

### As a Developer
```bash
# Check service status
python atlas_status.py --detailed

# Monitor processing
watch -n 5 "sqlite3 data/atlas.db 'SELECT COUNT(*) FROM content;'"

# Check for errors
tail -f logs/errors.log
```

---

## 🎯 Quick Workflow Example

**Scenario**: I want Atlas to process my "AI News" Gmail label

```bash
# 1. Make sure Gmail is configured (see GMAIL_SETUP_GUIDE.md)
# 2. Label emails in Gmail with "AI News"
# 3. Add label to watch list in .env:
nano .env
# Add: GMAIL_WATCH_LABELS=["Atlas", "Newsletter", "AI News"]

# 4. Restart Atlas (or wait for next check)
pkill -f atlas_manager && python atlas_manager.py

# 5. Check results
ls -lt vault/inbox/emails/
```

---

## ⚠️  IMPORTANT NOTES

### Current System State
- **Atlas is not running automatically** (based on CLAUDE.md)
- **You need to start it manually** or fix the systemd services
- **Database is intact** - your 25K+ records are safe

### Before You Start Adding Content
1. ✅ Verify Atlas is actually running
2. ✅ Check logs show processing activity
3. ✅ Test with ONE URL/email first
4. ✅ Confirm it appears in database/vault
5. ✅ THEN add more content

### If Nothing Happens
- Check `logs/atlas.log` for errors
- Verify `.env` configuration is correct
- Ensure only ONE atlas process is running: `ps aux | grep atlas`
- Check disk space: `df -h`

---

## 📖 Next Steps

1. **Read GMAIL_SETUP_GUIDE.md** - Set up Gmail integration properly
2. **Fix the system** - Follow CLAUDE.md rebuild instructions
3. **Test with one item** - Add single URL/email and verify
4. **Bulk add** - Once working, add all your sources

---

## 🆘 Quick Troubleshooting

### "I added content but nothing happened"
```bash
# Check if Atlas is running
ps aux | grep atlas_manager

# Force manual processing
python atlas_manager.py --process-now 2>/dev/null || python run.py --all

# Check logs
tail -n 50 logs/processing.log
```

### "Content appears but isn't searchable"
```bash
# Rebuild search index
python scripts/populate_enhanced_search.py 2>/dev/null || echo "Script not found"

# Test search
curl "http://localhost:7444/api/search?q=test"
```

### "Too much content, system is slow"
```bash
# Reduce concurrent processing in .env
nano .env
# Set:
# MAX_CONCURRENT_ARTICLES=2
# MAX_CONCURRENT_PODCASTS=1

# Restart Atlas
pkill -f atlas_manager && python atlas_manager.py
```

---

**Remember**: You're both developer and user. Start with getting it working (developer hat), then use it seamlessly (user hat).

**See also**:
- `GMAIL_SETUP_GUIDE.md` - Detailed Gmail configuration
- `CLAUDE.md` - Current system status and rebuild options
- `.env.template` - All configuration options
