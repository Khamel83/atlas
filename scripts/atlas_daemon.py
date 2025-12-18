#!/usr/bin/env python3
"""
Atlas Daemon - Master executor for all content ingestion.

Runs continuously as a systemd service, processing tasks from the master manifest.
Designed to run for weeks, fully resumable, atomic saves after each task.

Task types:
- url: Fetch URL content using robust_fetcher
- podcast: Fetch podcast transcript using resolvers
- daringfireball: Fetch DF article
- asianometry: Fetch Asianometry article with cookies
- dithering: Fetch Dithering show notes with cookies

Usage:
    python scripts/atlas_daemon.py                  # Run continuously
    python scripts/atlas_daemon.py --once           # Process one task and exit
    python scripts/atlas_daemon.py --limit 50       # Process 50 tasks and exit
    python scripts/atlas_daemon.py --type url       # Only process URL tasks
    python scripts/atlas_daemon.py --status         # Show current status
    python scripts/atlas_daemon.py --merge          # Merge all manifests into master

Features:
    - Atomic saves after each task (crash-safe)
    - Auto-restarts via systemd
    - Rate limiting (configurable delay)
    - ntfy alerts on completion/errors
    - Progress tracking in manifest
"""

import argparse
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/tmp/atlas-daemon.log')
    ]
)
logger = logging.getLogger(__name__)

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Paths
ATLAS_ROOT = Path(__file__).parent.parent
MASTER_MANIFEST = ATLAS_ROOT / "data/manifests/master_tasks.json"
MANIFESTS_DIR = ATLAS_ROOT / "data/manifests"

# Rate limiting
DEFAULT_DELAY = 10  # seconds between tasks
YOUTUBE_DELAY = 15  # longer for YouTube
ARCHIVE_DELAY = 5   # shorter for local crawlers

# ntfy alerts (minimal - only completion and critical errors)
NTFY_TOPIC = os.environ.get('ATLAS_NTFY_TOPIC', 'atlas-khamel-alerts')
NTFY_ENABLED = os.environ.get('ATLAS_NTFY_ENABLED', 'false').lower() == 'true'

# Graceful shutdown
shutdown_requested = False


def signal_handler(signum, frame):
    global shutdown_requested
    logger.info("Shutdown signal received, finishing current task...")
    shutdown_requested = True


signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


def load_manifest(path: Path) -> List[Dict[str, Any]]:
    """Load manifest from file."""
    if not path.exists():
        return []
    with open(path) as f:
        return json.load(f)


def save_manifest(manifest: List[Dict[str, Any]], path: Path):
    """Save manifest to file (atomic write)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix('.tmp')
    with open(temp_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    temp_path.rename(path)


def send_ntfy(title: str, message: str, priority: str = 'default'):
    """Send ntfy notification."""
    if not NTFY_ENABLED:
        return

    try:
        import requests
        requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=message.encode('utf-8'),
            headers={
                'Title': title,
                'Priority': priority,
            },
            timeout=10
        )
    except Exception as e:
        logger.warning(f"Failed to send ntfy: {e}")


def execute_url_task(task: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a URL fetch task."""
    from modules.ingest.robust_fetcher import RobustFetcher

    url = task['url']
    fetcher = RobustFetcher()

    try:
        result = fetcher.fetch(url)

        if result and result.success:
            task['status'] = 'fetched'
            task['fetched_at'] = datetime.now().isoformat()
            task['fetched_via'] = result.method or 'unknown'
            task['content_path'] = str(result.output_dir) if result.output_dir else None
            task['title'] = result.title
            logger.info(f"  SUCCESS via {task['fetched_via']}")
        else:
            task['status'] = 'failed'
            task['error'] = result.error if result else 'No content returned'
            logger.warning(f"  FAILED: {task['error']}")

    except Exception as e:
        task['status'] = 'failed'
        task['error'] = str(e)
        logger.error(f"  ERROR: {e}")

    return task


def execute_podcast_task(task: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a podcast transcript fetch task."""
    from modules.podcasts.store import PodcastStore
    from modules.podcasts.resolvers import get_all_resolvers

    store = PodcastStore()
    resolvers = {r.name: r for r in get_all_resolvers()}

    episode_id = task['episode_id']
    episode = store.get_episode(episode_id)

    if not episode:
        task['status'] = 'failed'
        task['error'] = 'Episode not found in database'
        return task

    strategy = task.get('resolution_strategy', 'retry_resolvers')

    # Handle whisper_local separately
    if strategy == 'whisper_local':
        from scripts.execute_podcast_manifest import execute_whisper_local
        return execute_whisper_local(task)

    # Try resolvers
    resolvers_to_try = task.get('resolvers_to_try', ['podscripts', 'generic_html', 'youtube_transcript'])

    for resolver_name in resolvers_to_try:
        if resolver_name.startswith('download_') or resolver_name == 'whisper_local':
            continue

        resolver = resolvers.get(resolver_name)
        if not resolver:
            continue

        logger.info(f"  Trying resolver: {resolver_name}")

        try:
            result = resolver.fetch(episode)
            if result and result.get('content'):
                transcript_path = store.save_transcript(episode_id, result['content'])
                task['status'] = 'fetched'
                task['fetched_at'] = datetime.now().isoformat()
                task['fetched_via'] = resolver_name
                task['transcript_path'] = transcript_path
                logger.info(f"  SUCCESS via {resolver_name}")
                return task
        except Exception as e:
            logger.warning(f"  {resolver_name} failed: {e}")

    task['status'] = 'failed'
    task['error'] = f'All resolvers failed: {resolvers_to_try}'
    return task


def execute_daringfireball_task(task: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a Daring Fireball fetch task."""
    from scripts.crawl_daringfireball import fetch_article, save_article

    url = task['url']

    try:
        result = fetch_article(url)

        if result.get('error'):
            task['status'] = 'failed'
            task['error'] = result['error']
            logger.warning(f"  FAILED: {result['error']}")
        else:
            content_path = save_article(task, result)
            task['status'] = 'fetched'
            task['fetched_at'] = datetime.now().isoformat()
            task['content_path'] = content_path
            logger.info(f"  SUCCESS: {content_path}")

    except Exception as e:
        task['status'] = 'failed'
        task['error'] = str(e)
        logger.error(f"  ERROR: {e}")

    return task


def execute_asianometry_task(task: Dict[str, Any]) -> Dict[str, Any]:
    """Execute an Asianometry fetch task."""
    from scripts.crawl_asianometry import fetch_article, save_article, get_session_with_cookies

    session = get_session_with_cookies()
    url = task['url']

    try:
        result = fetch_article(session, url)

        if result.get('error'):
            task['status'] = 'failed'
            task['error'] = result['error']
            logger.warning(f"  FAILED: {result['error']}")
        else:
            content_path = save_article(task, result)
            task['status'] = 'fetched'
            task['fetched_at'] = datetime.now().isoformat()
            task['content_path'] = content_path
            logger.info(f"  SUCCESS: {content_path}")

    except Exception as e:
        task['status'] = 'failed'
        task['error'] = str(e)
        logger.error(f"  ERROR: {e}")

    return task


def execute_dithering_task(task: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a Dithering fetch task."""
    from scripts.crawl_dithering import (
        fetch_episode, save_show_notes, add_urls_to_queue,
        queue_audio_for_whisper, get_session_with_cookies
    )

    session = get_session_with_cookies()
    url = task['url']

    try:
        result = fetch_episode(session, url)

        if result.get('error'):
            task['status'] = 'failed'
            task['error'] = result['error']
            logger.warning(f"  FAILED: {result['error']}")

            # If paywall, mark specially
            if result.get('is_paywall'):
                task['status'] = 'paywall'

        else:
            show_notes_path = save_show_notes(task, result)
            task['status'] = 'fetched'
            task['fetched_at'] = datetime.now().isoformat()
            task['show_notes_path'] = show_notes_path

            # Extract URLs
            urls = result.get('urls', [])
            if urls:
                added = add_urls_to_queue(urls, task['url_hash'])
                task['urls_extracted'] = added
                logger.info(f"  Added {added} URLs to queue")

            # Queue audio
            if result.get('audio_url'):
                audio_queued = queue_audio_for_whisper(task, result['audio_url'])
                task['audio_queued'] = audio_queued

            logger.info(f"  SUCCESS: {show_notes_path}")

    except Exception as e:
        task['status'] = 'failed'
        task['error'] = str(e)
        logger.error(f"  ERROR: {e}")

    return task


def execute_task(task: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a single task based on its type."""
    task_type = task.get('type', 'url')

    logger.info(f"Processing [{task_type}] {task.get('id', 'unknown')}: {task.get('url', task.get('episode_title', ''))[:60]}...")

    if task_type == 'url':
        return execute_url_task(task)
    elif task_type == 'podcast':
        return execute_podcast_task(task)
    elif task_type == 'daringfireball':
        return execute_daringfireball_task(task)
    elif task_type == 'asianometry':
        return execute_asianometry_task(task)
    elif task_type == 'dithering':
        return execute_dithering_task(task)
    else:
        task['status'] = 'failed'
        task['error'] = f'Unknown task type: {task_type}'
        return task


def get_delay_for_task(task: Dict[str, Any]) -> int:
    """Get appropriate delay for task type."""
    task_type = task.get('type', 'url')

    if task_type in ('daringfireball', 'asianometry', 'dithering'):
        return ARCHIVE_DELAY
    elif 'youtube' in str(task.get('resolvers_to_try', [])):
        return YOUTUBE_DELAY
    else:
        return DEFAULT_DELAY


def merge_manifests():
    """Merge all individual manifests into master manifest."""
    logger.info("Merging manifests into master...")

    all_tasks = []
    task_id = 0

    # URL manifest
    url_manifest = load_manifest(MANIFESTS_DIR / "url_tasks.json")
    for task in url_manifest:
        task['type'] = 'url'
        task['master_id'] = f'master-{task_id:06d}'
        task_id += 1
        all_tasks.append(task)
    logger.info(f"  URL tasks: {len(url_manifest)}")

    # Podcast manifest
    podcast_manifest = load_manifest(MANIFESTS_DIR / "podcast_tasks.json")
    for task in podcast_manifest:
        task['type'] = 'podcast'
        task['master_id'] = f'master-{task_id:06d}'
        task_id += 1
        all_tasks.append(task)
    logger.info(f"  Podcast tasks: {len(podcast_manifest)}")

    # Daring Fireball manifest
    df_manifest = load_manifest(MANIFESTS_DIR / "daringfireball_tasks.json")
    for task in df_manifest:
        task['type'] = 'daringfireball'
        task['master_id'] = f'master-{task_id:06d}'
        task_id += 1
        all_tasks.append(task)
    logger.info(f"  Daring Fireball tasks: {len(df_manifest)}")

    # Asianometry manifest
    asian_manifest = load_manifest(MANIFESTS_DIR / "asianometry_tasks.json")
    for task in asian_manifest:
        task['type'] = 'asianometry'
        task['master_id'] = f'master-{task_id:06d}'
        task_id += 1
        all_tasks.append(task)
    logger.info(f"  Asianometry tasks: {len(asian_manifest)}")

    # Dithering manifest
    dith_manifest = load_manifest(MANIFESTS_DIR / "dithering_tasks.json")
    for task in dith_manifest:
        task['type'] = 'dithering'
        task['master_id'] = f'master-{task_id:06d}'
        task_id += 1
        all_tasks.append(task)
    logger.info(f"  Dithering tasks: {len(dith_manifest)}")

    save_manifest(all_tasks, MASTER_MANIFEST)

    # Stats
    pending = sum(1 for t in all_tasks if t['status'] == 'pending')
    fetched = sum(1 for t in all_tasks if t['status'] == 'fetched')
    failed = sum(1 for t in all_tasks if t['status'] == 'failed')

    print(f"\n=== Master Manifest ===")
    print(f"Total tasks: {len(all_tasks)}")
    print(f"Pending:     {pending}")
    print(f"Fetched:     {fetched}")
    print(f"Failed:      {failed}")
    print(f"\nSaved to: {MASTER_MANIFEST}")


def print_status():
    """Print current daemon status."""
    manifest = load_manifest(MASTER_MANIFEST)

    if not manifest:
        print("No master manifest found. Run with --merge first.")
        return

    total = len(manifest)
    pending = sum(1 for t in manifest if t['status'] == 'pending')
    fetched = sum(1 for t in manifest if t['status'] == 'fetched')
    failed = sum(1 for t in manifest if t['status'] == 'failed')
    queued = sum(1 for t in manifest if t['status'] == 'queued_whisper')

    print(f"\n=== Atlas Daemon Status ===")
    print(f"Total:          {total}")
    print(f"Pending:        {pending} ({100*pending/total:.1f}%)")
    print(f"Fetched:        {fetched} ({100*fetched/total:.1f}%)")
    print(f"Failed:         {failed} ({100*failed/total:.1f}%)")
    print(f"Whisper Queue:  {queued}")

    # By type
    from collections import Counter
    types = Counter(t.get('type', 'url') for t in manifest if t['status'] == 'pending')
    if types:
        print(f"\nPending by type:")
        for task_type, count in types.most_common():
            print(f"  {task_type}: {count}")

    # Estimate time
    avg_time = DEFAULT_DELAY + 3
    remaining_seconds = pending * avg_time
    remaining_hours = remaining_seconds / 3600
    remaining_days = remaining_hours / 24
    print(f"\nEstimated time remaining: {remaining_days:.1f} days ({remaining_hours:.0f} hours)")


def run_daemon(limit: int = 0, task_type: Optional[str] = None, once: bool = False):
    """Run the daemon, processing tasks continuously."""
    global shutdown_requested

    manifest = load_manifest(MASTER_MANIFEST)

    if not manifest:
        logger.error("No master manifest found. Run with --merge first.")
        return

    # Filter to pending
    pending = [t for t in manifest if t['status'] == 'pending']

    if task_type:
        pending = [t for t in pending if t.get('type') == task_type]
        logger.info(f"Filtered to type: {task_type}")

    if limit > 0:
        pending = pending[:limit]

    logger.info(f"Starting daemon with {len(pending)} pending tasks")

    processed = 0
    start_time = datetime.now()

    for task in pending:
        if shutdown_requested:
            logger.info("Shutdown requested, stopping gracefully")
            break

        task_index = next(j for j, t in enumerate(manifest) if t.get('master_id') == task.get('master_id') or t.get('id') == task.get('id'))

        # Execute task
        updated_task = execute_task(task)

        # Update manifest
        manifest[task_index] = updated_task

        # Atomic save
        save_manifest(manifest, MASTER_MANIFEST)

        processed += 1

        # Check if done
        if once:
            logger.info("Single task mode, exiting")
            break

        # Rate limit
        delay = get_delay_for_task(task)
        logger.debug(f"Waiting {delay}s...")
        time.sleep(delay)

    # Summary
    elapsed = (datetime.now() - start_time).total_seconds()
    rate = processed / elapsed * 3600 if elapsed > 0 else 0

    logger.info(f"\nProcessed {processed} tasks in {elapsed/60:.1f} minutes ({rate:.0f} tasks/hour)")

    # Alert on completion if significant
    remaining = sum(1 for t in manifest if t['status'] == 'pending')
    if remaining == 0:
        send_ntfy(
            "Atlas Daemon Complete",
            f"All {len(manifest)} tasks processed!",
            priority='high'
        )
    elif processed >= 100:
        send_ntfy(
            "Atlas Daemon Progress",
            f"Processed {processed} tasks. {remaining} remaining.",
            priority='low'
        )


def main():
    parser = argparse.ArgumentParser(description='Atlas master daemon')
    parser.add_argument('--merge', action='store_true',
                       help='Merge all manifests into master')
    parser.add_argument('--status', action='store_true',
                       help='Show current status')
    parser.add_argument('--once', action='store_true',
                       help='Process one task and exit')
    parser.add_argument('--limit', '-l', type=int, default=0,
                       help='Limit number of tasks to process')
    parser.add_argument('--type', '-t', type=str, default=None,
                       choices=['url', 'podcast', 'daringfireball', 'asianometry', 'dithering'],
                       help='Only process specific task type')
    args = parser.parse_args()

    if args.merge:
        merge_manifests()
    elif args.status:
        print_status()
    else:
        run_daemon(limit=args.limit, task_type=args.type, once=args.once)


if __name__ == '__main__':
    main()
