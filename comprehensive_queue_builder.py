#!/usr/bin/env python3
"""
Comprehensive RSS feed processor to build queue with exact episode counts
"""

import csv
import feedparser
import sqlite3
import time
import logging
from datetime import datetime
import json
from urllib.parse import urljoin, urlparse

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/comprehensive_queue_builder.log'),
        logging.StreamHandler()
    ]
)

class ComprehensiveQueueBuilder:
    def __init__(self):
        self.conn = sqlite3.connect('data/atlas.db')
        self.cursor = self.conn.cursor()

        # Load exact podcast requirements from user's config
        self.podcast_requirements = self.load_podcast_requirements()

        # Load RSS feeds mapping
        self.rss_feeds = self.load_rss_feeds()

        # Track progress
        self.processed_episodes = {}
        self.failed_feeds = []

    def load_podcast_requirements(self):
        """Load exact episode counts from user's config"""
        requirements = {}

        # Based on the config file provided by user
        requirements = {
            # 1000 episodes each
            "ACQ2 by Acquired": 1000,
            "Acquired": 1000,
            "Sharp Tech with Ben Thompson": 1000,
            "Stratechery": 1000,
            "Hard Fork": 1000,
            "Joie de Vivek - A Sacramento Kings Podcast": 1000,
            "Conversations with Tyler": 1000,

            # 100 episodes each
            "Against the Rules with Michael Lewis": 100,
            "Planet Money": 100,
            "The Rewatchables": 100,
            "Radiolab": 100,
            "The Recipe with Kenji and Deb": 100,
            "Asianometry": 100,
            "Dithering": 100,
            "Dwarkesh Podcast": 100,
            "Land of the Giants": 100,
            "The Knowledge Project with Shane Parrish": 100,
            "The Ezra Klein Show": 100,
            "This American Life": 100,
            "Lex Fridman Podcast": 100,

            # 20 episodes each
            "Plain English with Derek Thompson": 20,
            "EconTalk": 20,

            # 10 episodes each
            "Accidental Tech Podcast": 10,
            "Slate Culture": 10,
            "The Prestige TV Podcast": 10,
            "99% Invisible": 10,
            "Animal Spirits Podcast": 10,
            "Articles of Interest": 10,
            "Bad Bets": 10,
            "Channels with Peter Kafka": 10,
            "Cortex": 10,
            "Exponent": 10,
            "Lenny's Reads": 10,
            "Odd Lots": 10,
            "The Big Picture": 10,
            "The Bill Simmons Podcast": 10,
            "The Watch": 10,

            # 5 episodes each
            "The Vergecast": 5,
            "Recipe Club": 5,

            # 4 episodes
            "Political Gabfest": 4,

            # 2 episodes each
            "The NPR Politics Podcast": 2,
            "Decoder with Nilay Patel": 2,
            "Greatest Of All Talk (Stratechery Plus Edition)": 2,
            "Bodega Boys": 2,

            # 1 episode each
            "Today, Explained": 1,
            "The Cognitive Revolution": 1,
            "Practical AI": 2
        }

        return requirements

    def load_rss_feeds(self):
        """Load RSS feeds from CSV file"""
        feeds = {}

        try:
            with open('config/podcast_rss_feeds.csv', 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 2:
                        podcast_name = row[0].strip('"')
                        rss_url = row[1].strip('"')
                        feeds[podcast_name] = rss_url
        except Exception as e:
            logging.error(f"Error loading RSS feeds: {e}")

        logging.info(f"Loaded {len(feeds)} RSS feeds")
        return feeds

    def extract_episode_metadata(self, entry, podcast_name):
        """Extract comprehensive metadata from RSS entry"""
        metadata = {
            'title': entry.get('title', 'Untitled Episode'),
            'url': entry.get('link', ''),
            'published_date': None,
            'duration': None,
            'audio_url': None,
            'description': entry.get('summary', entry.get('description', '')),
            'author': entry.get('author', ''),
            'episode_number': None,
            'season_number': None,
            'image_url': None,
            'guid': entry.get('id', entry.get('link', ''))
        }

        # Extract published date
        if 'published' in entry:
            try:
                metadata['published_date'] = datetime.strptime(
                    entry.published, '%a, %d %b %Y %H:%M:%S %z'
                ).isoformat()
            except:
                try:
                    metadata['published_date'] = datetime.strptime(
                        entry.published, '%a, %d %b %Y %H:%M:%S %Z'
                    ).isoformat()
                except:
                    pass

        # Extract audio URL
        if 'links' in entry:
            for link in entry.links:
                if link.get('type', '').startswith('audio/'):
                    metadata['audio_url'] = link.get('href')
                    break

        # Extract image URL
        if 'image' in entry:
            metadata['image_url'] = entry.image.get('href', '')
        elif 'itunes_image' in entry:
            metadata['image_url'] = entry.itunes_image.get('href', '')

        # Extract duration
        if 'itunes_duration' in entry:
            metadata['duration'] = entry.itunes_duration

        # Extract episode/season numbers
        if 'itunes_episode' in entry:
            metadata['episode_number'] = entry.itunes_episode
        if 'itunes_season' in entry:
            metadata['season_number'] = entry.itunes_season

        return metadata

    def check_if_episode_exists(self, url, guid):
        """Check if episode already exists in database"""
        self.cursor.execute('''
            SELECT COUNT(*) FROM content
            WHERE (url = ? OR title = ?) AND content_type = 'podcast_episode'
        ''', (url, guid))
        return self.cursor.fetchone()[0] > 0

    def add_episode_to_queue(self, podcast_name, metadata):
        """Add episode to database queue with all metadata"""
        try:
            # Check if already exists
            if self.check_if_episode_exists(metadata['url'], metadata['guid']):
                return False

            # Add to database
            self.cursor.execute('''
                INSERT INTO content (
                    title, url, content_type, created_at, updated_at
                ) VALUES (?, ?, 'podcast_episode', ?, ?)
            ''', (
                f"[PODCAST] {podcast_name}: {metadata['title']}",
                metadata['url'],
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))

            # Store additional metadata
            metadata_json = json.dumps(metadata)
            self.cursor.execute('''
                INSERT INTO episode_metadata (episode_url, metadata_json, created_at)
                VALUES (?, ?, ?)
            ''', (metadata['url'], metadata_json, datetime.now().isoformat()))

            self.conn.commit()
            return True

        except Exception as e:
            logging.error(f"Error adding episode to queue: {e}")
            return False

    def process_podcast_feed(self, podcast_name, rss_url, target_count):
        """Process a single podcast feed and add episodes up to target count"""
        try:
            logging.info(f"🔄 Processing {podcast_name} (target: {target_count} episodes)")

            # Check if we already have enough episodes
            current_count = self.processed_episodes.get(podcast_name, 0)
            if current_count >= target_count:
                logging.info(f"  ⏭️  Already have {current_count}/{target_count} episodes")
                return current_count

            # Parse RSS feed
            feed = feedparser.parse(rss_url)

            if not feed.entries:
                logging.warning(f"  ❌ No entries found in feed for {podcast_name}")
                return current_count

            logging.info(f"  📊 Found {len(feed.entries)} episodes in feed")

            episodes_added = 0
            processed_count = 0

            # Process episodes
            for entry in feed.entries:
                if current_count + episodes_added >= target_count:
                    break

                metadata = self.extract_episode_metadata(entry, podcast_name)

                if not metadata['url']:
                    continue

                # Add to queue
                if self.add_episode_to_queue(podcast_name, metadata):
                    episodes_added += 1

                processed_count += 1

                # Progress updates
                if processed_count % 50 == 0:
                    logging.info(f"    📊 Processed {processed_count} episodes, added {episodes_added}")

                # Rate limiting
                time.sleep(0.1)

            total_episodes = current_count + episodes_added
            self.processed_episodes[podcast_name] = total_episodes

            logging.info(f"  ✅ Added {episodes_added} episodes for {podcast_name} (total: {total_episodes}/{target_count})")
            return total_episodes

        except Exception as e:
            logging.error(f"  ❌ Error processing {podcast_name}: {e}")
            self.failed_feeds.append((podcast_name, rss_url, str(e)))
            return self.processed_episodes.get(podcast_name, 0)

    def build_comprehensive_queue(self):
        """Build the comprehensive queue from all RSS feeds"""
        logging.info("🚀 BUILDING COMPREHENSIVE QUEUE FROM RSS FEEDS")
        logging.info("=" * 80)
        logging.info(f"📋 Target podcasts: {len(self.podcast_requirements)}")
        logging.info(f"🔗 Available RSS feeds: {len(self.rss_feeds)}")
        logging.info("=" * 80)

        total_episodes = 0
        successful_feeds = 0

        # Process each target podcast
        for podcast_name, target_count in self.podcast_requirements.items():
            # Find RSS feed for this podcast
            rss_url = self.rss_feeds.get(podcast_name)

            if not rss_url:
                logging.warning(f"  ⚠️  No RSS feed found for {podcast_name}")
                continue

            # Process the feed
            episodes_count = self.process_podcast_feed(podcast_name, rss_url, target_count)

            if episodes_count > 0:
                total_episodes += episodes_count
                successful_feeds += 1

        # Final summary
        logging.info("\n" + "=" * 80)
        logging.info("🎉 COMPREHENSIVE QUEUE BUILDING COMPLETE!")
        logging.info("=" * 80)
        logging.info(f"📊 Total episodes added: {total_episodes}")
        logging.info(f"📋 Successful feeds: {successful_feeds}/{len(self.podcast_requirements)}")
        logging.info(f"❌ Failed feeds: {len(self.failed_feeds)}")

        if self.failed_feeds:
            logging.info("\n❌ Failed feeds:")
            for podcast, url, error in self.failed_feeds:
                logging.info(f"  - {podcast}: {error}")

        # Save progress report
        self.save_progress_report()

        self.conn.close()
        return total_episodes

    def save_progress_report(self):
        """Save progress report to file"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_episodes_processed': sum(self.processed_episodes.values()),
            'processed_episodes': self.processed_episodes,
            'failed_feeds': self.failed_feeds,
            'podcast_requirements': self.podcast_requirements
        }

        with open('logs/queue_progress_report.json', 'w') as f:
            json.dump(report, f, indent=2)

        logging.info(f"📊 Progress report saved to logs/queue_progress_report.json")

def main():
    builder = ComprehensiveQueueBuilder()
    total_episodes = builder.build_comprehensive_queue()
    print(f"\n✅ Built comprehensive queue with {total_episodes} episodes!")

if __name__ == "__main__":
    main()