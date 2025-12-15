#!/usr/bin/env python3
"""
Migrate Instapaper Selections to Notes

Finds all files with "Selection Content Extracted" pattern and:
1. Creates a note in data/content/note/ with the selection
2. Queues the source URL for full article fetch

Usage:
    python scripts/migrate_selections_to_notes.py --dry-run
    python scripts/migrate_selections_to_notes.py --apply
"""

import argparse
import hashlib
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.storage.content_types import ContentItem, ContentType, SourceType, ProcessingStatus

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

ARTICLE_DIR = Path("data/content/article")
NOTE_DIR = Path("data/content/note")
URL_QUEUE = Path("data/url_queue.txt")
SELECTION_PATTERN = "**Content Type:** Selection Content Extracted"


def find_selection_files() -> list[Path]:
    """Find all files containing 'Selection Content Extracted'."""
    selection_files = []

    for content_file in ARTICLE_DIR.rglob("content.md"):
        try:
            text = content_file.read_text(encoding='utf-8', errors='ignore')
            if SELECTION_PATTERN in text:
                selection_files.append(content_file)
        except Exception as e:
            logger.warning(f"Error reading {content_file}: {e}")

    return selection_files


def parse_selection_metadata(content: str) -> dict:
    """Extract metadata from Instapaper selection file."""
    metadata = {}

    # Extract title (first # heading)
    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if title_match:
        metadata['title'] = title_match.group(1).strip()

    # Extract source URL
    source_match = re.search(r'\*\*Source:\*\*\s*(https?://[^\s\n]+)', content)
    if source_match:
        metadata['source_url'] = source_match.group(1).strip()

    # Extract domain
    domain_match = re.search(r'\*\*Domain:\*\*\s*([^\s\n]+)', content)
    if domain_match:
        metadata['domain'] = domain_match.group(1).strip()

    # Extract folder
    folder_match = re.search(r'\*\*Folder:\*\*\s*([^\s\n]+)', content)
    if folder_match:
        metadata['folder'] = folder_match.group(1).strip()

    # Extract added date
    added_match = re.search(r'\*\*Added:\*\*\s*([^\s\n]+)', content)
    if added_match:
        try:
            metadata['added_at'] = datetime.fromisoformat(added_match.group(1).strip())
        except ValueError:
            pass

    # Extract selection length
    length_match = re.search(r'\*\*Selection Length:\*\*\s*(\d+)', content)
    if length_match:
        metadata['selection_length'] = int(length_match.group(1))

    # Extract the actual selection text (between "## Selected Content" and "---")
    selection_match = re.search(
        r'##\s*Selected Content\s*\n+(.*?)(?:\n---|\n\*This content)',
        content,
        re.DOTALL
    )
    if selection_match:
        metadata['selection_text'] = selection_match.group(1).strip()
    else:
        # Fallback: get content after metadata block
        parts = content.split('---')
        if len(parts) >= 2:
            metadata['selection_text'] = parts[1].strip()

    return metadata


def create_note_content(metadata: dict) -> str:
    """Create markdown content for the note."""
    lines = []

    # Title
    title = metadata.get('title', 'Untitled Selection')
    lines.append(f"# {title}")
    lines.append("")

    # Selection text
    selection = metadata.get('selection_text', '')
    if selection:
        lines.append(selection)
        lines.append("")

    # Footer with source
    lines.append("---")
    if metadata.get('source_url'):
        domain = metadata.get('domain', 'source')
        lines.append(f"*Source: [{domain}]({metadata['source_url']})*")
    if metadata.get('added_at'):
        lines.append(f"*Saved: {metadata['added_at'].strftime('%Y-%m-%d')}*")

    return '\n'.join(lines)


def migrate_selection(content_file: Path, dry_run: bool = True) -> dict:
    """Migrate a single selection file to a note."""
    result = {
        'source_file': str(content_file),
        'status': 'pending',
        'note_id': None,
        'url_queued': False,
        'error': None,
    }

    try:
        content = content_file.read_text(encoding='utf-8', errors='ignore')
        metadata = parse_selection_metadata(content)

        if not metadata.get('selection_text'):
            result['status'] = 'skipped'
            result['error'] = 'No selection text found'
            return result

        # Generate note ID based on selection content
        note_id = hashlib.sha256(
            (metadata.get('selection_text', '') +
             metadata.get('source_url', '')).encode()
        ).hexdigest()[:16]

        result['note_id'] = note_id
        result['title'] = metadata.get('title', 'Untitled')
        result['source_url'] = metadata.get('source_url')

        if dry_run:
            result['status'] = 'would_migrate'
            return result

        # Create note directory
        created_at = metadata.get('added_at', datetime.utcnow())
        date_str = created_at.strftime("%Y/%m/%d")
        note_dir = NOTE_DIR / date_str / note_id
        note_dir.mkdir(parents=True, exist_ok=True)

        # Create ContentItem
        item = ContentItem(
            content_id=note_id,
            content_type=ContentType.NOTE,
            source_type=SourceType.MIGRATION,
            title=metadata.get('title', 'Untitled Selection'),
            source_url=metadata.get('source_url'),
            created_at=created_at,
            updated_at=datetime.utcnow(),
            ingested_at=datetime.utcnow(),
            status=ProcessingStatus.COMPLETED,
            extra={
                'note_type': 'selection',
                'import_source': 'instapaper',
                'selection_length': metadata.get('selection_length', 0),
                'original_folder': metadata.get('folder', 'unknown'),
                'original_file': str(content_file),
                'domain': metadata.get('domain', ''),
            }
        )

        # Save metadata
        metadata_path = note_dir / "metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            f.write(item.to_json())

        # Save content
        note_content = create_note_content(metadata)
        content_path = note_dir / "content.md"
        with open(content_path, 'w', encoding='utf-8') as f:
            f.write(note_content)

        result['note_path'] = str(note_dir)

        # Queue source URL for article fetch
        if metadata.get('source_url'):
            with open(URL_QUEUE, 'a', encoding='utf-8') as f:
                f.write(metadata['source_url'] + '\n')
            result['url_queued'] = True

        result['status'] = 'migrated'

    except Exception as e:
        result['status'] = 'error'
        result['error'] = str(e)
        logger.error(f"Error migrating {content_file}: {e}")

    return result


def main():
    parser = argparse.ArgumentParser(description='Migrate Instapaper selections to notes')
    parser.add_argument('--dry-run', action='store_true', help='Preview without making changes')
    parser.add_argument('--apply', action='store_true', help='Actually perform migration')
    parser.add_argument('--limit', type=int, help='Limit number of files to process')
    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        print("Please specify --dry-run or --apply")
        sys.exit(1)

    dry_run = args.dry_run

    # Ensure directories exist
    NOTE_DIR.mkdir(parents=True, exist_ok=True)

    logger.info(f"Scanning for selection files in {ARTICLE_DIR}...")
    selection_files = find_selection_files()
    logger.info(f"Found {len(selection_files)} selection files")

    if args.limit:
        selection_files = selection_files[:args.limit]
        logger.info(f"Limited to {args.limit} files")

    # Process files
    results = {
        'migrated': 0,
        'would_migrate': 0,
        'skipped': 0,
        'errors': 0,
        'urls_queued': 0,
    }

    for i, content_file in enumerate(selection_files, 1):
        logger.info(f"[{i}/{len(selection_files)}] Processing {content_file}")

        result = migrate_selection(content_file, dry_run=dry_run)

        if result['status'] == 'migrated':
            results['migrated'] += 1
            if result['url_queued']:
                results['urls_queued'] += 1
            logger.info(f"  Migrated: {result['note_id']} - {result.get('title', 'Untitled')}")
        elif result['status'] == 'would_migrate':
            results['would_migrate'] += 1
            logger.info(f"  Would migrate: {result['note_id']} - {result.get('title', 'Untitled')}")
        elif result['status'] == 'skipped':
            results['skipped'] += 1
            logger.warning(f"  Skipped: {result['error']}")
        else:
            results['errors'] += 1
            logger.error(f"  Error: {result['error']}")

    # Summary
    print("\n" + "=" * 60)
    print("MIGRATION SUMMARY")
    print("=" * 60)
    print(f"Total files found:    {len(selection_files)}")

    if dry_run:
        print(f"Would migrate:        {results['would_migrate']}")
        print(f"Would skip:           {results['skipped']}")
        print(f"Errors:               {results['errors']}")
        print("\nRun with --apply to perform the migration")
    else:
        print(f"Migrated:             {results['migrated']}")
        print(f"URLs queued:          {results['urls_queued']}")
        print(f"Skipped:              {results['skipped']}")
        print(f"Errors:               {results['errors']}")
        print(f"\nNotes saved to:       {NOTE_DIR}")
        print(f"URLs queued in:       {URL_QUEUE}")


if __name__ == '__main__':
    main()
