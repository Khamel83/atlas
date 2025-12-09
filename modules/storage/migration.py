"""
Migration - Import data from legacy SQLite databases.

Migrates content from atlas_content_before_reorg.db (2,373 episodes)
and other legacy databases into the file-based storage system.
"""

import sqlite3
import logging
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

from .content_types import ContentItem, ContentType, SourceType, ProcessingStatus
from .file_store import FileStore
from .index_manager import IndexManager

logger = logging.getLogger(__name__)


class LegacyMigrator:
    """Migrate content from legacy SQLite databases."""

    def __init__(self, file_store: FileStore, index_manager: IndexManager):
        """
        Initialize migrator.

        Args:
            file_store: FileStore to save migrated content
            index_manager: IndexManager to index migrated content
        """
        self.file_store = file_store
        self.index_manager = index_manager
        self.stats = {
            "podcasts_migrated": 0,
            "episodes_migrated": 0,
            "content_items_migrated": 0,
            "skipped_duplicates": 0,
            "errors": 0,
        }

    def migrate_podcast_db(self, db_path: str) -> Dict[str, Any]:
        """
        Migrate from atlas_content_before_reorg.db (podcast episodes).

        Args:
            db_path: Path to the legacy database

        Returns:
            Migration statistics
        """
        db_path = Path(db_path)
        if not db_path.exists():
            raise FileNotFoundError(f"Database not found: {db_path}")

        logger.info(f"Migrating podcast database: {db_path}")

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row

        try:
            # First, get all podcasts
            podcasts = {}
            for row in conn.execute("SELECT * FROM podcasts"):
                podcasts[row["id"]] = dict(row)
                self.stats["podcasts_migrated"] += 1

            logger.info(f"Found {len(podcasts)} podcasts")

            # Then migrate episodes
            for row in conn.execute("""
                SELECT e.*, p.name as podcast_name, p.rss_feed
                FROM episodes e
                JOIN podcasts p ON e.podcast_id = p.id
            """):
                try:
                    self._migrate_episode(dict(row))
                    self.stats["episodes_migrated"] += 1
                except Exception as e:
                    logger.error(f"Error migrating episode {row['id']}: {e}")
                    self.stats["errors"] += 1

                if self.stats["episodes_migrated"] % 100 == 0:
                    logger.info(f"Migrated {self.stats['episodes_migrated']} episodes...")

        finally:
            conn.close()

        logger.info(f"Migration complete: {self.stats}")
        return self.stats

    def _migrate_episode(self, episode: Dict[str, Any]):
        """Migrate a single episode to file storage."""
        # Generate content ID from episode URL or title
        source_url = episode.get("url") or episode.get("link")
        content_id = ContentItem.generate_id(
            source_url=source_url,
            title=episode.get("title", ""),
        )

        # Check for duplicates
        if self.file_store.exists(content_id, ContentType.PODCAST):
            self.stats["skipped_duplicates"] += 1
            return

        # Parse dates
        created_at = datetime.utcnow()
        published_at = None
        if episode.get("published_at"):
            try:
                published_at = datetime.fromisoformat(
                    str(episode["published_at"]).replace("Z", "+00:00")
                )
                created_at = published_at
            except (ValueError, TypeError):
                pass

        # Create content item
        item = ContentItem(
            content_id=content_id,
            content_type=ContentType.PODCAST,
            source_type=SourceType.MIGRATION,
            title=episode.get("title", "Untitled Episode"),
            source_url=source_url,
            podcast_name=episode.get("podcast_name"),
            episode_number=episode.get("episode_number"),
            audio_url=episode.get("audio_url") or episode.get("enclosure_url"),
            description=episode.get("description", ""),
            created_at=created_at,
            published_at=published_at,
            status=ProcessingStatus.PENDING,
            extra={
                "legacy_id": episode.get("id"),
                "rss_feed": episode.get("rss_feed"),
                "migrated_at": datetime.utcnow().isoformat(),
            }
        )

        # Check for existing transcript content
        transcript = episode.get("transcript") or episode.get("content")

        # Save to file store
        item_dir = self.file_store.save(item, content=transcript)

        # Index the item
        self.index_manager.index_item(item, str(item_dir), search_text=transcript)

    def migrate_unified_db(self, db_path: str) -> Dict[str, Any]:
        """
        Migrate from atlas_unified.db (general content items).

        Args:
            db_path: Path to the legacy database

        Returns:
            Migration statistics
        """
        db_path = Path(db_path)
        if not db_path.exists():
            raise FileNotFoundError(f"Database not found: {db_path}")

        logger.info(f"Migrating unified database: {db_path}")

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row

        try:
            for row in conn.execute("SELECT * FROM content_items"):
                try:
                    self._migrate_content_item(dict(row))
                    self.stats["content_items_migrated"] += 1
                except Exception as e:
                    logger.error(f"Error migrating content item {row.get('id')}: {e}")
                    self.stats["errors"] += 1

                if self.stats["content_items_migrated"] % 100 == 0:
                    logger.info(
                        f"Migrated {self.stats['content_items_migrated']} content items..."
                    )

        finally:
            conn.close()

        logger.info(f"Migration complete: {self.stats}")
        return self.stats

    def _migrate_content_item(self, item_data: Dict[str, Any]):
        """Migrate a single content item to file storage."""
        source_url = item_data.get("url") or item_data.get("source_url")
        content_id = ContentItem.generate_id(
            source_url=source_url,
            title=item_data.get("title", ""),
        )

        # Check for duplicates
        existing_type = self._guess_content_type(item_data)
        if self.file_store.exists(content_id, existing_type):
            self.stats["skipped_duplicates"] += 1
            return

        # Parse dates
        created_at = datetime.utcnow()
        if item_data.get("created_at"):
            try:
                created_at = datetime.fromisoformat(
                    str(item_data["created_at"]).replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass

        # Create content item
        item = ContentItem(
            content_id=content_id,
            content_type=existing_type,
            source_type=SourceType.MIGRATION,
            title=item_data.get("title", "Untitled"),
            source_url=source_url,
            description=item_data.get("description") or item_data.get("summary"),
            created_at=created_at,
            status=ProcessingStatus.COMPLETED,
            extra={
                "legacy_id": item_data.get("id"),
                "migrated_at": datetime.utcnow().isoformat(),
            }
        )

        # Get content
        content = item_data.get("content") or item_data.get("body") or ""

        # Save to file store
        item_dir = self.file_store.save(item, content=content)

        # Index the item
        self.index_manager.index_item(item, str(item_dir), search_text=content)

    def _guess_content_type(self, item_data: Dict[str, Any]) -> ContentType:
        """Guess content type from legacy item data."""
        content_type = item_data.get("content_type", "").lower()
        source = item_data.get("source", "").lower()
        url = item_data.get("url", "").lower()

        if "podcast" in content_type or "podcast" in source:
            return ContentType.PODCAST
        elif "youtube" in content_type or "youtube.com" in url or "youtu.be" in url:
            return ContentType.YOUTUBE
        elif "newsletter" in content_type or "newsletter" in source:
            return ContentType.NEWSLETTER
        elif "email" in content_type or "email" in source:
            return ContentType.EMAIL
        else:
            return ContentType.ARTICLE


def run_full_migration(
    podcast_db: str = "data/databases/atlas_content_before_reorg.db",
    unified_db: str = "data/databases/atlas_unified.db",
    archive_dir: str = "archive/legacy_databases"
) -> Dict[str, Any]:
    """
    Run full migration from all legacy databases.

    Args:
        podcast_db: Path to podcast database
        unified_db: Path to unified content database
        archive_dir: Directory to move legacy databases after migration

    Returns:
        Combined migration statistics
    """
    file_store = FileStore()
    index_manager = IndexManager()
    migrator = LegacyMigrator(file_store, index_manager)

    total_stats = {}

    # Migrate podcast database
    if Path(podcast_db).exists():
        logger.info(f"Starting podcast database migration: {podcast_db}")
        stats = migrator.migrate_podcast_db(podcast_db)
        total_stats["podcast_db"] = stats

    # Migrate unified database
    if Path(unified_db).exists():
        logger.info(f"Starting unified database migration: {unified_db}")
        stats = migrator.migrate_unified_db(unified_db)
        total_stats["unified_db"] = stats

    # Archive legacy databases
    archive_path = Path(archive_dir)
    archive_path.mkdir(parents=True, exist_ok=True)

    for db_file in [podcast_db, unified_db]:
        if Path(db_file).exists():
            dest = archive_path / Path(db_file).name
            shutil.move(db_file, dest)
            logger.info(f"Archived {db_file} to {dest}")

    total_stats["final"] = migrator.stats
    logger.info(f"Full migration complete: {total_stats}")
    return total_stats


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) > 1 and sys.argv[1] == "--run":
        run_full_migration()
    else:
        print("Usage: python -m modules.storage.migration --run")
        print("This will migrate all legacy databases to file-based storage.")
