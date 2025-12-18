#!/usr/bin/env python3
"""
Atlas Error Reporter - Quick error analysis for Atlas system
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter, defaultdict


def analyze_recent_errors(hours=24):
    """Analyze errors from the last N hours"""
    error_log_path = Path("output/error_log.jsonl")

    if not error_log_path.exists():
        print("✅ No error log found - system is clean!")
        return

    cutoff_time = datetime.now() - timedelta(hours=hours)
    recent_errors = []

    try:
        with open(error_log_path, "r") as f:
            for line in f:
                if line.strip():
                    try:
                        error = json.loads(line.strip())
                        error_time = datetime.fromisoformat(
                            error["timestamp"].replace("Z", "+00:00")
                        )
                        if error_time.replace(tzinfo=None) > cutoff_time:
                            recent_errors.append(error)
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue
    except Exception as e:
        print(f"❌ Error reading log file: {e}")
        return

    if not recent_errors:
        print(f"✅ No errors in the last {hours} hours - system is clean!")
        return

    print(f"⚠️  Found {len(recent_errors)} errors in the last {hours} hours\n")

    # Group by category and severity
    by_category = Counter(error.get("category", "unknown") for error in recent_errors)
    by_severity = Counter(error.get("severity", "unknown") for error in recent_errors)
    by_module = Counter(error.get("module", "unknown") for error in recent_errors)

    print("📊 Error Summary:")
    print(f"   Categories: {dict(by_category)}")
    print(f"   Severities: {dict(by_severity)}")
    print(f"   Modules: {dict(by_module)}")
    print()

    # Show common error patterns
    error_patterns = defaultdict(list)
    for error in recent_errors:
        pattern = error.get("message", "").split(":")[
            0
        ]  # Get first part of error message
        error_patterns[pattern].append(error)

    print("🔍 Common Error Patterns:")
    for pattern, errors in sorted(
        error_patterns.items(), key=lambda x: len(x[1]), reverse=True
    ):
        count = len(errors)
        latest = errors[-1]
        print(f"   {pattern}: {count} occurrences")
        print(
            f"      Latest: {latest.get('url', 'No URL')} ({latest.get('module', 'unknown')})"
        )
    print()

    # Show recent critical errors (if any)
    critical_errors = [
        e for e in recent_errors if e.get("severity") in ["high", "critical"]
    ]
    if critical_errors:
        print("🚨 CRITICAL ERRORS (need attention):")
        for error in critical_errors[-5:]:  # Show last 5 critical
            print(f"   {error.get('timestamp')}: {error.get('message')}")
            if error.get("url"):
                print(f"      URL: {error['url']}")
        print()

    # Show recommendations
    youtube_errors = len(
        [e for e in recent_errors if e.get("module") == "youtube_ingestor"]
    )
    total_errors = len(recent_errors)

    print("💡 Recommendations:")
    if youtube_errors > total_errors * 0.8:
        print(
            "   • Most errors are YouTube-related - this is normal (videos get blocked/deleted)"
        )
        print("   • Consider: YouTube API key for better access (optional)")
    if any(e.get("severity") == "high" for e in recent_errors):
        print("   • Some high-severity errors detected - review above critical errors")
    else:
        print("   • All errors are minor - system is handling them gracefully")
    print("   • Errors are logged for retry - no manual action needed")


def show_error_stats():
    """Show overall error statistics"""
    error_log_path = Path("output/error_log.jsonl")

    if not error_log_path.exists():
        print("✅ No error log found - system is pristine!")
        return

    total_lines = 0
    try:
        with open(error_log_path, "r") as f:
            total_lines = sum(1 for line in f if line.strip())
    except Exception as e:
        print(f"❌ Error reading log file: {e}")
        return

    print(f"📈 Total errors logged: {total_lines}")
    print("   (This includes all retryable errors - most resolve automatically)")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--stats":
            show_error_stats()
        elif sys.argv[1].startswith("--hours="):
            hours = int(sys.argv[1].split("=")[1])
            analyze_recent_errors(hours)
        else:
            print("Usage: python atlas_errors.py [--stats] [--hours=24]")
    else:
        analyze_recent_errors()
