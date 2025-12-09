"""Search endpoints."""

from fastapi import APIRouter, Query
from typing import List, Optional
from pydantic import BaseModel

from modules.storage import IndexManager

router = APIRouter(tags=["search"])


class SearchResult(BaseModel):
    content_id: str
    title: str
    content_type: str
    source_url: Optional[str]
    score: float
    snippet: Optional[str]


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
    total: int


def get_index_manager() -> IndexManager:
    """Get index manager instance."""
    return IndexManager("data/indexes/atlas_index.db")


@router.get("/", response_model=SearchResponse)
async def search_content(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(default=20, le=100),
):
    """Search content by text."""
    index = get_index_manager()
    results = index.search(q, limit=limit)

    return SearchResponse(
        query=q,
        results=[
            SearchResult(
                content_id=r.get("content_id", ""),
                title=r.get("title", ""),
                content_type=r.get("content_type", "unknown"),
                source_url=r.get("source_url"),
                score=r.get("score", 0.0),
                snippet=r.get("snippet"),
            )
            for r in results
        ],
        total=len(results),
    )
