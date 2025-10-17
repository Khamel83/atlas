#!/usr/bin/env python3
"""
Google Search Analytics and Monitoring

Provides comprehensive analytics and monitoring for the Google Search
fallback system including usage patterns, performance metrics, and alerts.
"""

import sqlite3
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import statistics

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from helpers.google_search_queue import GoogleSearchQueue

@dataclass
class SearchAnalytics:
    """Analytics data for Google Search usage"""
    date: str
    searches_performed: int = 0
    successful_searches: int = 0
    failed_searches: int = 0
    quota_used: int = 0
    avg_response_time: float = 0.0
    top_queries: List[Tuple[str, int]] = None
    success_rate: float = 0.0
    quota_utilization: float = 0.0

class GoogleSearchMonitor:
    """Comprehensive monitoring for Google Search fallback system"""

    def __init__(self, queue: GoogleSearchQueue = None):
        self.queue = queue or GoogleSearchQueue()
        self.daily_quota = 8000  # 80% of 10k limit

    def get_current_status(self) -> Dict:
        """Get current system status and metrics"""
        queue_status = self.queue.get_queue_status()
        daily_used = self.queue._get_daily_usage()

        # Calculate utilization and remaining
        quota_utilization = (daily_used / self.daily_quota) * 100
        remaining_searches = max(0, self.daily_quota - daily_used)

        # Get time until quota reset
        now = datetime.utcnow()
        tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        hours_until_reset = (tomorrow - now).total_seconds() / 3600

        # Determine alert level
        alert_level = self._get_alert_level(quota_utilization, hours_until_reset)

        return {
            "timestamp": datetime.now().isoformat(),
            "quota": {
                "daily_limit": self.daily_quota,
                "used_today": daily_used,
                "remaining": remaining_searches,
                "utilization_percent": quota_utilization,
                "hours_until_reset": hours_until_reset
            },
            "queue": queue_status,
            "alert_level": alert_level,
            "system_health": self._assess_system_health(queue_status, quota_utilization)
        }

    def get_historical_analytics(self, days: int = 30) -> List[SearchAnalytics]:
        """Get historical analytics for the specified number of days"""
        analytics = []

        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days-1)

        with sqlite3.connect(self.queue.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Get daily stats
            cursor = conn.execute("""
                SELECT * FROM search_stats
                WHERE date BETWEEN ? AND ?
                ORDER BY date
            """, (start_date.isoformat(), end_date.isoformat()))

            for row in cursor.fetchall():
                data = dict(row)

                # Calculate derived metrics
                total_searches = data['searches_performed']
                successful = data['successful_searches']

                success_rate = (successful / total_searches * 100) if total_searches > 0 else 0
                quota_utilization = (data['quota_used'] / self.daily_quota * 100)

                # Get top queries for this date
                top_queries = self._get_top_queries_for_date(conn, data['date'])

                analytics.append(SearchAnalytics(
                    date=data['date'],
                    searches_performed=total_searches,
                    successful_searches=successful,
                    failed_searches=data['failed_searches'],
                    quota_used=data['quota_used'],
                    success_rate=success_rate,
                    quota_utilization=quota_utilization,
                    top_queries=top_queries
                ))

        return analytics

    def _get_top_queries_for_date(self, conn, date: str, limit: int = 5) -> List[Tuple[str, int]]:
        """Get top search queries for a specific date"""
        try:
            cursor = conn.execute("""
                SELECT query, COUNT(*) as count
                FROM search_queue
                WHERE DATE(created_at) = ?
                GROUP BY query
                ORDER BY count DESC
                LIMIT ?
            """, (date, limit))

            return cursor.fetchall()
        except Exception:
            return []

    def get_performance_metrics(self, days: int = 7) -> Dict:
        """Get performance metrics over the specified period"""
        analytics = self.get_historical_analytics(days)

        if not analytics:
            return {"error": "No analytics data available"}

        # Calculate aggregate metrics
        total_searches = sum(a.searches_performed for a in analytics)
        total_successful = sum(a.successful_searches for a in analytics)
        total_quota_used = sum(a.quota_used for a in analytics)

        success_rates = [a.success_rate for a in analytics if a.searches_performed > 0]
        utilization_rates = [a.quota_utilization for a in analytics]

        return {
            "period_days": days,
            "total_searches": total_searches,
            "total_successful": total_successful,
            "total_failed": total_searches - total_successful,
            "total_quota_used": total_quota_used,
            "avg_daily_searches": total_searches / days,
            "avg_daily_quota_usage": total_quota_used / days,
            "overall_success_rate": (total_successful / total_searches * 100) if total_searches > 0 else 0,
            "avg_success_rate": statistics.mean(success_rates) if success_rates else 0,
            "avg_quota_utilization": statistics.mean(utilization_rates) if utilization_rates else 0,
            "peak_daily_searches": max((a.searches_performed for a in analytics), default=0),
            "peak_quota_utilization": max(utilization_rates) if utilization_rates else 0
        }

    def get_search_patterns(self, days: int = 30) -> Dict:
        """Analyze search query patterns and trends"""
        with sqlite3.connect(self.queue.db_path) as conn:
            conn.row_factory = sqlite3.Row

            start_date = (datetime.now() - timedelta(days=days)).isoformat()

            # Most common queries
            cursor = conn.execute("""
                SELECT query, COUNT(*) as count,
                       COUNT(CASE WHEN status = 'completed' THEN 1 END) as successful,
                       AVG(attempts) as avg_attempts
                FROM search_queue
                WHERE created_at >= ?
                GROUP BY query
                ORDER BY count DESC
                LIMIT 20
            """, (start_date,))

            top_queries = []
            for row in cursor.fetchall():
                success_rate = (row['successful'] / row['count'] * 100) if row['count'] > 0 else 0
                top_queries.append({
                    "query": row['query'],
                    "count": row['count'],
                    "successful": row['successful'],
                    "success_rate": success_rate,
                    "avg_attempts": row['avg_attempts']
                })

            # Query complexity analysis
            cursor = conn.execute("""
                SELECT
                    AVG(LENGTH(query)) as avg_query_length,
                    MIN(LENGTH(query)) as min_query_length,
                    MAX(LENGTH(query)) as max_query_length
                FROM search_queue
                WHERE created_at >= ?
            """, (start_date,))

            complexity = dict(cursor.fetchone())

            # Failure patterns
            cursor = conn.execute("""
                SELECT error_message, COUNT(*) as count
                FROM search_queue
                WHERE status = 'failed' AND created_at >= ? AND error_message IS NOT NULL
                GROUP BY error_message
                ORDER BY count DESC
                LIMIT 10
            """, (start_date,))

            failure_patterns = [dict(row) for row in cursor.fetchall()]

            return {
                "analysis_period_days": days,
                "top_queries": top_queries,
                "query_complexity": complexity,
                "failure_patterns": failure_patterns,
                "total_unique_queries": len(top_queries)
            }

    def _get_alert_level(self, quota_utilization: float, hours_until_reset: float) -> str:
        """Determine alert level based on quota usage and time remaining"""
        if quota_utilization >= 95:
            return "CRITICAL"
        elif quota_utilization >= 85:
            return "WARNING"
        elif quota_utilization >= 70 and hours_until_reset > 12:
            return "INFO"
        else:
            return "OK"

    def _assess_system_health(self, queue_status: Dict, quota_utilization: float) -> str:
        """Assess overall system health"""
        pending_count = queue_status.get("status_counts", {}).get("pending", 0)
        failed_count = queue_status.get("status_counts", {}).get("failed", 0)

        if quota_utilization >= 95:
            return "DEGRADED - Quota Exhausted"
        elif pending_count > 100:
            return "DEGRADED - High Queue Backlog"
        elif failed_count > pending_count:
            return "DEGRADED - High Failure Rate"
        elif quota_utilization >= 85:
            return "CAUTION - High Quota Usage"
        else:
            return "HEALTHY"

    def check_alerts(self) -> List[Dict]:
        """Check for conditions that require alerts"""
        alerts = []
        status = self.get_current_status()

        quota = status["quota"]
        queue = status["queue"]

        # Quota alerts
        if quota["utilization_percent"] >= 95:
            alerts.append({
                "level": "CRITICAL",
                "type": "QUOTA_EXHAUSTED",
                "message": f"Daily quota nearly exhausted: {quota['used_today']}/{self.daily_quota} ({quota['utilization_percent']:.1f}%)",
                "recommendation": "Quota will reset in {:.1f} hours".format(quota["hours_until_reset"])
            })
        elif quota["utilization_percent"] >= 85:
            alerts.append({
                "level": "WARNING",
                "type": "QUOTA_HIGH",
                "message": f"High quota usage: {quota['utilization_percent']:.1f}%",
                "recommendation": "Monitor usage carefully"
            })

        # Queue alerts
        pending = queue["status_counts"].get("pending", 0)
        if pending > 100:
            alerts.append({
                "level": "WARNING",
                "type": "QUEUE_BACKLOG",
                "message": f"High queue backlog: {pending} pending searches",
                "recommendation": "Consider increasing processing rate or investigating failures"
            })

        failed = queue["status_counts"].get("failed", 0)
        if failed > pending:
            alerts.append({
                "level": "WARNING",
                "type": "HIGH_FAILURE_RATE",
                "message": f"High failure rate: {failed} failed vs {pending} pending",
                "recommendation": "Investigate common failure causes"
            })

        return alerts

    def generate_daily_report(self) -> str:
        """Generate a comprehensive daily report"""
        status = self.get_current_status()
        analytics = self.get_historical_analytics(1)  # Today only
        performance = self.get_performance_metrics(7)  # Last 7 days
        patterns = self.get_search_patterns(7)
        alerts = self.check_alerts()

        today_analytics = analytics[0] if analytics else None

        report = f"""
🔍 GOOGLE SEARCH FALLBACK - DAILY REPORT
========================================

📅 Report Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📊 TODAY'S USAGE:
- Searches performed: {today_analytics.searches_performed if today_analytics else 0}
- Success rate: {today_analytics.success_rate:.1f}% if today_analytics else 0
- Quota used: {status['quota']['used_today']}/{self.daily_quota} ({status['quota']['utilization_percent']:.1f}%)
- Remaining: {status['quota']['remaining']} searches
- Hours until reset: {status['quota']['hours_until_reset']:.1f}

🏃 QUEUE STATUS:
"""

        for status_name, count in status['queue']['status_counts'].items():
            report += f"- {status_name.title()}: {count}\n"

        report += f"""
📈 7-DAY PERFORMANCE:
- Average daily searches: {performance['avg_daily_searches']:.1f}
- Overall success rate: {performance['overall_success_rate']:.1f}%
- Peak daily quota usage: {performance['peak_quota_utilization']:.1f}%
- Total successful recoveries: {performance['total_successful']}

🔎 TOP SEARCH QUERIES:
"""

        for query_data in patterns['top_queries'][:5]:
            report += f"- '{query_data['query']}': {query_data['count']} searches ({query_data['success_rate']:.1f}% success)\n"

        if alerts:
            report += "\n🚨 ALERTS:\n"
            for alert in alerts:
                report += f"- [{alert['level']}] {alert['type']}: {alert['message']}\n"
                report += f"  → {alert['recommendation']}\n"
        else:
            report += "\n✅ NO ACTIVE ALERTS\n"

        report += f"\n🏥 SYSTEM HEALTH: {status['system_health']}\n"

        return report

def create_monitoring_dashboard() -> Dict:
    """Create a JSON dashboard for web display"""
    monitor = GoogleSearchMonitor()

    return {
        "current_status": monitor.get_current_status(),
        "performance_metrics": monitor.get_performance_metrics(7),
        "search_patterns": monitor.get_search_patterns(30),
        "historical_data": [asdict(a) for a in monitor.get_historical_analytics(30)],
        "alerts": monitor.check_alerts(),
        "last_updated": datetime.now().isoformat()
    }

if __name__ == "__main__":
    monitor = GoogleSearchMonitor()

    if len(sys.argv) > 1 and sys.argv[1] == "report":
        print(monitor.generate_daily_report())
    elif len(sys.argv) > 1 and sys.argv[1] == "dashboard":
        dashboard = create_monitoring_dashboard()
        print(json.dumps(dashboard, indent=2))
    else:
        status = monitor.get_current_status()
        print(json.dumps(status, indent=2))