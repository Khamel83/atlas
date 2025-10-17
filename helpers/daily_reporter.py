#!/usr/bin/env python3
"""
Atlas Daily Activity Reporter
Generates comprehensive daily reports of Atlas ingestion, processing, and system health.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any
import sqlite3


class AtlasDailyReporter:
    """Generate daily activity reports for Atlas system."""

    def __init__(self, base_path: str = "/home/ubuntu/dev/atlas"):
        self.base_path = Path(base_path)
        self.output_path = self.base_path / "output"
        self.logs_path = self.base_path / "logs"
        self.data_path = self.base_path / "data"

    def generate_daily_report(self, date: str = None) -> Dict[str, Any]:
        """Generate comprehensive daily activity report."""
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")

        report = {
            "date": date,
            "generated_at": datetime.now().isoformat(),
            "ingestion_summary": self._get_ingestion_summary(date),
            "podcast_activity": self._get_podcast_activity(date),
            "system_health": self._get_system_health(),
            "processing_metrics": self._get_processing_metrics(date),
            "error_summary": self._get_error_summary(date),
            "storage_usage": self._get_storage_usage(),
            "next_actions": self._get_next_actions(),
        }

        return report

    def _get_ingestion_summary(self, date: str) -> Dict[str, Any]:
        """Get daily ingestion statistics."""
        cutoff = datetime.strptime(date, "%Y-%m-%d")
        next_day = cutoff + timedelta(days=1)

        stats = {
            "articles_processed": 0,
            "podcasts_processed": 0,
            "youtube_processed": 0,
            "documents_processed": 0,
            "total_files_today": 0,
            "success_rate": 0.0,
            "new_content_mb": 0.0,
        }

        # Count files created today
        for category in ["articles", "podcasts", "youtube", "documents"]:
            category_path = self.output_path / category
            if category_path.exists():
                files = list(category_path.rglob("*.json"))
                today_files = [
                    f
                    for f in files
                    if datetime.fromtimestamp(f.stat().st_mtime) >= cutoff
                    and datetime.fromtimestamp(f.stat().st_mtime) < next_day
                ]

                stats[f"{category}_processed"] = len(today_files)
                stats["total_files_today"] += len(today_files)

                # Calculate size
                total_size = sum(f.stat().st_size for f in today_files)
                stats["new_content_mb"] += total_size / (1024 * 1024)

        return stats

    def _get_podcast_activity(self, date: str) -> Dict[str, Any]:
        """Get podcast-specific activity."""
        activity = {
            "episodes_discovered": 0,
            "transcripts_found": 0,
            "transcripts_downloaded": 0,
            "active_podcasts": 0,
            "discovery_runs": 0,
            "transcript_discovery": {
                "total_transcripts": 0,
                "podcasts_with_transcripts": 0,
                "success_rate_percent": 0.0,
                "last_discovery_run": None,
                "patterns_learned": 0,
            },
        }

        # Check podcast database if exists
        db_path = self.data_path / "podcasts" / "atlas_podcasts.db"
        if db_path.exists():
            try:
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()

                # Get basic stats
                cursor.execute("SELECT COUNT(*) FROM podcasts")
                activity["active_podcasts"] = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM episodes WHERE status = 'found'")
                activity["episodes_discovered"] = cursor.fetchone()[0]

                # Get transcript discovery stats
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM episodes
                    WHERE transcript_url IS NOT NULL OR transcript_status = 'found'
                """
                )
                activity["transcript_discovery"][
                    "total_transcripts"
                ] = cursor.fetchone()[0]

                cursor.execute(
                    """
                    SELECT COUNT(DISTINCT podcast_id) FROM episodes
                    WHERE transcript_url IS NOT NULL OR transcript_status = 'found'
                """
                )
                activity["transcript_discovery"][
                    "podcasts_with_transcripts"
                ] = cursor.fetchone()[0]

                # Calculate success rate
                cursor.execute("SELECT COUNT(*) FROM episodes")
                total_episodes = cursor.fetchone()[0]
                if total_episodes > 0:
                    success_rate = (
                        activity["transcript_discovery"]["total_transcripts"]
                        / total_episodes
                    ) * 100
                    activity["transcript_discovery"]["success_rate_percent"] = round(
                        success_rate, 2
                    )

                conn.close()
            except Exception:
                pass

        # Check transcript pattern database
        patterns_path = self.data_path / "podcasts" / "transcript_patterns.json"
        if patterns_path.exists():
            try:
                import json

                with open(patterns_path, "r") as f:
                    patterns = json.load(f)
                    activity["transcript_discovery"]["patterns_learned"] = len(patterns)

                    # Find most recent discovery run
                    latest_run = None
                    for podcast_data in patterns.values():
                        if "last_run" in podcast_data and podcast_data["last_run"]:
                            run_time = datetime.fromtimestamp(podcast_data["last_run"])
                            if latest_run is None or run_time > latest_run:
                                latest_run = run_time

                    if latest_run:
                        activity["transcript_discovery"]["last_discovery_run"] = (
                            latest_run.strftime("%Y-%m-%d %H:%M")
                        )
            except Exception:
                pass

        return activity

    def _get_system_health(self) -> Dict[str, Any]:
        """Get current system health status."""
        health = {
            "background_service_running": False,
            "disk_usage_percent": 0.0,
            "active_processes": 0,
            "last_successful_run": None,
            "errors_last_24h": 0,
        }

        # Check if background service is running
        try:
            import subprocess

            result = subprocess.run(["ps", "aux"], capture_output=True, text=True)
            if "atlas_background_service.py" in result.stdout:
                health["background_service_running"] = True
                health["active_processes"] = result.stdout.count("python")
        except Exception:
            pass

        # Check disk usage
        try:
            import shutil

            total, used, free = shutil.disk_usage(self.base_path)
            health["disk_usage_percent"] = (used / total) * 100
        except Exception:
            pass

        return health

    def _get_processing_metrics(self, date: str) -> Dict[str, Any]:
        """Get processing performance metrics."""
        metrics = {
            "total_content_items": 0,
            "avg_processing_time": 0.0,
            "success_rate": 0.0,
            "retry_queue_size": 0,
            "most_active_sources": [],
        }

        # Count total content items
        if self.output_path.exists():
            json_files = list(self.output_path.rglob("*.json"))
            metrics["total_content_items"] = len(json_files)

        return metrics

    def _get_error_summary(self, date: str) -> Dict[str, Any]:
        """Get error summary for the day."""
        errors = {
            "total_errors": 0,
            "critical_errors": 0,
            "common_error_types": [],
            "failed_urls": 0,
            "network_issues": 0,
        }

        # Check error log if exists
        error_log = self.output_path / "error_log.jsonl"
        if error_log.exists():
            try:
                with open(error_log, "r") as f:
                    lines = f.readlines()[-100:]  # Last 100 errors
                    errors["total_errors"] = len(lines)
            except Exception:
                pass

        return errors

    def _get_storage_usage(self) -> Dict[str, Any]:
        """Get storage usage breakdown."""
        usage = {
            "total_gb": 0.0,
            "articles_gb": 0.0,
            "podcasts_gb": 0.0,
            "logs_gb": 0.0,
            "cache_gb": 0.0,
        }

        def get_dir_size(path: Path) -> float:
            if not path.exists():
                return 0.0
            total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
            return total / (1024 * 1024 * 1024)  # Convert to GB

        usage["articles_gb"] = get_dir_size(self.output_path / "articles")
        usage["podcasts_gb"] = get_dir_size(self.output_path / "podcasts")
        usage["logs_gb"] = get_dir_size(self.logs_path)
        usage["total_gb"] = get_dir_size(self.base_path)

        return usage

    def _get_next_actions(self) -> List[str]:
        """Get recommended next actions."""
        actions = []

        # Check if background service is running
        try:
            import subprocess

            result = subprocess.run(["ps", "aux"], capture_output=True, text=True)
            if "atlas_background_service.py" not in result.stdout:
                actions.append(
                    "🔴 CRITICAL: Start background service with ./scripts/start_atlas_service.sh start"
                )
        except Exception:
            actions.append("⚠️  Check Atlas background service status")

        # Check for failed articles
        retry_path = self.base_path / "retries"
        if retry_path.exists() and list(retry_path.glob("*.txt")):
            actions.append("🔄 Process failed articles with retry_failed_articles.py")

        # Check for new input files
        inputs_path = self.base_path / "inputs"
        if inputs_path.exists():
            new_files = []
            for pattern in ["*.txt", "*.csv"]:
                new_files.extend(inputs_path.glob(pattern))
            if new_files:
                actions.append(f"📥 Process {len(new_files)} new input files")

        if not actions:
            actions.append("✅ All systems operating normally")

        return actions

    def save_daily_report(self, report: Dict[str, Any]) -> str:
        """Save daily report to file."""
        reports_dir = self.base_path / "reports" / "daily"
        reports_dir.mkdir(parents=True, exist_ok=True)

        filename = f"atlas_daily_{report['date']}.json"
        filepath = reports_dir / filename

        with open(filepath, "w") as f:
            json.dump(report, f, indent=2)

        return str(filepath)

    def generate_push_notification(self, report: Dict[str, Any]) -> str:
        """Generate a concise push notification summary."""
        summary = report["ingestion_summary"]
        health = report["system_health"]

        # Create status emoji
        status = "🟢" if health["background_service_running"] else "🔴"

        # Create summary text
        notification = (
            f"{status} Atlas Daily: {summary['total_files_today']} items processed"
        )

        if summary["articles_processed"] > 0:
            notification += f" • {summary['articles_processed']} articles"
        if summary["podcasts_processed"] > 0:
            notification += f" • {summary['podcasts_processed']} podcasts"

        # Add storage info
        storage = report["storage_usage"]
        notification += f" • {storage['total_gb']:.1f}GB total"

        # Add critical actions
        actions = report["next_actions"]
        critical_actions = [a for a in actions if "CRITICAL" in a]
        if critical_actions:
            notification += f" • ⚠️ {len(critical_actions)} critical issues"

        return notification


def generate_and_display_report():
    """CLI function to generate and display today's report."""
    reporter = AtlasDailyReporter()
    report = reporter.generate_daily_report()

    # Save report
    filepath = reporter.save_daily_report(report)

    # Generate notification
    notification = reporter.generate_push_notification(report)

    # Display summary
    print("=" * 60)
    print(f"📊 ATLAS DAILY REPORT - {report['date']}")
    print("=" * 60)
    print(f"📱 Push Summary: {notification}")
    print()

    print("📈 INGESTION SUMMARY:")
    ing = report["ingestion_summary"]
    print(f"   • Articles: {ing['articles_processed']}")
    print(f"   • Podcasts: {ing['podcasts_processed']}")
    print(f"   • YouTube: {ing['youtube_processed']}")
    print(f"   • Documents: {ing['documents_processed']}")
    print(f"   • Total today: {ing['total_files_today']}")
    print(f"   • New content: {ing['new_content_mb']:.1f} MB")
    print()

    print("🎙️ PODCAST ACTIVITY:")
    pod = report["podcast_activity"]
    print(f"   • Active podcasts: {pod['active_podcasts']}")
    print(f"   • Episodes discovered: {pod['episodes_discovered']}")
    print(f"   • Transcripts found: {pod['transcripts_found']}")
    print()

    print("🔍 TRANSCRIPT DISCOVERY:")
    td = pod["transcript_discovery"]
    print(f"   • Total transcripts: {td['total_transcripts']}")
    print(f"   • Podcasts with transcripts: {td['podcasts_with_transcripts']}")
    print(f"   • Success rate: {td['success_rate_percent']}%")
    print(f"   • Patterns learned: {td['patterns_learned']}")
    if td["last_discovery_run"]:
        print(f"   • Last discovery: {td['last_discovery_run']}")
    print()

    print("💾 STORAGE USAGE:")
    stor = report["storage_usage"]
    print(f"   • Total: {stor['total_gb']:.1f} GB")
    print(f"   • Articles: {stor['articles_gb']:.1f} GB")
    print(f"   • Podcasts: {stor['podcasts_gb']:.1f} GB")
    print(f"   • Logs: {stor['logs_gb']:.1f} GB")
    print()

    print("🎯 NEXT ACTIONS:")
    for action in report["next_actions"][:5]:
        print(f"   • {action}")
    print()

    print(f"📄 Full report saved: {filepath}")
    print("=" * 60)

    return report


if __name__ == "__main__":
    generate_and_display_report()
