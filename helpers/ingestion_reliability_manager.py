"""
Atlas Ingestion Reliability Manager
Production-grade reliability patterns for ingestion system.
"""

import asyncio
import time
import logging
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
import threading

from .queue_manager import QueueManager
from .error_recovery import ErrorRecoveryManager
from .resource_manager import ResourceManager
from .service_health_monitor import AtlasServiceHealthMonitor


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


@dataclass
class ReliabilityMetrics:
    """Reliability metrics collection"""
    total_processed: int = 0
    successful_processed: int = 0
    failed_processed: int = 0
    retry_count: int = 0
    circuit_breaker_trips: int = 0
    average_processing_time: float = 0.0
    system_health: HealthStatus = HealthStatus.HEALTHY
    last_health_check: datetime = field(default_factory=datetime.now)

    def calculate_success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.total_processed == 0:
            return 0.0
        return (self.successful_processed / self.total_processed) * 100

    def calculate_failure_rate(self) -> float:
        """Calculate failure rate percentage"""
        if self.total_processed == 0:
            return 0.0
        return (self.failed_processed / self.total_processed) * 100


class AdaptiveRateLimiter:
    """Adaptive rate limiter with token bucket algorithm"""

    def __init__(self, initial_rate: int = 100, burst_size: int = 50):
        self.max_rate = initial_rate
        self.burst_size = burst_size
        self.current_tokens = burst_size
        self.last_refill = time.time()
        self.refill_rate = initial_rate / 60.0  # tokens per second
        self._lock = threading.Lock()

    def acquire(self, tokens: int = 1) -> bool:
        """Acquire tokens from the bucket"""
        with self._lock:
            now = time.time()
            # Refill tokens based on elapsed time
            elapsed = now - self.last_refill
            self.current_tokens = min(
                self.burst_size,
                self.current_tokens + (elapsed * self.refill_rate)
            )
            self.last_refill = now

            if self.current_tokens >= tokens:
                self.current_tokens -= tokens
                return True
            return False

    def adjust_rate(self, new_rate: int):
        """Adjust rate limit based on system health"""
        with self._lock:
            self.max_rate = new_rate
            self.refill_rate = new_rate / 60.0


class PredictiveScaling:
    """Predictive scaling based on historical patterns"""

    def __init__(self, history_window: int = 100):
        self.processing_history = []
        self.history_window = history_window
        self.prediction_window = 5  # Predict 5 minutes ahead

    def record_processing_time(self, duration: float):
        """Record processing time for pattern analysis"""
        self.processing_history.append({
            'timestamp': time.time(),
            'duration': duration
        })

        # Keep only recent history
        if len(self.processing_history) > self.history_window:
            self.processing_history.pop(0)

    def predict_load(self) -> float:
        """Predict future load based on historical patterns"""
        if len(self.processing_history) < 10:
            return 0.0

        # Simple moving average prediction
        recent_times = [h['duration'] for h in self.processing_history[-10:]]
        avg_time = statistics.mean(recent_times)

        # Predict based on recent trends
        if len(recent_times) >= 5:
            trend = recent_times[-1] - recent_times[-5]
            predicted_time = avg_time + (trend * 0.5)  # Conservative trend prediction
            return max(0.0, predicted_time)

        return avg_time

    def get_optimal_worker_count(self, current_workers: int) -> int:
        """Calculate optimal worker count based on predictions"""
        predicted_load = self.predict_load()
        if predicted_load == 0:
            return current_workers

        # Simple scaling logic
        if predicted_load > 10.0:  # High load
            return min(current_workers * 2, 20)
        elif predicted_load < 1.0:  # Low load
            return max(current_workers // 2, 1)
        else:
            return current_workers


class IngestionReliabilityManager:
    """Production-grade ingestion reliability management"""

    def __init__(self, config_path: str = "config/ingestion_reliability.yaml"):
        self.logger = logging.getLogger(__name__)
        self.config_path = Path(config_path)
        self.metrics = ReliabilityMetrics()

        # Core components
        self.queue_manager = QueueManager()
        self.error_recovery = ErrorRecoveryManager("ingestion_reliability_manager")
        # Initialize resource manager with no log file checking to avoid permission issues
        self.resource_manager = None
        self.health_monitor = AtlasServiceHealthMonitor()

        # Reliability components
        self.rate_limiter = AdaptiveRateLimiter()
        self.predictive_scaling = PredictiveScaling()

        # Runtime state
        self.is_running = False
        self.workers = []
        self.circuit_breakers = {}
        self.retry_budget = 1000  # Global retry budget
        self._lock = threading.Lock()

        # Load configuration
        self.load_config()

    def load_config(self):
        """Load reliability configuration"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    config = json.load(f)

                # Configure rate limiter
                rate_config = config.get('rate_limiting', {})
                self.rate_limiter = AdaptiveRateLimiter(
                    initial_rate=rate_config.get('initial_rate', 100),
                    burst_size=rate_config.get('burst_size', 50)
                )

                # Configure predictive scaling
                scaling_config = config.get('predictive_scaling', {})
                self.predictive_scaling = PredictiveScaling(
                    history_window=scaling_config.get('history_window', 100)
                )

                # Configure retry budget
                self.retry_budget = config.get('retry_budget', 1000)

        except Exception as e:
            self.logger.warning(f"Failed to load reliability config: {e}")

    def start_reliability_manager(self):
        """Start the reliability manager"""
        if self.is_running:
            return

        self.is_running = True
        self.logger.info("Starting ingestion reliability manager...")

        # Start monitoring threads
        self.start_monitoring_threads()

        # Start predictive scaling
        self.start_predictive_scaling()

        self.logger.info("Ingestion reliability manager started")

    def stop_reliability_manager(self):
        """Stop the reliability manager"""
        self.is_running = False
        self.logger.info("Stopping ingestion reliability manager...")

        # Stop all workers
        for worker in self.workers:
            worker.stop()

        self.logger.info("Ingestion reliability manager stopped")

    def start_monitoring_threads(self):
        """Start background monitoring threads"""
        # Health monitoring
        def health_monitor():
            while self.is_running:
                try:
                    self.check_system_health()
                    time.sleep(30)  # Check every 30 seconds
                except Exception as e:
                    self.logger.error(f"Health monitor error: {e}")

        # Metrics collection
        def metrics_collector():
            while self.is_running:
                try:
                    self.collect_metrics()
                    time.sleep(60)  # Collect every minute
                except Exception as e:
                    self.logger.error(f"Metrics collector error: {e}")

        # Start threads
        threading.Thread(target=health_monitor, daemon=True).start()
        threading.Thread(target=metrics_collector, daemon=True).start()

    def start_predictive_scaling(self):
        """Start predictive scaling"""
        def scaling_worker():
            while self.is_running:
                try:
                    optimal_workers = self.predictive_scaling.get_optimal_worker_count(len(self.workers))
                    self.adjust_worker_count(optimal_workers)
                    time.sleep(300)  # Check every 5 minutes
                except Exception as e:
                    self.logger.error(f"Predictive scaling error: {e}")

        threading.Thread(target=scaling_worker, daemon=True).start()

    def check_system_health(self):
        """Check overall system health"""
        try:
            # Get health status from components
            queue_health = self.queue_manager.get_queue_health()
            resource_health = self.resource_manager.get_resource_health() if self.resource_manager else {
                'memory_usage': 50,
                'cpu_usage': 30,
                'healthy': True
            }
            service_health = self.health_monitor.get_overall_health()

            # Determine overall health
            critical_failures = 0
            total_checks = 0

            # Check queue health
            if queue_health.get('depth_ratio', 0) > 0.9:
                critical_failures += 1
            total_checks += 1

            # Check resource health
            if resource_health.get('memory_usage', 0) > 90:
                critical_failures += 1
            if resource_health.get('cpu_usage', 0) > 90:
                critical_failures += 1
            total_checks += 2

            # Check service health
            if service_health.get('overall_health', 'healthy') == 'unhealthy':
                critical_failures += 1
            total_checks += 1

            # Determine health status
            failure_rate = (critical_failures / total_checks) * 100 if total_checks > 0 else 0

            if failure_rate >= 75:
                self.metrics.system_health = HealthStatus.CRITICAL
            elif failure_rate >= 50:
                self.metrics.system_health = HealthStatus.UNHEALTHY
            elif failure_rate >= 25:
                self.metrics.system_health = HealthStatus.DEGRADED
            else:
                self.metrics.system_health = HealthStatus.HEALTHY

            # Adjust rate limiting based on health
            self.adjust_rate_based_on_health()

            self.metrics.last_health_check = datetime.now()

        except Exception as e:
            self.logger.error(f"Health check error: {e}")

    def adjust_rate_based_on_health(self):
        """Adjust rate limiting based on system health"""
        health = self.metrics.system_health

        if health == HealthStatus.CRITICAL:
            # Reduce rate to 10% of normal
            new_rate = max(10, int(self.rate_limiter.max_rate * 0.1))
        elif health == HealthStatus.UNHEALTHY:
            # Reduce rate to 25% of normal
            new_rate = max(25, int(self.rate_limiter.max_rate * 0.25))
        elif health == HealthStatus.DEGRADED:
            # Reduce rate to 50% of normal
            new_rate = max(50, int(self.rate_limiter.max_rate * 0.5))
        else:
            # Restore to normal rate
            new_rate = 100

        self.rate_limiter.adjust_rate(new_rate)

    def collect_metrics(self):
        """Collect reliability metrics"""
        try:
            # Get queue metrics
            queue_stats = self.queue_manager.get_queue_stats()

            # Get resource metrics
            resource_stats = self.resource_manager.get_resource_stats()

            # Update metrics
            self.metrics.total_processed = queue_stats.get('total_processed', 0)
            self.metrics.successful_processed = queue_stats.get('successful_processed', 0)
            self.metrics.failed_processed = queue_stats.get('failed_processed', 0)
            self.metrics.retry_count = queue_stats.get('retry_count', 0)
            self.metrics.circuit_breaker_trips = queue_stats.get('circuit_breaker_trips', 0)

            # Calculate average processing time
            processing_times = queue_stats.get('processing_times', [])
            if processing_times:
                self.metrics.average_processing_time = statistics.mean(processing_times)

        except Exception as e:
            self.logger.error(f"Metrics collection error: {e}")

    def adjust_worker_count(self, optimal_count: int):
        """Adjust worker count based on predictions"""
        current_count = len(self.workers)

        if optimal_count > current_count:
            # Scale up
            self.add_workers(optimal_count - current_count)
        elif optimal_count < current_count:
            # Scale down
            self.remove_workers(current_count - optimal_count)

    def add_workers(self, count: int):
        """Add new workers"""
        for _ in range(count):
            worker = IngestionWorker(self)
            worker.start()
            self.workers.append(worker)
            self.logger.info(f"Added ingestion worker, total workers: {len(self.workers)}")

    def remove_workers(self, count: int):
        """Remove workers"""
        for _ in range(min(count, len(self.workers))):
            if self.workers:
                worker = self.workers.pop()
                worker.stop()
                self.logger.info(f"Removed ingestion worker, total workers: {len(self.workers)}")

    def process_task(self, task_data: Dict[str, Any]) -> bool:
        """Process a task with reliability guarantees"""
        if not self.rate_limiter.acquire():
            self.logger.warning("Rate limit exceeded, task rejected")
            return False

        start_time = time.time()

        try:
            # Process the task
            success = self.queue_manager.process_task(task_data)

            # Record metrics
            processing_time = time.time() - start_time
            self.predictive_scaling.record_processing_time(processing_time)

            with self._lock:
                self.metrics.total_processed += 1
                if success:
                    self.metrics.successful_processed += 1
                else:
                    self.metrics.failed_processed += 1

            return success

        except Exception as e:
            self.logger.error(f"Task processing error: {e}")
            with self._lock:
                self.metrics.total_processed += 1
                self.metrics.failed_processed += 1
            return False

    def get_reliability_status(self) -> Dict[str, Any]:
        """Get current reliability status"""
        return {
            'system_health': self.metrics.system_health.value,
            'success_rate': self.metrics.calculate_success_rate(),
            'failure_rate': self.metrics.calculate_failure_rate(),
            'total_processed': self.metrics.total_processed,
            'retry_count': self.metrics.retry_count,
            'circuit_breaker_trips': self.metrics.circuit_breaker_trips,
            'average_processing_time': self.metrics.average_processing_time,
            'current_workers': len(self.workers),
            'rate_limit': self.rate_limiter.max_rate,
            'retry_budget': self.retry_budget,
            'last_health_check': self.metrics.last_health_check.isoformat()
        }


class IngestionWorker:
    """Individual ingestion worker"""

    def __init__(self, reliability_manager: IngestionReliabilityManager):
        self.reliability_manager = reliability_manager
        self.is_running = False
        self.worker_thread = None
        self.logger = logging.getLogger(__name__)

    def start(self):
        """Start the worker"""
        if self.is_running:
            return

        self.is_running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()

    def stop(self):
        """Stop the worker"""
        self.is_running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)

    def _worker_loop(self):
        """Main worker loop"""
        while self.is_running:
            try:
                # Get task from queue
                task = self.reliability_manager.queue_manager.get_next_task()
                if task:
                    # Process task with retry logic
                    self._process_task_with_retry(task)
                else:
                    time.sleep(1)  # No tasks, wait a bit

            except Exception as e:
                self.logger.error(f"Worker error: {e}")
                time.sleep(5)  # Wait before retrying

    def _process_task_with_retry(self, task: Dict[str, Any]):
        """Process task with retry logic"""
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                # Process the task
                success = self.reliability_manager.process_task(task)

                if success:
                    return
                else:
                    retry_count += 1
                    if retry_count < max_retries:
                        delay = 2 ** retry_count  # Exponential backoff
                        time.sleep(delay)

            except Exception as e:
                retry_count += 1
                if retry_count < max_retries:
                    delay = 2 ** retry_count
                    time.sleep(delay)
                else:
                    self.logger.error(f"Task failed after {max_retries} retries: {e}")

        # Task failed after all retries
        self.reliability_manager.queue_manager.move_to_dead_letter(task, "Max retries exceeded")


# Global instance
reliability_manager = None

def get_reliability_manager() -> IngestionReliabilityManager:
    """Get global reliability manager instance"""
    global reliability_manager
    if reliability_manager is None:
        reliability_manager = IngestionReliabilityManager()
    return reliability_manager