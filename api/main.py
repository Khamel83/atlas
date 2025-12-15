"""
Atlas API - Clean REST interface

This is the main FastAPI application that exposes modules/ functionality
via HTTP endpoints.
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import health, podcasts, content, search, dashboard, shiori_compat, notes

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
    "http://localhost:3000,http://localhost:7444,http://127.0.0.1:3000,http://127.0.0.1:7444,"
    "https://read.khamel.com,http://read.khamel.com"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,  # Enable for session cookie/header auth
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization", "X-Session-Id"],
)

# Include routers
app.include_router(health.router)
app.include_router(podcasts.router, prefix="/api/podcasts")
app.include_router(content.router, prefix="/api/content")
app.include_router(search.router, prefix="/api/search")
app.include_router(dashboard.router, prefix="/api")
# Shiori-compatible endpoints (for Atlas Reader frontend)
app.include_router(shiori_compat.router, prefix="/api")
# Notes endpoints (short-form curated content)
app.include_router(notes.router, prefix="/api/notes")


# Root endpoint moved to /api/info to allow StaticFiles to serve Vue frontend at /
@app.get("/api/info")
async def api_info():
    """API info endpoint."""
    return {
        "name": "Atlas API",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health",
    }


# Mount Vue frontend for Atlas Reader (Shiori-compatible UI)
# This must be AFTER API routes to avoid catching /api/* requests
from pathlib import Path
from fastapi.responses import FileResponse
WEBAPP_DIR = Path(__file__).parent.parent / "webapp" / "dist"
if WEBAPP_DIR.exists():
    from fastapi.staticfiles import StaticFiles

    # Serve static assets (js, css, images) - only if assets directory exists
    if (WEBAPP_DIR / "assets").exists():
        app.mount("/assets", StaticFiles(directory=str(WEBAPP_DIR / "assets")), name="assets")

    # Catch-all route for Vue SPA - serves index.html for client-side routing
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve Vue SPA for all non-API routes."""
        # Check if it's a static file that exists
        file_path = WEBAPP_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        # Otherwise serve index.html for Vue Router to handle
        return FileResponse(WEBAPP_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn
    # Bind to localhost only by default for security
    # Set ATLAS_API_HOST=0.0.0.0 to expose externally (use with caution)
    host = os.environ.get("ATLAS_API_HOST", "127.0.0.1")
    port = int(os.environ.get("ATLAS_API_PORT", "7444"))
    uvicorn.run(app, host=host, port=port)
