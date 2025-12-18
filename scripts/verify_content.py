#!/usr/bin/env python3
"""
Atlas Content Verification - Comprehensive quality scan of all content.

Scans ALL content (articles, podcasts, newsletters) and produces a verified report.

Usage:
    python scripts/verify_content.py                    # Full scan
    python scripts/verify_content.py --type podcasts    # Just podcasts
    python scripts/verify_content.py --quick            # Quick summary only
    python scripts/verify_content.py --report           # Generate markdown report
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.quality import ContentVerifier, QualityLevel


# Content locations to scan
CONTENT_SOURCES = {
    'podcasts': {
        'paths': ['data/podcasts'],
        'pattern': '**/*.md',
        'type': 'transcript',
        'description': 'Podcast transcripts',
    },
    'articles': {
        'paths': ['data/articles'],
        'pattern': '**/*.md',
        'type': 'article',
        'description': 'Fetched articles by domain',
    },
    'content_articles': {
        'paths': ['data/content/article'],
        'pattern': '**/content.md',
        'type': 'article',
        'description': 'Articles from URL fetcher',
    },
    'newsletters': {
        'paths': ['data/content/newsletter'],
        'pattern': '**/content.md',
        'type': 'newsletter',
        'description': 'Newsletter content',
    },
    'stratechery_articles': {
        'paths': ['data/stratechery/articles'],
        'pattern': '*.md',
        'type': 'article',
        'description': 'Stratechery articles',
    },
    'stratechery_podcasts': {
        'paths': ['data/stratechery/podcasts'],
        'pattern': '*.md',
        'type': 'transcript',
        'description': 'Stratechery podcasts',
    },
    'clean_content': {
        'paths': ['data/clean'],
        'pattern': '**/*.md',
        'type': 'auto',
        'description': 'Cleaned/enriched content',
    },
}


def scan_source(verifier: ContentVerifier, source_name: str, source_config: Dict,
               verbose: bool = False) -> Dict[str, Any]:
    """Scan a single content source."""
    results = {
        'name': source_name,
        'description': source_config['description'],
        'total': 0,
        'good': 0,
        'marginal': 0,
        'bad': 0,
        'bad_files': [],
    }

    for base_path in source_config['paths']:
        base = Path(base_path)
        if not base.exists():
            continue

        for file_path in base.rglob(source_config['pattern']):
            if not file_path.is_file():
                continue

            result = verifier.verify_file(file_path, source_config['type'])
            verifier.save_result(result, source_config['type'])

            results['total'] += 1

            if result.quality == QualityLevel.GOOD:
                results['good'] += 1
            elif result.quality == QualityLevel.MARGINAL:
                results['marginal'] += 1
            else:
                results['bad'] += 1
                # Keep track of bad files (limit to first 100)
                if len(results['bad_files']) < 100:
                    results['bad_files'].append({
                        'path': str(file_path),
                        'issues': result.issues,
                        'score': result.score,
                    })

            if verbose and results['total'] % 500 == 0:
                print(f"  Scanned {results['total']} files...", flush=True)

    return results


def print_summary(all_results: List[Dict], show_problems: int = 10):
    """Print verification summary."""
    print("\n" + "=" * 60)
    print("ATLAS CONTENT VERIFICATION REPORT")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    total_files = 0
    total_good = 0
    total_marginal = 0
    total_bad = 0
    all_bad_files = []

    for result in all_results:
        if result['total'] == 0:
            continue

        good_pct = (result['good'] / result['total'] * 100) if result['total'] > 0 else 0
        print(f"\n{result['description'].upper()}: {result['total']:,} files")
        print(f"  Good:     {result['good']:,} ({good_pct:.1f}%)")
        if result['marginal'] > 0:
            print(f"  Marginal: {result['marginal']:,}")
        if result['bad'] > 0:
            print(f"  Bad:      {result['bad']:,}")

        total_files += result['total']
        total_good += result['good']
        total_marginal += result['marginal']
        total_bad += result['bad']
        all_bad_files.extend(result['bad_files'])

    # Overall summary
    if total_files > 0:
        print("\n" + "-" * 60)
        print(f"OVERALL: {total_files:,} files verified")
        good_pct = total_good / total_files * 100
        print(f"  Good:     {total_good:,} ({good_pct:.1f}%)")
        if total_marginal > 0:
            marginal_pct = total_marginal / total_files * 100
            print(f"  Marginal: {total_marginal:,} ({marginal_pct:.1f}%)")
        if total_bad > 0:
            bad_pct = total_bad / total_files * 100
            print(f"  Bad:      {total_bad:,} ({bad_pct:.1f}%)")

    # Show problem files
    if all_bad_files and show_problems > 0:
        print(f"\n{'='*60}")
        print(f"TOP {min(show_problems, len(all_bad_files))} PROBLEMS:")
        print("-" * 60)
        for bf in all_bad_files[:show_problems]:
            print(f"  {bf['path']}")
            for issue in bf['issues'][:2]:
                print(f"    - {issue}")

    print("\n" + "=" * 60)

    return {
        'total': total_files,
        'good': total_good,
        'marginal': total_marginal,
        'bad': total_bad,
        'good_pct': round(good_pct, 1) if total_files > 0 else 0,
    }


def generate_report(all_results: List[Dict], output_path: Path):
    """Generate markdown report."""
    with open(output_path, 'w') as f:
        f.write(f"# Atlas Content Verification Report\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # Summary table
        f.write("## Summary\n\n")
        f.write("| Content Type | Total | Good | Marginal | Bad | Quality Rate |\n")
        f.write("|--------------|-------|------|----------|-----|-------------|\n")

        total_files = 0
        total_good = 0

        for result in all_results:
            if result['total'] == 0:
                continue
            good_pct = result['good'] / result['total'] * 100 if result['total'] > 0 else 0
            f.write(f"| {result['description']} | {result['total']:,} | {result['good']:,} | ")
            f.write(f"{result['marginal']:,} | {result['bad']:,} | {good_pct:.1f}% |\n")
            total_files += result['total']
            total_good += result['good']

        overall_pct = total_good / total_files * 100 if total_files > 0 else 0
        f.write(f"| **TOTAL** | **{total_files:,}** | **{total_good:,}** | - | - | **{overall_pct:.1f}%** |\n\n")

        # Problem files section
        all_bad = []
        for result in all_results:
            all_bad.extend(result['bad_files'])

        if all_bad:
            f.write("## Problem Files\n\n")
            f.write(f"Found {len(all_bad)} files with quality issues:\n\n")

            # Group by issue type
            by_issue = defaultdict(list)
            for bf in all_bad:
                for issue in bf['issues']:
                    by_issue[issue.split(':')[0]].append(bf['path'])

            for issue_type, paths in sorted(by_issue.items(), key=lambda x: -len(x[1])):
                f.write(f"### {issue_type} ({len(paths)} files)\n\n")
                for path in paths[:10]:
                    f.write(f"- `{path}`\n")
                if len(paths) > 10:
                    f.write(f"- ... and {len(paths) - 10} more\n")
                f.write("\n")

    print(f"\nReport saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description='Atlas Content Verification')
    parser.add_argument('--type', '-t', choices=list(CONTENT_SOURCES.keys()) + ['all'],
                       default='all', help='Content type to verify')
    parser.add_argument('--quick', '-q', action='store_true',
                       help='Quick summary without saving to database')
    parser.add_argument('--report', '-r', action='store_true',
                       help='Generate markdown report')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Show progress during scan')
    parser.add_argument('--problems', '-p', type=int, default=10,
                       help='Number of problem files to show')
    parser.add_argument('--json', '-j', action='store_true',
                       help='Output JSON instead of text')
    args = parser.parse_args()

    verifier = ContentVerifier()

    # Determine which sources to scan
    if args.type == 'all':
        sources_to_scan = list(CONTENT_SOURCES.items())
    else:
        sources_to_scan = [(args.type, CONTENT_SOURCES[args.type])]

    print(f"Starting Atlas Content Verification...")
    print(f"Scanning: {', '.join(s[0] for s in sources_to_scan)}")

    all_results = []
    for source_name, source_config in sources_to_scan:
        print(f"\nScanning {source_config['description']}...", flush=True)
        result = scan_source(verifier, source_name, source_config, verbose=args.verbose)
        all_results.append(result)
        print(f"  Found {result['total']} files: {result['good']} good, {result['bad']} bad")

    if args.json:
        summary = print_summary(all_results, show_problems=0)
        output = {
            'timestamp': datetime.now().isoformat(),
            'summary': summary,
            'by_source': all_results,
        }
        print(json.dumps(output, indent=2))
    else:
        print_summary(all_results, show_problems=args.problems)

    if args.report:
        report_dir = Path('data/reports')
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / f"quality_{datetime.now().strftime('%Y-%m-%d')}.md"
        generate_report(all_results, report_path)

    # Return exit code based on quality
    stats = verifier.get_stats()
    total = stats.get('total', 0)
    bad = stats.get('by_quality', {}).get('bad', 0)
    if total > 0 and bad / total > 0.1:  # More than 10% bad
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
