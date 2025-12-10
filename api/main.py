"""
Atlas API - Clean REST interface

This is the main FastAPI application that exposes modules/ functionality
via HTTP endpoints.
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import health, podcasts, content, search, dashboard

# Create app
app = FastAPI(
    title="Atlas API",
    description="Podcast transcript discovery and content management",
    version="2.0.0",
)

# CORS configuration - restrict to specific origins
# Set ATLAS_CORS_ORIGINS env var for custom origins (comma-separated)
ALLOWED_ORIGINS = os.environ.get(
    "ATLAS_CORS_ORIGINS",
    "http://localhost:3000,http://localhost:7444,http://127.0.0.1:3000,http://127.0.0.1:7444"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,  # Disabled - not needed for API-only access
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)

# Include routers
app.include_router(health.router)
app.include_router(podcasts.router, prefix="/api/podcasts")
app.include_router(content.router, prefix="/api/content")
app.include_router(search.router, prefix="/api/search")
app.include_router(dashboard.router, prefix="/api")


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
    # Bind to localhost only by default for security
    # Set ATLAS_API_HOST=0.0.0.0 to expose externally (use with caution)
    host = os.environ.get("ATLAS_API_HOST", "127.0.0.1")
    port = int(os.environ.get("ATLAS_API_PORT", "7444"))
    uvicorn.run(app, host=host, port=port)
