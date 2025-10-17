#!/usr/bin/env python3
"""
Mac Mini Client - Atlas side
Submits tasks to Mac Mini via file-based queue system
"""

import json
import uuid
import time
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MacMiniClient:
    """Client for submitting tasks to Mac Mini worker"""

    def __init__(self, ssh_host="macmini", queue_dir="~/atlas_worker/queue"):
        self.ssh_host = ssh_host
        self.queue_dir = queue_dir
        self.tasks_dir = f"{queue_dir}/tasks"
        self.results_dir = f"{queue_dir}/results"

        # Create queue directories on Mac Mini
        self._ensure_remote_directories()

    def _ensure_remote_directories(self):
        """Create queue directories on Mac Mini if they don't exist"""
        try:
            subprocess.run([
                "ssh", self.ssh_host,
                f"mkdir -p {self.tasks_dir} {self.results_dir}"
            ], check=True, capture_output=True)
            logger.info("✅ Queue directories ready on Mac Mini")
        except subprocess.CalledProcessError as e:
            logger.warning(f"⚠️ Mac Mini not available - queue directories not created: {e}")
            # Don't raise - allow graceful degradation

    def submit_task(self, task_type: str, **task_data) -> str:
        """Submit a task to Mac Mini queue"""
        task_id = str(uuid.uuid4())

        # Prepare task payload
        task_payload = {
            "task_id": task_id,
            "task_type": task_type,
            "submitted_at": datetime.now().isoformat(),
            "data": task_data
        }

        # Write task file locally first
        local_task_file = f"/tmp/{task_id}_task.json"
        with open(local_task_file, 'w') as f:
            json.dump(task_payload, f, indent=2)

        # Copy task file to Mac Mini
        remote_task_file = f"{self.tasks_dir}/{task_id}_task.json"
        try:
            subprocess.run([
                "scp", local_task_file, f"{self.ssh_host}:{remote_task_file}"
            ], check=True, capture_output=True)

            # Clean up local file
            Path(local_task_file).unlink()

            logger.info(f"📤 Task {task_id[:8]} submitted ({task_type})")
            return task_id

        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to submit task: {e}")
            Path(local_task_file).unlink(missing_ok=True)
            raise

    def get_task_result(self, task_id: str, timeout: int = 300) -> Optional[Dict[str, Any]]:
        """Wait for and retrieve task result"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            # Check for result file
            result_file = f"{self.results_dir}/{task_id}_result.json"
            error_file = f"{self.results_dir}/{task_id}_error.json"

            try:
                # Try to copy result file
                local_result = f"/tmp/{task_id}_result.json"
                result = subprocess.run([
                    "scp", f"{self.ssh_host}:{result_file}", local_result
                ], capture_output=True)

                if result.returncode == 0:
                    # Result found!
                    with open(local_result, 'r') as f:
                        result_data = json.load(f)
                    Path(local_result).unlink()

                    # Clean up remote result file
                    subprocess.run([
                        "ssh", self.ssh_host, f"rm -f {result_file}"
                    ], capture_output=True)

                    logger.info(f"✅ Task {task_id[:8]} completed successfully")
                    return result_data

                # Check for error file
                error_result = subprocess.run([
                    "scp", f"{self.ssh_host}:{error_file}", f"/tmp/{task_id}_error.json"
                ], capture_output=True)

                if error_result.returncode == 0:
                    # Error found
                    with open(f"/tmp/{task_id}_error.json", 'r') as f:
                        error_data = json.load(f)
                    Path(f"/tmp/{task_id}_error.json").unlink()

                    # Clean up remote error file
                    subprocess.run([
                        "ssh", self.ssh_host, f"rm -f {error_file}"
                    ], capture_output=True)

                    logger.error(f"❌ Task {task_id[:8]} failed: {error_data.get('error', 'Unknown error')}")
                    return error_data

            except Exception as e:
                logger.debug(f"Polling for task {task_id[:8]}: {e}")

            time.sleep(5)  # Poll every 5 seconds

        logger.warning(f"⏰ Task {task_id[:8]} timed out after {timeout}s")
        return None

    def transcribe_audio(self, audio_url: str, quality: str = "base", timeout: int = 600) -> Optional[Dict[str, Any]]:
        """Submit audio transcription task and wait for result"""
        task_id = self.submit_task("audio_transcribe",
                                   audio_url=audio_url,
                                   quality=quality)
        return self.get_task_result(task_id, timeout)

    def test_connection(self) -> bool:
        """Test Mac Mini connection"""
        try:
            result = subprocess.run([
                "ssh", self.ssh_host, "echo 'Mac Mini connection test successful'"
            ], check=True, capture_output=True, text=True)

            if "successful" in result.stdout:
                logger.info("✅ Mac Mini connection working")
                return True
            else:
                logger.error("❌ Mac Mini connection test failed")
                return False

        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Mac Mini connection failed: {e}")
            return False

def main():
    """CLI interface for Mac Mini client"""
    import argparse

    parser = argparse.ArgumentParser(description='Mac Mini Task Client')
    parser.add_argument('command', choices=['test', 'transcribe', 'submit_task'])
    parser.add_argument('--audio-url', help='Audio URL for transcription')
    parser.add_argument('--quality', default='base', choices=['tiny', 'base', 'small', 'medium'],
                       help='Whisper model quality')
    parser.add_argument('--task-type', help='Task type for generic submission')
    parser.add_argument('--timeout', type=int, default=600, help='Task timeout in seconds')

    args = parser.parse_args()

    client = MacMiniClient()

    if args.command == 'test':
        success = client.test_connection()
        exit(0 if success else 1)

    elif args.command == 'transcribe':
        if not args.audio_url:
            print("❌ --audio-url required for transcription")
            exit(1)

        print(f"🎵 Transcribing: {args.audio_url}")
        result = client.transcribe_audio(args.audio_url, args.quality, args.timeout)

        if result:
            if result.get('success'):
                print(f"✅ Transcription completed ({result.get('duration', 'N/A')}s)")
                print(f"📝 Transcript: {result.get('transcript', '')[:200]}...")
            else:
                print(f"❌ Transcription failed: {result.get('error', 'Unknown error')}")
                exit(1)
        else:
            print("⏰ Transcription timed out")
            exit(1)

    elif args.command == 'submit_task':
        if not args.task_type:
            print("❌ --task-type required")
            exit(1)

        task_id = client.submit_task(args.task_type)
        print(f"📤 Task submitted: {task_id}")

if __name__ == "__main__":
    main()