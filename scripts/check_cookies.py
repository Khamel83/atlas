#!/usr/bin/env python3
"""
Cookie Expiration Checker

Checks authentication cookies and sends alerts when they're about to expire.
Run daily via cron/systemd timer.

Monitored cookies:
- Stratechery (passport_token) - magic link auth
- YouTube (if using cookie auth)
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Alert thresholds (days before expiry)
WARNING_DAYS = 7
CRITICAL_DAYS = 2

# Cookie files to monitor
COOKIE_FILES = {
    'stratechery': Path.home() / '.config/atlas/stratechery_cookies.json',
    'youtube': Path.home() / '.config/atlas/youtube_cookies.txt',
    'nyt': Path.home() / '.config/atlas/cookies/nytimes.com.json',
    'dithering': Path.home() / '.config/atlas/cookies/dithering.passport.online.json',
    'asianometry': Path.home() / '.config/atlas/cookies/asianometry.passport.online.json',
}


def send_telegram_alert(message: str, critical: bool = False):
    """Send alert via Telegram"""
    try:
        from modules.notifications.telegram import TelegramNotifier

        notifier = TelegramNotifier()
        if not notifier.enabled:
            print("Telegram not configured (missing TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID)")
            return False

        prefix = "🚨 CRITICAL" if critical else "⚠️ WARNING"
        return notifier.send_message(f"{prefix}: {message}")
    except Exception as e:
        print(f"Failed to send Telegram alert: {e}")
        return False


def send_ntfy_alert(message: str, critical: bool = False):
    """Send alert via ntfy.sh"""
    import requests

    ntfy_topic = os.environ.get('NTFY_TOPIC', 'atlas-khamel-alerts')
    priority = 'urgent' if critical else 'high'

    try:
        requests.post(
            f"https://ntfy.sh/{ntfy_topic}",
            data=message.encode('utf-8'),
            headers={
                "Title": "Atlas Cookie Alert",
                "Priority": priority,
                "Tags": "warning,cookie" if not critical else "rotating_light,cookie"
            }
        )
        return True
    except Exception as e:
        print(f"Failed to send ntfy alert: {e}")
        return False


def check_json_cookies(filepath: Path, service: str) -> dict:
    """Check expiration of JSON-format cookies"""
    if not filepath.exists():
        return {
            'service': service,
            'status': 'missing',
            'message': f'{service} cookies file not found'
        }

    try:
        with open(filepath) as f:
            cookies = json.load(f)

        now = time.time()
        results = []

        for cookie in cookies:
            name = cookie.get('name', 'unknown')
            expiry = cookie.get('expirationDate', 0)

            if expiry == 0:
                # Session cookie, no expiry
                continue

            expires_at = datetime.fromtimestamp(expiry)
            days_remaining = (expires_at - datetime.now()).days

            results.append({
                'name': name,
                'expires': expires_at.isoformat(),
                'days_remaining': days_remaining
            })

        # Find the soonest expiring auth cookie
        auth_cookies = [r for r in results if 'token' in r['name'].lower() or 'session' in r['name'].lower()]

        if not auth_cookies:
            return {
                'service': service,
                'status': 'ok',
                'message': 'No auth cookies found (may be session-based)',
                'cookies': results
            }

        soonest = min(auth_cookies, key=lambda x: x['days_remaining'])

        if soonest['days_remaining'] <= CRITICAL_DAYS:
            status = 'critical'
        elif soonest['days_remaining'] <= WARNING_DAYS:
            status = 'warning'
        else:
            status = 'ok'

        return {
            'service': service,
            'status': status,
            'days_remaining': soonest['days_remaining'],
            'expires': soonest['expires'],
            'cookie_name': soonest['name'],
            'message': f"{service} auth expires in {soonest['days_remaining']} days"
        }

    except Exception as e:
        return {
            'service': service,
            'status': 'error',
            'message': f'Error checking {service} cookies: {e}'
        }


def check_netscape_cookies(filepath: Path, service: str) -> dict:
    """Check expiration of Netscape-format cookies (cookies.txt)"""
    if not filepath.exists():
        return {
            'service': service,
            'status': 'missing',
            'message': f'{service} cookies file not found'
        }

    try:
        now = time.time()
        results = []

        with open(filepath) as f:
            for line in f:
                if line.startswith('#') or not line.strip():
                    continue

                parts = line.strip().split('\t')
                if len(parts) >= 7:
                    name = parts[5]
                    expiry = int(parts[4]) if parts[4].isdigit() else 0

                    if expiry == 0:
                        continue

                    expires_at = datetime.fromtimestamp(expiry)
                    days_remaining = (expires_at - datetime.now()).days

                    results.append({
                        'name': name,
                        'expires': expires_at.isoformat(),
                        'days_remaining': days_remaining
                    })

        if not results:
            return {
                'service': service,
                'status': 'ok',
                'message': 'No expiring cookies found'
            }

        soonest = min(results, key=lambda x: x['days_remaining'])

        if soonest['days_remaining'] <= CRITICAL_DAYS:
            status = 'critical'
        elif soonest['days_remaining'] <= WARNING_DAYS:
            status = 'warning'
        else:
            status = 'ok'

        return {
            'service': service,
            'status': status,
            'days_remaining': soonest['days_remaining'],
            'expires': soonest['expires'],
            'message': f"{service} auth expires in {soonest['days_remaining']} days"
        }

    except Exception as e:
        return {
            'service': service,
            'status': 'error',
            'message': f'Error checking {service} cookies: {e}'
        }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Check cookie expiration")
    parser.add_argument("--alert", action="store_true", help="Send alerts for warnings/critical")
    parser.add_argument("--telegram", action="store_true", help="Use Telegram for alerts")
    parser.add_argument("--ntfy", action="store_true", help="Use ntfy.sh for alerts")
    args = parser.parse_args()

    results = []

    # Check Stratechery (JSON format)
    result = check_json_cookies(COOKIE_FILES['stratechery'], 'Stratechery')
    results.append(result)

    # Check YouTube (Netscape format) if exists
    if COOKIE_FILES['youtube'].exists():
        result = check_netscape_cookies(COOKIE_FILES['youtube'], 'YouTube')
        results.append(result)

    # Check NYT (JSON format) if exists
    if COOKIE_FILES['nyt'].exists():
        result = check_json_cookies(COOKIE_FILES['nyt'], 'NYT')
        results.append(result)

    # Check Dithering (JSON format) if exists
    if COOKIE_FILES['dithering'].exists():
        result = check_json_cookies(COOKIE_FILES['dithering'], 'Dithering')
        results.append(result)

    # Check Asianometry (JSON format) if exists
    if COOKIE_FILES['asianometry'].exists():
        result = check_json_cookies(COOKIE_FILES['asianometry'], 'Asianometry')
        results.append(result)

    # Print results
    print("=== Cookie Expiration Check ===\n")
    for r in results:
        status_icon = {
            'ok': '✅',
            'warning': '⚠️',
            'critical': '🚨',
            'missing': '❓',
            'error': '❌'
        }.get(r['status'], '?')

        print(f"{status_icon} {r['service']}: {r['message']}")

        if r.get('days_remaining'):
            print(f"   Days remaining: {r['days_remaining']}")
        if r.get('expires'):
            print(f"   Expires: {r['expires']}")

    # Send alerts if requested
    if args.alert:
        for r in results:
            if r['status'] in ('warning', 'critical'):
                is_critical = r['status'] == 'critical'

                if args.telegram:
                    send_telegram_alert(r['message'], critical=is_critical)
                if args.ntfy:
                    send_ntfy_alert(r['message'], critical=is_critical)

                # Default to printing if no alert method specified
                if not args.telegram and not args.ntfy:
                    print(f"\n{'🚨 ALERT' if is_critical else '⚠️ WARNING'}: {r['message']}")

    # Return exit code based on status
    statuses = [r['status'] for r in results]
    if 'critical' in statuses:
        return 2
    elif 'warning' in statuses:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
