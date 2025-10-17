"""
Safari Reading List Bulk Import System
Advanced Reading List integration with Safari and cross-device synchronization
"""

import json
import sqlite3
import plistlib
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import hashlib
import sys

sys.path.append(str(Path(__file__).parent.parent))
from helpers.config import load_config
from helpers.article_fetcher import ArticleFetcher


@dataclass
class ReadingListItem:
    """Safari Reading List item with enhanced metadata"""

    url: str
    title: str
    preview_text: Optional[str] = None
    date_added: Optional[datetime] = None
    date_last_viewed: Optional[datetime] = None
    read_status: bool = False
    tags: List[str] = None
    bookmark_id: Optional[str] = None
    device_origin: Optional[str] = None
    folder_path: Optional[str] = None
    site_name: Optional[str] = None
    word_count: Optional[int] = None
    estimated_reading_time: Optional[int] = None
    archive_url: Optional[str] = None


@dataclass
class ImportResult:
    """Results from Reading List import operation"""

    total_items: int
    new_items: int
    updated_items: int
    failed_items: int
    duplicate_items: int
    processing_time: float
    errors: List[str]
    imported_urls: List[str]


@dataclass
class SyncStatus:
    """Cross-device synchronization status"""

    device_id: str
    last_sync: datetime
    items_synced: int
    sync_conflicts: int
    sync_status: str  # 'success', 'partial', 'failed'


class ReadingListImporter:
    """Advanced Safari Reading List import and synchronization system"""

    def __init__(self, config=None):
        self.config = config or load_config()
        self.db_path = str(
            Path(__file__).parent.parent / "data" / "podcasts" / "atlas_podcasts.db"
        )
        self.article_fetcher = ArticleFetcher(self.config)

        # Platform-specific Reading List paths
        self.reading_list_paths = self._get_reading_list_paths()

        # Initialize database
        self._init_reading_list_database()

        # Import settings
        self.batch_size = 50
        self.import_delay = 1.0  # Seconds between requests
        self.max_retries = 3

    def _get_reading_list_paths(self) -> Dict[str, str]:
        """Get platform-specific Safari Reading List file paths"""

        home = Path.home()

        paths = {
            # macOS Safari
            "macos_safari": home / "Library/Safari/Bookmarks.plist",
            "macos_safari_cloudkit": home / "Library/Safari/CloudTabs.db",
            # iOS Safari (when accessible via iTunes backup)
            "ios_backup": home / "Library/Application Support/MobileSync/Backup",
            # Alternative locations
            "safari_bookmarks_backup": home / "Desktop/Bookmarks.plist",
            "exported_bookmarks": home / "Downloads/Bookmarks.html",
            # Manual import directory
            "manual_import": Path(__file__).parent.parent / "inputs" / "reading_list",
        }

        # Create manual import directory
        paths["manual_import"].mkdir(parents=True, exist_ok=True)

        return {k: str(v) for k, v in paths.items()}

    def _init_reading_list_database(self):
        """Initialize Reading List tracking database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Reading List items table
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS reading_list_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        url TEXT NOT NULL,
                        url_hash TEXT UNIQUE NOT NULL,
                        title TEXT NOT NULL,
                        preview_text TEXT,
                        date_added TIMESTAMP,
                        date_last_viewed TIMESTAMP,
                        read_status BOOLEAN DEFAULT FALSE,
                        tags TEXT,  -- JSON array
                        bookmark_id TEXT,
                        device_origin TEXT,
                        folder_path TEXT,
                        site_name TEXT,
                        word_count INTEGER,
                        estimated_reading_time INTEGER,
                        archive_url TEXT,
                        import_source TEXT,
                        imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        atlas_content_id TEXT,
                        processing_status TEXT DEFAULT 'pending',
                        processing_attempts INTEGER DEFAULT 0,
                        last_processing_attempt TIMESTAMP,
                        processing_error TEXT
                    )
                """
                )

                # Reading List sync status table
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS reading_list_sync (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        device_id TEXT NOT NULL,
                        sync_type TEXT NOT NULL,  -- 'import', 'export', 'bidirectional'
                        last_sync TIMESTAMP NOT NULL,
                        items_processed INTEGER DEFAULT 0,
                        items_success INTEGER DEFAULT 0,
                        items_failed INTEGER DEFAULT 0,
                        sync_conflicts INTEGER DEFAULT 0,
                        sync_status TEXT NOT NULL,
                        sync_log TEXT,  -- JSON log data
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                # Reading List folders table (for organization)
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS reading_list_folders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        folder_name TEXT NOT NULL,
                        folder_path TEXT NOT NULL,
                        parent_folder_id INTEGER,
                        item_count INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (parent_folder_id) REFERENCES reading_list_folders(id)
                    )
                """
                )

                # Reading List import history
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS reading_list_imports (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        import_source TEXT NOT NULL,
                        file_path TEXT,
                        total_items INTEGER NOT NULL,
                        new_items INTEGER NOT NULL,
                        updated_items INTEGER NOT NULL,
                        failed_items INTEGER NOT NULL,
                        duplicate_items INTEGER NOT NULL,
                        processing_time REAL NOT NULL,
                        import_status TEXT NOT NULL,
                        error_log TEXT,
                        imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                # Create indexes for performance
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_reading_list_url_hash ON reading_list_items(url_hash)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_reading_list_status ON reading_list_items(processing_status)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_reading_list_device ON reading_list_items(device_origin)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_reading_list_date_added ON reading_list_items(date_added)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_reading_list_sync_device ON reading_list_sync(device_id)"
                )

                conn.commit()
        except Exception as e:
            print(f"Error initializing reading list database: {e}")

    async def import_from_safari_bookmarks(self, file_path: str = None) -> ImportResult:
        """Import Reading List from Safari Bookmarks.plist file"""

        start_time = datetime.now()
        result = ImportResult(
            total_items=0,
            new_items=0,
            updated_items=0,
            failed_items=0,
            duplicate_items=0,
            processing_time=0.0,
            errors=[],
            imported_urls=[],
        )

        try:
            # Use provided path or auto-detect
            plist_path = file_path or self.reading_list_paths["macos_safari"]

            if not Path(plist_path).exists():
                result.errors.append(f"Safari bookmarks file not found: {plist_path}")
                return result

            # Read plist file
            with open(plist_path, "rb") as f:
                bookmarks_data = plistlib.load(f)

            # Extract Reading List items
            reading_list_items = self._extract_reading_list_from_plist(bookmarks_data)
            result.total_items = len(reading_list_items)

            # Process items in batches
            for i in range(0, len(reading_list_items), self.batch_size):
                batch = reading_list_items[i : i + self.batch_size]
                batch_result = await self._process_reading_list_batch(
                    batch, "safari_bookmarks"
                )

                result.new_items += batch_result["new"]
                result.updated_items += batch_result["updated"]
                result.failed_items += batch_result["failed"]
                result.duplicate_items += batch_result["duplicates"]
                result.errors.extend(batch_result["errors"])
                result.imported_urls.extend(batch_result["urls"])

                # Add delay between batches
                if i + self.batch_size < len(reading_list_items):
                    await asyncio.sleep(self.import_delay)

            # Record import history
            await self._record_import_history("safari_bookmarks", plist_path, result)

        except Exception as e:
            result.errors.append(f"Import error: {str(e)}")
            result.failed_items = result.total_items

        result.processing_time = (datetime.now() - start_time).total_seconds()
        return result

    def _extract_reading_list_from_plist(
        self, bookmarks_data: Dict[str, Any]
    ) -> List[ReadingListItem]:
        """Extract Reading List items from Safari bookmarks plist data"""

        reading_list_items = []

        def find_reading_list_folder(item):
            """Recursively find Reading List folder"""
            if isinstance(item, dict):
                # Check if this is the Reading List folder
                if (
                    item.get("Title") == "com.apple.ReadingList"
                    or item.get("WebBookmarkType") == "WebBookmarkTypeProxy"
                ):
                    return item.get("Children", [])

                # Check children
                children = item.get("Children", [])
                for child in children:
                    result = find_reading_list_folder(child)
                    if result:
                        return result

            return None

        # Find Reading List items
        reading_list_children = find_reading_list_folder(bookmarks_data)

        if reading_list_children:
            for item in reading_list_children:
                if isinstance(item, dict) and item.get("URLString"):
                    reading_list_item = self._parse_bookmark_item(item)
                    if reading_list_item:
                        reading_list_items.append(reading_list_item)

        return reading_list_items

    def _parse_bookmark_item(self, item: Dict[str, Any]) -> Optional[ReadingListItem]:
        """Parse individual bookmark item into ReadingListItem"""

        try:
            url = item.get("URLString", "").strip()
            if not url:
                return None

            title = (
                item.get("URIDictionary", {}).get("title", "")
                or item.get("Title", "")
                or url
            )

            # Extract metadata
            uri_dict = item.get("URIDictionary", {})
            reading_list_dict = item.get("ReadingList", {})

            # Parse dates
            date_added = None
            if "DateAdded" in reading_list_dict:
                try:
                    date_added = reading_list_dict["DateAdded"]
                    if isinstance(date_added, str):
                        date_added = datetime.fromisoformat(
                            date_added.replace("Z", "+00:00")
                        )
                except:
                    pass

            date_last_viewed = None
            if "DateLastViewed" in reading_list_dict:
                try:
                    date_last_viewed = reading_list_dict["DateLastViewed"]
                    if isinstance(date_last_viewed, str):
                        date_last_viewed = datetime.fromisoformat(
                            date_last_viewed.replace("Z", "+00:00")
                        )
                except:
                    pass

            # Extract additional metadata
            preview_text = reading_list_dict.get("PreviewText", "")
            site_name = uri_dict.get("title", "")

            # Estimate reading time based on preview text
            word_count = len(preview_text.split()) if preview_text else None
            estimated_reading_time = (
                (word_count // 200) if word_count else None
            )  # ~200 WPM

            return ReadingListItem(
                url=url,
                title=title,
                preview_text=preview_text,
                date_added=date_added,
                date_last_viewed=date_last_viewed,
                read_status=reading_list_dict.get("ReadingListNonSync", {}).get(
                    "isUnread", True
                )
                == False,
                bookmark_id=item.get("WebBookmarkUUID"),
                site_name=site_name,
                word_count=word_count,
                estimated_reading_time=estimated_reading_time,
            )

        except Exception as e:
            print(f"Error parsing bookmark item: {e}")
            return None

    async def _process_reading_list_batch(
        self, items: List[ReadingListItem], source: str
    ) -> Dict[str, Any]:
        """Process a batch of Reading List items"""

        result = {
            "new": 0,
            "updated": 0,
            "failed": 0,
            "duplicates": 0,
            "errors": [],
            "urls": [],
        }

        for item in items:
            try:
                # Generate URL hash for deduplication
                url_hash = hashlib.md5(item.url.encode()).hexdigest()

                # Check if item already exists
                existing_item = await self._get_existing_reading_list_item(url_hash)

                if existing_item:
                    # Update existing item if newer
                    if self._should_update_item(existing_item, item):
                        await self._update_reading_list_item(
                            existing_item["id"], item, source
                        )
                        result["updated"] += 1
                        result["urls"].append(item.url)
                    else:
                        result["duplicates"] += 1
                else:
                    # Insert new item
                    await self._insert_reading_list_item(item, url_hash, source)
                    result["new"] += 1
                    result["urls"].append(item.url)

                    # Queue for Atlas processing
                    await self._queue_for_atlas_processing(item.url)

            except Exception as e:
                result["failed"] += 1
                result["errors"].append(f"Failed to process {item.url}: {str(e)}")

        return result

    async def _get_existing_reading_list_item(
        self, url_hash: str
    ) -> Optional[Dict[str, Any]]:
        """Get existing Reading List item by URL hash"""

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                result = conn.execute(
                    """
                    SELECT * FROM reading_list_items WHERE url_hash = ?
                """,
                    (url_hash,),
                ).fetchone()

                return dict(result) if result else None

        except Exception as e:
            print(f"Error getting existing item: {e}")
            return None

    def _should_update_item(
        self, existing: Dict[str, Any], new_item: ReadingListItem
    ) -> bool:
        """Determine if existing item should be updated with new data"""

        # Update if new item has more recent data
        existing_date = existing.get("date_added")
        if existing_date and new_item.date_added:
            try:
                existing_datetime = datetime.fromisoformat(existing_date)
                return new_item.date_added > existing_datetime
            except:
                pass

        # Update if new item has more metadata
        if new_item.preview_text and not existing.get("preview_text"):
            return True

        if new_item.site_name and not existing.get("site_name"):
            return True

        return False

    async def _insert_reading_list_item(
        self, item: ReadingListItem, url_hash: str, source: str
    ):
        """Insert new Reading List item into database"""

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO reading_list_items
                    (url, url_hash, title, preview_text, date_added, date_last_viewed,
                     read_status, tags, bookmark_id, site_name, word_count,
                     estimated_reading_time, import_source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        item.url,
                        url_hash,
                        item.title,
                        item.preview_text,
                        item.date_added.isoformat() if item.date_added else None,
                        (
                            item.date_last_viewed.isoformat()
                            if item.date_last_viewed
                            else None
                        ),
                        item.read_status,
                        json.dumps(item.tags) if item.tags else None,
                        item.bookmark_id,
                        item.site_name,
                        item.word_count,
                        item.estimated_reading_time,
                        source,
                    ),
                )
                conn.commit()

        except Exception as e:
            print(f"Error inserting reading list item: {e}")
            raise

    async def _update_reading_list_item(
        self, item_id: int, item: ReadingListItem, source: str
    ):
        """Update existing Reading List item"""

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    UPDATE reading_list_items
                    SET title = ?, preview_text = ?, date_added = ?, date_last_viewed = ?,
                        read_status = ?, tags = ?, bookmark_id = ?, site_name = ?,
                        word_count = ?, estimated_reading_time = ?, import_source = ?,
                        last_updated = CURRENT_TIMESTAMP
                    WHERE id = ?
                """,
                    (
                        item.title,
                        item.preview_text,
                        item.date_added.isoformat() if item.date_added else None,
                        (
                            item.date_last_viewed.isoformat()
                            if item.date_last_viewed
                            else None
                        ),
                        item.read_status,
                        json.dumps(item.tags) if item.tags else None,
                        item.bookmark_id,
                        item.site_name,
                        item.word_count,
                        item.estimated_reading_time,
                        source,
                        item_id,
                    ),
                )
                conn.commit()

        except Exception as e:
            print(f"Error updating reading list item: {e}")
            raise

    async def _queue_for_atlas_processing(self, url: str):
        """Queue URL for Atlas article processing"""

        try:
            # Add to articles.txt for immediate processing
            articles_file = Path(__file__).parent.parent / "inputs" / "articles.txt"

            # Check if URL already exists in articles.txt
            existing_urls = set()
            if articles_file.exists():
                with open(articles_file, "r") as f:
                    existing_urls = {
                        line.strip()
                        for line in f
                        if line.strip() and not line.startswith("#")
                    }

            if url not in existing_urls:
                with open(articles_file, "a") as f:
                    f.write(
                        f"\n# From Reading List import - {datetime.now().isoformat()}\n"
                    )
                    f.write(f"{url}\n")

        except Exception as e:
            print(f"Error queuing for Atlas processing: {e}")

    async def _record_import_history(
        self, source: str, file_path: str, result: ImportResult
    ):
        """Record import operation in history"""

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO reading_list_imports
                    (import_source, file_path, total_items, new_items, updated_items,
                     failed_items, duplicate_items, processing_time, import_status, error_log)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        source,
                        file_path,
                        result.total_items,
                        result.new_items,
                        result.updated_items,
                        result.failed_items,
                        result.duplicate_items,
                        result.processing_time,
                        "success" if result.failed_items == 0 else "partial",
                        json.dumps(result.errors) if result.errors else None,
                    ),
                )
                conn.commit()

        except Exception as e:
            print(f"Error recording import history: {e}")

    async def import_from_exported_html(self, file_path: str) -> ImportResult:
        """Import Reading List from exported HTML bookmarks file"""

        start_time = datetime.now()
        result = ImportResult(
            total_items=0,
            new_items=0,
            updated_items=0,
            failed_items=0,
            duplicate_items=0,
            processing_time=0.0,
            errors=[],
            imported_urls=[],
        )

        try:
            if not Path(file_path).exists():
                result.errors.append(f"HTML bookmarks file not found: {file_path}")
                return result

            # Parse HTML bookmarks
            reading_list_items = await self._parse_html_bookmarks(file_path)
            result.total_items = len(reading_list_items)

            # Process items
            for i in range(0, len(reading_list_items), self.batch_size):
                batch = reading_list_items[i : i + self.batch_size]
                batch_result = await self._process_reading_list_batch(
                    batch, "html_export"
                )

                result.new_items += batch_result["new"]
                result.updated_items += batch_result["updated"]
                result.failed_items += batch_result["failed"]
                result.duplicate_items += batch_result["duplicates"]
                result.errors.extend(batch_result["errors"])
                result.imported_urls.extend(batch_result["urls"])

                if i + self.batch_size < len(reading_list_items):
                    await asyncio.sleep(self.import_delay)

            await self._record_import_history("html_export", file_path, result)

        except Exception as e:
            result.errors.append(f"HTML import error: {str(e)}")
            result.failed_items = result.total_items

        result.processing_time = (datetime.now() - start_time).total_seconds()
        return result

    async def _parse_html_bookmarks(self, file_path: str) -> List[ReadingListItem]:
        """Parse HTML bookmarks export file"""

        reading_list_items = []

        try:
            # Simple HTML parsing for bookmarks
            # This is a basic implementation - could be enhanced with proper HTML parsing
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Look for Reading List section
            import re

            # Find bookmark entries
            bookmark_pattern = r'<A HREF="([^"]+)"[^>]*>([^<]+)</A>'
            matches = re.findall(bookmark_pattern, content)

            for url, title in matches:
                # Basic validation
                if url.startswith("http"):
                    item = ReadingListItem(
                        url=url,
                        title=title,
                        date_added=datetime.now(),  # No date info in basic HTML export
                    )
                    reading_list_items.append(item)

        except Exception as e:
            print(f"Error parsing HTML bookmarks: {e}")

        return reading_list_items

    async def import_from_manual_files(self) -> ImportResult:
        """Import from manually placed files in the import directory"""

        start_time = datetime.now()
        result = ImportResult(
            total_items=0,
            new_items=0,
            updated_items=0,
            failed_items=0,
            duplicate_items=0,
            processing_time=0.0,
            errors=[],
            imported_urls=[],
        )

        try:
            import_dir = Path(self.reading_list_paths["manual_import"])

            # Look for supported files
            supported_files = []
            for pattern in ["*.plist", "*.html", "*.txt", "*.json"]:
                supported_files.extend(import_dir.glob(pattern))

            if not supported_files:
                result.errors.append(
                    "No supported files found in manual import directory"
                )
                return result

            # Process each file
            for file_path in supported_files:
                try:
                    if file_path.suffix.lower() == ".plist":
                        file_result = await self.import_from_safari_bookmarks(
                            str(file_path)
                        )
                    elif file_path.suffix.lower() == ".html":
                        file_result = await self.import_from_exported_html(
                            str(file_path)
                        )
                    elif file_path.suffix.lower() == ".txt":
                        file_result = await self._import_from_url_list(str(file_path))
                    elif file_path.suffix.lower() == ".json":
                        file_result = await self._import_from_json(str(file_path))
                    else:
                        continue

                    # Aggregate results
                    result.total_items += file_result.total_items
                    result.new_items += file_result.new_items
                    result.updated_items += file_result.updated_items
                    result.failed_items += file_result.failed_items
                    result.duplicate_items += file_result.duplicate_items
                    result.errors.extend(file_result.errors)
                    result.imported_urls.extend(file_result.imported_urls)

                except Exception as e:
                    result.errors.append(f"Error processing {file_path}: {str(e)}")

        except Exception as e:
            result.errors.append(f"Manual import error: {str(e)}")

        result.processing_time = (datetime.now() - start_time).total_seconds()
        return result

    async def _import_from_url_list(self, file_path: str) -> ImportResult:
        """Import from a simple text file with one URL per line"""

        result = ImportResult(
            total_items=0,
            new_items=0,
            updated_items=0,
            failed_items=0,
            duplicate_items=0,
            processing_time=0.0,
            errors=[],
            imported_urls=[],
        )

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            items = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith("#") and line.startswith("http"):
                    item = ReadingListItem(
                        url=line,
                        title=line,  # Will be updated when processed
                        date_added=datetime.now(),
                    )
                    items.append(item)

            result.total_items = len(items)

            # Process items
            if items:
                batch_result = await self._process_reading_list_batch(items, "url_list")
                result.new_items = batch_result["new"]
                result.updated_items = batch_result["updated"]
                result.failed_items = batch_result["failed"]
                result.duplicate_items = batch_result["duplicates"]
                result.errors = batch_result["errors"]
                result.imported_urls = batch_result["urls"]

        except Exception as e:
            result.errors.append(f"URL list import error: {str(e)}")
            result.failed_items = result.total_items

        return result

    async def _import_from_json(self, file_path: str) -> ImportResult:
        """Import from JSON format Reading List export"""

        result = ImportResult(
            total_items=0,
            new_items=0,
            updated_items=0,
            failed_items=0,
            duplicate_items=0,
            processing_time=0.0,
            errors=[],
            imported_urls=[],
        )

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            items = []
            if isinstance(data, list):
                for item_data in data:
                    if isinstance(item_data, dict) and "url" in item_data:
                        item = ReadingListItem(
                            url=item_data["url"],
                            title=item_data.get("title", item_data["url"]),
                            preview_text=item_data.get("preview_text"),
                            date_added=(
                                datetime.fromisoformat(item_data["date_added"])
                                if item_data.get("date_added")
                                else datetime.now()
                            ),
                            read_status=item_data.get("read_status", False),
                            tags=item_data.get("tags", []),
                        )
                        items.append(item)

            result.total_items = len(items)

            # Process items
            if items:
                batch_result = await self._process_reading_list_batch(
                    items, "json_export"
                )
                result.new_items = batch_result["new"]
                result.updated_items = batch_result["updated"]
                result.failed_items = batch_result["failed"]
                result.duplicate_items = batch_result["duplicates"]
                result.errors = batch_result["errors"]
                result.imported_urls = batch_result["urls"]

        except Exception as e:
            result.errors.append(f"JSON import error: {str(e)}")
            result.failed_items = result.total_items

        return result

    async def auto_detect_and_import(self) -> ImportResult:
        """Auto-detect available Reading List sources and import"""

        combined_result = ImportResult(
            total_items=0,
            new_items=0,
            updated_items=0,
            failed_items=0,
            duplicate_items=0,
            processing_time=0.0,
            errors=[],
            imported_urls=[],
        )

        start_time = datetime.now()

        try:
            # Try Safari bookmarks first
            safari_path = self.reading_list_paths["macos_safari"]
            if Path(safari_path).exists():
                print(f"Found Safari bookmarks at: {safari_path}")
                safari_result = await self.import_from_safari_bookmarks(safari_path)
                self._merge_import_results(combined_result, safari_result)

            # Try manual import directory
            manual_result = await self.import_from_manual_files()
            self._merge_import_results(combined_result, manual_result)

            # Try backup/alternative locations
            for name, path in self.reading_list_paths.items():
                if name.startswith("safari_bookmarks_backup") and Path(path).exists():
                    backup_result = await self.import_from_safari_bookmarks(path)
                    self._merge_import_results(combined_result, backup_result)

        except Exception as e:
            combined_result.errors.append(f"Auto-detect import error: {str(e)}")

        combined_result.processing_time = (datetime.now() - start_time).total_seconds()
        return combined_result

    def _merge_import_results(self, combined: ImportResult, new: ImportResult):
        """Merge import results from multiple sources"""
        combined.total_items += new.total_items
        combined.new_items += new.new_items
        combined.updated_items += new.updated_items
        combined.failed_items += new.failed_items
        combined.duplicate_items += new.duplicate_items
        combined.errors.extend(new.errors)
        combined.imported_urls.extend(new.imported_urls)

    async def get_reading_list_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get Reading List import and processing statistics"""

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                since_date = (datetime.now() - timedelta(days=days)).isoformat()

                # Basic statistics
                basic_stats = conn.execute(
                    """
                    SELECT
                        COUNT(*) as total_items,
                        COUNT(CASE WHEN processing_status = 'completed' THEN 1 END) as processed,
                        COUNT(CASE WHEN processing_status = 'pending' THEN 1 END) as pending,
                        COUNT(CASE WHEN processing_status = 'failed' THEN 1 END) as failed,
                        COUNT(CASE WHEN read_status = 1 THEN 1 END) as read_items,
                        AVG(estimated_reading_time) as avg_reading_time
                    FROM reading_list_items
                    WHERE imported_at > ?
                """,
                    (since_date,),
                ).fetchone()

                # Import source breakdown
                source_stats = conn.execute(
                    """
                    SELECT import_source, COUNT(*) as count
                    FROM reading_list_items
                    WHERE imported_at > ?
                    GROUP BY import_source
                    ORDER BY count DESC
                """,
                    (since_date,),
                ).fetchall()

                # Recent imports
                recent_imports = conn.execute(
                    """
                    SELECT * FROM reading_list_imports
                    WHERE imported_at > ?
                    ORDER BY imported_at DESC
                    LIMIT 10
                """,
                    (since_date,),
                ).fetchall()

                # Top sites
                top_sites = conn.execute(
                    """
                    SELECT site_name, COUNT(*) as count
                    FROM reading_list_items
                    WHERE site_name IS NOT NULL AND imported_at > ?
                    GROUP BY site_name
                    ORDER BY count DESC
                    LIMIT 10
                """,
                    (since_date,),
                ).fetchall()

                return {
                    "basic_statistics": dict(basic_stats) if basic_stats else {},
                    "import_sources": [dict(row) for row in source_stats],
                    "recent_imports": [dict(row) for row in recent_imports],
                    "top_sites": [dict(row) for row in top_sites],
                    "period_days": days,
                }

        except Exception as e:
            print(f"Error getting reading list statistics: {e}")
            return {}

    async def export_reading_list(
        self, format: str = "json", output_path: str = None
    ) -> Dict[str, Any]:
        """Export Reading List to various formats"""

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                items = conn.execute(
                    """
                    SELECT * FROM reading_list_items
                    ORDER BY date_added DESC
                """
                ).fetchall()

                items_data = [dict(row) for row in items]

                if not output_path:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    output_path = f"reading_list_export_{timestamp}.{format}"

                if format == "json":
                    with open(output_path, "w", encoding="utf-8") as f:
                        json.dump(items_data, f, indent=2, default=str)

                elif format == "csv":
                    import csv

                    with open(output_path, "w", newline="", encoding="utf-8") as f:
                        if items_data:
                            writer = csv.DictWriter(f, fieldnames=items_data[0].keys())
                            writer.writeheader()
                            writer.writerows(items_data)

                elif format == "txt":
                    with open(output_path, "w", encoding="utf-8") as f:
                        for item in items_data:
                            f.write(f"{item['title']}\n{item['url']}\n\n")

                return {
                    "success": True,
                    "items_exported": len(items_data),
                    "output_path": output_path,
                    "format": format,
                }

        except Exception as e:
            return {"success": False, "error": str(e)}
