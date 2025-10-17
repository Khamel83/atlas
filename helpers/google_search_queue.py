#!/usr/bin/env python3
"""
Google Search Queue Manager with Database Persistence

Provides persistent queue management for Google Search requests
with priority handling, retry logic, and quota tracking.
"""

import sqlite3
import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class QueuePriority(Enum):
    """Queue priority levels"""
    URGENT = 1      # User-initiated requests (process immediately)
    NORMAL = 2      # Normal processing
    BACKGROUND = 3  # Background processing

class QueueStatus(Enum):
    """Queue item status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"

@dataclass
class QueuedSearch:
    """A queued search request"""
    id: Optional[int] = None
    query: str = ""
    priority: int = 2
    status: str = "pending"
    attempts: int = 0
    max_attempts: int = 5
    created_at: Optional[str] = None
    last_attempt: Optional[str] = None
    result_url: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Optional[str] = None  # JSON string for additional data

class GoogleSearchQueue:
    """Database-backed queue for Google Search requests"""

    def __init__(self, db_path: str = "data/google_search_queue.db"):
        self.db_path = db_path
        self._ensure_database()
        self.daily_quota = 8000  # 80% of 10k limit
        self.daily_used = self._get_daily_usage()

    def _ensure_database(self):
        """Ensure database and tables exist"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS search_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT NOT NULL,
                    priority INTEGER DEFAULT 2,
                    status TEXT DEFAULT 'pending',
                    attempts INTEGER DEFAULT 0,
                    max_attempts INTEGER DEFAULT 5,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_attempt TEXT,
                    result_url TEXT,
                    error_message TEXT,
                    metadata TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS search_stats (
                    date TEXT PRIMARY KEY,
                    searches_performed INTEGER DEFAULT 0,
                    successful_searches INTEGER DEFAULT 0,
                    failed_searches INTEGER DEFAULT 0,
                    quota_used INTEGER DEFAULT 0
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_search_queue_status
                ON search_queue(status)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_search_queue_priority
                ON search_queue(priority, created_at)
            """)

    def add_search(self, query: str, priority: QueuePriority = QueuePriority.NORMAL,
                  metadata: Optional[Dict] = None) -> int:
        """Add a search request to the queue"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO search_queue (query, priority, metadata)
                VALUES (?, ?, ?)
            """, (query, priority.value, json.dumps(metadata) if metadata else None))

            search_id = cursor.lastrowid
            logger.info(f"Added search to queue: {query} (ID: {search_id}, Priority: {priority.name})")
            return search_id

    def get_next_search(self) -> Optional[QueuedSearch]:
        """Get the next search request to process"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM search_queue
                WHERE status = 'pending' AND attempts < max_attempts
                ORDER BY priority ASC, created_at ASC
                LIMIT 1
            """)

            row = cursor.fetchone()
            if not row:
                return None

            # Convert to dataclass
            search = QueuedSearch(**dict(row))

            # Mark as in progress
            conn.execute("""
                UPDATE search_queue
                SET status = 'in_progress', last_attempt = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (search.id,))

            return search

    def mark_completed(self, search_id: int, result_url: str):
        """Mark a search as completed successfully"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE search_queue
                SET status = 'completed', result_url = ?, last_attempt = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (result_url, search_id))

        self._update_daily_stats(successful=True)
        logger.info(f"Search completed: ID {search_id}")

    def mark_failed(self, search_id: int, error_message: str, increment_attempts: bool = True):
        """Mark a search as failed"""
        with sqlite3.connect(self.db_path) as conn:
            if increment_attempts:
                conn.execute("""
                    UPDATE search_queue
                    SET status = 'failed', error_message = ?, attempts = attempts + 1,
                        last_attempt = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (error_message, search_id))
            else:
                conn.execute("""
                    UPDATE search_queue
                    SET status = 'failed', error_message = ?, last_attempt = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (error_message, search_id))

        self._update_daily_stats(successful=False)
        logger.warning(f"Search failed: ID {search_id} - {error_message}")

    def mark_rate_limited(self, search_id: int):
        """Mark a search as rate limited (will retry later)"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE search_queue
                SET status = 'pending', attempts = attempts + 1, last_attempt = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (search_id,))

        logger.info(f"Search rate limited, will retry: ID {search_id}")

    def get_pending_count(self) -> int:
        """Get count of pending search requests"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT COUNT(*) FROM search_queue
                WHERE status = 'pending' AND attempts < max_attempts
            """)
            return cursor.fetchone()[0]

    def get_queue_status(self) -> Dict:
        """Get comprehensive queue status"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT status, COUNT(*) as count
                FROM search_queue
                GROUP BY status
            """)

            status_counts = dict(cursor.fetchall())

            cursor = conn.execute("""
                SELECT priority, COUNT(*) as count
                FROM search_queue
                WHERE status = 'pending'
                GROUP BY priority
            """)

            priority_counts = dict(cursor.fetchall())

            return {
                "status_counts": status_counts,
                "priority_counts": priority_counts,
                "daily_quota": self.daily_quota,
                "daily_used": self._get_daily_usage(),
                "daily_remaining": max(0, self.daily_quota - self._get_daily_usage())
            }

    def _get_daily_usage(self) -> int:
        """Get today's search usage"""
        today = datetime.now().strftime('%Y-%m-%d')

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT quota_used FROM search_stats WHERE date = ?
            """, (today,))

            result = cursor.fetchone()
            return result[0] if result else 0

    def _update_daily_stats(self, successful: bool):
        """Update daily statistics"""
        today = datetime.now().strftime('%Y-%m-%d')

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO search_stats
                (date, searches_performed, successful_searches, failed_searches, quota_used)
                VALUES (
                    ?,
                    COALESCE((SELECT searches_performed FROM search_stats WHERE date = ?), 0) + 1,
                    COALESCE((SELECT successful_searches FROM search_stats WHERE date = ?), 0) + ?,
                    COALESCE((SELECT failed_searches FROM search_stats WHERE date = ?), 0) + ?,
                    COALESCE((SELECT quota_used FROM search_stats WHERE date = ?), 0) + 1
                )
            """, (today, today, today, 1 if successful else 0, today, 0 if successful else 1, today))

    def cleanup_old_entries(self, days_old: int = 30):
        """Clean up old completed/failed entries"""
        cutoff_date = (datetime.now() - timedelta(days=days_old)).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                DELETE FROM search_queue
                WHERE status IN ('completed', 'failed') AND created_at < ?
            """, (cutoff_date,))

            deleted_count = cursor.rowcount
            logger.info(f"Cleaned up {deleted_count} old search queue entries")

    def reset_failed_searches(self):
        """Reset failed searches to pending for retry"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                UPDATE search_queue
                SET status = 'pending', attempts = 0, error_message = NULL
                WHERE status = 'failed'
            """)

            reset_count = cursor.rowcount
            logger.info(f"Reset {reset_count} failed searches for retry")

# Global queue instance
_queue_instance = None

def get_search_queue() -> GoogleSearchQueue:
    """Get global search queue instance"""
    global _queue_instance
    if _queue_instance is None:
        _queue_instance = GoogleSearchQueue()
    return _queue_instance

if __name__ == "__main__":
    # Test the queue system
    queue = GoogleSearchQueue("test_queue.db")

    # Add some test searches
    queue.add_search("Python programming", QueuePriority.URGENT)
    queue.add_search("Machine learning tutorial", QueuePriority.NORMAL)
    queue.add_search("Web development", QueuePriority.BACKGROUND)

    # Show queue status
    print("Queue Status:", json.dumps(queue.get_queue_status(), indent=2))

    # Process a search
    search = queue.get_next_search()
    if search:
        print(f"Processing: {search.query}")
        queue.mark_completed(search.id, "https://example.com/result")

    # Show updated status
    print("Updated Status:", json.dumps(queue.get_queue_status(), indent=2))