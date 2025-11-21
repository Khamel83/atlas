# Atlas Worker API Documentation

The Atlas Worker API enables distributed processing of transcription and content processing jobs across multiple machines (primarily Mac Mini workers).

## Base URL
```
https://atlas.khamel.com/api/v1/worker
```

## API Endpoints

### 1. Worker Registration
**POST** `/register`

Register a new worker with Atlas to receive jobs.

**Request Body:**
```json
{
    "worker_id": "mac_mini_01",
    "capabilities": ["transcribe_youtube", "transcribe_podcast", "transcribe_url"],
    "platform": "mac",
    "whisper_available": true,
    "ytdlp_available": true,
    "metadata": {
        "location": "office",
        "specs": "M2 Mac Mini"
    }
}
```

**Response:**
```json
{
    "success": true,
    "message": "Worker mac_mini_01 registered"
}
```

### 2. Get Jobs
**GET** `/jobs?worker_id={id}&capabilities={caps}`

Retrieve available jobs for a specific worker.

**Parameters:**
- `worker_id` (required): Unique worker identifier
- `capabilities` (optional): Comma-separated list of job types this worker can handle

**Response:**
```json
{
    "jobs": [
        {
            "id": "e54d2bbe-abec-448a-870c-5c3ee19dbce9",
            "type": "transcribe_youtube",
            "data": {
                "url": "https://youtube.com/watch?v=example",
                "title": "Example Video"
            },
            "priority": 5,
            "created_at": "2025-08-25T23:42:59.854326"
        }
    ]
}
```

**Empty Response (No Jobs):**
```json
{
    "jobs": []
}
```

### 3. Submit Job Results
**POST** `/results`

Submit completed job results back to Atlas.

**Request Body:**
```json
{
    "job_id": "e54d2bbe-abec-448a-870c-5c3ee19dbce9",
    "worker_id": "mac_mini_01",
    "status": "completed",
    "result": {
        "transcript": "Full transcript text here...",
        "filename": "example_video.txt",
        "source_url": "https://youtube.com/watch?v=example",
        "title": "Example Video",
        "length": 300
    },
    "timestamp": 1693000000.0
}
```

**Response:**
```json
{
    "success": true,
    "message": "Job result received"
}
```

### 4. Create Jobs
**POST** `/jobs`

Create a new transcription job (typically called by Atlas internally).

**Request Body:**
```json
{
    "type": "transcribe_youtube",
    "data": {
        "url": "https://youtube.com/watch?v=example",
        "title": "Example Video"
    },
    "priority": 5,
    "created_by": "atlas_system"
}
```

**Response:**
```json
{
    "success": true,
    "job_id": "new-uuid-here",
    "message": "Job created"
}
```

### 5. Worker Status
**GET** `/status`

Get overall worker system status and statistics.

**Response:**
```json
{
    "workers": {
        "active": 1,
        "total": 1,
        "recent": [
            {
                "worker_id": "mac_mini_01",
                "platform": "mac",
                "capabilities": ["transcribe_youtube", "transcribe_podcast"],
                "last_seen": "2025-08-25T23:43:11.181543"
            }
        ]
    },
    "jobs": {
        "pending": 0,
        "assigned": 3,
        "completed": 0,
        "failed": 0,
        "total": 3
    }
}
```

## Job Types

### transcribe_youtube
Transcribe YouTube videos using yt-dlp + Whisper.

**Required Data:**
- `url`: YouTube video URL
- `title`: Video title (optional)

### transcribe_podcast
Transcribe podcast episodes from RSS feeds.

**Required Data:**
- `url`: Audio file URL
- `title`: Episode title
- `show_name`: Podcast show name (optional)

### transcribe_url
Transcribe any audio/video URL.

**Required Data:**
- `url`: Media file URL
- `title`: Content title (optional)

## Job Priority Levels
- `1-3`: Low priority (bulk/batch processing)
- `4-6`: Normal priority (standard processing)
- `7-9`: High priority (user-requested content)
- `10`: Critical priority (urgent processing)

## Database Tables

### workers
- `worker_id`: Unique worker identifier
- `capabilities`: JSON array of supported job types
- `platform`: Worker platform (mac, linux, windows)
- `whisper_available`: Boolean - Whisper transcription capability
- `ytdlp_available`: Boolean - YouTube download capability
- `metadata`: JSON object with additional worker info
- `registered_at`: Worker registration timestamp
- `last_seen`: Last activity timestamp
- `status`: Worker status (active, inactive, error)

### worker_jobs
- `id`: Unique job identifier (UUID)
- `type`: Job type (transcribe_youtube, transcribe_podcast, etc.)
- `data`: JSON object with job-specific data
- `priority`: Job priority level (1-10)
- `status`: Job status (pending, assigned, completed, failed)
- `assigned_worker`: Worker ID assigned to job
- `created_at`: Job creation timestamp
- `assigned_at`: Job assignment timestamp
- `completed_at`: Job completion timestamp
- `result`: JSON object with job results

## Worker Implementation Notes

1. **Polling Interval**: Workers should poll for jobs every 30-60 seconds
2. **Capability Matching**: Jobs are assigned based on worker capabilities
3. **Heartbeat**: Workers update `last_seen` timestamp on each job request
4. **Error Handling**: Failed jobs should be reported with status "failed"
5. **Result Integration**: Successful transcripts are automatically integrated into Atlas content pipeline

## Example Worker Client (Python)

```python
import requests
import time
import json

class AtlasWorkerClient:
    def __init__(self, worker_id, capabilities, atlas_url="https://atlas.khamel.com"):
        self.worker_id = worker_id
        self.capabilities = capabilities
        self.base_url = f"{atlas_url}/api/v1/worker"

    def register(self):
        """Register this worker with Atlas"""
        response = requests.post(f"{self.base_url}/register", json={
            "worker_id": self.worker_id,
            "capabilities": self.capabilities,
            "platform": "mac",
            "whisper_available": True,
            "ytdlp_available": True
        })
        return response.json()

    def get_jobs(self):
        """Get available jobs from Atlas"""
        caps = ",".join(self.capabilities)
        response = requests.get(f"{self.base_url}/jobs", params={
            "worker_id": self.worker_id,
            "capabilities": caps
        })
        return response.json().get("jobs", [])

    def submit_result(self, job_id, status, result):
        """Submit job result back to Atlas"""
        response = requests.post(f"{self.base_url}/results", json={
            "job_id": job_id,
            "worker_id": self.worker_id,
            "status": status,
            "result": result,
            "timestamp": time.time()
        })
        return response.json()
```

## Testing Commands

```bash
# Test worker registration
curl -X POST https://atlas.khamel.com/api/v1/worker/register \
  -H "Content-Type: application/json" \
  -d '{"worker_id":"test_worker","capabilities":["transcribe_youtube"],"platform":"mac","whisper_available":true}'

# Test job creation
curl -X POST https://atlas.khamel.com/api/v1/worker/jobs \
  -H "Content-Type: application/json" \
  -d '{"type":"transcribe_youtube","data":{"url":"https://youtube.com/watch?v=test"}}'

# Test getting jobs
curl "https://atlas.khamel.com/api/v1/worker/jobs?worker_id=test_worker&capabilities=transcribe_youtube"

# Test status
curl https://atlas.khamel.com/api/v1/worker/status
```