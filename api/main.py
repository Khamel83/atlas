"""
Atlas API - Clean REST interface

This is the main FastAPI application that exposes modules/ functionality
via HTTP endpoints.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import health, podcasts, content, search

# Create app
app = FastAPI(
    title="Atlas API",
    description="Podcast transcript discovery and content management",
    version="2.0.0",
)

# CORS middleware for web access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(podcasts.router, prefix="/api/podcasts")
app.include_router(content.router, prefix="/api/content")
app.include_router(search.router, prefix="/api/search")


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "Atlas API",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7444)
