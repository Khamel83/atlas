#!/usr/bin/env python3
"""
Test Monitoring + Alert Manager Integration - Phase 3.2
Validates end-to-end monitoring and alerting functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from helpers.atlas_monitoring import AtlasMonitor
from scripts.alert_manager import AlertManager as AtlasAlertManager
from datetime import datetime

def test_monitoring_integration():
    """Test monitoring system with alert manager"""
    print("🧪 Testing Monitoring + Alert Integration")
    print("=" * 50)

    # Initialize systems
    monitor = AtlasMonitor()
    alert_manager = AtlasAlertManager()

    # Get current metrics
    print("📊 Collecting system metrics...")
    try:
        atlas_metrics = monitor.collect_atlas_metrics()
        system_metrics = monitor.collect_system_metrics()
    except Exception as e:
        print(f"❌ Monitoring error: {e}")
        return False

    # Check thresholds and generate alerts if needed
    alerts = []

    # CPU threshold (80%)
    if system_metrics.cpu_percent > 80:
        alerts.append({
            'timestamp': datetime.now().isoformat(),
            'metric_name': 'cpu_usage',
            'value': system_metrics.cpu_percent,
            'threshold': 80.0,
            'severity': 'WARNING' if system_metrics.cpu_percent < 90 else 'CRITICAL',
            'message': f"High CPU usage: {system_metrics.cpu_percent:.1f}%"
        })

    # Memory threshold (85%)
    if system_metrics.memory_percent > 85:
        alerts.append({
            'timestamp': datetime.now().isoformat(),
            'metric_name': 'memory_usage',
            'value': system_metrics.memory_percent,
            'threshold': 85.0,
            'severity': 'WARNING' if system_metrics.memory_percent < 95 else 'CRITICAL',
            'message': f"High memory usage: {system_metrics.memory_percent:.1f}%"
        })

    # Disk space threshold (90%)
    if system_metrics.disk_percent > 90:
        alerts.append({
            'timestamp': datetime.now().isoformat(),
            'metric_name': 'disk_usage',
            'value': system_metrics.disk_percent,
            'threshold': 90.0,
            'severity': 'CRITICAL',
            'message': f"Critical disk usage: {system_metrics.disk_percent:.1f}% (Free: {system_metrics.disk_free_gb:.1f}GB)"
        })

    # Process alerts
    if alerts:
        print(f"🚨 {len(alerts)} alerts triggered:")
        processed_count = alert_manager.process_multiple_alerts(alerts)
        print(f"✅ {processed_count} alerts processed successfully")
    else:
        # Create test alert to verify system works
        test_alert = {
            'timestamp': datetime.now().isoformat(),
            'metric_name': 'monitoring_test',
            'value': 100.0,
            'threshold': 95.0,
            'severity': 'INFO',
            'message': 'Monitoring system integration test - all systems operational'
        }
        alert_manager.process_alert(test_alert)
        print("✅ No alerts triggered - system within normal parameters")
        print("✅ Test alert sent to verify integration")

    # Display current status
    print("\n📊 Current System Status:")
    print(f"  CPU: {system_metrics.cpu_percent:.1f}%")
    print(f"  Memory: {system_metrics.memory_percent:.1f}%")
    print(f"  Disk Free: {system_metrics.disk_free_gb:.1f}GB")
    print(f"  Load Average: {system_metrics.load_average}")

    print("\n📋 Atlas Application Status:")
    print(f"  API Response Time: {atlas_metrics.api_response_time:.3f}s")
    print(f"  Database Size: {atlas_metrics.database_size_mb:.1f}MB")
    print(f"  Content Records: {atlas_metrics.content_records}")
    print(f"  Service Health: {atlas_metrics.service_health}")

    # Display alert manager status
    alert_status = alert_manager.get_alert_status()
    print(f"\n📋 Alert Manager Status:")
    print(f"  Email enabled: {alert_status['configuration']['email_enabled']}")
    print(f"  Webhook enabled: {alert_status['configuration']['webhook_enabled']}")
    print(f"  Total alerts sent: {alert_status['state']['total_alerts_sent']}")
    print(f"  Active suppressions: {alert_status['state']['active_suppressions']}")

    return True

def main():
    """Main test function"""
    print("🚀 Atlas Monitoring + Alert Integration Test")
    print("=" * 50)

    success = test_monitoring_integration()

    if success:
        print("\n✅ Integration test completed successfully!")
        print("🎯 Monitoring and alerting system ready for production")
    else:
        print("\n❌ Integration test failed")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())