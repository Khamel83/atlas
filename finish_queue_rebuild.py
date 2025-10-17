#!/usr/bin/env python3
"""
FINISH REBUILDING THE QUEUE WITH ALL 20 PODCASTS
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
        logging.FileHandler('logs/finish_queue_rebuild.log'),
        logging.StreamHandler()
    ]
)

class QueueFinisher:
    def __init__(self):
        self.conn = sqlite3.connect('data/atlas.db')
        self.cursor = self.conn.cursor()

        # All 20 priority podcast feeds
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

    def check_existing_episodes(self):
        """Check which podcasts already have episodes in queue"""
        self.cursor.execute('''
            SELECT COUNT(*) as count, SUBSTR(title, 1, 100) as sample
            FROM content WHERE content_type = 'podcast_episode'
            GROUP BY SUBSTR(title, 1, 30)
            ORDER BY count DESC
        ''')

        existing = self.cursor.fetchall()
        logging.info("📊 Current episodes in queue:")
        for count, sample in existing:
            logging.info(f"  - {sample}: {count} episodes")

        return len(existing)

    def add_episodes_from_feed(self, podcast_name, rss_url):
        """Add episodes from a specific feed"""

        try:
            # Check if we already have episodes from this podcast
            self.cursor.execute('''
                SELECT COUNT(*) FROM content
                WHERE content_type = 'podcast_episode' AND title LIKE ?
            ''', (f'%{podcast_name}%',))

            existing_count = self.cursor.fetchone()[0]
            if existing_count > 0:
                logging.info(f"  ⏭️  Skipping {podcast_name} (already has {existing_count} episodes)")
                return 0

            logging.info(f"  🔄 Processing {podcast_name}...")

            # Parse RSS feed
            feed = feedparser.parse(rss_url)

            if not feed.entries:
                logging.warning(f"    ❌ No entries found in feed")
                return 0

            logging.info(f"    Found {len(feed.entries)} episodes")

            episodes_added = 0

            # Process all episodes from this feed
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

                if episodes_added % 50 == 0:
                    logging.info(f"    📊 Added {episodes_added} episodes so far...")

                # Rate limiting
                time.sleep(0.05)

            self.conn.commit()
            logging.info(f"    ✅ Added {episodes_added} episodes from {podcast_name}")
            return episodes_added

        except Exception as e:
            logging.error(f"    ❌ Error processing {podcast_name}: {e}")
            return 0

    def finish_queue_rebuild(self):
        """Complete the queue rebuild with all remaining podcasts"""

        logging.info("🚀 FINISHING QUEUE REBUILD - ALL 20 PODCASTS")
        logging.info("=" * 80)

        # Check current status
        current_podcasts = self.check_existing_episodes()
        logging.info(f"\n📊 Currently have episodes from {current_podcasts} podcasts")

        # Process remaining podcasts
        total_added = 0
        successful_feeds = 0

        for i, (podcast_name, rss_url) in enumerate(self.priority_feeds.items(), 1):
            logging.info(f"\n[{i}/20] {podcast_name}")

            added = self.add_episodes_from_feed(podcast_name, rss_url)
            if added > 0:
                total_added += added
                successful_feeds += 1

        # Final summary
        logging.info("\n" + "=" * 80)
        logging.info("🎉 QUEUE REBUILD COMPLETE!")
        logging.info("=" * 80)
        logging.info(f"📊 New episodes added: {total_added}")
        logging.info(f"📋 Successful feeds: {successful_feeds}/20")

        # Check final status
        final_count = self.cursor.execute('''
            SELECT COUNT(*) FROM content WHERE content_type = 'podcast_episode'
        ''').fetchone()[0]

        logging.info(f"🎯 Total episodes in queue: {final_count}")
        logging.info("=" * 80)

        self.conn.close()

def main():
    finisher = QueueFinisher()
    finisher.finish_queue_rebuild()

if __name__ == "__main__":
    main()