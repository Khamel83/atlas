#!/usr/bin/env python3
"""
Atlas Worker Service

Background worker for processing queued content items.
Runs continuously, pulling items from the processing queue.
"""

import asyncio
import logging
import signal
import sys
import time
from datetime import datetime
from typing import Optional

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

class AtlasWorker:
    """Background worker for processing content"""

    def __init__(self):
        self.db = get_database()
        self.processor = get_processor()
        self.running = False
        self.task_count = 0
        self.error_count = 0

    async def process_queue(self):
        """Main processing loop"""
        logger.info("🏭 Atlas Worker starting...")

        self.running = True

        # Set up signal handlers
        def signal_handler(signum, frame):
            logger.info(f"📡 Received signal {signum}, shutting down...")
            self.running = False

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        while self.running:
            try:
                # Get next item from queue
                item = await self._get_next_item()

                if item:
                    await self._process_item(item)
                else:
                    # No items in queue, wait a bit
                    await asyncio.sleep(5)

            except Exception as e:
                logger.error(f"🚨 Processing error: {e}")
                self.error_count += 1
                await asyncio.sleep(10)  # Back off on errors

        logger.info("🛑 Atlas Worker stopped")

    async def _get_next_item(self) -> Optional[dict]:
        """Get next item from processing queue"""
        try:
            # Look for items that need processing
            # For now, this is a simple implementation
            # In a real system, this would query a proper queue table

            # Check for unprocessed URLs
            conn = self.db.get_connection()
            cursor = conn.execute("""
                SELECT id, url, title, content_type
                FROM content
                WHERE stage < 300
                AND (url IS NOT NULL OR content IS NOT NULL)
                ORDER BY created_at ASC
                LIMIT 1
            """)

            row = cursor.fetchone()
            conn.close()

            if row:
                return {
                    'id': row[0],
                    'url': row[1],
                    'title': row[2],
                    'content_type': row[3]
                }

        except Exception as e:
            logger.error(f"🚨 Error getting next item: {e}")

        return None

    async def _process_item(self, item: dict):
        """Process a single item"""
        start_time = time.time()

        try:
            logger.info(f"🔄 Processing item {item['id']}: {item['title'][:50]}...")

            # Process the item
            if item['url']:
                result = await self.processor.process(
                    item['url'],
                    title=item['title']
                )
            else:
                # Process as text content
                content = self._extract_content(item['id'])
                if content:
                    result = await self.processor.process(
                        content,
                        title=item['title']
                    )
                else:
                    logger.warning(f"⚠️ No content found for item {item['id']}")
                    return

            if result.success:
                processing_time = time.time() - start_time
                logger.info(f"✅ Processed item {item['id']} in {processing_time:.2f}s")
                self.task_count += 1
            else:
                logger.error(f"❌ Failed to process item {item['id']}: {result.error}")
                self.error_count += 1

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"🚨 Error processing item {item['id']} after {processing_time:.2f}s: {e}")
            self.error_count += 1

    def _extract_content(self, item_id: int) -> Optional[str]:
        """Extract content from database for processing"""
        try:
            conn = self.db.get_connection()
            cursor = conn.execute("SELECT content FROM content WHERE id = ?", (item_id,))
            row = cursor.fetchone()
            conn.close()

            return row[0] if row else None

        except Exception as e:
            logger.error(f"🚨 Error extracting content for item {item_id}: {e}")
            return None

    async def health_check(self) -> dict:
        """Health check for the worker"""
        return {
            'status': 'healthy' if self.running else 'stopped',
            'running': self.running,
            'tasks_processed': self.task_count,
            'errors': self.error_count,
            'timestamp': datetime.utcnow().isoformat()
        }

async def main():
    """Main entry point"""
    worker = AtlasWorker()

    try:
        await worker.process_queue()
    except KeyboardInterrupt:
        logger.info("🛑 Received KeyboardInterrupt, shutting down...")
    except Exception as e:
        logger.error(f"🚨 Worker crashed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())