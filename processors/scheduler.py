#!/usr/bin/env python3
"""
Atlas Scheduler Service

Periodic tasks for Atlas including RSS feed checking,
system maintenance, and cleanup operations.
"""

import asyncio
import logging
import sys
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Add current directory to path
sys.path.insert(0, '.')

from core.database import get_database
from core.processor import get_processor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AtlasScheduler:
    """Scheduler for periodic Atlas tasks"""

    def __init__(self):
        self.db = get_database()
        self.processor = get_processor()
        self.tasks_run = 0
        self.errors = 0

    async def run_scheduled_tasks(self):
        """Run all scheduled tasks"""
        logger.info("⏰ Atlas Scheduler running...")

        try:
            # Task 1: Process RSS feeds
            await self._process_rss_feeds()

            # Task 2: Clean up old logs
            await self._cleanup_old_logs()

            # Task 3: Update statistics
            await self._update_statistics()

            # Task 4: Check system health
            await self._check_system_health()

            self.tasks_run += 1
            logger.info(f"✅ Scheduler completed {self.tasks_run} runs")

        except Exception as e:
            logger.error(f"🚨 Scheduler error: {e}")
            self.errors += 1
            raise

    async def _process_rss_feeds(self):
        """Process RSS feeds for new content"""
        try:
            logger.info("📡 Processing RSS feeds...")

            # Get RSS feeds from database
            conn = self.db.get_connection()
            cursor = conn.execute("""
                SELECT id, url, title, last_checked
                FROM rss_feeds
                WHERE enabled = 1
                AND (last_checked IS NULL OR last_checked < datetime('now', '-1 hour'))
            """)

            feeds = cursor.fetchall()
            conn.close()

            processed_count = 0

            for feed_id, feed_url, feed_title, last_checked in feeds:
                try:
                    # Process RSS feed
                    await self._process_single_feed(feed_id, feed_url, feed_title)
                    processed_count += 1

                    # Small delay between feeds to avoid overwhelming
                    await asyncio.sleep(1)

                except Exception as e:
                    logger.error(f"🚨 Error processing feed {feed_title}: {e}")

            logger.info(f"📡 Processed {processed_count} RSS feeds")

        except Exception as e:
            logger.error(f"🚨 Error in RSS processing: {e}")

    async def _process_single_feed(self, feed_id: int, feed_url: str, feed_title: str):
        """Process a single RSS feed"""
        try:
            import feedparser
            import aiohttp

            logger.info(f"📡 Fetching RSS feed: {feed_title}")

            # Fetch RSS feed
            async with aiohttp.ClientSession() as session:
                async with session.get(feed_url, timeout=30) as response:
                    if response.status == 200:
                        feed_content = await response.text()
                        feed = feedparser.parse(feed_content)

                        # Process new entries
                        new_items = 0
                        for entry in feed.entries:
                            if await self._process_feed_entry(entry, feed_id):
                                new_items += 1

                        # Update last checked time
                        conn = self.db.get_connection()
                        conn.execute("""
                            UPDATE rss_feeds
                            SET last_checked = datetime('now')
                            WHERE id = ?
                        """, (feed_id,))
                        conn.commit()
                        conn.close()

                        logger.info(f"📡 Added {new_items} new items from {feed_title}")
                    else:
                        logger.warning(f"⚠️ RSS feed returned status {response.status}: {feed_title}")

        except Exception as e:
            logger.error(f"🚨 Error processing RSS feed {feed_title}: {e}")

    async def _process_feed_entry(self, entry, feed_id: int) -> bool:
        """Process a single RSS feed entry"""
        try:
            # Extract URL and title
            url = entry.get('link')
            title = entry.get('title', 'Untitled')

            if not url:
                logger.warning(f"⚠️ RSS entry missing URL: {title}")
                return False

            # Check if already exists
            conn = self.db.get_connection()
            cursor = conn.execute("SELECT id FROM content WHERE url = ?", (url,))
            existing = cursor.fetchone()
            conn.close()

            if existing:
                return False  # Already exists

            # Add to database for processing
            conn = self.db.get_connection()
            conn.execute("""
                INSERT INTO content (url, title, content_type, source, stage, created_at, updated_at)
                VALUES (?, ?, 'article', 'rss', 0, datetime('now'), datetime('now'))
            """, (url, title))
            conn.commit()
            conn.close()

            logger.info(f"📡 Added RSS item: {title}")
            return True

        except Exception as e:
            logger.error(f"🚨 Error processing RSS entry: {e}")
            return False

    async def _cleanup_old_logs(self):
        """Clean up old log files"""
        try:
            import os
            from pathlib import Path

            logger.info("🧹 Cleaning up old logs...")

            log_dir = Path('logs')
            if log_dir.exists():
                # Remove logs older than 30 days
                cutoff_date = datetime.now() - timedelta(days=30)

                for log_file in log_dir.glob('*.log.*'):
                    if log_file.stat().st_mtime < cutoff_date.timestamp():
                        log_file.unlink()
                        logger.info(f"🧹 Deleted old log: {log_file}")

            logger.info("🧹 Log cleanup completed")

        except Exception as e:
            logger.error(f"🚨 Error in log cleanup: {e}")

    async def _update_statistics(self):
        """Update system statistics"""
        try:
            logger.info("📊 Updating system statistics...")

            # Get database statistics
            stats = self.db.get_statistics()

            # Log key metrics
            logger.info(f"📊 Total content: {stats.get('total_content', 0)}")
            logger.info(f"📊 Queue size: {stats.get('queue_size', 0)}")
            logger.info(f"📊 Processing rate: {stats.get('processing_rate', 0)} items/hour")

            logger.info("📊 Statistics updated")

        except Exception as e:
            logger.error(f"🚨 Error updating statistics: {e}")

    async def _check_system_health(self):
        """Check overall system health"""
        try:
            logger.info("🏥 Running system health check...")

            # Check database health
            try:
                stats = self.db.get_statistics()
                db_health = "healthy"
            except Exception as e:
                logger.error(f"🚨 Database health check failed: {e}")
                db_health = "unhealthy"

            # Check processor health
            try:
                proc_health = await self.processor.health_check()
                proc_status = proc_health.get('status', 'unknown')
            except Exception as e:
                logger.error(f"🚨 Processor health check failed: {e}")
                proc_status = "unhealthy"

            # Check disk space
            import shutil
            total, used, free = shutil.disk_usage('.')
            free_gb = free // (1024**3)

            overall_health = "healthy"
            if db_health == "unhealthy" or proc_status == "unhealthy":
                overall_health = "degraded"
            if free_gb < 1:  # Less than 1GB free
                overall_health = "critical"

            logger.info(f"🏥 System health: {overall_health}")
            logger.info(f"🏥 Database: {db_health}")
            logger.info(f"🏥 Processor: {proc_status}")
            logger.info(f"🏥 Free disk space: {free_gb}GB")

        except Exception as e:
            logger.error(f"🚨 Error in health check: {e}")

    async def health_check(self) -> dict:
        """Health check for the scheduler"""
        return {
            'status': 'healthy',
            'tasks_run': self.tasks_run,
            'errors': self.errors,
            'timestamp': datetime.utcnow().isoformat()
        }

async def main():
    """Main entry point"""
    scheduler = AtlasScheduler()

    try:
        await scheduler.run_scheduled_tasks()
    except Exception as e:
        logger.error(f"🚨 Scheduler failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())