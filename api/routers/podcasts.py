"""Podcast management endpoints."""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from modules.podcasts.store import PodcastStore, Podcast, Episode

router = APIRouter(tags=["podcasts"])

# Pydantic models for API
class PodcastResponse(BaseModel):
    id: int
    name: str
    slug: str
    rss_url: str
    site_url: Optional[str]
    resolver: str
    created_at: Optional[str]

    class Config:
        from_attributes = True


class EpisodeResponse(BaseModel):
    id: int
    podcast_id: int
    title: str
    url: str
    publish_date: Optional[str]
    transcript_status: str
    transcript_url: Optional[str]

    class Config:
        from_attributes = True


class StatsResponse(BaseModel):
    total_podcasts: int
    episodes_by_status: dict
    recent_runs: List[dict]


def get_store() -> PodcastStore:
    """Get podcast store instance."""
    return PodcastStore()


@router.get("/", response_model=List[PodcastResponse])
async def list_podcasts():
    """List all podcasts."""
    store = get_store()
    podcasts = store.list_podcasts()
    return [
        PodcastResponse(
            id=p.id,
            name=p.name,
            slug=p.slug,
            rss_url=p.rss_url,
            site_url=p.site_url,
            resolver=p.resolver,
            created_at=p.created_at,
        )
        for p in podcasts
    ]


@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Get podcast statistics."""
    store = get_store()
    stats = store.get_stats()
    return StatsResponse(**stats)


@router.get("/{podcast_id}", response_model=PodcastResponse)
async def get_podcast(podcast_id: int):
    """Get a specific podcast."""
    store = get_store()
    podcast = store.get_podcast(podcast_id)
    if not podcast:
        raise HTTPException(status_code=404, detail="Podcast not found")
    return PodcastResponse(
        id=podcast.id,
        name=podcast.name,
        slug=podcast.slug,
        rss_url=podcast.rss_url,
        site_url=podcast.site_url,
        resolver=podcast.resolver,
        created_at=podcast.created_at,
    )


@router.get("/{podcast_id}/episodes", response_model=List[EpisodeResponse])
async def get_episodes(podcast_id: int):
    """Get episodes for a podcast."""
    store = get_store()
    podcast = store.get_podcast(podcast_id)
    if not podcast:
        raise HTTPException(status_code=404, detail="Podcast not found")

    episodes = store.get_episodes_by_podcast(podcast_id)
    return [
        EpisodeResponse(
            id=e.id,
            podcast_id=e.podcast_id,
            title=e.title,
            url=e.url,
            publish_date=e.publish_date,
            transcript_status=e.transcript_status,
            transcript_url=e.transcript_url,
        )
        for e in episodes
    ]
