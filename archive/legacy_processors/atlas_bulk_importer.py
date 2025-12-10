#!/usr/bin/env python3
"""
Atlas Bulk Importer
Imports all existing Atlas data into universal bookmarking system
"""

import os
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from atlas_universal_bookmarker import AtlasUniversalBookmarker
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AtlasBulkImporter:
    """Bulk import all existing Atlas data"""

    def __init__(self):
        self.bookmarker = AtlasUniversalBookmarker()
        self.project_root = Path("/home/ubuntu/dev/atlas")

    def import_backup_files(self):
        """Import all files from the backup directory"""
        print("📁 IMPORTING: Backup Files (11,347 files)")

        backup_dir = self.project_root / "atlas_backup_20251108_190319"
        if not backup_dir.exists():
            print(f"⚠️  Backup directory not found: {backup_dir}")
            return 0

        # Import all markdown files
        markdown_dir = backup_dir / "relayq_jobs"
        if markdown_dir.exists():
            imported = self.bookmarker.import_directory(markdown_dir, "*.md")
            print(f"✅ Imported {imported} RelayQ job files")
        else:
            print("⚠️  No relayq_jobs directory found in backup")

        # Look for other content files
        for pattern in ["*.md", "*.txt", "*.html"]:
            imported = self.bookmarker.import_directory(backup_dir, pattern)
            if imported > 0:
                print(f"✅ Imported {imported} {pattern} files from backup root")

        return imported

    def import_current_queue(self):
        """Import from current atlas_ingestion_queue"""
        print("\n📥 IMPORTING: Current Atlas Queue (1,414 items)")

        conn = sqlite3.connect("podcast_processing.db")
        cursor = conn.execute("""
            SELECT id, source_url, title, raw_content, source_type
            FROM atlas_ingestion_queue
            WHERE raw_content IS NOT NULL AND length(raw_content) > 100
        """)

        items = cursor.fetchall()
        imported = 0

        for item in items:
            item_id, source_url, title, raw_content, source_type = item

            try:
                bookmark_id = self.bookmarker.bookmark_text(
                    text=raw_content,
                    title=title,
                    url=source_url or "",
                    tags=f"ingestion_queue,source_type:{source_type}",
                    source="atlas_ingestion_queue"
                )
                if bookmark_id:
                    imported += 1
            except Exception as e:
                logger.error(f"Error importing queue item {item_id}: {e}")

        conn.close()
        print(f"✅ Imported {imported}/{len(items)} items from atlas_ingestion_queue")
        return imported

    def import_relayq_jobs(self):
        """Import from archived RelayQ jobs"""
        print("\n📋 IMPORTING: Archived RelayQ Jobs (378 files)")

        relayq_dir = self.project_root / "relayq_jobs_archived_20251116_172925"
        if not relayq_dir.exists():
            print(f"⚠️  RelayQ archive not found: {relayq_dir}")
            return 0

        imported = self.bookmarker.import_directory(relayq_dir, "*.md")
        print(f"✅ Imported {imported} RelayQ job files")
        return imported

    def import_content_directory(self):
        """Import from content/markdown directory"""
        print("\n📝 IMPORTING: Content Directory")

        content_dir = self.project_root / "content" / "markdown"
        if not content_dir.exists():
            print(f"⚠️  Content directory not found: {content_dir}")
            return 0

        imported = self.bookmarker.import_directory(content_dir, "*.md")
        print(f"✅ Imported {imported} content files")
        return imported

    def import_database_transcripts(self):
        """Import transcripts from main database"""
        print("\n🎙️  IMPORTING: Database Transcripts (152 episodes)")

        conn = sqlite3.connect("podcast_processing.db")
        cursor = conn.execute("""
            SELECT e.id, e.title, e.transcript_text, p.name as podcast_name, e.link
            FROM episodes e
            JOIN podcasts p ON e.podcast_id = p.id
            WHERE e.transcript_text IS NOT NULL AND length(e.transcript_text) > 1000
        """)

        episodes = cursor.fetchall()
        imported = 0

        for episode in episodes:
            episode_id, title, transcript_text, podcast_name, link = episodes[0]

            try:
                bookmark_id = self.bookmarker.bookmark_text(
                    text=transcript_text,
                    title=f"{podcast_name}: {title}",
                    url=link or "",
                    tags=f"transcript,podcast:{podcast_name},episode_id:{episode_id}",
                    source="podcast_database"
                )
                if bookmark_id:
                    imported += 1
            except Exception as e:
                logger.error(f"Error importing episode {episode_id}: {e}")

        conn.close()
        print(f"✅ Imported {imported} database transcripts")
        return imported

    def run_complete_import(self):
        """Run complete import of all existing data"""
        print("🚀 ATLAS BULK IMPORT - ALL DATA SOURCES")
        print("=" * 60)

        total_imported = 0

        # Import from all sources
        total_imported += self.import_backup_files()
        total_imported += self.import_current_queue()
        total_imported += self.import_relayq_jobs()
        total_imported += self.import_content_directory()
        total_imported += self.import_database_transcripts()

        # Final statistics
        print(f"\n🏁 BULK IMPORT COMPLETE!")
        print("=" * 60)

        stats = self.bookmarker.get_stats()
        print(f"📊 Total Bookmarks: {stats['total_bookmarks']:,}")
        print(f"📁 Total Imported This Session: {total_imported:,}")

        print(f"\n📋 By Content Type:")
        for content_type, count in stats['by_content_type'].items():
            print(f"   {content_type}: {count:,}")

        print(f"\n📂 By Source:")
        for source, count in list(stats['by_source'].items())[:10]:
            print(f"   {source}: {count:,}")

        return total_imported

if __name__ == "__main__":
    importer = AtlasBulkImporter()
    importer.run_complete_import()