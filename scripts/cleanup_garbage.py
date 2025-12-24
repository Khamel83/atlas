#!/usr/bin/env python3
"""
Cleanup garbage content from Atlas storage.

This script scans existing content and identifies/removes garbage based on:
1. Title patterns (error messages, empty, etc.)
2. Content patterns (JavaScript required, etc.)
3. URL patterns (tracking pixels, redirects)
4. Content length (too short)

Usage:
    python scripts/cleanup_garbage.py --dry-run      # Preview what would be deleted
    python scripts/cleanup_garbage.py --delete       # Actually delete garbage
    python scripts/cleanup_garbage.py --report       # Generate detailed report
"""

import argparse
import json
import logging
import shutil
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.quality.content_validator import ContentValidator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class GarbageScanner:
    """Scan content directories for garbage."""

    def __init__(self, content_dir: str = "data/content"):
        self.content_dir = Path(content_dir)
        self.validator = ContentValidator()
        self.stats = {
            "scanned": 0,
            "garbage": 0,
            "valid": 0,
            "errors": 0,
            "by_reason": {},
            "by_type": {},
        }
        self.garbage_items: List[Dict] = []

    def scan_item(self, item_dir: Path) -> Tuple[bool, str, Dict]:
        """
        Scan a single content item.

        Returns:
            Tuple of (is_garbage, reason, item_info)
        """
        metadata_file = item_dir / "metadata.json"
        content_file = item_dir / "content.md"
        html_file = item_dir / "article.html"

        if not metadata_file.exists():
            return True, "No metadata", {"path": str(item_dir)}

        try:
            with open(metadata_file) as f:
                metadata = json.load(f)
        except Exception as e:
            return True, f"Invalid metadata: {e}", {"path": str(item_dir)}

        # Get content
        content = ""
        if content_file.exists():
            try:
                content = content_file.read_text()
            except Exception:
                pass
        elif html_file.exists():
            try:
                content = html_file.read_text()
            except Exception:
                pass

        # Build item info
        item_info = {
            "path": str(item_dir),
            "title": metadata.get("title", ""),
            "url": metadata.get("source_url", ""),
            "content_length": len(content),
            "created_at": metadata.get("created_at", ""),
        }

        # Validate
        is_valid, reason, issues = self.validator.validate_all(
            url=item_info["url"],
            title=item_info["title"],
            content=content
        )

        if not is_valid:
            item_info["issues"] = issues
            return True, reason, item_info

        return False, "", item_info

    def scan_all(self) -> Dict:
        """Scan all content directories."""
        content_types = ["article", "newsletter", "youtube"]

        for ct in content_types:
            type_dir = self.content_dir / ct
            if not type_dir.exists():
                continue

            logger.info(f"Scanning {ct}...")

            # Find all metadata.json files
            for metadata_file in type_dir.glob("**/metadata.json"):
                item_dir = metadata_file.parent
                self.stats["scanned"] += 1

                try:
                    is_garbage, reason, item_info = self.scan_item(item_dir)
                    item_info["content_type"] = ct

                    if is_garbage:
                        self.stats["garbage"] += 1
                        self.garbage_items.append({
                            "reason": reason,
                            **item_info
                        })

                        # Track by reason
                        reason_key = reason.split(":")[0] if ":" in reason else reason
                        self.stats["by_reason"][reason_key] = \
                            self.stats["by_reason"].get(reason_key, 0) + 1

                        # Track by type
                        self.stats["by_type"][ct] = self.stats["by_type"].get(ct, 0) + 1
                    else:
                        self.stats["valid"] += 1

                except Exception as e:
                    logger.error(f"Error scanning {item_dir}: {e}")
                    self.stats["errors"] += 1

                # Progress
                if self.stats["scanned"] % 500 == 0:
                    logger.info(f"  Scanned {self.stats['scanned']} items, "
                               f"found {self.stats['garbage']} garbage...")

        return self.stats

    def delete_garbage(self, dry_run: bool = True) -> int:
        """
        Delete garbage items.

        Args:
            dry_run: If True, only log what would be deleted

        Returns:
            Number of items deleted
        """
        deleted = 0

        for item in self.garbage_items:
            item_path = Path(item["path"])

            if dry_run:
                logger.info(f"[DRY RUN] Would delete: {item_path.name} - {item.get('title', '')[:50]}")
            else:
                try:
                    if item_path.exists():
                        shutil.rmtree(item_path)
                        logger.info(f"Deleted: {item_path.name}")
                        deleted += 1
                except Exception as e:
                    logger.error(f"Failed to delete {item_path}: {e}")

        return deleted

    def generate_report(self, output_file: str = None) -> str:
        """Generate a detailed report."""
        report_lines = [
            "=" * 60,
            "ATLAS GARBAGE CONTENT REPORT",
            f"Generated: {datetime.now().isoformat()}",
            "=" * 60,
            "",
            "SUMMARY",
            "-" * 40,
            f"Total scanned:     {self.stats['scanned']}",
            f"Valid content:     {self.stats['valid']}",
            f"Garbage content:   {self.stats['garbage']}",
            f"Scan errors:       {self.stats['errors']}",
            f"Garbage rate:      {self.stats['garbage'] / max(self.stats['scanned'], 1) * 100:.1f}%",
            "",
            "BY CONTENT TYPE",
            "-" * 40,
        ]

        for ct, count in sorted(self.stats["by_type"].items(), key=lambda x: -x[1]):
            report_lines.append(f"  {ct}: {count}")

        report_lines.extend([
            "",
            "BY REJECTION REASON",
            "-" * 40,
        ])

        for reason, count in sorted(self.stats["by_reason"].items(), key=lambda x: -x[1]):
            report_lines.append(f"  {reason}: {count}")

        report_lines.extend([
            "",
            "TOP 50 GARBAGE ITEMS",
            "-" * 40,
        ])

        for item in self.garbage_items[:50]:
            title = (item.get("title") or "")[:40]
            reason = item.get("reason", "Unknown")[:30]
            report_lines.append(f"  [{reason}] {title}")

        report_lines.extend([
            "",
            "=" * 60,
        ])

        report = "\n".join(report_lines)

        if output_file:
            Path(output_file).write_text(report)
            logger.info(f"Report saved to: {output_file}")

        return report


def main():
    parser = argparse.ArgumentParser(description="Cleanup garbage content from Atlas")
    parser.add_argument("--dry-run", action="store_true",
                       help="Preview what would be deleted (default)")
    parser.add_argument("--delete", action="store_true",
                       help="Actually delete garbage content")
    parser.add_argument("--report", action="store_true",
                       help="Generate detailed report")
    parser.add_argument("--output", type=str,
                       help="Output file for report")
    parser.add_argument("--content-dir", type=str, default="data/content",
                       help="Content directory to scan")
    args = parser.parse_args()

    scanner = GarbageScanner(args.content_dir)

    print("Scanning content directories...")
    stats = scanner.scan_all()

    print("\n" + "=" * 50)
    print("SCAN COMPLETE")
    print("=" * 50)
    print(f"Scanned:       {stats['scanned']}")
    print(f"Valid:         {stats['valid']}")
    print(f"Garbage:       {stats['garbage']}")
    print(f"Errors:        {stats['errors']}")
    print("-" * 50)
    print("By reason:")
    for reason, count in sorted(stats["by_reason"].items(), key=lambda x: -x[1])[:10]:
        print(f"  {reason}: {count}")
    print("=" * 50)

    if args.report:
        output = args.output or f"data/garbage_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        report = scanner.generate_report(output)
        print(report)

    if args.delete:
        print("\n⚠️  DELETING GARBAGE CONTENT...")
        deleted = scanner.delete_garbage(dry_run=False)
        print(f"Deleted {deleted} items")
    elif not args.report:
        # Default to dry run
        print("\n[DRY RUN] Preview of what would be deleted:")
        scanner.delete_garbage(dry_run=True)
        print("\nTo actually delete, run with --delete flag")


if __name__ == "__main__":
    main()
