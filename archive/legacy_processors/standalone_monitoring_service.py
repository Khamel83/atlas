"""
Atlas Standalone Monitoring Dashboard Service
Runs as a separate service for monitoring and observability.
"""

import asyncio
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from helpers.monitoring_dashboard_service import router as monitoring_router
from helpers.monitoring_dashboard_service import start_monitoring_service, stop_monitoring_service
from helpers.logging_config import get_logger

# Create FastAPI app for standalone monitoring service
app = FastAPI(
    title="Atlas Monitoring Dashboard",
    description="Real-time monitoring and observability for Atlas",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include monitoring routes
app.include_router(monitoring_router)

# Configure logging
logger = get_logger("monitoring_service")

@app.on_event("startup")
async def startup_event():
    """Start monitoring service on startup."""
    logger.info("Starting Atlas Monitoring Dashboard Service")
    await start_monitoring_service()
    logger.info("Monitoring service started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Stop monitoring service on shutdown."""
    logger.info("Stopping Atlas Monitoring Dashboard Service")
    await stop_monitoring_service()
    logger.info("Monitoring service stopped successfully")

@app.get("/")
async def root():
    """Root endpoint with service info."""
    return {
        "service": "Atlas Monitoring Dashboard",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "dashboard": "/monitoring/",
            "websocket": "/monitoring/ws",
            "metrics": "/monitoring/metrics",
            "health": "/monitoring/health",
            "alerts": "/monitoring/alerts",
            "system": "/monitoring/system",
            "logs": "/monitoring/logs",
            "prometheus": "/monitoring/prometheus"
        },
        "documentation": "/docs"
    }

@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "service": "monitoring-dashboard",
        "status": "healthy",
        "timestamp": "2025-09-17T00:00:00Z"
    }

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Atlas Monitoring Dashboard Service")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8081, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    parser.add_argument("--log-level", default="info", help="Log level")

    args = parser.parse_args()

    logger.info(f"Starting Atlas Monitoring Dashboard on {args.host}:{args.port}")
    uvicorn.run(
        "standalone_monitoring_service:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level
    )