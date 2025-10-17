#!/usr/bin/env python3
"""
Simple Content Processor for Atlas
Minimal, generalizable processor that moves items through stages
"""

import time
import logging
import sqlite3
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimpleProcessor:
    def __init__(self, db_path="data/atlas.db"):
        self.db_path = db_path
        self.running = True

    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)

    def process_batch(self, batch_size=10):
        """Process a batch of Stage 0 items"""
        conn = self.get_connection()
        try:
            # Get Stage 0 items
            cursor = conn.execute('''
                SELECT id, url, title, content_type
                FROM content
                WHERE stage = 0
                LIMIT ?
            ''', (batch_size,))

            items = cursor.fetchall()
            if not items:
                logger.info("No items to process")
                return 0

            # Process each item (simple stage progression)
            processed = 0
            for item_id, url, title, content_type in items:
                try:
                    # Simple processing: just move to next stage
                    # In reality, this would extract content, generate summaries, etc.
                    conn.execute('''
                        UPDATE content
                        SET stage = 100, updated_at = datetime('now')
                        WHERE id = ?
                    ''', (item_id,))

                    processed += 1
                    logger.info(f"Processed item {item_id}: {title[:50]}...")

                except Exception as e:
                    logger.error(f"Failed to process item {item_id}: {e}")

            conn.commit()
            logger.info(f"Processed {processed} items in this batch")
            return processed

        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            conn.rollback()
            return 0
        finally:
            conn.close()

    def run_continuous(self, batch_size=10, delay=2):
        """Run processor continuously"""
        logger.info("Starting simple processor...")
        logger.info(f"Processing {batch_size} items every {delay} seconds")

        while self.running:
            try:
                processed = self.process_batch(batch_size)

                if processed == 0:
                    logger.info("No items to process, sleeping...")
                    time.sleep(delay * 10)  # Sleep longer when no work
                else:
                    time.sleep(delay)

            except KeyboardInterrupt:
                logger.info("Processor stopped by user")
                break
            except Exception as e:
                logger.error(f"Processor error: {e}")
                time.sleep(delay)

def main():
    """Main entry point"""
    processor = SimpleProcessor()

    try:
        processor.run_continuous(batch_size=5, delay=1)
    except KeyboardInterrupt:
        print("\nProcessor stopped")
    except Exception as e:
        logger.error(f"Processor failed: {e}")

if __name__ == "__main__":
    main()