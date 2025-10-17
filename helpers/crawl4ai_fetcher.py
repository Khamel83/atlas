#!/usr/bin/env python3
"""
Crawl4AI Enhanced Article Fetcher

Advanced content extraction using Crawl4AI with intelligent crawling,
JavaScript rendering, content cleaning, and structured data extraction.
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

# Add Atlas to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
    CRAWL4AI_AVAILABLE = True
except ImportError as e:
    CRAWL4AI_AVAILABLE = False
    AsyncWebCrawler = None
    print(f"Crawl4AI not available: {e}")

from helpers.config import load_config
from helpers.utils import log_info, log_error

logger = logging.getLogger(__name__)


class Crawl4AIConfig:
    """Configuration for Crawl4AI enhanced fetching."""

    DEFAULT_BROWSER_CONFIG = {
        "browser_type": "chromium",
        "headless": True,
        "viewport": {"width": 1920, "height": 1080},
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "accept_downloads": False,
        "java_script_enabled": True,
        "ignore_https_errors": True
    }

    DEFAULT_CRAWLER_CONFIG = {
        "word_count_threshold": 50,
        "cache_mode": CacheMode.ENABLED,
        "bypass_cache": False,
        "wait_for": None,  # Don't wait for specific selectors by default
        "delay_before_return_html": 2.0,  # Wait for content to load
        "remove_overlay_elements": True,
        "simulate_user": True,
        "magic": True,  # Enable smart content extraction
        "page_timeout": 30000,  # 30 second timeout
        "wait_for_timeout": 10000  # 10 second wait timeout
    }


class Crawl4AIFetcher:
    """Enhanced article fetcher using Crawl4AI."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize Crawl4AI fetcher."""
        if not CRAWL4AI_AVAILABLE:
            raise ImportError("Crawl4AI is not available. Install with: pip install crawl4ai")

        self.config = config or load_config()
        self.browser_config = BrowserConfig(**Crawl4AIConfig.DEFAULT_BROWSER_CONFIG)

        # Set up logging
        log_dir = self.config.get('log_directory', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        self.log_path = os.path.join(log_dir, 'crawl4ai_fetcher.log')

        # Statistics
        self.stats = {
            'total_requests': 0,
            'successful_extractions': 0,
            'failed_extractions': 0,
            'cache_hits': 0,
            'average_extraction_time': 0.0
        }

    async def extract_article(self, url: str, wait_for_content: str = None, custom_headers: Dict[str, str] = None) -> Dict[str, Any]:
        """Extract article content from URL using Crawl4AI."""
        start_time = time.time()
        self.stats['total_requests'] += 1

        log_info(self.log_path, f"🕷️ Crawling article: {url}")

        try:
            # Configure crawler for this request
            crawler_config = Crawl4AIConfig.DEFAULT_CRAWLER_CONFIG.copy()

            # Custom wait condition if provided
            if wait_for_content:
                crawler_config['wait_for'] = wait_for_content

            # Custom headers for authentication
            if custom_headers:
                crawler_config['headers'] = custom_headers

            # Create crawler instance
            async with AsyncWebCrawler(
                config=self.browser_config,
                verbose=False
            ) as crawler:

                # Crawl the page
                result = await crawler.arun(
                    url=url,
                    config=CrawlerRunConfig(**crawler_config)
                )

                # Check if extraction was successful
                if not result.success:
                    error_msg = f"Crawl failed: {result.error_message or 'Unknown error'}"
                    log_error(self.log_path, f"❌ {error_msg}")
                    self.stats['failed_extractions'] += 1
                    return self._create_error_result(url, error_msg, time.time() - start_time)

                # Extract structured content
                extracted_content = self._process_crawl_result(result, url)

                # Update statistics
                extraction_time = time.time() - start_time
                self.stats['successful_extractions'] += 1
                if result.is_cached:
                    self.stats['cache_hits'] += 1

                # Update average extraction time
                total_successful = self.stats['successful_extractions']
                self.stats['average_extraction_time'] = (
                    (self.stats['average_extraction_time'] * (total_successful - 1) + extraction_time) / total_successful
                )

                log_info(self.log_path, f"✅ Successfully extracted: {extracted_content.get('title', 'Unknown')[:50]} ({extraction_time:.2f}s)")

                return extracted_content

        except Exception as e:
            error_msg = f"Crawl4AI extraction error: {str(e)}"
            log_error(self.log_path, f"❌ {error_msg}")
            self.stats['failed_extractions'] += 1
            return self._create_error_result(url, error_msg, time.time() - start_time)

    def _process_crawl_result(self, result, url: str) -> Dict[str, Any]:
        """Process Crawl4AI result into Atlas format."""
        try:
            # Extract metadata
            title = result.metadata.get('title', 'Unknown Title')
            description = result.metadata.get('description', '')
            author = result.metadata.get('author', '')
            published_date = result.metadata.get('published_time', '')

            # Content extraction
            markdown_content = result.markdown or ''
            cleaned_html = result.cleaned_html or ''

            # Links and media
            internal_links = result.links.get('internal', [])
            external_links = result.links.get('external', [])
            images = result.media.get('images', [])

            # Word count and reading time
            word_count = len(markdown_content.split()) if markdown_content else 0
            reading_time_minutes = max(1, word_count // 200)  # ~200 WPM

            # Create structured result
            return {
                'success': True,
                'url': url,
                'title': title,
                'content': markdown_content,
                'html': cleaned_html,
                'metadata': {
                    'description': description,
                    'author': author,
                    'published_date': published_date,
                    'word_count': word_count,
                    'reading_time_minutes': reading_time_minutes,
                    'extraction_method': 'crawl4ai',
                    'page_type': self._infer_page_type(result),
                    'content_quality': self._assess_content_quality(markdown_content, title),
                    'extraction_timestamp': datetime.now().isoformat(),
                    'is_cached': getattr(result, 'is_cached', False)
                },
                'links': {
                    'internal': internal_links[:20],  # Limit to prevent bloat
                    'external': external_links[:20]
                },
                'media': {
                    'images': [img for img in images[:10] if self._is_content_image(img)]  # Filter and limit
                },
                'structured_data': self._extract_structured_data(result),
                'error': None,
                'processing_time': 0  # Will be set by caller
            }

        except Exception as e:
            return self._create_error_result(url, f"Result processing error: {str(e)}", 0)

    def _infer_page_type(self, result) -> str:
        """Infer the type of content page."""
        url = result.url.lower()
        content = (result.markdown or '').lower()

        if any(pattern in url for pattern in ['blog', 'post', 'article', 'news']):
            return 'article'
        elif any(pattern in url for pattern in ['podcast', 'episode', 'show']):
            return 'podcast'
        elif any(pattern in url for pattern in ['video', 'watch', 'youtube', 'vimeo']):
            return 'video'
        elif any(pattern in content for pattern in ['transcript', 'episode', 'podcast']):
            return 'podcast_transcript'
        elif len(content.split()) > 500:
            return 'long_form_content'
        else:
            return 'web_page'

    def _assess_content_quality(self, content: str, title: str) -> Dict[str, Any]:
        """Assess the quality of extracted content."""
        if not content:
            return {'score': 0.0, 'issues': ['no_content']}

        word_count = len(content.split())
        char_count = len(content)

        quality_indicators = {
            'sufficient_length': word_count >= 100,
            'good_title': len(title) > 10 and len(title) < 200,
            'paragraph_structure': content.count('\n\n') >= 2,
            'not_just_navigation': 'home' not in content.lower()[:200] or word_count > 200
        }

        score = sum(quality_indicators.values()) / len(quality_indicators)

        issues = []
        if word_count < 50:
            issues.append('very_short_content')
        if word_count < 100:
            issues.append('short_content')
        if not quality_indicators['paragraph_structure']:
            issues.append('poor_structure')
        if char_count / max(word_count, 1) < 4:
            issues.append('truncated_words')

        return {
            'score': score,
            'word_count': word_count,
            'char_count': char_count,
            'issues': issues,
            'indicators': quality_indicators
        }

    def _is_content_image(self, image: Dict) -> bool:
        """Filter out decorative/navigation images."""
        src = image.get('src', '').lower()
        alt = image.get('alt', '').lower()

        # Skip small images, icons, logos, etc.
        skip_patterns = ['icon', 'logo', 'avatar', 'button', 'arrow', 'star', 'social']

        if any(pattern in src or pattern in alt for pattern in skip_patterns):
            return False

        # Prefer images with descriptive alt text
        return len(alt) > 10 or 'content' in src

    def _extract_structured_data(self, result) -> Dict[str, Any]:
        """Extract structured data from the crawl result."""
        structured = {}

        # Try to extract JSON-LD structured data
        if hasattr(result, 'extracted_content') and result.extracted_content:
            try:
                if isinstance(result.extracted_content, str):
                    structured['raw'] = result.extracted_content
                elif isinstance(result.extracted_content, dict):
                    structured = result.extracted_content
            except:
                pass

        return structured

    def _create_error_result(self, url: str, error_message: str, processing_time: float) -> Dict[str, Any]:
        """Create standardized error result."""
        return {
            'success': False,
            'url': url,
            'title': None,
            'content': None,
            'html': None,
            'metadata': {
                'extraction_method': 'crawl4ai',
                'extraction_timestamp': datetime.now().isoformat(),
                'error_details': error_message
            },
            'links': {'internal': [], 'external': []},
            'media': {'images': []},
            'structured_data': {},
            'error': error_message,
            'processing_time': processing_time
        }

    async def batch_extract(self, urls: List[str], max_concurrent: int = 3, delay_between_batches: float = 1.0) -> List[Dict[str, Any]]:
        """Extract multiple URLs with concurrency control and rate limiting."""
        log_info(self.log_path, f"🚀 Starting batch extraction of {len(urls)} URLs (max {max_concurrent} concurrent)")

        results = []

        # Process in batches to avoid overwhelming the target site
        for i in range(0, len(urls), max_concurrent):
            batch = urls[i:i + max_concurrent]

            log_info(self.log_path, f"📦 Processing batch {i//max_concurrent + 1}: {len(batch)} URLs")

            # Execute batch concurrently
            batch_tasks = [self.extract_article(url) for url in batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            # Process results and handle exceptions
            for url, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    error_result = self._create_error_result(url, str(result), 0)
                    results.append(error_result)
                    log_error(self.log_path, f"❌ Batch error for {url}: {str(result)}")
                else:
                    results.append(result)

            # Rate limiting between batches
            if delay_between_batches > 0 and i + max_concurrent < len(urls):
                log_info(self.log_path, f"⏳ Waiting {delay_between_batches}s before next batch...")
                await asyncio.sleep(delay_between_batches)

        # Final statistics
        successful = sum(1 for r in results if r.get('success', False))
        success_rate = (successful / len(results) * 100) if results else 0

        log_info(self.log_path, f"🎉 Batch extraction complete: {successful}/{len(results)} successful ({success_rate:.1f}%)")

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get extraction statistics."""
        total_requests = self.stats['total_requests']
        success_rate = (self.stats['successful_extractions'] / total_requests * 100) if total_requests > 0 else 0
        cache_rate = (self.stats['cache_hits'] / total_requests * 100) if total_requests > 0 else 0

        return {
            **self.stats,
            'success_rate_percent': success_rate,
            'cache_hit_rate_percent': cache_rate,
            'performance': {
                'avg_extraction_time_seconds': self.stats['average_extraction_time'],
                'cache_effectiveness': cache_rate > 20  # Consider cache effective if >20% hit rate
            }
        }


async def main():
    """Test the Crawl4AI fetcher."""
    import argparse

    parser = argparse.ArgumentParser(description='Test Crawl4AI Enhanced Fetcher')
    parser.add_argument('urls', nargs='+', help='URLs to extract')
    parser.add_argument('--batch', action='store_true', help='Use batch extraction')
    parser.add_argument('--concurrent', type=int, default=2, help='Max concurrent requests for batch')
    parser.add_argument('--delay', type=float, default=1.0, help='Delay between batches')

    args = parser.parse_args()

    try:
        config = load_config()
        fetcher = Crawl4AIFetcher(config)

        if args.batch:
            results = await fetcher.batch_extract(
                args.urls,
                max_concurrent=args.concurrent,
                delay_between_batches=args.delay
            )

            print(f"\n🎯 Batch Results:")
            for i, result in enumerate(results, 1):
                status = "✅" if result.get('success') else "❌"
                title = result.get('title', 'Unknown')[:50]
                print(f"  {i}. {status} {title}")
        else:
            for url in args.urls:
                result = await fetcher.extract_article(url)
                status = "✅" if result.get('success') else "❌"
                title = result.get('title', 'Error')
                word_count = result.get('metadata', {}).get('word_count', 0)

                print(f"\n{status} {title}")
                print(f"   URL: {url}")
                print(f"   Words: {word_count}")
                if not result.get('success'):
                    print(f"   Error: {result.get('error')}")

        # Print statistics
        stats = fetcher.get_stats()
        print(f"\n📊 Statistics:")
        print(f"   Success Rate: {stats['success_rate_percent']:.1f}%")
        print(f"   Cache Hit Rate: {stats['cache_hit_rate_percent']:.1f}%")
        print(f"   Avg Time: {stats['average_extraction_time']:.2f}s")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    if CRAWL4AI_AVAILABLE:
        asyncio.run(main())
    else:
        print("❌ Crawl4AI not available. Install with: pip install crawl4ai")
        sys.exit(1)