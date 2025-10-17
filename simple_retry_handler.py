#!/usr/bin/env python3
"""
Simple Retry Handler for Atlas
Works with existing database schema
"""

import time
import random
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import sqlite3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleRetryHandler:
    def __init__(self, db_path: str = 'data/atlas.db'):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()

    def classify_error(self, error_message: str) -> str:
        """Classify error type based on error message"""
        error_lower = error_message.lower()

        if any(keyword in error_lower for keyword in ['timeout', 'timed out', 'connection timeout']):
            return 'timeout'
        elif any(keyword in error_lower for keyword in ['connection', 'network', 'dns', 'resolve']):
            return 'network'
        elif any(keyword in error_lower for keyword in ['rate limit', 'too many requests', '429']):
            return 'rate_limit'
        elif any(keyword in error_lower for keyword in ['not found', '404', 'no such file']):
            return 'permanent'
        else:
            return 'transient'

    def should_retry(self, episode_id: int, error_type: str) -> bool:
        """Check if episode should be retried based on retry history"""

        # Get retry history
        retry_history = self.cursor.execute(
            """SELECT COUNT(*) as retry_count,
                      MAX(updated_at) as last_retry
               FROM episode_queue
               WHERE id = ? AND status = 'error'""",
            [episode_id]
        ).fetchone()

        retry_count = retry_history[0] or 0
        last_retry = retry_history[1]

        # Define retry limits by error type
        retry_limits = {
            'timeout': 3,
            'network': 5,
            'rate_limit': 3,
            'transient': 3,
            'permanent': 0
        }

        max_retries = retry_limits.get(error_type, 3)

        # Check if we've exceeded max retries
        if retry_count >= max_retries:
            logger.info(f"Episode {episode_id} exceeded max retries ({retry_count}) for {error_type}")
            return False

        # Calculate delay based on error type and retry count
        delays = {
            'timeout': [60, 300, 1800],      # 1min, 5min, 30min
            'network': [30, 120, 600, 1800], # 30s, 2min, 10min, 30min
            'rate_limit': [300, 1800, 3600], # 5min, 30min, 1hr
            'transient': [10, 60, 300]       # 10s, 1min, 5min
        }

        if retry_count > 0 and retry_count <= len(delays.get(error_type, [10, 60, 300])):
            delay = delays.get(error_type, [10, 60, 300])[retry_count - 1]

            if last_retry:
                next_retry_time = datetime.fromisoformat(last_retry) + timedelta(seconds=delay)

                if datetime.now() < next_retry_time:
                    logger.info(f"Episode {episode_id} waiting for retry delay ({delay}s)")
                    return False

        return True

    def process_failed_batch(self, batch_size: int = 20) -> Dict[str, int]:
        """Process a batch of failed episodes with intelligent retry logic"""

        logger.info(f"Processing {batch_size} failed episodes with enhanced retry logic")

        # Get episodes that are ready for retry
        ready_episodes = self.cursor.execute(
            """SELECT id, podcast_name, episode_title, episode_url
               FROM episode_queue
               WHERE status = 'error'
               ORDER BY updated_at ASC
               LIMIT ?""",
            [batch_size]
        ).fetchall()

        results = {
            'retried': 0,
            'skipped': 0,
            'permanent_failures': 0
        }

        for episode_id, podcast_name, episode_title, episode_url in ready_episodes:
            try:
                # For simple implementation, we'll use a basic classification
                # In a real implementation, you'd store the actual error message
                error_type = 'transient'  # Default to transient since we don't have error_info

                # Check if we should retry
                if self.should_retry(episode_id, error_type):
                    # Update episode for retry
                    self.cursor.execute(
                        "UPDATE episode_queue SET status = 'pending', updated_at = ? WHERE id = ?",
                        (datetime.now().isoformat(), episode_id)
                    )
                    self.conn.commit()
                    results['retried'] += 1
                    logger.info(f"Episode {episode_id} queued for retry ({error_type})")
                else:
                    results['skipped'] += 1
                    logger.info(f"Episode {episode_id} skipped (max retries reached)")

            except Exception as e:
                logger.error(f"Error processing retry for episode {episode_id}: {e}")
                results['skipped'] += 1

        logger.info(f"Retry processing completed: {results}")
        return results

    def get_retry_statistics(self) -> Dict[str, Any]:
        """Get retry statistics for monitoring"""

        # Get retry queue status
        retry_status = self.cursor.execute(
            """SELECT
                  COUNT(CASE WHEN status = 'error' THEN 1 END) as total_errors,
                  COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_retry,
                  COUNT(CASE WHEN updated_at >= datetime('now', '-1 hour') THEN 1 END) as recent_errors
               FROM episode_queue"""
        ).fetchone()

        return {
            'retry_status': {
                'total_errors': retry_status[0],
                'pending_retry': retry_status[1],
                'recent_errors': retry_status[2]
            }
        }

    def cleanup_old_errors(self, days: int = 30):
        """Clean up old errors"""

        cutoff_date = datetime.now() - timedelta(days=days)

        # Remove old errors
        deleted = self.cursor.execute(
            """DELETE FROM episode_queue
               WHERE status = 'error'
               AND updated_at < ?""",
            [cutoff_date.isoformat()]
        ).rowcount

        self.conn.commit()
        logger.info(f"Cleaned up {deleted} old errors")

        return deleted

def main():
    """Test the simple retry handler"""
    handler = SimpleRetryHandler()

    # Process a batch
    results = handler.process_failed_batch(10)
    print(f"Retry results: {results}")

    # Show statistics
    stats = handler.get_retry_statistics()
    print(f"Retry statistics: {stats}")

if __name__ == "__main__":
    main()