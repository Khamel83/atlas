#!/usr/bin/env python3
"""
Batch processor to retry failed URLs using the robust fetcher.

Usage:
    python scripts/retry_failed_urls.py --limit 100  # Process up to 100 URLs
    python scripts/retry_failed_urls.py --dry-run    # Show what would be processed
    python scripts/retry_failed_urls.py              # Process all failed URLs
"""

import argparse
import json
import logging
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.ingest.robust_fetcher import RobustFetcher, should_skip_url, EmailRedirectDecoder
from modules.storage.index_manager import IndexManager
from modules.storage.content_types import ProcessingStatus

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_failed_urls(db_path: str = "data/indexes/atlas_index.db") -> List[Dict[str, Any]]:
    """Get all failed URLs from the index."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    cursor = conn.execute('''
        SELECT content_id, source_url, title, content_type, file_path
        FROM content_index
        WHERE status = 'failed' AND source_url IS NOT NULL
        ORDER BY created_at DESC
    ''')

    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def categorize_urls(urls: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Categorize URLs by type for processing decisions."""
    categories = {
        'skip_patterns': [],      # Marketing, unsubscribe, social media
        'redirect_decode': [],     # Email tracking URLs to decode
        'retry_fetch': [],         # Regular URLs to retry with robust fetcher
        'image_urls': [],          # Raw image URLs
    }

    for item in urls:
        url = item['source_url']

        # Check for image URLs
        if any(ext in url.lower() for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
            if 's3.amazonaws.com' in url or 'cloudfront' in url:
                categories['image_urls'].append(item)
                continue

        # Check if should skip
        should_skip, reason = should_skip_url(url)
        if should_skip:
            item['skip_reason'] = reason
            categories['skip_patterns'].append(item)
            continue

        # Check for redirect URLs that need decoding
        decoded = EmailRedirectDecoder.decode(url)
        if decoded != url:
            item['decoded_url'] = decoded
            # Re-check if decoded URL should be skipped
            should_skip, reason = should_skip_url(decoded)
            if should_skip:
                item['skip_reason'] = reason
                categories['skip_patterns'].append(item)
            else:
                categories['redirect_decode'].append(item)
            continue

        # Regular URL to retry
        categories['retry_fetch'].append(item)

    return categories


def update_item_status(db_path: str, content_id: str, status: str, error: str = None):
    """Update the status of an item in the index."""
    conn = sqlite3.connect(db_path)
    if error:
        conn.execute('''
            UPDATE content_index
            SET status = ?, title = ?
            WHERE content_id = ?
        ''', (status, f"Error: {error[:100]}", content_id))
    else:
        conn.execute('''
            UPDATE content_index
            SET status = ?
            WHERE content_id = ?
        ''', (status, content_id))
    conn.commit()
    conn.close()


def process_batch(
    urls: List[Dict[str, Any]],
    fetcher: RobustFetcher,
    db_path: str,
    dry_run: bool = False
) -> Dict[str, int]:
    """Process a batch of URLs."""
    stats = {
        'processed': 0,
        'success': 0,
        'failed': 0,
        'skipped': 0,
    }

    for i, item in enumerate(urls, 1):
        url = item.get('decoded_url', item['source_url'])
        content_type = item['content_type']
        content_id = item['content_id']

        logger.info(f"[{i}/{len(urls)}] Processing: {url[:80]}...")

        if dry_run:
            logger.info(f"  [DRY RUN] Would process with robust fetcher")
            stats['processed'] += 1
            continue

        try:
            result = fetcher.fetch(url, content_type=content_type)

            if result.success:
                logger.info(f"  SUCCESS via {result.method}: {result.title[:60] if result.title else 'No title'}...")
                update_item_status(db_path, content_id, 'completed')
                stats['success'] += 1
            else:
                logger.info(f"  FAILED: {result.error}")
                # Keep as failed but update error message
                update_item_status(db_path, content_id, 'failed', result.error)
                stats['failed'] += 1

            stats['processed'] += 1

        except Exception as e:
            logger.error(f"  ERROR: {e}")
            update_item_status(db_path, content_id, 'failed', str(e))
            stats['failed'] += 1
            stats['processed'] += 1

    return stats


def main():
    parser = argparse.ArgumentParser(description='Retry failed URLs with robust fetcher')
    parser.add_argument('--limit', type=int, default=None, help='Limit number of URLs to process')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be processed without doing it')
    parser.add_argument('--analyze', action='store_true', help='Just analyze and categorize URLs')
    parser.add_argument('--skip-playwright', action='store_true', help='Skip Playwright browser-based fetching')
    parser.add_argument('--cookies', type=str, help='Path to cookies JSON file')
    args = parser.parse_args()

    db_path = "data/indexes/atlas_index.db"

    # Get failed URLs
    logger.info("Loading failed URLs from database...")
    failed_urls = get_failed_urls(db_path)
    logger.info(f"Found {len(failed_urls)} failed URLs")

    # Categorize
    logger.info("\nCategorizing URLs...")
    categories = categorize_urls(failed_urls)

    print("\n" + "="*60)
    print("URL ANALYSIS")
    print("="*60)
    print(f"Total failed URLs:        {len(failed_urls)}")
    print(f"  Skip (marketing/etc):   {len(categories['skip_patterns'])}")
    print(f"  Need redirect decode:   {len(categories['redirect_decode'])}")
    print(f"  Image URLs:             {len(categories['image_urls'])}")
    print(f"  Ready to retry:         {len(categories['retry_fetch'])}")
    print("="*60 + "\n")

    if args.analyze:
        # Show sample of each category
        for cat_name, cat_items in categories.items():
            if cat_items:
                print(f"\n--- {cat_name.upper()} (sample of 5) ---")
                for item in cat_items[:5]:
                    print(f"  {item['source_url'][:70]}...")
                    if 'skip_reason' in item:
                        print(f"    Reason: {item['skip_reason']}")
                    if 'decoded_url' in item:
                        print(f"    Decoded: {item['decoded_url'][:70]}...")
        return

    # Mark skip_patterns as permanently skipped
    if categories['skip_patterns']:
        logger.info(f"\nMarking {len(categories['skip_patterns'])} URLs as skipped...")
        if not args.dry_run:
            for item in categories['skip_patterns']:
                update_item_status(
                    db_path,
                    item['content_id'],
                    'failed',
                    f"Skipped: {item.get('skip_reason', 'Not content')}"
                )

    # Mark image URLs as skipped
    if categories['image_urls']:
        logger.info(f"\nMarking {len(categories['image_urls'])} image URLs as skipped...")
        if not args.dry_run:
            for item in categories['image_urls']:
                update_item_status(
                    db_path,
                    item['content_id'],
                    'failed',
                    'Skipped: Raw image URL'
                )

    # Combine redirect_decode and retry_fetch for processing
    to_process = categories['redirect_decode'] + categories['retry_fetch']

    if args.limit:
        to_process = to_process[:args.limit]

    if not to_process:
        logger.info("No URLs to process!")
        return

    logger.info(f"\nProcessing {len(to_process)} URLs...")

    # Initialize fetcher
    fetcher = RobustFetcher(
        output_base=Path("data/content"),
        cookies_path=Path(args.cookies) if args.cookies else None,
    )

    # Process
    stats = process_batch(to_process, fetcher, db_path, dry_run=args.dry_run)

    print("\n" + "="*60)
    print("PROCESSING RESULTS")
    print("="*60)
    print(f"Processed: {stats['processed']}")
    print(f"Success:   {stats['success']}")
    print(f"Failed:    {stats['failed']}")
    print(f"Skipped:   {stats['skipped']}")
    print("="*60)

    # Save summary
    summary = {
        'timestamp': datetime.now().isoformat(),
        'total_failed': len(failed_urls),
        'categories': {k: len(v) for k, v in categories.items()},
        'processed': stats,
    }

    summary_path = Path("data/content/retry_summary.json")
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)

    logger.info(f"\nSummary saved to {summary_path}")


if __name__ == '__main__':
    main()
