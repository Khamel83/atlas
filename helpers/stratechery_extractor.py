#!/usr/bin/env python3
"""
Stratechery Historical Content Extractor

One-time historical extraction of all Stratechery content including:
- All articles from the archive
- Podcast episodes
- Member-only content

This is a specialized extractor for complete historical backfill.
"""

import os
import sys
import json
import time
import requests
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
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


class StratecheryExtractor:
    """Complete historical extraction of Stratechery content."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize Stratechery extractor with authentication."""
        self.config = config or load_config()

        # Stratechery credentials from environment
        self.username = os.getenv('STRATECHERY_USERNAME')
        self.password = os.getenv('STRATECHERY_PASSWORD')
        self.base_url = os.getenv('STRATECHERY_BASE_URL', 'https://stratechery.com')
        self.all_content_url = os.getenv('STRATECHERY_ALL_CONTENT_URL', 'https://stratechery.com/all-content/')
        self.rss_feed = os.getenv('STRATECHERY_RSS_FEED')

        if not all([self.username, self.password]):
            raise ValueError("Stratechery credentials not found in environment variables")

        # Initialize session for authenticated requests
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

        # Initialize Atlas components
        self.article_manager = ArticleManager(config)

        # Set up logging
        log_dir = self.config.get('log_directory', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        self.log_path = os.path.join(log_dir, 'stratechery_extractor.log')

        # Database for tracking progress
        self.db_path = Path('data/stratechery_extraction.db')
        self._init_database()

        # Extraction statistics
        self.stats = {
            'articles_found': 0,
            'articles_extracted': 0,
            'podcasts_found': 0,
            'podcasts_extracted': 0,
            'errors': 0,
            'start_time': datetime.now()
        }

    def _init_database(self):
        """Initialize extraction tracking database."""
        self.db_path.parent.mkdir(exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS extraction_progress (
                    url TEXT PRIMARY KEY,
                    title TEXT,
                    content_type TEXT,
                    extracted_at TIMESTAMP,
                    success BOOLEAN,
                    error_message TEXT,
                    atlas_uid TEXT
                )
            ''')

            conn.execute('''
                CREATE TABLE IF NOT EXISTS extraction_stats (
                    run_id TEXT PRIMARY KEY,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    articles_found INTEGER,
                    articles_extracted INTEGER,
                    podcasts_found INTEGER,
                    podcasts_extracted INTEGER,
                    total_errors INTEGER
                )
            ''')

    def authenticate(self) -> bool:
        """Authenticate with Stratechery using credentials."""
        log_info(self.log_path, "Authenticating with Stratechery...")

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

            # Check if login was successful
            if login_response.status_code == 200:
                # Look for indicators of successful login
                if 'logout' in login_response.text.lower() or 'dashboard' in login_response.text.lower():
                    log_info(self.log_path, "Successfully authenticated with Stratechery")
                    return True
                else:
                    # Try alternate login indicators
                    test_response = self.session.get(self.all_content_url)
                    if test_response.status_code == 200 and 'member' in test_response.text.lower():
                        log_info(self.log_path, "Authentication verified via member content access")
                        return True

            log_error(self.log_path, f"Authentication failed: {login_response.status_code}")
            return False

        except Exception as e:
            log_error(self.log_path, f"Authentication error: {str(e)}")
            return False

    def extract_from_rss(self) -> List[Dict[str, Any]]:
        """Extract content URLs from RSS feed."""
        log_info(self.log_path, "Extracting URLs from RSS feed...")

        try:
            # Parse RSS feed
            feed = feedparser.parse(self.rss_feed)

            if not feed.entries:
                log_error(self.log_path, "No entries found in RSS feed")
                return []

            urls = []
            for entry in feed.entries:
                urls.append({
                    'url': entry.link,
                    'title': entry.title,
                    'published': entry.get('published', ''),
                    'summary': entry.get('summary', ''),
                    'content_type': 'article'  # Default, may be podcast
                })

            log_info(self.log_path, f"Found {len(urls)} items in RSS feed")
            self.stats['articles_found'] = len(urls)
            return urls

        except Exception as e:
            log_error(self.log_path, f"RSS extraction error: {str(e)}")
            return []

    def extract_from_archive(self) -> List[Dict[str, Any]]:
        """Extract all content URLs from the archive page."""
        log_info(self.log_path, "Extracting URLs from all-content archive...")

        try:
            response = self.session.get(self.all_content_url)
            if response.status_code != 200:
                log_error(self.log_path, f"Failed to access archive: {response.status_code}")
                return []

            soup = BeautifulSoup(response.content, 'html.parser')

            # Find all article links (adjust selector based on site structure)
            urls = []

            # Common patterns for Stratechery content
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                if not href:
                    continue

                # Make absolute URL
                if href.startswith('/'):
                    href = urljoin(self.base_url, href)

                # Filter for content URLs
                if (self.base_url in href and
                    any(pattern in href for pattern in ['/article/', '/post/', '/content/', '/2020/', '/2021/', '/2022/', '/2023/', '/2024/', '/2025/'])):

                    title = link.get_text(strip=True) or "Stratechery Article"

                    urls.append({
                        'url': href,
                        'title': title,
                        'content_type': 'article',
                        'source': 'archive'
                    })

            # Remove duplicates
            seen_urls = set()
            unique_urls = []
            for item in urls:
                if item['url'] not in seen_urls:
                    seen_urls.add(item['url'])
                    unique_urls.append(item)

            log_info(self.log_path, f"Found {len(unique_urls)} unique URLs in archive")
            self.stats['articles_found'] += len(unique_urls)
            return unique_urls

        except Exception as e:
            log_error(self.log_path, f"Archive extraction error: {str(e)}")
            return []

    def is_already_extracted(self, url: str) -> bool:
        """Check if content has already been extracted."""
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute(
                'SELECT success FROM extraction_progress WHERE url = ?',
                (url,)
            ).fetchone()
            return result is not None and result[0]

    def mark_extracted(self, url: str, title: str, content_type: str, success: bool, error_message: str = None, atlas_uid: str = None):
        """Mark content as extracted in progress database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO extraction_progress
                (url, title, content_type, extracted_at, success, error_message, atlas_uid)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (url, title, content_type, datetime.now(), success, error_message, atlas_uid))

    def extract_single_article(self, item: Dict[str, Any]) -> bool:
        """Extract a single article using ArticleManager."""
        url = item['url']
        title = item['title']

        log_info(self.log_path, f"Extracting: {title[:80]}...")

        try:
            # Use ArticleManager to process the article
            result = self.article_manager.process_article(url)

            if result and result.success:
                atlas_uid = getattr(result, 'uid', '') or result.url or ''
                log_info(self.log_path, f"✅ Successfully extracted: {title[:50]}")
                self.mark_extracted(url, title, 'article', True, atlas_uid=atlas_uid)
                self.stats['articles_extracted'] += 1
                return True
            else:
                error_msg = result.error if result else 'No result returned'
                log_error(self.log_path, f"❌ Failed to extract {title[:50]}: {error_msg}")
                self.mark_extracted(url, title, 'article', False, error_message=error_msg)
                self.stats['errors'] += 1
                return False

        except Exception as e:
            error_msg = str(e)
            log_error(self.log_path, f"❌ Exception extracting {title[:50]}: {error_msg}")
            self.mark_extracted(url, title, 'article', False, error_message=error_msg)
            self.stats['errors'] += 1
            return False

    def run_historical_extraction(self, max_articles: int = None, delay_seconds: float = 1.0) -> Dict[str, Any]:
        """Run complete historical extraction."""
        log_info(self.log_path, "🚀 Starting Stratechery historical extraction...")

        run_id = f"stratechery_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        try:
            # Step 1: Authenticate
            if not self.authenticate():
                log_error(self.log_path, "Authentication failed - cannot proceed")
                return {'success': False, 'error': 'Authentication failed'}

            # Step 2: Collect all content URLs
            all_urls = []

            # Get from RSS feed
            rss_urls = self.extract_from_rss()
            all_urls.extend(rss_urls)

            # Get from archive page
            archive_urls = self.extract_from_archive()
            all_urls.extend(archive_urls)

            # Remove duplicates
            seen_urls = set()
            unique_urls = []
            for item in all_urls:
                if item['url'] not in seen_urls:
                    seen_urls.add(item['url'])
                    unique_urls.append(item)

            total_found = len(unique_urls)
            log_info(self.log_path, f"📊 Total unique URLs found: {total_found}")

            # Apply limit if specified
            if max_articles and max_articles < total_found:
                unique_urls = unique_urls[:max_articles]
                log_info(self.log_path, f"🎯 Limited to first {max_articles} articles")

            # Step 3: Extract each article
            processed = 0
            for item in unique_urls:
                if self.is_already_extracted(item['url']):
                    log_info(self.log_path, f"⏭️  Skipping already extracted: {item['title'][:50]}")
                    continue

                self.extract_single_article(item)
                processed += 1

                # Rate limiting
                if delay_seconds > 0:
                    time.sleep(delay_seconds)

                # Progress update every 10 items
                if processed % 10 == 0:
                    log_info(self.log_path, f"📈 Progress: {processed}/{total_found} ({self.stats['articles_extracted']} successful)")

            # Final statistics
            end_time = datetime.now()
            duration = (end_time - self.stats['start_time']).total_seconds()

            # Save run statistics
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO extraction_stats
                    (run_id, start_time, end_time, articles_found, articles_extracted, podcasts_found, podcasts_extracted, total_errors)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    run_id, self.stats['start_time'], end_time,
                    self.stats['articles_found'], self.stats['articles_extracted'],
                    self.stats['podcasts_found'], self.stats['podcasts_extracted'],
                    self.stats['errors']
                ))

            final_stats = {
                'success': True,
                'run_id': run_id,
                'duration_seconds': duration,
                'articles_found': self.stats['articles_found'],
                'articles_extracted': self.stats['articles_extracted'],
                'errors': self.stats['errors'],
                'success_rate': (self.stats['articles_extracted'] / total_found * 100) if total_found > 0 else 0
            }

            log_info(self.log_path, f"🎉 Extraction complete! Stats: {final_stats}")
            return final_stats

        except Exception as e:
            log_error(self.log_path, f"💥 Critical error in extraction: {str(e)}")
            return {'success': False, 'error': str(e)}


def main():
    """Main execution function."""
    import argparse

    parser = argparse.ArgumentParser(description='Stratechery Historical Content Extractor')
    parser.add_argument('--max-articles', type=int, help='Maximum number of articles to extract (for testing)')
    parser.add_argument('--delay', type=float, default=1.0, help='Delay between requests in seconds')
    parser.add_argument('--test-auth', action='store_true', help='Test authentication only')

    args = parser.parse_args()

    try:
        config = load_config()
        extractor = StratecheryExtractor(config)

        if args.test_auth:
            success = extractor.authenticate()
            print(f"Authentication {'successful' if success else 'failed'}")
            return

        results = extractor.run_historical_extraction(
            max_articles=args.max_articles,
            delay_seconds=args.delay
        )

        print(f"\n🎯 Stratechery Extraction Results:")
        print(f"   Success: {results.get('success', False)}")
        print(f"   Articles Found: {results.get('articles_found', 0)}")
        print(f"   Articles Extracted: {results.get('articles_extracted', 0)}")
        print(f"   Success Rate: {results.get('success_rate', 0):.1f}%")
        print(f"   Duration: {results.get('duration_seconds', 0):.1f} seconds")
        print(f"   Errors: {results.get('errors', 0)}")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()