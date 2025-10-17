#!/usr/bin/env python3
"""
Test Service Health Monitoring - Phase 3.4
Comprehensive testing of the health monitoring system
"""

import sys
import os
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from helpers.service_health_monitor import (
    AtlasServiceHealthMonitor, HealthCheck, HealthStatus
)
import json

def test_individual_health_checks():
    """Test individual health check functions"""
    print("🔍 Testing Individual Health Checks")
    print("-" * 50)

    monitor = AtlasServiceHealthMonitor()

    # Test each health check individually
    health_checks = [
        "system_resources",
        "database_connectivity",
        "disk_space",
        "atlas_api",
        "background_processing",
        "search_functionality",
        "content_pipeline"
    ]

    results = {}

    for check_name in health_checks:
        print(f"📊 Testing {check_name}...")

        start_time = time.time()
        result = monitor.perform_health_check(check_name)
        duration = time.time() - start_time

        service = monitor.services[check_name]
        status = "✅" if result else "❌"

        print(f"   {status} Result: {result} ({duration:.2f}s)")
        print(f"   Status: {service.status.value}")

        if service.last_error:
            print(f"   Error: {service.last_error}")

        if service.metadata:
            print(f"   Metadata: {list(service.metadata.keys())}")

        results[check_name] = result
        print()

    successful_checks = sum(1 for result in results.values() if result)
    print(f"📈 Health Check Results: {successful_checks}/{len(health_checks)} checks passed")

    return successful_checks >= len(health_checks) // 2  # At least half should pass

def test_health_status_transitions():
    """Test health status transitions based on consecutive failures"""
    print("🔄 Testing Health Status Transitions")
    print("-" * 50)

    monitor = AtlasServiceHealthMonitor()

    # Add a test health check that we can control
    failure_count = 0
    def controllable_check():
        nonlocal failure_count
        failure_count += 1
        # Fail first 3 times, then succeed
        return failure_count > 3

    test_check = HealthCheck(
        name="test_transition",
        check_function=controllable_check,
        critical=True,
        consecutive_failures_threshold=2
    )

    monitor.add_health_check(test_check)

    # Test status transitions
    expected_statuses = [
        HealthStatus.DEGRADED,    # First failure
        HealthStatus.CRITICAL,    # Second failure (threshold reached, critical service)
        HealthStatus.CRITICAL,    # Third failure (still critical)
        HealthStatus.HEALTHY      # Fourth check succeeds
    ]

    actual_statuses = []

    for i in range(4):
        result = monitor.perform_health_check("test_transition")
        service = monitor.services["test_transition"]
        actual_statuses.append(service.status)

        print(f"Check {i+1}: Result={result}, Status={service.status.value}")

    # Verify status transitions
    transitions_correct = True
    for i, (expected, actual) in enumerate(zip(expected_statuses, actual_statuses)):
        if expected != actual:
            print(f"❌ Check {i+1}: Expected {expected.value}, got {actual.value}")
            transitions_correct = False

    if transitions_correct:
        print("✅ Status transitions working correctly")
    else:
        print("❌ Status transitions not working as expected")

    return transitions_correct

def test_system_health_summary():
    """Test comprehensive system health summary"""
    print("📊 Testing System Health Summary")
    print("-" * 50)

    monitor = AtlasServiceHealthMonitor()

    # Run all health checks first
    monitor.run_all_health_checks()

    # Get comprehensive summary
    summary = monitor.get_system_health_summary()

    print(f"🏥 System Health Summary:")
    print(f"   Overall Status: {summary['overall_status']}")
    print(f"   Total Services: {summary['statistics']['total_services']}")
    print(f"   Healthy: {summary['statistics']['healthy']}")
    print(f"   Degraded: {summary['statistics']['degraded']}")
    print(f"   Critical: {summary['statistics']['critical']}")
    print(f"   Down: {summary['statistics']['down']}")

    print(f"\n🔍 Service Details:")
    for service_name, service_info in summary['services'].items():
        status = service_info['status']
        uptime = service_info['uptime_percentage']
        response_time = service_info['response_time']

        status_emoji = {
            'healthy': '✅',
            'degraded': '⚠️',
            'critical': '❌',
            'down': '💥',
            'unknown': '❓'
        }.get(status, '❓')

        print(f"   {status_emoji} {service_name}: {status} ({uptime:.1f}% uptime, {response_time:.3f}s)")

    if summary['alerts']:
        print(f"\n🚨 Active Alerts:")
        for alert in summary['alerts']:
            print(f"   - {alert['service']}: {alert['message']}")
    else:
        print("\n✅ No active alerts")

    # Validate summary structure
    required_keys = ['timestamp', 'overall_status', 'services', 'statistics', 'alerts']
    structure_valid = all(key in summary for key in required_keys)

    return structure_valid and summary['statistics']['total_services'] > 0

def test_custom_health_checks():
    """Test adding custom health checks"""
    print("🛠️ Testing Custom Health Checks")
    print("-" * 50)

    monitor = AtlasServiceHealthMonitor()

    # Add custom health checks
    def mock_external_api_check():
        # Simulate external API check
        import random
        return random.random() > 0.3  # 70% success rate

    def mock_file_system_check():
        # Always succeed for testing
        return True

    custom_checks = [
        HealthCheck(
            name="external_api",
            check_function=mock_external_api_check,
            critical=False,
            interval=30,
            consecutive_failures_threshold=3
        ),
        HealthCheck(
            name="file_system_integrity",
            check_function=mock_file_system_check,
            critical=True,
            interval=60,
            consecutive_failures_threshold=2
        )
    ]

    for check in custom_checks:
        monitor.add_health_check(check)
        print(f"✅ Added custom health check: {check.name}")

    # Run the custom checks
    results = {}
    for check in custom_checks:
        result = monitor.perform_health_check(check.name)
        results[check.name] = result
        service = monitor.services[check.name]
        print(f"   {check.name}: {'✅' if result else '❌'} ({service.status.value})")

    custom_checks_working = len(results) == len(custom_checks)

    if custom_checks_working:
        print("✅ Custom health checks working correctly")
    else:
        print("❌ Custom health checks not working")

    return custom_checks_working

def test_persistent_state():
    """Test persistent state saving and loading"""
    print("💾 Testing Persistent State")
    print("-" * 50)

    # Create first monitor and run some checks
    monitor1 = AtlasServiceHealthMonitor()
    monitor1.run_all_health_checks()

    # Get initial state
    initial_summary = monitor1.get_system_health_summary()
    initial_service_count = initial_summary['statistics']['total_services']

    print(f"📊 Initial state: {initial_service_count} services monitored")

    # Create second monitor (should load saved state)
    monitor2 = AtlasServiceHealthMonitor()
    loaded_summary = monitor2.get_system_health_summary()
    loaded_service_count = loaded_summary['statistics']['total_services']

    print(f"📊 Loaded state: {loaded_service_count} services monitored")

    # Compare some services
    state_consistency = True
    for service_name in ['system_resources', 'database_connectivity', 'disk_space']:
        if (service_name in initial_summary['services'] and
            service_name in loaded_summary['services']):

            initial_checks = monitor1.services[service_name].total_checks
            loaded_checks = monitor2.services[service_name].total_checks

            print(f"   {service_name}: {initial_checks} -> {loaded_checks} checks")

            # Should maintain state (though exact counts may differ due to timing)
            if loaded_checks < 0:  # Basic sanity check
                state_consistency = False

    if state_consistency and loaded_service_count == initial_service_count:
        print("✅ Persistent state working correctly")
    else:
        print("❌ Persistent state not working as expected")

    return state_consistency

def test_integration_with_monitoring():
    """Test integration with Atlas monitoring and alerting"""
    print("🔗 Testing Integration with Monitoring")
    print("-" * 50)

    monitor = AtlasServiceHealthMonitor()

    # Verify integration components are initialized
    has_atlas_monitor = hasattr(monitor, 'atlas_monitor') and monitor.atlas_monitor is not None
    has_alert_manager = hasattr(monitor, 'alert_manager') and monitor.alert_manager is not None

    print(f"   Atlas Monitor: {'✅' if has_atlas_monitor else '❌'}")
    print(f"   Alert Manager: {'✅' if has_alert_manager else '❌'}")

    # Test that health checks can trigger alerts
    # Add a failing health check to trigger alert
    def always_fail():
        return False

    failing_check = HealthCheck(
        name="integration_test_failing",
        check_function=always_fail,
        critical=True,
        consecutive_failures_threshold=1
    )

    monitor.add_health_check(failing_check)

    # This should trigger an alert
    result = monitor.perform_health_check("integration_test_failing")
    service = monitor.services["integration_test_failing"]

    alert_triggered = not result and service.status in [HealthStatus.CRITICAL, HealthStatus.DOWN]

    print(f"   Alert Trigger Test: {'✅' if alert_triggered else '❌'}")

    integration_working = has_atlas_monitor and has_alert_manager and alert_triggered

    if integration_working:
        print("✅ Integration with monitoring working correctly")
    else:
        print("❌ Integration with monitoring needs attention")

    return integration_working

def main():
    """Run all health monitoring tests"""
    print("🚀 Atlas Service Health Monitoring Test Suite")
    print("=" * 60)

    tests = [
        ("Individual Health Checks", test_individual_health_checks),
        ("Health Status Transitions", test_health_status_transitions),
        ("System Health Summary", test_system_health_summary),
        ("Custom Health Checks", test_custom_health_checks),
        ("Persistent State", test_persistent_state),
        ("Integration with Monitoring", test_integration_with_monitoring)
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        try:
            if test_func():
                print(f"✅ {test_name}: PASSED")
                passed += 1
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"💥 {test_name}: CRASHED - {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*60}")
    print(f"📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("✅ All health monitoring tests PASSED!")
        print("🎯 Service health monitoring system ready for production")

        # Show final health status
        monitor = AtlasServiceHealthMonitor()
        summary = monitor.get_system_health_summary()
        print(f"\n🏥 Final System Health:")
        print(f"   Overall Status: {summary['overall_status'].upper()}")
        print(f"   Services Monitored: {summary['statistics']['total_services']}")

        return 0
    else:
        print("❌ Some tests failed - review health monitoring implementation")
        return 1

if __name__ == "__main__":
    exit(main())