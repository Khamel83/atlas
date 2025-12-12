#!/usr/bin/env python3
"""
Analyze the link queue to evaluate extracted URLs for potential ingestion.

Generates insights about:
- Domain distribution (what sources are most linked?)
- Score distribution (how many are high-quality?)
- Content categories (articles, research, etc.)
- Source content (which podcasts/articles link the most?)
- Sample URLs at each tier for manual review

Usage:
    python scripts/analyze_link_queue.py              # Full analysis
    python scripts/analyze_link_queue.py --summary    # Quick summary
    python scripts/analyze_link_queue.py --samples    # Show sample URLs
    python scripts/analyze_link_queue.py --export     # Export high-value to CSV
"""

import argparse
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

DB_PATH = Path('data/enrich/link_queue.db')


def get_summary(conn):
    """Get quick summary stats."""
    stats = {}

    # Total URLs
    cursor = conn.execute("SELECT COUNT(*) FROM extracted_links")
    stats['total'] = cursor.fetchone()[0]

    # By status
    cursor = conn.execute("""
        SELECT status, COUNT(*) FROM extracted_links GROUP BY status
    """)
    stats['by_status'] = dict(cursor.fetchall())

    # By score tier
    cursor = conn.execute("""
        SELECT
            CASE
                WHEN score >= 0.8 THEN 'HIGH (0.8+)'
                WHEN score >= 0.6 THEN 'MEDIUM (0.6-0.8)'
                WHEN score >= 0.4 THEN 'LOW (0.4-0.6)'
                ELSE 'VERY LOW (<0.4)'
            END as tier,
            COUNT(*)
        FROM extracted_links
        GROUP BY tier
        ORDER BY tier
    """)
    stats['by_score'] = dict(cursor.fetchall())

    # By category
    cursor = conn.execute("""
        SELECT category, COUNT(*) FROM extracted_links GROUP BY category
    """)
    stats['by_category'] = dict(cursor.fetchall())

    # Unique domains
    cursor = conn.execute("SELECT COUNT(DISTINCT domain) FROM extracted_links")
    stats['unique_domains'] = cursor.fetchone()[0]

    return stats


def get_domain_analysis(conn, limit=50):
    """Analyze most-linked domains."""
    cursor = conn.execute("""
        SELECT domain,
               COUNT(*) as count,
               AVG(score) as avg_score,
               MAX(score) as max_score
        FROM extracted_links
        GROUP BY domain
        ORDER BY count DESC
        LIMIT ?
    """, (limit,))
    return cursor.fetchall()


def get_source_analysis(conn, limit=30):
    """Analyze which source content links the most."""
    cursor = conn.execute("""
        SELECT source_content_id,
               COUNT(*) as link_count,
               AVG(score) as avg_score
        FROM extracted_links
        GROUP BY source_content_id
        ORDER BY link_count DESC
        LIMIT ?
    """, (limit,))
    return cursor.fetchall()


def get_high_value_samples(conn, min_score=0.8, limit=20):
    """Get sample high-value URLs."""
    cursor = conn.execute("""
        SELECT url, domain, score, category, anchor_text
        FROM extracted_links
        WHERE score >= ? AND status = 'pending'
        ORDER BY score DESC
        LIMIT ?
    """, (min_score, limit))
    return cursor.fetchall()


def get_domain_samples(conn, domain, limit=10):
    """Get sample URLs from a specific domain."""
    cursor = conn.execute("""
        SELECT url, score, category, anchor_text, source_content_id
        FROM extracted_links
        WHERE domain = ?
        ORDER BY score DESC
        LIMIT ?
    """, (domain, limit))
    return cursor.fetchall()


def export_high_value(conn, min_score=0.7, output_path='data/enrich/high_value_links.csv'):
    """Export high-value URLs to CSV for review."""
    import csv

    cursor = conn.execute("""
        SELECT url, domain, score, category, anchor_text, source_content_id
        FROM extracted_links
        WHERE score >= ? AND status = 'pending'
        ORDER BY score DESC
    """, (min_score,))

    rows = cursor.fetchall()

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['url', 'domain', 'score', 'category', 'anchor_text', 'source'])
        writer.writerows(rows)

    return len(rows), output_path


def analyze_duplicate_content(conn):
    """Find URLs linked from multiple sources (consensus = valuable)."""
    cursor = conn.execute("""
        SELECT url, domain, COUNT(DISTINCT source_content_id) as source_count,
               AVG(score) as avg_score
        FROM extracted_links
        GROUP BY url
        HAVING source_count > 1
        ORDER BY source_count DESC
        LIMIT 50
    """)
    return cursor.fetchall()


def main():
    parser = argparse.ArgumentParser(description='Analyze link queue')
    parser.add_argument('--summary', action='store_true', help='Quick summary only')
    parser.add_argument('--domains', action='store_true', help='Domain analysis')
    parser.add_argument('--sources', action='store_true', help='Source content analysis')
    parser.add_argument('--samples', action='store_true', help='Show sample URLs')
    parser.add_argument('--duplicates', action='store_true', help='URLs linked multiple times')
    parser.add_argument('--export', action='store_true', help='Export high-value to CSV')
    parser.add_argument('--min-score', type=float, default=0.7, help='Min score for export')
    parser.add_argument('--domain', type=str, help='Analyze specific domain')
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}")
        return 1

    # Use URI mode for read-only access with timeout
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=30.0)

    # Always show summary
    print("=" * 70)
    print("LINK QUEUE ANALYSIS")
    print("=" * 70)

    stats = get_summary(conn)
    print(f"\nTotal URLs: {stats['total']:,}")
    print(f"Unique domains: {stats['unique_domains']:,}")

    print("\nBy Status:")
    for status, count in sorted(stats['by_status'].items()):
        print(f"  {status}: {count:,}")

    print("\nBy Score Tier:")
    for tier, count in sorted(stats['by_score'].items()):
        pct = count / stats['total'] * 100
        print(f"  {tier}: {count:,} ({pct:.1f}%)")

    print("\nBy Category:")
    for cat, count in sorted(stats['by_category'].items(), key=lambda x: -x[1]):
        pct = count / stats['total'] * 100
        print(f"  {cat}: {count:,} ({pct:.1f}%)")

    if args.summary:
        conn.close()
        return 0

    # Domain analysis
    if args.domains or not any([args.sources, args.samples, args.duplicates, args.export, args.domain]):
        print("\n" + "=" * 70)
        print("TOP DOMAINS")
        print("=" * 70)
        domains = get_domain_analysis(conn)
        print(f"\n{'Domain':<35} {'Count':>8} {'Avg Score':>10} {'Max Score':>10}")
        print("-" * 70)
        for domain, count, avg_score, max_score in domains[:30]:
            print(f"{domain:<35} {count:>8,} {avg_score:>10.2f} {max_score:>10.2f}")

    # Source analysis
    if args.sources:
        print("\n" + "=" * 70)
        print("TOP LINKING SOURCES")
        print("=" * 70)
        sources = get_source_analysis(conn)
        print(f"\n{'Source Content ID':<50} {'Links':>8} {'Avg Score':>10}")
        print("-" * 70)
        for source, count, avg in sources:
            print(f"{source[:50]:<50} {count:>8,} {avg:>10.2f}")

    # Sample URLs
    if args.samples:
        print("\n" + "=" * 70)
        print("HIGH-VALUE SAMPLES (score >= 0.8)")
        print("=" * 70)
        samples = get_high_value_samples(conn)
        for url, domain, score, category, anchor in samples:
            print(f"\n[{score:.2f}] {category} | {domain}")
            print(f"  URL: {url[:80]}...")
            if anchor:
                print(f"  Anchor: {anchor[:60]}")

    # Duplicate analysis
    if args.duplicates:
        print("\n" + "=" * 70)
        print("MULTI-SOURCE LINKS (consensus = valuable)")
        print("=" * 70)
        dups = analyze_duplicate_content(conn)
        print(f"\n{'URL':<50} {'Sources':>8} {'Avg Score':>10}")
        print("-" * 70)
        for url, domain, sources, avg in dups[:30]:
            print(f"{url[:50]:<50} {sources:>8} {avg:>10.2f}")

    # Specific domain
    if args.domain:
        print("\n" + "=" * 70)
        print(f"DOMAIN: {args.domain}")
        print("=" * 70)
        samples = get_domain_samples(conn, args.domain)
        for url, score, category, anchor, source in samples:
            print(f"\n[{score:.2f}] {category}")
            print(f"  URL: {url[:80]}...")
            if anchor:
                print(f"  Anchor: {anchor[:60]}")
            print(f"  Source: {source}")

    # Export
    if args.export:
        count, path = export_high_value(conn, args.min_score)
        print(f"\nExported {count:,} high-value URLs to: {path}")

    conn.close()
    return 0


if __name__ == '__main__':
    exit(main())
