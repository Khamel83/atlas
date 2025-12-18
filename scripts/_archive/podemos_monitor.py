#!/usr/bin/env python3
"""
PODEMOS Monitor
Real-time monitoring and alerting for the PODEMOS processing pipeline.
"""

import psutil
import time
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path
import requests
import subprocess
import os

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PodmosMonitor:
    """Real-time monitoring system for PODEMOS."""

    def __init__(self, config_file: str = "podemos_monitor_config.json"):
        """Initialize monitor with configuration."""
        self.config = self._load_config(config_file)
        self.alerts_sent = {}  # Track alerts to prevent spam
        self.metrics_history = []

    def _load_config(self, config_file: str) -> Dict:
        """Load monitoring configuration."""
        default_config = {
            "check_interval_seconds": 60,
            "alert_thresholds": {
                "processing_time_minutes": 25,
                "failure_rate_percent": 30,
                "disk_usage_percent": 85,
                "memory_usage_percent": 90,
                "consecutive_failures": 3
            },
            "retention_days": 30,
            "notification_settings": {
                "cooldown_minutes": 60,
                "webhooks": [],
                "email": {
                    "enabled": False,
                    "smtp_server": "",
                    "from_address": "",
                    "to_addresses": []
                }
            },
            "health_checks": {
                "database": True,
                "disk_space": True,
                "memory": True,
                "services": ["podemos"]
            }
        }

        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    user_config = json.load(f)
                default_config.update(user_config)
                logger.info(f"Loaded monitor configuration from {config_file}")
            except Exception as e:
                logger.warning(f"Failed to load monitor config: {e}")
        else:
            with open(config_file, 'w') as f:
                json.dump(default_config, f, indent=2)
            logger.info(f"Created default monitor configuration: {config_file}")

        return default_config

    def collect_metrics(self) -> Dict:
        """Collect system and processing metrics."""
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "system": self._collect_system_metrics(),
            "processing": self._collect_processing_metrics(),
            "storage": self._collect_storage_metrics(),
            "services": self._collect_service_metrics()
        }

        self.metrics_history.append(metrics)

        # Keep only recent history
        cutoff_time = datetime.now() - timedelta(hours=24)
        self.metrics_history = [
            m for m in self.metrics_history
            if datetime.fromisoformat(m['timestamp']) > cutoff_time
        ]

        return metrics

    def _collect_system_metrics(self) -> Dict:
        """Collect system resource metrics."""
        try:
            return {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage_percent": psutil.disk_usage('/').percent,
                "load_average": os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0],
                "uptime_seconds": time.time() - psutil.boot_time()
            }
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
            return {}

    def _collect_processing_metrics(self) -> Dict:
        """Collect PODEMOS processing metrics."""
        try:
            # Connect to PODEMOS database
            conn = sqlite3.connect('podemos.db')
            cursor = conn.cursor()

            # Get recent processing stats
            cursor.execute('''
                SELECT COUNT(*) FROM podemos_episodes
                WHERE discovered_at > datetime('now', '-24 hours')
            ''')
            episodes_24h = cursor.fetchone()[0]

            cursor.execute('''
                SELECT COUNT(*) FROM podemos_episodes
                WHERE processing_status = 'completed'
                AND processed_at > datetime('now', '-24 hours')
            ''')
            completed_24h = cursor.fetchone()[0]

            cursor.execute('''
                SELECT COUNT(*) FROM podemos_episodes
                WHERE processing_status = 'failed'
                AND processed_at > datetime('now', '-24 hours')
            ''')
            failed_24h = cursor.fetchone()[0]

            cursor.execute('''
                SELECT processing_status, COUNT(*)
                FROM podemos_episodes
                GROUP BY processing_status
            ''')
            status_counts = dict(cursor.fetchall())

            conn.close()

            # Calculate metrics
            total_processed = completed_24h + failed_24h
            failure_rate = (failed_24h / total_processed * 100) if total_processed > 0 else 0

            return {
                "episodes_discovered_24h": episodes_24h,
                "episodes_completed_24h": completed_24h,
                "episodes_failed_24h": failed_24h,
                "failure_rate_percent": failure_rate,
                "status_breakdown": status_counts,
                "queue_size": status_counts.get('discovered', 0) + status_counts.get('processing', 0)
            }

        except Exception as e:
            logger.error(f"Failed to collect processing metrics: {e}")
            return {}

    def _collect_storage_metrics(self) -> Dict:
        """Collect storage-related metrics."""
        try:
            metrics = {}

            # Check temp directories
            temp_dirs = ["/tmp/podemos", "/tmp/podemos_audio", "./podemos_output"]
            for temp_dir in temp_dirs:
                if os.path.exists(temp_dir):
                    size = sum(f.stat().st_size for f in Path(temp_dir).rglob('*') if f.is_file())
                    metrics[f"temp_dir_{os.path.basename(temp_dir)}_mb"] = size / 1024 / 1024

            # Check log files
            log_files = ["podemos_scheduler.log", "podemos_monitor.log"]
            for log_file in log_files:
                if os.path.exists(log_file):
                    size = os.path.getsize(log_file) / 1024 / 1024
                    metrics[f"log_file_{log_file}_mb"] = size

            return metrics

        except Exception as e:
            logger.error(f"Failed to collect storage metrics: {e}")
            return {}

    def _collect_service_metrics(self) -> Dict:
        """Collect service status metrics."""
        try:
            metrics = {}

            for service_name in self.config["health_checks"]["services"]:
                try:
                    # Check if process is running
                    result = subprocess.run(
                        ['pgrep', '-f', service_name],
                        capture_output=True,
                        text=True
                    )
                    metrics[f"service_{service_name}_running"] = result.returncode == 0
                except Exception as e:
                    logger.debug(f"Service check failed for {service_name}: {e}")
                    metrics[f"service_{service_name}_running"] = False

            return metrics

        except Exception as e:
            logger.error(f"Failed to collect service metrics: {e}")
            return {}

    def check_alerts(self, metrics: Dict):
        """Check metrics against alert thresholds."""
        alerts = []
        current_time = datetime.now()

        # System alerts
        if metrics.get('system', {}).get('memory_percent', 0) > self.config['alert_thresholds']['memory_usage_percent']:
            alerts.append({
                "type": "memory_high",
                "severity": "warning",
                "message": f"Memory usage high: {metrics['system']['memory_percent']:.1f}%",
                "value": metrics['system']['memory_percent']
            })

        if metrics.get('system', {}).get('disk_usage_percent', 0) > self.config['alert_thresholds']['disk_usage_percent']:
            alerts.append({
                "type": "disk_high",
                "severity": "warning",
                "message": f"Disk usage high: {metrics['system']['disk_usage_percent']:.1f}%",
                "value": metrics['system']['disk_usage_percent']
            })

        # Processing alerts
        failure_rate = metrics.get('processing', {}).get('failure_rate_percent', 0)
        if failure_rate > self.config['alert_thresholds']['failure_rate_percent']:
            alerts.append({
                "type": "failure_rate_high",
                "severity": "error",
                "message": f"Processing failure rate high: {failure_rate:.1f}%",
                "value": failure_rate
            })

        # Service alerts
        for service_name in self.config["health_checks"]["services"]:
            service_key = f"service_{service_name}_running"
            if not metrics.get('services', {}).get(service_key, True):
                alerts.append({
                    "type": "service_down",
                    "severity": "error",
                    "message": f"Service not running: {service_name}",
                    "service": service_name
                })

        # Send alerts (with cooldown)
        for alert in alerts:
            self._send_alert_if_needed(alert, current_time)

    def _send_alert_if_needed(self, alert: Dict, current_time: datetime):
        """Send alert if cooldown period has passed."""
        alert_key = f"{alert['type']}_{alert.get('service', '')}"
        cooldown_minutes = self.config['notification_settings']['cooldown_minutes']

        # Check cooldown
        if alert_key in self.alerts_sent:
            last_sent = self.alerts_sent[alert_key]
            if (current_time - last_sent).total_seconds() < cooldown_minutes * 60:
                return  # Still in cooldown

        # Send alert
        try:
            self._send_alert_notification(alert)
            self.alerts_sent[alert_key] = current_time
            logger.warning(f"Alert sent: {alert['message']}")
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")

    def _send_alert_notification(self, alert: Dict):
        """Send alert notification via configured channels."""
        notification = {
            "title": f"🚨 PODEMOS Alert: {alert['type']}",
            "message": alert['message'],
            "severity": alert['severity'],
            "timestamp": datetime.now().isoformat()
        }

        # Send to webhooks
        for webhook_url in self.config['notification_settings']['webhooks']:
            try:
                response = requests.post(webhook_url, json=notification, timeout=10)
                response.raise_for_status()
            except Exception as e:
                logger.warning(f"Failed to send webhook alert: {e}")

    def generate_health_report(self) -> Dict:
        """Generate comprehensive health report."""
        current_metrics = self.collect_metrics()

        # Calculate trends from recent history
        recent_metrics = [m for m in self.metrics_history[-24:]]  # Last 24 data points

        trends = {}
        if len(recent_metrics) >= 2:
            # Calculate memory trend
            memory_values = [m.get('system', {}).get('memory_percent', 0) for m in recent_metrics]
            memory_trend = (memory_values[-1] - memory_values[0]) / len(memory_values) if memory_values else 0
            trends['memory_trend_per_hour'] = memory_trend

            # Calculate processing trend
            completed_values = [m.get('processing', {}).get('episodes_completed_24h', 0) for m in recent_metrics]
            avg_completed = sum(completed_values) / len(completed_values) if completed_values else 0
            trends['avg_episodes_completed_24h'] = avg_completed

        report = {
            "generated_at": datetime.now().isoformat(),
            "current_metrics": current_metrics,
            "trends": trends,
            "health_status": self._calculate_health_status(current_metrics),
            "recommendations": self._generate_recommendations(current_metrics)
        }

        return report

    def _calculate_health_status(self, metrics: Dict) -> str:
        """Calculate overall health status."""
        issues = 0

        # Check critical thresholds
        if metrics.get('system', {}).get('memory_percent', 0) > 95:
            issues += 2
        elif metrics.get('system', {}).get('memory_percent', 0) > 85:
            issues += 1

        if metrics.get('system', {}).get('disk_usage_percent', 0) > 90:
            issues += 2
        elif metrics.get('system', {}).get('disk_usage_percent', 0) > 80:
            issues += 1

        if metrics.get('processing', {}).get('failure_rate_percent', 0) > 50:
            issues += 2
        elif metrics.get('processing', {}).get('failure_rate_percent', 0) > 20:
            issues += 1

        # Check services
        for service_name in self.config["health_checks"]["services"]:
            service_key = f"service_{service_name}_running"
            if not metrics.get('services', {}).get(service_key, True):
                issues += 2

        if issues >= 4:
            return "critical"
        elif issues >= 2:
            return "warning"
        elif issues >= 1:
            return "degraded"
        else:
            return "healthy"

    def _generate_recommendations(self, metrics: Dict) -> List[str]:
        """Generate recommendations based on current metrics."""
        recommendations = []

        memory_percent = metrics.get('system', {}).get('memory_percent', 0)
        if memory_percent > 85:
            recommendations.append("Consider increasing system memory or optimizing processing concurrency")

        disk_percent = metrics.get('system', {}).get('disk_usage_percent', 0)
        if disk_percent > 80:
            recommendations.append("Clean up temporary files and old logs to free disk space")

        failure_rate = metrics.get('processing', {}).get('failure_rate_percent', 0)
        if failure_rate > 20:
            recommendations.append("Investigate processing failures and consider adjusting retry logic")

        queue_size = metrics.get('processing', {}).get('queue_size', 0)
        if queue_size > 50:
            recommendations.append("Processing queue is large - consider increasing processing capacity")

        return recommendations

    def cleanup_old_data(self):
        """Clean up old monitoring data and files."""
        try:
            retention_days = self.config['retention_days']
            cutoff_date = datetime.now() - timedelta(days=retention_days)

            # Clean up old report files
            for report_file in Path('.').glob('podemos_report_*.json'):
                if report_file.stat().st_mtime < cutoff_date.timestamp():
                    report_file.unlink()
                    logger.info(f"Cleaned up old report: {report_file}")

            # Clean up old temp files
            temp_dirs = ["/tmp/podemos", "/tmp/podemos_audio"]
            for temp_dir in temp_dirs:
                if os.path.exists(temp_dir):
                    for temp_file in Path(temp_dir).rglob('*'):
                        if temp_file.is_file() and temp_file.stat().st_mtime < cutoff_date.timestamp():
                            temp_file.unlink()

            logger.info("Cleanup completed")

        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")

    def start_monitoring(self):
        """Start continuous monitoring loop."""
        logger.info("🔍 Starting PODEMOS monitoring service...")

        check_interval = self.config['check_interval_seconds']
        logger.info(f"Monitoring interval: {check_interval} seconds")

        try:
            while True:
                try:
                    # Collect metrics and check alerts
                    metrics = self.collect_metrics()
                    self.check_alerts(metrics)

                    # Periodic cleanup (once per day)
                    if datetime.now().hour == 3 and datetime.now().minute < 5:
                        self.cleanup_old_data()

                    time.sleep(check_interval)

                except Exception as e:
                    logger.error(f"Monitoring cycle error: {e}")
                    time.sleep(60)  # Wait longer on error

        except KeyboardInterrupt:
            logger.info("🛑 Monitoring stopped by user")

def main():
    """Main entry point for PODEMOS monitor."""
    import argparse

    parser = argparse.ArgumentParser(description="PODEMOS Processing Monitor")
    parser.add_argument('--daemon', action='store_true', help='Run as monitoring daemon')
    parser.add_argument('--report', action='store_true', help='Generate health report')
    parser.add_argument('--metrics', action='store_true', help='Show current metrics')
    parser.add_argument('--cleanup', action='store_true', help='Clean up old data')
    args = parser.parse_args()

    monitor = PodmosMonitor()

    if args.report:
        report = monitor.generate_health_report()
        print(json.dumps(report, indent=2))

    elif args.metrics:
        metrics = monitor.collect_metrics()
        print(json.dumps(metrics, indent=2))

    elif args.cleanup:
        monitor.cleanup_old_data()

    elif args.daemon:
        monitor.start_monitoring()

    else:
        print("PODEMOS Processing Monitor")
        print("Usage:")
        print("  --daemon     Run as monitoring daemon")
        print("  --report     Generate health report")
        print("  --metrics    Show current metrics")
        print("  --cleanup    Clean up old data")

if __name__ == "__main__":
    main()