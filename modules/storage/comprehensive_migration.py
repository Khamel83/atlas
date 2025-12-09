"""
Comprehensive Migration - Slurp ALL existing data from everywhere.

This migrator finds and consolidates:
- Metadata JSON files (metadata/*.json)
- Markdown content (markdown/*.md)
- HTML content (html/*.html)
- SQLite databases (*.db files)
- Duplicate copies in mac_data/, "data for atlas/", etc.

All content is deduplicated and migrated to the file-based storage system.
"""

import os
import json
import sqlite3
import logging
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, Set, List, Iterator
from dataclasses import dataclass

from .content_types import ContentItem, ContentType, SourceType, ProcessingStatus
from .file_store import FileStore
from .index_manager import IndexManager

logger = logging.getLogger(__name__)


@dataclass
class MigrationStats:
    """Track migration progress."""
    items_found: int = 0
    items_migrated: int = 0
    items_skipped_duplicate: int = 0
    items_failed: int = 0
    sources_processed: List[str] = None

    def __post_init__(self):
        if self.sources_processed is None:
            self.sources_processed = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "items_found": self.items_found,
            "items_migrated": self.items_migrated,
            "items_skipped_duplicate": self.items_skipped_duplicate,
            "items_failed": self.items_failed,
            "sources_processed": self.sources_processed,
        }


class ComprehensiveMigrator:
    """Migrate ALL existing data to file-based storage."""

    def __init__(self, base_dir: str = "."):
        """
        Initialize migrator.

        Args:
            base_dir: Atlas project root directory
        """
        self.base_dir = Path(base_dir)
        self.file_store = FileStore("data/content")
        self.index_manager = IndexManager("data/indexes/atlas_index.db")
        self.stats = MigrationStats()
        self.seen_urls: Set[str] = set()
        self.seen_ids: Set[str] = set()

    def run_full_migration(self) -> MigrationStats:
        """Run complete migration from all sources."""
        logger.info("Starting comprehensive migration...")

        # 1. Migrate from metadata/ + markdown/ + html/ (primary source)
        self._migrate_from_metadata_dir()

        # 2. Migrate from SQLite databases
        self._migrate_from_databases()

        # 3. Check for any orphaned content files
        self._migrate_orphaned_content()

        # 4. Clean up empty directories
        self.file_store.cleanup_empty_dirs()

        logger.info(f"Migration complete: {self.stats.to_dict()}")
        return self.stats

    def _migrate_from_metadata_dir(self):
        """Migrate from metadata/*.json with corresponding markdown/html files."""
        metadata_dir = self.base_dir / "metadata"
        markdown_dir = self.base_dir / "markdown"
        html_dir = self.base_dir / "html"

        if not metadata_dir.exists():
            logger.warning("No metadata/ directory found")
            return

        logger.info(f"Migrating from {metadata_dir}...")
        self.stats.sources_processed.append(str(metadata_dir))

        for json_file in metadata_dir.glob("*.json"):
            try:
                self.stats.items_found += 1
                self._migrate_metadata_item(json_file, markdown_dir, html_dir)
            except Exception as e:
                logger.error(f"Error migrating {json_file}: {e}")
                self.stats.items_failed += 1

            if self.stats.items_found % 500 == 0:
                logger.info(f"Processed {self.stats.items_found} items...")

    def _migrate_metadata_item(self, json_file: Path, markdown_dir: Path, html_dir: Path):
        """Migrate a single metadata item."""
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        uid = data.get("uid", json_file.stem)
        source_url = data.get("source", "")

        # Check for duplicates
        if source_url and source_url in self.seen_urls:
            self.stats.items_skipped_duplicate += 1
            return
        if uid in self.seen_ids:
            self.stats.items_skipped_duplicate += 1
            return

        if source_url:
            self.seen_urls.add(source_url)
        self.seen_ids.add(uid)

        # Determine content type
        content_type = self._map_content_type(data.get("content_type", ""))

        # Parse dates
        created_at = datetime.utcnow()
        date_str = data.get("date") or data.get("created_at")
        if date_str:
            try:
                created_at = datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        # Create content item
        item = ContentItem(
            content_id=uid,
            content_type=content_type,
            source_type=SourceType.MIGRATION,
            title=data.get("title", "Untitled"),
            source_url=source_url,
            description=data.get("type_specific", {}).get("cleaned_selection", "")[:500] if data.get("type_specific") else "",
            tags=data.get("tags", []),
            created_at=created_at,
            status=ProcessingStatus.COMPLETED,
            extra={
                "legacy_uid": uid,
                "original_content_type": data.get("content_type"),
                "fetch_method": data.get("fetch_method"),
                "domain": data.get("type_specific", {}).get("domain") if data.get("type_specific") else None,
            }
        )

        # Load markdown content
        content = None
        md_file = markdown_dir / f"{uid}.md"
        if md_file.exists():
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()

        # Save to new storage
        item_dir = self.file_store.save(item, content=content)

        # Index the item
        self.index_manager.index_item(item, str(item_dir), search_text=content)

        self.stats.items_migrated += 1

    def _migrate_from_databases(self):
        """Migrate from all SQLite databases."""
        db_files = [
            self.base_dir / "data/databases/atlas_content_before_reorg.db",
            self.base_dir / "data/databases/atlas_unified.db",
            self.base_dir / "podcast_processing.db",
        ]

        for db_file in db_files:
            if db_file.exists():
                try:
                    self._migrate_database(db_file)
                except Exception as e:
                    logger.error(f"Error migrating database {db_file}: {e}")

    def _migrate_database(self, db_path: Path):
        """Migrate from a single SQLite database."""
        logger.info(f"Migrating database: {db_path}")
        self.stats.sources_processed.append(str(db_path))

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row

        try:
            # Check what tables exist
            tables = [row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()]

            # Migrate podcasts/episodes
            if "episodes" in tables:
                self._migrate_podcast_episodes(conn)

            # Migrate content_items
            if "content_items" in tables:
                self._migrate_content_items(conn)

        finally:
            conn.close()

    def _migrate_podcast_episodes(self, conn):
        """Migrate podcast episodes from database."""
        try:
            # Try to join with podcasts table
            query = """
                SELECT e.*, p.name as podcast_name, p.rss_feed
                FROM episodes e
                LEFT JOIN podcasts p ON e.podcast_id = p.id
            """
            rows = conn.execute(query).fetchall()
        except sqlite3.OperationalError:
            # Fallback if no podcasts table
            rows = conn.execute("SELECT * FROM episodes").fetchall()

        for row in rows:
            try:
                self.stats.items_found += 1
                self._migrate_episode_row(dict(row))
            except Exception as e:
                logger.error(f"Error migrating episode: {e}")
                self.stats.items_failed += 1

    def _migrate_episode_row(self, data: Dict[str, Any]):
        """Migrate a single podcast episode."""
        source_url = data.get("url") or data.get("link", "")
        title = data.get("title", "Untitled Episode")

        # Generate consistent ID
        content_id = ContentItem.generate_id(source_url=source_url, title=title)

        # Check duplicates
        if source_url and source_url in self.seen_urls:
            self.stats.items_skipped_duplicate += 1
            return
        if content_id in self.seen_ids:
            self.stats.items_skipped_duplicate += 1
            return

        if source_url:
            self.seen_urls.add(source_url)
        self.seen_ids.add(content_id)

        # Parse dates
        created_at = datetime.utcnow()
        if data.get("published_at"):
            try:
                created_at = datetime.fromisoformat(
                    str(data["published_at"]).replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass

        item = ContentItem(
            content_id=content_id,
            content_type=ContentType.PODCAST,
            source_type=SourceType.MIGRATION,
            title=title,
            source_url=source_url,
            podcast_name=data.get("podcast_name"),
            episode_number=data.get("episode_number"),
            audio_url=data.get("audio_url") or data.get("enclosure_url"),
            description=data.get("description", ""),
            created_at=created_at,
            published_at=created_at,
            status=ProcessingStatus.PENDING,
            extra={
                "legacy_id": data.get("id"),
                "rss_feed": data.get("rss_feed"),
            }
        )

        transcript = data.get("transcript") or data.get("content")
        if transcript:
            item.status = ProcessingStatus.COMPLETED

        item_dir = self.file_store.save(item, content=transcript)
        self.index_manager.index_item(item, str(item_dir), search_text=transcript)
        self.stats.items_migrated += 1

    def _migrate_content_items(self, conn):
        """Migrate content_items table."""
        rows = conn.execute("SELECT * FROM content_items").fetchall()

        for row in rows:
            try:
                self.stats.items_found += 1
                self._migrate_content_item_row(dict(row))
            except Exception as e:
                logger.error(f"Error migrating content item: {e}")
                self.stats.items_failed += 1

    def _migrate_content_item_row(self, data: Dict[str, Any]):
        """Migrate a single content item row."""
        source_url = data.get("url") or data.get("source_url", "")
        title = data.get("title", "Untitled")

        content_id = ContentItem.generate_id(source_url=source_url, title=title)

        if source_url and source_url in self.seen_urls:
            self.stats.items_skipped_duplicate += 1
            return
        if content_id in self.seen_ids:
            self.stats.items_skipped_duplicate += 1
            return

        if source_url:
            self.seen_urls.add(source_url)
        self.seen_ids.add(content_id)

        content_type = self._map_content_type(data.get("content_type", ""))

        created_at = datetime.utcnow()
        if data.get("created_at"):
            try:
                created_at = datetime.fromisoformat(
                    str(data["created_at"]).replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass

        item = ContentItem(
            content_id=content_id,
            content_type=content_type,
            source_type=SourceType.MIGRATION,
            title=title,
            source_url=source_url,
            description=data.get("description") or data.get("summary", ""),
            created_at=created_at,
            status=ProcessingStatus.COMPLETED,
            extra={"legacy_id": data.get("id")}
        )

        content = data.get("content") or data.get("body")
        item_dir = self.file_store.save(item, content=content)
        self.index_manager.index_item(item, str(item_dir), search_text=content)
        self.stats.items_migrated += 1

    def _migrate_orphaned_content(self):
        """Check for markdown files without metadata and migrate them."""
        markdown_dir = self.base_dir / "markdown"
        metadata_dir = self.base_dir / "metadata"

        if not markdown_dir.exists():
            return

        for md_file in markdown_dir.glob("*.md"):
            uid = md_file.stem
            metadata_file = metadata_dir / f"{uid}.json"

            # Skip if already processed via metadata
            if metadata_file.exists() or uid in self.seen_ids:
                continue

            try:
                self.stats.items_found += 1
                self._migrate_orphan_markdown(md_file)
            except Exception as e:
                logger.error(f"Error migrating orphan {md_file}: {e}")
                self.stats.items_failed += 1

    def _migrate_orphan_markdown(self, md_file: Path):
        """Migrate a markdown file without metadata."""
        uid = md_file.stem

        if uid in self.seen_ids:
            self.stats.items_skipped_duplicate += 1
            return

        self.seen_ids.add(uid)

        with open(md_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Try to extract title from first line
        lines = content.split("\n")
        title = "Untitled"
        for line in lines:
            if line.startswith("# "):
                title = line[2:].strip()
                break

        # Try to extract URL from content
        source_url = None
        for line in lines:
            if line.startswith("**Source:**"):
                source_url = line.replace("**Source:**", "").strip()
                break

        item = ContentItem(
            content_id=uid,
            content_type=ContentType.ARTICLE,
            source_type=SourceType.MIGRATION,
            title=title,
            source_url=source_url,
            created_at=datetime.fromtimestamp(md_file.stat().st_mtime),
            status=ProcessingStatus.COMPLETED,
            extra={"source_file": str(md_file)}
        )

        item_dir = self.file_store.save(item, content=content)
        self.index_manager.index_item(item, str(item_dir), search_text=content)
        self.stats.items_migrated += 1

    def _map_content_type(self, legacy_type: str) -> ContentType:
        """Map legacy content type to new ContentType enum."""
        legacy_type = legacy_type.lower()

        if "podcast" in legacy_type or "episode" in legacy_type:
            return ContentType.PODCAST
        elif "youtube" in legacy_type or "video" in legacy_type:
            return ContentType.YOUTUBE
        elif "newsletter" in legacy_type:
            return ContentType.NEWSLETTER
        elif "email" in legacy_type:
            return ContentType.EMAIL
        elif "document" in legacy_type or "pdf" in legacy_type:
            return ContentType.DOCUMENT
        elif "note" in legacy_type:
            return ContentType.NOTE
        else:
            return ContentType.ARTICLE


def run_migration():
    """Run the comprehensive migration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    migrator = ComprehensiveMigrator()
    stats = migrator.run_full_migration()

    print("\n" + "="*50)
    print("MIGRATION COMPLETE")
    print("="*50)
    print(f"Items found:      {stats.items_found}")
    print(f"Items migrated:   {stats.items_migrated}")
    print(f"Duplicates:       {stats.items_skipped_duplicate}")
    print(f"Errors:           {stats.items_failed}")
    print(f"Sources:          {stats.sources_processed}")
    print("="*50)

    return stats


if __name__ == "__main__":
    run_migration()
