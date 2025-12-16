#!/usr/bin/env python3
"""
Retry Failed URLs with Fixed Fetchers

Loads failed URLs from url_fetcher_state.json and retries them using
the improved RobustFetcher with:
- Fixed Archive.is URL format
- Multi-snapshot Wayback fallback
- Cookie propagation to Playwright

Usage:
    python scripts/retry_failed_with_fixes.py --limit 100
    python scripts/retry_failed_with_fixes.py --domain nytimes.com
    python scripts/retry_failed_with_fixes.py --all
"""

import argparse
import json
import logging
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.ingest.robust_fetcher import RobustFetcher
from modules.quality import verify_content, QualityLevel

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Paths
STATE_FILE = Path("data/url_fetcher_state.json")
COOKIES_DIR = Path.home() / ".config/atlas/cookies"
OUTPUT_DIR = Path("data/content/article")

# Priority domains (news sites most likely to be archived)
PRIORITY_DOMAINS = [
    'nytimes.com',
    'washingtonpost.com',
    'wsj.com',
    'theverge.com',
    'arstechnica.com',
    'wired.com',
    'theatlantic.com',
    'newyorker.com',
    'bloomberg.com',
    'ft.com',
    'reuters.com',
    'apnews.com',
    'bbc.com',
    'theguardian.com',
    'economist.com',
    'npr.org',
]


def load_state():
    """Load fetcher state file."""
    if not STATE_FILE.exists():
        logger.error(f"State file not found: {STATE_FILE}")
        return None
    with open(STATE_FILE) as f:
        return json.load(f)


def save_state(state):
    """Save fetcher state file."""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def get_cookie_file_for_url(url: str) -> Path | None:
    """Find the cookie file for a URL's domain."""
    parsed = urlparse(url)
    domain = parsed.netloc.lower()

    # Direct match
    cookie_file = COOKIES_DIR / f"{domain}.json"
    if cookie_file.exists():
        return cookie_file

    # Try without www prefix
    if domain.startswith('www.'):
        cookie_file = COOKIES_DIR / f"{domain[4:]}.json"
        if cookie_file.exists():
            return cookie_file

    # Try partial domain match
    for cookie_file in COOKIES_DIR.glob("*.json"):
        cookie_domain = cookie_file.stem
        if cookie_domain in domain or domain in cookie_domain:
            return cookie_file

    return None


def get_domain(url: str) -> str:
    """Extract domain from URL."""
    parsed = urlparse(url)
    return parsed.netloc.lower().replace('www.', '')


def prioritize_urls(failed_urls: list) -> list:
    """Sort URLs by priority (news sites first)."""
    def priority_key(item):
        url = item['url']
        domain = get_domain(url)
        for i, pd in enumerate(PRIORITY_DOMAINS):
            if pd in domain:
                return (i, url)
        return (len(PRIORITY_DOMAINS), url)

    return sorted(failed_urls, key=priority_key)


def retry_url(url: str, stats: dict) -> dict | None:
    """
    Retry fetching a URL with the improved RobustFetcher.

    Returns result dict if successful, None otherwise.
    """
    cookies_path = get_cookie_file_for_url(url)
    fetcher = RobustFetcher(
        output_base=OUTPUT_DIR,
        cookies_path=cookies_path
    )

    result = fetcher.fetch(url)

    if result.success and result.output_dir:
        content_file = Path(result.output_dir) / 'content.md'
        if content_file.exists():
            content = content_file.read_text()

            # Verify quality
            quality = verify_content(content, 'article')
            if quality.quality == QualityLevel.BAD:
                stats['bad_quality'] += 1
                logger.warning(f"  Quality check failed: {quality.issues}")
                return None

            # Track success method
            method = result.method or 'unknown'
            stats['by_method'][method] += 1

            return {
                'title': result.title or url,
                'content': content,
                'url': url,
                'method': method,
                'output_dir': str(result.output_dir)
            }

    # Track failure reason
    if result.error:
        stats['errors'][result.error] = stats['errors'].get(result.error, 0) + 1

    return None


def main():
    parser = argparse.ArgumentParser(description="Retry failed URLs with fixed fetchers")
    parser.add_argument("--limit", type=int, default=100, help="Max URLs to retry")
    parser.add_argument("--domain", type=str, help="Only retry URLs from this domain")
    parser.add_argument("--all", action="store_true", help="Retry all failed URLs")
    parser.add_argument("--delay", type=float, default=5.0, help="Delay between requests")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be retried")
    args = parser.parse_args()

    state = load_state()
    if not state:
        return 1

    failed = state.get('failed', {})
    fetched = state.get('fetched', {})

    logger.info(f"Loaded state: {len(fetched)} fetched, {len(failed)} failed")

    # Get failed URLs as list
    failed_list = [{'hash': h, **v} for h, v in failed.items()]

    # Filter by domain if specified
    if args.domain:
        failed_list = [f for f in failed_list if args.domain in get_domain(f['url'])]
        logger.info(f"Filtered to {len(failed_list)} URLs matching domain: {args.domain}")

    # Prioritize
    failed_list = prioritize_urls(failed_list)

    # Apply limit
    if not args.all:
        failed_list = failed_list[:args.limit]

    logger.info(f"Will retry {len(failed_list)} URLs")

    if args.dry_run:
        print("\nWould retry these URLs:")
        for f in failed_list[:20]:
            print(f"  - {f['url']}")
        if len(failed_list) > 20:
            print(f"  ... and {len(failed_list) - 20} more")
        return 0

    # Stats tracking
    stats = {
        'attempted': 0,
        'success': 0,
        'failed': 0,
        'bad_quality': 0,
        'by_method': defaultdict(int),
        'errors': {},
    }

    # Retry each URL
    for item in failed_list:
        url = item['url']
        url_hash = item['hash']

        stats['attempted'] += 1
        logger.info(f"[{stats['attempted']}/{len(failed_list)}] Retrying: {url}")

        result = retry_url(url, stats)

        if result:
            stats['success'] += 1
            logger.info(f"  ✅ Success via {result['method']}")

            # Move from failed to fetched
            del failed[url_hash]
            fetched[url_hash] = {
                'url': url,
                'filepath': result['output_dir'],
                'fetched_at': datetime.now().isoformat(),
                'method': result['method']
            }

            # Save state periodically
            if stats['success'] % 10 == 0:
                state['fetched'] = fetched
                state['failed'] = failed
                save_state(state)
                logger.info("  State saved")
        else:
            stats['failed'] += 1
            logger.warning(f"  ❌ Still failed")

        time.sleep(args.delay)

    # Final save
    state['fetched'] = fetched
    state['failed'] = failed
    save_state(state)

    # Print summary
    print("\n" + "="*60)
    print("RETRY SUMMARY")
    print("="*60)
    print(f"Attempted:    {stats['attempted']}")
    print(f"Successful:   {stats['success']} ({100*stats['success']/max(1,stats['attempted']):.1f}%)")
    print(f"Failed:       {stats['failed']}")
    print(f"Bad quality:  {stats['bad_quality']}")

    if stats['by_method']:
        print("\nSuccess by method:")
        for method, count in sorted(stats['by_method'].items(), key=lambda x: -x[1]):
            print(f"  {method}: {count}")

    if stats['errors']:
        print("\nTop errors:")
        for err, count in sorted(stats['errors'].items(), key=lambda x: -x[1])[:5]:
            print(f"  {err}: {count}")

    print(f"\nFinal state: {len(fetched)} fetched, {len(failed)} failed")

    return 0


if __name__ == "__main__":
    sys.exit(main())
