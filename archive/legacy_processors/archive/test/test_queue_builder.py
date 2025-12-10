#!/usr/bin/env python3
"""
Quick test of queue builder with first 5 podcasts
"""

import csv
import feedparser
import sqlite3
from datetime import datetime

class QuickTest:
    def __init__(self):
        self.conn = sqlite3.connect('data/atlas.db')
        self.cursor = self.conn.cursor()

        # Load RSS feed mappings
        self.rss_mappings = {}
        try:
            with open('config/podcast_rss_feeds.csv', 'r') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 2:
                        podcast_name = row[0].strip('"')
                        rss_url = row[1].strip('"')
                        self.rss_mappings[podcast_name] = rss_url
        except:
            self.rss_mappings = {}

        # Get first 5 user podcasts
        self.test_podcasts = []
        try:
            with open('config/podcast_config.csv', 'r') as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                for row in reader:
                    if len(row) >= 6 and row[5] == '0':  # Not excluded
                        podcast_name = row[1].strip('"')
                        if podcast_name in self.rss_mappings:
                            self.test_podcasts.append(podcast_name)
                            if len(self.test_podcasts) >= 5:
                                break
        except:
            pass

    def test_podcast(self, podcast_name):
        print(f"\nTesting: {podcast_name}")
        print(f"RSS: {self.rss_mappings[podcast_name]}")

        try:
            feed = feedparser.parse(self.rss_mappings[podcast_name])
            print(f"Found {len(feed.entries)} episodes")

            # Add first 3 episodes to queue
            for i, entry in enumerate(feed.entries[:3]):
                episode_url = entry.get('link', '')
                title = entry.get('title', 'Untitled Episode')

                self.cursor.execute("""
                    INSERT INTO episode_queue
                    (podcast_name, episode_title, episode_url, rss_url, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, 'pending', ?, ?)
                """, (
                    podcast_name,
                    title,
                    episode_url,
                    self.rss_mappings[podcast_name],
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))
                print(f"  Added: {title[:50]}...")

            self.conn.commit()
            print(f"✅ Added episodes for {podcast_name}")

        except Exception as e:
            print(f"❌ Error: {e}")

    def run_test(self):
        print("QUICK QUEUE TEST - First 5 Podcasts")
        print("=" * 50)

        for podcast in self.test_podcasts:
            self.test_podcast(podcast)

        total = self.cursor.execute("SELECT COUNT(*) FROM episode_queue").fetchone()[0]
        print(f"\nTotal episodes in queue: {total}")

        self.conn.close()

if __name__ == "__main__":
    test = QuickTest()
    test.run_test()