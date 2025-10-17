#!/usr/bin/env python3
"""
ATLAS UNIVERSAL URL REGISTRY
Single source of truth for every URL ever submitted to Atlas
Implements immutable storage and complete audit trail
"""

import sqlite3
import json
import hashlib
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging

class UniversalURLRegistry:
    """
    Immutable URL Registry - Single source of truth for all URLs
    Guarantees no URL is ever lost and provides complete audit trail
    """

    def __init__(self, db_path: str = "data/atlas.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._ensure_registry_tables()

    def _ensure_registry_tables(self):
        """Create registry tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Main URL registry table - immutable once inserted
        cursor.execute("CREATE TABLE IF NOT EXISTS universal_url_registry ("
                "url_id TEXT PRIMARY KEY,"
                "url_hash TEXT UNIQUE NOT NULL,"
                "original_url TEXT NOT NULL,"
                "normalized_url TEXT NOT NULL,"
                "source_context TEXT,"
                "submission_timestamp TEXT NOT NULL,"
                "submitted_by TEXT,"
                "content_type_guess TEXT,"
                "priority INTEGER DEFAULT 50,"
                "status TEXT DEFAULT 'registered',"
                "created_at TEXT NOT NULL,"
                "is_immutable BOOLEAN DEFAULT 1"
            ")")

        # URL processing history - append-only audit trail
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS url_processing_history (
                history_id TEXT PRIMARY KEY,
                url_id TEXT NOT NULL,
                strategy_sequence TEXT,
                current_strategy INTEGER DEFAULT 0,
                total_attempts INTEGER DEFAULT 0,
                last_attempt_timestamp TEXT,
                next_retry_timestamp TEXT,
                processing_state TEXT DEFAULT 'pending',
                exhaustion_criteria TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (url_id) REFERENCES universal_url_registry(url_id)
            )
        """)

        # Individual attempt logs - detailed audit trail
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS url_attempt_details (
                attempt_id TEXT PRIMARY KEY,
                url_id TEXT NOT NULL,
                strategy_id INTEGER NOT NULL,
                strategy_name TEXT NOT NULL,
                attempt_timestamp TEXT NOT NULL,
                success BOOLEAN NOT NULL,
                quality_score REAL,
                processing_time_ms INTEGER,
                error_category TEXT,
                error_message TEXT,
                response_metadata TEXT,
                content_preview TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (url_id) REFERENCES universal_url_registry(url_id)
            )
        """)

        # Create indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_url_hash ON universal_url_registry(url_hash)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_url_status ON universal_url_registry(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_url_id ON url_processing_history(url_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_attempt_url_id ON url_attempt_details(url_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_attempt_strategy ON url_attempt_details(strategy_id, success)")

        conn.commit()
        conn.close()

    def _normalize_url(self, url: str) -> str:
        """Normalize URL for deduplication"""
        # Remove fragments, normalize case, sort parameters
        try:
            from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
            parsed = urlparse(url.lower())

            # Remove fragment
            clean_url = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                '',  # params
                '',  # query - keep for now but could normalize
                ''   # fragment
            ))

            return clean_url
        except:
            return url.lower().strip()

    def _generate_url_id(self, url: str) -> str:
        """Generate unique ID for URL"""
        url_hash = hashlib.sha256(self._normalize_url(url).encode()).hexdigest()[:16]
        return f"url_{url_hash}"

    def register_url(self, url: str, source_context: Dict[str, Any] = None,
                    submitted_by: str = "user", priority: int = 50) -> Dict[str, Any]:
        """
        Register a new URL in the registry.
        Returns URL record and indicates if it's a duplicate.
        """
        normalized_url = self._normalize_url(url)
        url_hash = hashlib.sha256(normalized_url.encode()).hexdigest()
        url_id = self._generate_url_id(url)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check if URL already exists
        cursor.execute("SELECT url_id, status FROM universal_url_registry WHERE url_hash = ?", (url_hash,))
        existing = cursor.fetchone()

        if existing:
            existing_id, status = existing
            result = {
                "url_id": existing_id,
                "is_duplicate": True,
                "status": status,
                "message": f"URL already registered with status: {status}"
            }
            conn.close()
            return result

        # Register new URL
        timestamp = datetime.now(timezone.utc).isoformat()

        cursor.execute("""
            INSERT INTO universal_url_registry
            (url_id, url_hash, original_url, normalized_url, source_context,
             submission_timestamp, submitted_by, priority, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            url_id, url_hash, url, normalized_url,
            json.dumps(source_context or {}),
            timestamp, submitted_by, priority, 'registered', timestamp
        ))

        # Create processing history record
        history_id = f"hist_{uuid.uuid4().hex[:12]}"
        cursor.execute("""
            INSERT INTO url_processing_history
            (history_id, url_id, processing_state, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (history_id, url_id, 'pending', timestamp, timestamp))

        conn.commit()
        conn.close()

        self.logger.info(f"Registered new URL: {url_id} - {url[:100]}...")

        return {
            "url_id": url_id,
            "is_duplicate": False,
            "status": "registered",
            "message": "URL successfully registered"
        }

    def log_attempt(self, url_id: str, strategy_id: int, strategy_name: str,
                   success: bool, quality_score: float = None,
                   processing_time_ms: int = None, error_category: str = None,
                   error_message: str = None, response_metadata: Dict = None,
                   content_preview: str = None) -> str:
        """Log a single extraction attempt"""
        attempt_id = f"att_{uuid.uuid4().hex[:12]}"
        timestamp = datetime.now(timezone.utc).isoformat()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Log the attempt
        cursor.execute("""
            INSERT INTO url_attempt_details
            (attempt_id, url_id, strategy_id, strategy_name, attempt_timestamp,
             success, quality_score, processing_time_ms, error_category,
             error_message, response_metadata, content_preview, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            attempt_id, url_id, strategy_id, strategy_name, timestamp,
            success, quality_score, processing_time_ms, error_category,
            error_message, json.dumps(response_metadata or {}),
            content_preview[:500] if content_preview else None, timestamp
        ))

        # Update processing history
        cursor.execute("""
            UPDATE url_processing_history
            SET total_attempts = total_attempts + 1,
                current_strategy = ?,
                last_attempt_timestamp = ?,
                updated_at = ?
            WHERE url_id = ?
        """, (strategy_id, timestamp, timestamp, url_id))

        # If successful, mark as completed
        if success:
            cursor.execute("""
                UPDATE universal_url_registry
                SET status = 'completed'
                WHERE url_id = ?
            """, (url_id,))

            cursor.execute("""
                UPDATE url_processing_history
                SET processing_state = 'completed',
                    updated_at = ?
                WHERE url_id = ?
            """, (timestamp, url_id))

        conn.commit()
        conn.close()

        status_text = "SUCCESS" if success else "FAILED"
        self.logger.info(f"Attempt logged: {url_id} - Strategy {strategy_id:03d} ({strategy_name}) - {status_text}")

        return attempt_id

    def get_url_history(self, url_id: str) -> Dict[str, Any]:
        """Get complete processing history for a URL"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get URL info
        cursor.execute("""
            SELECT url_id, original_url, status, submission_timestamp, source_context
            FROM universal_url_registry WHERE url_id = ?
        """, (url_id,))
        url_info = cursor.fetchone()

        if not url_info:
            conn.close()
            return {"error": "URL not found"}

        url_data = {
            "url_id": url_info[0],
            "original_url": url_info[1],
            "status": url_info[2],
            "submission_timestamp": url_info[3],
            "source_context": json.loads(url_info[4] or '{}')
        }

        # Get processing history
        cursor.execute("""
            SELECT processing_state, total_attempts, current_strategy,
                   last_attempt_timestamp, next_retry_timestamp, exhaustion_criteria
            FROM url_processing_history WHERE url_id = ?
        """, (url_id,))
        history = cursor.fetchone()

        if history:
            url_data["processing_state"] = history[0]
            url_data["total_attempts"] = history[1]
            url_data["current_strategy"] = history[2]
            url_data["last_attempt_timestamp"] = history[3]
            url_data["next_retry_timestamp"] = history[4]
            url_data["exhaustion_criteria"] = json.loads(history[5] or '{}')

        # Get all attempts
        cursor.execute("""
            SELECT strategy_id, strategy_name, attempt_timestamp, success,
                   quality_score, processing_time_ms, error_category, error_message
            FROM url_attempt_details
            WHERE url_id = ?
            ORDER BY strategy_id, attempt_timestamp
        """, (url_id,))

        attempts = []
        for row in cursor.fetchall():
            attempts.append({
                "strategy_id": row[0],
                "strategy_name": row[1],
                "attempt_timestamp": row[2],
                "success": row[3],
                "quality_score": row[4],
                "processing_time_ms": row[5],
                "error_category": row[6],
                "error_message": row[7]
            })

        url_data["attempts"] = attempts
        conn.close()

        return url_data

    def mark_exhausted(self, url_id: str, exhaustion_criteria: Dict[str, Any]) -> bool:
        """Mark a URL as exhausted with proof"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        timestamp = datetime.now(timezone.utc).isoformat()

        # Update registry status
        cursor.execute("""
            UPDATE universal_url_registry
            SET status = 'exhausted'
            WHERE url_id = ?
        """, (url_id,))

        # Update processing history with exhaustion proof
        cursor.execute("""
            UPDATE url_processing_history
            SET processing_state = 'exhausted',
                exhaustion_criteria = ?,
                updated_at = ?
            WHERE url_id = ?
        """, (json.dumps(exhaustion_criteria), timestamp, url_id))

        conn.commit()
        conn.close()

        self.logger.info(f"URL marked as exhausted: {url_id} - Criteria: {exhaustion_criteria}")
        return True

    def get_pending_urls(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get URLs pending processing"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT url_id, original_url, priority, submission_timestamp
            FROM universal_url_registry
            WHERE status = 'registered'
            ORDER BY priority DESC, submission_timestamp ASC
            LIMIT ?
        """, (limit,))

        urls = []
        for row in cursor.fetchall():
            urls.append({
                "url_id": row[0],
                "original_url": row[1],
                "priority": row[2],
                "submission_timestamp": row[3]
            })

        conn.close()
        return urls

    def get_queue_metrics(self) -> Dict[str, Any]:
        """Get overall queue metrics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Count by status
        cursor.execute("""
            SELECT status, COUNT(*)
            FROM universal_url_registry
            GROUP BY status
        """)
        status_counts = {row[0]: row[1] for row in cursor.fetchall()}

        # Get attempt statistics
        cursor.execute("""
            SELECT strategy_id, success, COUNT(*)
            FROM url_attempt_details
            GROUP BY strategy_id, success
        """)
        attempt_stats = {}
        for row in cursor.fetchall():
            strategy_id, success, count = row
            if strategy_id not in attempt_stats:
                attempt_stats[strategy_id] = {"success": 0, "failed": 0}
            attempt_stats[strategy_id]["success" if success else "failed"] = count

        conn.close()

        return {
            "status_counts": status_counts,
            "attempt_statistics": attempt_stats,
            "total_urls": sum(status_counts.values())
        }

# Test the registry
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    registry = UniversalURLRegistry()

    # Test registration
    test_urls = [
        "https://example.com/article1",
        "https://example.com/article2",
        "https://EXAMPLE.COM/article1",  # duplicate (case insensitive)
    ]

    for url in test_urls:
        result = registry.register_url(url, {"test": True})
        print(f"Registered {url}: {result}")

    # Test attempt logging
    url_id = registry._generate_url_id("https://example.com/article1")
    registry.log_attempt(url_id, 1, "direct_fetch", True, 0.85, 1500)
    registry.log_attempt(url_id, 2, "reader_mode", False, error_category="timeout")

    # Get history
    history = registry.get_url_history(url_id)
    print(f"URL History: {json.dumps(history, indent=2)}")

    # Get metrics
    metrics = registry.get_queue_metrics()
    print(f"Queue Metrics: {json.dumps(metrics, indent=2)}")