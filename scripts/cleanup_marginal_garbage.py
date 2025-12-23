#!/usr/bin/env python3
"""
Cleanup Marginal Garbage Files

Identifies and removes files that are failed fetches pretending to be content:
- YouTube footer HTML (no actual transcript)
- Podcast files with only metadata headers (empty body)
- Article files that are just nav/index pages

Also re-queues URLs for articles that need refetching.

Usage:
    python scripts/cleanup_marginal_garbage.py --dry-run   # Preview what will be deleted
    python scripts/cleanup_marginal_garbage.py --apply     # Actually delete and re-queue
"""

import argparse
import json
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# Patterns that indicate garbage content (not real articles/transcripts)
GARBAGE_PATTERNS = [
    # YouTube footer junk
    r'\[About\].*\[Press\].*\[Copyright\]',
    r'\(C\) 20\d{2} Google LLC',
    r'^\[\]\(/.*YouTube.*\)\[\]',
    r'\*No transcript available',  # YouTube placeholder files

    # Generic navigation/footer patterns
    r'^(About|Contact|Terms|Privacy|Advertise)\s*\|',
    r'All Rights Reserved',
    r'Subscribe to our newsletter',

    # Index/tag page patterns
    r'Latest News, Photos & Videos',
    r'^\s*#\s*\w+\s*\|\s*Latest\s+News',

    # NPR page navigation (not transcripts)
    r'NPR\s+App.*Apple Podcasts.*Spotify',
    r'LISTEN & FOLLOW',
    r'Want to hear.*a week before everyone else',
    r'Sign up for Embedded\+',
    r'plus\.npr\.org/embedded',

    # Podcast ads masquerading as transcripts
    r'Otter\.?\s*AI',
    r'monday sidekick',
    r'Just generate it',
    r'I created this indicator.*buy and sell signals',
    r'click the button on this video',
    r'recorded a \d+-minute video tutorial',

    # Generic ad patterns
    r'Transform(?:ed)? my (?:trading|productivity)',
    r'Try today and take back control',
]

# Compile patterns for efficiency
GARBAGE_REGEXES = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in GARBAGE_PATTERNS]


def is_garbage_content(content: str) -> Tuple[bool, str]:
    """Check if content is garbage (nav, footer, empty body)."""

    # If file has substantial content, it's not garbage even if it has boilerplate
    word_count = len(content.split())
    if word_count > 300:
        return False, ""

    # Check for garbage patterns (only in short files)
    for i, regex in enumerate(GARBAGE_REGEXES):
        if regex.search(content):
            return True, f"matches garbage pattern: {GARBAGE_PATTERNS[i][:50]}"

    # Check for empty body after YAML frontmatter
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            body = parts[2].strip()
            # Body is just whitespace or very short
            if len(body) < 100:
                return True, "empty body after YAML frontmatter"
            # Body is just a title line
            if body.startswith('#') and '\n' not in body.strip():
                return True, "body is just a title, no content"

    # Check for metadata-only podcast files
    if 'transcript_source:' in content and 'fetched_at:' in content:
        # Find content after the YAML block
        match = re.search(r'^---\s*$', content, re.MULTILINE)
        if match:
            after_yaml = content[match.end():].strip()
            # Remove any title line
            lines = [l for l in after_yaml.split('\n') if l.strip() and not l.startswith('#')]
            if len(lines) < 5:
                return True, "podcast metadata only, no transcript"

    return False, ""


def is_too_short(content: str, min_words: int = 100) -> bool:
    """Check if content has too few words."""
    words = len(content.split())
    return words < min_words


def extract_url_from_file(filepath: Path) -> str:
    """Try to extract the original URL from a content file."""
    try:
        content = filepath.read_text(encoding='utf-8', errors='ignore')

        # Look for URL in various formats
        patterns = [
            r'\*\*URL:\*\*\s*(https?://[^\s\n]+)',
            r'^URL:\s*(https?://[^\s\n]+)',
            r'Source:\s*(https?://[^\s\n]+)',
            r'^(https?://[^\s\n]+)$',
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.MULTILINE)
            if match:
                return match.group(1).strip()

        return ""
    except Exception:
        return ""


def analyze_marginal_files(db_path: str) -> Dict[str, List[dict]]:
    """Analyze all marginal files and categorize them.

    AGGRESSIVE MODE: Based on analysis, 100% of marginals are garbage
    (failed fetches, ads, navigation, stubs). We classify everything
    as garbage unless it passes strict content quality checks.
    """

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    results = {
        'garbage': [],      # Delete immediately
        'refetch': [],      # Re-queue URL for fetching
        'keep': [],         # Legitimately short, keep (rare!)
        'unknown': [],      # Need manual review
    }

    cursor = conn.execute("""
        SELECT file_path, issues, word_count
        FROM verifications
        WHERE quality = 'marginal'
    """)

    for row in cursor:
        filepath = Path(row['file_path'])

        if not filepath.exists():
            continue

        try:
            content = filepath.read_text(encoding='utf-8', errors='ignore')
        except Exception as e:
            results['unknown'].append({
                'path': str(filepath),
                'reason': f"read error: {e}",
                'url': ''
            })
            continue

        # Use directory path for classification
        dir_path = str(filepath.parent)
        word_count = len(content.split())

        # Check for garbage patterns first
        is_garbage, reason = is_garbage_content(content)

        if is_garbage:
            results['garbage'].append({
                'path': str(filepath),
                'reason': reason,
                'url': extract_url_from_file(filepath)
            })
            continue

        # YouTube: ALL marginal YouTube files are garbage (no transcript placeholders)
        if '/youtube/' in dir_path:
            results['garbage'].append({
                'path': str(filepath),
                'reason': "YouTube file with no/empty transcript",
                'url': ''
            })
            continue

        # Podcasts: Check for actual transcript content vs ads/metadata
        if '/podcasts/' in dir_path or dir_path.startswith('data/podcasts'):
            # Look for signs of real transcript (speaker labels, dialogue)
            has_speaker = bool(re.search(r'^(?:\*\*)?[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?(?:\*\*)?:', content, re.MULTILINE))
            has_dialogue = content.count('\n\n') > 5  # Real transcripts have many paragraphs

            if word_count > 300 and has_speaker and has_dialogue:
                # Looks like a real transcript
                results['keep'].append({
                    'path': str(filepath),
                    'reason': f"real transcript with {word_count} words",
                    'url': ''
                })
            else:
                # Ads, metadata, or failed fetch
                results['garbage'].append({
                    'path': str(filepath),
                    'reason': f"podcast garbage: {word_count} words, speaker={has_speaker}, dialogue={has_dialogue}",
                    'url': ''
                })
            continue

        # Articles: Try to extract URL for re-fetch, otherwise garbage
        if '/article/' in dir_path or '/articles/' in dir_path:
            url = extract_url_from_file(filepath)
            if url and word_count < 100:
                results['refetch'].append({
                    'path': str(filepath),
                    'reason': row['issues'],
                    'url': url
                })
            else:
                results['garbage'].append({
                    'path': str(filepath),
                    'reason': "article stub/garbage",
                    'url': ''
                })
            continue

        # Newsletters: Most short ones are garbage
        if '/newsletter/' in dir_path:
            if word_count > 200:
                results['keep'].append({
                    'path': str(filepath),
                    'reason': f"newsletter with {word_count} words",
                    'url': ''
                })
            else:
                results['garbage'].append({
                    'path': str(filepath),
                    'reason': "newsletter stub",
                    'url': ''
                })
            continue

        # Stratechery: Try refetch for short files
        if '/stratechery/' in dir_path:
            url = extract_url_from_file(filepath)
            if url:
                results['refetch'].append({
                    'path': str(filepath),
                    'reason': row['issues'],
                    'url': url
                })
            else:
                results['garbage'].append({
                    'path': str(filepath),
                    'reason': "stratechery stub with no URL",
                    'url': ''
                })
            continue

        # Default: Everything else is garbage
        results['garbage'].append({
            'path': str(filepath),
            'reason': f"marginal content ({word_count} words) - treating as garbage",
            'url': ''
        })

    conn.close()
    return results


def delete_garbage_files(files: List[dict], dry_run: bool = True) -> int:
    """Delete garbage files."""
    deleted = 0

    for f in files:
        path = Path(f['path'])
        if path.exists():
            if dry_run:
                print(f"  [DRY RUN] Would delete: {path}")
            else:
                try:
                    path.unlink()
                    deleted += 1
                except Exception as e:
                    print(f"  ERROR deleting {path}: {e}")

    return deleted


def requeue_urls(files: List[dict], queue_file: str, dry_run: bool = True) -> int:
    """Add URLs back to the fetch queue."""
    urls_to_queue = []

    for f in files:
        url = f.get('url', '')
        if url and url.startswith('http'):
            urls_to_queue.append(url)

    # Deduplicate
    urls_to_queue = list(set(urls_to_queue))

    if dry_run:
        print(f"  [DRY RUN] Would queue {len(urls_to_queue)} URLs for refetch")
        for url in urls_to_queue[:10]:
            print(f"    {url[:80]}...")
        if len(urls_to_queue) > 10:
            print(f"    ... and {len(urls_to_queue) - 10} more")
    else:
        # Append to queue file
        queue_path = Path(queue_file)
        with open(queue_path, 'a') as f:
            for url in urls_to_queue:
                f.write(url + '\n')
        print(f"  Queued {len(urls_to_queue)} URLs for refetch")

    return len(urls_to_queue)


def update_verification_db(deleted_paths: List[str], db_path: str, dry_run: bool = True):
    """Remove deleted files from verification database."""
    if dry_run or not deleted_paths:
        return

    conn = sqlite3.connect(db_path)
    for path in deleted_paths:
        conn.execute("DELETE FROM verifications WHERE file_path = ?", (path,))
    conn.commit()
    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Cleanup marginal garbage files")
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying')
    parser.add_argument('--apply', action='store_true', help='Actually delete files and re-queue URLs')
    parser.add_argument('--db', default='data/quality/verification.db', help='Verification database path')
    parser.add_argument('--queue', default='data/url_queue.txt', help='URL queue file path')
    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        print("Must specify --dry-run or --apply")
        return

    dry_run = args.dry_run

    print("=" * 60)
    print("MARGINAL GARBAGE CLEANUP")
    print("=" * 60)
    print(f"\nMode: {'DRY RUN' if dry_run else 'APPLY'}")
    print(f"Database: {args.db}")
    print(f"Queue: {args.queue}\n")

    # Analyze files
    print("Analyzing marginal files...")
    results = analyze_marginal_files(args.db)

    # Summary
    print(f"\n{'=' * 60}")
    print("ANALYSIS RESULTS")
    print(f"{'=' * 60}")
    print(f"  Garbage (delete):     {len(results['garbage']):,}")
    print(f"  Refetch (re-queue):   {len(results['refetch']):,}")
    print(f"  Keep (legitimate):    {len(results['keep']):,}")
    print(f"  Unknown (manual):     {len(results['unknown']):,}")
    print(f"  TOTAL:                {sum(len(v) for v in results.values()):,}")

    # Show samples
    print(f"\n{'=' * 60}")
    print("GARBAGE SAMPLES (will delete)")
    print(f"{'=' * 60}")
    for f in results['garbage'][:5]:
        print(f"  {f['path']}")
        print(f"    Reason: {f['reason']}")

    print(f"\n{'=' * 60}")
    print("REFETCH SAMPLES (will re-queue)")
    print(f"{'=' * 60}")
    for f in results['refetch'][:5]:
        print(f"  {f['path']}")
        print(f"    URL: {f['url'][:60]}..." if f['url'] else "    URL: (none)")

    # Execute
    print(f"\n{'=' * 60}")
    print("EXECUTING CLEANUP")
    print(f"{'=' * 60}")

    print("\n1. Deleting garbage files...")
    deleted = delete_garbage_files(results['garbage'], dry_run)
    print(f"   {'Would delete' if dry_run else 'Deleted'}: {deleted if not dry_run else len(results['garbage'])} files")

    print("\n2. Re-queuing URLs for refetch...")
    queued = requeue_urls(results['refetch'], args.queue, dry_run)

    print("\n3. Updating verification database...")
    if not dry_run:
        deleted_paths = [f['path'] for f in results['garbage']]
        update_verification_db(deleted_paths, args.db, dry_run)
        print(f"   Removed {len(deleted_paths)} entries from DB")
    else:
        print("   [DRY RUN] Would remove entries from DB")

    print(f"\n{'=' * 60}")
    print("COMPLETE")
    print(f"{'=' * 60}")

    if dry_run:
        print("\nRun with --apply to execute these changes")

    # Save report
    report_path = f"data/reports/marginal_cleanup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    Path(report_path).parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'dry_run': dry_run,
            'summary': {k: len(v) for k, v in results.items()},
            'garbage_count': len(results['garbage']),
            'refetch_count': len(results['refetch']),
        }, f, indent=2)
    print(f"\nReport saved: {report_path}")


if __name__ == '__main__':
    main()
