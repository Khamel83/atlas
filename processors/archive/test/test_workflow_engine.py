#!/usr/bin/env python3
"""
Test the strategy progression engine directly
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from helpers.strategy_progression_engine import StrategyProgressionEngine
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_workflow_engine():
    """Test the workflow engine with a sample job"""

    # Use one of our test jobs
    test_job_id = "18c66cfc-6b5c-4152-9369-20502e2ed894"  # example.com

    # Initialize workflow engine (without Google search for testing)
    from helpers.strategy_progression_engine import StrategyProgressionEngine, StrategyType
    import sqlite3
    from datetime import datetime
    import json
    import uuid
    from typing import Dict, Any, List, Optional
    from pathlib import Path
    import sys

    # Add parent directory to path
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from helpers.article_strategies import ArticleFetcher

    class TestWorkflowEngine:
        def __init__(self, db_path: str = "data/atlas.db"):
            self.db_path = db_path
            self.article_fetcher = ArticleFetcher()
            self.min_content_length = 500

        def get_job_workflow_summary(self, job_id: str) -> Dict[str, Any]:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute("""
                        SELECT status, attempted_strategies, strategy_history,
                               source_url, actual_url, content_source
                        FROM worker_jobs WHERE id = ?
                    """, (job_id,))
                    result = cursor.fetchone()

                    if not result:
                        return {"error": "Job not found"}

                    return {
                        "job_id": job_id,
                        "status": result[0],
                        "attempted_strategies": json.loads(result[1] or "[]"),
                        "strategy_history": json.loads(result[2] or "[]"),
                        "source_url": result[3],
                        "actual_url": result[4],
                        "content_source": result[5]
                    }
            except Exception as e:
                return {"error": str(e)}

        def test_process_job(self, job_id: str) -> Dict[str, Any]:
            """Test processing a job without Google search"""
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute("""
                        SELECT data, source_url FROM worker_jobs WHERE id = ?
                    """, (job_id,))
                    result = cursor.fetchone()

                    if not result:
                        return {"success": False, "error": "Job not found"}

                    job_data = json.loads(result[0])
                    url = job_data.get("url") or result[1]

                # Test article fetcher directly
                strategy_result = self.article_fetcher.fetch_with_fallbacks(url, f"test_{job_id}")

                if strategy_result.success:
                    content = strategy_result.content or ""
                    word_count = len(content.split()) if content else 0

                    return {
                        "success": True,
                        "content": content,
                        "word_count": word_count,
                        "actual_url": url,
                        "title": strategy_result.title,
                        "strategy_used": strategy_result.method,
                        "is_truncated": strategy_result.is_truncated
                    }
                else:
                    return {
                        "success": False,
                        "error": strategy_result.error
                    }

            except Exception as e:
                return {"success": False, "error": f"Test error: {str(e)}"}

    engine = TestWorkflowEngine()

    logger.info(f"🧪 Testing workflow engine with job: {test_job_id}")

    # Get initial job state
    initial_state = engine.get_job_workflow_summary(test_job_id)
    logger.info(f"Initial state: {json.dumps(initial_state, indent=2)}")

    # Test article fetcher directly
    logger.info("🔄 Testing article fetcher...")
    result = engine.test_process_job(test_job_id)

    logger.info(f"Test result: {json.dumps(result, indent=2)}")

if __name__ == "__main__":
    test_workflow_engine()