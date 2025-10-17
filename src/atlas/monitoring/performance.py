"""
Performance Monitoring for Atlas v4

Tracks system performance, resource usage, and operational metrics
with alerting and historical analysis capabilities.
"""

import asyncio
import json
import psutil
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
import threading

from ..logging.enhanced_logging import get_logger, OperationLogger


@dataclass
class PerformanceMetric:
    """Individual performance metric."""
    timestamp: str
    metric_name: str
    value: float
    unit: str
    component: str
    operation: str = None
    tags: Dict[str, str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class SystemMetrics:
    """System-level performance metrics."""
    timestamp: str
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    disk_free_gb: float
    disk_used_gb: float
    network_io: Dict[str, int]
    process_count: int
    load_average: List[float] = None

    def __post_init__(self):
        if self.network_io is None:
            self.network_io = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class AlertRule:
    """Alert rule definition."""
    name: str
    metric_name: str
    condition: str  # gt, lt, eq, gte, lte
    threshold: float
    duration: int = 300  # seconds
    severity: str = "warning"  # info, warning, critical
    enabled: bool = True
    tags: Dict[str, str] = None
    action: str = "log"  # log, email, webhook

    def __post_init__(self):
        if self.tags is None:
            self.tags = {}

    def evaluate(self, value: float) -> bool:
        """Evaluate alert condition."""
        if self.condition == "gt":
            return value > self.threshold
        elif self.condition == "lt":
            return value < self.threshold
        elif self.condition == "eq":
            return value == self.threshold
        elif self.condition == "gte":
            return value >= self.threshold
        elif self.condition == "lte":
            return value <= self.threshold
        return False


class PerformanceCollector:
    """Collects performance metrics from various sources."""

    def __init__(self, component_name: str = "atlas"):
        self.component_name = component_name
        self.logger = get_logger(f"{component_name}.performance")
        self.collectors: Dict[str, Callable] = {}
        self.running = False
        self._setup_default_collectors()

    def _setup_default_collectors(self):
        """Setup default metric collectors."""
        self.collectors.update({
            "system.cpu": self._collect_cpu,
            "system.memory": self._collect_memory,
            "system.disk": self._collect_disk,
            "system.network": self._collect_network,
            "system.processes": self._collect_processes,
            "atlas.operations": self._collect_operations,
            "atlas.errors": self._collect_errors,
            "atlas.database": self._collect_database
        })

    def _collect_cpu(self) -> Dict[str, float]:
        """Collect CPU metrics."""
        try:
            return {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "cpu_count": psutil.cpu_count(),
                "load_average": list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else []
            }
        except Exception as e:
            self.logger.log_error(e, operation="collect_cpu")
            return {}

    def _collect_memory(self) -> Dict[str, float]:
        """Collect memory metrics."""
        try:
            memory = psutil.virtual_memory()
            return {
                "memory_percent": memory.percent,
                "memory_used_mb": memory.used / 1024 / 1024,
                "memory_available_mb": memory.available / 1024 / 1024,
                "memory_total_mb": memory.total / 1024 / 1024
            }
        except Exception as e:
            self.logger.log_error(e, operation="collect_memory")
            return {}

    def _collect_disk(self) -> Dict[str, float]:
        """Collect disk metrics."""
        try:
            disk = psutil.disk_usage('/')
            return {
                "disk_usage_percent": (disk.used / disk.total) * 100,
                "disk_free_gb": disk.free / 1024 / 1024 / 1024,
                "disk_used_gb": disk.used / 1024 / 1024 / 1024,
                "disk_total_gb": disk.total / 1024 / 1024 / 1024
            }
        except Exception as e:
            self.logger.log_error(e, operation="collect_disk")
            return {}

    def _collect_network(self) -> Dict[str, int]:
        """Collect network metrics."""
        try:
            net_io = psutil.net_io_counters()
            return {
                "network_bytes_sent": net_io.bytes_sent,
                "network_bytes_recv": net_io.bytes_recv,
                "network_packets_sent": net_io.packets_sent,
                "network_packets_recv": net_io.packets_recv
            }
        except Exception as e:
            self.logger.log_error(e, operation="collect_network")
            return {}

    def _collect_processes(self) -> Dict[str, int]:
        """Collect process metrics."""
        try:
            return {
                "process_count": len(psutil.pids()),
                "atlas_processes": len([p for p in psutil.process_iter() if 'atlas' in p.name().lower()])
            }
        except Exception as e:
            self.logger.log_error(e, operation="collect_processes")
            return {}

    def _collect_operations(self) -> Dict[str, float]:
        """Collect Atlas operation metrics."""
        # This would be implemented based on actual operation tracking
        return {
            "ingestion_rate": 0.0,
            "processing_rate": 0.0,
            "error_rate": 0.0
        }

    def _collect_errors(self) -> Dict[str, float]:
        """Collect error metrics."""
        # This would be implemented based on actual error tracking
        return {
            "error_count_5m": 0.0,
            "error_count_1h": 0.0,
            "error_rate": 0.0
        }

    def _collect_database(self) -> Dict[str, float]:
        """Collect database metrics."""
        try:
            # Check if database exists and get basic stats
            db_path = Path("/opt/atlas/data/atlas.db")
            if not db_path.exists():
                return {}

            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Get table counts
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()

            metrics = {"database_tables": len(tables)}

            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
                count = cursor.fetchone()[0]
                metrics[f"table_{table[0]}_count"] = count

            conn.close()
            return metrics

        except Exception as e:
            self.logger.log_error(e, operation="collect_database")
            return {}

    def collect_all_metrics(self) -> List[PerformanceMetric]:
        """Collect all registered metrics."""
        metrics = []
        timestamp = datetime.utcnow().isoformat() + "Z"

        for metric_name, collector in self.collectors.items():
            try:
                with OperationLogger(
                    self.logger,
                    operation=f"collect_{metric_name.replace('.', '_')}",
                    component="performance"
                ):
                    values = collector()

                    for key, value in values.items():
                        metric = PerformanceMetric(
                            timestamp=timestamp,
                            metric_name=key,
                            value=float(value),
                            unit="",
                            component=self.component_name,
                            operation="collection"
                        )
                        metrics.append(metric)

            except Exception as e:
                self.logger.log_error(
                    e,
                    operation=f"collect_{metric_name}",
                    component="performance"
                )

        return metrics

    def add_collector(self, name: str, collector: Callable[[], Dict[str, Any]]):
        """Add custom metric collector."""
        self.collectors[name] = collector

    def remove_collector(self, name: str):
        """Remove metric collector."""
        self.collectors.pop(name, None)


class PerformanceMonitor:
    """Main performance monitoring system."""

    def __init__(
        self,
        metrics_db: str = "/opt/atlas/monitoring/metrics.db",
        component_name: str = "atlas",
        collection_interval: int = 60,
        retention_days: int = 30
    ):
        self.metrics_db = Path(metrics_db)
        self.component_name = component_name
        self.collection_interval = collection_interval
        self.retention_days = retention_days
        self.logger = get_logger(f"{component_name}.monitor")

        # Initialize components
        self.collector = PerformanceCollector(component_name)
        self.alert_rules: List[AlertRule] = []
        self.alert_states: Dict[str, Dict] = {}

        # Database setup
        self._setup_database()

        # Add default alert rules
        self._setup_default_alerts()

    def _setup_database(self):
        """Setup metrics database."""
        self.metrics_db.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(str(self.metrics_db))
        cursor = conn.cursor()

        # Create metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                value REAL NOT NULL,
                unit TEXT,
                component TEXT,
                operation TEXT,
                tags TEXT
            )
        """)

        # Create alerts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                alert_name TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                severity TEXT,
                value REAL,
                threshold REAL,
                message TEXT,
                resolved INTEGER DEFAULT 0,
                resolved_timestamp TEXT
            )
        """)

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON performance_metrics(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_name ON performance_metrics(metric_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_resolved ON alerts(resolved)")

        conn.commit()
        conn.close()

    def _setup_default_alerts(self):
        """Setup default alert rules."""
        default_alerts = [
            AlertRule(
                name="high_cpu_usage",
                metric_name="cpu_percent",
                condition="gt",
                threshold=80.0,
                duration=300,
                severity="warning"
            ),
            AlertRule(
                name="high_memory_usage",
                metric_name="memory_percent",
                condition="gt",
                threshold=85.0,
                duration=300,
                severity="warning"
            ),
            AlertRule(
                name="low_disk_space",
                metric_name="disk_usage_percent",
                condition="gt",
                threshold=90.0,
                duration=60,
                severity="critical"
            ),
            AlertRule(
                name="high_error_rate",
                metric_name="error_rate",
                condition="gt",
                threshold=0.1,  # 10%
                duration=300,
                severity="warning"
            )
        ]

        for alert in default_alerts:
            self.add_alert_rule(alert)

    def add_alert_rule(self, rule: AlertRule):
        """Add alert rule."""
        self.alert_rules.append(rule)
        self.logger.log_operation(
            level="INFO",
            operation="add_alert_rule",
            message=f"Added alert rule: {rule.name}",
            component="monitoring"
        )

    def remove_alert_rule(self, rule_name: str):
        """Remove alert rule."""
        self.alert_rules = [rule for rule in self.alert_rules if rule.name != rule_name]
        if rule_name in self.alert_states:
            del self.alert_states[rule_name]

        self.logger.log_operation(
            level="INFO",
            operation="remove_alert_rule",
            message=f"Removed alert rule: {rule_name}",
            component="monitoring"
        )

    def store_metrics(self, metrics: List[PerformanceMetric]):
        """Store metrics in database."""
        if not metrics:
            return

        conn = sqlite3.connect(str(self.metrics_db))
        cursor = conn.cursor()

        for metric in metrics:
            cursor.execute("""
                INSERT INTO performance_metrics
                (timestamp, metric_name, value, unit, component, operation, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                metric.timestamp,
                metric.metric_name,
                metric.value,
                metric.unit,
                metric.component,
                metric.operation,
                json.dumps(metric.tags) if metric.tags else None
            ))

        conn.commit()
        conn.close()

    def evaluate_alerts(self, metrics: List[PerformanceMetric]):
        """Evaluate alert rules against metrics."""
        metric_values = {metric.metric_name: metric.value for metric in metrics}

        for rule in self.alert_rules:
            if not rule.enabled:
                continue

            if rule.metric_name not in metric_values:
                continue

            current_value = metric_values[rule.metric_name]
            is_triggered = rule.evaluate(current_value)

            self._update_alert_state(rule, current_value, is_triggered)

    def _update_alert_state(self, rule: AlertRule, value: float, is_triggered: bool):
        """Update alert state and trigger alerts if needed."""
        now = datetime.utcnow()
        alert_key = rule.name

        if alert_key not in self.alert_states:
            self.alert_states[alert_key] = {
                "triggered": False,
                "first_triggered": None,
                "last_notified": None,
                "count": 0
            }

        state = self.alert_states[alert_key]

        if is_triggered:
            if not state["triggered"]:
                # Alert just triggered
                state["triggered"] = True
                state["first_triggered"] = now
                state["count"] = 1
            else:
                # Alert still triggered
                state["count"] += 1

            # Check if duration threshold met
            if state["first_triggered"]:
                duration_seconds = (now - state["first_triggered"]).total_seconds()

                if duration_seconds >= rule.duration:
                    # Check if we should notify (avoid spam)
                    if not state["last_notified"] or (now - state["last_notified"]).total_seconds() >= rule.duration:
                        self._trigger_alert(rule, value)
                        state["last_notified"] = now

        else:
            # Alert not triggered, reset state
            if state["triggered"]:
                self._resolve_alert(rule)
            state["triggered"] = False
            state["first_triggered"] = None
            state["last_notified"] = None
            state["count"] = 0

    def _trigger_alert(self, rule: AlertRule, value: float):
        """Trigger alert notification."""
        message = f"Alert '{rule.name}' triggered: {rule.metric_name} = {value} (threshold: {rule.threshold})"

        self.logger.log_operation(
            level="ERROR" if rule.severity == "critical" else "WARNING",
            operation="alert_triggered",
            message=message,
            component="monitoring",
            extra_data={
                "alert_name": rule.name,
                "metric_name": rule.metric_name,
                "value": value,
                "threshold": rule.threshold,
                "severity": rule.severity
            }
        )

        # Store alert in database
        self._store_alert(rule, value, message)

    def _resolve_alert(self, rule: AlertRule):
        """Resolve alert."""
        message = f"Alert '{rule.name}' resolved"

        self.logger.log_operation(
            level="INFO",
            operation="alert_resolved",
            message=message,
            component="monitoring",
            extra_data={
                "alert_name": rule.name,
                "metric_name": rule.metric_name
            }
        )

        # Mark alert as resolved in database
        self._resolve_alert_in_db(rule.name)

    def _store_alert(self, rule: AlertRule, value: float, message: str):
        """Store alert in database."""
        conn = sqlite3.connect(str(self.metrics_db))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO alerts
            (timestamp, alert_name, metric_name, severity, value, threshold, message, resolved)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.utcnow().isoformat() + "Z",
            rule.name,
            rule.metric_name,
            rule.severity,
            value,
            rule.threshold,
            message,
            0  # not resolved
        ))

        conn.commit()
        conn.close()

    def _resolve_alert_in_db(self, alert_name: str):
        """Mark alert as resolved in database."""
        conn = sqlite3.connect(str(self.metrics_db))
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE alerts
            SET resolved = 1, resolved_timestamp = ?
            WHERE alert_name = ? AND resolved = 0
        """, (datetime.utcnow().isoformat() + "Z", alert_name))

        conn.commit()
        conn.close()

    async def start_monitoring(self):
        """Start performance monitoring."""
        self.logger.log_operation(
            level="INFO",
            operation="start_monitoring",
            message=f"Starting performance monitoring (interval: {self.collection_interval}s)",
            component="monitoring"
        )

        self.running = True

        while self.running:
            try:
                with OperationLogger(
                    self.logger,
                    operation="collect_metrics",
                    component="monitoring"
                ):
                    # Collect metrics
                    metrics = self.collector.collect_all_metrics()

                    # Store metrics
                    self.store_metrics(metrics)

                    # Evaluate alerts
                    self.evaluate_alerts(metrics)

                    # Cleanup old metrics
                    self._cleanup_old_metrics()

            except Exception as e:
                self.logger.log_error(e, operation="monitoring_loop", component="monitoring")

            # Wait for next collection
            await asyncio.sleep(self.collection_interval)

    def stop_monitoring(self):
        """Stop performance monitoring."""
        self.running = False
        self.logger.log_operation(
            level="INFO",
            operation="stop_monitoring",
            message="Performance monitoring stopped",
            component="monitoring"
        )

    def _cleanup_old_metrics(self):
        """Cleanup old metrics based on retention policy."""
        cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)

        conn = sqlite3.connect(str(self.metrics_db))
        cursor = conn.cursor()

        # Delete old metrics
        cursor.execute("""
            DELETE FROM performance_metrics
            WHERE timestamp < ?
        """, (cutoff_date.isoformat() + "Z",))

        # Delete old resolved alerts
        cursor.execute("""
            DELETE FROM alerts
            WHERE resolved = 1 AND resolved_timestamp < ?
        """, (cutoff_date.isoformat() + "Z",))

        conn.commit()
        conn.close()

    def get_metrics(
        self,
        metric_name: str = None,
        start_time: datetime = None,
        end_time: datetime = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Get metrics from database."""
        conn = sqlite3.connect(str(self.metrics_db))
        cursor = conn.cursor()

        query = "SELECT * FROM performance_metrics WHERE 1=1"
        params = []

        if metric_name:
            query += " AND metric_name = ?"
            params.append(metric_name)

        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat() + "Z")

        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat() + "Z")

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        # Convert to dictionaries
        columns = [desc[0] for desc in cursor.description]
        metrics = [dict(zip(columns, row)) for row in rows]

        conn.close()
        return metrics

    def get_alerts(
        self,
        resolved: bool = None,
        severity: str = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get alerts from database."""
        conn = sqlite3.connect(str(self.metrics_db))
        cursor = conn.cursor()

        query = "SELECT * FROM alerts WHERE 1=1"
        params = []

        if resolved is not None:
            query += " AND resolved = ?"
            params.append(1 if resolved else 0)

        if severity:
            query += " AND severity = ?"
            params.append(severity)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        # Convert to dictionaries
        columns = [desc[0] for desc in cursor.description]
        alerts = [dict(zip(columns, row)) for row in rows]

        conn.close()
        return alerts

    def get_system_summary(self) -> Dict[str, Any]:
        """Get system performance summary."""
        # Get latest metrics
        latest_metrics = self.get_metrics(limit=100)

        # Group by metric name and get latest value
        summary = {}
        for metric in latest_metrics:
            name = metric["metric_name"]
            if name not in summary:
                summary[name] = metric

        # Add alert summary
        active_alerts = len([a for a in self.get_alerts(resolved=False)])
        total_alerts = len(self.get_alerts(limit=1000))

        summary.update({
            "active_alerts": active_alerts,
            "total_alerts": total_alerts,
            "monitoring_active": self.running,
            "collection_interval": self.collection_interval
        })

        return summary