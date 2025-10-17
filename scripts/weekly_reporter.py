#!/usr/bin/env python3
"""
Atlas Weekly Health Reporter
Generates comprehensive weekly health reports and sends via Telegram.
"""

import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.metrics_collector import get_metrics_collector
from helpers.queue_manager import get_queue_status
from helpers.database_config import get_database_connection, get_database_path
from scripts.notify import send_notification


class WeeklyReporter:
    """Generates comprehensive weekly health reports."""

    def __init__(self):
        """Initialize weekly reporter."""
        self.report_file = Path("data/weekly_reports.json")
        self.previous_reports = self._load_previous_reports()

    def _load_previous_reports(self) -> Dict[str, Any]:
        """Load previous weekly reports for comparison."""
        if self.report_file.exists():
            try:
                with open(self.report_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {"reports": []}

    def _save_report(self, report: Dict[str, Any]):
        """Save report to history."""
        try:
            self.report_file.parent.mkdir(exist_ok=True)
            self.previous_reports["reports"].append(report)

            # Keep only last 12 weeks
            if len(self.previous_reports["reports"]) > 12:
                self.previous_reports["reports"] = self.previous_reports["reports"][-12:]

            with open(self.report_file, 'w') as f:
                json.dump(self.previous_reports, f, indent=2)
        except Exception as e:
            print(f"Failed to save report: {e}")

    def generate_weekly_report(self) -> Dict[str, Any]:
        """Generate comprehensive weekly health report."""
        report_date = datetime.now()
        week_start = report_date - timedelta(days=7)

        # Collect current metrics
        metrics_collector = get_metrics_collector()
        queue_status = get_queue_status()

        # System overview
        system_stats = self._get_system_stats()

        # Processing performance
        processing_stats = self._get_processing_stats(week_start)

        # Queue health
        queue_health = self._get_queue_health()

        # Error analysis
        error_analysis = self._get_error_analysis()

        # Capacity planning
        capacity_metrics = self._get_capacity_metrics()

        # Recommendations
        recommendations = self._generate_recommendations(system_stats, processing_stats, queue_health, error_analysis)

        report = {
            "report_date": report_date.isoformat(),
            "period": {
                "start": week_start.isoformat(),
                "end": report_date.isoformat(),
                "days": 7
            },
            "system_stats": system_stats,
            "processing_stats": processing_stats,
            "queue_health": queue_health,
            "error_analysis": error_analysis,
            "capacity_metrics": capacity_metrics,
            "recommendations": recommendations,
            "summary": self._generate_summary(system_stats, processing_stats, queue_health)
        }

        return report

    def _get_system_stats(self) -> Dict[str, Any]:
        """Get system health statistics."""
        try:
            import psutil

            # Database stats
            db_path = get_database_path()
            db_size_mb = db_path.stat().st_size / 1024 / 1024 if db_path.exists() else 0

            # System resources
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            # Uptime estimation (simplified)
            uptime_hours = 24 * 7  # Assume running for report period

            return {
                "database_size_mb": round(db_size_mb, 1),
                "memory_total_gb": round(memory.total / 1024**3, 1),
                "memory_used_percent": memory.percent,
                "disk_total_gb": round(disk.total / 1024**3, 1),
                "disk_free_gb": round(disk.free / 1024**3, 1),
                "disk_used_percent": round((disk.used / disk.total) * 100, 1),
                "estimated_uptime_hours": uptime_hours
            }
        except Exception as e:
            return {"error": str(e)}

    def _get_processing_stats(self, week_start: datetime) -> Dict[str, Any]:
        """Get processing performance statistics."""
        try:
            conn = get_database_connection()
            cursor = conn.cursor()

            # Transcriptions this week
            cursor.execute("""
                SELECT COUNT(*) FROM transcriptions
                WHERE created_at > ?
            """, (week_start,))
            weekly_transcriptions = cursor.fetchone()[0]

            # Total transcriptions
            cursor.execute("SELECT COUNT(*) FROM transcriptions")
            total_transcriptions = cursor.fetchone()[0]

            # Episodes harvested
            cursor.execute("SELECT COUNT(*) FROM podcast_episodes")
            total_episodes = cursor.fetchone()[0]

            # Articles processed
            cursor.execute("SELECT COUNT(*) FROM content WHERE content_type = 'article'")
            total_articles = cursor.fetchone()[0]

            # Average processing rate
            avg_per_day = weekly_transcriptions / 7
            avg_per_hour = avg_per_day / 24

            conn.close()

            return {
                "weekly_transcriptions": weekly_transcriptions,
                "total_transcriptions": total_transcriptions,
                "total_episodes_harvested": total_episodes,
                "total_articles_processed": total_articles,
                "avg_transcriptions_per_day": round(avg_per_day, 1),
                "avg_transcriptions_per_hour": round(avg_per_hour, 2),
                "processing_rate": "excellent" if avg_per_hour > 1 else "moderate" if avg_per_hour > 0.1 else "low"
            }
        except Exception as e:
            return {"error": str(e)}

    def _get_queue_health(self) -> Dict[str, Any]:
        """Get queue health metrics."""
        try:
            queue_status = get_queue_status()

            queue_counts = queue_status.get("queue_counts", {})
            circuit_breakers = queue_status.get("circuit_breakers", {})

            # Circuit breaker analysis
            open_breakers = sum(1 for cb in circuit_breakers.values() if cb.get("state") == "open")
            total_breakers = len(circuit_breakers)

            return {
                "pending_tasks": queue_counts.get("pending", 0),
                "processing_tasks": queue_counts.get("processing", 0),
                "completed_tasks": queue_counts.get("completed", 0),
                "failed_tasks": queue_status.get("failed_tasks", 0),
                "retry_ready": queue_status.get("retry_ready", 0),
                "circuit_breakers_open": open_breakers,
                "total_circuit_breakers": total_breakers,
                "queue_health": "excellent" if queue_counts.get("pending", 0) < 100 else "moderate" if queue_counts.get("pending", 0) < 500 else "poor"
            }
        except Exception as e:
            return {"error": str(e)}

    def _get_error_analysis(self) -> Dict[str, Any]:
        """Analyze error patterns and trends."""
        try:
            conn = get_database_connection()
            cursor = conn.cursor()

            # Failed tasks analysis
            cursor.execute("""
                SELECT error_msg, COUNT(*) as count
                FROM failed_tasks
                GROUP BY error_msg
                ORDER BY count DESC
                LIMIT 5
            """)

            error_patterns = []
            for error_msg, count in cursor.fetchall():
                error_patterns.append({
                    "error": error_msg[:100] + "..." if len(error_msg) > 100 else error_msg,
                    "count": count
                })

            # Calculate error rate
            cursor.execute("SELECT COUNT(*) FROM failed_tasks")
            total_failed = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM task_queue WHERE status = 'completed'")
            total_completed = cursor.fetchone()[0]

            total_processed = total_failed + total_completed
            error_rate = (total_failed / max(total_processed, 1)) * 100

            conn.close()

            return {
                "total_failed_tasks": total_failed,
                "total_completed_tasks": total_completed,
                "error_rate_percent": round(error_rate, 2),
                "top_error_patterns": error_patterns,
                "error_trend": "improving" if error_rate < 5 else "stable" if error_rate < 10 else "concerning"
            }
        except Exception as e:
            return {"error": str(e)}

    def _get_capacity_metrics(self) -> Dict[str, Any]:
        """Get capacity planning metrics."""
        try:
            metrics_collector = get_metrics_collector()

            # Current utilization
            queue_depth = metrics_collector.get_metric_value("atlas_queue_pending_total") or 0
            memory_usage = metrics_collector.get_metric_value("atlas_memory_usage_bytes") or 0

            # Capacity estimates
            max_queue_capacity = 1000  # Alert threshold
            queue_utilization = (queue_depth / max_queue_capacity) * 100

            memory_gb = memory_usage / 1024**3

            return {
                "queue_utilization_percent": round(queue_utilization, 1),
                "memory_usage_gb": round(memory_gb, 2),
                "estimated_capacity_remaining": max(100 - queue_utilization, 0),
                "scaling_recommendation": "scale_up" if queue_utilization > 70 else "monitor" if queue_utilization > 40 else "optimal"
            }
        except Exception as e:
            return {"error": str(e)}

    def _generate_recommendations(self, system_stats: Dict, processing_stats: Dict,
                                 queue_health: Dict, error_analysis: Dict) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        # Queue recommendations
        if queue_health.get("pending_tasks", 0) > 500:
            recommendations.append("🚨 High queue depth detected. Consider scaling up workers or optimizing processing speed.")

        # Error rate recommendations
        error_rate = error_analysis.get("error_rate_percent", 0)
        if error_rate > 10:
            recommendations.append("⚠️ High error rate detected. Review top error patterns and implement fixes.")
        elif error_rate > 5:
            recommendations.append("📊 Moderate error rate. Monitor error patterns for improvement opportunities.")

        # Processing rate recommendations
        processing_rate = processing_stats.get("processing_rate", "unknown")
        if processing_rate == "low":
            recommendations.append("⚡ Low processing rate. Check worker health and resource allocation.")
        elif processing_rate == "excellent":
            recommendations.append("✅ Excellent processing rate. Current configuration is optimal.")

        # Disk space recommendations
        disk_free = system_stats.get("disk_free_gb", 0)
        if disk_free < 10:
            recommendations.append("🚨 Low disk space. Implement cleanup procedures immediately.")
        elif disk_free < 25:
            recommendations.append("⚠️ Disk space getting low. Plan cleanup or expansion soon.")

        # Circuit breaker recommendations
        open_breakers = queue_health.get("circuit_breakers_open", 0)
        if open_breakers > 0:
            recommendations.append(f"⚡ {open_breakers} circuit breaker(s) open. Investigate worker failures.")

        if not recommendations:
            recommendations.append("🎉 System is running optimally! No immediate action required.")

        return recommendations

    def _generate_summary(self, system_stats: Dict, processing_stats: Dict, queue_health: Dict) -> str:
        """Generate executive summary."""
        # Overall health score
        health_scores = []

        # Processing health
        rate = processing_stats.get("processing_rate", "unknown")
        if rate == "excellent":
            health_scores.append(100)
        elif rate == "moderate":
            health_scores.append(70)
        else:
            health_scores.append(40)

        # Queue health
        queue_status = queue_health.get("queue_health", "unknown")
        if queue_status == "excellent":
            health_scores.append(100)
        elif queue_status == "moderate":
            health_scores.append(70)
        else:
            health_scores.append(40)

        # System health (disk space)
        disk_free = system_stats.get("disk_free_gb", 0)
        if disk_free > 25:
            health_scores.append(100)
        elif disk_free > 10:
            health_scores.append(70)
        else:
            health_scores.append(30)

        overall_health = sum(health_scores) / len(health_scores)

        if overall_health >= 90:
            return "🟢 EXCELLENT - System operating at peak performance"
        elif overall_health >= 70:
            return "🟡 GOOD - System stable with minor optimizations needed"
        elif overall_health >= 50:
            return "🟠 FAIR - System functional but requires attention"
        else:
            return "🔴 POOR - System needs immediate intervention"

    def format_report_for_telegram(self, report: Dict[str, Any]) -> str:
        """Format report for Telegram delivery."""
        system = report["system_stats"]
        processing = report["processing_stats"]
        queue = report["queue_health"]
        errors = report["error_analysis"]

        message = f"""📊 *Atlas Weekly Health Report*
_{report["period"]["start"][:10]} to {report["period"]["end"][:10]}_

*🎯 SYSTEM SUMMARY*
{report["summary"]}

*📈 PROCESSING PERFORMANCE*
• Transcriptions this week: {processing.get("weekly_transcriptions", "N/A")}
• Daily average: {processing.get("avg_transcriptions_per_day", "N/A")}
• Processing rate: {processing.get("processing_rate", "unknown").title()}

*🔄 QUEUE HEALTH*
• Pending: {queue.get("pending_tasks", "N/A")} tasks
• Failed: {queue.get("failed_tasks", "N/A")} tasks
• Queue status: {queue.get("queue_health", "unknown").title()}

*💾 SYSTEM RESOURCES*
• Database: {system.get("database_size_mb", "N/A")} MB
• Disk free: {system.get("disk_free_gb", "N/A")} GB
• Memory used: {system.get("memory_used_percent", "N/A")}%

*⚠️ ERRORS & ISSUES*
• Error rate: {errors.get("error_rate_percent", "N/A")}%
• Failed tasks: {errors.get("total_failed_tasks", "N/A")}

*💡 RECOMMENDATIONS*
"""

        for i, rec in enumerate(report["recommendations"][:3], 1):
            message += f"{i}. {rec}\n"

        if len(report["recommendations"]) > 3:
            message += f"... and {len(report['recommendations']) - 3} more\n"

        message += f"\n📅 Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        return message

    def send_weekly_report(self, test_mode: bool = False) -> bool:
        """Generate and send weekly health report."""
        try:
            report = self.generate_weekly_report()

            if not test_mode:
                self._save_report(report)

            # Format for Telegram
            telegram_message = self.format_report_for_telegram(report)

            # Send notification
            title = "Atlas Weekly Health Report" + (" (Test)" if test_mode else "")
            success = send_notification(telegram_message, title, "info")

            if success:
                print(f"✅ Weekly report sent successfully")
                return True
            else:
                print(f"❌ Failed to send weekly report")
                return False

        except Exception as e:
            print(f"❌ Error generating weekly report: {e}")
            return False


def main():
    """Main weekly reporter function."""
    import argparse

    parser = argparse.ArgumentParser(description="Atlas Weekly Health Reporter")
    parser.add_argument("--send", action="store_true", help="Generate and send weekly report")
    parser.add_argument("--test", action="store_true", help="Send test report")
    parser.add_argument("--generate", action="store_true", help="Generate report without sending")

    args = parser.parse_args()

    reporter = WeeklyReporter()

    if args.send:
        reporter.send_weekly_report(test_mode=False)
    elif args.test:
        reporter.send_weekly_report(test_mode=True)
    elif args.generate:
        report = reporter.generate_weekly_report()
        print(json.dumps(report, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()