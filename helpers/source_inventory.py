#!/usr/bin/env python3
"""
Source Inventory Discovery System for Atlas

Implements the core "Are we done?" discovery logic that scans source files
vs database content to identify unprocessed work and creates stage 0 entries
in the content table for automatic processing through the Atlas pipeline.

This system ensures no content is left unprocessed by continuously discovering
gaps between source materials and processed content.
"""

import csv
import sqlite3
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import hashlib
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.numeric_stages import NumericStage

logger = logging.getLogger(__name__)

class SourceInventoryDiscovery:
    """
    Discovers unprocessed work from various source types and queues it for processing.

    The system scans:
    - Instapaper CSV exports for unprocessed URLs
    - Podcast episodes marked as unprocessed
    - Future: RSS feeds, YouTube channels, etc.
    """

    def __init__(self, db_path: str = "data/atlas.db", uploads_dir: str = "uploads"):
        self.db_path = db_path
        self.uploads_dir = Path(uploads_dir)
        self.batch_limit = 1000  # Process max 1000 items per run

    def discover_csv_work(self) -> List[Dict[str, Any]]:
        """
        Compare Instapaper CSV URLs against content table to find unprocessed URLs.

        Returns:
            List of unprocessed URL entries with metadata
        """
        logger.info("🔍 Discovering unprocessed CSV work...")

        # Find the latest Instapaper CSV file
        csv_files = list(self.uploads_dir.glob("*ip.csv"))
        if not csv_files:
            logger.warning("No Instapaper CSV files found in uploads directory")
            return []

        latest_csv = max(csv_files, key=lambda f: f.stat().st_mtime)
        logger.info(f"📄 Processing CSV file: {latest_csv}")

        # Read CSV and extract URLs
        csv_urls = []
        try:
            with open(latest_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    url = row.get('URL', '').strip()
                    title = row.get('Title', '').strip()
                    if url and url.startswith('http'):
                        csv_urls.append({
                            'url': url,
                            'title': title,
                            'source': f'instapaper_csv_{latest_csv.name}',
                            'folder': row.get('Folder', ''),
                            'timestamp': row.get('Timestamp', '')
                        })
        except Exception as e:
            logger.error(f"❌ Error reading CSV file {latest_csv}: {e}")
            return []

        logger.info(f"📊 Found {len(csv_urls)} URLs in CSV file")

        # Compare against existing content in database
        unprocessed_urls = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                for url_data in csv_urls:
                    url = url_data['url']
                    cursor = conn.execute("SELECT url FROM content WHERE url = ?", (url,))
                    if not cursor.fetchone():
                        unprocessed_urls.append(url_data)

                        # Apply batch limit
                        if len(unprocessed_urls) >= self.batch_limit:
                            logger.info(f"⚠️ Reached batch limit of {self.batch_limit} items")
                            break

        except Exception as e:
            logger.error(f"❌ Error querying database: {e}")
            return []

        logger.info(f"✅ Discovered {len(unprocessed_urls)} unprocessed CSV URLs")
        return unprocessed_urls

    def discover_podcast_work(self) -> List[Dict[str, Any]]:
        """
        Find podcast episodes with processed=0 in podcast_episodes table.

        Returns:
            List of unprocessed podcast episodes
        """
        logger.info("🎙️ Discovering unprocessed podcast work...")

        unprocessed_episodes = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Find podcast content that needs transcript processing
                # Look for podcast items without transcript content
                cursor = conn.execute("""
                    SELECT url, title, content_type, metadata
                    FROM content
                    WHERE content_type = 'podcast'
                    AND (content IS NULL OR content = '')
                    LIMIT ?
                """, (self.batch_limit,))

                for row in cursor.fetchall():
                    url, title, content_type, metadata = row
                    unprocessed_episodes.append({
                        'url': url,
                        'title': title or "Untitled Podcast Episode",
                        'source': 'podcast_processing_discovery',
                        'content_type': content_type,
                        'metadata': metadata
                    })

        except Exception as e:
            logger.error(f"❌ Error querying podcast episodes: {e}")
            return []

        logger.info(f"✅ Discovered {len(unprocessed_episodes)} unprocessed podcast episodes")
        return unprocessed_episodes

    def create_stage_entries(self, work_items: List[Dict[str, Any]]) -> int:
        """
        Insert discovered URLs as stage 0 (SYSTEM_INIT) in content table.

        Args:
            work_items: List of work items to create stage entries for

        Returns:
            Number of entries successfully created
        """
        if not work_items:
            return 0

        logger.info(f"📝 Creating stage 0 entries for {len(work_items)} items...")

        created_count = 0
        current_time = datetime.now().isoformat()

        try:
            with sqlite3.connect(self.db_path) as conn:
                for item in work_items:
                    try:
                        # Create content entry at stage 0
                        conn.execute("""
                            INSERT OR IGNORE INTO content
                            (url, title, content_type, metadata, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            item['url'],
                            item['title'],
                            'source_discovery',
                            str({
                                'source': item['source'],
                                'discovery_stage': NumericStage.SYSTEM_INIT.value,
                                'discovered_at': current_time,
                                **{k: v for k, v in item.items() if k not in ['url', 'title']}
                            }),
                            current_time,
                            current_time
                        ))

                        # Check if the insert was successful (not ignored due to duplicate)
                        if conn.total_changes > created_count:
                            created_count += 1

                    except Exception as e:
                        logger.warning(f"⚠️ Failed to create entry for {item['url']}: {e}")
                        continue

                conn.commit()

        except Exception as e:
            logger.error(f"❌ Error creating stage entries: {e}")
            return 0

        logger.info(f"✅ Created {created_count} new stage 0 entries")
        return created_count

    def discover_unprocessed_work(self) -> Dict[str, Any]:
        """
        Main orchestrator that calls all discovery functions and returns summary.

        Returns:
            Summary of discovery results
        """
        logger.info("🚀 Starting source inventory discovery...")
        start_time = time.time()

        results = {
            'csv_urls_added': 0,
            'podcast_episodes_added': 0,
            'total_work_created': 0,
            'discovery_time': 0,
            'sources_scanned': []
        }

        try:
            # Discover CSV work
            csv_work = self.discover_csv_work()
            if csv_work:
                csv_added = self.create_stage_entries(csv_work)
                results['csv_urls_added'] = csv_added
                results['sources_scanned'].append('instapaper_csv')

            # Discover podcast work
            podcast_work = self.discover_podcast_work()
            if podcast_work:
                podcast_added = self.create_stage_entries(podcast_work)
                results['podcast_episodes_added'] = podcast_added
                results['sources_scanned'].append('podcast_episodes')

            # Calculate totals
            results['total_work_created'] = results['csv_urls_added'] + results['podcast_episodes_added']
            results['discovery_time'] = round(time.time() - start_time, 2)

            logger.info(f"✅ Source discovery completed in {results['discovery_time']}s")
            logger.info(f"📊 Results: {results['total_work_created']} total items queued")
            logger.info(f"   📄 CSV URLs: {results['csv_urls_added']}")
            logger.info(f"   🎙️ Podcast episodes: {results['podcast_episodes_added']}")

        except Exception as e:
            logger.error(f"❌ Source discovery failed: {e}")
            results['error'] = str(e)

        return results


def discover_unprocessed_work(db_path: str = "data/atlas.db") -> Dict[str, Any]:
    """
    Convenience function for scheduler integration.

    Args:
        db_path: Path to Atlas database

    Returns:
        Discovery results summary
    """
    discovery = SourceInventoryDiscovery(db_path)
    return discovery.discover_unprocessed_work()


if __name__ == "__main__":
    """Test the source discovery system manually."""

    print("🔍 Atlas Source Inventory Discovery Test")
    print("=" * 50)

    # Run discovery
    results = discover_unprocessed_work()

    # Print results
    print(f"✅ Discovery completed!")
    print(f"📊 Total work created: {results.get('total_work_created', 0)}")
    print(f"📄 CSV URLs added: {results.get('csv_urls_added', 0)}")
    print(f"🎙️ Podcast episodes added: {results.get('podcast_episodes_added', 0)}")
    print(f"⏱️ Discovery time: {results.get('discovery_time', 0)}s")
    print(f"📁 Sources scanned: {', '.join(results.get('sources_scanned', []))}")

    if 'error' in results:
        print(f"❌ Error: {results['error']}")