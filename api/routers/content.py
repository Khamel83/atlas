"""Content management endpoints."""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from modules.storage import FileStore, IndexManager, ContentItem, ContentType, SourceType
from modules.storage.content_types import ProcessingStatus

router = APIRouter(tags=["content"])


class ContentItemResponse(BaseModel):
    content_id: str
    content_type: str
    source_type: str
    title: str
    source_url: Optional[str]
    status: str
    created_at: str

    class Config:
        from_attributes = True


class ContentListResponse(BaseModel):
    items: List[ContentItemResponse]
    total: int


class ContentSubmitRequest(BaseModel):
    url: str
    content_type: Optional[str] = "article"


def get_file_store() -> FileStore:
    """Get file store instance."""
    return FileStore("data/content")


def get_index_manager() -> IndexManager:
    """Get index manager instance."""
    return IndexManager("data/indexes/atlas_index.db")


@router.get("/", response_model=ContentListResponse)
async def list_content(
    content_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
):
    """List content items."""
    index = get_index_manager()

    # If no content_type specified, list all types
    if content_type:
        ct = ContentType(content_type)
        st = ProcessingStatus(status) if status else None
        items = index.list_by_type(content_type=ct, status=st, limit=limit, offset=offset)
    else:
        # List from all types
        items = []
        st = ProcessingStatus(status) if status else None
        for ct in ContentType:
            type_items = index.list_by_type(content_type=ct, status=st, limit=limit, offset=offset)
            items.extend(type_items)
            if len(items) >= limit:
                items = items[:limit]
                break

    return ContentListResponse(
        items=[
            ContentItemResponse(
                content_id=item.get("content_id", ""),
                content_type=item.get("content_type", "unknown"),
                source_type=item.get("source_type", "unknown"),
                title=item.get("title", ""),
                source_url=item.get("source_url"),
                status=item.get("status", "unknown"),
                created_at=item.get("created_at", ""),
            )
            for item in items
        ],
        total=len(items),
    )


@router.get("/stats")
async def get_content_stats():
    """Get content statistics."""
    index = get_index_manager()
    return index.get_stats()


@router.get("/{content_id}", response_model=ContentItemResponse)
async def get_content_item(content_id: str):
    """Get a specific content item."""
    store = get_file_store()
    item = store.load(content_id)
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")

    return ContentItemResponse(
        content_id=item.content_id,
        content_type=item.content_type.value,
        source_type=item.source_type.value,
        title=item.title,
        source_url=item.source_url,
        status=item.status.value,
        created_at=item.created_at.isoformat() if item.created_at else "",
    )


@router.post("/submit", status_code=201)
async def submit_content(request: ContentSubmitRequest):
    """Submit a URL for processing."""
    from fastapi.responses import JSONResponse
    from modules.pipeline.content_pipeline import ContentPipeline

    pipeline = ContentPipeline()
    item = pipeline.process_url(request.url)

    if item:
        return JSONResponse(
            status_code=201,
            content={
                "status": "created",
                "content_id": item.content_id,
                "title": item.title,
            }
        )
    else:
        return JSONResponse(
            status_code=200,
            content={
                "status": "skipped",
                "message": "Duplicate or failed to process",
            }
        )


class ContentDetailResponse(ContentItemResponse):
    """Extended content response with text/html."""
    text: Optional[str] = None
    html: Optional[str] = None
    metadata: Optional[dict] = None


@router.get("/{content_id}/text")
async def get_content_text(content_id: str):
    """Get just the text content for an item."""
    from pathlib import Path

    store = get_file_store()
    item = store.load(content_id)
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")

    # Try to find the content file
    base_path = store.base_path / item.content_type.value
    content_path = None

    # Look for content.md or content.txt
    for date_dir in base_path.iterdir() if base_path.exists() else []:
        if not date_dir.is_dir():
            continue
        content_dir = date_dir / content_id
        if content_dir.exists():
            for filename in ["content.md", "content.txt", "article.html"]:
                path = content_dir / filename
                if path.exists():
                    content_path = path
                    break
            break

    if not content_path:
        raise HTTPException(status_code=404, detail="Content file not found")

    try:
        return {"text": content_path.read_text(), "filename": content_path.name}
    except (IOError, UnicodeDecodeError) as e:
        raise HTTPException(status_code=500, detail=f"Error reading content: {e}")
