#!/usr/bin/env python3
"""
Nuclear Fallback System - The Ultimate Safety Net

This system ensures NO content is EVER lost. If everything fails,
this system will keep retrying indefinitely with intelligent backoff
until success is achieved or human intervention is required.

Philosophy: "Compute time doesn't matter, human time does"
"""

import asyncio
import sqlite3
import json
import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from helpers.google_search_queue import GoogleSearchQueue, QueuePriority
from helpers.google_search_fallback import search_with_google_fallback
from helpers.config import load_config
from ingest.link_dispatcher import process_url_file
import uuid
import tempfile

logger = logging.getLogger(__name__)

class FailureType(Enum):
    """Types of failures that can be retried"""
    URL_PROCESSING = "url_processing"
    GOOGLE_SEARCH = "google_search"
    CONTENT_EXTRACTION = "content_extraction"
    API_ERROR = "api_error"
    NETWORK_ERROR = "network_error"
    UNKNOWN = "unknown"

class RetryStatus(Enum):
    """Status of retry attempts"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    PERMANENT_FAILURE = "permanent_failure"
    HUMAN_INTERVENTION_REQUIRED = "human_intervention_required"

@dataclass
class FailureRecord:
    """Record of a failed operation for nuclear retry"""
    id: Optional[int] = None
    failure_type: str = FailureType.UNKNOWN.value
    original_url: str = ""
    content_title: str = ""
    error_message: str = ""
    retry_status: str = RetryStatus.PENDING.value
    retry_count: int = 0
    first_failed_at: Optional[str] = None
    last_retry_at: Optional[str] = None
    next_retry_at: Optional[str] = None
    metadata: Optional[str] = None  # JSON string
    success_url: Optional[str] = None
    human_notes: Optional[str] = None

class NuclearFallbackSystem:
    """The ultimate safety net that never gives up"""

    def __init__(self, db_path: str = "data/nuclear_fallback.db"):
        self.db_path = db_path
        self.config = load_config()
        self._ensure_database()

        # Retry configuration
        self.max_retry_attempts = 100  # Keep trying for a long time
        self.base_backoff_seconds = 60  # 1 minute base
        self.max_backoff_seconds = 86400  # 24 hours max
        self.human_intervention_threshold = 30  # After 30 failures, alert human

    def _ensure_database(self):
        """Ensure nuclear fallback database exists"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS nuclear_failures (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    failure_type TEXT NOT NULL,
                    original_url TEXT NOT NULL,
                    content_title TEXT,
                    error_message TEXT,
                    retry_status TEXT DEFAULT 'pending',
                    retry_count INTEGER DEFAULT 0,
                    first_failed_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_retry_at TEXT,
                    next_retry_at TEXT,
                    metadata TEXT,
                    success_url TEXT,
                    human_notes TEXT
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_nuclear_retry_status
                ON nuclear_failures(retry_status)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_nuclear_next_retry
                ON nuclear_failures(next_retry_at)
            """)

    def record_failure(self, failure_type: FailureType, url: str, title: str = "",
                      error_message: str = "", metadata: Dict = None) -> int:
        """Record a failure for nuclear retry"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO nuclear_failures
                (failure_type, original_url, content_title, error_message, metadata, next_retry_at)
                VALUES (?, ?, ?, ?, ?, datetime('now', '+1 minute'))
            """, (
                failure_type.value,
                url,
                title,
                error_message,
                json.dumps(metadata) if metadata else None
            ))

            failure_id = cursor.lastrowid
            logger.warning(f"🆘 Nuclear Fallback: Recorded failure #{failure_id} for {url}")
            return failure_id

    def get_pending_retries(self, limit: int = 50) -> List[FailureRecord]:
        """Get failures ready for retry"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM nuclear_failures
                WHERE retry_status = 'pending'
                  AND (next_retry_at IS NULL OR next_retry_at <= datetime('now'))
                  AND retry_count < ?
                ORDER BY first_failed_at ASC
                LIMIT ?
            """, (self.max_retry_attempts, limit))

            return [FailureRecord(**dict(row)) for row in cursor.fetchall()]

    async def process_nuclear_retries(self):
        """Process all pending nuclear retries - THE MAIN EVENT"""
        logger.info("🚀 Nuclear Fallback: Starting retry processing session")

        retries = self.get_pending_retries()
        if not retries:
            logger.info("✅ Nuclear Fallback: No pending retries")
            return {"processed": 0, "successful": 0, "failed": 0, "human_required": 0}

        logger.info(f"🔄 Nuclear Fallback: Processing {len(retries)} pending retries")

        stats = {"processed": 0, "successful": 0, "failed": 0, "human_required": 0}

        for failure in retries:
            try:
                await self._process_single_retry(failure, stats)

                # Small delay between retries to be respectful
                await asyncio.sleep(2)

            except Exception as e:
                logger.error(f"❌ Nuclear Fallback: Error processing retry {failure.id}: {e}")
                self._mark_retry_failed(failure.id, str(e))
                stats["failed"] += 1

        logger.info(f"🏁 Nuclear Fallback: Session complete. Stats: {stats}")
        return stats

    async def _process_single_retry(self, failure: FailureRecord, stats: Dict):
        """Process a single retry with maximum determination"""
        logger.info(f"🔄 Nuclear Retry #{failure.retry_count + 1}: {failure.original_url}")

        # Mark as in progress
        self._mark_in_progress(failure.id)
        stats["processed"] += 1

        success = False

        try:
            if failure.failure_type == FailureType.URL_PROCESSING.value:
                success = await self._retry_url_processing(failure)
            elif failure.failure_type == FailureType.GOOGLE_SEARCH.value:
                success = await self._retry_google_search(failure)
            elif failure.failure_type == FailureType.CONTENT_EXTRACTION.value:
                success = await self._retry_content_extraction(failure)
            else:
                # Try everything - the nuclear approach
                success = await self._nuclear_retry_everything(failure)

            if success:
                self._mark_success(failure.id, failure.success_url)
                stats["successful"] += 1
                logger.info(f"🎉 Nuclear Success: {failure.original_url}")
            else:
                # Schedule next retry with exponential backoff
                next_retry = self._calculate_next_retry(failure.retry_count + 1)

                if failure.retry_count + 1 >= self.human_intervention_threshold:
                    self._mark_human_intervention_required(failure.id, "Exceeded retry threshold")
                    stats["human_required"] += 1
                    logger.warning(f"🚨 Human intervention required: {failure.original_url}")
                else:
                    self._schedule_next_retry(failure.id, next_retry)
                    stats["failed"] += 1
                    logger.info(f"⏰ Nuclear Retry scheduled: {failure.original_url} at {next_retry}")

        except Exception as e:
            logger.error(f"❌ Nuclear Retry failed: {failure.original_url} - {e}")
            next_retry = self._calculate_next_retry(failure.retry_count + 1)
            self._schedule_next_retry(failure.id, next_retry, str(e))
            stats["failed"] += 1

    async def _nuclear_retry_everything(self, failure: FailureRecord) -> bool:
        """The nuclear option - try EVERYTHING until something works"""
        url = failure.original_url
        title = failure.content_title

        logger.info(f"💥 NUCLEAR RETRY: Trying everything for {url}")

        # Strategy 1: Direct URL processing retry
        try:
            success = await self._retry_url_processing(failure)
            if success:
                logger.info(f"✅ Nuclear: Direct processing succeeded")
                return True
        except Exception as e:
            logger.debug(f"Nuclear: Direct processing failed: {e}")

        # Strategy 2: Google Search for alternatives
        try:
            success = await self._retry_google_search(failure)
            if success:
                logger.info(f"✅ Nuclear: Google Search succeeded")
                return True
        except Exception as e:
            logger.debug(f"Nuclear: Google Search failed: {e}")

        # Strategy 3: Try with different search queries
        search_variations = self._generate_search_variations(url, title)
        for query in search_variations:
            try:
                alternative_url = await search_with_google_fallback(query, priority=1)
                if alternative_url and alternative_url != url:
                    success = await self._try_process_url(alternative_url)
                    if success:
                        failure.success_url = alternative_url
                        logger.info(f"✅ Nuclear: Alternative query succeeded: '{query}' -> {alternative_url}")
                        return True

                await asyncio.sleep(1)  # Brief pause between variations

            except Exception as e:
                logger.debug(f"Nuclear: Search variation '{query}' failed: {e}")
                continue

        # Strategy 4: Wait and try again (maybe temporary issue)
        logger.info(f"💤 Nuclear: All strategies failed, will retry later: {url}")
        return False

    async def _retry_url_processing(self, failure: FailureRecord) -> bool:
        """Retry direct URL processing"""
        try:
            success = await self._try_process_url(failure.original_url)
            return success
        except Exception as e:
            logger.debug(f"URL processing retry failed: {e}")
            return False

    async def _retry_google_search(self, failure: FailureRecord) -> bool:
        """Retry Google Search for alternative URL"""
        try:
            # Generate search query from URL and title
            query = self._extract_search_query(failure.original_url, failure.content_title)

            alternative_url = await search_with_google_fallback(query, priority=2)

            if alternative_url and alternative_url != failure.original_url:
                success = await self._try_process_url(alternative_url)
                if success:
                    failure.success_url = alternative_url
                    return True

            return False

        except Exception as e:
            logger.debug(f"Google Search retry failed: {e}")
            return False

    async def _retry_content_extraction(self, failure: FailureRecord) -> bool:
        """Retry content extraction with different strategies"""
        # This could try different extraction methods
        return await self._retry_url_processing(failure)

    async def _try_process_url(self, url: str) -> bool:
        """Try to process a URL through Atlas ingestion"""
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(url)
                temp_file = f.name

            results = process_url_file(temp_file, self.config)
            os.unlink(temp_file)

            # Check if processing was successful
            if results.get("successful") and len(results["successful"]) > 0:
                return True
            elif results.get("duplicate") and len(results["duplicate"]) > 0:
                # Duplicate is also success for our purposes
                return True
            else:
                return False

        except Exception as e:
            logger.debug(f"URL processing failed: {e}")
            return False

    def _generate_search_variations(self, url: str, title: str) -> List[str]:
        """Generate different search query variations"""
        queries = []

        if title and title.strip():
            # Clean title variations
            clean_title = title.replace('[', '').replace(']', '').replace('(', '').replace(')', '')
            queries.append(clean_title[:80])  # Truncate long titles

            # Title with site
            from urllib.parse import urlparse
            domain = urlparse(url).netloc.replace('www.', '').split('.')[0]
            queries.append(f"{clean_title[:60]} site:{domain}")

        # URL-based queries
        from urllib.parse import urlparse, unquote
        parsed = urlparse(url)
        path_parts = [part for part in parsed.path.split('/') if part and not part.isdigit()]

        if path_parts:
            # Last part of path
            last_part = unquote(path_parts[-1]).replace('-', ' ').replace('_', ' ')
            queries.append(last_part[:80])

            # Multiple parts
            if len(path_parts) > 1:
                combined = ' '.join(unquote(part).replace('-', ' ') for part in path_parts[-2:])
                queries.append(combined[:80])

        # Domain-based fallback
        domain = parsed.netloc.replace('www.', '').replace('.com', '').replace('.org', '')
        queries.append(f"article {domain}")

        return queries[:5]  # Limit to 5 variations

    def _extract_search_query(self, url: str, title: str) -> str:
        """Extract best search query from URL and title"""
        variations = self._generate_search_variations(url, title)
        return variations[0] if variations else f"article {url}"

    def _calculate_next_retry(self, retry_count: int) -> str:
        """Calculate next retry time with exponential backoff"""
        backoff_seconds = min(
            self.base_backoff_seconds * (2 ** retry_count),
            self.max_backoff_seconds
        )

        next_retry = datetime.now() + timedelta(seconds=backoff_seconds)
        return next_retry.isoformat()

    def _mark_in_progress(self, failure_id: int):
        """Mark failure as being retried"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE nuclear_failures
                SET retry_status = 'in_progress',
                    retry_count = retry_count + 1,
                    last_retry_at = datetime('now')
                WHERE id = ?
            """, (failure_id,))

    def _mark_success(self, failure_id: int, success_url: str = None):
        """Mark failure as successfully resolved"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE nuclear_failures
                SET retry_status = 'success',
                    success_url = ?,
                    last_retry_at = datetime('now')
                WHERE id = ?
            """, (success_url, failure_id))

    def _mark_human_intervention_required(self, failure_id: int, reason: str):
        """Mark failure as requiring human intervention"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE nuclear_failures
                SET retry_status = 'human_intervention_required',
                    human_notes = ?,
                    last_retry_at = datetime('now')
                WHERE id = ?
            """, (reason, failure_id))

    def _schedule_next_retry(self, failure_id: int, next_retry_time: str, error: str = None):
        """Schedule the next retry attempt"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE nuclear_failures
                SET retry_status = 'pending',
                    next_retry_at = ?,
                    error_message = COALESCE(?, error_message),
                    last_retry_at = datetime('now')
                WHERE id = ?
            """, (next_retry_time, error, failure_id))

    def _mark_retry_failed(self, failure_id: int, error: str):
        """Mark a retry attempt as failed"""
        next_retry = self._calculate_next_retry(1)  # Schedule retry
        self._schedule_next_retry(failure_id, next_retry, error)

    def get_nuclear_stats(self) -> Dict:
        """Get comprehensive nuclear fallback statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT
                    retry_status,
                    COUNT(*) as count,
                    AVG(retry_count) as avg_retries
                FROM nuclear_failures
                GROUP BY retry_status
            """)

            status_stats = {row[0]: {"count": row[1], "avg_retries": row[2]}
                          for row in cursor.fetchall()}

            cursor = conn.execute("""
                SELECT COUNT(*) FROM nuclear_failures
                WHERE retry_status = 'human_intervention_required'
            """)

            human_intervention_needed = cursor.fetchone()[0]

            cursor = conn.execute("""
                SELECT COUNT(*) FROM nuclear_failures
                WHERE retry_status = 'success'
            """)

            total_recoveries = cursor.fetchone()[0]

            return {
                "status_breakdown": status_stats,
                "human_intervention_needed": human_intervention_needed,
                "total_recoveries": total_recoveries,
                "last_updated": datetime.now().isoformat()
            }

async def run_nuclear_fallback():
    """Main nuclear fallback runner"""
    logger.info("💥 NUCLEAR FALLBACK SYSTEM - STARTING")

    nuclear = NuclearFallbackSystem()

    try:
        stats = await nuclear.process_nuclear_retries()

        logger.info("💥 Nuclear Fallback Complete:")
        logger.info(f"   - Processed: {stats['processed']}")
        logger.info(f"   - Successful: {stats['successful']}")
        logger.info(f"   - Failed: {stats['failed']}")
        logger.info(f"   - Human intervention required: {stats['human_required']}")

        return stats

    except Exception as e:
        logger.error(f"💥 Nuclear Fallback System Error: {e}")
        raise

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    asyncio.run(run_nuclear_fallback())