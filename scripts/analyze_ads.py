#!/usr/bin/env python3
"""
Analyze ad detection data from enrich.db.

Usage:
    python scripts/analyze_ads.py              # Full report
    python scripts/analyze_ads.py --top 20     # Top N advertisers
    python scripts/analyze_ads.py --fp         # Focus on false positives
    python scripts/analyze_ads.py --pattern "Squarespace"  # Analyze specific pattern
"""

import argparse
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path


def load_changes(changes_dir: Path, limit: int = None):
    """Load removal records from changes directory."""
    files = list(changes_dir.glob("*.json"))
    if limit:
        files = files[:limit]

    records = []
    for f in files:
        try:
            data = json.loads(f.read_text())
            content_id = data.get("content_id", "")
            for r in data.get("removals", []):
                r["content_id"] = content_id
                records.append(r)
        except Exception:
            pass
    return records


def analyze_stats(conn):
    """Overall statistics."""
    cursor = conn.execute("""
        SELECT
            content_type,
            COUNT(*) as total,
            SUM(ads_removed) as total_ads,
            SUM(chars_removed) as total_chars,
            AVG(percent_removed) as avg_percent
        FROM cleaning_records
        GROUP BY content_type
        ORDER BY total_ads DESC
    """)

    print("=" * 70)
    print("OVERALL STATISTICS")
    print("=" * 70)
    print(f"{'Type':<15} {'Files':>10} {'Ads':>10} {'Chars':>12} {'Avg %':>8}")
    print("-" * 70)

    totals = [0, 0, 0]
    for row in cursor.fetchall():
        print(f"{row[0]:<15} {row[1]:>10,} {row[2] or 0:>10,} {row[3] or 0:>12,} {row[4] or 0:>7.2f}%")
        totals[0] += row[1]
        totals[1] += row[2] or 0
        totals[2] += row[3] or 0

    print("-" * 70)
    print(f"{'TOTAL':<15} {totals[0]:>10,} {totals[1]:>10,} {totals[2]:>12,}")


def analyze_patterns(records, top_n: int = 20):
    """Analyze detection patterns."""
    pattern_counter = Counter()
    method_counter = Counter()
    advertiser_counter = Counter()

    for r in records:
        pattern = r.get("pattern", "unknown")
        method = r.get("method", "unknown")

        pattern_counter[pattern] += 1
        method_counter[method] += 1

        if method == "advertiser":
            advertiser_counter[pattern] += 1

    print("\n" + "=" * 70)
    print("DETECTION METHODS")
    print("=" * 70)
    for method, count in method_counter.most_common():
        pct = count / len(records) * 100
        print(f"  {method:<20} {count:>8,} ({pct:.1f}%)")

    print("\n" + "=" * 70)
    print(f"TOP {top_n} ADVERTISERS")
    print("=" * 70)
    for adv, count in advertiser_counter.most_common(top_n):
        print(f"  {count:>6}x  {adv}")

    print("\n" + "=" * 70)
    print(f"TOP {top_n} KEYWORD PATTERNS")
    print("=" * 70)
    keyword_patterns = [(p, c) for p, c in pattern_counter.most_common(50)
                        if p not in dict(advertiser_counter.most_common(50))]
    for pattern, count in keyword_patterns[:top_n]:
        display = pattern[:50] + "..." if len(pattern) > 50 else pattern
        print(f"  {count:>6}x  {display}")


def analyze_false_positives(records):
    """Find potential false positives."""
    fp_candidates = []

    sponsor_signals = [
        "sponsor", "brought to you", "thanks to", "promo",
        "code ", "offer", "trial", "discount", "% off"
    ]

    for r in records:
        method = r.get("method", "")
        pattern = r.get("pattern", "")
        text = r.get("text", "")
        confidence = r.get("confidence", 0)
        text_lower = text.lower()

        has_sponsor_signal = any(s in text_lower for s in sponsor_signals)

        # Check for likely false positives
        is_fp = False
        fp_reason = ""

        if method == "advertiser":
            pattern_lower = pattern.lower()
            if pattern_lower in ["indeed", "notion", "slack"]:
                if not has_sponsor_signal:
                    is_fp = True
                    fp_reason = f"{pattern} used as common word"

        if method == "url_pattern" and pattern in [r"\?utm_", r"\?ref="]:
            if "my book" in text_lower or "my newsletter" in text_lower:
                is_fp = True
                fp_reason = "Self-promotion, not paid ad"

        if is_fp:
            fp_candidates.append({
                "reason": fp_reason,
                "pattern": pattern,
                "confidence": confidence,
                "text": text[:200],
                "content_id": r.get("content_id", ""),
            })

    print("\n" + "=" * 70)
    print(f"POTENTIAL FALSE POSITIVES ({len(fp_candidates)} found)")
    print("=" * 70)

    # Group by reason
    by_reason = defaultdict(list)
    for fp in fp_candidates:
        by_reason[fp["reason"]].append(fp)

    for reason, items in sorted(by_reason.items(), key=lambda x: -len(x[1])):
        print(f"\n### {reason} ({len(items)} cases)")
        print("-" * 50)
        for item in items[:3]:
            print(f"Content: {item['content_id']}")
            print(f"Text: {item['text']}")
            print()


def analyze_specific_pattern(records, pattern: str):
    """Analyze a specific pattern in detail."""
    matching = [r for r in records if pattern.lower() in r.get("pattern", "").lower()]

    print(f"\n{'=' * 70}")
    print(f"ANALYSIS: '{pattern}' ({len(matching)} detections)")
    print("=" * 70)

    if not matching:
        print("No matches found.")
        return

    # Confidence distribution
    high = sum(1 for r in matching if r.get("confidence", 0) >= 0.9)
    medium = sum(1 for r in matching if 0.7 <= r.get("confidence", 0) < 0.9)
    low = sum(1 for r in matching if r.get("confidence", 0) < 0.7)

    print(f"\nConfidence: high={high}, medium={medium}, low={low}")

    # Sample texts
    print("\nSample detections:")
    print("-" * 50)
    for r in matching[:5]:
        print(f"Confidence: {r.get('confidence', 0):.2f}")
        print(f"Text: {r.get('text', '')[:200]}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Analyze ad detection data")
    parser.add_argument("--top", type=int, default=15, help="Show top N patterns")
    parser.add_argument("--fp", action="store_true", help="Focus on false positives")
    parser.add_argument("--pattern", type=str, help="Analyze specific pattern")
    parser.add_argument("--limit", type=int, help="Limit records to analyze")
    args = parser.parse_args()

    db_path = Path("data/enrich/enrich.db")
    changes_dir = Path("data/enrich/changes")

    if not db_path.exists():
        print("Error: data/enrich/enrich.db not found")
        return 1

    conn = sqlite3.connect(db_path)
    records = load_changes(changes_dir, args.limit)

    print(f"Loaded {len(records):,} removal records from {len(list(changes_dir.glob('*.json'))):,} files")

    # Always show stats
    analyze_stats(conn)

    if args.pattern:
        analyze_specific_pattern(records, args.pattern)
    elif args.fp:
        analyze_false_positives(records)
    else:
        analyze_patterns(records, args.top)

    conn.close()
    return 0


if __name__ == "__main__":
    exit(main())
