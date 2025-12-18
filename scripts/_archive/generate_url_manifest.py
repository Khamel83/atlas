#!/usr/bin/env python3
"""
Generate URL Manifest - Static task list for URL fetching.

Creates a JSON manifest with every URL to fetch, pre-computed:
- File type classification (content/image/audio/pdf)
- Fallback chain based on domain
- Cookie availability
- Status tracking

Usage:
    python scripts/generate_url_manifest.py
    python scripts/generate_url_manifest.py --output data/manifests/url_tasks.json
    python scripts/generate_url_manifest.py --include-fetched  # Include already-fetched URLs
"""

import argparse
import json
import logging
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from typing import Dict, List, Optional, Any

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Paths
ATLAS_ROOT = Path(__file__).parent.parent
LINK_QUEUE_DB = ATLAS_ROOT / "data/enrich/link_queue.db"
URL_STATE_FILE = ATLAS_ROOT / "data/url_fetcher_state.json"
COOKIES_DIR = Path(os.path.expanduser("~/.config/atlas/cookies"))
OUTPUT_FILE = ATLAS_ROOT / "data/manifests/url_tasks.json"

# Media extensions to filter out
MEDIA_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.ico', '.bmp',
    '.mp3', '.mp4', '.wav', '.m4a', '.ogg', '.flac', '.aac',
    '.webm', '.mkv', '.avi', '.mov',
}

# Domains with special handling
PAYWALLED_DOMAINS = {
    'nytimes.com', 'wsj.com', 'bloomberg.com', 'economist.com',
    'newyorker.com', 'theatlantic.com', 'wired.com', 'ft.com',
    'stratechery.com', 'reuters.com',
}

ARCHIVE_FRIENDLY_DOMAINS = {
    'nytimes.com', 'wsj.com', 'bloomberg.com', 'washingtonpost.com',
    'newyorker.com', 'theatlantic.com',
}


def get_available_cookies() -> Dict[str, str]:
    """Get list of domains with available cookies."""
    cookies = {}
    if COOKIES_DIR.exists():
        for cookie_file in COOKIES_DIR.glob("*.json"):
            domain = cookie_file.stem
            cookies[domain] = str(cookie_file)
    return cookies


def classify_url_type(url: str) -> str:
    """Classify URL by file type."""
    parsed = urlparse(url)
    path_lower = parsed.path.lower()

    # Check for media extensions
    for ext in MEDIA_EXTENSIONS:
        if ext in path_lower:
            if ext in {'.mp3', '.mp4', '.wav', '.m4a', '.ogg', '.flac', '.aac', '.webm', '.mkv', '.avi', '.mov'}:
                return 'audio' if ext in {'.mp3', '.wav', '.m4a', '.ogg', '.flac', '.aac'} else 'video'
            return 'image'

    # PDF detection
    if '.pdf' in path_lower:
        return 'pdf'

    return 'content'


def get_fallback_chain(domain: str, has_cookies: bool) -> List[str]:
    """Determine fallback chain for a domain."""
    chain = []

    # Always try direct first
    chain.append('direct')

    # Paywalled sites need Playwright
    if domain in PAYWALLED_DOMAINS or has_cookies:
        chain.append('playwright')

    # Archive sources for compatible domains
    if domain in ARCHIVE_FRIENDLY_DOMAINS:
        chain.append('archive.is')
        chain.append('wayback')
    else:
        # Still try archives as last resort
        chain.append('wayback')

    # URL resurrection as final attempt
    chain.append('resurrect')

    return chain


def load_existing_state() -> Dict[str, Any]:
    """Load existing URL fetcher state."""
    if URL_STATE_FILE.exists():
        with open(URL_STATE_FILE) as f:
            return json.load(f)
    return {'fetched': {}, 'failed': {}}


def generate_manifest(include_fetched: bool = False) -> List[Dict[str, Any]]:
    """Generate the URL manifest from link queue database."""
    available_cookies = get_available_cookies()
    existing_state = load_existing_state()

    # Get already-fetched URL hashes
    fetched_hashes = set(existing_state.get('fetched', {}).keys())
    failed_hashes = set(existing_state.get('failed', {}).keys())

    logger.info(f"Available cookies: {list(available_cookies.keys())}")
    logger.info(f"Already fetched: {len(fetched_hashes)}")
    logger.info(f"Previously failed: {len(failed_hashes)}")

    manifest = []
    task_id = 0

    # Query all links from database
    conn = sqlite3.connect(LINK_QUEUE_DB)
    conn.row_factory = sqlite3.Row

    cursor = conn.execute("""
        SELECT id, url, domain, score, category, status, source_content_id, source_path
        FROM extracted_links
        ORDER BY score DESC, id ASC
    """)

    stats = {
        'total': 0,
        'content': 0,
        'image': 0,
        'audio': 0,
        'video': 0,
        'pdf': 0,
        'skipped_media': 0,
        'skipped_fetched': 0,
        'with_cookies': 0,
    }

    for row in cursor:
        stats['total'] += 1
        url = row['url']
        domain = row['domain'].lower().replace('www.', '')

        # Classify URL type
        file_type = classify_url_type(url)
        stats[file_type] = stats.get(file_type, 0) + 1

        # Skip media files (images, audio, video)
        if file_type in ('image', 'audio', 'video'):
            stats['skipped_media'] += 1
            continue

        # Check if already fetched
        import hashlib
        url_hash = hashlib.md5(url.strip().lower().encode()).hexdigest()[:12]

        if url_hash in fetched_hashes and not include_fetched:
            stats['skipped_fetched'] += 1
            continue

        # Determine cookie availability
        has_cookies = any(
            cookie_domain in domain or domain in cookie_domain
            for cookie_domain in available_cookies.keys()
        )
        if has_cookies:
            stats['with_cookies'] += 1

        # Build task
        task_id += 1
        task = {
            'id': f'url-{task_id:05d}',
            'url': url,
            'url_hash': url_hash,
            'domain': domain,
            'score': row['score'],
            'source': row['source_content_id'] or '',
            'source_path': row['source_path'] or '',
            'db_status': row['status'],
            'file_type': file_type,
            'fallback_chain': get_fallback_chain(domain, has_cookies),
            'cookies_available': has_cookies,
            'status': 'pending',
            'previously_failed': url_hash in failed_hashes,
            'fetched_at': None,
            'fetched_via': None,
            'content_path': None,
            'error': None,
        }

        manifest.append(task)

    conn.close()

    # Log stats
    logger.info(f"\n=== Manifest Generation Complete ===")
    logger.info(f"Total links in DB: {stats['total']}")
    logger.info(f"Content URLs: {stats['content']}")
    logger.info(f"PDF URLs: {stats['pdf']}")
    logger.info(f"Image URLs (skipped): {stats['image']}")
    logger.info(f"Audio URLs (skipped): {stats['audio']}")
    logger.info(f"Video URLs (skipped): {stats.get('video', 0)}")
    logger.info(f"Already fetched (skipped): {stats['skipped_fetched']}")
    logger.info(f"With cookies: {stats['with_cookies']}")
    logger.info(f"Final manifest size: {len(manifest)}")

    return manifest


def main():
    parser = argparse.ArgumentParser(description='Generate URL manifest')
    parser.add_argument('--output', '-o', type=str, default=str(OUTPUT_FILE),
                       help='Output file path')
    parser.add_argument('--include-fetched', action='store_true',
                       help='Include already-fetched URLs')
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Generating URL manifest...")
    manifest = generate_manifest(include_fetched=args.include_fetched)

    # Write manifest
    with open(output_path, 'w') as f:
        json.dump(manifest, f, indent=2)

    logger.info(f"Manifest written to: {output_path}")
    logger.info(f"Total tasks: {len(manifest)}")

    # Summary by status
    pending = sum(1 for t in manifest if t['status'] == 'pending')
    previously_failed = sum(1 for t in manifest if t['previously_failed'])
    with_cookies = sum(1 for t in manifest if t['cookies_available'])

    print(f"\n=== Manifest Summary ===")
    print(f"Total tasks: {len(manifest)}")
    print(f"Pending: {pending}")
    print(f"Previously failed (retry): {previously_failed}")
    print(f"With cookies: {with_cookies}")

    # Top domains
    from collections import Counter
    domains = Counter(t['domain'] for t in manifest)
    print(f"\nTop 15 domains:")
    for domain, count in domains.most_common(15):
        print(f"  {domain}: {count}")


if __name__ == '__main__':
    main()
