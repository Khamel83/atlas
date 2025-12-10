#!/usr/bin/env python3
"""
SQLite database store for podcast transcript sourcing.
Manages podcasts, episodes, transcript sources, and discovery runs.
"""

import sqlite3
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from contextlib import contextmanager


@dataclass
class Podcast:
    """Podcast metadata"""

    id: Optional[int] = None
    name: str = ""
    slug: str = ""
    rss_url: str = ""
    site_url: str = ""
    resolver: str = "generic_html"
    episode_selector: str = ""
    transcript_selector: str = ""
    config: Dict[str, Any] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def __post_init__(self):
        if self.config is None:
            self.config = {}


@dataclass
class Episode:
    """Episode metadata"""

    id: Optional[int] = None
    podcast_id: int = 0
    guid: str = ""
    title: str = ""
    url: str = ""
    publish_date: Optional[str] = None
    transcript_url: Optional[str] = None
    transcript_status: str = "unknown"  # unknown, found, missing, fetched, failed
    transcript_path: Optional[str] = None
    metadata: Dict[str, Any] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class TranscriptSource:
    """Discovered transcript source"""

    id: Optional[int] = None
    episode_id: int = 0
    resolver: str = ""
    url: str = ""
    confidence: float = 0.0
    metadata: Dict[str, Any] = None
    created_at: Optional[str] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class DiscoveryRun:
    """Discovery run tracking"""

    id: Optional[int] = None
    podcast_id: int = 0
    resolver: str = ""
    episodes_found: int = 0
    transcripts_found: int = 0
    errors: int = 0
    duration_seconds: float = 0.0
    status: str = "running"  # running, completed, failed
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class PodcastStore:
    """SQLite database for podcast transcript management"""

    def __init__(self, db_path: str = "data/podcasts/atlas_podcasts.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
        self._init_database()

    def _init_database(self):
        """Initialize database schema"""
        with self._get_connection() as conn:
            # Enable WAL mode for better concurrency
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=30000")

            # Podcasts table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS podcasts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    slug TEXT UNIQUE NOT NULL,
                    rss_url TEXT NOT NULL,
                    site_url TEXT,
                    resolver TEXT DEFAULT 'generic_html',
                    episode_selector TEXT,
                    transcript_selector TEXT,
                    config TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Episodes table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS episodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    podcast_id INTEGER NOT NULL,
                    guid TEXT NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    publish_date TIMESTAMP,
                    transcript_url TEXT,
                    transcript_status TEXT DEFAULT 'unknown',
                    transcript_path TEXT,
                    metadata TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (podcast_id) REFERENCES podcasts (id),
                    UNIQUE (podcast_id, guid)
                )
            """
            )

            # Transcript sources table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS transcript_sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    episode_id INTEGER NOT NULL,
                    resolver TEXT NOT NULL,
                    url TEXT NOT NULL,
                    confidence REAL DEFAULT 0.0,
                    metadata TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (episode_id) REFERENCES episodes (id)
                )
            """
            )

            # Discovery runs table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS discovery_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    podcast_id INTEGER NOT NULL,
                    resolver TEXT NOT NULL,
                    episodes_found INTEGER DEFAULT 0,
                    transcripts_found INTEGER DEFAULT 0,
                    errors INTEGER DEFAULT 0,
                    duration_seconds REAL DEFAULT 0.0,
                    status TEXT DEFAULT 'running',
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (podcast_id) REFERENCES podcasts (id)
                )
            """
            )

            # Create indexes
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_episodes_podcast_id ON episodes (podcast_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_episodes_status ON episodes (transcript_status)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_transcript_sources_episode_id ON transcript_sources (episode_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_discovery_runs_podcast_id ON discovery_runs (podcast_id)"
            )

    @contextmanager
    def _get_connection(self):
        """Get database connection with automatic commit/rollback"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _serialize_dict(self, data: Dict[str, Any]) -> str:
        """Serialize dictionary to JSON string"""
        return json.dumps(data) if data else "{}"

    def _deserialize_dict(self, data: str) -> Dict[str, Any]:
        """Deserialize JSON string to dictionary"""
        try:
            return json.loads(data) if data else {}
        except json.JSONDecodeError:
            return {}

    # Podcast CRUD operations
    def create_podcast(self, podcast: Podcast) -> int:
        """Create new podcast, return ID"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO podcasts
                (name, slug, rss_url, site_url, resolver, episode_selector, transcript_selector, config)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    podcast.name,
                    podcast.slug,
                    podcast.rss_url,
                    podcast.site_url,
                    podcast.resolver,
                    podcast.episode_selector,
                    podcast.transcript_selector,
                    self._serialize_dict(podcast.config),
                ),
            )
            return cursor.lastrowid

    def get_podcast(self, podcast_id: int) -> Optional[Podcast]:
        """Get podcast by ID"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM podcasts WHERE id = ?", (podcast_id,)
            ).fetchone()
            if row:
                return Podcast(
                    id=row["id"],
                    name=row["name"],
                    slug=row["slug"],
                    rss_url=row["rss_url"],
                    site_url=row["site_url"],
                    resolver=row["resolver"],
                    episode_selector=row["episode_selector"],
                    transcript_selector=row["transcript_selector"],
                    config=self._deserialize_dict(row["config"]),
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
        return None

    def get_podcast_by_slug(self, slug: str) -> Optional[Podcast]:
        """Get podcast by slug"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM podcasts WHERE slug = ?", (slug,)
            ).fetchone()
            if row:
                return Podcast(
                    id=row["id"],
                    name=row["name"],
                    slug=row["slug"],
                    rss_url=row["rss_url"],
                    site_url=row["site_url"],
                    resolver=row["resolver"],
                    episode_selector=row["episode_selector"],
                    transcript_selector=row["transcript_selector"],
                    config=self._deserialize_dict(row["config"]),
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
        return None

    def list_podcasts(self) -> List[Podcast]:
        """List all podcasts"""
        podcasts = []
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM podcasts ORDER BY name").fetchall()
            for row in rows:
                podcasts.append(
                    Podcast(
                        id=row["id"],
                        name=row["name"],
                        slug=row["slug"],
                        rss_url=row["rss_url"],
                        site_url=row["site_url"],
                        resolver=row["resolver"],
                        episode_selector=row["episode_selector"],
                        transcript_selector=row["transcript_selector"],
                        config=self._deserialize_dict(row["config"]),
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                    )
                )
        return podcasts

    # Episode CRUD operations
    def create_episode(self, episode: Episode) -> int:
        """Create new episode, return ID"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT OR REPLACE INTO episodes
                (podcast_id, guid, title, url, publish_date, transcript_url,
                 transcript_status, transcript_path, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    episode.podcast_id,
                    episode.guid,
                    episode.title,
                    episode.url,
                    episode.publish_date,
                    episode.transcript_url,
                    episode.transcript_status,
                    episode.transcript_path,
                    self._serialize_dict(episode.metadata),
                ),
            )
            return cursor.lastrowid

    def get_episodes_by_podcast(self, podcast_id: int) -> List[Episode]:
        """Get all episodes for a podcast"""
        episodes = []
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM episodes WHERE podcast_id = ?
                ORDER BY publish_date DESC
            """,
                (podcast_id,),
            ).fetchall()
            for row in rows:
                episodes.append(
                    Episode(
                        id=row["id"],
                        podcast_id=row["podcast_id"],
                        guid=row["guid"],
                        title=row["title"],
                        url=row["url"],
                        publish_date=row["publish_date"],
                        transcript_url=row["transcript_url"],
                        transcript_status=row["transcript_status"],
                        transcript_path=row["transcript_path"],
                        metadata=self._deserialize_dict(row["metadata"]),
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                    )
                )
        return episodes

    def get_all_podcast_stats(self) -> List[dict]:
        """
        Get aggregated stats for all podcasts in a single query.

        Returns list of dicts with: slug, name, total, fetched, pending, failed, coverage
        """
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    p.slug,
                    p.name,
                    COUNT(CASE WHEN e.transcript_status != 'excluded' THEN 1 END) as total,
                    COUNT(CASE WHEN e.transcript_status = 'fetched' THEN 1 END) as fetched,
                    COUNT(CASE WHEN e.transcript_status IN ('unknown', 'found') THEN 1 END) as pending,
                    COUNT(CASE WHEN e.transcript_status = 'failed' THEN 1 END) as failed
                FROM podcasts p
                LEFT JOIN episodes e ON p.id = e.podcast_id
                GROUP BY p.id, p.slug, p.name
                HAVING total > 0
                ORDER BY p.name
                """
            ).fetchall()

            return [
                {
                    'slug': row['slug'],
                    'name': row['name'],
                    'total': row['total'],
                    'fetched': row['fetched'],
                    'pending': row['pending'],
                    'failed': row['failed'],
                    'coverage': round((row['fetched'] / row['total']) * 100, 1) if row['total'] > 0 else 0
                }
                for row in rows
            ]

    def get_overall_stats(self) -> dict:
        """
        Get overall transcript statistics in a single query.

        Returns dict with: total_episodes, fetched, pending, failed, coverage
        """
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(CASE WHEN transcript_status != 'excluded' THEN 1 END) as total,
                    COUNT(CASE WHEN transcript_status = 'fetched' THEN 1 END) as fetched,
                    COUNT(CASE WHEN transcript_status IN ('unknown', 'found') THEN 1 END) as pending,
                    COUNT(CASE WHEN transcript_status = 'failed' THEN 1 END) as failed
                FROM episodes
                """
            ).fetchone()

            total = row['total'] or 0
            fetched = row['fetched'] or 0
            pending = row['pending'] or 0
            failed = row['failed'] or 0

            return {
                'total_episodes': total,
                'fetched': fetched,
                'pending': pending,
                'failed': failed,
                'coverage': round((fetched / total) * 100, 1) if total > 0 else 0
            }

    def update_episode_transcript_status(
        self, episode_id: int, status: str, transcript_path: Optional[str] = None
    ):
        """Update episode transcript status"""
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE episodes
                SET transcript_status = ?, transcript_path = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """,
                (status, transcript_path, episode_id),
            )

    # Discovery run tracking
    def create_discovery_run(self, run: DiscoveryRun) -> int:
        """Create new discovery run, return ID"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO discovery_runs
                (podcast_id, resolver, episodes_found, transcripts_found, errors,
                 duration_seconds, status, started_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    run.podcast_id,
                    run.resolver,
                    run.episodes_found,
                    run.transcripts_found,
                    run.errors,
                    run.duration_seconds,
                    run.status,
                    run.started_at,
                ),
            )
            return cursor.lastrowid

    def complete_discovery_run(
        self,
        run_id: int,
        episodes_found: int,
        transcripts_found: int,
        errors: int,
        duration_seconds: float,
        status: str = "completed",
    ):
        """Complete discovery run with final stats"""
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE discovery_runs
                SET episodes_found = ?, transcripts_found = ?, errors = ?,
                    duration_seconds = ?, status = ?, completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """,
                (
                    episodes_found,
                    transcripts_found,
                    errors,
                    duration_seconds,
                    status,
                    run_id,
                ),
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        with self._get_connection() as conn:
            stats = {}

            # Podcast count
            stats["total_podcasts"] = conn.execute(
                "SELECT COUNT(*) FROM podcasts"
            ).fetchone()[0]

            # Episode counts by status
            episode_stats = conn.execute(
                """
                SELECT transcript_status, COUNT(*) as count
                FROM episodes
                GROUP BY transcript_status
            """
            ).fetchall()
            stats["episodes_by_status"] = {
                row["transcript_status"]: row["count"] for row in episode_stats
            }

            # Recent discovery runs
            recent_runs = conn.execute(
                """
                SELECT podcast_id, resolver, episodes_found, transcripts_found,
                       errors, completed_at, status
                FROM discovery_runs
                ORDER BY started_at DESC
                LIMIT 10
            """
            ).fetchall()
            stats["recent_runs"] = [dict(row) for row in recent_runs]

        return stats
