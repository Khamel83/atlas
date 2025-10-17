#!/usr/bin/env python3
"""
Enhanced Stratechery Deep Archive Scraper

Comprehensive historical extraction using multiple discovery methods:
- Archive.org snapshots of Stratechery
- Year-based archive pages
- Category/tag pages
- Sitemap discovery
- Search results pagination

This should find the missing ~400+ Stratechery articles.
"""

import os
import sys
import json
import time
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Set
import sqlite3
from urllib.parse import urljoin, urlparse
import feedparser
from bs4 import BeautifulSoup
import logging

# Add Atlas to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.config import load_config
from helpers.utils import log_info, log_error
from helpers.article_manager import ArticleManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StratecheryDeepScraper:
    """Comprehensive Stratechery archive discovery and extraction."""

    def __init__(self, config: Dict = None):
        """Initialize deep scraper with multiple discovery methods."""
        self.config = config or load_config()

        # Stratechery credentials from environment
        self.username = os.getenv('STRATECHERY_USERNAME')
        self.password = os.getenv('STRATECHERY_PASSWORD')
        self.base_url = os.getenv('STRATECHERY_BASE_URL', 'https://stratechery.com')

        if not all([self.username, self.password]):
            raise ValueError("Stratechery credentials not found in environment variables")

        # Initialize session for authenticated requests
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

        # Initialize Atlas components
        self.article_manager = ArticleManager(config)

        # Set up logging
        log_dir = self.config.get('log_directory', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        self.log_path = os.path.join(log_dir, 'stratechery_deep_scraper.log')

        # URL discovery storage
        self.discovered_urls = set()
        self.processed_urls = set()

        # Load existing URLs to avoid reprocessing
        self._load_existing_urls()

        # Statistics
        self.stats = {
            'urls_discovered': 0,
            'urls_extracted': 0,
            'new_articles': 0,
            'errors': 0,
            'start_time': datetime.now()
        }

    def _load_existing_urls(self):
        """Load existing Stratechery URLs from database."""
        try:
            with sqlite3.connect('data/atlas.db') as conn:
                cursor = conn.execute("SELECT DISTINCT url FROM content WHERE url LIKE '%stratechery%'")
                self.processed_urls = {row[0] for row in cursor.fetchall()}
            log_info(self.log_path, f"📚 Loaded {len(self.processed_urls)} existing Stratechery URLs")
        except Exception as e:
            log_error(self.log_path, f"Error loading existing URLs: {e}")
            self.processed_urls = set()

    def authenticate(self) -> bool:
        """Authenticate with Stratechery."""
        log_info(self.log_path, "🔐 Authenticating with Stratechery...")

        try:
            # Get login page first
            login_page = self.session.get(f"{self.base_url}/login/")
            if login_page.status_code != 200:
                log_error(self.log_path, f"Failed to access login page: {login_page.status_code}")
                return False

            # Extract any CSRF tokens or form data
            soup = BeautifulSoup(login_page.content, 'html.parser')
            login_form = soup.find('form')

            # Prepare login data
            login_data = {
                'username': self.username,
                'password': self.password
            }

            # Add any hidden form fields
            if login_form:
                for hidden_input in login_form.find_all('input', type='hidden'):
                    name = hidden_input.get('name')
                    value = hidden_input.get('value')
                    if name and value:
                        login_data[name] = value

            # Attempt login
            login_response = self.session.post(
                f"{self.base_url}/login/",
                data=login_data,
                allow_redirects=True
            )

            # Verify authentication
            if login_response.status_code == 200:
                test_response = self.session.get(f"{self.base_url}/all-content/")
                if test_response.status_code == 200 and ('member' in test_response.text.lower() or 'articles' in test_response.text.lower()):
                    log_info(self.log_path, "✅ Successfully authenticated")
                    return True

            log_error(self.log_path, f"Authentication failed: {login_response.status_code}")
            return False

        except Exception as e:
            log_error(self.log_path, f"Authentication error: {str(e)}")
            return False

    def discover_from_archive_org(self, start_year: int = 2013, end_year: int = 2025) -> Set[str]:
        """Discover URLs from Archive.org snapshots."""
        log_info(self.log_path, f"🏛️  Discovering from Archive.org ({start_year}-{end_year})...")

        discovered = set()

        try:
            # Query Archive.org CDX API for Stratechery snapshots
            cdx_url = "http://web.archive.org/cdx/search/cdx"
            params = {
                'url': 'stratechery.com/*',
                'matchType': 'prefix',
                'collapse': 'urlkey',
                'from': str(start_year),
                'to': str(end_year),
                'filter': 'statuscode:200',
                'limit': 10000  # Get lots of snapshots
            }

            response = requests.get(cdx_url, params=params, timeout=30)

            if response.status_code == 200:
                lines = response.text.strip().split('\n')

                for line in lines:
                    if line:
                        parts = line.split(' ')
                        if len(parts) >= 3:
                            original_url = parts[2]

                            # Filter for likely article URLs
                            if self._is_likely_article_url(original_url):
                                discovered.add(original_url)

                log_info(self.log_path, f"📦 Archive.org discovered: {len(discovered)} URLs")
            else:
                log_error(self.log_path, f"Archive.org request failed: {response.status_code}")

        except Exception as e:
            log_error(self.log_path, f"Archive.org discovery error: {str(e)}")

        return discovered

    def discover_from_year_archives(self, start_year: int = 2013, end_year: int = 2025) -> Set[str]:
        """Discover from year-based archive pages."""
        log_info(self.log_path, f"📅 Discovering from year archives ({start_year}-{end_year})...")

        discovered = set()

        for year in range(start_year, end_year + 1):
            try:
                # Try common year archive URL patterns
                year_urls = [
                    f"{self.base_url}/{year}/",
                    f"{self.base_url}/archives/{year}/",
                    f"{self.base_url}/content/{year}/",
                    f"{self.base_url}/year/{year}/"
                ]

                for year_url in year_urls:
                    response = self.session.get(year_url, timeout=10)

                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')

                        # Extract article links
                        for link in soup.find_all('a', href=True):
                            href = link.get('href')
                            if href:
                                full_url = urljoin(self.base_url, href)

                                if self._is_likely_article_url(full_url):
                                    discovered.add(full_url)

                        log_info(self.log_path, f"   📆 {year}: Found {len([u for u in discovered if f'/{year}/' in u])} URLs")
                        break  # Found working year archive

                    time.sleep(0.5)  # Rate limiting

            except Exception as e:
                log_error(self.log_path, f"Year {year} discovery error: {str(e)}")

        log_info(self.log_path, f"📦 Year archives discovered: {len(discovered)} URLs")
        return discovered

    def discover_from_sitemap(self) -> Set[str]:
        """Discover URLs from sitemap.xml."""
        log_info(self.log_path, "🗺️  Discovering from sitemap...")

        discovered = set()

        try:
            sitemap_urls = [
                f"{self.base_url}/sitemap.xml",
                f"{self.base_url}/sitemap_index.xml",
                f"{self.base_url}/wp-sitemap.xml"
            ]

            for sitemap_url in sitemap_urls:
                response = self.session.get(sitemap_url, timeout=10)

                if response.status_code == 200:
                    # Parse sitemap
                    soup = BeautifulSoup(response.content, 'xml')

                    # Extract URLs from sitemap
                    for loc in soup.find_all('loc'):
                        url = loc.get_text().strip()

                        if self._is_likely_article_url(url):
                            discovered.add(url)
                        elif 'sitemap' in url.lower():
                            # Follow sub-sitemaps
                            try:
                                sub_response = self.session.get(url, timeout=10)
                                if sub_response.status_code == 200:
                                    sub_soup = BeautifulSoup(sub_response.content, 'xml')
                                    for sub_loc in sub_soup.find_all('loc'):
                                        sub_url = sub_loc.get_text().strip()
                                        if self._is_likely_article_url(sub_url):
                                            discovered.add(sub_url)
                            except:
                                pass

                    log_info(self.log_path, f"📦 Sitemap discovered: {len(discovered)} URLs")
                    break  # Found working sitemap

                time.sleep(0.5)  # Rate limiting

        except Exception as e:
            log_error(self.log_path, f"Sitemap discovery error: {str(e)}")

        return discovered

    def discover_from_search_pagination(self, search_terms: List[str] = None) -> Set[str]:
        """Discover from internal search pagination."""
        log_info(self.log_path, "🔍 Discovering from search pagination...")

        if not search_terms:
            search_terms = ['2023', '2024', '2025', 'apple', 'google', 'meta', 'microsoft', 'ai']

        discovered = set()

        for term in search_terms:
            try:
                # Try search URL patterns
                search_urls = [
                    f"{self.base_url}/?s={term}",
                    f"{self.base_url}/search?q={term}",
                    f"{self.base_url}/search/{term}/"
                ]

                for search_url in search_urls:
                    page = 1
                    while page <= 10:  # Limit pagination depth
                        try:
                            paginated_url = f"{search_url}&page={page}" if '?' in search_url else f"{search_url}?page={page}"
                            response = self.session.get(paginated_url, timeout=10)

                            if response.status_code == 200:
                                soup = BeautifulSoup(response.content, 'html.parser')

                                # Extract article links
                                page_urls = set()
                                for link in soup.find_all('a', href=True):
                                    href = link.get('href')
                                    if href:
                                        full_url = urljoin(self.base_url, href)

                                        if self._is_likely_article_url(full_url):
                                            page_urls.add(full_url)
                                            discovered.add(full_url)

                                # Stop if no new URLs found
                                if not page_urls:
                                    break

                                page += 1
                                time.sleep(1)  # Rate limiting
                            else:
                                break

                        except Exception as e:
                            log_error(self.log_path, f"Search pagination error for {term} page {page}: {str(e)}")
                            break

                    break  # Found working search pattern

                time.sleep(1)  # Rate limiting between terms

            except Exception as e:
                log_error(self.log_path, f"Search term {term} discovery error: {str(e)}")

        log_info(self.log_path, f"📦 Search pagination discovered: {len(discovered)} URLs")
        return discovered

    def discover_from_category_pages(self) -> Set[str]:
        """Discover from category and tag pages."""
        log_info(self.log_path, "🏷️  Discovering from category pages...")

        discovered = set()

        try:
            # Common category/tag page patterns
            category_patterns = [
                f"{self.base_url}/category/",
                f"{self.base_url}/categories/",
                f"{self.base_url}/tag/",
                f"{self.base_url}/tags/"
            ]

            # Common categories/tags
            categories = [
                'articles', 'updates', 'analysis', 'tech', 'strategy',
                'apple', 'google', 'meta', 'microsoft', 'amazon',
                'ai', 'social-media', 'streaming', 'gaming'
            ]

            for pattern in category_patterns:
                for category in categories:
                    try:
                        category_url = urljoin(pattern, category + '/')
                        response = self.session.get(category_url, timeout=10)

                        if response.status_code == 200:
                            soup = BeautifulSoup(response.content, 'html.parser')

                            # Extract article links
                            for link in soup.find_all('a', href=True):
                                href = link.get('href')
                                if href:
                                    full_url = urljoin(self.base_url, href)

                                    if self._is_likely_article_url(full_url):
                                        discovered.add(full_url)

                        time.sleep(0.5)  # Rate limiting

                    except Exception as e:
                        # Silent fail for category discovery
                        pass

        except Exception as e:
            log_error(self.log_path, f"Category discovery error: {str(e)}")

        log_info(self.log_path, f"📦 Category pages discovered: {len(discovered)} URLs")
        return discovered

    def _is_likely_article_url(self, url: str) -> bool:
        """Check if URL is likely a Stratechery article."""
        if not url or 'stratechery.com' not in url:
            return False

        # Skip non-content URLs
        skip_patterns = [
            '/login', '/register', '/account', '/subscription', '/payment',
            '/contact', '/about', '/privacy', '/terms', '/wp-admin',
            '/wp-content', '/wp-includes', '/feed', '/rss', '/sitemap',
            '.xml', '.jpg', '.png', '.gif', '.css', '.js', '.pdf',
            '/category/', '/tag/', '/author/', '/search', '/page/',
            '#', '?replytocom', '?share', '?utm'
        ]

        if any(pattern in url.lower() for pattern in skip_patterns):
            return False

        # Look for article indicators
        article_indicators = [
            '/2013/', '/2014/', '/2015/', '/2016/', '/2017/', '/2018/',
            '/2019/', '/2020/', '/2021/', '/2022/', '/2023/', '/2024/', '/2025/',
            'article', 'update', 'interview', 'analysis'
        ]

        return any(indicator in url.lower() for indicator in article_indicators)

    def run_comprehensive_discovery(self) -> Dict:
        """Run all discovery methods and return comprehensive results."""
        log_info(self.log_path, "🚀 Starting comprehensive Stratechery discovery...")

        if not self.authenticate():
            return {'success': False, 'error': 'Authentication failed'}

        all_discovered = set()

        try:
            # Method 1: Archive.org
            archive_urls = self.discover_from_archive_org()
            all_discovered.update(archive_urls)

            # Method 2: Year archives
            year_urls = self.discover_from_year_archives()
            all_discovered.update(year_urls)

            # Method 3: Sitemap
            sitemap_urls = self.discover_from_sitemap()
            all_discovered.update(sitemap_urls)

            # Method 4: Search pagination
            search_urls = self.discover_from_search_pagination()
            all_discovered.update(search_urls)

            # Method 5: Category pages
            category_urls = self.discover_from_category_pages()
            all_discovered.update(category_urls)

            # Filter out already processed URLs
            new_urls = all_discovered - self.processed_urls

            log_info(self.log_path, f"📊 Discovery Summary:")
            log_info(self.log_path, f"   Total URLs discovered: {len(all_discovered)}")
            log_info(self.log_path, f"   Already processed: {len(all_discovered & self.processed_urls)}")
            log_info(self.log_path, f"   New URLs to process: {len(new_urls)}")

            return {
                'success': True,
                'total_discovered': len(all_discovered),
                'already_processed': len(all_discovered & self.processed_urls),
                'new_urls': list(new_urls),
                'discovery_breakdown': {
                    'archive_org': len(archive_urls),
                    'year_archives': len(year_urls),
                    'sitemap': len(sitemap_urls),
                    'search_pagination': len(search_urls),
                    'category_pages': len(category_urls)
                }
            }

        except Exception as e:
            log_error(self.log_path, f"💥 Discovery error: {str(e)}")
            return {'success': False, 'error': str(e)}


def main():
    """Main execution function."""
    import argparse

    parser = argparse.ArgumentParser(description='Stratechery Deep Archive Discovery')
    parser.add_argument('--discover-only', action='store_true', help='Only discover URLs, don\'t extract')
    parser.add_argument('--max-urls', type=int, help='Maximum URLs to process')

    args = parser.parse_args()

    try:
        config = load_config()
        scraper = StratecheryDeepScraper(config)

        results = scraper.run_comprehensive_discovery()

        if results['success']:
            print(f"\n🎯 Deep Discovery Results:")
            print(f"   Total URLs discovered: {results['total_discovered']}")
            print(f"   New URLs to process: {len(results['new_urls'])}")
            print(f"\n📋 Discovery Breakdown:")
            for method, count in results['discovery_breakdown'].items():
                print(f"   {method}: {count}")

            if not args.discover_only and results['new_urls']:
                print(f"\n🔄 Would extract {min(len(results['new_urls']), args.max_urls or len(results['new_urls']))} new articles")
                print("Use the regular stratechery_extractor.py to process these URLs")
        else:
            print(f"\n❌ Discovery failed: {results.get('error')}")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()