#!/usr/bin/env python3
"""
Daily processor for new episodes starting from this morning
"""

import sqlite3
import csv
import feedparser
from datetime import datetime, timedelta
import time
from podcast_manager import PodcastManager

class DailyProcessor(PodcastManager):
    def __init__(self):
        super().__init__()
        self.today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    def process_todays_episodes(self):
        """Process episodes published today"""
        print("PROCESSING TODAY'S EPISODES")
        print("=" * 50)
        print(f"Processing since: {self.today_start.strftime('%Y-%m-%d %H:%M')}")
        print()

        future_podcasts = [p for p in self.user_podcasts if p['future'] and p['name'] in self.rss_mappings]

        total_new = 0
        transcripts_found = 0

        for podcast in future_podcasts:
            podcast_name = podcast['name']
            rss_url = self.rss_mappings[podcast_name]

            print(f"🔄 {podcast_name}")

            try:
                feed = feedparser.parse(rss_url)
                today_episodes = []

                for entry in feed.entries:
                    pub_date = entry.get('published_parsed')
                    if pub_date:
                        pub_datetime = datetime(*pub_date[:6])

                        # Check if published today
                        if pub_datetime >= self.today_start:
                            today_episodes.append({
                                'title': entry.get('title', 'Untitled Episode'),
                                'url': entry.get('link', ''),
                                'pub_date': pub_datetime,
                                'description': entry.get('description', '')
                            })

                if today_episodes:
                    print(f"  Found {len(today_episodes)} episodes today")
                    total_new += len(today_episodes)

                    # Process each episode
                    for episode in today_episodes:
                        if self.process_new_episode(podcast_name, episode):
                            transcripts_found += 1
                else:
                    print(f"  No episodes today")

            except Exception as e:
                print(f"  ❌ Error: {e}")

            time.sleep(0.5)  # Small delay

        print(f"\n{'='*50}")
        print("DAILY PROCESSING COMPLETE")
        print(f"{'='*50}")
        print(f"Episodes processed: {total_new}")
        print(f"Transcripts found: {transcripts_found}")

        return total_new, transcripts_found

    def show_daily_summary(self):
        """Show summary of today's activity"""
        print("DAILY SUMMARY")
        print("-" * 30)

        # Today's transcripts
        today_transcripts = self.cursor.execute("""
            SELECT COUNT(*) FROM content
            WHERE content_type = 'podcast_transcript'
            AND created_at >= ?
        """, (self.today_start.isoformat(),)).fetchone()[0]

        # Queue activity
        queue_processed = self.cursor.execute("""
            SELECT COUNT(*) FROM episode_queue
            WHERE status IN ('found', 'not_found', 'error')
            AND updated_at >= ?
        """, (self.today_start.isoformat(),)).fetchone()[0]

        print(f"Transcripts added today: {today_transcripts}")
        print(f"Queue items processed: {queue_processed}")

        # Recent podcasts
        print(f"\nRecent transcripts:")
        self.cursor.execute("""
            SELECT title, created_at
            FROM content
            WHERE content_type = 'podcast_transcript'
            AND created_at >= ?
            ORDER BY created_at DESC
            LIMIT 5
        """)

        for title, created_at in self.cursor.fetchall():
            time_str = datetime.fromisoformat(created_at).strftime('%H:%M')
            print(f"  {time_str} - {title[:60]}...")

def main():
    print("DAILY PODCAST PROCESSOR")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    processor = DailyProcessor()

    # Show current status
    print("\nCURRENT STATUS")
    print("-" * 20)
    processor.get_processing_status()

    # Process today's episodes
    print("\nPROCESSING NEW EPISODES")
    processor.process_todays_episodes()

    # Show daily summary
    print("\n")
    processor.show_daily_summary()

    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()