"""
Inbox storage for captured items.

Uses SQLite for persistence. Items have statuses:
- pending: Not yet processed
- processing: Currently being processed
- completed: Successfully processed and indexed
- failed: Processing failed
"""

import logging
import sqlite3
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class InboxStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class SourceType(str, Enum):
    URL = "url"
    TEXT = "text"
    FILE = "file"


@dataclass
class InboxItem:
    """An item in the capture inbox."""
    id: str
    source_type: SourceType
    content: str  # URL, text, or file path
    status: InboxStatus = InboxStatus.PENDING
    tags: List[str] = field(default_factory=list)
    notes: Optional[str] = None
    captured_at: datetime = field(default_factory=datetime.now)
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    content_id: Optional[str] = None  # ID after processing

    @classmethod
    def from_row(cls, row: tuple) -> "InboxItem":
        """Create from database row."""
        return cls(
            id=row[0],
            source_type=SourceType(row[1]),
            content=row[2],
            status=InboxStatus(row[3]),
            tags=row[4].split(",") if row[4] else [],
            notes=row[5],
            captured_at=datetime.fromisoformat(row[6]) if row[6] else datetime.now(),
            processed_at=datetime.fromisoformat(row[7]) if row[7] else None,
            error_message=row[8],
            content_id=row[9],
        )


class InboxStore:
    """SQLite storage for inbox items."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path("data/capture/inbox.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inbox (
                id TEXT PRIMARY KEY,
                source_type TEXT NOT NULL,
                content TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                tags TEXT,
                notes TEXT,
                captured_at TEXT DEFAULT CURRENT_TIMESTAMP,
                processed_at TEXT,
                error_message TEXT,
                content_id TEXT
            )
        """)

        # Index for status queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_inbox_status ON inbox(status)
        """)

        conn.commit()
        conn.close()

    def add(
        self,
        source_type: SourceType,
        content: str,
        tags: Optional[List[str]] = None,
        notes: Optional[str] = None,
    ) -> InboxItem:
        """Add item to inbox."""
        item = InboxItem(
            id=str(uuid.uuid4())[:8],
            source_type=source_type,
            content=content,
            tags=tags or [],
            notes=notes,
        )

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO inbox (id, source_type, content, status, tags, notes, captured_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item.id,
                item.source_type.value,
                item.content,
                item.status.value,
                ",".join(item.tags) if item.tags else None,
                item.notes,
                item.captured_at.isoformat(),
            ),
        )

        conn.commit()
        conn.close()

        logger.info(f"Added to inbox: {item.id} ({item.source_type.value})")
        return item

    def get(self, item_id: str) -> Optional[InboxItem]:
        """Get item by ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM inbox WHERE id = ?", (item_id,))
        row = cursor.fetchone()
        conn.close()

        return InboxItem.from_row(row) if row else None

    def list(
        self,
        status: Optional[InboxStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[InboxItem]:
        """List inbox items."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if status:
            cursor.execute(
                """
                SELECT * FROM inbox
                WHERE status = ?
                ORDER BY captured_at DESC
                LIMIT ? OFFSET ?
                """,
                (status.value, limit, offset),
            )
        else:
            cursor.execute(
                """
                SELECT * FROM inbox
                ORDER BY captured_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            )

        rows = cursor.fetchall()
        conn.close()

        return [InboxItem.from_row(row) for row in rows]

    def update_status(
        self,
        item_id: str,
        status: InboxStatus,
        error_message: Optional[str] = None,
        content_id: Optional[str] = None,
    ):
        """Update item status."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        processed_at = datetime.now().isoformat() if status in (
            InboxStatus.COMPLETED, InboxStatus.FAILED
        ) else None

        cursor.execute(
            """
            UPDATE inbox
            SET status = ?, processed_at = ?, error_message = ?, content_id = ?
            WHERE id = ?
            """,
            (status.value, processed_at, error_message, content_id, item_id),
        )

        conn.commit()
        conn.close()

    def delete(self, item_id: str):
        """Delete item from inbox."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM inbox WHERE id = ?", (item_id,))
        conn.commit()
        conn.close()

    def stats(self) -> dict:
        """Get inbox statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT status, COUNT(*) FROM inbox GROUP BY status
        """)
        rows = cursor.fetchall()
        conn.close()

        stats = {status.value: 0 for status in InboxStatus}
        for status, count in rows:
            stats[status] = count

        stats["total"] = sum(stats.values())
        return stats


# Convenience functions
_store: Optional[InboxStore] = None


def _get_store() -> InboxStore:
    global _store
    if _store is None:
        _store = InboxStore()
    return _store


def capture_url(url: str, tags: Optional[List[str]] = None, notes: Optional[str] = None) -> InboxItem:
    """Capture a URL for later processing."""
    return _get_store().add(SourceType.URL, url, tags, notes)


def capture_text(text: str, tags: Optional[List[str]] = None, notes: Optional[str] = None) -> InboxItem:
    """Capture text for later processing."""
    return _get_store().add(SourceType.TEXT, text, tags, notes)


def capture_file(path: str, tags: Optional[List[str]] = None, notes: Optional[str] = None) -> InboxItem:
    """Capture a file path for later processing."""
    return _get_store().add(SourceType.FILE, path, tags, notes)


def get_inbox(status: Optional[str] = None, limit: int = 50) -> List[InboxItem]:
    """Get inbox items."""
    status_enum = InboxStatus(status) if status else None
    return _get_store().list(status=status_enum, limit=limit)
