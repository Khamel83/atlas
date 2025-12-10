#!/usr/bin/env python3
"""
Test the complete content processing pipeline with real URLs
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from helpers.content_pipeline import ContentProcessingPipeline
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_content_pipeline():
    """Test the content processing pipeline with a real URL"""

    # Use a real URL from our backlog
    test_job_id = "37c9b14f-1b02-43e9-8bb2-b9ea1c4d88f1"
    test_url = "https://www.nytimes.com/2024/08/04/us/minnesota-farm-lino-lakes-mosque.html"
    test_source = "backlog_cleanup"

    # Initialize pipeline
    pipeline = ContentProcessingPipeline()

    logger.info(f"🚀 Testing content processing pipeline with real URL: {test_url}")
    logger.info(f"Job ID: {test_job_id}")

    # Process through complete pipeline
    result = pipeline.process_url_job(test_job_id, test_url, test_source)

    logger.info(f"Pipeline result: {json.dumps(result, indent=2)}")

    # Check if content was created
    if result.get("success"):
        content_id = result.get("content_id")
        if content_id:
            logger.info(f"📄 Checking content files for {content_id}...")

            # Check raw content file
            raw_file = Path(f"content/raw/{content_id}.txt")
            if raw_file.exists():
                logger.info(f"✅ Raw content file exists: {raw_file}")
                with open(raw_file, 'r') as f:
                    content = f.read()
                    word_count = len(content.split())
                    logger.info(f"   Word count: {word_count}")
            else:
                logger.error(f"❌ Raw content file missing: {raw_file}")

            # Check markdown file
            md_file = Path(f"content/markdown/{content_id}.md")
            if md_file.exists():
                logger.info(f"✅ Markdown file exists: {md_file}")
            else:
                logger.error(f"❌ Markdown file missing: {md_file}")

            # Check HTML file
            html_file = Path(f"content/html/{content_id}.html")
            if html_file.exists():
                logger.info(f"✅ HTML file exists: {html_file}")
            else:
                logger.error(f"❌ HTML file missing: {html_file}")

    # Get pipeline statistics
    stats = pipeline.get_pipeline_stats()
    logger.info(f"Pipeline stats: {json.dumps(stats, indent=2)}")

if __name__ == "__main__":
    test_content_pipeline()