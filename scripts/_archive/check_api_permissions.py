#!/usr/bin/env python3
"""
API Permission Checker for Atlas

Runs before any Atlas process to ensure expensive APIs are properly authorized.
This prevents unexpected charges and ensures proper oversight.

Usage:
    python3 scripts/check_api_permissions.py
    # Exits with code 1 if unauthorized expensive APIs are enabled
"""

import os
import sys
import json
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define expensive services that require explicit authorization
EXPENSIVE_SERVICES = {
    "google_search": {
        "env_keys": ["GOOGLE_SEARCH_API_KEY", "GOOGLE_SEARCH_ENGINE_ID"],
        "cost": "high",
        "daily_quota": 100,
        "auth_file": "google_search_enabled"
    },
    "openai": {
        "env_keys": ["OPENAI_API_KEY"],
        "cost": "premium",
        "daily_quota": None,
        "auth_file": "openai_enabled"
    },
    "anthropic": {
        "env_keys": ["ANTHROPIC_API_KEY"],
        "cost": "premium",
        "daily_quota": None,
        "auth_file": "anthropic_enabled"
    }
}

def check_expensive_services():
    """Check if expensive services are enabled without authorization"""
    unauthorized_services = []
    config_dir = Path("/home/ubuntu/dev/atlas/config")

    # Ensure config directory exists
    config_dir.mkdir(exist_ok=True)

    for service_name, service_config in EXPENSIVE_SERVICES.items():
        # Check if any API keys for this service are set
        keys_set = []
        for key in service_config["env_keys"]:
            if os.getenv(key):
                keys_set.append(key)

        if keys_set:
            # Check if authorization file exists
            auth_file = config_dir / service_config["auth_file"]

            if not auth_file.exists():
                unauthorized_services.append({
                    "service": service_name,
                    "cost": service_config["cost"],
                    "keys_set": keys_set,
                    "auth_file": str(auth_file)
                })
            else:
                logger.info(f"✅ {service_name} authorized via {auth_file}")

    return unauthorized_services

def generate_report(unauthorized_services):
    """Generate a report of unauthorized services"""
    report = {
        "timestamp": json.dumps({"timestamp": "now"}),
        "unauthorized_services": unauthorized_services,
        "total_unauthorized": len(unauthorized_services)
    }

    return report

def disable_unauthorized_services(unauthorized_services):
    """Disable unauthorized services by removing environment variables"""
    for service in unauthorized_services:
        for key in service["keys_set"]:
            if key in os.environ:
                del os.environ[key]
                logger.info(f"🚫 Removed environment variable: {key}")

def main():
    """Main function"""
    logger.info("🔍 Checking API permissions...")

    unauthorized_services = check_expensive_services()

    if not unauthorized_services:
        logger.info("✅ All expensive services properly authorized or disabled")
        return 0

    # Generate and log report
    report = generate_report(unauthorized_services)

    logger.warning("🚨 UNAUTHORIZED EXPENSIVE SERVICES DETECTED!")
    logger.warning("=" * 50)

    for service in unauthorized_services:
        logger.warning(f"Service: {service['service']}")
        logger.warning(f"Cost Level: {service['cost']}")
        logger.warning(f"API Keys Set: {', '.join(service['keys_set'])}")
        logger.warning(f"Authorization File: {service['auth_file']} (MISSING)")
        logger.warning("-" * 30)

    # Disable the unauthorized services
    disable_unauthorized_services(unauthorized_services)

    logger.warning("🚫 Unauthorized services have been disabled")
    logger.warning("💡 To enable these services:")
    logger.warning("   1. Create authorization file: /home/ubuntu/dev/atlas/config/{service}_enabled")
    logger.warning("   2. Add reason for enabling the service")
    logger.warning("   3. Run with explicit approval")

    # Save report to file
    report_file = Path("/home/ubuntu/dev/atlas/logs/api_permission_check.json")
    report_file.parent.mkdir(exist_ok=True)

    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    logger.warning(f"📄 Report saved to: {report_file}")

    # Exit with error code to prevent processes from running
    return 1

if __name__ == "__main__":
    sys.exit(main())