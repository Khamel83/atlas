#!/usr/bin/env python3
"""
Atlas API Startup Script

Simple script to start the Atlas API server with proper configuration.
"""

import sys
import os
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Start the Atlas API server"""
    try:
        # Import the API app
        from api import app
        import uvicorn

        logger.info("🚀 Starting Atlas API server...")
        logger.info("📊 API Documentation available at:")
        logger.info("   Swagger UI: http://localhost:8000/docs")
        logger.info("   ReDoc: http://localhost:8000/redoc")
        logger.info("📱 Mobile integration ready!")

        # Start the server
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )

    except KeyboardInterrupt:
        logger.info("🛑 API server stopped by user")
    except Exception as e:
        logger.error(f"❌ Failed to start API server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()