#!/usr/bin/env python3
"""
Enhanced Content Extraction - Phase B2
Robust content extraction with multiple strategies and improved success rates.
"""

import os
import sys
import logging
import asyncio
import time
import json
import requests
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import subprocess
import tempfile

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedContentExtractor:
    """Enhanced content extraction with multiple strategies."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize enhanced content extractor."""
        self.config = config or {}
        self.timeout = self.config.get('extraction_timeout', 30)
        self.user_agent = self.config.get('user_agent',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

        # Track extraction strategies and their success rates
        self.strategy_stats = {
            'direct_requests': {'attempts': 0, 'successes': 0},
            'crawl4ai': {'attempts': 0, 'successes': 0},
            'playwright': {'attempts': 0, 'successes': 0},
            'mercury_parser': {'attempts': 0, 'successes': 0},
            'fallback_scraper': {'attempts': 0, 'successes': 0}
        }

    def extract_content(self, url: str, strategies: List[str] = None) -> Dict[str, Any]:
        """Extract content using multiple strategies."""
        if not strategies:
            strategies = ['direct_requests', 'crawl4ai', 'playwright', 'mercury_parser']

        logger.info(f"🔍 Extracting content from: {url}")

        for strategy in strategies:
            try:
                logger.info(f"   Trying strategy: {strategy}")
                self.strategy_stats[strategy]['attempts'] += 1

                result = self._extract_with_strategy(url, strategy)

                if result and result.get('content') and len(result['content'].strip()) > 100:
                    self.strategy_stats[strategy]['successes'] += 1
                    result['extraction_strategy'] = strategy
                    result['extracted_at'] = datetime.now().isoformat()
                    logger.info(f"   ✅ Success with {strategy}: {len(result['content'])} chars")
                    return result
                else:
                    logger.warning(f"   ⚠️ {strategy} returned insufficient content")

            except Exception as e:
                logger.error(f"   ❌ {strategy} failed: {str(e)[:100]}")
                continue

        logger.error(f"❌ All extraction strategies failed for: {url}")
        return {
            'url': url,
            'content': '',
            'title': '',
            'extraction_strategy': 'failed',
            'extracted_at': datetime.now().isoformat(),
            'error': 'All extraction strategies failed'
        }

    def _extract_with_strategy(self, url: str, strategy: str) -> Dict[str, Any]:
        """Extract content using specific strategy."""
        if strategy == 'direct_requests':
            return self._extract_direct_requests(url)
        elif strategy == 'crawl4ai':
            return self._extract_crawl4ai(url)
        elif strategy == 'playwright':
            return self._extract_playwright(url)
        elif strategy == 'mercury_parser':
            return self._extract_mercury_parser(url)
        elif strategy == 'fallback_scraper':
            return self._extract_fallback_scraper(url)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

    def _extract_direct_requests(self, url: str) -> Dict[str, Any]:
        """Extract using direct HTTP requests with BeautifulSoup."""
        import requests
        from bs4 import BeautifulSoup

        headers = {
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }

        response = requests.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Remove script and style elements
        for script in soup(['script', 'style', 'nav', 'footer', 'aside']):
            script.decompose()

        # Extract title
        title = ''
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text().strip()

        # Try to find main content
        content = ''
        content_selectors = [
            'article',
            '.post-content', '.entry-content', '.content',
            'main', '.main-content',
            '.story-body', '.article-body',
            '[role="main"]'
        ]

        for selector in content_selectors:
            elements = soup.select(selector)
            if elements:
                content = '\n'.join([elem.get_text(separator='\n').strip() for elem in elements])
                break

        # Fallback to body if no specific content found
        if not content:
            body = soup.find('body')
            if body:
                content = body.get_text(separator='\n').strip()

        return {
            'url': url,
            'title': title,
            'content': content,
            'html_length': len(response.text),
            'content_length': len(content)
        }

    def _extract_crawl4ai(self, url: str) -> Dict[str, Any]:
        """Extract using Crawl4AI for JavaScript-heavy sites."""
        try:
            # Try to import and use crawl4ai
            try:
                from crawl4ai import WebCrawler
            except ImportError:
                logger.info("   crawl4ai not installed, trying pip install...")
                subprocess.run([sys.executable, '-m', 'pip', 'install', 'crawl4ai'],
                             capture_output=True, check=True)
                from crawl4ai import WebCrawler

            # Create crawler instance
            crawler = WebCrawler()

            # Start crawler
            crawler.start()

            try:
                # Crawl the URL
                result = crawler.run(url=url, word_count_threshold=10)

                if result.success:
                    return {
                        'url': url,
                        'title': result.metadata.get('title', ''),
                        'content': result.cleaned_html or result.markdown or '',
                        'metadata': result.metadata,
                        'content_length': len(result.cleaned_html or result.markdown or '')
                    }
                else:
                    raise Exception(f"Crawl4AI failed: {result.error}")

            finally:
                crawler.close()

        except ImportError as e:
            logger.warning("   Crawl4AI not available, skipping")
            raise e
        except Exception as e:
            logger.error(f"   Crawl4AI extraction failed: {e}")
            raise e

    def _extract_playwright(self, url: str) -> Dict[str, Any]:
        """Extract using Playwright for dynamic content."""
        try:
            # Use subprocess to run playwright extraction
            script_content = f'''
import asyncio
from playwright.async_api import async_playwright
import json

async def extract_content():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Set user agent
        await page.set_user_agent("{self.user_agent}")

        try:
            # Navigate to page
            await page.goto("{url}", wait_until="domcontentloaded", timeout={self.timeout * 1000})

            # Wait for content to load
            await page.wait_for_timeout(2000)

            # Extract title
            title = await page.title()

            # Extract content
            content = await page.evaluate("""() => {{
                // Remove unwanted elements
                const unwanted = document.querySelectorAll('script, style, nav, footer, aside, .advertisement');
                unwanted.forEach(el => el.remove());

                // Try to find main content
                const selectors = ['article', '.post-content', '.entry-content', '.content', 'main', '.main-content'];
                for (const selector of selectors) {{
                    const element = document.querySelector(selector);
                    if (element) {{
                        return element.innerText.trim();
                    }}
                }}

                // Fallback to body
                return document.body.innerText.trim();
            }}""")

            return {{
                "url": "{url}",
                "title": title,
                "content": content,
                "content_length": len(content)
            }}

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(extract_content())
    print(json.dumps(result))
'''

            # Write script to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(script_content)
                script_path = f.name

            try:
                # Run playwright extraction
                result = subprocess.run([
                    sys.executable, script_path
                ], capture_output=True, text=True, timeout=self.timeout + 10)

                if result.returncode == 0:
                    return json.loads(result.stdout)
                else:
                    raise Exception(f"Playwright extraction failed: {result.stderr}")

            finally:
                os.unlink(script_path)

        except Exception as e:
            logger.error(f"   Playwright extraction failed: {e}")
            raise e

    def _extract_mercury_parser(self, url: str) -> Dict[str, Any]:
        """Extract using Mercury Parser API or similar service."""
        try:
            # Try to use a free readability service
            api_url = "https://mercury.postlight.com/parser"
            api_key = self.config.get('mercury_api_key')

            if not api_key:
                # Try alternative readability service
                api_url = f"https://r.jina.ai/{url}"

                response = requests.get(api_url, timeout=self.timeout, headers={
                    'User-Agent': self.user_agent
                })

                if response.status_code == 200:
                    # Jina reader returns markdown directly
                    content = response.text
                    return {
                        'url': url,
                        'title': '',  # Would need to extract from content
                        'content': content,
                        'content_length': len(content)
                    }
                else:
                    raise Exception(f"Jina reader failed: {response.status_code}")
            else:
                # Use Mercury API
                headers = {
                    'x-api-key': api_key,
                    'Content-Type': 'application/json'
                }

                params = {'url': url}
                response = requests.get(api_url, headers=headers, params=params, timeout=self.timeout)
                response.raise_for_status()

                data = response.json()

                return {
                    'url': url,
                    'title': data.get('title', ''),
                    'content': data.get('content', ''),
                    'content_length': len(data.get('content', ''))
                }

        except Exception as e:
            logger.error(f"   Mercury parser extraction failed: {e}")
            raise e

    def _extract_fallback_scraper(self, url: str) -> Dict[str, Any]:
        """Fallback scraper using newspaper3k or similar."""
        try:
            # Try newspaper3k
            try:
                from newspaper import Article
            except ImportError:
                logger.info("   Installing newspaper3k...")
                subprocess.run([sys.executable, '-m', 'pip', 'install', 'newspaper3k'],
                             capture_output=True, check=True)
                from newspaper import Article

            article = Article(url)
            article.download()
            article.parse()

            return {
                'url': url,
                'title': article.title or '',
                'content': article.text or '',
                'authors': article.authors,
                'publish_date': article.publish_date.isoformat() if article.publish_date else None,
                'content_length': len(article.text or '')
            }

        except Exception as e:
            logger.error(f"   Fallback scraper failed: {e}")
            raise e

    def get_strategy_performance(self) -> Dict[str, Any]:
        """Get performance statistics for extraction strategies."""
        performance = {}

        for strategy, stats in self.strategy_stats.items():
            if stats['attempts'] > 0:
                success_rate = (stats['successes'] / stats['attempts']) * 100
                performance[strategy] = {
                    'attempts': stats['attempts'],
                    'successes': stats['successes'],
                    'success_rate': round(success_rate, 1)
                }
            else:
                performance[strategy] = {
                    'attempts': 0,
                    'successes': 0,
                    'success_rate': 0.0
                }

        return performance

    def fix_podcast_transcript_timeouts(self, podcast_urls: List[str]) -> Dict[str, Any]:
        """Fix podcast transcript fetching with improved timeout handling."""
        results = {
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'timeouts': 0,
            'errors': []
        }

        for url in podcast_urls:
            try:
                logger.info(f"🎙️ Processing podcast: {url}")
                results['processed'] += 1

                # Use enhanced extraction with longer timeout for podcasts
                original_timeout = self.timeout
                self.timeout = 60  # 1 minute for podcasts

                try:
                    content_result = self.extract_content(url, strategies=['direct_requests', 'playwright'])

                    if content_result.get('content') and len(content_result['content']) > 100:
                        results['successful'] += 1
                        logger.info(f"   ✅ Extracted {len(content_result['content'])} chars")
                    else:
                        results['failed'] += 1
                        logger.warning(f"   ⚠️ Insufficient content extracted")

                except asyncio.TimeoutError:
                    results['timeouts'] += 1
                    logger.error(f"   ⏱️ Timeout processing {url}")

                finally:
                    self.timeout = original_timeout

            except Exception as e:
                results['failed'] += 1
                results['errors'].append({'url': url, 'error': str(e)})
                logger.error(f"   ❌ Error processing {url}: {e}")

        return results

def test_enhanced_extraction():
    """Test enhanced content extraction."""
    logger.info("🧪 Testing Enhanced Content Extraction")

    extractor = EnhancedContentExtractor()

    # Test URLs
    test_urls = [
        'https://stratechery.com',  # JavaScript-heavy site
        'https://news.ycombinator.com',  # Simple HTML
        'https://www.npr.org',  # Media site
    ]

    for url in test_urls:
        try:
            result = extractor.extract_content(url, strategies=['direct_requests'])
            logger.info(f"   {url}: {len(result.get('content', ''))} chars extracted")
        except Exception as e:
            logger.error(f"   {url}: Failed - {e}")

    # Print performance stats
    performance = extractor.get_strategy_performance()
    logger.info("📊 Extraction Strategy Performance:")
    for strategy, stats in performance.items():
        logger.info(f"   {strategy}: {stats['success_rate']}% ({stats['successes']}/{stats['attempts']})")

if __name__ == "__main__":
    test_enhanced_extraction()