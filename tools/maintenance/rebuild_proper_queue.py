#!/usr/bin/env python3
"""
REBUILD PROPER EPISODE QUEUE WITH ACTUAL URLs FROM RSS FEEDS
"""

import sqlite3
import feedparser
import time
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/rebuild_queue.log'),
        logging.StreamHandler()
    ]
)

class QueueRebuilder:
    def __init__(self):
        self.conn = sqlite3.connect('data/atlas.db')
        self.cursor = self.conn.cursor()

        # Priority podcast feeds with their RSS URLs
        self.priority_feeds = {
            "Lex Fridman Podcast": "https://lexfridman.com/feed/podcast/",
            "EconTalk": "https://feeds.simplecast.com/wgl4xEgL",
            "Conversations with Tyler": "https://cowenconvos.libsyn.com/rss",
            "This American Life": "https://www.thisamericanlife.org/podcast/rss.xml",
            "99% Invisible": "https://feeds.simplecast.com/BqbsxVfO",
            "Radiolab": "https://feeds.simplecast.com/EmVW7VGp",
            "Planet Money": "https://feeds.npr.org/510289/podcast.xml",
            "The Knowledge Project with Shane Parrish": "https://feeds.megaphone.fm/FSMI7575968096",
            "Practical AI": "https://feeds.transistor.fm/practical-ai-machine-learning-data-science-llm",
            "Acquired": "https://feeds.transistor.fm/acquired",
            "Hard Fork": "https://feeds.simplecast.com/l2i9YnTd",
            "The Ezra Klein Show": "https://feeds.simplecast.com/82FI35Px",
            "ACQ2 by Acquired": "https://feeds.transistor.fm/acq2",
            "Accidental Tech Podcast": "https://cdn.atp.fm/rss/public?wtvryzdm",
            "Cortex": "https://www.relay.fm/cortex/feed",
            "Exponent": "https://exponent.fm/feed/",
            "The Vergecast": "https://feeds.megaphone.fm/vergecast",
            "Decoder with Nilay Patel": "https://feeds.megaphone.fm/recodedecode",
            "The Big Picture": "https://feeds.megaphone.fm/the-big-picture",
            "The Rewatchables": "https://feeds.megaphone.fm/the-rewatchables"
        }

    def add_episode_to_queue(self, podcast_name, title, url, pub_date):
        """Add a single episode to the queue"""

        try:
            # Check if episode already exists
            self.cursor.execute('''
                SELECT COUNT(*) FROM content
                WHERE url = ? AND content_type = 'podcast_episode'
            ''', (url,))
            exists = self.cursor.fetchone()[0]

            if exists:
                return False

            # Add to queue
            self.cursor.execute('''
                INSERT INTO content (title, url, content_type, created_at, updated_at)
                VALUES (?, ?, 'podcast_episode', ?, ?)
            ''', (f"[PODCAST] {title}", url, datetime.now().isoformat(), datetime.now().isoformat()))

            self.conn.commit()
            return True

        except Exception as e:
            logging.error(f"Error adding episode: {e}")
            return False

    def rebuild_queue_from_feeds(self):
        """Rebuild the entire queue from RSS feeds"""

        logging.info("🔄 REBUILDING PROPER EPISODE QUEUE")
        logging.info("=" * 80)
        logging.info(f"📋 Processing {len(self.priority_feeds)} podcast feeds")
        logging.info("🎯 Goal: Build comprehensive queue with actual URLs")
        logging.info("=" * 80)

        total_episodes = 0
        successful_feeds = 0

        for i, (podcast_name, rss_url) in enumerate(self.priority_feeds.items(), 1):
            logging.info(f"\n[{i}/{len(self.priority_feeds)}] Processing: {podcast_name}")
            logging.info(f"RSS: {rss_url}")

            try:
                # Parse RSS feed
                feed = feedparser.parse(rss_url)

                if not feed.entries:
                    logging.warning(f"  ❌ No entries found in feed")
                    continue

                logging.info(f"  Found {len(feed.entries)} episodes in feed")

                episodes_added = 0
                episodes_processed = 0

                # Process all episodes from this feed
                for entry in feed.entries:
                    episode_url = entry.get('link', '')
                    if not episode_url:
                        continue

                    title = entry.get('title', 'Untitled Episode')
                    pub_date = entry.get('published', '')

                    episodes_processed += 1

                    # Add to queue
                    if self.add_episode_to_queue(podcast_name, title, episode_url, pub_date):
                        episodes_added += 1
                        total_episodes += 1

                    # Progress update
                    if episodes_processed % 25 == 0:
                        logging.info(f"  📊 Processed {episodes_processed}/{len(feed.entries)} episodes, added {episodes_added}")

                    # Rate limiting
                    time.sleep(0.1)

                logging.info(f"  ✅ Added {episodes_added} episodes from {podcast_name}")
                successful_feeds += 1

            except Exception as e:
                logging.error(f"  ❌ Error processing {podcast_name}: {e}")

        # Final summary
        logging.info("\n" + "=" * 80)
        logging.info("🎉 QUEUE REBUILD COMPLETE")
        logging.info("=" * 80)
        logging.info(f"📊 Total episodes added to queue: {total_episodes}")
        logging.info(f"📋 Successful feeds: {successful_feeds}/{len(self.priority_feeds)}")
        logging.info("🚀 Ready for transcript extraction!")
        logging.info("=" * 80)

        self.conn.close()

        return total_episodes

def main():
    rebuilder = QueueRebuilder()
    total_episodes = rebuilder.rebuild_queue_from_feeds()

    print(f"\n✅ Queue rebuilt with {total_episodes} episodes!")
    print("Now run: python3 process_entire_queue.py")

if __name__ == "__main__":
    main()