#!/usr/bin/env python3
"""
URL Fetcher Status Report - Per-domain success/failure breakdown

Usage:
    python scripts/url_status.py           # Full report
    python scripts/url_status.py --brief   # Just summary
    python scripts/url_status.py --json    # JSON output
    python scripts/url_status.py --save    # Save to data/reports/url_status.md
"""

import argparse
import json
from pathlib import Path
from collections import defaultdict
from urllib.parse import urlparse
from dataclasses import dataclass
from typing import List, Dict

STATE_FILE = Path(__file__).parent.parent / "data/url_fetcher_state.json"

@dataclass
class DomainStatus:
    domain: str
    fetched: int
    failed: int
    top_failure_reason: str = ""

    @property
    def total(self) -> int:
        return self.fetched + self.failed

    @property
    def success_rate(self) -> float:
        return (self.fetched / self.total * 100) if self.total > 0 else 0

    @property
    def category(self) -> str:
        if self.failed == 0:
            return "PERFECT"
        elif self.success_rate >= 80:
            return "GOOD"
        elif self.success_rate >= 50:
            return "MIXED"
        elif self.success_rate > 0:
            return "POOR"
        else:
            return "BLOCKED"


def get_url_status() -> List[DomainStatus]:
    """Analyze URL fetcher state by domain."""
    if not STATE_FILE.exists():
        return []

    state = json.loads(STATE_FILE.read_text())

    fetched_by_domain = defaultdict(int)
    failed_by_domain = defaultdict(int)
    failure_reasons = defaultdict(lambda: defaultdict(int))

    for h, info in state.get('fetched', {}).items():
        url = info.get('url', '')
        domain = urlparse(url).netloc.replace('www.', '')
        if domain:
            fetched_by_domain[domain] += 1

    for h, info in state.get('failed', {}).items():
        url = info.get('url', '')
        reason = info.get('reason', 'unknown')[:40]
        domain = urlparse(url).netloc.replace('www.', '')
        if domain:
            failed_by_domain[domain] += 1
            failure_reasons[domain][reason] += 1

    # Combine into results
    all_domains = set(fetched_by_domain.keys()) | set(failed_by_domain.keys())
    results = []

    for domain in all_domains:
        fetched = fetched_by_domain.get(domain, 0)
        failed = failed_by_domain.get(domain, 0)
        reasons = failure_reasons.get(domain, {})
        top_reason = max(reasons.items(), key=lambda x: x[1])[0] if reasons else ""

        results.append(DomainStatus(
            domain=domain,
            fetched=fetched,
            failed=failed,
            top_failure_reason=top_reason
        ))

    return results


def print_report(domains: List[DomainStatus], brief: bool = False):
    """Print formatted status report."""

    # Filter to domains with 5+ URLs
    significant = [d for d in domains if d.total >= 5]

    # Group by category
    perfect = [d for d in significant if d.category == "PERFECT"]
    good = [d for d in significant if d.category == "GOOD"]
    mixed = [d for d in significant if d.category == "MIXED"]
    poor = [d for d in significant if d.category == "POOR"]
    blocked = [d for d in significant if d.category == "BLOCKED"]

    total_fetched = sum(d.fetched for d in domains)
    total_failed = sum(d.failed for d in domains)
    total = total_fetched + total_failed

    print("=" * 70)
    print("URL FETCHER STATUS BY DOMAIN")
    print("=" * 70)
    print()
    print(f"Overall: {total_fetched:,}/{total:,} URLs ({total_fetched/total*100:.1f}% success)")
    print(f"  Perfect (100%):    {len(perfect)} domains")
    print(f"  Good (80-99%):     {len(good)} domains")
    print(f"  Mixed (50-79%):    {len(mixed)} domains")
    print(f"  Poor (1-49%):      {len(poor)} domains")
    print(f"  Blocked (0%):      {len(blocked)} domains")
    print()

    if brief:
        return

    # Blocked (most actionable - consider skipping these)
    if blocked:
        print("-" * 70)
        print("❌ BLOCKED (0% success - consider skipping)")
        print("-" * 70)
        for d in sorted(blocked, key=lambda x: x.failed, reverse=True)[:15]:
            print(f"  {d.domain:40} 0/{d.failed:4}  {d.top_failure_reason}")
        print()

    # Poor
    if poor:
        print("-" * 70)
        print("⚠️  POOR (<50% success - may need cookies/proxy)")
        print("-" * 70)
        for d in sorted(poor, key=lambda x: x.failed, reverse=True)[:15]:
            print(f"  {d.domain:40} {d.fetched:4}/{d.total:4} ({d.success_rate:4.0f}%)  {d.top_failure_reason}")
        print()

    # Mixed
    if mixed:
        print("-" * 70)
        print("🔶 MIXED (50-79% success)")
        print("-" * 70)
        for d in sorted(mixed, key=lambda x: x.total, reverse=True)[:15]:
            print(f"  {d.domain:40} {d.fetched:4}/{d.total:4} ({d.success_rate:4.0f}%)")
        print()

    # Good (show top performers)
    if good:
        print("-" * 70)
        print("✅ GOOD (80%+ success)")
        print("-" * 70)
        for d in sorted(good, key=lambda x: x.fetched, reverse=True)[:20]:
            print(f"  {d.domain:40} {d.fetched:4}/{d.total:4} ({d.success_rate:4.0f}%)")
        print()


def generate_markdown_report(domains: List[DomainStatus]) -> str:
    """Generate markdown report for file output."""
    from datetime import datetime

    significant = [d for d in domains if d.total >= 5]

    perfect = [d for d in significant if d.category == "PERFECT"]
    good = [d for d in significant if d.category == "GOOD"]
    mixed = [d for d in significant if d.category == "MIXED"]
    poor = [d for d in significant if d.category == "POOR"]
    blocked = [d for d in significant if d.category == "BLOCKED"]

    total_fetched = sum(d.fetched for d in domains)
    total_failed = sum(d.failed for d in domains)
    total = total_fetched + total_failed

    lines = []
    lines.append("# URL Fetcher Status by Domain")
    lines.append(f"\n**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    lines.append("## Summary\n")
    lines.append(f"**Overall:** {total_fetched:,}/{total:,} URLs ({total_fetched/total*100:.1f}% success)\n")
    lines.append("| Category | Domains | Description |")
    lines.append("|----------|---------|-------------|")
    lines.append(f"| Perfect | {len(perfect)} | 100% success |")
    lines.append(f"| Good | {len(good)} | 80-99% success |")
    lines.append(f"| Mixed | {len(mixed)} | 50-79% success |")
    lines.append(f"| Poor | {len(poor)} | 1-49% success |")
    lines.append(f"| Blocked | {len(blocked)} | 0% - skip these |")
    lines.append("")

    # Blocked
    if blocked:
        lines.append("## ❌ Blocked (consider skipping)\n")
        lines.append("| Domain | Failed | Reason |")
        lines.append("|--------|--------|--------|")
        for d in sorted(blocked, key=lambda x: x.failed, reverse=True)[:20]:
            lines.append(f"| {d.domain} | {d.failed} | {d.top_failure_reason} |")
        lines.append("")

    # Poor
    if poor:
        lines.append("## ⚠️ Poor (may need cookies/proxy)\n")
        lines.append("| Domain | Success | Total | Rate |")
        lines.append("|--------|---------|-------|------|")
        for d in sorted(poor, key=lambda x: x.failed, reverse=True)[:20]:
            lines.append(f"| {d.domain} | {d.fetched} | {d.total} | {d.success_rate:.0f}% |")
        lines.append("")

    # Good
    if good:
        lines.append("## ✅ Good (working well)\n")
        lines.append("| Domain | Success | Total | Rate |")
        lines.append("|--------|---------|-------|------|")
        for d in sorted(good, key=lambda x: x.fetched, reverse=True)[:30]:
            lines.append(f"| {d.domain} | {d.fetched} | {d.total} | {d.success_rate:.0f}% |")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description='URL fetcher status by domain')
    parser.add_argument('--brief', action='store_true', help='Just show summary')
    parser.add_argument('--json', action='store_true', help='JSON output')
    parser.add_argument('--save', action='store_true', help='Save to data/reports/url_status.md')
    args = parser.parse_args()

    domains = get_url_status()

    if args.save:
        report = generate_markdown_report(domains)
        report_dir = Path(__file__).parent.parent / "data" / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / "url_status.md"
        report_path.write_text(report)
        print(f"Saved to {report_path}")
    elif args.json:
        data = {
            'domains': [
                {
                    'domain': d.domain,
                    'fetched': d.fetched,
                    'failed': d.failed,
                    'total': d.total,
                    'success_rate': round(d.success_rate, 1),
                    'category': d.category,
                    'top_failure_reason': d.top_failure_reason
                }
                for d in domains if d.total >= 5
            ]
        }
        print(json.dumps(data, indent=2))
    else:
        print_report(domains, brief=args.brief)


if __name__ == '__main__':
    main()
