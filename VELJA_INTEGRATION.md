# 🔗 ATLAS v3 + VELJA INTEGRATION

**Status**: ✅ WORKING - Atlas v3 successfully ingests URLs with unique IDs

## 🎯 What Atlas v3 Does

**ONE THING PERFECTLY**: Receives any URL → Assigns unique ID → Stores in database

```
Velja → http://localhost:35555/ingest?url=<URL> → Atlas v3 → SQLite Database
```

## 🚀 Atlas v3 Server

### Start the Server
```bash
cd /home/ubuntu/dev/atlas
python3 atlas_v3.py
```

### What You'll See
```
🚀 Atlas v3 - Simple URL Ingestion
========================================
📊 Current database: 3 URLs
🌐 Server running on http://localhost:35555
📥 Ingestion endpoint: http://localhost:35555/ingest?url=<URL>
💡 Test: curl 'http://localhost:35555/ingest?url=https://example.com'
```

## 🔧 Velja Configuration

### Option 1: Browser Extension Rule (Recommended)
In Velja settings, create a rule:
- **Pattern**: `*` (all URLs)
- **Action**: Custom URL
- **URL**: `http://localhost:35555/ingest?url={url}`

### Option 2: Manual URL Testing
```bash
# Test any URL
curl 'http://localhost:35555/ingest?url=https://example.com'

# Response
{
  "status": "success",
  "unique_id": "5da72cc3-50cb-4bab-a192-378221575830",
  "url": "https://example.com",
  "message": "URL ingested successfully"
}
```

### Option 3: AppleScript Integration (TODO)
Coming soon - AppleScript that monitors clipboard/browser for URLs.

## 📊 Database Schema

**File**: `data/atlas_v3.db`

```sql
CREATE TABLE ingested_urls (
    unique_id TEXT PRIMARY KEY,     -- UUID for each URL
    url TEXT NOT NULL,              -- The actual URL
    created_at TEXT NOT NULL,       -- ISO timestamp
    source TEXT DEFAULT 'velja'     -- Always 'velja' for now
);
```

## 🔍 Checking What's Ingested

### Database Query
```bash
sqlite3 data/atlas_v3.db "SELECT * FROM ingested_urls ORDER BY created_at DESC LIMIT 10;"
```

### Status Page
Open: http://localhost:35555/

### Count URLs
```bash
sqlite3 data/atlas_v3.db "SELECT COUNT(*) FROM ingested_urls;"
```

## ✅ Verification

**Test these work**:

1. **Start Atlas v3**: `python3 atlas_v3.py`
2. **Test URL**: `curl 'http://localhost:35555/ingest?url=https://example.com'`
3. **Check database**: `sqlite3 data/atlas_v3.db "SELECT COUNT(*) FROM ingested_urls;"`
4. **Status page**: Visit `http://localhost:35555/`

**Expected Results**:
- ✅ Server starts without errors
- ✅ URLs get unique IDs (UUIDs)
- ✅ Database records are created
- ✅ Status page shows count

## 🗂️ Architecture

```
atlas_v3.py
├── AtlasV3Database       # Simple SQLite operations
├── AtlasV3Handler        # HTTP request handling
├── /ingest endpoint      # Receives URLs from Velja
└── / status page         # Shows ingestion count
```

**Key Features**:
- **Single Python file** - no complex dependencies
- **Unique ID per URL** - UUID4 for every ingestion
- **Simple HTTP API** - GET/POST to /ingest
- **SQLite database** - reliable, local storage
- **No processing** - just ingestion (step 1 only)

## 🔄 Next Steps (Not Implemented Yet)

1. **Search**: Query ingested URLs by unique ID
2. **Content Extraction**: Download and process content
3. **Classification**: Determine content type
4. **Advanced Features**: Full text search, metadata

**Philosophy**: Build each step perfectly before moving to the next.

---

**Status**: ✅ ATLAS v3 is ready for Velja integration
**Test Command**: `curl 'http://localhost:35555/ingest?url=https://example.com'`
**Database**: `data/atlas_v3.db` with unique IDs for all URLs