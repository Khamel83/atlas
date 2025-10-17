# Atlas API Documentation

## Overview

The Atlas API provides a unified interface for all cognitive amplification features, content management, and system analytics. It combines both new FastAPI-based endpoints and existing Flask-based services.

## API Structure

### New FastAPI Endpoints

1. **Authentication API** (`/api/v1/auth/*`)
   - User registration and login
   - API key management
   - JWT token authentication

2. **Content Management API** (`/api/v1/content/*`)
   - List, create, update, and delete content items
   - Content processing and reprocessing
   - Content statistics and health checks

3. **Cognitive Features API** (`/api/v1/cognitive/*`)
   - Proactive content surfacing
   - Temporal relationship analysis
   - Socratic question generation
   - Spaced repetition recall
   - Pattern detection and insights

4. **Transcript Search API** (`/api/v1/transcripts/*`)
   - Advanced transcript search and discovery
   - Podcast transcript filtering and analytics
   - Speaker-based content filtering
   - Modern web interface for transcript exploration

5. **Transcription Processing API** (`/api/v1/transcriptions/*`)
   - Mac Mini transcription result submission
   - External transcription service integration
   - Transcription status tracking and management

6. **Worker Management API** (`/api/v1/worker/*`)
   - Mac Mini worker task coordination
   - Background processing queue management
   - Distributed task status monitoring

7. **Podcast Progress API** (`/api/v1/podcast-progress/*`)
   - PODEMOS processing status tracking
   - Episode processing progress monitoring
   - Feed update notifications and alerts

8. **Apple Shortcuts API** (`/api/v1/shortcuts/*`)
   - iOS/macOS shortcut integration endpoints
   - Voice capture and content submission
   - Mobile device content processing

### Existing Flask Endpoints

1. **Analytics API** (`/api/analytics/*`)
   - System metrics
   - Content processing statistics
   - User engagement analytics
   - Dashboard data

2. **Search API** (`/api/search/*`)
   - Full-text search
   - Semantic search
   - Document indexing and management

3. **Capture API** (`/api/capture/*`)
   - Content capture from Apple devices
   - Capture status tracking
   - Recent captures listing

## Authentication

Most endpoints require authentication. You can use either:

1. **JWT Tokens** (for user authentication)
2. **API Keys** (for service-to-service communication)

### Getting a JWT Token

```bash
curl -X POST "https://atlas.khamel.com/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"username": "user", "password": "password"}'
```

### Using an API Key

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
     https://atlas.khamel.com/content/items
```

## Core Endpoints

### Health Check

```bash
GET /health
```

Returns the overall health status of the API.

### Authentication

```bash
POST /auth/register
POST /auth/login
POST /auth/api-keys
GET  /auth/api-keys
DELETE /auth/api-keys/{key_id}
```

### Content Management

```bash
GET    /content/items
GET    /content/items/{content_id}
POST   /content/items
PUT    /content/items/{content_id}
DELETE /content/items/{content_id}
POST   /content/items/{content_id}/process
GET    /content/health
```

### Cognitive Features

```bash
GET  /cognitive/proactive/items
POST /cognitive/proactive/items/{content_id}/mark-surfaced
GET  /cognitive/proactive/stats

GET  /cognitive/temporal/relationships
GET  /cognitive/temporal/insights

POST /cognitive/socratic/questions
GET  /cognitive/socratic/questions/{content_id}

GET  /cognitive/recall/items
POST /cognitive/recall/items/{content_id}/mark-reviewed
GET  /cognitive/recall/analytics

GET  /cognitive/patterns/tags
GET  /cognitive/patterns/insights

GET  /cognitive/health
```

### Transcript Search API

Advanced transcript search with filtering and analytics:

```bash
GET    /api/v1/transcripts/discovery              # Interactive transcript discovery UI
POST   /api/v1/transcripts/search                 # Advanced transcript search
GET    /api/v1/transcripts/stats                  # Transcript database statistics
GET    /api/v1/transcripts/podcasts               # Available podcast list
GET    /api/v1/transcripts/speakers               # Available speakers list
```

**Example Search Request:**
```json
{
  "query": "artificial intelligence",
  "podcasts": ["The AI Podcast", "Lex Fridman"],
  "speakers": ["Lex Fridman"],
  "limit": 20,
  "offset": 0
}
```

### Transcription Processing API

Mac Mini and external transcription service integration:

```bash
POST   /api/v1/transcriptions/                    # Submit transcription results
GET    /api/v1/transcriptions/{transcription_id}  # Get transcription status
PUT    /api/v1/transcriptions/{transcription_id}  # Update transcription
DELETE /api/v1/transcriptions/{transcription_id}  # Remove transcription
```

**Example Transcription Submission:**
```json
{
  "filename": "podcast_episode_123.mp3",
  "transcript": "Welcome to the podcast...",
  "source": "mac_mini_whisper",
  "metadata": {
    "model": "base",
    "processing_time": 45.2,
    "confidence": 0.95
  }
}
```

### Worker Management API

Distributed task processing coordination:

```bash
GET    /api/v1/worker/status                      # Worker system status
POST   /api/v1/worker/tasks                       # Submit new task
GET    /api/v1/worker/tasks/{task_id}             # Get task status
PUT    /api/v1/worker/tasks/{task_id}             # Update task status
DELETE /api/v1/worker/tasks/{task_id}             # Cancel task
GET    /api/v1/worker/queue                       # View processing queue
```

### Podcast Progress API

PODEMOS processing monitoring and control:

```bash
GET    /api/v1/podcast-progress/feeds             # All monitored feeds
GET    /api/v1/podcast-progress/feeds/{feed_id}   # Specific feed status
POST   /api/v1/podcast-progress/feeds/{feed_id}/refresh  # Force feed refresh
GET    /api/v1/podcast-progress/episodes         # Recent episodes
GET    /api/v1/podcast-progress/processing       # Current processing status
GET    /api/v1/podcast-progress/stats            # Processing statistics
```

### Apple Shortcuts API

iOS/macOS integration endpoints:

```bash
POST   /api/v1/shortcuts/capture                  # Submit content from shortcuts
GET    /api/v1/shortcuts/recent                   # Recent shortcut submissions
POST   /api/v1/shortcuts/voice                    # Voice memo processing
POST   /api/v1/shortcuts/screenshot               # Screenshot OCR processing
GET    /api/v1/shortcuts/status/{submission_id}   # Submission processing status
```

**Example Shortcut Capture:**
```json
{
  "content_type": "voice_memo",
  "content": "base64_encoded_audio_data",
  "metadata": {
    "device": "iPhone",
    "location": "San Francisco, CA",
    "timestamp": "2025-09-09T10:30:00Z"
  }
}
```

## YouTube Processing API

Automated YouTube content processing:

```bash
GET    /api/v1/youtube/subscriptions              # Monitored subscriptions
POST   /api/v1/youtube/process                    # Process specific video
GET    /api/v1/youtube/processing                 # Current processing status
GET    /api/v1/youtube/quota                      # API quota usage
GET    /api/v1/youtube/videos                     # Processed videos
GET    /api/v1/youtube/stats                      # Processing statistics
```

## Mac Mini Integration API

Dedicated hardware processing coordination:

```bash
GET    /api/v1/macmini/status                     # Mac Mini connection status
POST   /api/v1/macmini/tasks                      # Submit transcription task
GET    /api/v1/macmini/tasks/{task_id}            # Task status and results
GET    /api/v1/macmini/queue                      # Processing queue status
GET    /api/v1/macmini/models                     # Available Whisper models
POST   /api/v1/macmini/test                       # Test connection
```

## Error Handling

All endpoints return consistent error responses:

```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Detailed error description",
    "details": {
      "field": "specific_field_name",
      "reason": "validation_error"
    }
  },
  "timestamp": "2025-09-09T10:30:00Z",
  "request_id": "req_123456789"
}
```

## Rate Limiting

API endpoints are rate limited to prevent abuse:

- **General Endpoints**: 1000 requests/hour per IP
- **Search Endpoints**: 200 requests/hour per IP
- **Processing Endpoints**: 50 requests/hour per IP
- **Upload Endpoints**: 20 requests/hour per IP

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1694251200
```

## Running the API

To start the unified API server:

```bash
cd /path/to/atlas
python api/unified_server.py
```

The API will be available at `https://atlas.khamel.com`.

## API Documentation

Once the server is running, you can access the interactive API documentation at:

- FastAPI Docs: `https://atlas.khamel.com/docs`
- FastAPI ReDoc: `https://atlas.khamel.com/redoc`