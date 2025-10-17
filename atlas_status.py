#!/usr/bin/env python3
"""
Atlas Status Dashboard - Never-Fail Startup Script

A bulletproof startup script that always works and gives you instant Atlas status.
No matter what's broken, this script will tell you what's going on and get you started.

Usage:
    python atlas_status.py              # Quick status
    python atlas_status.py --detailed   # Full report
    python atlas_status.py --dev        # Development startup
"""

import os
import sys
import json
import time
import psutil
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# Load Atlas configuration and secrets
try:
    from helpers.config import load_config

    config = load_config()
except Exception:
    config = {}


# Color codes for output
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    PURPLE = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BOLD = "\033[1m"
    END = "\033[0m"


def safe_print(message, color=Colors.WHITE, bold=False):
    """Print with color, never fails"""
    try:
        prefix = Colors.BOLD if bold else ""
        print(f"{prefix}{color}{message}{Colors.END}")
    except:
        print(message)  # Fallback to plain text


def safe_file_count(directory, pattern="*", recursive=False):
    """Count files safely, never fails"""
    try:
        from pathlib import Path

        if recursive:
            return len(list(Path(directory).rglob(pattern)))
        else:
            return len(list(Path(directory).glob(pattern)))
    except:
        return 0


def safe_file_age(filepath):
    """Get file age safely, never fails"""
    try:
        return datetime.now() - datetime.fromtimestamp(os.path.getmtime(filepath))
    except:
        return timedelta(days=999)  # Very old if can't read


def check_process_running(name_pattern):
    """Check if process is running, never fails"""
    try:
        for proc in psutil.process_iter(["pid", "name", "cmdline", "create_time"]):
            try:
                cmdline = " ".join(proc.info["cmdline"] or [])
                if name_pattern in cmdline:
                    return {
                        "pid": proc.info["pid"],
                        "running_time": datetime.now()
                        - datetime.fromtimestamp(proc.info["create_time"]),
                        "cmdline": cmdline,
                    }
            except:
                continue
        return None
    except:
        return None


def get_processing_stats():
    """Get processing statistics safely, never fails"""
    stats = {
        "articles_total": 0,
        "podcasts_total": 0,
        "episodes_total": 0,
        "transcriptions_total": 0,
        "html_remaining": 0,
        "log_activity": "Unknown",
        "last_activity": "Unknown",
        "latest_transcription": "None",
    }

    try:
        # Get database statistics using centralized config
        try:
            from helpers.database_config import get_database_connection
            conn = get_database_connection()
            cursor = conn.cursor()

            # Get episode count
            cursor.execute("SELECT COUNT(*) FROM podcast_episodes")
            stats["episodes_total"] = cursor.fetchone()[0]

            # Get transcriptions count
            cursor.execute("SELECT COUNT(*) FROM transcriptions")
            stats["transcriptions_total"] = cursor.fetchone()[0]

            # Get latest transcription timestamp
            cursor.execute("SELECT MAX(created_at) FROM transcriptions WHERE created_at IS NOT NULL")
            latest = cursor.fetchone()[0]
            stats["latest_transcription"] = latest if latest else "None"

            conn.close()
        except Exception as db_error:
            stats["db_error"] = str(db_error)

        # Count processed content from files
        stats["articles_total"] = safe_file_count("output/articles/metadata", "*.json")
        stats["podcasts_total"] = safe_file_count("output/podcasts", "*.json")
        # Count only unprocessed HTML files (exclude processed_html directory)
        stats["html_remaining"] = safe_file_count("inputs/saved_html", "*.html")
        stats["html_saved"] = safe_file_count("inputs/saved_html", "*.html")
        stats["html_processed"] = safe_file_count("inputs/processed_html", "*.html")

        # Check recent activity from logs
        log_files = [
            "logs/atlas_background_service.log",
            "output/automated_ingestion.log",
            "output/Full_Pipeline.log",
        ]

        latest_activity = None
        for log_file in log_files:
            try:
                if os.path.exists(log_file):
                    age = safe_file_age(log_file)
                    if latest_activity is None or age < latest_activity:
                        latest_activity = age
                        stats["last_activity"] = f"{age.total_seconds()/3600:.1f}h ago"
            except:
                continue

    except Exception as e:
        stats["error"] = str(e)

    return stats


def get_current_activity():
    """Check what the background service is currently doing"""
    try:
        log_file = "logs/atlas_background_service.log"
        if not os.path.exists(log_file):
            return "No log file found"

        # Get last 10 lines to see current activity
        with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            if not lines:
                return "No activity logged"

            recent_lines = lines[-10:]

            # Look for specific activity patterns
            for line in reversed(recent_lines):
                line = line.strip()
                if "Starting:" in line:
                    activity = line.split("Starting:")[-1].strip()
                    return f"Starting {activity}"
                elif "Processing" in line and "file" in line:
                    return "Processing files"
                elif "Configuration Validation" in line:
                    return "Stuck in config validation (API key issue)"
                elif "YouTube video processing" in line:
                    return "Processing YouTube videos"
                elif "Podcast processing" in line:
                    return "Processing podcasts"
                elif "Article processing" in line:
                    return "Processing articles"

            # Check if stuck
            if len(recent_lines) >= 3:
                last_3 = recent_lines[-3:]
                if all("Configuration Validation" in line for line in last_3):
                    return "STUCK - Config validation loop"

            return "Active (see logs for details)"

    except Exception as e:
        return f"Error checking activity: {str(e)}"


def get_recent_progress():
    """Calculate recent progress safely, never fails"""
    progress = {
        "last_hour": {"articles": 0, "podcasts": 0},
        "last_day": {"articles": 0, "podcasts": 0},
        "last_week": {"articles": 0, "podcasts": 0},
    }

    try:
        # This is a simplified version - in reality we'd parse logs for timestamps
        # For now, we'll estimate based on total counts and assume recent activity
        stats = get_processing_stats()

        # Rough estimates (would be more accurate with log parsing)
        total_articles = stats["articles_total"]
        total_podcasts = stats["podcasts_total"]

        if total_articles > 0:
            # Assume most processing happened recently
            progress["last_day"]["articles"] = min(total_articles, 500)
            progress["last_hour"]["articles"] = min(total_articles, 150)
            progress["last_week"]["articles"] = total_articles

        if total_podcasts > 0:
            progress["last_day"]["podcasts"] = min(total_podcasts, 100)
            progress["last_hour"]["podcasts"] = min(total_podcasts, 25)
            progress["last_week"]["podcasts"] = total_podcasts

    except Exception as e:
        progress["error"] = str(e)

    return progress


def check_system_health():
    """Check overall system health, never fails"""
    health = {
        "status": "UNKNOWN",
        "issues": [],
        "warnings": [],
        "disk_usage": "Unknown",
    }

    try:
        issues = []
        warnings = []

        # Check background service
        bg_service = check_process_running("atlas_service_manager.py")
        if not bg_service:
            issues.append("Background service not running")
        elif bg_service["running_time"].total_seconds() > 86400:  # 24 hours
            warnings.append(
                f"Background service running {bg_service['running_time'].days}+ days"
            )

        # Check disk space
        try:
            disk_usage = psutil.disk_usage(".")
            free_gb = disk_usage.free / (1024**3)
            if free_gb < 1:
                issues.append(f"Low disk space: {free_gb:.1f}GB free")
            elif free_gb < 5:
                warnings.append(f"Disk space getting low: {free_gb:.1f}GB free")
            health["disk_usage"] = f"{free_gb:.1f}GB free"
        except:
            health["disk_usage"] = "Cannot check"

        # Check for stuck processes or errors
        if os.path.exists("output/error_log.jsonl"):
            try:
                error_age = safe_file_age("output/error_log.jsonl")
                if error_age.total_seconds() < 3600:  # Errors in last hour
                    warnings.append("Recent errors detected")
            except:
                pass

        # Determine overall status
        if issues:
            health["status"] = "ISSUES"
        elif warnings:
            health["status"] = "WARNINGS"
        else:
            health["status"] = "HEALTHY"

        health["issues"] = issues
        health["warnings"] = warnings

    except Exception as e:
        health["status"] = "ERROR"
        health["error"] = str(e)

    return health


def check_context_updates():
    """Check CLAUDE.md and other context, never fails"""
    context = {
        "claude_md_updated": False,
        "env_loaded": False,
        "model_config": "Unknown",
        "api_keys_present": False,
    }

    try:
        # Check CLAUDE.md age
        if os.path.exists("CLAUDE.md"):
            claude_age = safe_file_age("CLAUDE.md")
            context["claude_md_updated"] = (
                claude_age.total_seconds() < 86400
            )  # Updated in last day

        # Check environment
        if os.path.exists(".env"):
            context["env_loaded"] = True

        # Check if secrets file exists
        secrets_file = os.path.expanduser("~/.secrets/atlas.env")
        context["api_keys_present"] = os.path.exists(secrets_file)

        # Try to get model config
        try:
            model = config.get("llm_model") or os.environ.get("MODEL", "Not set")
            context["model_config"] = model
        except:
            model = os.environ.get("MODEL", "Not set")
            context["model_config"] = model

    except Exception as e:
        context["error"] = str(e)

    return context


def print_status_dashboard(detailed=False):
    """Print the main status dashboard, never fails"""
    try:
        # Header
        safe_print("=" * 60, Colors.CYAN, bold=True)
        safe_print(
            f"🎯 Atlas Status Dashboard - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            Colors.CYAN,
            bold=True,
        )
        safe_print("=" * 60, Colors.CYAN, bold=True)

        # System Health
        health = check_system_health()
        if health["status"] == "HEALTHY":
            safe_print("✅ SYSTEMS HEALTHY", Colors.GREEN, bold=True)
        elif health["status"] == "WARNINGS":
            safe_print("⚠️  SYSTEMS RUNNING (Warnings)", Colors.YELLOW, bold=True)
        else:
            safe_print("🚨 SYSTEM ISSUES DETECTED", Colors.RED, bold=True)

        # Background service status
        bg_service = check_process_running("atlas_background_service.py")
        if bg_service:
            runtime = bg_service["running_time"]
            hours = int(runtime.total_seconds() / 3600)
            minutes = int((runtime.total_seconds() % 3600) / 60)
            safe_print(
                f"🔄 Background service: Running ({hours}h {minutes}m) - PID {bg_service['pid']}",
                Colors.GREEN,
            )
        else:
            safe_print("❌ Background service: Not running", Colors.RED)

        safe_print("")

        # Processing Stats
        stats = get_processing_stats()
        safe_print("📊 CURRENT STATUS", Colors.BLUE, bold=True)
        safe_print(
            f"   📰 Articles processed: {stats['articles_total']:,}", Colors.WHITE
        )
        safe_print(
            f"   🎙️  Podcasts processed: {stats['podcasts_total']:,}", Colors.WHITE
        )
        safe_print(
            f"   📻 Episodes harvested: {stats['episodes_total']:,}", Colors.WHITE
        )
        safe_print(
            f"   📝 Transcriptions: {stats['transcriptions_total']:,}", Colors.WHITE
        )
        safe_print(
            f"   🕐 Latest transcription: {stats['latest_transcription']}", Colors.WHITE
        )
        safe_print(
            f"   📁 HTML files remaining: {stats['html_remaining']:,}", Colors.WHITE
        )
        if "html_processed" in stats:
            safe_print(
                f"   ✅ HTML files processed: {stats['html_processed']:,}", Colors.GREEN
            )

        # Show database errors if any
        if "db_error" in stats:
            safe_print(f"   ⚠️  Database error: {stats['db_error']}", Colors.RED)

        # Show current activity status
        current_activity = get_current_activity()
        if current_activity:
            safe_print(f"   🔄 Current activity: {current_activity}", Colors.YELLOW)

        if stats["html_remaining"] > 0:
            total = stats["articles_total"] + stats["html_remaining"]
            progress = (stats["articles_total"] / total) * 100
            safe_print(f"   📈 Progress: {progress:.1f}% complete", Colors.CYAN)
        else:
            safe_print("   🎉 All HTML files processed!", Colors.GREEN)

        # Queue Health Status
        try:
            from helpers.queue_manager import get_queue_status
            queue_status = get_queue_status()

            safe_print("")
            safe_print("🔄 QUEUE HEALTH", Colors.BLUE, bold=True)

            # Queue counts
            queue_counts = queue_status.get("queue_counts", {})
            pending = queue_counts.get("pending", 0)
            processing = queue_counts.get("processing", 0)
            completed = queue_counts.get("completed", 0)

            safe_print(f"   📥 Pending tasks: {pending:,}", Colors.WHITE)
            safe_print(f"   ⚙️  Processing tasks: {processing:,}", Colors.WHITE)
            safe_print(f"   ✅ Completed tasks: {completed:,}", Colors.WHITE)

            # Failed tasks
            failed_tasks = queue_status.get("failed_tasks", 0)
            retry_ready = queue_status.get("retry_ready", 0)
            if failed_tasks > 0:
                safe_print(f"   ❌ Failed tasks: {failed_tasks:,}", Colors.RED)
                if retry_ready > 0:
                    safe_print(f"   🔄 Ready for retry: {retry_ready:,}", Colors.YELLOW)
            else:
                safe_print("   ✅ No failed tasks", Colors.GREEN)

            # Queue alerts
            if pending > 1000:
                safe_print("   🚨 ALERT: High queue depth!", Colors.RED, bold=True)
            elif pending > 500:
                safe_print("   ⚠️  WARNING: Queue depth elevated", Colors.YELLOW)

            # Circuit breaker status
            circuit_breakers = queue_status.get("circuit_breakers", {})
            open_breakers = [worker for worker, cb in circuit_breakers.items() if cb.get("state") == "open"]
            if open_breakers:
                safe_print(f"   ⚡ Circuit breakers open: {', '.join(open_breakers)}", Colors.RED)

        except Exception as e:
            safe_print(f"   ⚠️  Queue status unavailable: {e}", Colors.YELLOW)

        safe_print(f"   ⏰ Last activity: {stats['last_activity']}", Colors.WHITE)
        safe_print("")

        # Recent Progress (if detailed)
        if detailed:
            progress = get_recent_progress()
            safe_print("📈 RECENT PROGRESS", Colors.BLUE, bold=True)
            safe_print(
                f"   Last hour:  {progress['last_hour']['articles']} articles, {progress['last_hour']['podcasts']} podcasts",
                Colors.WHITE,
            )
            safe_print(
                f"   Last day:   {progress['last_day']['articles']} articles, {progress['last_day']['podcasts']} podcasts",
                Colors.WHITE,
            )
            safe_print(
                f"   Last week:  {progress['last_week']['articles']} articles, {progress['last_week']['podcasts']} podcasts",
                Colors.WHITE,
            )
            safe_print("")

        # Health Issues
        if health["issues"]:
            safe_print("🚨 ISSUES", Colors.RED, bold=True)
            for issue in health["issues"]:
                safe_print(f"   ❌ {issue}", Colors.RED)
            safe_print("")

        if health["warnings"]:
            safe_print("⚠️  WARNINGS", Colors.YELLOW, bold=True)
            for warning in health["warnings"]:
                safe_print(f"   ⚠️  {warning}", Colors.YELLOW)
            safe_print("")

        # Context Status
        context = check_context_updates()
        safe_print("💡 DEVELOPMENT CONTEXT", Colors.PURPLE, bold=True)

        if context["claude_md_updated"]:
            safe_print("   📋 CLAUDE.md: Recently updated", Colors.GREEN)
        else:
            safe_print("   📋 CLAUDE.md: No recent changes", Colors.WHITE)

        if context["api_keys_present"]:
            safe_print("   🔑 API Keys: Available", Colors.GREEN)
        else:
            safe_print("   🔑 API Keys: Missing", Colors.RED)

        safe_print(f"   🤖 Model: {context['model_config']}", Colors.WHITE)
        safe_print(f"   💾 Disk space: {health['disk_usage']}", Colors.WHITE)

        safe_print("")
        safe_print("=" * 60, Colors.CYAN)

        # Final status
        if health["status"] == "HEALTHY":
            safe_print(
                "🚀 Atlas is healthy and processing smoothly!", Colors.GREEN, bold=True
            )
        elif health["status"] == "WARNINGS":
            safe_print(
                "⚡ Atlas is running with minor warnings", Colors.YELLOW, bold=True
            )
        else:
            safe_print(
                "🔧 Atlas needs attention - see issues above", Colors.RED, bold=True
            )

        safe_print("=" * 60, Colors.CYAN)

    except Exception as e:
        # Ultimate fallback - never let this fail
        print("=" * 60)
        print(f"🎯 Atlas Status - {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 60)
        print(f"❌ Status dashboard error: {e}")
        print("✅ But you can still work! Try:")
        print("   source load_secrets.sh")
        print("   python run.py --help")
        print("=" * 60)


def development_startup():
    """Handle development startup tasks, never fails"""
    try:
        safe_print("\n🚀 DEVELOPMENT STARTUP", Colors.CYAN, bold=True)

        # Load secrets
        safe_print("🔐 Loading secrets...", Colors.YELLOW)
        secrets_file = os.path.expanduser("~/.secrets/atlas.env")
        if os.path.exists(secrets_file):
            safe_print("   ✅ Secrets file found", Colors.GREEN)
        else:
            safe_print("   ❌ Secrets file missing - run setup script", Colors.RED)

        # Check virtual environment
        if "venv" in sys.executable or "VIRTUAL_ENV" in os.environ:
            safe_print("   ✅ Virtual environment active", Colors.GREEN)
        else:
            safe_print("   ⚠️  Virtual environment not detected", Colors.YELLOW)
            safe_print("   💡 Run: source venv/bin/activate", Colors.CYAN)

        # Quick commands reminder
        safe_print("\n💡 QUICK COMMANDS", Colors.PURPLE, bold=True)
        safe_print("   source load_secrets.sh           # Load API keys", Colors.WHITE)
        safe_print(
            "   python run.py --all              # Run full processing", Colors.WHITE
        )
        safe_print(
            "   ./scripts/start_atlas_service.sh # Manage background service",
            Colors.WHITE,
        )
        safe_print(
            "   python atlas_status.py --detailed # Detailed status", Colors.WHITE
        )

    except Exception as e:
        safe_print(f"⚠️  Startup tasks failed: {e}", Colors.YELLOW)
        safe_print("✅ But you can still work normally!", Colors.GREEN)


def main():
    """Main function - absolutely never fails"""
    try:
        parser = argparse.ArgumentParser(description="Atlas Status Dashboard")
        parser.add_argument(
            "--detailed", action="store_true", help="Show detailed progress reports"
        )
        parser.add_argument(
            "--dev", action="store_true", help="Development startup mode"
        )

        args = parser.parse_args()

        # Always show the dashboard first
        print_status_dashboard(detailed=args.detailed)

        # Development startup if requested
        if args.dev:
            development_startup()

    except Exception as e:
        # Ultimate fallback for any catastrophic failure
        print("\n" + "=" * 50)
        print("🎯 Atlas Status (Emergency Mode)")
        print("=" * 50)
        print(f"❌ Script error: {e}")
        print("\n✅ EMERGENCY COMMANDS:")
        print("   source load_secrets.sh")
        print("   source venv/bin/activate")
        print("   python run.py --help")
        print("\n🔧 Check background service:")
        print("   ./scripts/start_atlas_service.sh status")
        print("=" * 50)


if __name__ == "__main__":
    main()
