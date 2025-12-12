#!/usr/bin/env python3
"""
Full Atlas content enrichment workflow.

Runs the complete enrichment pipeline:
1. Clean all content (podcasts, articles, newsletters, youtube, stratechery)
2. Analyze for false positives
3. If FPs found, fix and re-run (up to 3 iterations)
4. Sanitize URLs (strip tracking params from all content)
5. Extract links (queue high-value URLs for potential ingestion)
6. Generate report

Usage:
    python scripts/run_enrichment.py              # Full run
    python scripts/run_enrichment.py --dry-run    # Preview only
    python scripts/run_enrichment.py --type podcasts  # Specific type
    python scripts/run_enrichment.py --report     # Just generate report
    python scripts/run_enrichment.py --skip-links # Skip link extraction

Designed to be run via systemd timer (weekly) or manually after ingestion.
"""

import argparse
import json
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '.')

from modules.enrich.versioned_cleaner import VersionedCleaner
from modules.enrich.url_sanitizer import sanitize_file
from modules.enrich.link_extractor import LinkExtractor


# Risky patterns that cause false positives
RISKY_PATTERNS = ['slack', 'indeed', 'notion', 'monday', 'asana', 'pitch', 'loom']
SPONSOR_SIGNALS = ['sponsor', 'brought to you', 'promo', 'code ', 'trial', 'discount']


def find_false_positives(changes_dir: Path) -> list:
    """Find likely false positives in change records."""
    fps = []

    for f in changes_dir.glob('*.json'):
        try:
            data = json.loads(f.read_text())
            content_id = data.get('content_id', '')
            for r in data.get('removals', []):
                method = r.get('method', '')
                pattern = r.get('pattern', '').lower()
                text = r.get('text', '').lower()

                has_sponsor = any(s in text for s in SPONSOR_SIGNALS)

                if method == 'advertiser' and pattern in RISKY_PATTERNS and not has_sponsor:
                    fps.append({
                        'content_id': content_id,
                        'pattern': pattern,
                        'file': f.name,
                    })
        except:
            pass

    return fps


def get_paths_for_fps(fps: list, db_path: Path) -> list:
    """Get original paths for false positive content."""
    if not fps:
        return []

    content_ids = set(fp['content_id'] for fp in fps)
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


def reclean_fps(paths: list, changes_dir: Path, cleaner: VersionedCleaner) -> int:
    """Re-clean files that had false positives."""
    success = 0
    for content_id, orig_path, content_type in paths:
        try:
            if Path(orig_path).exists():
                cleaner.clean_file(orig_path, content_type, force=True)
                success += 1

                # Remove old change record
                safe_id = content_id.replace(':', '_').replace('/', '_')
                old_record = changes_dir / f'{safe_id}.json'
                if old_record.exists():
                    old_record.unlink()
        except:
            pass
    return success


def generate_report(db_path: Path, changes_dir: Path,
                    sanitize_stats: dict = None, link_stats: dict = None) -> str:
    """Generate markdown report."""
    conn = sqlite3.connect(db_path)

    # Get stats by type
    cursor = conn.execute('''
        SELECT content_type, COUNT(*), SUM(ads_removed), SUM(chars_removed)
        FROM cleaning_records
        GROUP BY content_type
    ''')
    stats = {row[0]: {'files': row[1], 'ads': row[2] or 0, 'chars': row[3] or 0}
             for row in cursor.fetchall()}

    # Count change records
    change_count = len(list(changes_dir.glob('*.json')))

    # Get top patterns
    pattern_counter = Counter()
    for f in list(changes_dir.glob('*.json'))[:500]:
        try:
            data = json.loads(f.read_text())
            for r in data.get('removals', []):
                pattern_counter[r.get('pattern', 'unknown')] += 1
        except:
            pass

    conn.close()

    report = f"""# Atlas Enrichment Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Summary

| Content Type | Files | Ads Removed | Chars Removed |
|--------------|-------|-------------|---------------|
"""

    total_files = total_ads = total_chars = 0
    for ctype, s in sorted(stats.items()):
        report += f"| {ctype} | {s['files']:,} | {s['ads']:,} | {s['chars']:,} |\n"
        total_files += s['files']
        total_ads += s['ads']
        total_chars += s['chars']

    report += f"| **TOTAL** | **{total_files:,}** | **{total_ads:,}** | **{total_chars:,}** |\n"

    # URL Sanitization section
    if sanitize_stats and sanitize_stats.get('urls_sanitized', 0) > 0:
        report += f"""
## URL Sanitization

- Files processed: {sanitize_stats.get('files', 0):,}
- Tracking URLs cleaned: {sanitize_stats.get('urls_sanitized', 0):,}
"""

    # Link Extraction section
    if link_stats and link_stats.get('links_added', 0) > 0:
        report += f"""
## Link Extraction

- Files scanned: {link_stats.get('files_processed', 0):,}
- New links queued: {link_stats.get('links_added', 0):,}
- Link queue: data/enrich/link_queue.db
"""

    report += f"""
## Top Patterns Detected

| Pattern | Count |
|---------|-------|
"""
    for pattern, count in pattern_counter.most_common(15):
        report += f"| {pattern} | {count} |\n"

    report += f"""
## Details

- Change records: {change_count}
- Database: {db_path}
- Clean files: data/clean/
"""

    return report


def main():
    parser = argparse.ArgumentParser(description='Run full Atlas enrichment workflow')
    parser.add_argument('--dry-run', action='store_true', help='Preview only')
    parser.add_argument('--type', choices=['podcasts', 'articles', 'newsletters', 'youtube', 'stratechery', 'all'],
                        default='all', help='Content type to process')
    parser.add_argument('--report', action='store_true', help='Just generate report')
    parser.add_argument('--max-iterations', type=int, default=3, help='Max FP fix iterations')
    parser.add_argument('--force', action='store_true', help='Re-clean everything')
    parser.add_argument('--skip-sanitize', action='store_true', help='Skip URL sanitization')
    parser.add_argument('--skip-links', action='store_true', help='Skip link extraction')
    args = parser.parse_args()

    db_path = Path('data/enrich/enrich.db')
    changes_dir = Path('data/enrich/changes')

    if args.report:
        if db_path.exists():
            print(generate_report(db_path, changes_dir))
        else:
            print('No enrichment data found.')
        return 0

    print('=' * 60)
    print('ATLAS CONTENT ENRICHMENT')
    print('=' * 60)
    print(f'Started: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print()

    cleaner = VersionedCleaner()

    # Step 1: Clean content
    print('STEP 1: Cleaning content')
    print('-' * 40)

    results = {}

    if args.type in ['all', 'podcasts']:
        print('Processing podcasts...')
        stats = cleaner.clean_all_podcasts(dry_run=args.dry_run, force=args.force)
        results['podcasts'] = stats
        print(f"  Podcasts: {stats['cleaned']} cleaned, {stats['ads_found']} ads")

    if args.type in ['all', 'articles']:
        print('Processing articles...')
        stats = cleaner.clean_all_articles(dry_run=args.dry_run, force=args.force)
        results['articles'] = stats
        print(f"  Articles: {stats['cleaned']} cleaned, {stats['ads_found']} ads")

    if args.type in ['all', 'newsletters']:
        print('Processing newsletters...')
        stats = cleaner.clean_all_newsletters(dry_run=args.dry_run, force=args.force)
        results['newsletters'] = stats
        print(f"  Newsletters: {stats['cleaned']} cleaned, {stats['ads_found']} ads")

    if args.type in ['all', 'youtube']:
        print('Processing youtube...')
        stats = cleaner.clean_all_youtube(dry_run=args.dry_run, force=args.force)
        results['youtube'] = stats
        print(f"  YouTube: {stats['cleaned']} cleaned, {stats['ads_found']} ads")

    if args.type in ['all', 'stratechery']:
        print('Processing stratechery...')
        stats = cleaner.clean_all_stratechery(dry_run=args.dry_run, force=args.force)
        results['stratechery'] = stats
        print(f"  Stratechery: {stats['cleaned']} cleaned, {stats['ads_found']} ads")

    if args.dry_run:
        print('\n[DRY RUN] No changes made.')
        return 0

    # Step 2: Find and fix false positives
    print()
    print('STEP 2: Checking for false positives')
    print('-' * 40)

    for iteration in range(args.max_iterations):
        fps = find_false_positives(changes_dir)

        if not fps:
            print(f'  ✅ No false positives detected!')
            break

        print(f'  Found {len(fps)} potential FPs (iteration {iteration + 1})')

        paths = get_paths_for_fps(fps, db_path)
        fixed = reclean_fps(paths, changes_dir, cleaner)
        print(f'  Re-cleaned {fixed} files')

    # Step 3: Sanitize URLs (strip tracking params)
    print()
    print('STEP 3: Sanitizing URLs')
    print('-' * 40)

    sanitize_stats = {'files': 0, 'urls_sanitized': 0}

    if args.skip_sanitize:
        print('  [SKIPPED] --skip-sanitize flag set')
    else:
        clean_dir = Path('data/clean')
        clean_files = list(clean_dir.rglob('*.md'))
        print(f'  Processing {len(clean_files)} clean files...')

        for f in clean_files:
            try:
                found, modified = sanitize_file(f)
                sanitize_stats['files'] += 1
                sanitize_stats['urls_sanitized'] += modified
            except Exception:
                pass

        print(f'  ✅ Sanitized {sanitize_stats["urls_sanitized"]} URLs in {sanitize_stats["files"]} files')

    # Step 4: Extract links for potential ingestion
    print()
    print('STEP 4: Extracting links')
    print('-' * 40)

    link_stats = {'files_processed': 0, 'links_added': 0}

    if args.skip_links:
        print('  [SKIPPED] --skip-links flag set')
    else:
        extractor = LinkExtractor()
        print('  Scanning clean content for high-value links...')
        link_stats = extractor.extract_from_clean()
        print(f'  ✅ Added {link_stats["links_added"]} new links to queue')

        # Show top domains found
        db_stats = extractor.db.get_stats()
        top_domains = list(db_stats.get('top_domains', {}).items())[:5]
        if top_domains:
            print('  Top domains in queue:')
            for domain, count in top_domains:
                print(f'    {count:>5}  {domain}')

    # Step 5: Generate report
    print()
    print('STEP 5: Generating report')
    print('-' * 40)

    report = generate_report(db_path, changes_dir, sanitize_stats, link_stats)
    report_path = Path('data/enrich/reports')
    report_path.mkdir(parents=True, exist_ok=True)

    report_file = report_path / f"enrichment_{datetime.now().strftime('%Y-%m-%d')}.md"
    report_file.write_text(report)
    print(f'  Report saved to: {report_file}')

    # Summary
    print()
    print('=' * 60)
    print('COMPLETE')
    print('=' * 60)

    total_cleaned = sum(r.get('cleaned', 0) for r in results.values())
    total_ads = sum(r.get('ads_found', 0) for r in results.values())

    print(f'Files cleaned: {total_cleaned:,}')
    print(f'Ads removed: {total_ads:,}')
    print(f'Finished: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')

    return 0


if __name__ == '__main__':
    exit(main())
