# 🚨 ATLAS INGESTION ARCHITECTURE

## 🎯 CRITICAL RULE: ONE FUNNEL FOR EVERYTHING

**ALL URL ingestion MUST go through the unified queue system.**
**NO EXCEPTIONS. NO SHORTCUTS. NO BYPASSES.**

## 🏗️ Architecture Overview

```
ANY URL SOURCE → helpers/unified_ingestion.py → worker_jobs table → processors
```

### Single Entry Points

**✅ ALWAYS USE THESE:**
- `submit_url(url, priority, source)` - Single URL
- `submit_urls(urls, priority, source)` - Bulk URLs
- `get_ingestion_status()` - Queue status

**❌ NEVER DO THIS:**
- Direct HTTP calls to endpoints
- Creating temp files
- Bypassing the queue
- Multiple processing paths
- Custom bulk processing

## 🔄 How It Works

1. **Any URL source** (API, CSV, manual, bookmarklet) calls unified_ingestion functions
2. **URLs are queued** in `worker_jobs` table with type='url_processing'
3. **Workers dequeue** and process URLs asynchronously
4. **All processing** goes through the same pipeline

## 📁 File Structure

```
helpers/
  unified_ingestion.py         ← MAIN INGESTION SYSTEM

api/routers/
  content.py                   ← submit-url endpoint uses unified_ingestion

api/
  main.py                      ← CSV processing uses unified_ingestion

web/
  app.py                       ← File uploads use unified_ingestion
```

## 🚨 Implementation Rules

### For Developers

1. **Import the functions:**
   ```python
   from helpers.unified_ingestion import submit_url, submit_urls
   ```

2. **Submit single URLs:**
   ```python
   job_id = submit_url(url, priority=50, source="api")
   ```

3. **Submit bulk URLs:**
   ```python
   job_ids = submit_urls(url_list, priority=60, source="csv_upload")
   ```

4. **Check queue status:**
   ```python
   from helpers.unified_ingestion import get_ingestion_status
   status = get_ingestion_status()
   ```

### For New Features

**BEFORE creating ANY new ingestion path:**

1. ✅ Import `helpers.unified_ingestion`
2. ✅ Use `submit_url()` or `submit_urls()`
3. ✅ NO custom processing
4. ✅ NO temp files
5. ✅ NO HTTP calls to submit-url

## 🔍 Current Implementations

### API Endpoint
```python
# api/routers/content.py
@router.post("/submit-url")
async def submit_url_for_processing(submission: ContentSubmission):
    from helpers.unified_ingestion import submit_url
    job_id = submit_url(submission.url, priority=50, source="api")
    return {"job_id": job_id, "status": "queued"}
```

### CSV Processing
```python
# api/main.py
async def process_urls_batch(urls):
    from helpers.unified_ingestion import submit_urls
    job_ids = submit_urls(urls, priority=60, source="csv_upload")
```

### File Uploads
```python
# web/app.py (TODO: Update file upload processing)
from helpers.unified_ingestion import submit_urls
# Extract URLs from uploaded file
job_ids = submit_urls(extracted_urls, source="file_upload")
```

## 📊 Queue Management

### Database Table: `worker_jobs`

```sql
CREATE TABLE worker_jobs (
    id TEXT PRIMARY KEY,           -- UUID
    type TEXT NOT NULL,            -- 'url_processing'
    data TEXT NOT NULL,            -- JSON: {"url": "...", "source": "..."}
    priority INTEGER DEFAULT 50,   -- Higher = processed first
    status TEXT DEFAULT 'pending', -- pending/running/completed/failed
    assigned_worker TEXT,          -- Worker ID
    created_at TEXT NOT NULL,      -- ISO timestamp
    assigned_at TEXT,              -- When worker claimed it
    completed_at TEXT,             -- When completed
    result TEXT,                   -- Processing result
    retry_count INTEGER DEFAULT 0  -- Retry attempts
);
```

### Priority Levels
- **70+**: Critical/urgent URLs
- **60**: CSV bulk uploads
- **50**: Regular API submissions
- **40**: Low priority batch processing
- **30**: Background/maintenance URLs

## 🛠️ Monitoring & Debugging

### Check Queue Status
```python
from helpers.unified_ingestion import get_ingestion_status
status = get_ingestion_status()
print(f"Pending: {status['pending']}, Processing: {status['running']}")
```

### Database Queries
```sql
-- Check queue status
SELECT status, COUNT(*) FROM worker_jobs
WHERE type = 'url_processing'
GROUP BY status;

-- Recent submissions
SELECT url, source, status, created_at
FROM worker_jobs
WHERE type = 'url_processing'
ORDER BY created_at DESC
LIMIT 10;
```

## 🚨 Emergency Procedures

### If Queue Gets Stuck
```sql
-- Reset stuck jobs (running > 1 hour)
UPDATE worker_jobs
SET status = 'pending', assigned_worker = NULL
WHERE status = 'running'
AND assigned_at < datetime('now', '-1 hour');
```

### Clear Failed Jobs
```sql
-- Remove old failed jobs
DELETE FROM worker_jobs
WHERE status = 'failed'
AND created_at < datetime('now', '-7 days');
```

## ✅ Testing Checklist

Before deploying ingestion changes:

- [ ] All URLs go through unified_ingestion functions
- [ ] No direct HTTP calls to submit-url
- [ ] No temp file creation for URL processing
- [ ] Bulk processing uses submit_urls()
- [ ] Queue status shows correct counts
- [ ] Workers can process queued jobs
- [ ] Failed jobs are retried properly

## 📚 Documentation Updates

When this architecture changes:

1. ✅ Update this file
2. ✅ Update CLAUDE.md
3. ✅ Update README.md
4. ✅ Update inline code comments
5. ✅ Notify team members

---

**Remember: ONE FUNNEL, ONE QUEUE, ONE TRUTH.**
**If you see URL processing that doesn't use unified_ingestion.py, FIX IT IMMEDIATELY.**