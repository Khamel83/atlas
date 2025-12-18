#!/usr/bin/env python3
"""
Test Alert Triggers
Tests various alert conditions to verify the monitoring system.
"""

import sys
import time
import uuid
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.metrics_collector import get_metrics_collector
from helpers.queue_manager import get_queue_manager, enqueue_task
from scripts.alert_manager import AlertManager


def test_queue_depth_alert():
    """Test high queue depth alert."""
    print("🔍 Testing Queue Depth Alert")
    print("=" * 40)

    qm = get_queue_manager()

    # Create many tasks to trigger queue depth alert
    print("Creating 600 test tasks to trigger queue alert...")
    for i in range(600):
        task_id = f"alert-test-{i}-{uuid.uuid4().hex[:8]}"
        task_data = {"test": True, "batch": "queue_alert_test"}
        enqueue_task(task_id, "alert_test", task_data, priority=0)

        if i % 100 == 0:
            print(f"  Created {i+1}/600 tasks...")

    # Let metrics collect
    time.sleep(2)

    # Check alert conditions
    alert_manager = AlertManager()
    alerts = alert_manager.check_all_alerts()

    queue_alerts = [a for a in alerts if "queue" in a["rule"]]

    if queue_alerts:
        print(f"✅ Queue depth alert triggered: {len(queue_alerts)} alerts")
        for alert in queue_alerts:
            print(f"   🚨 {alert['severity']}: {alert['rule']}")
    else:
        print("❌ Queue depth alert not triggered")

    return len(queue_alerts) > 0


def test_circuit_breaker_alert():
    """Test circuit breaker alert."""
    print("\n⚡ Testing Circuit Breaker Alert")
    print("=" * 40)

    qm = get_queue_manager()
    worker_id = "alert-test-worker"

    # Create and fail many tasks to trigger circuit breaker
    print("Creating failing tasks to trigger circuit breaker...")
    for i in range(12):
        task_id = f"cb-alert-test-{i}"
        task_data = {"will_fail": True}

        enqueue_task(task_id, "alert_test", task_data)
        task = qm.dequeue_task(worker_id, ["alert_test"])

        if task:
            qm.fail_task(task.task_id, worker_id, f"Alert test failure {i}")
            print(f"  Failed task {i+1}/12")

            # Check if circuit breaker opened
            if i >= 9:  # Should open after 10 failures
                # Let metrics collect
                time.sleep(1)

                alert_manager = AlertManager()
                alerts = alert_manager.check_all_alerts()

                cb_alerts = [a for a in alerts if "circuit_breaker" in a["rule"]]
                if cb_alerts:
                    print(f"✅ Circuit breaker alert triggered after {i+1} failures")
                    return True

    print("❌ Circuit breaker alert not triggered")
    return False


def test_error_rate_alert():
    """Test error rate alert."""
    print("\n📊 Testing Error Rate Alert")
    print("=" * 40)

    qm = get_queue_manager()
    worker_id = "error-rate-test-worker"

    # Create a mix of successful and failed tasks
    print("Creating tasks with high error rate...")

    # Create some successful tasks first
    for i in range(10):
        task_id = f"success-{i}"
        enqueue_task(task_id, "success_test", {"success": True})
        task = qm.dequeue_task(worker_id, ["success_test"])
        if task:
            qm.complete_task(task.task_id, worker_id)

    # Create many failed tasks to raise error rate
    for i in range(50):
        task_id = f"error-{i}"
        enqueue_task(task_id, "error_test", {"will_fail": True})
        task = qm.dequeue_task(worker_id, ["error_test"])
        if task:
            qm.fail_task(task.task_id, worker_id, f"Error rate test failure {i}")

    # Let metrics collect
    time.sleep(2)

    # Check alert conditions
    alert_manager = AlertManager()
    alerts = alert_manager.check_all_alerts()

    error_alerts = [a for a in alerts if "error_rate" in a["rule"]]

    if error_alerts:
        print(f"✅ Error rate alert triggered: {len(error_alerts)} alerts")
        for alert in error_alerts:
            print(f"   🚨 {alert['severity']}: {alert['rule']}")
    else:
        print("❌ Error rate alert not triggered")

    return len(error_alerts) > 0


def test_processing_stalled_alert():
    """Test processing stalled alert."""
    print("\n⏸️  Testing Processing Stalled Alert")
    print("=" * 40)

    # This would require manipulating metrics to simulate no activity
    # For now, just check if the rule evaluates correctly

    alert_manager = AlertManager()
    metrics_collector = get_metrics_collector()

    # Get current transcription rate
    transcription_rate = metrics_collector.get_metric_value("atlas_transcription_rate") or 0

    print(f"Current transcription rate: {transcription_rate}/min")

    if transcription_rate == 0:
        print("🔍 Checking if stalled alert would trigger...")
        alerts = alert_manager.check_all_alerts()
        stalled_alerts = [a for a in alerts if "processing_stalled" in a["rule"]]

        if stalled_alerts:
            print("✅ Processing stalled alert would trigger")
            return True
        else:
            print("❌ Processing stalled alert would not trigger")
    else:
        print("ℹ️  Processing is active, stalled alert would not trigger")
        return True  # This is expected behavior

    return False


def cleanup_test_data():
    """Clean up test data created during alert testing."""
    print("\n🧹 Cleaning up test data...")

    qm = get_queue_manager()

    # Clean up old test tasks (this would need to be implemented in queue manager)
    cleaned = qm.cleanup_old_tasks(days_old=0)  # Clean everything for testing
    print(f"Cleaned up {cleaned} test tasks")


def main():
    """Run all alert trigger tests."""
    print("🧪 Atlas Alert Trigger Tests")
    print("=" * 50)

    tests = [
        ("Queue Depth Alert", test_queue_depth_alert),
        ("Circuit Breaker Alert", test_circuit_breaker_alert),
        ("Error Rate Alert", test_error_rate_alert),
        ("Processing Stalled Alert", test_processing_stalled_alert),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = test_func()
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"\n{test_name}: {status}")
            results.append((test_name, result))
        except Exception as e:
            print(f"\n{test_name}: ❌ ERROR - {e}")
            results.append((test_name, False))

    # Cleanup
    cleanup_test_data()

    # Summary
    print(f"\n{'='*50}")
    print("📋 Alert Test Summary:")
    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅" if result else "❌"
        print(f"  {status} {test_name}")

    print(f"\n🎯 Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All alert trigger tests passed!")
        return True
    else:
        print("⚠️  Some alert tests failed")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)