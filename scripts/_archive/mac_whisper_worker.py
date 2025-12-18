#!/usr/bin/env python3
"""
Mac Mini Whisper Worker

Run this on the Mac Mini. It:
1. Reads queue.json from SMB share
2. Downloads audio files
3. Transcribes with MacWhisper Pro (via watch folder)
4. Copies transcripts back to SMB share

Setup on Mac Mini:
1. Mount SMB share: mount_smbfs //user@server/atlas /Volumes/atlas
   Or add to Finder: smb://server/atlas
2. Configure MacWhisper Pro watch folder -> /Volumes/atlas/data/whisper_queue/audio
3. Configure MacWhisper Pro output -> /Volumes/atlas/data/whisper_queue/transcripts
4. Run this script to download audio files

Directory structure on SMB:
  /Volumes/atlas/data/whisper_queue/
    queue.json          <- Server writes this
    audio/              <- This script downloads here, MacWhisper watches
    transcripts/        <- MacWhisper outputs here, server imports
    processed.json      <- Server tracks what's done
"""

import argparse
import json
import logging
import os
import subprocess
import time
from pathlib import Path
from urllib.parse import urlparse

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def download_audio(url: str, output_path: Path, rate_limit: float = 2.0) -> bool:
    """Download audio file using curl."""
    try:
        if output_path.exists():
            logger.info(f"Already downloaded: {output_path.name}")
            return True

        logger.info(f"Downloading: {output_path.name}")

        # Use curl for robust downloading
        cmd = [
            'curl', '-L', '-o', str(output_path),
            '--max-time', '600',  # 10 min timeout
            '--retry', '3',
            '-H', 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
            url
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error(f"Download failed: {result.stderr}")
            return False

        # Verify file exists and has content
        if output_path.exists() and output_path.stat().st_size > 1000:
            logger.info(f"Downloaded: {output_path.name} ({output_path.stat().st_size / 1024 / 1024:.1f} MB)")
            time.sleep(rate_limit)  # Rate limit
            return True
        else:
            logger.error(f"Download too small or missing: {output_path}")
            output_path.unlink(missing_ok=True)
            return False

    except Exception as e:
        logger.error(f"Download error: {e}")
        return False


def process_queue(queue_dir: Path, limit: int = 0, rate_limit: float = 2.0):
    """Process the queue file and download audio."""

    queue_file = queue_dir / 'queue.json'
    audio_dir = queue_dir / 'audio'
    transcripts_dir = queue_dir / 'transcripts'

    if not queue_file.exists():
        logger.error(f"Queue file not found: {queue_file}")
        logger.info("Run 'python scripts/export_for_whisper.py' on the server first")
        return

    audio_dir.mkdir(exist_ok=True)
    transcripts_dir.mkdir(exist_ok=True)

    # Load queue
    queue = json.loads(queue_file.read_text())
    episodes = queue.get('episodes', [])
    logger.info(f"Queue has {len(episodes)} episodes")

    # Check what's already transcribed
    transcribed = set()
    for tf in transcripts_dir.glob('*'):
        # Extract episode ID from filename
        name = tf.stem
        if '_' in name:
            try:
                ep_id = int(name.split('_')[-1])
                transcribed.add(ep_id)
            except ValueError:
                pass

    logger.info(f"Already transcribed: {len(transcribed)}")

    # Download audio for episodes not yet transcribed
    downloaded = 0
    skipped = 0

    for ep in episodes:
        ep_id = ep['id']

        if ep_id in transcribed:
            skipped += 1
            continue

        audio_path = audio_dir / ep['filename']

        # Check if already downloaded (MacWhisper might be processing)
        if audio_path.exists():
            logger.info(f"Audio exists, waiting for MacWhisper: {ep['filename']}")
            skipped += 1
            continue

        if download_audio(ep['audio_url'], audio_path, rate_limit):
            downloaded += 1
        else:
            logger.error(f"Failed to download: {ep['title']}")

        if limit and downloaded >= limit:
            logger.info(f"Reached limit of {limit} downloads")
            break

    print(f"\nDownload complete:")
    print(f"  Downloaded: {downloaded}")
    print(f"  Skipped (already done): {skipped}")
    print(f"  Remaining: {len(episodes) - downloaded - skipped}")
    print(f"\nMacWhisper Pro should now process files in: {audio_dir}")
    print(f"Transcripts will appear in: {transcripts_dir}")


def main():
    parser = argparse.ArgumentParser(description='Mac Mini Whisper Worker')
    parser.add_argument('--queue-dir', '-q',
                        default='/Volumes/atlas/data/whisper_queue',
                        help='Queue directory (SMB path)')
    parser.add_argument('--limit', '-l', type=int, default=10,
                        help='Limit downloads per run (default: 10)')
    parser.add_argument('--rate-limit', '-r', type=float, default=2.0,
                        help='Seconds between downloads (default: 2)')
    args = parser.parse_args()

    process_queue(Path(args.queue_dir), args.limit, args.rate_limit)


if __name__ == '__main__':
    main()
