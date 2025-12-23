#!/usr/bin/env python3
"""
Fix Episode URLs

Many podcasts have bad/missing episode URLs in their RSS feeds.
This script generates proper URLs from episode titles for known podcasts.

URL Patterns:
- Acquired: https://www.acquired.fm/episodes/{slug}
- ACQ2: https://www.acquired.fm/episodes/{slug}
- Dithering: No public URLs (private RSS)
- Conversations with Tyler: https://conversationswithtyler.com/episodes/{slug}
- EconTalk: https://www.econtalk.org/{slug}/
- Dwarkesh: https://www.dwarkeshpatel.com/p/{slug}
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.podcasts.store import PodcastStore


# URL patterns for known podcasts
URL_PATTERNS = {
    'acquired': 'https://www.acquired.fm/episodes/{slug}',
    'acq2-by-acquired': 'https://www.acquired.fm/episodes/{slug}',
    'conversations-with-tyler': 'https://conversationswithtyler.com/episodes/{slug}',
    'econtalk': 'https://www.econtalk.org/{slug}/',
    'dwarkesh-podcast': 'https://www.dwarkeshpatel.com/p/{slug}',
    'hard-fork': 'https://www.nytimes.com/column/hard-fork',  # No direct episode URLs
    'radiolab': 'https://radiolab.org/podcast/{slug}',
    'planet-money': 'https://www.npr.org/podcasts/510289/planet-money',  # Search needed
}


def title_to_slug(title: str) -> str:
    """Convert episode title to URL slug"""
    # Remove special characters and normalize
    slug = title.lower()
    slug = re.sub(r'[^\w\s-]', '', slug)  # Remove special chars
    slug = re.sub(r'[\s_]+', '-', slug)    # Replace spaces with hyphens
    slug = re.sub(r'-+', '-', slug)         # Collapse multiple hyphens
    slug = slug.strip('-')
    return slug


def fix_urls_for_podcast(store: PodcastStore, slug: str, dry_run: bool = True):
    """Fix URLs for a specific podcast"""
    if slug not in URL_PATTERNS:
        print(f"No URL pattern known for: {slug}")
        return 0

    pattern = URL_PATTERNS[slug]
    podcast = store.get_podcast_by_slug(slug)
    if not podcast:
        print(f"Podcast not found: {slug}")
        return 0

    episodes = store.get_episodes_by_podcast(podcast.id)
    fixed = 0

    for ep in episodes:
        # Skip if already has a good URL
        if ep.url and len(ep.url) > 30 and ep.url != podcast.site_url:
            continue

        # Generate URL from title
        ep_slug = title_to_slug(ep.title)
        new_url = pattern.format(slug=ep_slug)

        if dry_run:
            print(f"  Would fix: {ep.title[:50]}...")
            print(f"    Old: {ep.url}")
            print(f"    New: {new_url}")
            fixed += 1
        else:
            # Use direct SQL via _get_connection context manager
            with store._get_connection() as conn:
                conn.execute(
                    "UPDATE episodes SET url = ? WHERE id = ?",
                    (new_url, ep.id)
                )
                conn.commit()
            fixed += 1

    return fixed


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Fix episode URLs")
    parser.add_argument("--slug", help="Specific podcast to fix")
    parser.add_argument("--all", action="store_true", help="Fix all known podcasts")
    parser.add_argument("--apply", action="store_true", help="Actually apply changes")
    args = parser.parse_args()

    store = PodcastStore('data/podcasts/atlas_podcasts.db')
    dry_run = not args.apply

    if dry_run:
        print("DRY RUN - no changes will be made. Use --apply to commit.\n")

    if args.slug:
        slugs = [args.slug]
    elif args.all:
        slugs = list(URL_PATTERNS.keys())
    else:
        print("Specify --slug or --all")
        return

    total_fixed = 0
    for slug in slugs:
        print(f"\n=== {slug} ===")
        fixed = fix_urls_for_podcast(store, slug, dry_run)
        total_fixed += fixed
        if not dry_run:
            print(f"  Fixed {fixed} URLs")

    if dry_run:
        print(f"\nWould fix URLs for {len(slugs)} podcasts")
    else:
        print(f"\nFixed {total_fixed} URLs total")


if __name__ == "__main__":
    main()
