#!/usr/bin/env python3
"""
Atlas Universal Bookmarker
Accepts ANY data source and bookmarks it into unified system
"""

import sqlite3
import hashlib
import json
import os
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AtlasUniversalBookmarker:
    """Universal bookmarking system for all data types"""

    def __init__(self, db_path: str = "podcast_processing.db"):
        self.db_path = db_path
        self.setup_database()

    def setup_database(self):
        """Create universal bookmarking schema"""
        conn = sqlite3.connect(self.db_path)

        # Create main bookmarks table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS atlas_bookmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT,
                title TEXT,
                content_type TEXT,
                source TEXT,
                source_path TEXT,        -- Original file path if applicable
                content_hash TEXT UNIQUE,
                content_file_path TEXT,   -- Local file for stored content
                content_preview TEXT,     -- First 500 chars for search
                metadata TEXT,            -- JSON metadata
                file_size INTEGER,        -- File size in bytes
                word_count INTEGER,       -- Word count estimate
                tags TEXT,                -- Comma-separated tags
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP,
                processing_status TEXT DEFAULT 'pending',  -- pending, processing, completed, failed
                quality_score INTEGER DEFAULT 5
            )
        """)

        # Create indexes for performance
        conn.execute("CREATE INDEX IF NOT EXISTS idx_content_hash ON atlas_bookmarks(content_hash)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_content_type ON atlas_bookmarks(content_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_source ON atlas_bookmarks(source)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_processing_status ON atlas_bookmarks(processing_status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_added_date ON atlas_bookmarks(added_date)")

        # Create source tracking table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bookmark_sources (
                id INTEGER PRIMARY KEY,
                source_name TEXT UNIQUE,
                source_type TEXT,  -- file_import, url_import, api_import, manual_add
                import_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                items_imported INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active'
            )
        """)

        conn.commit()
        conn.close()
        logger.info("✅ Atlas Universal Bookmarker initialized")

    def get_content_hash(self, content: str) -> str:
        """Generate SHA-256 hash for content deduplication"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def get_file_hash(self, file_path: str) -> str:
        """Generate SHA-256 hash for file deduplication"""
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.error(f"Error hashing file {file_path}: {e}")
            return ""

    def bookmark_file(self, file_path: str, tags: str = "", source: str = "file_import") -> Optional[int]:
        """Bookmark a local file"""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                logger.error(f"File not found: {file_path}")
                return None

            # Check if already bookmarked
            file_hash = self.get_file_hash(str(file_path))
            if self.is_duplicate_hash(file_hash):
                logger.info(f"File already bookmarked (duplicate): {file_path}")
                return None

            # Read file content
            content = ""
            try:
                if file_path.suffix.lower() in ['.md', '.txt']:
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                else:
                    # For other files, read as binary and note the type
                    content = f"[Binary file: {file_path.suffix}] Size: {file_path.stat().st_size} bytes"
            except Exception as e:
                logger.error(f"Error reading file {file_path}: {e}")
                return None

            # Extract title from filename or content
            title = file_path.stem.replace('_', ' ').replace('-', ' ')
            if len(content) > 100:
                # Try to extract title from first line of content
                first_line = content.split('\n')[0].strip()
                if len(first_line) > 10 and len(first_line) < 200:
                    title = first_line.replace('#', '').strip()

            # Determine content type
            content_type = "unknown"
            if file_path.suffix.lower() in ['.md', '.txt']:
                content_type = "text"
            elif file_path.suffix.lower() in ['.html', '.htm']:
                content_type = "html"
            elif file_path.suffix.lower() in ['.pdf']:
                content_type = "pdf"
            elif 'transcript' in str(file_path).lower():
                content_type = "transcript"
            elif 'podcast' in str(file_path).lower():
                content_type = "podcast"

            # Prepare metadata
            metadata = {
                "original_path": str(file_path),
                "file_extension": file_path.suffix,
                "file_size": file_path.stat().st_size,
                "modified_date": file_path.stat().st_mtime,
                "import_method": "file_import"
            }

            # Store bookmark
            bookmark_id = self.store_bookmark(
                url=str(file_path),
                title=title,
                content_type=content_type,
                source=source,
                source_path=str(file_path),
                content=content,
                metadata=metadata,
                tags=tags
            )

            if bookmark_id:
                logger.info(f"✅ Bookmarked file: {file_path}")
                return bookmark_id
            return None

        except Exception as e:
            logger.error(f"Error bookmarking file {file_path}: {e}")
            return None

    def bookmark_url(self, url: str, title: str = "", tags: str = "", source: str = "url_import") -> Optional[int]:
        """Bookmark a URL"""
        try:
            # Check if already bookmarked
            if self.is_duplicate_url(url):
                logger.info(f"URL already bookmarked: {url}")
                return None

            # Fetch content (with timeout and error handling)
            content = ""
            content_hash = ""

            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                }
                response = requests.get(url, headers=headers, timeout=15)
                response.raise_for_status()
                content = response.text
                content_hash = self.get_content_hash(content)

                # Check for content duplicates
                if self.is_duplicate_hash(content_hash):
                    logger.info(f"URL content already bookmarked: {url}")
                    return None

            except Exception as e:
                logger.warning(f"Could not fetch URL content {url}: {e}")
                # Still bookmark the URL even if content fetch fails
                content_hash = self.get_content_hash(url)

            # Extract title if not provided
            if not title and content:
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(content, 'html.parser')
                    if soup.title:
                        title = soup.title.string
                    elif content:
                        # Fallback to first line
                        title = content.split('\n')[0][:100]
                except:
                    title = url

            # Prepare metadata
            metadata = {
                "original_url": url,
                "fetch_successful": bool(content),
                "content_length": len(content) if content else 0,
                "import_method": "url_import"
            }

            # Determine content type
            content_type = "web_page"
            if 'transcript' in url.lower() or 'transcript' in title.lower():
                content_type = "transcript"
            elif 'podcast' in url.lower() or 'podcast' in title.lower():
                content_type = "podcast"
            elif 'article' in url.lower():
                content_type = "article"

            # Store bookmark
            bookmark_id = self.store_bookmark(
                url=url,
                title=title or url,
                content_type=content_type,
                source=source,
                content=content,
                metadata=metadata,
                tags=tags,
                content_hash=content_hash
            )

            if bookmark_id:
                logger.info(f"✅ Bookmarked URL: {url}")
                return bookmark_id
            return None

        except Exception as e:
            logger.error(f"Error bookmarking URL {url}: {e}")
            return None

    def bookmark_text(self, text: str, title: str = "", url: str = "", tags: str = "", source: str = "manual_add") -> Optional[int]:
        """Bookmark text content directly"""
        try:
            if not text.strip():
                logger.warning("Empty text provided for bookmarking")
                return None

            content_hash = self.get_content_hash(text)

            # Check for duplicates
            if self.is_duplicate_hash(content_hash):
                logger.info("Text content already bookmarked")
                return None

            # Prepare metadata
            metadata = {
                "import_method": "manual_add",
                "content_length": len(text),
                "word_count": len(text.split())
            }

            # Store bookmark
            bookmark_id = self.store_bookmark(
                url=url,
                title=title or f"Text Content ({datetime.now().strftime('%Y-%m-%d')})",
                content_type="text",
                source=source,
                content=text,
                metadata=metadata,
                tags=tags,
                content_hash=content_hash
            )

            if bookmark_id:
                logger.info(f"✅ Bookmarked text: {title[:50]}...")
                return bookmark_id
            return None

        except Exception as e:
            logger.error(f"Error bookmarking text: {e}")
            return None

    def store_bookmark(self, url: str, title: str, content_type: str, source: str,
                      content: str, metadata: Dict, tags: str = "", source_path: str = "",
                      content_hash: str = "") -> Optional[int]:
        """Store bookmark in database"""
        try:
            conn = sqlite3.connect(self.db_path)

            # Generate content hash if not provided
            if not content_hash:
                content_hash = self.get_content_hash(content)

            # Create content preview (first 500 characters)
            content_preview = content[:500].replace('\n', ' ').strip()

            # Estimate word count
            word_count = len(content.split()) if content else 0

            # Insert bookmark
            cursor = conn.execute("""
                INSERT OR IGNORE INTO atlas_bookmarks
                (url, title, content_type, source, source_path, content_hash,
                 content_preview, metadata, file_size, word_count, tags, processing_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'completed')
            """, (
                url, title, content_type, source, source_path, content_hash,
                content_preview, json.dumps(metadata), len(content), word_count, tags
            ))

            bookmark_id = cursor.lastrowid

            # Update source tracking
            self.update_source_tracking(source, 1)

            conn.commit()
            conn.close()

            return bookmark_id if bookmark_id else None

        except Exception as e:
            logger.error(f"Error storing bookmark: {e}")
            return None

    def is_duplicate_hash(self, content_hash: str) -> bool:
        """Check if content hash already exists"""
        if not content_hash:
            return False

        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT id FROM atlas_bookmarks WHERE content_hash = ?", (content_hash,))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists

    def is_duplicate_url(self, url: str) -> bool:
        """Check if URL already exists"""
        if not url:
            return False

        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT id FROM atlas_bookmarks WHERE url = ?", (url,))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists

    def update_source_tracking(self, source_name: str, items_count: int):
        """Update source tracking information"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT OR REPLACE INTO bookmark_sources (source_name, items_imported, import_date)
            VALUES (?, COALESCE((SELECT items_imported FROM bookmark_sources WHERE source_name = ?), 0) + ?, CURRENT_TIMESTAMP)
        """, (source_name, source_name, items_count))
        conn.commit()
        conn.close()

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive bookmarking statistics"""
        conn = sqlite3.connect(self.db_path)

        # Total bookmarks
        cursor = conn.execute("SELECT COUNT(*) FROM atlas_bookmarks")
        total_bookmarks = cursor.fetchone()[0]

        # By content type
        cursor = conn.execute("""
            SELECT content_type, COUNT(*)
            FROM atlas_bookmarks
            GROUP BY content_type
        """)
        by_type = dict(cursor.fetchall())

        # By source
        cursor = conn.execute("""
            SELECT source, COUNT(*)
            FROM atlas_bookmarks
            GROUP BY source
            ORDER BY COUNT(*) DESC
        """)
        by_source = dict(cursor.fetchall())

        # Recent imports
        cursor = conn.execute("""
            SELECT DATE(added_date) as date, COUNT(*)
            FROM atlas_bookmarks
            WHERE added_date >= date('now', '-7 days')
            GROUP BY DATE(added_date)
            ORDER BY date DESC
        """)
        recent_imports = dict(cursor.fetchall())

        conn.close()

        return {
            "total_bookmarks": total_bookmarks,
            "by_content_type": by_type,
            "by_source": by_source,
            "recent_imports": recent_imports
        }

    def search_bookmarks(self, query: str, limit: int = 50) -> List[Dict]:
        """Search bookmarks by title, content preview, or tags"""
        conn = sqlite3.connect(self.db_path)

        cursor = conn.execute("""
            SELECT id, url, title, content_type, source, content_preview, tags, added_date, file_size, word_count
            FROM atlas_bookmarks
            WHERE title LIKE ? OR content_preview LIKE ? OR tags LIKE ?
            ORDER BY added_date DESC
            LIMIT ?
        """, (f"%{query}%", f"%{query}%", f"%{query}%", limit))

        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row[0],
                "url": row[1],
                "title": row[2],
                "content_type": row[3],
                "source": row[4],
                "content_preview": row[5],
                "tags": row[6],
                "added_date": row[7],
                "file_size": row[8],
                "word_count": row[9]
            })

        conn.close()
        return results

    def import_directory(self, directory_path: str, pattern: str = "*") -> int:
        """Import all files from a directory"""
        directory = Path(directory_path)
        if not directory.exists():
            logger.error(f"Directory not found: {directory_path}")
            return 0

        imported_count = 0
        source_name = f"directory_import_{directory.name}"

        for file_path in directory.glob(pattern):
            if file_path.is_file():
                if self.bookmark_file(file_path, tags=f"directory:{directory.name}", source=source_name):
                    imported_count += 1

        logger.info(f"📁 Imported {imported_count} files from {directory_path}")
        return imported_count

if __name__ == "__main__":
    bookmarker = AtlasUniversalBookmarker()

    print("🚀 Atlas Universal Bookmarker Ready!")
    print("=" * 50)
    print("📚 Supports: Files, URLs, Text, Direct Input")
    print("🔗 Deduplication: SHA-256 content hashing")
    print("🏷️  Tagging: Full search and organization")
    print("📊 Ready for your data sources!")

    stats = bookmarker.get_stats()
    print(f"\n📊 Current Status: {stats['total_bookmarks']} bookmarks")