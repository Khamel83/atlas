#!/usr/bin/env python3
"""
Unified CLI for the Atlas link discovery and ingestion pipeline.

Usage:
    python -m modules.links.cli extract-shownotes --all
    python -m modules.links.cli approve --dry-run
    python -m modules.links.cli ingest --drip
    python -m modules.links.cli status
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.links.extractor import LinkExtractor
from modules.links.approval import ApprovalEngine
from modules.links.bridge import LinkBridge
from modules.links.shownotes import ShowNotesExtractor
from modules.links.models import LinkSource


def cmd_extract_shownotes(args):
    """Extract links from podcast show notes (RSS descriptions)."""
    extractor = ShowNotesExtractor()

    print("=" * 60)
    print("EXTRACTING LINKS FROM PODCAST SHOW NOTES")
    print("=" * 60)

    if args.slug:
        print(f"Podcast: {args.slug}")
    else:
        print("Podcast: ALL")

    if args.limit:
        print(f"Limit: {args.limit} episodes")

    print()

    stats = extractor.extract_all(
        podcast_slug=args.slug,
        limit=args.limit
    )

    print(f"\nResults:")
    print(f"  Episodes processed: {stats['episodes_processed']:,}")
    print(f"  Episodes with links: {stats['episodes_with_links']:,}")
    print(f"  Links added: {stats['links_added']:,}")

    if stats['by_podcast'] and len(stats['by_podcast']) <= 20:
        print(f"\nBy podcast:")
        for slug, s in sorted(stats['by_podcast'].items(), key=lambda x: -x[1]['links']):
            print(f"  {slug}: {s['episodes']} episodes, {s['links']} links")


def cmd_extract_file(args):
    """Extract links from a text file."""
    extractor = LinkExtractor()

    filepath = Path(args.file)
    if not filepath.exists():
        print(f"Error: File not found: {filepath}")
        return 1

    text = filepath.read_text(encoding='utf-8')
    content_id = args.content_id or filepath.stem
    source_type = LinkSource(args.source) if args.source in [e.value for e in LinkSource] else LinkSource.UNKNOWN

    added = extractor.extract_and_save(
        text=text,
        content_id=content_id,
        source_path=str(filepath),
        source_type=source_type
    )

    print(f"Extracted {added} links from {filepath}")


def cmd_approve(args):
    """Run approval workflow on pending links."""
    engine = ApprovalEngine()

    print("=" * 60)
    print("LINK APPROVAL WORKFLOW")
    print("=" * 60)

    if args.dry_run:
        print("[DRY RUN] No changes will be made\n")

    stats = engine.run(dry_run=args.dry_run, limit=args.limit or 10000)

    print(f"Processed: {stats['processed']:,}")
    print(f"  Approved: {stats['approved']:,}")
    print(f"  Rejected: {stats['rejected']:,}")
    print(f"  Unchanged: {stats['unchanged']:,}")

    if stats['by_rule']:
        print(f"\nBy rule:")
        for rule, count in sorted(stats['by_rule'].items(), key=lambda x: -x[1]):
            print(f"  {rule}: {count:,}")


def cmd_ingest(args):
    """Bridge approved links to the URL queue for fetching."""
    bridge = LinkBridge()

    print("=" * 60)
    print("LINK INGESTION BRIDGE")
    print("=" * 60)

    if args.dry_run:
        print("[DRY RUN] No changes will be made\n")

    stats = bridge.run(
        limit=args.limit,
        drip=args.drip,
        dry_run=args.dry_run
    )

    print(f"Processed: {stats['processed']:,}")
    print(f"  Added to queue: {stats['added']:,}")
    print(f"  Skipped (duplicate): {stats['skipped_duplicate']:,}")

    if stats['urls'] and len(stats['urls']) <= 20:
        print(f"\nURLs added:")
        for u in stats['urls']:
            print(f"  [{u['score']:.2f}] {u['domain']}")


def cmd_status(args):
    """Show pipeline status and statistics."""
    from modules.links.approval import ApprovalEngine
    from modules.links.bridge import LinkBridge

    engine = ApprovalEngine()
    bridge = LinkBridge()

    print("=" * 60)
    print("LINK PIPELINE STATUS")
    print("=" * 60)

    # Get approval stats
    approval_stats = engine.get_stats()

    print("\nLink Queue:")
    total = sum(approval_stats.get('by_status', {}).values())
    print(f"  Total links: {total:,}")

    for status, count in sorted(approval_stats.get('by_status', {}).items()):
        pct = (count / total * 100) if total > 0 else 0
        print(f"  - {status}: {count:,} ({pct:.1f}%)")

    # Get bridge stats
    bridge_stats = bridge.get_stats()

    print(f"\nIngestion Queue:")
    print(f"  Approved waiting: {bridge_stats['approved_waiting']:,}")
    print(f"  Ingested (24h): {bridge_stats['ingested_24h']:,}")
    print(f"  URL queue file: {bridge_stats['queue_file_urls']:,} URLs")

    if args.verbose and approval_stats.get('by_rule'):
        print(f"\nApproval Rules Applied:")
        for rule, count in sorted(approval_stats['by_rule'].items(), key=lambda x: -x[1]):
            print(f"  {rule}: {count:,}")


def cmd_stats(args):
    """Show detailed statistics."""
    import sqlite3

    db_path = Path('data/enrich/link_queue.db')
    if not db_path.exists():
        print("No link database found")
        return 1

    conn = sqlite3.connect(db_path)

    print("=" * 60)
    print("LINK QUEUE STATISTICS")
    print("=" * 60)

    if args.by_domain:
        print("\nTop Domains (approved):")
        cursor = conn.execute("""
            SELECT domain, COUNT(*) as cnt, AVG(score) as avg_score
            FROM extracted_links
            WHERE status = 'approved'
            GROUP BY domain
            ORDER BY cnt DESC
            LIMIT 30
        """)
        print(f"{'Domain':<40} {'Count':>8} {'Avg Score':>10}")
        print("-" * 60)
        for row in cursor:
            print(f"{row[0]:<40} {row[1]:>8} {row[2]:>10.2f}")

    elif args.by_source:
        print("\nBy Source Type:")
        cursor = conn.execute("""
            SELECT source_type, status, COUNT(*) as cnt
            FROM extracted_links
            GROUP BY source_type, status
            ORDER BY source_type, status
        """)
        current_source = None
        for row in cursor:
            if row[0] != current_source:
                print(f"\n{row[0] or 'unknown'}:")
                current_source = row[0]
            print(f"  {row[1]}: {row[2]:,}")

    else:
        # General stats
        cursor = conn.execute("SELECT COUNT(*) FROM extracted_links")
        total = cursor.fetchone()[0]
        print(f"\nTotal links: {total:,}")

        cursor = conn.execute("SELECT COUNT(DISTINCT domain) FROM extracted_links")
        domains = cursor.fetchone()[0]
        print(f"Unique domains: {domains:,}")

        cursor = conn.execute("""
            SELECT
                CASE
                    WHEN score >= 0.85 THEN 'HIGH (>=0.85)'
                    WHEN score >= 0.60 THEN 'MEDIUM (0.60-0.85)'
                    WHEN score >= 0.40 THEN 'LOW (0.40-0.60)'
                    ELSE 'VERY LOW (<0.40)'
                END as tier,
                COUNT(*)
            FROM extracted_links
            GROUP BY tier
            ORDER BY tier
        """)
        print("\nScore Distribution:")
        for row in cursor:
            pct = (row[1] / total * 100) if total > 0 else 0
            print(f"  {row[0]}: {row[1]:,} ({pct:.1f}%)")

    conn.close()


def main():
    parser = argparse.ArgumentParser(
        description='Atlas Link Discovery and Ingestion Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s extract-shownotes --all           Extract from all podcast show notes
    %(prog)s extract-shownotes --slug acquired  Extract from one podcast
    %(prog)s approve --dry-run                  Preview approval decisions
    %(prog)s approve --apply                    Apply approval rules
    %(prog)s ingest --drip                      Add approved URLs to queue (drip mode)
    %(prog)s status                             Show pipeline status
    %(prog)s stats --by-domain                  Show domain breakdown
        """
    )

    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # extract-shownotes
    p_shownotes = subparsers.add_parser('extract-shownotes', help='Extract links from podcast show notes')
    p_shownotes.add_argument('--all', action='store_true', help='Process all podcasts')
    p_shownotes.add_argument('--slug', type=str, help='Process specific podcast by slug')
    p_shownotes.add_argument('--limit', type=int, help='Limit episodes to process')

    # extract (from file)
    p_extract = subparsers.add_parser('extract', help='Extract links from a text file')
    p_extract.add_argument('--file', required=True, help='File to extract from')
    p_extract.add_argument('--source', default='manual', help='Source type (transcript, article, newsletter, manual)')
    p_extract.add_argument('--content-id', help='Content identifier')

    # approve
    p_approve = subparsers.add_parser('approve', help='Run approval workflow')
    p_approve.add_argument('--dry-run', action='store_true', help='Preview without changes')
    p_approve.add_argument('--apply', action='store_true', help='Apply changes (default without --dry-run)')
    p_approve.add_argument('--limit', type=int, help='Max links to process')

    # ingest
    p_ingest = subparsers.add_parser('ingest', help='Bridge approved links to URL queue')
    p_ingest.add_argument('--dry-run', action='store_true', help='Preview without changes')
    p_ingest.add_argument('--drip', action='store_true', default=True, help='Use drip mode (default)')
    p_ingest.add_argument('--no-drip', action='store_false', dest='drip', help='Disable drip mode')
    p_ingest.add_argument('--limit', type=int, help='Max URLs to add')

    # status
    p_status = subparsers.add_parser('status', help='Show pipeline status')

    # stats
    p_stats = subparsers.add_parser('stats', help='Show detailed statistics')
    p_stats.add_argument('--by-domain', action='store_true', help='Show domain breakdown')
    p_stats.add_argument('--by-source', action='store_true', help='Show source type breakdown')

    args = parser.parse_args()

    # Set up logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    if not args.command:
        parser.print_help()
        return 1

    # Route to command
    commands = {
        'extract-shownotes': cmd_extract_shownotes,
        'extract': cmd_extract_file,
        'approve': cmd_approve,
        'ingest': cmd_ingest,
        'status': cmd_status,
        'stats': cmd_stats,
    }

    return commands[args.command](args) or 0


if __name__ == '__main__':
    sys.exit(main())
