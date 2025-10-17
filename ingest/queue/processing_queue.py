"""
Processing Queue System

This module manages the queue of captured items waiting for processing.
Queue operations can fail without affecting captured data. The queue provides
priority handling, status tracking, and recovery mechanisms.
"""

import json
import logging
import os
import threading
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from helpers.config import load_config
from helpers.utils import ensure_directory

logger = logging.getLogger(__name__)


class QueueStatus(Enum):
    """Status of items in the processing queue."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"
    ABANDONED = "abandoned"


class Priority(Enum):
    """Processing priority levels."""

    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


@dataclass
class QueueItem:
    """Item in the processing queue."""

    capture_id: str
    item_type: str  # "url", "file", "text"
    priority: Priority
    status: QueueStatus
    added_timestamp: str
    source: str
    user_context: Dict[str, Any]

    # Processing tracking
    processing_attempts: int = 0
    last_attempt_timestamp: Optional[str] = None
    processor_id: Optional[str] = None
    processing_started: Optional[str] = None
    processing_completed: Optional[str] = None

    # Error handling
    last_error: Optional[str] = None
    error_count: int = 0
    next_retry_time: Optional[str] = None

    # Results
    result_paths: Dict[str, str] = None
    processing_time: Optional[float] = None

    def __post_init__(self):
        if self.result_paths is None:
            self.result_paths = {}
        if not self.added_timestamp:
            self.added_timestamp = datetime.now().isoformat()


class ProcessingQueue:
    """
    Manages queue of captured items waiting for processing.
    Thread-safe operations with file-based persistence.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize processing queue with configuration."""
        self.config = config or load_config()
        self.queue_dir = self.config.get(
            "PROCESSING_QUEUE_DIRECTORY", "output/processing_queue"
        )
        self.queue_file = os.path.join(self.queue_dir, "queue.json")
        self.lock_file = os.path.join(self.queue_dir, "queue.lock")
        self.max_processing_time = self.config.get("MAX_PROCESSING_TIME_MINUTES", 60)
        self.max_retry_attempts = self.config.get("MAX_RETRY_ATTEMPTS", 3)
        self.retry_backoff_multiplier = self.config.get("RETRY_BACKOFF_MULTIPLIER", 2)
        self.retry_max_delay = self.config.get("RETRY_MAX_DELAY", 3600)

        # Thread safety
        self._lock = threading.Lock()

        # Ensure queue directory exists
        self._ensure_queue_directory()

        # Initialize queue if it doesn't exist
        self._initialize_queue()

    def _ensure_queue_directory(self):
        """Ensure queue directory exists."""
        try:
            ensure_directory(self.queue_dir)
        except Exception as e:
            logger.error(f"Failed to create queue directory: {e}")
            raise

    def _initialize_queue(self):
        """Initialize queue file if it doesn't exist."""
        if not os.path.exists(self.queue_file):
            try:
                with open(self.queue_file, "w") as f:
                    json.dump([], f)
            except Exception as e:
                logger.error(f"Failed to initialize queue file: {e}")
                raise

    def _load_queue(self) -> List[QueueItem]:
        """Load queue from file."""
        try:
            with open(self.queue_file, "r") as f:
                queue_data = json.load(f)

            # Convert to QueueItem objects
            items = []
            for item_data in queue_data:
                try:
                    # Convert enum values
                    item_data["priority"] = Priority(item_data["priority"])
                    item_data["status"] = QueueStatus(item_data["status"])

                    items.append(QueueItem(**item_data))
                except Exception as e:
                    logger.warning(f"Failed to load queue item: {e}")
                    continue

            return items
        except Exception as e:
            logger.error(f"Failed to load queue: {e}")
            return []

    def _save_queue(self, items: List[QueueItem]) -> bool:
        """Save queue to file."""
        try:
            # Convert to serializable format
            queue_data = []
            for item in items:
                item_dict = asdict(item)
                item_dict["priority"] = item.priority.value
                item_dict["status"] = item.status.value
                queue_data.append(item_dict)

            # Write to temporary file first, then rename (atomic operation)
            temp_file = f"{self.queue_file}.tmp"
            with open(temp_file, "w") as f:
                json.dump(queue_data, f, indent=2)

            os.rename(temp_file, self.queue_file)
            return True
        except Exception as e:
            logger.error(f"Failed to save queue: {e}")
            return False

    def _calculate_retry_delay(self, attempt_count: int) -> int:
        """Calculate retry delay with exponential backoff."""
        base_delay = 60  # 1 minute base delay
        delay = base_delay * (self.retry_backoff_multiplier ** (attempt_count - 1))
        return min(delay, self.retry_max_delay)

    def add_to_queue(
        self,
        capture_id: str,
        item_type: str,
        source: str,
        user_context: Dict[str, Any] = None,
        priority: Priority = Priority.MEDIUM,
    ) -> bool:
        """
        Add captured item to processing queue with priority.

        Args:
            capture_id: Unique capture identifier
            item_type: Type of item ("url", "file", "text")
            source: Source of the item
            user_context: Optional user context
            priority: Processing priority

        Returns:
            True if successfully added to queue
        """
        try:
            with self._lock:
                # Load current queue
                items = self._load_queue()

                # Check if item already exists
                for item in items:
                    if item.capture_id == capture_id:
                        logger.warning(f"Item {capture_id} already in queue")
                        return False

                # Create new queue item
                new_item = QueueItem(
                    capture_id=capture_id,
                    item_type=item_type,
                    priority=priority,
                    status=QueueStatus.PENDING,
                    added_timestamp=datetime.now().isoformat(),
                    source=source,
                    user_context=user_context or {},
                )

                # Add to queue
                items.append(new_item)

                # Save queue
                if self._save_queue(items):
                    logger.info(
                        f"Added {capture_id} to processing queue with priority {priority.name}"
                    )
                    return True
                else:
                    logger.error(f"Failed to save queue after adding {capture_id}")
                    return False

        except Exception as e:
            logger.error(f"Failed to add {capture_id} to queue: {e}")
            return False

    def get_next_item(
        self, item_types: List[str] = None, processor_id: str = None
    ) -> Optional[QueueItem]:
        """
        Get next item for processing, respecting priorities.

        Args:
            item_types: Optional list of item types to process
            processor_id: Unique processor identifier

        Returns:
            Next item to process or None if queue is empty
        """
        try:
            with self._lock:
                items = self._load_queue()

                # Filter available items
                available_items = []
                for item in items:
                    # Skip if not in requested types
                    if item_types and item.item_type not in item_types:
                        continue

                    # Only process pending items or items ready for retry
                    if item.status == QueueStatus.PENDING:
                        available_items.append(item)
                    elif item.status == QueueStatus.RETRY:
                        # Check if retry time has passed
                        if item.next_retry_time:
                            retry_time = datetime.fromisoformat(item.next_retry_time)
                            if datetime.now() >= retry_time:
                                available_items.append(item)

                if not available_items:
                    return None

                # Sort by priority (lower number = higher priority)
                available_items.sort(
                    key=lambda x: (x.priority.value, x.added_timestamp)
                )

                # Get the highest priority item
                next_item = available_items[0]

                # Update item status
                next_item.status = QueueStatus.PROCESSING
                next_item.processor_id = processor_id or str(uuid.uuid4())
                next_item.processing_started = datetime.now().isoformat()
                next_item.processing_attempts += 1
                next_item.last_attempt_timestamp = datetime.now().isoformat()

                # Save updated queue
                if self._save_queue(items):
                    logger.info(
                        f"Assigned {next_item.capture_id} to processor {next_item.processor_id}"
                    )
                    return next_item
                else:
                    logger.error(
                        f"Failed to save queue after assigning {next_item.capture_id}"
                    )
                    return None

        except Exception as e:
            logger.error(f"Failed to get next item: {e}")
            return None

    def mark_processing(self, capture_id: str, processor_id: str) -> bool:
        """
        Mark item as currently being processed.

        Args:
            capture_id: Capture ID to mark as processing
            processor_id: Processor identifier

        Returns:
            True if successfully marked
        """
        try:
            with self._lock:
                items = self._load_queue()

                for item in items:
                    if item.capture_id == capture_id:
                        item.status = QueueStatus.PROCESSING
                        item.processor_id = processor_id
                        item.processing_started = datetime.now().isoformat()
                        item.processing_attempts += 1
                        item.last_attempt_timestamp = datetime.now().isoformat()

                        if self._save_queue(items):
                            logger.info(
                                f"Marked {capture_id} as processing by {processor_id}"
                            )
                            return True
                        else:
                            logger.error(
                                f"Failed to save queue after marking {capture_id}"
                            )
                            return False

                logger.warning(f"Item {capture_id} not found in queue")
                return False

        except Exception as e:
            logger.error(f"Failed to mark {capture_id} as processing: {e}")
            return False

    def mark_complete(
        self, capture_id: str, result_paths: Dict[str, str] = None
    ) -> bool:
        """
        Mark item as successfully processed.

        Args:
            capture_id: Capture ID to mark as complete
            result_paths: Dictionary of result file paths

        Returns:
            True if successfully marked
        """
        try:
            with self._lock:
                items = self._load_queue()

                for item in items:
                    if item.capture_id == capture_id:
                        item.status = QueueStatus.COMPLETED
                        item.processing_completed = datetime.now().isoformat()
                        item.result_paths = result_paths or {}

                        # Calculate processing time
                        if item.processing_started:
                            start_time = datetime.fromisoformat(item.processing_started)
                            end_time = datetime.now()
                            item.processing_time = (
                                end_time - start_time
                            ).total_seconds()

                        if self._save_queue(items):
                            logger.info(f"Marked {capture_id} as completed")
                            return True
                        else:
                            logger.error(
                                f"Failed to save queue after completing {capture_id}"
                            )
                            return False

                logger.warning(f"Item {capture_id} not found in queue")
                return False

        except Exception as e:
            logger.error(f"Failed to mark {capture_id} as complete: {e}")
            return False

    def mark_failed(self, capture_id: str, error: str, retry_count: int = 0) -> bool:
        """
        Mark item as failed, handle retry logic.

        Args:
            capture_id: Capture ID to mark as failed
            error: Error message
            retry_count: Current retry count

        Returns:
            True if successfully marked
        """
        try:
            with self._lock:
                items = self._load_queue()

                for item in items:
                    if item.capture_id == capture_id:
                        item.last_error = error
                        item.error_count += 1
                        item.processing_completed = datetime.now().isoformat()

                        # Determine if we should retry
                        if item.processing_attempts < self.max_retry_attempts:
                            item.status = QueueStatus.RETRY

                            # Calculate next retry time
                            delay = self._calculate_retry_delay(
                                item.processing_attempts
                            )
                            next_retry = datetime.now() + timedelta(seconds=delay)
                            item.next_retry_time = next_retry.isoformat()

                            logger.info(
                                f"Marked {capture_id} for retry in {delay} seconds"
                            )
                        else:
                            item.status = QueueStatus.FAILED
                            logger.warning(
                                f"Marked {capture_id} as permanently failed after {item.processing_attempts} attempts"
                            )

                        if self._save_queue(items):
                            return True
                        else:
                            logger.error(
                                f"Failed to save queue after marking {capture_id} as failed"
                            )
                            return False

                logger.warning(f"Item {capture_id} not found in queue")
                return False

        except Exception as e:
            logger.error(f"Failed to mark {capture_id} as failed: {e}")
            return False

    def get_queue_status(self) -> Dict[str, Any]:
        """
        Return comprehensive queue statistics.

        Returns:
            Dictionary with queue statistics
        """
        try:
            with self._lock:
                items = self._load_queue()

                status_counts = {}
                priority_counts = {}
                type_counts = {}

                for item in items:
                    # Count by status
                    status = item.status.value
                    status_counts[status] = status_counts.get(status, 0) + 1

                    # Count by priority
                    priority = item.priority.name
                    priority_counts[priority] = priority_counts.get(priority, 0) + 1

                    # Count by type
                    item_type = item.item_type
                    type_counts[item_type] = type_counts.get(item_type, 0) + 1

                # Find stuck items (processing too long)
                stuck_items = []
                now = datetime.now()
                for item in items:
                    if (
                        item.status == QueueStatus.PROCESSING
                        and item.processing_started
                    ):
                        start_time = datetime.fromisoformat(item.processing_started)
                        processing_time = (
                            now - start_time
                        ).total_seconds() / 60  # minutes

                        if processing_time > self.max_processing_time:
                            stuck_items.append(
                                {
                                    "capture_id": item.capture_id,
                                    "processor_id": item.processor_id,
                                    "processing_time_minutes": processing_time,
                                }
                            )

                return {
                    "total_items": len(items),
                    "status_counts": status_counts,
                    "priority_counts": priority_counts,
                    "type_counts": type_counts,
                    "stuck_items": stuck_items,
                    "queue_file": self.queue_file,
                    "last_updated": datetime.now().isoformat(),
                }

        except Exception as e:
            logger.error(f"Failed to get queue status: {e}")
            return {"error": str(e)}

    def cleanup_stale_items(self, max_age_hours: int = 24) -> int:
        """
        Clean up items stuck in processing state.

        Args:
            max_age_hours: Maximum age for processing items

        Returns:
            Number of items cleaned up
        """
        try:
            with self._lock:
                items = self._load_queue()
                cleaned_count = 0

                now = datetime.now()
                cutoff_time = now - timedelta(hours=max_age_hours)

                for item in items:
                    if (
                        item.status == QueueStatus.PROCESSING
                        and item.processing_started
                    ):
                        start_time = datetime.fromisoformat(item.processing_started)

                        if start_time < cutoff_time:
                            # Mark as failed due to timeout
                            item.status = QueueStatus.FAILED
                            item.last_error = (
                                f"Processing timed out after {max_age_hours} hours"
                            )
                            item.processing_completed = now.isoformat()
                            cleaned_count += 1

                            logger.warning(f"Cleaned up stale item {item.capture_id}")

                if cleaned_count > 0:
                    self._save_queue(items)
                    logger.info(f"Cleaned up {cleaned_count} stale items")

                return cleaned_count

        except Exception as e:
            logger.error(f"Failed to cleanup stale items: {e}")
            return 0

    def get_failed_items(self) -> List[QueueItem]:
        """Get all failed items."""
        try:
            with self._lock:
                items = self._load_queue()
                return [item for item in items if item.status == QueueStatus.FAILED]
        except Exception as e:
            logger.error(f"Failed to get failed items: {e}")
            return []

    def get_retry_items(self) -> List[QueueItem]:
        """Get all items waiting for retry."""
        try:
            with self._lock:
                items = self._load_queue()
                return [item for item in items if item.status == QueueStatus.RETRY]
        except Exception as e:
            logger.error(f"Failed to get retry items: {e}")
            return []

    def remove_item(self, capture_id: str) -> bool:
        """Remove item from queue."""
        try:
            with self._lock:
                items = self._load_queue()

                for i, item in enumerate(items):
                    if item.capture_id == capture_id:
                        del items[i]

                        if self._save_queue(items):
                            logger.info(f"Removed {capture_id} from queue")
                            return True
                        else:
                            logger.error(
                                f"Failed to save queue after removing {capture_id}"
                            )
                            return False

                logger.warning(f"Item {capture_id} not found in queue")
                return False

        except Exception as e:
            logger.error(f"Failed to remove {capture_id} from queue: {e}")
            return False


# Convenience functions for direct use
def add_to_queue(
    capture_id: str,
    item_type: str,
    source: str,
    user_context: Dict[str, Any] = None,
    priority: Priority = Priority.MEDIUM,
) -> bool:
    """Add item to processing queue."""
    queue = ProcessingQueue()
    return queue.add_to_queue(capture_id, item_type, source, user_context, priority)


def get_next_item(
    item_types: List[str] = None, processor_id: str = None
) -> Optional[QueueItem]:
    """Get next item for processing."""
    queue = ProcessingQueue()
    return queue.get_next_item(item_types, processor_id)


def mark_complete(capture_id: str, result_paths: Dict[str, str] = None) -> bool:
    """Mark item as completed."""
    queue = ProcessingQueue()
    return queue.mark_complete(capture_id, result_paths)


def mark_failed(capture_id: str, error: str, retry_count: int = 0) -> bool:
    """Mark item as failed."""
    queue = ProcessingQueue()
    return queue.mark_failed(capture_id, error, retry_count)


def get_queue_status() -> Dict[str, Any]:
    """Get queue status."""
    queue = ProcessingQueue()
    return queue.get_queue_status()
