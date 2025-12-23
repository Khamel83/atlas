"""
Atlas Capture - Quick inbox for "save now, process later" workflow.

Captures URLs, text snippets, and files into a queue for later processing.
Processing runs enrichment, chunking, and embedding.

Usage:
    from modules.capture import capture_url, capture_text, process_inbox

    # Quick capture
    capture_url("https://example.com/article", tags=["ai", "work"])
    capture_text("Important thought", tags=["personal"])

    # Process inbox (runs enrichment + embedding)
    results = process_inbox(limit=10)
"""

from .inbox import (
    InboxItem,
    InboxStore,
    capture_url,
    capture_text,
    capture_file,
    get_inbox,
)
from .processor import process_inbox, process_item

__all__ = [
    "InboxItem",
    "InboxStore",
    "capture_url",
    "capture_text",
    "capture_file",
    "get_inbox",
    "process_inbox",
    "process_item",
]
