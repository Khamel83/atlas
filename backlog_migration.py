#!/usr/bin/env python3
"""
Atlas v1 → v2 Complete Backlog Migration

This script migrates ALL pending episodes from Atlas v1 to Atlas v2
and configures Atlas v2 for high-throughput backlog processing.
"""

import sqlite3
import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add Atlas v2 modules
sys.path.append('/home/ubuntu/dev/atlas/atlas_v2')

from modules.database import DatabaseManager
from modules.id_generator import IDGenerator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AtlasBacklogMigrator:
    """Complete Atlas v1 → v2 backlog migration"""

    def __init__(self):
        self.v1_queue_db = "/home/ubuntu/dev/atlas/output/processing_queue.db"
        self.v2_db = DatabaseManager(db_path="/home/ubuntu/dev/atlas/atlas_v2/data/atlas_v2.db")
        self.id_generator = IDGenerator()
        self.migrated_count = 0
        self.error_count = 0

    async def migrate_entire_backlog(self):
        """Migrate all pending episodes from Atlas v1 to Atlas v2"""
        logger.info("🚀 Starting complete Atlas v1 → v2 backlog migration...")

        # Initialize Atlas v2 database
        await self.v2_db.init_database()

        # Connect to Atlas v1 queue database
        v1_conn = sqlite3.connect(self.v1_queue_db)
        v1_conn.row_factory = sqlite3.Row

        try:
            # Get all pending episodes
            cursor = v1_conn.execute("""
                SELECT
                    episode_url,
                    episode_title,
                    podcast_name,
                    episode_description,
                    transcript_url,
                    created_at,
                    updated_at
                FROM processing_queue
                WHERE status = 'pending'
                ORDER BY created_at ASC
            """)

            pending_episodes = cursor.fetchall()
            logger.info(f"📊 Found {len(pending_episodes)} pending episodes to migrate")

            # Process in batches
            batch_size = 50
            batch = []

            for episode in pending_episodes:
                # Create content ID
                title = episode['episode_title'] or 'unknown'
                date_str = self._extract_date_from_title(title) or datetime.now().strftime('%Y-%m-%d')
                slug = self.id_generator._create_slug(title)
                content_id = f"podcast-{date_str}-{slug}"

                # Create metadata
                metadata = {
                    'title': episode['episode_title'],
                    'podcast_name': episode['podcast_name'],
                    'description': episode['episode_description'],
                    'transcript_url': episode['transcript_url'],
                    'migrated_from': 'atlas_v1',
                    'original_created_at': episode['created_at'],
                    'priority': 'high'  # Prioritize backlog items
                }

                batch.append({
                    'content_id': content_id,
                    'source_url': episode['episode_url'],
                    'source_name': episode['podcast_name'],
                    'content_type': 'podcast',
                    'metadata': metadata,
                    'created_at': episode['created_at']
                })

                # Process batch
                if len(batch) >= batch_size:
                    await self._process_batch(batch)
                    batch = []

            # Process remaining batch
            if batch:
                await self._process_batch(batch)

            logger.info(f"✅ Migration complete!")
            logger.info(f"📊 Successfully migrated: {self.migrated_count} episodes")
            logger.info(f"❌ Failed to migrate: {self.error_count} episodes")

        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            raise
        finally:
            v1_conn.close()

    def _extract_date_from_title(self, title):
        """Try to extract date from episode title"""
        import re
        # Look for common date patterns
        date_patterns = [
            r'(\d{4}-\d{2}-\d{2})',
            r'(\d{1,2}/\d{1,2}/\d{4})',
            r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}'
        ]

        for pattern in date_patterns:
            match = re.search(pattern, title)
            if match:
                return match.group(1)

        return None

    async def _process_batch(self, batch):
        """Process a batch of episodes"""
        logger.info(f"📦 Processing batch of {len(batch)} episodes...")

        for item in batch:
            try:
                # Check if already exists
                existing = await self.v2_db.get_queue_item(item['content_id'])
                if existing:
                    logger.debug(f"⏭️ Skipping {item['content_id']} - already exists")
                    continue

                # Add to Atlas v2 queue
                await self.v2_db.add_to_queue(
                    content_id=item['content_id'],
                    url=item['source_url'],
                    content_type=item['content_type'],
                    metadata=item['metadata']
                )

                self.migrated_count += 1

                if self.migrated_count % 25 == 0:
                    logger.info(f"📊 Progress: {self.migrated_count} episodes migrated...")

            except Exception as e:
                logger.error(f"❌ Failed to migrate {item['content_id']}: {e}")
                self.error_count += 1

async def main():
    """Run the complete backlog migration"""
    migrator = AtlasBacklogMigrator()
    await migrator.migrate_entire_backlog()

if __name__ == "__main__":
    asyncio.run(main())