# Atlas-Controlled Mac Mini Worker Setup

## Overview
**Atlas decides what to send to Mac Mini** based on content type, size, and processing requirements. Mac Mini polls Atlas for jobs, executes them, and reports results back.

## Smart Dispatcher Flow
```
Content → Atlas Analysis → Smart Decision:
├─ Articles/Small content → Process on Atlas immediately
├─ Large videos/podcasts → Queue job for Mac Mini
└─ Mac Mini polls → Downloads → Transcribes → Reports back
```

**Atlas never stops working** - continues processing regardless of Mac Mini availability.

## Setup

### 1. Copy Worker Client to Mac Mini
```bash
# Copy Atlas-controlled client:
scp atlas_controlled_mac_client.py mac_mini_setup.sh user@mac-mini:~/
ssh user@mac-mini
chmod +x mac_mini_setup.sh atlas_controlled_mac_client.py
```

### 2. Install Dependencies (on Mac Mini)
```bash
# Install whisper.cpp and yt-dlp
brew install whisper-cpp yt-dlp
pip3 install requests
```

### 3. Configure Atlas Connection
```bash
export ATLAS_URL=http://your-oci-ip:8000
export ATLAS_API_KEY=optional_api_key
export ATLAS_WORKER_ID=mac_mini_01
```

### 4. Start Atlas Worker
```bash
python3 atlas_controlled_mac_client.py
```

## How It Works

### Atlas Smart Decisions
Atlas analyzes incoming content and makes intelligent dispatch decisions:

```python
# YouTube video 30min → Queue for Mac Mini (save OCI storage)
# Podcast 5min → Process locally on Atlas (quick)
# Article → Process immediately on Atlas (text content)
# Audio file upload → Queue for Mac Mini (better transcription)
```

### Mac Mini Execution
1. **Polls Atlas** every 10 seconds for jobs
2. **Downloads content** when job received
3. **Transcribes with whisper.cpp** locally
4. **Reports transcript back** to Atlas
5. **Atlas processes transcript** into knowledge base

### No Manual Work Required
- **Atlas feeds Mac Mini jobs automatically**
- **No file dropping or manual intervention**
- **Mac Mini can be offline - Atlas continues working**

## API Integration

### Worker API Endpoints
```bash
POST /api/v1/worker/register     # Mac Mini registers as worker
GET  /api/v1/worker/jobs         # Mac Mini polls for jobs
POST /api/v1/worker/results      # Mac Mini reports job results
GET  /api/v1/worker/status       # Check worker and job status
```

### Smart Dispatcher Integration
```bash
POST /api/v1/worker/jobs         # Atlas creates jobs for heavy content
GET  /api/v1/transcriptions/status    # View transcription processing stats
```

### Data Flow
1. **Content arrives at Atlas** (YouTube, podcast, article, etc.)
2. **Smart Dispatcher decides** - process locally or queue for Mac Mini
3. **If queued**: Mac Mini polls, gets job, downloads, transcribes
4. **Mac Mini reports back** - transcript text sent to Atlas
5. **Atlas processes transcript** - stores, indexes, makes searchable

**Atlas always captures metadata first - never loses information**

## Auto-Start (Optional)
```bash
# Start on Mac Mini boot
launchctl load ~/Library/LaunchAgents/com.atlas.transcription.plist
launchctl start com.atlas.transcription
```