"""
Input file cleanup utilities for Atlas.

This module handles moving processed input files to appropriate folders
to keep the inputs/ directory clean and organized.
"""

import os
import shutil
from datetime import datetime
from typing import List, Optional

from helpers.utils import log_info, log_error


def ensure_processed_directory(base_path: str = ".") -> str:
    """Ensure the processed directory exists and return its path."""
    processed_dir = os.path.join(base_path, "processed")
    os.makedirs(processed_dir, exist_ok=True)

    # Create subdirectories for different types
    for subdir in ["urls", "csv", "html", "emails", "other"]:
        os.makedirs(os.path.join(processed_dir, subdir), exist_ok=True)

    return processed_dir


def move_processed_file(
    file_path: str, file_type: str = "other", config: Optional[dict] = None
) -> bool:
    """
    Move a successfully processed file to the processed directory.

    Args:
        file_path: Path to the file to move
        file_type: Type of file (urls, csv, html, emails, other)
        config: Optional config dict for logging

    Returns:
        bool: True if move was successful
    """
    if not os.path.exists(file_path):
        return False

    try:
        processed_dir = ensure_processed_directory()

        # Generate timestamped filename to avoid conflicts
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        original_name = os.path.basename(file_path)
        name_parts = os.path.splitext(original_name)
        new_name = f"{name_parts[0]}_{timestamp}{name_parts[1]}"

        destination = os.path.join(processed_dir, file_type, new_name)
        shutil.move(file_path, destination)

        if config:
            log_path = os.path.join(
                config.get("data_directory", "output"), "input_cleanup.log"
            )
            log_info(log_path, f"Moved processed file: {file_path} -> {destination}")

        return True

    except Exception as e:
        if config:
            log_path = os.path.join(
                config.get("data_directory", "output"), "input_cleanup.log"
            )
            log_error(log_path, f"Failed to move file {file_path}: {str(e)}")
        return False


def cleanup_processed_urls(
    url_file_path: str, successful_urls: List[str], config: Optional[dict] = None
) -> bool:
    """
    Clean up URL file after processing. Removes successful URLs and moves file if all processed.

    Args:
        url_file_path: Path to the URL file
        successful_urls: List of successfully processed URLs
        config: Optional config dict

    Returns:
        bool: True if cleanup was successful
    """
    if not os.path.exists(url_file_path) or not successful_urls:
        return False

    try:
        # Read all URLs from file
        with open(url_file_path, "r") as f:
            all_urls = [line.strip() for line in f if line.strip()]

        # Remove successful URLs
        remaining_urls = [url for url in all_urls if url not in successful_urls]

        if not remaining_urls:
            # All URLs processed successfully, move the file
            return move_processed_file(url_file_path, "urls", config)
        else:
            # Write remaining URLs back to file
            with open(url_file_path, "w") as f:
                for url in remaining_urls:
                    f.write(f"{url}\n")

            if config:
                log_path = os.path.join(
                    config.get("data_directory", "output"), "input_cleanup.log"
                )
                log_info(
                    log_path,
                    f"Updated {url_file_path}: removed {len(successful_urls)} processed URLs, {len(remaining_urls)} remaining",
                )

            return True

    except Exception as e:
        if config:
            log_path = os.path.join(
                config.get("data_directory", "output"), "input_cleanup.log"
            )
            log_error(log_path, f"Failed to cleanup URL file {url_file_path}: {str(e)}")
        return False


def cleanup_processed_csv(
    csv_file_path: str, successful_urls: List[str], config: Optional[dict] = None
) -> bool:
    """
    Clean up CSV file after processing. For now, just moves it since we don't modify CSVs.

    Args:
        csv_file_path: Path to the CSV file
        successful_urls: List of successfully processed URLs
        config: Optional config dict

    Returns:
        bool: True if cleanup was successful
    """
    if not os.path.exists(csv_file_path):
        return False

    # For CSV files, we typically don't modify them, just move them when fully processed
    # You could implement partial processing logic here if needed

    if successful_urls:  # Only move if we processed something
        return move_processed_file(csv_file_path, "csv", config)

    return True


def cleanup_html_files(
    html_dir: str, processed_files: List[str], config: Optional[dict] = None
) -> int:
    """
    Clean up HTML files that have been successfully processed.

    Args:
        html_dir: Directory containing HTML files
        processed_files: List of file paths that were successfully processed
        config: Optional config dict

    Returns:
        int: Number of files moved
    """
    moved_count = 0

    for file_path in processed_files:
        if os.path.exists(file_path) and file_path.endswith(".html"):
            if move_processed_file(file_path, "html", config):
                moved_count += 1

    return moved_count


def cleanup_email_files(
    email_dir: str, processed_files: List[str], config: Optional[dict] = None
) -> int:
    """
    Clean up email files that have been successfully processed.

    Args:
        email_dir: Directory containing email files
        processed_files: List of file paths that were successfully processed
        config: Optional config dict

    Returns:
        int: Number of files moved
    """
    moved_count = 0

    for file_path in processed_files:
        if os.path.exists(file_path) and file_path.endswith(".eml"):
            if move_processed_file(file_path, "emails", config):
                moved_count += 1

    return moved_count


def get_processed_file_stats(base_path: str = ".") -> dict:
    """
    Get statistics about processed files.

    Returns:
        dict: Statistics about processed files by type
    """
    processed_dir = os.path.join(base_path, "processed")

    if not os.path.exists(processed_dir):
        return {}

    stats = {}

    for subdir in ["urls", "csv", "html", "emails", "other"]:
        subdir_path = os.path.join(processed_dir, subdir)
        if os.path.exists(subdir_path):
            files = [
                f
                for f in os.listdir(subdir_path)
                if os.path.isfile(os.path.join(subdir_path, f))
            ]
            stats[subdir] = len(files)
        else:
            stats[subdir] = 0

    return stats
