"""
Process inbox items - fetch, enrich, chunk, embed.

Handles:
- URLs: Fetch content, extract text, enrich, embed
- Text: Directly enrich and embed
- Files: Read content, enrich, embed
"""

import logging
from typing import List, Optional
from pathlib import Path
from dataclasses import dataclass

from .inbox import (
    InboxStore,
    InboxItem,
    InboxStatus,
    SourceType,
)

logger = logging.getLogger(__name__)


@dataclass
class ProcessResult:
    """Result of processing an inbox item."""
    item_id: str
    success: bool
    content_id: Optional[str] = None
    chunks_created: int = 0
    error: Optional[str] = None


def process_item(item: InboxItem, store: Optional[InboxStore] = None) -> ProcessResult:
    """
    Process a single inbox item.

    Steps:
    1. Fetch/read content based on source type
    2. Run through enrichment (if URL)
    3. Chunk and embed
    4. Update status
    """
    store = store or InboxStore()

    # Mark as processing
    store.update_status(item.id, InboxStatus.PROCESSING)

    try:
        if item.source_type == SourceType.URL:
            return _process_url(item, store)
        elif item.source_type == SourceType.TEXT:
            return _process_text(item, store)
        elif item.source_type == SourceType.FILE:
            return _process_file(item, store)
        else:
            raise ValueError(f"Unknown source type: {item.source_type}")

    except Exception as e:
        logger.error(f"Failed to process {item.id}: {e}")
        store.update_status(item.id, InboxStatus.FAILED, error_message=str(e))
        return ProcessResult(item_id=item.id, success=False, error=str(e))


def _process_url(item: InboxItem, store: InboxStore) -> ProcessResult:
    """Process a URL item."""
    from modules.ingest.fetcher import fetch_url
    from modules.ask.indexer import index_single

    url = item.content

    # Fetch URL content
    logger.info(f"Fetching URL: {url}")
    result = fetch_url(url)

    if not result or not result.get("content"):
        store.update_status(item.id, InboxStatus.FAILED, error_message="Failed to fetch URL")
        return ProcessResult(item_id=item.id, success=False, error="Failed to fetch URL")

    content = result["content"]
    title = result.get("title", url)

    # Generate content ID from URL
    from modules.storage.content_store import generate_content_id
    content_id = generate_content_id(url)

    # Index the content (chunk + embed)
    chunks_created = index_single(
        content_id=content_id,
        content=content,
        metadata={
            "title": title,
            "url": url,
            "source": "capture",
            "tags": item.tags,
            "notes": item.notes,
        },
    )

    store.update_status(item.id, InboxStatus.COMPLETED, content_id=content_id)

    logger.info(f"Processed URL {item.id}: {chunks_created} chunks")
    return ProcessResult(
        item_id=item.id,
        success=True,
        content_id=content_id,
        chunks_created=chunks_created,
    )


def _process_text(item: InboxItem, store: InboxStore) -> ProcessResult:
    """Process a text snippet."""
    from modules.ask.indexer import index_single
    import hashlib

    text = item.content

    # Generate content ID from text hash
    text_hash = hashlib.sha256(text.encode()).hexdigest()[:12]
    content_id = f"text-{text_hash}"

    # Index the content
    chunks_created = index_single(
        content_id=content_id,
        content=text,
        metadata={
            "title": f"Note ({item.captured_at.strftime('%Y-%m-%d')})",
            "source": "capture",
            "type": "note",
            "tags": item.tags,
            "notes": item.notes,
        },
    )

    store.update_status(item.id, InboxStatus.COMPLETED, content_id=content_id)

    logger.info(f"Processed text {item.id}: {chunks_created} chunks")
    return ProcessResult(
        item_id=item.id,
        success=True,
        content_id=content_id,
        chunks_created=chunks_created,
    )


def _process_file(item: InboxItem, store: InboxStore) -> ProcessResult:
    """Process a file."""
    from modules.ask.indexer import index_single

    file_path = Path(item.content)

    if not file_path.exists():
        store.update_status(item.id, InboxStatus.FAILED, error_message="File not found")
        return ProcessResult(item_id=item.id, success=False, error="File not found")

    # Read file content
    try:
        content = file_path.read_text()
    except Exception as e:
        store.update_status(item.id, InboxStatus.FAILED, error_message=f"Read error: {e}")
        return ProcessResult(item_id=item.id, success=False, error=str(e))

    # Use filename as content ID
    content_id = file_path.stem

    # Index the content
    chunks_created = index_single(
        content_id=content_id,
        content=content,
        metadata={
            "title": file_path.name,
            "source": "capture",
            "type": "file",
            "path": str(file_path),
            "tags": item.tags,
            "notes": item.notes,
        },
    )

    store.update_status(item.id, InboxStatus.COMPLETED, content_id=content_id)

    logger.info(f"Processed file {item.id}: {chunks_created} chunks")
    return ProcessResult(
        item_id=item.id,
        success=True,
        content_id=content_id,
        chunks_created=chunks_created,
    )


def process_inbox(limit: int = 10) -> List[ProcessResult]:
    """
    Process pending inbox items.

    Args:
        limit: Maximum items to process

    Returns:
        List of ProcessResults
    """
    store = InboxStore()
    items = store.list(status=InboxStatus.PENDING, limit=limit)

    if not items:
        logger.info("No pending items in inbox")
        return []

    logger.info(f"Processing {len(items)} inbox items")

    results = []
    for item in items:
        result = process_item(item, store)
        results.append(result)

    # Summary
    success = sum(1 for r in results if r.success)
    failed = len(results) - success
    logger.info(f"Processed {len(results)} items: {success} success, {failed} failed")

    return results
