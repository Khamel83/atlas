#!/usr/bin/env python3
"""
Universal URL Processor - Log-Stream Version
High-performance processing of the massive URL queue using log-stream architecture
"""

import sqlite3
import json
import time
import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import requests
from urllib.parse import urlparse
import os

# Import our log-stream logger
from oos_logger import get_logger

class UniversalURLProcessor:
    """High-performance URL processor using log-stream architecture"""

    def __init__(self, db_path: str = "data/atlas.db", log_file: str = "universal_url_operations.log"):
        self.logger = get_logger(log_file)
        self.db_path = db_path
        self.processed_urls = set()
        self.load_processed_urls()

        # Processing configuration - SPEED OPTIMIZED
        self.batch_size = 100  # Double batch size
        self.processing_interval = 0.5  # Faster between batches
        self.timeout = 15  # Reduce timeout per URL

        # Article sources configuration
        self.article_sources = self._load_article_sources()

        self.logger.metrics("system", "universal_processor", {
            "event": "startup",
            "db_path": db_path,
            "batch_size": self.batch_size,
            "article_sources": len(self.article_sources)
        })

    def _load_article_sources(self) -> List[Dict[str, Any]]:
        """Load article sources configuration"""
        try:
            with open('config/article_sources.json', 'r') as f:
                config = json.load(f)
                return [s for s in config['sources'] if s.get('enabled', True)]
        except Exception as e:
            self.logger.fail("system", "config_loader", "article_sources", {"error": str(e)})
            return []

    def load_processed_urls(self):
        """Load already processed URLs from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT json_extract(data, '$.url') as url
                    FROM worker_jobs
                    WHERE type = 'url_processing' AND status = 'completed'
                    ORDER BY completed_at DESC
                    LIMIT 10000
                ''')
                self.processed_urls = {row[0] for row in cursor.fetchall() if row[0]}
        except Exception as e:
            self.logger.fail("system", "url_loader", "processed_urls", {"error": str(e)})

    def get_next_batch(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get next batch of URLs to process"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT id, data, priority
                    FROM worker_jobs
                    WHERE type = 'url_processing' AND status = 'pending'
                    ORDER BY priority DESC, created_at ASC
                    LIMIT ?
                ''', (limit,))

                jobs = []
                for row in cursor.fetchall():
                    job_id, data_json, priority = row
                    try:
                        job_data = json.loads(data_json)
                        url = job_data.get('url')
                        # Skip URL filtering for now to debug
                        if url:  # and url not in self.processed_urls:
                            jobs.append({
                                'job_id': job_id,
                                'url': url,
                                'source': job_data.get('source', 'unknown'),
                                'priority': priority,
                                'data': job_data
                            })
                    except Exception as e:
                        self.logger.fail("system", "job_parser", job_id, {"error": str(e)})

                print(f"DEBUG: Found {len(jobs)} jobs from query")
                return jobs

        except Exception as e:
            self.logger.fail("system", "batch_retrieval", "database", {"error": str(e)})
            return []

    def process_url(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single URL"""
        job_id = job['job_id']
        url = job['url']
        source = job['source']

        self.logger.process("url", source, job_id, {
            "action": "process_url",
            "url": url,
            "priority": job['priority']
        })

        try:
            # Try different strategies based on URL patterns
            content = self._fetch_with_strategies(url, job)

            if content:
                # Save content
                filename = self._save_content(url, content)
                if filename:
                    # Mark job as completed
                    self._mark_job_completed(job_id, {
                        "file_path": filename,
                        "content_length": len(content),
                        "word_count": len(content.split())
                    })

                    self.logger.complete("url", source, job_id, {
                        "file_path": filename,
                        "word_count": len(content.split()),
                        "content_length": len(content)
                    })

                    return {"success": True, "file_path": filename}
                else:
                    raise Exception("Failed to save content")
            else:
                raise Exception("No content extracted")

        except Exception as e:
            self._mark_job_failed(job_id, str(e))
            self.logger.fail("url", source, job_id, {
                "error": str(e),
                "url": url
            })
            return {"success": False, "error": str(e)}

    def _fetch_with_strategies(self, url: str, job: Dict[str, Any]) -> Optional[str]:
        """Try different strategies to fetch URL content"""
        strategies = [
            self._direct_fetch,
            self._paywall_bypass_fetch,
            self._archive_fetch,
            self._playwright_fetch
        ]

        for strategy in strategies:
            try:
                content = strategy(url, job)
                if content and len(content.strip()) > 100:  # Minimum content threshold
                    return content
            except Exception as e:
                self.logger.process("url", job['source'], job['job_id'], {
                    "strategy": strategy.__name__,
                    "error": str(e),
                    "url": url
                })
                continue

        return None

    def _direct_fetch(self, url: str, job: Dict[str, Any]) -> Optional[str]:
        """Direct HTTP fetch"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }

            response = requests.get(url, timeout=self.timeout, headers=headers)
            response.raise_for_status()

            # Extract main content (simplified)
            content = self._extract_main_content(response.text, url)
            return content

        except Exception as e:
            raise Exception(f"Direct fetch failed: {e}")

    def _paywall_bypass_fetch(self, url: str, job: Dict[str, Any]) -> Optional[str]:
        """Try paywall bypass services"""
        try:
            # Try different user agents and headers
            headers = {
                'User-Agent': 'Googlebot/2.1 (+http://www.google.com/bot.html)',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }

            response = requests.get(url, timeout=self.timeout, headers=headers)
            response.raise_for_status()

            content = self._extract_main_content(response.text, url)
            return content

        except Exception as e:
            raise Exception(f"Paywall bypass failed: {e}")

    def _archive_fetch(self, url: str, job: Dict[str, Any]) -> Optional[str]:
        """Try archive services"""
        try:
            # Try archive.today
            archive_url = f"https://archive.today/{url}"
            response = requests.get(archive_url, timeout=self.timeout)
            response.raise_for_status()

            content = self._extract_main_content(response.text, url)
            return content

        except Exception as e:
            raise Exception(f"Archive fetch failed: {e}")

    def _playwright_fetch(self, url: str, job: Dict[str, Any]) -> Optional[str]:
        """Headless browser fetch (if available)"""
        try:
            # This would require playwright installation
            # For now, return None to skip
            return None
        except Exception as e:
            raise Exception(f"Playwright fetch failed: {e}")

    def _extract_main_content(self, html: str, url: str) -> str:
        """Extract main content from HTML (simplified)"""
        try:
            # Very basic content extraction
            # In reality, you'd use something like readability or newspaper3k

            # Remove script and style tags
            import re
            html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
            html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)

            # Extract text
            text = re.sub(r'<[^>]+>', ' ', html)
            text = re.sub(r'\s+', ' ', text).strip()

            # Basic quality check
            if len(text) < 200:
                return None

            # Create structured content
            content = f"# {self._get_title_from_url(url)}\n\n"
            content += f"**Source**: {url}\n"
            content += f"**Extracted**: {datetime.now(timezone.utc).isoformat()}\n\n"
            content += "---\n\n"
            content += text[:10000]  # Limit content size

            return content

        except Exception as e:
            return None

    def _get_title_from_url(self, url: str) -> str:
        """Extract title from URL"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.replace('www.', '')
            path_parts = [p for p in parsed.path.split('/') if p]
            if path_parts:
                title = path_parts[-1].replace('-', ' ').replace('_', ' ').title()
            else:
                title = domain
            return title
        except:
            return "Untitled"

    def _save_content(self, url: str, content: str) -> Optional[str]:
        """Save content to file"""
        try:
            # Create safe filename from URL
            safe_url = url.replace('://', '_').replace('/', '_').replace('?', '_').replace('&', '_')[:100]
            filename = f"content/markdown/url_{safe_url}.md"

            os.makedirs("content/markdown", exist_ok=True)

            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)

            return filename

        except Exception as e:
            self.logger.fail("system", "content_saver", url, {"error": str(e)})
            return None

    def _mark_job_completed(self, job_id: str, result_data: Dict[str, Any]):
        """Mark job as completed in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    UPDATE worker_jobs
                    SET status = 'completed', result = ?, completed_at = ?
                    WHERE id = ?
                ''', (json.dumps(result_data), datetime.now(timezone.utc).isoformat(), job_id))
                conn.commit()

                # Add to processed URLs set
                url_data = json.loads(conn.execute('SELECT data FROM worker_jobs WHERE id = ?', (job_id,)).fetchone()[0])
                url = url_data.get('url')
                if url:
                    self.processed_urls.add(url)

        except Exception as e:
            self.logger.fail("system", "job_updater", job_id, {"error": str(e)})

    def _mark_job_failed(self, job_id: str, error: str):
        """Mark job as failed in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    UPDATE worker_jobs
                    SET status = 'failed', result = ?
                    WHERE id = ?
                ''', (json.dumps({"error": error}), job_id))
                conn.commit()

        except Exception as e:
            self.logger.fail("system", "job_updater", job_id, {"error": str(e)})

    def process_batch(self, limit: int = 50) -> Dict[str, Any]:
        """Process a batch of URLs"""
        start_time = time.time()

        self.logger.metrics("batch_processor", f"batch_{int(time.time())}", {
            "action": "start_batch",
            "limit": limit,
            "start_time": datetime.now(timezone.utc).isoformat()
        })

        # Get next batch
        jobs = self.get_next_batch(limit)
        if not jobs:
            self.logger.metrics("batch_processor", f"batch_{int(time.time())}", {
                "action": "no_jobs",
                "message": "No pending jobs found"
            })
            return {"discovered": 0, "success": 0, "failed": 0, "duration": 0}

        # Process jobs
        success_count = 0
        fail_count = 0

        for job in jobs:
            result = self.process_url(job)
            if result.get("success"):
                success_count += 1
            else:
                fail_count += 1

            # Minimal delay between requests
            time.sleep(0.05)  # Cut delay in half

        end_time = time.time()
        duration = end_time - start_time

        self.logger.metrics("batch_processor", f"batch_{int(time.time())}", {
            "action": "complete_batch",
            "discovered": len(jobs),
            "success": success_count,
            "failed": fail_count,
            "duration_seconds": duration,
            "urls_per_second": len(jobs) / duration if duration > 0 else 0,
            "end_time": datetime.now(timezone.utc).isoformat()
        })

        return {
            'discovered': len(jobs),
            'success': success_count,
            'failed': fail_count,
            'duration': duration,
            'ups': len(jobs) / duration if duration > 0 else 0
        }

    def run_continuous(self):
        """Run continuous processing"""
        print("🚀 Universal URL Processor Starting...")
        print(f"📊 Article sources configured: {len(self.article_sources)}")
        print(f"📝 Processing batch size: {self.batch_size}")

        batch_count = 0
        while True:
            try:
                batch_count += 1
                print(f"\n🔄 Processing URL batch #{batch_count}")

                result = self.process_batch(self.batch_size)

                print(f"📈 Batch Results:")
                print(f"   Discovered: {result['discovered']}")
                print(f"   Success: {result['success']}")
                print(f"   Failed: {result['failed']}")
                print(f"   Duration: {result['duration']:.2f}s")
                print(f"   URLs/sec: {result['ups']:.2f}")

                # Sleep between batches - OPTIMIZED
                if result['discovered'] > 0:
                    sleep_time = 2  # 2 seconds between batches with work
                else:
                    sleep_time = 10  # 10 seconds between empty batches

                print(f"😴 Sleeping {sleep_time}s before next batch...")
                time.sleep(sleep_time)

            except KeyboardInterrupt:
                print("\n🛑 Stopping Universal URL Processor")
                break
            except Exception as e:
                print(f"❌ Error in batch processing: {e}")
                time.sleep(60)  # Wait before retrying

def main():
    """Main entry point"""
    processor = UniversalURLProcessor()

    # Check queue status first
    from helpers.unified_ingestion import get_ingestion_status
    status = get_ingestion_status()

    print("🚀 UNIVERSAL URL PROCESSOR - LOG-STREAM VERSION")
    print("=" * 60)
    print(f"📊 Current Queue Status:")
    print(f"   Total Jobs: {status['total_jobs']:,}")
    print(f"   Pending: {status['pending']:,}")
    print(f"   Running: {status['running']:,}")
    print(f"   Completed: {status['completed']:,}")
    print(f"   Failed: {status['failed']:,}")

    if status['pending'] > 0:
        print(f"\n🎯 Starting continuous processing of {status['pending']:,} URLs...")
        processor.run_continuous()
    else:
        print("\n✅ No pending URLs to process")

if __name__ == "__main__":
    main()