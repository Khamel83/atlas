#!/usr/bin/env python3
"""
Magic Wormhole Receiver for Atlas

Receives files via magic-wormhole and auto-ingests them into Atlas.
Supports:
- URL lists (.txt with URLs)
- Instapaper/Pocket exports
- Markdown files
- JSON exports
- Archives (.zip, .tar.gz) containing any of the above

Usage:
    # One-time receive with code
    python -m modules.wormhole.receiver --code 7-crossword-potato

    # Interactive mode (prompts for code)
    python -m modules.wormhole.receiver

    # Watch mode - continuously listen for transfers
    python -m modules.wormhole.receiver --watch

The sender just runs:
    wormhole send myfile.txt
"""

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional, List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Config
ATLAS_ROOT = Path(__file__).parent.parent.parent
RECEIVE_DIR = ATLAS_ROOT / "data/wormhole"
INBOX_DIR = ATLAS_ROOT / "data/inbox"
URL_QUEUE = ATLAS_ROOT / "data/url_queue.txt"


class WormholeReceiver:
    """Receive and process files from magic-wormhole."""

    def __init__(self):
        RECEIVE_DIR.mkdir(parents=True, exist_ok=True)
        INBOX_DIR.mkdir(parents=True, exist_ok=True)

    def receive(self, code: Optional[str] = None) -> Optional[Path]:
        """
        Receive a file via wormhole.

        Args:
            code: Wormhole code (e.g., "7-crossword-potato").
                  If None, will prompt interactively.

        Returns:
            Path to received file, or None if failed.
        """
        # Build command
        cmd = ["wormhole", "receive", "--accept-file", "-o", str(RECEIVE_DIR)]
        if code:
            cmd.append(code)

        logger.info(f"Waiting for wormhole transfer...")
        if code:
            logger.info(f"Using code: {code}")
        else:
            logger.info("Enter the wormhole code when prompted")

        try:
            # Run wormhole receive
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode != 0:
                logger.error(f"Wormhole receive failed: {result.stderr}")
                return None

            # Parse output to find received filename
            # Output looks like: "Receiving 'filename.txt' (1234 bytes)"
            output = result.stdout + result.stderr
            for line in output.split('\n'):
                if "Receiving" in line or "received" in line.lower():
                    logger.info(line.strip())

            # Find the most recently modified file in receive dir
            files = list(RECEIVE_DIR.glob("*"))
            if not files:
                logger.error("No file received")
                return None

            received = max(files, key=lambda f: f.stat().st_mtime)
            logger.info(f"Received: {received.name}")
            return received

        except subprocess.TimeoutExpired:
            logger.error("Wormhole receive timed out")
            return None
        except Exception as e:
            logger.error(f"Wormhole receive error: {e}")
            return None

    def process_file(self, filepath: Path) -> dict:
        """
        Process a received file and ingest into Atlas.

        Returns:
            Dict with processing results.
        """
        results = {
            'file': filepath.name,
            'type': None,
            'urls_found': 0,
            'urls_added': 0,
            'errors': []
        }

        suffix = filepath.suffix.lower()

        try:
            # Handle archives
            if suffix == '.zip':
                results['type'] = 'zip_archive'
                extracted = self._extract_zip(filepath)
                for f in extracted:
                    sub_results = self.process_file(f)
                    results['urls_found'] += sub_results['urls_found']
                    results['urls_added'] += sub_results['urls_added']
                    results['errors'].extend(sub_results['errors'])

            elif suffix in ['.tar', '.gz', '.tgz']:
                results['type'] = 'tar_archive'
                extracted = self._extract_tar(filepath)
                for f in extracted:
                    sub_results = self.process_file(f)
                    results['urls_found'] += sub_results['urls_found']
                    results['urls_added'] += sub_results['urls_added']
                    results['errors'].extend(sub_results['errors'])

            # Handle URL lists
            elif suffix == '.txt':
                results['type'] = 'url_list'
                urls = self._extract_urls_from_txt(filepath)
                results['urls_found'] = len(urls)
                results['urls_added'] = self._add_urls_to_queue(urls)

            # Handle HTML exports (Instapaper, Pocket)
            elif suffix in ['.html', '.htm']:
                results['type'] = 'html_export'
                urls = self._extract_urls_from_html(filepath)
                results['urls_found'] = len(urls)
                results['urls_added'] = self._add_urls_to_queue(urls)

            # Handle JSON exports
            elif suffix == '.json':
                results['type'] = 'json_export'
                urls = self._extract_urls_from_json(filepath)
                results['urls_found'] = len(urls)
                results['urls_added'] = self._add_urls_to_queue(urls)

            # Handle Markdown
            elif suffix in ['.md', '.markdown']:
                results['type'] = 'markdown'
                urls = self._extract_urls_from_markdown(filepath)
                results['urls_found'] = len(urls)
                results['urls_added'] = self._add_urls_to_queue(urls)

            # Handle CSV
            elif suffix == '.csv':
                results['type'] = 'csv'
                urls = self._extract_urls_from_csv(filepath)
                results['urls_found'] = len(urls)
                results['urls_added'] = self._add_urls_to_queue(urls)

            else:
                results['type'] = 'unknown'
                results['errors'].append(f"Unknown file type: {suffix}")

        except Exception as e:
            results['errors'].append(str(e))
            logger.error(f"Error processing {filepath}: {e}")

        # Move to inbox for further processing
        if filepath.exists():
            dest = INBOX_DIR / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filepath.name}"
            shutil.move(str(filepath), str(dest))
            logger.info(f"Moved to inbox: {dest}")

        return results

    def _extract_zip(self, filepath: Path) -> List[Path]:
        """Extract zip and return list of extracted files."""
        extracted = []
        with tempfile.TemporaryDirectory() as tmpdir:
            with zipfile.ZipFile(filepath, 'r') as zf:
                zf.extractall(tmpdir)

            for root, dirs, files in os.walk(tmpdir):
                for f in files:
                    src = Path(root) / f
                    dest = RECEIVE_DIR / f
                    shutil.copy2(src, dest)
                    extracted.append(dest)

        return extracted

    def _extract_tar(self, filepath: Path) -> List[Path]:
        """Extract tar/tar.gz and return list of extracted files."""
        extracted = []
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(filepath) as tf:
                tf.extractall(tmpdir)

            for root, dirs, files in os.walk(tmpdir):
                for f in files:
                    src = Path(root) / f
                    dest = RECEIVE_DIR / f
                    shutil.copy2(src, dest)
                    extracted.append(dest)

        return extracted

    def _extract_urls_from_txt(self, filepath: Path) -> List[str]:
        """Extract URLs from text file (one per line)."""
        urls = []
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if line.startswith(('http://', 'https://')):
                    urls.append(line)
        return urls

    def _extract_urls_from_html(self, filepath: Path) -> List[str]:
        """Extract URLs from HTML file (Instapaper/Pocket export)."""
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            logger.warning("BeautifulSoup not available, skipping HTML parsing")
            return []

        urls = []
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')

        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.startswith(('http://', 'https://')):
                urls.append(href)

        return urls

    def _extract_urls_from_json(self, filepath: Path) -> List[str]:
        """Extract URLs from JSON file."""
        urls = []
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Handle various JSON formats
        if isinstance(data, list):
            for item in data:
                if isinstance(item, str) and item.startswith('http'):
                    urls.append(item)
                elif isinstance(item, dict):
                    for key in ['url', 'href', 'link', 'resolved_url', 'given_url']:
                        if key in item and item[key]:
                            urls.append(item[key])
                            break
        elif isinstance(data, dict):
            # Pocket export format
            if 'list' in data:
                for item_id, item in data['list'].items():
                    if 'resolved_url' in item:
                        urls.append(item['resolved_url'])
                    elif 'given_url' in item:
                        urls.append(item['given_url'])

        return urls

    def _extract_urls_from_markdown(self, filepath: Path) -> List[str]:
        """Extract URLs from Markdown file."""
        import re
        urls = []

        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Match [text](url) pattern
        md_links = re.findall(r'\[([^\]]*)\]\(([^)]+)\)', content)
        for text, url in md_links:
            if url.startswith(('http://', 'https://')):
                urls.append(url)

        # Match bare URLs
        bare_urls = re.findall(r'https?://[^\s<>"\']+', content)
        urls.extend(bare_urls)

        return list(set(urls))  # Dedupe

    def _extract_urls_from_csv(self, filepath: Path) -> List[str]:
        """Extract URLs from CSV file."""
        import csv
        urls = []

        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            # Try to detect if there's a header
            sample = f.read(1024)
            f.seek(0)

            has_header = 'url' in sample.lower() or 'http' not in sample[:100].lower()

            reader = csv.reader(f)
            if has_header:
                next(reader, None)  # Skip header

            for row in reader:
                for cell in row:
                    cell = cell.strip()
                    if cell.startswith(('http://', 'https://')):
                        urls.append(cell)

        return urls

    def _add_urls_to_queue(self, urls: List[str]) -> int:
        """Add URLs to the main queue file."""
        if not urls:
            return 0

        # Read existing URLs
        existing = set()
        if URL_QUEUE.exists():
            with open(URL_QUEUE, 'r') as f:
                existing = set(line.strip() for line in f if line.strip())

        # Add new URLs
        added = 0
        with open(URL_QUEUE, 'a') as f:
            for url in urls:
                if url not in existing:
                    f.write(url + '\n')
                    existing.add(url)
                    added += 1

        logger.info(f"Added {added} new URLs to queue (skipped {len(urls) - added} duplicates)")
        return added


def receive_and_ingest(code: Optional[str] = None) -> dict:
    """
    Convenience function to receive and ingest in one call.

    Args:
        code: Wormhole code, or None for interactive

    Returns:
        Processing results dict
    """
    receiver = WormholeReceiver()
    filepath = receiver.receive(code)

    if filepath:
        return receiver.process_file(filepath)
    else:
        return {'error': 'Failed to receive file'}


def main():
    parser = argparse.ArgumentParser(
        description='Receive files via magic-wormhole and ingest into Atlas',
        usage='atlas-wormhole-receive [CODE] [--watch]'
    )
    parser.add_argument('code', nargs='?', type=str, help='Wormhole code (e.g., 7-crossword-potato)')
    parser.add_argument('--watch', '-w', action='store_true', help='Watch mode - continuously listen')
    args = parser.parse_args()

    receiver = WormholeReceiver()

    if args.watch:
        logger.info("Starting watch mode - waiting for transfers...")
        logger.info("Sender should run: wormhole send <file>")
        while True:
            try:
                filepath = receiver.receive(args.code)
                if filepath:
                    results = receiver.process_file(filepath)
                    logger.info(f"Processed: {results}")
            except KeyboardInterrupt:
                logger.info("Stopping watch mode")
                break
    else:
        results = receive_and_ingest(args.code)
        print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
