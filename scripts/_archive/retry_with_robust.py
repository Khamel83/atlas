#!/usr/bin/env python3
"""
Retry Failed URLs with Robust Fetcher

Uses the full robust_fetcher with all fallbacks:
- Direct fetch with cookies
- Playwright headless browser
- Archive.is
- Wayback Machine
- URL resurrection

Usage:
    python scripts/retry_with_robust.py              # Retry all failed
    python scripts/retry_with_robust.py --limit 50   # Retry 50 URLs
    python scripts/retry_with_robust.py --domain wired.com  # Only wired.com
    python scripts/retry_with_robust.py --dry-run    # Preview only
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.ingest.robust_fetcher import RobustFetcher

# Config
STATE_FILE = Path("data/url_fetcher_state.json")
COOKIES_DIR = Path(os.path.expanduser("~/.config/atlas/cookies"))
OUTPUT_DIR = Path("data/content/article")
DELAY_SECONDS = 15  # Be polite

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_state() -> dict:
    """Load fetcher state."""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {'fetched': {}, 'failed': {}}


def save_state(state: dict):
    """Save fetcher state."""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def get_cookies_for_domain(domain: str) -> Path | None:
    """Find cookies file for a domain."""
    if not COOKIES_DIR.exists():
        return None

    # Try exact match
    cookie_file = COOKIES_DIR / f"{domain}.json"
    if cookie_file.exists():
        return cookie_file

    # Try without www
    domain_clean = domain.replace('www.', '')
    cookie_file = COOKIES_DIR / f"{domain_clean}.json"
    if cookie_file.exists():
        return cookie_file

    return None


def url_hash(url: str) -> str:
    """Create short hash of URL (matching simple_url_fetcher)."""
    import hashlib
    url = url.strip().lower()
    return hashlib.md5(url.encode()).hexdigest()[:12]


def retry_failed_urls(
    limit: int = None,
    domain_filter: str = None,
    dry_run: bool = False
):
    """Retry failed URLs using robust fetcher."""
    state = load_state()
    failed = state.get('failed', {})

    if not failed:
        logger.info("No failed URLs to retry")
        return

    # Filter by domain if specified
    urls_to_retry = []
    for hash_id, entry in failed.items():
        url = entry.get('url', '')
        if not url:
            continue

        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        if domain_filter and domain_filter not in domain:
            continue

        urls_to_retry.append((hash_id, url, domain))

    if limit:
        urls_to_retry = urls_to_retry[:limit]

    logger.info(f"Found {len(urls_to_retry)} failed URLs to retry")

    if dry_run:
        for hash_id, url, domain in urls_to_retry:
            cookies = get_cookies_for_domain(domain)
            cookie_status = "with cookies" if cookies else "no cookies (will try archive/wayback)"
            logger.info(f"  Would retry: {url} ({cookie_status})")
        return

    # Group by domain for cookie efficiency
    success_count = 0
    fail_count = 0

    for i, (hash_id, url, domain) in enumerate(urls_to_retry):
        logger.info(f"[{i+1}/{len(urls_to_retry)}] Retrying: {url}")

        # Get domain-specific cookies
        cookies_path = get_cookies_for_domain(domain)
        if cookies_path:
            logger.info(f"  Using cookies from {cookies_path.name}")
        else:
            logger.info(f"  No cookies - will try archive.is/Wayback")

        # Create fetcher with cookies
        fetcher = RobustFetcher(
            output_base=OUTPUT_DIR,
            cookies_path=cookies_path
        )

        try:
            result = fetcher.fetch(url)

            if result.success:
                logger.info(f"  SUCCESS via {result.method}: {result.title[:60] if result.title else 'No title'}...")

                # Move from failed to fetched
                del state['failed'][hash_id]
                state['fetched'][hash_id] = {
                    'url': url,
                    'path': str(result.output_dir) if result.output_dir else '',
                    'method': result.method,
                    'fetched_at': time.strftime('%Y-%m-%dT%H:%M:%S')
                }
                save_state(state)
                success_count += 1
            else:
                logger.warning(f"  FAILED: {result.error}")
                fail_count += 1

        except Exception as e:
            logger.error(f"  ERROR: {e}")
            fail_count += 1

        # Rate limit
        if i < len(urls_to_retry) - 1:
            time.sleep(DELAY_SECONDS)

    logger.info(f"\nDone! Success: {success_count}, Failed: {fail_count}")


def main():
    parser = argparse.ArgumentParser(description='Retry failed URLs with robust fetcher')
    parser.add_argument('--limit', type=int, help='Max URLs to retry')
    parser.add_argument('--domain', type=str, help='Only retry URLs from this domain')
    parser.add_argument('--dry-run', action='store_true', help='Preview without fetching')
    args = parser.parse_args()

    retry_failed_urls(
        limit=args.limit,
        domain_filter=args.domain,
        dry_run=args.dry_run
    )


if __name__ == '__main__':
    main()
