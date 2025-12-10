#!/usr/bin/env python3
"""
Atlas Manager Fixed - Works with existing data without database locking
"""

import sqlite3
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

class AtlasManager:
    """Manage your existing Atlas data without database locking"""

    def __init__(self):
        self.project_root = Path("/home/ubuntu/dev/atlas")
        self.setup_lightweight_index()

    def setup_lightweight_index(self):
        """Create simple search index for existing data"""
        self.index_db = self.project_root / "atlas_search_index.db"
        conn = sqlite3.connect(str(self.index_db))

        # Simple search table - no content storage, just indexing
        conn.execute("""
            CREATE TABLE IF NOT EXISTS content_locator (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_hash TEXT UNIQUE,
                file_path TEXT,
                title TEXT,
                content_type TEXT,
                source TEXT,
                tags TEXT,
                file_size INTEGER,
                indexed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def index_existing_content(self):
        """Index your existing content without moving it"""
        print("📊 INDEXING EXISTING ATLAS CONTENT")
        print("=" * 50)

        indexed_total = 0

        # Index backup files
        backup_dir = self.project_root / "atlas_backup_20251108_190319"
        if backup_dir.exists():
            backup_files = list(backup_dir.rglob("*.md"))
            print(f"📁 Found {len(backup_files)} backup files to index")

            backup_indexed = 0
            for file_path in backup_files:
                try:
                    # Quick read to generate hash
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    if len(content) > 100:  # Only index substantial content
                        content_hash = hashlib.sha256(content.encode()).hexdigest()
                        title = file_path.stem.replace('_', ' ').replace('-', ' ')

                        conn = sqlite3.connect(str(self.index_db))
                        conn.execute("""
                            INSERT OR IGNORE INTO content_locator
                            (content_hash, file_path, title, content_type, source, file_size)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (content_hash, str(file_path), title, 'markdown', 'backup', len(content)))
                        conn.commit()
                        conn.close()
                        backup_indexed += 1

                except Exception as e:
                    print(f"⚠️  Error indexing {file_path}: {e}")

            print(f"✅ Indexed {backup_indexed} backup files")
            indexed_total += backup_indexed

        # Index current queue content
        try:
            conn = sqlite3.connect("podcast_processing.db")
            cursor = conn.execute("""
                SELECT id, source_url, title, raw_content, source_type
                FROM atlas_ingestion_queue
                WHERE raw_content IS NOT NULL AND length(raw_content) > 1000
            """)

            items = cursor.fetchall()
            queue_indexed = 0

            for item_id, source_url, title, raw_content, source_type in items:
                try:
                    content_hash = hashlib.sha256(raw_content.encode()).hexdigest()

                    conn2 = sqlite3.connect(str(self.index_db))
                    conn2.execute("""
                        INSERT OR IGNORE INTO content_locator
                        (content_hash, file_path, title, content_type, source, file_size)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (content_hash, f"queue_item_{item_id}", title, 'queue_content', 'atlas_queue', len(raw_content)))
                    conn2.commit()
                    conn2.close()
                    queue_indexed += 1

                except Exception as e:
                    print(f"⚠️  Error indexing queue item {item_id}: {e}")

            conn.close()
            print(f"✅ Indexed {queue_indexed} queue items")
            indexed_total += queue_indexed

        except Exception as e:
            print(f"⚠️  Error with queue indexing: {e}")

        return indexed_total

    def add_new_content(self, content: str, title: str, content_type: str,
                       source: str, tags: str = "") -> str:
        """Add new content and return its hash"""
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        # Store content as file (avoids database locking)
        content_dir = self.project_root / "atlas_content"
        content_dir.mkdir(exist_ok=True)

        content_file = content_dir / f"{content_hash}.txt"
        with open(content_file, 'w', encoding='utf-8') as f:
            f.write(content)

        # Store metadata
        metadata_file = content_dir / f"{content_hash}_metadata.json"
        metadata = {
            'title': title,
            'content_type': content_type,
            'source': source,
            'tags': tags,
            'added_date': datetime.now().isoformat()
        }

        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)

        # Index for search
        conn = sqlite3.connect(str(self.index_db))
        conn.execute("""
            INSERT OR REPLACE INTO content_locator
            (content_hash, file_path, title, content_type, source, file_size, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (content_hash, str(content_file), title, content_type, source, len(content), tags))
        conn.commit()
        conn.close()

        return content_hash

    def search(self, query: str) -> List[Dict]:
        """Search your content"""
        conn = sqlite3.connect(str(self.index_db))
        cursor = conn.execute("""
            SELECT content_hash, file_path, title, content_type, source, tags, file_size, indexed_date
            FROM content_locator
            WHERE title LIKE ? OR tags LIKE ?
            ORDER BY indexed_date DESC
            LIMIT 50
        """, (f"%{query}%", f"%{query}%"))

        results = []
        for row in cursor.fetchall():
            results.append({
                'content_hash': row[0],
                'file_path': row[1],
                'title': row[2],
                'content_type': row[3],
                'source': row[4],
                'tags': row[5],
                'file_size': row[6],
                'indexed_date': row[7]
            })

        conn.close()
        return results

    def get_stats(self) -> Dict:
        """Get current status"""
        conn = sqlite3.connect(str(self.index_db))

        cursor = conn.execute("SELECT COUNT(*) FROM content_locator")
        total = cursor.fetchone()[0]

        cursor = conn.execute("SELECT content_type, COUNT(*) FROM content_locator GROUP BY content_type")
        by_type = dict(cursor.fetchall())

        cursor = conn.execute("SELECT source, COUNT(*) FROM content_locator GROUP BY source")
        by_source = dict(cursor.fetchall())

        conn.close()

        content_dir = self.project_root / "atlas_content"
        content_files = len(list(content_dir.glob("*.txt"))) if content_dir.exists() else 0

        return {
            'total_indexed': total,
            'by_type': by_type,
            'by_source': by_source,
            'content_files': content_files
        }

    def show_status(self):
        """Show current status"""
        stats = self.get_stats()
        print(f"📊 ATLAS MANAGER STATUS:")
        print(f"   Total indexed: {stats['total_indexed']:,}")
        print(f"   Content files: {stats['content_files']:,}")

        if stats['by_type']:
            print(f"   By type: {stats['by_type']}")

        if stats['by_source']:
            print(f"   By source: {stats['by_source']}")

    def bookmark_url(self, url: str, title: str = "", tags: str = ""):
        """Bookmark a URL"""
        try:
            import requests
            headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            content = response.text

            return self.add_new_content(
                content,
                title or url,
                'web_content',
                'url_import',
                tags
            )
        except Exception as e:
            print(f"⚠️  Could not fetch URL {url}: {e}")
            return None

    def import_urls(self, urls: List[str]):
        """Import multiple URLs"""
        imported = 0
        for url in urls:
            if self.bookmark_url(url):
                imported += 1
        print(f"✅ Imported {imported}/{len(urls)} URLs")
        return imported

    def import_files(self, file_paths: List[str]):
        """Import multiple files"""
        imported = 0
        for file_path in file_paths:
            try:
                path = Path(file_path)
                if path.exists():
                    content = path.read_text(encoding='utf-8', errors='ignore')
                    self.add_new_content(
                        content,
                        path.stem,
                        'file_content',
                        'file_import',
                        f"filename:{path.name}"
                    )
                    imported += 1
            except Exception as e:
                print(f"⚠️  Error importing {file_path}: {e}")
        print(f"✅ Imported {imported}/{len(file_paths)} files")
        return imported

if __name__ == "__main__":
    manager = AtlasManager()

    print("🚀 ATLAS MANAGER - Your Existing Data Interface")
    print("=" * 50)
    print("📁 Works with your existing 11,000+ files")
    print("🔗 No database locking issues")
    print("🔍 Fast search indexing")
    print("📊 Real-time statistics")
    print()

    # Index existing content
    indexed = manager.index_existing_content()
    print(f"\n🎉 INDEXING COMPLETE: {indexed} items")
    print()

    # Show final status
    manager.show_status()