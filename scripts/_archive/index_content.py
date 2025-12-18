#!/usr/bin/env python3
"""
Content Indexer for Atlas
Index all content in the database to Meilisearch
"""

import sqlite3
import json
import meilisearch
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

class ContentIndexer:
    def __init__(self):
        self.db_path = "atlas.db"
        self.client = meilisearch.Client('http://localhost:7700', 'atlas_search_key')
        self.index_name = "atlas_content"

    def setup_index(self):
        """Create and configure search index"""
        try:
            # Try to get existing index
            index = self.client.get_index(self.index_name)
        except:
            # Index doesn't exist, create it
            task_info = self.client.create_index(self.index_name, {'primaryKey': 'id'})
            # Wait for index creation
            import time
            time.sleep(2)
            index = self.client.get_index(self.index_name)

        # Configure search settings
        index.update_settings({
            'searchableAttributes': ['title', 'content'],
            'displayedAttributes': ['*'],
            'filterableAttributes': ['content_type', 'created_at'],
            'sortableAttributes': ['created_at'],
        })

        return index

    def get_all_content(self):
        """Get all content from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, title, content, content_type, url, metadata, created_at
            FROM content
            ORDER BY id
        """)

        results = cursor.fetchall()
        conn.close()

        # Convert to list of dicts
        content = []
        for row in results:
            content.append({
                'id': row[0],
                'title': row[1] or '',
                'content': row[2] or '',
                'content_type': row[3] or 'unknown',
                'url': row[4] or '',
                'metadata': row[5] or '{}',
                'created_at': row[6] or ''
            })

        return content

    def index_all_content(self):
        """Index all content to Meilisearch"""
        print("Setting up search index...")
        index = self.setup_index()

        print("Loading content from database...")
        content = self.get_all_content()
        print(f"Found {len(content)} items to index")

        if not content:
            print("No content found to index!")
            return

        # Index in batches of 1000
        batch_size = 1000
        batches = [content[i:i + batch_size] for i in range(0, len(content), batch_size)]

        total_indexed = 0
        for i, batch in enumerate(batches, 1):
            print(f"Indexing batch {i}/{len(batches)} ({len(batch)} items)")

            try:
                # Add documents to index
                result = index.add_documents(batch)
                print(f"  Task ID: {result.task_uid}")
                total_indexed += len(batch)
            except Exception as e:
                print(f"  Error indexing batch {i}: {e}")

        print(f"\n🎉 Indexing complete!")
        print(f"✅ Total items indexed: {total_indexed}")
        print(f"📊 Content breakdown:")

        # Show content type breakdown
        type_counts = {}
        for item in content:
            content_type = item['content_type']
            type_counts[content_type] = type_counts.get(content_type, 0) + 1

        for content_type, count in sorted(type_counts.items()):
            print(f"   - {content_type}: {count}")

        print(f"\n🔍 Search available at: http://localhost:7700")

    def test_search(self, query="artificial intelligence"):
        """Test the search functionality"""
        try:
            index = self.client.get_index(self.index_name)
            results = index.search(query, {'limit': 5})

            print(f"\n🔍 Test search for '{query}':")
            print(f"Found {results['estimatedTotalHits']} results")

            for i, hit in enumerate(results['hits'], 1):
                title = hit.get('title', 'No title')[:100]
                content_type = hit.get('content_type', 'unknown')
                print(f"  {i}. [{content_type}] {title}")
        except Exception as e:
            print(f"Search test failed: {e}")

def main():
    """Main entry point"""
    indexer = ContentIndexer()
    indexer.index_all_content()
    indexer.test_search()

if __name__ == "__main__":
    main()