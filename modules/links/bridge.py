"""
Link Bridge - Move approved links from link_queue.db to url_queue.txt for ingestion.

This module bridges the gap between link approval and the existing URL fetcher.
Supports drip mode to be polite to target sites.
"""

import sqlite3
import hashlib
import json
import re
import time
import logging
from pathlib import Path
from typing import List, Dict, Optional, Set
from datetime import datetime

from modules.links.models import ApprovalRules

logger = logging.getLogger(__name__)

# Content directories to check for existing URLs
FETCHER_STATE_FILE = Path('data/url_fetcher_state.json')
STRATECHERY_ARTICLES_DIR = Path('data/stratechery/articles')
STRATECHERY_PODCASTS_DIR = Path('data/stratechery/podcasts')

DEFAULT_LINK_DB = Path('data/enrich/link_queue.db')
DEFAULT_URL_QUEUE = Path('data/url_queue.txt')
DEFAULT_CONFIG = Path('config/link_approval_rules.yml')


class LinkBridge:
    """Bridge approved links to the URL fetcher queue."""

    def __init__(
        self,
        link_db_path: Path = DEFAULT_LINK_DB,
        url_queue_path: Path = DEFAULT_URL_QUEUE,
        config_path: Path = DEFAULT_CONFIG
    ):
        self.link_db_path = link_db_path
        self.url_queue_path = url_queue_path
        self.config_path = config_path
        self.rules = self._load_rules()

        # Ensure url_queue.txt exists
        self.url_queue_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.url_queue_path.exists():
            self.url_queue_path.touch()

    def _load_rules(self) -> ApprovalRules:
        """Load drip settings from config."""
        if not self.config_path.exists():
            return ApprovalRules()

        import yaml
        with open(self.config_path) as f:
            data = yaml.safe_load(f)

        return ApprovalRules.from_dict(data)

    def get_approved_links(self, limit: int = 100) -> List[Dict]:
        """Get approved links that haven't been ingested yet."""
        conn = sqlite3.connect(self.link_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("""
            SELECT id, url, domain, score, category, source_content_id
            FROM extracted_links
            WHERE status = 'approved'
            ORDER BY score DESC
            LIMIT ?
        """, (limit,))
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    def get_existing_urls(self) -> Set[str]:
        """
        Get URLs that already exist in queue or have been fetched.

        Checks multiple sources to prevent duplicates:
        1. Queue file (pending fetches)
        2. Fetcher state file (already fetched)
        3. Stratechery content directories (already have content)
        """
        urls: Set[str] = set()

        # 1. Queue file
        if self.url_queue_path.exists():
            with open(self.url_queue_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        urls.add(line)
            logger.debug(f"Found {len(urls)} URLs in queue file")

        # 2. Fetcher state file (already fetched URLs)
        if FETCHER_STATE_FILE.exists():
            try:
                with open(FETCHER_STATE_FILE) as f:
                    state = json.load(f)
                fetched_urls = set(state.get('fetched', {}).keys())
                failed_urls = set(state.get('failed', {}).keys())
                urls.update(fetched_urls)
                urls.update(failed_urls)
                logger.debug(f"Found {len(fetched_urls)} fetched, {len(failed_urls)} failed in state")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Could not load fetcher state: {e}")

        # 3. Stratechery content (extract URLs from filenames)
        stratechery_count = 0
        for content_dir in [STRATECHERY_ARTICLES_DIR, STRATECHERY_PODCASTS_DIR]:
            if content_dir.exists():
                for md_file in content_dir.glob('*.md'):
                    # Extract URL from file - stratechery files have URL pattern in name
                    # Files named like: 2024-01-15-article-slug.md
                    # Build stratechery URL from slug
                    stem = md_file.stem  # e.g., "2024-01-15-some-article-title"
                    if stem and len(stem) > 10:
                        # Construct possible stratechery URL
                        stratechery_url = f"https://stratechery.com/{stem}/"
                        urls.add(stratechery_url)
                        # Also add variant without trailing slash
                        urls.add(stratechery_url.rstrip('/'))
                        stratechery_count += 1
        if stratechery_count:
            logger.debug(f"Found {stratechery_count} Stratechery content files")

        logger.info(f"Total existing URLs: {len(urls)}")
        return urls

    def add_to_queue(self, url: str) -> bool:
        """Add URL to the queue file."""
        with open(self.url_queue_path, 'a') as f:
            f.write(f"{url}\n")
        return True

    def mark_ingested(self, link_id: int):
        """Mark link as ingested in database."""
        conn = sqlite3.connect(self.link_db_path)
        conn.execute("""
            UPDATE extracted_links
            SET status = 'ingested', ingested_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (link_id,))
        conn.commit()
        conn.close()

    def run(
        self,
        limit: Optional[int] = None,
        drip: bool = True,
        dry_run: bool = False
    ) -> Dict:
        """
        Bridge approved links to the URL queue.

        Args:
            limit: Max URLs to add (defaults to drip settings)
            drip: If True, use delay between URLs
            dry_run: If True, don't actually add URLs

        Returns:
            Statistics dictionary
        """
        stats = {
            'processed': 0,
            'added': 0,
            'skipped_duplicate': 0,
            'urls': [],
        }

        # Determine limit from config or parameter
        max_urls = limit or self.rules.drip_urls_per_run
        delay = self.rules.drip_delay_seconds if drip else 0

        # Get existing URLs to avoid duplicates
        existing_urls = self.get_existing_urls()
        logger.info(f"Found {len(existing_urls)} existing URLs in queue")

        # Get approved links
        approved = self.get_approved_links(limit=max_urls * 2)  # Get extra to account for dups
        logger.info(f"Found {len(approved)} approved links")

        for link in approved:
            if stats['added'] >= max_urls:
                break

            url = link['url']
            stats['processed'] += 1

            # Check for duplicate
            if url in existing_urls:
                stats['skipped_duplicate'] += 1
                # Still mark as ingested to avoid reprocessing
                if not dry_run:
                    self.mark_ingested(link['id'])
                continue

            # Add to queue
            if not dry_run:
                self.add_to_queue(url)
                self.mark_ingested(link['id'])
                existing_urls.add(url)  # Track in memory too

            stats['added'] += 1
            stats['urls'].append({
                'url': url,
                'domain': link['domain'],
                'score': link['score'],
            })

            logger.debug(f"Added: {url} (score: {link['score']:.2f})")

            # Drip delay
            if drip and delay > 0 and stats['added'] < max_urls:
                time.sleep(delay)

        return stats

    def get_stats(self) -> Dict:
        """Get bridge statistics."""
        conn = sqlite3.connect(self.link_db_path)

        stats = {}

        # Count by status
        cursor = conn.execute("""
            SELECT status, COUNT(*) FROM extracted_links GROUP BY status
        """)
        stats['by_status'] = dict(cursor.fetchall())

        # Approved waiting
        cursor = conn.execute("""
            SELECT COUNT(*) FROM extracted_links WHERE status = 'approved'
        """)
        stats['approved_waiting'] = cursor.fetchone()[0]

        # Recently ingested
        cursor = conn.execute("""
            SELECT COUNT(*) FROM extracted_links
            WHERE status = 'ingested' AND ingested_at > datetime('now', '-1 day')
        """)
        stats['ingested_24h'] = cursor.fetchone()[0]

        # Queue file size
        if self.url_queue_path.exists():
            stats['queue_file_urls'] = len(self.get_existing_urls())
        else:
            stats['queue_file_urls'] = 0

        conn.close()
        return stats


def bridge_to_queue(
    limit: Optional[int] = None,
    drip: bool = True,
    dry_run: bool = False
) -> int:
    """
    Convenience function to bridge approved links to the URL queue.

    Args:
        limit: Max URLs to add
        drip: If True, use delay between URLs
        dry_run: If True, don't actually add URLs

    Returns:
        Number of URLs added
    """
    bridge = LinkBridge()
    stats = bridge.run(limit=limit, drip=drip, dry_run=dry_run)
    return stats['added']
