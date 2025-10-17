#!/usr/bin/env python3
"""
Resilient queue system with dead letter queue and retry logic
"""

import json
import time
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import sqlite3
from queue import Queue, Empty
import os
import sys
from pathlib import Path

# Add helpers to path for database integration
sys.path.insert(0, str(Path(__file__).parent))
from database_config import DatabaseManager

class TaskStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"
    RETRY = "retry"

class CircuitBreakerState(Enum):
    CLOSED = "closed"       # Normal operation
    OPEN = "open"          # Circuit breaker tripped
    HALF_OPEN = "half_open" # Testing if service recovered

@dataclass
class QueueTask:
    """Container for queue tasks"""
    id: str
    task_type: str
    task_data: Dict
    status: TaskStatus = TaskStatus.PENDING
    attempt_count: int = 0
    max_attempts: int = 9
    created_at: datetime = None
    updated_at: datetime = None
    next_retry_at: datetime = None
    error_message: str = None
    worker_id: str = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()

class CircuitBreaker:
    """Circuit breaker for queue workers"""

    def __init__(self, failure_threshold: int = 10, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED
        self.consecutive_successes = 0
        self.lock = threading.Lock()

    def can_execute(self) -> bool:
        """Check if operations can be executed"""
        with self.lock:
            if self.state == CircuitBreakerState.CLOSED:
                return True
            elif self.state == CircuitBreakerState.OPEN:
                # Check if recovery timeout has passed
                if (self.last_failure_time and
                    datetime.now() - self.last_failure_time > timedelta(seconds=self.recovery_timeout)):
                    self.state = CircuitBreakerState.HALF_OPEN
                    return True
                return False
            elif self.state == CircuitBreakerState.HALF_OPEN:
                return True

            return False

    def record_success(self):
        """Record successful operation"""
        with self.lock:
            if self.state == CircuitBreakerState.HALF_OPEN:
                self.consecutive_successes += 1
                if self.consecutive_successes >= 3:  # Need 3 successes to close
                    self.state = CircuitBreakerState.CLOSED
                    self.failure_count = 0
                    self.last_failure_time = None
                    self.consecutive_successes = 0
            elif self.state == CircuitBreakerState.CLOSED:
                # Reset failure count on success
                self.failure_count = max(0, self.failure_count - 1)

    def record_failure(self):
        """Record failed operation"""
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            self.consecutive_successes = 0

            if self.state == CircuitBreakerState.HALF_OPEN:
                self.state = CircuitBreakerState.OPEN
            elif self.state == CircuitBreakerState.CLOSED:
                if self.failure_count >= self.failure_threshold:
                    self.state = CircuitBreakerState.OPEN

    def get_status(self) -> Dict:
        """Get circuit breaker status"""
        with self.lock:
            return {
                'state': self.state.value,
                'failure_count': self.failure_count,
                'failure_threshold': self.failure_threshold,
                'last_failure_time': self.last_failure_time.isoformat() if self.last_failure_time else None,
                'can_execute': self.can_execute(),
                'consecutive_successes': self.consecutive_successes
            }

class ResilientQueue:
    """Resilient queue with dead letter queue and retry logic"""

    def __init__(self, queue_name: str = "default", db_path: str = "data/oos.db"):
        self.queue_name = queue_name
        self.db_manager = DatabaseManager(db_path)
        self.logger = self._setup_logging()
        self.circuit_breaker = CircuitBreaker()

        # Background processing
        self.worker_threads = {}
        self.shutdown_flag = threading.Event()

        # Retry schedule (exponential backoff in seconds)
        self.retry_schedule = [1, 2, 4, 8, 16, 32, 60, 120, 300]

        # Initialize database schema
        self._initialize_schema()

        # Start background processors
        self._start_background_processors()

        self.logger.info(f"Resilient queue '{queue_name}' initialized")

    def _setup_logging(self) -> logging.Logger:
        """Setup logging for queue manager"""
        logger = logging.getLogger(f'queue_manager_{self.queue_name}')
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.FileHandler('data/queue_manager.log')
            os.makedirs(os.path.dirname('data/queue_manager.log'), exist_ok=True)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def _initialize_schema(self):
        """Initialize database schema for queue"""
        try:
            with self.db_manager.pool.get_connection() as conn:
                # Main queue table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS queue_tasks (
                        id TEXT PRIMARY KEY,
                        queue_name TEXT NOT NULL,
                        task_type TEXT NOT NULL,
                        task_data TEXT NOT NULL,
                        status TEXT NOT NULL,
                        attempt_count INTEGER DEFAULT 0,
                        max_attempts INTEGER DEFAULT 9,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        next_retry_at TIMESTAMP NULL,
                        error_message TEXT NULL,
                        worker_id TEXT NULL
                    )
                ''')

                # Dead letter queue table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS dead_letter_tasks (
                        id TEXT PRIMARY KEY,
                        original_task_id TEXT NOT NULL,
                        queue_name TEXT NOT NULL,
                        task_type TEXT NOT NULL,
                        task_data TEXT NOT NULL,
                        final_error_message TEXT,
                        attempt_count INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        moved_to_dlq_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Queue metrics table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS queue_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        queue_name TEXT NOT NULL,
                        metric_name TEXT NOT NULL,
                        metric_value TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Create indexes
                conn.execute('CREATE INDEX IF NOT EXISTS idx_queue_tasks_status ON queue_tasks(queue_name, status)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_queue_tasks_retry ON queue_tasks(next_retry_at)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_queue_metrics_name ON queue_metrics(queue_name, metric_name)')

        except Exception as e:
            self.logger.error(f"Failed to initialize schema: {e}")
            raise

    def enqueue(self, task_type: str, task_data: Dict, max_attempts: int = 9) -> str:
        """Add task to queue"""
        task_id = str(uuid.uuid4())

        task = QueueTask(
            id=task_id,
            task_type=task_type,
            task_data=task_data,
            max_attempts=max_attempts
        )

        try:
            with self.db_manager.pool.get_connection() as conn:
                conn.execute('''
                    INSERT INTO queue_tasks
                    (id, queue_name, task_type, task_data, status, max_attempts, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    task.id,
                    self.queue_name,
                    task.task_type,
                    json.dumps(task.task_data),
                    task.status.value,
                    task.max_attempts,
                    task.created_at,
                    task.updated_at
                ))

            self.logger.info(f"Task {task_id} enqueued successfully")
            self._record_metric("tasks_enqueued", 1)

            return task_id

        except Exception as e:
            self.logger.error(f"Failed to enqueue task: {e}")
            raise

    def dequeue(self, worker_id: str, timeout: int = 30) -> Optional[QueueTask]:
        """Get next available task for processing"""
        if not self.circuit_breaker.can_execute():
            self.logger.warning(f"Circuit breaker is open, worker {worker_id} cannot dequeue")
            return None

        try:
            with self.db_manager.pool.get_connection() as conn:
                # Get next available task
                cursor = conn.execute('''
                    SELECT id, task_type, task_data, status, attempt_count, max_attempts,
                           created_at, updated_at, next_retry_at, error_message
                    FROM queue_tasks
                    WHERE queue_name = ?
                      AND status IN (?, ?)
                      AND (next_retry_at IS NULL OR next_retry_at <= CURRENT_TIMESTAMP)
                    ORDER BY created_at ASC
                    LIMIT 1
                ''', (self.queue_name, TaskStatus.PENDING.value, TaskStatus.RETRY.value))

                row = cursor.fetchone()
                if not row:
                    return None

                # Mark task as processing
                task_id = row[0]
                conn.execute('''
                    UPDATE queue_tasks
                    SET status = ?, worker_id = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (TaskStatus.PROCESSING.value, worker_id, task_id))

                # Create task object
                task = QueueTask(
                    id=row[0],
                    task_type=row[1],
                    task_data=json.loads(row[2]),
                    status=TaskStatus.PROCESSING,
                    attempt_count=row[4],
                    max_attempts=row[5],
                    created_at=datetime.fromisoformat(row[6]),
                    updated_at=datetime.now(),
                    next_retry_at=datetime.fromisoformat(row[8]) if row[8] else None,
                    error_message=row[9],
                    worker_id=worker_id
                )

                self.logger.debug(f"Task {task_id} dequeued by worker {worker_id}")
                return task

        except Exception as e:
            self.logger.error(f"Failed to dequeue task: {e}")
            return None

    def complete_task(self, task_id: str, worker_id: str) -> bool:
        """Mark task as completed"""
        try:
            with self.db_manager.pool.get_connection() as conn:
                cursor = conn.execute('''
                    UPDATE queue_tasks
                    SET status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND worker_id = ?
                ''', (TaskStatus.COMPLETED.value, task_id, worker_id))

                if cursor.rowcount > 0:
                    self.logger.info(f"Task {task_id} completed by worker {worker_id}")
                    self.circuit_breaker.record_success()
                    self._record_metric("tasks_completed", 1)
                    return True
                else:
                    self.logger.warning(f"Task {task_id} not found or not assigned to worker {worker_id}")
                    return False

        except Exception as e:
            self.logger.error(f"Failed to complete task {task_id}: {e}")
            return False

    def fail_task(self, task_id: str, worker_id: str, error_message: str) -> bool:
        """Mark task as failed and schedule retry or move to DLQ"""
        try:
            with self.db_manager.pool.get_connection() as conn:
                # Get current task state
                cursor = conn.execute('''
                    SELECT attempt_count, max_attempts
                    FROM queue_tasks
                    WHERE id = ? AND worker_id = ?
                ''', (task_id, worker_id))

                row = cursor.fetchone()
                if not row:
                    self.logger.warning(f"Task {task_id} not found or not assigned to worker {worker_id}")
                    return False

                attempt_count = row[0] + 1
                max_attempts = row[1]

                if attempt_count >= max_attempts:
                    # Move to dead letter queue
                    return self._move_to_dead_letter_queue(task_id, error_message, attempt_count, conn)
                else:
                    # Schedule retry
                    return self._schedule_retry(task_id, attempt_count, error_message, conn)

        except Exception as e:
            self.logger.error(f"Failed to fail task {task_id}: {e}")
            self.circuit_breaker.record_failure()
            return False

    def _schedule_retry(self, task_id: str, attempt_count: int, error_message: str, conn) -> bool:
        """Schedule task for retry with exponential backoff"""
        try:
            # Calculate next retry time
            delay_index = min(attempt_count - 1, len(self.retry_schedule) - 1)
            delay_seconds = self.retry_schedule[delay_index]
            next_retry_at = datetime.now() + timedelta(seconds=delay_seconds)

            # Update task
            cursor = conn.execute('''
                UPDATE queue_tasks
                SET status = ?, attempt_count = ?, error_message = ?,
                    next_retry_at = ?, updated_at = CURRENT_TIMESTAMP, worker_id = NULL
                WHERE id = ?
            ''', (TaskStatus.RETRY.value, attempt_count, error_message, next_retry_at, task_id))

            if cursor.rowcount > 0:
                self.logger.info(f"Task {task_id} scheduled for retry #{attempt_count} in {delay_seconds}s")
                self._record_metric("tasks_retried", 1)
                return True
            else:
                return False

        except Exception as e:
            self.logger.error(f"Failed to schedule retry for task {task_id}: {e}")
            return False

    def _move_to_dead_letter_queue(self, task_id: str, error_message: str, attempt_count: int, conn) -> bool:
        """Move task to dead letter queue"""
        try:
            # Get task data
            cursor = conn.execute('''
                SELECT task_type, task_data, created_at
                FROM queue_tasks
                WHERE id = ?
            ''', (task_id,))

            row = cursor.fetchone()
            if not row:
                return False

            # Insert into dead letter queue
            conn.execute('''
                INSERT INTO dead_letter_tasks
                (id, original_task_id, queue_name, task_type, task_data,
                 final_error_message, attempt_count, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                str(uuid.uuid4()),
                task_id,
                self.queue_name,
                row[0],  # task_type
                row[1],  # task_data
                error_message,
                attempt_count,
                row[2]   # created_at
            ))

            # Update original task
            conn.execute('''
                UPDATE queue_tasks
                SET status = ?, error_message = ?, updated_at = CURRENT_TIMESTAMP, worker_id = NULL
                WHERE id = ?
            ''', (TaskStatus.DEAD_LETTER.value, error_message, task_id))

            self.logger.warning(f"Task {task_id} moved to dead letter queue after {attempt_count} attempts")
            self.circuit_breaker.record_failure()
            self._record_metric("tasks_dead_lettered", 1)

            return True

        except Exception as e:
            self.logger.error(f"Failed to move task {task_id} to dead letter queue: {e}")
            return False

    def retry_dead_letter_task(self, dlq_task_id: str) -> bool:
        """Manually retry a task from dead letter queue"""
        try:
            with self.db_manager.pool.get_connection() as conn:
                # Get task from DLQ
                cursor = conn.execute('''
                    SELECT original_task_id, task_type, task_data
                    FROM dead_letter_tasks
                    WHERE id = ? AND queue_name = ?
                ''', (dlq_task_id, self.queue_name))

                row = cursor.fetchone()
                if not row:
                    self.logger.warning(f"Dead letter task {dlq_task_id} not found")
                    return False

                original_task_id, task_type, task_data = row

                # Create new task (reset attempts)
                new_task_id = self.enqueue(task_type, json.loads(task_data))

                # Remove from DLQ
                conn.execute('''
                    DELETE FROM dead_letter_tasks WHERE id = ?
                ''', (dlq_task_id,))

                self.logger.info(f"Dead letter task {dlq_task_id} retried as new task {new_task_id}")
                return True

        except Exception as e:
            self.logger.error(f"Failed to retry dead letter task {dlq_task_id}: {e}")
            return False

    def get_queue_stats(self) -> Dict:
        """Get queue statistics"""
        try:
            with self.db_manager.pool.get_connection() as conn:
                stats = {}

                # Task counts by status
                cursor = conn.execute('''
                    SELECT status, COUNT(*)
                    FROM queue_tasks
                    WHERE queue_name = ?
                    GROUP BY status
                ''', (self.queue_name,))

                for status, count in cursor.fetchall():
                    stats[f"tasks_{status}"] = count

                # Dead letter queue count
                cursor = conn.execute('''
                    SELECT COUNT(*)
                    FROM dead_letter_tasks
                    WHERE queue_name = ?
                ''', (self.queue_name,))

                stats["tasks_in_dlq"] = cursor.fetchone()[0]

                # Average processing time (simplified)
                cursor = conn.execute('''
                    SELECT AVG(
                        CASE WHEN updated_at > created_at THEN
                            (julianday(updated_at) - julianday(created_at)) * 24 * 60 * 60
                        ELSE 0 END
                    )
                    FROM queue_tasks
                    WHERE queue_name = ? AND status = ?
                ''', (self.queue_name, TaskStatus.COMPLETED.value))

                avg_time = cursor.fetchone()[0]
                stats["avg_processing_time_seconds"] = round(avg_time or 0, 2)

                # Add circuit breaker status
                stats["circuit_breaker"] = self.circuit_breaker.get_status()

                return stats

        except Exception as e:
            self.logger.error(f"Failed to get queue stats: {e}")
            return {"error": str(e)}

    def _record_metric(self, metric_name: str, value: Any):
        """Record queue metric"""
        try:
            with self.db_manager.pool.get_connection() as conn:
                conn.execute('''
                    INSERT INTO queue_metrics (queue_name, metric_name, metric_value)
                    VALUES (?, ?, ?)
                ''', (self.queue_name, metric_name, str(value)))

                # Keep only last 1000 metrics per queue
                conn.execute('''
                    DELETE FROM queue_metrics
                    WHERE queue_name = ? AND id NOT IN (
                        SELECT id FROM queue_metrics
                        WHERE queue_name = ?
                        ORDER BY timestamp DESC
                        LIMIT 1000
                    )
                ''', (self.queue_name, self.queue_name))

        except Exception as e:
            self.logger.debug(f"Failed to record metric {metric_name}: {e}")

    def _start_background_processors(self):
        """Start background processing threads"""
        # Cleanup thread
        cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
        cleanup_thread.start()
        self.worker_threads["cleanup"] = cleanup_thread

        # Retry processor thread
        retry_thread = threading.Thread(target=self._retry_processor, daemon=True)
        retry_thread.start()
        self.worker_threads["retry"] = retry_thread

    def _cleanup_worker(self):
        """Background worker to cleanup old tasks"""
        cleanup_interval = 6 * 3600  # 6 hours

        while not self.shutdown_flag.is_set():
            try:
                self._cleanup_old_tasks()

                # Wait for next cleanup
                if self.shutdown_flag.wait(cleanup_interval):
                    break

            except Exception as e:
                self.logger.error(f"Cleanup worker error: {e}")
                if self.shutdown_flag.wait(300):  # Wait 5 minutes on error
                    break

    def _cleanup_old_tasks(self):
        """Clean up old completed and dead letter tasks"""
        try:
            cutoff_date = datetime.now() - timedelta(days=7)

            with self.db_manager.pool.get_connection() as conn:
                # Clean up old completed tasks
                cursor = conn.execute('''
                    DELETE FROM queue_tasks
                    WHERE queue_name = ? AND status = ? AND updated_at < ?
                ''', (self.queue_name, TaskStatus.COMPLETED.value, cutoff_date))

                completed_cleaned = cursor.rowcount

                # Clean up old dead letter tasks
                cursor = conn.execute('''
                    DELETE FROM dead_letter_tasks
                    WHERE queue_name = ? AND moved_to_dlq_at < ?
                ''', (self.queue_name, cutoff_date))

                dlq_cleaned = cursor.rowcount

                if completed_cleaned > 0 or dlq_cleaned > 0:
                    self.logger.info(f"Cleanup: removed {completed_cleaned} completed tasks, {dlq_cleaned} DLQ tasks")

        except Exception as e:
            self.logger.error(f"Failed to cleanup old tasks: {e}")

    def _retry_processor(self):
        """Background processor for retry tasks"""
        check_interval = 60  # Check every minute

        while not self.shutdown_flag.is_set():
            try:
                self._process_ready_retries()

                if self.shutdown_flag.wait(check_interval):
                    break

            except Exception as e:
                self.logger.error(f"Retry processor error: {e}")
                if self.shutdown_flag.wait(60):  # Wait 1 minute on error
                    break

    def _process_ready_retries(self):
        """Process tasks that are ready for retry"""
        try:
            with self.db_manager.pool.get_connection() as conn:
                # Find tasks ready for retry
                cursor = conn.execute('''
                    SELECT id
                    FROM queue_tasks
                    WHERE queue_name = ? AND status = ? AND next_retry_at <= CURRENT_TIMESTAMP
                ''', (self.queue_name, TaskStatus.RETRY.value))

                ready_tasks = [row[0] for row in cursor.fetchall()]

                if ready_tasks:
                    # Mark them as pending
                    placeholders = ','.join('?' * len(ready_tasks))
                    conn.execute(f'''
                        UPDATE queue_tasks
                        SET status = ?, next_retry_at = NULL, updated_at = CURRENT_TIMESTAMP
                        WHERE id IN ({placeholders})
                    ''', [TaskStatus.PENDING.value] + ready_tasks)

                    self.logger.debug(f"Marked {len(ready_tasks)} tasks as ready for retry")

        except Exception as e:
            self.logger.error(f"Failed to process ready retries: {e}")

    def shutdown(self):
        """Shutdown the queue manager"""
        self.logger.info(f"Shutting down queue '{self.queue_name}'")

        # Signal shutdown
        self.shutdown_flag.set()

        # Wait for worker threads
        for name, thread in self.worker_threads.items():
            if thread.is_alive():
                self.logger.info(f"Waiting for {name} thread to finish...")
                thread.join(timeout=30)

        # Shutdown database manager
        self.db_manager.shutdown()

        self.logger.info(f"Queue '{self.queue_name}' shutdown complete")

# Global queue manager instances
_queue_managers = {}
_queue_lock = threading.Lock()

def get_queue_manager(queue_name: str = "default") -> ResilientQueue:
    """Get or create queue manager instance"""
    with _queue_lock:
        if queue_name not in _queue_managers:
            _queue_managers[queue_name] = ResilientQueue(queue_name)
        return _queue_managers[queue_name]

def get_circuit_breaker_status(queue_name: str = "default") -> Dict:
    """Get circuit breaker status for queue"""
    queue_manager = get_queue_manager(queue_name)
    return queue_manager.circuit_breaker.get_status()

if __name__ == "__main__":
    # CLI interface for testing
    import argparse

    parser = argparse.ArgumentParser(description="Queue Manager")
    parser.add_argument("--queue", default="default", help="Queue name")
    parser.add_argument("--enqueue", help="Enqueue a test task")
    parser.add_argument("--stats", action="store_true", help="Show queue stats")
    parser.add_argument("--circuit-breaker", action="store_true", help="Show circuit breaker status")
    parser.add_argument("--cleanup", action="store_true", help="Run cleanup")

    args = parser.parse_args()

    queue_manager = get_queue_manager(args.queue)

    try:
        if args.enqueue:
            task_id = queue_manager.enqueue("test_task", {"message": args.enqueue})
            print(f"Enqueued task: {task_id}")
        elif args.stats:
            stats = queue_manager.get_queue_stats()
            print(json.dumps(stats, indent=2))
        elif args.circuit_breaker:
            status = queue_manager.circuit_breaker.get_status()
            print(json.dumps(status, indent=2))
        elif args.cleanup:
            queue_manager._cleanup_old_tasks()
            print("Cleanup completed")
        else:
            print("Use --help for usage information")
    finally:
        queue_manager.shutdown()