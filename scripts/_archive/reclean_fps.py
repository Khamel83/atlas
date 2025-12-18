#!/usr/bin/env python3
"""
Re-clean files that had potential false positives.

After updating negative patterns in ad_stripper.py, run this to:
1. Find all files that had removals matching risky patterns
2. Re-run the cleaner on those files (reads from original, writes to clean)
3. The updated negative patterns will prevent false positives

Usage:
    python scripts/reclean_fps.py --dry-run    # Preview what would be re-cleaned
    python scripts/reclean_fps.py              # Actually re-clean
"""

import argparse
import json
import sqlite3
from pathlib import Path
import sys

sys.path.insert(0, '.')

from modules.enrich.versioned_cleaner import VersionedCleaner


# Patterns that are known to cause false positives
RISKY_PATTERNS = [
    'slack', 'indeed', 'notion',  # Common words
    'monday', 'pitch', 'loom',    # Other risky brand names
]


def find_affected_content(changes_dir: Path) -> set:
    """Find content IDs that had risky pattern matches."""
    affected = set()

    for f in changes_dir.glob('*.json'):
        try:
            data = json.loads(f.read_text())
            content_id = data.get('content_id', '')
            for r in data.get('removals', []):
                pattern = r.get('pattern', '').lower()
                method = r.get('method', '')

                # Check if this was a risky pattern
                if method == 'advertiser' and pattern in RISKY_PATTERNS:
                    affected.add(content_id)
                    break

                # Also catch URL pattern FPs
                if method == 'url_pattern' and pattern in [r'\?utm_', r'\?ref=']:
                    text = r.get('text', '').lower()
                    if 'my book' in text or 'my newsletter' in text:
                        affected.add(content_id)
                        break
        except Exception:
            pass

    return affected


def get_original_paths(conn, content_ids: set) -> list:
    """Get original file paths for affected content."""
    if not content_ids:
        return []

    placeholders = ','.join('?' * len(content_ids))
    cursor = conn.execute(f'''
        SELECT content_id, original_path, content_type
        FROM cleaning_records
        WHERE content_id IN ({placeholders})
    ''', list(content_ids))

    return [(row[0], row[1], row[2]) for row in cursor.fetchall()]


def main():
    parser = argparse.ArgumentParser(description='Re-clean files with potential false positives')
    parser.add_argument('--dry-run', action='store_true', help='Preview without making changes')
    args = parser.parse_args()

    changes_dir = Path('data/enrich/changes')
    db_path = Path('data/enrich/enrich.db')

    if not changes_dir.exists() or not db_path.exists():
        print('Error: enrich data not found. Run the cleaner first.')
        return 1

    # Find affected content
    print('Scanning for files with potential false positives...')
    affected_ids = find_affected_content(changes_dir)
    print(f'Found {len(affected_ids)} potentially affected files')

    if not affected_ids:
        print('No files need re-cleaning!')
        return 0

    # Get original paths
    conn = sqlite3.connect(db_path)
    paths = get_original_paths(conn, affected_ids)
    conn.close()

    print(f'Resolved {len(paths)} file paths')

    if args.dry_run:
        print('\n[DRY RUN] Would re-clean:')
        for content_id, orig_path, content_type in paths[:20]:
            print(f'  {content_type}: {content_id}')
        if len(paths) > 20:
            print(f'  ... and {len(paths) - 20} more')
        return 0

    # Re-clean with updated patterns
    print('\nRe-cleaning with updated negative patterns...')
    cleaner = VersionedCleaner()

    success = 0
    errors = 0

    for content_id, orig_path, content_type in paths:
        try:
            if Path(orig_path).exists():
                record = cleaner.clean_file(orig_path, content_type, force=True)
                if record:
                    success += 1
                    if success % 50 == 0:
                        print(f'  Progress: {success}/{len(paths)}')
        except Exception as e:
            errors += 1
            print(f'  Error on {content_id}: {e}')

    print(f'\nDone! Re-cleaned {success} files, {errors} errors')

    # Clean up old change records for re-cleaned files
    print('\nCleaning up old change records...')
    for content_id, _, _ in paths:
        safe_id = content_id.replace(':', '_').replace('/', '_')
        old_record = changes_dir / f'{safe_id}.json'
        if old_record.exists():
            old_record.unlink()

    print('Complete!')
    return 0


if __name__ == '__main__':
    exit(main())
