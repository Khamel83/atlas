#!/usr/bin/env python3
"""
Atlas Disk Cleanup Script

This script performs comprehensive disk cleanup tasks.
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
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"Success: {description}")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error executing: {description}")
        print(f"Error: {e.stderr}")
        return None

def cleanup_logs():
    """Clean up old log files"""
    print("Cleaning up logs...")

    log_dir = "/home/ubuntu/dev/atlas/logs"
    if not os.path.exists(log_dir):
        print("Log directory not found")
        return False

    # Count log files before cleanup
    count_cmd = f"find {log_dir} -name '*.log' | wc -l"
    count_result = subprocess.run(count_cmd, shell=True, capture_output=True, text=True)
    if count_result.returncode == 0:
        before_count = int(count_result.stdout.strip())
        print(f"Log files before cleanup: {before_count}")

    # Delete log files older than 30 days
    cmd = f"find {log_dir} -name '*.log' -mtime +30 -delete"
    result = run_command(cmd, "Deleting old log files")

    if result is not None:
        # Count log files after cleanup
        count_result = subprocess.run(count_cmd, shell=True, capture_output=True, text=True)
        if count_result.returncode == 0:
            after_count = int(count_result.stdout.strip())
            print(f"Log files after cleanup: {after_count}")
            print(f"Deleted {before_count - after_count} log files")
        return True
    else:
        print("Log cleanup failed")
        return False

def cleanup_temp():
    """Clean up temporary files"""
    print("Cleaning up temporary files...")

    temp_dirs = [
        "/tmp/atlas",
        "/home/ubuntu/dev/atlas/tmp"
    ]

    total_cleaned = 0

    for temp_dir in temp_dirs:
        if os.path.exists(temp_dir):
            try:
                # Count files before cleanup
                count_cmd = f"find {temp_dir} -type f | wc -l"
                count_result = subprocess.run(count_cmd, shell=True, capture_output=True, text=True)
                if count_result.returncode == 0:
                    before_count = int(count_result.stdout.strip())
                    print(f"Files in {temp_dir} before cleanup: {before_count}")

                # Delete files older than 7 days
                cmd = f"find {temp_dir} -type f -mtime +7 -delete"
                result = run_command(cmd, f"Deleting old files in {temp_dir}")

                if result is not None:
                    # Count files after cleanup
                    count_result = subprocess.run(count_cmd, shell=True, capture_output=True, text=True)
                    if count_result.returncode == 0:
                        after_count = int(count_result.stdout.strip())
                        cleaned = before_count - after_count
                        total_cleaned += cleaned
                        print(f"Deleted {cleaned} files from {temp_dir}")
            except Exception as e:
                print(f"Error cleaning {temp_dir}: {str(e)}")

    print(f"Total temporary files cleaned: {total_cleaned}")
    return total_cleaned > 0

def cleanup_backups():
    """Clean up old backups"""
    print("Cleaning up backups...")

    backup_dir = "/home/ubuntu/dev/atlas/backups"
    if not os.path.exists(backup_dir):
        print("Backup directory not found")
        return False

    # Count backup files before cleanup
    count_cmd = f"find {backup_dir} -name 'atlas_backup_*.sql.gz.enc' | wc -l"
    count_result = subprocess.run(count_cmd, shell=True, capture_output=True, text=True)
    if count_result.returncode == 0:
        before_count = int(count_result.stdout.strip())
        print(f"Backup files before cleanup: {before_count}")

    # Delete backup files older than 30 days
    cmd = f"find {backup_dir} -name 'atlas_backup_*.sql.gz.enc' -mtime +30 -delete"
    result = run_command(cmd, "Deleting old backup files")

    if result is not None:
        # Count backup files after cleanup
        count_result = subprocess.run(count_cmd, shell=True, capture_output=True, text=True)
        if count_result.returncode == 0:
            after_count = int(count_result.stdout.strip())
            print(f"Backup files after cleanup: {after_count}")
            print(f"Deleted {before_count - after_count} backup files")
        return True
    else:
        print("Backup cleanup failed")
        return False

def main():
    """Main cleanup function"""
    print("Starting disk cleanup...")
    print("=" * 40)

    # Perform cleanup tasks
    tasks = [
        ("Log cleanup", cleanup_logs),
        ("Temporary file cleanup", cleanup_temp),
        ("Backup cleanup", cleanup_backups)
    ]

    results = []

    for task_name, task_func in tasks:
        print(f"
{task_name}:")
        try:
            result = task_func()
            results.append((task_name, result))
        except Exception as e:
            print(f"Error in {task_name}: {str(e)}")
            results.append((task_name, False))

    # Print summary
    print("
" + "=" * 40)
    print("Cleanup Summary:")
    print("=" * 40)

    all_success = True
    for task_name, success in results:
        status = "PASS" if success else "FAIL"
        print(f"{task_name}: {status}")
        if not success:
            all_success = False

    if all_success:
        print("
All cleanup tasks completed successfully!")
    else:
        print("
Some cleanup tasks failed. Please check the logs.")

    return all_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
