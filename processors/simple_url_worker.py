#!/usr/bin/env python3
"""
Simple URL Processing Worker - No complex dependencies
"""

import sqlite3
import json
import time
import logging
import requests
from datetime import datetime
import uuid
import hashlib
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimpleURLWorker:
    """Simple worker that just fetches URLs and stores basic content"""

    def __init__(self, db_path="atlas.db"):
        self.db_path = db_path
        self.worker_id = f"simple_worker_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.running = False
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def get_next_job(self):
        """Get next URL processing job from queue"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                UPDATE worker_jobs
                SET status = 'running', assigned_worker = ?, assigned_at = ?
                WHERE id = (
                    SELECT id FROM worker_jobs
                    WHERE status = 'pending' AND type = 'url_processing'
                    ORDER BY priority DESC, created_at ASC
                    LIMIT 1
                )
                RETURNING id, type, data, priority, status, created_at
            """, (self.worker_id, datetime.now().isoformat()))

            row = cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'type': row[1],
                    'data': json.loads(row[2]),
                    'priority': row[3],
                    'status': row[4],
                    'created_at': row[5]
                }
            return None

    def normalize_url(self, url):
        """Basic URL normalization for deduplication"""
        url = url.lower().strip()
        # Remove common tracking parameters
        for param in ['utm_', 'fbclid', 'gclid', '_ga', 'ref=']:
            if param in url:
                url = url.split(param)[0].rstrip('?&')
        return url

    def get_url_uid(self, url):
        """Generate stable UID for URL"""
        canonical = self.normalize_url(url)
        return hashlib.sha1(canonical.encode("utf-8")).hexdigest()[:16]

    def is_duplicate(self, url):
        """Check if URL already exists in database"""
        url_uid = self.get_url_uid(url)
        try:
            with sqlite3.connect('data/atlas.db') as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM content WHERE url LIKE ?", (f"%{url_uid}%",))
                count = cursor.fetchone()[0]
                return count > 0
        except:
            return False  # If check fails, proceed anyway

    def process_url_simple(self, url):
        """Simple URL processing - just fetch and return basic info"""
        try:
            # Check for duplicates first
            if self.is_duplicate(url):
                return {
                    'success': True,
                    'duplicate': True,
                    'message': 'URL already exists (duplicate)'
                }

            logger.info(f"Fetching: {url}")
            response = self.session.get(url, timeout=30, allow_redirects=True)
            response.raise_for_status()

            content = response.text[:5000]  # First 5K chars
            title = "Processed Article"

            # Try to extract title from HTML
            if '<title>' in content.lower():
                try:
                    start = content.lower().find('<title>') + 7
                    end = content.lower().find('</title>', start)
                    if start > 6 and end > start:
                        title = content[start:end].strip()[:200]
                except:
                    pass

            # Store in content database using correct schema
            try:
                with sqlite3.connect('data/atlas.db') as conn:
                    # Use the actual table schema (no 'id' column)
                    conn.execute("""
                        INSERT OR REPLACE INTO content
                        (url, title, content, content_type, metadata, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        url,
                        title,
                        content[:2000],  # Truncate content
                        'article',
                        '{}',  # Empty metadata JSON
                        datetime.now().isoformat(),
                        datetime.now().isoformat()
                    ))
                    conn.commit()
                    logger.info(f"💾 Saved to database: {title[:50]}...")
            except Exception as db_error:
                logger.error(f"❌ Database insert failed: {db_error}")
                # Don't fail the job due to DB issues, content was fetched successfully

            return {
                'success': True,
                'title': title,
                'content_length': len(content),
                'status_code': response.status_code,
                'content_id': url  # URL is the primary key/content_id
            }

        except requests.exceptions.Timeout:
            return {'success': False, 'error': 'Request timeout'}
        except requests.exceptions.RequestException as e:
            return {'success': False, 'error': f'Request failed: {str(e)}'}
        except Exception as e:
            return {'success': False, 'error': f'Processing error: {str(e)}'}

    def complete_job(self, job_id, result):
        """Mark job as completed"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE worker_jobs
                SET status = 'completed', completed_at = ?, result = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), json.dumps(result), job_id))
            conn.commit()

    def fail_job(self, job_id, error):
        """Mark job as failed"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE worker_jobs
                SET status = 'failed', completed_at = ?, result = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), str(error), job_id))
            conn.commit()

    def trigger_fallback(self, url, job_id, error):
        """Trigger Google Search fallback and requeue alternative URLs"""
        try:
            # Import Atlas's fallback system
            from helpers.google_search_fallback import search_with_google_fallback
            from helpers.unified_ingestion import submit_urls
            import asyncio

            # Extract search terms from failed URL
            from urllib.parse import urlparse
            parsed_url = urlparse(url)

            # Create search query from URL
            domain = parsed_url.netloc.replace('www.', '')
            path_parts = [part for part in parsed_url.path.split('/') if part and not part.isdigit()][:2]
            search_query = f"site:{domain} {' '.join(path_parts)}"

            logger.info(f"🔍 Triggering Google fallback for: {search_query}")

            # Run Google search fallback
            async def run_fallback():
                try:
                    result = await search_with_google_fallback(
                        query=search_query,
                        priority=1  # High priority for fallback searches
                    )

                    if result:
                        # Google fallback returns a single URL
                        found_urls = [result]
                        logger.info(f"🎯 Found alternative URL via Google search")

                        # Submit alternative URL back to unified queue
                        job_ids = submit_urls(
                            found_urls,
                            priority=80,  # Higher priority for fallback URLs
                            source=f"google_fallback_for_{domain}"
                        )

                        # Mark original job as completed with fallback info
                        fallback_result = {
                            'original_error': error,
                            'fallback_triggered': True,
                            'alternative_urls_queued': len(job_ids),
                            'job_ids': job_ids
                        }
                        self.complete_job(job_id, fallback_result)

                        logger.info(f"✅ Fallback complete: {len(job_ids)} alternatives queued for {url}")
                        return True
                    else:
                        logger.warning(f"❌ No alternatives found for: {url}")
                        self.fail_job(job_id, f"Fallback failed: {error}")
                        return False

                except Exception as fallback_error:
                    logger.error(f"❌ Fallback system failed: {fallback_error}")
                    self.fail_job(job_id, f"Fallback error: {str(fallback_error)}")
                    return False

            # Run the async fallback
            try:
                loop = asyncio.get_event_loop()
                return loop.run_until_complete(run_fallback())
            except RuntimeError:
                # Create new event loop if needed
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                return loop.run_until_complete(run_fallback())

        except Exception as e:
            logger.error(f"❌ Fallback system error: {e}")
            self.fail_job(job_id, f"Fallback system error: {str(e)}")
            return False

    def process_job(self, job):
        """Process a single job"""
        try:
            url = job['data']['url']
            source = job['data'].get('source', 'unknown')

            logger.info(f"Processing: {url} (source: {source})")

            result = self.process_url_simple(url)

            if result['success']:
                if result.get('duplicate'):
                    self.complete_job(job['id'], result)
                    logger.info(f"⚠️  Duplicate: {url} - {result['message']}")
                    return True
                else:
                    self.complete_job(job['id'], result)
                    logger.info(f"✅ Completed: {url} - {result.get('title', 'No title')[:50]}...")
                    return True
            else:
                # FAILED - trigger fallback pipeline
                logger.warning(f"🔄 Primary fetch failed: {url} - {result['error']}")
                self.trigger_fallback(url, job['id'], result['error'])
                return False

        except Exception as e:
            error_msg = f"Job processing error: {str(e)}"
            logger.error(error_msg)
            self.fail_job(job['id'], error_msg)
            return False

    def run(self):
        """Main worker loop"""
        logger.info(f"🚀 Starting Simple URL worker {self.worker_id}")
        self.running = True

        processed_count = 0
        consecutive_empty = 0

        while self.running:
            try:
                job = self.get_next_job()
                if job:
                    consecutive_empty = 0
                    success = self.process_job(job)
                    if success:
                        processed_count += 1
                        if processed_count % 10 == 0:
                            logger.info(f"📊 Processed {processed_count} URLs so far")
                else:
                    consecutive_empty += 1
                    if consecutive_empty >= 3:
                        logger.info("No jobs available, waiting...")
                        time.sleep(10)
                        consecutive_empty = 0
                    else:
                        time.sleep(2)

            except KeyboardInterrupt:
                logger.info("👋 Worker stopped by user")
                break
            except Exception as e:
                logger.error(f"Worker loop error: {e}")
                time.sleep(5)

        logger.info(f"✅ Worker finished. Processed {processed_count} URLs total")

if __name__ == "__main__":
    worker = SimpleURLWorker()
    worker.run()