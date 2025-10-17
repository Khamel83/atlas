#!/usr/bin/env python3
"""
Atlas Disk Space Monitoring Script

This script monitors disk space usage and performs cleanup when thresholds are exceeded.
"""

import os
import sys
import subprocess
import shutil
from datetime import datetime, timedelta


def run_command(cmd, description=""):
    """Run a shell command with error handling"""
    try:
        print(f"Executing: {description}")
        result = subprocess.run(
            cmd, shell=True, check=True, capture_output=True, text=True
        )
        print(f"Success: {description}")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error executing: {description}")
        print(f"Error: {e.stderr}")
        return None


def get_disk_usage():
    """Get disk usage percentage for root filesystem"""
    try:
        # Get disk usage for root filesystem
        result = subprocess.run(["df", "/"], capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split("\n")

        if len(lines) > 1:
            # Parse disk usage percentage
            usage_info = lines[1].split()
            usage_percent = int(usage_info[4].rstrip("%"))
            return usage_percent
        else:
            return None
    except Exception as e:
        print(f"Error getting disk usage: {str(e)}")
        return None


def send_alert(usage_percent, threshold):
    """Send disk space alert"""
    print(f"WARNING: Disk usage at {usage_percent}% exceeds {threshold}% threshold")

    # Send email alert (implementation would be similar to previous alert scripts)
    # For now, we'll just print to log
    log_message = f"DISK_ALERT: Usage {usage_percent}% exceeds {threshold}% threshold"
    with open("/home/ubuntu/dev/atlas/logs/disk_alert.log", "a") as f:
        f.write(f"{datetime.now()}: {log_message}\n")

    return True


def cleanup_old_logs():
    """Clean up old log files"""
    print("Cleaning up old log files...")

    log_dir = "/home/ubuntu/dev/atlas/logs"
    if not os.path.exists(log_dir):
        print("Log directory not found")
        return False

    # Find and delete log files older than 30 days
    cmd = f"find {log_dir} -name '*.log' -mtime +30 -delete"
    result = run_command(cmd, "Deleting old log files")

    if result is not None:
        print("Old log cleanup completed")
        return True
    else:
        print("Old log cleanup failed")
        return False


def cleanup_temp_files():
    """Clean up temporary files"""
    print("Cleaning up temporary files...")

    temp_dirs = ["/tmp/atlas", "/home/ubuntu/dev/atlas/tmp"]

    cleaned_count = 0

    for temp_dir in temp_dirs:
        if os.path.exists(temp_dir):
            try:
                # Find and delete files older than 7 days
                cmd = f"find {temp_dir} -type f -mtime +7 -delete"
                result = run_command(cmd, f"Cleaning temporary directory: {temp_dir}")

                if result is not None:
                    # Count files in directory after cleanup
                    count_cmd = f"find {temp_dir} -type f | wc -l"
                    count_result = subprocess.run(
                        count_cmd, shell=True, capture_output=True, text=True
                    )
                    if count_result.returncode == 0:
                        file_count = int(count_result.stdout.strip())
                        print(
                            f"Temporary directory {temp_dir} contains {file_count} files"
                        )
                        cleaned_count += 1
            except Exception as e:
                print(f"Error cleaning temporary directory {temp_dir}: {str(e)}")

    print("Temporary file cleanup completed")
    return cleaned_count > 0


def cleanup_old_backups():
    """Clean up old backups"""
    print("Cleaning up old backups...")

    backup_dir = "/home/ubuntu/dev/atlas/backups"
    if not os.path.exists(backup_dir):
        print("Backup directory not found")
        return False

    # Find and delete backup files older than 30 days
    cmd = f"find {backup_dir} -name 'atlas_backup_*.sql.gz.enc' -mtime +30 -delete"
    result = run_command(cmd, "Deleting old backup files")

    if result is not None:
        print("Old backup cleanup completed")
        return True
    else:
        print("Old backup cleanup failed")
        return False


def cleanup_oci_backups():
    """Clean up old OCI backups"""
    print("Cleaning up old OCI backups...")

    # This would interact with OCI Object Storage to delete old backups
    # For now, we'll just print a message
    print("OCI backup cleanup would be implemented here")
    print("This would use the OCI CLI to delete old objects from the bucket")

    return True


def perform_cleanup():
    """Perform all cleanup tasks"""
    print("Performing disk space cleanup...")

    # Perform cleanup tasks
    tasks = [
        ("Old log cleanup", cleanup_old_logs),
        ("Temporary file cleanup", cleanup_temp_files),
        ("Old backup cleanup", cleanup_old_backups),
        ("OCI backup cleanup", cleanup_oci_backups),
    ]

    results = []

    for task_name, task_func in tasks:
        print(f"\n{task_name}:")
        try:
            result = task_func()
            results.append((task_name, result))
        except Exception as e:
            print(f"Error in {task_name}: {str(e)}")
            results.append((task_name, False))

    # Print summary
    print("\n" + "=" * 40)
    print("Cleanup Summary:")
    print("=" * 40)

    all_success = True
    for task_name, success in results:
        status = "PASS" if success else "FAIL"
        print(f"{task_name}: {status}")
        if not success:
            all_success = False

    return all_success


def main():
    """Main disk monitoring function"""
    print("Starting disk space monitoring...")

    # Get current disk usage
    usage_percent = get_disk_usage()

    if usage_percent is None:
        print("Error getting disk usage")
        return False

    print(f"Current disk usage: {usage_percent}%")

    # Check thresholds
    if usage_percent >= 90:
        print("CRITICAL: Disk usage exceeds 90%")
        send_alert(usage_percent, 90)
        # Perform immediate cleanup
        perform_cleanup()
    elif usage_percent >= 80:
        print("WARNING: Disk usage exceeds 80%")
        send_alert(usage_percent, 80)
        # Perform cleanup
        perform_cleanup()
    else:
        print("Disk usage is within acceptable limits")
        # Perform routine cleanup
        cleanup_temp_files()

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
