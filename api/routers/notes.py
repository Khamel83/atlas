"""Notes API endpoints for Atlas.

Notes are short-form user-curated content (selections, quotes, highlights).
They are exempt from quality verification.
"""

import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from modules.storage import FileStore, ContentItem, ContentType, SourceType
from modules.storage.content_types import ProcessingStatus

router = APIRouter(tags=["notes"])


# Request/Response models
class NoteCreateRequest(BaseModel):
    """Create a note from text."""
    text: str
    title: Optional[str] = None
    source_url: Optional[str] = None


class NoteFromUrlRequest(BaseModel):
    """Create a note from a URL with selected text."""
    url: str
    selection: str
    title: Optional[str] = None
    fetch_full_article: bool = True  # Also queue URL for article fetch


class NoteResponse(BaseModel):
    """Response for a single note."""
    content_id: str
    title: str
    text: str
    source_url: Optional[str]
    created_at: str
    extra: Optional[dict] = None

    class Config:
        from_attributes = True


class NoteListResponse(BaseModel):
    """Response for listing notes."""
    items: List[NoteResponse]
    total: int


class NoteCreateResponse(BaseModel):
    """Response after creating a note."""
    status: str
    content_id: str
    title: str
    article_queued: bool = False


# Constants
NOTES_DIR = Path("data/content")
URL_QUEUE_PATH = Path("data/url_queue.txt")


def get_file_store() -> FileStore:
    """Get file store instance for notes."""
    return FileStore(str(NOTES_DIR))


def generate_note_id(text: str, source_url: Optional[str] = None) -> str:
    """Generate unique ID for a note based on content."""
    data = f"{text}{source_url or ''}"
    return hashlib.sha256(data.encode()).hexdigest()[:16]


def create_note_content(title: str, text: str, source_url: Optional[str] = None,
                        domain: Optional[str] = None) -> str:
    """Create markdown content for a note."""
    lines = [f"# {title}", "", text, "", "---"]

    if source_url:
        domain_display = domain or source_url.split("/")[2] if source_url.startswith("http") else "source"
        lines.append(f"*Source: [{domain_display}]({source_url})*")

    lines.append(f"*Saved: {datetime.now().strftime('%Y-%m-%d')}*")

    return "\n".join(lines)


def extract_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        if url.startswith("http"):
            return url.split("/")[2]
    except (IndexError, AttributeError):
        pass
    return "unknown"


def queue_url_for_fetch(url: str) -> bool:
    """Add URL to fetch queue for article processing."""
    try:
        URL_QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(URL_QUEUE_PATH, "a", encoding="utf-8") as f:
            f.write(url + "\n")
        return True
    except IOError:
        return False


@router.post("/", response_model=NoteCreateResponse, status_code=201)
async def create_note(request: NoteCreateRequest):
    """
    Create a note from text.

    Notes are user-curated short-form content that skip quality verification.
    """
    store = get_file_store()

    # Generate ID
    note_id = generate_note_id(request.text, request.source_url)

    # Check for duplicate
    if store.exists(note_id, ContentType.NOTE):
        raise HTTPException(status_code=409, detail="Note already exists")

    # Create title
    title = request.title or request.text[:50].strip() + ("..." if len(request.text) > 50 else "")

    # Create ContentItem
    item = ContentItem(
        content_id=note_id,
        content_type=ContentType.NOTE,
        source_type=SourceType.API_SUBMIT,
        title=title,
        source_url=request.source_url,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        ingested_at=datetime.utcnow(),
        status=ProcessingStatus.COMPLETED,
        extra={
            "note_type": "text",
            "text_length": len(request.text),
        }
    )

    # Create markdown content
    content = create_note_content(
        title=title,
        text=request.text,
        source_url=request.source_url,
        domain=extract_domain(request.source_url) if request.source_url else None
    )

    # Save
    store.save(item, content=content)

    return NoteCreateResponse(
        status="created",
        content_id=note_id,
        title=title,
        article_queued=False
    )


@router.post("/url", response_model=NoteCreateResponse, status_code=201)
async def create_note_from_url(request: NoteFromUrlRequest):
    """
    Create a note from a URL with selected text.

    This is designed for iOS Shortcuts and browser extensions that capture
    both the URL and highlighted text from a webpage.

    If fetch_full_article is True (default), the URL will also be queued
    for full article fetch.
    """
    store = get_file_store()

    # Generate ID
    note_id = generate_note_id(request.selection, request.url)

    # Check for duplicate
    if store.exists(note_id, ContentType.NOTE):
        raise HTTPException(status_code=409, detail="Note already exists")

    # Create title
    title = request.title or request.selection[:50].strip() + ("..." if len(request.selection) > 50 else "")
    domain = extract_domain(request.url)

    # Create ContentItem
    item = ContentItem(
        content_id=note_id,
        content_type=ContentType.NOTE,
        source_type=SourceType.API_SUBMIT,
        title=title,
        source_url=request.url,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        ingested_at=datetime.utcnow(),
        status=ProcessingStatus.COMPLETED,
        extra={
            "note_type": "selection",
            "selection_length": len(request.selection),
            "domain": domain,
        }
    )

    # Create markdown content
    content = create_note_content(
        title=title,
        text=request.selection,
        source_url=request.url,
        domain=domain
    )

    # Save
    store.save(item, content=content)

    # Queue URL for article fetch if requested
    article_queued = False
    if request.fetch_full_article:
        article_queued = queue_url_for_fetch(request.url)

    return NoteCreateResponse(
        status="created",
        content_id=note_id,
        title=title,
        article_queued=article_queued
    )


@router.get("/", response_model=NoteListResponse)
async def list_notes(
    limit: int = Query(default=50, le=200),
    offset: int = 0,
):
    """
    List all notes.

    Notes are returned in reverse chronological order (newest first).
    """
    store = get_file_store()

    # Get all notes
    all_notes = store.list_items(
        content_type=ContentType.NOTE,
        limit=limit + offset  # Get extra to handle offset
    )

    # Apply offset
    notes = all_notes[offset:offset + limit]

    items = []
    for note in notes:
        # Load content
        text = store.load_content(note) or ""

        # Extract just the text portion (skip title and footer)
        lines = text.split("\n")
        text_lines = []
        in_content = False
        for line in lines:
            if line.startswith("# "):
                in_content = True
                continue
            if line.startswith("---"):
                break
            if in_content:
                text_lines.append(line)

        text_content = "\n".join(text_lines).strip()

        items.append(NoteResponse(
            content_id=note.content_id,
            title=note.title,
            text=text_content,
            source_url=note.source_url,
            created_at=note.created_at.isoformat() if note.created_at else "",
            extra=note.extra
        ))

    return NoteListResponse(
        items=items,
        total=len(all_notes)
    )


@router.get("/{note_id}", response_model=NoteResponse)
async def get_note(note_id: str):
    """Get a specific note by ID."""
    store = get_file_store()

    note = store.load(note_id, content_type=ContentType.NOTE)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    # Load content
    text = store.load_content(note) or ""

    # Extract just the text portion
    lines = text.split("\n")
    text_lines = []
    in_content = False
    for line in lines:
        if line.startswith("# "):
            in_content = True
            continue
        if line.startswith("---"):
            break
        if in_content:
            text_lines.append(line)

    text_content = "\n".join(text_lines).strip()

    return NoteResponse(
        content_id=note.content_id,
        title=note.title,
        text=text_content,
        source_url=note.source_url,
        created_at=note.created_at.isoformat() if note.created_at else "",
        extra=note.extra
    )


@router.delete("/{note_id}")
async def delete_note(note_id: str):
    """Delete a note by ID."""
    store = get_file_store()

    # Check if exists
    if not store.exists(note_id, ContentType.NOTE):
        raise HTTPException(status_code=404, detail="Note not found")

    # Delete
    success = store.delete(note_id, ContentType.NOTE)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete note")

    return {"status": "deleted", "content_id": note_id}


@router.get("/stats/summary")
async def get_notes_stats():
    """Get statistics about notes."""
    store = get_file_store()

    notes = store.list_items(content_type=ContentType.NOTE, limit=10000)

    # Aggregate stats
    by_type = {}
    total_length = 0

    for note in notes:
        note_type = note.extra.get("note_type", "unknown") if note.extra else "unknown"
        by_type[note_type] = by_type.get(note_type, 0) + 1

        if note.extra:
            total_length += note.extra.get("text_length", 0) or note.extra.get("selection_length", 0)

    return {
        "total_notes": len(notes),
        "by_type": by_type,
        "avg_length": total_length // len(notes) if notes else 0,
    }
