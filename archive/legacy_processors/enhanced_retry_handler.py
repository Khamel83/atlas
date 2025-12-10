#!/usr/bin/env python3
"""
Enhanced Retry Handler for Atlas
Implements exponential backoff and intelligent retry strategies
"""

import time
import random
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import sqlite3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedRetryHandler:
    def __init__(self, db_path: str = 'data/atlas.db'):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()

    def get_retry_strategy(self, error_type: str, retry_count: int) -> Dict[str, Any]:
        """Get retry strategy based on error type and retry count"""

        strategies = {
            'timeout': {
                'max_retries': 3,
                'base_delay': 60,  # 1 minute
                'max_delay': 3600,  # 1 hour
                'backoff_factor': 2.0
            },
            'network': {
                'max_retries': 5,
                'base_delay': 30,  # 30 seconds
                'max_delay': 1800,  # 30 minutes
                'backoff_factor': 2.0
            },
            'rate_limit': {
                'max_retries': 3,
                'base_delay': 300,  # 5 minutes
                'max_delay': 3600,  # 1 hour
                'backoff_factor': 1.5
            },
            'transient': {
                'max_retries': 3,
                'base_delay': 10,  # 10 seconds
                'max_delay': 300,  # 5 minutes
                'backoff_factor': 2.0
            },
            'permanent': {
                'max_retries': 0,  # Don't retry permanent errors
                'base_delay': 0,
                'max_delay': 0,
                'backoff_factor': 1.0
            }
        }

        return strategies.get(error_type, strategies['transient'])

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

    def calculate_delay(self, strategy: Dict[str, Any], retry_count: int) -> int:
        """Calculate delay with exponential backoff and jitter"""
        if retry_count == 0:
            return 0

        # Exponential backoff with jitter
        base_delay = strategy['base_delay']
        backoff_factor = strategy['backoff_factor']
        max_delay = strategy['max_delay']

        # Calculate exponential delay
        delay = base_delay * (backoff_factor ** (retry_count - 1))

        # Add jitter to avoid thundering herd
        jitter = random.uniform(0.8, 1.2)
        delay = int(delay * jitter)

        # Cap at maximum delay
        return min(delay, max_delay)

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

        # Get strategy for this error type
        strategy = self.get_retry_strategy(error_type, retry_count)

        # Check if we've exceeded max retries
        if retry_count >= strategy['max_retries']:
            logger.info(f"Episode {episode_id} exceeded max retries ({retry_count}) for {error_type}")
            return False

        # Check if we should wait longer before retrying
        if last_retry:
            delay = self.calculate_delay(strategy, retry_count)
            next_retry_time = datetime.fromisoformat(last_retry) + timedelta(seconds=delay)

            if datetime.now() < next_retry_time:
                logger.info(f"Episode {episode_id} waiting for retry delay ({delay}s)")
                return False

        return True

    def update_episode_for_retry(self, episode_id: int, error_type: str, error_message: str):
        """Update episode with retry information"""

        # Add retry metadata to error message
        retry_info = self.cursor.execute(
            "SELECT COUNT(*) FROM episode_queue WHERE id = ? AND status = 'error'",
            [episode_id]
        ).fetchone()[0] or 0

        enhanced_error = f"[{error_type}][Retry #{retry_info + 1}] {error_message}"

        self.cursor.execute(
            "UPDATE episode_queue SET status = 'pending', error_info = ?, updated_at = ? WHERE id = ?",
            (enhanced_error, datetime.now().isoformat(), episode_id)
        )

        self.conn.commit()
        logger.info(f"Episode {episode_id} queued for retry ({error_type})")

    def process_failed_batch(self, batch_size: int = 20) -> Dict[str, int]:
        """Process a batch of failed episodes with intelligent retry logic"""

        logger.info(f"Processing {batch_size} failed episodes with enhanced retry logic")

        # Get episodes that are ready for retry
        ready_episodes = self.cursor.execute(
            """SELECT id, podcast_name, episode_title, episode_url, error_info
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

        for episode_id, podcast_name, episode_title, episode_url, error_info in ready_episodes:
            try:
                # Classify the error
                error_type = self.classify_error(error_info or "unknown error")

                # Check if we should retry
                if self.should_retry(episode_id, error_type):
                    self.update_episode_for_retry(episode_id, error_type, error_info or "unknown error")
                    results['retried'] += 1
                else:
                    # Check if it's a permanent failure
                    strategy = self.get_retry_strategy(error_type, 0)
                    if strategy['max_retries'] == 0:
                        results['permanent_failures'] += 1
                        logger.info(f"Episode {episode_id} marked as permanent failure ({error_type})")
                    else:
                        results['skipped'] += 1
                        logger.info(f"Episode {episode_id} skipped (waiting for retry delay)")

            except Exception as e:
                logger.error(f"Error processing retry for episode {episode_id}: {e}")
                results['skipped'] += 1

        logger.info(f"Retry processing completed: {results}")
        return results

    def get_retry_statistics(self) -> Dict[str, Any]:
        """Get retry statistics for monitoring"""

        # Get error type distribution
        error_types = self.cursor.execute(
            """SELECT
                  CASE
                      WHEN error_info LIKE '%[timeout]%' THEN 'timeout'
                      WHEN error_info LIKE '%[network]%' THEN 'network'
                      WHEN error_info LIKE '%[rate_limit]%' THEN 'rate_limit'
                      WHEN error_info LIKE '%[permanent]%' THEN 'permanent'
                      ELSE 'transient'
                  END as error_type,
                  COUNT(*) as count
               FROM episode_queue
               WHERE status = 'error' AND error_info IS NOT NULL
               GROUP BY error_type"""
        ).fetchall()

        # Get retry queue status
        retry_status = self.cursor.execute(
            """SELECT
                  COUNT(CASE WHEN status = 'error' THEN 1 END) as total_errors,
                  COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_retry,
                  COUNT(CASE WHEN updated_at >= datetime('now', '-1 hour') THEN 1 END) as recent_errors
               FROM episode_queue"""
        ).fetchone()

        return {
            'error_types': dict(error_types),
            'retry_status': {
                'total_errors': retry_status[0],
                'pending_retry': retry_status[1],
                'recent_errors': retry_status[2]
            }
        }

    def cleanup_old_errors(self, days: int = 30):
        """Clean up old permanent failures"""

        cutoff_date = datetime.now() - timedelta(days=days)

        # Remove old permanent failures
        deleted = self.cursor.execute(
            """DELETE FROM episode_queue
               WHERE status = 'error'
               AND error_info LIKE '%[permanent]%'
               AND updated_at < ?""",
            [cutoff_date.isoformat()]
        ).rowcount

        self.conn.commit()
        logger.info(f"Cleaned up {deleted} old permanent failures")

        return deleted

def main():
    """Test the enhanced retry handler"""
    handler = EnhancedRetryHandler()

    # Process a batch
    results = handler.process_failed_batch(10)
    print(f"Retry results: {results}")

    # Show statistics
    stats = handler.get_retry_statistics()
    print(f"Retry statistics: {stats}")

if __name__ == "__main__":
    main()