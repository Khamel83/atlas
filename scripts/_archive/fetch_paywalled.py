#!/usr/bin/env python3
"""
Fetch paywalled URLs using robust_fetcher with Playwright + cookies.

Usage:
    python scripts/fetch_paywalled.py                    # Process all
    python scripts/fetch_paywalled.py --domain wsj.com   # Just WSJ
    python scripts/fetch_paywalled.py --limit 100        # First 100
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlparse
import hashlib

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.ingest.robust_fetcher import RobustFetcher

try:
    from modules.quality import verify_file, QualityLevel
    HAS_QUALITY = True
except ImportError:
    HAS_QUALITY = False

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Config
QUEUE_FILE = Path("data/url_queue.txt")
STATE_FILE = Path("data/url_fetcher_state.json")
COOKIES_DIR = Path(os.path.expanduser("~/.config/atlas/cookies"))
OUTPUT_DIR = Path("data/content/article")
DELAY_SECONDS = 10

# Domains that need Playwright + their cookie files
DOMAIN_COOKIES = {
    'wsj.com': 'wsj.com.json',
    'nytimes.com': 'nytimes.com.json',
    'bloomberg.com': 'bloomberg.com.json',
    'stratechery.com': 'stratechery.com.json',
}


def url_hash(url: str) -> str:
    return hashlib.md5(url.strip().lower().encode()).hexdigest()[:12]


def load_state() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {'fetched': {}, 'failed': {}}


def save_state(state: dict):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description='Fetch paywalled URLs with Playwright')
    parser.add_argument('--domain', type=str, help='Only process this domain')
    parser.add_argument('--limit', type=int, help='Max URLs to process')
    parser.add_argument('--dry-run', action='store_true', help='Preview only')
    args = parser.parse_args()

    state = load_state()

    # Read queue
    with open(QUEUE_FILE) as f:
        all_urls = [l.strip() for l in f if l.strip().startswith('http')]

    # Filter to paywalled domains
    urls_to_process = []
    for url in all_urls:
        domain = urlparse(url).netloc.replace('www.', '')

        # Check if it's a paywalled domain
        if domain not in DOMAIN_COOKIES:
            continue

        # Check domain filter
        if args.domain and args.domain not in domain:
            continue

        # Skip already fetched
        if url_hash(url) in state.get('fetched', {}):
            continue

        urls_to_process.append((url, domain))

    if args.limit:
        urls_to_process = urls_to_process[:args.limit]

    logger.info(f"Found {len(urls_to_process)} paywalled URLs to process")

    if args.dry_run:
        for url, domain in urls_to_process[:20]:
            logger.info(f"  Would fetch: {url}")
        if len(urls_to_process) > 20:
            logger.info(f"  ... and {len(urls_to_process) - 20} more")
        return

    success_count = 0
    fail_count = 0

    for i, (url, domain) in enumerate(urls_to_process):
        logger.info(f"[{i+1}/{len(urls_to_process)}] {url}")

        # Get cookies for domain
        cookie_file = COOKIES_DIR / DOMAIN_COOKIES[domain]
        if not cookie_file.exists():
            logger.warning(f"  No cookies for {domain}")
            continue

        # Create fetcher with cookies
        fetcher = RobustFetcher(
            output_base=OUTPUT_DIR,
            cookies_path=cookie_file
        )

        try:
            result = fetcher.fetch(url)

            if result.success:
                # Quality gate: verify content before marking as success
                quality_passed = True
                if HAS_QUALITY and result.output_dir:
                    content_file = Path(result.output_dir) / 'content.md'
                    if content_file.exists():
                        qresult = verify_file(content_file, 'article')
                        if qresult.quality == QualityLevel.BAD:
                            logger.warning(f"  QUALITY FAILED: {qresult.issues}")
                            logger.info(f"  Trying archive fallback...")

                            # Try without cookies (archive.org, archive.is)
                            archive_fetcher = RobustFetcher(output_base=OUTPUT_DIR)
                            archive_result = archive_fetcher.fetch(url)

                            if archive_result.success and archive_result.output_dir:
                                archive_content = Path(archive_result.output_dir) / 'content.md'
                                if archive_content.exists():
                                    archive_qresult = verify_file(archive_content, 'article')
                                    if archive_qresult.quality != QualityLevel.BAD:
                                        # Archive version is good
                                        result = archive_result
                                        quality_passed = True
                                        logger.info(f"  Recovered via archive fallback")
                                    else:
                                        quality_passed = False
                                else:
                                    quality_passed = False
                            else:
                                quality_passed = False

                            if not quality_passed:
                                state['failed'][url_hash(url)] = {
                                    'url': url,
                                    'reason': f"Quality check failed (all methods): {', '.join(qresult.issues[:2])}",
                                    'status': 'unrecoverable',
                                    'failed_at': time.strftime('%Y-%m-%dT%H:%M:%S')
                                }
                                save_state(state)
                                fail_count += 1
                        elif qresult.quality == QualityLevel.MARGINAL:
                            logger.info(f"  Marginal quality (score {qresult.score})")

                if quality_passed:
                    logger.info(f"  SUCCESS via {result.method}")
                    state['fetched'][url_hash(url)] = {
                        'url': url,
                        'path': str(result.output_dir) if result.output_dir else '',
                        'method': result.method,
                        'fetched_at': time.strftime('%Y-%m-%dT%H:%M:%S')
                    }
                    # Remove from failed if present
                    if url_hash(url) in state.get('failed', {}):
                        del state['failed'][url_hash(url)]
                    save_state(state)
                    success_count += 1
            else:
                logger.warning(f"  FAILED: {result.error}")
                state['failed'][url_hash(url)] = {
                    'url': url,
                    'reason': result.error or 'Unknown error',
                    'failed_at': time.strftime('%Y-%m-%dT%H:%M:%S')
                }
                save_state(state)
                fail_count += 1

        except Exception as e:
            logger.error(f"  ERROR: {e}")
            fail_count += 1

        # Rate limit
        if i < len(urls_to_process) - 1:
            time.sleep(DELAY_SECONDS)

    logger.info(f"\nDone! Success: {success_count}, Failed: {fail_count}")


if __name__ == '__main__':
    main()
