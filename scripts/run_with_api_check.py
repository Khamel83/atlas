#!/usr/bin/env python3
"""
Atlas Runner with API Permission Check

Wrapper script that ensures API permissions are checked before running any Atlas process.
This prevents unexpected charges from expensive APIs.

Usage:
    python3 scripts/run_with_api_check.py <command> [args...]

Example:
    python3 scripts/run_with_api_check.py python3 helpers/podcast_transcript_lookup.py
"""

import sys
import os
import subprocess
import logging
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.check_api_permissions import main as check_permissions

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/run_with_api_check.py <command> [args...]")
        print("Example: python3 scripts/run_with_api_check.py python3 helpers/podcast_transcript_lookup.py")
        sys.exit(1)

    # Check API permissions first
    logger.info("🔍 Checking API permissions before running Atlas process...")
    permission_result = check_permissions()

    if permission_result != 0:
        logger.error("❌ API permission check failed. Process aborted.")
        sys.exit(permission_result)

    # Extract the command to run
    command = sys.argv[1:]
    logger.info(f"✅ API permissions verified. Running: {' '.join(command)}")

    # Run the command
    try:
        result = subprocess.run(command, cwd=project_root)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error running command: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()