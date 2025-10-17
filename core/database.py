"""
Universal Database Service for Atlas

Replaces 242+ scattered SQLite connections with a single, robust service.
Provides connection pooling, transaction management, caching, and health monitoring.
"""

import sqlite3
import json
import time
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Iterator
from dataclasses import dataclass, asdict
import logging

from .config import DatabaseConfig


@dataclass
class Content:
    """Unified content data model"""
    id: Optional[int] = None
    title: str = ""
    url: str = ""
    content: str = ""
    content_type: str = "article"
    metadata: Dict[str, Any] = None
    created_at: str = ""
    updated_at: str = ""
    ai_summary: Optional[str] = None
    ai_tags: Optional[str] = None
    stage: int = 0

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.utcnow().isoformat()


class ConnectionPool:
    """Simple SQLite connection pool with health monitoring"""

    def __init__(self, db_path: Union[str, Path], max_connections: int = 10):
        self.db_path = str(db_path)
        self.max_connections = max_connections
        self._pool = []
        self._used = set()
        self._lock = threading.Lock()
        self._logger = logging.getLogger(__name__)

        # Initialize pool
        for _ in range(max_connections):
            conn = self._create_connection()
            self._pool.append(conn)

    def _create_connection(self) -> sqlite3.Connection:
        """Create a new connection with proper settings"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # Enable WAL mode for better concurrency
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    @contextmanager
    def get_connection(self) -> Iterator[sqlite3.Connection]:
        """Get connection from pool with automatic return"""
        conn = None
        try:
            with self._lock:
                if self._pool:
                    conn = self._pool.pop()
                elif len(self._used) < self.max_connections:
                    conn = self._create_connection()
                else:
                    raise RuntimeError("Connection pool exhausted")

                self._used.add(id(conn))

            # Test connection health
            try:
                conn.execute("SELECT 1").fetchone()
            except sqlite3.Error:
                # Replace unhealthy connection
                conn = self._create_connection()

            yield conn

        finally:
            if conn:
                with self._lock:
                    self._used.discard(id(conn))
                    self._pool.append(conn)

    def close_all(self):
        """Close all connections in pool"""
        with self._lock:
            for conn in self._pool + list(self._used):
                try:
                    conn.close()
                except:
                    pass
            self._pool.clear()
            self._used.clear()


class LRUCache:
    """Simple LRU cache for database results"""

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache = {}
        self.access_order = []

    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            self.access_order.remove(key)
            self.access_order.append(key)
            return self.cache[key]
        return None

    def put(self, key: str, value: Any):
        if key in self.cache:
            self.access_order.remove(key)
        elif len(self.cache) >= self.max_size:
            oldest = self.access_order.pop(0)
            del self.cache[oldest]

        self.cache[key] = value
        self.access_order.append(key)

    def invalidate(self, key: str = None):
        """Invalidate specific key or entire cache"""
        if key:
            if key in self.cache:
                del self.cache[key]
                self.access_order.remove(key)
        else:
            self.cache.clear()
            self.access_order.clear()


class UniversalDatabase:
    """Single database service for entire Atlas system"""

    def __init__(self, config_path: str = "config/database.yaml"):
        self.config = DatabaseConfig.load(config_path)
        self.pool = ConnectionPool(self.config.db_path, self.config.max_connections)
        self.cache = LRUCache(self.config.cache_size)
        self._logger = logging.getLogger(__name__)

        # Initialize database schema
        self._init_schema()

    def _init_schema(self):
        """Initialize database tables if they don't exist"""
        with self.pool.get_connection() as conn:
            # Content table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS content (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    url TEXT UNIQUE,
                    content TEXT,
                    content_type TEXT DEFAULT 'article',
                    metadata TEXT DEFAULT '{}',
                    created_at TEXT,
                    updated_at TEXT,
                    ai_summary TEXT,
                    ai_tags TEXT,
                    stage INTEGER DEFAULT 0
                )
            """)

            # Create indexes for better performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_content_url ON content(url)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_content_type ON content(content_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_content_created ON content(created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_content_stage ON content(stage)")

            # Worker jobs table (simplified from current system)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS worker_jobs (
                    id TEXT PRIMARY KEY,
                    type TEXT,
                    data TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT,
                    completed_at TEXT,
                    result TEXT
                )
            """)

            conn.commit()

    @contextmanager
    def transaction(self):
        """Context manager for database transactions"""
        with self.pool.get_connection() as conn:
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def store_content(self, content: Content) -> int:
        """Store content with automatic duplicate detection"""
        # Check for duplicates by URL
        if content.url:
            existing = self.get_content_by_url(content.url)
            if existing:
                # Update existing content
                content.id = existing.id
                return self.update_content(content)

        # Insert new content
        with self.transaction() as conn:
            cursor = conn.execute("""
                INSERT INTO content (title, url, content, content_type, metadata,
                                    created_at, updated_at, ai_summary, ai_tags, stage)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                content.title,
                content.url,
                content.content,
                content.content_type,
                json.dumps(content.metadata),
                content.created_at,
                content.updated_at,
                content.ai_summary,
                content.ai_tags,
                content.stage
            ))

            content_id = cursor.lastrowid

            # Invalidate cache
            self.cache.invalidate()

            return content_id

    def update_content(self, content: Content) -> int:
        """Update existing content"""
        with self.transaction() as conn:
            conn.execute("""
                UPDATE content
                SET title = ?, content = ?, content_type = ?, metadata = ?,
                    updated_at = ?, ai_summary = ?, ai_tags = ?, stage = ?
                WHERE id = ?
            """, (
                content.title,
                content.content,
                content.content_type,
                json.dumps(content.metadata),
                datetime.utcnow().isoformat(),
                content.ai_summary,
                content.ai_tags,
                content.stage,
                content.id
            ))

            # Invalidate cache
            self.cache.invalidate()

            return content.id

    def get_content(self, content_id: int) -> Optional[Content]:
        """Get content by ID with caching"""
        cache_key = f"content_{content_id}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        with self.pool.get_connection() as conn:
            row = conn.execute("SELECT * FROM content WHERE id = ?", (content_id,)).fetchone()
            if row:
                content = self._row_to_content(row)
                self.cache.put(cache_key, content)
                return content
            return None

    def get_content_by_url(self, url: str) -> Optional[Content]:
        """Get content by URL"""
        with self.pool.get_connection() as conn:
            row = conn.execute("SELECT * FROM content WHERE url = ?", (url,)).fetchone()
            if row:
                return self._row_to_content(row)
            return None

    def search_content(self, query: str, limit: int = 50, offset: int = 0) -> List[Content]:
        """Simple full-text search across content"""
        with self.pool.get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM content
                WHERE title LIKE ? OR content LIKE ? OR ai_summary LIKE ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (f"%{query}%", f"%{query}%", f"%{query}%", limit, offset)).fetchall()

            return [self._row_to_content(row) for row in rows]

    def get_recent_content(self, limit: int = 20, content_type: str = None) -> List[Content]:
        """Get recent content, optionally filtered by type"""
        with self.pool.get_connection() as conn:
            if content_type:
                rows = conn.execute("""
                    SELECT * FROM content
                    WHERE content_type = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (content_type, limit)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM content
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (limit,)).fetchall()

            return [self._row_to_content(row) for row in rows]

    def get_content_by_stage(self, stage: int) -> List[Content]:
        """Get content by processing stage"""
        with self.pool.get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM content
                WHERE stage = ?
                ORDER BY created_at ASC
            """, (stage,)).fetchall()

            return [self._row_to_content(row) for row in rows]

    def update_content_stage(self, content_id: int, stage: int) -> bool:
        """Update content processing stage"""
        with self.transaction() as conn:
            cursor = conn.execute(
                "UPDATE content SET stage = ?, updated_at = ? WHERE id = ?",
                (stage, datetime.utcnow().isoformat(), content_id)
            )

            # Invalidate cache
            self.cache.invalidate(f"content_{content_id}")

            return cursor.rowcount > 0

    def delete_content(self, content_id: int) -> bool:
        """Delete content by ID"""
        with self.transaction() as conn:
            cursor = conn.execute("DELETE FROM content WHERE id = ?", (content_id,))

            # Invalidate cache
            self.cache.invalidate(f"content_{content_id}")
            self.cache.invalidate()  # Clear all cache since search results might be affected

            return cursor.rowcount > 0

    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        with self.pool.get_connection() as conn:
            # Total content
            total = conn.execute("SELECT COUNT(*) FROM content").fetchone()[0]

            # Content by type
            by_type = dict(conn.execute("""
                SELECT content_type, COUNT(*)
                FROM content
                GROUP BY content_type
            """).fetchall())

            # Content by stage
            by_stage = dict(conn.execute("""
                SELECT stage, COUNT(*)
                FROM content
                GROUP BY stage
                ORDER BY stage
            """).fetchall())

            # Recent activity
            recent = conn.execute("""
                SELECT COUNT(*) FROM content
                WHERE created_at >= datetime('now', '-7 days')
            """).fetchone()[0]

            # AI summaries
            with_ai = conn.execute("""
                SELECT COUNT(*) FROM content
                WHERE ai_summary IS NOT NULL AND ai_summary != ''
            """).fetchone()[0]

            return {
                "total_content": total,
                "by_type": by_type,
                "by_stage": by_stage,
                "recent_activity": recent,
                "with_ai_summaries": with_ai
            }

    def _row_to_content(self, row: sqlite3.Row) -> Content:
        """Convert database row to Content object"""
        # Safely parse JSON metadata
        metadata_str = row["metadata"] or "{}"
        try:
            metadata = json.loads(metadata_str)
        except json.JSONDecodeError:
            # Fix common JSON issues
            try:
                # Try to fix missing quotes around property names
                fixed_metadata_str = metadata_str.replace("{", "{\"").replace(":", "\":\"").replace(", ", "\",\"").replace("}", "\"}")
                if not fixed_metadata_str.startswith("{"):
                    fixed_metadata_str = "{" + fixed_metadata_str
                if not fixed_metadata_str.endswith("}"):
                    fixed_metadata_str = fixed_metadata_str + "}"
                metadata = json.loads(fixed_metadata_str)
            except:
                # If all else fails, use empty metadata
                metadata = {}

        return Content(
            id=row["id"],
            title=row["title"] or "",
            url=row["url"] or "",
            content=row["content"] or "",
            content_type=row["content_type"] or "article",
            metadata=metadata,
            created_at=row["created_at"] or "",
            updated_at=row["updated_at"] or "",
            ai_summary=row["ai_summary"],
            ai_tags=row["ai_tags"],
            stage=row["stage"] or 0
        )

    def health_check(self) -> Dict[str, Any]:
        """Perform health check on database"""
        try:
            with self.pool.get_connection() as conn:
                # Test basic connectivity
                result = conn.execute("SELECT 1").fetchone()

                # Get database stats
                stats = self.get_statistics()

                return {
                    "status": "healthy",
                    "total_content": stats.get("total_content", 0),
                    "connections_available": len(self.pool._pool),
                    "connections_used": len(self.pool._used),
                    "cache_size": len(self.cache.cache),
                    "statistics": stats
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    def migrate_from_old_system(self, old_db_path: str):
        """Migrate data from old Atlas database"""
        old_db_path = Path(old_db_path)
        if not old_db_path.exists():
            self._logger.warning(f"Old database not found: {old_db_path}")
            return

        try:
            # Connect to old database
            old_conn = sqlite3.connect(str(old_db_path))
            old_conn.row_factory = sqlite3.Row

            # Get all content from old database
            old_content = old_conn.execute("SELECT * FROM content").fetchall()

            migrated = 0
            for row in old_content:
                content = Content(
                    title=row["title"] or "",
                    url=row["url"] or "",
                    content=row["content"] or "",
                    content_type=row["content_type"] or "article",
                    metadata=json.loads(row["metadata"] or "{}"),
                    created_at=row["created_at"] or "",
                    updated_at=row["updated_at"] or "",
                    ai_summary=row["ai_summary"],
                    ai_tags=row["ai_tags"],
                    stage=0  # Reset to initial stage for reprocessing
                )

                self.store_content(content)
                migrated += 1

                if migrated % 1000 == 0:
                    self._logger.info(f"Migrated {migrated} content items...")

            old_conn.close()
            self._logger.info(f"Migration complete: {migrated} items migrated")

        except Exception as e:
            self._logger.error(f"Migration failed: {e}")
            raise

    def get_connection_pool_info(self) -> Dict[str, Any]:
        """Get connection pool information"""
        return {
            "pool_size": self.pool.max_connections,
            "available_connections": len(self.pool._pool),
            "used_connections": len(self.pool._used),
            "db_path": self.pool.db_path
        }

    def get_cache_info(self) -> Dict[str, Any]:
        """Get cache information"""
        return {
            "cache_size": len(self.cache.cache),
            "max_size": self.cache.max_size,
            "cache_keys": list(self.cache.cache.keys())
        }

    def close(self):
        """Close database connections"""
        self.pool.close_all()


# Singleton instance for easy import
db_instance = None

def reset_database():
    """Reset database instance - useful for testing or reconfiguration"""
    global db_instance
    db_instance = None

def get_database() -> UniversalDatabase:
    """Get singleton database instance"""
    global db_instance
    if db_instance is None:
        db_instance = UniversalDatabase(config_path="/home/ubuntu/dev/atlas/config/database.yaml")
    return db_instance