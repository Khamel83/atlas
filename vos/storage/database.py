import json
import os
import sqlite3
import uuid
from pathlib import Path
from typing import Optional

DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS content (
    id TEXT PRIMARY KEY,
    url TEXT,
    title TEXT,
    source TEXT,
    content_type TEXT,
    html_path TEXT,
    text_path TEXT,
    metadata TEXT,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS queue_audit (
    id TEXT PRIMARY KEY,
    job_id TEXT,
    status TEXT,
    processed_at TEXT,
    error TEXT
);
CREATE TABLE IF NOT EXISTS feed_state (
    feed_url TEXT PRIMARY KEY,
    last_guid TEXT,
    last_checked TEXT
);
CREATE TABLE IF NOT EXISTS processed_entries (
    feed_url TEXT,
    guid TEXT,
    PRIMARY KEY(feed_url, guid)
);
"""


def init_db(db_path: str):
    conn = sqlite3.connect(db_path)
    conn.executescript(DB_SCHEMA)
    conn.close()


def get_connection(db_path: str = os.getenv("DATABASE_PATH", "data/atlas_vos.db")):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def insert_content(conn: sqlite3.Connection, record: dict):
    conn.execute(
        """
        INSERT OR REPLACE INTO content (
            id, url, title, source, content_type, html_path, text_path, metadata, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record["id"],
            record["url"],
            record["title"],
            record["source"],
            record["content_type"],
            record["html_path"],
            record["text_path"],
            json.dumps(record.get("metadata", {})),
            record["created_at"],
        ),
    )
    conn.commit()


def log_queue_audit(
    conn: sqlite3.Connection, job_id: str, status: str, error: Optional[str] = None
):
    conn.execute(
        """
        INSERT INTO queue_audit (id, job_id, status, processed_at, error)
        VALUES (?, ?, ?, datetime('now'), ?)
        """,
        (uuid.uuid4().hex, job_id, status, error),
    )
    conn.commit()


def __ensure_feed_state(conn: sqlite3.Connection):
    conn.execute(
        "CREATE TABLE IF NOT EXISTS feed_state (feed_url TEXT PRIMARY KEY, last_guid TEXT, last_checked TEXT)"
    )


def update_feed_state(conn: sqlite3.Connection, feed_url: str, guid: str):
    conn.execute(
        """
        INSERT INTO feed_state (feed_url, last_guid, last_checked)
        VALUES (?, ?, datetime('now'))
        ON CONFLICT(feed_url) DO UPDATE SET last_guid = excluded.last_guid, last_checked = excluded.last_checked
        """,
        (feed_url, guid),
    )
    conn.commit()


def get_feed_state(conn: sqlite3.Connection, feed_url: str) -> Optional[str]:
    cursor = conn.execute(
        "SELECT last_guid FROM feed_state WHERE feed_url = ?", (feed_url,)
    )
    row = cursor.fetchone()
    return row["last_guid"] if row else None


def has_processed_entry(conn: sqlite3.Connection, feed_url: str, guid: str) -> bool:
    cursor = conn.execute(
        "SELECT 1 FROM processed_entries WHERE feed_url = ? AND guid = ?",
        (feed_url, guid),
    )
    return cursor.fetchone() is not None


def mark_processed_entry(conn: sqlite3.Connection, feed_url: str, guid: str):
    conn.execute(
        "INSERT OR IGNORE INTO processed_entries (feed_url, guid) VALUES (?, ?)",
        (feed_url, guid),
    )
    conn.commit()
