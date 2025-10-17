#!/usr/bin/env python3
"""
Stratechery Historical Archive Fixer - Phase B2.3
Complete the Stratechery historical archive extraction.
"""

import os
import json
import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import requests
from bs4 import BeautifulSoup
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StratecheryArchiveFixer:
    """Fix and complete Stratechery historical archive."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize Stratechery archive fixer."""
        self.config = config or {}
        self.db_path = self.config.get('db_path', 'data/atlas.db')
        self.output_dir = Path(self.config.get('output_dir', 'output'))
        self.delay = self.config.get('delay_seconds', 2.0)

        # Stratechery authentication if available
        self.stratechery_auth = {
            'username': self.config.get('stratechery_username'),
            'password': self.config.get('stratechery_password')
        }

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

    def analyze_existing_stratechery_content(self) -> Dict[str, Any]:
        """Analyze existing Stratechery content in the database."""
        if not os.path.exists(self.db_path):
            return {'error': 'Database not found'}

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Find Stratechery content
        cursor.execute("""
            SELECT COUNT(*) as total,
                   MIN(created_at) as earliest,
                   MAX(created_at) as latest,
                   AVG(LENGTH(content)) as avg_length
            FROM content
            WHERE url LIKE '%stratechery.com%'
               OR json_extract(metadata, '$.domain') = 'stratechery.com'
        """)

        stats = cursor.fetchone()

        # Get sample URLs to check completeness
        cursor.execute("""
            SELECT url, title, LENGTH(content) as content_length, created_at
            FROM content
            WHERE url LIKE '%stratechery.com%'
               OR json_extract(metadata, '$.domain') = 'stratechery.com'
            ORDER BY created_at DESC
            LIMIT 20
        """)

        sample_articles = cursor.fetchall()

        # Check for incomplete content (short articles that should be longer)
        cursor.execute("""
            SELECT COUNT(*) as incomplete_count
            FROM content
            WHERE (url LIKE '%stratechery.com%' OR json_extract(metadata, '$.domain') = 'stratechery.com')
              AND LENGTH(content) < 1000
        """)

        incomplete_stats = cursor.fetchone()

        conn.close()

        return {
            'total_articles': stats[0] if stats[0] else 0,
            'earliest_date': stats[1],
            'latest_date': stats[2],
            'average_length': int(stats[3]) if stats[3] else 0,
            'incomplete_articles': incomplete_stats[0] if incomplete_stats[0] else 0,
            'sample_articles': [
                {
                    'url': row[0],
                    'title': row[1],
                    'content_length': row[2],
                    'created_at': row[3]
                }
                for row in sample_articles
            ]
        }

    def authenticate_stratechery(self) -> bool:
        """Authenticate with Stratechery if credentials are available."""
        if not self.stratechery_auth['username'] or not self.stratechery_auth['password']:
            logger.info("No Stratechery credentials provided, will use public content only")
            return False

        try:
            # Get login page
            login_url = 'https://stratechery.com/wp-login.php'
            response = self.session.get(login_url)

            # Parse login form
            soup = BeautifulSoup(response.text, 'html.parser')

            # Submit login
            login_data = {
                'log': self.stratechery_auth['username'],
                'pwd': self.stratechery_auth['password'],
                'wp-submit': 'Log In',
                'redirect_to': 'https://stratechery.com/',
                'testcookie': '1'
            }

            response = self.session.post(login_url, data=login_data)

            # Check if login successful
            if 'wp-admin' in response.url or 'dashboard' in response.text.lower():
                logger.info("✅ Successfully authenticated with Stratechery")
                return True
            else:
                logger.warning("❌ Stratechery authentication failed")
                return False

        except Exception as e:
            logger.error(f"Error authenticating with Stratechery: {e}")
            return False

    def discover_missing_articles(self) -> List[Dict[str, Any]]:
        """Discover missing Stratechery articles from archives and sitemap."""
        missing_articles = []

        try:
            # Try to get sitemap
            sitemap_urls = [
                'https://stratechery.com/sitemap.xml',
                'https://stratechery.com/sitemap_index.xml',
                'https://stratechery.com/post-sitemap.xml'
            ]

            for sitemap_url in sitemap_urls:
                try:
                    response = self.session.get(sitemap_url, timeout=30)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'xml')

                        # Extract URLs from sitemap
                        urls = []
                        for loc in soup.find_all('loc'):
                            url = loc.text.strip()
                            if 'stratechery.com' in url and '/2' in url:  # Likely an article
                                urls.append(url)

                        logger.info(f"Found {len(urls)} URLs in {sitemap_url}")

                        # Check which URLs we don't have
                        if urls:
                            missing_articles.extend(self._check_missing_urls(urls))
                            break  # Success, don't try other sitemaps

                except Exception as e:
                    logger.warning(f"Failed to get sitemap {sitemap_url}: {e}")
                    continue

            # If sitemap approach failed, try archive pages
            if not missing_articles:
                missing_articles = self._discover_from_archives()

        except Exception as e:
            logger.error(f"Error discovering missing articles: {e}")

        return missing_articles

    def _check_missing_urls(self, urls: List[str]) -> List[Dict[str, Any]]:
        """Check which URLs are missing from our database."""
        if not os.path.exists(self.db_path):
            return [{'url': url} for url in urls]

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        missing = []
        for url in urls:
            cursor.execute("SELECT COUNT(*) FROM content WHERE url = ?", (url,))
            if cursor.fetchone()[0] == 0:
                missing.append({'url': url})

        conn.close()
        return missing

    def _discover_from_archives(self) -> List[Dict[str, Any]]:
        """Discover articles from Stratechery archive pages."""
        archive_articles = []

        try:
            # Try to access archive pages for recent years
            current_year = datetime.now().year
            for year in range(current_year, current_year - 5, -1):  # Last 5 years
                archive_url = f'https://stratechery.com/{year}/'

                try:
                    response = self.session.get(archive_url, timeout=30)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')

                        # Look for article links
                        links = soup.find_all('a', href=True)
                        for link in links:
                            href = link['href']
                            if ('stratechery.com' in href and f'/{year}/' in href and
                                not any(x in href for x in ['#', 'comment', 'tag', 'category'])):

                                # Extract title if available
                                title = link.get_text().strip()
                                if len(title) > 5:  # Avoid navigation links
                                    archive_articles.append({
                                        'url': href,
                                        'title': title,
                                        'year': year
                                    })

                        logger.info(f"Found {len([a for a in archive_articles if a['year'] == year])} articles for {year}")
                        time.sleep(self.delay)  # Rate limiting

                except Exception as e:
                    logger.warning(f"Failed to get archive for {year}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error discovering from archives: {e}")

        # Remove duplicates
        seen_urls = set()
        unique_articles = []
        for article in archive_articles:
            if article['url'] not in seen_urls:
                seen_urls.add(article['url'])
                unique_articles.append(article)

        return self._check_missing_urls([a['url'] for a in unique_articles])

    def fix_incomplete_articles(self) -> Dict[str, Any]:
        """Fix articles that were incompletely extracted."""
        if not os.path.exists(self.db_path):
            return {'error': 'Database not found'}

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Find incomplete articles (very short content)
        cursor.execute("""
            SELECT id, url, title, LENGTH(content) as content_length
            FROM content
            WHERE (url LIKE '%stratechery.com%' OR json_extract(metadata, '$.domain') = 'stratechery.com')
              AND LENGTH(content) < 1000
            ORDER BY created_at DESC
            LIMIT 50
        """)

        incomplete_articles = cursor.fetchall()
        conn.close()

        results = {
            'found_incomplete': len(incomplete_articles),
            'fixed': 0,
            'failed': 0,
            'errors': []
        }

        logger.info(f"🔧 Found {len(incomplete_articles)} incomplete Stratechery articles")

        # Try to re-extract these articles
        from helpers.enhanced_content_extraction import EnhancedContentExtractor
        extractor = EnhancedContentExtractor()

        for article in incomplete_articles:
            article_id, url, title, content_length = article

            try:
                logger.info(f"   Fixing: {title} ({content_length} chars)")

                # Re-extract with enhanced methods
                extraction_result = extractor.extract_content(url,
                    strategies=['direct_requests', 'playwright', 'mercury_parser'])

                new_content = extraction_result.get('content', '')
                if len(new_content) > content_length * 2:  # Significantly more content
                    # Update the database
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()

                    updated_metadata = {
                        'extraction_method': extraction_result.get('extraction_strategy', 'enhanced'),
                        'content_length': len(new_content),
                        'fixed_at': datetime.now().isoformat()
                    }

                    cursor.execute("""
                        UPDATE content
                        SET content = ?,
                            metadata = json_patch(metadata, ?)
                        WHERE id = ?
                    """, (new_content, json.dumps(updated_metadata), article_id))

                    conn.commit()
                    conn.close()

                    results['fixed'] += 1
                    logger.info(f"   ✅ Fixed: {len(new_content)} chars (was {content_length})")
                else:
                    results['failed'] += 1
                    logger.warning(f"   ⚠️ No improvement: {len(new_content)} chars")

                time.sleep(self.delay)  # Rate limiting

            except Exception as e:
                results['failed'] += 1
                results['errors'].append({'url': url, 'error': str(e)})
                logger.error(f"   ❌ Failed to fix {url}: {e}")

        return results

    def generate_stratechery_report(self) -> Dict[str, Any]:
        """Generate comprehensive Stratechery archive report."""
        logger.info("📊 Generating Stratechery Archive Report...")

        report = {
            'generated_at': datetime.now().isoformat(),
            'existing_content': self.analyze_existing_stratechery_content(),
            'authentication_status': 'not_attempted',
            'missing_articles': [],
            'fix_results': {}
        }

        # Try authentication if credentials available
        if self.stratechery_auth['username']:
            authenticated = self.authenticate_stratechery()
            report['authentication_status'] = 'success' if authenticated else 'failed'

        # Discover missing articles
        missing = self.discover_missing_articles()
        report['missing_articles'] = missing[:20]  # Limit for report

        # Fix incomplete articles
        fix_results = self.fix_incomplete_articles()
        report['fix_results'] = fix_results

        # Summary
        report['summary'] = {
            'total_existing': report['existing_content'].get('total_articles', 0),
            'incomplete_fixed': fix_results.get('fixed', 0),
            'missing_discovered': len(missing),
            'completion_estimate': self._calculate_completion_estimate(report)
        }

        return report

    def _calculate_completion_estimate(self, report: Dict[str, Any]) -> str:
        """Calculate estimated completion percentage."""
        existing = report['existing_content'].get('total_articles', 0)
        missing = len(report.get('missing_articles', []))

        if existing + missing > 0:
            completion = (existing / (existing + missing)) * 100
            return f"{completion:.1f}%"
        else:
            return "unknown"

def main():
    """Main function to fix Stratechery archive."""
    logger.info("🏛️ Stratechery Historical Archive Fixer")

    # Load config if available
    config = {}
    if os.path.exists('.env'):
        import os
        from dotenv import load_dotenv
        load_dotenv()

        config = {
            'stratechery_username': os.getenv('STRATECHERY_USERNAME'),
            'stratechery_password': os.getenv('STRATECHERY_PASSWORD')
        }

    fixer = StratecheryArchiveFixer(config)
    report = fixer.generate_stratechery_report()

    # Print report
    logger.info("📊 Stratechery Archive Report:")
    logger.info(f"   Existing articles: {report['summary']['total_existing']}")
    logger.info(f"   Incomplete fixed: {report['summary']['incomplete_fixed']}")
    logger.info(f"   Missing discovered: {report['summary']['missing_discovered']}")
    logger.info(f"   Estimated completion: {report['summary']['completion_estimate']}")

    # Save detailed report
    report_path = Path('docs/stratechery_archive_report.json')
    report_path.parent.mkdir(exist_ok=True)

    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)

    logger.info(f"📄 Detailed report saved to: {report_path}")

if __name__ == "__main__":
    main()