"""
Index Manager - SQLite index for fast content queries.

This is NOT the source of truth - files are.
The index exists only for fast searching and filtering.
It can be rebuilt from files at any time.
"""

import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

from .content_types import ContentItem, ContentType, SourceType, ProcessingStatus

logger = logging.getLogger(__name__)


class IndexManager:
    """
    SQLite index for fast content queries.

    The index is a cache - it can be rebuilt from files.
    Always use FileStore for writes, then update the index.
    """

    def __init__(self, db_path: str = "data/indexes/atlas_index.db"):
        """
        Initialize index manager.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        logger.info(f"IndexManager initialized at {self.db_path}")

    @contextmanager
    def _get_conn(self):
        """Get a database connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        """Initialize database schema."""
        with self._get_conn() as conn:
            conn.executescript("""
                -- Main content index
                CREATE TABLE IF NOT EXISTS content_index (
                    content_id TEXT PRIMARY KEY,
                    content_type TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    source_url TEXT,
                    author TEXT,
                    description TEXT,

                    -- Podcast fields
                    podcast_name TEXT,
                    episode_number INTEGER,

                    -- YouTube fields
                    channel_name TEXT,
                    video_id TEXT,

                    -- Timestamps
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    published_at TEXT,
                    ingested_at TEXT NOT NULL,

                    -- Processing
                    status TEXT NOT NULL,
                    file_path TEXT NOT NULL,

                    -- Full-text search
                    search_text TEXT
                );

                -- URL lookup for deduplication
                CREATE TABLE IF NOT EXISTS url_index (
                    url TEXT PRIMARY KEY,
                    content_id TEXT NOT NULL,
                    FOREIGN KEY (content_id) REFERENCES content_index(content_id)
                );

                -- Tags
                CREATE TABLE IF NOT EXISTS tags (
                    content_id TEXT NOT NULL,
                    tag TEXT NOT NULL,
                    PRIMARY KEY (content_id, tag),
                    FOREIGN KEY (content_id) REFERENCES content_index(content_id)
                );

                -- Parent-child relationships
                CREATE TABLE IF NOT EXISTS relationships (
                    parent_id TEXT NOT NULL,
                    child_id TEXT NOT NULL,
                    PRIMARY KEY (parent_id, child_id),
                    FOREIGN KEY (parent_id) REFERENCES content_index(content_id),
                    FOREIGN KEY (child_id) REFERENCES content_index(content_id)
                );

                -- Indexes for common queries
                CREATE INDEX IF NOT EXISTS idx_content_type ON content_index(content_type);
                CREATE INDEX IF NOT EXISTS idx_source_type ON content_index(source_type);
                CREATE INDEX IF NOT EXISTS idx_status ON content_index(status);
                CREATE INDEX IF NOT EXISTS idx_created_at ON content_index(created_at);
                CREATE INDEX IF NOT EXISTS idx_podcast_name ON content_index(podcast_name);
                CREATE INDEX IF NOT EXISTS idx_channel_name ON content_index(channel_name);

                -- Full-text search index
                CREATE VIRTUAL TABLE IF NOT EXISTS content_fts USING fts5(
                    content_id,
                    title,
                    description,
                    search_text,
                    content='content_index',
                    content_rowid='rowid'
                );
            """)

    def index_item(self, item: ContentItem, file_path: str,
                   search_text: Optional[str] = None):
        """
        Add or update an item in the index.

        Args:
            item: ContentItem to index
            file_path: Path to the item directory
            search_text: Full text content for search (optional)
        """
        with self._get_conn() as conn:
            # Insert or replace main record
            conn.execute("""
                INSERT OR REPLACE INTO content_index (
                    content_id, content_type, source_type, title, source_url,
                    author, description, podcast_name, episode_number,
                    channel_name, video_id, created_at, updated_at,
                    published_at, ingested_at, status, file_path, search_text
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item.content_id,
                item.content_type.value,
                item.source_type.value,
                item.title,
                item.source_url,
                item.author,
                item.description,
                item.podcast_name,
                item.episode_number,
                item.channel_name,
                item.video_id,
                item.created_at.isoformat(),
                item.updated_at.isoformat(),
                item.published_at.isoformat() if item.published_at else None,
                item.ingested_at.isoformat(),
                item.status.value,
                file_path,
                search_text,
            ))

            # Index URL
            if item.source_url:
                conn.execute("""
                    INSERT OR REPLACE INTO url_index (url, content_id)
                    VALUES (?, ?)
                """, (item.source_url, item.content_id))

            # Index tags
            conn.execute("DELETE FROM tags WHERE content_id = ?", (item.content_id,))
            for tag in item.tags:
                conn.execute("""
                    INSERT OR IGNORE INTO tags (content_id, tag) VALUES (?, ?)
                """, (item.content_id, tag))

            # Index relationships
            if item.parent_id:
                conn.execute("""
                    INSERT OR IGNORE INTO relationships (parent_id, child_id)
                    VALUES (?, ?)
                """, (item.parent_id, item.content_id))

            for child_id in item.child_ids:
                conn.execute("""
                    INSERT OR IGNORE INTO relationships (parent_id, child_id)
                    VALUES (?, ?)
                """, (item.content_id, child_id))

    def remove_item(self, content_id: str):
        """Remove an item from the index."""
        with self._get_conn() as conn:
            conn.execute("DELETE FROM content_index WHERE content_id = ?", (content_id,))
            conn.execute("DELETE FROM url_index WHERE content_id = ?", (content_id,))
            conn.execute("DELETE FROM tags WHERE content_id = ?", (content_id,))
            conn.execute(
                "DELETE FROM relationships WHERE parent_id = ? OR child_id = ?",
                (content_id, content_id)
            )

    def lookup_url(self, url: str) -> Optional[str]:
        """
        Check if a URL is already indexed.

        Returns:
            content_id if found, None otherwise
        """
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT content_id FROM url_index WHERE url = ?", (url,)
            ).fetchone()
            return row["content_id"] if row else None

    def search(self, query: str, content_type: Optional[ContentType] = None,
               limit: int = 50) -> List[Dict[str, Any]]:
        """
        Full-text search across content.

        Args:
            query: Search query
            content_type: Filter by content type
            limit: Maximum results

        Returns:
            List of matching items (dict with id, title, snippet)
        """
        with self._get_conn() as conn:
            if content_type:
                rows = conn.execute("""
                    SELECT c.content_id, c.title, c.description, c.file_path,
                           c.content_type, c.source_url, c.created_at
                    FROM content_index c
                    JOIN content_fts f ON c.rowid = f.rowid
                    WHERE content_fts MATCH ? AND c.content_type = ?
                    ORDER BY rank
                    LIMIT ?
                """, (query, content_type.value, limit)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT c.content_id, c.title, c.description, c.file_path,
                           c.content_type, c.source_url, c.created_at
                    FROM content_index c
                    JOIN content_fts f ON c.rowid = f.rowid
                    WHERE content_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                """, (query, limit)).fetchall()

            return [dict(row) for row in rows]

    def list_by_type(self, content_type: ContentType,
                     status: Optional[ProcessingStatus] = None,
                     limit: int = 100,
                     offset: int = 0) -> List[Dict[str, Any]]:
        """List items by content type."""
        with self._get_conn() as conn:
            if status:
                rows = conn.execute("""
                    SELECT * FROM content_index
                    WHERE content_type = ? AND status = ?
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                """, (content_type.value, status.value, limit, offset)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM content_index
                    WHERE content_type = ?
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                """, (content_type.value, limit, offset)).fetchall()

            return [dict(row) for row in rows]

    def list_by_podcast(self, podcast_name: str,
                        limit: int = 100) -> List[Dict[str, Any]]:
        """List episodes for a podcast."""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM content_index
                WHERE podcast_name = ?
                ORDER BY episode_number DESC, created_at DESC
                LIMIT ?
            """, (podcast_name, limit)).fetchall()
            return [dict(row) for row in rows]

    def list_by_channel(self, channel_name: str,
                        limit: int = 100) -> List[Dict[str, Any]]:
        """List videos for a YouTube channel."""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM content_index
                WHERE channel_name = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (channel_name, limit)).fetchall()
            return [dict(row) for row in rows]

    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        with self._get_conn() as conn:
            stats = {
                "total": conn.execute(
                    "SELECT COUNT(*) FROM content_index"
                ).fetchone()[0],
                "by_type": {},
                "by_status": {},
                "unique_urls": conn.execute(
                    "SELECT COUNT(*) FROM url_index"
                ).fetchone()[0],
            }

            for row in conn.execute("""
                SELECT content_type, COUNT(*) as count
                FROM content_index GROUP BY content_type
            """):
                stats["by_type"][row["content_type"]] = row["count"]

            for row in conn.execute("""
                SELECT status, COUNT(*) as count
                FROM content_index GROUP BY status
            """):
                stats["by_status"][row["status"]] = row["count"]

            return stats

    def rebuild_from_files(self, file_store: "FileStore"):
        """
        Rebuild the entire index from files.

        Use this if the index gets corrupted or out of sync.
        """
        logger.info("Rebuilding index from files...")

        # Clear existing index
        with self._get_conn() as conn:
            conn.execute("DELETE FROM content_index")
            conn.execute("DELETE FROM url_index")
            conn.execute("DELETE FROM tags")
            conn.execute("DELETE FROM relationships")

        # Re-index all items
        count = 0
        for item in file_store.list_items(limit=100000):
            item_dir = file_store._get_item_dir(item)
            content = file_store.load_content(item)
            self.index_item(item, str(item_dir), search_text=content)
            count += 1

        logger.info(f"Rebuilt index with {count} items")
        return count
