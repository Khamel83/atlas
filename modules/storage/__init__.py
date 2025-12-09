"""
Atlas File-Based Storage System

The source of truth is files on disk, not databases.
SQLite indexes exist only for fast querying.
"""

from .content_types import ContentItem, ContentType, SourceType
from .file_store import FileStore
from .index_manager import IndexManager

__all__ = [
    "ContentItem",
    "ContentType",
    "SourceType",
    "FileStore",
    "IndexManager",
]
