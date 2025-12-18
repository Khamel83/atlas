#!/usr/bin/env python3
"""
Continuous improvement loop for ad detection.

This script implements the feedback loop:
1. Analyze current detections for false positives
2. Show patterns that need fixing
3. Re-clean affected files after patterns are updated
4. Repeat until FP rate is acceptable

Usage:
    python scripts/enrich_improve_loop.py              # Full analysis
    python scripts/enrich_improve_loop.py --fix        # Re-clean FPs after pattern update
    python scripts/enrich_improve_loop.py --threshold 10  # Stop when FPs < 10
"""

import argparse
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
import sys

sys.path.insert(0, '.')


# Known risky patterns (brand names that are common words)
RISKY_ADVERTISER_PATTERNS = [
    'slack', 'indeed', 'notion', 'monday', 'pitch', 'loom',
    'grain', 'stripe', 'square', 'asana', 'airtable', 'linear',
    'superhuman', 'mercury', 'ramp', 'brex', 'plaid',
]

# Sponsor signals that indicate it's really an ad
SPONSOR_SIGNALS = [
    'sponsor', 'brought to you', 'thanks to', 'promo',
    'code ', 'offer', 'trial', 'discount', '% off',
    'sign up', 'free trial', 'check out', 'visit',
]


def load_records(changes_dir: Path):
    """Load all removal records."""
    records = []
    for f in changes_dir.glob('*.json'):
        try:
            data = json.loads(f.read_text())
            content_id = data.get('content_id', '')
            for r in data.get('removals', []):
                r['content_id'] = content_id
                r['file'] = f.name
                records.append(r)
        except:
            pass
    return records


def find_false_positives(records):
    """Identify likely false positives."""
    fps = []

    for r in records:
        method = r.get('method', '')
        pattern = r.get('pattern', '')
        text = r.get('text', '')
        text_lower = text.lower()

        has_sponsor_signal = any(s in text_lower for s in SPONSOR_SIGNALS)

        is_fp = False
        fp_type = ''

        # Check advertiser patterns
        if method == 'advertiser':
            pattern_lower = pattern.lower()
            if pattern_lower in RISKY_ADVERTISER_PATTERNS:
                if not has_sponsor_signal:
                    is_fp = True
                    fp_type = f'{pattern} (common word)'

        # Check URL patterns
        if method == 'url_pattern' and pattern in [r'\?utm_', r'\?ref=', 'bit\\.ly/']:
            if 'my book' in text_lower or 'my newsletter' in text_lower or 'my substack' in text_lower:
                is_fp = True
                fp_type = 'Self-promo link'

        if is_fp:
            fps.append({
                'type': fp_type,
                'pattern': pattern,
                'method': method,
                'text': text[:200],
                'content_id': r.get('content_id', ''),
                'file': r.get('file', ''),
            })

    return fps


def analyze_and_report(records, fps):
    """Generate analysis report."""
    print('=' * 70)
    print('ENRICHMENT IMPROVEMENT ANALYSIS')
    print('=' * 70)

    print(f'\nTotal removals: {len(records):,}')
    print(f'Potential false positives: {len(fps)}')

    if not fps:
        print('\n✅ No false positives detected! Algorithm is performing well.')
        return

    fp_rate = len(fps) / len(records) * 100
    print(f'FP rate: {fp_rate:.2f}%')

    # Group by type
    by_type = defaultdict(list)
    for fp in fps:
        by_type[fp['type']].append(fp)

    print('\n' + '-' * 70)
    print('FALSE POSITIVES BY TYPE')
    print('-' * 70)

    for fp_type, items in sorted(by_type.items(), key=lambda x: -len(x[1])):
        print(f'\n### {fp_type} ({len(items)} cases)')

        # Show examples
        for item in items[:2]:
            print(f'  Content: {item["content_id"]}')
            print(f'  Text: {item["text"][:100]}...')
            print()

    # Suggest fixes
    print('\n' + '-' * 70)
    print('SUGGESTED FIXES for ad_stripper.py')
    print('-' * 70)

    for fp_type, items in sorted(by_type.items(), key=lambda x: -len(x[1])):
        pattern = items[0]['pattern'].lower()
        if 'common word' in fp_type:
            print(f'\n# Fix for "{pattern}" ({len(items)} FPs):')
            print(f'# Add to DEFAULT_NEGATIVE_PATTERNS:')
            print(f'#   r"\\b{pattern}\\b(?!.*(?:sponsor|promo|code|trial))",')


def get_affected_files(fps, db_path: Path):
    """Get original paths for files needing re-clean."""
    content_ids = set(fp['content_id'] for fp in fps)

    if not content_ids:
        return []

    conn = sqlite3.connect(db_path)
    placeholders = ','.join('?' * len(content_ids))
    cursor = conn.execute(f'''
        SELECT content_id, original_path, content_type
        FROM cleaning_records
        WHERE content_id IN ({placeholders})
    ''', list(content_ids))

    paths = [(row[0], row[1], row[2]) for row in cursor.fetchall()]
    conn.close()
    return paths


def reclean_files(paths, changes_dir: Path):
    """Re-clean files with updated patterns."""
    from modules.enrich.versioned_cleaner import VersionedCleaner

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

    # Clean up old change records
    for content_id, _, _ in paths:
        safe_id = content_id.replace(':', '_').replace('/', '_')
        old_record = changes_dir / f'{safe_id}.json'
        if old_record.exists():
            old_record.unlink()

    return success, errors


def main():
    parser = argparse.ArgumentParser(description='Continuous ad detection improvement')
    parser.add_argument('--fix', action='store_true', help='Re-clean files after pattern update')
    parser.add_argument('--threshold', type=int, default=0, help='Acceptable FP count')
    parser.add_argument('--iterations', type=int, default=1, help='Max improvement iterations')
    args = parser.parse_args()

    changes_dir = Path('data/enrich/changes')
    db_path = Path('data/enrich/enrich.db')

    if not changes_dir.exists():
        print('Error: No enrichment data found. Run the cleaner first.')
        return 1

    for iteration in range(args.iterations):
        if args.iterations > 1:
            print(f'\n{"=" * 70}')
            print(f'ITERATION {iteration + 1}')
            print('=' * 70)

        # Load and analyze
        records = load_records(changes_dir)
        fps = find_false_positives(records)

        analyze_and_report(records, fps)

        # Check threshold
        if len(fps) <= args.threshold:
            print(f'\n✅ FP count ({len(fps)}) is at or below threshold ({args.threshold})')
            break

        # Fix if requested
        if args.fix and fps:
            print(f'\nRe-cleaning {len(fps)} affected files...')
            paths = get_affected_files(fps, db_path)
            success, errors = reclean_files(paths, changes_dir)
            print(f'Re-cleaned {success} files, {errors} errors')
        elif fps:
            print('\nRun with --fix to re-clean affected files after updating patterns')
            break

    return 0


if __name__ == '__main__':
    exit(main())
