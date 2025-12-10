"""
Bulk Import - Process a messy folder of mixed content.

Drop any files here and they'll be auto-detected and processed:
- Instapaper HTML exports
- URL lists (.txt, .csv)
- Markdown files (.md)
- HTML files (.html)
- JSON exports (Pocket, etc.)

Deduplicates by URL hash - safe to re-run on same folder.

Usage:
    python -m modules.ingest.bulk_import /path/to/messy/folder
    python -m modules.ingest.bulk_import /path/to/folder --dry-run
"""

import os
import re
import csv
import json
import hashlib
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum

from bs4 import BeautifulSoup

from modules.storage import IndexManager
from modules.pipeline.content_pipeline import ContentPipeline

logger = logging.getLogger(__name__)


class FileType(Enum):
    """Detected file types."""
    INSTAPAPER_HTML = "instapaper_html"
    POCKET_JSON = "pocket_json"
    URL_LIST = "url_list"
    CSV_URLS = "csv_urls"
    MARKDOWN = "markdown"
    HTML_ARTICLE = "html_article"
    UNKNOWN = "unknown"


@dataclass
class ExtractedURL:
    """A URL extracted from a file."""
    url: str
    title: Optional[str] = None
    source_file: Optional[str] = None
    timestamp: Optional[datetime] = None


class BulkImporter:
    """Import content from a messy folder of mixed files."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.index = IndexManager("data/indexes/atlas_index.db")
        self.pipeline = ContentPipeline() if not dry_run else None

        self.stats = {
            "files_scanned": 0,
            "urls_found": 0,
            "urls_new": 0,
            "urls_duplicate": 0,
            "urls_processed": 0,
            "urls_failed": 0,
            "by_type": {}
        }

        # Track URLs we've seen this run (for intra-batch dedup)
        self.seen_urls: Set[str] = set()

    def _url_hash(self, url: str) -> str:
        """Generate hash for URL deduplication."""
        # Normalize URL
        url = url.strip().lower()
        # Remove tracking params
        url = re.sub(r'\?utm_[^&]+(&|$)', '', url)
        url = re.sub(r'&utm_[^&]+', '', url)
        return hashlib.sha256(url.encode()).hexdigest()[:16]

    def _is_duplicate(self, url: str) -> bool:
        """Check if URL is already processed."""
        # Check in-memory (this batch)
        url_hash = self._url_hash(url)
        if url_hash in self.seen_urls:
            return True

        # Check database
        existing = self.index.lookup_url(url)
        if existing:
            return True

        # Mark as seen for this batch
        self.seen_urls.add(url_hash)
        return False

    def _detect_file_type(self, path: Path) -> FileType:
        """Auto-detect what kind of file this is."""
        suffix = path.suffix.lower()

        if suffix == '.html' or suffix == '.htm':
            try:
                content = path.read_text(errors='ignore')
                # Instapaper exports have specific structure
                if 'instapaper' in content.lower() or '<ol>' in content and 'href=' in content:
                    soup = BeautifulSoup(content, 'html.parser')
                    # Instapaper exports are lists of links
                    links = soup.find_all('a', href=True)
                    if len(links) > 5:
                        return FileType.INSTAPAPER_HTML
                return FileType.HTML_ARTICLE
            except Exception as e:
                logger.debug(f"Error detecting HTML type for {path}: {e}")
                return FileType.UNKNOWN

        elif suffix == '.json':
            try:
                content = json.loads(path.read_text())
                # Pocket exports
                if isinstance(content, list) and content and 'url' in content[0]:
                    return FileType.POCKET_JSON
                if isinstance(content, dict) and 'list' in content:
                    return FileType.POCKET_JSON
            except Exception as e:
                logger.debug(f"Error parsing JSON {path}: {e}")
            return FileType.UNKNOWN

        elif suffix == '.txt':
            try:
                content = path.read_text(errors='ignore')
                # Check if it's a list of URLs
                lines = content.strip().split('\n')
                url_count = sum(1 for line in lines if line.strip().startswith('http'))
                if url_count > len(lines) * 0.5:
                    return FileType.URL_LIST
            except Exception as e:
                logger.debug(f"Error reading text file {path}: {e}")
            return FileType.UNKNOWN

        elif suffix == '.csv':
            return FileType.CSV_URLS

        elif suffix == '.md':
            return FileType.MARKDOWN

        return FileType.UNKNOWN

    def _extract_urls_instapaper(self, path: Path) -> List[ExtractedURL]:
        """Extract URLs from Instapaper HTML export."""
        urls = []
        try:
            soup = BeautifulSoup(path.read_text(errors='ignore'), 'html.parser')
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                if href.startswith('http') and 'instapaper.com' not in href:
                    urls.append(ExtractedURL(
                        url=href,
                        title=link.get_text(strip=True) or None,
                        source_file=str(path)
                    ))
        except Exception as e:
            logger.error(f"Error parsing Instapaper HTML {path}: {e}")
        return urls

    def _extract_urls_pocket(self, path: Path) -> List[ExtractedURL]:
        """Extract URLs from Pocket JSON export."""
        urls = []
        try:
            content = json.loads(path.read_text())
            items = content if isinstance(content, list) else content.get('list', {}).values()
            for item in items:
                if isinstance(item, dict) and 'url' in item:
                    urls.append(ExtractedURL(
                        url=item['url'],
                        title=item.get('title') or item.get('resolved_title'),
                        source_file=str(path)
                    ))
        except Exception as e:
            logger.error(f"Error parsing Pocket JSON {path}: {e}")
        return urls

    def _extract_urls_list(self, path: Path) -> List[ExtractedURL]:
        """Extract URLs from a plain text file (one per line)."""
        urls = []
        try:
            for line in path.read_text(errors='ignore').split('\n'):
                line = line.strip()
                if line.startswith('http'):
                    urls.append(ExtractedURL(url=line, source_file=str(path)))
        except Exception as e:
            logger.error(f"Error parsing URL list {path}: {e}")
        return urls

    def _extract_urls_csv(self, path: Path) -> List[ExtractedURL]:
        """Extract URLs from CSV file."""
        urls = []
        try:
            with open(path, newline='', errors='ignore') as f:
                # Try to detect if there's a header
                sample = f.read(2048)
                f.seek(0)
                has_header = csv.Sniffer().has_header(sample)

                reader = csv.reader(f)
                if has_header:
                    headers = next(reader)
                    # Find URL column
                    url_col = None
                    title_col = None
                    for i, h in enumerate(headers):
                        h_lower = h.lower()
                        if 'url' in h_lower or 'link' in h_lower:
                            url_col = i
                        if 'title' in h_lower:
                            title_col = i

                    if url_col is not None:
                        for row in reader:
                            if len(row) > url_col and row[url_col].startswith('http'):
                                title = row[title_col] if title_col and len(row) > title_col else None
                                urls.append(ExtractedURL(
                                    url=row[url_col],
                                    title=title,
                                    source_file=str(path)
                                ))
                else:
                    # No header - assume first column is URL
                    for row in reader:
                        if row and row[0].startswith('http'):
                            urls.append(ExtractedURL(url=row[0], source_file=str(path)))
        except Exception as e:
            logger.error(f"Error parsing CSV {path}: {e}")
        return urls

    def _extract_urls_markdown(self, path: Path) -> List[ExtractedURL]:
        """Extract URLs from markdown file (links in [text](url) format)."""
        urls = []
        try:
            content = path.read_text(errors='ignore')
            # Find markdown links
            for match in re.finditer(r'\[([^\]]*)\]\((https?://[^)]+)\)', content):
                urls.append(ExtractedURL(
                    url=match.group(2),
                    title=match.group(1) or None,
                    source_file=str(path)
                ))
            # Also find bare URLs
            for match in re.finditer(r'(?<!\()(https?://\S+?)(?=[)\s,\]"]|$)', content):
                url = match.group(1).rstrip('.,;:')
                if not any(u.url == url for u in urls):
                    urls.append(ExtractedURL(url=url, source_file=str(path)))
        except Exception as e:
            logger.error(f"Error parsing markdown {path}: {e}")
        return urls

    def _extract_urls_html(self, path: Path) -> List[ExtractedURL]:
        """Extract the main URL from an HTML article (or URLs within)."""
        urls = []
        try:
            soup = BeautifulSoup(path.read_text(errors='ignore'), 'html.parser')

            # Look for canonical URL
            canonical = soup.find('link', rel='canonical')
            if canonical and canonical.get('href'):
                urls.append(ExtractedURL(
                    url=canonical['href'],
                    title=soup.title.string if soup.title else None,
                    source_file=str(path)
                ))

            # Look for og:url
            og_url = soup.find('meta', property='og:url')
            if og_url and og_url.get('content'):
                if not urls or urls[0].url != og_url['content']:
                    urls.append(ExtractedURL(
                        url=og_url['content'],
                        title=soup.title.string if soup.title else None,
                        source_file=str(path)
                    ))
        except Exception as e:
            logger.error(f"Error parsing HTML {path}: {e}")
        return urls

    def scan_folder(self, folder: Path) -> List[ExtractedURL]:
        """Scan a folder and extract all URLs."""
        all_urls = []

        for root, dirs, files in os.walk(folder):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]

            for filename in files:
                if filename.startswith('.'):
                    continue

                path = Path(root) / filename
                file_type = self._detect_file_type(path)
                self.stats["files_scanned"] += 1

                # Track by type
                type_name = file_type.value
                self.stats["by_type"][type_name] = self.stats["by_type"].get(type_name, 0) + 1

                # Extract URLs based on type
                urls = []
                if file_type == FileType.INSTAPAPER_HTML:
                    urls = self._extract_urls_instapaper(path)
                elif file_type == FileType.POCKET_JSON:
                    urls = self._extract_urls_pocket(path)
                elif file_type == FileType.URL_LIST:
                    urls = self._extract_urls_list(path)
                elif file_type == FileType.CSV_URLS:
                    urls = self._extract_urls_csv(path)
                elif file_type == FileType.MARKDOWN:
                    urls = self._extract_urls_markdown(path)
                elif file_type == FileType.HTML_ARTICLE:
                    urls = self._extract_urls_html(path)

                if urls:
                    logger.info(f"Found {len(urls)} URLs in {path.name} ({file_type.value})")
                    all_urls.extend(urls)

        return all_urls

    def process(self, folder: str) -> Dict[str, Any]:
        """
        Process a folder of mixed content.

        Args:
            folder: Path to folder to process

        Returns:
            Stats dictionary
        """
        folder_path = Path(folder)
        if not folder_path.exists():
            raise ValueError(f"Folder not found: {folder}")

        logger.info(f"Scanning {folder_path}...")
        urls = self.scan_folder(folder_path)
        self.stats["urls_found"] = len(urls)

        # Deduplicate
        new_urls = []
        for url_info in urls:
            if self._is_duplicate(url_info.url):
                self.stats["urls_duplicate"] += 1
            else:
                new_urls.append(url_info)
                self.stats["urls_new"] += 1

        logger.info(f"Found {len(urls)} URLs, {len(new_urls)} new after dedup")

        if self.dry_run:
            logger.info("DRY RUN - not processing URLs")
            print(f"\nWould process {len(new_urls)} new URLs:")
            for u in new_urls[:20]:
                print(f"  • {u.url[:80]}...")
            if len(new_urls) > 20:
                print(f"  ... and {len(new_urls) - 20} more")
            return self.stats

        # Process new URLs
        for i, url_info in enumerate(new_urls):
            try:
                logger.info(f"[{i+1}/{len(new_urls)}] Processing: {url_info.url[:60]}...")
                result = self.pipeline.process_url(url_info.url, title=url_info.title)
                if result:
                    self.stats["urls_processed"] += 1
                else:
                    self.stats["urls_failed"] += 1
            except Exception as e:
                logger.error(f"Failed to process {url_info.url}: {e}")
                self.stats["urls_failed"] += 1

        return self.stats


def main():
    parser = argparse.ArgumentParser(
        description="Bulk import from a messy folder of mixed content"
    )
    parser.add_argument("folder", help="Path to folder to process")
    parser.add_argument("--dry-run", action="store_true",
                        help="Scan and report without processing")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Verbose output")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    importer = BulkImporter(dry_run=args.dry_run)
    stats = importer.process(args.folder)

    print(f"\n{'='*60}")
    print("BULK IMPORT RESULTS")
    print(f"{'='*60}")
    print(f"Files scanned:    {stats['files_scanned']}")
    print(f"URLs found:       {stats['urls_found']}")
    print(f"  New:            {stats['urls_new']}")
    print(f"  Duplicate:      {stats['urls_duplicate']}")
    if not args.dry_run:
        print(f"  Processed:      {stats['urls_processed']}")
        print(f"  Failed:         {stats['urls_failed']}")
    print(f"\nBy file type:")
    for file_type, count in sorted(stats['by_type'].items()):
        print(f"  {file_type}: {count}")


if __name__ == "__main__":
    main()
