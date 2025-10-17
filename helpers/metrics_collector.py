"""
Atlas Metrics Collector
Collects and exports Prometheus-style metrics for monitoring.
"""

import time
import threading
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, deque
import logging

from .database_config import get_database_connection
from .queue_manager import get_queue_status


@dataclass
class MetricPoint:
    """Single metric measurement."""
    timestamp: float
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class Metric:
    """Metric definition with history."""
    name: str
    help_text: str
    metric_type: str  # counter, gauge, histogram
    points: deque = field(default_factory=lambda: deque(maxlen=1000))
    labels: Dict[str, str] = field(default_factory=dict)


class MetricsCollector:
    """Collects and exports system metrics."""

    def __init__(self):
        """Initialize metrics collector."""
        self.logger = logging.getLogger(__name__)
        self._metrics: Dict[str, Metric] = {}
        self._collection_thread = None
        self._running = False
        self._lock = threading.RLock()

        # Performance tracking
        self._last_collection = time.time()
        self._collection_interval = 60  # seconds

        # Initialize core metrics
        self._initialize_metrics()

    def _initialize_metrics(self):
        """Initialize core system metrics."""
        metrics_config = [
            # Queue metrics
            ("atlas_queue_pending_total", "Number of pending tasks in queue", "gauge"),
            ("atlas_queue_processing_total", "Number of tasks currently processing", "gauge"),
            ("atlas_queue_completed_total", "Number of completed tasks", "counter"),
            ("atlas_queue_failed_total", "Number of failed tasks", "counter"),
            ("atlas_queue_retry_ready_total", "Number of tasks ready for retry", "gauge"),

            # Processing metrics
            ("atlas_transcriptions_total", "Total number of transcriptions processed", "counter"),
            ("atlas_transcription_rate", "Transcriptions processed per minute", "gauge"),
            ("atlas_episodes_harvested_total", "Total episodes harvested", "counter"),
            ("atlas_articles_processed_total", "Total articles processed", "counter"),

            # System health metrics
            ("atlas_system_uptime_seconds", "System uptime in seconds", "gauge"),
            ("atlas_database_size_bytes", "Database size in bytes", "gauge"),
            ("atlas_memory_usage_bytes", "Memory usage in bytes", "gauge"),
            ("atlas_disk_free_bytes", "Free disk space in bytes", "gauge"),

            # Error metrics
            ("atlas_error_rate", "Error rate percentage", "gauge"),
            ("atlas_circuit_breaker_open", "Circuit breaker status (1=open, 0=closed)", "gauge"),

            # Performance metrics
            ("atlas_response_time_seconds", "Response time for operations", "histogram"),
            ("atlas_database_connections", "Active database connections", "gauge"),
        ]

        for name, help_text, metric_type in metrics_config:
            self._metrics[name] = Metric(
                name=name,
                help_text=help_text,
                metric_type=metric_type
            )

    def start_collection(self):
        """Start background metrics collection."""
        if self._running:
            return

        self._running = True
        self._collection_thread = threading.Thread(target=self._collection_loop, daemon=True)
        self._collection_thread.start()
        self.logger.info("Metrics collection started")

    def stop_collection(self):
        """Stop background metrics collection."""
        self._running = False
        if self._collection_thread:
            self._collection_thread.join(timeout=5)
        self.logger.info("Metrics collection stopped")

    def _collection_loop(self):
        """Main collection loop."""
        while self._running:
            try:
                self._collect_all_metrics()
                time.sleep(self._collection_interval)
            except Exception as e:
                self.logger.error(f"Error in metrics collection: {e}")
                time.sleep(30)  # Shorter interval on error

    def _collect_all_metrics(self):
        """Collect all system metrics."""
        current_time = time.time()

        # Queue metrics
        self._collect_queue_metrics(current_time)

        # Processing metrics
        self._collect_processing_metrics(current_time)

        # System metrics
        self._collect_system_metrics(current_time)

        # Performance metrics
        self._collect_performance_metrics(current_time)

        self._last_collection = current_time

    def _collect_queue_metrics(self, timestamp: float):
        """Collect queue-related metrics."""
        try:
            queue_status = get_queue_status()
            queue_counts = queue_status.get("queue_counts", {})

            self.record_metric("atlas_queue_pending_total", queue_counts.get("pending", 0), timestamp)
            self.record_metric("atlas_queue_processing_total", queue_counts.get("processing", 0), timestamp)
            self.record_metric("atlas_queue_completed_total", queue_counts.get("completed", 0), timestamp)
            self.record_metric("atlas_queue_failed_total", queue_status.get("failed_tasks", 0), timestamp)
            self.record_metric("atlas_queue_retry_ready_total", queue_status.get("retry_ready", 0), timestamp)

            # Circuit breaker metrics
            circuit_breakers = queue_status.get("circuit_breakers", {})
            for worker, cb_status in circuit_breakers.items():
                is_open = 1 if cb_status.get("state") == "open" else 0
                self.record_metric("atlas_circuit_breaker_open", is_open, timestamp, {"worker": worker})

        except Exception as e:
            self.logger.error(f"Failed to collect queue metrics: {e}")

    def _collect_processing_metrics(self, timestamp: float):
        """Collect processing-related metrics."""
        try:
            conn = get_database_connection()
            cursor = conn.cursor()

            # Transcription metrics
            cursor.execute("SELECT COUNT(*) FROM transcriptions")
            transcription_count = cursor.fetchone()[0]
            self.record_metric("atlas_transcriptions_total", transcription_count, timestamp)

            # Episodes harvested
            cursor.execute("SELECT COUNT(*) FROM podcast_episodes")
            episodes_count = cursor.fetchone()[0]
            self.record_metric("atlas_episodes_harvested_total", episodes_count, timestamp)

            # Articles processed
            cursor.execute("SELECT COUNT(*) FROM content WHERE content_type = 'article'")
            articles_count = cursor.fetchone()[0]
            self.record_metric("atlas_articles_processed_total", articles_count, timestamp)

            # Calculate transcription rate (last hour)
            one_hour_ago = datetime.now() - timedelta(hours=1)
            cursor.execute("""
                SELECT COUNT(*) FROM transcriptions
                WHERE created_at > ?
            """, (one_hour_ago,))
            recent_transcriptions = cursor.fetchone()[0]
            transcription_rate = recent_transcriptions / 60.0  # per minute
            self.record_metric("atlas_transcription_rate", transcription_rate, timestamp)

            conn.close()

        except Exception as e:
            self.logger.error(f"Failed to collect processing metrics: {e}")

    def _collect_system_metrics(self, timestamp: float):
        """Collect system health metrics."""
        try:
            import psutil

            # Memory usage
            process = psutil.Process()
            memory_info = process.memory_info()
            self.record_metric("atlas_memory_usage_bytes", memory_info.rss, timestamp)

            # Disk space
            disk_usage = psutil.disk_usage('/')
            self.record_metric("atlas_disk_free_bytes", disk_usage.free, timestamp)

            # Database size
            from .database_config import get_database_path
            db_path = get_database_path()
            if db_path.exists():
                db_size = db_path.stat().st_size
                self.record_metric("atlas_database_size_bytes", db_size, timestamp)

        except Exception as e:
            self.logger.error(f"Failed to collect system metrics: {e}")

    def _collect_performance_metrics(self, timestamp: float):
        """Collect performance metrics."""
        try:
            # Database connections (approximate)
            conn_count = 1  # Simplified for now
            self.record_metric("atlas_database_connections", conn_count, timestamp)

        except Exception as e:
            self.logger.error(f"Failed to collect performance metrics: {e}")

    def record_metric(self, name: str, value: float, timestamp: Optional[float] = None,
                     labels: Optional[Dict[str, str]] = None):
        """Record a metric value."""
        if name not in self._metrics:
            self.logger.warning(f"Unknown metric: {name}")
            return

        if timestamp is None:
            timestamp = time.time()

        if labels is None:
            labels = {}

        with self._lock:
            metric = self._metrics[name]
            point = MetricPoint(timestamp=timestamp, value=value, labels=labels)
            metric.points.append(point)

    def get_metric_value(self, name: str, labels: Optional[Dict[str, str]] = None) -> Optional[float]:
        """Get the latest value for a metric."""
        if name not in self._metrics:
            return None

        with self._lock:
            metric = self._metrics[name]
            if not metric.points:
                return None

            # Find matching point with labels
            for point in reversed(metric.points):
                if labels is None or point.labels == labels:
                    return point.value

            return None

    def get_prometheus_metrics(self) -> str:
        """Export metrics in Prometheus format."""
        output = []

        with self._lock:
            for metric in self._metrics.values():
                if not metric.points:
                    continue

                # Add help and type
                output.append(f"# HELP {metric.name} {metric.help_text}")
                output.append(f"# TYPE {metric.name} {metric.metric_type}")

                # Get latest value for each label combination
                latest_points = {}
                for point in metric.points:
                    labels_key = frozenset(point.labels.items()) if point.labels else frozenset()
                    if labels_key not in latest_points or point.timestamp > latest_points[labels_key].timestamp:
                        latest_points[labels_key] = point

                # Output metrics
                for point in latest_points.values():
                    if point.labels:
                        labels_str = ','.join(f'{k}="{v}"' for k, v in point.labels.items())
                        output.append(f"{metric.name}{{{labels_str}}} {point.value}")
                    else:
                        output.append(f"{metric.name} {point.value}")

                output.append("")  # Empty line between metrics

        return "\n".join(output)

    def get_alert_conditions(self) -> List[Dict[str, Any]]:
        """Check for alert conditions."""
        alerts = []
        current_time = time.time()

        # Processing stalled >20min
        transcription_rate = self.get_metric_value("atlas_transcription_rate")
        if transcription_rate is not None and transcription_rate == 0:
            # Check if we have any recent activity
            twenty_min_ago = current_time - (20 * 60)
            recent_activity = any(
                point.timestamp > twenty_min_ago
                for point in self._metrics.get("atlas_transcriptions_total", Metric("", "", "")).points
            )
            if not recent_activity:
                alerts.append({
                    "severity": "critical",
                    "condition": "processing_stalled",
                    "message": "Transcript processing has been stalled for >20 minutes",
                    "metric": "atlas_transcription_rate",
                    "value": 0
                })

        # Queue depth >500
        queue_depth = self.get_metric_value("atlas_queue_pending_total")
        if queue_depth is not None and queue_depth > 500:
            severity = "critical" if queue_depth > 1000 else "warning"
            alerts.append({
                "severity": severity,
                "condition": "high_queue_depth",
                "message": f"Queue depth is {queue_depth} (threshold: 500)",
                "metric": "atlas_queue_pending_total",
                "value": queue_depth
            })

        # Circuit breakers open
        for metric_name, metric in self._metrics.items():
            if metric_name == "atlas_circuit_breaker_open":
                for point in metric.points:
                    if point.value == 1:  # Circuit breaker is open
                        worker = point.labels.get("worker", "unknown")
                        alerts.append({
                            "severity": "warning",
                            "condition": "circuit_breaker_open",
                            "message": f"Circuit breaker open for worker: {worker}",
                            "metric": metric_name,
                            "value": 1,
                            "labels": point.labels
                        })

        return alerts

    def get_health_summary(self) -> Dict[str, Any]:
        """Get overall system health summary."""
        alerts = self.get_alert_conditions()
        critical_alerts = [a for a in alerts if a["severity"] == "critical"]
        warning_alerts = [a for a in alerts if a["severity"] == "warning"]

        status = "healthy"
        if critical_alerts:
            status = "critical"
        elif warning_alerts:
            status = "warning"

        return {
            "status": status,
            "alerts": alerts,
            "critical_count": len(critical_alerts),
            "warning_count": len(warning_alerts),
            "metrics_collected": len([m for m in self._metrics.values() if m.points]),
            "last_collection": self._last_collection,
            "collection_interval": self._collection_interval
        }


# Global metrics collector instance
_metrics_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance."""
    return _metrics_collector


def start_metrics_collection():
    """Start global metrics collection."""
    _metrics_collector.start_collection()


def stop_metrics_collection():
    """Stop global metrics collection."""
    _metrics_collector.stop_collection()


def get_prometheus_metrics() -> str:
    """Get Prometheus-formatted metrics."""
    return _metrics_collector.get_prometheus_metrics()


def get_health_summary() -> Dict[str, Any]:
    """Get system health summary."""
    return _metrics_collector.get_health_summary()