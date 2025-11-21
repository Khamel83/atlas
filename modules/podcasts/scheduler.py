#!/usr/bin/env python3
"""
Scheduler for continuous podcast transcript discovery.
Handles watch mode and periodic discovery runs.
"""

import logging
import threading
from datetime import datetime
from typing import Dict, Any, Callable
import signal
import sys

logger = logging.getLogger(__name__)


class PodcastScheduler:
    """Scheduler for periodic podcast transcript discovery"""

    def __init__(self, discovery_callback: Callable[[Dict[str, Any]], None]):
        self.discovery_callback = discovery_callback
        self.running = False
        self.thread = None
        self.stop_event = threading.Event()

        # Set up signal handling for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def start_watch(self, interval_minutes: int = 30, podcasts: str = "all"):
        """Start watch mode with specified interval"""
        if self.running:
            logger.warning("Scheduler already running")
            return False

        logger.info(
            f"Starting watch mode: {interval_minutes}min interval, podcasts={podcasts}"
        )

        self.running = True
        self.stop_event.clear()

        # Start discovery thread
        self.thread = threading.Thread(
            target=self._discovery_loop, args=(interval_minutes, podcasts), daemon=True
        )
        self.thread.start()

        return True

    def stop_watch(self):
        """Stop watch mode"""
        if not self.running:
            return

        logger.info("Stopping watch mode...")
        self.running = False
        self.stop_event.set()

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)

        logger.info("Watch mode stopped")

    def _discovery_loop(self, interval_minutes: int, podcasts: str):
        """Main discovery loop"""
        interval_seconds = interval_minutes * 60
        last_run = None

        while self.running and not self.stop_event.is_set():
            try:
                now = datetime.now()

                # Check if it's time for next discovery
                if (
                    last_run is None
                    or (now - last_run).total_seconds() >= interval_seconds
                ):
                    logger.info(f"Starting scheduled discovery run at {now}")

                    # Run discovery
                    discovery_config = {
                        "podcasts": podcasts,
                        "scheduled": True,
                        "timestamp": now.isoformat(),
                    }

                    try:
                        self.discovery_callback(discovery_config)
                        last_run = now
                        logger.info("Scheduled discovery run completed")

                    except Exception as e:
                        logger.error(f"Error in scheduled discovery: {e}")

                # Wait a bit before checking again (but allow for quick shutdown)
                self.stop_event.wait(timeout=60)  # Check every minute

            except Exception as e:
                logger.error(f"Error in discovery loop: {e}")
                # Wait before retrying
                self.stop_event.wait(timeout=300)  # Wait 5 minutes on error

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop_watch()
        sys.exit(0)

    def is_running(self) -> bool:
        """Check if scheduler is running"""
        return self.running and self.thread and self.thread.is_alive()

    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status"""
        return {
            "running": self.running,
            "thread_alive": self.thread.is_alive() if self.thread else False,
            "thread_name": self.thread.name if self.thread else None,
        }


class IntervalParser:
    """Parse interval strings like '30m', '2h', '1d'"""

    @staticmethod
    def parse_interval(interval_str: str) -> int:
        """Parse interval string and return minutes"""
        if not interval_str:
            return 30  # Default 30 minutes

        interval_str = interval_str.lower().strip()

        # Extract number and unit
        import re

        match = re.match(r"^(\d+)([smhd]?)$", interval_str)

        if not match:
            logger.warning(f"Invalid interval format: {interval_str}, using 30m")
            return 30

        number = int(match.group(1))
        unit = match.group(2) or "m"  # Default to minutes

        # Convert to minutes
        multipliers = {
            "s": 1 / 60,  # seconds to minutes
            "m": 1,  # minutes
            "h": 60,  # hours to minutes
            "d": 1440,  # days to minutes
        }

        minutes = int(number * multipliers[unit])

        # Sanity checks
        if minutes < 1:
            logger.warning(f"Interval too short: {interval_str}, using 1m")
            return 1
        elif minutes > 10080:  # 1 week
            logger.warning(f"Interval too long: {interval_str}, using 1d")
            return 1440

        return minutes


class DiscoveryQueue:
    """Queue for managing discovery tasks"""

    def __init__(self, max_concurrent: int = 3):
        self.max_concurrent = max_concurrent
        self.active_tasks = {}
        self.pending_tasks = []
        self.completed_tasks = []
        self.lock = threading.Lock()

    def add_task(self, task_id: str, podcast_config: Dict[str, Any]) -> bool:
        """Add discovery task to queue"""
        with self.lock:
            if task_id in self.active_tasks:
                return False  # Task already running

            if len(self.active_tasks) < self.max_concurrent:
                # Start immediately
                self.active_tasks[task_id] = {
                    "config": podcast_config,
                    "started_at": datetime.now(),
                    "status": "running",
                }
                return True
            else:
                # Add to pending queue
                self.pending_tasks.append(
                    {
                        "task_id": task_id,
                        "config": podcast_config,
                        "queued_at": datetime.now(),
                    }
                )
                return True

    def complete_task(self, task_id: str, result: Dict[str, Any]):
        """Mark task as completed and start next pending task"""
        with self.lock:
            if task_id in self.active_tasks:
                task = self.active_tasks.pop(task_id)
                task["completed_at"] = datetime.now()
                task["result"] = result
                task["status"] = "completed"

                self.completed_tasks.append(task)

                # Start next pending task if any
                if self.pending_tasks:
                    next_task = self.pending_tasks.pop(0)
                    self.active_tasks[next_task["task_id"]] = {
                        "config": next_task["config"],
                        "started_at": datetime.now(),
                        "status": "running",
                    }

    def get_status(self) -> Dict[str, Any]:
        """Get queue status"""
        with self.lock:
            return {
                "active_count": len(self.active_tasks),
                "pending_count": len(self.pending_tasks),
                "completed_count": len(self.completed_tasks),
                "active_tasks": list(self.active_tasks.keys()),
                "max_concurrent": self.max_concurrent,
            }
