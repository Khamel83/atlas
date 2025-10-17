#!/usr/bin/env python3
"""
Atlas Transactional Metrics Dashboard

Single source of truth for all content processing metrics.
Provides comprehensive analytics from the content_transactions table.
"""

import json
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
import argparse
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.content_transactions import ContentTransactionSystem
from helpers.numeric_stages import NumericStage

logger = logging.getLogger(__name__)

class AtlasMetricsDashboard:
    """
    Comprehensive metrics dashboard using the transactional system as single source of truth.

    This dashboard provides real-time insights into:
    - Content processing pipeline performance
    - Stage progression efficiency
    - Success rates and failure patterns
    - System health and throughput
    """

    def __init__(self, db_path: str = "data/atlas.db"):
        self.db_path = db_path
        self.transaction_system = ContentTransactionSystem(db_path)

    def get_system_overview(self) -> Dict[str, Any]:
        """Get comprehensive system overview from transactional data."""
        recent_activity = self.transaction_system.get_recent_activity(minutes=60)
        stage_distribution = self.transaction_system.get_stage_distribution()
        daily_summary = self.transaction_system.get_daily_summary()

        # Calculate system health metrics
        total_recent = len(recent_activity)
        successful_recent = sum(1 for a in recent_activity if a["success"])
        success_rate = (successful_recent / total_recent * 100) if total_recent > 0 else 0

        # Calculate processing efficiency
        total_content = sum(stage_distribution.values())
        active_processing = sum(count for stage, count in stage_distribution.items()
                              if 100 <= int(stage) <= 399)  # Acquisition and Processing phases

        return {
            "system_health": {
                "transaction_system_ready": True,
                "total_content_items": total_content,
                "active_processing_count": active_processing,
                "recent_activity_count": total_recent,
                "success_rate_percent": round(success_rate, 2),
                "system_uptime": "Operational"
            },
            "stage_distribution": stage_distribution,
            "daily_processing": daily_summary,
            "recent_activity_sample": recent_activity[:10] if recent_activity else []
        }

    def get_content_lifecycle_metrics(self) -> Dict[str, Any]:
        """Get detailed content lifecycle metrics."""
        # Get stage progression statistics
        progression_stats = self.transaction_system.get_stage_progression_stats()

        # Group by major phases
        phase_mapping = {
            "acquisition": range(100, 200),
            "validation": range(200, 300),
            "processing": range(300, 400),
            "enhancement": range(400, 500),
            "finalization": range(500, 600)
        }

        phase_distribution = {}
        for phase_name, stage_range in phase_mapping.items():
            phase_count = sum(count for stage, count in self.transaction_system.get_stage_distribution().items()
                             if int(stage) in stage_range)
            phase_distribution[phase_name] = phase_count

        # Calculate efficiency metrics
        total_transitions = sum(stat["transition_count"] for stat in progression_stats)
        avg_success_rate = sum(stat["success_rate"] * stat["transition_count"] for stat in progression_stats) / total_transitions if total_transitions > 0 else 0

        return {
            "phase_distribution": phase_distribution,
            "progression_efficiency": {
                "total_stage_transitions": total_transitions,
                "average_success_rate_percent": round(avg_success_rate * 100, 2),
                "total_progression_paths": len(progression_stats)
            },
            "stage_transitions": progression_stats[:20]  # Top 20 transitions
        }

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance and timing metrics."""
        recent_activity = self.transaction_system.get_recent_activity(minutes=60)

        # Calculate timing metrics
        durations = [a["duration_ms"] for a in recent_activity if a.get("duration_ms")]
        avg_duration = sum(durations) / len(durations) if durations else 0

        # Calculate throughput
        hourly_rate = len(recent_activity)  # Activity in last hour

        return {
            "timing_performance": {
                "average_processing_time_ms": round(avg_duration, 2),
                "total_processed_events": len(recent_activity),
                "hourly_throughput": hourly_rate,
                "events_with_timing": len(durations)
            },
            "quality_metrics": {
                "recent_success_rate": sum(1 for a in recent_activity if a["success"]) / len(recent_activity) * 100 if recent_activity else 0,
                "failure_analysis": self._analyze_failures(recent_activity)
            }
        }

    def _analyze_failures(self, activity: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze failure patterns."""
        failures = [a for a in activity if not a["success"]]

        if not failures:
            return {"total_failures": 0, "failure_rate_percent": 0}

        # Group failures by stage
        failure_by_stage = {}
        for failure in failures:
            stage = failure["stage"]
            failure_by_stage[stage] = failure_by_stage.get(stage, 0) + 1

        # Find most common failure stages
        worst_stages = sorted(failure_by_stage.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "total_failures": len(failures),
            "failure_rate_percent": round(len(failures) / len(activity) * 100, 2),
            "problem_stages": [{"stage": stage, "failures": count} for stage, count in worst_stages]
        }

    def get_content_item_details(self, content_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific content item."""
        progress = self.transaction_system.get_content_progress(content_id)
        metrics = self.transaction_system.get_content_metrics(content_id)
        current_stage = self.transaction_system.get_current_stage(content_id)

        return {
            "content_id": content_id,
            "current_numeric_stage": current_stage,
            "processing_history": progress,
            "comprehensive_metrics": metrics,
            "total_processing_steps": len(progress),
            "successful_steps": sum(1 for p in progress if p["success"]),
            "overall_success_rate": (sum(1 for p in progress if p["success"]) / len(progress) * 100) if progress else 0
        }

    def generate_real_time_dashboard(self) -> str:
        """Generate a real-time dashboard view."""
        overview = self.get_system_overview()
        lifecycle = self.get_content_lifecycle_metrics()
        performance = self.get_performance_metrics()

        dashboard = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    ATLAS TRANSACTIONAL METRICS DASHBOARD                     ║
║                               Single Source of Truth                         ║
╠══════════════════════════════════════════════════════════════════════════════╣

📊 SYSTEM OVERVIEW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Total Content Items: {overview['system_health']['total_content_items']}
• Active Processing: {overview['system_health']['active_processing_count']}
• Success Rate: {overview['system_health']['success_rate_percent']}%
• Recent Activity: {overview['system_health']['recent_activity_count']} events (last hour)
• System Status: {overview['system_health']['system_uptime']}

🔄 CONTENT LIFECYCLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

        # Add phase distribution
        for phase, count in lifecycle['phase_distribution'].items():
            dashboard += f"• {phase.title()}: {count} items\n"

        dashboard += f"""
• Average Success Rate: {lifecycle['progression_efficiency']['average_success_rate_percent']}%
• Stage Transitions: {lifecycle['progression_efficiency']['total_stage_transitions']}

⚡ PERFORMANCE METRICS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Avg Processing Time: {performance['timing_performance']['average_processing_time_ms']}ms
• Hourly Throughput: {performance['timing_performance']['hourly_throughput']} events/hour
• Recent Success Rate: {performance['quality_metrics']['recent_success_rate']:.1f}%
• Total Failures: {performance['quality_metrics']['failure_analysis']['total_failures']}

📈 STAGE DISTRIBUTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

        # Add stage distribution
        for stage, count in overview['stage_distribution'].items():
            stage_name = self._get_stage_name(int(stage))
            dashboard += f"• Stage {stage} ({stage_name}): {count} items\n"

        dashboard += f"""
╚══════════════════════════════════════════════════════════════════════════════╝
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Database: {self.db_path}
"""

        return dashboard

    def _get_stage_name(self, stage: int) -> str:
        """Get human-readable stage name."""
        try:
            return NumericStage(stage).name.replace('_', ' ').title()
        except ValueError:
            return f"Unknown Stage {stage}"

    def export_metrics_json(self, filepath: str = None) -> str:
        """Export comprehensive metrics to JSON file."""
        if not filepath:
            filepath = f"atlas_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        metrics = {
            "export_timestamp": datetime.now().isoformat(),
            "database_path": self.db_path,
            "system_overview": self.get_system_overview(),
            "content_lifecycle": self.get_content_lifecycle_metrics(),
            "performance_metrics": self.get_performance_metrics()
        }

        with open(filepath, 'w') as f:
            json.dump(metrics, f, indent=2, default=str)

        logger.info(f"📊 Metrics exported to: {filepath}")
        return filepath

def main():
    """Main function to run the metrics dashboard."""
    parser = argparse.ArgumentParser(description="Atlas Transactional Metrics Dashboard")
    parser.add_argument("--dashboard", action="store_true", help="Show real-time dashboard")
    parser.add_argument("--export", help="Export metrics to JSON file")
    parser.add_argument("--content-id", help="Get details for specific content item")
    parser.add_argument("--watch", action="store_true", help="Continuously update dashboard")
    parser.add_argument("--interval", type=int, default=30, help="Update interval in seconds (for --watch)")

    args = parser.parse_args()

    dashboard = AtlasMetricsDashboard()

    if args.content_id:
        # Show details for specific content item
        details = dashboard.get_content_item_details(args.content_id)
        print(f"📋 Content Item Details: {args.content_id}")
        print(json.dumps(details, indent=2, default=str))
        return

    if args.export:
        # Export metrics to JSON
        filepath = dashboard.export_metrics_json(args.export)
        print(f"✅ Metrics exported to: {filepath}")
        return

    if args.dashboard or args.watch:
        # Show real-time dashboard
        try:
            while True:
                print("\033[2J\033[H")  # Clear screen
                print(dashboard.generate_real_time_dashboard())

                if not args.watch:
                    break

                import time
                print(f"\n⏱️  Updating every {args.interval} seconds... Press Ctrl+C to exit")
                time.sleep(args.interval)

        except KeyboardInterrupt:
            print("\n👋 Dashboard stopped by user")
            return

    # Default: show system overview
    overview = dashboard.get_system_overview()
    print("📊 Atlas System Overview")
    print(json.dumps(overview, indent=2, default=str))

if __name__ == "__main__":
    main()