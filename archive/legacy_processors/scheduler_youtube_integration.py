#!/usr/bin/env python3
"""
Atlas Scheduler YouTube Integration

This module handles YouTube integration through the Atlas scheduler:
1. Daily YouTube history collection (2 AM as requested)
2. Podcast transcript lookup with YouTube fallback
3. Integration with numeric stage system

Everything runs through the scheduler, not standalone scripts.
"""

import logging
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import schedule
import time

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from helpers.podcast_transcript_lookup_simple import PodcastTranscriptLookup, TranscriptLookupResult
from helpers.youtube_modules_integration import YouTubeIntegrationManager
from helpers.numeric_stages import NumericStage
from helpers.content_transactions import TransactionTimer, ContentTransactionSystem
from helpers.database_config import get_database_connection

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('youtube_scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AtlasYouTubeScheduler:
    """YouTube integration for Atlas scheduler"""

    def __init__(self):
        self.podcast_lookup = PodcastTranscriptLookup()
        self.youtube_manager = YouTubeIntegrationManager()
        self.db_path = "data/atlas.db"
        self.transaction_system = ContentTransactionSystem(self.db_path)

    def collect_youtube_history_daily(self) -> Dict[str, Any]:
        """Collect YouTube history - scheduled to run daily at 2 AM"""
        logger.info("🎬 Starting daily YouTube history collection")

        with TransactionTimer(self.transaction_system, "youtube_history_daily", NumericStage.CONTENT_RECEIVED.value, "scheduled_collection") as timer:
            try:
                # Try to collect history (may fail without auth)
                result = self.youtube_manager.collect_watched_videos(
                    max_videos=100,
                    days_back=1
                )

                if result['success']:
                    logger.info(f"✅ Collected {result['videos_collected']} YouTube videos")
                    # Timer metadata is captured automatically
                else:
                    logger.warning(f"⚠️ YouTube history collection failed: {result['error']}")

                return result

            except Exception as e:
                logger.error(f"❌ Daily YouTube history collection error: {e}")
                return {'success': False, 'error': str(e)}

    def process_pending_transcript_lookups(self) -> Dict[str, Any]:
        """Process pending podcast transcript lookups"""
        logger.info("🎙️ Processing pending transcript lookups")

        with TransactionTimer(self.transaction_system, "transcript_lookup_batch", NumericStage.STRUCTURE_ANALYSIS.value, "scheduled_processing") as timer:
            try:
                # Get pending transcript lookup jobs from database
                conn = get_database_connection()
                cursor = conn.cursor()

                # Create transcript lookup jobs table if not exists
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS transcript_lookup_jobs (
                        id TEXT PRIMARY KEY,
                        podcast_name TEXT NOT NULL,
                        episode_title TEXT NOT NULL,
                        episode_url TEXT,
                        status TEXT DEFAULT 'pending',
                        created_at TEXT NOT NULL,
                        completed_at TEXT,
                        result_data TEXT,
                        error_message TEXT,
                        retry_count INTEGER DEFAULT 0,
                        next_retry_at TEXT
                    )
                """)

                # Get pending jobs
                cursor.execute("""
                    SELECT id, podcast_name, episode_title, episode_url, retry_count
                    FROM transcript_lookup_jobs
                    WHERE status = 'pending'
                    OR (status = 'failed' AND retry_count < 3 AND next_retry_at <= datetime('now'))
                    ORDER BY created_at ASC
                    LIMIT 10
                """)

                pending_jobs = cursor.fetchall()

                if not pending_jobs:
                    logger.info("✅ No pending transcript lookup jobs")
                    return {'success': True, 'jobs_processed': 0}

                processed_count = 0
                success_count = 0

                for job_id, podcast_name, episode_title, episode_url, retry_count in pending_jobs:
                    try:
                        logger.info(f"🔍 Processing transcript lookup: {podcast_name} - {episode_title}")

                        # Perform transcript lookup
                        result = self.podcast_lookup.lookup_transcript(
                            podcast_name,
                            episode_title,
                            episode_url
                        )

                        # Update job record
                        if result.success:
                            cursor.execute("""
                                UPDATE transcript_lookup_jobs
                                SET status = 'completed',
                                    completed_at = datetime('now'),
                                    result_data = ?,
                                    retry_count = ?
                                WHERE id = ?
                            """, (
                                json.dumps({
                                    'transcript': result.transcript,
                                    'source': result.source,
                                    'confidence': result.confidence,
                                    'metadata': result.metadata
                                }),
                                retry_count,
                                job_id
                            ))
                            success_count += 1
                            logger.info(f"✅ Successfully found transcript for {podcast_name} - {episode_title}")
                        else:
                            # Schedule retry if not exhausted
                            next_retry = datetime.now() + timedelta(hours=2 ** retry_count)
                            cursor.execute("""
                                UPDATE transcript_lookup_jobs
                                SET status = 'failed',
                                    completed_at = datetime('now'),
                                    error_message = ?,
                                    retry_count = ?,
                                    next_retry_at = ?
                                WHERE id = ?
                            """, (
                                result.error_message,
                                retry_count + 1,
                                next_retry.isoformat(),
                                job_id
                            ))
                            logger.warning(f"❌ Failed to find transcript for {podcast_name} - {episode_title}: {result.error_message}")

                        processed_count += 1
                        conn.commit()

                    except Exception as e:
                        logger.error(f"❌ Error processing job {job_id}: {e}")
                        continue

                conn.close()

                # Timer metadata is captured automatically

                logger.info(f"✅ Processed {processed_count} transcript lookup jobs ({success_count} successful)")
                return {
                    'success': True,
                    'jobs_processed': processed_count,
                    'jobs_successful': success_count
                }

            except Exception as e:
                logger.error(f"❌ Transcript lookup processing error: {e}")
                return {'success': False, 'error': str(e)}

    def submit_transcript_lookup_job(self, podcast_name: str, episode_title: str, episode_url: str = None) -> str:
        """Submit a new transcript lookup job"""
        import uuid
        job_id = str(uuid.uuid4())

        try:
            conn = get_database_connection()
            cursor = conn.cursor()

            # Ensure table exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transcript_lookup_jobs (
                    id TEXT PRIMARY KEY,
                    podcast_name TEXT NOT NULL,
                    episode_title TEXT NOT NULL,
                    episode_url TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    completed_at TEXT,
                    result_data TEXT,
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    next_retry_at TEXT
                )
            """)

            cursor.execute("""
                INSERT INTO transcript_lookup_jobs (
                    id, podcast_name, episode_title, episode_url,
                    status, created_at, retry_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                job_id, podcast_name, episode_title, episode_url,
                'pending', datetime.now().isoformat(), 0
            ))

            conn.commit()
            conn.close()

            logger.info(f"✅ Submitted transcript lookup job: {podcast_name} - {episode_title}")
            return job_id

        except Exception as e:
            logger.error(f"❌ Failed to submit transcript lookup job: {e}")
            raise

    def get_scheduler_status(self) -> Dict[str, Any]:
        """Get current scheduler status"""
        try:
            conn = get_database_connection()
            cursor = conn.cursor()

            # Check transcript lookup jobs
            cursor.execute("""
                SELECT status, COUNT(*)
                FROM transcript_lookup_jobs
                GROUP BY status
            """)
            job_stats = dict(cursor.fetchall())

            # Get YouTube integration status
            youtube_status = self.youtube_manager.get_youtube_collection_status()

            # Get recent collection history
            cursor.execute("""
                SELECT COUNT(*) as total_videos,
                       MAX(created_at) as last_collection
                FROM content
                WHERE content_type = 'youtube_video'
                AND source = 'youtube_history'
            """)
            video_stats = cursor.fetchone()

            conn.close()

            return {
                'success': True,
                'transcript_jobs': job_stats,
                'youtube_integration': youtube_status,
                'video_collection': {
                    'total_videos': video_stats[0] if video_stats[0] else 0,
                    'last_collection': video_stats[1] if video_stats[1] else None
                },
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"❌ Error getting scheduler status: {e}")
            return {'success': False, 'error': str(e)}

    def run_scheduler_loop(self):
        """Run the main scheduler loop"""
        logger.info("🚀 Starting Atlas YouTube Scheduler")

        # Schedule daily YouTube history collection at 2 AM
        schedule.every().day.at("02:00").do(self.collect_youtube_history_daily)

        # Schedule transcript lookup processing every 30 minutes
        schedule.every(30).minutes.do(self.process_pending_transcript_lookups)

        # Schedule status check every hour
        schedule.every().hour.do(lambda: logger.info(f"Scheduler status: {self.get_scheduler_status()}"))

        logger.info("✅ Scheduler configured:")
        logger.info("  - YouTube history collection: Daily at 2:00 AM")
        logger.info("  - Transcript lookup processing: Every 30 minutes")
        logger.info("  - Status checks: Every hour")

        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute

        except KeyboardInterrupt:
            logger.info("🛑 Scheduler stopped by user")
        except Exception as e:
            logger.error(f"❌ Scheduler error: {e}")

def main():
    """Main entry point for testing and manual execution"""
    scheduler = AtlasYouTubeScheduler()

    # Test transcript lookup
    print("🎙️ Testing transcript lookup...")
    job_id = scheduler.submit_transcript_lookup_job("Huberman Lab", "sleep")
    result = scheduler.process_pending_transcript_lookups()
    print(f"Transcript lookup result: {result}")

    # Test YouTube collection (will likely fail without auth)
    print("\n🎬 Testing YouTube history collection...")
    history_result = scheduler.collect_youtube_history_daily()
    print(f"YouTube history result: {history_result}")

    # Get status
    print("\n📊 Scheduler status:")
    status = scheduler.get_scheduler_status()
    print(json.dumps(status, indent=2))

if __name__ == "__main__":
    main()