"""
URL Processing Strategy

Handles web page content extraction from URLs with error handling and retry logic.
"""

import asyncio
import time
import logging
from typing import Dict, Any, Optional
from urllib.parse import urljoin, urlparse
import re

try:
    import aiohttp
    from bs4 import BeautifulSoup
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False


class URLProcessor:
    """Processor for URL content extraction"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.session = None
        self.timeout = 30
        self.max_retries = 3
        self.retry_delay = 2

    async def process_url(self, url: str) -> Dict[str, Any]:
        """Process URL and extract content"""
        if not HAS_DEPS:
            return {
                'success': False,
                'error': 'Required dependencies (aiohttp, beautifulsoup4) not available'
            }

        try:
            # Validate URL
            if not self._validate_url(url):
                return {
                    'success': False,
                    'error': f'Invalid URL: {url}'
                }

            # Fetch content with retries
            html_content = await self._fetch_with_retries(url)
            if not html_content:
                return {
                    'success': False,
                    'error': f'Failed to fetch content from {url}'
                }

            # Extract content from HTML
            extracted_content = self._extract_content(html_content, url)

            return {
                'success': True,
                'title': extracted_content['title'],
                'content': extracted_content['content'],
                'url': url,
                'metadata': extracted_content['metadata']
            }

        except Exception as e:
            self.logger.error(f"URL processing failed for {url}: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _validate_url(self, url: str) -> bool:
        """Validate URL format"""
        try:
            parsed = urlparse(url)
            return all([parsed.scheme in ['http', 'https'], parsed.netloc])
        except Exception:
            return False

    async def _fetch_with_retries(self, url: str) -> Optional[str]:
        """Fetch URL content with retry logic"""
        if not self.session:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers={
                    'User-Agent': 'Mozilla/5.0 (compatible; Atlas/1.0; +https://github.com/atlas/atlas)'
                }
            )

        for attempt in range(self.max_retries):
            try:
                async with self.session.get(url) as response:
                    if response.status == 200:
                        content_type = response.headers.get('content-type', '')
                        if 'text/html' in content_type.lower():
                            return await response.text()
                        else:
                            return {
                                'success': False,
                                'error': f'Unsupported content type: {content_type}'
                            }
                    else:
                        self.logger.warning(f"HTTP {response.status} for {url}")
                        if attempt == self.max_retries - 1:
                            return None

            except Exception as e:
                self.logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt == self.max_retries - 1:
                    return None

            # Wait before retry
            if attempt < self.max_retries - 1:
                await asyncio.sleep(self.retry_delay * (2 ** attempt))

        return None

    def _extract_content(self, html_content: str, url: str) -> Dict[str, Any]:
        """Extract content from HTML"""
        soup = BeautifulSoup(html_content, 'html.parser')

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        # Extract title
        title = self._extract_title(soup)

        # Extract main content
        content = self._extract_main_content(soup)

        # Extract metadata
        metadata = self._extract_metadata(soup, url)

        return {
            'title': title,
            'content': content,
            'metadata': metadata
        }

    def _extract_title(self, soup) -> str:
        """Extract page title"""
        # Try different title sources
        title_sources = [
            soup.find('title'),
            soup.find('h1'),
            soup.find('meta', attrs={'property': 'og:title'}),
            soup.find('meta', attrs={'name': 'twitter:title'})
        ]

        for source in title_sources:
            if source:
                if source.name == 'title' or source.name in ['h1']:
                    title = source.get_text().strip()
                else:
                    title = source.get('content', '').strip()

                if title:
                    return title

        return "Untitled"

    def _extract_main_content(self, soup) -> str:
        """Extract main content from page"""
        content_candidates = []

        # Try different content selectors in order of preference
        content_selectors = [
            'article',
            'main',
            '[role="main"]',
            '.content',
            '.post-content',
            '.entry-content',
            '.article-content',
            'div.content'
        ]

        for selector in content_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text().strip()
                if len(text) > 200:  # Minimum content length
                    content_candidates.append(text)

        # If no structured content found, use body
        if not content_candidates:
            body = soup.find('body')
            if body:
                content_candidates.append(body.get_text().strip())

        # Select the longest content candidate
        if content_candidates:
            content = max(content_candidates, key=len)
            return self._clean_text(content)

        return ""

    def _extract_metadata(self, soup, url: str) -> Dict[str, Any]:
        """Extract page metadata"""
        metadata = {
            'url': url,
            'domain': urlparse(url).netloc,
            'extracted_at': time.time()
        }

        # Extract meta tags
        meta_tags = soup.find_all('meta')
        for tag in meta_tags:
            name = tag.get('name') or tag.get('property')
            content = tag.get('content')
            if name and content:
                metadata[name] = content

        # Extract author
        author_selectors = [
            'meta[name="author"]',
            '.author',
            '.byline',
            '[rel="author"]'
        ]

        for selector in author_selectors:
            element = soup.select_one(selector)
            if element:
                if element.name == 'meta':
                    author = element.get('content')
                else:
                    author = element.get_text().strip()

                if author:
                    metadata['author'] = author
                    break

        # Extract publish date
        date_selectors = [
            'meta[property="article:published_time"]',
            'time[datetime]',
            '.date',
            '.published'
        ]

        for selector in date_selectors:
            element = soup.select_one(selector)
            if element:
                if element.name == 'meta':
                    date = element.get('content')
                elif element.get('datetime'):
                    date = element.get('datetime')
                else:
                    date = element.get_text().strip()

                if date:
                    metadata['published_date'] = date
                    break

        return metadata

    def _clean_text(self, text: str) -> str:
        """Clean extracted text"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove empty lines
        text = re.sub(r'\n\s*\n', '\n\n', text)
        # Strip leading/trailing whitespace
        text = text.strip()

        return text

    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None


async def process_url_simple(url: str) -> Dict[str, Any]:
    """Simple URL processing function for backward compatibility"""
    processor = URLProcessor()
    try:
        result = await processor.process_url(url)
        return result
    finally:
        await processor.close()