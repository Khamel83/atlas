"""
Inbox Processor - Process files dropped into data/inbox/.

Supports:
- URLs: data/inbox/urls/*.txt (one URL per line)
- Files: data/inbox/files/*.{md,txt,html}
- Audio: data/inbox/audio/*.{mp3,m4a,wav}
- PDFs: data/inbox/pdfs/*.pdf
- Articles: data/inbox/articles/**/*.md (Instapaper exports with selections)

Files are moved to archive/inbox/ after processing.
"""

import hashlib
import json
import os
import logging
import re
import shutil
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

from modules.storage import FileStore, IndexManager, ContentItem, ContentType, SourceType

logger = logging.getLogger(__name__)


class InboxProcessor:
    """Process files from the manual inbox."""

    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir)
        self.inbox_dir = self.base_dir / "data/inbox"
        self.archive_dir = self.base_dir / "archive/inbox"
        self.file_store = FileStore("data/content")
        self.index_manager = IndexManager("data/indexes/atlas_index.db")

        # Rate limiting
        self.request_delay = 2.5  # seconds between external requests
        self.last_request_time = 0.0

        # Create directories
        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        for subdir in ["urls", "files", "audio", "pdfs", "articles"]:
            (self.inbox_dir / subdir).mkdir(exist_ok=True)
            (self.archive_dir / subdir).mkdir(exist_ok=True)

        # Notes directory for selections
        self.notes_dir = self.base_dir / "data/content/note"
        self.notes_dir.mkdir(parents=True, exist_ok=True)

        self.stats = {
            "urls_processed": 0,
            "files_processed": 0,
            "audio_processed": 0,
            "pdfs_processed": 0,
            "articles_processed": 0,
            "urls_queued": 0,
            "errors": 0,
            "skipped_duplicates": 0,
        }

    def _rate_limit(self):
        """Enforce rate limiting between external requests."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.request_delay:
            time.sleep(self.request_delay - elapsed)
        self.last_request_time = time.time()

    def _archive_file(self, file_path: Path, subdir: str):
        """Move processed file to archive."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_name = f"{timestamp}_{file_path.name}"
        dest = self.archive_dir / subdir / archive_name
        shutil.move(str(file_path), str(dest))
        logger.info(f"Archived {file_path.name} to {dest}")

    def process_all(self) -> Dict[str, Any]:
        """Process all items in the inbox."""
        logger.info("Processing inbox...")

        self._process_url_files()
        self._process_text_files()
        self._process_audio_files()
        self._process_pdf_files()
        self._process_article_exports()

        logger.info(f"Inbox processing complete: {self.stats}")
        return self.stats

    def _process_url_files(self):
        """Process URL files (one URL per line)."""
        url_dir = self.inbox_dir / "urls"

        for txt_file in url_dir.glob("*.txt"):
            logger.info(f"Processing URL file: {txt_file.name}")
            try:
                with open(txt_file, "r", encoding="utf-8") as f:
                    urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]

                for url in urls:
                    try:
                        self._process_url(url)
                        self.stats["urls_processed"] += 1
                    except Exception as e:
                        logger.error(f"Error processing URL {url}: {e}")
                        self.stats["errors"] += 1

                self._archive_file(txt_file, "urls")
            except Exception as e:
                logger.error(f"Error reading URL file {txt_file}: {e}")
                self.stats["errors"] += 1

    def _process_url(self, url: str):
        """Process a single URL."""
        # Check for duplicate
        exists, content_id = self.file_store.exists_by_url(url)
        if exists:
            logger.info(f"Skipping duplicate URL: {url}")
            self.stats["skipped_duplicates"] += 1
            return

        self._rate_limit()

        # For now, create a placeholder item
        # The content pipeline will handle actual fetching
        content_id = ContentItem.generate_id(source_url=url)

        item = ContentItem(
            content_id=content_id,
            content_type=ContentType.ARTICLE,
            source_type=SourceType.MANUAL,
            title=f"Pending: {url[:50]}...",
            source_url=url,
            status="pending",
            extra={"inbox_source": "urls", "needs_fetch": True}
        )

        item_dir = self.file_store.save(item)
        self.index_manager.index_item(item, str(item_dir))
        logger.info(f"Queued URL for processing: {url}")

    def _process_text_files(self):
        """Process text/markdown files."""
        files_dir = self.inbox_dir / "files"

        for file_path in files_dir.glob("*"):
            if file_path.suffix.lower() not in [".md", ".txt", ".html"]:
                continue

            logger.info(f"Processing text file: {file_path.name}")
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Extract title from first line if markdown heading
                lines = content.split("\n")
                title = file_path.stem
                for line in lines:
                    if line.startswith("# "):
                        title = line[2:].strip()
                        break

                content_id = ContentItem.generate_id(title=title, content=content[:500])

                # Check for duplicate
                if self.file_store.exists(content_id):
                    logger.info(f"Skipping duplicate file: {file_path.name}")
                    self.stats["skipped_duplicates"] += 1
                    self._archive_file(file_path, "files")
                    continue

                content_type = ContentType.NOTE
                if file_path.suffix.lower() == ".html":
                    content_type = ContentType.ARTICLE

                item = ContentItem(
                    content_id=content_id,
                    content_type=content_type,
                    source_type=SourceType.MANUAL,
                    title=title,
                    status="completed",
                    extra={"inbox_source": "files", "original_filename": file_path.name}
                )

                item_dir = self.file_store.save(item, content=content)
                self.index_manager.index_item(item, str(item_dir), search_text=content)

                self._archive_file(file_path, "files")
                self.stats["files_processed"] += 1
                logger.info(f"Processed file: {file_path.name}")

            except Exception as e:
                logger.error(f"Error processing file {file_path}: {e}")
                self.stats["errors"] += 1

    def _process_audio_files(self):
        """Process audio files for transcription."""
        audio_dir = self.inbox_dir / "audio"

        for file_path in audio_dir.glob("*"):
            if file_path.suffix.lower() not in [".mp3", ".m4a", ".wav", ".ogg", ".flac"]:
                continue

            logger.info(f"Processing audio file: {file_path.name}")
            try:
                content_id = ContentItem.generate_id(title=file_path.stem)

                if self.file_store.exists(content_id):
                    logger.info(f"Skipping duplicate audio: {file_path.name}")
                    self.stats["skipped_duplicates"] += 1
                    self._archive_file(file_path, "audio")
                    continue

                # Create item for transcription queue
                item = ContentItem(
                    content_id=content_id,
                    content_type=ContentType.PODCAST,
                    source_type=SourceType.MANUAL,
                    title=file_path.stem,
                    status="pending",
                    extra={
                        "inbox_source": "audio",
                        "original_filename": file_path.name,
                        "needs_transcription": True
                    }
                )

                # Read audio file as raw data
                with open(file_path, "rb") as f:
                    audio_data = f.read()

                item_dir = self.file_store.save(
                    item,
                    raw_data=audio_data,
                    raw_filename=file_path.name
                )
                self.index_manager.index_item(item, str(item_dir))

                self._archive_file(file_path, "audio")
                self.stats["audio_processed"] += 1
                logger.info(f"Queued audio for transcription: {file_path.name}")

            except Exception as e:
                logger.error(f"Error processing audio {file_path}: {e}")
                self.stats["errors"] += 1

    def _process_pdf_files(self):
        """Process PDF files."""
        pdf_dir = self.inbox_dir / "pdfs"

        for file_path in pdf_dir.glob("*.pdf"):
            logger.info(f"Processing PDF file: {file_path.name}")
            try:
                content_id = ContentItem.generate_id(title=file_path.stem)

                if self.file_store.exists(content_id):
                    logger.info(f"Skipping duplicate PDF: {file_path.name}")
                    self.stats["skipped_duplicates"] += 1
                    self._archive_file(file_path, "pdfs")
                    continue

                item = ContentItem(
                    content_id=content_id,
                    content_type=ContentType.DOCUMENT,
                    source_type=SourceType.MANUAL,
                    title=file_path.stem,
                    status="pending",
                    extra={
                        "inbox_source": "pdfs",
                        "original_filename": file_path.name,
                        "needs_extraction": True
                    }
                )

                # Read PDF as raw data
                with open(file_path, "rb") as f:
                    pdf_data = f.read()

                item_dir = self.file_store.save(
                    item,
                    raw_data=pdf_data,
                    raw_filename=file_path.name
                )
                self.index_manager.index_item(item, str(item_dir))

                self._archive_file(file_path, "pdfs")
                self.stats["pdfs_processed"] += 1
                logger.info(f"Queued PDF for extraction: {file_path.name}")

            except Exception as e:
                logger.error(f"Error processing PDF {file_path}: {e}")
                self.stats["errors"] += 1

    def _process_article_exports(self):
        """Process Instapaper-style markdown exports (selections/highlights)."""
        articles_dir = self.inbox_dir / "articles"
        if not articles_dir.exists():
            return

        # Load known URLs to avoid duplicates
        known_urls = self._load_known_urls()

        # Find all markdown files recursively
        for md_file in articles_dir.rglob("*.md"):
            try:
                data = self._parse_article_export(md_file)
                if not data:
                    continue

                url = data.get("url", "")
                if url in known_urls:
                    logger.debug(f"Skipping duplicate: {url[:50]}")
                    self.stats["skipped_duplicates"] += 1
                    self._archive_article(md_file)
                    continue

                # Create note from selection
                if data.get("is_selection") and data.get("selection"):
                    self._create_note_from_selection(data)
                    self.stats["articles_processed"] += 1

                # Queue URL for full article fetch
                if url:
                    self._queue_url_for_fetch(url)
                    self.stats["urls_queued"] += 1
                    known_urls.add(url)

                self._archive_article(md_file)

            except Exception as e:
                logger.error(f"Error processing article {md_file}: {e}")
                self.stats["errors"] += 1

    def _parse_article_export(self, filepath: Path) -> Optional[Dict[str, Any]]:
        """Parse an Instapaper-style markdown export."""
        try:
            content = filepath.read_text(encoding="utf-8")
        except Exception:
            return None

        # Extract metadata
        title_match = re.search(r'^# (.+)$', content, re.MULTILINE)
        url_match = re.search(r'\*\*Source:\*\*\s*(https?://[^\s]+)', content)
        domain_match = re.search(r'\*\*Domain:\*\*\s*(\S+)', content)
        date_match = re.search(r'\*\*Added:\*\*\s*(\d{4}-\d{2}-\d{2})', content)

        # Extract selection content
        selection_match = re.search(
            r'## Selected Content\n\n(.+?)(?:\n---|\Z)', content, re.DOTALL
        )

        if not url_match:
            return None

        # Parse date
        added_date = datetime.now()
        if date_match:
            try:
                added_date = datetime.strptime(date_match.group(1), '%Y-%m-%d')
            except ValueError:
                pass

        is_selection = bool(selection_match) or 'Selection Content' in content

        return {
            "title": title_match.group(1) if title_match else "Untitled",
            "url": url_match.group(1).strip(),
            "domain": domain_match.group(1) if domain_match else "",
            "added_date": added_date,
            "selection": selection_match.group(1).strip() if selection_match else "",
            "is_selection": is_selection,
            "source_file": str(filepath),
        }

    def _create_note_from_selection(self, data: Dict[str, Any]):
        """Create a note from parsed selection data."""
        # Generate content_id from URL
        content_id = hashlib.sha256(data["url"].encode()).hexdigest()[:16]

        # Create path based on original date
        date_path = data["added_date"].strftime('%Y/%m/%d')
        note_dir = self.notes_dir / date_path / content_id

        if note_dir.exists():
            logger.debug(f"Note already exists: {content_id}")
            return

        note_dir.mkdir(parents=True, exist_ok=True)

        # Write content.md
        content_md = f"""# {data['title']}

{data['selection']}

---
Source: {data['url']}
"""
        (note_dir / 'content.md').write_text(content_md, encoding="utf-8")

        # Write metadata.json
        metadata = {
            "content_id": content_id,
            "type": "selection",
            "url": data["url"],
            "domain": data["domain"],
            "title": data["title"],
            "created_at": data["added_date"].isoformat(),
            "imported_at": datetime.now().isoformat(),
            "source_file": data["source_file"],
        }
        (note_dir / 'metadata.json').write_text(
            json.dumps(metadata, indent=2), encoding="utf-8"
        )

        logger.info(f"Created note: {data['domain']} - {data['title'][:40]}")

    def _load_known_urls(self) -> set:
        """Load all known URLs from queue and fetcher state."""
        known = set()

        # Load from url_queue.txt
        queue_file = self.base_dir / "data/url_queue.txt"
        if queue_file.exists():
            for line in queue_file.read_text().splitlines():
                if line.strip().startswith("http"):
                    known.add(line.strip())

        # Load from url_fetcher_state.json
        state_file = self.base_dir / "data/url_fetcher_state.json"
        if state_file.exists():
            try:
                state = json.loads(state_file.read_text())
                known.update(state.get("fetched", {}).keys())
                known.update(state.get("failed", {}).keys())
            except Exception:
                pass

        return known

    def _queue_url_for_fetch(self, url: str):
        """Append URL to the fetch queue."""
        queue_file = self.base_dir / "data/url_queue.txt"
        with open(queue_file, "a", encoding="utf-8") as f:
            f.write(url + "\n")

    def _archive_article(self, file_path: Path):
        """Move processed article to archive, preserving subdirectory structure."""
        articles_dir = self.inbox_dir / "articles"
        try:
            rel_path = file_path.relative_to(articles_dir)
        except ValueError:
            rel_path = Path(file_path.name)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_subdir = self.archive_dir / "articles" / rel_path.parent
        archive_subdir.mkdir(parents=True, exist_ok=True)

        dest = archive_subdir / f"{timestamp}_{file_path.name}"
        shutil.move(str(file_path), str(dest))
        logger.debug(f"Archived {file_path.name}")


def process_inbox():
    """CLI entry point for inbox processing."""
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    processor = InboxProcessor()
    stats = processor.process_all()

    print("\n" + "=" * 50)
    print("INBOX PROCESSING COMPLETE")
    print("=" * 50)
    print(f"URLs processed:     {stats['urls_processed']}")
    print(f"Files processed:    {stats['files_processed']}")
    print(f"Audio processed:    {stats['audio_processed']}")
    print(f"PDFs processed:     {stats['pdfs_processed']}")
    print(f"Articles processed: {stats['articles_processed']}")
    print(f"URLs queued:        {stats['urls_queued']}")
    print(f"Duplicates skipped: {stats['skipped_duplicates']}")
    print(f"Errors:             {stats['errors']}")
    print("=" * 50)

    return stats


if __name__ == "__main__":
    process_inbox()
