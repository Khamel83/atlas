#!/usr/bin/env python3
"""
Atlas File-Based System
Separates discovery from storage to avoid database locking
Uses file-based queue with SQLite for indexing only
"""

import os
import json
import hashlib
from pathlib import Path
from datetime import datetime
import time
from typing import Dict, List, Any
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

class AtlasFileBasedSystem:
    """File-first system that avoids database locking issues"""

    def __init__(self, base_dir: str = "atlas_content"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)

        # Subdirectories
        self.raw_content_dir = self.base_dir / "raw_content"
        self.processed_content_dir = self.base_dir / "processed_content"
        self.metadata_dir = self.base_dir / "metadata"
        self.urls_dir = self.base_dir / "urls"

        # Create directories
        for dir_path in [self.raw_content_dir, self.processed_content_dir,
                         self.metadata_dir, self.urls_dir]:
            dir_path.mkdir(exist_ok=True)

        # Create lightweight index database (used only for search/discovery)
        self.setup_index_db()

        # Thread lock for file operations
        self.file_lock = threading.Lock()

    def setup_index_db(self):
        """Create lightweight index database (only for discovery/search)"""
        self.index_db_path = self.base_dir / "atlas_index.db"
        conn = sqlite3.connect(str(self.index_db_path))

        # Simple index tables - only for discovery, not for storage
        conn.execute("""
            CREATE TABLE IF NOT EXISTS content_index (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_hash TEXT UNIQUE,
                file_path TEXT,
                title TEXT,
                content_type TEXT,
                source TEXT,
                tags TEXT,
                indexed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                file_size INTEGER
            )
        """)

        conn.execute("CREATE INDEX IF NOT EXISTS idx_content_hash ON content_index(content_hash)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_title ON content_index(title)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tags ON content_index(tags)")
        conn.commit()
        conn.close()

    def get_content_hash(self, content: str) -> str:
        """Generate content hash"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def is_duplicate(self, content_hash: str) -> bool:
        """Quick duplicate check"""
        conn = sqlite3.connect(str(self.index_db_path))
        cursor = conn.execute("SELECT id FROM content_index WHERE content_hash = ?", (content_hash,))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists

    def save_raw_content(self, content: str, content_hash: str, metadata: Dict) -> str:
        """Save raw content as file, return file path"""
        with self.file_lock:
            file_path = self.raw_content_dir / f"{content_hash}.txt"

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            # Save metadata separately
            metadata_path = self.metadata_dir / f"{content_hash}.json"
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)

        return str(file_path)

    def index_content(self, content_hash: str, file_path: str, title: str,
                     content_type: str, source: str, tags: str, file_size: int):
        """Index content for search/discovery"""
        try:
            conn = sqlite3.connect(str(self.index_db_path))
            conn.execute("""
                INSERT OR REPLACE INTO content_index
                (content_hash, file_path, title, content_type, source, tags, file_size)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (content_hash, file_path, title, content_type, source, tags, file_size))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"⚠️  Index error (non-critical): {e}")

    def process_url(self, url: str, title: str = "", tags: str = "") -> bool:
        """Process a URL - file first, then index"""
        try:
            # Save URL file
            url_hash = self.get_content_hash(url)
            url_file = self.urls_dir / f"{url_hash}.url"

            with self.file_lock:
                with open(url_file, 'w', encoding='utf-8') as f:
                    f.write(url)

            # Fetch content (basic fetch, no complex processing)
            import requests
            try:
                headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
                response = requests.get(url, headers=headers, timeout=15)
                response.raise_for_status()
                content = response.text

                # Check for duplicates using content hash
                content_hash = self.get_content_hash(content)
                if self.is_duplicate(content_hash):
                    print(f"⏭️  Content already exists: {url[:50]}...")
                    return True

                # Save content
                file_path = self.save_raw_content(content, content_hash, {
                    'url': url,
                    'title': title,
                    'source': 'url_import',
                    'import_date': datetime.now().isoformat(),
                    'tags': tags
                })

                # Index for search
                self.index_content(
                    content_hash, file_path, title or url,
                    'web_content', 'url_import', tags, len(content)
                )

                print(f"✅ Processed URL: {title[:50]}...")
                return True

            except Exception as e:
                # Still index the URL even if fetch failed
                self.index_content(
                    url_hash, str(url_file), title or url,
                    'url', 'url_import', tags, 0
                )
                print(f"⚠️  Indexed URL (fetch failed): {url[:50]}...")
                return True

        except Exception as e:
            print(f"❌ Failed to process URL {url}: {e}")
            return False

    def process_file(self, file_path: str, tags: str = "") -> bool:
        """Process a file - copy to Atlas, then index"""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                print(f"❌ File not found: {file_path}")
                return False

            # Read file content
            if file_path.suffix.lower() in ['.txt', '.md']:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
            else:
                # For binary files, just store metadata
                content = f"[Binary file: {file_path.suffix}] Size: {file_path.stat().st_size} bytes"

            content_hash = self.get_content_hash(content)

            # Check for duplicates
            if self.is_duplicate(content_hash):
                print(f"⏭️  File already exists: {file_path}")
                return True

            # Determine content type
            content_type = 'text'
            if file_path.suffix.lower() == '.md':
                content_type = 'markdown'
            elif 'transcript' in str(file_path).lower():
                content_type = 'transcript'
            elif 'podcast' in str(file_path).lower():
                content_type = 'podcast'

            # Extract title from filename or content
            title = file_path.stem.replace('_', ' ').replace('-', ' ')
            if len(content) > 100 and content_type == 'text':
                first_line = content.split('\n')[0].strip()
                if len(first_line) > 10 and len(first_line) < 200:
                    title = first_line.replace('#', '').strip()

            # Save content
            saved_path = self.save_raw_content(content, content_hash, {
                'original_path': str(file_path),
                'title': title,
                'content_type': content_type,
                'source': 'file_import',
                'import_date': datetime.now().isoformat(),
                'tags': tags,
                'file_size': file_path.stat().st_size
            })

            # Index for search
            self.index_content(
                content_hash, saved_path, title, content_type,
                'file_import', tags, len(content)
            )

            print(f"✅ Processed file: {title[:50]}...")
            return True

        except Exception as e:
            print(f"❌ Failed to process file {file_path}: {e}")
            return False

    def process_text(self, text: str, title: str = "", tags: str = "") -> bool:
        """Process text content directly"""
        try:
            if not text.strip():
                print(f"❌ Empty text content")
                return False

            content_hash = self.get_content_hash(text)

            # Check for duplicates
            if self.is_duplicate(content_hash):
                print(f"⏭️  Text already exists")
                return True

            content_type = 'text'
            if 'transcript' in title.lower() or 'transcript' in text.lower():
                content_type = 'transcript'

            # Generate title if not provided
            if not title:
                title = f"Text Content ({datetime.now().strftime('%Y-%m-%d')})"

            # Save content
            saved_path = self.save_raw_content(text, content_hash, {
                'title': title,
                'content_type': content_type,
                'source': 'text_import',
                'import_date': datetime.now().isoformat(),
                'tags': tags,
                'word_count': len(text.split())
            })

            # Index for search
            self.index_content(
                content_hash, saved_path, title, content_type,
                'text_import', tags, len(text)
            )

            print(f"✅ Processed text: {title[:50]}...")
            return True

        except Exception as e:
            print(f"❌ Failed to process text: {e}")
            return False

    def import_directory(self, directory_path: str, pattern: str = "*") -> int:
        """Import directory in parallel"""
        directory = Path(directory_path)
        if not directory.exists():
            print(f"❌ Directory not found: {directory_path}")
            return 0

        # Find all files matching pattern
        files = list(directory.glob(pattern))
        print(f"📂 Found {len(files)} files to import")

        # Process in parallel with limited workers to avoid overwhelming
        imported = 0
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = []

            for file_path in files:
                if file_path.is_file() and file_path.stat().st_size > 100:  # Skip very small files
                    future = executor.submit(self.process_file, str(file_path), f"directory:{directory.name}")
                    futures.append(future)

            for future in as_completed(futures):
                try:
                    if future.result():
                        imported += 1
                except Exception as e:
                    print(f"❌ Error in file import: {e}")

        print(f"✅ Imported {imported}/{len(files)} files from {directory_path}")
        return imported

    def import_backup_files(self):
        """Import all backup files"""
        backup_dir = Path("atlas_backup_20251108_190319")
        if not backup_dir.exists():
            print(f"⚠️  Backup directory not found: {backup_dir}")
            return 0

        # Import all markdown files from backup
        markdown_files = list(backup_dir.rglob("*.md"))
        print(f"📁 Found {len(markdown_files)} backup files to import")

        # Process in smaller batches
        batch_size = 100
        imported = 0

        for i in range(0, len(markdown_files), batch_size):
            batch = markdown_files[i:i+batch_size]
            print(f"📦 Processing batch {i//batch_size + 1}/{(len(markdown_files)-1)//batch_size + 1}: {len(batch)} files")

            for file_path in batch:
                try:
                    if self.process_file(str(file_path), f"backup_batch_{i//batch_size + 1}"):
                        imported += 1

                    # Small delay to be gentle
                    time.sleep(0.05)

                except Exception as e:
                    print(f"⚠️  Error processing {file_path}: {e}")

            print(f"   Batch complete. Total so far: {imported}")

            # Brief pause between batches
            if i + batch_size < len(markdown_files):
                time.sleep(1)

        print(f"🎉 Backup import complete! Imported {imported}/{len(markdown_files)} files")
        return imported

    def search(self, query: str, limit: int = 50) -> List[Dict]:
        """Search indexed content"""
        conn = sqlite3.connect(str(self.index_db_path))
        cursor = conn.execute("""
            SELECT id, content_hash, file_path, title, content_type, source, tags, indexed_date
            FROM content_index
            WHERE title LIKE ? OR tags LIKE ?
            ORDER BY indexed_date DESC
            LIMIT ?
        """, (f"%{query}%", f"%{query}%", limit))

        results = []
        for row in cursor.fetchall():
            results.append({
                'id': row[0],
                'content_hash': row[1],
                'file_path': row[2],
                'title': row[3],
                'content_type': row[4],
                'source': row[5],
                'tags': row[6],
                'indexed_date': row[7]
            })

        conn.close()
        return results

    def get_stats(self) -> Dict:
        """Get system statistics"""
        conn = sqlite3.connect(str(self.index_db_path))

        cursor = conn.execute("SELECT COUNT(*) FROM content_index")
        total = cursor.fetchone()[0]

        cursor = conn.execute("SELECT content_type, COUNT(*) FROM content_index GROUP BY content_type")
        by_type = dict(cursor.fetchall())

        cursor = conn.execute("SELECT source, COUNT(*) FROM content_index GROUP BY source")
        by_source = dict(cursor.fetchall())

        conn.close()

        return {
            'total_items': total,
            'by_type': by_type,
            'by_source': by_source,
            'raw_files': len(list(self.raw_content_dir.glob("*.txt"))),
            'metadata_files': len(list(self.metadata_dir.glob("*.json"))),
            'url_files': len(list(self.urls_dir.glob("*.url")))
        }

if __name__ == "__main__":
    atlas = AtlasFileBasedSystem()
    print("🚀 ATLAS FILE-BASED SYSTEM READY!")
    print("=" * 50)
    print("📁 Content-first architecture (no database locking)")
    print("🔗 Parallel processing capabilities")
    print("🔍 Fast search index")
    print("📊 Real-time statistics")
    print()

    stats = atlas.get_stats()
    print(f"📊 Current Status: {stats['total_items']} items indexed")
    print(f"📁 Raw files: {stats['raw_files']}")
    print(f"📄 Metadata files: {stats['metadata_files']}")
    print(f"🔗 URL files: {stats['url_files']}")

    print(f"\n🎯 Ready for your data sources!")