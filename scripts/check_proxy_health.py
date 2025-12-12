#!/usr/bin/env python3
"""
Proxy Health Check and VPN Rotation

Checks if the gluetun HTTP proxy is working.
If YouTube is blocked or proxy is down, rotates to a new VPN server.

Usage:
    python scripts/check_proxy_health.py           # Check only
    python scripts/check_proxy_health.py --rotate  # Force rotation
    python scripts/check_proxy_health.py --fix     # Check and fix if needed
"""

import argparse
import subprocess
import sys
import time
import requests


PROXY_URL = "http://localhost:8118"
TEST_URL = "https://www.youtube.com"
GLUETUN_API = "http://localhost:8000"  # Gluetun control API

# Regions to rotate through if blocked
VPN_REGIONS = [
    "United States",
    "Canada",
    "United Kingdom",
    "Germany",
    "Netherlands",
    "Switzerland",
]


def check_proxy_health():
    """Check if proxy is working and can reach YouTube."""
    try:
        # Test basic proxy connectivity
        response = requests.get(
            TEST_URL,
            proxies={"http": PROXY_URL, "https": PROXY_URL},
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0"}
        )

        if response.status_code == 200:
            # Check for YouTube block page indicators
            content = response.text.lower()
            # More specific checks - avoid false positives from client config
            if "unusual traffic from your computer" in content:
                return False, "YouTube is showing unusual traffic warning"
            if "to continue, please solve the" in content and "captcha" in content:
                return False, "YouTube is showing CAPTCHA"
            if "please verify you are a human" in content:
                return False, "YouTube is asking for human verification"
            return True, f"Proxy healthy (status {response.status_code})"
        else:
            return False, f"Bad status code: {response.status_code}"

    except requests.exceptions.ProxyError as e:
        return False, f"Proxy unreachable: {e}"
    except requests.exceptions.Timeout:
        return False, "Request timed out"
    except Exception as e:
        return False, f"Error: {e}"


def get_current_ip():
    """Get current VPN IP address."""
    try:
        response = requests.get(
            "https://api.ipify.org?format=json",
            proxies={"http": PROXY_URL, "https": PROXY_URL},
            timeout=10
        )
        return response.json().get("ip", "unknown")
    except:
        return "unknown"


def rotate_vpn_server(region=None):
    """Rotate to a new VPN server via docker restart."""
    print(f"Rotating VPN server...")

    if region:
        # Update region in gluetun
        print(f"  Setting region to: {region}")
        # This requires modifying the docker compose and restarting
        # For now, just restart to get a new server in same region

    # Restart gluetun container
    result = subprocess.run(
        ["docker", "restart", "gluetun"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"  Failed to restart gluetun: {result.stderr}")
        return False

    # Wait for VPN to reconnect
    print("  Waiting for VPN to reconnect...")
    time.sleep(30)

    # Check new IP
    new_ip = get_current_ip()
    print(f"  New IP: {new_ip}")

    return True


def main():
    parser = argparse.ArgumentParser(description="Check and fix VPN proxy health")
    parser.add_argument("--rotate", action="store_true", help="Force VPN rotation")
    parser.add_argument("--fix", action="store_true", help="Check and fix if needed")
    parser.add_argument("--quiet", "-q", action="store_true", help="Only output on failure")
    args = parser.parse_args()

    # Force rotation
    if args.rotate:
        current_ip = get_current_ip()
        print(f"Current IP: {current_ip}")
        if rotate_vpn_server():
            print("✅ VPN rotated successfully")
            sys.exit(0)
        else:
            print("❌ VPN rotation failed")
            sys.exit(1)

    # Health check
    healthy, message = check_proxy_health()
    current_ip = get_current_ip()

    if healthy:
        if not args.quiet:
            print(f"✅ Proxy healthy")
            print(f"   IP: {current_ip}")
            print(f"   {message}")
        sys.exit(0)
    else:
        print(f"❌ Proxy unhealthy")
        print(f"   IP: {current_ip}")
        print(f"   {message}")

        if args.fix:
            print("\nAttempting to fix...")
            if rotate_vpn_server():
                # Re-check after rotation
                time.sleep(5)
                healthy, message = check_proxy_health()
                if healthy:
                    print("✅ Fixed! Proxy now healthy")
                    sys.exit(0)
                else:
                    print(f"❌ Still unhealthy after rotation: {message}")
                    sys.exit(1)
            else:
                print("❌ Failed to rotate VPN")
                sys.exit(1)

        sys.exit(1)


if __name__ == "__main__":
    main()
