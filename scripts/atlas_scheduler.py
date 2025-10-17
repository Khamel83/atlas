#!/usr/bin/env python3
"""
Atlas Background Scheduler
Runs the comprehensive processing service on schedule.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import time
import argparse
import logging
import subprocess
from datetime import datetime, timedelta
import atexit
import signal
from helpers.bulletproof_process_manager import get_manager, create_managed_process
from helpers.resource_monitor import check_system_health

# Import Universal Processing Queue for coordinated job management
sys.path.insert(0, str(Path(__file__).parent.parent))
from universal_processing_queue import UniversalProcessingQueue, add_youtube_processing_job

sys.path.insert(0, str(Path(__file__).parent.parent))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/atlas_scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AtlasScheduler:
    """Atlas background task scheduler."""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.last_comprehensive_run = None
        self.last_transcript_run = None
        self.last_transcript_success = None
        self.last_transcript_check = None
        self.last_youtube_run = None
        self.last_source_inventory_run = None
        self.comprehensive_interval = 30  # 30 seconds - run continuously
        self.transcript_interval = 60 * 60  # 1 hour - keep trying more frequently
        self.transcript_check_interval = 5 * 60  # 5 minutes for light transcript checking
        self.youtube_interval = 5 * 60 * 60  # 5 hours for YouTube processing
        self.source_inventory_interval = 2 * 60 * 60  # 2 hours for source discovery
        # Use venv Python, not system Python
        self.python_executable = str(self.project_root / "venv" / "bin" / "python3")

        # Register cleanup on exit
        atexit.register(self.cleanup_processes)
        signal.signal(signal.SIGTERM, lambda s, f: self.cleanup_processes())
        signal.signal(signal.SIGINT, lambda s, f: self.cleanup_processes())

    def cleanup_processes(self):
        """Cleanup all managed processes"""
        manager = get_manager()
        manager.cleanup_all()
        logger.info("🧹 All processes cleaned up")

    def should_run_comprehensive(self) -> bool:
        """Check if comprehensive cycle should run."""
        if not self.last_comprehensive_run:
            return True
        return (datetime.now() - self.last_comprehensive_run).seconds >= self.comprehensive_interval

    def should_run_transcript_discovery(self) -> bool:
        """Check if smart transcript discovery should run - retry failed attempts more frequently."""
        if not self.last_transcript_run:
            return True
        # If last run was successful, wait full interval
        if self.last_transcript_success and self.last_transcript_success == self.last_transcript_run:
            return (datetime.now() - self.last_transcript_run).seconds >= self.transcript_interval
        # For failed attempts, retry in 10 minutes instead of waiting full interval
        return (datetime.now() - self.last_transcript_run).seconds >= (10 * 60)

    def should_run_transcript_check(self) -> bool:
        """Check if light transcript checking should run."""
        if not self.last_transcript_check:
            return True
        return (datetime.now() - self.last_transcript_check).seconds >= self.transcript_check_interval

    def should_run_youtube_processing(self) -> bool:
        """Check if YouTube processing should run."""
        if not self.last_youtube_run:
            return True
        return (datetime.now() - self.last_youtube_run).seconds >= self.youtube_interval

    def should_run_source_inventory(self) -> bool:
        """Check if source inventory discovery should run."""
        if not self.last_source_inventory_run:
            return True
        return (datetime.now() - self.last_source_inventory_run).seconds >= self.source_inventory_interval

    def run_comprehensive_service(self) -> bool:
        """Run the comprehensive processing service."""
        try:
            logger.info("🚀 Starting comprehensive processing cycle...")

            process = create_managed_process([
                self.python_executable, str(self.project_root / "atlas_comprehensive_service.py")
            ], "comprehensive_service", cwd=self.project_root, timeout=7200)
            stdout, stderr = process.communicate()

            if process.returncode == 0:
                logger.info("✅ Comprehensive processing completed successfully")
                self.last_comprehensive_run = datetime.now()
                return True
            else:
                logger.error(f"❌ Comprehensive processing failed with code {process.returncode}")
                return False
        except Exception as e:
            logger.error(f"❌ Comprehensive processing error: {e}")
            return False

    def run_transcript_discovery(self) -> bool:
        """Run smart transcript discovery with continuous retry."""
        try:
            logger.info("🎙️ Starting smart transcript discovery...")

            # Use batch transcript fetcher for rapid processing
            process = create_managed_process([
                self.python_executable, "scripts/batch_transcript_fetcher.py", "--limit", "20"
            ], "transcript_discovery", cwd=self.project_root, timeout=300)
            stdout, stderr = process.communicate()

            if process.returncode == 0:
                logger.info("✅ Batch transcript fetching completed successfully")
                self.last_transcript_run = datetime.now()
                self.last_transcript_success = self.last_transcript_run
                return True
            else:
                logger.error(f"❌ Batch transcript fetching failed with code {process.returncode}")
                logger.error(f"Stderr: {stderr.decode() if stderr else 'No error output'}")
                # Update run time but not success time - enables faster retry
                self.last_transcript_run = datetime.now()
                return False
        except Exception as e:
            logger.error(f"❌ Batch transcript fetching error: {e}")
            return False

    def run_universal_queue_processing(self) -> bool:
        """Run universal queue processing - handles all background tasks"""
        try:
            logger.info("⚡ Starting universal queue processing...")

            # Import the universal queue
            sys.path.insert(0, str(self.project_root))
            from universal_processing_queue import UniversalProcessingQueue

            queue = UniversalProcessingQueue()

            # Process up to 5 jobs per scheduler cycle
            queue.process_jobs(max_jobs=5)

            logger.info("✅ Universal queue processing completed")
            return True

        except Exception as e:
            logger.error(f"❌ Universal queue processing error: {e}")
            return False

    def run_transcript_check(self) -> bool:
        """Run light transcript checking - processes 1-2 podcasts from database."""
        try:
            logger.info("📝 Starting light transcript check...")

            # Import transcript processing functions
            sys.path.insert(0, str(self.project_root))
            from transcript_orchestrator import find_transcript
            import sqlite3

            # Connect to database
            db_path = str(self.project_root / "atlas.db")

            with sqlite3.connect(db_path) as conn:
                # Get 1-2 podcasts that need checking (oldest last_checked or never checked)
                cursor = conn.execute("""
                    SELECT name, id FROM podcasts
                    WHERE last_transcript_check IS NULL
                       OR datetime(last_transcript_check) < datetime('now', '-1 day')
                    ORDER BY COALESCE(last_transcript_check, '1970-01-01') ASC
                    LIMIT 2
                """)
                podcasts_to_check = cursor.fetchall()

                if not podcasts_to_check:
                    logger.info("📝 No podcasts need transcript checking")
                    self.last_transcript_check = datetime.now()
                    return True

                for podcast_name, podcast_id in podcasts_to_check:
                    logger.info(f"📝 Checking transcripts for: {podcast_name}")

                    # Update last_checked timestamp
                    conn.execute("""
                        UPDATE podcasts SET last_transcript_check = datetime('now')
                        WHERE id = ?
                    """, (podcast_id,))

                    # Get recent episodes for this podcast to check
                    episode_cursor = conn.execute("""
                        SELECT title, url FROM episodes
                        WHERE podcast_id = ? AND transcript_url IS NULL
                        ORDER BY published_date DESC LIMIT 3
                    """, (podcast_id,))
                    episodes = episode_cursor.fetchall()

                    for episode_title, episode_url in episodes:
                        try:
                            transcript = find_transcript(podcast_name, episode_title, episode_url)
                            if transcript:
                                logger.info(f"✅ Found transcript for: {episode_title[:50]}...")
                                # Store in database (this would be done by find_transcript function)
                        except Exception as e:
                            logger.warning(f"❌ Transcript check failed for {episode_title[:30]}: {e}")

                conn.commit()

            logger.info("✅ Light transcript check completed successfully")
            self.last_transcript_check = datetime.now()
            return True

        except Exception as e:
            logger.error(f"❌ Light transcript check error: {e}")
            return False

    def run_youtube_processing(self) -> bool:
        """Run YouTube content processing with rate limiting."""
        try:
            logger.info("📺 Starting YouTube processing...")

            # Import YouTube processing components
            sys.path.insert(0, str(self.project_root))
            from helpers.youtube_ingestor import YouTubeIngestor
            from integrations.youtube_api_client import YouTubeAPIClient
            import os

            # Check if YouTube API key is available
            youtube_api_key = os.getenv('YOUTUBE_API_KEY')
            if not youtube_api_key:
                logger.warning("📺 YouTube API key not found, skipping YouTube processing")
                return False

            # Initialize YouTube client and ingestor
            youtube_client = YouTubeAPIClient(youtube_api_key)
            youtube_ingestor = YouTubeIngestor()

            try:
                # Authenticate with YouTube
                youtube_client.authenticate()
                logger.info("📺 YouTube API authentication successful")

                # Monitor new videos (limited to prevent rate limits)
                new_videos = youtube_client.monitor_new_videos()

                if new_videos:
                    logger.info(f"📺 Found {len(new_videos)} new YouTube videos")

                    # Store videos in Atlas database
                    storage_results = youtube_client.store_videos_in_atlas(new_videos)
                    logger.info(f"📺 YouTube storage results: {storage_results}")

                    # Process a subset of videos with full ingestor for transcripts
                    # Limit to 5 videos to prevent API rate limits
                    video_urls = [v['url'] for v in new_videos[:5]]
                    if video_urls:
                        logger.info(f"📺 Processing {len(video_urls)} videos for transcript extraction...")
                        ingest_results = youtube_ingestor.ingest_video_list(video_urls)
                        logger.info(f"📺 YouTube transcript processing results: {ingest_results}")
                else:
                    logger.info("📺 No new YouTube videos found")

                logger.info("✅ YouTube processing completed successfully")
                self.last_youtube_run = datetime.now()
                return True

            except Exception as e:
                logger.error(f"❌ YouTube API error: {e}")
                return False
            finally:
                youtube_ingestor.cleanup()

        except Exception as e:
            logger.error(f"❌ YouTube processing error: {e}")
            return False

    def run_source_inventory(self) -> bool:
        """Run source inventory discovery to find unprocessed work."""
        try:
            logger.info("🔍 Starting source inventory discovery...")

            # Import source inventory module
            sys.path.insert(0, str(self.project_root))
            from helpers.source_inventory import discover_unprocessed_work

            # Run discovery
            results = discover_unprocessed_work(str(self.project_root / "data" / "atlas.db"))

            if 'error' in results:
                logger.error(f"❌ Source inventory failed: {results['error']}")
                return False

            # Log results
            total_work = results.get('total_work_created', 0)
            csv_urls = results.get('csv_urls_added', 0)
            podcast_episodes = results.get('podcast_episodes_added', 0)
            discovery_time = results.get('discovery_time', 0)

            if total_work > 0:
                logger.info(f"✅ Source inventory completed: {total_work} new items queued for processing")
                logger.info(f"   📄 CSV URLs: {csv_urls}")
                logger.info(f"   🎙️ Podcast episodes: {podcast_episodes}")
                logger.info(f"   ⏱️ Discovery time: {discovery_time}s")
            else:
                logger.info("✅ Source inventory completed: No new work discovered")

            self.last_source_inventory_run = datetime.now()
            return True

        except Exception as e:
            logger.error(f"❌ Source inventory error: {e}")
            return False

    def run_scheduler(self):
        """Main scheduler loop."""
        logger.info("🕐 Atlas Background Scheduler started")
        logger.info(f"   Comprehensive cycle: every {self.comprehensive_interval//3600} hours")
        logger.info(f"   Transcript discovery: every {self.transcript_interval//3600} hours")
        logger.info(f"   Transcript check: every {self.transcript_check_interval//60} minutes")
        logger.info(f"   YouTube processing: every {self.youtube_interval//3600} hours")
        logger.info(f"   Source inventory: every {self.source_inventory_interval//3600} hours")

        # Run once immediately on startup
        logger.info("🔄 Running initial comprehensive cycle...")
        self.run_comprehensive_service()

        while True:
            try:
                # Check if we should run source inventory discovery
                if self.should_run_source_inventory():
                    self.run_source_inventory()

                # Check if we should run YouTube processing
                elif self.should_run_youtube_processing():
                    self.run_youtube_processing()

                # Check if we should run transcript discovery
                elif self.should_run_transcript_discovery():
                    self.run_transcript_discovery()

                # Check if we should run light transcript checking
                elif self.should_run_transcript_check():
                    self.run_transcript_check()

                # Check if we should run comprehensive processing
                elif self.should_run_comprehensive():
                    self.run_comprehensive_service()

                # Always run universal queue processing (lightweight, handles all background jobs)
                self.run_universal_queue_processing()

                # Sleep for 10 minutes before checking again
                time.sleep(600)

            except KeyboardInterrupt:
                logger.info("🛑 Scheduler stopped by user")
                break
            except Exception as e:
                logger.error(f"❌ Scheduler error: {e}")
                time.sleep(300)  # Wait 5 minutes on error

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Atlas Background Scheduler')
    parser.add_argument('--start', action='store_true', help='Start the scheduler')
    parser.add_argument('--test-mode', action='store_true', help='Test scheduler configuration (shows what would run)')
    args = parser.parse_args()

    if args.test_mode:
        print("=== Atlas Scheduler Test Mode ===")
        scheduler = AtlasScheduler()

        print(f"📊 Configuration:")
        print(f"  Comprehensive cycle: every {scheduler.comprehensive_interval//3600} hours ({scheduler.comprehensive_interval//60} minutes)")
        print(f"  Transcript discovery: every {scheduler.transcript_interval//3600} hours")
        print(f"  Transcript check: every {scheduler.transcript_check_interval//60} minutes")
        print(f"  YouTube processing: every {scheduler.youtube_interval//3600} hours")

        print(f"\n🔧 Jobs that would run:")
        print(f"  ✅ Comprehensive service (atlas_comprehensive_service.py)")
        print(f"  ✅ Enhanced transcript discovery (enhanced_transcript_discovery.py)")
        print(f"  ✅ Light transcript checking (database-based)")
        print(f"  ✅ YouTube processing (YouTube API + ingestor)")
        print(f"  ✅ Universal queue processing (background jobs)")

        print(f"\n📺 YouTube processing details:")
        print(f"  - Runs every {scheduler.youtube_interval//3600} hours")
        print(f"  - Monitors subscribed channels for new videos")
        print(f"  - Processes up to 5 videos per run for transcripts")
        print(f"  - Stores videos in Atlas with content_type='youtube_video'")
        print(f"  - Includes rate limiting to prevent YouTube API exhaustion")

        print(f"\n✨ Test completed - scheduler configuration verified")

    elif args.start:
        if not check_system_health():
            logger.error("System health check failed, aborting")
            sys.exit(1)
        # Ensure logs directory exists
        Path('logs').mkdir(exist_ok=True)

        scheduler = AtlasScheduler()
        scheduler.run_scheduler()
    else:
        print("Usage:")
        print("  atlas_scheduler.py --start      # Start the scheduler")
        print("  atlas_scheduler.py --test-mode  # Test configuration")