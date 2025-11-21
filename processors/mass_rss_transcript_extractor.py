#!/usr/bin/env python3
"""
Mass RSS feed processor to extract thousands of episodes and their transcripts
"""

import csv
import requests
from bs4 import BeautifulSoup
import sqlite3
from datetime import datetime
import time
import random
import feedparser
import re
from urllib.parse import urljoin

class MassTranscriptExtractor:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

        # Load RSS feeds
        self.rss_feeds = {}
        self.load_rss_feeds()

        # Load existing sources cache for transcript extraction patterns
        try:
            import json
            with open('config/podcast_sources_cache.json', 'r') as f:
                self.sources_cache = json.load(f)
        except:
            self.sources_cache = {}

    def load_rss_feeds(self):
        """Load RSS feeds from USER'S podcast config - only ones they care about"""

        # Load RSS feed mappings
        rss_mappings = {}
        try:
            with open('config/podcast_rss_feeds.csv', 'r') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 2:
                        podcast_name = row[0].strip('"')
                        rss_url = row[1].strip('"')
                        rss_mappings[podcast_name] = rss_url
        except:
            rss_mappings = {}

        # Get user's actual podcasts from their config
        user_podcasts = []
        try:
            with open('config/podcast_config.csv', 'r') as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                for row in reader:
                    if len(row) >= 6 and row[5] == '0':  # Not excluded
                        podcast_name = row[1].strip('"')
                        user_podcasts.append(podcast_name)
        except:
            user_podcasts = []

        # Map user's podcasts to RSS feeds
        self.rss_feeds = {}
        for podcast in user_podcasts:
            if podcast in rss_mappings:
                self.rss_feeds[podcast] = rss_mappings[podcast]

        print(f"Loaded {len(self.rss_feeds)} RSS feeds from USER'S podcast list")

    def extract_episodes_from_rss(self, podcast_name, rss_url, max_episodes=100):
        """Extract episodes from RSS feed"""

        print(f"\n{'='*60}")
        print(f"PROCESSING RSS: {podcast_name}")
        print(f"Feed: {rss_url}")
        print(f"{'='*60}")

        episodes = []

        try:
            # Parse RSS feed
            feed = feedparser.parse(rss_url)

            if not feed.entries:
                print(f"  ❌ No entries in RSS feed")
                return episodes

            print(f"  Found {len(feed.entries)} episodes in RSS")

            # Process each episode
            for entry in feed.entries[:max_episodes]:

                # Get episode URL
                episode_url = entry.get('link', '')
                if not episode_url:
                    continue

                # Get episode title
                title = entry.get('title', 'Untitled Episode')

                # Get publication date
                pub_date = entry.get('published', '')

                # Get description
                description = entry.get('description', '')

                episodes.append({
                    'podcast_name': podcast_name,
                    'title': title,
                    'url': episode_url,
                    'pub_date': pub_date,
                    'description': description
                })

            print(f"  ✅ Extracted {len(episodes)} episodes")

        except Exception as e:
            print(f"  ❌ RSS parsing error: {e}")

        return episodes

    def extract_transcript_from_episode(self, episode):
        """Try to extract transcript from episode URL"""

        try:
            response = self.session.get(episode['url'], timeout=15)
            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.content, 'html.parser')

            # Try multiple transcript extraction strategies
            transcript = None

            # Strategy 1: Use existing network-specific patterns
            podcast_name = episode['podcast_name']
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
                                    transcript = text
                                    break
                    if transcript:
                        break

            # Strategy 2: Generic transcript selectors
            if not transcript:
                selectors = [
                    '.transcript',
                    '#transcript',
                    '.episode-transcript',
                    '.full-text',
                    '[class*="transcript"]',
                    '[id*="transcript"]'
                ]

                for selector in selectors:
                    element = soup.select_one(selector)
                    if element:
                        text = element.get_text(separator=' ', strip=True)
                        if len(text) > 1000 and 'transcript' in text.lower():
                            transcript = text
                            break

            # Strategy 3: Look for transcript links
            if not transcript:
                transcript_links = soup.find_all('a', href=True)
                for link in transcript_links:
                    link_text = link.get_text().lower()
                    if 'transcript' in link_text or 'full text' in link_text:
                        transcript_url = urljoin(episode['url'], link['href'])
                        try:
                            transcript_response = self.session.get(transcript_url, timeout=10)
                            if transcript_response.status_code == 200:
                                transcript_soup = BeautifulSoup(transcript_response.content, 'html.parser')
                                transcript = transcript_soup.get_text(separator=' ', strip=True)
                                if len(transcript) > 1000:
                                    break
                        except:
                            continue

            # Strategy 4: Check if show notes contain transcript
            if not transcript:
                content_areas = soup.select('article, .content, .post-content, .entry-content, main')
                for area in content_areas:
                    text = area.get_text(separator=' ', strip=True)
                    if (len(text) > 3000 and
                        'transcript' in text.lower() and
                        any(word in text.lower() for word in ['speaker', 'host', ':', 'said', 'says'])):
                        transcript = text
                        break

            return transcript

        except Exception as e:
            print(f"    ❌ Transcript extraction error: {e}")
            return None

    def store_episode_with_transcript(self, episode, transcript):
        """Store episode and transcript in database"""

        try:
            conn = sqlite3.connect('data/atlas.db')
            cursor = conn.cursor()

            # Check if already exists
            existing = cursor.execute(
                "SELECT id FROM content WHERE url = ?",
                (episode['url'],)
            ).fetchone()

            if existing:
                print(f"    ⏭️  Already exists: {episode['title'][:50]}...")
                conn.close()
                return False

            # Insert new transcript
            cursor.execute("""
                INSERT INTO content (title, url, content, content_type, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                f"[{episode['podcast_name']}] {episode['title']}",
                episode['url'],
                transcript,
                'podcast_transcript',
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))

            conn.commit()
            conn.close()

            print(f"    ✅ Added: {episode['title'][:50]}... ({len(transcript):,} chars)")
            return True

        except Exception as e:
            print(f"    ❌ Database error: {e}")
            return False

    def process_all_rss_feeds(self, target_episodes_per_podcast=50):
        """Process all RSS feeds to extract thousands of transcripts"""

        print("MASS RSS TRANSCRIPT EXTRACTION")
        print("=" * 80)
        print(f"Target: {target_episodes_per_podcast} episodes per podcast")
        print(f"Total podcasts: {len(self.rss_feeds)}")
        print(f"Estimated total episodes: {len(self.rss_feeds) * target_episodes_per_podcast:,}")
        print("=" * 80)

        total_episodes_processed = 0
        total_transcripts_found = 0

        for i, (podcast_name, rss_url) in enumerate(self.rss_feeds.items(), 1):

            print(f"\n[{i}/{len(self.rss_feeds)}] {podcast_name}")

            # Extract episodes from RSS
            episodes = self.extract_episodes_from_rss(
                podcast_name,
                rss_url,
                max_episodes=target_episodes_per_podcast
            )

            if not episodes:
                continue

            podcast_transcripts = 0

            # Process each episode
            for j, episode in enumerate(episodes, 1):
                print(f"  [{j}/{len(episodes)}] Processing: {episode['title'][:40]}...")

                # Try to extract transcript
                transcript = self.extract_transcript_from_episode(episode)

                if transcript:
                    # Store in database
                    success = self.store_episode_with_transcript(episode, transcript)
                    if success:
                        podcast_transcripts += 1
                        total_transcripts_found += 1
                else:
                    print(f"    ❌ No transcript found")

                total_episodes_processed += 1

                # Rate limiting
                time.sleep(random.uniform(0.5, 1.5))

                # Stop if we found enough for this podcast
                if podcast_transcripts >= 10:  # Limit per podcast to avoid overloading
                    print(f"  ✅ Found {podcast_transcripts} transcripts for {podcast_name}")
                    break

            print(f"  📊 {podcast_name}: {podcast_transcripts} transcripts found")

            # Longer pause between podcasts
            time.sleep(random.uniform(2, 4))

        # Final report
        print(f"\n{'='*80}")
        print("MASS EXTRACTION COMPLETE")
        print(f"{'='*80}")
        print(f"Episodes processed: {total_episodes_processed:,}")
        print(f"Transcripts found: {total_transcripts_found:,}")
        print(f"Success rate: {total_transcripts_found/total_episodes_processed*100:.1f}%")

        # Database summary
        conn = sqlite3.connect('data/atlas.db')
        cursor = conn.cursor()

        total_transcripts = cursor.execute(
            "SELECT COUNT(*) FROM content WHERE content_type = 'podcast_transcript'"
        ).fetchone()[0]

        print(f"Total transcripts in database: {total_transcripts:,}")
        conn.close()

def main():
    extractor = MassTranscriptExtractor()
    extractor.process_all_rss_feeds(target_episodes_per_podcast=9999)  # ALL episodes

if __name__ == "__main__":
    main()