#!/usr/bin/env python3
"""
Failure Notifier - Immediate notification when capture fails

This module provides immediate notification when capture operations fail.
It ensures users are instantly aware of any issues while never allowing
notification failures to break the capture process.

Key Functions:
- notify_capture_failure() - Immediate notification when capture fails
- notify_processing_failure() - Notification when processing fails
- notify_system_issue() - Notification for system-level issues
- get_notification_history() - View notification history
"""

import json
import logging
import os
import platform
import subprocess
from datetime import datetime, timedelta
from typing import Any, Dict, List

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class NotificationLevel:
    """Notification severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class NotificationMethod:
    """Available notification methods."""

    CONSOLE = "console"
    LOG_FILE = "log_file"
    DESKTOP = "desktop"
    EMAIL = "email"  # Future implementation
    WEBHOOK = "webhook"  # Future implementation


def _ensure_log_directory() -> bool:
    """Ensure notification log directory exists."""
    try:
        log_dir = "output/logs"
        os.makedirs(log_dir, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Failed to create log directory: {e}")
        return False


def _log_notification(
    notification_type: str, level: str, message: str, details: Dict[str, Any] = {}
) -> None:
    """Log notification to file. Never fails."""
    try:
        if not _ensure_log_directory():
            return

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "notification_type": notification_type,
            "level": level,
            "message": message,
            "details": details or {},
        }

        log_path = "output/logs/notifications.log"
        with open(log_path, "a") as log_file:
            log_file.write(json.dumps(log_entry) + "\n")

    except Exception as e:
        # Even logging failures shouldn't break notifications
        logger.error(f"Notification logging failed: {e}")


def _write_failure_log(
    failure_type: str, item: str, error: Exception, details: Dict[str, Any] = {}
) -> None:
    """Write failure to dedicated failure log. Never fails."""
    try:
        if not _ensure_log_directory():
            return

        failure_entry = {
            "timestamp": datetime.now().isoformat(),
            "failure_type": failure_type,
            "item": item,
            "error": str(error),
            "error_type": type(error).__name__,
            "details": details or {},
        }

        log_path = "output/logs/CAPTURE_FAILURES.log"
        with open(log_path, "a") as log_file:
            log_file.write(json.dumps(failure_entry) + "\n")

    except Exception as e:
        logger.error(f"Failure logging failed: {e}")


def _send_console_notification(level: str, message: str) -> bool:
    """Send notification to console. Never fails."""
    try:
        # Use different colors/symbols based on level
        symbols = {
            NotificationLevel.INFO: "ℹ️",
            NotificationLevel.WARNING: "⚠️",
            NotificationLevel.ERROR: "❌",
            NotificationLevel.CRITICAL: "🚨",
        }

        symbol = symbols.get(level, "📢")
        timestamp = datetime.now().strftime("%H:%M:%S")

        print(f"\n{symbol} [{timestamp}] {level.upper()}: {message}")

        return True

    except Exception as e:
        logger.error(f"Console notification failed: {e}")
        return False


def _send_desktop_notification(
    level: str, message: str, title: str = "Atlas Capture"
) -> bool:
    """Send desktop notification. Never fails."""
    try:
        system = platform.system()

        if system == "Darwin":  # macOS
            return _send_macos_notification(title, message)
        elif system == "Linux":
            return _send_linux_notification(title, message)
        elif system == "Windows":
            return _send_windows_notification(title, message)
        else:
            logger.warning(f"Desktop notifications not supported on {system}")
            return False

    except Exception as e:
        logger.error(f"Desktop notification failed: {e}")
        return False


def _send_macos_notification(title: str, message: str) -> bool:
    """Send macOS notification using osascript."""
    try:
        script = f"""
        display notification "{message}" with title "{title}"
        """

        subprocess.run(
            ["osascript", "-e", script], check=True, capture_output=True, text=True
        )

        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"macOS notification failed: {e}")
        return False
    except Exception as e:
        logger.error(f"macOS notification error: {e}")
        return False


def _send_linux_notification(title: str, message: str) -> bool:
    """Send Linux notification using notify-send."""
    try:
        subprocess.run(
            ["notify-send", title, message], check=True, capture_output=True, text=True
        )

        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"Linux notification failed: {e}")
        return False
    except FileNotFoundError:
        logger.warning(
            "notify-send not found - install libnotify-bin for desktop notifications"
        )
        return False
    except Exception as e:
        logger.error(f"Linux notification error: {e}")
        return False


def _send_windows_notification(title: str, message: str) -> bool:
    """Send Windows notification using PowerShell."""
    try:
        # Use PowerShell to show a balloon notification
        script = f"""
        Add-Type -AssemblyName System.Windows.Forms
        $notification = New-Object System.Windows.Forms.NotifyIcon
        $notification.Icon = [System.Drawing.SystemIcons]::Information
        $notification.BalloonTipTitle = "{title}"
        $notification.BalloonTipText = "{message}"
        $notification.Visible = $true
        $notification.ShowBalloonTip(3000)
        """

        subprocess.run(
            ["powershell", "-Command", script],
            check=True,
            capture_output=True,
            text=True,
        )

        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"Windows notification failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Windows notification error: {e}")
        return False


def notify_capture_failure(
    item: str, error: Exception, details: Dict[str, Any] = {}
) -> None:
    """
    Immediate notification when capture fails.

    Args:
        item: The item that failed to capture (URL, file path, etc.)
        error: The exception that occurred
        details: Additional details about the failure
    """
    try:
        # Create notification message
        message = f"Capture failed for: {item[:50]}{'...' if len(item) > 50 else ''}"
        error_msg = str(error)

        # Write to failure log first (most important)
        _write_failure_log("capture_failure", item, error, details)

        # Send console notification
        console_msg = f"{message}\nError: {error_msg}"
        _send_console_notification(NotificationLevel.ERROR, console_msg)

        # Send desktop notification
        desktop_msg = f"{message}\nError: {error_msg[:100]}{'...' if len(error_msg) > 100 else ''}"
        _send_desktop_notification(
            NotificationLevel.ERROR, desktop_msg, "Atlas Capture Failed"
        )

        # Log notification
        _log_notification(
            "capture_failure",
            NotificationLevel.ERROR,
            message,
            {
                "item": item,
                "error": error_msg,
                "error_type": type(error).__name__,
                "details": details or {},
            },
        )

    except Exception as e:
        # Even if notification fails, log the original error
        logger.error(f"Notification system failed while reporting capture failure: {e}")
        logger.error(f"Original capture failure - Item: {item}, Error: {error}")


def notify_processing_failure(
    capture_id: str, error: Exception, details: Dict[str, Any] = {}
) -> None:
    """
    Notification when processing fails.

    Args:
        capture_id: The capture ID that failed processing
        error: The exception that occurred
        details: Additional details about the failure
    """
    try:
        # Create notification message
        message = f"Processing failed for capture: {capture_id}"
        error_msg = str(error)

        # Write to failure log
        _write_failure_log("processing_failure", capture_id, error, details)

        # Send console notification
        console_msg = f"{message}\nError: {error_msg}"
        _send_console_notification(NotificationLevel.WARNING, console_msg)

        # Send desktop notification (less urgent than capture failure)
        desktop_msg = f"{message}\nError: {error_msg[:100]}{'...' if len(error_msg) > 100 else ''}"
        _send_desktop_notification(
            NotificationLevel.WARNING, desktop_msg, "Atlas Processing Failed"
        )

        # Log notification
        _log_notification(
            "processing_failure",
            NotificationLevel.WARNING,
            message,
            {
                "capture_id": capture_id,
                "error": error_msg,
                "error_type": type(error).__name__,
                "details": details or {},
            },
        )

    except Exception as e:
        logger.error(
            f"Notification system failed while reporting processing failure: {e}"
        )
        logger.error(
            f"Original processing failure - Capture ID: {capture_id}, Error: {error}"
        )


def notify_system_issue(
    issue_type: str,
    message: str,
    level: str = NotificationLevel.WARNING,
    details: Dict[str, Any] = {},
) -> None:
    """
    Notification for system-level issues.

    Args:
        issue_type: Type of system issue
        message: Human-readable message
        level: Notification level
        details: Additional details
    """
    try:
        # Create full message
        full_message = f"System issue ({issue_type}): {message}"

        # Write to failure log if it's an error or critical
        if level in [NotificationLevel.ERROR, NotificationLevel.CRITICAL]:
            fake_error = Exception(message)
            _write_failure_log("system_issue", issue_type, fake_error, details)

        # Send console notification
        _send_console_notification(level, full_message)

        # Send desktop notification for warnings and above
        if level in [
            NotificationLevel.WARNING,
            NotificationLevel.ERROR,
            NotificationLevel.CRITICAL,
        ]:
            title = f"Atlas System {level.title()}"
            _send_desktop_notification(level, full_message, title)

        # Log notification
        _log_notification(
            "system_issue",
            level,
            full_message,
            {"issue_type": issue_type, "details": details or {}},
        )

    except Exception as e:
        logger.error(f"Notification system failed while reporting system issue: {e}")
        logger.error(f"Original system issue - Type: {issue_type}, Message: {message}")


def notify_success(operation: str, message: str, details: Dict[str, Any] = {}) -> None:
    """
    Notification for successful operations.

    Args:
        operation: Type of operation that succeeded
        message: Success message
        details: Additional details
    """
    try:
        # Create full message
        full_message = f"Success ({operation}): {message}"

        # Send console notification
        _send_console_notification(NotificationLevel.INFO, full_message)

        # Log notification (but don't spam desktop for successes)
        _log_notification(
            "success",
            NotificationLevel.INFO,
            full_message,
            {"operation": operation, "details": details or {}},
        )

    except Exception as e:
        logger.error(f"Notification system failed while reporting success: {e}")


def get_notification_history(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get recent notification history.

    Args:
        limit: Maximum number of notifications to return

    Returns:
        List of recent notifications
    """
    try:
        log_path = "output/logs/notifications.log"
        if not os.path.exists(log_path):
            return []

        notifications: List[Dict[str, Any]] = []

        # Calculate cutoff time (last 30 days)
        cutoff_time = datetime.now() - timedelta(days=30)
        cutoff_iso = cutoff_time.isoformat()

        # Read log file and parse JSON lines
        with open(log_path, "r") as log_file:
            for line in log_file:
                try:
                    notification: Dict[str, Any] = json.loads(line.strip())
                    if notification.get("timestamp", "") > cutoff_iso:
                        notifications.append(notification)
                except json.JSONDecodeError:
                    # Skip malformed lines
                    continue

        # Sort by timestamp (newest first) and limit
        notifications.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return notifications[:limit]

    except Exception as e:
        logger.error(f"Failed to get notification history: {e}")
        return []


def get_failure_history(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get recent failure history.

    Args:
        limit: Maximum number of failures to return

    Returns:
        List of recent failures
    """
    try:
        log_path = "output/logs/CAPTURE_FAILURES.log"
        if not os.path.exists(log_path):
            return []

        failures: List[Dict[str, Any]] = []

        # Calculate cutoff time (last 30 days)
        cutoff_time = datetime.now() - timedelta(days=30)
        cutoff_iso = cutoff_time.isoformat()

        # Read log file and parse JSON lines
        with open(log_path, "r") as log_file:
            for line in log_file:
                try:
                    failure: Dict[str, Any] = json.loads(line.strip())
                    if failure.get("timestamp", "") > cutoff_iso:
                        failures.append(failure)
                except json.JSONDecodeError:
                    # Skip malformed lines
                    continue

        # Sort by timestamp (newest first) and limit
        failures.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return failures[:limit]

    except Exception as e:
        logger.error(f"Failed to get failure history: {e}")
        return []


def get_notification_statistics() -> Dict[str, Any]:
    """
    Get notification statistics.

    Returns:
        Dictionary with notification statistics
    """
    try:
        notifications = get_notification_history(1000)  # Get more for statistics

        stats = {
            "total_notifications": len(notifications),
            "by_level": {},
            "by_type": {},
            "recent_failures": 0,
            "oldest_notification": None,
            "newest_notification": None,
        }

        # Process notifications
        for notification in notifications:
            # Count by level
            level = notification.get("level", "unknown")
            stats["by_level"][level] = stats["by_level"].get(level, 0) + 1

            # Count by type
            notification_type = notification.get("notification_type", "unknown")
            stats["by_type"][notification_type] = (
                stats["by_type"].get(notification_type, 0) + 1
            )

            # Track timestamps
            timestamp = notification.get("timestamp")
            if timestamp:
                if (
                    not stats["oldest_notification"]
                    or timestamp < stats["oldest_notification"]
                ):
                    stats["oldest_notification"] = timestamp
                if (
                    not stats["newest_notification"]
                    or timestamp > stats["newest_notification"]
                ):
                    stats["newest_notification"] = timestamp

        # Count recent failures (last 24 hours)
        recent_cutoff = (
            datetime.now()
            .replace(hour=0, minute=0, second=0, microsecond=0)
            .isoformat()
        )
        stats["recent_failures"] = len(
            [
                n
                for n in notifications
                if n.get("timestamp", "") > recent_cutoff
                and n.get("level")
                in [NotificationLevel.ERROR, NotificationLevel.CRITICAL]
            ]
        )

        return stats

    except Exception as e:
        logger.error(f"Failed to get notification statistics: {e}")
        return {"error": str(e)}


def clear_old_notifications(days_old: int = 30) -> Dict[str, Any]:
    """
    Clear old notifications from logs.

    Args:
        days_old: Remove notifications older than this many days

    Returns:
        Dictionary with cleanup results
    """
    try:
        cutoff_date = datetime.now() - timedelta(days=days_old)
        cutoff_iso = cutoff_date.isoformat()

        results = {"notifications_removed": 0, "failures_removed": 0, "errors": []}

        # Clean notifications log
        try:
            log_path = "output/logs/notifications.log"
            if os.path.exists(log_path):
                kept_lines = []
                removed_count = 0

                with open(log_path, "r") as log_file:
                    for line in log_file:
                        try:
                            notification: Dict[str, Any] = json.loads(line.strip())
                            if notification.get("timestamp", "") > cutoff_iso:
                                kept_lines.append(line)
                            else:
                                removed_count += 1
                        except json.JSONDecodeError:
                            # Keep malformed lines
                            kept_lines.append(line)

                # Write back kept lines
                with open(log_path, "w") as log_file:
                    log_file.writelines(kept_lines)

                results["notifications_removed"] = removed_count

        except Exception as e:
            results["errors"].append(f"Failed to clean notifications log: {e}")

        # Clean failures log
        try:
            log_path = "output/logs/CAPTURE_FAILURES.log"
            if os.path.exists(log_path):
                kept_lines = []
                removed_count = 0

                with open(log_path, "r") as log_file:
                    for line in log_file:
                        try:
                            failure: Dict[str, Any] = json.loads(line.strip())
                            if failure.get("timestamp", "") > cutoff_iso:
                                kept_lines.append(line)
                            else:
                                removed_count += 1
                        except json.JSONDecodeError:
                            # Keep malformed lines
                            kept_lines.append(line)

                # Write back kept lines
                with open(log_path, "w") as log_file:
                    log_file.writelines(kept_lines)

                results["failures_removed"] = removed_count

        except Exception as e:
            results["errors"].append(f"Failed to clean failures log: {e}")

        return results

    except Exception as e:
        logger.error(f"Failed to clear old notifications: {e}")
        return {"error": str(e)}


def test_notifications() -> None:
    """Test all notification methods."""
    print("Testing notification system...")

    # Test console notification
    _send_console_notification(NotificationLevel.INFO, "Console notification test")

    # Test desktop notification
    _send_desktop_notification(
        NotificationLevel.INFO, "Desktop notification test", "Atlas Test"
    )

    # Test failure notification
    test_error = Exception("This is a test error")
    notify_capture_failure("test_item", test_error, {"test": True})

    # Test system notification
    notify_system_issue(
        "test", "This is a test system issue", NotificationLevel.WARNING
    )

    # Test success notification
    notify_success("test", "This is a test success message")

    print("Notification tests completed. Check console, desktop, and logs.")


if __name__ == "__main__":
    # Run notification tests
    test_notifications()

    # Show statistics
    stats = get_notification_statistics()
    print(f"\nNotification statistics: {stats}")

    # Show recent history
    history = get_notification_history(5)
    print(f"\nRecent notifications: {len(history)}")
    for notification in history:
        print(
            f"  {notification.get('timestamp', '')}: {notification.get('level', '')} - {notification.get('message', '')}"
        )
