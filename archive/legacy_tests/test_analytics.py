#!/usr/bin/env python3
"""
Test script for Atlas Analytics Dashboard
"""

import sys
import os
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_dashboard_core():
    """Test the core dashboard functionality"""
    print("Testing Analytics Dashboard Core...")

    try:
        from analytics.dashboard import PersonalAnalyticsDashboard

        # Create dashboard instance
        dashboard = PersonalAnalyticsDashboard()

        # Test metrics collection
        system_metrics = dashboard.collect_system_metrics()
        assert isinstance(system_metrics, dict)
        assert 'cpu_usage' in system_metrics

        content_metrics = dashboard.collect_content_metrics()
        assert isinstance(content_metrics, dict)
        assert 'articles_processed' in content_metrics

        user_metrics = dashboard.collect_user_metrics()
        assert isinstance(user_metrics, dict)
        assert 'daily_active_time' in user_metrics

        # Test chart generation
        charts = dashboard.generate_charts()
        assert isinstance(charts, dict)
        assert 'content_processing' in charts

        # Test report generation
        reports = dashboard.generate_reports()
        assert isinstance(reports, dict)
        assert 'weekly_summary' in reports

        # Test full data retrieval
        data = dashboard.get_dashboard_data()
        assert isinstance(data, dict)
        assert 'metrics' in data
        assert 'charts' in data
        assert 'reports' in data

        print("✅ Analytics Dashboard Core test passed!")
        return True

    except Exception as e:
        print(f"❌ Analytics Dashboard Core test failed: {e}")
        return False

def test_api_endpoints():
    """Test the API endpoints"""
    print("Testing Analytics API Endpoints...")

    try:
        from api.analytics_api import analytics_bp

        # Test that blueprint was created
        assert analytics_bp is not None
        assert analytics_bp.name == 'analytics'
        assert analytics_bp.url_prefix == '/api/analytics'

        print("✅ Analytics API Endpoints test passed!")
        return True

    except Exception as e:
        print(f"❌ Analytics API Endpoints test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("Running Atlas Analytics Dashboard Tests")
    print("=" * 40)

    tests = [
        test_dashboard_core,
        test_api_endpoints
    ]

    passed = 0
    failed = 0

    for test in tests:
        if test():
            passed += 1
        else:
            failed += 1

    print("\n" + "=" * 40)
    print(f"Test Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All tests passed!")
        return True
    else:
        print("⚠️  Some tests failed!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)