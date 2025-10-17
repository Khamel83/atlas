#!/usr/bin/env python3
"""
Bulletproof Capture System - NEVER FAILS

This module implements the core principle: NEVER LOSE WHAT THE USER SENT.
All functions in this module must handle ALL exceptions internally and
provide immediate capture confirmation.

Architecture:
- Capture functions NEVER raise unhandled exceptions
- Atomic file operations (write to temp, then rename)
- Redundant storage (primary + backup locations)
- Immediate user feedback with tracking IDs
- Comprehensive logging for debugging
"""

import json
import logging
import os
import shutil
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

# Configure logging for capture operations
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class CaptureResult:
    """Standardized result object for all capture operations."""

    def __init__(
        self,
        success: bool,
        capture_id: Optional[str] = None,
        error: Optional[str] = None,
        metadata: Dict[str, Any] = {},
    ):
        self.success = success
        self.capture_id = capture_id
        self.error = error
        self.metadata = metadata or {}
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "capture_id": self.capture_id,
            "error": self.error,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


def _generate_capture_id() -> str:
    """Generate unique capture ID with timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    return f"CAPTURE_{timestamp}_{unique_id}"


def _ensure_directory_exists(path: str) -> bool:
    """Ensure directory exists, create if necessary. Never fails."""
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Failed to create directory {path}: {e}")
        return False


def _atomic_write(content: str, target_path: str) -> bool:
    """Write content atomically using temp file + rename. Never fails."""
    try:
        # Ensure target directory exists
        target_dir = os.path.dirname(target_path)
        if not _ensure_directory_exists(target_dir):
            return False

        # Write to temporary file first
        with tempfile.NamedTemporaryFile(
            mode="w", dir=target_dir, delete=False, suffix=".tmp"
        ) as temp_file:
            temp_file.write(content)
            temp_path = temp_file.name

        # Atomic rename
        os.rename(temp_path, target_path)
        return True

    except Exception as e:
        logger.error(f"Atomic write failed for {target_path}: {e}")
        # Clean up temp file if it exists
        try:
            if "temp_path" in locals() and os.path.exists(temp_path):
                os.unlink(temp_path)
        except Exception:
            pass
        return False


def _create_backup_copy(source_path: str, backup_path: str) -> bool:
    """Create backup copy of captured data. Never fails."""
    try:
        # Ensure backup directory exists
        backup_dir = os.path.dirname(backup_path)
        if not _ensure_directory_exists(backup_dir):
            return False

        shutil.copy2(source_path, backup_path)
        return True

    except Exception as e:
        logger.error(f"Backup creation failed: {source_path} -> {backup_path}: {e}")
        return False


def _log_capture_operation(
    capture_id: str, operation: str, success: bool, details: Dict[str, Any] = {}
) -> None:
    """Log capture operation to comprehensive log. Never fails."""
    try:
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "capture_id": capture_id,
            "operation": operation,
            "success": success,
            "details": details or {},
        }

        log_path = "output/logs/capture.log"
        _ensure_directory_exists(os.path.dirname(log_path))

        with open(log_path, "a") as log_file:
            log_file.write(json.dumps(log_entry) + "\n")

    except Exception as e:
        # Even logging failures shouldn't break capture
        logger.error(f"Capture logging failed: {e}")


def capture_url(url: str, user_context: Dict[str, Any] = {}) -> CaptureResult:
    """
    NEVER FAILS. Immediately saves URL with metadata to multiple locations.

    Args:
        url: The URL to capture
        user_context: Additional context provided by user

    Returns:
        CaptureResult with success status and capture_id
    """
    capture_id = _generate_capture_id()

    try:
        # Validate URL format
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            return CaptureResult(
                success=False, capture_id=capture_id, error="Invalid URL format"
            )

        # Create comprehensive metadata
        metadata = {
            "type": "url",
            "url": url,
            "parsed_url": {
                "scheme": parsed_url.scheme,
                "netloc": parsed_url.netloc,
                "path": parsed_url.path,
                "query": parsed_url.query,
                "fragment": parsed_url.fragment,
            },
            "user_context": user_context or {},
            "capture_timestamp": datetime.now().isoformat(),
            "capture_id": capture_id,
            "status": "captured",
        }

        # Primary storage location
        primary_path = f"output/captured/urls/{capture_id}.json"
        metadata_path = f"output/captured/metadata/{capture_id}_metadata.json"
        backup_path = f"output/captured/backups/{capture_id}_backup.json"

        # Atomic write to primary location
        primary_content = json.dumps(metadata, indent=2)
        if not _atomic_write(primary_content, primary_path):
            return CaptureResult(
                success=False,
                capture_id=capture_id,
                error="Failed to write to primary storage",
            )

        # Write metadata separately
        metadata_content = json.dumps(metadata, indent=2)
        if not _atomic_write(metadata_content, metadata_path):
            logger.warning(f"Metadata write failed for {capture_id}")

        # Create backup copy
        if not _create_backup_copy(primary_path, backup_path):
            logger.warning(f"Backup creation failed for {capture_id}")

        # Log successful capture
        _log_capture_operation(
            capture_id,
            "capture_url",
            True,
            {"url": url, "paths": [primary_path, metadata_path, backup_path]},
        )

        return CaptureResult(success=True, capture_id=capture_id, metadata=metadata)

    except Exception as e:
        # Even if everything fails, return graceful error
        error_msg = f"Capture failed: {str(e)}"
        logger.error(f"URL capture failed for {capture_id}: {e}")

        _log_capture_operation(
            capture_id, "capture_url", False, {"url": url, "error": error_msg}
        )

        return CaptureResult(success=False, capture_id=capture_id, error=error_msg)


def capture_file(file_path: str, user_context: Dict[str, Any] = {}) -> CaptureResult:
    """
    NEVER FAILS. Immediately copies file to secure storage.

    Args:
        file_path: Path to the file to capture
        user_context: Additional context provided by user

    Returns:
        CaptureResult with success status and capture_id
    """
    capture_id = _generate_capture_id()

    try:
        # Validate file exists and is readable
        if not os.path.exists(file_path):
            return CaptureResult(
                success=False,
                capture_id=capture_id,
                error=f"File not found: {file_path}",
            )

        if not os.path.isfile(file_path):
            return CaptureResult(
                success=False, capture_id=capture_id, error=f"Not a file: {file_path}"
            )

        # Get file information
        file_stat = os.stat(file_path)
        file_size = file_stat.st_size
        file_mtime = datetime.fromtimestamp(file_stat.st_mtime).isoformat()

        # Create comprehensive metadata
        metadata = {
            "type": "file",
            "original_path": file_path,
            "filename": os.path.basename(file_path),
            "file_size": file_size,
            "file_mtime": file_mtime,
            "user_context": user_context or {},
            "capture_timestamp": datetime.now().isoformat(),
            "capture_id": capture_id,
            "status": "captured",
        }

        # Storage locations
        file_extension = os.path.splitext(file_path)[1]
        captured_filename = f"{capture_id}{file_extension}"
        primary_file_path = f"output/captured/files/{captured_filename}"
        metadata_path = f"output/captured/metadata/{capture_id}_metadata.json"
        backup_file_path = f"output/captured/backups/{captured_filename}"

        # Copy file to primary location
        if not _ensure_directory_exists(os.path.dirname(primary_file_path)):
            return CaptureResult(
                success=False,
                capture_id=capture_id,
                error="Failed to create capture directory",
            )

        shutil.copy2(file_path, primary_file_path)

        # Update metadata with captured file path
        metadata["captured_path"] = primary_file_path

        # Write metadata
        metadata_content = json.dumps(metadata, indent=2)
        if not _atomic_write(metadata_content, metadata_path):
            logger.warning(f"Metadata write failed for {capture_id}")

        # Create backup copy
        if not _create_backup_copy(primary_file_path, backup_file_path):
            logger.warning(f"Backup creation failed for {capture_id}")

        # Log successful capture
        _log_capture_operation(
            capture_id,
            "capture_file",
            True,
            {
                "original_path": file_path,
                "captured_path": primary_file_path,
                "file_size": file_size,
            },
        )

        return CaptureResult(success=True, capture_id=capture_id, metadata=metadata)

    except Exception as e:
        # Even if everything fails, return graceful error
        error_msg = f"File capture failed: {str(e)}"
        logger.error(f"File capture failed for {capture_id}: {e}")

        _log_capture_operation(
            capture_id,
            "capture_file",
            False,
            {"file_path": file_path, "error": error_msg},
        )

        return CaptureResult(success=False, capture_id=capture_id, error=error_msg)


def capture_text(
    text: str, content_type: str = "text", user_context: Dict[str, Any] = {}
) -> CaptureResult:
    """
    NEVER FAILS. Immediately saves text content with metadata.

    Args:
        text: The text content to capture
        content_type: Type of content (text, note, paste, etc.)
        user_context: Additional context provided by user

    Returns:
        CaptureResult with success status and capture_id
    """
    capture_id = _generate_capture_id()

    try:
        # Create comprehensive metadata
        metadata = {
            "type": "text",
            "content_type": content_type,
            "text_length": len(text),
            "user_context": user_context or {},
            "capture_timestamp": datetime.now().isoformat(),
            "capture_id": capture_id,
            "status": "captured",
        }

        # Storage locations
        primary_path = f"output/captured/files/{capture_id}.txt"
        metadata_path = f"output/captured/metadata/{capture_id}_metadata.json"
        backup_path = f"output/captured/backups/{capture_id}_backup.txt"

        # Write text to primary location
        if not _atomic_write(text, primary_path):
            return CaptureResult(
                success=False,
                capture_id=capture_id,
                error="Failed to write text to primary storage",
            )

        # Update metadata with captured file path
        metadata["captured_path"] = primary_path

        # Write metadata
        metadata_content = json.dumps(metadata, indent=2)
        if not _atomic_write(metadata_content, metadata_path):
            logger.warning(f"Metadata write failed for {capture_id}")

        # Create backup copy
        if not _create_backup_copy(primary_path, backup_path):
            logger.warning(f"Backup creation failed for {capture_id}")

        # Log successful capture
        _log_capture_operation(
            capture_id,
            "capture_text",
            True,
            {
                "content_type": content_type,
                "text_length": len(text),
                "captured_path": primary_path,
            },
        )

        return CaptureResult(success=True, capture_id=capture_id, metadata=metadata)

    except Exception as e:
        # Even if everything fails, return graceful error
        error_msg = f"Text capture failed: {str(e)}"
        logger.error(f"Text capture failed for {capture_id}: {e}")

        _log_capture_operation(
            capture_id,
            "capture_text",
            False,
            {"content_type": content_type, "error": error_msg},
        )

        return CaptureResult(success=False, capture_id=capture_id, error=error_msg)


def get_capture_status(capture_id: str) -> Dict[str, Any]:
    """
    Return current status of any captured item.

    Args:
        capture_id: The capture ID to check

    Returns:
        Dictionary with capture status and metadata
    """
    try:
        # Look for metadata file
        metadata_path = f"output/captured/metadata/{capture_id}_metadata.json"

        if not os.path.exists(metadata_path):
            return {"found": False, "error": f"Capture ID {capture_id} not found"}

        # Read metadata
        with open(metadata_path, "r") as f:
            metadata = json.load(f)

        # Check if primary file exists
        primary_exists = False
        backup_exists = False

        if metadata.get("type") == "url":
            primary_path = f"output/captured/urls/{capture_id}.json"
            backup_path = f"output/captured/backups/{capture_id}_backup.json"
        else:
            captured_path = metadata.get("captured_path", "")
            if captured_path:
                primary_path = captured_path
                filename = os.path.basename(captured_path)
                backup_path = f"output/captured/backups/{filename}"
            else:
                primary_path = backup_path = ""

        if primary_path:
            primary_exists = os.path.exists(primary_path)
        if backup_path:
            backup_exists = os.path.exists(backup_path)

        return {
            "found": True,
            "capture_id": capture_id,
            "metadata": metadata,
            "primary_exists": primary_exists,
            "backup_exists": backup_exists,
            "primary_path": primary_path,
            "backup_path": backup_path,
        }

    except Exception as e:
        logger.error(f"Status check failed for {capture_id}: {e}")
        return {"found": False, "error": f"Status check failed: {str(e)}"}


def list_captured_items(limit: int = 100) -> List[Dict[str, Any]]:
    """
    List recently captured items.

    Args:
        limit: Maximum number of items to return

    Returns:
        List of captured item summaries
    """
    try:
        metadata_dir = "output/captured/metadata"
        if not os.path.exists(metadata_dir):
            return []

        # Get all metadata files
        metadata_files = [
            f for f in os.listdir(metadata_dir) if f.endswith("_metadata.json")
        ]

        # Sort by modification time (newest first)
        metadata_files.sort(
            key=lambda f: os.path.getmtime(os.path.join(metadata_dir, f)), reverse=True
        )

        # Limit results
        metadata_files = metadata_files[:limit]

        # Read metadata for each file
        items = []
        for filename in metadata_files:
            try:
                with open(os.path.join(metadata_dir, filename), "r") as f:
                    metadata = json.load(f)

                items.append(
                    {
                        "capture_id": metadata.get("capture_id"),
                        "type": metadata.get("type"),
                        "timestamp": metadata.get("capture_timestamp"),
                        "url": metadata.get("url"),
                        "filename": metadata.get("filename"),
                        "content_type": metadata.get("content_type"),
                        "status": metadata.get("status", "captured"),
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to read metadata file {filename}: {e}")
                continue

        return items

    except Exception as e:
        logger.error(f"Failed to list captured items: {e}")
        return []


def get_capture_statistics() -> Dict[str, Any]:
    """
    Get statistics about captured items.

    Returns:
        Dictionary with capture statistics
    """
    try:
        stats: Dict[str, Any] = {
            "total_captured": 0,
            "by_type": {},
            "total_size": 0,
            "total_captured_size": 0,
            "oldest_capture": None,
            "newest_capture": None,
        }

        metadata_dir = "output/captured/metadata"
        if not os.path.exists(metadata_dir):
            return stats

        # Process all metadata files
        for filename in os.listdir(metadata_dir):
            if not filename.endswith("_metadata.json"):
                continue

            try:
                with open(os.path.join(metadata_dir, filename), "r") as f:
                    metadata = json.load(f)

                stats["total_captured"] += 1

                # Count by type
                item_type = metadata.get("type", "unknown")
                stats["by_type"][item_type] = stats["by_type"].get(item_type, 0) + 1

                # Track timestamps
                timestamp = metadata.get("capture_timestamp")
                if timestamp:
                    if (
                        not stats["oldest_capture"]
                        or timestamp < stats["oldest_capture"]
                    ):
                        stats["oldest_capture"] = timestamp
                    if (
                        not stats["newest_capture"]
                        or timestamp > stats["newest_capture"]
                    ):
                        stats["newest_capture"] = timestamp

                # Add file size if available
                stats["total_captured_size"] += metadata.get("file_size", 0)

            except Exception as e:
                logger.warning(f"Failed to process metadata file {filename}: {e}")
                continue

        return stats

    except Exception as e:
        logger.error(f"Failed to get capture statistics: {e}")
        return {"error": str(e)}


if __name__ == "__main__":
    # Simple test of capture functions
    print("Testing bulletproof capture system...")

    # Test URL capture
    result = capture_url("https://example.com", {"source": "test"})
    print(f"URL capture: {result.success}, ID: {result.capture_id}")

    # Test text capture
    result = capture_text("This is a test", "note", {"source": "test"})
    print(f"Text capture: {result.success}, ID: {result.capture_id}")

    # Test statistics
    stats = get_capture_statistics()
    print(f"Statistics: {stats}")

    # Test listing
    items = list_captured_items(5)
    print(f"Recent items: {len(items)}")
    for item in items:
        print(f"  {item['capture_id']}: {item['type']} - {item['timestamp']}")
