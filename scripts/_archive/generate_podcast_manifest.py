#!/usr/bin/env python3
"""
Generate Podcast Manifest - Static task list for podcast transcript fetching.

Creates a JSON manifest with every failed episode, pre-computed:
- Resolution strategy (whisper_local, retry_with_vpn, paywall_bypass, etc.)
- Audio URL for local transcription
- Status tracking

Usage:
    python scripts/generate_podcast_manifest.py
    python scripts/generate_podcast_manifest.py --output data/manifests/podcast_tasks.json
"""

import argparse
import json
import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Paths
ATLAS_ROOT = Path(__file__).parent.parent
PODCAST_DB = ATLAS_ROOT / "data/podcasts/atlas_podcasts.db"
COOKIES_DIR = Path(os.path.expanduser("~/.config/atlas/cookies"))
OUTPUT_FILE = ATLAS_ROOT / "data/manifests/podcast_tasks.json"

# Podcast configurations
# Paywalled podcasts that need subscription or local Whisper
PAYWALLED_PODCASTS = {
    'dithering': 'whisper_local',
    'asianometry': 'whisper_local',  # User says they have access, try cookies first
}

# Podcasts known to have YouTube versions
YOUTUBE_PODCASTS = {
    'lex-fridman-podcast',
    'conversations-with-tyler',
    'dwarkesh-podcast',
    'acquired',
    'acq2-by-acquired',
    'cortex',
    'hard-fork',
}

# Podcasts with website transcripts (high success rate)
WEBSITE_TRANSCRIPT_PODCASTS = {
    'stratechery',
    'planet-money',
    'the-npr-politics-podcast',
    'this-american-life',
}


def get_available_cookies() -> Dict[str, str]:
    """Get list of domains with available cookies."""
    cookies = {}
    if COOKIES_DIR.exists():
        for cookie_file in COOKIES_DIR.glob("*.json"):
            domain = cookie_file.stem
            cookies[domain] = str(cookie_file)
    return cookies


def determine_resolution_strategy(slug: str, metadata: dict) -> str:
    """Determine the best strategy for fetching this podcast's transcript."""
    # Check for paywalled
    if slug in PAYWALLED_PODCASTS:
        return PAYWALLED_PODCASTS[slug]

    # Check for YouTube availability
    if slug in YOUTUBE_PODCASTS:
        return 'retry_with_vpn'

    # Check for website transcripts
    if slug in WEBSITE_TRANSCRIPT_PODCASTS:
        return 'website_retry'

    # Default: try all resolvers again (maybe podscripts updated)
    return 'retry_resolvers'


def generate_manifest() -> List[Dict[str, Any]]:
    """Generate the podcast manifest from database."""
    available_cookies = get_available_cookies()

    logger.info(f"Available cookies: {list(available_cookies.keys())}")

    manifest = []
    task_id = 0

    # Query all failed episodes
    conn = sqlite3.connect(PODCAST_DB)
    conn.row_factory = sqlite3.Row

    cursor = conn.execute("""
        SELECT
            e.id, e.guid, e.title, e.url, e.publish_date,
            e.transcript_status, e.metadata,
            p.slug, p.name as podcast_title, p.rss_url
        FROM episodes e
        JOIN podcasts p ON e.podcast_id = p.id
        WHERE e.transcript_status IN ('failed', 'unknown', 'found', 'local')
        ORDER BY p.slug, e.publish_date DESC
    """)

    stats = {
        'total': 0,
        'by_strategy': {},
        'by_podcast': {},
    }

    for row in cursor:
        stats['total'] += 1
        slug = row['slug']
        stats['by_podcast'][slug] = stats['by_podcast'].get(slug, 0) + 1

        # Parse metadata
        try:
            metadata = json.loads(row['metadata']) if row['metadata'] else {}
        except json.JSONDecodeError:
            metadata = {}

        # Get audio URL from metadata or episode URL
        audio_url = metadata.get('enclosure_url') or metadata.get('audio_url') or row['url']

        # Determine strategy
        strategy = determine_resolution_strategy(slug, metadata)
        stats['by_strategy'][strategy] = stats['by_strategy'].get(strategy, 0) + 1

        # Build task
        task_id += 1
        task = {
            'id': f'pod-{task_id:05d}',
            'episode_id': row['id'],
            'guid': row['guid'],
            'podcast_slug': slug,
            'podcast_title': row['podcast_title'],
            'episode_title': row['title'],
            'episode_url': row['url'],
            'audio_url': audio_url,
            'published_date': row['publish_date'],
            'resolution_strategy': strategy,
            'resolvers_to_try': get_resolvers_for_strategy(strategy, slug),
            'status': 'pending',
            'fetched_at': None,
            'fetched_via': None,
            'transcript_path': None,
            'error': None,
        }

        manifest.append(task)

    conn.close()

    # Log stats
    logger.info(f"\n=== Manifest Generation Complete ===")
    logger.info(f"Total failed episodes: {stats['total']}")
    logger.info(f"\nBy strategy:")
    for strategy, count in sorted(stats['by_strategy'].items(), key=lambda x: -x[1]):
        logger.info(f"  {strategy}: {count}")
    logger.info(f"\nTop podcasts:")
    for podcast, count in sorted(stats['by_podcast'].items(), key=lambda x: -x[1])[:15]:
        logger.info(f"  {podcast}: {count}")

    return manifest


def get_resolvers_for_strategy(strategy: str, slug: str) -> List[str]:
    """Get resolver chain for a strategy."""
    if strategy == 'whisper_local':
        return ['download_audio', 'whisper_local']
    elif strategy == 'retry_with_vpn':
        return ['podscripts', 'youtube_transcript_vpn']
    elif strategy == 'website_retry':
        return ['generic_html', 'network_transcripts', 'podscripts']
    elif strategy == 'paywall_bypass':
        return ['generic_html_with_cookies', 'archive.is', 'wayback']
    else:  # retry_resolvers
        return ['podscripts', 'generic_html', 'youtube_transcript', 'pattern']


def main():
    parser = argparse.ArgumentParser(description='Generate podcast manifest')
    parser.add_argument('--output', '-o', type=str, default=str(OUTPUT_FILE),
                       help='Output file path')
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Generating podcast manifest...")
    manifest = generate_manifest()

    # Write manifest
    with open(output_path, 'w') as f:
        json.dump(manifest, f, indent=2)

    logger.info(f"Manifest written to: {output_path}")
    logger.info(f"Total tasks: {len(manifest)}")

    # Summary
    print(f"\n=== Manifest Summary ===")
    print(f"Total failed episodes: {len(manifest)}")

    from collections import Counter
    strategies = Counter(t['resolution_strategy'] for t in manifest)
    print(f"\nBy resolution strategy:")
    for strategy, count in strategies.most_common():
        print(f"  {strategy}: {count}")

    podcasts = Counter(t['podcast_slug'] for t in manifest)
    print(f"\nTop 15 podcasts with failures:")
    for podcast, count in podcasts.most_common(15):
        print(f"  {podcast}: {count}")


if __name__ == '__main__':
    main()
