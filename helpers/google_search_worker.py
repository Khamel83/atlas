#!/usr/bin/env python3
"""
Google Search Background Worker

Processes Google Search requests from the queue at a controlled rate
to respect API quotas and rate limits.
"""

import asyncio
import logging
import os
import signal
import sys
import time
from datetime import datetime, timedelta
from typing import Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from helpers.google_search_queue import GoogleSearchQueue, QueuePriority, QueueStatus
from helpers.google_search_fallback import GoogleSearchFallback

logger = logging.getLogger(__name__)

class GoogleSearchWorker:
    """Background worker for processing Google Search queue"""

    def __init__(self):
        self.queue = GoogleSearchQueue()
        self.fallback = GoogleSearchFallback()
        self.running = False
        self.searches_per_hour = 333  # 8000 daily / 24 hours = 333 per hour
        self.current_hour_searches = 0
        self.current_hour = None

    async def start(self):
        """Start the background worker"""
        if self.running:
            logger.warning("Worker is already running")
            return

        self.running = True
        logger.info("🚀 Starting Google Search background worker")
        logger.info(f"⏱️  Hourly burst: {self.searches_per_hour} searches per hour")
        logger.info(f"📊 Daily quota: {self.queue.daily_quota} searches")

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        try:
            await self._main_loop()
        except Exception as e:
            logger.error(f"Worker crashed: {e}")
            raise
        finally:
            self.running = False
            logger.info("🛑 Google Search worker stopped")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False

    async def _main_loop(self):
        """Main worker loop"""
        consecutive_idle_cycles = 0
        max_idle_cycles = 60  # Sleep longer after 1 hour of inactivity

        while self.running:
            try:
                # Check daily quota
                daily_used = self.queue._get_daily_usage()
                if daily_used >= self.queue.daily_quota:
                    logger.warning(f"Daily quota exhausted: {daily_used}/{self.queue.daily_quota}")
                    await self._sleep_until_quota_reset()
                    continue

                # Check hourly quota - reset if new hour
                current_hour = datetime.now().hour
                if self.current_hour != current_hour:
                    logger.info(f"🕐 New hour started: {current_hour}:00 - Resetting hourly counter")
                    self.current_hour = current_hour
                    self.current_hour_searches = 0

                # Check if we've hit hourly limit
                if self.current_hour_searches >= self.searches_per_hour:
                    minutes_until_next_hour = 60 - datetime.now().minute
                    logger.info(f"⏰ Hourly quota reached ({self.current_hour_searches}/{self.searches_per_hour}). Waiting {minutes_until_next_hour} minutes until next hour.")
                    await asyncio.sleep(minutes_until_next_hour * 60)
                    continue

                # Get next search request
                search = self.queue.get_next_search()

                if not search:
                    consecutive_idle_cycles += 1
                    if consecutive_idle_cycles > max_idle_cycles:
                        # Sleep longer when idle for extended periods
                        logger.debug("No searches in queue, extending sleep...")
                        await asyncio.sleep(60)  # 1 minute
                        consecutive_idle_cycles = 0
                    else:
                        await asyncio.sleep(10)  # 10 seconds
                    continue

                consecutive_idle_cycles = 0

                # Process the search immediately (no per-second rate limiting)
                await self._process_search(search)

                # Increment hourly counter
                self.current_hour_searches += 1

                # Brief pause between searches to avoid overwhelming the API
                await asyncio.sleep(0.5)  # Just 0.5 seconds between searches

            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(30)  # Wait 30 seconds before retrying

    def _get_hourly_stats(self):
        """Get current hourly processing statistics"""
        return {
            "current_hour": self.current_hour,
            "searches_this_hour": self.current_hour_searches,
            "hourly_limit": self.searches_per_hour,
            "remaining_this_hour": max(0, self.searches_per_hour - self.current_hour_searches)
        }

    async def _process_search(self, search):
        """Process a single search request"""
        logger.info(f"🔍 Processing search: '{search.query}' (Priority: {search.priority}, Attempt: {search.attempts + 1})")

        try:
            # Use the fallback system to perform the search
            result_url = await self._perform_google_search(search.query)

            if result_url:
                self.queue.mark_completed(search.id, result_url)
                logger.info(f"✅ Search successful: {result_url}")
            else:
                # No results found, but not an error
                self.queue.mark_failed(search.id, "No search results found", increment_attempts=True)
                logger.info(f"❌ No results found for: {search.query}")

        except Exception as e:
            error_msg = str(e)

            # Handle rate limiting
            if "429" in error_msg or "rate limit" in error_msg.lower():
                self.queue.mark_rate_limited(search.id)
                logger.warning(f"⏱️  Rate limited, will retry: {search.query}")
                # Add extra delay for rate limiting
                await asyncio.sleep(60)
            else:
                self.queue.mark_failed(search.id, error_msg, increment_attempts=True)
                logger.error(f"❌ Search failed: {search.query} - {error_msg}")

    async def _perform_google_search(self, query: str) -> Optional[str]:
        """Perform the actual Google search using the fallback system"""
        try:
            # Create a high-priority search request
            result = await self.fallback.search_with_fallback(query, priority=1)
            return result

        except Exception as e:
            logger.error(f"Google search API error: {e}")
            raise

    async def _sleep_until_quota_reset(self):
        """Sleep until daily quota resets (midnight UTC)"""
        now = datetime.utcnow()
        tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        sleep_seconds = (tomorrow - now).total_seconds()

        logger.info(f"💤 Sleeping {sleep_seconds/3600:.1f} hours until quota reset")

        # Sleep in chunks to allow for graceful shutdown
        while sleep_seconds > 0 and self.running:
            chunk_sleep = min(300, sleep_seconds)  # 5-minute chunks
            await asyncio.sleep(chunk_sleep)
            sleep_seconds -= chunk_sleep

    def get_stats(self) -> dict:
        """Get worker and queue statistics"""
        queue_status = self.queue.get_queue_status()
        hourly_stats = self._get_hourly_stats()

        return {
            "worker_running": self.running,
            "hourly_burst_mode": True,
            "searches_per_hour": self.searches_per_hour,
            "hourly_stats": hourly_stats,
            "queue_status": queue_status,
            "fallback_stats": self.fallback.get_stats() if hasattr(self.fallback, 'get_stats') else {}
        }

async def main():
    """Main entry point for the background worker"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/google_search_worker.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Ensure logs directory exists
    os.makedirs('logs', exist_ok=True)

    worker = GoogleSearchWorker()

    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Worker failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())