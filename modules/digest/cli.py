#!/usr/bin/env python3
"""
CLI for Atlas Digest - weekly content summaries.

Usage:
    # Generate digest for last 7 days
    python -m modules.digest.cli generate

    # Generate for custom period
    python -m modules.digest.cli generate --days 14

    # Save to file
    python -m modules.digest.cli generate --save

    # Output as JSON
    python -m modules.digest.cli generate --json
"""

import argparse
import sys
import os
import logging
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)


def cmd_generate(args):
    """Generate a digest."""
    from modules.digest.summarizer import generate_digest, save_digest

    logger.info(f"Generating digest for last {args.days} days...")

    digest = generate_digest(
        days=args.days,
        min_clusters=args.min_clusters,
        max_clusters=args.max_clusters,
    )

    if not digest.clusters:
        print("No content found for the specified period.")
        return 1

    if args.json:
        # Output as JSON
        output = {
            "date": digest.date.isoformat(),
            "period_days": digest.period_days,
            "total_items": digest.total_items,
            "tokens_used": digest.tokens_used,
            "clusters": [
                {
                    "topic": c.topic,
                    "summary": c.summary,
                    "items": c.items,
                    "keywords": c.keywords,
                }
                for c in digest.clusters
            ],
        }
        print(json.dumps(output, indent=2))
    else:
        # Output as markdown
        print(digest.markdown)

    if args.save:
        filepath = save_digest(digest)
        print(f"\nSaved to: {filepath}")

    print(f"\n[{len(digest.clusters)} topics, {digest.total_items} items, {digest.tokens_used} tokens]")

    return 0


def cmd_history(args):
    """List past digests."""
    from pathlib import Path

    digest_dir = Path("data/digests")
    if not digest_dir.exists():
        print("No digests found.")
        return 0

    files = sorted(digest_dir.glob("*.md"), reverse=True)

    if not files:
        print("No digests found.")
        return 0

    print(f"\n{'='*60}")
    print(f"DIGEST HISTORY ({len(files)} digests)")
    print('='*60)

    for f in files[:args.limit]:
        print(f"\n  {f.stem}")
        # Read first few lines
        content = f.read_text()
        lines = content.split("\n")
        for line in lines[3:7]:  # Skip title, get metadata
            if line.strip():
                print(f"    {line.strip()}")

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Atlas Digest - weekly summaries",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # generate command
    gen_parser = subparsers.add_parser("generate", help="Generate a digest")
    gen_parser.add_argument("--days", "-d", type=int, default=7, help="Days to look back")
    gen_parser.add_argument("--min-clusters", type=int, default=3, help="Min topic clusters")
    gen_parser.add_argument("--max-clusters", type=int, default=8, help="Max topic clusters")
    gen_parser.add_argument("--save", "-s", action="store_true", help="Save to file")
    gen_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # history command
    hist_parser = subparsers.add_parser("history", help="List past digests")
    hist_parser.add_argument("--limit", "-l", type=int, default=10)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Check for API key for generation
    if args.command == "generate" and not os.getenv("OPENROUTER_API_KEY"):
        print("OPENROUTER_API_KEY not set.")
        print("Run with: ./scripts/run_with_secrets.sh python -m modules.digest.cli ...")
        return 1

    commands = {
        "generate": cmd_generate,
        "history": cmd_history,
    }

    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
