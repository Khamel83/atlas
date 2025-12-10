#!/usr/bin/env python3
"""
Atlas Monitoring Dashboard Service
Standalone service for real-time monitoring with WebSocket support.
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import the monitoring router
from helpers.monitoring_dashboard_service import router as monitoring_router
from helpers.monitoring_dashboard_service import start_monitoring_service, stop_monitoring_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/monitoring_service.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Create FastAPI app for monitoring
app = FastAPI(
    title="Atlas Monitoring Service",
    description="Real-time monitoring dashboard for Atlas system",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include monitoring routes
app.include_router(monitoring_router)

@app.on_event("startup")
async def startup_event():
    """Start the monitoring service when the app starts."""
    logger.info("Starting Atlas Monitoring Service...")

    # Ensure logs directory exists
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Start the background monitoring service
    await start_monitoring_service()

    logger.info("Atlas Monitoring Service started successfully")
    logger.info("Monitoring dashboard available at: http://localhost:7445/monitoring/")

@app.on_event("shutdown")
async def shutdown_event():
    """Stop the monitoring service when the app shuts down."""
    logger.info("Stopping Atlas Monitoring Service...")
    await stop_monitoring_service()
    logger.info("Atlas Monitoring Service stopped")

@app.get("/")
async def root():
    """Root endpoint redirecting to monitoring dashboard."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/monitoring/")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "atlas-monitoring",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    # Configuration
    HOST = "0.0.0.0"
    PORT = 7445
    RELOAD = True  # Set to False in production

    print(f"🚀 Starting Atlas Monitoring Dashboard Service")
    print(f"📍 Dashboard will be available at: http://{HOST}:{PORT}/monitoring/")
    print(f"🔧 Health check: http://{HOST}:{PORT}/health")
    print(f"📊 Prometheus metrics: http://{HOST}:{PORT}/monitoring/prometheus")
    print(f"📡 WebSocket endpoint: ws://{HOST}:{PORT}/monitoring/ws")

    # Start the service
    uvicorn.run(
        "monitoring_service:app",
        host=HOST,
        port=PORT,
        reload=RELOAD,
        log_level="info"
    )