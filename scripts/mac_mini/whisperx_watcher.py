#!/usr/bin/env python3
"""
WhisperX watch folder script for Atlas podcast transcription.

Watches the SMB-mounted audio folder for new MP3 files and transcribes them
using WhisperX with speaker diarization.

SETUP:
1. Install WhisperX: pip install whisperx pyannote.audio
2. Get HuggingFace token and save to ~/.huggingface/token
3. Mount SMB share: mount_smbfs //user@homelab/atlas /Volumes/atlas
4. Run this script: python whisperx_watcher.py

This script is designed to run on the Mac Mini M4.
"""

import os
import json
import time
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional

# Configuration
WATCH_DIR = Path("/Volumes/atlas-whisper/audio")
OUTPUT_DIR = Path("/Volumes/atlas-whisper/transcripts")
PROCESSED_DIR = Path("/Volumes/atlas-whisper/diarized_audio")
STATE_FILE = Path.home() / ".whisperx_state.json"

# WhisperX settings
MODEL = "large-v3"
LANGUAGE = "en"
BATCH_SIZE = 8  # Reduce if running out of memory
COMPUTE_TYPE = "int8"  # int8 for M-series Macs (float16 not supported in ctranslate2)

# Polling interval (seconds)
POLL_INTERVAL = 60

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(Path.home() / "logs" / "whisperx.log")
    ]
)
logger = logging.getLogger(__name__)


def get_hf_token() -> Optional[str]:
    """Get HuggingFace token from file or environment."""
    # Try environment variable first
    token = os.environ.get("HF_TOKEN")
    if token:
        return token

    # Try file
    token_file = Path.home() / ".huggingface" / "token"
    if token_file.exists():
        return token_file.read_text().strip()

    logger.error("No HuggingFace token found. Set HF_TOKEN env var or create ~/.huggingface/token")
    return None


def load_state() -> dict:
    """Load processing state from file."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception as e:
            logger.warning(f"Error loading state: {e}")
    return {"processed": [], "failed": []}


def save_state(state: dict):
    """Save processing state to file."""
    STATE_FILE.write_text(json.dumps(state, indent=2))


def is_smb_mounted() -> bool:
    """Check if SMB share is mounted."""
    return WATCH_DIR.exists() and WATCH_DIR.is_dir()


def get_pending_files(state: dict) -> list:
    """Get list of MP3 files that haven't been processed."""
    if not WATCH_DIR.exists():
        return []

    processed = set(state.get("processed", []))
    failed = set(state.get("failed", []))

    pending = []
    for mp3 in WATCH_DIR.glob("*.mp3"):
        if mp3.name not in processed and mp3.name not in failed:
            pending.append(mp3)

    # Sort by modification time (oldest first)
    pending.sort(key=lambda p: p.stat().st_mtime)
    return pending


def transcribe_file(audio_path: Path, hf_token: str) -> Optional[Path]:
    """
    Transcribe an audio file using WhisperX with diarization.

    Returns path to output JSON file, or None if failed.
    """
    logger.info(f"Transcribing: {audio_path.name}")

    output_path = OUTPUT_DIR / f"{audio_path.stem}.json"

    try:
        # Build whisperx command
        cmd = [
            "whisperx",
            str(audio_path),
            "--model", MODEL,
            "--language", LANGUAGE,
            "--diarize",
            "--hf_token", hf_token,
            "--batch_size", str(BATCH_SIZE),
            "--compute_type", COMPUTE_TYPE,
            "--output_dir", str(OUTPUT_DIR),
            "--output_format", "json",
        ]

        # Run whisperx
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout
        )

        if result.returncode != 0:
            logger.error(f"WhisperX failed: {result.stderr}")
            return None

        # Check if output file was created
        if output_path.exists():
            logger.info(f"Transcribed: {audio_path.name} -> {output_path.name}")
            return output_path
        else:
            logger.error(f"Output file not created: {output_path}")
            return None

    except subprocess.TimeoutExpired:
        logger.error(f"Transcription timed out: {audio_path.name}")
        return None
    except Exception as e:
        logger.error(f"Error transcribing {audio_path.name}: {e}")
        return None


def process_batch(state: dict, hf_token: str, limit: int = 5):
    """Process a batch of pending audio files."""
    pending = get_pending_files(state)

    if not pending:
        logger.debug("No pending files to process")
        return

    logger.info(f"Found {len(pending)} pending files, processing up to {limit}")

    for audio_path in pending[:limit]:
        output_path = transcribe_file(audio_path, hf_token)

        if output_path:
            state["processed"].append(audio_path.name)

            # Optionally move processed audio to separate folder
            if PROCESSED_DIR.exists():
                try:
                    audio_path.rename(PROCESSED_DIR / audio_path.name)
                except Exception as e:
                    logger.warning(f"Could not move processed file: {e}")
        else:
            state["failed"].append(audio_path.name)

        save_state(state)

        # Small delay between files
        time.sleep(5)


def main():
    """Main loop: watch folder and process new files."""
    logger.info("WhisperX Watcher starting...")

    # Create directories
    (Path.home() / "logs").mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # Get HuggingFace token
    hf_token = get_hf_token()
    if not hf_token:
        logger.error("Cannot start without HuggingFace token")
        return

    # Load state
    state = load_state()
    logger.info(f"Loaded state: {len(state.get('processed', []))} processed, {len(state.get('failed', []))} failed")

    while True:
        try:
            # Check SMB mount
            if not is_smb_mounted():
                logger.warning("SMB share not mounted, waiting...")
                time.sleep(POLL_INTERVAL * 2)
                continue

            # Process batch of files
            process_batch(state, hf_token, limit=3)

        except KeyboardInterrupt:
            logger.info("Shutting down...")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
