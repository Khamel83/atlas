#!/usr/bin/env python3
"""
Build queue with JUST the user's 16 target podcasts
"""

import sqlite3
import feedparser
import time
import logging
from datetime import datetime
import csv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/targeted_queue.log'),
        logging.StreamHandler()
    ]
)

class TargetedQueueBuilder:
    def __init__(self):
        self.conn = sqlite3.connect('data/atlas.db')
        self.cursor = self.conn.cursor()

        # Load user's target podcasts from config
        self.target_podcasts = {}
        with open('config/podcasts.csv', 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['Exclude'] == '0':  # Only include non-excluded podcasts
                    self.target_podcasts[row['Podcast Name']] = row['RSS URL']

    def add_episodes_from_feed(self, podcast_name, rss_url):
        """Add ALL episodes from a specific feed"""

        try:
            logging.info(f"🔄 Processing {podcast_name}...")
            logging.info(f"  RSS: {rss_url}")

            # Parse RSS feed
            feed = feedparser.parse(rss_url)

            if not feed.entries:
                logging.warning(f"  ❌ No entries found in feed")
                return 0

            logging.info(f"  Found {len(feed.entries)} episodes")

            episodes_added = 0
            episodes_processed = 0

            # Process ALL episodes from this feed
            for entry in feed.entries:
                episode_url = entry.get('link', '')
                if not episode_url:
                    continue

                title = entry.get('title', 'Untitled Episode')

                # Check if already exists
                self.cursor.execute('''
                    SELECT COUNT(*) FROM content
                    WHERE url = ? AND content_type = 'podcast_episode'
                ''', (episode_url,))
                exists = self.cursor.fetchone()[0]

                if exists:
                    continue

                # Add to queue
                self.cursor.execute('''
                    INSERT INTO content (title, url, content_type, created_at, updated_at)
                    VALUES (?, ?, 'podcast_episode', ?, ?)
                ''', (f"[PODCAST] {title}", episode_url, datetime.now().isoformat(), datetime.now().isoformat()))

                episodes_added += 1
                episodes_processed += 1

                # Progress updates
                if episodes_processed % 50 == 0:
                    logging.info(f"  📊 Processed {episodes_processed}/{len(feed.entries)} episodes, added {episodes_added}")

                # Rate limiting
                time.sleep(0.1)

            self.conn.commit()
            logging.info(f"  ✅ Added {episodes_added} episodes from {podcast_name}")
            return episodes_added

        except Exception as e:
            logging.error(f"  ❌ Error processing {podcast_name}: {e}")
            return 0

    def build_targeted_queue(self):
        """Build queue with only the user's target podcasts"""

        logging.info("🎯 BUILDING TARGETED QUEUE - USER'S 16 PODCASTS")
        logging.info("=" * 80)
        logging.info(f"📋 Target podcasts: {len(self.target_podcasts)}")
        logging.info("🎯 Goal: ALL episodes from each target podcast")
        logging.info("=" * 80)

        # List target podcasts
        logging.info("📋 Target podcasts:")
        for i, (podcast_name, rss_url) in enumerate(self.target_podcasts.items(), 1):
            logging.info(f"  {i}. {podcast_name}")

        total_episodes = 0
        successful_feeds = 0

        # Process each target podcast
        for i, (podcast_name, rss_url) in enumerate(self.target_podcasts.items(), 1):
            logging.info(f"\n[{i}/{len(self.target_podcasts)}] {podcast_name}")

            added = self.add_episodes_from_feed(podcast_name, rss_url)
            if added > 0:
                total_episodes += added
                successful_feeds += 1

        # Final summary
        logging.info("\n" + "=" * 80)
        logging.info("🎉 TARGETED QUEUE BUILD COMPLETE!")
        logging.info("=" * 80)
        logging.info(f"📊 Total episodes added: {total_episodes}")
        logging.info(f"📋 Successful feeds: {successful_feeds}/{len(self.target_podcasts)}")
        logging.info("🚀 Ready for transcript extraction!")
        logging.info("=" * 80)

        self.conn.close()

        return total_episodes

def main():
    builder = TargetedQueueBuilder()
    total_episodes = builder.build_targeted_queue()
    print(f"\n✅ Built targeted queue with {total_episodes} episodes!")

if __name__ == "__main__":
    main()