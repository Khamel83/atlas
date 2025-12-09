"""Health check endpoints."""

from fastapi import APIRouter
from datetime import datetime
from pathlib import Path

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Basic health check."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0",
    }


@router.get("/metrics")
async def metrics():
    """Basic metrics endpoint."""
    # Check data directories exist
    data_exists = Path("data").exists()
    podcast_db_exists = Path("data/podcasts/atlas_podcasts.db").exists()

    return {
        "uptime": "unknown",  # Would need process start time
        "data_directory": data_exists,
        "podcast_database": podcast_db_exists,
        "timestamp": datetime.utcnow().isoformat(),
    }
