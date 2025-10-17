"""
Atlas Alerting Service
Comprehensive alerting system with webhooks, email, and Slack integration.
"""

import asyncio
import smtplib
import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from pathlib import Path

from helpers.metrics_collector import get_metrics_collector
from helpers.logging_config import get_logger


@dataclass
class Alert:
    """Alert definition."""
    id: str
    name: str
    severity: str  # critical, warning, info
    condition: str
    description: str
    metric_name: str
    threshold: float
    operator: str  # gt, lt, eq
    duration: int  # seconds
    cooldown: int  # seconds between alerts
    enabled: bool = True
    channels: List[str] = None
    last_triggered: Optional[float] = None

    def __post_init__(self):
        if self.channels is None:
            self.channels = ["log"]


@dataclass
class AlertInstance:
    """Active alert instance."""
    alert_id: str
    triggered_at: float
    resolved_at: Optional[float] = None
    current_value: float = 0.0
    status: str = "active"  # active, resolved
    notifications_sent: List[str] = None

    def __post_init__(self):
        if self.notifications_sent is None:
            self.notifications_sent = []


class AlertingService:
    """Comprehensive alerting service."""

    def __init__(self, config_path: str = "config/alerting.yaml"):
        self.logger = get_logger("alerting")
        self.config_path = Path(config_path)
        self.alerts: Dict[str, Alert] = {}
        self.active_alerts: Dict[str, AlertInstance] = {}
        self.alert_history: List[Dict[str, Any]] = []
        self._running = False
        self._check_interval = 30  # seconds
        self._last_check = 0

        # Notification channels
        self.channels = {
            "log": self._log_notification,
            "webhook": self._webhook_notification,
            "email": self._email_notification,
            "slack": self._slack_notification,
        }

        # Load configuration
        self.load_config()

    def load_config(self):
        """Load alerting configuration."""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    config = json.load(f)

                # Load alerts
                alerts_config = config.get('alerts', [])
                for alert_config in alerts_config:
                    alert = Alert(**alert_config)
                    self.alerts[alert.id] = alert

                # Load notification settings
                self.notification_config = config.get('notifications', {})

                self.logger.info(f"Loaded {len(self.alerts)} alert configurations")
            else:
                self.logger.info("No alerting config found, using default alerts")
                self._create_default_alerts()

        except Exception as e:
            self.logger.error(f"Failed to load alerting config: {e}")
            self._create_default_alerts()

    def _create_default_alerts(self):
        """Create default alert configurations."""
        default_alerts = [
            Alert(
                id="high_queue_depth",
                name="High Queue Depth",
                severity="warning",
                condition="queue_depth > 500",
                description="Queue depth is above threshold",
                metric_name="atlas_queue_pending_total",
                threshold=500,
                operator="gt",
                duration=300,
                cooldown=900,
                channels=["log", "webhook"]
            ),
            Alert(
                id="critical_queue_depth",
                name="Critical Queue Depth",
                severity="critical",
                condition="queue_depth > 1000",
                description="Queue depth is critically high",
                metric_name="atlas_queue_pending_total",
                threshold=1000,
                operator="gt",
                duration=60,
                cooldown=300,
                channels=["log", "webhook", "email"]
            ),
            Alert(
                id="processing_stalled",
                name="Processing Stalled",
                severity="critical",
                condition="transcription_rate == 0",
                description="Transcription processing has stalled",
                metric_name="atlas_transcription_rate",
                threshold=0,
                operator="eq",
                duration=1200,
                cooldown=1800,
                channels=["log", "webhook", "email"]
            ),
            Alert(
                id="high_memory_usage",
                name="High Memory Usage",
                severity="warning",
                condition="memory_usage > 80",
                description="Memory usage is above 80%",
                metric_name="atlas_memory_usage_bytes",
                threshold=80,
                operator="gt",
                duration=300,
                cooldown=1800,
                channels=["log"]
            ),
            Alert(
                id="circuit_breaker_open",
                name="Circuit Breaker Open",
                severity="warning",
                condition="circuit_breaker_open == 1",
                description="Circuit breaker is open",
                metric_name="atlas_circuit_breaker_open",
                threshold=1,
                operator="eq",
                duration=60,
                cooldown=300,
                channels=["log", "webhook"]
            ),
        ]

        for alert in default_alerts:
            self.alerts[alert.id] = alert

    def start_alerting(self):
        """Start the alerting service."""
        if self._running:
            return

        self._running = True
        asyncio.create_task(self._alerting_loop())
        self.logger.info("Alerting service started")

    def stop_alerting(self):
        """Stop the alerting service."""
        self._running = False
        self.logger.info("Alerting service stopped")

    async def _alerting_loop(self):
        """Main alerting loop."""
        while self._running:
            try:
                current_time = time.time()

                if current_time - self._last_check >= self._check_interval:
                    await self._check_all_alerts()
                    self._last_check = current_time

                await asyncio.sleep(self._check_interval)

            except Exception as e:
                self.logger.error(f"Error in alerting loop: {e}")
                await asyncio.sleep(60)

    async def _check_all_alerts(self):
        """Check all alert conditions."""
        metrics_collector = get_metrics_collector()

        for alert in self.alerts.values():
            if not alert.enabled:
                continue

            try:
                await self._check_alert(metrics_collector, alert)
            except Exception as e:
                self.logger.error(f"Error checking alert {alert.id}: {e}")

    async def _check_alert(self, metrics_collector, alert: Alert):
        """Check a specific alert condition."""
        # Get metric value
        metric_value = metrics_collector.get_metric_value(alert.metric_name)

        if metric_value is None:
            return

        # Check if condition is met
        condition_met = self._evaluate_condition(metric_value, alert)

        if condition_met:
            await self._trigger_alert(alert, metric_value)
        else:
            await self._resolve_alert(alert, metric_value)

    def _evaluate_condition(self, value: float, alert: Alert) -> bool:
        """Evaluate alert condition."""
        if alert.operator == "gt":
            return value > alert.threshold
        elif alert.operator == "lt":
            return value < alert.threshold
        elif alert.operator == "eq":
            return value == alert.threshold
        elif alert.operator == "gte":
            return value >= alert.threshold
        elif alert.operator == "lte":
            return value <= alert.threshold
        else:
            return False

    async def _trigger_alert(self, alert: Alert, current_value: float):
        """Trigger an alert."""
        current_time = time.time()

        # Check cooldown
        if (alert.last_triggered and
            current_time - alert.last_triggered < alert.cooldown):
            return

        # Check if already active
        if alert.id in self.active_alerts:
            return

        # Create alert instance
        alert_instance = AlertInstance(
            alert_id=alert.id,
            triggered_at=current_time,
            current_value=current_value
        )

        self.active_alerts[alert.id] = alert_instance
        alert.last_triggered = current_time

        # Send notifications
        await self._send_notifications(alert, alert_instance)

        # Log to history
        self._log_alert_to_history(alert, alert_instance, "triggered")

        self.logger.warning(
            f"Alert triggered: {alert.name} (current: {current_value}, threshold: {alert.threshold})",
            alert_id=alert.id,
            severity=alert.severity,
            current_value=current_value,
            threshold=alert.threshold
        )

    async def _resolve_alert(self, alert: Alert, current_value: float):
        """Resolve an alert."""
        if alert.id not in self.active_alerts:
            return

        alert_instance = self.active_alerts[alert.id]
        alert_instance.resolved_at = time.time()
        alert_instance.status = "resolved"
        alert_instance.current_value = current_value

        # Remove from active alerts
        del self.active_alerts[alert.id]

        # Log to history
        self._log_alert_to_history(alert, alert_instance, "resolved")

        self.logger.info(
            f"Alert resolved: {alert.name} (current: {current_value})",
            alert_id=alert.id,
            severity=alert.severity,
            current_value=current_value
        )

    async def _send_notifications(self, alert: Alert, alert_instance: AlertInstance):
        """Send notifications for an alert."""
        for channel in alert.channels:
            try:
                notification_func = self.channels.get(channel)
                if notification_func:
                    await notification_func(alert, alert_instance)
                    alert_instance.notifications_sent.append(channel)
            except Exception as e:
                self.logger.error(f"Failed to send {channel} notification for alert {alert.id}: {e}")

    async def _log_notification(self, alert: Alert, alert_instance: AlertInstance):
        """Log notification (always available)."""
        self.logger.warning(
            f"ALERT: {alert.name} - {alert.description}",
            alert_id=alert.id,
            severity=alert.severity,
            current_value=alert_instance.current_value,
            threshold=alert.threshold,
            triggered_at=datetime.fromtimestamp(alert_instance.triggered_at).isoformat()
        )

    async def _webhook_notification(self, alert: Alert, alert_instance: AlertInstance):
        """Send webhook notification."""
        webhook_url = self.notification_config.get("webhook_url")
        if not webhook_url:
            return

        payload = {
            "alert_id": alert.id,
            "alert_name": alert.name,
            "severity": alert.severity,
            "description": alert.description,
            "current_value": alert_instance.current_value,
            "threshold": alert.threshold,
            "triggered_at": alert_instance.triggered_at,
            "timestamp": datetime.utcnow().isoformat()
        }

        try:
            response = requests.post(
                webhook_url,
                json=payload,
                timeout=30,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            self.logger.info(f"Webhook notification sent for alert {alert.id}")
        except Exception as e:
            self.logger.error(f"Failed to send webhook notification: {e}")

    async def _email_notification(self, alert: Alert, alert_instance: AlertInstance):
        """Send email notification."""
        email_config = self.notification_config.get("email", {})
        if not email_config:
            return

        smtp_server = email_config.get("smtp_server")
        smtp_port = email_config.get("smtp_port", 587)
        username = email_config.get("username")
        password = email_config.get("password")
        recipients = email_config.get("recipients", [])

        if not all([smtp_server, username, password, recipients]):
            return

        # Create message
        msg = MIMEMultipart()
        msg['From'] = username
        msg['To'] = ', '.join(recipients)
        msg['Subject'] = f"[ALERT] {alert.name} - {alert.severity.upper()}"

        body = f"""
Alert Details:
- Name: {alert.name}
- Severity: {alert.severity.upper()}
- Description: {alert.description}
- Current Value: {alert_instance.current_value}
- Threshold: {alert.threshold}
- Triggered At: {datetime.fromtimestamp(alert_instance.triggered_at)}

Please check your Atlas system immediately.
        """

        msg.attach(MIMEText(body, 'plain'))

        try:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(username, password)
                server.send_message(msg)

            self.logger.info(f"Email notification sent for alert {alert.id}")
        except Exception as e:
            self.logger.error(f"Failed to send email notification: {e}")

    async def _slack_notification(self, alert: Alert, alert_instance: AlertInstance):
        """Send Slack notification."""
        slack_config = self.notification_config.get("slack", {})
        webhook_url = slack_config.get("webhook_url")
        if not webhook_url:
            return

        # Determine color based on severity
        colors = {
            "critical": "#ff0000",
            "warning": "#ffaa00",
            "info": "#36a64f"
        }

        payload = {
            "attachments": [
                {
                    "color": colors.get(alert.severity, "#36a64f"),
                    "title": f"🚨 {alert.name}",
                    "text": alert.description,
                    "fields": [
                        {
                            "title": "Severity",
                            "value": alert.severity.upper(),
                            "short": True
                        },
                        {
                            "title": "Current Value",
                            "value": str(alert_instance.current_value),
                            "short": True
                        },
                        {
                            "title": "Threshold",
                            "value": str(alert.threshold),
                            "short": True
                        },
                        {
                            "title": "Triggered At",
                            "value": datetime.fromtimestamp(alert_instance.triggered_at).strftime("%Y-%m-%d %H:%M:%S"),
                            "short": False
                        }
                    ],
                    "footer": "Atlas Alerting System",
                    "ts": int(alert_instance.triggered_at)
                }
            ]
        }

        try:
            response = requests.post(
                webhook_url,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            self.logger.info(f"Slack notification sent for alert {alert.id}")
        except Exception as e:
            self.logger.error(f"Failed to send Slack notification: {e}")

    def _log_alert_to_history(self, alert: Alert, alert_instance: AlertInstance, action: str):
        """Log alert to history."""
        history_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "alert_id": alert.id,
            "alert_name": alert.name,
            "severity": alert.severity,
            "action": action,
            "current_value": alert_instance.current_value,
            "triggered_at": alert_instance.triggered_at,
            "resolved_at": alert_instance.resolved_at,
            "notifications_sent": alert_instance.notifications_sent
        }

        self.alert_history.append(history_entry)

        # Keep only last 1000 entries
        if len(self.alert_history) > 1000:
            self.alert_history = self.alert_history[-1000:]

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get currently active alerts."""
        return [
            {
                "alert_id": instance.alert_id,
                "alert": self.alerts[instance.alert_id],
                "triggered_at": instance.triggered_at,
                "current_value": instance.current_value,
                "duration": time.time() - instance.triggered_at,
                "notifications_sent": instance.notifications_sent
            }
            for instance in self.active_alerts.values()
        ]

    def get_alert_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get alert history."""
        return self.alert_history[-limit:]

    def add_alert(self, alert: Alert):
        """Add a new alert."""
        self.alerts[alert.id] = alert
        self.logger.info(f"Added new alert: {alert.name}")

    def remove_alert(self, alert_id: str):
        """Remove an alert."""
        if alert_id in self.alerts:
            del self.alerts[alert_id]
            # Also resolve if active
            if alert_id in self.active_alerts:
                del self.active_alerts[alert_id]
            self.logger.info(f"Removed alert: {alert_id}")

    def get_alert_status(self) -> Dict[str, Any]:
        """Get overall alerting status."""
        return {
            "total_alerts": len(self.alerts),
            "enabled_alerts": len([a for a in self.alerts.values() if a.enabled]),
            "active_alerts": len(self.active_alerts),
            "alerts_by_severity": {
                severity: len([a for a in self.active_alerts.values()
                              if self.alerts[a.alert_id].severity == severity])
                for severity in ["critical", "warning", "info"]
            },
            "last_check": self._last_check,
            "check_interval": self._check_interval
        }


# Global alerting service instance
_alerting_service = None


def get_alerting_service() -> AlertingService:
    """Get the global alerting service instance."""
    global _alerting_service
    if _alerting_service is None:
        _alerting_service = AlertingService()
    return _alerting_service


def start_alerting():
    """Start global alerting service."""
    service = get_alerting_service()
    service.start_alerting()


def stop_alerting():
    """Stop global alerting service."""
    service = get_alerting_service()
    service.stop_alerting()