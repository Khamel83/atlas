"""
File Store - Core file operations for Atlas content storage.

The file system is the source of truth. This module handles:
- Saving content to organized directory structure
- Loading content from files
- Listing and searching content
- Deduplication checks
"""

import os
import json
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Iterator, Tuple

from .content_types import ContentItem, ContentType, ProcessingStatus

logger = logging.getLogger(__name__)


class FileStore:
    """
    File-based storage system for Atlas content.

    Directory Structure:
        data/content/
        ├── article/
        │   └── 2025/01/15/
        │       └── abc123def456/
        │           ├── content.md
        │           ├── metadata.json
        │           └── raw/  (optional)
        ├── podcast/
        ├── youtube/
        ├── newsletter/
        └── email/
    """

    def __init__(self, base_dir: str = "data/content"):
        """
        Initialize file store.

        Args:
            base_dir: Base directory for content storage
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories for each content type
        for content_type in ContentType:
            (self.base_dir / content_type.value).mkdir(exist_ok=True)

        logger.info(f"FileStore initialized at {self.base_dir}")

    def _get_item_dir(self, item: ContentItem) -> Path:
        """Get the directory path for a content item."""
        date_str = item.created_at.strftime("%Y/%m/%d")
        return self.base_dir / item.content_type.value / date_str / item.content_id

    def save(self, item: ContentItem, content: Optional[str] = None,
             raw_data: Optional[bytes] = None, raw_filename: Optional[str] = None) -> Path:
        """
        Save a content item to disk.

        Args:
            item: ContentItem to save
            content: Markdown content to save (optional)
            raw_data: Raw file data (PDF, audio, etc.) to save (optional)
            raw_filename: Filename for raw data

        Returns:
            Path to the item directory
        """
        item_dir = self._get_item_dir(item)
        item_dir.mkdir(parents=True, exist_ok=True)

        # Save metadata
        metadata_path = item_dir / "metadata.json"
        item.updated_at = datetime.utcnow()

        # Update paths relative to item dir
        if content:
            item.content_path = "content.md"
        if raw_data and raw_filename:
            item.raw_path = f"raw/{raw_filename}"

        with open(metadata_path, "w", encoding="utf-8") as f:
            f.write(item.to_json())

        # Save content
        if content:
            content_path = item_dir / "content.md"
            with open(content_path, "w", encoding="utf-8") as f:
                f.write(content)

        # Save raw data
        if raw_data and raw_filename:
            raw_dir = item_dir / "raw"
            raw_dir.mkdir(exist_ok=True)
            raw_path = raw_dir / raw_filename
            with open(raw_path, "wb") as f:
                f.write(raw_data)

        logger.debug(f"Saved content item {item.content_id} to {item_dir}")
        return item_dir

    def load(self, content_id: str, content_type: Optional[ContentType] = None,
             date: Optional[datetime] = None) -> Optional[ContentItem]:
        """
        Load a content item by ID.

        Args:
            content_id: The content ID to load
            content_type: Content type (optional, will search all if not provided)
            date: Date to look in (optional, will search all dates if not provided)

        Returns:
            ContentItem if found, None otherwise
        """
        # If we have exact path info, use it
        if content_type and date:
            date_str = date.strftime("%Y/%m/%d")
            item_dir = self.base_dir / content_type.value / date_str / content_id
            if item_dir.exists():
                return self._load_from_dir(item_dir)

        # Otherwise search
        for found_dir in self._find_item_dirs(content_id, content_type):
            return self._load_from_dir(found_dir)

        return None

    def load_content(self, item: ContentItem) -> Optional[str]:
        """Load the markdown content for an item."""
        item_dir = self._get_item_dir(item)
        content_path = item_dir / "content.md"

        if content_path.exists():
            with open(content_path, "r", encoding="utf-8") as f:
                return f.read()
        return None

    def _load_from_dir(self, item_dir: Path) -> Optional[ContentItem]:
        """Load a ContentItem from a directory."""
        metadata_path = item_dir / "metadata.json"
        if not metadata_path.exists():
            return None

        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                return ContentItem.from_json(f.read())
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error loading {metadata_path}: {e}")
            return None

    def _find_item_dirs(self, content_id: str,
                        content_type: Optional[ContentType] = None) -> Iterator[Path]:
        """Find all directories for a content ID."""
        search_dirs = [self.base_dir / content_type.value] if content_type else \
            [self.base_dir / ct.value for ct in ContentType]

        for type_dir in search_dirs:
            if not type_dir.exists():
                continue
            # Walk through date directories
            for year_dir in type_dir.iterdir():
                if not year_dir.is_dir():
                    continue
                for month_dir in year_dir.iterdir():
                    if not month_dir.is_dir():
                        continue
                    for day_dir in month_dir.iterdir():
                        if not day_dir.is_dir():
                            continue
                        item_dir = day_dir / content_id
                        if item_dir.exists():
                            yield item_dir

    def exists(self, content_id: str, content_type: Optional[ContentType] = None) -> bool:
        """Check if a content item exists."""
        for _ in self._find_item_dirs(content_id, content_type):
            return True
        return False

    def exists_by_url(self, url: str) -> Tuple[bool, Optional[str]]:
        """
        Check if content with this URL already exists.

        Returns:
            Tuple of (exists, content_id if exists)
        """
        content_id = ContentItem.generate_id(source_url=url)
        exists = self.exists(content_id)
        return (exists, content_id if exists else None)

    def delete(self, content_id: str, content_type: Optional[ContentType] = None) -> bool:
        """Delete a content item."""
        for item_dir in self._find_item_dirs(content_id, content_type):
            try:
                shutil.rmtree(item_dir)
                logger.info(f"Deleted content item {content_id}")
                return True
            except OSError as e:
                logger.error(f"Error deleting {item_dir}: {e}")
                return False
        return False

    def list_items(self, content_type: Optional[ContentType] = None,
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None,
                   status: Optional[ProcessingStatus] = None,
                   limit: int = 100) -> List[ContentItem]:
        """
        List content items with optional filtering.

        Args:
            content_type: Filter by content type
            start_date: Filter items created after this date
            end_date: Filter items created before this date
            status: Filter by processing status
            limit: Maximum items to return

        Returns:
            List of ContentItems
        """
        items = []
        type_dirs = [self.base_dir / content_type.value] if content_type else \
            [self.base_dir / ct.value for ct in ContentType]

        for type_dir in type_dirs:
            if not type_dir.exists():
                continue

            for item in self._walk_items(type_dir, start_date, end_date):
                if status and item.status != status:
                    continue
                items.append(item)
                if len(items) >= limit:
                    return items

        return items

    def _walk_items(self, type_dir: Path,
                    start_date: Optional[datetime] = None,
                    end_date: Optional[datetime] = None) -> Iterator[ContentItem]:
        """Walk through items in a type directory."""
        if not type_dir.exists():
            return

        for year_dir in sorted(type_dir.iterdir(), reverse=True):
            if not year_dir.is_dir() or not year_dir.name.isdigit():
                continue
            year = int(year_dir.name)

            # Quick date filtering at year level
            if start_date and year < start_date.year:
                continue
            if end_date and year > end_date.year:
                continue

            for month_dir in sorted(year_dir.iterdir(), reverse=True):
                if not month_dir.is_dir() or not month_dir.name.isdigit():
                    continue

                for day_dir in sorted(month_dir.iterdir(), reverse=True):
                    if not day_dir.is_dir() or not day_dir.name.isdigit():
                        continue

                    for item_dir in day_dir.iterdir():
                        if not item_dir.is_dir():
                            continue

                        item = self._load_from_dir(item_dir)
                        if item:
                            # Date filtering
                            if start_date and item.created_at < start_date:
                                continue
                            if end_date and item.created_at > end_date:
                                continue
                            yield item

    def get_stats(self) -> dict:
        """Get storage statistics."""
        stats = {
            "total_items": 0,
            "by_type": {},
            "by_status": {},
            "disk_usage_bytes": 0,
        }

        for content_type in ContentType:
            type_dir = self.base_dir / content_type.value
            if type_dir.exists():
                count = sum(1 for _ in self._walk_items(type_dir))
                stats["by_type"][content_type.value] = count
                stats["total_items"] += count

                # Calculate disk usage
                for root, dirs, files in os.walk(type_dir):
                    for file in files:
                        stats["disk_usage_bytes"] += os.path.getsize(
                            os.path.join(root, file))

        return stats

    def cleanup_empty_dirs(self):
        """Remove empty date directories."""
        for content_type in ContentType:
            type_dir = self.base_dir / content_type.value
            if not type_dir.exists():
                continue

            for year_dir in list(type_dir.iterdir()):
                if not year_dir.is_dir():
                    continue
                for month_dir in list(year_dir.iterdir()):
                    if not month_dir.is_dir():
                        continue
                    for day_dir in list(month_dir.iterdir()):
                        if not day_dir.is_dir():
                            continue
                        if not any(day_dir.iterdir()):
                            day_dir.rmdir()
                    if not any(month_dir.iterdir()):
                        month_dir.rmdir()
                if not any(year_dir.iterdir()):
                    year_dir.rmdir()
