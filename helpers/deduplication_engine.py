#!/usr/bin/env python3
"""
Atlas Content Deduplication Engine
Identifies and manages duplicate content across the database
"""

import sqlite3
import hashlib
import logging
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict
import re
from urllib.parse import urlparse
from difflib import SequenceMatcher

class DeduplicationEngine:
    def __init__(self, db_path: str = "atlas.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)

    def analyze_duplicates(self) -> Dict[str, any]:
        """Comprehensive duplicate analysis"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        analysis = {
            'title_duplicates': self._find_title_duplicates(cursor),
            'content_hash_duplicates': self._find_content_duplicates(cursor),
            'url_duplicates': self._find_url_duplicates(cursor),
            'garbage_content': self._find_garbage_content(cursor),
            'summary': {}
        }

        # Calculate summary stats
        total_duplicates = sum([
            len(analysis['title_duplicates']),
            len(analysis['content_hash_duplicates']),
            len(analysis['url_duplicates']),
            len(analysis['garbage_content'])
        ])

        analysis['summary'] = {
            'total_duplicate_groups': total_duplicates,
            'estimated_removable_items': sum([
                sum([count-1 for count in analysis['title_duplicates'].values()]),
                sum([count-1 for count in analysis['content_hash_duplicates'].values()]),
                len(analysis['garbage_content'])
            ])
        }

        conn.close()
        return analysis

    def _find_title_duplicates(self, cursor) -> Dict[str, int]:
        """Find exact duplicate titles"""
        cursor.execute("""
            SELECT LOWER(TRIM(title)) as clean_title, COUNT(*) as count,
                   GROUP_CONCAT(id) as ids
            FROM content
            WHERE title IS NOT NULL
              AND title != ''
              AND title NOT IN ('...', 'nytimes.com', 'wsj.com', 'Attention Required!')
            GROUP BY clean_title
            HAVING COUNT(*) > 1
            ORDER BY count DESC
        """)

        results = {}
        for clean_title, count, ids in cursor.fetchall():
            # Skip obvious garbage titles
            if len(clean_title) < 10 or clean_title in ['untitled', 'no title']:
                continue
            results[clean_title] = count

        return results

    def _find_content_duplicates(self, cursor) -> Dict[str, int]:
        """Find content duplicates using hash comparison"""
        cursor.execute("""
            SELECT id, content FROM content
            WHERE content IS NOT NULL AND LENGTH(content) > 100
        """)

        content_hashes = defaultdict(list)
        for content_id, content in cursor.fetchall():
            # Create hash of first 1000 chars to find duplicates
            content_sample = content[:1000].strip().lower()
            content_hash = hashlib.md5(content_sample.encode()).hexdigest()
            content_hashes[content_hash].append(content_id)

        # Return only hashes with duplicates
        return {h: len(ids) for h, ids in content_hashes.items() if len(ids) > 1}

    def _find_url_duplicates(self, cursor) -> Dict[str, int]:
        """Find duplicate URLs"""
        cursor.execute("""
            SELECT url, COUNT(*) as count
            FROM content
            WHERE url IS NOT NULL AND url != ''
            GROUP BY url
            HAVING COUNT(*) > 1
            ORDER BY count DESC
        """)

        return {url: count for url, count in cursor.fetchall()}

    def _find_garbage_content(self, cursor) -> List[int]:
        """Find obviously garbage content to remove"""
        garbage_conditions = [
            "title IN ('...', 'nytimes.com', 'wsj.com', 'Attention Required!', 'Access Denied')",
            "LENGTH(content) < 50",
            "content LIKE '%cloudflare%ray id%'",
            "content LIKE '%access denied%'",
            "content LIKE '%403 forbidden%'",
            "title LIKE '%.com%' AND LENGTH(title) < 20",
        ]

        garbage_ids = []
        for condition in garbage_conditions:
            cursor.execute(f"SELECT id FROM content WHERE {condition}")
            garbage_ids.extend([row[0] for row in cursor.fetchall()])

        return list(set(garbage_ids))  # Remove duplicates

    def remove_garbage_content(self) -> int:
        """Remove obviously garbage content"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        garbage_ids = self._find_garbage_content(cursor)

        if garbage_ids:
            placeholders = ','.join(['?' for _ in garbage_ids])
            cursor.execute(f"DELETE FROM content WHERE id IN ({placeholders})", garbage_ids)
            removed_count = cursor.rowcount
            conn.commit()
            self.logger.info(f"Removed {removed_count} garbage content items")
        else:
            removed_count = 0

        conn.close()
        return removed_count

    def deduplicate_by_title(self, keep_newest: bool = True) -> int:
        """Remove duplicate titles, keeping newest or oldest"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Find duplicates and keep only one per title
        order_clause = "DESC" if keep_newest else "ASC"
        cursor.execute(f"""
            WITH RankedContent AS (
                SELECT id, title,
                       ROW_NUMBER() OVER (
                           PARTITION BY LOWER(TRIM(title))
                           ORDER BY created_at {order_clause}
                       ) as rn
                FROM content
                WHERE title IS NOT NULL
                  AND title != ''
                  AND title NOT IN ('...', 'nytimes.com', 'wsj.com', 'Attention Required!')
            )
            DELETE FROM content
            WHERE id IN (
                SELECT id FROM RankedContent WHERE rn > 1
            )
        """)

        removed_count = cursor.rowcount
        conn.commit()
        conn.close()

        self.logger.info(f"Removed {removed_count} duplicate titles")
        return removed_count

    def deduplicate_by_content_similarity(self, similarity_threshold: float = 0.9) -> int:
        """Remove content with high similarity"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get all content for comparison
        cursor.execute("""
            SELECT id, content FROM content
            WHERE content IS NOT NULL AND LENGTH(content) > 100
            ORDER BY created_at DESC
        """)

        content_items = cursor.fetchall()
        to_remove = set()

        # Compare content pairwise (expensive but thorough)
        for i, (id1, content1) in enumerate(content_items):
            if id1 in to_remove:
                continue

            content1_sample = content1[:500].strip().lower()

            for j, (id2, content2) in enumerate(content_items[i+1:], i+1):
                if id2 in to_remove:
                    continue

                content2_sample = content2[:500].strip().lower()

                similarity = SequenceMatcher(None, content1_sample, content2_sample).ratio()
                if similarity >= similarity_threshold:
                    to_remove.add(id2)  # Remove the later one

        # Remove similar content
        if to_remove:
            placeholders = ','.join(['?' for _ in to_remove])
            cursor.execute(f"DELETE FROM content WHERE id IN ({placeholders})", list(to_remove))
            removed_count = cursor.rowcount
            conn.commit()
        else:
            removed_count = 0

        conn.close()
        self.logger.info(f"Removed {removed_count} similar content items")
        return removed_count

    def full_deduplication(self, similarity_threshold: float = 0.85) -> Dict[str, int]:
        """Run complete deduplication process"""
        results = {}

        print("🧹 Starting comprehensive deduplication...")

        # Step 1: Remove obvious garbage
        print("1️⃣ Removing garbage content...")
        results['garbage_removed'] = self.remove_garbage_content()

        # Step 2: Remove duplicate titles
        print("2️⃣ Removing duplicate titles...")
        results['title_duplicates_removed'] = self.deduplicate_by_title(keep_newest=True)

        # Step 3: Remove similar content (be conservative)
        print("3️⃣ Removing similar content...")
        results['similar_content_removed'] = self.deduplicate_by_content_similarity(similarity_threshold)

        # Final stats
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM content")
        results['final_content_count'] = cursor.fetchone()[0]
        conn.close()

        total_removed = sum([results[k] for k in results if k.endswith('_removed')])
        print(f"\n✅ Deduplication complete!")
        print(f"📊 Total items removed: {total_removed}")
        print(f"📊 Final content count: {results['final_content_count']}")

        return results

def main():
    """CLI interface for deduplication"""
    import argparse

    parser = argparse.ArgumentParser(description="Atlas Content Deduplication")
    parser.add_argument("--analyze", action="store_true", help="Analyze duplicates without removing")
    parser.add_argument("--remove-garbage", action="store_true", help="Remove garbage content only")
    parser.add_argument("--full", action="store_true", help="Full deduplication process")
    parser.add_argument("--similarity", type=float, default=0.85, help="Similarity threshold (0.0-1.0)")

    args = parser.parse_args()

    deduper = DeduplicationEngine()

    if args.analyze:
        analysis = deduper.analyze_duplicates()
        print("=== DUPLICATE CONTENT ANALYSIS ===")
        print(f"Title duplicates: {len(analysis['title_duplicates'])} groups")
        print(f"Content hash duplicates: {len(analysis['content_hash_duplicates'])} groups")
        print(f"URL duplicates: {len(analysis['url_duplicates'])} groups")
        print(f"Garbage items: {len(analysis['garbage_content'])}")
        print(f"Estimated removable: {analysis['summary']['estimated_removable_items']}")

    elif args.remove_garbage:
        removed = deduper.remove_garbage_content()
        print(f"Removed {removed} garbage items")

    elif args.full:
        results = deduper.full_deduplication(args.similarity)

    else:
        print("Use --analyze, --remove-garbage, or --full")

if __name__ == "__main__":
    main()