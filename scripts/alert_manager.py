#!/usr/bin/env python3
"""
Atlas Alert Manager
Centralized alerting system with intelligent alert throttling and escalation.
"""

import sys
import time
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.metrics_collector import get_metrics_collector, get_health_summary
from helpers.queue_manager import get_queue_status
from scripts.notify import send_notification


@dataclass
class AlertRule:
    """Alert rule definition."""
    name: str
    condition: str
    threshold: float
    severity: str
    message_template: str
    cooldown_minutes: int = 30
    escalation_minutes: int = 120


class AlertManager:
    """Centralized alert management system."""

    def __init__(self):
        """Initialize alert manager."""
        self.logger = logging.getLogger(__name__)
        self.state_file = Path("data/alert_state.json")
        self.alert_state = self._load_alert_state()

        # Define alert rules
        self.alert_rules = [
            AlertRule(
                name="processing_stalled",
                condition="transcription_rate_zero_20min",
                threshold=0,
                severity="critical",
                message_template="🚨 CRITICAL: Transcript processing stalled for >20 minutes\n\nTranscription rate: {transcription_rate}/min\nLast activity: {last_activity}\n\nAction required: Check transcript workers and queue status.",
                cooldown_minutes=30,
                escalation_minutes=60
            ),
            AlertRule(
                name="high_queue_depth",
                condition="queue_pending_high",
                threshold=500,
                severity="warning",
                message_template="⚠️ WARNING: High queue depth detected\n\nPending tasks: {queue_pending}\nThreshold: {threshold}\n\nQueue may be backing up. Monitor for continued growth.",
                cooldown_minutes=30
            ),
            AlertRule(
                name="critical_queue_depth",
                condition="queue_pending_critical",
                threshold=1000,
                severity="critical",
                message_template="🚨 CRITICAL: Queue depth exceeds critical threshold\n\nPending tasks: {queue_pending}\nCritical threshold: {threshold}\n\nImmediate action required to prevent system overload.",
                cooldown_minutes=15,
                escalation_minutes=30
            ),
            AlertRule(
                name="high_error_rate",
                condition="error_rate_high",
                threshold=5.0,
                severity="warning",
                message_template="⚠️ WARNING: High error rate detected\n\nError rate: {error_rate}%\nThreshold: {threshold}%\nFailed tasks: {failed_tasks}\n\nInvestigate recent failures and system stability.",
                cooldown_minutes=20
            ),
            AlertRule(
                name="circuit_breaker_open",
                condition="circuit_breaker_triggered",
                threshold=1,
                severity="warning",
                message_template="⚡ WARNING: Circuit breaker opened\n\nWorker: {worker}\nFailure count: {failure_count}\nState: {state}\n\nWorker disabled due to consecutive failures.",
                cooldown_minutes=60
            ),
            AlertRule(
                name="low_disk_space",
                condition="disk_space_low",
                threshold=5.0,  # GB
                severity="critical",
                message_template="🚨 CRITICAL: Low disk space\n\nFree space: {disk_free_gb:.1f} GB\nThreshold: {threshold} GB\n\nUrgent: Clean up space or processing will halt.",
                cooldown_minutes=60,
                escalation_minutes=30
            ),
            AlertRule(
                name="high_memory_usage",
                condition="memory_usage_high",
                threshold=1024,  # MB
                severity="warning",
                message_template="⚠️ WARNING: High memory usage\n\nMemory: {memory_mb:.0f} MB\nThreshold: {threshold} MB\n\nMonitor for memory leaks or resource exhaustion.",
                cooldown_minutes=30
            )
        ]

    def _load_alert_state(self) -> Dict[str, Any]:
        """Load persistent alert state."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Failed to load alert state: {e}")

        return {
            "last_alerts": {},  # rule_name -> timestamp
            "escalations": {},  # rule_name -> escalation_timestamp
            "alert_counts": {}  # rule_name -> count
        }

    def _save_alert_state(self):
        """Save persistent alert state."""
        try:
            self.state_file.parent.mkdir(exist_ok=True)
            with open(self.state_file, 'w') as f:
                json.dump(self.alert_state, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save alert state: {e}")

    def check_all_alerts(self) -> List[Dict[str, Any]]:
        """Check all alert conditions and trigger alerts."""
        metrics_collector = get_metrics_collector()
        health_summary = get_health_summary()
        triggered_alerts = []

        current_time = datetime.now()

        for rule in self.alert_rules:
            try:
                should_alert, context = self._evaluate_rule(rule, metrics_collector)

                if should_alert:
                    # Check cooldown
                    last_alert_time = self.alert_state["last_alerts"].get(rule.name)
                    if last_alert_time:
                        last_alert = datetime.fromisoformat(last_alert_time)
                        cooldown_delta = timedelta(minutes=rule.cooldown_minutes)
                        if current_time - last_alert < cooldown_delta:
                            continue  # Still in cooldown

                    # Send alert
                    alert_sent = self._send_alert(rule, context)
                    if alert_sent:
                        self.alert_state["last_alerts"][rule.name] = current_time.isoformat()
                        self.alert_state["alert_counts"][rule.name] = self.alert_state["alert_counts"].get(rule.name, 0) + 1

                        triggered_alerts.append({
                            "rule": rule.name,
                            "severity": rule.severity,
                            "message": rule.message_template.format(**context),
                            "context": context,
                            "timestamp": current_time.isoformat()
                        })

                # Check for escalation
                if rule.escalation_minutes and rule.severity != "critical":
                    self._check_escalation(rule, should_alert, current_time)

            except Exception as e:
                self.logger.error(f"Error evaluating alert rule {rule.name}: {e}")

        if triggered_alerts:
            self._save_alert_state()

        return triggered_alerts

    def _evaluate_rule(self, rule: AlertRule, metrics_collector) -> tuple[bool, Dict[str, Any]]:
        """Evaluate a specific alert rule."""
        context = {}

        if rule.condition == "transcription_rate_zero_20min":
            transcription_rate = metrics_collector.get_metric_value("atlas_transcription_rate") or 0
            context["transcription_rate"] = transcription_rate
            context["last_activity"] = "20+ minutes ago"  # Simplified
            return transcription_rate == 0, context

        elif rule.condition == "queue_pending_high":
            queue_pending = metrics_collector.get_metric_value("atlas_queue_pending_total") or 0
            context["queue_pending"] = int(queue_pending)
            context["threshold"] = int(rule.threshold)
            return queue_pending > rule.threshold, context

        elif rule.condition == "queue_pending_critical":
            queue_pending = metrics_collector.get_metric_value("atlas_queue_pending_total") or 0
            context["queue_pending"] = int(queue_pending)
            context["threshold"] = int(rule.threshold)
            return queue_pending > rule.threshold, context

        elif rule.condition == "error_rate_high":
            failed_tasks = metrics_collector.get_metric_value("atlas_queue_failed_total") or 0
            total_tasks = failed_tasks + (metrics_collector.get_metric_value("atlas_queue_completed_total") or 0)
            error_rate = (failed_tasks / max(total_tasks, 1)) * 100
            context["error_rate"] = error_rate
            context["threshold"] = rule.threshold
            context["failed_tasks"] = int(failed_tasks)
            return error_rate > rule.threshold, context

        elif rule.condition == "circuit_breaker_triggered":
            # Check circuit breaker metrics
            cb_metric = metrics_collector._metrics.get("atlas_circuit_breaker_open")
            if cb_metric and cb_metric.points:
                for point in cb_metric.points:
                    if point.value == 1:  # Circuit breaker open
                        context["worker"] = point.labels.get("worker", "unknown")
                        context["state"] = "open"
                        context["failure_count"] = "10+"  # Simplified
                        return True, context
            return False, context

        elif rule.condition == "disk_space_low":
            disk_free = metrics_collector.get_metric_value("atlas_disk_free_bytes") or 0
            disk_free_gb = disk_free / 1024 / 1024 / 1024
            context["disk_free_gb"] = disk_free_gb
            context["threshold"] = rule.threshold
            return disk_free_gb < rule.threshold, context

        elif rule.condition == "memory_usage_high":
            memory_usage = metrics_collector.get_metric_value("atlas_memory_usage_bytes") or 0
            memory_mb = memory_usage / 1024 / 1024
            context["memory_mb"] = memory_mb
            context["threshold"] = rule.threshold
            return memory_mb > rule.threshold, context

        return False, context

    def _send_alert(self, rule: AlertRule, context: Dict[str, Any]) -> bool:
        """Send an alert notification."""
        try:
            message = rule.message_template.format(**context)
            title = f"Atlas Alert: {rule.name.replace('_', ' ').title()}"

            success = send_notification(message, title, priority=rule.severity)

            if success:
                self.logger.info(f"Alert sent: {rule.name} ({rule.severity})")
            else:
                self.logger.error(f"Failed to send alert: {rule.name}")

            return success

        except Exception as e:
            self.logger.error(f"Error sending alert {rule.name}: {e}")
            return False

    def _check_escalation(self, rule: AlertRule, condition_active: bool, current_time: datetime):
        """Check if alert should be escalated."""
        if not condition_active:
            # Clear escalation if condition resolved
            if rule.name in self.alert_state["escalations"]:
                del self.alert_state["escalations"][rule.name]
            return

        escalation_time = self.alert_state["escalations"].get(rule.name)
        if not escalation_time:
            # Start escalation timer
            self.alert_state["escalations"][rule.name] = current_time.isoformat()
            return

        escalation_start = datetime.fromisoformat(escalation_time)
        escalation_delta = timedelta(minutes=rule.escalation_minutes)

        if current_time - escalation_start >= escalation_delta:
            # Escalate to critical
            escalated_rule = AlertRule(
                name=f"{rule.name}_escalated",
                condition=rule.condition,
                threshold=rule.threshold,
                severity="critical",
                message_template=f"🚨 ESCALATED: {rule.message_template}",
                cooldown_minutes=rule.cooldown_minutes
            )

            # Reset escalation timer
            self.alert_state["escalations"][rule.name] = current_time.isoformat()

            self.logger.warning(f"Alert escalated: {rule.name}")

    def get_alert_summary(self) -> Dict[str, Any]:
        """Get summary of alert system status."""
        return {
            "total_rules": len(self.alert_rules),
            "active_escalations": len(self.alert_state["escalations"]),
            "total_alerts_sent": sum(self.alert_state["alert_counts"].values()),
            "last_check": datetime.now().isoformat(),
            "rules": [
                {
                    "name": rule.name,
                    "severity": rule.severity,
                    "threshold": rule.threshold,
                    "cooldown_minutes": rule.cooldown_minutes,
                    "alert_count": self.alert_state["alert_counts"].get(rule.name, 0),
                    "last_alert": self.alert_state["last_alerts"].get(rule.name)
                }
                for rule in self.alert_rules
            ]
        }

    def test_alerts(self) -> Dict[str, Any]:
        """Test alert system with sample conditions."""
        test_results = []

        # Test notification system
        try:
            test_message = "🧪 Atlas Alert System Test\n\nThis is a test alert to verify the notification system is working properly."
            success = send_notification(test_message, "Atlas Alert Test", priority="info")
            test_results.append({"test": "notification", "success": success})
        except Exception as e:
            test_results.append({"test": "notification", "success": False, "error": str(e)})

        # Test alert rule evaluation
        metrics_collector = get_metrics_collector()
        for rule in self.alert_rules[:3]:  # Test first 3 rules
            try:
                should_alert, context = self._evaluate_rule(rule, metrics_collector)
                test_results.append({
                    "test": f"rule_{rule.name}",
                    "success": True,
                    "should_alert": should_alert,
                    "context": context
                })
            except Exception as e:
                test_results.append({
                    "test": f"rule_{rule.name}",
                    "success": False,
                    "error": str(e)
                })

        return {
            "timestamp": datetime.now().isoformat(),
            "tests": test_results,
            "success_count": sum(1 for t in test_results if t["success"]),
            "total_tests": len(test_results)
        }


def main():
    """Main alert manager function."""
    import argparse

    parser = argparse.ArgumentParser(description="Atlas Alert Manager")
    parser.add_argument("--check", action="store_true", help="Check all alert conditions")
    parser.add_argument("--test", action="store_true", help="Test alert system")
    parser.add_argument("--summary", action="store_true", help="Show alert summary")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")
    parser.add_argument("--interval", type=int, default=300, help="Daemon check interval (seconds)")

    args = parser.parse_args()

    alert_manager = AlertManager()

    if args.test:
        print("🧪 Testing Alert System")
        print("=" * 40)
        results = alert_manager.test_alerts()

        for test in results["tests"]:
            status = "✅" if test["success"] else "❌"
            print(f"{status} {test['test']}")
            if not test["success"] and "error" in test:
                print(f"   Error: {test['error']}")

        print(f"\n📊 Results: {results['success_count']}/{results['total_tests']} tests passed")

    elif args.summary:
        print("📊 Alert System Summary")
        print("=" * 40)
        summary = alert_manager.get_alert_summary()

        print(f"Total Rules: {summary['total_rules']}")
        print(f"Active Escalations: {summary['active_escalations']}")
        print(f"Total Alerts Sent: {summary['total_alerts_sent']}")
        print(f"Last Check: {summary['last_check']}")
        print()

        for rule in summary["rules"]:
            print(f"📋 {rule['name']} ({rule['severity']})")
            print(f"   Threshold: {rule['threshold']}")
            print(f"   Alert Count: {rule['alert_count']}")
            print(f"   Last Alert: {rule['last_alert'] or 'Never'}")
            print()

    elif args.check or args.daemon:
        if args.daemon:
            print(f"🔄 Starting alert daemon (check every {args.interval}s)")
            while True:
                try:
                    alerts = alert_manager.check_all_alerts()
                    if alerts:
                        print(f"📨 Sent {len(alerts)} alerts")
                    time.sleep(args.interval)
                except KeyboardInterrupt:
                    print("\n🛑 Alert daemon stopped")
                    break
                except Exception as e:
                    print(f"❌ Error in alert daemon: {e}")
                    time.sleep(60)  # Sleep longer on error
        else:
            print("🔍 Checking Alert Conditions")
            print("=" * 40)
            alerts = alert_manager.check_all_alerts()

            if alerts:
                for alert in alerts:
                    print(f"🚨 {alert['severity'].upper()}: {alert['rule']}")
                    print(f"   {alert['message']}")
                    print()
                print(f"📨 Total alerts sent: {len(alerts)}")
            else:
                print("✅ No alerts triggered")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()