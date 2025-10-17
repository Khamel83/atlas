#!/usr/bin/env python3
"""
Content Transaction System for Atlas

Simple transactional tracking with numeric IDs and stages.
One table to rule all metrics and progress tracking.

Table: content_transactions
- id: INTEGER (auto-incrementing numeric ID)
- content_id: TEXT (unique content identifier)
- stage: INTEGER (100-599 numeric stage)
- previous_stage: INTEGER (previous stage for progression tracking)
- action: TEXT (description of what happened)
- timestamp: DATETIME (when it happened)
- duration_ms: INTEGER (how long it took)
- metadata: TEXT (JSON with additional data)
- success: BOOLEAN (did the action succeed)
"""

import json
import sqlite3
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

class ContentTransactionSystem:
    """
    Simple transactional system for tracking all content processing.

    One table = all metrics, progress tracking, and analytics.
    """

    def __init__(self, db_path: str = "data/atlas.db"):
        self.db_path = db_path
        self._ensure_transactions_table()

    def _ensure_transactions_table(self):
        """Create the single transactions table if it doesn't exist"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS content_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content_id TEXT NOT NULL,
                    stage INTEGER NOT NULL,
                    previous_stage INTEGER,
                    action TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    duration_ms INTEGER,
                    metadata TEXT DEFAULT '{}',
                    success BOOLEAN DEFAULT TRUE,
                    project_id TEXT DEFAULT 'default',
                    batch_id TEXT DEFAULT NULL
                )
            """)

            # Create indexes for fast queries
            conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_content ON content_transactions(content_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_stage ON content_transactions(stage)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_timestamp ON content_transactions(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_project ON content_transactions(project_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_batch ON content_transactions(batch_id)")

            conn.commit()
            logger.info("Content transactions table ready")

    def record_transaction(self, content_id: str, stage: int, action: str,
                         previous_stage: int = None, duration_ms: int = None,
                         metadata: Dict[str, Any] = None, success: bool = True,
                         project_id: str = 'default', batch_id: str = None) -> int:
        """
        Record a content processing transaction.

        Args:
            content_id: Unique content identifier
            stage: Current numeric stage (100-599)
            action: Description of what happened
            previous_stage: Previous stage for progression tracking
            duration_ms: How long the action took
            metadata: Additional data as JSON
            success: Did the action succeed?
            project_id: Project identifier
            batch_id: Batch identifier for grouped operations

        Returns:
            Transaction ID
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO content_transactions (
                    content_id, stage, previous_stage, action, timestamp,
                    duration_ms, metadata, success, project_id, batch_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                content_id,
                stage,
                previous_stage,
                action,
                datetime.now().isoformat(),
                duration_ms,
                json.dumps(metadata or {}),
                success,
                project_id,
                batch_id
            ))
            conn.commit()
            return cursor.lastrowid

    def get_content_progress(self, content_id: str) -> List[Dict[str, Any]]:
        """Get complete progression history for a content item"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, stage, previous_stage, action, timestamp,
                       duration_ms, metadata, success
                FROM content_transactions
                WHERE content_id = ?
                ORDER BY timestamp ASC
            """, (content_id,))

            return [
                {
                    "transaction_id": row[0],
                    "stage": row[1],
                    "previous_stage": row[2],
                    "action": row[3],
                    "timestamp": row[4],
                    "duration_ms": row[5],
                    "metadata": json.loads(row[6] or "{}"),
                    "success": row[7]
                }
                for row in cursor.fetchall()
            ]

    def get_current_stage(self, content_id: str) -> Optional[int]:
        """Get the current stage for a content item"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT stage FROM content_transactions
                WHERE content_id = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (content_id,))
            result = cursor.fetchone()
            return result[0] if result else None

    def get_recent_activity(self, minutes: int = 60, project_id: str = None) -> List[Dict[str, Any]]:
        """Get activity in the last N minutes"""
        since_time = datetime.now() - timedelta(minutes=minutes)

        with sqlite3.connect(self.db_path) as conn:
            if project_id:
                cursor = conn.execute("""
                    SELECT id, content_id, stage, action, timestamp,
                           duration_ms, success
                    FROM content_transactions
                    WHERE timestamp >= ? AND project_id = ?
                    ORDER BY timestamp DESC
                    LIMIT 1000
                """, (since_time.isoformat(), project_id))
            else:
                cursor = conn.execute("""
                    SELECT id, content_id, stage, action, timestamp,
                           duration_ms, success
                    FROM content_transactions
                    WHERE timestamp >= ?
                    ORDER BY timestamp DESC
                    LIMIT 1000
                """, (since_time.isoformat(),))

            return [
                {
                    "transaction_id": row[0],
                    "content_id": row[1],
                    "stage": row[2],
                    "action": row[3],
                    "timestamp": row[4],
                    "duration_ms": row[5],
                    "success": row[6]
                }
                for row in cursor.fetchall()
            ]

    def get_stage_distribution(self, project_id: str = None) -> Dict[int, int]:
        """Get current distribution of content across stages"""
        with sqlite3.connect(self.db_path) as conn:
            if project_id:
                cursor = conn.execute("""
                    SELECT stage, COUNT(DISTINCT content_id) as count
                    FROM content_transactions
                    WHERE project_id = ?
                    GROUP BY stage
                """, (project_id,))
            else:
                cursor = conn.execute("""
                    SELECT stage, COUNT(DISTINCT content_id) as count
                    FROM content_transactions
                    GROUP BY stage
                """)

            return {row[0]: row[1] for row in cursor.fetchall()}

    def get_content_metrics(self, content_id: str) -> Dict[str, Any]:
        """Get comprehensive metrics for a content item"""
        transactions = self.get_content_progress(content_id)
        if not transactions:
            return {}

        total_duration = sum(t.get("duration_ms", 0) for t in transactions)
        total_steps = len(transactions)
        successful_steps = sum(1 for t in transactions if t["success"])
        current_stage = transactions[-1]["stage"]

        return {
            "content_id": content_id,
            "current_stage": current_stage,
            "total_steps": total_steps,
            "successful_steps": successful_steps,
            "success_rate": successful_steps / total_steps if total_steps > 0 else 0,
            "total_duration_ms": total_duration,
            "avg_duration_ms": total_duration / total_steps if total_steps > 0 else 0,
            "first_action": transactions[0]["timestamp"],
            "last_action": transactions[-1]["timestamp"]
        }

    def get_daily_summary(self, date: str = None, project_id: str = None) -> Dict[str, Any]:
        """Get daily processing summary"""
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")

        start_date = f"{date} 00:00:00"
        end_date = f"{date} 23:59:59"

        with sqlite3.connect(self.db_path) as conn:
            if project_id:
                cursor = conn.execute("""
                    SELECT
                        COUNT(DISTINCT content_id) as unique_content,
                        COUNT(*) as total_transactions,
                        SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_transactions,
                        AVG(duration_ms) as avg_duration_ms,
                        COUNT(CASE WHEN stage BETWEEN 100 AND 199 THEN 1 END) as acquisition_actions,
                        COUNT(CASE WHEN stage BETWEEN 200 AND 299 THEN 1 END) as validation_actions,
                        COUNT(CASE WHEN stage BETWEEN 300 AND 399 THEN 1 END) as processing_actions,
                        COUNT(CASE WHEN stage BETWEEN 400 AND 499 THEN 1 END) as enhancement_actions,
                        COUNT(CASE WHEN stage BETWEEN 500 AND 599 THEN 1 END) as finalization_actions
                    FROM content_transactions
                    WHERE timestamp BETWEEN ? AND ? AND project_id = ?
                """, (start_date, end_date, project_id))
            else:
                cursor = conn.execute("""
                    SELECT
                        COUNT(DISTINCT content_id) as unique_content,
                        COUNT(*) as total_transactions,
                        SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_transactions,
                        AVG(duration_ms) as avg_duration_ms,
                        COUNT(CASE WHEN stage BETWEEN 100 AND 199 THEN 1 END) as acquisition_actions,
                        COUNT(CASE WHEN stage BETWEEN 200 AND 299 THEN 1 END) as validation_actions,
                        COUNT(CASE WHEN stage BETWEEN 300 AND 399 THEN 1 END) as processing_actions,
                        COUNT(CASE WHEN stage BETWEEN 400 AND 499 THEN 1 END) as enhancement_actions,
                        COUNT(CASE WHEN stage BETWEEN 500 AND 599 THEN 1 END) as finalization_actions
                    FROM content_transactions
                    WHERE timestamp BETWEEN ? AND ?
                """, (start_date, end_date))

            result = cursor.fetchone()
            if result:
                return {
                    "date": date,
                    "unique_content": result[0],
                    "total_transactions": result[1],
                    "successful_transactions": result[2],
                    "success_rate": result[2] / result[1] if result[1] > 0 else 0,
                    "avg_duration_ms": result[3] or 0,
                    "acquisition_actions": result[4],
                    "validation_actions": result[5],
                    "processing_actions": result[6],
                    "enhancement_actions": result[7],
                    "finalization_actions": result[8]
                }
            return {}

    def get_stage_progression_stats(self) -> Dict[str, Any]:
        """Get statistics about stage progression efficiency"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT
                    stage,
                    previous_stage,
                    COUNT(*) as transition_count,
                    AVG(duration_ms) as avg_duration_ms,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_transitions,
                    COUNT(*) - SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as failed_transitions
                FROM content_transactions
                WHERE previous_stage IS NOT NULL
                GROUP BY stage, previous_stage
                ORDER BY stage, previous_stage
            """)

            return [
                {
                    "from_stage": row[1],
                    "to_stage": row[0],
                    "transition_count": row[2],
                    "avg_duration_ms": row[3] or 0,
                    "success_rate": row[4] / row[2] if row[2] > 0 else 0
                }
                for row in cursor.fetchall()
            ]

    def cleanup_old_transactions(self, days_to_keep: int = 30):
        """Clean up old transaction data"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                DELETE FROM content_transactions
                WHERE timestamp < ?
            """, (cutoff_date.isoformat(),))
            deleted_count = cursor.rowcount
            conn.commit()

            logger.info(f"Cleaned up {deleted_count} old transactions")
            return deleted_count

class TransactionTimer:
    """Context manager for timing transactions"""

    def __init__(self, transaction_system: ContentTransactionSystem,
                 content_id: str, stage: int, action: str,
                 previous_stage: int = None, metadata: Dict[str, Any] = None,
                 project_id: str = 'default', batch_id: str = None):
        self.transaction_system = transaction_system
        self.content_id = content_id
        self.stage = stage
        self.action = action
        self.previous_stage = previous_stage
        self.metadata = metadata
        self.project_id = project_id
        self.batch_id = batch_id
        self.start_time = None
        self.success = True

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = int((time.time() - self.start_time) * 1000)
        self.success = exc_type is None

        # Make metadata JSON-safe
        safe_metadata = self._make_json_safe(self.metadata)

        self.transaction_system.record_transaction(
            content_id=self.content_id,
            stage=self.stage,
            action=self.action,
            previous_stage=self.previous_stage,
            duration_ms=duration_ms,
            metadata=safe_metadata,
            success=self.success,
            project_id=self.project_id,
            batch_id=self.batch_id
        )

        if exc_type:
            logger.error(f"Transaction failed: {self.action} - {exc_val}")
            return False
        return True

    def _make_json_safe(self, obj):
        """Convert objects to JSON-serializable format."""
        if obj is None:
            return None
        elif isinstance(obj, dict):
            return {key: self._make_json_safe(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_safe(item) for item in obj]
        elif isinstance(obj, (str, int, float, bool)):
            return obj
        elif hasattr(obj, 'value'):  # For enums
            return obj.value
        elif hasattr(obj, '__dict__'):
            return str(obj)
        else:
            return str(obj)

if __name__ == "__main__":
    # Test the transaction system
    transactions = ContentTransactionSystem()

    print("Content Transaction System initialized")

    # Record some test transactions
    test_content = "test_content_123"

    with TransactionTimer(transactions, test_content, 100, "Content received"):
        time.sleep(0.1)  # Simulate work

    with TransactionTimer(transactions, test_content, 110, "Content queued", previous_stage=100):
        time.sleep(0.05)

    with TransactionTimer(transactions, test_content, 120, "Fetch attempting", previous_stage=110):
        time.sleep(0.2)

    # Get metrics
    print(f"Current stage: {transactions.get_current_stage(test_content)}")
    print(f"Content metrics: {transactions.get_content_metrics(test_content)}")
    print(f"Recent activity: {len(transactions.get_recent_activity(minutes=1))} items")
    print(f"Stage distribution: {transactions.get_stage_distribution()}")