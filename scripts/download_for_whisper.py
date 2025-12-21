#!/usr/bin/env python3
"""
Download podcast audio files for local Whisper transcription.

Downloads audio for episodes that need Whisper transcription.

Usage:
    # Download from config (recommended)
    python scripts/download_for_whisper.py --from-config --limit 10

    # Download by status (legacy)
    python scripts/download_for_whisper.py --status local --limit 10

    # Dry run
    python scripts/download_for_whisper.py --from-config --dry-run

Config file: config/whisper_podcasts.json
  Defines which podcasts need Whisper (paywalled, no online source, etc.)

Output folder: data/whisper_queue/audio/
  Files named: {podcast_slug}_{episode_id}_{date}_{title_slug}.mp3

MacWhisper/WhisperX config:
  - Watch folder: /path/to/smb/atlas/data/whisper_queue/audio
  - Output folder: /path/to/smb/atlas/data/whisper_queue/transcripts
  - Output format: JSON (WhisperX) or TXT (MacWhisper)
"""

import argparse
import json
import logging
import re
import subprocess
import time
from pathlib import Path
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.podcasts.store import PodcastStore

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def slugify(text: str, max_len: int = 50) -> str:
    """Convert text to filename-safe slug."""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s]+', '-', text)
    return text[:max_len].strip('-')


def download_audio(url: str, output_path: Path, timeout: int = 600) -> bool:
    """Download audio file."""
    try:
        cmd = [
            'curl', '-L', '-o', str(output_path),
            '--max-time', str(timeout),
            '--retry', '3',
            '--fail',
            '-H', 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
            url
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error(f"curl failed: {result.stderr[:200]}")
            return False

        if output_path.exists() and output_path.stat().st_size > 10000:
            return True

        output_path.unlink(missing_ok=True)
        return False

    except Exception as e:
        logger.error(f"Download error: {e}")
        return False


def load_whisper_config() -> list:
    """Load podcasts that need Whisper from config file."""
    config_path = Path(__file__).parent.parent / 'config' / 'whisper_podcasts.json'
    if not config_path.exists():
        logger.warning(f"Config not found: {config_path}")
        return []

    with open(config_path) as f:
        data = json.load(f)

    return [p['slug'] for p in data.get('podcasts', [])]


def main():
    parser = argparse.ArgumentParser(description='Download audio for Whisper')
    parser.add_argument('--output', '-o', default='data/whisper_queue/audio',
                        help='Output directory')
    parser.add_argument('--limit', '-l', type=int, default=10,
                        help='Number of episodes to download')
    parser.add_argument('--all', action='store_true',
                        help='Download all episodes')
    parser.add_argument('--dry-run', '-n', action='store_true',
                        help='Show what would be downloaded')
    parser.add_argument('--delay', '-d', type=float, default=2.0,
                        help='Delay between downloads (seconds)')
    parser.add_argument('--status', '-s', default='local',
                        help='Episode status to process (legacy mode)')
    parser.add_argument('--from-config', action='store_true',
                        help='Use config/whisper_podcasts.json to determine podcasts')
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Track what we've already downloaded
    downloaded_file = output_dir.parent / 'downloaded.json'
    downloaded_ids = set()
    if downloaded_file.exists():
        downloaded_ids = set(json.loads(downloaded_file.read_text()))

    store = PodcastStore()
    podcasts = store.list_podcasts()

    # Determine which podcasts to process
    if args.from_config:
        whisper_slugs = set(load_whisper_config())
        if not whisper_slugs:
            logger.error("No podcasts configured in config/whisper_podcasts.json")
            return
        logger.info(f"Using config: {len(whisper_slugs)} podcasts need Whisper")
        # Filter podcasts to only those in config
        podcasts = [p for p in podcasts if p.slug in whisper_slugs]
        # For config mode, look for unknown or failed episodes
        target_statuses = {'unknown', 'failed'}
    else:
        # Legacy mode: use --status flag
        target_statuses = {args.status}

    # Collect episodes to download
    to_download = []
    for podcast in podcasts:
        episodes = store.get_episodes_by_podcast(podcast.id)
        for ep in episodes:
            if ep.transcript_status in target_statuses and ep.id not in downloaded_ids:
                # Get audio URL from metadata or fall back to episode URL
                audio_url = ep.metadata.get('audio_url') or ep.metadata.get('enclosure_url') or ep.url
                if audio_url:
                    to_download.append((podcast, ep, audio_url))

    logger.info(f"Found {len(to_download)} episodes needing download")

    if not args.all:
        to_download = to_download[:args.limit]

    # Summary by podcast
    by_podcast = {}
    for podcast, ep, audio_url in to_download:
        by_podcast[podcast.slug] = by_podcast.get(podcast.slug, 0) + 1

    print(f"\nWill download {len(to_download)} episodes:")
    for slug, count in sorted(by_podcast.items(), key=lambda x: -x[1]):
        print(f"  {slug}: {count}")

    if args.dry_run:
        print("\n(Dry run - no files downloaded)")
        return

    # Download
    success = 0
    failed = 0

    for podcast, ep, audio_url in to_download:
        date_str = ep.publish_date[:10] if ep.publish_date else 'unknown'
        title_slug = slugify(ep.title)

        # Filename format: slug_id_date_title.mp3
        filename = f"{podcast.slug}_{ep.id}_{date_str}_{title_slug}.mp3"
        output_path = output_dir / filename

        if output_path.exists():
            logger.info(f"Already exists: {filename}")
            downloaded_ids.add(ep.id)
            continue

        logger.info(f"Downloading: {ep.title[:60]}...")
        logger.info(f"  URL: {audio_url}")

        if download_audio(audio_url, output_path):
            size_mb = output_path.stat().st_size / 1024 / 1024
            logger.info(f"  Success: {size_mb:.1f} MB")
            downloaded_ids.add(ep.id)
            success += 1
        else:
            logger.error(f"  Failed!")
            failed += 1

        # Save progress
        downloaded_file.write_text(json.dumps(list(downloaded_ids)))

        time.sleep(args.delay)

    print(f"\nDownload complete:")
    print(f"  Success: {success}")
    print(f"  Failed: {failed}")
    print(f"\nAudio files are in: {output_dir}")
    print("MacWhisper Pro will automatically transcribe them.")


if __name__ == '__main__':
    main()
