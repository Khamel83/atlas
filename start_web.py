#!/usr/bin/env python3
"""
Atlas Web Interface Startup Script

Simple script to start the Atlas web interface.
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
    """Start the Atlas web interface"""
    try:
        # Import the web interface
        from web_interface import main as web_main

        logger.info("🌐 Starting Atlas Web Interface...")
        logger.info("📊 Access at: http://localhost:7444")
        logger.info("📱 Mobile-friendly interface ready!")

        # Start the web interface
        web_main()

    except KeyboardInterrupt:
        logger.info("🛑 Web interface stopped by user")
    except Exception as e:
        logger.error(f"❌ Failed to start web interface: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()