#!/usr/bin/env python3
"""
Discovery Scheduler for Atlas

This module schedules and manages automated content discovery tasks
with configurable intervals and priority-based checking.
"""

import time
import threading
from typing import List, Dict, Any, Callable, Optional
from collections import defaultdict
import json
from datetime import datetime, timedelta
import heapq


class DiscoveryScheduler:
    """Automated content discovery scheduling system"""

    def __init__(self):
        """Initialize the discovery scheduler"""
        self.scheduled_tasks = []
        self.task_intervals = {}  # task_id -> interval_seconds
        self.task_priorities = {}  # task_id -> priority (lower = higher priority)
        self.task_last_run = {}  # task_id -> timestamp
        self.task_functions = {}  # task_id -> callable
        self.task_sources = {}  # task_id -> source_info
        self.running = False
        self.scheduler_thread = None
        self.check_interval = 60  # Check for tasks every 60 seconds

        # Quota management
        self.daily_quota = 1000  # Maximum discovery tasks per day
        self.tasks_today = 0
        self.quota_reset_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)

    def add_discovery_task(self, task_id: str, task_function: Callable,
                          interval_hours: float, priority: int = 5,
                          source_info: Dict[str, Any] = None):
        """
        Add a discovery task to the scheduler

        Args:
            task_id (str): Unique identifier for the task
            task_function (Callable): Function to execute for the task
            interval_hours (float): Interval between runs in hours
            priority (int): Task priority (1=highest, 10=lowest)
            source_info (Dict[str, Any]): Information about the source
        """
        interval_seconds = interval_hours * 3600

        self.task_intervals[task_id] = interval_seconds
        self.task_priorities[task_id] = priority
        self.task_functions[task_id] = task_function
        self.task_sources[task_id] = source_info or {}
        self.task_last_run[task_id] = 0  # Never run

        print(f"Added discovery task: {task_id} (interval: {interval_hours}h, priority: {priority})")

    def set_adaptive_scheduling(self, task_id: str, update_patterns: Dict[str, Any]):
        """
        Set adaptive scheduling based on source update patterns

        Args:
            task_id (str): Task identifier
            update_patterns (Dict[str, Any]): Source update patterns
        """
        # Adjust interval based on source update frequency
        if 'update_frequency' in update_patterns:
            frequency = update_patterns['update_frequency']
            if frequency == 'hourly':
                new_interval = 1.0  # 1 hour
            elif frequency == 'daily':
                new_interval = 24.0  # 24 hours
            elif frequency == 'weekly':
                new_interval = 168.0  # 168 hours (1 week)
            else:
                new_interval = 24.0  # Default to daily

            # Update interval
            if task_id in self.task_intervals:
                old_interval = self.task_intervals[task_id] / 3600
                self.task_intervals[task_id] = new_interval * 3600
                print(f"Updated task {task_id} interval from {old_interval}h to {new_interval}h")

    def set_discovery_quota(self, daily_quota: int):
        """
        Set daily discovery quota to prevent overwhelming

        Args:
            daily_quota (int): Maximum discovery tasks per day
        """
        self.daily_quota = daily_quota
        print(f"Set discovery quota to {daily_quota} tasks per day")

    def start_scheduler(self):
        """
        Start the discovery scheduler
        """
        if self.running:
            print("Scheduler is already running")
            return

        self.running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        print("Discovery scheduler started")

    def stop_scheduler(self):
        """
        Stop the discovery scheduler
        """
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        print("Discovery scheduler stopped")

    def get_scheduler_status(self) -> Dict[str, Any]:
        """
        Get scheduler status and statistics

        Returns:
            Dict[str, Any]: Scheduler status information
        """
        return {
            'running': self.running,
            'scheduled_tasks': len(self.task_intervals),
            'tasks_today': self.tasks_today,
            'daily_quota': self.daily_quota,
            'quota_remaining': max(0, self.daily_quota - self.tasks_today),
            'next_quota_reset': self.quota_reset_time.isoformat(),
            'task_details': [
                {
                    'task_id': task_id,
                    'interval_hours': self.task_intervals[task_id] / 3600,
                    'priority': self.task_priorities[task_id],
                    'last_run': datetime.fromtimestamp(self.task_last_run[task_id]).isoformat()
                               if self.task_last_run[task_id] > 0 else 'never',
                    'source': self.task_sources.get(task_id, {})
                }
                for task_id in self.task_intervals
            ]
        }

    def _scheduler_loop(self):
        """
        Main scheduler loop
        """
        while self.running:
            try:
                self._check_quota_reset()
                self._execute_ready_tasks()
                time.sleep(self.check_interval)
            except Exception as e:
                print(f"Scheduler error: {e}")
                time.sleep(self.check_interval)

    def _check_quota_reset(self):
        """
        Check if daily quota should be reset
        """
        now = datetime.now()
        if now >= self.quota_reset_time:
            self.tasks_today = 0
            self.quota_reset_time = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            print("Daily discovery quota reset")

    def _execute_ready_tasks(self):
        """
        Execute tasks that are ready to run
        """
        if self.tasks_today >= self.daily_quota:
            print("Daily quota exceeded, skipping discovery tasks")
            return

        now = time.time()
        ready_tasks = []

        # Find ready tasks
        for task_id in self.task_intervals:
            interval = self.task_intervals[task_id]
            last_run = self.task_last_run[task_id]

            # Check if task is due
            if now - last_run >= interval:
                priority = self.task_priorities[task_id]
                ready_tasks.append((priority, task_id))

        # Sort by priority (lower number = higher priority)
        ready_tasks.sort()

        # Execute ready tasks (respect quota)
        executed_count = 0
        for priority, task_id in ready_tasks:
            if self.tasks_today >= self.daily_quota:
                print(f"Reached daily quota, skipped {len(ready_tasks) - executed_count} tasks")
                break

            try:
                self._execute_task(task_id)
                executed_count += 1
                self.tasks_today += 1
            except Exception as e:
                print(f"Error executing task {task_id}: {e}")

    def _execute_task(self, task_id: str):
        """
        Execute a single discovery task

        Args:
            task_id (str): Task identifier
        """
        if task_id not in self.task_functions:
            print(f"Task {task_id} not found")
            return

        print(f"Executing discovery task: {task_id}")

        try:
            # Execute the task function
            task_function = self.task_functions[task_id]
            result = task_function()

            # Update last run time
            self.task_last_run[task_id] = time.time()

            print(f"Task {task_id} completed successfully")
            return result
        except Exception as e:
            print(f"Task {task_id} failed: {e}")
            raise

    def get_task_queue(self) -> List[Dict[str, Any]]:
        """
        Get the current task queue with next run times

        Returns:
            List[Dict[str, Any]]: Task queue information
        """
        now = time.time()
        queue = []

        for task_id in self.task_intervals:
            interval = self.task_intervals[task_id]
            last_run = self.task_last_run[task_id]
            next_run = last_run + interval
            time_until_run = max(0, next_run - now)

            queue.append({
                'task_id': task_id,
                'priority': self.task_priorities[task_id],
                'last_run': datetime.fromtimestamp(last_run).isoformat() if last_run > 0 else 'never',
                'next_run': datetime.fromtimestamp(next_run).isoformat(),
                'time_until_run_seconds': time_until_run,
                'source': self.task_sources.get(task_id, {})
            })

        # Sort by time until run
        queue.sort(key=lambda x: x['time_until_run_seconds'])
        return queue

    def remove_task(self, task_id: str):
        """
        Remove a task from the scheduler

        Args:
            task_id (str): Task identifier to remove
        """
        if task_id in self.task_intervals:
            del self.task_intervals[task_id]
        if task_id in self.task_priorities:
            del self.task_priorities[task_id]
        if task_id in self.task_last_run:
            del self.task_last_run[task_id]
        if task_id in self.task_functions:
            del self.task_functions[task_id]
        if task_id in self.task_sources:
            del self.task_sources[task_id]

        print(f"Removed task: {task_id}")

    def pause_task(self, task_id: str):
        """
        Pause a task (set its interval to a very large value)

        Args:
            task_id (str): Task identifier to pause
        """
        if task_id in self.task_intervals:
            # Set interval to 1 year (effectively paused)
            self.task_intervals[task_id] = 365 * 24 * 3600
            print(f"Paused task: {task_id}")

    def resume_task(self, task_id: str, interval_hours: float):
        """
        Resume a paused task

        Args:
            task_id (str): Task identifier to resume
            interval_hours (float): New interval in hours
        """
        if task_id in self.task_intervals:
            self.task_intervals[task_id] = interval_hours * 3600
            print(f"Resumed task: {task_id} with interval {interval_hours}h")


class DiscoveryJobQueue:
    """Discovery job queue with retry logic"""

    def __init__(self):
        """Initialize the job queue"""
        self.queue = []  # Priority queue: (priority, timestamp, job_data)
        self.processed_jobs = set()  # Track processed job IDs
        self.failed_jobs = defaultdict(int)  # job_id -> failure_count
        self.max_retries = 3

    def add_job(self, job_data: Dict[str, Any], priority: int = 5):
        """
        Add a job to the queue

        Args:
            job_data (Dict[str, Any]): Job data
            priority (int): Job priority (1=highest, 10=lowest)
        """
        timestamp = time.time()
        job_id = job_data.get('job_id', f"job_{int(timestamp)}")
        job_data['job_id'] = job_id

        # Add to queue
        heapq.heappush(self.queue, (priority, timestamp, job_data))
        print(f"Added job to queue: {job_id} (priority: {priority})")

    def get_next_job(self) -> Optional[Dict[str, Any]]:
        """
        Get the next job from the queue

        Returns:
            Optional[Dict[str, Any]]: Next job data or None if queue is empty
        """
        while self.queue:
            priority, timestamp, job_data = heapq.heappop(self.queue)
            job_id = job_data['job_id']

            # Check if job has failed too many times
            if self.failed_jobs[job_id] >= self.max_retries:
                print(f"Skipping job {job_id} - max retries exceeded")
                continue

            # Check if job was already processed
            if job_id in self.processed_jobs:
                print(f"Skipping duplicate job {job_id}")
                continue

            return job_data

        return None

    def mark_job_complete(self, job_id: str):
        """
        Mark a job as complete

        Args:
            job_id (str): Job identifier
        """
        self.processed_jobs.add(job_id)
        if job_id in self.failed_jobs:
            del self.failed_jobs[job_id]
        print(f"Marked job complete: {job_id}")

    def mark_job_failed(self, job_id: str):
        """
        Mark a job as failed (will be retried)

        Args:
            job_id (str): Job identifier
        """
        self.failed_jobs[job_id] += 1
        print(f"Marked job failed: {job_id} (attempt {self.failed_jobs[job_id]})")

    def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get queue statistics

        Returns:
            Dict[str, Any]: Queue statistics
        """
        return {
            'queue_size': len(self.queue),
            'processed_jobs': len(self.processed_jobs),
            'failed_jobs': dict(self.failed_jobs),
            'max_retries': self.max_retries
        }


def main():
    """Example usage of DiscoveryScheduler"""
    # Create scheduler
    scheduler = DiscoveryScheduler()

    # Create job queue
    job_queue = DiscoveryJobQueue()

    # Sample task functions
    def discover_github_repos():
        print("Discovering GitHub repositories...")
        # Simulate discovery work
        time.sleep(1)
        return {"repos_found": 5, "sources_checked": 10}

    def discover_tech_blogs():
        print("Discovering technical blogs...")
        # Simulate discovery work
        time.sleep(1)
        return {"articles_found": 12, "sources_checked": 8}

    def discover_academic_papers():
        print("Discovering academic papers...")
        # Simulate discovery work
        time.sleep(1)
        return {"papers_found": 3, "sources_checked": 5}

    # Add tasks to scheduler
    scheduler.add_discovery_task(
        "github_discovery",
        discover_github_repos,
        interval_hours=24,  # Daily
        priority=3,
        source_info={"type": "github", "sources": 50}
    )

    scheduler.add_discovery_task(
        "blog_discovery",
        discover_tech_blogs,
        interval_hours=6,  # Every 6 hours
        priority=1,
        source_info={"type": "blogs", "sources": 100}
    )

    scheduler.add_discovery_task(
        "paper_discovery",
        discover_academic_papers,
        interval_hours=168,  # Weekly
        priority=5,
        source_info={"type": "academic", "sources": 20}
    )

    # Set adaptive scheduling for a task
    scheduler.set_adaptive_scheduling(
        "github_discovery",
        {"update_frequency": "daily"}
    )

    # Set discovery quota
    scheduler.set_discovery_quota(100)  # 100 tasks per day

    # Add jobs to queue
    for i in range(5):
        job_queue.add_job({
            "job_type": "content_discovery",
            "source": f"source_{i}",
            "discovery_type": "web_scraping"
        }, priority=i+1)

    # Display scheduler status
    status = scheduler.get_scheduler_status()
    print(f"\nScheduler Status:")
    print(f"  Running: {status['running']}")
    print(f"  Scheduled Tasks: {status['scheduled_tasks']}")
    print(f"  Tasks Today: {status['tasks_today']}")
    print(f"  Quota Remaining: {status['quota_remaining']}")

    # Display task queue
    task_queue = scheduler.get_task_queue()
    print(f"\nTask Queue ({len(task_queue)} tasks):")
    for task in task_queue[:3]:  # Show first 3
        print(f"  - {task['task_id']}: {task['time_until_run_seconds']:.0f}s until run")

    # Display job queue stats
    queue_stats = job_queue.get_queue_stats()
    print(f"\nJob Queue Stats:")
    print(f"  Queue Size: {queue_stats['queue_size']}")
    print(f"  Processed Jobs: {queue_stats['processed_jobs']}")
    print(f"  Failed Jobs: {queue_stats['failed_jobs']}")

    # Start scheduler (in a real implementation)
    # scheduler.start_scheduler()
    # time.sleep(10)  # Run for 10 seconds
    # scheduler.stop_scheduler()


if __name__ == "__main__":
    main()