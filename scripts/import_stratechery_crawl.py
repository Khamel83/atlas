#!/usr/bin/env python3
"""
Import Stratechery crawled content into the podcast database.

Reads crawled articles from data/stratechery/articles/ and matches
them to pending Stratechery episodes by URL.
"""

import argparse
import logging
import re
import shutil
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.podcasts.store import PodcastStore

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def normalize_url(url: str) -> str:
    """Normalize URL for matching (remove tokens, trailing slashes)."""
    # Remove access_token and other query params
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip('/')
    return base_url.lower()


def extract_url_from_markdown(file_path: Path) -> str | None:
    """Extract the URL from markdown frontmatter."""
    try:
        content = file_path.read_text(encoding='utf-8')
        # Look for **URL:** pattern in frontmatter
        match = re.search(r'\*\*URL:\*\*\s*(https?://[^\s]+)', content)
        if match:
            return match.group(1).strip()
    except Exception as e:
        logger.error(f"Error reading {file_path}: {e}")
    return None


def extract_title_from_url(url: str) -> str:
    """Extract title slug from Stratechery URL."""
    # URL like https://stratechery.com/2025/the-youtube-juggernaut/
    parsed = urlparse(url)
    path_parts = parsed.path.strip('/').split('/')
    if len(path_parts) >= 2:
        # Last part is the slug
        return path_parts[-1].replace('-', ' ').title()
    return ""


def main():
    parser = argparse.ArgumentParser(description='Import Stratechery crawl to podcast database')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done')
    parser.add_argument('--limit', type=int, default=0, help='Limit number of imports')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Paths
    crawl_dir = Path('data/stratechery/articles')
    transcript_dir = Path('data/podcasts/stratechery/transcripts')

    if not crawl_dir.exists():
        logger.error(f"Crawl directory not found: {crawl_dir}")
        return

    transcript_dir.mkdir(parents=True, exist_ok=True)

    # Get database connection
    store = PodcastStore()

    # Get Stratechery podcast
    podcast = store.get_podcast_by_slug('stratechery')
    if not podcast:
        logger.error("Stratechery podcast not found in database")
        return

    # Get pending episodes
    episodes = store.get_episodes_by_podcast(podcast.id)
    pending_episodes = [e for e in episodes if e.transcript_status == 'unknown']
    logger.info(f"Found {len(pending_episodes)} pending Stratechery episodes")

    # Build URL lookup map
    url_to_episode = {}
    for ep in pending_episodes:
        normalized = normalize_url(ep.url)
        url_to_episode[normalized] = ep
        logger.debug(f"Pending: {normalized}")

    # Get crawled files
    crawled_files = sorted(crawl_dir.glob('*.md'))
    logger.info(f"Found {len(crawled_files)} crawled files")

    # Match and import
    matched = 0
    skipped = 0
    errors = 0

    for file_path in crawled_files:
        if args.limit and matched >= args.limit:
            break

        # Extract URL from file
        file_url = extract_url_from_markdown(file_path)
        if not file_url:
            logger.warning(f"No URL found in {file_path.name}")
            errors += 1
            continue

        normalized_url = normalize_url(file_url)

        # Check if we have a pending episode for this URL
        if normalized_url not in url_to_episode:
            logger.debug(f"No pending episode for: {normalized_url}")
            skipped += 1
            continue

        episode = url_to_episode[normalized_url]

        # Generate transcript filename
        date_str = episode.publish_date[:10] if episode.publish_date else datetime.now().strftime('%Y-%m-%d')
        title_slug = re.sub(r'[^\w\s-]', '', episode.title.lower())
        title_slug = re.sub(r'[\s]+', '-', title_slug)[:80]
        transcript_filename = f"{date_str}_{title_slug}.md"
        transcript_path = transcript_dir / transcript_filename

        if args.dry_run:
            logger.info(f"Would import: {episode.title[:60]}...")
            logger.info(f"  From: {file_path.name}")
            logger.info(f"  To: {transcript_path.name}")
            matched += 1
            continue

        # Copy file and update database
        try:
            shutil.copy(file_path, transcript_path)
            store.update_episode_transcript_status(
                episode.id,
                'fetched',
                str(transcript_path)
            )
            logger.info(f"Imported: {episode.title[:60]}...")
            matched += 1
        except Exception as e:
            logger.error(f"Error importing {episode.title}: {e}")
            errors += 1

    # Summary
    print()
    print("=" * 60)
    print("STRATECHERY IMPORT SUMMARY")
    print("=" * 60)
    print(f"Pending episodes:   {len(pending_episodes)}")
    print(f"Crawled files:      {len(crawled_files)}")
    print(f"Matched & imported: {matched}")
    print(f"Skipped (no match): {skipped}")
    print(f"Errors:             {errors}")

    if args.dry_run:
        print()
        print("(Dry run - no changes made)")


if __name__ == '__main__':
    main()
