#!/usr/bin/env python3
"""
Demo script for Atlas Analytics Dashboard
"""

import sys
import os
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

def demo_dashboard_core():
    """Demo the core dashboard functionality"""
    print("📊 Atlas Analytics Dashboard Demo")
    print("=" * 40)

    try:
        from analytics.dashboard import PersonalAnalyticsDashboard

        # Create dashboard instance
        dashboard = PersonalAnalyticsDashboard()

        # Get dashboard data
        print("Collecting dashboard data...")
        data = dashboard.get_dashboard_data()

        # Display metrics
        print("\n📈 System Metrics:")
        system_metrics = data['metrics']['system']
        print(f"  CPU Usage: {system_metrics['cpu_usage']:.1f}%")
        print(f"  Memory Usage: {system_metrics['memory_usage']:.1f}%")
        print(f"  Disk Usage: {system_metrics['disk_usage']:.1f}%")

        print("\n📄 Content Metrics:")
        content_metrics = data['metrics']['content']
        print(f"  Articles Processed: {content_metrics['articles_processed']}")
        print(f"  Success Rate: {content_metrics['articles_success_rate']:.1f}%")
        print(f"  Podcasts Processed: {content_metrics['podcasts_processed']}")

        print("\n👥 User Metrics:")
        user_metrics = data['metrics']['user']
        print(f"  Daily Active Time: {user_metrics['daily_active_time']:.1f} hours")
        print(f"  Weekly Reading Time: {user_metrics['weekly_reading_time']:.1f} hours")
        print(f"  Favorite Topics: {', '.join(user_metrics['favorite_topics'][:3])}")

        # Display charts info
        print("\n📊 Charts Generated:")
        for chart_name, chart_data in data['charts'].items():
            print(f"  - {chart_name}: {chart_data['type']} chart")

        # Display reports info
        print("\n📝 Reports Generated:")
        for report_name, report_data in data['reports'].items():
            print(f"  - {report_name}")

        print("\n✅ Analytics Dashboard demo completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Analytics Dashboard demo failed: {e}")
        return False

def demo_api_endpoints():
    """Demo the API endpoints"""
    print("\n🌐 Atlas Analytics API Demo")
    print("=" * 40)

    try:
        from api.analytics_api import analytics_bp, update_metrics_periodically

        # Show available endpoints
        print("Available API Endpoints:")
        print("  GET /api/analytics/dashboard")
        print("  GET /api/analytics/metrics/system")
        print("  GET /api/analytics/metrics/content")
        print("  GET /api/analytics/metrics/user")
        print("  GET /api/analytics/charts")
        print("  GET /api/analytics/reports/weekly")
        print("  GET /api/analytics/reports/trends")
        print("  POST /api/analytics/metrics/system")
        print("  POST /api/analytics/metrics/content")
        print("  POST /api/analytics/metrics/user")
        print("  GET /api/analytics/health")

        # Demo metrics update
        print("\n🔄 Updating metrics with simulated data...")
        update_metrics_periodically()
        print("✅ Metrics updated successfully!")

        print("\n✅ Analytics API demo completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Analytics API demo failed: {e}")
        return False

def main():
    """Run all demos"""
    print("🚀 Atlas Analytics Dashboard Demo")
    print("=" * 50)

    demos = [
        demo_dashboard_core,
        demo_api_endpoints
    ]

    passed = 0
    failed = 0

    for demo in demos:
        if demo():
            passed += 1
        else:
            failed += 1

    print("\n" + "=" * 50)
    print(f"Demo Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All demos completed successfully!")
        print("\n🎯 Atlas Analytics Dashboard is ready for use!")
        return True
    else:
        print("⚠️  Some demos failed!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)