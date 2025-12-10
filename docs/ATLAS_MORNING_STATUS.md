# Atlas Morning Status

**Date:** December 5, 2025
**Status:** Core infrastructure complete, ready for activation

---

## What's Done

### 1. Data Migration ✅
- **5,980 items migrated** from scattered sources to unified file-based storage
- Sources consolidated:
  - `metadata/*.json` (2,410 files)
  - `markdown/*.md` (2,415 files)
  - Legacy SQLite databases (atlas_content_before_reorg.db, atlas_unified.db, podcast_processing.db)
- **3,542 duplicates identified and skipped**
- Content breakdown:
  - Articles: 3,852
  - Podcasts: 2,034
  - Newsletters: 94

### 2. Storage System ✅
**Location:** `modules/storage/`
- `content_types.py` - ContentItem, ContentType, SourceType, ProcessingStatus
- `file_store.py` - File-based storage (source of truth)
- `index_manager.py` - SQLite index for fast queries
- `migration.py` - Legacy database migration
- `comprehensive_migration.py` - Full data consolidation

**Directory Structure:**
```
data/content/
├── article/
│   └── YYYY/MM/DD/
│       └── {content_id}/
│           ├── metadata.json
│           ├── content.md
│           └── raw/
├── podcast/
├── youtube/
├── newsletter/
├── email/
├── document/
└── note/
```

### 3. Content Pipeline ✅
**Location:** `modules/pipeline/content_pipeline.py`
- Rate-limited web fetching (2-3s delays between requests)
- HTML to markdown conversion (trafilatura + html2text)
- Content type detection from URL patterns
- Deduplication by URL hash

### 4. Inbox System ✅
**Location:** `data/inbox/`
- `urls/` - Drop text files with URLs (one per line)
- `files/` - Markdown, text, HTML files
- `audio/` - Audio files for transcription
- `pdfs/` - PDF documents

Processor: `modules/ingest/inbox_processor.py`

### 5. Gmail Ingestion ✅
**Location:** `modules/ingest/gmail_ingester.py`
- Watches labels: atlas, Atlas, Newsletter, newsletter
- Extracts and processes URLs from emails
- Rate-limited external requests
- Integrates with content pipeline

### 6. Secrets Management ✅
- SOPS-encrypted environment: `secrets.env.encrypted`
- Age key: `~/.age/key.txt`
- Config: `.sops.yaml`
- Helper: `scripts/run_with_secrets.sh`

**To edit secrets:**
```bash
sops --input-type dotenv --output-type dotenv secrets.env.encrypted
```

### 7. Systemd Units ✅
**Location:** `systemd/`
- `atlas-gmail.service` + `atlas-gmail.timer` (every 5 min)
- `atlas-inbox.service` + `atlas-inbox.timer` (every 5 min)
- `atlas-youtube.service` + `atlas-youtube.timer` (daily 2am)

**To install:**
```bash
sudo ./systemd/install.sh
```

### 8. Telegram Notifications ✅
**Location:** `modules/notifications/telegram.py`
- Error notifications for failures
- Success notifications for completions
- Warning notifications

---

## What Needs Your Action

### 1. Set Gmail App Password
The Gmail app password is a placeholder. You need to:

1. Go to https://myaccount.google.com/apppasswords
2. Generate an app password for "Mail" on "Linux Computer"
3. Edit the secrets file:
   ```bash
   cd ~/github/atlas
   sops --input-type dotenv --output-type dotenv secrets.env.encrypted
   ```
4. Replace `PLACEHOLDER_SET_REAL_PASSWORD` with the actual app password

### 2. Configure Telegram Bot (Optional)
If you want failure notifications:

1. Create a bot via @BotFather on Telegram
2. Get your chat ID by messaging @userinfobot
3. Add to secrets:
   ```
   TELEGRAM_BOT_TOKEN=your-bot-token
   TELEGRAM_CHAT_ID=your-chat-id
   ```

### 3. Install Systemd Timers
```bash
sudo ./systemd/install.sh
```

### 4. YouTube OAuth (Deferred)
This was explicitly deferred to last. When ready:

1. Go to https://console.cloud.google.com/
2. Create OAuth 2.0 credentials for YouTube Data API
3. Run the OAuth flow to get refresh token
4. Add credentials to secrets.env.encrypted

---

## Quick Commands

### Test Gmail Ingestion
```bash
./scripts/run_with_secrets.sh python -m modules.ingest.gmail_ingester --since-days 7
```

### Process Inbox
```bash
.venv/bin/python -m modules.ingest.inbox_processor
```

### Fetch a URL
```bash
.venv/bin/python -c "
from modules.pipeline import ContentPipeline
p = ContentPipeline()
p.process_url('https://example.com')
"
```

### Check Storage Stats
```bash
.venv/bin/python -c "
from modules.storage import FileStore, IndexManager
fs = FileStore('data/content')
print(fs.get_stats())
"
```

### Search Content
```bash
.venv/bin/python -c "
from modules.storage import IndexManager
idx = IndexManager('data/indexes/atlas_index.db')
results = idx.search('your search term')
for r in results[:10]:
    print(f'{r[\"title\"]} - {r[\"file_path\"]}')"
```

---

## File Tree

```
atlas/
├── modules/
│   ├── storage/
│   │   ├── content_types.py
│   │   ├── file_store.py
│   │   ├── index_manager.py
│   │   ├── migration.py
│   │   └── comprehensive_migration.py
│   ├── pipeline/
│   │   └── content_pipeline.py
│   ├── ingest/
│   │   ├── inbox_processor.py
│   │   └── gmail_ingester.py
│   └── notifications/
│       └── telegram.py
├── data/
│   ├── content/          # File storage (source of truth)
│   ├── indexes/          # SQLite index
│   └── inbox/            # Manual drop folder
├── systemd/              # Service and timer units
├── scripts/
│   ├── run_with_secrets.sh
│   └── run_with_notify.sh
├── secrets.env.encrypted # SOPS encrypted secrets
├── .sops.yaml           # SOPS configuration
└── pyproject.toml       # Python package config
```

---

## What's Not Done (Deferred)

1. **YouTube OAuth & History Import** - Deferred to last per your instructions
2. **MacWhisper NFS Integration** - Paths configured, but NFS mount not set up
3. **Full transcript processing pipeline** - Existing fetchers available in `modules/transcript_discovery/`

---

## Notes

- Rate limiting is set to 2-3 seconds between external requests
- All external fetches go through the content pipeline
- SQLite index can be rebuilt from files at any time
- 2,034 podcasts are in "pending" status (need transcription)
