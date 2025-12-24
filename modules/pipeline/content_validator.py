#!/usr/bin/env python3
"""
Content Validator & Retry Pipeline

Scans existing content for:
1. Stubs (< 500 bytes)
2. JS-blocked content ("You need to enable JavaScript")
3. Failed fetches marked in metadata
4. Redirect/tracking URLs that need resolution

Then retries with:
1. Redirect resolver (follows 301/302/meta-refresh to real URL)
2. Headless browser for JS-rendered sites
3. Better headers for 403 errors

Usage:
    python -m modules.pipeline.content_validator --scan          # Identify problems
    python -m modules.pipeline.content_validator --retry         # Retry all failures
    python -m modules.pipeline.content_validator --retry --limit 50  # Retry first 50
"""

import asyncio
import json
import logging
import os
import re
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse

import requests
import trafilatura

logger = logging.getLogger(__name__)


# Known redirect/tracking URL patterns that need resolution
REDIRECT_PATTERNS = [
    r'404media\.co/r/',
    r'email\.puck\.news/e/c/',
    r'links\.message\.bloomberg\.com/',
    r'bloom\.bg/',
    r'bit\.ly/',
    r't\.co/',
    r'lnkd\.in/',
    r'ow\.ly/',
    r'tinyurl\.com/',
    r'substack\.com/redirect/',
]

# Patterns indicating JS-blocked content
JS_BLOCKED_PATTERNS = [
    'you need to enable javascript',
    'please enable javascript',
    'javascript is required',
    'this site requires javascript',
    'enable javascript to view',
]

# Non-article URLs to skip
SKIP_URL_PATTERNS = [
    r'\.jpg$', r'\.png$', r'\.gif$', r'\.webp$', r'\.svg$',  # Images
    r'\.pdf$', r'\.mp3$', r'\.mp4$',  # Media files
    r'youtube\.com/embed', r'ytimg\.com',  # YouTube embeds
    r'twitter\.com/intent', r'facebook\.com/sharer',  # Share widgets
]


class ContentValidator:
    """Validates and retries failed content fetches"""

    def __init__(self, content_dir: str = "data/content"):
        self.content_dir = Path(content_dir)
        self.stats = {
            'scanned': 0,
            'stubs': 0,
            'js_blocked': 0,
            'failed': 0,
            'redirect_urls': 0,
            'skip_urls': 0,
            'good': 0,
        }
        self.retry_queue: List[Dict[str, Any]] = []

    def scan_content(self, content_type: str = "article") -> Dict[str, Any]:
        """Scan content directory and categorize items by quality"""
        type_dir = self.content_dir / content_type

        if not type_dir.exists():
            return self.stats

        for year_dir in type_dir.iterdir():
            if not year_dir.is_dir():
                continue
            for month_dir in year_dir.iterdir():
                if not month_dir.is_dir():
                    continue
                for day_dir in month_dir.iterdir():
                    if not day_dir.is_dir():
                        continue
                    for item_dir in day_dir.iterdir():
                        if not item_dir.is_dir():
                            continue
                        self._check_item(item_dir)

        return self.stats

    def _check_item(self, item_dir: Path):
        """Check a single content item for quality issues"""
        self.stats['scanned'] += 1

        metadata_file = item_dir / "metadata.json"
        content_file = item_dir / "content.md"

        if not metadata_file.exists():
            return

        try:
            with open(metadata_file) as f:
                metadata = json.load(f)
        except Exception:
            return

        source_url = metadata.get('source_url', '')

        # Check if URL should be skipped
        for pattern in SKIP_URL_PATTERNS:
            if re.search(pattern, source_url, re.IGNORECASE):
                self.stats['skip_urls'] += 1
                return

        # Check if it's a redirect URL
        is_redirect = False
        for pattern in REDIRECT_PATTERNS:
            if re.search(pattern, source_url):
                is_redirect = True
                self.stats['redirect_urls'] += 1
                break

        # Check content quality
        content_size = 0
        content_text = ""
        if content_file.exists():
            content_size = content_file.stat().st_size
            try:
                with open(content_file) as f:
                    content_text = f.read(2000).lower()  # Read first 2k for JS check
            except Exception:
                pass

        # Categorize the issue
        issue = None
        if metadata.get('status') == 'failed' or metadata.get('error_message'):
            issue = 'failed'
            self.stats['failed'] += 1
        elif content_size < 500:
            issue = 'stub'
            self.stats['stubs'] += 1
        elif any(pattern in content_text for pattern in JS_BLOCKED_PATTERNS):
            issue = 'js_blocked'
            self.stats['js_blocked'] += 1
        elif is_redirect:
            issue = 'redirect'
            # Already counted above
        else:
            self.stats['good'] += 1
            return  # No issue

        # Add to retry queue
        self.retry_queue.append({
            'item_dir': str(item_dir),
            'source_url': source_url,
            'issue': issue,
            'content_id': metadata.get('content_id', ''),
            'title': metadata.get('title', '')[:50],
        })

    def print_scan_results(self):
        """Print scan results summary"""
        print(f"\n{'='*60}")
        print("CONTENT VALIDATION SCAN RESULTS")
        print(f"{'='*60}")
        print(f"Total scanned:   {self.stats['scanned']:,}")
        print(f"  Good content:  {self.stats['good']:,}")
        print(f"  Stubs (<500b): {self.stats['stubs']:,}")
        print(f"  JS blocked:    {self.stats['js_blocked']:,}")
        print(f"  Failed:        {self.stats['failed']:,}")
        print(f"  Redirect URLs: {self.stats['redirect_urls']:,}")
        print(f"  Skip (images): {self.stats['skip_urls']:,}")
        print(f"\nRetry queue:     {len(self.retry_queue):,} items")
        print(f"{'='*60}\n")

        # Show sample of issues
        if self.retry_queue:
            print("Sample issues:")
            for item in self.retry_queue[:5]:
                print(f"  [{item['issue']}] {item['source_url'][:60]}...")


class ContentRetryPipeline:
    """Retry failed content fetches with improved methods"""

    # Cookie files for paywalled sites
    COOKIE_DIR = Path.home() / ".config" / "atlas" / "cookies"

    def __init__(self, content_dir: str = "data/content"):
        self.content_dir = Path(content_dir)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        })
        self.rate_limit = 2.0
        self.last_request = 0
        self.stats = {
            'attempted': 0,
            'resolved_redirects': 0,
            'fetched_with_browser': 0,
            'fetched_with_requests': 0,
            'still_failed': 0,
            'content_improved': 0,
        }
        # Load cookies for authenticated sites
        self._load_cookies()

    def _rate_limit(self):
        """Enforce rate limiting"""
        elapsed = time.time() - self.last_request
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self.last_request = time.time()

    def _load_cookies(self):
        """Load cookies from cookie files into requests session."""
        if not self.COOKIE_DIR.exists():
            logger.info("No cookie directory found")
            return

        loaded = []
        for cookie_file in self.COOKIE_DIR.glob("*.json"):
            try:
                with open(cookie_file) as f:
                    cookies = json.load(f)

                # Handle both formats: list of cookies or dict
                if isinstance(cookies, list):
                    for cookie in cookies:
                        if 'name' in cookie and 'value' in cookie:
                            self.session.cookies.set(
                                cookie['name'],
                                cookie['value'],
                                domain=cookie.get('domain', ''),
                                path=cookie.get('path', '/')
                            )
                loaded.append(cookie_file.stem)
            except Exception as e:
                logger.warning(f"Failed to load cookies from {cookie_file}: {e}")

        if loaded:
            logger.info(f"Loaded cookies for: {', '.join(loaded)}")

    def _get_cookie_file_for_url(self, url: str) -> Optional[Path]:
        """Get the cookie file for a specific URL domain."""
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.lower()

        # Map domains to cookie files
        domain_map = {
            'wsj.com': 'wsj.com.json',
            'www.wsj.com': 'wsj.com.json',
            'bloomberg.com': 'bloomberg.com.json',
            'www.bloomberg.com': 'bloomberg.com.json',
            'nytimes.com': 'nytimes.com.json',
            'www.nytimes.com': 'nytimes.com.json',
        }

        for key, filename in domain_map.items():
            if key in domain:
                cookie_path = self.COOKIE_DIR / filename
                if cookie_path.exists():
                    return cookie_path
        return None

    def resolve_redirect(self, url: str) -> Tuple[str, bool]:
        """
        Resolve redirect/tracking URLs to their final destination.
        Returns (final_url, changed)
        """
        self._rate_limit()

        try:
            # Use HEAD request first (faster)
            response = self.session.head(url, allow_redirects=True, timeout=15)
            final_url = response.url

            if final_url != url:
                logger.info(f"Resolved redirect: {url[:50]}... -> {final_url[:50]}...")
                return final_url, True

        except Exception as e:
            logger.debug(f"HEAD failed for {url}, trying GET: {e}")

            # Fall back to GET for sites that don't support HEAD
            try:
                response = self.session.get(url, allow_redirects=True, timeout=15)
                final_url = response.url

                # Also check for meta-refresh redirects
                if 'http-equiv="refresh"' in response.text.lower():
                    match = re.search(r'url=([^"\'>\s]+)', response.text, re.IGNORECASE)
                    if match:
                        final_url = match.group(1)
                        return final_url, True

                if final_url != url:
                    return final_url, True

            except Exception as e2:
                logger.warning(f"Could not resolve {url}: {e2}")

        return url, False

    def fetch_with_requests(self, url: str) -> Tuple[Optional[str], Optional[Dict]]:
        """Fetch content with requests + trafilatura"""
        self._rate_limit()

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            html = response.text

            # Extract content
            content = trafilatura.extract(
                html,
                include_links=True,
                include_images=True,
                output_format="markdown"
            )

            metadata = trafilatura.extract_metadata(html)
            meta_dict = {}
            if metadata:
                meta_dict = {
                    'title': metadata.title or '',
                    'author': metadata.author or '',
                    'description': metadata.description or '',
                    'date': metadata.date or '',
                }

            return content, meta_dict

        except Exception as e:
            logger.warning(f"Requests fetch failed for {url}: {e}")
            return None, {'error': str(e)}

    async def fetch_with_browser(self, url: str) -> Tuple[Optional[str], Optional[Dict]]:
        """Fetch content with headless browser, using cookies for paywalled sites"""
        import sys
        from pathlib import Path
        # Add project root to path if needed
        project_root = Path(__file__).parent.parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        from modules.browser import Browser

        # Get cookie file for this URL
        cookie_file = self._get_cookie_file_for_url(url)

        try:
            async with Browser(timeout=45000, cookies_file=cookie_file) as browser:
                # Get the rendered page
                html = await browser.fetch(url, wait_for="load", wait_time=3000)

                # Extract content
                content = trafilatura.extract(
                    html,
                    include_links=True,
                    include_images=True,
                    output_format="markdown"
                )

                metadata = trafilatura.extract_metadata(html)
                meta_dict = {}
                if metadata:
                    meta_dict = {
                        'title': metadata.title or '',
                        'author': metadata.author or '',
                    }

                if cookie_file and content and len(content) > 500:
                    logger.info(f"Successfully fetched with cookies: {url[:50]}...")

                return content, meta_dict

        except Exception as e:
            logger.warning(f"Browser fetch failed for {url}: {e}")
            return None, {'error': str(e)}

    def fetch_from_wayback(self, url: str) -> Tuple[Optional[str], Optional[Dict]]:
        """
        Fetch content from Wayback Machine as last resort.
        This bypasses paywalls and bot detection since it's an archived snapshot.
        """
        from urllib.parse import quote_plus

        try:
            # Check if Wayback has this URL
            check_url = f"https://archive.org/wayback/available?url={quote_plus(url)}"
            response = self.session.get(check_url, timeout=15)
            if response.status_code != 200:
                return None, {'error': 'Wayback check failed'}

            data = response.json()
            snapshots = data.get('archived_snapshots', {})
            closest = snapshots.get('closest', {})

            if not closest.get('available'):
                logger.debug(f"No Wayback snapshot for: {url}")
                return None, {'error': 'No snapshot available'}

            # Fetch the archived version
            archive_url = closest['url']
            logger.info(f"Fetching from Wayback: {archive_url[:60]}...")

            archive_response = self.session.get(archive_url, timeout=30)
            if archive_response.status_code != 200:
                return None, {'error': f'Wayback fetch failed: {archive_response.status_code}'}

            html = archive_response.text

            # Extract content
            content = trafilatura.extract(
                html,
                include_links=True,
                include_images=True,
                output_format="markdown"
            )

            metadata = trafilatura.extract_metadata(html)
            meta_dict = {'wayback_url': archive_url}
            if metadata:
                meta_dict['title'] = metadata.title or ''
                meta_dict['author'] = metadata.author or ''

            if content and len(content) > 500:
                logger.info(f"Successfully fetched from Wayback: {url[:50]}...")
                self.stats['fetched_from_wayback'] = self.stats.get('fetched_from_wayback', 0) + 1
                return content, meta_dict

            return None, {'error': 'Content too short from Wayback'}

        except Exception as e:
            logger.warning(f"Wayback fetch failed for {url}: {e}")
            return None, {'error': str(e)}

    async def retry_item(self, item: Dict[str, Any]) -> bool:
        """
        Retry a single failed item.
        Returns True if content was improved.
        """
        self.stats['attempted'] += 1

        item_dir = Path(item['item_dir'])
        source_url = item['source_url']
        issue = item['issue']

        print(f"  [{issue}] Retrying: {source_url[:60]}...")

        # Step 1: Resolve redirects if needed
        final_url = source_url
        if issue == 'redirect' or any(re.search(p, source_url) for p in REDIRECT_PATTERNS):
            final_url, changed = self.resolve_redirect(source_url)
            if changed:
                self.stats['resolved_redirects'] += 1
                print(f"    -> Resolved to: {final_url[:60]}...")

        # Step 2: Try fetching content with fallback chain
        # requests → browser → wayback
        content = None
        metadata = {}

        # For JS-blocked, go straight to browser
        if issue == 'js_blocked':
            content, metadata = await self.fetch_with_browser(final_url)
            if content and len(content) > 500:
                self.stats['fetched_with_browser'] += 1
        else:
            # Try requests first (faster)
            content, metadata = self.fetch_with_requests(final_url)

            if content and len(content) > 500:
                self.stats['fetched_with_requests'] += 1
            else:
                # Fall back to browser
                content, metadata = await self.fetch_with_browser(final_url)
                if content and len(content) > 500:
                    self.stats['fetched_with_browser'] += 1

        # Step 2.5: If still no content, try Wayback Machine
        # This handles bot-blocked sites (WSJ, Bloomberg with DataDome)
        if not content or len(content) < 500:
            wayback_content, wayback_meta = self.fetch_from_wayback(final_url)
            if wayback_content and len(wayback_content) > 500:
                content = wayback_content
                metadata = wayback_meta

        # Step 3: Update the content if we got something better
        if content and len(content) > 500:
            content_file = item_dir / "content.md"
            metadata_file = item_dir / "metadata.json"

            # Update content
            with open(content_file, 'w', encoding='utf-8') as f:
                f.write(content)

            # Update metadata
            try:
                with open(metadata_file) as f:
                    existing_meta = json.load(f)
            except Exception:
                existing_meta = {}

            existing_meta['status'] = 'completed'
            existing_meta['retry_at'] = datetime.now().isoformat()
            existing_meta['resolved_url'] = final_url if final_url != source_url else None
            if metadata.get('title'):
                existing_meta['title'] = metadata['title']
            if metadata.get('error'):
                del existing_meta['error_message']

            with open(metadata_file, 'w') as f:
                json.dump(existing_meta, f, indent=2)

            self.stats['content_improved'] += 1
            print(f"    ✓ Improved! ({len(content)} chars)")
            return True
        else:
            self.stats['still_failed'] += 1
            print(f"    ✗ Still failed")
            return False

    async def retry_all(self, queue: List[Dict[str, Any]], limit: int = 0):
        """Retry all items in queue"""
        if limit > 0:
            queue = queue[:limit]

        print(f"\n{'='*60}")
        print(f"RETRYING {len(queue)} ITEMS")
        print(f"{'='*60}\n")

        for item in queue:
            try:
                await self.retry_item(item)
            except Exception as e:
                logger.error(f"Error retrying {item['source_url']}: {e}")
                self.stats['still_failed'] += 1

        self.print_results()

    def print_results(self):
        """Print retry results"""
        print(f"\n{'='*60}")
        print("RETRY RESULTS")
        print(f"{'='*60}")
        print(f"Attempted:          {self.stats['attempted']}")
        print(f"Redirects resolved: {self.stats['resolved_redirects']}")
        print(f"Fetched (requests): {self.stats['fetched_with_requests']}")
        print(f"Fetched (browser):  {self.stats['fetched_with_browser']}")
        print(f"Fetched (wayback):  {self.stats.get('fetched_from_wayback', 0)}")
        print(f"Content improved:   {self.stats['content_improved']}")
        print(f"Still failed:       {self.stats['still_failed']}")
        print(f"{'='*60}\n")


async def main():
    """CLI entry point"""
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    parser = argparse.ArgumentParser(description="Content Validator & Retry Pipeline")
    parser.add_argument("--scan", action="store_true", help="Scan and identify issues")
    parser.add_argument("--retry", action="store_true", help="Retry failed content")
    parser.add_argument("--limit", type=int, default=0, help="Limit items to retry")
    parser.add_argument("--type", type=str, default="article", help="Content type to scan")
    args = parser.parse_args()

    if args.scan or args.retry:
        # Always scan first
        validator = ContentValidator()
        validator.scan_content(args.type)
        validator.print_scan_results()

        if args.retry and validator.retry_queue:
            pipeline = ContentRetryPipeline()
            await pipeline.retry_all(validator.retry_queue, limit=args.limit)
    else:
        print("Usage: python -m modules.pipeline.content_validator --scan [--retry] [--limit N]")


if __name__ == "__main__":
    asyncio.run(main())
