#!/usr/bin/env python3
"""
Fixed Atlas Bulk Importer
Handles database locking with smaller batches and better error handling
"""

import os
import sqlite3
import json
import time
from datetime import datetime
from pathlib import Path
from atlas_universal_bookmarker import AtlasUniversalBookmarker
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AtlasBulkImporterFixed:
    """Fixed bulk importer with proper database handling"""

    def __init__(self):
        self.bookmarker = AtlasUniversalBookmarker()
        self.project_root = Path("/home/ubuntu/dev/atlas")

    def import_backup_files_batched(self, batch_size=50):
        """Import backup files in smaller batches to avoid database locks"""
        print("📁 IMPORTING: Backup Files (batched import)")

        backup_dir = self.project_root / "atlas_backup_20251108_190319"
        if not backup_dir.exists():
            print(f"⚠️  Backup directory not found: {backup_dir}")
            return 0

        # Find all markdown files
        markdown_files = list(backup_dir.rglob("*.md"))
        print(f"📊 Found {len(markdown_files)} markdown files")

        imported = 0
        for i in range(0, len(markdown_files), batch_size):
            batch = markdown_files[i:i+batch_size]
            print(f"📦 Processing batch {i//batch_size + 1}: {len(batch)} files")

            for file_path in batch:
                try:
                    # Use a fresh connection for each file
                    bookmarker = AtlasUniversalBookmarker()
                    if bookmarker.bookmark_file(
                        file_path,
                        tags=f"backup_import,batch:{i//batch_size + 1}",
                        source="atlas_backup"
                    ):
                        imported += 1

                    # Small delay to avoid overwhelming the database
                    time.sleep(0.1)

                except Exception as e:
                    logger.error(f"Error importing {file_path}: {e}")
                    continue

            # Pause between batches
            if i + batch_size < len(markdown_files):
                print(f"⏳ Pausing before next batch...")
                time.sleep(2)

        print(f"✅ Imported {imported}/{len(markdown_files)} backup files")
        return imported

    def import_current_queue_sample(self, limit=100):
        """Import a sample from current queue to test functionality"""
        print(f"\n📥 IMPORTING: Current Atlas Queue Sample (limit: {limit})")

        conn = sqlite3.connect("podcast_processing.db")
        cursor = conn.execute(f"""
            SELECT id, source_url, title, raw_content, source_type
            FROM atlas_ingestion_queue
            WHERE raw_content IS NOT NULL AND length(raw_content) > 100
            LIMIT {limit}
        """)

        items = cursor.fetchall()
        imported = 0

        for item in items:
            item_id, source_url, title, raw_content, source_type = item

            try:
                # Fresh bookmarker instance
                bookmarker = AtlasUniversalBookmarker()
                if bookmarker.bookmark_text(
                    text=raw_content,
                    title=title,
                    url=source_url or "",
                    tags=f"ingestion_queue,source_type:{source_type}",
                    source="atlas_ingestion_queue"
                ):
                    imported += 1

                time.sleep(0.1)  # Small delay

            except Exception as e:
                logger.error(f"Error importing queue item {item_id}: {e}")
                continue

        conn.close()
        print(f"✅ Imported {imported}/{len(items)} items from atlas_ingestion_queue")
        return imported

    def run_safe_import(self):
        """Run safe import with error handling"""
        print("🚀 ATLAS SAFE BULK IMPORT")
        print("=" * 50)

        total_imported = 0

        try:
            # Import current queue sample first
            total_imported += self.import_current_queue_sample(50)

            # Then import backup files in batches
            total_imported += self.import_backup_files_batched(batch_size=20)

        except Exception as e:
            logger.error(f"Import error: {e}")

        # Final statistics
        print(f"\n🏁 SAFE IMPORT COMPLETE!")
        print("=" * 50)

        try:
            stats = self.bookmarker.get_stats()
            print(f"📊 Total Bookmarks: {stats['total_bookmarks']:,}")
            print(f"📁 Total Imported This Session: {total_imported:,}")

            if stats['by_content_type']:
                print(f"\n📋 By Content Type:")
                for content_type, count in stats['by_content_type'].items():
                    print(f"   {content_type}: {count:,}")

        except Exception as e:
            logger.error(f"Error getting stats: {e}")

        return total_imported

if __name__ == "__main__":
    importer = AtlasBulkImporterFixed()
    importer.run_safe_import()