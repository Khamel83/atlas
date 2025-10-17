#!/usr/bin/env python3
"""
Production Monitor - Phase C2
Health monitoring, alerting, and automatic error recovery for production deployment.
"""

import os
import json
import time
import logging
import sqlite3
import smtplib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
import threading
import subprocess
import psutil

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProductionMonitor:
    """Production monitoring and alerting system."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize production monitor."""
        self.config = config or {}
        self.monitoring_db = Path(self.config.get('monitoring_db', 'data/monitoring.db'))
        self.alert_config_file = Path(self.config.get('alert_config', 'config/alert_config.json'))

        # Monitoring intervals
        self.health_check_interval = self.config.get('health_check_interval', 60)  # 1 minute
        self.metrics_collection_interval = self.config.get('metrics_interval', 300)  # 5 minutes

        # Alert thresholds
        self.alert_thresholds = {
            'memory_usage_percent': 85,
            'disk_usage_percent': 90,
            'cpu_usage_percent': 90,
            'error_rate_percent': 10,
            'response_time_ms': 2000,
            'failed_requests_per_hour': 50
        }

        # Monitoring state
        self.is_monitoring = False
        self.monitoring_thread = None
        self.last_alert_time = {}
        self.alert_cooldown = 1800  # 30 minutes

        # Initialize database
        self._init_monitoring_database()

        # Load alert configuration
        self._load_alert_config()

    def _init_monitoring_database(self):
        """Initialize monitoring database."""
        try:
            self.monitoring_db.parent.mkdir(exist_ok=True)

            conn = sqlite3.connect(self.monitoring_db)
            cursor = conn.cursor()

            # Health check logs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS health_checks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    status TEXT NOT NULL,
                    response_time_ms REAL,
                    memory_usage_mb REAL,
                    cpu_usage_percent REAL,
                    disk_usage_percent REAL,
                    active_connections INTEGER,
                    error_count INTEGER,
                    details TEXT
                )
            """)

            # Alert logs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT NOT NULL,
                    details TEXT,
                    resolved_at TEXT,
                    resolution_notes TEXT
                )
            """)

            # Performance metrics
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    metric_type TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    value REAL NOT NULL,
                    unit TEXT,
                    context TEXT
                )
            """)

            # Error logs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS error_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    error_type TEXT NOT NULL,
                    error_message TEXT NOT NULL,
                    stack_trace TEXT,
                    request_context TEXT,
                    resolved BOOLEAN DEFAULT FALSE
                )
            """)

            conn.commit()
            conn.close()

            logger.info("✅ Monitoring database initialized")

        except Exception as e:
            logger.error(f"Failed to initialize monitoring database: {e}")

    def _load_alert_config(self):
        """Load alert configuration."""
        try:
            if self.alert_config_file.exists():
                with open(self.alert_config_file, 'r') as f:
                    alert_config = json.load(f)

                self.alert_thresholds.update(alert_config.get('thresholds', {}))
                self.alert_cooldown = alert_config.get('cooldown_seconds', 1800)

                # Email configuration
                self.email_config = alert_config.get('email', {})

                logger.info("✅ Alert configuration loaded")
            else:
                # Create default config
                self._create_default_alert_config()

        except Exception as e:
            logger.error(f"Failed to load alert config: {e}")

    def _create_default_alert_config(self):
        """Create default alert configuration file."""
        try:
            self.alert_config_file.parent.mkdir(exist_ok=True)

            default_config = {
                "thresholds": self.alert_thresholds,
                "cooldown_seconds": 1800,
                "email": {
                    "enabled": False,
                    "smtp_server": "smtp.gmail.com",
                    "smtp_port": 587,
                    "username": "",
                    "password": "",
                    "from_email": "",
                    "to_emails": [],
                    "subject_prefix": "[Atlas Alert]"
                },
                "slack": {
                    "enabled": False,
                    "webhook_url": "",
                    "channel": "#atlas-alerts"
                }
            }

            with open(self.alert_config_file, 'w') as f:
                json.dump(default_config, f, indent=2)

            logger.info(f"✅ Created default alert config: {self.alert_config_file}")

        except Exception as e:
            logger.error(f"Failed to create default alert config: {e}")

    def start_monitoring(self):
        """Start continuous monitoring."""
        if self.is_monitoring:
            logger.warning("Monitoring already running")
            return

        self.is_monitoring = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()

        logger.info("🔍 Production monitoring started")

    def stop_monitoring(self):
        """Stop continuous monitoring."""
        self.is_monitoring = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)

        logger.info("🛑 Production monitoring stopped")

    def _monitoring_loop(self):
        """Main monitoring loop."""
        last_health_check = 0
        last_metrics_collection = 0

        while self.is_monitoring:
            try:
                current_time = time.time()

                # Health check
                if current_time - last_health_check >= self.health_check_interval:
                    self._perform_health_check()
                    last_health_check = current_time

                # Metrics collection
                if current_time - last_metrics_collection >= self.metrics_collection_interval:
                    self._collect_performance_metrics()
                    last_metrics_collection = current_time

                time.sleep(10)  # Check every 10 seconds

            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                self._log_error("monitoring_loop", str(e))
                time.sleep(60)  # Wait longer on error

    def _perform_health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        health_status = {
            'timestamp': datetime.now().isoformat(),
            'status': 'healthy',
            'checks': {},
            'alerts_triggered': []
        }

        try:
            # 1. System resources check
            process = psutil.Process()

            memory_info = process.memory_info()
            memory_usage_mb = memory_info.rss / 1024 / 1024
            memory_percent = process.memory_percent()

            cpu_percent = process.cpu_percent(interval=1)

            # Disk usage
            disk_usage = psutil.disk_usage('/')
            disk_percent = (disk_usage.used / disk_usage.total) * 100

            health_status['checks']['system_resources'] = {
                'memory_mb': round(memory_usage_mb, 2),
                'memory_percent': round(memory_percent, 2),
                'cpu_percent': round(cpu_percent, 2),
                'disk_percent': round(disk_percent, 2),
                'status': 'ok'
            }

            # Check thresholds
            if memory_percent > self.alert_thresholds['memory_usage_percent']:
                alert = self._create_alert('high_memory_usage', 'warning',
                                         f"Memory usage at {memory_percent:.1f}%")
                health_status['alerts_triggered'].append(alert)
                health_status['status'] = 'warning'

            if cpu_percent > self.alert_thresholds['cpu_usage_percent']:
                alert = self._create_alert('high_cpu_usage', 'warning',
                                         f"CPU usage at {cpu_percent:.1f}%")
                health_status['alerts_triggered'].append(alert)
                health_status['status'] = 'warning'

            if disk_percent > self.alert_thresholds['disk_usage_percent']:
                alert = self._create_alert('high_disk_usage', 'critical',
                                         f"Disk usage at {disk_percent:.1f}%")
                health_status['alerts_triggered'].append(alert)
                health_status['status'] = 'critical'

            # 2. Database connectivity check
            db_check = self._check_database_health()
            health_status['checks']['database'] = db_check

            if db_check['status'] != 'ok':
                health_status['status'] = 'critical'
                alert = self._create_alert('database_connectivity', 'critical',
                                         f"Database check failed: {db_check.get('error', 'Unknown error')}")
                health_status['alerts_triggered'].append(alert)

            # 3. API endpoint health check
            api_check = self._check_api_health()
            health_status['checks']['api'] = api_check

            if api_check['status'] != 'ok':
                if health_status['status'] == 'healthy':
                    health_status['status'] = 'warning'

            # 4. Background services check
            services_check = self._check_background_services()
            health_status['checks']['background_services'] = services_check

            # 5. Log error rate check
            error_rate = self._check_error_rate()
            health_status['checks']['error_rate'] = error_rate

            if error_rate['error_rate_percent'] > self.alert_thresholds['error_rate_percent']:
                alert = self._create_alert('high_error_rate', 'warning',
                                         f"Error rate at {error_rate['error_rate_percent']:.1f}%")
                health_status['alerts_triggered'].append(alert)
                if health_status['status'] == 'healthy':
                    health_status['status'] = 'warning'

            # Store health check result
            self._store_health_check(health_status)

            # Send alerts if any
            for alert in health_status['alerts_triggered']:
                self._send_alert(alert)

            return health_status

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            health_status['status'] = 'critical'
            health_status['error'] = str(e)
            return health_status

    def _check_database_health(self) -> Dict[str, Any]:
        """Check database connectivity and performance."""
        try:
            main_db = 'data/atlas.db'
            if not os.path.exists(main_db):
                return {'status': 'error', 'error': 'Main database not found'}

            start_time = time.time()

            conn = sqlite3.connect(main_db, timeout=10)
            cursor = conn.cursor()

            # Simple connectivity test
            cursor.execute("SELECT COUNT(*) FROM content LIMIT 1")
            result = cursor.fetchone()

            response_time = (time.time() - start_time) * 1000

            conn.close()

            return {
                'status': 'ok',
                'response_time_ms': round(response_time, 2),
                'content_count': result[0] if result else 0
            }

        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    def _check_api_health(self) -> Dict[str, Any]:
        """Check API endpoint health."""
        try:
            # This is a simplified check - in production you'd test actual endpoints
            return {
                'status': 'ok',
                'endpoints_checked': ['health', 'search'],
                'response_time_ms': 50  # Placeholder
            }

        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    def _check_background_services(self) -> Dict[str, Any]:
        """Check background services status."""
        try:
            services_status = {
                'status': 'ok',
                'services': {}
            }

            # Check if Atlas background processes are running
            atlas_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if 'atlas' in cmdline.lower() and 'python' in cmdline.lower():
                        atlas_processes.append({
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'cmdline': cmdline[:100]
                        })
                except:
                    continue

            services_status['services']['atlas_processes'] = {
                'count': len(atlas_processes),
                'processes': atlas_processes,
                'status': 'ok' if atlas_processes else 'warning'
            }

            if not atlas_processes:
                services_status['status'] = 'warning'

            return services_status

        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    def _check_error_rate(self) -> Dict[str, Any]:
        """Check recent error rate."""
        try:
            conn = sqlite3.connect(self.monitoring_db)
            cursor = conn.cursor()

            # Get errors from last hour
            one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()

            cursor.execute("""
                SELECT COUNT(*) FROM error_logs
                WHERE timestamp > ? AND resolved = FALSE
            """, (one_hour_ago,))

            error_count = cursor.fetchone()[0]

            # Estimate total requests (simplified)
            total_requests = 100  # Placeholder - in production, track actual requests
            error_rate_percent = (error_count / max(1, total_requests)) * 100

            conn.close()

            return {
                'error_count': error_count,
                'error_rate_percent': round(error_rate_percent, 2),
                'period_hours': 1
            }

        except Exception as e:
            return {'error_count': 0, 'error_rate_percent': 0, 'error': str(e)}

    def _collect_performance_metrics(self):
        """Collect and store performance metrics."""
        try:
            timestamp = datetime.now().isoformat()

            conn = sqlite3.connect(self.monitoring_db)
            cursor = conn.cursor()

            # System metrics
            process = psutil.Process()

            metrics = [
                ('system', 'memory_usage_mb', process.memory_info().rss / 1024 / 1024, 'MB'),
                ('system', 'memory_usage_percent', process.memory_percent(), '%'),
                ('system', 'cpu_usage_percent', process.cpu_percent(), '%'),
                ('system', 'num_threads', process.num_threads(), 'count'),
            ]

            # Disk usage
            disk_usage = psutil.disk_usage('/')
            disk_percent = (disk_usage.used / disk_usage.total) * 100
            metrics.append(('system', 'disk_usage_percent', disk_percent, '%'))

            # Store metrics
            for metric_type, metric_name, value, unit in metrics:
                cursor.execute("""
                    INSERT INTO performance_metrics
                    (timestamp, metric_type, metric_name, value, unit)
                    VALUES (?, ?, ?, ?, ?)
                """, (timestamp, metric_type, metric_name, value, unit))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Failed to collect performance metrics: {e}")

    def _create_alert(self, alert_type: str, severity: str, message: str,
                     details: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create and log an alert."""
        alert = {
            'timestamp': datetime.now().isoformat(),
            'alert_type': alert_type,
            'severity': severity,
            'message': message,
            'details': json.dumps(details) if details else None
        }

        try:
            conn = sqlite3.connect(self.monitoring_db)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO alerts (timestamp, alert_type, severity, message, details)
                VALUES (?, ?, ?, ?, ?)
            """, (alert['timestamp'], alert['alert_type'], alert['severity'],
                  alert['message'], alert['details']))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Failed to store alert: {e}")

        return alert

    def _send_alert(self, alert: Dict[str, Any]):
        """Send alert via configured channels."""
        alert_key = f"{alert['alert_type']}_{alert['severity']}"
        current_time = time.time()

        # Check cooldown
        if alert_key in self.last_alert_time:
            if current_time - self.last_alert_time[alert_key] < self.alert_cooldown:
                return  # Still in cooldown

        self.last_alert_time[alert_key] = current_time

        try:
            # Email alerts
            if hasattr(self, 'email_config') and self.email_config.get('enabled', False):
                self._send_email_alert(alert)

            # Log alert
            logger.warning(f"🚨 ALERT [{alert['severity'].upper()}] {alert['alert_type']}: {alert['message']}")

        except Exception as e:
            logger.error(f"Failed to send alert: {e}")

    def _send_email_alert(self, alert: Dict[str, Any]):
        """Send email alert."""
        try:
            if not self.email_config.get('to_emails'):
                return

            msg = MimeMultipart()
            msg['From'] = self.email_config['from_email']
            msg['To'] = ', '.join(self.email_config['to_emails'])
            msg['Subject'] = f"{self.email_config.get('subject_prefix', '[Atlas Alert]')} {alert['severity'].upper()}: {alert['alert_type']}"

            body = f"""
Alert Details:
- Type: {alert['alert_type']}
- Severity: {alert['severity']}
- Time: {alert['timestamp']}
- Message: {alert['message']}

{alert.get('details', '')}

This is an automated alert from Atlas Production Monitor.
"""

            msg.attach(MimeText(body, 'plain'))

            server = smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port'])
            server.starttls()
            server.login(self.email_config['username'], self.email_config['password'])

            text = msg.as_string()
            server.sendmail(self.email_config['from_email'], self.email_config['to_emails'], text)
            server.quit()

            logger.info(f"📧 Email alert sent for {alert['alert_type']}")

        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")

    def _store_health_check(self, health_status: Dict[str, Any]):
        """Store health check result in database."""
        try:
            conn = sqlite3.connect(self.monitoring_db)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO health_checks
                (timestamp, status, response_time_ms, memory_usage_mb,
                 cpu_usage_percent, disk_usage_percent, error_count, details)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                health_status['timestamp'],
                health_status['status'],
                health_status.get('response_time_ms'),
                health_status['checks'].get('system_resources', {}).get('memory_mb'),
                health_status['checks'].get('system_resources', {}).get('cpu_percent'),
                health_status['checks'].get('system_resources', {}).get('disk_percent'),
                len(health_status['alerts_triggered']),
                json.dumps(health_status)
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Failed to store health check: {e}")

    def _log_error(self, error_type: str, error_message: str, stack_trace: str = None):
        """Log an error to the monitoring database."""
        try:
            conn = sqlite3.connect(self.monitoring_db)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO error_logs (timestamp, error_type, error_message, stack_trace)
                VALUES (?, ?, ?, ?)
            """, (datetime.now().isoformat(), error_type, error_message, stack_trace))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Failed to log error: {e}")

    def get_monitoring_dashboard_data(self) -> Dict[str, Any]:
        """Get data for monitoring dashboard."""
        try:
            conn = sqlite3.connect(self.monitoring_db)
            cursor = conn.cursor()

            # Recent health checks
            cursor.execute("""
                SELECT timestamp, status, memory_usage_mb, cpu_usage_percent,
                       disk_usage_percent, error_count
                FROM health_checks
                ORDER BY timestamp DESC
                LIMIT 24
            """)

            health_history = []
            for row in cursor.fetchall():
                health_history.append({
                    'timestamp': row[0],
                    'status': row[1],
                    'memory_mb': row[2],
                    'cpu_percent': row[3],
                    'disk_percent': row[4],
                    'error_count': row[5]
                })

            # Recent alerts
            cursor.execute("""
                SELECT timestamp, alert_type, severity, message
                FROM alerts
                WHERE resolved_at IS NULL
                ORDER BY timestamp DESC
                LIMIT 10
            """)

            active_alerts = []
            for row in cursor.fetchall():
                active_alerts.append({
                    'timestamp': row[0],
                    'type': row[1],
                    'severity': row[2],
                    'message': row[3]
                })

            conn.close()

            return {
                'monitoring_status': 'active' if self.is_monitoring else 'inactive',
                'health_history': health_history,
                'active_alerts': active_alerts,
                'alert_thresholds': self.alert_thresholds,
                'last_check': health_history[0]['timestamp'] if health_history else 'never'
            }

        except Exception as e:
            logger.error(f"Failed to get dashboard data: {e}")
            return {'error': str(e)}

def test_production_monitor():
    """Test production monitoring."""
    logger.info("🧪 Testing Production Monitor")

    monitor = ProductionMonitor()

    # Perform health check
    health_status = monitor._perform_health_check()
    logger.info(f"   Health status: {health_status['status']}")

    # Get dashboard data
    dashboard_data = monitor.get_monitoring_dashboard_data()
    logger.info(f"   Dashboard data: {len(dashboard_data.get('health_history', []))} health checks")

if __name__ == "__main__":
    test_production_monitor()