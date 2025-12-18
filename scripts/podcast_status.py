#!/usr/bin/env python3
"""
Podcast Status Report - Per-podcast transcript coverage

Usage:
    python scripts/podcast_status.py           # Full report
    python scripts/podcast_status.py --brief   # Just summary
    python scripts/podcast_status.py --json    # JSON output
"""

import argparse
import json
import sqlite3
from pathlib import Path
from dataclasses import dataclass
from typing import List

DB_PATH = Path(__file__).parent.parent / "data/podcasts/atlas_podcasts.db"

@dataclass
class PodcastStatus:
    slug: str
    fetched: int
    pending: int
    failed: int
    total: int

    @property
    def pct(self) -> float:
        return (self.fetched / self.total * 100) if self.total > 0 else 0

    @property
    def category(self) -> str:
        if self.pending == 0 and self.failed == 0:
            return "COMPLETE"
        elif self.pending > 0:
            return "PROCESSING"
        elif self.fetched == 0:
            return "NO_SOURCE"
        else:
            return "PARTIAL"

    @property
    def status_line(self) -> str:
        if self.category == "COMPLETE":
            return f"✅ {self.fetched}/{self.total}"
        elif self.category == "PROCESSING":
            return f"⏳ {self.fetched}/{self.total} ({self.pending} pending)"
        elif self.category == "NO_SOURCE":
            return f"❌ 0/{self.total} (need MacWhisper)"
        else:
            return f"⚠️  {self.fetched}/{self.total} ({self.failed} failed)"


def get_podcast_status() -> List[PodcastStatus]:
    """Get status for all podcasts."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT
            p.slug,
            SUM(CASE WHEN e.transcript_status = 'fetched' THEN 1 ELSE 0 END),
            SUM(CASE WHEN e.transcript_status = 'unknown' THEN 1 ELSE 0 END),
            SUM(CASE WHEN e.transcript_status = 'failed' THEN 1 ELSE 0 END),
            SUM(CASE WHEN e.transcript_status NOT IN ('excluded') THEN 1 ELSE 0 END)
        FROM episodes e
        JOIN podcasts p ON e.podcast_id = p.id
        WHERE e.transcript_status != 'excluded'
        GROUP BY p.slug
        ORDER BY p.slug
    """)

    results = []
    for row in cur.fetchall():
        results.append(PodcastStatus(
            slug=row[0],
            fetched=row[1] or 0,
            pending=row[2] or 0,
            failed=row[3] or 0,
            total=row[4] or 0
        ))

    conn.close()
    return results


def print_report(podcasts: List[PodcastStatus], brief: bool = False):
    """Print formatted status report."""

    # Group by category
    complete = [p for p in podcasts if p.category == "COMPLETE"]
    processing = [p for p in podcasts if p.category == "PROCESSING"]
    partial = [p for p in podcasts if p.category == "PARTIAL"]
    no_source = [p for p in podcasts if p.category == "NO_SOURCE"]

    total_fetched = sum(p.fetched for p in podcasts)
    total_episodes = sum(p.total for p in podcasts)
    total_pending = sum(p.pending for p in podcasts)
    total_failed = sum(p.failed for p in podcasts)

    print("=" * 60)
    print("PODCAST TRANSCRIPT STATUS")
    print("=" * 60)
    print()
    print(f"Overall: {total_fetched:,}/{total_episodes:,} episodes ({total_fetched/total_episodes*100:.1f}%)")
    print(f"  Complete:   {len(complete)} podcasts")
    print(f"  Processing: {len(processing)} podcasts ({total_pending} episodes pending)")
    print(f"  Partial:    {len(partial)} podcasts ({total_failed} failed, need alt source)")
    print(f"  No source:  {len(no_source)} podcasts (need MacWhisper)")
    print()

    if brief:
        return

    # Processing (most actionable)
    if processing:
        print("-" * 60)
        print("⏳ PROCESSING (being fetched now)")
        print("-" * 60)
        for p in sorted(processing, key=lambda x: x.pending, reverse=True):
            print(f"  {p.slug:40} {p.status_line}")
        print()

    # Partial (have some, missing some)
    if partial:
        print("-" * 60)
        print("⚠️  PARTIAL (some failed, may need MacWhisper)")
        print("-" * 60)
        for p in sorted(partial, key=lambda x: x.failed, reverse=True):
            reason = ""
            if p.slug in ('asianometry', 'dithering'):
                reason = " [PAYWALLED]"
            elif p.slug == 'against-the-rules-with-michael-lewis':
                reason = " [NO ONLINE SOURCE]"
            print(f"  {p.slug:40} {p.status_line}{reason}")
        print()

    # No source (all failed)
    if no_source:
        print("-" * 60)
        print("❌ NO SOURCE (need MacWhisper for all)")
        print("-" * 60)
        for p in sorted(no_source, key=lambda x: x.total, reverse=True):
            print(f"  {p.slug:40} {p.status_line}")
        print()

    # Complete (good news at the end)
    if complete:
        print("-" * 60)
        print("✅ COMPLETE")
        print("-" * 60)
        for p in sorted(complete, key=lambda x: x.fetched, reverse=True):
            print(f"  {p.slug:40} {p.fetched} episodes")
        print()


def generate_markdown_report(podcasts: List[PodcastStatus]) -> str:
    """Generate markdown report for file output."""
    from datetime import datetime

    lines = []
    lines.append("# Podcast Transcript Status")
    lines.append(f"\n**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    # Summary
    complete = [p for p in podcasts if p.category == "COMPLETE"]
    processing = [p for p in podcasts if p.category == "PROCESSING"]
    partial = [p for p in podcasts if p.category == "PARTIAL"]
    no_source = [p for p in podcasts if p.category == "NO_SOURCE"]

    total_fetched = sum(p.fetched for p in podcasts)
    total_episodes = sum(p.total for p in podcasts)
    total_pending = sum(p.pending for p in podcasts)
    total_failed = sum(p.failed for p in podcasts)

    lines.append("## Summary\n")
    lines.append(f"**Overall:** {total_fetched:,}/{total_episodes:,} episodes ({total_fetched/total_episodes*100:.1f}%)\n")
    lines.append(f"| Category | Podcasts | Episodes |")
    lines.append(f"|----------|----------|----------|")
    lines.append(f"| Complete | {len(complete)} | - |")
    lines.append(f"| Processing | {len(processing)} | {total_pending} pending |")
    lines.append(f"| Partial | {len(partial)} | {total_failed} failed |")
    lines.append(f"| No Source | {len(no_source)} | need MacWhisper |")
    lines.append("")

    # Processing
    if processing:
        lines.append("## ⏳ Processing (being fetched now)\n")
        lines.append("| Podcast | Progress | Pending |")
        lines.append("|---------|----------|---------|")
        for p in sorted(processing, key=lambda x: x.pending, reverse=True):
            lines.append(f"| {p.slug} | {p.fetched}/{p.total} | {p.pending} |")
        lines.append("")

    # Partial
    if partial:
        lines.append("## ⚠️ Partial (some failed, may need MacWhisper)\n")
        lines.append("| Podcast | Progress | Failed | Notes |")
        lines.append("|---------|----------|--------|-------|")
        for p in sorted(partial, key=lambda x: x.failed, reverse=True):
            note = ""
            if p.slug in ('asianometry', 'dithering'):
                note = "PAYWALLED"
            elif p.slug == 'against-the-rules-with-michael-lewis':
                note = "NO ONLINE SOURCE"
            lines.append(f"| {p.slug} | {p.fetched}/{p.total} | {p.failed} | {note} |")
        lines.append("")

    # No source
    if no_source:
        lines.append("## ❌ No Source (need MacWhisper for all)\n")
        lines.append("| Podcast | Episodes |")
        lines.append("|---------|----------|")
        for p in sorted(no_source, key=lambda x: x.total, reverse=True):
            lines.append(f"| {p.slug} | {p.total} |")
        lines.append("")

    # Complete
    if complete:
        lines.append("## ✅ Complete\n")
        lines.append("| Podcast | Episodes |")
        lines.append("|---------|----------|")
        for p in sorted(complete, key=lambda x: x.fetched, reverse=True):
            lines.append(f"| {p.slug} | {p.fetched} |")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description='Podcast transcript status')
    parser.add_argument('--brief', action='store_true', help='Just show summary')
    parser.add_argument('--json', action='store_true', help='JSON output')
    parser.add_argument('--save', action='store_true', help='Save to data/reports/podcast_status.md')
    args = parser.parse_args()

    podcasts = get_podcast_status()

    if args.save:
        report = generate_markdown_report(podcasts)
        report_dir = Path(__file__).parent.parent / "data" / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / "podcast_status.md"
        report_path.write_text(report)
        print(f"Saved to {report_path}")
    elif args.json:
        data = {
            'podcasts': [
                {
                    'slug': p.slug,
                    'fetched': p.fetched,
                    'pending': p.pending,
                    'failed': p.failed,
                    'total': p.total,
                    'pct': round(p.pct, 1),
                    'category': p.category
                }
                for p in podcasts
            ],
            'summary': {
                'total_fetched': sum(p.fetched for p in podcasts),
                'total_episodes': sum(p.total for p in podcasts),
                'total_pending': sum(p.pending for p in podcasts),
                'total_failed': sum(p.failed for p in podcasts),
                'complete_podcasts': len([p for p in podcasts if p.category == "COMPLETE"]),
                'processing_podcasts': len([p for p in podcasts if p.category == "PROCESSING"]),
                'partial_podcasts': len([p for p in podcasts if p.category == "PARTIAL"]),
                'no_source_podcasts': len([p for p in podcasts if p.category == "NO_SOURCE"])
            }
        }
        print(json.dumps(data, indent=2))
    else:
        print_report(podcasts, brief=args.brief)


if __name__ == '__main__':
    main()
