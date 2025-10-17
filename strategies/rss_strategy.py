"""
RSS Processing Strategy

Handles RSS feed parsing and content extraction from feed entries.
"""

import asyncio
import time
import logging
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET

try:
    import aiohttp
    import feedparser
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False


class RSSProcessor:
    """Processor for RSS feed content extraction"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.session = None
        self.timeout = 30
        self.max_retries = 3
        self.retry_delay = 2

    async def process_feed(self, feed_url: str) -> Dict[str, Any]:
        """Process RSS feed and extract entries"""
        if not HAS_DEPS:
            return {
                'success': False,
                'error': 'Required dependencies (aiohttp, feedparser) not available'
            }

        try:
            # Validate feed URL
            if not self._validate_feed_url(feed_url):
                return {
                    'success': False,
                    'error': f'Invalid feed URL: {feed_url}'
                }

            # Fetch feed content
            feed_content = await self._fetch_feed_with_retries(feed_url)
            if not feed_content:
                return {
                    'success': False,
                    'error': f'Failed to fetch feed from {feed_url}'
                }

            # Parse feed
            parsed_feed = self._parse_feed(feed_content)
            if not parsed_feed:
                return {
                    'success': False,
                    'error': f'Failed to parse feed from {feed_url}'
                }

            # Extract entries
            entries = self._extract_entries(parsed_feed, feed_url)

            return {
                'success': True,
                'feed_title': parsed_feed.feed.get('title', 'Untitled Feed'),
                'feed_description': parsed_feed.feed.get('description', ''),
                'feed_link': parsed_feed.feed.get('link', ''),
                'entries': entries,
                'entry_count': len(entries),
                'metadata': {
                    'feed_url': feed_url,
                    'updated': parsed_feed.feed.get('updated', ''),
                    'extracted_at': time.time()
                }
            }

        except Exception as e:
            self.logger.error(f"RSS processing failed for {feed_url}: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _validate_feed_url(self, url: str) -> bool:
        """Validate RSS feed URL"""
        try:
            parsed = urlparse(url)
            return all([parsed.scheme in ['http', 'https'], parsed.netloc])
        except Exception:
            return False

    async def _fetch_feed_with_retries(self, feed_url: str) -> Optional[str]:
        """Fetch RSS feed content with retry logic"""
        if not self.session:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers={
                    'User-Agent': 'Mozilla/5.0 (compatible; Atlas/1.0; +https://github.com/atlas/atlas)'
                }
            )

        for attempt in range(self.max_retries):
            try:
                async with self.session.get(feed_url) as response:
                    if response.status == 200:
                        content_type = response.headers.get('content-type', '')
                        if any(t in content_type.lower() for t in ['xml', 'rss', 'atom']):
                            return await response.text()
                        else:
                            # Try to parse as RSS anyway
                            return await response.text()
                    else:
                        self.logger.warning(f"HTTP {response.status} for {feed_url}")
                        if attempt == self.max_retries - 1:
                            return None

            except Exception as e:
                self.logger.warning(f"Attempt {attempt + 1} failed for {feed_url}: {e}")
                if attempt == self.max_retries - 1:
                    return None

            # Wait before retry
            if attempt < self.max_retries - 1:
                await asyncio.sleep(self.retry_delay * (2 ** attempt))

        return None

    def _parse_feed(self, feed_content: str):
        """Parse RSS feed content"""
        try:
            # Use feedparser to parse the feed
            return feedparser.parse(feed_content)
        except Exception as e:
            self.logger.error(f"Feed parsing failed: {e}")
            return None

    def _extract_entries(self, parsed_feed, feed_url: str) -> List[Dict[str, Any]]:
        """Extract entries from parsed feed"""
        entries = []
        max_entries = 50  # Limit entries to prevent overload

        for entry in parsed_feed.entries[:max_entries]:
            try:
                entry_data = {
                    'title': self._extract_entry_title(entry),
                    'link': self._extract_entry_link(entry, feed_url),
                    'content': self._extract_entry_content(entry),
                    'summary': self._extract_entry_summary(entry),
                    'published': self._extract_entry_published(entry),
                    'author': self._extract_entry_author(entry),
                    'tags': self._extract_entry_tags(entry),
                    'metadata': {
                        'feed_url': feed_url,
                        'entry_id': entry.get('id', ''),
                        'extracted_at': time.time()
                    }
                }
                entries.append(entry_data)
            except Exception as e:
                self.logger.warning(f"Failed to extract entry: {e}")
                continue

        return entries

    def _extract_entry_title(self, entry) -> str:
        """Extract entry title"""
        return entry.get('title', 'Untitled')

    def _extract_entry_link(self, entry, feed_url: str) -> str:
        """Extract entry link"""
        link = entry.get('link', '')
        if link:
            # Handle relative URLs
            if link.startswith('/'):
                parsed_feed = urlparse(feed_url)
                link = f"{parsed_feed.scheme}://{parsed_feed.netloc}{link}"
            return link
        return feed_url  # Fallback to feed URL

    def _extract_entry_content(self, entry) -> str:
        """Extract entry content"""
        # Try different content sources
        content_sources = [
            entry.get('content', []),
            entry.get('summary', ''),
            entry.get('description', '')
        ]

        for source in content_sources:
            if isinstance(source, list) and source:
                for item in source:
                    if hasattr(item, 'value') and item.value:
                        return item.value
            elif isinstance(source, str) and source.strip():
                return source.strip()

        return ""

    def _extract_entry_summary(self, entry) -> str:
        """Extract entry summary"""
        summary = entry.get('summary', '')
        if summary:
            return summary.strip()
        return ""

    def _extract_entry_published(self, entry) -> str:
        """Extract entry published date"""
        return entry.get('published', '') or entry.get('updated', '')

    def _extract_entry_author(self, entry) -> str:
        """Extract entry author"""
        return entry.get('author', '')

    def _extract_entry_tags(self, entry) -> List[str]:
        """Extract entry tags"""
        tags = []
        if hasattr(entry, 'tags'):
            for tag in entry.tags:
                if hasattr(tag, 'term'):
                    tags.append(tag.term)
        return tags

    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None


async def process_rss_feed_simple(feed_url: str) -> Dict[str, Any]:
    """Simple RSS processing function for backward compatibility"""
    processor = RSSProcessor()
    try:
        result = await processor.process_feed(feed_url)
        return result
    finally:
        await processor.close()