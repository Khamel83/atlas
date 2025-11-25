# Atlas REST API Documentation

Atlas provides a comprehensive REST API that enables integration with external systems like TrojanHorse, web applications, and automation scripts. The API exposes content management, search, and dedicated TrojanHorse integration endpoints.

## 🚀 Quick Start

### Start the API Server

```bash
# Start API server (default localhost:7444)
atlas api

# Custom configuration
atlas api --host 0.0.0.0 --port 8787

# Development with auto-reload
atlas api --reload

# Multiple workers for production
atlas api --workers 4
```

### Interactive Documentation

- **Main API Docs**: http://localhost:7444/docs
- **TrojanHorse Integration**: http://localhost:7444/trojanhorse/docs
- **OpenAPI Schema**: http://localhost:7444/openapi.json

## 📡 API Endpoints

### Base URL
```
http://localhost:7444
```

### Core Endpoints

#### Health Check
```http
GET /health
GET /api/v1/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "Atlas API",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

#### Content Search
```http
GET /api/v1/search?q=python&limit=20&skip=0&content_type=article
```

**Query Parameters:**
- `q` (string, required): Search query
- `limit` (integer, default=20): Maximum results
- `skip` (integer, default=0): Pagination offset
- `content_type` (string, optional): Filter by content type

**Response:**
```json
{
  "results": [
    {
      "id": 12345,
      "title": "Advanced Python Programming Techniques",
      "url": "https://example.com/python-advanced",
      "content_type": "article",
      "ai_summary": "Comprehensive guide covering advanced Python concepts...",
      "created_at": "2024-01-15T09:00:00.000Z",
      "relevance_score": 0.95
    }
  ],
  "total": 1,
  "took": 23
}
```

#### Content Management
```http
# Submit URL for processing
POST /api/v1/content/submit-url
Content-Type: application/json

{
  "url": "https://example.com/interesting-article"
}

# Get content by ID
GET /api/v1/content/{content_id}

# Browse content
GET /api/v1/content/html
```

### TrojanHorse Integration

#### Health Check
```http
GET /trojanhorse/health
```

**Response:**
```json
{
  "status": "ok",
  "service": "Atlas TrojanHorse Integration",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

#### Ingest Single Note
```http
POST /trojanhorse/ingest
Content-Type: application/json
X-API-Key: your-atlas-api-key (optional)
```

**Request Body:**
```json
{
  "id": "2024-01-15-143000-project-sync",
  "path": "/Users/user/WorkVault/Processed/work/meetings/2024/2024-01-15-project-sync.md",
  "title": "Project Sync Meeting",
  "source": "drafts",
  "raw_type": "meeting_transcript",
  "class_type": "work",
  "category": "meeting",
  "project": "project-x",
  "tags": ["project-x", "sync", "timeline"],
  "created_at": "2024-01-15T14:30:00.000Z",
  "updated_at": "2024-01-15T14:35:00.000Z",
  "summary": "Weekly project sync with team. Discussed timeline and blockers.",
  "body": "# Project Sync Meeting\n\n## Attendees\n- John (PM)\n- Sarah (Dev)\n\n## Discussion\nDiscussed the Q1 roadmap and timeline...",
  "frontmatter": {
    "meeting_type": "weekly_sync",
    "duration_minutes": 45,
    "priority": "high"
  }
}
```

**Response:**
```json
{
  "status": "ok",
  "message": "Note 'Project Sync Meeting' successfully ingested",
  "count": 1
}
```

#### Ingest Batch Notes
```http
POST /trojanhorse/ingest/batch
Content-Type: application/json
X-API-Key: your-atlas-api-key (optional)
```

**Request Body:**
```json
{
  "notes": [
    {
      "id": "note-1",
      "title": "Idea: Dashboard Analytics",
      "body": "Add real-time analytics dashboard...",
      "category": "idea",
      "project": "dashboard"
    },
    {
      "id": "note-2",
      "title": "Task: Fix Payment Bug",
      "body": "Critical bug in payment processing...",
      "category": "task",
      "project": "payments"
    }
  ]
}
```

**Response:**
```json
{
  "status": "ok",
  "message": "Successfully ingested 2 notes",
  "count": 2
}
```

#### TrojanHorse Statistics
```http
GET /trojanhorse/stats
X-API-Key: your-atlas-api-key (optional)
```

**Response:**
```json
{
  "trojanhorse_stats": {
    "total_notes": 1250,
    "work_notes": 890,
    "personal_notes": 360,
    "meeting_notes": 234,
    "idea_notes": 189,
    "task_notes": 145,
    "unique_projects": 12
  },
  "recent_activity": [
    {
      "title": "Project Sync Meeting",
      "created_at": "2024-01-15T14:30:00.000Z",
      "category": "meeting"
    },
    {
      "title": "New Feature Idea",
      "created_at": "2024-01-15T11:20:00.000Z",
      "category": "idea"
    }
  ],
  "project_breakdown": [
    {
      "project": "project-x",
      "count": 89
    },
    {
      "project": "dashboard",
      "count": 45
    },
    {
      "project": "payments",
      "count": 23
    }
  ]
}
```

## 🔧 Configuration

### Environment Variables

```bash
# Atlas configuration
export ATLAS_VAULT="/Users/user/.atlas"
export ATLAS_API_PORT="7444"

# API authentication (optional)
export ATLAS_API_KEY="your-secure-api-key"

# LLM configuration
export OPENAI_API_KEY="your-openai-key"
export OPENAI_MODEL="gpt-4"

# Database configuration
export ATLAS_DB_PATH="/Users/user/.atlas/atlas.db"
```

### API Server Options

| Option | Default | Description |
|--------|---------|-------------|
| `--host` | `127.0.0.1` | Host to bind server to |
| `--port` | `7444` | Port to bind server to |
| `--reload` | `false` | Enable auto-reload for development |
| `--workers` | `1` | Number of worker processes |
| `--log-level` | `info` | Logging level (critical/error/warning/info/debug) |

## 🔌 Integration Examples

### TrojanHorse Integration

The complete workflow for promoting TrojanHorse notes to Atlas:

```bash
# 1. Start Atlas API
atlas api --host 0.0.0.0 --port 8787

# 2. Configure TrojanHorse (in separate terminal)
export ATLAS_API_URL="http://localhost:8787"
export ATLAS_API_KEY="your-secure-key"

# 3. Start TrojanHorse API
th api --host 0.0.0.0 --port 8765

# 4. Promote notes from TrojanHorse to Atlas
th promote-to-atlas "note1,note2,note3" --th-url http://localhost:8765
```

### Python Client for TrojanHorse Integration

```python
import requests
import os

class AtlasClient:
    def __init__(self, base_url="http://localhost:7444", api_key=None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key or os.getenv('ATLAS_API_KEY')
        self.session = requests.Session()

        if self.api_key:
            self.session.headers.update({'X-API-Key': self.api_key})

    def health_check(self):
        """Check Atlas API health."""
        response = self.session.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()

    def trojanhorse_health(self):
        """Check TrojanHorse integration health."""
        response = self.session.get(f"{self.base_url}/trojanhorse/health")
        response.raise_for_status()
        return response.json()

    def ingest_note(self, note):
        """Ingest a single TrojanHorse note."""
        response = self.session.post(
            f"{self.base_url}/trojanhorse/ingest",
            json=note
        )
        response.raise_for_status()
        return response.json()

    def ingest_notes_batch(self, notes):
        """Ingest multiple TrojanHorse notes."""
        response = self.session.post(
            f"{self.base_url}/trojanhorse/ingest/batch",
            json={"notes": notes}
        )
        response.raise_for_status()
        return response.json()

    def get_trojanhorse_stats(self):
        """Get TrojanHorse content statistics."""
        response = self.session.get(f"{self.base_url}/trojanhorse/stats")
        response.raise_for_status()
        return response.json()

# Usage
atlas = AtlasClient()

# Check health
health = atlas.health_check()
print(f"Atlas API Status: {health['status']}")

# Ingest notes from TrojanHorse promotion
def handle_trojanhorse_promotion(notes):
    """Handle notes promoted from TrojanHorse."""
    try:
        result = atlas.ingest_notes_batch(notes)
        print(f"✅ Successfully ingested {result['count']} notes")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to ingest notes: {e}")
        return False
```

### JavaScript Integration

```javascript
class AtlasClient {
    constructor(baseUrl = 'http://localhost:7444', apiKey = null) {
        this.baseUrl = baseUrl.replace(/\/$/, '');
        this.apiKey = apiKey || process.env.ATLAS_API_KEY;
    }

    async _request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        if (this.apiKey) {
            headers['X-API-Key'] = this.apiKey;
        }

        const response = await fetch(url, {
            ...options,
            headers
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return response.json();
    }

    async healthCheck() {
        return await this._request('/health');
    }

    async trojanhorseHealth() {
        return await this._request('/trojanhorse/health');
    }

    async ingestNotes(notes) {
        return await this._request('/trojanhorse/ingest/batch', {
            method: 'POST',
            body: JSON.stringify({ notes })
        });
    }

    async getTrojanhorseStats() {
        return await this._request('/trojanhorse/stats');
    }
}

// Usage
const atlas = new AtlasClient('http://localhost:8787', 'your-api-key');

// Handle TrojanHorse promotion
async function handlePromotion(notes) {
    try {
        const result = await atlas.ingestNotes(notes);
        console.log(`✅ Ingested ${result.count} notes`);
        return result;
    } catch (error) {
        console.error('❌ Ingestion failed:', error.message);
        throw error;
    }
}
```

### Shell Script Integration

```bash
#!/bin/bash
# TrojanHorse to Atlas promotion script

ATLAS_URL="${ATLAS_API_URL:-http://localhost:7444}"
ATLAS_KEY="${ATLAS_API_KEY:-}"

# Check Atlas health
check_atlas_health() {
    echo "🔍 Checking Atlas API health..."
    if curl -s -f "$ATLAS_URL/health" > /dev/null; then
        echo "✅ Atlas API is healthy"
        return 0
    else
        echo "❌ Atlas API is not responding"
        return 1
    fi
}

# Ingest notes to Atlas
ingest_notes() {
    local notes_file="$1"

    echo "📤 Ingesting notes to Atlas..."

    local curl_cmd="curl -s -X POST $ATLAS_URL/trojanhorse/ingest/batch"
    curl_cmd="$curl_cmd -H 'Content-Type: application/json'"

    if [ -n "$ATLAS_KEY" ]; then
        curl_cmd="$curl_cmd -H 'X-API-Key: $ATLAS_KEY'"
    fi

    curl_cmd="$curl_cmd -d @$notes_file"

    local result=$(eval $curl_cmd)
    local count=$(echo "$result" | jq -r '.count // 0')

    if [ "$count" -gt 0 ]; then
        echo "✅ Successfully ingested $count notes"
        return 0
    else
        echo "❌ Failed to ingest notes"
        echo "$result" | jq -r '.message // "Unknown error"'
        return 1
    fi
}

# Get TrojanHorse statistics
get_stats() {
    echo "📊 Getting TrojanHorse statistics..."

    local curl_cmd="curl -s $ATLAS_URL/trojanhorse/stats"

    if [ -n "$ATLAS_KEY" ]; then
        curl_cmd="$curl_cmd -H 'X-API-Key: $ATLAS_KEY'"
    fi

    local result=$(eval $curl_cmd)

    echo "📈 TrojanHorse Content in Atlas:"
    echo "$result" | jq -r '
        "Total Notes: \(.trojanhorse_stats.total_notes)",
        "Work Notes: \(.trojanhorse_stats.work_notes)",
        "Personal Notes: \(.trojanhorse_stats.personal_notes)",
        "Meetings: \(.trojanhorse_stats.meeting_notes)",
        "Ideas: \(.trojanhorse_stats.idea_notes)",
        "Tasks: \(.trojanhorse_stats.task_notes)",
        "Projects: \(.trojanhorse_stats.unique_projects)"
    '
}

# Main workflow
main() {
    local notes_file="$1"

    if [ -z "$notes_file" ]; then
        echo "Usage: $0 <notes_file.json>"
        exit 1
    fi

    if ! check_atlas_health; then
        exit 1
    fi

    if ingest_notes "$notes_file"; then
        get_stats
    else
        exit 1
    fi
}

# Run main function
main "$@"
```

## 🛡️ Security & Best Practices

### API Key Authentication

```python
# Generate secure API key
import secrets
import string

def generate_api_key(length=32):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

api_key = generate_api_key()
print(f"Generated API key: {api_key}")
```

### Environment Configuration

```bash
# .env file for Atlas configuration
ATLAS_API_KEY="your-secure-api-key-here"
ATLAS_API_PORT="8787"
ATLAS_VAULT="/Users/user/.atlas"

# Set in shell
export ATLAS_API_KEY="your-secure-api-key-here"
export ATLAS_API_PORT="8787"
```

### Request Validation

```python
from pydantic import BaseModel, validator
from typing import List, Optional, Dict, Any
from datetime import datetime

class IngestNote(BaseModel):
    """Validate TrojanHorse note payload."""
    id: str
    path: str
    title: str
    body: str
    source: Optional[str] = None
    raw_type: Optional[str] = None
    class_type: Optional[str] = None
    category: Optional[str] = None
    project: Optional[str] = None
    tags: List[str] = []
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    summary: Optional[str] = None
    frontmatter: Dict[str, Any] = {}

    @validator('title')
    def validate_title(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('title cannot be empty')
        if len(v) > 500:
            raise ValueError('title too long (max 500 chars)')
        return v.strip()

    @validator('body')
    def validate_body(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('body cannot be empty')
        if len(v) > 1000000:  # 1MB limit
            raise ValueError('body too long (max 1MB)')
        return v

    @validator('tags')
    def validate_tags(cls, v):
        if len(v) > 50:
            raise ValueError('too many tags (max 50)')
        for tag in v:
            if len(tag) > 100:
                raise ValueError('tag too long (max 100 chars)')
        return v
```

### Rate Limiting Implementation

```python
from fastapi import HTTPException, Request
from fastapi.middleware import Middleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Rate limiting
limiter = Limiter(key_func=get_remote_address)

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Apply rate limiting to API endpoints
    if request.url.path.startswith("/trojanhorse/"):
        # 100 requests per minute for TrojanHorse endpoints
        try:
            await limiter.check("100/minute")
        except RateLimitExceeded:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded"
            )

    response = await call_next(request)
    return response
```

## 🔍 Monitoring & Debugging

### Health Monitoring

```bash
# Comprehensive health check
check_atlas_health() {
    echo "🔍 Checking Atlas API..."

    # Basic health
    if ! curl -s -f "$ATLAS_URL/health" > /dev/null; then
        echo "❌ Atlas API not responding"
        return 1
    fi

    # TrojanHorse integration health
    if ! curl -s -f "$ATLAS_URL/trojanhorse/health" > /dev/null; then
        echo "⚠️  TrojanHorse integration not healthy"
    fi

    # Database connectivity
    local db_check=$(curl -s "$ATLAS_URL/api/v1/health" | jq -r '.status // "error"')
    if [ "$db_check" = "healthy" ]; then
        echo "✅ Atlas API fully healthy"
        return 0
    else
        echo "❌ Atlas database issues"
        return 1
    fi
}
```

### API Usage Statistics

```python
import time
from collections import defaultdict
from datetime import datetime, timedelta

class APIMonitor:
    def __init__(self):
        self.requests = defaultdict(list)
        self.errors = defaultdict(list)

    def record_request(self, endpoint, duration, status_code):
        """Record API request metrics."""
        now = datetime.now()
        self.requests[endpoint].append({
            'timestamp': now,
            'duration': duration,
            'status_code': status_code
        })

        # Clean old data (keep last hour)
        cutoff = now - timedelta(hours=1)
        self.requests[endpoint] = [
            r for r in self.requests[endpoint]
            if r['timestamp'] > cutoff
        ]

    def get_stats(self):
        """Get API usage statistics."""
        stats = {}
        now = datetime.now()
        cutoff = now - timedelta(hours=1)

        for endpoint, requests in self.requests.items():
            recent = [r for r in requests if r['timestamp'] > cutoff]

            if recent:
                durations = [r['duration'] for r in recent]
                stats[endpoint] = {
                    'requests_per_hour': len(recent),
                    'avg_duration': sum(durations) / len(durations),
                    'max_duration': max(durations),
                    'min_duration': min(durations),
                    'error_rate': len([r for r in recent if r['status_code'] >= 400]) / len(recent)
                }

        return stats

# Usage in FastAPI middleware
@app.middleware("http")
async def monitoring_middleware(request: Request, call_next):
    start_time = time.time()

    response = await call_next(request)

    duration = time.time() - start_time
    monitor.record_request(
        str(request.url.path),
        duration,
        response.status_code
    )

    return response
```

### Log Analysis

```bash
# Monitor Atlas API logs
monitor_atlas_logs() {
    echo "📋 Atlas API Logs (last 100 lines):"
    journalctl -u atlas-api -n 100 --no-pager

    echo ""
    echo "📊 Error Analysis:"
    journalctl -u atlas-api --since "1 hour ago" | grep -i error | tail -10

    echo ""
    echo "📈 Request Analysis:"
    journalctl -u atlas-api --since "1 hour ago" | grep "POST /trojanhorse" | wc -l | xargs echo "TrojanHorse requests last hour:"
}
```

## 🚨 Troubleshooting

### Common Issues

**API won't start:**
```bash
# Check port availability
lsof -i :7444

# Check dependencies
pip list | grep -E "(fastapi|uvicorn)"

# Check configuration
atlas config --validate
```

**TrojanHorse integration fails:**
```bash
# Test connection
curl -v http://localhost:7444/trojanhorse/health

# Check API key
echo $ATLAS_API_KEY

# Test with explicit headers
curl -X POST http://localhost:7444/trojanhorse/ingest \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{"id":"test","title":"Test","body":"Test content"}'
```

**Database issues:**
```bash
# Check database
sqlite3 ~/.atlas/atlas.db "SELECT COUNT(*) FROM content;"

# Check database integrity
sqlite3 ~/.atlas/atlas.db "PRAGMA integrity_check;"

# Rebuild if needed
atlas cleanup --rebuild-index
```

**Performance issues:**
```bash
# Check resource usage
ps aux | grep atlas

# Check database size
du -sh ~/.atlas/

# Monitor response times
time curl http://localhost:7444/health
```

### Debug Mode

```bash
# Start with debug logging
ATLAS_LOG_LEVEL=debug atlas api --reload

# Enable verbose output
atlas api --log-level debug --verbose
```

### API Testing

```bash
# Health checks
curl http://localhost:7444/health
curl http://localhost:7444/trojanhorse/health

# TrojanHorse integration test
curl -X POST http://localhost:7444/trojanhorse/ingest \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $ATLAS_API_KEY" \
  -d '{
    "id": "test-note-123",
    "title": "Test Note",
    "body": "This is a test note from TrojanHorse integration test",
    "category": "test",
    "tags": ["test", "integration"]
  }'

# Batch test
curl -X POST http://localhost:7444/trojanhorse/ingest/batch \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $ATLAS_API_KEY" \
  -d '{
    "notes": [
      {"id": "test-1", "title": "Test 1", "body": "Content 1"},
      {"id": "test-2", "title": "Test 2", "body": "Content 2"}
    ]
  }'

# Statistics
curl -H "X-API-Key: $ATLAS_API_KEY" \
  http://localhost:7444/trojanhorse/stats | jq .
```

## 📚 Additional Resources

- **Main Documentation**: See `README.md`
- **Configuration**: See `.env.template`
- **Architecture**: See `docs/ARCHITECTURE.md`
- **TrojanHorse Integration**: See TrojanHorse API documentation
- **CLI Commands**: `atlas --help`

---

*For questions or issues, please refer to the main README.md or create an issue on GitHub.*