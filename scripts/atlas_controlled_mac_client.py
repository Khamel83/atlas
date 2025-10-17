#!/usr/bin/env python3
"""
Atlas-Controlled Mac Mini Worker Client
Polls Atlas for jobs, executes transcription tasks, reports back
"""

import os
import time
import json
import subprocess
import requests
from pathlib import Path
import tempfile
import urllib.request
import hashlib
from helpers.bulletproof_process_manager import create_managed_process

class AtlasWorkerClient:
    def __init__(self, atlas_url, api_key=None, worker_id=None):
        self.atlas_url = atlas_url.rstrip('/')
        self.api_key = api_key
        self.worker_id = worker_id or f"mac_mini_{hashlib.md5(os.getenv('USER', 'unknown').encode()).hexdigest()[:8]}"

        # Create work directories
        self.work_dir = Path.home() / "atlas_worker"
        self.temp_dir = self.work_dir / "temp"
        self.completed_dir = self.work_dir / "completed"

        for dir_path in [self.work_dir, self.temp_dir, self.completed_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

    def poll_for_jobs(self):
        """Poll Atlas for available transcription jobs"""
        try:
            headers = {'Content-Type': 'application/json'}
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'

            response = requests.get(
                f"{self.atlas_url}/api/v1/worker/jobs",
                params={'worker_id': self.worker_id, 'capabilities': 'transcription'},
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                jobs = response.json().get('jobs', [])
                return jobs
            elif response.status_code == 204:
                return []  # No jobs available
            else:
                print(f"❌ Error polling for jobs: {response.status_code}")
                return []

        except requests.exceptions.RequestException as e:
            print(f"❌ Network error polling jobs: {e}")
            return []

    def execute_job(self, job):
        """Execute a transcription job from Atlas"""
        job_id = job['id']
        job_type = job['type']

        print(f"🎯 Starting job {job_id}: {job_type}")
        print(f"   📋 Title: {job['data'].get('title', 'Unknown')}")
        print(f"   🔗 URL: {job['data'].get('url', 'N/A')}")

        try:
            if job_type == 'transcribe_podcast':
                result = self.transcribe_podcast(job)
            elif job_type == 'transcribe_youtube':
                result = self.transcribe_youtube(job)
            elif job_type == 'transcribe_audio_file':
                result = self.transcribe_audio_file(job)
            else:
                raise Exception(f"Unknown job type: {job_type}")

            # Add Atlas content ID to result for linking
            result['atlas_content_id'] = job['data'].get('atlas_content_id')

            # Report success back to Atlas
            self.report_job_result(job_id, 'completed', result)
            print(f"✅ Job {job_id} completed successfully")
            print(f"   📝 Transcript: {len(result.get('transcript', ''))} chars")

        except Exception as e:
            print(f"❌ Job {job_id} failed: {e}")
            self.report_job_result(job_id, 'failed', {'error': str(e), 'atlas_content_id': job['data'].get('atlas_content_id')})

    def transcribe_from_url(self, job):
        """Download audio from URL and transcribe"""
        url = job['data']['url']
        filename = job['data'].get('filename', f"audio_{job['id']}")

        # Download audio file
        print(f"📥 Downloading: {url}")
        temp_file = self.temp_dir / f"{filename}.tmp"

        urllib.request.urlretrieve(url, temp_file)
        print(f"✅ Downloaded: {temp_file}")

        # Transcribe
        transcript = self.transcribe_with_whisper(temp_file)

        # Cleanup
        temp_file.unlink()

        return {
            'transcript': transcript,
            'source_url': url,
            'filename': filename,
            'length': len(transcript)
        }

    def transcribe_podcast(self, job):
        """Download and transcribe podcast episode"""
        episode_data = job['data']
        url = episode_data.get('url')  # Direct audio URL
        title = episode_data.get('title', 'Unknown Episode')

        print(f"🎙️ Processing podcast: {title}")

        # Download audio
        temp_file = self.temp_dir / f"podcast_{job['id']}.mp3"
        urllib.request.urlretrieve(url, temp_file)

        # Transcribe
        transcript = self.transcribe_with_whisper(temp_file)

        # Cleanup
        temp_file.unlink()

        return {
            'transcript': transcript,
            'source_url': url,
            'title': title,
            'content_type': 'podcast',
            'length': len(transcript)
        }

    def transcribe_audio_file(self, job):
        """Transcribe audio file that was uploaded to Atlas"""
        file_data = job['data']
        url = file_data.get('url')  # Could be uploaded file URL
        title = file_data.get('title', 'Audio File')

        print(f"🎵 Processing audio file: {title}")

        # Download if URL, or handle local file
        temp_file = self.temp_dir / f"audio_{job['id']}.tmp"

        if url.startswith('http'):
            urllib.request.urlretrieve(url, temp_file)
        else:
            raise Exception("Local file handling not implemented yet")

        # Transcribe
        transcript = self.transcribe_with_whisper(temp_file)

        # Cleanup
        temp_file.unlink()

        return {
            'transcript': transcript,
            'source_url': url,
            'title': title,
            'content_type': 'audio_file',
            'length': len(transcript)
        }

    def transcribe_youtube(self, job):
        """Download YouTube audio and transcribe"""
        url = job['data'].get('url') or job['data'].get('video_url')
        title = job['data'].get('title', 'YouTube Video')

        print(f"📺 Processing YouTube: {title}")
        print(f"   🔗 URL: {url}")

        # Use yt-dlp to download audio only
        temp_file = self.temp_dir / f"youtube_{job['id']}.%(ext)s"

        try:
            # Download audio with better options
            process = create_managed_process([
                'yt-dlp',
                '--extract-audio',
                '--audio-format', 'mp3',
                '--audio-quality', '0',  # Best quality
                '--output', str(temp_file),
                '--no-playlist',
                url
            ], "yt_dlp_download", timeout=1200)
            stdout, stderr = process.communicate()

            if process.returncode != 0:
                raise Exception(f"YouTube download failed: {stderr.decode('utf-8')}")

            # Find the actual downloaded file
            downloaded_files = list(self.temp_dir.glob(f"youtube_{job['id']}.*"))
            if not downloaded_files:
                raise Exception("Downloaded file not found")

            actual_file = downloaded_files[0]
            print(f"   💾 Downloaded: {actual_file.name}")

            # Transcribe
            transcript = self.transcribe_with_whisper(actual_file)

            # Cleanup
            actual_file.unlink()

            return {
                'transcript': transcript,
                'source_url': url,
                'video_url': url,  # For backward compatibility
                'title': title,
                'content_type': 'youtube',
                'length': len(transcript)
            }

        except subprocess.CalledProcessError as e:
            raise Exception(f"YouTube download failed: {e.stderr}")
        except subprocess.TimeoutExpired:
            raise Exception("YouTube download timed out (20min)")

    def transcribe_with_whisper(self, audio_path):
        """Transcribe audio using whisper.cpp"""
        try:
            process = create_managed_process([
                'whisper',
                str(audio_path),
                '--language', 'en',
                '--model', 'base',
                '--output_format', 'txt',
                '--output_dir', '/tmp'
            ], "whisper_transcribe", timeout=600)
            stdout, stderr = process.communicate()

            if process.returncode != 0:
                raise Exception(f"Whisper failed: {stderr.decode('utf-8')}")

            if result.returncode != 0:
                raise Exception(f"Whisper failed: {result.stderr}")

            # Read transcript
            transcript_file = Path('/tmp') / f"{audio_path.stem}.txt"
            if transcript_file.exists():
                transcript = transcript_file.read_text().strip()
                transcript_file.unlink()
                return transcript
            else:
                raise Exception("Transcript file not found")

        except subprocess.TimeoutExpired:
            raise Exception("Transcription timed out (10min)")

    def report_job_result(self, job_id, status, result_data):
        """Report job completion back to Atlas"""
        try:
            headers = {'Content-Type': 'application/json'}
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'

            payload = {
                'job_id': job_id,
                'worker_id': self.worker_id,
                'status': status,
                'result': result_data,
                'timestamp': time.time()
            }

            response = requests.post(
                f"{self.atlas_url}/api/v1/worker/results",
                json=payload,
                headers=headers,
                timeout=30
            )

            if response.status_code != 200:
                print(f"❌ Failed to report result: {response.status_code}")

        except Exception as e:
            print(f"❌ Error reporting result: {e}")

    def register_worker(self):
        """Register this worker with Atlas"""
        try:
            headers = {'Content-Type': 'application/json'}
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'

            worker_info = {
                'worker_id': self.worker_id,
                'capabilities': ['transcription', 'youtube', 'podcast'],
                'platform': 'macos',
                'whisper_available': True,
                'ytdlp_available': create_managed_process(['which', 'yt-dlp'], 'check_ytdlp_available').wait() == 0
            }

            response = requests.post(
                f"{self.atlas_url}/api/v1/worker/register",
                json=worker_info,
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                print(f"✅ Worker registered: {self.worker_id}")
                return True
            else:
                print(f"❌ Worker registration failed: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ Registration error: {e}")
            return False

    def run(self):
        """Main worker loop"""
        print(f"🤖 Atlas Worker Client Starting")
        print(f"🆔 Worker ID: {self.worker_id}")
        print(f"🌐 Atlas URL: {self.atlas_url}")
        print(f"📁 Work Dir: {self.work_dir}")
        print("=" * 60)

        # Register with Atlas
        if not self.register_worker():
            print("❌ Failed to register worker. Exiting.")
            return

        print("🔄 Polling Atlas for jobs... (Ctrl+C to stop)")

        try:
            while True:
                # Poll for jobs
                jobs = self.poll_for_jobs()

                if jobs:
                    print(f"📋 Found {len(jobs)} job(s)")
                    for job in jobs:
                        self.execute_job(job)
                else:
                    # No jobs, wait before polling again
                    time.sleep(10)

        except KeyboardInterrupt:
            print("\n⏹️ Stopping Atlas worker...")

        print("✅ Worker stopped")

def main():
    # Configuration
    ATLAS_URL = os.getenv('ATLAS_URL', 'http://localhost:8000')
    API_KEY = os.getenv('ATLAS_API_KEY')
    WORKER_ID = os.getenv('ATLAS_WORKER_ID')

    worker = AtlasWorkerClient(ATLAS_URL, API_KEY, WORKER_ID)
    worker.run()

if __name__ == "__main__":
    main()