#!/usr/bin/env python3
"""
Strategy Progression Engine for Atlas Ingestion

Implements intelligent workflow branching with multiple fallback strategies.
Handles URL processing with progressive strategy attempts and Google search fallback.
"""

import json
import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import uuid

# Add parent directory to path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.google_search_fallback import GoogleSearchFallback
from helpers.article_strategies import ArticleFetcher

logger = logging.getLogger(__name__)

class ProcessingStatus(Enum):
    """Processing status states for workflow tracking."""
    PENDING = "pending"
    STRATEGY_1_ATTEMPTING = "strategy_1_attempting"
    STRATEGY_1_FAILED = "strategy_1_failed"
    STRATEGY_2_ATTEMPTING = "strategy_2_attempting"
    STRATEGY_2_FAILED = "strategy_2_failed"
    STRATEGY_3_ATTEMPTING = "strategy_3_attempting"
    STRATEGY_3_FAILED = "strategy_3_failed"
    GOOGLE_SEARCH_ATTEMPTING = "google_search_attempting"
    GOOGLE_SEARCH_FOUND = "google_search_found"
    GOOGLE_SEARCH_FAILED = "google_search_failed"
    FINAL_FAILURE = "final_failure"
    INGESTED = "ingested"

class StrategyType(Enum):
    """Available processing strategies."""
    DIRECT_HTTP = "direct_http"
    PLAYWRIGHT = "playwright"
    READER_MODE = "reader_mode"
    ARCHIVE_ORG = "archive_org"
    GOOGLE_SEARCH = "google_search"

class StrategyProgressionEngine:
    """
    Intelligent strategy progression engine for URL processing.

    Implements branching workflow with multiple fallback strategies.
    """

    def __init__(self, db_path: str = "data/atlas.db"):
        self.db_path = db_path
        self.google_search = GoogleSearchFallback()
        self.article_fetcher = ArticleFetcher()

        # Define strategy order for URL processing
        self.url_strategy_order = [
            StrategyType.DIRECT_HTTP,
            StrategyType.PLAYWRIGHT,
            StrategyType.READER_MODE,
            StrategyType.ARCHIVE_ORG,
            StrategyType.GOOGLE_SEARCH
        ]

        # Strategy success thresholds
        self.min_content_length = 500  # Minimum words for successful ingestion
        self.max_retry_attempts = 3

    def update_job_strategy_state(self, job_id: str, strategy: StrategyType,
                                status: ProcessingStatus, error_message: str = None,
                                actual_url: str = None, content_source: str = None) -> bool:
        """Update job strategy tracking information."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get current job data
                cursor = conn.execute("""
                    SELECT attempted_strategies, strategy_history, source_url
                    FROM worker_jobs WHERE id = ?
                """, (job_id,))
                result = cursor.fetchone()

                if not result:
                    logger.error(f"Job {job_id} not found")
                    return False

                attempted_strategies = json.loads(result[0])
                strategy_history = json.loads(result[1])
                source_url = result[2]

                # Update attempted strategies if not already attempted
                if strategy.value not in attempted_strategies:
                    attempted_strategies.append(strategy.value)

                # Add to strategy history
                history_entry = {
                    "strategy": strategy.value,
                    "status": status.value,
                    "timestamp": datetime.now().isoformat(),
                    "error_message": error_message
                }
                if actual_url:
                    history_entry["actual_url"] = actual_url
                if content_source:
                    history_entry["content_source"] = content_source

                strategy_history.append(history_entry)

                # Update job record
                conn.execute("""
                    UPDATE worker_jobs SET
                        attempted_strategies = ?,
                        current_strategy = ?,
                        strategy_history = ?,
                        status = ?,
                        actual_url = COALESCE(?, actual_url),
                        content_source = COALESCE(?, content_source)
                    WHERE id = ?
                """, (
                    json.dumps(attempted_strategies),
                    strategy.value if status in [
                        ProcessingStatus.STRATEGY_1_ATTEMPTING,
                        ProcessingStatus.STRATEGY_2_ATTEMPTING,
                        ProcessingStatus.STRATEGY_3_ATTEMPTING,
                        ProcessingStatus.GOOGLE_SEARCH_ATTEMPTING
                    ] else None,
                    json.dumps(strategy_history),
                    status.value,
                    actual_url,
                    content_source,
                    job_id
                ))

                conn.commit()
                return True

        except Exception as e:
            logger.error(f"Failed to update job {job_id} strategy state: {e}")
            return False

    def get_next_strategy(self, job_id: str) -> Optional[StrategyType]:
        """Determine the next strategy to attempt for a job."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT attempted_strategies FROM worker_jobs WHERE id = ?
                """, (job_id,))
                result = cursor.fetchone()

                if not result:
                    return None

                attempted_strategies = json.loads(result[0])

                # Find next unattempted strategy
                for strategy in self.url_strategy_order:
                    if strategy.value not in attempted_strategies:
                        return strategy

                return None  # All strategies attempted

        except Exception as e:
            logger.error(f"Failed to get next strategy for job {job_id}: {e}")
            return None

    def process_job_with_strategy(self, job_id: str, strategy: StrategyType) -> Dict[str, Any]:
        """Process a job using the article fetcher (which handles all strategies internally)."""
        try:
            # Get job details
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT data, source_url FROM worker_jobs WHERE id = ?
                """, (job_id,))
                result = cursor.fetchone()

                if not result:
                    return {"success": False, "error": "Job not found"}

                job_data = json.loads(result[0])
                url = job_data.get("url") or result[1]

            # Use article fetcher with built-in fallback strategies and Google search
            strategy_result = self.article_fetcher.fetch_with_fallbacks(url, f"workflow_{job_id}")

            if strategy_result.success:
                # Check if content meets quality thresholds
                content = strategy_result.content or ""
                word_count = len(content.split()) if content else 0

                if word_count >= self.min_content_length and not strategy_result.is_truncated:
                    # Determine actual URL and content source
                    actual_url = url
                    content_source = "direct_processing"

                    # Extract actual URL and source from metadata
                    if strategy_result.metadata:
                        if strategy_result.metadata.get('final_url'):
                            actual_url = strategy_result.metadata['final_url']
                        if strategy_result.metadata.get('google_search_fallback'):
                            content_source = "google_search"
                            actual_url = strategy_result.metadata.get('alternative_url', actual_url)

                    # Mark as successfully ingested
                    self.update_job_strategy_state(
                        job_id, StrategyType.DIRECT_HTTP, ProcessingStatus.INGESTED,
                        actual_url=actual_url,
                        content_source=content_source
                    )

                    return {
                        "success": True,
                        "content": content,
                        "word_count": word_count,
                        "actual_url": actual_url,
                        "title": strategy_result.title,
                        "strategy_used": strategy_result.method
                    }
                else:
                    error_msg = f"Content too short ({word_count} words) or truncated"
                    self.update_job_strategy_state(
                        job_id, StrategyType.DIRECT_HTTP, getattr(ProcessingStatus, f"STRATEGY_1_FAILED"),
                        error_message=error_msg
                    )
                    return {"success": False, "error": error_msg}
            else:
                # All strategies failed, try Google search as final fallback
                logger.info(f"All fetch strategies failed for {url}, trying Google search fallback")
                search_result = self.google_search.search_fallback_url(url)

                if search_result["success"] and search_result["urls"]:
                    alternative_url = search_result["urls"][0]

                    # Update job with Google search result
                    self.update_job_strategy_state(
                        job_id, StrategyType.GOOGLE_SEARCH, ProcessingStatus.GOOGLE_SEARCH_FOUND,
                        actual_url=alternative_url, content_source="google_search"
                    )

                    # Submit new job for the found URL
                    self.submit_alternative_url_job(alternative_url, original_job_id=job_id)

                    return {
                        "success": True,
                        "message": "Google search found alternative URL",
                        "alternative_url": alternative_url
                    }
                else:
                    # Complete failure
                    self.update_job_strategy_state(
                        job_id, StrategyType.GOOGLE_SEARCH, ProcessingStatus.FINAL_FAILURE,
                        error_message="All fetch strategies and Google search failed"
                    )
                    return {"success": False, "error": "All strategies exhausted"}

        except Exception as e:
            error_msg = f"Strategy processing error: {str(e)}"
            self.update_job_strategy_state(
                job_id, StrategyType.DIRECT_HTTP, getattr(ProcessingStatus, f"STRATEGY_1_FAILED"),
                error_message=error_msg
            )
            return {"success": False, "error": error_msg}

    def submit_alternative_url_job(self, url: str, original_job_id: str) -> str:
        """Submit a new job for an alternative URL found through Google search."""
        try:
            job_id = str(uuid.uuid4())

            # Get original job data
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT data FROM worker_jobs WHERE id = ?
                """, (original_job_id,))
                result = cursor.fetchone()

                original_data = json.loads(result[0]) if result else {}

            # Create new job data
            job_data = {
                "url": url,
                "source": "google_search_fallback",
                "original_job_id": original_job_id,
                "original_url": original_data.get("url"),
                "search_timestamp": datetime.now().isoformat()
            }

            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO worker_jobs (
                        id, type, data, priority, status, created_at,
                        source_url, actual_url, content_source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job_id,
                    "url_processing",
                    json.dumps(job_data),
                    70,  # Higher priority for Google search results
                    "pending",
                    datetime.now().isoformat(),
                    original_data.get("url"),  # Original URL as source
                    url,  # This URL as actual
                    "google_search"
                ))
                conn.commit()

            return job_id

        except Exception as e:
            logger.error(f"Failed to submit alternative URL job: {e}")
            return None

    def process_job_with_workflow(self, job_id: str) -> Dict[str, Any]:
        """Process a job through the complete workflow progression."""
        try:
            while True:
                # Get next strategy to attempt
                next_strategy = self.get_next_strategy(job_id)

                if not next_strategy:
                    # All strategies attempted, mark as final failure
                    self.update_job_strategy_state(
                        job_id, StrategyType.GOOGLE_SEARCH, ProcessingStatus.FINAL_FAILURE,
                        error_message="All strategies exhausted"
                    )
                    return {"success": False, "error": "All strategies exhausted"}

                # Update job status to attempting this strategy
                strategy_index = self.url_strategy_order.index(next_strategy)
                if next_strategy == StrategyType.GOOGLE_SEARCH:
                    status = ProcessingStatus.GOOGLE_SEARCH_ATTEMPTING
                elif strategy_index < 3:
                    status = getattr(ProcessingStatus, f"STRATEGY_{strategy_index + 1}_ATTEMPTING")
                else:
                    # For strategies beyond 3, use strategy_3_attempting as fallback
                    status = ProcessingStatus.STRATEGY_3_ATTEMPTING

                self.update_job_strategy_state(job_id, next_strategy, status)

                # Attempt processing with this strategy
                result = self.process_job_with_strategy(job_id, next_strategy)

                if result["success"]:
                    # Strategy succeeded
                    if next_strategy == StrategyType.GOOGLE_SEARCH:
                        # Google search found alternative URLs but doesn't complete the job
                        return {
                            "success": True,
                            "message": "Google search found alternative URLs",
                            "alternative_jobs_created": True
                        }
                    else:
                        # Direct processing succeeded
                        return result
                else:
                    # Strategy failed, continue to next strategy
                    logger.info(f"Strategy {next_strategy.value} failed for job {job_id}: {result['error']}")
                    continue

        except Exception as e:
            logger.error(f"Workflow processing error for job {job_id}: {e}")
            return {"success": False, "error": f"Workflow error: {str(e)}"}

    def get_job_workflow_summary(self, job_id: str) -> Dict[str, Any]:
        """Get a summary of a job's workflow progression."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT status, attempted_strategies, strategy_history,
                           source_url, actual_url, content_source
                    FROM worker_jobs WHERE id = ?
                """, (job_id,))
                result = cursor.fetchone()

                if not result:
                    return {"error": "Job not found"}

                return {
                    "job_id": job_id,
                    "status": result[0],
                    "attempted_strategies": json.loads(result[1]),
                    "strategy_history": json.loads(result[2]),
                    "source_url": result[3],
                    "actual_url": result[4],
                    "content_source": result[5]
                }

        except Exception as e:
            logger.error(f"Failed to get workflow summary for job {job_id}: {e}")
            return {"error": str(e)}

if __name__ == "__main__":
    # Test the engine
    engine = StrategyProgressionEngine()

    # Example usage
    test_job_id = "test-job-123"
    print("Strategy Progression Engine initialized successfully")
    print(f"Available strategies: {[s.value for s in engine.url_strategy_order]}")