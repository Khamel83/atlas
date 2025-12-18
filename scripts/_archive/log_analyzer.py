#!/usr/bin/env python3
"""
Atlas Log Analyzer
Automated log analysis with pattern detection, anomaly detection, and alerting.
"""

import os
import sys
import json
import re
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
import hashlib

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.logging_config import get_logger
from scripts.notify import AtlasNotificationSystem

@dataclass
class ErrorPattern:
    """Detected error pattern."""
    pattern_id: str
    pattern_text: str
    count: int
    first_seen: datetime
    last_seen: datetime
    severity: str
    components: List[str]
    sample_messages: List[str]

@dataclass
class AnomalyAlert:
    """Anomaly detection alert."""
    alert_type: str
    component: str
    description: str
    severity: str
    threshold: float
    current_value: float
    historical_average: float
    timestamp: datetime

class LogAnalyzer:
    """Automated log analysis and pattern detection system."""

    def __init__(self):
        self.logger = get_logger("log_analyzer")

        # Use same log directory logic as logging_config
        try:
            self.log_dir = Path("/var/log/atlas")
            self.log_dir.mkdir(exist_ok=True, parents=True)
        except PermissionError:
            self.log_dir = Path("logs") / "atlas"
            self.log_dir.mkdir(exist_ok=True, parents=True)

        self.analysis_db_path = self.log_dir / "log_analysis.db"
        self.notifier = AtlasNotificationSystem()

        # Pattern detection configuration
        self.error_patterns = [
            r"connection.*(?:refused|timeout|failed)",
            r"out of memory|memory.*exhausted",
            r"disk.*full|no space left",
            r"permission denied|access denied",
            r"database.*(?:locked|corrupt|busy)",
            r"timeout.*exceeded|request.*timeout",
            r"failed to.*start|startup.*failed",
            r"critical.*error|fatal.*error",
            r"deadlock|race condition",
            r"overflow|buffer.*overflow"
        ]

        # Anomaly detection thresholds
        self.anomaly_thresholds = {
            "error_rate": {"warning": 5, "critical": 20},  # errors per minute
            "memory_growth": {"warning": 50, "critical": 100},  # MB per hour
            "cpu_spike": {"warning": 80, "critical": 95},  # percent
            "queue_backlog": {"warning": 100, "critical": 500}  # pending items
        }

        self.setup_analysis_database()

    def setup_analysis_database(self):
        """Setup database for storing analysis results."""
        try:
            self.log_dir.mkdir(exist_ok=True, parents=True)

            conn = sqlite3.connect(self.analysis_db_path)
            cursor = conn.cursor()

            # Error patterns table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS error_patterns (
                    pattern_id TEXT PRIMARY KEY,
                    pattern_text TEXT NOT NULL,
                    regex_pattern TEXT NOT NULL,
                    count INTEGER DEFAULT 0,
                    first_seen DATETIME,
                    last_seen DATETIME,
                    severity TEXT DEFAULT 'medium',
                    components TEXT,
                    sample_messages TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Anomalies table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS anomalies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_type TEXT NOT NULL,
                    component TEXT NOT NULL,
                    description TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    threshold_value REAL,
                    current_value REAL,
                    historical_average REAL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    resolved BOOLEAN DEFAULT FALSE
                )
            """)

            # Create indexes separately
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_anomalies_timestamp ON anomalies(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_anomalies_component ON anomalies(component)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_anomalies_severity ON anomalies(severity)")

            # Performance metrics history
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS performance_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    component TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_perf_history ON performance_history(component, metric_name, timestamp)")

            # Alert suppression
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alert_suppression (
                    pattern_id TEXT PRIMARY KEY,
                    suppressed_until DATETIME,
                    reason TEXT
                )
            """)

            conn.commit()
            conn.close()

        except Exception as e:
            self.logger.error(f"Failed to setup analysis database: {e}")

    def analyze_error_patterns(self, hours_back: int = 24) -> List[ErrorPattern]:
        """Analyze logs for error patterns."""
        try:
            patterns_found = []

            # Read JSON log files
            for log_file in self.log_dir.glob("*.json.log"):
                with open(log_file, 'r') as f:
                    for line in f:
                        try:
                            log_data = json.loads(line.strip())

                            # Skip if too old
                            log_time = datetime.fromisoformat(log_data.get('timestamp', ''))
                            if log_time < datetime.now() - timedelta(hours=hours_back):
                                continue

                            # Only analyze error and critical logs
                            if log_data.get('level') not in ['ERROR', 'CRITICAL']:
                                continue

                            message = log_data.get('message', '').lower()
                            component = log_data.get('component', 'unknown')

                            # Check against known patterns
                            for pattern in self.error_patterns:
                                if re.search(pattern, message, re.IGNORECASE):
                                    pattern_id = hashlib.md5(pattern.encode()).hexdigest()[:8]

                                    # Store or update pattern
                                    self._store_error_pattern(
                                        pattern_id, pattern, message, component, log_time
                                    )

                        except (json.JSONDecodeError, ValueError):
                            continue

            # Retrieve stored patterns
            patterns_found = self._get_stored_patterns(hours_back)

            # Alert on critical patterns
            for pattern in patterns_found:
                if pattern.severity == 'critical' and pattern.count >= 5:
                    self._send_pattern_alert(pattern)

            return patterns_found

        except Exception as e:
            self.logger.error(f"Failed to analyze error patterns: {e}")
            return []

    def _store_error_pattern(self, pattern_id: str, regex_pattern: str,
                           message: str, component: str, timestamp: datetime):
        """Store or update error pattern in database."""
        try:
            conn = sqlite3.connect(self.analysis_db_path)
            cursor = conn.cursor()

            # Check if pattern exists
            cursor.execute("SELECT count, components, sample_messages FROM error_patterns WHERE pattern_id = ?",
                         (pattern_id,))
            result = cursor.fetchone()

            if result:
                # Update existing pattern
                count, components_json, samples_json = result

                components = json.loads(components_json) if components_json else []
                if component not in components:
                    components.append(component)

                samples = json.loads(samples_json) if samples_json else []
                if message not in samples and len(samples) < 5:
                    samples.append(message)

                cursor.execute("""
                    UPDATE error_patterns
                    SET count = count + 1, last_seen = ?, components = ?, sample_messages = ?
                    WHERE pattern_id = ?
                """, (timestamp.isoformat(), json.dumps(components), json.dumps(samples), pattern_id))
            else:
                # Insert new pattern
                severity = self._determine_pattern_severity(regex_pattern, message)

                cursor.execute("""
                    INSERT INTO error_patterns
                    (pattern_id, pattern_text, regex_pattern, count, first_seen, last_seen,
                     severity, components, sample_messages)
                    VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?)
                """, (pattern_id, message[:100], regex_pattern, timestamp.isoformat(),
                     timestamp.isoformat(), severity, json.dumps([component]),
                     json.dumps([message])))

            conn.commit()
            conn.close()

        except Exception as e:
            self.logger.error(f"Failed to store error pattern: {e}")

    def _determine_pattern_severity(self, pattern: str, message: str) -> str:
        """Determine severity of error pattern."""
        critical_keywords = ['critical', 'fatal', 'crash', 'memory', 'disk full', 'corruption']
        high_keywords = ['failed', 'error', 'exception', 'timeout']

        message_lower = message.lower()

        if any(keyword in message_lower for keyword in critical_keywords):
            return 'critical'
        elif any(keyword in message_lower for keyword in high_keywords):
            return 'high'
        else:
            return 'medium'

    def _get_stored_patterns(self, hours_back: int) -> List[ErrorPattern]:
        """Retrieve stored error patterns."""
        try:
            conn = sqlite3.connect(self.analysis_db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT pattern_id, pattern_text, count, first_seen, last_seen,
                       severity, components, sample_messages
                FROM error_patterns
                WHERE last_seen >= datetime('now', '-{} hours')
                ORDER BY count DESC, severity DESC
            """.format(hours_back))

            patterns = []
            for row in cursor.fetchall():
                pattern_id, pattern_text, count, first_seen, last_seen, severity, components_json, samples_json = row

                components = json.loads(components_json) if components_json else []
                samples = json.loads(samples_json) if samples_json else []

                patterns.append(ErrorPattern(
                    pattern_id=pattern_id,
                    pattern_text=pattern_text,
                    count=count,
                    first_seen=datetime.fromisoformat(first_seen),
                    last_seen=datetime.fromisoformat(last_seen),
                    severity=severity,
                    components=components,
                    sample_messages=samples
                ))

            conn.close()
            return patterns

        except Exception as e:
            self.logger.error(f"Failed to get stored patterns: {e}")
            return []

    def detect_anomalies(self, hours_back: int = 24) -> List[AnomalyAlert]:
        """Detect performance and behavior anomalies."""
        try:
            anomalies = []

            # Analyze error rate spikes
            anomalies.extend(self._detect_error_rate_anomalies(hours_back))

            # Analyze memory growth patterns
            anomalies.extend(self._detect_memory_anomalies(hours_back))

            # Analyze CPU usage spikes
            anomalies.extend(self._detect_cpu_anomalies(hours_back))

            # Analyze queue backlog growth
            anomalies.extend(self._detect_queue_anomalies(hours_back))

            # Store anomalies and send alerts
            for anomaly in anomalies:
                self._store_anomaly(anomaly)
                if anomaly.severity in ['critical', 'high']:
                    self._send_anomaly_alert(anomaly)

            return anomalies

        except Exception as e:
            self.logger.error(f"Failed to detect anomalies: {e}")
            return []

    def _detect_error_rate_anomalies(self, hours_back: int) -> List[AnomalyAlert]:
        """Detect error rate anomalies."""
        try:
            anomalies = []

            # Count errors per hour for recent period
            from web.log_dashboard import get_log_dashboard
            dashboard = get_log_dashboard()

            conn = sqlite3.connect(dashboard.log_db_path)
            cursor = conn.cursor()

            # Get error counts per hour
            cursor.execute("""
                SELECT
                    strftime('%Y-%m-%d %H', timestamp) as hour,
                    component,
                    COUNT(*) as error_count
                FROM log_entries
                WHERE level IN ('ERROR', 'CRITICAL')
                AND timestamp >= datetime('now', '-{} hours')
                GROUP BY hour, component
                HAVING error_count > 5
                ORDER BY error_count DESC
            """.format(hours_back))

            for row in cursor.fetchall():
                hour, component, error_count = row

                # Check against thresholds
                if error_count >= self.anomaly_thresholds["error_rate"]["critical"]:
                    severity = "critical"
                elif error_count >= self.anomaly_thresholds["error_rate"]["warning"]:
                    severity = "high"
                else:
                    continue

                anomalies.append(AnomalyAlert(
                    alert_type="error_rate_spike",
                    component=component,
                    description=f"High error rate detected: {error_count} errors in hour {hour}",
                    severity=severity,
                    threshold=float(self.anomaly_thresholds["error_rate"]["warning"]),
                    current_value=float(error_count),
                    historical_average=0.0,  # Would calculate from historical data
                    timestamp=datetime.now()
                ))

            conn.close()
            return anomalies

        except Exception as e:
            self.logger.error(f"Failed to detect error rate anomalies: {e}")
            return []

    def _detect_memory_anomalies(self, hours_back: int) -> List[AnomalyAlert]:
        """Detect memory usage anomalies."""
        try:
            # This would analyze memory usage trends from performance logs
            # Implementation depends on having performance metrics in logs
            return []
        except Exception as e:
            self.logger.error(f"Failed to detect memory anomalies: {e}")
            return []

    def _detect_cpu_anomalies(self, hours_back: int) -> List[AnomalyAlert]:
        """Detect CPU usage anomalies."""
        try:
            # This would analyze CPU usage patterns from performance logs
            # Implementation depends on having performance metrics in logs
            return []
        except Exception as e:
            self.logger.error(f"Failed to detect CPU anomalies: {e}")
            return []

    def _detect_queue_anomalies(self, hours_back: int) -> List[AnomalyAlert]:
        """Detect queue backlog anomalies."""
        try:
            # This would analyze queue depth trends from performance logs
            # Implementation depends on having queue metrics in logs
            return []
        except Exception as e:
            self.logger.error(f"Failed to detect queue anomalies: {e}")
            return []

    def _store_anomaly(self, anomaly: AnomalyAlert):
        """Store anomaly in database."""
        try:
            conn = sqlite3.connect(self.analysis_db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO anomalies
                (alert_type, component, description, severity, threshold_value,
                 current_value, historical_average, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                anomaly.alert_type, anomaly.component, anomaly.description,
                anomaly.severity, anomaly.threshold, anomaly.current_value,
                anomaly.historical_average, anomaly.timestamp.isoformat()
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            self.logger.error(f"Failed to store anomaly: {e}")

    def _send_pattern_alert(self, pattern: ErrorPattern):
        """Send alert for critical error pattern."""
        try:
            # Check if this pattern is suppressed
            if self._is_pattern_suppressed(pattern.pattern_id):
                return

            alert_message = f"""
🚨 CRITICAL ERROR PATTERN DETECTED

Pattern: {pattern.pattern_text}
Occurrences: {pattern.count} times
Components: {', '.join(pattern.components)}
Severity: {pattern.severity}
First seen: {pattern.first_seen.strftime('%Y-%m-%d %H:%M')}
Last seen: {pattern.last_seen.strftime('%Y-%m-%d %H:%M')}

Sample messages:
{chr(10).join('• ' + msg[:100] for msg in pattern.sample_messages[:3])}

This pattern requires immediate attention.
            """.strip()

            self.notifier.send_alert(
                title="Critical Error Pattern Detected",
                message=alert_message,
                severity="critical"
            )

            # Suppress this pattern for 1 hour to avoid spam
            self._suppress_pattern(pattern.pattern_id, hours=1)

        except Exception as e:
            self.logger.error(f"Failed to send pattern alert: {e}")

    def _send_anomaly_alert(self, anomaly: AnomalyAlert):
        """Send alert for detected anomaly."""
        try:
            alert_message = f"""
⚠️ SYSTEM ANOMALY DETECTED

Type: {anomaly.alert_type}
Component: {anomaly.component}
Severity: {anomaly.severity}

{anomaly.description}

Current value: {anomaly.current_value}
Threshold: {anomaly.threshold}
Historical average: {anomaly.historical_average}

Time: {anomaly.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
            """.strip()

            self.notifier.send_alert(
                title=f"System Anomaly: {anomaly.alert_type}",
                message=alert_message,
                severity=anomaly.severity
            )

        except Exception as e:
            self.logger.error(f"Failed to send anomaly alert: {e}")

    def _is_pattern_suppressed(self, pattern_id: str) -> bool:
        """Check if pattern alerts are suppressed."""
        try:
            conn = sqlite3.connect(self.analysis_db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT suppressed_until FROM alert_suppression
                WHERE pattern_id = ? AND suppressed_until > datetime('now')
            """, (pattern_id,))

            result = cursor.fetchone()
            conn.close()

            return result is not None

        except Exception:
            return False

    def _suppress_pattern(self, pattern_id: str, hours: int = 1):
        """Suppress alerts for a pattern."""
        try:
            conn = sqlite3.connect(self.analysis_db_path)
            cursor = conn.cursor()

            suppressed_until = datetime.now() + timedelta(hours=hours)

            cursor.execute("""
                INSERT OR REPLACE INTO alert_suppression (pattern_id, suppressed_until, reason)
                VALUES (?, ?, ?)
            """, (pattern_id, suppressed_until.isoformat(), f"Auto-suppressed for {hours} hour(s)"))

            conn.commit()
            conn.close()

        except Exception as e:
            self.logger.error(f"Failed to suppress pattern: {e}")

    def generate_analysis_report(self, hours_back: int = 24) -> Dict[str, Any]:
        """Generate comprehensive analysis report."""
        try:
            patterns = self.analyze_error_patterns(hours_back)
            anomalies = self.detect_anomalies(hours_back)

            # Categorize patterns by severity
            critical_patterns = [p for p in patterns if p.severity == 'critical']
            high_patterns = [p for p in patterns if p.severity == 'high']
            medium_patterns = [p for p in patterns if p.severity == 'medium']

            # Component error breakdown
            component_errors = defaultdict(int)
            for pattern in patterns:
                for component in pattern.components:
                    component_errors[component] += pattern.count

            report = {
                "analysis_period": f"{hours_back} hours",
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "total_patterns": len(patterns),
                    "critical_patterns": len(critical_patterns),
                    "high_patterns": len(high_patterns),
                    "medium_patterns": len(medium_patterns),
                    "total_anomalies": len(anomalies),
                    "most_affected_component": max(component_errors.items(), key=lambda x: x[1])[0] if component_errors else "none"
                },
                "critical_patterns": [asdict(p) for p in critical_patterns],
                "top_error_components": dict(sorted(component_errors.items(), key=lambda x: x[1], reverse=True)[:10]),
                "recent_anomalies": [asdict(a) for a in anomalies],
                "recommendations": self._generate_recommendations(patterns, anomalies)
            }

            return report

        except Exception as e:
            self.logger.error(f"Failed to generate analysis report: {e}")
            return {"error": str(e)}

    def _generate_recommendations(self, patterns: List[ErrorPattern],
                                anomalies: List[AnomalyAlert]) -> List[str]:
        """Generate actionable recommendations based on analysis."""
        recommendations = []

        # Pattern-based recommendations
        if any(p.severity == 'critical' for p in patterns):
            recommendations.append("URGENT: Critical error patterns detected. Review system logs immediately.")

        connection_patterns = [p for p in patterns if 'connection' in p.pattern_text.lower()]
        if connection_patterns:
            recommendations.append("Network connectivity issues detected. Check network configuration and dependencies.")

        memory_patterns = [p for p in patterns if 'memory' in p.pattern_text.lower()]
        if memory_patterns:
            recommendations.append("Memory-related issues detected. Consider increasing system memory or optimizing memory usage.")

        disk_patterns = [p for p in patterns if 'disk' in p.pattern_text.lower() or 'space' in p.pattern_text.lower()]
        if disk_patterns:
            recommendations.append("Disk space issues detected. Implement log rotation and cleanup procedures.")

        # Anomaly-based recommendations
        if any(a.alert_type == 'error_rate_spike' for a in anomalies):
            recommendations.append("Error rate spikes detected. Investigate recent changes and implement circuit breakers.")

        if not recommendations:
            recommendations.append("No critical issues detected. Continue monitoring system health.")

        return recommendations

def run_continuous_analysis(interval_minutes: int = 30):
    """Run continuous log analysis."""
    import time

    analyzer = LogAnalyzer()
    logger = get_logger("log_analyzer_daemon")

    logger.info(f"Starting continuous log analysis (interval: {interval_minutes} minutes)")

    while True:
        try:
            logger.info("Running log analysis cycle...")

            # Run analysis
            patterns = analyzer.analyze_error_patterns(hours_back=1)  # Analyze last hour
            anomalies = analyzer.detect_anomalies(hours_back=1)

            if patterns or anomalies:
                logger.info(f"Analysis complete: {len(patterns)} patterns, {len(anomalies)} anomalies")

            # Wait for next cycle
            time.sleep(interval_minutes * 60)

        except KeyboardInterrupt:
            logger.info("Stopping continuous analysis...")
            break
        except Exception as e:
            logger.error(f"Error in analysis cycle: {e}")
            time.sleep(60)  # Wait 1 minute before retrying

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Atlas Log Analyzer")
    parser.add_argument("--analyze", action="store_true", help="Run one-time analysis")
    parser.add_argument("--continuous", action="store_true", help="Run continuous analysis")
    parser.add_argument("--interval", type=int, default=30, help="Analysis interval in minutes")
    parser.add_argument("--hours", type=int, default=24, help="Hours of logs to analyze")
    parser.add_argument("--report", action="store_true", help="Generate analysis report")
    parser.add_argument("--patterns", action="store_true", help="Show error patterns only")
    parser.add_argument("--anomalies", action="store_true", help="Show anomalies only")

    args = parser.parse_args()

    analyzer = LogAnalyzer()

    if args.continuous:
        run_continuous_analysis(args.interval)

    elif args.analyze or args.patterns:
        patterns = analyzer.analyze_error_patterns(args.hours)
        print(f"Found {len(patterns)} error patterns in last {args.hours} hours:")

        for pattern in patterns:
            print(f"\n[{pattern.severity.upper()}] {pattern.pattern_text}")
            print(f"  Count: {pattern.count}")
            print(f"  Components: {', '.join(pattern.components)}")
            print(f"  Last seen: {pattern.last_seen.strftime('%Y-%m-%d %H:%M')}")

    elif args.anomalies:
        anomalies = analyzer.detect_anomalies(args.hours)
        print(f"Found {len(anomalies)} anomalies in last {args.hours} hours:")

        for anomaly in anomalies:
            print(f"\n[{anomaly.severity.upper()}] {anomaly.alert_type}")
            print(f"  Component: {anomaly.component}")
            print(f"  Description: {anomaly.description}")
            print(f"  Current: {anomaly.current_value}, Threshold: {anomaly.threshold}")

    elif args.report:
        report = analyzer.generate_analysis_report(args.hours)
        print(json.dumps(report, indent=2, default=str))

    else:
        print("Use --help to see available options")