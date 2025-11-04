# Atlas + RelayQ Integration Design

**Date**: 2025-11-04
**Purpose**: Design hybrid architecture - Atlas (OCI VM) + RelayQ (Physical Machines)
**Goal**: Use RelayQ as-is for compute-intensive tasks that benefit from physical hardware

---

## Executive Summary

**Architecture**: Atlas runs lightweight coordination on OCI VM, offloads heavy compute to physical machines via RelayQ.

**Key Insight**: RelayQ is **already perfect for this** - uses GitHub Actions as queue, no Redis needed, zero inbound ports.

**Integration Approach**: ✅ **Use RelayQ as-is** - Just add Atlas-specific workflows and job submission logic.

---

## RelayQ Quick Refresher

### What It Does
```
Atlas (OCI VM) ──submits job──> GitHub Actions (queue)
                                      │
                                      │ (polling, no inbound ports)
                                      ▼
                          Mac mini / RPi4 / RPi3
                              (self-hosted runners)
                                      │
                                      ▼
                                  Results stored
                                      │
                                      ▼
                          Atlas polls or receives webhook
```

### Key Features
- ✅ **GitHub Actions as queue** - Free 2,000 minutes/month
- ✅ **Self-hosted runners** - Run on your physical machines
- ✅ **Zero inbound ports** - All outbound connections
- ✅ **Runner labels** - Route jobs to specific hardware
- ✅ **Multiple backends** - Local Whisper, OpenAI API, Router APIs
- ✅ **Job artifacts** - Results stored in GitHub (7 days retention)

### Runner Labels
| Runner | Labels | Use Cases |
|--------|--------|-----------|
| Mac mini | `self-hosted, macmini, audio, ffmpeg, heavy` | Podcast transcription, video processing |
| RPi4 | `self-hosted, rpi4, audio, light` | Light audio, text processing |
| RPi3 | `self-hosted, rpi3, overflow, verylight` | Background tasks, overflow |

---

## Atlas Tasks to Offload

### 1. Podcast Transcription (PRIMARY USE CASE) 🎙️

**Current State in Atlas**:
- Atlas discovers podcast episodes via RSS
- Needs transcripts for podcast episodes
- Currently relies on external sources or skips

**Why Offload to RelayQ**:
- ✅ **Heavy compute** - Whisper models are CPU/GPU intensive
- ✅ **Long running** - 1 hour podcast = ~5-10 min transcription
- ✅ **Better on physical hardware** - Mac mini with Apple Silicon is FAST
- ✅ **Cost** - Local Whisper is free vs $0.006/min for OpenAI
- ✅ **Privacy** - Keep podcast transcripts on your hardware

**Integration Flow**:
```
Atlas (OCI VM)
    │
    ├── Discovers podcast episode via RSS
    ├── Checks: Does transcript already exist?
    ├── If NO: Submit to RelayQ
    │       │
    │       └──> gh workflow run transcribe_audio.yml url=<episode_url>
    │
    └── RelayQ processes on Mac mini
            │
            ├── Downloads podcast audio
            ├── Runs Whisper transcription
            ├── Saves transcript as artifact
            │
            └──> Atlas polls for completion
                     │
                     └──> Downloads transcript
                          │
                          └──> Saves to Atlas database
```

### 2. YouTube Video Processing 🎥

**Current State in Atlas**:
- YouTube integration exists
- Downloads videos with yt-dlp
- Extracts metadata and transcripts

**Why Offload to RelayQ**:
- ✅ **Bandwidth** - Videos are large, better on home network
- ✅ **yt-dlp compatibility** - Some formats work better on Mac
- ✅ **Storage** - Can store on local NAS before deleting
- ✅ **FFmpeg processing** - Mac has hardware acceleration

**Integration Flow**:
```
Atlas discovers YouTube video
    │
    └──> Submit to RelayQ: download + extract + transcribe
            │
            └──> Mac mini processes
                    │
                    ├── Downloads video (yt-dlp)
                    ├── Extracts audio (FFmpeg)
                    ├── Transcribes (Whisper)
                    └──> Returns metadata + transcript
```

### 3. Bulk Audio/Video Downloads 📦

**Use Case**:
- Importing large podcast backlogs
- Downloading YouTube channel archives
- Batch processing of audio files

**Why Offload**:
- ✅ **Bandwidth** - Don't saturate OCI VM bandwidth
- ✅ **Storage** - Can use local NAS
- ✅ **Parallel processing** - Mac mini can handle multiple jobs

### 4. Heavy Content Extraction 🌐

**Use Case**:
- Paywalled articles (needs Playwright/browser)
- JavaScript-heavy sites
- PDF processing with OCR

**Why Offload**:
- ✅ **Browser rendering** - Mac has better Chrome/Playwright support
- ✅ **OCR** - Tesseract runs better on physical hardware
- ✅ **Memory** - Heavy browser automation needs RAM

---

## Integration Architecture

### Design Principles

1. **✅ Use RelayQ as-is** - Don't modify RelayQ core
2. **Atlas submits jobs** - Atlas code calls `gh workflow run`
3. **RelayQ workflows** - Add Atlas-specific workflows to RelayQ repo
4. **Polling for results** - Atlas polls GitHub artifacts API
5. **Store in Atlas** - Results go into Atlas database

### Atlas Side Changes

**New Module**: `atlas/integrations/relayq_client.py`

```python
#!/usr/bin/env python3
"""
Atlas RelayQ Client
Submits compute-intensive jobs to RelayQ for processing on physical hardware
"""

import subprocess
import os
import time
import requests
from pathlib import Path
from typing import Optional, Dict, Any

class RelayQClient:
    """Submit jobs to RelayQ and retrieve results"""

    def __init__(self):
        self.relayq_repo = os.getenv('RELAYQ_REPO', 'Khamel83/relayq')
        self.dispatch_script = os.getenv('RELAYQ_DISPATCH_SCRIPT',
                                         '/home/ubuntu/relayq/bin/dispatch.sh')
        self.github_token = os.getenv('GITHUB_TOKEN')  # For API calls

    def submit_transcription(
        self,
        audio_url: str,
        backend: str = "local",
        model: str = "base",
        runner_preference: str = "pooled"  # pooled, mac, rpi
    ) -> Dict[str, Any]:
        """
        Submit audio transcription job to RelayQ

        Args:
            audio_url: URL to audio file
            backend: ASR backend (local, openai, router)
            model: Whisper model for local backend
            runner_preference: Which runner to use (pooled, mac, rpi)

        Returns:
            Job info dict with run_url and run_id
        """
        # Select workflow based on preference
        workflows = {
            "pooled": ".github/workflows/transcribe_audio.yml",
            "mac": ".github/workflows/transcribe_mac.yml",
            "rpi": ".github/workflows/transcribe_rpi.yml"
        }
        workflow = workflows.get(runner_preference, workflows["pooled"])

        # Build dispatch command
        cmd = [
            self.dispatch_script,
            workflow,
            f"url={audio_url}",
            f"backend={backend}",
            f"model={model}"
        ]

        # Execute dispatch
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            raise Exception(f"Failed to submit job: {result.stderr}")

        # Extract run URL from output
        run_url = self._extract_run_url(result.stdout)
        run_id = self._extract_run_id(run_url)

        return {
            "run_url": run_url,
            "run_id": run_id,
            "audio_url": audio_url,
            "backend": backend,
            "status": "queued"
        }

    def check_job_status(self, run_id: str) -> Dict[str, Any]:
        """
        Check status of a RelayQ job

        Args:
            run_id: GitHub Actions run ID

        Returns:
            Status dict with completion status and artifact URL
        """
        # Use GitHub API to check run status
        url = f"https://api.github.com/repos/{self.relayq_repo}/actions/runs/{run_id}"
        headers = {
            "Authorization": f"Bearer {self.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }

        response = requests.get(url, headers=headers)
        response.raise_for_status()

        data = response.json()

        return {
            "status": data["status"],  # queued, in_progress, completed
            "conclusion": data.get("conclusion"),  # success, failure, cancelled
            "created_at": data["created_at"],
            "updated_at": data["updated_at"],
            "html_url": data["html_url"]
        }

    def get_job_artifacts(self, run_id: str) -> list:
        """
        Get artifacts from completed job

        Args:
            run_id: GitHub Actions run ID

        Returns:
            List of artifact URLs
        """
        url = f"https://api.github.com/repos/{self.relayq_repo}/actions/runs/{run_id}/artifacts"
        headers = {
            "Authorization": f"Bearer {self.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }

        response = requests.get(url, headers=headers)
        response.raise_for_status()

        data = response.json()
        return data.get("artifacts", [])

    def download_transcript(self, run_id: str, output_path: str) -> Optional[str]:
        """
        Download transcript from completed job

        Args:
            run_id: GitHub Actions run ID
            output_path: Where to save transcript

        Returns:
            Path to downloaded transcript file
        """
        # Get artifacts
        artifacts = self.get_job_artifacts(run_id)

        # Find transcript artifact
        transcript_artifact = None
        for artifact in artifacts:
            if "transcript" in artifact["name"].lower():
                transcript_artifact = artifact
                break

        if not transcript_artifact:
            return None

        # Download artifact
        download_url = transcript_artifact["archive_download_url"]
        headers = {
            "Authorization": f"Bearer {self.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }

        response = requests.get(download_url, headers=headers)
        response.raise_for_status()

        # Save artifact (it's a ZIP file)
        import zipfile
        import io

        zip_data = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_data) as zip_file:
            # Extract transcript file
            for name in zip_file.namelist():
                if name.endswith('.txt'):
                    transcript_content = zip_file.read(name).decode('utf-8')
                    with open(output_path, 'w') as f:
                        f.write(transcript_content)
                    return output_path

        return None

    def wait_for_completion(
        self,
        run_id: str,
        timeout: int = 3600,
        poll_interval: int = 30
    ) -> Dict[str, Any]:
        """
        Wait for job to complete (blocking)

        Args:
            run_id: GitHub Actions run ID
            timeout: Max seconds to wait
            poll_interval: Seconds between status checks

        Returns:
            Final status dict
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            status = self.check_job_status(run_id)

            if status["status"] == "completed":
                return status

            time.sleep(poll_interval)

        raise TimeoutError(f"Job {run_id} did not complete within {timeout}s")

    def _extract_run_url(self, output: str) -> str:
        """Extract GitHub Actions run URL from dispatch output"""
        import re
        match = re.search(r'https://github\.com/.+/actions/runs/\d+', output)
        if match:
            return match.group(0)
        raise ValueError("Could not extract run URL from output")

    def _extract_run_id(self, run_url: str) -> str:
        """Extract run ID from URL"""
        return run_url.split('/')[-1]


# Example usage in Atlas
if __name__ == "__main__":
    client = RelayQClient()

    # Submit transcription job
    job = client.submit_transcription(
        audio_url="https://example.com/podcast.mp3",
        backend="local",
        model="base",
        runner_preference="mac"  # Prefer Mac mini
    )

    print(f"Job submitted: {job['run_url']}")
    print(f"Run ID: {job['run_id']}")

    # Wait for completion
    print("Waiting for job to complete...")
    status = client.wait_for_completion(job['run_id'])

    if status["conclusion"] == "success":
        print("Job completed successfully!")

        # Download transcript
        transcript_path = client.download_transcript(
            job['run_id'],
            f"/tmp/transcript-{job['run_id']}.txt"
        )

        print(f"Transcript downloaded to: {transcript_path}")
    else:
        print(f"Job failed: {status['conclusion']}")
```

### RelayQ Side Changes (Minimal)

**Option 1: No Changes Required** ✅ **RECOMMENDED**
- Use existing `transcribe_audio.yml` workflow
- Atlas just calls it with URLs
- RelayQ doesn't need to know about Atlas

**Option 2: Add Atlas-Specific Workflows** (Optional)
- Create `.github/workflows/atlas_transcribe.yml`
- Optimized for Atlas podcast processing
- Could add webhook callbacks to Atlas

---

## Integration Patterns

### Pattern 1: Fire and Forget (Simple)

```python
# In Atlas podcast processor
from integrations.relayq_client import RelayQClient

def process_podcast_episode(episode_url, episode_id):
    # Check if transcript exists
    if has_transcript(episode_id):
        return

    # Submit to RelayQ
    client = RelayQClient()
    job = client.submit_transcription(
        audio_url=episode_url,
        backend="local",
        runner_preference="mac"
    )

    # Store job info for later polling
    save_pending_job(episode_id, job['run_id'])

    # Continue processing other episodes
    return
```

**Pros**:
- ✅ Non-blocking
- ✅ High throughput
- ✅ Simple

**Cons**:
- ❌ Need separate polling process
- ❌ Transcript not immediately available

### Pattern 2: Wait for Completion (Blocking)

```python
def process_podcast_episode_blocking(episode_url, episode_id):
    client = RelayQClient()

    # Submit job
    job = client.submit_transcription(episode_url)

    # Wait for completion (blocks)
    status = client.wait_for_completion(job['run_id'], timeout=3600)

    if status['conclusion'] == 'success':
        # Download transcript
        transcript = client.download_transcript(job['run_id'])

        # Save to database
        save_transcript(episode_id, transcript)

    return
```

**Pros**:
- ✅ Transcript immediately available
- ✅ Simple error handling

**Cons**:
- ❌ Blocks Atlas processing
- ❌ Low throughput

### Pattern 3: Background Worker (Optimal) ⭐

```python
# Atlas main process (non-blocking)
def discover_podcasts():
    episodes = fetch_rss_episodes()

    for episode in episodes:
        if not has_transcript(episode['id']):
            # Submit to RelayQ
            client = RelayQClient()
            job = client.submit_transcription(episode['audio_url'])

            # Queue for later processing
            queue_for_polling(episode['id'], job['run_id'])

# Separate background worker
def transcript_poller():
    """Background worker that polls RelayQ jobs"""
    while True:
        pending_jobs = get_pending_jobs()

        for job in pending_jobs:
            client = RelayQClient()
            status = client.check_job_status(job['run_id'])

            if status['status'] == 'completed':
                if status['conclusion'] == 'success':
                    # Download and save transcript
                    transcript = client.download_transcript(job['run_id'])
                    save_transcript(job['episode_id'], transcript)

                # Remove from pending queue
                remove_pending_job(job['id'])

        time.sleep(60)  # Poll every minute
```

**Pros**:
- ✅ Non-blocking discovery
- ✅ High throughput
- ✅ Scalable
- ✅ Automatic retry handling

**Cons**:
- ❌ Slightly more complex
- ❌ Need background worker process

---

## Use Case Mapping

### Use Case 1: Podcast Backlog Import

**Scenario**: Import 100 podcast episodes from RSS feed

**Flow**:
```
1. Atlas discovers 100 episodes via RSS
2. For each episode without transcript:
   a. Submit to RelayQ (non-blocking)
   b. Store run_id in pending_jobs table
3. Background worker polls every minute:
   a. Check status of pending jobs
   b. Download completed transcripts
   c. Save to Atlas database
```

**Atlas Code**:
```python
# In atlas_log_processor.py or podcast_processor.py
from integrations.relayq_client import RelayQClient

def process_podcast_with_relayq(episode_data):
    """Process podcast episode using RelayQ for transcription"""

    # Check if transcript needed
    if episode_data.get('transcript_url'):
        # Already has transcript, use it
        return fetch_existing_transcript(episode_data['transcript_url'])

    # Need transcription - submit to RelayQ
    client = RelayQClient()

    try:
        job = client.submit_transcription(
            audio_url=episode_data['audio_url'],
            backend='local',  # Use local Whisper on Mac mini
            model='base',     # Fast, good quality
            runner_preference='mac'  # Prefer Mac mini
        )

        # Store pending job
        store_pending_transcription(
            episode_id=episode_data['id'],
            run_id=job['run_id'],
            audio_url=episode_data['audio_url'],
            submitted_at=datetime.now()
        )

        logger.info(f"Submitted transcription job: {job['run_url']}")
        return None  # Transcript will be available later

    except Exception as e:
        logger.error(f"Failed to submit transcription: {e}")
        return None
```

**RelayQ Workflow**: Use existing `transcribe_audio.yml` ✅

### Use Case 2: Real-Time YouTube Processing

**Scenario**: User emails YouTube URL to Atlas

**Flow**:
```
1. Atlas receives email with YouTube URL
2. Submits to RelayQ for download + transcription
3. Waits for completion (or polls in background)
4. Saves video metadata + transcript to database
```

**Atlas Code**:
```python
def process_youtube_url_via_relayq(youtube_url):
    """Process YouTube video using RelayQ"""

    client = RelayQClient()

    # Submit job (use Mac mini for video processing)
    job = client.submit_transcription(
        audio_url=youtube_url,
        backend='local',
        runner_preference='mac'
    )

    # For YouTube, might want to wait (blocking)
    # or add to queue for background processing
    return job['run_id']
```

**RelayQ Workflow**: Need new workflow `atlas_youtube.yml`

### Use Case 3: Bulk Transcript Generation

**Scenario**: Generate transcripts for all podcast episodes missing them

**Flow**:
```
1. Atlas queries database for episodes without transcripts
2. Submits batch of jobs to RelayQ (e.g., 50 episodes)
3. Background worker polls and processes results
4. Runs overnight, completes by morning
```

**Atlas Code**:
```python
def bulk_transcribe_missing_episodes(max_jobs=50):
    """Bulk transcribe episodes missing transcripts"""

    episodes = get_episodes_without_transcripts(limit=max_jobs)
    client = RelayQClient()

    submitted = 0
    for episode in episodes:
        try:
            job = client.submit_transcription(
                audio_url=episode['audio_url'],
                backend='local',
                runner_preference='pooled'  # Use any available runner
            )

            store_pending_transcription(
                episode_id=episode['id'],
                run_id=job['run_id']
            )

            submitted += 1
            time.sleep(2)  # Rate limit submissions

        except Exception as e:
            logger.error(f"Failed to submit {episode['id']}: {e}")
            continue

    logger.info(f"Submitted {submitted} transcription jobs to RelayQ")
```

---

## Configuration

### Atlas Environment Variables

Add to Atlas `.env`:
```bash
# RelayQ Integration
RELAYQ_ENABLED=true
RELAYQ_REPO=Khamel83/relayq
RELAYQ_DISPATCH_SCRIPT=/home/ubuntu/relayq/bin/dispatch.sh
RELAYQ_DEFAULT_BACKEND=local
RELAYQ_DEFAULT_MODEL=base
RELAYQ_RUNNER_PREFERENCE=mac  # mac, rpi, pooled
GITHUB_TOKEN=ghp_your_github_token_here  # For API calls
```

### RelayQ Runner Configuration

**No changes needed** - Use existing runner setup ✅

Runners already configured with:
```bash
# ~/.config/relayq/env
ASR_BACKEND=local
WHISPER_MODEL=base
AI_API_KEY=your_key_here  # Optional, for OpenAI fallback
```

---

## Database Schema Changes

### New Table: `relayq_jobs`

```sql
CREATE TABLE relayq_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    episode_id INTEGER,  -- FK to content table
    run_id TEXT NOT NULL,
    run_url TEXT,
    audio_url TEXT NOT NULL,
    backend TEXT DEFAULT 'local',
    runner_preference TEXT DEFAULT 'pooled',
    status TEXT DEFAULT 'queued',  -- queued, in_progress, completed, failed
    conclusion TEXT,  -- success, failure, cancelled
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    transcript_path TEXT,
    error_message TEXT,

    FOREIGN KEY (episode_id) REFERENCES content(id),
    INDEX idx_status (status),
    INDEX idx_run_id (run_id),
    INDEX idx_episode (episode_id)
);
```

### Update Content Table

Add column for RelayQ transcription:
```sql
ALTER TABLE content ADD COLUMN transcribed_via_relayq BOOLEAN DEFAULT FALSE;
ALTER TABLE content ADD COLUMN relayq_job_id INTEGER;
```

---

## Implementation Plan

### Phase 1: Basic Integration (Week 1)

**Goals**:
- ✅ Atlas can submit jobs to RelayQ
- ✅ Atlas can poll job status
- ✅ Transcripts downloaded and saved

**Tasks**:
1. Create `atlas/integrations/relayq_client.py`
2. Add environment variables to Atlas `.env`
3. Test job submission with single podcast episode
4. Verify transcript download and storage
5. Add database table for pending jobs

### Phase 2: Background Worker (Week 2)

**Goals**:
- ✅ Non-blocking job submission
- ✅ Background polling of pending jobs
- ✅ Automatic retry on failures

**Tasks**:
1. Create `atlas/workers/transcript_poller.py`
2. Add to systemd services
3. Implement retry logic
4. Add monitoring and logging

### Phase 3: Advanced Features (Week 3-4)

**Goals**:
- ✅ YouTube video processing
- ✅ Bulk transcription operations
- ✅ Cost optimization (choose backend based on file size)

**Tasks**:
1. Add YouTube-specific RelayQ workflow
2. Implement cost optimizer (local vs API)
3. Add batch processing UI/CLI
4. Performance tuning

---

## Cost Analysis

### Current Approach (Without RelayQ)

**Podcast Transcription**:
- Option A: Use OpenAI Whisper API
  - Cost: $0.006/minute
  - 1 hour podcast = $0.36
  - 100 podcasts/month = $36/month

- Option B: Skip podcasts without transcripts
  - Cost: $0
  - Coverage: ~30% (only podcasts with existing transcripts)

### With RelayQ Integration

**Podcast Transcription**:
- Local Whisper on Mac mini
  - Cost: ~$0.01 in electricity per hour
  - 1 hour podcast = ~10 min processing = $0.0017
  - 100 podcasts/month = $0.17/month

**Savings**: **$36 → $0.17 = $35.83/month saved** 💰

**Additional Benefits**:
- ✅ Complete privacy (everything local)
- ✅ No API limits
- ✅ Better quality (can use larger models)
- ✅ Faster processing (Apple Silicon M1/M2)

---

## Monitoring & Observability

### Metrics to Track

**In Atlas**:
```python
# Add to atlas_status.py or monitoring
{
    "relayq_integration": {
        "jobs_submitted": 45,
        "jobs_pending": 12,
        "jobs_completed": 30,
        "jobs_failed": 3,
        "success_rate": 0.91,
        "avg_processing_time_seconds": 580,
        "transcripts_per_day": 24
    }
}
```

**In RelayQ**:
- Use GitHub Actions UI to monitor jobs
- Check runner status: `gh api repos/Khamel83/relayq/actions/runners`
- View workflow runs: `gh run list --repo Khamel83/relayq`

### Alerts

Add to Atlas monitoring:
```python
def check_relayq_health():
    """Monitor RelayQ integration health"""

    # Check for stuck jobs (pending > 1 hour)
    stuck_jobs = get_jobs_pending_longer_than(hours=1)
    if len(stuck_jobs) > 0:
        alert("RelayQ jobs stuck", stuck_jobs)

    # Check for high failure rate
    failure_rate = get_failure_rate_last_24h()
    if failure_rate > 0.2:  # > 20% failures
        alert("RelayQ high failure rate", failure_rate)

    # Check for runner offline
    runner_status = check_runner_status()
    if not runner_status['macmini_online']:
        alert("Mac mini runner offline")
```

---

## Failure Modes & Recovery

### Failure Mode 1: Runner Offline

**Detection**:
- Jobs stay in "queued" state for > 30 minutes
- GitHub API shows runner offline

**Recovery**:
1. Auto-restart runner service (systemd)
2. If still offline, fall back to OpenAI API
3. Alert admin

**Atlas Code**:
```python
def submit_with_fallback(audio_url):
    """Submit to RelayQ with API fallback"""

    client = RelayQClient()

    try:
        # Try local first (via RelayQ)
        job = client.submit_transcription(
            audio_url=audio_url,
            backend='local',
            runner_preference='mac'
        )

        # Check if job starts within 5 minutes
        time.sleep(300)  # 5 min
        status = client.check_job_status(job['run_id'])

        if status['status'] == 'queued':
            # Still queued, runner might be offline
            logger.warn("Runner not picking up job, falling back to API")
            return transcribe_via_openai_api(audio_url)

        return job

    except Exception as e:
        logger.error(f"RelayQ submission failed, using API fallback: {e}")
        return transcribe_via_openai_api(audio_url)
```

### Failure Mode 2: Transcription Failed

**Detection**:
- Job completes with conclusion="failure"

**Recovery**:
1. Check error logs in GitHub Actions
2. Retry with different backend
3. If persistent, skip episode

**Atlas Code**:
```python
def handle_failed_transcription(run_id, episode_id):
    """Handle failed transcription job"""

    client = RelayQClient()

    # Get failure details
    status = client.check_job_status(run_id)

    # Check retry count
    retry_count = get_retry_count(episode_id)

    if retry_count < 3:
        # Retry with different backend
        if retry_count == 0:
            # First retry: try different model
            return client.submit_transcription(
                audio_url=get_audio_url(episode_id),
                backend='local',
                model='small'  # Larger model
            )
        elif retry_count == 1:
            # Second retry: try API
            return client.submit_transcription(
                audio_url=get_audio_url(episode_id),
                backend='openai'
            )
        else:
            # Third retry failed, give up
            mark_episode_as_failed(episode_id, status)
```

### Failure Mode 3: GitHub Actions Down

**Detection**:
- API calls fail with 503 Service Unavailable

**Recovery**:
1. Fall back to direct OpenAI API
2. Queue jobs for later retry
3. Resume when GitHub Actions is back

---

## Testing Strategy

### Unit Tests

```python
# tests/test_relayq_client.py
import pytest
from integrations.relayq_client import RelayQClient

def test_submit_transcription(mock_subprocess):
    """Test job submission"""
    client = RelayQClient()

    job = client.submit_transcription(
        audio_url="https://example.com/test.mp3",
        backend="local"
    )

    assert job['run_id']
    assert job['status'] == 'queued'

def test_check_job_status(mock_github_api):
    """Test status checking"""
    client = RelayQClient()

    status = client.check_job_status("12345")

    assert status['status'] in ['queued', 'in_progress', 'completed']

def test_download_transcript(mock_github_api):
    """Test transcript download"""
    client = RelayQClient()

    path = client.download_transcript("12345", "/tmp/test.txt")

    assert path.exists()
    assert path.read_text()
```

### Integration Tests

```python
# tests/integration/test_relayq_integration.py
def test_end_to_end_transcription():
    """Test complete transcription flow"""

    # Submit job
    client = RelayQClient()
    job = client.submit_transcription(
        audio_url="https://example.com/short-test.mp3",
        backend="local"
    )

    # Wait for completion (short test file)
    status = client.wait_for_completion(job['run_id'], timeout=300)

    assert status['conclusion'] == 'success'

    # Download transcript
    transcript = client.download_transcript(job['run_id'], "/tmp/test.txt")

    assert transcript
    assert len(transcript) > 0
```

---

## Summary

### Can We Use RelayQ As-Is?

**YES!** ✅ **RelayQ is perfect for this.**

**No changes needed to RelayQ core**:
- ✅ Use existing workflows (`transcribe_audio.yml`, etc.)
- ✅ Use existing dispatch script
- ✅ Use existing runner labels
- ✅ Use existing backends (local, openai, router)

**Only Atlas-side changes**:
- ✅ Add RelayQ client library
- ✅ Add background polling worker
- ✅ Add database table for pending jobs
- ✅ Integrate into podcast processor

### Benefits

**Cost Savings**:
- 💰 $36/month → $0.17/month (210x cheaper)

**Privacy**:
- 🔒 All processing local
- 🔒 No data sent to APIs

**Performance**:
- ⚡ Apple Silicon M1/M2 is fast
- ⚡ Can use larger Whisper models
- ⚡ Parallel processing

**Flexibility**:
- 🎯 Route jobs to specific hardware
- 🎯 Fallback to APIs when needed
- 🎯 Mix local + API based on file size

### Next Steps

1. **Week 1**: Implement `relayq_client.py` in Atlas
2. **Week 2**: Add background polling worker
3. **Week 3**: Test with podcast backlog
4. **Week 4**: Production deployment

---

**Integration Status**: ✅ **Designed and Ready to Implement**
**RelayQ Changes Required**: ❌ **None** - Use as-is
**Atlas Changes Required**: ✅ **Minimal** - Add client library + worker
**Estimated Implementation**: 2-4 weeks
**Cost Savings**: $35.83/month (210x cheaper)
**Privacy Improvement**: 100% (everything local)
