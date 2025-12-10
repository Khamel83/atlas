#!/usr/bin/env python3
"""
ATLAS MANAGEMENT SYSTEM - FULLY AUTOMATED
Runs continuously without manual intervention
"""

import sqlite3
import csv
import feedparser
import schedule
import threading
import time
import subprocess
import os
import signal
import sys
from datetime import datetime, timedelta
import logging
import json
from contextlib import contextmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/atlas_manager.log'),
        logging.StreamHandler()
    ]
)

class AtlasManager:
    def __init__(self):
        # Use WAL mode and timeout for better concurrent access
        self.conn = sqlite3.connect('data/atlas.db', timeout=30.0)
        self.cursor = self.conn.cursor()

        # Enable WAL mode for better concurrent access
        self.cursor.execute('PRAGMA journal_mode=WAL')
        self.cursor.execute('PRAGMA busy_timeout=30000')
        self.conn.commit()
        self.running = True

        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)

        # Load configurations
        self.load_configurations()

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        logging.info("Atlas Manager initialized")
        logging.info(f"Total transcripts in database: {self.get_transcript_count()}")
        logging.info(f"Queue status: {self.get_queue_status()}")

    @contextmanager
    def db_operation(self, max_retries=3):
        """Context manager for database operations with retry logic"""
        for attempt in range(max_retries):
            try:
                yield self.conn
                return
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    logging.warning(f"Database locked, retrying (attempt {attempt + 1}/{max_retries})")
                    time.sleep(1)
                else:
                    raise
            except Exception as e:
                logging.error(f"Database operation failed: {e}")
                raise

    def load_configurations(self):
        """Load podcast configurations"""
        self.user_podcasts = []
        with open('config/podcast_config.csv', 'r') as f:
            reader = csv.reader(f)
            next(reader)
            for row in reader:
                if len(row) >= 6 and row[5] == '0':
                    self.user_podcasts.append({
                        'name': row[1].strip('"'),
                        'count': int(row[2]) if row[2].isdigit() else 0,
                        'future': row[3] == '1',
                        'transcript_only': row[4] == '1'
                    })

        self.rss_mappings = {}
        with open('config/podcast_rss_feeds.csv', 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2:
                    self.rss_mappings[row[0].strip('"')] = row[1].strip('"')

        logging.info(f"Loaded {len(self.user_podcasts)} user podcasts")
        logging.info(f"Loaded {len(self.rss_mappings)} RSS mappings")

    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logging.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False

    def get_transcript_count(self):
        """Get current transcript count"""
        return self.cursor.execute(
            "SELECT COUNT(*) FROM content WHERE content_type = 'podcast_transcript'"
        ).fetchone()[0]

    def get_queue_status(self):
        """Get current queue status"""
        status = self.cursor.execute(
            "SELECT status, COUNT(*) FROM episode_queue GROUP BY status"
        ).fetchall()
        return dict(status)

    def check_and_add_new_episodes(self):
        """Check for and add new episodes since September 1, 2025"""
        logging.info("Checking for new episodes since September 1, 2025")

        cutoff_date = datetime(2025, 9, 1)
        future_podcasts = [p for p in self.user_podcasts if p['future'] and p['name'] in self.rss_mappings]

        total_added = 0

        for podcast in future_podcasts:
            podcast_name = podcast['name']
            rss_url = self.rss_mappings[podcast_name]

            try:
                feed = feedparser.parse(rss_url)
                new_episodes = []

                for entry in feed.entries:
                    pub_date = entry.get('published_parsed')
                    if pub_date:
                        pub_datetime = datetime(*pub_date[:6])

                        if pub_datetime >= cutoff_date:
                            episode_url = entry.get('link', '')
                            if episode_url:
                                # Check if already in queue or processed
                                existing = self.cursor.execute(
                                    "SELECT id FROM episode_queue WHERE episode_url = ? UNION "
                                    "SELECT id FROM content WHERE url = ?",
                                    (episode_url, episode_url)
                                ).fetchone()

                                if not existing:
                                    new_episodes.append({
                                        'title': entry.get('title', 'Untitled Episode'),
                                        'url': episode_url,
                                        'pub_date': pub_datetime
                                    })

                if new_episodes:
                    # Add to queue
                    for episode in new_episodes:
                        self.cursor.execute("""
                            INSERT INTO episode_queue
                            (podcast_name, episode_title, episode_url, rss_url, status, created_at, updated_at)
                            VALUES (?, ?, ?, ?, 'pending', ?, ?)
                        """, (
                            podcast_name,
                            episode['title'],
                            episode['url'],
                            rss_url,
                            datetime.now().isoformat(),
                            datetime.now().isoformat()
                        ))
                        total_added += 1

                    logging.info(f"Added {len(new_episodes)} episodes for {podcast_name}")

                time.sleep(0.5)  # Rate limiting

            except Exception as e:
                logging.error(f"Error checking {podcast_name}: {e}")

        self.conn.commit()
        logging.info(f"Total new episodes added: {total_added}")
        return total_added

    def process_queue_batch(self, batch_size=20):
        """Process a batch of queued episodes"""
        logging.info(f"Processing batch of {batch_size} episodes")

        # Get pending episodes
        pending = self.cursor.execute(
            "SELECT id, podcast_name, episode_title, episode_url FROM episode_queue "
            "WHERE status = 'pending' LIMIT ?",
            (batch_size,)
        ).fetchall()

        if not pending:
            logging.info("No pending episodes to process")
            return 0

        processed = 0
        found = 0

        for episode_id, podcast_name, episode_title, episode_url in pending:
            try:
                # Run episode processor in subprocess
                result = subprocess.run([
                    'python3', 'single_episode_processor.py',
                    str(episode_id),
                    episode_url,
                    podcast_name
                ], capture_output=True, text=True, timeout=60)

                if result.returncode == 0:
                    # Update status based on result
                    if 'transcript found' in result.stdout.lower():
                        self.cursor.execute(
                            "UPDATE episode_queue SET status = 'found', updated_at = ? WHERE id = ?",
                            (datetime.now().isoformat(), episode_id)
                        )
                        found += 1
                    else:
                        self.cursor.execute(
                            "UPDATE episode_queue SET status = 'not_found', updated_at = ? WHERE id = ?",
                            (datetime.now().isoformat(), episode_id)
                        )
                    processed += 1
                else:
                    self.cursor.execute(
                        "UPDATE episode_queue SET status = 'error', updated_at = ? WHERE id = ?",
                        (datetime.now().isoformat(), episode_id)
                    )
                    logging.error(f"Error processing episode {episode_id}: {result.stderr}")

            except Exception as e:
                self.cursor.execute(
                    "UPDATE episode_queue SET status = 'error', updated_at = ? WHERE id = ?",
                    (datetime.now().isoformat(), episode_id)
                )
                logging.error(f"Exception processing episode {episode_id}: {e}")

        self.conn.commit()
        logging.info(f"Processed {processed} episodes, found {found} transcripts")
        return processed

    def retry_failed_episodes(self, batch_size=30):
        """Retry previously failed episodes with intelligent retry logic"""
        logging.info(f"Retrying {batch_size} failed episodes with enhanced logic")

        try:
            # Use simple retry handler
            from simple_retry_handler import SimpleRetryHandler
            handler = SimpleRetryHandler()
            results = handler.process_failed_batch(batch_size)

            # Log results
            logging.info(f"Simple retry completed: {results}")

            # Also run the original retry processor for any newly queued episodes
            from retry_failed_episodes import retry_failed_episodes
            success_count = retry_failed_episodes(batch_size)

            logging.info(f"Original retry completed: {success_count} new transcripts extracted")
            return success_count

        except Exception as e:
            logging.error(f"Error in simple retry process: {e}")
            return 0

    def process_url_ingestion(self, batch_size=5):
        """Process URLs from the universal ingestion system"""
        logging.info(f"Processing {batch_size} URLs from ingestion system")

        try:
            from url_ingestion_service import AtlasIngestionService
            service = AtlasIngestionService()
            result = service.process_pending_batch(batch_size)
            logging.info(f"URL ingestion result: {result}")
            return result.get('success', 0)
        except Exception as e:
            logging.error(f"Error processing URL ingestion: {e}")
            return 0

    def maintenance_tasks(self):
        """Perform routine maintenance"""
        logging.info("Running maintenance tasks")

        # Clean up old error entries
        week_ago = datetime.now() - timedelta(days=7)
        deleted = self.cursor.execute(
            "DELETE FROM episode_queue WHERE status = 'error' AND updated_at < ?",
            (week_ago.isoformat(),)
        ).rowcount

        # Commit transaction before VACUUM
        self.conn.commit()

        # Compact database if needed (VACUUM requires no active transaction)
        try:
            self.conn.execute("VACUUM")
        except Exception as e:
            logging.warning(f"VACUUM failed: {e}")
            # Continue even if VACUUM fails

        logging.info(f"Cleaned up {deleted} old error entries")

        # Log current status
        transcripts = self.get_transcript_count()
        queue_status = self.get_queue_status()

        logging.info(f"Current status: {transcripts} transcripts, queue: {queue_status}")

    def hourly_tasks(self):
        """Tasks that run every hour"""
        logging.info("Running hourly tasks")

        # Process a batch of queue items
        self.process_queue_batch(batch_size=50)

        # Retry failed episodes with improved patterns
        self.retry_failed_episodes(batch_size=30)

        # Process URLs from universal ingestion system
        self.process_url_ingestion(batch_size=5)

        # Check if we need to add more episodes
        pending_count = self.cursor.execute(
            "SELECT COUNT(*) FROM episode_queue WHERE status = 'pending'"
        ).fetchone()[0]

        if pending_count < 1000:
            self.check_and_add_new_episodes()

    def daily_tasks(self):
        """Tasks that run daily"""
        logging.info("Running daily tasks")

        # Check for new episodes from all future podcasts
        self.check_and_add_new_episodes()

        # Process larger batch
        self.process_queue_batch(batch_size=100)

        # Run maintenance
        self.maintenance_tasks()

    def setup_scheduler(self):
        """Setup the task scheduler"""
        # Daily tasks at 9:00 AM
        schedule.every().day.at("09:00").do(self.daily_tasks)

        # Weekly summary on Monday at 2:00 PM
        schedule.every().monday.at("14:00").do(self.maintenance_tasks)

        # Hourly tasks
        schedule.every().hour.do(self.hourly_tasks)

    def run_continuous(self):
        """Run continuous processing loop"""
        logging.info("Starting continuous processing loop")

        self.setup_scheduler()

        while self.running:
            try:
                # Run scheduled tasks
                schedule.run_pending()

                # If no scheduled tasks, process larger batches continuously
                if not schedule.jobs:
                    self.process_queue_batch(batch_size=50)

                # Sleep for a shorter interval for faster processing
                time.sleep(30)  # 30 seconds instead of 5 minutes

            except KeyboardInterrupt:
                logging.info("Received keyboard interrupt, shutting down...")
                self.running = False
            except Exception as e:
                logging.error(f"Error in continuous loop: {e}")
                time.sleep(60)  # Wait a minute before retrying

    def run(self):
        """Main entry point"""
        logging.info("Starting Atlas Manager")

        try:
            # Initial setup
            self.check_and_add_new_episodes()
            self.maintenance_tasks()

            # Start continuous processing
            self.run_continuous()

        except Exception as e:
            logging.error(f"Fatal error: {e}")
            raise
        finally:
            logging.info("Atlas Manager shutting down")
            self.conn.close()

def main():
    """Start the Atlas Manager"""
    print("🚀 STARTING ATLAS MANAGEMENT SYSTEM")
    print("=" * 60)
    print("This system will run continuously and automatically:")
    print("• Check for new podcast episodes")
    print("• Process transcripts from queued episodes")
    print("• Perform maintenance tasks")
    print("• No manual intervention required")
    print("=" * 60)

    manager = AtlasManager()
    manager.run()

if __name__ == "__main__":
    main()