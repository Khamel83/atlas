"""
Failure queue management for Atlas v4.

Provides persistent queue management for failed operations that need
to be retried later, with priority handling and batch processing.
"""

import json
import time
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Callable
from dataclasses import dataclass, asdict, field
from enum import Enum
import logging

from .retry import RetryConfig, RetryResult


class QueueStatus(Enum):
    """Status of queue items."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class QueuePriority(Enum):
    """Priority levels for queue items."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class QueueItem:
    """Item in the failure queue."""
    id: str
    data: Dict[str, Any]
    error: str
    attempt_count: int = 0
    max_attempts: int = 3
    priority: QueuePriority = QueuePriority.NORMAL
    status: QueueStatus = QueueStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    next_retry_at: Optional[datetime] = None
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class FailureQueue:
    """
    Persistent failure queue for retry management.

    Features:
    - SQLite-based persistent storage
    - Priority-based processing
    - Automatic retry scheduling
    - Batch processing support
    - Thread-safe operations
    """

    def __init__(self, queue_path: Union[str, Path]):
        """
        Initialize failure queue.

        Args:
            queue_path: Path to queue database file
        """
        self.queue_path = Path(queue_path)
        self.queue_path.parent.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(f"atlas.core.{self.__class__.__name__}")
        self._lock = threading.Lock()

        # Initialize database
        self._init_database()

    def _init_database(self) -> None:
        """Initialize SQLite database schema."""
        with sqlite3.connect(self.queue_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS queue_items (
                    id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    error TEXT NOT NULL,
                    attempt_count INTEGER DEFAULT 0,
                    max_attempts INTEGER DEFAULT 3,
                    priority INTEGER DEFAULT 2,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    next_retry_at TEXT,
                    context TEXT DEFAULT '{}',
                    metadata TEXT DEFAULT '{}'
                )
            """)

            # Create indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON queue_items(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_priority ON queue_items(priority DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_next_retry ON queue_items(next_retry_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON queue_items(created_at)")

            conn.commit()

    def add_item(
        self,
        item_id: str,
        data: Dict[str, Any],
        error: Union[str, Exception],
        priority: QueuePriority = QueuePriority.NORMAL,
        max_attempts: int = 3,
        context: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Add item to failure queue.

        Args:
            item_id: Unique identifier for the item
            data: Original data that failed to process
            error: Error that occurred
            priority: Priority level for retry
            max_attempts: Maximum retry attempts
            context: Processing context
            metadata: Additional metadata

        Returns:
            True if item was added successfully
        """
        try:
            with self._lock:
                with sqlite3.connect(self.queue_path) as conn:
                    # Check if item already exists
                    existing = conn.execute(
                        "SELECT id FROM queue_items WHERE id = ?",
                        (item_id,)
                    ).fetchone()

                    if existing:
                        # Update existing item
                        conn.execute("""
                            UPDATE queue_items SET
                                data = ?, error = ?, attempt_count = 0,
                                status = 'pending', updated_at = ?,
                                next_retry_at = NULL, context = ?, metadata = ?
                            WHERE id = ?
                        """, (
                            json.dumps(data),
                            str(error),
                            datetime.now().isoformat(),
                            json.dumps(context or {}),
                            json.dumps(metadata or {}),
                            item_id
                        ))
                    else:
                        # Insert new item
                        queue_item = QueueItem(
                            id=item_id,
                            data=data,
                            error=str(error),
                            priority=priority,
                            max_attempts=max_attempts,
                            context=context or {},
                            metadata=metadata or {}
                        )

                        conn.execute("""
                            INSERT INTO queue_items (
                                id, data, error, attempt_count, max_attempts,
                                priority, status, created_at, updated_at,
                                context, metadata
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            queue_item.id,
                            json.dumps(queue_item.data),
                            queue_item.error,
                            queue_item.attempt_count,
                            queue_item.max_attempts,
                            queue_item.priority.value,
                            queue_item.status.value,
                            queue_item.created_at.isoformat(),
                            queue_item.updated_at.isoformat(),
                            json.dumps(queue_item.context),
                            json.dumps(queue_item.metadata)
                        ))

                    conn.commit()

            self.logger.debug(f"Added item to failure queue: {item_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to add item to failure queue: {item_id}", error=str(e))
            return False

    def get_next_item(self) -> Optional[QueueItem]:
        """
        Get next item ready for processing.

        Returns:
            QueueItem if available, None otherwise
        """
        try:
            with self._lock:
                with sqlite3.connect(self.queue_path) as conn:
                    now = datetime.now().isoformat()

                    # Get highest priority pending item that's ready for retry
                    row = conn.execute("""
                        SELECT * FROM queue_items
                        WHERE status = 'pending'
                        AND (next_retry_at IS NULL OR next_retry_at <= ?)
                        ORDER BY priority DESC, created_at ASC
                        LIMIT 1
                    """, (now,)).fetchone()

                    if row:
                        # Mark as processing
                        conn.execute("""
                            UPDATE queue_items
                            SET status = 'processing', updated_at = ?
                            WHERE id = ?
                        """, (datetime.now().isoformat(), row[0]))

                        conn.commit()

                        return self._row_to_queue_item(row)

            return None

        except Exception as e:
            self.logger.error("Failed to get next item from queue", error=str(e))
            return None

    def complete_item(self, item_id: str, result: Optional[Dict[str, Any]] = None) -> bool:
        """
        Mark item as completed successfully.

        Args:
            item_id: ID of item to complete
            result: Optional result data

        Returns:
            True if successful
        """
        try:
            with self._lock:
                with sqlite3.connect(self.queue_path) as conn:
                    metadata = {}
                    if result:
                        metadata['result'] = result

                    conn.execute("""
                        UPDATE queue_items
                        SET status = 'completed', updated_at = ?, metadata = ?
                        WHERE id = ?
                    """, (
                        datetime.now().isoformat(),
                        json.dumps(metadata),
                        item_id
                    ))

                    conn.commit()

            self.logger.debug(f"Completed queue item: {item_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to complete queue item: {item_id}", error=str(e))
            return False

    def fail_item(
        self,
        item_id: str,
        error: Union[str, Exception],
        next_retry_delay: Optional[timedelta] = None
    ) -> bool:
        """
        Mark item as failed and schedule next retry if applicable.

        Args:
            item_id: ID of item that failed
            error: Error that occurred
            next_retry_delay: Delay until next retry

        Returns:
            True if successful
        """
        try:
            with self._lock:
                with sqlite3.connect(self.queue_path) as conn:
                    # Get current item data
                    row = conn.execute(
                        "SELECT * FROM queue_items WHERE id = ?",
                        (item_id,)
                    ).fetchone()

                    if not row:
                        return False

                    item = self._row_to_queue_item(row)
                    item.attempt_count += 1

                    if item.attempt_count >= item.max_attempts:
                        # Mark as permanently failed
                        conn.execute("""
                            UPDATE queue_items
                            SET status = 'failed', updated_at = ?, error = ?
                            WHERE id = ?
                        """, (
                            datetime.now().isoformat(),
                            str(error),
                            item_id
                        ))
                    else:
                        # Schedule for retry
                        next_retry_at = datetime.now() + (next_retry_delay or timedelta(minutes=5))

                        conn.execute("""
                            UPDATE queue_items
                            SET status = 'pending', updated_at = ?,
                                attempt_count = ?, error = ?, next_retry_at = ?
                            WHERE id = ?
                        """, (
                            datetime.now().isoformat(),
                            item.attempt_count,
                            str(error),
                            next_retry_at.isoformat(),
                            item_id
                        ))

                    conn.commit()

            self.logger.debug(
                f"Failed queue item: {item_id} (attempt {item.attempt_count}/{item.max_attempts})"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to update queue item: {item_id}", error=str(e))
            return False

    def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the queue.

        Returns:
            Dictionary with queue statistics
        """
        try:
            with sqlite3.connect(self.queue_path) as conn:
                # Count items by status
                status_counts = {}
                for status in QueueStatus:
                    count = conn.execute(
                        "SELECT COUNT(*) FROM queue_items WHERE status = ?",
                        (status.value,)
                    ).fetchone()[0]
                    status_counts[status.value] = count

                # Count items by priority
                priority_counts = {}
                for priority in QueuePriority:
                    count = conn.execute(
                        "SELECT COUNT(*) FROM queue_items WHERE priority = ?",
                        (priority.value,)
                    ).fetchone()[0]
                    priority_counts[priority.name.lower()] = count

                # Get age statistics
                oldest_row = conn.execute(
                    "SELECT created_at FROM queue_items ORDER BY created_at ASC LIMIT 1"
                ).fetchone()

                newest_row = conn.execute(
                    "SELECT created_at FROM queue_items ORDER BY created_at DESC LIMIT 1"
                ).fetchone()

                stats = {
                    "total_items": sum(status_counts.values()),
                    "status_counts": status_counts,
                    "priority_counts": priority_counts,
                    "oldest_item": oldest_row[0] if oldest_row else None,
                    "newest_item": newest_row[0] if newest_row else None,
                    "queue_size_bytes": self.queue_path.stat().st_size if self.queue_path.exists() else 0
                }

                return stats

        except Exception as e:
            self.logger.error("Failed to get queue stats", error=str(e))
            return {}

    def cleanup_old_items(self, days_old: int = 30) -> int:
        """
        Clean up old completed/failed items.

        Args:
            days_old: Age in days to keep items

        Returns:
            Number of items cleaned up
        """
        try:
            with self._lock:
                with sqlite3.connect(self.queue_path) as conn:
                    cutoff_date = (datetime.now() - timedelta(days=days_old)).isoformat()

                    cursor = conn.execute("""
                        DELETE FROM queue_items
                        WHERE status IN ('completed', 'failed')
                        AND updated_at < ?
                    """, (cutoff_date,))

                    deleted_count = cursor.rowcount
                    conn.commit()

            self.logger.info(f"Cleaned up {deleted_count} old queue items")
            return deleted_count

        except Exception as e:
            self.logger.error("Failed to cleanup old queue items", error=str(e))
            return 0

    def get_items(
        self,
        status: Optional[QueueStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[QueueItem]:
        """
        Get items from queue.

        Args:
            status: Filter by status
            limit: Maximum number of items
            offset: Offset for pagination

        Returns:
            List of QueueItems
        """
        try:
            with sqlite3.connect(self.queue_path) as conn:
                query = "SELECT * FROM queue_items"
                params = []

                if status:
                    query += " WHERE status = ?"
                    params.append(status.value)

                query += " ORDER BY priority DESC, created_at ASC LIMIT ? OFFSET ?"
                params.extend([limit, offset])

                rows = conn.execute(query, params).fetchall()
                return [self._row_to_queue_item(row) for row in rows]

        except Exception as e:
            self.logger.error("Failed to get queue items", error=str(e))
            return []

    def _row_to_queue_item(self, row) -> QueueItem:
        """Convert database row to QueueItem."""
        return QueueItem(
            id=row[0],
            data=json.loads(row[1]),
            error=row[2],
            attempt_count=row[3],
            max_attempts=row[4],
            priority=QueuePriority(row[5]),
            status=QueueStatus(row[6]),
            created_at=datetime.fromisoformat(row[7]),
            updated_at=datetime.fromisoformat(row[8]),
            next_retry_at=datetime.fromisoformat(row[9]) if row[9] else None,
            context=json.loads(row[10]),
            metadata=json.loads(row[11])
        )


class QueueProcessor:
    """
    Processes items from failure queue.

    Handles automatic retry processing with configurable processors
    and error handling.
    """

    def __init__(self, failure_queue: FailureQueue):
        """
        Initialize queue processor.

        Args:
            failure_queue: FailureQueue to process
        """
        self.queue = failure_queue
        self.processors: Dict[str, Callable] = {}
        self.running = False
        self.logger = logging.getLogger(f"atlas.core.{self.__class__.__name__}")

    def register_processor(self, content_type: str, processor: Callable) -> None:
        """
        Register processor for specific content type.

        Args:
            content_type: Type of content to process
            processor: Processing function
        """
        self.processors[content_type] = processor
        self.logger.debug(f"Registered processor for: {content_type}")

    def process_items(self, max_items: int = 10) -> Dict[str, int]:
        """
        Process items from queue.

        Args:
            max_items: Maximum items to process in this batch

        Returns:
            Processing statistics
        """
        stats = {
            "processed": 0,
            "completed": 0,
            "failed": 0,
            "no_processor": 0
        }

        for _ in range(max_items):
            item = self.queue.get_next_item()
            if not item:
                break

            stats["processed"] += 1

            try:
                # Get appropriate processor
                content_type = item.metadata.get("content_type", "unknown")
                processor = self.processors.get(content_type)

                if not processor:
                    self.logger.warning(f"No processor for content type: {content_type}")
                    self.queue.fail_item(item.id, f"No processor for {content_type}")
                    stats["no_processor"] += 1
                    continue

                # Process item
                result = processor(item.data, item.context)

                if result:
                    self.queue.complete_item(item.id, result)
                    stats["completed"] += 1
                    self.logger.info(f"Successfully processed queue item: {item.id}")
                else:
                    self.queue.fail_item(item.id, "Processing returned no result")
                    stats["failed"] += 1

            except Exception as e:
                self.queue.fail_item(item.id, e)
                stats["failed"] += 1
                self.logger.error(f"Failed to process queue item: {item.id}", error=str(e))

        return stats

    def start_processing(self, interval_seconds: int = 60) -> None:
        """
        Start automatic processing in background thread.

        Args:
            interval_seconds: Processing interval
        """
        def processing_loop():
            self.running = True
            while self.running:
                try:
                    stats = self.process_items()
                    if stats["processed"] > 0:
                        self.logger.info(
                            f"Queue processing batch completed",
                            stats=stats
                        )

                    time.sleep(interval_seconds)

                except Exception as e:
                    self.logger.error("Error in processing loop", error=str(e))
                    time.sleep(interval_seconds)

        import threading
        thread = threading.Thread(target=processing_loop, daemon=True)
        thread.start()

        self.logger.info(f"Started queue processing (interval: {interval_seconds}s)")

    def stop_processing(self) -> None:
        """Stop automatic processing."""
        self.running = False
        self.logger.info("Stopped queue processing")