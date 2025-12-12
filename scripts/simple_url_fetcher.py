#!/usr/bin/env python3
"""
Simple URL Fetcher - The MVP for articles/URLs

A dead-simple always-running script that:
1. Watches a queue file for new URLs
2. Fetches content slowly
3. Saves to disk
4. Loops forever

Queue is just a text file - one URL per line.
Add URLs by appending to the file. That's it.

Usage:
    python scripts/simple_url_fetcher.py

Add URLs:
    echo "https://example.com/article" >> data/url_queue.txt
"""

import hashlib
import json
import logging
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

try:
    import trafilatura
    HAS_TRAFILATURA = True
except ImportError:
    HAS_TRAFILATURA = False

# Config
QUEUE_FILE = "data/url_queue.txt"
OUTPUT_DIR = "data/articles"
STATE_FILE = "data/url_fetcher_state.json"
SLEEP_BETWEEN_URLS = 10  # seconds
LOOP_INTERVAL = 60  # seconds between queue checks

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SimpleURLFetcher:
    """Simple, reliable URL fetcher."""

    def __init__(self):
        self.queue_file = Path(QUEUE_FILE)
        self.output_dir = Path(OUTPUT_DIR)
        self.state_file = Path(STATE_FILE)

        # Create dirs
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.queue_file.parent.mkdir(parents=True, exist_ok=True)

        # Touch queue file if doesn't exist
        if not self.queue_file.exists():
            self.queue_file.touch()

        self.state = self._load_state()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

    def _load_state(self) -> Dict:
        """Load state of what we've already fetched."""
        if self.state_file.exists():
            with open(self.state_file) as f:
                return json.load(f)
        return {'fetched': {}, 'failed': {}}

    def _save_state(self):
        """Save state to disk."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)

    def _url_hash(self, url: str) -> str:
        """Create short hash of URL."""
        # Normalize URL
        url = url.strip().lower()
        return hashlib.md5(url.encode()).hexdigest()[:12]

    def _is_fetched(self, url: str) -> bool:
        """Check if we already fetched this URL."""
        return self._url_hash(url) in self.state.get('fetched', {})

    def _mark_fetched(self, url: str, filepath: str):
        """Mark URL as fetched."""
        self.state['fetched'][self._url_hash(url)] = {
            'url': url,
            'path': filepath,
            'fetched_at': datetime.now().isoformat()
        }
        self._save_state()

    def _mark_failed(self, url: str, reason: str):
        """Mark URL as failed."""
        self.state['failed'][self._url_hash(url)] = {
            'url': url,
            'reason': reason,
            'failed_at': datetime.now().isoformat()
        }
        self._save_state()

    def get_pending_urls(self) -> list:
        """Get URLs from queue that we haven't processed yet."""
        if not self.queue_file.exists():
            return []

        pending = []
        with open(self.queue_file) as f:
            for line in f:
                url = line.strip()
                if url and url.startswith('http') and not self._is_fetched(url):
                    # Skip if already failed (don't retry forever)
                    if self._url_hash(url) not in self.state.get('failed', {}):
                        pending.append(url)

        return pending

    def fetch_content(self, url: str) -> Optional[Dict]:
        """Fetch and extract content from URL."""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            html = response.text

            # Try trafilatura first (best quality)
            if HAS_TRAFILATURA:
                content = trafilatura.extract(html, include_comments=False)
                if content and len(content) > 200:
                    # Get title
                    soup = BeautifulSoup(html, 'html.parser')
                    title = soup.title.string if soup.title else url
                    return {
                        'title': title.strip() if title else url,
                        'content': content,
                        'url': url
                    }

            # Fallback to BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')

            # Remove junk
            for tag in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                tag.decompose()

            # Try to find main content
            content = None
            for selector in ['article', 'main', '.post-content', '.entry-content', '.article-body', '#content']:
                elem = soup.select_one(selector)
                if elem:
                    content = elem.get_text(separator='\n', strip=True)
                    if len(content) > 500:
                        break

            # Fallback to body
            if not content or len(content) < 500:
                body = soup.find('body')
                if body:
                    content = body.get_text(separator='\n', strip=True)

            if content and len(content) > 200:
                title = soup.title.string if soup.title else url
                return {
                    'title': title.strip() if title else url,
                    'content': content,
                    'url': url
                }

        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")

        return None

    def save_article(self, data: Dict) -> str:
        """Save article to disk."""
        # Create filename from URL
        parsed = urlparse(data['url'])
        domain = parsed.netloc.replace('www.', '')

        # Clean title for filename
        title_slug = re.sub(r'[^\w\s-]', '', data['title'].lower())
        title_slug = re.sub(r'[-\s]+', '-', title_slug).strip('-')[:60]

        date_str = datetime.now().strftime('%Y-%m-%d')
        filename = f"{date_str}_{domain}_{title_slug}.md"

        # Organize by domain
        domain_dir = self.output_dir / domain.replace('.', '-')
        domain_dir.mkdir(parents=True, exist_ok=True)

        filepath = domain_dir / filename

        # Write content
        with open(filepath, 'w') as f:
            f.write(f"# {data['title']}\n\n")
            f.write(f"**URL:** {data['url']}\n\n")
            f.write(f"**Fetched:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
            f.write("---\n\n")
            f.write(data['content'])

        return str(filepath)

    def process_url(self, url: str) -> bool:
        """Process a single URL. Returns True if successful."""
        logger.info(f"Fetching: {url}")

        data = self.fetch_content(url)

        if data:
            filepath = self.save_article(data)
            self._mark_fetched(url, filepath)
            logger.info(f"  ✅ Saved: {filepath}")
            return True
        else:
            self._mark_failed(url, "Could not extract content")
            logger.warning(f"  ❌ Failed: {url}")
            return False

    def run_once(self) -> int:
        """Process all pending URLs. Returns count of successful fetches."""
        pending = self.get_pending_urls()

        if not pending:
            logger.info("No pending URLs")
            return 0

        logger.info(f"Processing {len(pending)} URLs...")

        success = 0
        for url in pending:
            if self.process_url(url):
                success += 1
            time.sleep(SLEEP_BETWEEN_URLS)

        logger.info(f"Done. Fetched {success}/{len(pending)} URLs.")
        return success

    def run_loop(self):
        """Run forever, checking queue periodically."""
        logger.info(f"Starting URL fetcher loop (checking every {LOOP_INTERVAL}s)")

        while True:
            try:
                self.run_once()
            except Exception as e:
                logger.error(f"Error in run loop: {e}")

            time.sleep(LOOP_INTERVAL)


def main():
    fetcher = SimpleURLFetcher()
    fetcher.run_loop()


if __name__ == '__main__':
    main()
