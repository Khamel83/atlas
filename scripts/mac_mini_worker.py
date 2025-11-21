#!/usr/bin/env python3
"""
Mac Mini Worker - Mac Mini side
Processes tasks from Atlas via file-based queue system
Run this script ON THE MAC MINI
"""

import json
import time
import logging
import whisper
import requests
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import os
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('~/atlas_worker/logs/worker.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MacMiniWorker:
    """Mac Mini worker that processes Atlas tasks"""

    def __init__(self, queue_dir="~/atlas_worker/queue"):
        self.queue_dir = Path(queue_dir).expanduser()
        self.tasks_dir = self.queue_dir / "tasks"
        self.results_dir = self.queue_dir / "results"

        # Create directories
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)

        # Load Whisper models
        self.whisper_models = {}
        self._load_whisper_models()

        logger.info(f"🤖 Mac Mini Worker initialized")
        logger.info(f"📁 Queue directory: {self.queue_dir}")

    def _load_whisper_models(self):
        """Preload Whisper models for faster processing"""
        try:
            for model_name in ['tiny', 'base', 'small']:
                logger.info(f"📥 Loading Whisper model: {model_name}")
                self.whisper_models[model_name] = whisper.load_model(model_name)
            logger.info("✅ Whisper models loaded")
        except Exception as e:
            logger.error(f"❌ Failed to load Whisper models: {e}")

    def _download_audio(self, audio_url: str) -> Optional[Path]:
        """Download audio file from URL"""
        try:
            logger.info(f"📥 Downloading audio: {audio_url}")
            response = requests.get(audio_url, stream=True, timeout=60)
            response.raise_for_status()

            # Create temporary file
            suffix = '.mp3'  # Default to mp3
            if audio_url.endswith('.m4a'):
                suffix = '.m4a'
            elif audio_url.endswith('.wav'):
                suffix = '.wav'

            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)

            # Download in chunks
            for chunk in response.iter_content(chunk_size=8192):
                temp_file.write(chunk)

            temp_file.close()
            audio_file = Path(temp_file.name)

            logger.info(f"✅ Audio downloaded: {audio_file} ({audio_file.stat().st_size} bytes)")
            return audio_file

        except Exception as e:
            logger.error(f"❌ Failed to download audio: {e}")
            return None

    def transcribe_audio(self, audio_url: str, quality: str = "base") -> Dict[str, Any]:
        """Transcribe audio using Whisper"""
        start_time = time.time()

        try:
            # Download audio file
            audio_file = self._download_audio(audio_url)
            if not audio_file:
                return {"success": False, "error": "Failed to download audio"}

            # Get Whisper model
            if quality not in self.whisper_models:
                return {"success": False, "error": f"Whisper model '{quality}' not available"}

            model = self.whisper_models[quality]

            # Transcribe
            logger.info(f"🎤 Transcribing with {quality} model...")
            result = model.transcribe(str(audio_file))

            # Clean up audio file
            audio_file.unlink()

            processing_time = time.time() - start_time

            logger.info(f"✅ Transcription completed in {processing_time:.1f}s")

            return {
                "success": True,
                "transcript": result["text"],
                "language": result.get("language", "unknown"),
                "duration": processing_time,
                "model": quality,
                "segments": len(result.get("segments", [])),
                "completed_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"❌ Transcription failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "duration": time.time() - start_time
            }

    def process_task(self, task_file: Path) -> bool:
        """Process a single task file"""
        try:
            # Read task
            with open(task_file, 'r') as f:
                task = json.load(f)

            task_id = task["task_id"]
            task_type = task["task_type"]
            task_data = task.get("data", {})

            logger.info(f"▶️ Processing task {task_id[:8]} ({task_type})")

            # Process based on task type
            if task_type == "audio_transcribe":
                result = self.transcribe_audio(
                    task_data.get("audio_url"),
                    task_data.get("quality", "base")
                )
            else:
                result = {
                    "success": False,
                    "error": f"Unknown task type: {task_type}"
                }

            # Add task metadata to result
            result.update({
                "task_id": task_id,
                "task_type": task_type,
                "processed_at": datetime.now().isoformat()
            })

            # Write result file
            if result.get("success"):
                result_file = self.results_dir / f"{task_id}_result.json"
            else:
                result_file = self.results_dir / f"{task_id}_error.json"

            with open(result_file, 'w') as f:
                json.dump(result, f, indent=2)

            # Remove task file
            task_file.unlink()

            status = "✅" if result.get("success") else "❌"
            logger.info(f"{status} Task {task_id[:8]} processed")

            return True

        except Exception as e:
            logger.error(f"❌ Failed to process task {task_file.name}: {e}")

            # Write error result
            try:
                task_id = task_file.stem.replace('_task', '')
                error_result = {
                    "success": False,
                    "error": f"Task processing failed: {e}",
                    "task_id": task_id,
                    "processed_at": datetime.now().isoformat()
                }

                error_file = self.results_dir / f"{task_id}_error.json"
                with open(error_file, 'w') as f:
                    json.dump(error_result, f, indent=2)

                # Remove task file
                task_file.unlink()

            except Exception as cleanup_error:
                logger.error(f"❌ Failed to write error result: {cleanup_error}")

            return False

    def run(self, poll_interval: int = 30):
        """Main worker loop"""
        logger.info(f"🚀 Starting Mac Mini worker (poll interval: {poll_interval}s)")

        try:
            while True:
                # Look for new task files
                task_files = list(self.tasks_dir.glob("*_task.json"))

                if task_files:
                    logger.info(f"📋 Found {len(task_files)} task(s) to process")

                    for task_file in task_files:
                        self.process_task(task_file)

                else:
                    logger.debug(f"💤 No tasks found, sleeping {poll_interval}s...")

                time.sleep(poll_interval)

        except KeyboardInterrupt:
            logger.info("🛑 Worker stopped by user")
        except Exception as e:
            logger.error(f"❌ Worker crashed: {e}")
            raise

def main():
    """CLI interface for Mac Mini worker"""
    import argparse

    parser = argparse.ArgumentParser(description='Mac Mini Worker')
    parser.add_argument('--queue-dir', default='~/atlas_worker/queue',
                       help='Queue directory path')
    parser.add_argument('--poll-interval', type=int, default=30,
                       help='Polling interval in seconds')
    parser.add_argument('--test', action='store_true',
                       help='Test worker setup and exit')

    args = parser.parse_args()

    worker = MacMiniWorker(args.queue_dir)

    if args.test:
        # Test worker setup
        logger.info("🧪 Testing Mac Mini worker setup...")

        # Test Whisper
        if worker.whisper_models:
            logger.info(f"✅ Whisper models loaded: {list(worker.whisper_models.keys())}")
        else:
            logger.error("❌ No Whisper models loaded")
            return 1

        # Test directories
        if worker.tasks_dir.exists() and worker.results_dir.exists():
            logger.info(f"✅ Queue directories ready")
        else:
            logger.error("❌ Queue directories not ready")
            return 1

        logger.info("🎉 Mac Mini worker ready!")
        return 0

    else:
        # Run worker
        worker.run(args.poll_interval)

if __name__ == "__main__":
    sys.exit(main())