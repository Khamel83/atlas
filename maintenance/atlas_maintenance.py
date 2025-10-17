#!/usr/bin/env python3
"""
Atlas Maintenance Script

This script performs regular maintenance tasks for the Atlas system.
"""

import os
import sys
import subprocess
import sqlite3
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


def retry_failed_articles():
    """Retry processing failed articles"""
    print("Retrying failed articles...")

    # Database path
    db_path = "/home/ubuntu/dev/atlas/atlas.db"

    if not os.path.exists(db_path):
        print("Database not found")
        return False

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Find articles that failed in the last 7 days
        seven_days_ago = datetime.now() - timedelta(days=7)
        cursor.execute(
            """
            SELECT id, url FROM articles
            WHERE status = 'failed'
            AND created_at > ?
            ORDER BY created_at DESC
        """,
            (seven_days_ago.isoformat(),),
        )

        failed_articles = cursor.fetchall()

        if not failed_articles:
            print("No failed articles to retry")
            conn.close()
            return True

        print(f"Found {len(failed_articles)} failed articles to retry")

        # Update status to 'pending' for retry
        for article_id, url in failed_articles:
            cursor.execute(
                """
                UPDATE articles
                SET status = 'pending', updated_at = ?
                WHERE id = ?
            """,
                (datetime.now().isoformat(), article_id),
            )
            print(f"Retrying article {article_id}: {url}")

        conn.commit()
        conn.close()

        print("Failed articles retry process completed")
        return True

    except Exception as e:
        print(f"Error retrying failed articles: {str(e)}")
        return False


def optimize_database():
    """Optimize the Atlas database"""
    print("Optimizing database...")

    # Database path
    db_path = "/home/ubuntu/dev/atlas/atlas.db"

    if not os.path.exists(db_path):
        print("Database not found")
        return False

    try:
        conn = sqlite3.connect(db_path)

        # Run database optimization
        conn.execute("PRAGMA optimize")
        conn.execute("VACUUM")

        conn.close()

        print("Database optimization completed")
        return True

    except Exception as e:
        print(f"Error optimizing database: {str(e)}")
        return False


def rotate_logs():
    """Rotate and cleanup Atlas logs"""
    print("Rotating logs...")

    # Log directory
    log_dir = "/home/ubuntu/dev/atlas/logs"

    if not os.path.exists(log_dir):
        print("Log directory not found")
        return False

    # Find log files older than 30 days
    cmd = f"find {log_dir} -name '*.log' -mtime +30 -delete"
    result = run_command(cmd, "Deleting old log files")

    if result is not None:
        print("Log rotation completed")
        return True
    else:
        print("Log rotation failed")
        return False


def deduplicate_content():
    """Remove duplicate content"""
    print("Removing duplicate content...")

    # Database path
    db_path = "/home/ubuntu/dev/atlas/atlas.db"

    if not os.path.exists(db_path):
        print("Database not found")
        return False

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Find and remove duplicate articles based on URL
        cursor.execute(
            """
            DELETE FROM articles
            WHERE id NOT IN (
                SELECT MIN(id)
                FROM articles
                GROUP BY url
            )
        """
        )

        deleted_count = cursor.rowcount

        # Find and remove duplicate podcasts based on URL
        cursor.execute(
            """
            DELETE FROM podcasts
            WHERE id NOT IN (
                SELECT MIN(id)
                FROM podcasts
                GROUP BY url
            )
        """
        )

        deleted_count += cursor.rowcount

        # Find and remove duplicate YouTube videos based on URL
        cursor.execute(
            """
            DELETE FROM youtube_videos
            WHERE id NOT IN (
                SELECT MIN(id)
                FROM youtube_videos
                GROUP BY url
            )
        """
        )

        deleted_count += cursor.rowcount

        conn.commit()
        conn.close()

        print(f"Removed {deleted_count} duplicate entries")
        return True

    except Exception as e:
        print(f"Error removing duplicates: {str(e)}")
        return False


def cleanup_temp_files():
    """Clean up temporary files"""
    print("Cleaning up temporary files...")

    # Temporary directories
    temp_dirs = ["/tmp/atlas", "/home/ubuntu/dev/atlas/tmp"]

    for temp_dir in temp_dirs:
        if os.path.exists(temp_dir):
            cmd = f"find {temp_dir} -type f -mtime +7 -delete"
            run_command(cmd, f"Cleaning temporary directory: {temp_dir}")

    print("Temporary file cleanup completed")
    return True


def check_service_health():
    """Check Atlas service health and restart if needed"""
    print("Checking service health...")

    # Check if Atlas service is running
    result = subprocess.run(
        ["systemctl", "is-active", "atlas"], capture_output=True, text=True
    )

    if result.stdout.strip() == "active":
        print("Atlas service is running")
        return True
    else:
        print("Atlas service is not running, attempting restart...")

        # Restart service
        restart_result = subprocess.run(
            ["sudo", "systemctl", "restart", "atlas"], capture_output=True, text=True
        )

        if restart_result.returncode == 0:
            print("Atlas service restarted successfully")
            return True
        else:
            print("Failed to restart Atlas service")
            return False


def main():
    """Main maintenance function"""
    print("Starting Atlas maintenance tasks...")
    print("=" * 40)

    # Perform maintenance tasks
    tasks = [
        ("Retry failed articles", retry_failed_articles),
        ("Optimize database", optimize_database),
        ("Rotate logs", rotate_logs),
        ("Remove duplicates", deduplicate_content),
        ("Clean temporary files", cleanup_temp_files),
        ("Check service health", check_service_health),
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
    print("Maintenance Summary:")
    print("=" * 40)

    all_success = True
    for task_name, success in results:
        status = "PASS" if success else "FAIL"
        print(f"{task_name}: {status}")
        if not success:
            all_success = False

    if all_success:
        print("\nAll maintenance tasks completed successfully!")
    else:
        print("\nSome maintenance tasks failed. Please check the logs.")

    return all_success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
