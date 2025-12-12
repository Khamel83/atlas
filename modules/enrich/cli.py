"""
CLI for Atlas Enrich module.

Commands:
    clean       Clean a single file or stdin
    batch       Process multiple files
    scan        Scan content for ads (detect only)
    stats       Show processing statistics

Examples:
    # Clean a podcast transcript
    python -m modules.enrich.cli clean transcript.md --type podcast

    # Scan for ads without removing
    python -m modules.enrich.cli scan transcript.md --type podcast

    # Batch process all transcripts
    python -m modules.enrich.cli batch data/podcasts/*/transcripts/*.md --type podcast

    # Process from stdin
    cat article.md | python -m modules.enrich.cli clean --type article
"""

import argparse
import sys
import json
import logging
from pathlib import Path
from typing import List

from .ad_stripper import AdStripper, ContentType
from .content_cleaner import ContentCleaner


def cmd_clean(args):
    """Clean content (remove ads, normalize)."""
    cleaner = ContentCleaner(
        strip_ads=not args.no_ads,
        ad_confidence=args.confidence,
    )

    # Read input
    if args.file and args.file != "-":
        text = Path(args.file).read_text()
    else:
        text = sys.stdin.read()

    result = cleaner.clean(text, args.type)

    if args.output:
        Path(args.output).write_text(result.cleaned_text)
        print(f"Wrote cleaned content to {args.output}", file=sys.stderr)
    else:
        print(result.cleaned_text)

    if args.verbose:
        print(f"\n--- Stats ---", file=sys.stderr)
        print(f"Ads removed: {result.ads_removed}", file=sys.stderr)
        print(f"Chars removed: {result.ad_chars_removed} ({result.ad_percent_removed:.1f}%)", file=sys.stderr)
        print(f"Quality score: {result.quality_score:.2f}", file=sys.stderr)


def cmd_scan(args):
    """Scan content for ads (detect only, no modification)."""
    stripper = AdStripper(min_confidence=args.confidence)

    # Read input
    if args.file and args.file != "-":
        text = Path(args.file).read_text()
    else:
        text = sys.stdin.read()

    content_type = ContentType(args.type)
    detections = stripper.detect(text, content_type)

    if args.json:
        output = [
            {
                "start": d.start_char,
                "end": d.end_char,
                "method": d.method.value,
                "confidence": d.confidence,
                "pattern": d.matched_pattern,
                "text_preview": d.text[:100] + "..." if len(d.text) > 100 else d.text,
            }
            for d in detections
        ]
        print(json.dumps(output, indent=2))
    else:
        print(f"Found {len(detections)} potential ad segments:\n")
        for i, d in enumerate(detections, 1):
            print(f"{i}. [{d.method.value}] confidence={d.confidence:.2f}")
            print(f"   Chars {d.start_char}-{d.end_char} ({d.length} chars)")
            if d.matched_pattern:
                print(f"   Pattern: {d.matched_pattern}")
            print(f"   Preview: {d.text[:80]}...")
            print()

        total_chars = sum(d.length for d in detections)
        print(f"Total: {total_chars} chars would be removed ({total_chars/len(text)*100:.1f}% of content)")


def cmd_batch(args):
    """Batch process multiple files."""
    cleaner = ContentCleaner(
        strip_ads=not args.no_ads,
        ad_confidence=args.confidence,
    )

    files = []
    for pattern in args.files:
        if "*" in pattern:
            files.extend(Path(".").glob(pattern))
        else:
            files.append(Path(pattern))

    print(f"Processing {len(files)} files...")

    results = []
    for filepath in files:
        if not filepath.exists():
            print(f"  SKIP: {filepath} (not found)")
            continue

        text = filepath.read_text()
        result = cleaner.clean(text, args.type)

        if args.in_place:
            filepath.write_text(result.cleaned_text)
            action = "CLEANED"
        else:
            action = "SCANNED"

        if result.ads_removed > 0 or args.verbose:
            print(f"  {action}: {filepath.name} - {result.ads_removed} ads, "
                  f"{result.ad_percent_removed:.1f}% removed, "
                  f"quality={result.quality_score:.2f}")

        results.append({
            "file": str(filepath),
            "ads_removed": result.ads_removed,
            "chars_removed": result.ad_chars_removed,
            "percent_removed": result.ad_percent_removed,
            "quality_score": result.quality_score,
        })

    # Summary
    total_ads = sum(r["ads_removed"] for r in results)
    total_chars = sum(r["chars_removed"] for r in results)
    avg_quality = sum(r["quality_score"] for r in results) / len(results) if results else 0

    print(f"\n{'='*50}")
    print(f"BATCH COMPLETE")
    print(f"{'='*50}")
    print(f"Files processed: {len(results)}")
    print(f"Total ads found: {total_ads}")
    print(f"Total chars removed: {total_chars}")
    print(f"Avg quality score: {avg_quality:.2f}")

    if args.json:
        print(json.dumps(results, indent=2))


def cmd_stats(args):
    """Show statistics from a batch scan."""
    # This would integrate with the database to show historical stats
    print("Stats command - shows historical enrichment statistics")
    print("(Not yet implemented - requires database integration)")


def main():
    parser = argparse.ArgumentParser(
        description="Atlas Enrich - Content cleaning and ad removal",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Clean command
    clean_parser = subparsers.add_parser("clean", help="Clean a single file")
    clean_parser.add_argument("file", nargs="?", default="-", help="File to clean (or - for stdin)")
    clean_parser.add_argument("--type", "-t", default="unknown",
                              choices=["podcast", "youtube", "article", "newsletter", "unknown"])
    clean_parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    clean_parser.add_argument("--no-ads", action="store_true", help="Disable ad stripping")
    clean_parser.add_argument("--confidence", "-c", type=float, default=0.6,
                              help="Minimum confidence for ad detection")
    clean_parser.add_argument("--verbose", "-v", action="store_true", help="Show stats")

    # Scan command
    scan_parser = subparsers.add_parser("scan", help="Scan for ads (detect only)")
    scan_parser.add_argument("file", nargs="?", default="-", help="File to scan")
    scan_parser.add_argument("--type", "-t", default="unknown",
                             choices=["podcast", "youtube", "article", "newsletter", "unknown"])
    scan_parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    scan_parser.add_argument("--confidence", "-c", type=float, default=0.6)

    # Batch command
    batch_parser = subparsers.add_parser("batch", help="Batch process files")
    batch_parser.add_argument("files", nargs="+", help="Files or glob patterns")
    batch_parser.add_argument("--type", "-t", default="unknown",
                              choices=["podcast", "youtube", "article", "newsletter", "unknown"])
    batch_parser.add_argument("--in-place", "-i", action="store_true",
                              help="Modify files in place")
    batch_parser.add_argument("--no-ads", action="store_true", help="Disable ad stripping")
    batch_parser.add_argument("--confidence", "-c", type=float, default=0.6)
    batch_parser.add_argument("--json", "-j", action="store_true", help="Output results as JSON")

    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show enrichment statistics")

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")
    else:
        logging.basicConfig(level=logging.WARNING)

    if args.command == "clean":
        cmd_clean(args)
    elif args.command == "scan":
        cmd_scan(args)
    elif args.command == "batch":
        cmd_batch(args)
    elif args.command == "stats":
        cmd_stats(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
