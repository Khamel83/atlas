#!/usr/bin/env python3
"""
Backfill episode metadata from RSS feeds.

Goes through ALL podcasts and updates episode metadata (description, duration,
audio_url) from the current RSS feed. This enriches episodes regardless of
how they were originally discovered or transcribed.

Usage:
    python scripts/backfill_episode_metadata.py
    python scripts/backfill_episode_metadata.py --dry-run
    python scripts/backfill_episode_metadata.py --slug acquired
"""

import argparse
import json
import logging
import sqlite3
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.podcasts.store import PodcastStore
from modules.podcasts.rss import RSSParser

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def backfill_metadata(slug: str = None, dry_run: bool = False):
    """Backfill metadata for all episodes from RSS feeds."""

    db_path = Path('data/podcasts/atlas_podcasts.db')
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    parser = RSSParser()

    # Get podcasts to process
    if slug:
        cursor = conn.execute("SELECT * FROM podcasts WHERE slug = ?", (slug,))
    else:
        cursor = conn.execute("SELECT * FROM podcasts")

    podcasts = cursor.fetchall()
    logger.info(f"Processing {len(podcasts)} podcasts")

    total_updated = 0
    total_skipped = 0

    for podcast in podcasts:
        podcast_id = podcast['id']
        podcast_slug = podcast['slug']
        rss_url = podcast['rss_url']

        if not rss_url:
            logger.warning(f"No RSS URL for {podcast_slug}, skipping")
            continue

        # Fetch fresh RSS
        try:
            rss_episodes = parser.parse_feed(rss_url)
        except Exception as e:
            logger.error(f"Failed to parse RSS for {podcast_slug}: {e}")
            continue

        # Build lookup by GUID
        rss_by_guid = {ep.guid: ep for ep in rss_episodes}

        # Get relevant episodes only (skip excluded)
        ep_cursor = conn.execute(
            "SELECT id, guid, metadata FROM episodes WHERE podcast_id = ? AND transcript_status != 'excluded'",
            (podcast_id,)
        )

        updated = 0
        skipped = 0

        for row in ep_cursor.fetchall():
            ep_id = row['id']
            guid = row['guid']
            current_metadata = json.loads(row['metadata']) if row['metadata'] else {}

            if guid not in rss_by_guid:
                skipped += 1
                continue

            rss_ep = rss_by_guid[guid]

            # Build new metadata
            new_metadata = {
                'description': rss_ep.description or current_metadata.get('description', ''),
                'duration': rss_ep.duration or current_metadata.get('duration', ''),
                'audio_url': rss_ep.audio_url or current_metadata.get('audio_url', ''),
                'transcript_links': rss_ep.transcript_links or current_metadata.get('transcript_links', []),
            }

            # Preserve any existing metadata fields we don't want to overwrite
            for key in current_metadata:
                if key not in new_metadata:
                    new_metadata[key] = current_metadata[key]

            if not dry_run:
                conn.execute(
                    "UPDATE episodes SET metadata = ? WHERE id = ?",
                    (json.dumps(new_metadata), ep_id)
                )
            updated += 1

        if not dry_run:
            conn.commit()

        logger.info(f"{podcast_slug}: updated {updated}, skipped {skipped} (not in RSS)")
        total_updated += updated
        total_skipped += skipped

    conn.close()

    print(f"\n{'DRY RUN: ' if dry_run else ''}Metadata backfill complete")
    print(f"  Updated: {total_updated}")
    print(f"  Skipped: {total_skipped} (not in current RSS feed)")


def main():
    parser = argparse.ArgumentParser(description='Backfill episode metadata from RSS')
    parser.add_argument('--slug', '-s', help='Process only this podcast')
    parser.add_argument('--dry-run', '-n', action='store_true', help='Show what would be done')
    args = parser.parse_args()

    backfill_metadata(args.slug, args.dry_run)


if __name__ == '__main__':
    main()
