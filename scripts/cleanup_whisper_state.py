#!/usr/bin/env python3
"""
Clean up whisper state files (processed.json, downloaded.json).

Removes stale IDs that don't exist in database or have incorrect status.
"""

import argparse
import json
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.podcasts.store import PodcastStore

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def cleanup_state_files(queue_dir: Path, dry_run: bool = True):
    """Clean up processed.json and downloaded.json state files."""
    
    store = PodcastStore()
    
    processed_file = queue_dir / 'processed.json'
    downloaded_file = queue_dir / 'downloaded.json'
    
    # Load state files
    processed_ids = set()
    downloaded_ids = set()
    
    if processed_file.exists():
        processed_ids = set(json.loads(processed_file.read_text()))
    if downloaded_file.exists():
        downloaded_ids = set(json.loads(downloaded_file.read_text()))
    
    print(f"Current state:")
    print(f"  processed.json: {len(processed_ids)} IDs")
    print(f"  downloaded.json: {len(downloaded_ids)} IDs")
    
    # Get valid episode IDs from database
    with store._get_connection() as conn:
        # Episodes that are actually fetched
        fetched_rows = conn.execute(
            "SELECT id FROM episodes WHERE transcript_status = 'fetched'"
        ).fetchall()
        fetched_ids = {row["id"] for row in fetched_rows}
        
        # All episode IDs
        all_rows = conn.execute("SELECT id FROM episodes").fetchall()
        all_ids = {row["id"] for row in all_rows}
    
    print(f"\nDatabase:")
    print(f"  Total episodes: {len(all_ids)}")
    print(f"  Fetched episodes: {len(fetched_ids)}")
    
    # Find stale IDs
    stale_processed = processed_ids - fetched_ids
    stale_downloaded = downloaded_ids - all_ids
    
    print(f"\nStale IDs to remove:")
    print(f"  processed.json: {len(stale_processed)} (not in 'fetched' status)")
    print(f"  downloaded.json: {len(stale_downloaded)} (not in database)")
    
    if dry_run:
        print("\n(Dry run - no changes made)")
        return
    
    # Clean up processed.json
    if stale_processed:
        new_processed = processed_ids - stale_processed
        processed_file.write_text(json.dumps(list(new_processed)))
        logger.info(f"Cleaned processed.json: {len(processed_ids)} -> {len(new_processed)}")
    
    # Clean up downloaded.json
    if stale_downloaded:
        new_downloaded = downloaded_ids - stale_downloaded
        downloaded_file.write_text(json.dumps(list(new_downloaded)))
        logger.info(f"Cleaned downloaded.json: {len(downloaded_ids)} -> {len(new_downloaded)}")
    
    print(f"\nCleaned up {len(stale_processed) + len(stale_downloaded)} stale IDs")


def main():
    parser = argparse.ArgumentParser(description='Clean up whisper state files')
    parser.add_argument('--queue-dir', default='data/whisper_queue', help='Queue directory')
    parser.add_argument('--fix', action='store_true', help='Actually apply fixes')
    args = parser.parse_args()
    
    cleanup_state_files(Path(args.queue_dir), dry_run=not args.fix)


if __name__ == '__main__':
    main()
