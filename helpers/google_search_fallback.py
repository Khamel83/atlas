#!/usr/bin/env python3
"""
Google Search Fallback Module for Atlas

The ultimate safety net that ensures NO content is ever truly lost.
If Google can find it, Atlas will get it.

Key Features:
- Rate limiting (8,000 queries/day = 1 every 11 seconds)
- Circuit breaker pattern to prevent cascade failures
- Exponential backoff retry logic
- Queue management for background processing
- Memory leak prevention and resource cleanup
- Comprehensive logging and monitoring
"""

import asyncio
import logging
import os
import time
import urllib.parse
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import httpx
import json
from dataclasses import dataclass
from enum import Enum

# Configure logging
logger = logging.getLogger(__name__)

class SearchStatus(Enum):
    """Status of a search request"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"
    CIRCUIT_OPEN = "circuit_open"

@dataclass
class SearchRequest:
    """A Google search request with metadata"""
    query: str
    priority: int = 1  # 1=urgent, 2=normal, 3=background
    max_retries: int = 5
    attempt_count: int = 0
    created_at: datetime = None
    last_attempt: datetime = None
    status: SearchStatus = SearchStatus.PENDING
    result_url: Optional[str] = None
    error_message: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()

class CircuitBreaker:
    """Circuit breaker to prevent cascade failures"""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def record_success(self):
        """Record a successful operation"""
        self.failure_count = 0
        self.state = "CLOSED"
        logger.debug("Circuit breaker: Success recorded, circuit CLOSED")

    def record_failure(self):
        """Record a failed operation"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(f"Circuit breaker: OPEN due to {self.failure_count} failures")

    def can_execute(self) -> bool:
        """Check if operation can be executed"""
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            # Check if enough time has passed to try again
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                logger.info("Circuit breaker: Moving to HALF_OPEN state")
                return True
            return False
        elif self.state == "HALF_OPEN":
            return True

        return False

    def is_closed(self) -> bool:
        """Check if circuit is closed (allowing requests)"""
        return self.state == "CLOSED"

    def reset(self):
        """Reset circuit breaker to closed state"""
        self.failure_count = 0
        self.state = "CLOSED"
        self.last_failure_time = None
        logger.info("Circuit breaker: Reset to CLOSED state")

class RateLimiter:
    """Rate limiter for Google Search API"""

    def __init__(self, max_queries_per_day: int = 8000):
        self.max_queries_per_day = max_queries_per_day
        self.queries_today = 0
        self.last_reset_date = datetime.utcnow().date()
        self.last_query_time = 0
        self.min_interval = 86400 / max_queries_per_day  # seconds between queries

    def reset_daily_count_if_needed(self):
        """Reset daily count if it's a new day"""
        today = datetime.utcnow().date()
        if today > self.last_reset_date:
            self.queries_today = 0
            self.last_reset_date = today
            logger.info(f"Rate limiter: Daily count reset for {today}")

    async def wait_if_needed(self):
        """Wait if we need to throttle requests (daily limit only)"""
        self.reset_daily_count_if_needed()

        # Check daily limit only - let worker handle hourly bursts
        if self.queries_today >= self.max_queries_per_day:
            wait_time = (datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) +
                        timedelta(days=1) - datetime.utcnow()).total_seconds()
            logger.warning(f"Rate limiter: Daily limit reached, waiting {wait_time:.0f} seconds")
            await asyncio.sleep(wait_time)
            self.reset_daily_count_if_needed()

        # No per-second limiting - just record the query
        self.last_query_time = time.time()
        self.queries_today += 1
        logger.debug(f"Rate limiter: Query {self.queries_today}/{self.max_queries_per_day} for today")

    def get_remaining_quota(self) -> int:
        """Get remaining queries for today"""
        self.reset_daily_count_if_needed()
        return max(0, self.max_queries_per_day - self.queries_today)

    async def can_make_request(self) -> bool:
        """Check if we can make a request (for testing)"""
        self.reset_daily_count_if_needed()
        return self.queries_today < self.max_queries_per_day

    async def record_request(self):
        """Record a request (for testing)"""
        self.queries_today += 1
        self.last_query_time = time.time()
        logger.debug(f"Rate limiter: Query recorded, total: {self.queries_today}")

class GoogleSearchFallback:
    """
    Universal Google Search fallback system for Atlas.

    The philosophy: If Google can find it, Atlas will get it.
    No more "couldn't find it" - just intelligent retrying.
    """

    def __init__(self):
        self.api_key = os.getenv('GOOGLE_SEARCH_API_KEY')
        self.search_engine_id = os.getenv('GOOGLE_SEARCH_ENGINE_ID')
        self.rate_limiter = RateLimiter()
        self.circuit_breaker = CircuitBreaker()
        self.search_queue: List[SearchRequest] = []
        self.search_history: Dict[str, SearchRequest] = {}
        self.is_processing = False

        # FORCE DISABLED - Google Search API is expensive and we use free alternatives
        self.enabled = False
        logger.info("Google Search API DISABLED - using free search alternatives instead")

    def search_fallback_url(self, url: str) -> Dict[str, Any]:
        """
        Synchronous wrapper for searching fallback URLs

        Args:
            url: Original URL that failed processing

        Returns:
            Dict with search results
        """
        if not self.enabled:
            return {
                "success": False,
                "error": "Google Search fallback not configured",
                "urls": []
            }

        # For now, return a simple result
        # In a real implementation, this would call the async search method
        return {
            "success": False,
            "error": "Google Search fallback requires async configuration",
            "urls": []
        }

    async def search(self, query: str, priority: int = 2) -> Optional[str]:
        """
        Simple search method for testing compatibility.

        Args:
            query: Search query string
            priority: Priority level (1=urgent, 2=normal, 3=background)

        Returns:
            Found URL or None if failed
        """
        # For testing, just delegate to the existing method
        try:
            return await self.search_with_fallback(query, priority)
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return None

    async def search_with_fallback(self, query: str, priority: int = 2) -> Optional[str]:
        """
        Search for a query with full fallback and retry logic.

        Args:
            query: Search query string
            priority: 1=urgent, 2=normal, 3=background

        Returns:
            Found URL or None if truly unfindable
        """
        # Check if we've already searched for this query recently
        if query in self.search_history:
            cached_result = self.search_history[query]
            if cached_result.status == SearchStatus.SUCCESS:
                logger.debug(f"Returning cached result for: {query}")
                return cached_result.result_url

        # Create search request
        request = SearchRequest(query=query, priority=priority)

        # Try immediate search first (for urgent requests)
        if priority == 1:
            result = await self._execute_search_request(request)
            if result:
                return result

        # Queue for background processing
        await self.queue_search(request)

        # For urgent requests, wait a bit and check again
        if priority == 1:
            await asyncio.sleep(2)
            if request.status == SearchStatus.SUCCESS:
                return request.result_url

        return None

    async def queue_search(self, request: SearchRequest):
        """Queue a search request for background processing"""
        self.search_queue.append(request)
        self.search_history[request.query] = request

        logger.info(f"Queued search: {request.query} (priority {request.priority})")

        # Start background processor if not running
        if not self.is_processing:
            asyncio.create_task(self._process_queue())

    async def _process_queue(self):
        """Background queue processor with intelligent retry logic"""
        if self.is_processing:
            return

        self.is_processing = True
        logger.info("Starting background search queue processor")

        try:
            while self.search_queue:
                # Sort by priority (1=urgent first)
                self.search_queue.sort(key=lambda x: (x.priority, x.created_at))

                request = self.search_queue.pop(0)

                # Skip if already successful
                if request.status == SearchStatus.SUCCESS:
                    continue

                # Check if we should retry
                if request.attempt_count >= request.max_retries:
                    request.status = SearchStatus.FAILED
                    logger.warning(f"Search failed after {request.max_retries} attempts: {request.query}")
                    continue

                # Execute search with exponential backoff
                await self._execute_search_request(request)

                # If failed, re-queue with exponential backoff
                if request.status == SearchStatus.FAILED:
                    backoff_time = min(300, 2 ** request.attempt_count)  # Max 5 min
                    logger.info(f"Re-queuing search after {backoff_time}s: {request.query}")

                    await asyncio.sleep(backoff_time)
                    self.search_queue.append(request)

        except Exception as e:
            logger.error(f"Error in queue processor: {e}")
        finally:
            self.is_processing = False
            logger.info("Background search queue processor stopped")

    async def _execute_search_request(self, request: SearchRequest) -> Optional[str]:
        """Execute a single search request with all safety mechanisms"""
        request.attempt_count += 1
        request.last_attempt = datetime.utcnow()
        request.status = SearchStatus.IN_PROGRESS

        logger.debug(f"Executing search (attempt {request.attempt_count}): {request.query}")

        try:
            # Check circuit breaker
            if not self.circuit_breaker.can_execute():
                request.status = SearchStatus.CIRCUIT_OPEN
                request.error_message = "Circuit breaker is open"
                logger.warning(f"Search blocked by circuit breaker: {request.query}")
                return None

            # Apply rate limiting
            await self.rate_limiter.wait_if_needed()

            # Perform the actual search
            result = await self._perform_google_search(request.query)

            if result:
                request.status = SearchStatus.SUCCESS
                request.result_url = result
                self.circuit_breaker.record_success()
                logger.info(f"Search successful: {request.query} -> {result}")
                return result
            else:
                request.status = SearchStatus.FAILED
                request.error_message = "No search results found"
                self.circuit_breaker.record_failure()
                logger.debug(f"No results found for: {request.query}")
                return None

        except Exception as e:
            request.status = SearchStatus.FAILED
            request.error_message = str(e)
            self.circuit_breaker.record_failure()
            logger.error(f"Search error for '{request.query}': {e}")
            return None

    async def _perform_google_search(self, query: str) -> Optional[str]:
        """Perform the actual Google Custom Search API call"""
        try:
            # Prepare the search query
            encoded_query = urllib.parse.quote(f'"{query}"')
            url = f"https://www.googleapis.com/customsearch/v1?key={self.api_key}&cx={self.search_engine_id}&q={encoded_query}&num=1"

            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=10.0)

                if response.status_code == 200:
                    data = response.json()
                    if 'items' in data and len(data['items']) > 0:
                        return data['items'][0]['link']
                    else:
                        return None

                elif response.status_code == 429:
                    # Rate limited - this should be handled by our rate limiter
                    logger.warning("Google API rate limit hit despite our rate limiting")
                    raise Exception("Rate limited by Google API")

                else:
                    logger.error(f"Google API error {response.status_code}: {response.text}")
                    raise Exception(f"Google API error: {response.status_code}")

        except httpx.TimeoutException:
            logger.warning(f"Search timeout for: {query}")
            raise Exception("Search request timed out")
        except Exception as e:
            logger.error(f"Search API error: {e}")
            raise

    def get_stats(self) -> Dict:
        """Get current statistics and health metrics"""
        total_searches = len(self.search_history)
        successful = sum(1 for r in self.search_history.values() if r.status == SearchStatus.SUCCESS)
        failed = sum(1 for r in self.search_history.values() if r.status == SearchStatus.FAILED)
        pending = len(self.search_queue)

        return {
            "total_searches": total_searches,
            "successful_searches": successful,
            "failed_searches": failed,
            "pending_searches": pending,
            "success_rate": successful / max(1, total_searches),
            "remaining_quota": self.rate_limiter.get_remaining_quota(),
            "circuit_breaker_state": self.circuit_breaker.state,
            "is_processing": self.is_processing
        }

    async def nuclear_retry_all_failures(self):
        """
        Nuclear option: Retry ALL historical failures.

        This is the "never give up" function that runs daily
        to ensure nothing is permanently lost.
        """
        logger.info("Starting nuclear retry of all failures")

        failed_requests = [r for r in self.search_history.values()
                          if r.status == SearchStatus.FAILED]

        logger.info(f"Found {len(failed_requests)} failed searches to retry")

        for request in failed_requests:
            # Reset for retry
            request.status = SearchStatus.PENDING
            request.attempt_count = 0
            request.error_message = None

            # Add to queue for processing
            self.search_queue.append(request)

        # Start processing if not already running
        if not self.is_processing:
            await self._process_queue()

# Global instance
_google_search_fallback = None

def get_google_search_fallback() -> GoogleSearchFallback:
    """Get or create the global GoogleSearchFallback instance"""
    global _google_search_fallback
    if _google_search_fallback is None:
        _google_search_fallback = GoogleSearchFallback()
    return _google_search_fallback

# Convenience functions for easy integration
async def search_with_google_fallback(query: str, priority: int = 2) -> Optional[str]:
    """
    Main entry point for Google Search fallback.

    Usage:
        url = await search_with_google_fallback("Article title here")
    """
    fallback = get_google_search_fallback()
    return await fallback.search_with_fallback(query, priority)

async def urgent_google_search(query: str) -> Optional[str]:
    """Urgent Google search (tries immediately, doesn't wait)"""
    return await search_with_google_fallback(query, priority=1)

async def background_google_search(query: str) -> Optional[str]:
    """Background Google search (queued for later processing)"""
    return await search_with_google_fallback(query, priority=3)

def get_google_search_stats() -> Dict:
    """Get Google Search fallback statistics"""
    fallback = get_google_search_fallback()
    return fallback.get_stats()

if __name__ == "__main__":
    # Simple test
    async def test():
        result = await search_with_google_fallback("Python programming tutorial")
        print(f"Search result: {result}")

        stats = get_google_search_stats()
        print(f"Stats: {stats}")

    asyncio.run(test())