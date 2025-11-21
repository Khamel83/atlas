#!/usr/bin/env python3
"""
Episode Queue Builder - Phase 1 Implementation
Builds complete episode queue from user's 68 podcasts with exact tracking
"""

import csv
import feedparser
import sqlite3
from datetime import datetime
import time
import random

class EpisodeQueueBuilder:
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

        # Get user's actual podcasts from their config
        self.user_podcasts = []
        try:
            with open('config/podcast_config.csv', 'r') as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                for row in reader:
                    if len(row) >= 6 and row[5] == '0':  # Not excluded
                        podcast_name = row[1].strip('"')
                        episode_count = int(row[2]) if row[2].isdigit() else 0
                        self.user_podcasts.append({
                            'name': podcast_name,
                            'requested_count': episode_count
                        })
        except:
            self.user_podcasts = []

        # Map user's podcasts to RSS feeds
        self.target_podcasts = {}
        for podcast in self.user_podcasts:
            if podcast['name'] in self.rss_mappings:
                self.target_podcasts[podcast['name']] = {
                    'rss_url': self.rss_mappings[podcast['name']],
                    'requested_count': podcast['requested_count']
                }

    def extract_episodes_from_rss(self, podcast_name, rss_url):
        """Extract all available episodes from RSS feed"""
        episodes = []

        try:
            feed = feedparser.parse(rss_url)

            if not feed.entries:
                return episodes

            # Process all available episodes
            for entry in feed.entries:
                episode_url = entry.get('link', '')
                if not episode_url:
                    continue

                title = entry.get('title', 'Untitled Episode')
                pub_date = entry.get('published', '')

                episodes.append({
                    'podcast_name': podcast_name,
                    'episode_title': title,
                    'episode_url': episode_url,
                    'rss_url': rss_url,
                    'pub_date': pub_date
                })

        except Exception as e:
            print(f"  ❌ RSS parsing error for {podcast_name}: {e}")

        return episodes

    def add_episode_to_queue(self, episode):
        """Add single episode to queue"""
        try:
            # Check if already exists
            existing = self.cursor.execute(
                "SELECT id FROM episode_queue WHERE episode_url = ?",
                (episode['episode_url'],)
            ).fetchone()

            if existing:
                return False

            # Insert new episode
            self.cursor.execute("""
                INSERT INTO episode_queue
                (podcast_name, episode_title, episode_url, rss_url, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'pending', ?, ?)
            """, (
                episode['podcast_name'],
                episode['episode_title'],
                episode['episode_url'],
                episode['rss_url'],
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))

            return True

        except Exception as e:
            print(f"    ❌ Database error: {e}")
            return False

    def build_complete_queue(self):
        """Build complete episode queue for all user podcasts"""

        print("EPISODE QUEUE BUILDER - PHASE 1")
        print("=" * 80)
        print(f"Target podcasts: {len(self.target_podcasts)}")
        print(f"RSS mappings available: {len(self.rss_mappings)}")
        print("=" * 80)

        total_episodes_added = 0
        podcast_summaries = []

        for i, (podcast_name, podcast_data) in enumerate(self.target_podcasts.items(), 1):

            print(f"\n[{i}/{len(self.target_podcasts)}] {podcast_name}")
            print(f"  RSS: {podcast_data['rss_url']}")
            print(f"  User requested: {podcast_data['requested_count']} episodes")

            # Extract episodes from RSS
            episodes = self.extract_episodes_from_rss(podcast_name, podcast_data['rss_url'])

            if not episodes:
                print(f"  ❌ No episodes found in RSS feed")
                podcast_summaries.append({
                    'name': podcast_name,
                    'requested': podcast_data['requested_count'],
                    'available': 0,
                    'added': 0
                })
                continue

            print(f"  Found {len(episodes)} episodes in RSS feed")

            # Limit to user's requested count if specified
            episodes_to_add = episodes
            if podcast_data['requested_count'] > 0:
                episodes_to_add = episodes[:podcast_data['requested_count']]
                print(f"  Limiting to {len(episodes_to_add)} episodes (user requested)")

            # Add episodes to queue
            episodes_added = 0
            for episode in episodes_to_add:
                success = self.add_episode_to_queue(episode)
                if success:
                    episodes_added += 1

            total_episodes_added += episodes_added

            print(f"  ✅ Added {episodes_added} episodes to queue")

            podcast_summaries.append({
                'name': podcast_name,
                'requested': podcast_data['requested_count'],
                'available': len(episodes),
                'added': episodes_added
            })

            # Rate limiting between RSS feeds
            time.sleep(random.uniform(0.5, 1.5))

        # Commit all changes
        self.conn.commit()

        # Generate final report
        print(f"\n{'='*80}")
        print("QUEUE BUILDING COMPLETE")
        print(f"{'='*80}")
        print(f"Total episodes added to queue: {total_episodes_added:,}")
        print(f"Podcasts processed: {len([p for p in podcast_summaries if p['added'] > 0])}")

        # Show podcast-by-podcast breakdown
        print(f"\nPODCAST-BY-PODCAST BREAKDOWN:")
        print("-" * 80)

        for summary in podcast_summaries:
            status = "✅" if summary['added'] > 0 else "❌"
            print(f"{status} {summary['name']}")
            print(f"    Requested: {summary['requested']}, Available: {summary['available']}, Added: {summary['added']}")

        # Show summary statistics
        requested_total = sum(p['requested'] for p in podcast_summaries)
        available_total = sum(p['available'] for p in podcast_summaries)

        print(f"\nSUMMARY:")
        print(f"Total requested episodes: {requested_total:,}")
        print(f"Total available episodes: {available_total:,}")
        print(f"Total episodes in queue: {total_episodes_added:,}")

        if requested_total > 0:
            coverage_pct = (total_episodes_added / requested_total) * 100
            print(f"Coverage of requested episodes: {coverage_pct:.1f}%")

        self.conn.close()

        return {
            'total_episodes': total_episodes_added,
            'podcasts_processed': len([p for p in podcast_summaries if p['added'] > 0]),
            'podcast_summaries': podcast_summaries
        }

def main():
    builder = EpisodeQueueBuilder()
    results = builder.build_complete_queue()
    return results

if __name__ == "__main__":
    main()