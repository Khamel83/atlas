#!/usr/bin/env python3
"""
CLI for Atlas Capture - quick inbox for save-now-process-later.

Usage:
    # Capture a URL
    python -m modules.capture.cli url "https://example.com/article" --tags ai,work

    # Capture text
    python -m modules.capture.cli text "Important thought" --tags personal

    # Capture a file
    python -m modules.capture.cli file ~/Documents/report.pdf

    # List inbox
    python -m modules.capture.cli inbox
    python -m modules.capture.cli inbox --status pending

    # Process inbox items
    python -m modules.capture.cli process --limit 10

    # Show stats
    python -m modules.capture.cli stats
"""

import argparse
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)


def cmd_url(args):
    """Capture a URL."""
    from modules.capture.inbox import capture_url

    tags = [t.strip() for t in args.tags.split(",")] if args.tags else None

    item = capture_url(args.url, tags=tags, notes=args.notes)
    print(f"Captured: {item.id}")
    print(f"  URL: {item.content}")
    if tags:
        print(f"  Tags: {', '.join(tags)}")
    return 0


def cmd_text(args):
    """Capture text."""
    from modules.capture.inbox import capture_text

    tags = [t.strip() for t in args.tags.split(",")] if args.tags else None

    item = capture_text(args.text, tags=tags, notes=args.notes)
    print(f"Captured: {item.id}")
    print(f"  Text: {item.content[:100]}{'...' if len(item.content) > 100 else ''}")
    if tags:
        print(f"  Tags: {', '.join(tags)}")
    return 0


def cmd_file(args):
    """Capture a file."""
    from modules.capture.inbox import capture_file

    path = Path(args.path).expanduser().resolve()
    if not path.exists():
        print(f"File not found: {path}")
        return 1

    tags = [t.strip() for t in args.tags.split(",")] if args.tags else None

    item = capture_file(str(path), tags=tags, notes=args.notes)
    print(f"Captured: {item.id}")
    print(f"  File: {path}")
    if tags:
        print(f"  Tags: {', '.join(tags)}")
    return 0


def cmd_inbox(args):
    """List inbox items."""
    from modules.capture.inbox import get_inbox, InboxStatus

    status = args.status
    items = get_inbox(status=status, limit=args.limit)

    if not items:
        print("Inbox is empty" if not status else f"No {status} items")
        return 0

    print(f"\n{'='*60}")
    print(f"INBOX ({len(items)} items" + (f", status={status}" if status else "") + ")")
    print('='*60)

    for item in items:
        status_icon = {
            "pending": "⏳",
            "processing": "🔄",
            "completed": "✅",
            "failed": "❌",
        }.get(item.status.value, "?")

        print(f"\n{status_icon} [{item.id}] {item.source_type.value}")
        print(f"   {item.content[:80]}{'...' if len(item.content) > 80 else ''}")
        print(f"   Captured: {item.captured_at.strftime('%Y-%m-%d %H:%M')}")
        if item.tags:
            print(f"   Tags: {', '.join(item.tags)}")
        if item.error_message:
            print(f"   Error: {item.error_message}")

    return 0


def cmd_process(args):
    """Process inbox items."""
    from modules.capture.processor import process_inbox

    if args.dry_run:
        from modules.capture.inbox import get_inbox
        items = get_inbox(status="pending", limit=args.limit)
        print(f"Would process {len(items)} items:")
        for item in items:
            print(f"  - [{item.id}] {item.source_type.value}: {item.content[:60]}...")
        return 0

    results = process_inbox(limit=args.limit)

    if not results:
        print("No items to process")
        return 0

    print(f"\n{'='*60}")
    print(f"PROCESSED {len(results)} ITEMS")
    print('='*60)

    success = 0
    for r in results:
        if r.success:
            print(f"✅ {r.item_id}: {r.chunks_created} chunks created")
            success += 1
        else:
            print(f"❌ {r.item_id}: {r.error}")

    print(f"\nSuccess: {success}/{len(results)}")
    return 0


def cmd_stats(args):
    """Show inbox statistics."""
    from modules.capture.inbox import InboxStore

    store = InboxStore()
    stats = store.stats()

    print(f"\n{'='*60}")
    print("INBOX STATISTICS")
    print('='*60)

    print(f"\n  Total items: {stats['total']}")
    print(f"  Pending:     {stats['pending']}")
    print(f"  Processing:  {stats['processing']}")
    print(f"  Completed:   {stats['completed']}")
    print(f"  Failed:      {stats['failed']}")

    return 0


def cmd_delete(args):
    """Delete an inbox item."""
    from modules.capture.inbox import InboxStore

    store = InboxStore()
    item = store.get(args.id)

    if not item:
        print(f"Item not found: {args.id}")
        return 1

    store.delete(args.id)
    print(f"Deleted: {args.id}")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Atlas Capture - quick inbox",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # url command
    url_parser = subparsers.add_parser("url", help="Capture a URL")
    url_parser.add_argument("url", help="URL to capture")
    url_parser.add_argument("--tags", "-t", help="Comma-separated tags")
    url_parser.add_argument("--notes", "-n", help="Personal notes")

    # text command
    text_parser = subparsers.add_parser("text", help="Capture text")
    text_parser.add_argument("text", help="Text to capture")
    text_parser.add_argument("--tags", "-t", help="Comma-separated tags")
    text_parser.add_argument("--notes", "-n", help="Personal notes")

    # file command
    file_parser = subparsers.add_parser("file", help="Capture a file")
    file_parser.add_argument("path", help="File path")
    file_parser.add_argument("--tags", "-t", help="Comma-separated tags")
    file_parser.add_argument("--notes", "-n", help="Personal notes")

    # inbox command
    inbox_parser = subparsers.add_parser("inbox", help="List inbox")
    inbox_parser.add_argument("--status", "-s", choices=["pending", "processing", "completed", "failed"])
    inbox_parser.add_argument("--limit", "-l", type=int, default=20)

    # process command
    process_parser = subparsers.add_parser("process", help="Process inbox items")
    process_parser.add_argument("--limit", "-l", type=int, default=10)
    process_parser.add_argument("--dry-run", action="store_true")

    # stats command
    subparsers.add_parser("stats", help="Show statistics")

    # delete command
    delete_parser = subparsers.add_parser("delete", help="Delete an item")
    delete_parser.add_argument("id", help="Item ID to delete")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "url": cmd_url,
        "text": cmd_text,
        "file": cmd_file,
        "inbox": cmd_inbox,
        "process": cmd_process,
        "stats": cmd_stats,
        "delete": cmd_delete,
    }

    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
