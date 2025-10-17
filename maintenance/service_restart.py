#!/usr/bin/env python3
"""
Atlas Service Restart Script

This script provides functionality to restart Atlas services.
"""

import os
import sys
import subprocess
from datetime import datetime

def restart_service(service_name):
    """Restart a service"""
    print(f"Restarting service: {service_name}")

    try:
        # Stop service
        subprocess.run(["sudo", "systemctl", "stop", service_name],
                      check=True, capture_output=True)
        print(f"Service {service_name} stopped")

        # Wait a moment
        import time
        time.sleep(2)

        # Start service
        subprocess.run(["sudo", "systemctl", "start", service_name],
                      check=True, capture_output=True)
        print(f"Service {service_name} started")

        # Log restart
        log_file = "/home/ubuntu/dev/atlas/logs/service_restarts.log"
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

        with open(log_file, "a") as f:
            f.write(f"{datetime.now()}: {service_name} restarted\n")

        return True
    except subprocess.CalledProcessError as e:
        print(f"Error restarting service {service_name}: {e}")
        return False

def restart_all_services():
    """Restart all Atlas services"""
    print("Restarting all Atlas services...")

    services = [
        "atlas",
        "prometheus",
        "grafana-server",
        "nginx"
    ]

    results = []

    for service in services:
        result = restart_service(service)
        results.append((service, result))

    # Print summary
    print("\n" + "=" * 40)
    print("Restart Summary:")
    print("=" * 40)

    all_success = True
    for service, success in results:
        status = "SUCCESS" if success else "FAILED"
        print(f"{service}: {status}")
        if not success:
            all_success = False

    if all_success:
        print("\nAll services restarted successfully!")
    else:
        print("\nSome services failed to restart.")

    return all_success

def main():
    """Main restart function"""
    if len(sys.argv) > 1:
        service_name = sys.argv[1]
        restart_service(service_name)
    else:
        restart_all_services()

if __name__ == "__main__":
    main()
