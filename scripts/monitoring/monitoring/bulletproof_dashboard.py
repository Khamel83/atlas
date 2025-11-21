#!/usr/bin/env python3
"""
Bulletproof Process Management Dashboard
Real-time monitoring of system health
"""
import time
import json
from helpers.bulletproof_process_manager import get_manager
from helpers.resource_monitor import check_system_health

def generate_dashboard():
    """Generate system dashboard data"""
    manager = get_manager()
    status = manager.get_status()

    dashboard = {
        'timestamp': str(status['timestamp']),
        'system_health': check_system_health(),
        'processes': {
            'total': status['total_processes'],
            'running': status['running_processes'],
        },
        'resources': {
            'memory_mb': status['memory_usage_mb'],
            'cpu_percent': status['cpu_percent'],
            'open_files': status['open_files']
        },
        'circuit_breakers': status['circuit_breakers']
    }

    return dashboard

if __name__ == "__main__":
    while True:
        dashboard = generate_dashboard()
        print(f"\n🛡️ Atlas Bulletproof Dashboard - {dashboard['timestamp']}")
        print(f"System Health: {'✅' if dashboard['system_health'] else '❌'}")
        print(f"Processes: {dashboard['processes']['running']}/{dashboard['processes']['total']}")
        print(f"Memory: {dashboard['resources']['memory_mb']:.1f}MB")
        print(f"CPU: {dashboard['resources']['cpu_percent']:.1f}%")

        time.sleep(10)
