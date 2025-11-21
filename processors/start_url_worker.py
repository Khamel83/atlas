#!/usr/bin/env python3
"""
Enhanced URL Processing Worker - Uses strategy progression engine for robust ingestion
"""

import sqlite3
import json
import time
import logging
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class URLWorker:
    """Worker to process URL jobs from the unified queue"""

    def __init__(self, db_path="data/atlas.db"):
        self.db_path = db_path
        self.worker_id = f"url_worker_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.running = False

        # Import and initialize the strategy progression engine
        from helpers.strategy_progression_engine import StrategyProgressionEngine
        self.workflow_engine = StrategyProgressionEngine(db_path)

    def get_next_job(self):
        """Get next URL processing job from queue"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                UPDATE worker_jobs
                SET status = 'running', assigned_worker = ?, assigned_at = ?
                WHERE id = (
                    SELECT id FROM worker_jobs
                    WHERE status = 'pending' AND type = 'url_processing'
                    ORDER BY priority DESC, created_at ASC
                    LIMIT 1
                )
                RETURNING id, type, data, priority, status, created_at
            """, (self.worker_id, datetime.now().isoformat()))

            row = cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'type': row[1],
                    'data': json.loads(row[2]),
                    'priority': row[3],
                    'status': row[4],
                    'created_at': row[5]
                }
            return None

    def process_url_job(self, job):
        """Process a single URL job using the content processing pipeline"""
        try:
            url = job['data']['url']
            source = job['data'].get('source', 'unknown')

            logger.info(f"🔄 Processing URL with content pipeline: {url} (source: {source})")

            # Import and initialize the content processing pipeline
            from helpers.content_pipeline import ContentProcessingPipeline
            pipeline = ContentProcessingPipeline(self.db_path)

            # Process through the complete content pipeline
            pipeline_result = pipeline.process_url_job(job['id'], url, source)

            if pipeline_result["success"]:
                final_stage = pipeline_result.get("final_stage", "unknown")
                quality_score = pipeline_result.get("quality_score", 0)
                word_count = pipeline_result.get("word_count", 0)
                content_id = pipeline_result.get("content_id", "unknown")

                logger.info(f"✅ Pipeline processing succeeded for: {url}")
                logger.info(f"   Content ID: {content_id}")
                logger.info(f"   Final Stage: {final_stage}")
                logger.info(f"   Quality Score: {quality_score}")
                logger.info(f"   Word Count: {word_count}")

                # Complete the worker job
                result_msg = f"Pipeline completed: {final_stage} (quality: {quality_score}, words: {word_count})"
                self.complete_job(job['id'], result_msg)

                return True
            else:
                error_msg = pipeline_result.get("error", "Pipeline failed")
                content_id = pipeline_result.get("content_id", "unknown")

                logger.error(f"❌ Pipeline processing failed for {url}: {error_msg}")
                logger.info(f"   Content ID: {content_id}")

                # Fail the worker job
                self.fail_job(job['id'], error_msg)

                return False

        except Exception as e:
            error_msg = f"Pipeline processing error: {str(e)}"
            logger.error(f"❌ {error_msg}")
            self.fail_job(job['id'], error_msg)
            return False

    def complete_job(self, job_id, result):
        """Mark job as completed"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE worker_jobs
                SET status = 'completed', completed_at = ?, result = ?,
                    current_strategy = NULL
                WHERE id = ?
            """, (datetime.now().isoformat(), result, job_id))
            conn.commit()

    def fail_job(self, job_id, error):
        """Mark job as failed"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE worker_jobs
                SET status = 'failed', completed_at = ?, result = ?,
                    current_strategy = NULL
                WHERE id = ?
            """, (datetime.now().isoformat(), error, job_id))
            conn.commit()

    def run(self):
        """Main worker loop"""
        logger.info(f"🚀 Starting URL worker {self.worker_id}")
        self.running = True

        processed_count = 0

        while self.running:
            try:
                job = self.get_next_job()
                if job:
                    success = self.process_url_job(job)
                    if success:
                        processed_count += 1
                        logger.info(f"📊 Processed {processed_count} URLs so far")
                else:
                    # No jobs available, wait a bit
                    time.sleep(5)

            except KeyboardInterrupt:
                logger.info("👋 Worker stopped by user")
                break
            except Exception as e:
                logger.error(f"Worker error: {e}")
                time.sleep(10)  # Wait before retrying

        logger.info(f"✅ Worker finished. Processed {processed_count} URLs total")

def main():
    worker = URLWorker()
    try:
        worker.run()
    except KeyboardInterrupt:
        logger.info("Worker stopped")

if __name__ == "__main__":
    main()