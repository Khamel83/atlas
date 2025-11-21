#!/usr/bin/env python3
"""
Migration script to convert from the legacy retries.json to the new retry queue.

This script reads the old retries.json file, converts each entry to the new format,
and adds them to the new retry queue using the helpers.retry_queue module.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from helpers.config import load_config
from helpers.retry_queue import enqueue
from helpers.utils import log_error, log_info


def migrate_retry_queue(config: dict):
    """
    Migrate from the old retries.json to the new retry queue.

    Args:
        config: The application configuration dictionary
    """
    # Path to the old retries.json file
    old_retry_path = Path("retries.json")

    # Path for logging
    log_path = Path(config.get("data_directory", "output")) / "migration.log"

    if not old_retry_path.exists():
        log_info(log_path, "No retries.json file found. Nothing to migrate.")
        return

    try:
        # Load the old retries.json file
        with open(old_retry_path, "r") as f:
            old_retries = json.load(f)

        # Count of migrated items
        youtube_count = 0
        podcast_count = 0

        # Migrate YouTube retries
        if "youtube" in old_retries:
            for video_id in old_retries["youtube"]:
                # Create a new retry task
                retry_task = {
                    "type": "youtube",
                    "video_id": video_id,
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "error": "Migrated from legacy retry system",
                    "timestamp": datetime.now().isoformat(),
                    "attempts": 1,
                    "migrated": True,
                }

                # Add to the new retry queue
                enqueue(retry_task)
                youtube_count += 1

        # Migrate podcast retries
        if "podcasts" in old_retries:
            for podcast_id in old_retries["podcasts"]:
                # Create a new retry task
                retry_task = {
                    "type": "podcast",
                    "uid": podcast_id,
                    "error": "Migrated from legacy retry system",
                    "timestamp": datetime.now().isoformat(),
                    "attempts": 1,
                    "migrated": True,
                }

                # Add to the new retry queue
                enqueue(retry_task)
                podcast_count += 1

        # Log the results
        log_info(
            log_path,
            f"Migration complete. Migrated {youtube_count} YouTube retries and {podcast_count} podcast retries.",
        )

        # Create a backup of the old retries.json file
        backup_path = old_retry_path.with_suffix(".json.bak")
        old_retry_path.rename(backup_path)
        log_info(log_path, f"Backed up old retries.json to {backup_path}")

    except Exception as e:
        log_error(log_path, f"Error migrating retry queue: {e}")
        return False

    return True


if __name__ == "__main__":
    config = load_config()
    success = migrate_retry_queue(config)

    if success:
        print("Migration completed successfully.")
    else:
        print("Migration failed. Check the logs for details.")
        sys.exit(1)
