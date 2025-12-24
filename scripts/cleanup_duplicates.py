#!/usr/bin/env python3
"""
Cleanup Duplicate Content - Keep the best version of each content ID.

For each duplicate content_id:
1. Score each version (content length, proper title, success status)
2. Keep the best version
3. Delete the rest

Usage:
    python scripts/cleanup_duplicates.py --dry-run   # Preview what would be deleted
    python scripts/cleanup_duplicates.py --delete    # Actually delete duplicates
"""

import argparse
import json
import os
import shutil
from collections import defaultdict
from pathlib import Path


def find_all_content(base_dir: Path) -> dict:
    """Find all content items grouped by content_id."""
    content_by_id = defaultdict(list)

    content_types = ["article", "newsletter", "youtube", "podcast", "email"]

    for content_type in content_types:
        type_dir = base_dir / content_type
        if not type_dir.exists():
            continue

        for year_dir in type_dir.iterdir():
            if not year_dir.is_dir() or not year_dir.name.isdigit():
                continue
            for month_dir in year_dir.iterdir():
                if not month_dir.is_dir() or not month_dir.name.isdigit():
                    continue
                for day_dir in month_dir.iterdir():
                    if not day_dir.is_dir() or not day_dir.name.isdigit():
                        continue
                    for item_dir in day_dir.iterdir():
                        if not item_dir.is_dir():
                            continue
                        content_id = item_dir.name
                        content_by_id[content_id].append(item_dir)

    return content_by_id


def score_content(item_dir: Path) -> tuple:
    """
    Score a content item for quality.
    Returns (score, info_dict) - higher score is better.
    """
    metadata_file = item_dir / "metadata.json"
    content_file = item_dir / "content.md"

    score = 0
    info = {
        "path": str(item_dir),
        "has_content": False,
        "content_size": 0,
        "title": "",
        "status": "",
    }

    # Load metadata
    if metadata_file.exists():
        try:
            with open(metadata_file) as f:
                meta = json.load(f)

            title = meta.get("title", "")
            info["title"] = title[:50]
            info["status"] = meta.get("status", meta.get("method", ""))

            # Score based on title quality
            if title and not title.startswith("http"):
                score += 100  # Has real title
                if not title.startswith("Failed:"):
                    score += 50  # Not a failure message

            # Score based on status
            if meta.get("status") == "completed":
                score += 20
            if meta.get("method") in ["playwright", "wayback", "direct"]:
                score += 10

        except (json.JSONDecodeError, Exception):
            pass

    # Score based on content
    if content_file.exists():
        content_size = content_file.stat().st_size
        info["has_content"] = True
        info["content_size"] = content_size

        if content_size > 500:
            score += 200  # Has real content
            score += min(content_size / 100, 100)  # More content is better (up to 10k)

    return (score, info)


def cleanup_duplicates(base_dir: Path, dry_run: bool = True):
    """Find and clean up duplicate content."""
    content_by_id = find_all_content(base_dir)

    # Find duplicates
    duplicates = {cid: paths for cid, paths in content_by_id.items() if len(paths) > 1}

    print(f"\n{'='*60}")
    print(f"DUPLICATE CONTENT CLEANUP")
    print(f"{'='*60}")
    print(f"Total content items: {sum(len(v) for v in content_by_id.values())}")
    print(f"Unique content IDs:  {len(content_by_id)}")
    print(f"Duplicate IDs:       {len(duplicates)}")
    print(f"Duplicate entries:   {sum(len(v) for v in duplicates.values()) - len(duplicates)}")
    print(f"Mode:                {'DRY RUN' if dry_run else 'DELETE'}")
    print(f"{'='*60}\n")

    to_delete = []
    to_keep = []

    for content_id, paths in sorted(duplicates.items()):
        # Score each version
        scored = [(score_content(p), p) for p in paths]
        scored.sort(key=lambda x: x[0][0], reverse=True)  # Highest score first

        # Keep the best, delete the rest
        best = scored[0]
        to_keep.append((content_id, best[1], best[0]))

        for (score, info), path in scored[1:]:
            to_delete.append((content_id, path, score, info))

    # Show what we're keeping/deleting
    print(f"KEEPING {len(to_keep)} BEST VERSIONS:")
    for cid, path, (score, info) in to_keep[:10]:
        print(f"  [{score:4.0f}] {cid}: {info['title'][:40]}...")
    if len(to_keep) > 10:
        print(f"  ... and {len(to_keep) - 10} more")

    print(f"\nDELETING {len(to_delete)} DUPLICATES:")
    for cid, path, score, info in to_delete[:20]:
        print(f"  [{score:4.0f}] {path.name}: {info['title'][:40] or '(no title)'}... -> {path}")
    if len(to_delete) > 20:
        print(f"  ... and {len(to_delete) - 20} more")

    if dry_run:
        print(f"\n{'='*60}")
        print("DRY RUN - No changes made")
        print("Run with --delete to actually remove duplicates")
        print(f"{'='*60}\n")
    else:
        print(f"\n{'='*60}")
        print(f"DELETING {len(to_delete)} duplicate entries...")
        print(f"{'='*60}\n")

        deleted = 0
        errors = 0
        for cid, path, score, info in to_delete:
            try:
                shutil.rmtree(path)
                deleted += 1
            except Exception as e:
                print(f"  ERROR deleting {path}: {e}")
                errors += 1

        print(f"\nDone: {deleted} deleted, {errors} errors")


def main():
    parser = argparse.ArgumentParser(description="Cleanup duplicate content")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Preview changes without deleting (default)")
    parser.add_argument("--delete", action="store_true",
                        help="Actually delete duplicate content")
    parser.add_argument("--base-dir", type=str, default="data/content",
                        help="Base content directory")
    args = parser.parse_args()

    dry_run = not args.delete
    cleanup_duplicates(Path(args.base_dir), dry_run=dry_run)


if __name__ == "__main__":
    main()
