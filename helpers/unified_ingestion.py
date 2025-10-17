"""
ATLAS UNIFIED INGESTION SYSTEM

🚨 CRITICAL ARCHITECTURE RULE:
ALL URL ingestion MUST go through this single funnel.
NO EXCEPTIONS. NO SHORTCUTS. NO BYPASSES.

This is the ONLY way URLs should enter the Atlas processing pipeline.
"""

import uuid
import sqlite3
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class UnifiedIngestionManager:
    """
    Single source of truth for ALL Atlas content ingestion.

    🎯 ARCHITECTURE PRINCIPLE:
    One funnel -> One queue -> Multiple processors
    """

    def __init__(self, db_path: str = "data/atlas.db"):
        self.db_path = db_path
        self._ensure_queue_table()

    def _ensure_queue_table(self):
        """Ensure worker_jobs table exists"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS worker_jobs (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    data TEXT NOT NULL,
                    priority INTEGER DEFAULT 50,
                    status TEXT DEFAULT 'pending',
                    assigned_worker TEXT,
                    created_at TEXT NOT NULL,
                    assigned_at TEXT,
                    completed_at TEXT,
                    result TEXT,
                    retry_count INTEGER DEFAULT 0
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_worker_jobs_status_priority ON worker_jobs(status, priority DESC, created_at ASC)")
            conn.commit()

    def submit_single_url(self, url: str, priority: int = 50, source: str = "manual") -> str:
        """
        Submit a single URL for processing.

        🚨 THIS IS THE ONLY WAY TO SUBMIT URLS

        Args:
            url: The URL to process
            priority: Job priority (higher = processed first)
            source: Where this URL came from (manual, csv, api, etc.)

        Returns:
            job_id: Unique identifier for tracking this job
        """
        if not url or not url.strip():
            raise ValueError("URL cannot be empty")

        job_id = str(uuid.uuid4())
        job_data = {
            "url": url.strip(),
            "source": source,
            "submitted_at": datetime.now().isoformat()
        }

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO worker_jobs (id, type, data, priority, status, created_at)
                VALUES (?, 'url_processing', ?, ?, 'pending', ?)
            """, (job_id, json.dumps(job_data), priority, datetime.now().isoformat()))
            conn.commit()

        logger.info(f"✅ Queued URL: {url} (job: {job_id[:8]}, source: {source})")
        return job_id

    def submit_bulk_urls(self, urls: List[str], priority: int = 50, source: str = "bulk") -> List[str]:
        """
        Submit multiple URLs for processing.

        🚨 THIS IS THE ONLY WAY TO SUBMIT BULK URLS

        Args:
            urls: List of URLs to process
            priority: Job priority for all URLs
            source: Where these URLs came from

        Returns:
            List of job_ids for tracking
        """
        if not urls:
            return []

        job_ids = []
        current_time = datetime.now().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            for url in urls:
                if not url or not url.strip():
                    continue

                job_id = str(uuid.uuid4())
                job_data = {
                    "url": url.strip(),
                    "source": source,
                    "submitted_at": current_time
                }

                conn.execute("""
                    INSERT INTO worker_jobs (id, type, data, priority, status, created_at)
                    VALUES (?, 'url_processing', ?, ?, 'pending', ?)
                """, (job_id, json.dumps(job_data), priority, current_time))

                job_ids.append(job_id)

            conn.commit()

        logger.info(f"✅ Queued {len(job_ids)} URLs from {source}")
        return job_ids

    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT status, COUNT(*) as count
                FROM worker_jobs
                WHERE type = 'url_processing'
                GROUP BY status
            """)

            status_counts = dict(cursor.fetchall())
            total = sum(status_counts.values())

            return {
                "total_jobs": total,
                "pending": status_counts.get("pending", 0),
                "running": status_counts.get("running", 0),
                "completed": status_counts.get("completed", 0),
                "failed": status_counts.get("failed", 0)
            }


# Global instance - USE THIS EVERYWHERE
_ingestion_manager = UnifiedIngestionManager()

def submit_url(url: str, priority: int = 50, source: str = "manual") -> str:
    """
    🚨 UNIVERSAL URL SUBMISSION FUNCTION

    THIS IS THE ONLY FUNCTION THAT SHOULD BE USED TO SUBMIT URLS.
    Import this function anywhere you need to submit URLs.

    NO MORE:
    - Direct HTTP calls to submit-url endpoints
    - Creating temp files
    - Bypassing the queue
    - Multiple ingestion paths

    ALWAYS USE THIS.
    """
    return _ingestion_manager.submit_single_url(url, priority, source)

def submit_urls(urls: List[str], priority: int = 50, source: str = "bulk") -> List[str]:
    """
    🚨 UNIVERSAL BULK URL SUBMISSION FUNCTION

    THIS IS THE ONLY FUNCTION FOR BULK URL SUBMISSION.
    Use this for CSV processing, batch imports, etc.

    ALWAYS USE THIS FOR BULK OPERATIONS.
    """
    return _ingestion_manager.submit_bulk_urls(urls, priority, source)

def get_ingestion_status() -> Dict[str, Any]:
    """Get current ingestion queue status"""
    return _ingestion_manager.get_queue_status()


if __name__ == "__main__":
    # Test the system
    manager = UnifiedIngestionManager()
    status = manager.get_queue_status()
    print(f"Queue status: {status}")