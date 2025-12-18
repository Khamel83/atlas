#!/usr/bin/env python3
"""
Execute URL Manifest - Deterministic URL fetching from static manifest.

Reads url_tasks.json and fetches each URL using the pre-computed fallback chain.
Saves progress after each URL (fully resumable).

Usage:
    python scripts/execute_url_manifest.py
    python scripts/execute_url_manifest.py --limit 100
    python scripts/execute_url_manifest.py --dry-run
    python scripts/execute_url_manifest.py --skip-failed  # Skip previously failed URLs
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

from modules.ingest.robust_fetcher import RobustFetcher

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Paths
ATLAS_ROOT = Path(__file__).parent.parent
MANIFEST_FILE = ATLAS_ROOT / "data/manifests/url_tasks.json"
COOKIES_DIR = Path(os.path.expanduser("~/.config/atlas/cookies"))

# Rate limiting
DELAY_BETWEEN_URLS = 10  # seconds


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


def get_cookies_for_domain(domain: str) -> Optional[Path]:
    """Get cookie file for domain if available."""
    if not COOKIES_DIR.exists():
        return None

    # Try exact match
    cookie_file = COOKIES_DIR / f"{domain}.json"
    if cookie_file.exists():
        return cookie_file

    # Try without subdomain
    parts = domain.split('.')
    if len(parts) > 2:
        base_domain = '.'.join(parts[-2:])
        cookie_file = COOKIES_DIR / f"{base_domain}.json"
        if cookie_file.exists():
            return cookie_file

    return None


def execute_task(task: Dict[str, Any], fetcher: RobustFetcher, dry_run: bool = False) -> Dict[str, Any]:
    """Execute a single URL fetch task."""
    url = task['url']
    domain = task['domain']
    fallback_chain = task['fallback_chain']

    if dry_run:
        logger.info(f"[DRY RUN] Would fetch: {url[:80]}...")
        task['status'] = 'dry_run'
        return task

    logger.info(f"Fetching: {url[:80]}...")
    logger.info(f"  Fallback chain: {fallback_chain}")

    # Check for cookies
    cookie_file = get_cookies_for_domain(domain)
    if cookie_file:
        logger.info(f"  Using cookies from: {cookie_file.name}")

    # Try fetching with robust_fetcher
    try:
        result = fetcher.fetch(url)

        if result and result.get('content_path'):
            task['status'] = 'fetched'
            task['fetched_at'] = datetime.now().isoformat()
            task['fetched_via'] = result.get('method', 'unknown')
            task['content_path'] = result.get('content_path')
            task['title'] = result.get('title', '')[:100]
            logger.info(f"  SUCCESS via {task['fetched_via']}: {task.get('title', '')[:50]}...")
        else:
            task['status'] = 'failed'
            task['error'] = result.get('error') if result else 'No content returned'
            logger.warning(f"  FAILED: {task['error']}")

    except Exception as e:
        task['status'] = 'failed'
        task['error'] = str(e)
        logger.error(f"  ERROR: {e}")

    return task


def print_progress(manifest: List[Dict[str, Any]]):
    """Print current progress summary."""
    total = len(manifest)
    pending = sum(1 for t in manifest if t['status'] == 'pending')
    fetched = sum(1 for t in manifest if t['status'] == 'fetched')
    failed = sum(1 for t in manifest if t['status'] == 'failed')

    print(f"\n=== Progress ===")
    print(f"Total:   {total}")
    print(f"Pending: {pending} ({100*pending/total:.1f}%)")
    print(f"Fetched: {fetched} ({100*fetched/total:.1f}%)")
    print(f"Failed:  {failed} ({100*failed/total:.1f}%)")

    if fetched > 0:
        # Success rate
        attempted = fetched + failed
        success_rate = 100 * fetched / attempted if attempted > 0 else 0
        print(f"Success rate: {success_rate:.1f}%")


def main():
    parser = argparse.ArgumentParser(description='Execute URL manifest')
    parser.add_argument('--manifest', '-m', type=str, default=str(MANIFEST_FILE),
                       help='Manifest file path')
    parser.add_argument('--limit', '-l', type=int, default=0,
                       help='Limit number of URLs to process (0=all)')
    parser.add_argument('--delay', '-d', type=int, default=DELAY_BETWEEN_URLS,
                       help='Delay between URLs in seconds')
    parser.add_argument('--skip-failed', action='store_true',
                       help='Skip URLs that previously failed')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without fetching')
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        logger.error(f"Manifest not found: {manifest_path}")
        logger.error("Run: python scripts/generate_url_manifest.py first")
        sys.exit(1)

    # Load manifest
    logger.info(f"Loading manifest: {manifest_path}")
    manifest = load_manifest(manifest_path)
    logger.info(f"Loaded {len(manifest)} tasks")

    # Filter to pending tasks
    pending_tasks = [t for t in manifest if t['status'] == 'pending']

    if args.skip_failed:
        pending_tasks = [t for t in pending_tasks if not t.get('previously_failed')]
        logger.info(f"Skipping previously failed URLs")

    logger.info(f"Pending tasks: {len(pending_tasks)}")

    if args.limit > 0:
        pending_tasks = pending_tasks[:args.limit]
        logger.info(f"Limited to {args.limit} tasks")

    if not pending_tasks:
        logger.info("No pending tasks to process")
        print_progress(manifest)
        return

    # Initialize fetcher
    fetcher = RobustFetcher()

    # Process tasks
    processed = 0
    for i, task in enumerate(pending_tasks):
        task_index = manifest.index(task)

        logger.info(f"\n[{i+1}/{len(pending_tasks)}] Processing {task['id']}")

        # Execute task
        updated_task = execute_task(task, fetcher, dry_run=args.dry_run)

        # Update manifest in place
        manifest[task_index] = updated_task

        # Save after each task (resumable)
        if not args.dry_run:
            save_manifest(manifest, manifest_path)

        processed += 1

        # Rate limit
        if i < len(pending_tasks) - 1 and not args.dry_run:
            logger.info(f"  Waiting {args.delay}s...")
            time.sleep(args.delay)

    # Final summary
    print_progress(manifest)

    if not args.dry_run:
        logger.info(f"\nManifest saved to: {manifest_path}")


if __name__ == '__main__':
    main()
