"""Search API router for Atlas content search functionality.

Provides FastAPI endpoints for searching content with support for
filtering, pagination, and comprehensive error handling.
"""

import json
import os
import sqlite3
import sys
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

# Add parent directory to path for module imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from helpers.config import load_config
from helpers.database_config import get_database_path_str
from helpers.metadata_manager import MetadataManager
from helpers.semantic_search_ranker import SemanticSearchRanker

router = APIRouter()


def get_metadata_manager() -> MetadataManager:
    """Dependency injection for MetadataManager.

    Returns:
        Configured MetadataManager instance

    Raises:
        HTTPException: If manager initialization fails
    """
    try:
        config = load_config()
        return MetadataManager(config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize metadata manager: {e}")


class SearchResult(BaseModel):
    """Search result model for API responses."""
    uid: str = Field(..., description="Unique identifier for the content")
    title: str = Field(..., description="Content title")
    source: str = Field(..., description="Content source URL")
    content_type: str = Field(..., description="Type of content (article, document, etc.)")
    excerpt: str = Field(..., description="Content excerpt or snippet")
    score: float = Field(..., ge=0, le=1, description="Relevance score (0-1)")
    # Enhanced with structured insights
    summary: Optional[str] = Field(None, description="AI-generated summary")
    topics: Optional[List[str]] = Field(None, description="Key topics extracted")
    entities: Optional[List[str]] = Field(None, description="Named entities found")
    quality_score: Optional[float] = Field(None, description="Content quality score (0-1)")
    sentiment: Optional[str] = Field(None, description="Content sentiment")
    # Semantic search enhancements
    ranking_factors: Optional[Dict] = Field(None, description="Detailed ranking score breakdown")
    related_content: Optional[List[Dict]] = Field(None, description="Related content suggestions")


class SearchResponse(BaseModel):
    """Search API response model."""
    results: List[SearchResult] = Field(default_factory=list, description="List of search results")
    total: int = Field(ge=0, description="Total number of matching results")
    query: str = Field(..., description="Original search query")
    processing_time_ms: Optional[float] = Field(None, description="Query processing time in milliseconds")

def get_search_db_path() -> str:
    """Get the path to the search database.

    Returns:
        Path to the search database file
    """
    return os.path.join("data", "enhanced_search.db")

@router.get("/semantic", response_model=SearchResponse)
async def semantic_search(
    query: str = Query(..., min_length=1, description="Search query string"),
    skip: int = Query(0, ge=0, description="Number of results to skip for pagination"),
    limit: int = Query(20, ge=1, le=50, description="Maximum number of results to return"),
    content_type: Optional[str] = Query(None, description="Filter by content type")
) -> SearchResponse:
    """Perform semantic search with intelligent ranking.

    Uses TF-IDF, content quality, recency, and other factors to provide
    the most relevant search results with detailed ranking information.

    Args:
        query: Search query string (required, minimum 1 character)
        skip: Number of results to skip (default: 0)
        limit: Maximum results to return (1-50, default: 20)
        content_type: Optional content type filter

    Returns:
        SearchResponse with semantically ranked results

    Raises:
        HTTPException: If search fails or system is unavailable
    """
    import time
    start_time = time.time()

    try:
        # Initialize semantic search ranker
        ranker = SemanticSearchRanker()

        # Perform semantic search
        ranked_results = ranker.search_with_ranking(query, limit=(limit + skip))

        # Apply pagination
        paginated_results = ranked_results[skip:skip + limit]

        # Convert to SearchResult objects
        results = []
        for result in paginated_results:
            # Extract data safely
            uid = str(result.get('id', ''))
            title = result.get('title', 'Untitled')
            source = result.get('url', '')
            content_type = result.get('content_type', 'unknown')
            content = result.get('content', '')
            excerpt = content[:200] + ('...' if len(content) > 200 else '')

            # Get ranking score
            ranking_score = result.get('ranking_score', {})
            score = ranking_score.get('total', 0.0)

            # Get related content
            related_content = result.get('related_content', [])

            results.append(SearchResult(
                uid=uid,
                title=title,
                source=source,
                content_type=content_type,
                excerpt=excerpt,
                score=min(1.0, score),  # Cap at 1.0
                ranking_factors=ranking_score,
                related_content=related_content
            ))

        # Calculate processing time
        processing_time_ms = (time.time() - start_time) * 1000

        return SearchResponse(
            results=results,
            total=len(ranked_results),
            query=query,
            processing_time_ms=processing_time_ms
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Semantic search failed: {str(e)}")

@router.get("/", response_model=SearchResponse)
async def search_content(
    query: str = Query(..., min_length=1, description="Search query string"),
    skip: int = Query(0, ge=0, description="Number of results to skip for pagination"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results to return"),
    content_type: Optional[str] = Query(None, description="Filter by content type")
) -> SearchResponse:
    """Search content using SQLite full-text search.

    Performs full-text search across indexed content with support for
    content type filtering and pagination.

    Args:
        query: Search query string (required, minimum 1 character)
        skip: Number of results to skip (default: 0)
        limit: Maximum results to return (1-100, default: 20)
        content_type: Optional content type filter
        manager: Injected MetadataManager dependency

    Returns:
        SearchResponse containing results, total count, query, and timing

    Raises:
        HTTPException: If search fails or database is unavailable
    """
    import time
    start_time = time.time()

    try:
        # Use direct database approach for faster response
        import sqlite3

        # Connect directly to main atlas database
        atlas_db_path = get_database_path_str()
        if not os.path.exists(atlas_db_path):
            raise HTTPException(status_code=503, detail="Atlas database not available")

        conn = sqlite3.connect(atlas_db_path)
        cursor = conn.cursor()

        # Simple search implementation
        like_query = f"%{query}%"

        if content_type:
            # With content type filter
            cursor.execute("""
                SELECT
                    id as uid,
                    title,
                    url as source,
                    content_type,
                    SUBSTR(COALESCE(content, ''), 1, 200) as excerpt
                FROM content
                WHERE (title LIKE ? OR url LIKE ? OR metadata LIKE ?)
                AND title IS NOT NULL
                AND content_type = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, [like_query, like_query, like_query, content_type, limit, skip])

            rows = cursor.fetchall()

            # Get count
            cursor.execute("""
                SELECT COUNT(*)
                FROM content
                WHERE (title LIKE ? OR url LIKE ? OR metadata LIKE ?)
                AND title IS NOT NULL
                AND content_type = ?
            """, [like_query, like_query, like_query, content_type])
        else:
            # Without content type filter
            cursor.execute("""
                SELECT
                    id as uid,
                    title,
                    url as source,
                    content_type,
                    SUBSTR(COALESCE(content, ''), 1, 200) as excerpt
                FROM content
                WHERE (title LIKE ? OR url LIKE ? OR metadata LIKE ?)
                AND title IS NOT NULL
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, [like_query, like_query, like_query, limit, skip])

            rows = cursor.fetchall()

            # Get count
            cursor.execute("""
                SELECT COUNT(*)
                FROM content
                WHERE (title LIKE ? OR url LIKE ? OR metadata LIKE ?)
                AND title IS NOT NULL
            """, [like_query, like_query, like_query])

        total = cursor.fetchone()[0]

        # Convert to SearchResult objects
        results = []
        for row in rows:
            uid = str(row[0])
            title = row[1] if row[1] else "Untitled"
            source = row[2] if row[2] else ""
            content_type_val = row[3] if row[3] else "unknown"
            excerpt = row[4] if row[4] else ""

            results.append(SearchResult(
                uid=uid,
                title=title,
                source=source,
                content_type=content_type_val,
                excerpt=excerpt,
                score=1.0,
                summary=None
            ))

        conn.close()

        # Calculate processing time
        processing_time_ms = (time.time() - start_time) * 1000

        return SearchResponse(
            results=results,
            total=total,
            query=query,
            processing_time_ms=processing_time_ms
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error performing search: {str(e)}")

@router.post("/index")
async def index_content(
    manager: MetadataManager = Depends(get_metadata_manager)
) -> Dict[str, str]:
    """Index all content for full-text search.

    Rebuilds the search index from all available content metadata.
    This operation may take some time for large content collections.

    Args:
        manager: Injected MetadataManager dependency

    Returns:
        Dictionary with indexing status and count

    Raises:
        HTTPException: If indexing fails
    """
    try:
        # Get all metadata
        all_metadata = manager.get_all_metadata()

        # Create or connect to search database
        db_path = get_search_db_path()
        # Ensure output directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create FTS table if it doesn't exist
        cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(
            uid, title, source, content_type, content, rank
        )
        """)

        # Clear existing index
        cursor.execute("DELETE FROM search_index")

        # Index each content item
        indexed_count = 0
        for metadata in all_metadata:
            # Read content if available
            content_text = ""
            if metadata.content_path and os.path.exists(metadata.content_path):
                try:
                    with open(metadata.content_path, 'r', encoding='utf-8') as f:
                        content_text = f.read()
                except Exception:
                    pass  # Skip if can't read

            # Insert into search index
            cursor.execute("""
            INSERT INTO search_index (uid, title, source, content_type, content)
            VALUES (?, ?, ?, ?, ?)
            """, (
                metadata.uid,
                metadata.title,
                metadata.source,
                metadata.content_type.value,
                content_text
            ))
            indexed_count += 1

        conn.commit()
        conn.close()

        return {"message": f"Indexed {indexed_count} content items"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error indexing content: {str(e)}")

@router.get("/autocomplete")
async def get_search_autocomplete(
    query: str = Query("", description="Partial query for autocomplete"),
    limit: int = Query(10, ge=1, le=20, description="Maximum suggestions to return")
) -> List[str]:
    """Get search autocomplete suggestions.

    Returns search suggestions based on common terms and phrases
    in the content corpus.

    Args:
        query: Partial query string (optional)
        limit: Maximum suggestions to return (1-20, default: 10)

    Returns:
        List of search suggestions

    Raises:
        HTTPException: If autocomplete service fails
    """
    try:
        # Load autocomplete data
        autocomplete_file = Path("data/autocomplete_suggestions.json")

        if not autocomplete_file.exists():
            # Build autocomplete if it doesn't exist
            ranker = SemanticSearchRanker()
            ranker.add_search_autocomplete()

        # Load suggestions
        with open(autocomplete_file, 'r') as f:
            autocomplete_data = json.load(f)

        suggestions = autocomplete_data.get('suggestions', [])

        # Filter suggestions based on query
        if query and query.strip():
            query_lower = query.strip().lower()
            filtered_suggestions = [
                s for s in suggestions
                if query_lower in s.lower()
            ]
        else:
            # Return most common suggestions
            filtered_suggestions = suggestions[:limit * 2]

        # Return top suggestions
        return filtered_suggestions[:limit]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Autocomplete failed: {str(e)}")

@router.get("/stats")
async def get_search_stats() -> Dict[str, Any]:
    """Get search system statistics.

    Returns information about search index status, performance,
    and configuration.

    Returns:
        Dictionary with search system statistics
    """
    try:
        ranker = SemanticSearchRanker()
        stats = ranker.get_search_performance_stats()

        # Add database info
        db_path = get_search_db_path()
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM search_index")
            indexed_count = cursor.fetchone()[0]

            conn.close()
            stats['indexed_documents'] = indexed_count
        else:
            stats['indexed_documents'] = 0

        return stats

    except Exception as e:
        return {"error": str(e), "status": "unavailable"}