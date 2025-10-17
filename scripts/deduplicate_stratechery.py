#!/usr/bin/env python3
"""
Stratechery Content Deduplication

Remove duplicate Stratechery articles from Atlas database,
keeping only the most recent/complete version of each unique article.
"""

import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import json
from datetime import datetime

# Add Atlas to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.utils import log_info, log_error

class StratecheryDeduplicator:
    """Remove duplicate Stratechery articles from Atlas database."""

    def __init__(self, db_path: str = "data/atlas.db"):
        """Initialize deduplicator."""
        self.db_path = db_path
        self.log_path = "logs/stratechery_dedupe.log"

        # Statistics
        self.stats = {
            'total_stratechery': 0,
            'unique_articles': 0,
            'duplicates_removed': 0,
            'bytes_saved': 0
        }

    def analyze_duplicates(self) -> Dict:
        """Analyze duplicate patterns in Stratechery content."""
        log_info(self.log_path, "🔍 Analyzing Stratechery duplicates...")

        with sqlite3.connect(self.db_path) as conn:
            # Get duplicate analysis
            cursor = conn.execute('''
                SELECT
                    title,
                    url,
                    COUNT(*) as duplicate_count,
                    GROUP_CONCAT(id) as all_ids,
                    MIN(created_at) as first_seen,
                    MAX(created_at) as last_seen
                FROM content
                WHERE url LIKE '%stratechery%'
                GROUP BY title, url
                HAVING COUNT(*) > 1
                ORDER BY duplicate_count DESC
            ''')

            duplicates = cursor.fetchall()

            # Summary statistics
            total_query = conn.execute("SELECT COUNT(*) FROM content WHERE url LIKE '%stratechery%'")
            total_stratechery = total_query.fetchone()[0]

            unique_query = conn.execute('''
                SELECT COUNT(DISTINCT title), COUNT(DISTINCT url)
                FROM content WHERE url LIKE '%stratechery%'
            ''')
            unique_titles, unique_urls = unique_query.fetchone()

            self.stats.update({
                'total_stratechery': total_stratechery,
                'unique_articles': unique_urls,
                'potential_duplicates': total_stratechery - unique_urls
            })

            log_info(self.log_path, f"📊 Analysis complete:")
            log_info(self.log_path, f"   Total Stratechery items: {total_stratechery}")
            log_info(self.log_path, f"   Unique articles: {unique_urls}")
            log_info(self.log_path, f"   Potential duplicates: {total_stratechery - unique_urls}")
            log_info(self.log_path, f"   Duplicate groups: {len(duplicates)}")

            return {
                'total_stratechery': total_stratechery,
                'unique_articles': unique_urls,
                'duplicate_groups': len(duplicates),
                'duplicates': duplicates[:10]  # Top 10 for inspection
            }

    def deduplicate_by_url(self) -> Dict:
        """Remove duplicates, keeping best version of each unique URL."""
        log_info(self.log_path, "🧹 Starting Stratechery deduplication by URL...")

        removed_count = 0
        bytes_saved = 0

        with sqlite3.connect(self.db_path) as conn:
            # Get all Stratechery duplicates grouped by URL
            cursor = conn.execute('''
                SELECT url, title, COUNT(*) as count
                FROM content
                WHERE url LIKE '%stratechery%'
                GROUP BY url
                HAVING COUNT(*) > 1
                ORDER BY count DESC
            ''')

            duplicate_groups = cursor.fetchall()
            log_info(self.log_path, f"📋 Found {len(duplicate_groups)} duplicate URL groups")

            for url, title, count in duplicate_groups:
                log_info(self.log_path, f"🔧 Deduplicating: {title[:60]}... ({count} copies)")

                # Get all versions of this URL
                versions = conn.execute('''
                    SELECT id, created_at, LENGTH(COALESCE(content, '')) as content_length,
                           content_type, title
                    FROM content
                    WHERE url = ?
                    ORDER BY
                        content_length DESC,
                        created_at DESC
                ''', (url,)).fetchall()

                if len(versions) <= 1:
                    continue

                # Keep the best version (first in sorted order)
                keep_id = versions[0][0]
                remove_ids = [v[0] for v in versions[1:]]

                log_info(self.log_path, f"   ✅ Keeping: {keep_id} ({versions[0][2]} chars)")
                log_info(self.log_path, f"   🗑️  Removing: {len(remove_ids)} duplicates")

                # Calculate bytes saved
                for row_id, _, content_length, _, _ in versions[1:]:
                    bytes_saved += content_length

                # Remove duplicates
                placeholders = ','.join(['?'] * len(remove_ids))
                conn.execute(f'DELETE FROM content WHERE id IN ({placeholders})', remove_ids)

                removed_count += len(remove_ids)

        self.stats.update({
            'duplicates_removed': removed_count,
            'bytes_saved': bytes_saved
        })

        log_info(self.log_path, f"✅ Deduplication complete:")
        log_info(self.log_path, f"   Duplicates removed: {removed_count}")
        log_info(self.log_path, f"   Space saved: {bytes_saved / 1024 / 1024:.1f} MB")

        return self.stats

    def deduplicate_by_title_similarity(self, similarity_threshold: float = 0.9) -> Dict:
        """Remove near-duplicate titles (advanced deduplication)."""
        log_info(self.log_path, "🧠 Advanced deduplication by title similarity...")

        with sqlite3.connect(self.db_path) as conn:
            # Get all unique Stratechery titles
            cursor = conn.execute('''
                SELECT DISTINCT title, url, id, LENGTH(COALESCE(content, '')) as content_length
                FROM content
                WHERE url LIKE '%stratechery%'
                ORDER BY content_length DESC
            ''')

            articles = cursor.fetchall()

            # Simple similarity check for now (could use more advanced matching)
            titles_seen = set()
            duplicates_found = []

            for title, url, uid, content_length in articles:
                # Normalize title for comparison
                normalized = title.lower().strip()

                # Check for very similar titles
                similar_found = False
                for seen_title in titles_seen:
                    if self._titles_similar(normalized, seen_title, similarity_threshold):
                        duplicates_found.append((title, url, uid))
                        similar_found = True
                        break

                if not similar_found:
                    titles_seen.add(normalized)

            # Remove similar duplicates (keeping longer content)
            if duplicates_found:
                log_info(self.log_path, f"🎯 Found {len(duplicates_found)} similar title duplicates")

                for title, url, row_id in duplicates_found:
                    log_info(self.log_path, f"   🗑️  Removing similar: {title[:60]}...")
                    conn.execute('DELETE FROM content WHERE id = ?', (row_id,))

                self.stats['duplicates_removed'] += len(duplicates_found)

        return self.stats

    def _titles_similar(self, title1: str, title2: str, threshold: float) -> bool:
        """Check if two titles are similar enough to be considered duplicates."""
        # Simple Jaccard similarity on words
        words1 = set(title1.split())
        words2 = set(title2.split())

        if not words1 or not words2:
            return False

        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))

        similarity = intersection / union if union > 0 else 0
        return similarity >= threshold

    def verify_deduplication(self) -> Dict:
        """Verify deduplication results."""
        log_info(self.log_path, "✅ Verifying deduplication results...")

        with sqlite3.connect(self.db_path) as conn:
            # Get final counts
            final_count = conn.execute("SELECT COUNT(*) FROM content WHERE url LIKE '%stratechery%'").fetchone()[0]
            unique_urls = conn.execute("SELECT COUNT(DISTINCT url) FROM content WHERE url LIKE '%stratechery%'").fetchone()[0]
            unique_titles = conn.execute("SELECT COUNT(DISTINCT title) FROM content WHERE url LIKE '%stratechery%'").fetchone()[0]

            # Check for remaining duplicates
            remaining_dupes = conn.execute('''
                SELECT COUNT(*) FROM (
                    SELECT url FROM content WHERE url LIKE '%stratechery%'
                    GROUP BY url HAVING COUNT(*) > 1
                )
            ''').fetchone()[0]

            results = {
                'final_count': final_count,
                'unique_urls': unique_urls,
                'unique_titles': unique_titles,
                'remaining_duplicates': remaining_dupes,
                'deduplication_success': remaining_dupes == 0
            }

            log_info(self.log_path, f"📊 Final verification:")
            log_info(self.log_path, f"   Final Stratechery count: {final_count}")
            log_info(self.log_path, f"   Unique URLs: {unique_urls}")
            log_info(self.log_path, f"   Unique titles: {unique_titles}")
            log_info(self.log_path, f"   Remaining duplicates: {remaining_dupes}")
            log_info(self.log_path, f"   Success: {'✅' if remaining_dupes == 0 else '❌'}")

            return results

    def run_full_deduplication(self) -> Dict:
        """Run complete deduplication process."""
        log_info(self.log_path, "🚀 Starting full Stratechery deduplication...")

        try:
            # Phase 1: Analysis
            analysis = self.analyze_duplicates()

            # Phase 2: URL-based deduplication
            url_results = self.deduplicate_by_url()

            # Phase 3: Title similarity deduplication
            # similarity_results = self.deduplicate_by_title_similarity()

            # Phase 4: Verification
            verification = self.verify_deduplication()

            final_results = {
                'success': True,
                'analysis': analysis,
                'deduplication': url_results,
                'verification': verification,
                'summary': {
                    'initial_count': analysis['total_stratechery'],
                    'final_count': verification['final_count'],
                    'removed': analysis['total_stratechery'] - verification['final_count'],
                    'space_saved_mb': url_results['bytes_saved'] / 1024 / 1024
                }
            }

            log_info(self.log_path, f"🎉 Deduplication complete!")
            log_info(self.log_path, f"   {final_results['summary']['initial_count']} → {final_results['summary']['final_count']} articles")
            log_info(self.log_path, f"   Removed: {final_results['summary']['removed']} duplicates")
            log_info(self.log_path, f"   Space saved: {final_results['summary']['space_saved_mb']:.1f} MB")

            return final_results

        except Exception as e:
            log_error(self.log_path, f"💥 Deduplication error: {str(e)}")
            return {'success': False, 'error': str(e)}


def main():
    """Main execution function."""
    import argparse

    parser = argparse.ArgumentParser(description='Deduplicate Stratechery content')
    parser.add_argument('--analyze-only', action='store_true', help='Only analyze, don\'t remove')
    parser.add_argument('--db-path', default='data/atlas.db', help='Database path')

    args = parser.parse_args()

    try:
        deduplicator = StratecheryDeduplicator(args.db_path)

        if args.analyze_only:
            results = deduplicator.analyze_duplicates()
            print(f"\n📊 Stratechery Duplicate Analysis:")
            print(f"   Total items: {results['total_stratechery']}")
            print(f"   Unique articles: {results['unique_articles']}")
            print(f"   Potential duplicates: {results['total_stratechery'] - results['unique_articles']}")
        else:
            results = deduplicator.run_full_deduplication()

            if results['success']:
                summary = results['summary']
                print(f"\n✅ Deduplication Success:")
                print(f"   {summary['initial_count']} → {summary['final_count']} articles")
                print(f"   Removed: {summary['removed']} duplicates")
                print(f"   Space saved: {summary['space_saved_mb']:.1f} MB")
            else:
                print(f"\n❌ Deduplication failed: {results.get('error')}")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()