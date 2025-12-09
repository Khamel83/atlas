"""
Inbox Processor - Process files dropped into data/inbox/.

Supports:
- URLs: data/inbox/urls/*.txt (one URL per line)
- Files: data/inbox/files/*.{md,txt,html}
- Audio: data/inbox/audio/*.{mp3,m4a,wav}
- PDFs: data/inbox/pdfs/*.pdf

Files are moved to archive/inbox/ after processing.
"""

import os
import logging
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
        for subdir in ["urls", "files", "audio", "pdfs"]:
            (self.inbox_dir / subdir).mkdir(exist_ok=True)
            (self.archive_dir / subdir).mkdir(exist_ok=True)

        self.stats = {
            "urls_processed": 0,
            "files_processed": 0,
            "audio_processed": 0,
            "pdfs_processed": 0,
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
    print(f"Duplicates skipped: {stats['skipped_duplicates']}")
    print(f"Errors:             {stats['errors']}")
    print("=" * 50)

    return stats


if __name__ == "__main__":
    process_inbox()
