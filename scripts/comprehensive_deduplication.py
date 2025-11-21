#!/usr/bin/env python3
"""
Comprehensive Atlas Content Deduplication

Advanced deduplication across ALL Atlas content with intelligent metadata preservation:
- Detects duplicates by URL, title similarity, content hash
- Preserves best metadata from all versions
- Maintains processing history and quality scores
- Handles multi-source content intelligently
"""

import sqlite3
import sys
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple, Set
import json
from datetime import datetime
import difflib

# Add Atlas to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.utils import log_info, log_error

class ComprehensiveDeduplicator:
    """Advanced deduplication with metadata preservation."""

    def __init__(self, db_path: str = "data/atlas.db"):
        """Initialize comprehensive deduplicator."""
        self.db_path = db_path
        self.log_path = "logs/comprehensive_dedupe.log"

        # Statistics
        self.stats = {
            'total_items': 0,
            'duplicate_groups': 0,
            'items_removed': 0,
            'bytes_saved': 0,
            'metadata_merged': 0,
            'start_time': datetime.now()
        }

        # Deduplication strategies
        self.strategies = {
            'exact_url': self._find_exact_url_duplicates,
            'similar_title': self._find_similar_title_duplicates,
            'content_hash': self._find_content_hash_duplicates,
            'url_variations': self._find_url_variations
        }

    def analyze_all_duplicates(self) -> Dict:
        """Comprehensive duplicate analysis across all content."""
        log_info(self.log_path, "🔍 Analyzing duplicates across ALL Atlas content...")

        with sqlite3.connect(self.db_path) as conn:
            # Get overall statistics
            total_items = conn.execute("SELECT COUNT(*) FROM content").fetchone()[0]

            # Analyze by URL
            exact_url_dupes = conn.execute('''
                SELECT url, COUNT(*) as count FROM content
                WHERE url IS NOT NULL AND url != ''
                GROUP BY url HAVING COUNT(*) > 1
                ORDER BY count DESC
            ''').fetchall()

            # Analyze by title similarity (simplified)
            title_analysis = conn.execute('''
                SELECT title, COUNT(*) as count FROM content
                WHERE title IS NOT NULL AND title != ''
                GROUP BY title HAVING COUNT(*) > 1
                ORDER BY count DESC
                LIMIT 50
            ''').fetchall()

            # Analyze by content size patterns
            content_patterns = conn.execute('''
                SELECT
                    LENGTH(COALESCE(content, '')) as content_length,
                    COUNT(*) as count
                FROM content
                GROUP BY content_length
                HAVING count > 5 AND content_length > 0
                ORDER BY count DESC
                LIMIT 20
            ''').fetchall()

            # Source analysis
            source_analysis = conn.execute('''
                SELECT
                    CASE
                        WHEN url LIKE '%stratechery%' THEN 'stratechery'
                        WHEN url LIKE '%youtube%' THEN 'youtube'
                        WHEN url LIKE '%instapaper%' THEN 'instapaper'
                        WHEN url LIKE '%github%' THEN 'github'
                        WHEN url LIKE '%reddit%' THEN 'reddit'
                        WHEN url LIKE '%twitter%' THEN 'twitter'
                        WHEN url LIKE '%medium%' THEN 'medium'
                        ELSE 'other'
                    END as source,
                    COUNT(*) as count,
                    COUNT(DISTINCT url) as unique_urls,
                    COUNT(*) - COUNT(DISTINCT url) as potential_dupes
                FROM content
                WHERE url IS NOT NULL
                GROUP BY source
                ORDER BY potential_dupes DESC
            ''').fetchall()

            self.stats.update({
                'total_items': total_items,
                'exact_url_duplicates': len(exact_url_dupes),
                'title_duplicates': len(title_analysis)
            })

            log_info(self.log_path, f"📊 Atlas-wide Duplicate Analysis:")
            log_info(self.log_path, f"   Total content items: {total_items:,}")
            log_info(self.log_path, f"   URLs with duplicates: {len(exact_url_dupes)}")
            log_info(self.log_path, f"   Titles with duplicates: {len(title_analysis)}")

            return {
                'total_items': total_items,
                'exact_url_duplicates': exact_url_dupes[:10],  # Top 10
                'title_duplicates': title_analysis[:10],
                'content_patterns': content_patterns,
                'source_analysis': source_analysis
            }

    def _find_exact_url_duplicates(self) -> List[Tuple]:
        """Find exact URL duplicates."""
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute('''
                SELECT url, GROUP_CONCAT(id) as ids, COUNT(*) as count
                FROM content
                WHERE url IS NOT NULL AND url != ''
                GROUP BY url
                HAVING COUNT(*) > 1
                ORDER BY count DESC
            ''').fetchall()

    def _find_similar_title_duplicates(self, similarity_threshold: float = 0.85) -> List[Tuple]:
        """Find similar title duplicates using fuzzy matching."""
        similar_groups = []

        with sqlite3.connect(self.db_path) as conn:
            # Get all unique titles with their IDs
            titles_data = conn.execute('''
                SELECT id, title, url, LENGTH(COALESCE(content, '')) as content_length
                FROM content
                WHERE title IS NOT NULL AND title != '' AND LENGTH(title) > 10
                ORDER BY content_length DESC
            ''').fetchall()

            processed_ids = set()

            for i, (id1, title1, url1, len1) in enumerate(titles_data):
                if id1 in processed_ids:
                    continue

                similar_group = [(id1, title1, url1, len1)]
                processed_ids.add(id1)

                # Compare with remaining titles
                for j in range(i + 1, len(titles_data)):
                    id2, title2, url2, len2 = titles_data[j]

                    if id2 in processed_ids:
                        continue

                    # Calculate similarity
                    similarity = difflib.SequenceMatcher(None, title1.lower(), title2.lower()).ratio()

                    if similarity >= similarity_threshold:
                        similar_group.append((id2, title2, url2, len2))
                        processed_ids.add(id2)

                # Only keep groups with multiple items
                if len(similar_group) > 1:
                    similar_groups.append(similar_group)

        return similar_groups

    def _find_content_hash_duplicates(self) -> List[Tuple]:
        """Find duplicates by content hash."""
        hash_groups = {}

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT id, title, url, content
                FROM content
                WHERE content IS NOT NULL AND LENGTH(content) > 100
            ''')

            for row in cursor:
                id_val, title, url, content = row

                # Create content hash
                content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()

                if content_hash not in hash_groups:
                    hash_groups[content_hash] = []

                hash_groups[content_hash].append((id_val, title, url, len(content)))

        # Return only groups with duplicates
        return [(hash_val, items) for hash_val, items in hash_groups.items() if len(items) > 1]

    def _find_url_variations(self) -> List[Tuple]:
        """Find URL variations (with/without params, redirects, etc)."""
        from urllib.parse import urlparse, parse_qs

        url_groups = {}

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT id, title, url, LENGTH(COALESCE(content, '')) as content_length
                FROM content
                WHERE url IS NOT NULL AND url != ''
            ''')

            for row in cursor:
                id_val, title, url, content_length = row

                # Normalize URL
                parsed = urlparse(url)

                # Create base URL key (domain + path, no params)
                base_key = f"{parsed.netloc}{parsed.path}".lower()

                # Remove common variations
                base_key = base_key.rstrip('/')
                base_key = base_key.replace('www.', '')

                if base_key not in url_groups:
                    url_groups[base_key] = []

                url_groups[base_key].append((id_val, title, url, content_length))

        # Return only groups with variations
        return [(base_key, items) for base_key, items in url_groups.items() if len(items) > 1]

    def merge_metadata(self, duplicate_items: List[Tuple]) -> Dict:
        """Intelligently merge metadata from duplicate items."""
        merged = {
            'title': '',
            'url': '',
            'content': '',
            'content_type': '',
            'metadata': {},
            'created_at': '',
            'updated_at': '',
            'quality_score': 0,
            'content_length': 0,
            'source_count': 0,
            'merged_from': []
        }

        # Sort by content length (prefer longer content)
        sorted_items = sorted(duplicate_items, key=lambda x: len(x[3] or ''), reverse=True)

        for item_id, title, url, content, content_type, metadata_str, created_at, updated_at in sorted_items:
            # Use best title (longest, most descriptive)
            if not merged['title'] or len(title or '') > len(merged['title']):
                merged['title'] = title or merged['title']

            # Use shortest, cleanest URL
            if not merged['url'] or (url and len(url) < len(merged['url'])):
                merged['url'] = url or merged['url']

            # Use longest content
            if not merged['content'] or len(content or '') > len(merged['content']):
                merged['content'] = content or merged['content']
                merged['content_length'] = len(content or '')

            # Use most specific content type
            if content_type and (not merged['content_type'] or len(content_type) > len(merged['content_type'])):
                merged['content_type'] = content_type

            # Merge metadata
            if metadata_str:
                try:
                    item_metadata = json.loads(metadata_str)
                    if isinstance(item_metadata, dict):
                        # Merge with preference for more detailed values
                        for key, value in item_metadata.items():
                            if key not in merged['metadata'] or (value and len(str(value)) > len(str(merged['metadata'].get(key, '')))):
                                merged['metadata'][key] = value
                except:
                    pass

            # Use earliest creation date
            if created_at and (not merged['created_at'] or created_at < merged['created_at']):
                merged['created_at'] = created_at

            # Use latest update date
            if updated_at and (not merged['updated_at'] or updated_at > merged['updated_at']):
                merged['updated_at'] = updated_at

            # Track source
            merged['merged_from'].append({
                'id': item_id,
                'title': title[:100] if title else '',
                'url': url,
                'content_length': len(content or ''),
                'created_at': created_at
            })

        merged['source_count'] = len(merged['merged_from'])
        merged['quality_score'] = min(1.0, merged['content_length'] / 1000 + merged['source_count'] * 0.1)

        return merged

    def deduplicate_with_metadata_preservation(self, strategy: str = 'exact_url', max_groups: int = None) -> Dict:
        """Run deduplication while preserving valuable metadata."""
        log_info(self.log_path, f"🧹 Deduplicating with {strategy} strategy...")

        if strategy not in self.strategies:
            raise ValueError(f"Unknown strategy: {strategy}")

        # Find duplicates
        if strategy == 'similar_title':
            duplicate_groups = self._find_similar_title_duplicates()
        elif strategy == 'content_hash':
            duplicate_groups = self._find_content_hash_duplicates()
        elif strategy == 'url_variations':
            duplicate_groups = self._find_url_variations()
        else:  # exact_url
            duplicate_groups = self._find_exact_url_duplicates()

        if max_groups:
            duplicate_groups = duplicate_groups[:max_groups]

        log_info(self.log_path, f"📋 Found {len(duplicate_groups)} duplicate groups to process")

        processed_groups = 0
        items_removed = 0
        bytes_saved = 0

        with sqlite3.connect(self.db_path) as conn:
            for group in duplicate_groups:
                try:
                    if strategy in ['similar_title', 'content_hash', 'url_variations']:
                        if strategy == 'content_hash':
                            _, items = group
                        elif strategy in ['similar_title', 'url_variations']:
                            _, items = group
                            # Convert to expected format
                        else:
                            items = group
                    else:
                        # exact_url format: (url, ids_string, count)
                        url, ids_string, count = group
                        ids = [int(id_str) for id_str in ids_string.split(',')]

                        # Get full data for these IDs
                        placeholders = ','.join(['?'] * len(ids))
                        items_data = conn.execute(f'''
                            SELECT id, title, url, content, content_type, metadata, created_at, updated_at
                            FROM content WHERE id IN ({placeholders})
                        ''', ids).fetchall()

                        items = items_data

                    if len(items) <= 1:
                        continue

                    # Merge metadata from all duplicates
                    merged = self.merge_metadata(items)

                    # Keep the ID with the longest content
                    keep_id = max(items, key=lambda x: len(x[3] or ''))[0]
                    remove_ids = [item[0] for item in items if item[0] != keep_id]

                    # Update the kept item with merged metadata
                    conn.execute('''
                        UPDATE content SET
                            title = ?,
                            content = ?,
                            content_type = ?,
                            metadata = ?,
                            updated_at = ?
                        WHERE id = ?
                    ''', (
                        merged['title'],
                        merged['content'],
                        merged['content_type'],
                        json.dumps(merged['metadata']),
                        datetime.now().isoformat(),
                        keep_id
                    ))

                    # Calculate space saved before deletion
                    for item in items:
                        if item[0] in remove_ids:
                            bytes_saved += len(item[3] or '')

                    # Remove duplicates
                    if remove_ids:
                        placeholders = ','.join(['?'] * len(remove_ids))
                        conn.execute(f'DELETE FROM content WHERE id IN ({placeholders})', remove_ids)
                        items_removed += len(remove_ids)

                    processed_groups += 1

                    if processed_groups % 10 == 0:
                        log_info(self.log_path, f"   🔄 Processed {processed_groups} groups, removed {items_removed} items")

                except Exception as e:
                    log_error(self.log_path, f"Error processing group: {str(e)}")
                    continue

        self.stats.update({
            'duplicate_groups': processed_groups,
            'items_removed': items_removed,
            'bytes_saved': bytes_saved
        })

        log_info(self.log_path, f"✅ Deduplication complete:")
        log_info(self.log_path, f"   Groups processed: {processed_groups}")
        log_info(self.log_path, f"   Items removed: {items_removed}")
        log_info(self.log_path, f"   Space saved: {bytes_saved / 1024 / 1024:.1f} MB")

        return self.stats

    def run_comprehensive_deduplication(self) -> Dict:
        """Run all deduplication strategies in optimal order."""
        log_info(self.log_path, "🚀 Starting comprehensive Atlas deduplication...")

        try:
            # Phase 1: Analysis
            analysis = self.analyze_all_duplicates()

            # Phase 2: Exact URL duplicates (highest confidence)
            url_results = self.deduplicate_with_metadata_preservation('exact_url', max_groups=100)

            # Phase 3: URL variations (medium confidence)
            variation_results = self.deduplicate_with_metadata_preservation('url_variations', max_groups=50)

            # Phase 4: Content hash duplicates (high confidence)
            hash_results = self.deduplicate_with_metadata_preservation('content_hash', max_groups=50)

            # Phase 5: Similar titles (lower confidence, limited)
            # title_results = self.deduplicate_with_metadata_preservation('similar_title', max_groups=20)

            # Final verification
            with sqlite3.connect(self.db_path) as conn:
                final_count = conn.execute("SELECT COUNT(*) FROM content").fetchone()[0]

            total_removed = analysis['total_items'] - final_count

            results = {
                'success': True,
                'initial_count': analysis['total_items'],
                'final_count': final_count,
                'total_removed': total_removed,
                'space_saved_mb': self.stats['bytes_saved'] / 1024 / 1024,
                'analysis': analysis,
                'phases': {
                    'exact_url': url_results,
                    'url_variations': variation_results,
                    'content_hash': hash_results
                }
            }

            log_info(self.log_path, f"🎉 Comprehensive deduplication complete!")
            log_info(self.log_path, f"   {analysis['total_items']:,} → {final_count:,} items")
            log_info(self.log_path, f"   Removed: {total_removed:,} duplicates")
            log_info(self.log_path, f"   Space saved: {results['space_saved_mb']:.1f} MB")

            return results

        except Exception as e:
            log_error(self.log_path, f"💥 Comprehensive deduplication error: {str(e)}")
            return {'success': False, 'error': str(e)}


def main():
    """Main execution function."""
    import argparse

    parser = argparse.ArgumentParser(description='Comprehensive Atlas Content Deduplication')
    parser.add_argument('--analyze-only', action='store_true', help='Only analyze, don\'t remove')
    parser.add_argument('--strategy', choices=['exact_url', 'similar_title', 'content_hash', 'url_variations'],
                       default='exact_url', help='Deduplication strategy')
    parser.add_argument('--max-groups', type=int, help='Maximum groups to process')
    parser.add_argument('--db-path', default='data/atlas.db', help='Database path')

    args = parser.parse_args()

    try:
        deduplicator = ComprehensiveDeduplicator(args.db_path)

        if args.analyze_only:
            results = deduplicator.analyze_all_duplicates()

            print(f"\n📊 Atlas Comprehensive Duplicate Analysis:")
            print(f"   Total content items: {results['total_items']:,}")
            print(f"   URLs with duplicates: {len(results['exact_url_duplicates'])}")
            print(f"   Titles with duplicates: {len(results['title_duplicates'])}")

            print(f"\n🏷️  Source Analysis (Potential Duplicates):")
            for source, count, unique, dupes in results['source_analysis']:
                if dupes > 0:
                    print(f"   {source}: {dupes:,} potential duplicates ({count:,} total, {unique:,} unique)")

        else:
            if args.strategy == 'comprehensive':
                results = deduplicator.run_comprehensive_deduplication()
            else:
                results = deduplicator.deduplicate_with_metadata_preservation(
                    args.strategy,
                    max_groups=args.max_groups
                )

            if results.get('success', True):
                print(f"\n✅ Deduplication Success:")
                if 'initial_count' in results:
                    print(f"   {results['initial_count']:,} → {results['final_count']:,} items")
                    print(f"   Removed: {results['total_removed']:,} duplicates")
                    print(f"   Space saved: {results['space_saved_mb']:.1f} MB")
                else:
                    print(f"   Groups processed: {results['duplicate_groups']}")
                    print(f"   Items removed: {results['items_removed']}")
                    print(f"   Space saved: {results['bytes_saved'] / 1024 / 1024:.1f} MB")
            else:
                print(f"\n❌ Deduplication failed: {results.get('error')}")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()