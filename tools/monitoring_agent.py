#!/usr/bin/env python3
"""
Atlas Monitoring Agent

Continuous monitoring and alerting agent for Atlas systems.
Provides real-time monitoring, alerting, and automated responses.
"""

import os
import sys
import json
import time
import signal
import smtplib
import requests
import psutil
import logging
from pathlib import Path
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from threading import Thread, Event

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.configuration_manager import ConfigurationManager, Environment
from helpers.secret_manager import SecretManager


@dataclass
class Metric:
    """System metric."""
    name: str
    value: float
    timestamp: datetime
    unit: str
    tags: Dict[str, str]


@dataclass
class Alert:
    """Alert information."""
    id: str
    severity: str  # "critical", "warning", "info"
    title: str
    description: str
    timestamp: datetime
    source: str
    resolved: bool = False
    resolved_at: Optional[datetime] = None


@dataclass
class HealthCheck:
    """Health check definition."""
    name: str
    check_func: Callable[[], bool]
    interval: int
    timeout: int
    critical: bool = True


class MonitoringAgent:
    """Main monitoring agent class."""

    def __init__(self, config_dir: str = "config", secrets_dir: str = "config"):
        """Initialize monitoring agent."""
        self.config_dir = Path(config_dir)
        self.secrets_dir = Path(secrets_dir)
        self.environment = os.getenv("ATLAS_ENVIRONMENT", "development")
        self.running = False
        self.shutdown_event = Event()

        # Initialize managers
        self.config_manager = ConfigurationManager(
            environment=Environment(self.environment),
            config_dir=str(config_dir),
            secrets_dir=str(secrets_dir)
        )
        self.secret_manager = SecretManager(
            secrets_dir=str(secrets_dir),
            environment=self.environment
        )

        # Monitoring configuration
        self.config = self._load_monitoring_config()

        # Storage for metrics and alerts
        self.metrics: List[Metric] = []
        self.alerts: List[Alert] = []
        self.health_checks: Dict[str, HealthCheck] = {}

        # Setup logging
        self._setup_logging()

        # Initialize monitoring components
        self._initialize_health_checks()
        self._initialize_alert_rules()

    def _load_monitoring_config(self) -> Dict[str, Any]:
        """Load monitoring configuration."""
        # Get monitoring configuration from config manager
        config = {
            "collection_interval": self.config_manager.get("MONITORING_INTERVAL", 60),
            "metrics_retention_hours": self.config_manager.get("METRICS_RETENTION_HOURS", 24),
            "alerting_enabled": self.config_manager.get("ALERTING_ENABLED", True),
            "email_alerts": self.config_manager.get("EMAIL_ALERTS_ENABLED", False),
            "webhook_url": self.config_manager.get("WEBHOOK_URL"),
            "slack_webhook": self.config_manager.get("SLACK_WEBHOOK_URL"),
            "thresholds": {
                "cpu_warning": 80.0,
                "cpu_critical": 95.0,
                "memory_warning": 80.0,
                "memory_critical": 95.0,
                "disk_warning": 85.0,
                "disk_critical": 95.0,
                "response_time_warning": 5.0,
                "response_time_critical": 10.0
            }
        }
        return config

    def _setup_logging(self):
        """Setup logging configuration."""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "monitoring_agent.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def _initialize_health_checks(self):
        """Initialize health checks."""
        # API health check
        self.health_checks["api"] = HealthCheck(
            name="api",
            check_func=self._check_api_health,
            interval=30,
            timeout=10,
            critical=True
        )

        # Database health check
        self.health_checks["database"] = HealthCheck(
            name="database",
            check_func=self._check_database_health,
            interval=60,
            timeout=30,
            critical=True
        )

        # Disk space check
        self.health_checks["disk"] = HealthCheck(
            name="disk",
            check_func=self._check_disk_space,
            interval=300,
            timeout=10,
            critical=True
        )

        # Memory check
        self.health_checks["memory"] = HealthCheck(
            name="memory",
            check_func=self._check_memory,
            interval=60,
            timeout=10,
            critical=False
        )

        # Services check
        self.health_checks["services"] = HealthCheck(
            name="services",
            check_func=self._check_services,
            interval=60,
            timeout=30,
            critical=True
        )

    def _initialize_alert_rules(self):
        """Initialize alert rules."""
        self.alert_rules = {
            "high_cpu": {
                "condition": lambda metrics: metrics.get("cpu_percent", 0) > self.config["thresholds"]["cpu_critical"],
                "severity": "critical",
                "message": "High CPU usage detected",
                "cooldown": 300  # 5 minutes
            },
            "high_memory": {
                "condition": lambda metrics: metrics.get("memory_percent", 0) > self.config["thresholds"]["memory_critical"],
                "severity": "critical",
                "message": "High memory usage detected",
                "cooldown": 300
            },
            "high_disk": {
                "condition": lambda metrics: metrics.get("disk_percent", 0) > self.config["thresholds"]["disk_critical"],
                "severity": "critical",
                "message": "High disk usage detected",
                "cooldown": 600  # 10 minutes
            },
            "api_down": {
                "condition": lambda checks: not checks.get("api", {}).get("healthy", False),
                "severity": "critical",
                "message": "API service is down",
                "cooldown": 60
            },
            "database_down": {
                "condition": lambda checks: not checks.get("database", {}).get("healthy", False),
                "severity": "critical",
                "message": "Database service is down",
                "cooldown": 60
            }
        }

        # Track alert cooldowns
        self.alert_cooldowns: Dict[str, datetime] = {}

    def _check_api_health(self) -> bool:
        """Check API health."""
        try:
            response = requests.get(
                "http://localhost:7444/health",
                timeout=10
            )
            return response.status_code == 200
        except Exception:
            return False

    def _check_database_health(self) -> bool:
        """Check database health."""
        try:
            import sqlite3

            db_path = self.config_manager.get("ATLAS_DATABASE_PATH")
            if not db_path or not Path(db_path).exists():
                return False

            conn = sqlite3.connect(db_path, timeout=10)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM content")
            cursor.fetchone()
            conn.close()
            return True
        except Exception:
            return False

    def _check_disk_space(self) -> bool:
        """Check disk space."""
        try:
            disk_usage = psutil.disk_usage('/')
            percent_used = (disk_usage.used / disk_usage.total) * 100
            return percent_used < self.config["thresholds"]["disk_critical"]
        except Exception:
            return False

    def _check_memory(self) -> bool:
        """Check memory usage."""
        try:
            memory = psutil.virtual_memory()
            return memory.percent < self.config["thresholds"]["memory_critical"]
        except Exception:
            return False

    def _check_services(self) -> bool:
        """Check if required services are running."""
        required_services = ["atlas-api", "atlas-scheduler"]
        for service in required_services:
            try:
                result = subprocess.run(
                    ["systemctl", "is-active", service],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode != 0:
                    return False
            except Exception:
                return False
        return True

    def collect_metrics(self):
        """Collect system metrics."""
        # System metrics
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        # Collect base metrics
        metrics_data = {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_available": memory.available,
            "disk_percent": (disk.used / disk.total) * 100,
            "disk_free": disk.free,
            "load_avg_1": psutil.getloadavg()[0],
            "uptime": time.time()
        }

        # Add API metrics if available
        try:
            response = requests.get("http://localhost:7444/metrics", timeout=5)
            if response.status_code == 200:
                api_metrics = response.json()
                metrics_data.update(api_metrics)
        except:
            pass

        # Store metrics
        timestamp = datetime.now()
        for name, value in metrics_data.items():
            if isinstance(value, (int, float)):
                self.metrics.append(Metric(
                    name=name,
                    value=value,
                    timestamp=timestamp,
                    unit="percent" if "percent" in name else "count",
                    tags={"environment": self.environment}
                ))

        # Clean up old metrics
        cutoff_time = datetime.now() - timedelta(hours=self.config["metrics_retention_hours"])
        self.metrics = [m for m in self.metrics if m.timestamp > cutoff_time]

        return metrics_data

    def run_health_checks(self) -> Dict[str, Any]:
        """Run all health checks."""
        results = {}
        current_time = datetime.now()

        for name, health_check in self.health_checks.items():
            # Check if we should run this check
            last_run = getattr(health_check, 'last_run', None)
            if last_run and (current_time - last_run).seconds < health_check.interval:
                continue

            # Run health check
            try:
                health_check.last_run = current_time
                healthy = health_check.check_func()
                results[name] = {
                    "healthy": healthy,
                    "timestamp": current_time.isoformat(),
                    "critical": health_check.critical
                }
            except Exception as e:
                results[name] = {
                    "healthy": False,
                    "error": str(e),
                    "timestamp": current_time.isoformat(),
                    "critical": health_check.critical
                }

        return results

    def evaluate_alerts(self, metrics: Dict[str, Any], health_checks: Dict[str, Any]):
        """Evaluate alert conditions."""
        current_time = datetime.now()

        for rule_name, rule in self.alert_rules.items():
            # Check cooldown
            if rule_name in self.alert_cooldowns:
                if (current_time - self.alert_cooldowns[rule_name]).seconds < rule["cooldown"]:
                    continue

            # Evaluate condition
            try:
                if rule["condition"](metrics) or rule["condition"](health_checks):
                    # Create alert
                    alert_id = f"{rule_name}_{int(current_time.timestamp())}"
                    alert = Alert(
                        id=alert_id,
                        severity=rule["severity"],
                        title=rule["message"],
                        description=f"Alert triggered: {rule['message']} at {current_time.strftime('%Y-%m-%d %H:%M:%S')}",
                        timestamp=current_time,
                        source="monitoring_agent"
                    )

                    self.alerts.append(alert)
                    self.alert_cooldowns[rule_name] = current_time

                    # Send notification
                    self._send_alert_notification(alert)

                    self.logger.warning(f"Alert triggered: {rule['message']}")

            except Exception as e:
                self.logger.error(f"Error evaluating alert rule {rule_name}: {e}")

    def _send_alert_notification(self, alert: Alert):
        """Send alert notification."""
        if not self.config["alerting_enabled"]:
            return

        # Send email notification
        if self.config["email_alerts"]:
            self._send_email_alert(alert)

        # Send webhook notification
        if self.config["webhook_url"]:
            self._send_webhook_alert(alert)

        # Send Slack notification
        if self.config["slack_webhook"]:
            self._send_slack_alert(alert)

    def _send_email_alert(self, alert: Alert):
        """Send email alert notification."""
        try:
            # Get email configuration
            smtp_server = self.config_manager.get("SMTP_SERVER", "smtp.gmail.com")
            smtp_port = self.config_manager.get("SMTP_PORT", 587)
            email_username = self.secret_manager.get_secret("EMAIL_USERNAME")
            email_password = self.secret_manager.get_secret("EMAIL_PASSWORD")
            recipient_emails = self.config_manager.get("ALERT_EMAIL_RECIPIENTS", "").split(",")

            if not email_username or not email_password or not recipient_emails:
                return

            # Create message
            msg = MimeText(f"""
Atlas Alert - {alert.severity.upper()}

{alert.title}

{alert.description}

Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
Environment: {self.environment}
Alert ID: {alert.id}

This is an automated alert from the Atlas monitoring system.
""")

            msg['Subject'] = f"Atlas Alert [{alert.severity.upper()}]: {alert.title}"
            msg['From'] = email_username
            msg['To'] = ', '.join(recipient_emails)

            # Send email
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(email_username, email_password)
            server.send_message(msg)
            server.quit()

            self.logger.info(f"Email alert sent: {alert.title}")

        except Exception as e:
            self.logger.error(f"Failed to send email alert: {e}")

    def _send_webhook_alert(self, alert: Alert):
        """Send webhook alert notification."""
        try:
            payload = {
                "alert_id": alert.id,
                "severity": alert.severity,
                "title": alert.title,
                "description": alert.description,
                "timestamp": alert.timestamp.isoformat(),
                "environment": self.environment,
                "source": "atlas_monitoring"
            }

            response = requests.post(
                self.config["webhook_url"],
                json=payload,
                timeout=10
            )
            response.raise_for_status()

            self.logger.info(f"Webhook alert sent: {alert.title}")

        except Exception as e:
            self.logger.error(f"Failed to send webhook alert: {e}")

    def _send_slack_alert(self, alert: Alert):
        """Send Slack alert notification."""
        try:
            # Determine color based on severity
            colors = {
                "critical": "danger",
                "warning": "warning",
                "info": "good"
            }
            color = colors.get(alert.severity, "warning")

            payload = {
                "attachments": [
                    {
                        "color": color,
                        "title": f"Atlas Alert - {alert.severity.upper()}",
                        "text": alert.title,
                        "fields": [
                            {
                                "title": "Description",
                                "value": alert.description,
                                "short": False
                            },
                            {
                                "title": "Environment",
                                "value": self.environment,
                                "short": True
                            },
                            {
                                "title": "Time",
                                "value": alert.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                                "short": True
                            }
                        ],
                        "footer": "Atlas Monitoring",
                        "ts": int(alert.timestamp.timestamp())
                    }
                ]
            }

            response = requests.post(
                self.config["slack_webhook"],
                json=payload,
                timeout=10
            )
            response.raise_for_status()

            self.logger.info(f"Slack alert sent: {alert.title}")

        except Exception as e:
            self.logger.error(f"Failed to send Slack alert: {e}")

    def start(self):
        """Start the monitoring agent."""
        self.logger.info("Starting Atlas monitoring agent")
        self.running = True

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # Main monitoring loop
        while self.running and not self.shutdown_event.is_set():
            try:
                # Collect metrics
                metrics = self.collect_metrics()

                # Run health checks
                health_checks = self.run_health_checks()

                # Evaluate alerts
                self.evaluate_alerts(metrics, health_checks)

                # Log status
                self.logger.info(f"Monitoring cycle completed - "
                              f"Metrics: {len(metrics)}, "
                              f"Health checks: {len(health_checks)}, "
                              f"Active alerts: {len([a for a in self.alerts if not a.resolved])}")

                # Wait for next collection interval
                self.shutdown_event.wait(self.config["collection_interval"])

            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                self.shutdown_event.wait(5)  # Brief pause before retry

        self.logger.info("Atlas monitoring agent stopped")

    def stop(self):
        """Stop the monitoring agent."""
        self.logger.info("Stopping Atlas monitoring agent")
        self.running = False
        self.shutdown_event.set()

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.stop()

    def get_status(self) -> Dict[str, Any]:
        """Get current monitoring status."""
        return {
            "running": self.running,
            "environment": self.environment,
            "metrics_count": len(self.metrics),
            "alerts_count": len(self.alerts),
            "active_alerts": len([a for a in self.alerts if not a.resolved]),
            "config": self.config,
            "last_collection": self.metrics[-1].timestamp.isoformat() if self.metrics else None,
            "health_checks": {name: check.last_run.isoformat() if hasattr(check, 'last_run') else None
                             for name, check in self.health_checks.items()}
        }

    def get_metrics(self, hours: int = 1) -> List[Dict[str, Any]]:
        """Get recent metrics."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_metrics = [m for m in self.metrics if m.timestamp > cutoff_time]
        return [asdict(m) for m in recent_metrics]

    def get_alerts(self, resolved: Optional[bool] = None) -> List[Dict[str, Any]]:
        """Get alerts."""
        alerts = self.alerts
        if resolved is not None:
            alerts = [a for a in alerts if a.resolved == resolved]
        return [asdict(a) for a in sorted(alerts, key=lambda a: a.timestamp, reverse=True)]

    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert."""
        for alert in self.alerts:
            if alert.id == alert_id and not alert.resolved:
                alert.resolved = True
                alert.resolved_at = datetime.now()
                self.logger.info(f"Alert resolved: {alert.title}")
                return True
        return False


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Atlas Monitoring Agent")
    parser.add_argument("--config-dir", default="config", help="Configuration directory")
    parser.add_argument("--secrets-dir", default="config", help="Secrets directory")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")

    args = parser.parse_args()

    try:
        # Initialize monitoring agent
        agent = MonitoringAgent(args.config_dir, args.secrets_dir)

        if args.daemon:
            # Run as daemon
            agent.start()
        else:
            # Run once and show status
            agent.collect_metrics()
            health_checks = agent.run_health_checks()
            status = agent.get_status()

            print("Atlas Monitoring Agent Status")
            print("=" * 40)
            print(f"Running: {status['running']}")
            print(f"Environment: {status['environment']}")
            print(f"Metrics collected: {status['metrics_count']}")
            print(f"Active alerts: {status['active_alerts']}")
            print(f"Last collection: {status['last_collection']}")

            print("\nHealth Checks:")
            for name, last_run in status['health_checks'].items():
                status_icon = "✅" if health_checks.get(name, {}).get("healthy", False) else "❌"
                print(f"  {status_icon} {name}: {last_run}")

            if status['active_alerts'] > 0:
                print("\nActive Alerts:")
                for alert in agent.get_alerts(resolved=False)[:5]:
                    print(f"  {alert['severity'].upper()}: {alert['title']}")

    except KeyboardInterrupt:
        print("\nMonitoring agent stopped by user")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()