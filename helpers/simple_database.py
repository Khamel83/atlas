"""
Simple database interface for Atlas content management.

Provides a unified SQLite interface for storing and managing content,
transcriptions, worker jobs, and worker metadata. Handles database
initialization, connection management, and basic CRUD operations.

Typical usage:
    db = SimpleDatabase()
    content_id = db.store_content(content="Sample", title="Test",
                                 url="http://test.com", content_type="article")
    data = db.get_all_content()
"""

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .database_config import get_database_path

class SimpleDatabase:
    """Simple SQLite database interface for Atlas content management.

    Attributes:
        db_path: Path to the SQLite database file
    """

    def __init__(self, db_path: Optional[Union[str, Path]] = None) -> None:
        """Initialize database with optional custom path.

        Args:
            db_path: Optional path to database file. Defaults to ~/dev/atlas/atlas.db

        Raises:
            sqlite3.Error: If database initialization fails
        """
        if db_path is None:
            # Use centralized database configuration
            db_path = get_database_path()

        self.db_path = db_path
        self._init_tables()

    def get_connection(self) -> sqlite3.Connection:
        """Get database connection with error handling.

        Returns:
            SQLite connection object

        Raises:
            sqlite3.Error: If connection fails
        """
        try:
            return sqlite3.connect(str(self.db_path))
        except sqlite3.Error as e:
            raise sqlite3.Error(f"Failed to connect to database {self.db_path}: {e}")

    def _init_tables(self) -> None:
        """Initialize required database tables with proper schema.

        Creates tables for content, worker_jobs, workers, and transcriptions
        if they don't already exist.

        Raises:
            sqlite3.Error: If table creation fails
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Content table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS content (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    url TEXT,
                    content TEXT,
                    content_type TEXT,
                    metadata TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    ai_summary TEXT,
                    ai_tags TEXT,
                    ai_socratic TEXT,
                    ai_patterns TEXT,
                    ai_recommendations TEXT,
                    ai_classification TEXT
                )
            """)

            # Worker jobs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS worker_jobs (
                    id TEXT PRIMARY KEY,
                    type TEXT,
                    data TEXT,
                    priority INTEGER,
                    status TEXT DEFAULT 'pending',
                    assigned_worker TEXT,
                    created_at TEXT,
                    assigned_at TEXT,
                    completed_at TEXT,
                    result TEXT
                )
            """)

            # Workers table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workers (
                    worker_id TEXT PRIMARY KEY,
                    capabilities TEXT,
                    platform TEXT,
                    whisper_available INTEGER,
                    ytdlp_available INTEGER,
                    metadata TEXT,
                    registered_at TEXT,
                    last_seen TEXT,
                    status TEXT DEFAULT 'active'
                )
            """)

            # Transcriptions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transcriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT,
                    transcript TEXT,
                    source TEXT,
                    metadata TEXT,
                    created_at TEXT,
                    processed INTEGER DEFAULT 0
                )
            """)

            conn.commit()
        except sqlite3.Error as e:
            raise sqlite3.Error(f"Failed to initialize database tables: {e}")
        finally:
            if conn:
                conn.close()

    def store_content(self, content: str, title: str, url: str,
                     content_type: str, metadata: Optional[Dict[str, Any]] = None) -> int:
        """Store content record in database.

        Args:
            content: The main content text
            title: Content title
            url: Source URL
            content_type: Type of content (article, document, podcast, etc.)
            metadata: Optional metadata dictionary

        Returns:
            Content ID of stored record

        Raises:
            sqlite3.Error: If storage fails
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            now = self._get_current_timestamp()

            cursor.execute("""
                INSERT INTO content (title, url, content, content_type, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                title,
                url,
                content,
                content_type,
                json.dumps(metadata or {}),
                now,
                now
            ))

            content_id = cursor.lastrowid
            conn.commit()
            return content_id
        except sqlite3.Error as e:
            raise sqlite3.Error(f"Failed to store content: {e}")
        finally:
            if conn:
                conn.close()

    def store_transcription(self, transcription_data: Dict[str, Any]) -> int:
        """Store transcription record in database.

        Args:
            transcription_data: Dictionary containing transcription fields:
                - filename: Source filename
                - transcript: Transcription text
                - source: Transcription source/method
                - metadata: Additional metadata
                - created_at: Creation timestamp
                - processed: Processing status (optional)

        Returns:
            Transcription ID of stored record

        Raises:
            sqlite3.Error: If storage fails
            KeyError: If required fields are missing
        """
        required_fields = ['filename', 'transcript', 'source', 'metadata', 'created_at']
        for field in required_fields:
            if field not in transcription_data:
                raise KeyError(f"Required field '{field}' missing from transcription_data")

        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO transcriptions (filename, transcript, source, metadata, created_at, processed)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                transcription_data['filename'],
                transcription_data['transcript'],
                transcription_data['source'],
                transcription_data['metadata'],
                transcription_data['created_at'],
                1 if transcription_data.get('processed', False) else 0
            ))

            transcription_id = cursor.lastrowid
            conn.commit()
            return transcription_id
        except sqlite3.Error as e:
            raise sqlite3.Error(f"Failed to store transcription: {e}")
        finally:
            if conn:
                conn.close()

    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format.

        Returns:
            Current UTC timestamp as ISO format string
        """
        return datetime.utcnow().isoformat()

    def get_all_content(self) -> List[Dict[str, Any]]:
        """Retrieve all content records from database.

        Returns:
            List of content records as dictionaries

        Raises:
            sqlite3.Error: If query fails
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, title, url, content, content_type, metadata, created_at, updated_at
                FROM content ORDER BY created_at DESC
            """)

            columns = ['id', 'title', 'url', 'content', 'content_type', 'metadata', 'created_at', 'updated_at']
            results = []

            for row in cursor.fetchall():
                record = dict(zip(columns, row))
                # Parse metadata JSON
                try:
                    record['metadata'] = json.loads(record['metadata']) if record['metadata'] else {}
                except json.JSONDecodeError:
                    record['metadata'] = {}
                results.append(record)

            return results
        except sqlite3.Error as e:
            raise sqlite3.Error(f"Failed to retrieve content: {e}")
        finally:
            if conn:
                conn.close()