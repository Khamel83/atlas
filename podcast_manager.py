#!/usr/bin/env python3
"""
Ongoing Podcast Management System
Handles both historical processing and future content updates
"""

import sqlite3
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import json
import schedule
import threading
import csv

class PodcastManager:
    def __init__(self):
        self.conn = sqlite3.connect('data/atlas.db')
        self.cursor = self.conn.cursor()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

        # Load sources cache
        try:
            with open('config/podcast_sources_cache.json', 'r') as f:
                self.sources_cache = json.load(f)
        except:
            self.sources_cache = {}

        # Load user preferences
        self.user_podcasts = self.load_user_podcasts()
        self.rss_mappings = self.load_rss_mappings()

    def load_user_podcasts(self):
        """Load user podcast preferences"""
        podcasts = []
        with open('config/podcast_config.csv', 'r') as f:
            reader = csv.reader(f)
            next(reader)
            for row in reader:
                if len(row) >= 6 and row[5] == '0':  # Not excluded
                    podcasts.append({
                        'name': row[1].strip('"'),
                        'count': int(row[2]) if row[2].isdigit() else 0,
                        'future': row[3] == '1',
                        'transcript_only': row[4] == '1'
                    })
        return podcasts

    def load_rss_mappings(self):
        """Load RSS feed mappings"""
        mappings = {}
        with open('config/podcast_rss_feeds.csv', 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2:
                    mappings[row[0].strip('"')] = row[1].strip('"')
        return mappings

    def check_for_new_episodes(self, podcast_name, rss_url, last_processed_date=None):
        """Check for new episodes since September 1, 2025"""
        try:
            feed = feedparser.parse(rss_url)
            new_episodes = []

            # Define cutoff date as September 1, 2025
            cutoff_date = datetime(2025, 9, 1)

            for entry in feed.entries:
                pub_date = entry.get('published_parsed')
                if pub_date:
                    pub_datetime = datetime(*pub_date[:6])

                    # If this episode is newer than September 1, 2025
                    if pub_datetime >= cutoff_date:
                        new_episodes.append({
                            'title': entry.get('title', 'Untitled Episode'),
                            'url': entry.get('link', ''),
                            'pub_date': pub_datetime,
                            'description': entry.get('description', '')
                        })

            return new_episodes

        except Exception as e:
            print(f"Error checking {podcast_name}: {e}")
            return []

    def extract_transcript(self, episode_url, podcast_name):
        """Extract transcript from episode URL"""
        try:
            response = self.session.get(episode_url, timeout=15)
            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.content, 'html.parser')

            # Try cached patterns first
            for podcast_key, podcast_data in self.sources_cache.items():
                if podcast_name.lower() in podcast_key.lower():
                    network_config = podcast_data.get('config', {})
                    if 'selectors' in network_config:
                        for selector in network_config['selectors']:
                            element = soup.select_one(selector)
                            if element:
                                text = element.get_text(separator=' ', strip=True)
                                min_length = network_config.get('min_length', 1000)
                                if len(text) > min_length:
                                    return text

            # Generic selectors
            selectors = ['.transcript', '#transcript', '.episode-transcript', '[class*="transcript"]']
            for selector in selectors:
                element = soup.select_one(selector)
                if element:
                    text = element.get_text(separator=' ', strip=True)
                    if len(text) > 1000 and 'transcript' in text.lower():
                        return text

            return None

        except Exception as e:
            print(f"Extraction error for {podcast_name}: {e}")
            return None

    def process_new_episode(self, podcast_name, episode):
        """Process a single new episode"""
        print(f"Processing new episode: {podcast_name} - {episode['title']}")

        # Check if already processed
        existing = self.cursor.execute(
            "SELECT id FROM content WHERE url = ?", (episode['url'],)
        ).fetchone()

        if existing:
            print(f"  Already processed")
            return False

        # Try to extract transcript
        transcript = self.extract_transcript(episode['url'], podcast_name)

        if transcript:
            # Store transcript
            self.cursor.execute("""
                INSERT INTO content (title, url, content, content_type, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                f"[{podcast_name}] {episode['title']}",
                episode['url'],
                transcript,
                'podcast_transcript',
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))

            self.conn.commit()
            print(f"  ✅ Transcript extracted and stored ({len(transcript):,} chars)")
            return True
        else:
            print(f"  ❌ No transcript found")
            return False

    def process_future_podcasts(self):
        """Process podcasts with future=1 for episodes since September 1, 2025"""
        print("CHECKING FOR EPISODES SINCE SEPTEMBER 1, 2025 (FUTURE PODCASTS)")
        print("=" * 60)

        future_podcasts = [p for p in self.user_podcasts if p['future'] and p['name'] in self.rss_mappings]

        total_new_episodes = 0
        transcripts_found = 0

        for podcast in future_podcasts:
            podcast_name = podcast['name']
            rss_url = self.rss_mappings[podcast_name]

            print(f"\n🔄 {podcast_name}")

            # Check for episodes since September 1, 2025
            new_episodes = self.check_for_new_episodes(podcast_name, rss_url)

            if new_episodes:
                print(f"  Found {len(new_episodes)} new episodes")
                total_new_episodes += len(new_episodes)

                # Process each new episode
                for episode in new_episodes:
                    if self.process_new_episode(podcast_name, episode):
                        transcripts_found += 1

                # Small delay between podcasts
                time.sleep(1)
            else:
                print(f"  No episodes since September 1, 2025")

        print(f"\n{'='*60}")
        print("FUTURE PROCESSING COMPLETE")
        print(f"{'='*60}")
        print(f"Future podcasts checked: {len(future_podcasts)}")
        print(f"New episodes found: {total_new_episodes}")
        print(f"Transcripts extracted: {transcripts_found}")

    def get_processing_status(self):
        """Get current processing status"""
        # Queue status
        queue_status = self.cursor.execute("""
            SELECT status, COUNT(*) FROM episode_queue GROUP BY status
        """).fetchall()

        # Database status
        total_transcripts = self.cursor.execute("""
            SELECT COUNT(*) FROM content WHERE content_type = 'podcast_transcript'
        """).fetchone()[0]

        # Recent activity
        recent_transcripts = self.cursor.execute("""
            SELECT COUNT(*) FROM content
            WHERE content_type = 'podcast_transcript'
            AND created_at > datetime('now', '-7 days')
        """).fetchone()[0]

        print("\nPODCAST PROCESSING STATUS")
        print("=" * 50)
        print(f"Total transcripts in database: {total_transcripts:,}")
        print(f"Transcripts added in last 7 days: {recent_transcripts}")

        print(f"\nQueue Status:")
        for status, count in queue_status:
            print(f"  {status}: {count}")

        # Top podcasts by transcript count
        top_podcasts = self.cursor.execute("""
            SELECT
                SUBSTR(title, 2, INSTR(title, ']') - 2) as podcast_name,
                COUNT(*) as transcript_count
            FROM content
            WHERE content_type = 'podcast_transcript'
            GROUP BY podcast_name
            ORDER BY transcript_count DESC
            LIMIT 10
        """).fetchall()

        print(f"\nTop 10 Podcasts by Transcript Count:")
        for podcast, count in top_podcasts:
            print(f"  {podcast}: {count}")

    def run_scheduled_tasks(self):
        """Run all scheduled tasks"""
        print("RUNNING SCHEDULED PODCAST MANAGEMENT TASKS")
        print("=" * 60)

        # Process future podcasts for new episodes
        self.process_future_podcasts()

        # Process queue if it has pending items
        pending_count = self.cursor.execute(
            "SELECT COUNT(*) FROM episode_queue WHERE status = 'pending'"
        ).fetchone()[0]

        if pending_count > 0:
            print(f"\nProcessing {pending_count} pending queue items...")
            # You could integrate the episode processor here

        # Show status
        self.get_processing_status()

    def start_scheduler(self):
        """Start the background scheduler"""
        def job():
            try:
                self.run_scheduled_tasks()
            except Exception as e:
                print(f"Scheduler error: {e}")

        # Schedule tasks
        schedule.every().day.at("09:00").do(job)      # Daily check at 9 AM
        schedule.every().monday.at("14:00").do(job)    # Weekly check on Monday at 2 PM

        def run_continuously():
            while True:
                schedule.run_pending()
                time.sleep(3600)  # Check every hour

        # Start scheduler in background thread
        scheduler_thread = threading.Thread(target=run_continuously, daemon=True)
        scheduler_thread.start()

        print("📅 Podcast scheduler started")
        print("   - Daily checks at 9:00 AM")
        print("   - Weekly summaries on Monday at 2:00 PM")

def main():
    manager = PodcastManager()

    # Show current status
    manager.get_processing_status()

    # Process future podcasts once
    manager.process_future_podcasts()

    # Ask if user wants to start scheduler
    response = input("\nStart background scheduler for ongoing management? (y/n): ")
    if response.lower() == 'y':
        manager.start_scheduler()
        print("Scheduler started. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            print("Scheduler stopped.")

if __name__ == "__main__":
    main()