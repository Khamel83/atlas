#!/usr/bin/env python3
"""
Test the new strategy progression workflow with sample URLs
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from helpers.unified_ingestion import UnifiedIngestionManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_workflow():
    """Test the workflow with various URL types"""

    # Sample URLs to test different scenarios
    test_urls = [
        # Easy success case
        "https://example.com",

        # News article that should work
        "https://www.nytimes.com/2024/01/01/technology/ai-development.html",

        # URL that might need fallback strategies
        "https://www.economist.com/leaders/2024/01/01/the-world-in-2024",

        # Paywall case that might need Google search
        "https://www.wsj.com/articles/tech-innovation-2024",

        # URL that might be hard to reach
        "https://www.theatlantic.com/magazine/archive/2024/01/ai-future/123456/"
    ]

    # Initialize ingestion manager
    ingestion = UnifiedIngestionManager()

    logger.info("🧪 Testing workflow with sample URLs")

    submitted_count = 0
    for url in test_urls:
        try:
            job_id = ingestion.submit_single_url(
                url=url,
                priority=90,  # High priority for testing
                source="workflow_test"
            )
            logger.info(f"✅ Submitted test URL: {url} (job: {job_id})")
            submitted_count += 1
        except Exception as e:
            logger.error(f"❌ Failed to submit {url}: {e}")

    logger.info(f"📊 Submitted {submitted_count} test URLs")
    logger.info("🚀 Now run the URL worker to test the workflow:")
    logger.info("   python3 start_url_worker.py")

if __name__ == "__main__":
    test_workflow()