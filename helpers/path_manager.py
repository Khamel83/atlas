"""
Path Manager Module

This module provides centralized path management utilities for the Atlas system,
consolidating duplicate file path creation logic and ensuring consistent path handling.
"""

import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from helpers.metadata_manager import ContentType


class PathType(Enum):
    """Types of paths in the Atlas system."""

    METADATA = "metadata"
    MARKDOWN = "markdown"
    HTML = "html"
    AUDIO = "audio"
    VIDEO = "video"
    TRANSCRIPT = "transcript"
    LOG = "log"
    EVALUATION = "evaluation"
    TEMP = "temp"


@dataclass
class PathSet:
    """Container for a complete set of paths for a content item."""

    uid: str
    content_type: ContentType
    base_dir: str
    paths: Dict[PathType, str]

    def get_path(self, path_type: PathType) -> Optional[str]:
        """Get a specific path type."""
        return self.paths.get(path_type)

    @property
    def base_path(self) -> str:
        """Get the base path for this content item (without extension)."""
        return os.path.join(self.base_dir, self.uid)

    def ensure_directories(self) -> bool:
        """Ensure all parent directories exist."""
        try:
            for path in self.paths.values():
                os.makedirs(os.path.dirname(path), exist_ok=True)
            return True
        except OSError:
            return False


class PathManager:
    """Centralized path management for Atlas system."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.data_directory = config.get("data_directory", "output")

        # Content type base directories
        self.type_directories = {
            ContentType.ARTICLE: config.get(
                "article_output_path", os.path.join(self.data_directory, "articles")
            ),
            ContentType.PODCAST: config.get(
                "podcast_output_path", os.path.join(self.data_directory, "podcasts")
            ),
            ContentType.YOUTUBE: config.get(
                "youtube_output_path", os.path.join(self.data_directory, "youtube")
            ),
            ContentType.INSTAPAPER: config.get(
                "article_output_path", os.path.join(self.data_directory, "articles")
            ),
            ContentType.DOCUMENT: config.get(
                "document_output_path", os.path.join(self.data_directory, "documents")
            ),
        }

        # Path templates for different content types
        self.path_templates = {
            ContentType.ARTICLE: {
                PathType.METADATA: "metadata/{uid}.json",
                PathType.MARKDOWN: "markdown/{uid}.md",
                PathType.HTML: "html/{uid}.html",
                PathType.LOG: "ingest.log",
                PathType.EVALUATION: "../evaluation/articles/{uid}.eval.json",
            },
            ContentType.PODCAST: {
                PathType.METADATA: "metadata/{uid}.json",
                PathType.MARKDOWN: "markdown/{uid}.md",
                PathType.AUDIO: "audio/{uid}.mp3",
                PathType.TRANSCRIPT: "transcripts/{uid}.txt",
                PathType.LOG: "ingest.log",
                PathType.EVALUATION: "../evaluation/podcasts/{uid}.eval.json",
            },
            ContentType.YOUTUBE: {
                PathType.METADATA: "metadata/{uid}.json",
                PathType.MARKDOWN: "markdown/{uid}.md",
                PathType.VIDEO: "videos/{uid}.mp4",
                PathType.TRANSCRIPT: "transcripts/{uid}.txt",
                PathType.LOG: "ingest.log",
                PathType.EVALUATION: "../evaluation/youtube/{uid}.eval.json",
            },
            ContentType.DOCUMENT: {
                PathType.METADATA: "metadata/{uid}.json",
                PathType.MARKDOWN: "markdown/{uid}.md",
                PathType.LOG: "ingest.log",
                PathType.EVALUATION: "../evaluation/documents/{uid}.eval.json",
            },
        }

    def get_base_directory(self, content_type: ContentType) -> str:
        """Get the base directory for a content type."""
        return self.type_directories[content_type]

    def get_path_set(self, content_type: ContentType, uid: str) -> PathSet:
        """Get complete path set for a content item."""
        base_dir = self.get_base_directory(content_type)
        templates = self.path_templates.get(content_type, {})

        paths = {}
        for path_type, template in templates.items():
            if template:
                path = os.path.join(base_dir, template.format(uid=uid))
                paths[path_type] = os.path.normpath(path)

        return PathSet(
            uid=uid, content_type=content_type, base_dir=base_dir, paths=paths
        )

    def get_single_path(
        self, content_type: ContentType, uid: str, path_type: PathType
    ) -> Optional[str]:
        """Get a single path for a content item."""
        path_set = self.get_path_set(content_type, uid)
        return path_set.get_path(path_type)

    def ensure_directories(self, content_type: ContentType, uid: str = None) -> bool:
        """Ensure all directories exist for a content type."""
        try:
            base_dir = self.get_base_directory(content_type)
            templates = self.path_templates.get(content_type, {})

            # Create all standard directories
            for path_type, template in templates.items():
                if template and "/" in template:
                    # Extract directory from template
                    dir_part = os.path.dirname(template)
                    if dir_part:
                        full_dir = os.path.join(base_dir, dir_part)
                        os.makedirs(full_dir, exist_ok=True)

            # If UID is provided, ensure specific item directories
            if uid:
                path_set = self.get_path_set(content_type, uid)
                path_set.ensure_directories()

            return True
        except OSError:
            return False

    def get_log_path(self, content_type: ContentType) -> str:
        """Get the log path for a content type."""
        base_dir = self.get_base_directory(content_type)
        return os.path.join(base_dir, "ingest.log")

    def get_evaluation_path(self, content_type: ContentType, uid: str) -> str:
        """Get the evaluation path for a content item."""
        return os.path.join("evaluation", content_type.value, f"{uid}.eval.json")

    def get_temp_path(
        self, content_type: ContentType, uid: str, suffix: str = ""
    ) -> str:
        """Get a temporary path for processing."""
        base_dir = self.get_base_directory(content_type)
        temp_dir = os.path.join(base_dir, "temp")
        os.makedirs(temp_dir, exist_ok=True)

        filename = f"{uid}{suffix}"
        return os.path.join(temp_dir, filename)

    def cleanup_temp_files(self, content_type: ContentType, uid: str = None) -> bool:
        """Clean up temporary files."""
        try:
            base_dir = self.get_base_directory(content_type)
            temp_dir = os.path.join(base_dir, "temp")

            if not os.path.exists(temp_dir):
                return True

            if uid:
                # Clean up specific UID temp files
                for filename in os.listdir(temp_dir):
                    if filename.startswith(uid):
                        os.remove(os.path.join(temp_dir, filename))
            else:
                # Clean up all temp files
                import shutil

                shutil.rmtree(temp_dir)
                os.makedirs(temp_dir, exist_ok=True)

            return True
        except OSError:
            return False

    def get_relative_path(self, absolute_path: str) -> str:
        """Convert absolute path to relative path from data directory."""
        try:
            return os.path.relpath(absolute_path, self.data_directory)
        except ValueError:
            return absolute_path

    def get_absolute_path(self, relative_path: str) -> str:
        """Convert relative path to absolute path."""
        if os.path.isabs(relative_path):
            return relative_path
        return os.path.join(self.data_directory, relative_path)

    def validate_path(self, path: str) -> bool:
        """Validate that a path is within the data directory."""
        try:
            abs_path = os.path.abspath(path)
            abs_data_dir = os.path.abspath(self.data_directory)
            return abs_path.startswith(abs_data_dir)
        except (OSError, ValueError):
            return False

    def get_all_content_paths(self, content_type: ContentType) -> List[PathSet]:
        """Get all existing content paths for a content type."""
        base_dir = self.get_base_directory(content_type)
        metadata_dir = os.path.join(base_dir, "metadata")

        if not os.path.exists(metadata_dir):
            return []

        path_sets = []
        for filename in os.listdir(metadata_dir):
            if filename.endswith(".json"):
                uid = filename[:-5]  # Remove .json extension
                path_set = self.get_path_set(content_type, uid)
                path_sets.append(path_set)

        return path_sets

    def migrate_paths(
        self, old_base_dir: str, new_base_dir: str, content_type: ContentType
    ) -> bool:
        """Migrate content from old base directory to new base directory."""
        try:
            import shutil

            if not os.path.exists(old_base_dir):
                return True

            # Create new base directory
            os.makedirs(new_base_dir, exist_ok=True)

            # Copy all subdirectories
            for item in os.listdir(old_base_dir):
                old_path = os.path.join(old_base_dir, item)
                new_path = os.path.join(new_base_dir, item)

                if os.path.isdir(old_path):
                    shutil.copytree(old_path, new_path, dirs_exist_ok=True)
                else:
                    shutil.copy2(old_path, new_path)

            # Update the type directory mapping
            self.type_directories[content_type] = new_base_dir

            return True
        except (OSError, shutil.Error):
            return False

    def get_backup_path(
        self, content_type: ContentType, uid: str, timestamp: str = None
    ) -> str:
        """Get backup path for a content item."""
        if not timestamp:
            from datetime import datetime

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        base_dir = self.get_base_directory(content_type)
        backup_dir = os.path.join(base_dir, "backups", timestamp)
        os.makedirs(backup_dir, exist_ok=True)

        return backup_dir

    def create_backup(self, content_type: ContentType, uid: str) -> Optional[str]:
        """Create backup of all files for a content item."""
        try:
            import shutil
            from datetime import datetime

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = self.get_backup_path(content_type, uid, timestamp)

            path_set = self.get_path_set(content_type, uid)

            # Backup all existing files
            for path_type, path in path_set.paths.items():
                if os.path.exists(path):
                    filename = os.path.basename(path)
                    backup_path = os.path.join(backup_dir, filename)
                    shutil.copy2(path, backup_path)

            return backup_dir
        except (OSError, shutil.Error):
            return None


def create_path_manager(config: Dict[str, Any]) -> PathManager:
    """Factory function to create path manager."""
    return PathManager(config)


# Convenience functions
def get_content_paths(
    content_type: ContentType, uid: str, config: Dict[str, Any]
) -> PathSet:
    """Get paths for a content item."""
    manager = create_path_manager(config)
    return manager.get_path_set(content_type, uid)


def ensure_content_directories(
    content_type: ContentType, config: Dict[str, Any]
) -> bool:
    """Ensure directories exist for a content type."""
    manager = create_path_manager(config)
    return manager.ensure_directories(content_type)


def get_log_path(content_type: ContentType, config: Dict[str, Any]) -> str:
    """Get log path for a content type."""
    manager = create_path_manager(config)
    return manager.get_log_path(content_type)
