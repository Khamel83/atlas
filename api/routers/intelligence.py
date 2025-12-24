"""Intelligence endpoints - Topic maps, quotes, recommendations, etc."""

from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(tags=["intelligence"])


class TopicClusterResponse(BaseModel):
    id: str
    label: str
    count: int
    sources: List[str]


class TopicMapResponse(BaseModel):
    clusters: List[TopicClusterResponse]
    connections: List[Dict[str, Any]]
    source_distribution: Dict[str, int]
    date_distribution: Dict[str, int]
    total_content: int
    generated_at: str


class QuoteResponse(BaseModel):
    text: str
    source: str
    title: str
    date: Optional[str]
    score: float


class SourcePerspectiveResponse(BaseModel):
    source: str
    topic: str
    summary: Optional[str]
    key_points: List[str]
    content_count: int
    sample_titles: List[str]


class ContradictionResponse(BaseModel):
    topic: str
    source_a: str
    source_b: str
    position_a: str
    position_b: str
    severity: str


class RecommendationResponse(BaseModel):
    content_id: str
    title: str
    source: str
    reason: str
    score: float


@router.get("/topicmap", response_model=TopicMapResponse)
async def get_topic_map(
    limit: int = Query(default=1000, le=5000, description="Max chunks to analyze"),
    min_cluster_size: int = Query(default=5, description="Minimum items per cluster"),
):
    """Generate a topic map from indexed content."""
    try:
        from modules.ask.topic_map import TopicMapper

        mapper = TopicMapper()
        topic_map = mapper.generate_map(limit=limit, min_cluster_size=min_cluster_size)

        return TopicMapResponse(
            clusters=[
                TopicClusterResponse(
                    id=c.id,
                    label=c.label,
                    count=c.content_count,
                    sources=c.sources,
                )
                for c in topic_map.clusters
            ],
            connections=topic_map.connections,
            source_distribution=topic_map.source_distribution,
            date_distribution=topic_map.date_distribution,
            total_content=topic_map.total_content,
            generated_at=topic_map.generated_at.isoformat(),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/topicmap/html", response_class=HTMLResponse)
async def get_topic_map_html(
    limit: int = Query(default=1000, le=5000),
    min_cluster_size: int = Query(default=5),
):
    """Get topic map as interactive HTML visualization."""
    try:
        from modules.ask.topic_map import TopicMapper

        mapper = TopicMapper()
        topic_map = mapper.generate_map(limit=limit, min_cluster_size=min_cluster_size)
        html = mapper.generate_html(topic_map)

        return HTMLResponse(content=html)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quotes", response_model=List[QuoteResponse])
async def get_quotes(
    topic: str = Query(..., min_length=2, description="Topic to find quotes about"),
    limit: int = Query(default=5, le=20),
    source: Optional[str] = Query(default=None, description="Filter by source"),
):
    """Extract quotable passages on a topic."""
    try:
        from modules.ask.intelligence import QuoteExtractor

        extractor = QuoteExtractor()
        quotes = extractor.extract_quotes(topic=topic, limit=limit, source_filter=source)

        return [
            QuoteResponse(
                text=q.text,
                source=q.source,
                title=q.title,
                date=q.date,
                score=q.score,
            )
            for q in quotes
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/source/{source_name}", response_model=SourcePerspectiveResponse)
async def get_source_perspective(
    source_name: str,
    topic: str = Query(..., min_length=2, description="Topic to query about"),
    limit: int = Query(default=5, le=20),
):
    """Get what a specific source thinks about a topic."""
    try:
        from modules.ask.intelligence import SourceQueryEngine

        engine = SourceQueryEngine()
        perspective = engine.what_does_x_think(source=source_name, topic=topic, limit=limit)

        if not perspective:
            raise HTTPException(status_code=404, detail=f"No content found for {source_name} on {topic}")

        return SourcePerspectiveResponse(
            source=perspective.source,
            topic=perspective.topic,
            summary=perspective.summary,
            key_points=perspective.key_points,
            content_count=perspective.content_count,
            sample_titles=perspective.sample_titles,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/contradictions", response_model=List[ContradictionResponse])
async def find_contradictions(
    topic: str = Query(..., min_length=2, description="Topic to find contradictions about"),
    min_sources: int = Query(default=2, description="Minimum sources needed"),
):
    """Find contradicting opinions across sources."""
    try:
        from modules.ask.intelligence import ContradictionRadar

        radar = ContradictionRadar()
        contradictions = radar.find_contradictions(topic=topic, min_sources=min_sources)

        return [
            ContradictionResponse(
                topic=c.topic,
                source_a=c.source_a,
                source_b=c.source_b,
                position_a=c.position_a,
                position_b=c.position_b,
                severity=c.severity,
            )
            for c in contradictions
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommendations", response_model=List[RecommendationResponse])
async def get_recommendations(
    limit: int = Query(default=5, le=20),
    based_on: str = Query(default="annotations", description="Basis for recommendations"),
):
    """Get content recommendations based on user interests."""
    try:
        from modules.ask.intelligence import RecommendationEngine

        engine = RecommendationEngine()
        results = engine.get_recommendations(limit=limit, based_on=based_on)

        return [
            RecommendationResponse(
                content_id=r.content_id,
                title=r.metadata.get("title", "Untitled"),
                source=r.metadata.get("source", "Unknown"),
                reason="Based on your interests",
                score=r.score,
            )
            for r in results
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_intelligence_stats():
    """Get overall intelligence layer stats."""
    try:
        from modules.ask.config import get_config
        import sqlite3

        config = get_config()
        stats = {
            "vector_db_exists": config.vector_db_path.exists(),
            "total_chunks": 0,
            "sources": [],
            "research_threads": 0,
        }

        if config.vector_db_path.exists():
            with sqlite3.connect(config.vector_db_path) as conn:
                stats["total_chunks"] = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]

                # Get unique sources
                rows = conn.execute("""
                    SELECT DISTINCT content_id FROM chunks LIMIT 1000
                """).fetchall()

                # Infer sources from content_ids
                source_set = set()
                for (content_id,) in rows:
                    cid = content_id.lower()
                    if "stratechery" in cid:
                        source_set.add("Stratechery")
                    elif "acquired" in cid:
                        source_set.add("Acquired")
                    elif "hard-fork" in cid:
                        source_set.add("Hard Fork")
                    elif "ezra" in cid:
                        source_set.add("Ezra Klein")
                    elif "lex" in cid:
                        source_set.add("Lex Fridman")
                    elif "article" in cid:
                        source_set.add("Articles")
                    elif "newsletter" in cid:
                        source_set.add("Newsletters")

                stats["sources"] = sorted(source_set)

        # Check research threads
        threads_db = config.vector_db_path.parent / "research_threads.db"
        if threads_db.exists():
            with sqlite3.connect(threads_db) as conn:
                try:
                    stats["research_threads"] = conn.execute("SELECT COUNT(*) FROM threads").fetchone()[0]
                except:
                    pass

        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
