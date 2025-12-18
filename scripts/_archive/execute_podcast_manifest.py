#!/usr/bin/env python3
"""
Execute Podcast Manifest - Deterministic podcast transcript fetching.

Reads podcast_tasks.json and fetches transcripts using the pre-computed resolution strategy.
Saves progress after each episode (fully resumable).

Usage:
    python scripts/execute_podcast_manifest.py
    python scripts/execute_podcast_manifest.py --limit 100
    python scripts/execute_podcast_manifest.py --strategy whisper_local  # Only process specific strategy
    python scripts/execute_podcast_manifest.py --dry-run
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.podcasts.store import PodcastStore
from modules.podcasts.resolvers import get_all_resolvers

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Paths
ATLAS_ROOT = Path(__file__).parent.parent
MANIFEST_FILE = ATLAS_ROOT / "data/manifests/podcast_tasks.json"
COOKIES_DIR = Path(os.path.expanduser("~/.config/atlas/cookies"))
WHISPER_QUEUE_DIR = ATLAS_ROOT / "data/whisper_queue/audio"

# Rate limiting
DELAY_BETWEEN_EPISODES = 5  # seconds
YOUTUBE_DELAY = 15  # longer delay for YouTube to avoid rate limits


def load_manifest(path: Path) -> List[Dict[str, Any]]:
    """Load manifest from file."""
    with open(path) as f:
        return json.load(f)


def save_manifest(manifest: List[Dict[str, Any]], path: Path):
    """Save manifest to file (atomic write)."""
    temp_path = path.with_suffix('.tmp')
    with open(temp_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    temp_path.rename(path)


def execute_whisper_local(task: Dict[str, Any]) -> Dict[str, Any]:
    """Download audio for local Whisper transcription."""
    import subprocess
    import re

    audio_url = task.get('audio_url')
    if not audio_url:
        task['status'] = 'failed'
        task['error'] = 'No audio URL available'
        return task

    # Create filename
    slug = task['podcast_slug']
    episode_id = task['episode_id']
    date = task.get('published_date', '')[:10] or 'unknown'
    title_slug = re.sub(r'[^\w\s-]', '', task.get('episode_title', '')[:50]).strip().replace(' ', '_')
    filename = f"{slug}_{episode_id}_{date}_{title_slug}.mp3"

    output_path = WHISPER_QUEUE_DIR / filename

    if output_path.exists():
        task['status'] = 'queued_whisper'
        task['audio_path'] = str(output_path)
        logger.info(f"  Already downloaded: {filename}")
        return task

    # Download using yt-dlp or curl
    logger.info(f"  Downloading audio to: {filename}")

    try:
        # Try yt-dlp first (handles more formats)
        result = subprocess.run(
            ['yt-dlp', '-x', '--audio-format', 'mp3', '-o', str(output_path), audio_url],
            capture_output=True,
            text=True,
            timeout=300
        )

        if result.returncode != 0:
            # Fall back to curl
            result = subprocess.run(
                ['curl', '-L', '-o', str(output_path), audio_url],
                capture_output=True,
                text=True,
                timeout=300
            )

        if output_path.exists() and output_path.stat().st_size > 1000:
            task['status'] = 'queued_whisper'
            task['audio_path'] = str(output_path)
            logger.info(f"  Downloaded: {output_path.stat().st_size / 1024 / 1024:.1f} MB")
        else:
            task['status'] = 'failed'
            task['error'] = 'Download failed or file too small'

    except subprocess.TimeoutExpired:
        task['status'] = 'failed'
        task['error'] = 'Download timeout'
    except Exception as e:
        task['status'] = 'failed'
        task['error'] = str(e)

    return task


def execute_resolver_chain(task: Dict[str, Any], store: PodcastStore, resolvers: dict) -> Dict[str, Any]:
    """Try resolvers in order until one succeeds."""
    episode_id = task['episode_id']
    resolvers_to_try = task.get('resolvers_to_try', [])

    # Get episode from database
    episode = store.get_episode(episode_id)
    if not episode:
        task['status'] = 'failed'
        task['error'] = 'Episode not found in database'
        return task

    # Try each resolver
    for resolver_name in resolvers_to_try:
        if resolver_name.startswith('download_') or resolver_name == 'whisper_local':
            continue  # These are handled separately

        resolver = resolvers.get(resolver_name)
        if not resolver:
            logger.warning(f"  Unknown resolver: {resolver_name}")
            continue

        logger.info(f"  Trying resolver: {resolver_name}")

        try:
            result = resolver.fetch(episode)
            if result and result.get('content'):
                # Save transcript
                transcript_path = store.save_transcript(episode_id, result['content'])
                task['status'] = 'fetched'
                task['fetched_at'] = datetime.now().isoformat()
                task['fetched_via'] = resolver_name
                task['transcript_path'] = transcript_path
                logger.info(f"  SUCCESS via {resolver_name}")
                return task

        except Exception as e:
            logger.warning(f"  {resolver_name} failed: {e}")
            continue

    # All resolvers failed
    task['status'] = 'failed'
    task['error'] = f'All resolvers failed: {resolvers_to_try}'
    return task


def execute_task(task: Dict[str, Any], store: PodcastStore, resolvers: dict, dry_run: bool = False) -> Dict[str, Any]:
    """Execute a single podcast transcript task."""
    strategy = task['resolution_strategy']

    if dry_run:
        logger.info(f"[DRY RUN] Would process: {task['podcast_slug']} - {task['episode_title'][:50]}...")
        logger.info(f"  Strategy: {strategy}")
        task['status'] = 'dry_run'
        return task

    logger.info(f"Processing: {task['podcast_slug']} - {task['episode_title'][:50]}...")
    logger.info(f"  Strategy: {strategy}")

    if strategy == 'whisper_local':
        return execute_whisper_local(task)
    else:
        return execute_resolver_chain(task, store, resolvers)


def print_progress(manifest: List[Dict[str, Any]]):
    """Print current progress summary."""
    total = len(manifest)
    pending = sum(1 for t in manifest if t['status'] == 'pending')
    fetched = sum(1 for t in manifest if t['status'] == 'fetched')
    queued_whisper = sum(1 for t in manifest if t['status'] == 'queued_whisper')
    failed = sum(1 for t in manifest if t['status'] == 'failed')

    print(f"\n=== Progress ===")
    print(f"Total:          {total}")
    print(f"Pending:        {pending} ({100*pending/total:.1f}%)")
    print(f"Fetched:        {fetched} ({100*fetched/total:.1f}%)")
    print(f"Queued Whisper: {queued_whisper} ({100*queued_whisper/total:.1f}%)")
    print(f"Failed:         {failed} ({100*failed/total:.1f}%)")

    # By strategy
    from collections import Counter
    strategies = Counter(t['resolution_strategy'] for t in manifest if t['status'] == 'pending')
    if strategies:
        print(f"\nPending by strategy:")
        for strategy, count in strategies.most_common():
            print(f"  {strategy}: {count}")


def main():
    parser = argparse.ArgumentParser(description='Execute podcast manifest')
    parser.add_argument('--manifest', '-m', type=str, default=str(MANIFEST_FILE),
                       help='Manifest file path')
    parser.add_argument('--limit', '-l', type=int, default=0,
                       help='Limit number of episodes to process (0=all)')
    parser.add_argument('--strategy', '-s', type=str, default=None,
                       help='Only process specific strategy')
    parser.add_argument('--delay', '-d', type=int, default=DELAY_BETWEEN_EPISODES,
                       help='Delay between episodes in seconds')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without fetching')
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        logger.error(f"Manifest not found: {manifest_path}")
        logger.error("Run: python scripts/generate_podcast_manifest.py first")
        sys.exit(1)

    # Ensure whisper queue directory exists
    WHISPER_QUEUE_DIR.mkdir(parents=True, exist_ok=True)

    # Load manifest
    logger.info(f"Loading manifest: {manifest_path}")
    manifest = load_manifest(manifest_path)
    logger.info(f"Loaded {len(manifest)} tasks")

    # Filter to pending tasks
    pending_tasks = [t for t in manifest if t['status'] == 'pending']

    if args.strategy:
        pending_tasks = [t for t in pending_tasks if t['resolution_strategy'] == args.strategy]
        logger.info(f"Filtered to strategy: {args.strategy}")

    logger.info(f"Pending tasks: {len(pending_tasks)}")

    if args.limit > 0:
        pending_tasks = pending_tasks[:args.limit]
        logger.info(f"Limited to {args.limit} tasks")

    if not pending_tasks:
        logger.info("No pending tasks to process")
        print_progress(manifest)
        return

    # Initialize store and resolvers
    store = PodcastStore()
    resolvers = {r.name: r for r in get_all_resolvers()}
    logger.info(f"Available resolvers: {list(resolvers.keys())}")

    # Process tasks
    for i, task in enumerate(pending_tasks):
        task_index = manifest.index(task)

        logger.info(f"\n[{i+1}/{len(pending_tasks)}] Processing {task['id']}")

        # Execute task
        updated_task = execute_task(task, store, resolvers, dry_run=args.dry_run)

        # Update manifest in place
        manifest[task_index] = updated_task

        # Save after each task (resumable)
        if not args.dry_run:
            save_manifest(manifest, manifest_path)

        # Rate limit
        if i < len(pending_tasks) - 1 and not args.dry_run:
            delay = YOUTUBE_DELAY if 'youtube' in str(task.get('resolvers_to_try', [])) else args.delay
            logger.info(f"  Waiting {delay}s...")
            time.sleep(delay)

    # Final summary
    print_progress(manifest)

    if not args.dry_run:
        logger.info(f"\nManifest saved to: {manifest_path}")


if __name__ == '__main__':
    main()
