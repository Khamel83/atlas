"""
Atlas Utility Functions

This module provides core utility functions used throughout the Atlas project
for file operations, logging, content conversion, and data processing.

All functions follow defensive programming principles and include comprehensive
error handling to ensure robust operation in production environments.
"""

import hashlib
import logging
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Union

from markdownify import markdownify as md


def convert_html_to_markdown(html_content: str, base_url: Optional[str] = None) -> str:
    """
    Convert HTML content to Markdown format.

    This function provides a standardized way to convert HTML to Markdown
    throughout the Atlas system, with consistent formatting options.

    Args:
        html_content (str): The HTML content to convert
        base_url (Optional[str]): Base URL for resolving relative links

    Returns:
        str: The converted Markdown content

    Example:
        >>> html = '<h1>Title</h1><p>Content</p>'
        >>> markdown = convert_html_to_markdown(html)
        >>> print(markdown)
        # Title

        Content
    """
    if not html_content:
        return ""

    try:
        return md(html_content, base_url=base_url, heading_style="ATX")
    except Exception as e:
        logging.error(f"Failed to convert HTML to Markdown: {e}")
        return html_content  # Fallback to original content


def ensure_directory(directory_path: str) -> None:
    """
    Ensure a directory exists, creating it and parent directories if needed.

    This function safely creates directories with proper error handling,
    ensuring the Atlas system can create output and temporary directories.

    Args:
        directory_path (str): Path to the directory to create

    Raises:
        OSError: If directory creation fails due to permissions or disk space

    Example:
        >>> ensure_directory("/path/to/new/directory")
        >>> # Directory now exists
    """
    if not directory_path:
        return

    try:
        os.makedirs(directory_path, exist_ok=True)
    except OSError as e:
        logging.error(f"Failed to create directory {directory_path}: {e}")
        raise


def setup_logging(log_path: str) -> None:
    """
    Configure comprehensive logging for the Atlas system.

    Sets up dual logging to both file and console with appropriate formatters
    for debugging and production monitoring. Clears existing handlers to prevent
    duplicate log entries.

    Args:
        log_path (str): Path to the log file to create

    Example:
        >>> setup_logging("/var/log/atlas/atlas.log")
        >>> logging.info("System started")  # Appears in both file and console
    """
    log_dir = os.path.dirname(log_path)
    ensure_directory(log_dir)

    # Get the root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Clear existing handlers to avoid duplicate logs
    if logger.hasHandlers():
        logger.handlers.clear()

    # Create file handler
    file_handler = logging.FileHandler(log_path, mode="a", encoding="utf-8")
    file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Create console handler
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter("%(levelname)s: %(message)s")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)


def sanitize_filename(name: str) -> str:
    """
    Sanitize a string to create a safe filesystem filename.

    Removes special characters, converts to lowercase, and replaces spaces
    with underscores to ensure compatibility across different filesystems.

    Args:
        name (str): The original filename or string to sanitize

    Returns:
        str: A filesystem-safe filename

    Example:
        >>> sanitize_filename("My Article Title! (2024)")
        'my_article_title_2024'
    """
    if not name:
        return "unnamed"

    # Replace spaces and special chars with underscores
    name = re.sub(r"[^\w\s-]", "", name).strip().lower()
    name = re.sub(r"[-\s]+", "_", name)
    return name or "unnamed"


def extract_video_id(url: str) -> Optional[str]:
    """
    Extract YouTube video ID from various URL formats.

    Supports multiple YouTube URL formats including standard watch URLs,
    shortened youtu.be links, embed URLs, and mobile formats.

    Args:
        url (str): YouTube URL in any supported format

    Returns:
        Optional[str]: Video ID if found, None if URL is invalid

    Example:
        >>> extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        'dQw4w9WgXcQ'
        >>> extract_video_id("https://youtu.be/dQw4w9WgXcQ")
        'dQw4w9WgXcQ'
    """
    if not url:
        return None
    regex_patterns = [
        r"youtu\.be/([^\?&]+)",
        r"youtube\.com/watch\?v=([^\?&]+)",
        r"youtube\.com/embed/([^\?&]+)",
        r"youtube\.com/v/([^\?&]+)",
        r"youtube\.com/shorts/([^\?&]+)",
    ]

    for pattern in regex_patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def generate_markdown_summary(
    title: str,
    source: str,
    date: str,
    tags: Optional[List[str]] = None,
    notes: Optional[List[str]] = None,
    content: Optional[str] = None
) -> str:
    """
    Generate a Markdown document with YAML frontmatter.

    Creates a standardized Markdown format used throughout Atlas for
    storing processed content with structured metadata.

    Args:
        title (str): Document title
        source (str): Source URL or identifier
        date (str): ISO date string
        tags (Optional[List[str]]): List of category tags
        notes (Optional[List[str]]): List of additional notes
        content (Optional[str]): Main document content

    Returns:
        str: Complete Markdown document with YAML frontmatter

    Example:
        >>> summary = generate_markdown_summary(
        ...     "Test Article",
        ...     "https://example.com",
        ...     "2024-01-01",
        ...     tags=["technology"],
        ...     content="Article content here"
        ... )
        >>> print(summary[:50])
        title: Test Article
        source: https://example.com
    """
    tags = tags or []
    notes = notes or []

    frontmatter = [
        f"title: {title}",
        f"source: {source}",
        f"date: {date}",
        f"tags: [{', '.join([repr(t) for t in tags])}]",
    ]

    for note in notes:
        frontmatter.append(f"- {note}")
    frontmatter.append("---\n")

    md = "\n".join(frontmatter)
    if content:
        md += content.strip() + "\n"
    return md


def log_message(log_path: str, level: str, message: str) -> None:
    """
    Log a message to both file and console with timestamp.

    Provides simple file-based logging when full logging setup is not needed.
    Automatically creates log directory if it doesn't exist.

    Args:
        log_path (str): Path to log file
        level (str): Log level (INFO, ERROR, etc.)
        message (str): Message to log
    """
    if not log_path:
        return  # No-op if log_path is empty or None
    # Ensure the directory for the log file exists
    log_dir = os.path.dirname(log_path)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    log_line = f"{datetime.now().isoformat()} {level}: {message}\n"
    with open(log_path, "a", encoding="utf-8") as logf:
        logf.write(log_line)
    # Also print to console
    print(log_line.strip())


def log_info(log_path: str, message: str) -> None:
    """
    Log an info-level message.

    Args:
        log_path (str): Path to log file
        message (str): Info message to log
    """
    if not log_path:
        return
    log_message(log_path, "INFO", message)


def log_error(log_path: str, message: str) -> None:
    """
    Log an error-level message.

    Args:
        log_path (str): Path to log file
        message (str): Error message to log
    """
    if not log_path:
        return
    log_message(log_path, "ERROR", message)


def calculate_hash(file_path: str) -> str:
    """
    Calculate SHA256 hash of a file's content.

    Provides secure file integrity checking and duplicate detection
    throughout the Atlas system.

    Args:
        file_path (str): Path to the file to hash

    Returns:
        str: SHA256 hash as hexadecimal string

    Raises:
        IOError: If file cannot be read

    Example:
        >>> hash_val = calculate_hash("example.txt")
        >>> print(len(hash_val))
        64
    """
    hasher = hashlib.sha256()

    try:
        with open(file_path, "rb") as f:
            # Read file in chunks for memory efficiency
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except IOError as e:
        logging.error(f"Failed to calculate hash for {file_path}: {e}")
        raise
