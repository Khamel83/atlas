#!/usr/bin/env python3
"""
BALANCED PROCESSING - Get episodes from ALL podcasts, not just one at a time
"""

import sqlite3
import time
import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import random
from collections import defaultdict

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/balanced_processing.log'),
        logging.StreamHandler()
    ]
)

class BalancedQueueProcessor:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.transcripts_found = 0
        self.episodes_processed = 0

        # Connect to database
        self.conn = sqlite3.connect('data/atlas.db')
        self.cursor = self.conn.cursor()

        # Track processed episodes to avoid re-processing
        self.processed_urls = set()

    def extract_transcript_from_url(self, url):
        """Extract transcript from a single URL using all available methods"""

        try:
            logging.info(f"  🔄 Attempting to extract transcript from: {url}")

            # Method 1: Direct Google cache search
            google_url = f"https://webcache.googleusercontent.com/search?q=cache:{url}"
            response = self.session.get(google_url, timeout=30)

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')

                # Remove Google cache overlay
                for overlay in soup.select('.google-cache-overlay, .google-cache-header'):
                    overlay.decompose()

                # Look for transcript content
                transcript_selectors = [
                    '.transcript', '.episode-transcript',
                    '.show-transcript', '.transcript-text',
                    '[class*="transcript"]', '[id*="transcript"]'
                ]

                for selector in transcript_selectors:
                    elements = soup.select(selector)
                    if elements:
                        transcript = ' '.join([elem.get_text(strip=True) for elem in elements])
                        if len(transcript) > 5000:  # Minimum length check
                            logging.info(f"  ✅ Found transcript via selector {selector}: {len(transcript)} chars")
                            return transcript

                # If no structured transcript, look for large text blocks
                text_blocks = []
                for p in soup.find_all(['p', 'div']):
                    text = p.get_text(strip=True)
                    if len(text) > 200:  # substantial text block
                        text_blocks.append(text)

                if text_blocks:
                    combined_text = ' '.join(text_blocks)
                    if len(combined_text) > 10000:  # Large combined text
                        logging.info(f"  ✅ Found large text content: {len(combined_text)} chars")
                        return combined_text

            # Method 2: Try direct URL access
            direct_response = self.session.get(url, timeout=30)
            if direct_response.status_code == 200:
                soup = BeautifulSoup(direct_response.content, 'html.parser')

                # Same extraction logic as above
                text_blocks = []
                for p in soup.find_all(['p', 'div']):
                    text = p.get_text(strip=True)
                    if len(text) > 200:
                        text_blocks.append(text)

                if text_blocks:
                    combined_text = ' '.join(text_blocks)
                    if len(combined_text) > 10000:
                        logging.info(f"  ✅ Found direct content: {len(combined_text)} chars")
                        return combined_text

        except Exception as e:
            logging.warning(f"  ❌ Error extracting from {url}: {e}")

        return None

    def group_episodes_by_podcast(self):
        """Group episodes by podcast for balanced processing"""

        # Get all unprocessed episodes
        self.cursor.execute('''
            SELECT id, title, url FROM content
            WHERE content_type = 'podcast_episode'
            AND url NOT IN (SELECT url FROM content WHERE content_type = 'podcast_transcript')
            ORDER BY created_at
        ''')

        episodes = self.cursor.fetchall()

        # Group by podcast (extract podcast name from title)
        podcast_groups = defaultdict(list)

        for episode_id, title, url in episodes:
            if url in self.processed_urls:
                continue

            # Extract podcast name from title like "[PODCAST] #123 - Episode Title"
            if ' - ' in title:
                podcast_name = title.split(' - ')[0].replace('[PODCAST] ', '').strip()
            elif '|' in title:
                podcast_name = title.split('|')[0].replace('[PODCAST] ', '').strip()
            else:
                podcast_name = 'Unknown'

            podcast_groups[podcast_name].append((episode_id, title, url))

        return podcast_groups

    def process_single_episode(self, episode_id, title, url, podcast_name):
        """Process a single episode from the database"""

        self.episodes_processed += 1
        self.processed_urls.add(url)

        logging.info(f"\n📝 [{self.episodes_processed}] {podcast_name}: {title[:60]}...")

        # Extract transcript
        transcript = self.extract_transcript_from_url(url)

        if transcript:
            # Store in database
            try:
                self.cursor.execute('''
                    INSERT OR REPLACE INTO content
                    (title, url, content, content_type, created_at, updated_at)
                    VALUES (?, ?, ?, 'podcast_transcript', ?, ?)
                ''', (title, url, transcript, datetime.now().isoformat(), datetime.now().isoformat()))

                self.conn.commit()
                self.transcripts_found += 1

                logging.info(f"  ✅ SUCCESS: Transcript stored ({len(transcript)} chars)")
                logging.info(f"  📊 Total transcripts found: {self.transcripts_found}")

                return True

            except Exception as e:
                logging.error(f"  ❌ Database error: {e}")
                return False
        else:
            logging.info(f"  ❌ No transcript found")
            return False

    def process_balanced_queue(self, max_episodes_per_podcast=20):
        """Process episodes in a balanced way across all podcasts"""

        logging.info("🚀 STARTING BALANCED QUEUE PROCESSING")
        logging.info("=" * 80)
        logging.info(f"🎯 Strategy: Process {max_episodes_per_podcast} episodes per podcast")
        logging.info("📋 Goal: Cover ALL podcasts, not just one at a time")
        logging.info("=" * 80)

        # Get episodes grouped by podcast
        podcast_groups = self.group_episodes_by_podcast()

        logging.info(f"📊 Found {len(podcast_groups)} different podcasts in queue")

        if not podcast_groups:
            logging.warning("❌ No episodes found in queue")
            return

        # Show podcast breakdown
        logging.info("\n📋 Podcast breakdown:")
        for podcast_name, episodes in sorted(podcast_groups.items()):
            logging.info(f"  - {podcast_name}: {len(episodes)} episodes")

        # Process in rounds - take a few episodes from each podcast
        rounds_completed = 0
        total_episodes_to_process = sum(len(episodes) for episodes in podcast_groups.values())

        while any(podcast_groups.values()):
            rounds_completed += 1
            logging.info(f"\n🔄 Starting Round {rounds_completed}")
            logging.info("-" * 50)

            processed_this_round = 0

            # Process each podcast that still has episodes
            for podcast_name, episodes in sorted(podcast_groups.items()):
                if not episodes:
                    continue

                # Take up to max_episodes_per_podcast from this podcast
                episodes_to_process = episodes[:max_episodes_per_podcast]
                remaining_episodes = episodes[max_episodes_per_podcast:]

                # Process these episodes
                for episode_id, title, url in episodes_to_process:
                    success = self.process_single_episode(episode_id, title, url, podcast_name)
                    processed_this_round += 1

                    # Rate limiting
                    time.sleep(random.uniform(1.0, 2.0))

                # Update remaining episodes for this podcast
                podcast_groups[podcast_name] = remaining_episodes

                logging.info(f"  📊 {podcast_name}: Processed {len(episodes_to_process)}, {len(remaining_episodes)} remaining")

                if processed_this_round % 50 == 0:
                    logging.info(f"📈 Round {rounds_completed} progress: {self.transcripts_found} transcripts found")

            logging.info(f"\n📊 Round {rounds_completed} complete:")
            logging.info(f"  - Episodes processed this round: {processed_this_round}")
            logging.info(f"  - Total transcripts found: {self.transcripts_found}")
            logging.info(f"  - Progress: {self.episodes_processed}/{total_episodes_to_process} ({self.episodes_processed/total_episodes_to_process*100:.1f}%)")

            # Small break between rounds
            if any(podcast_groups.values()):
                time.sleep(5)

        # Final summary
        logging.info("\n" + "=" * 80)
        logging.info("🎉 BALANCED PROCESSING COMPLETE")
        logging.info("=" * 80)
        logging.info(f"📊 Total episodes processed: {self.episodes_processed}")
        logging.info(f"🎯 Total transcripts found: {self.transcripts_found}")
        logging.info(f"📈 Success rate: {(self.transcripts_found/self.episodes_processed*100):.1f}%")
        logging.info(f"🔄 Rounds completed: {rounds_completed}")
        logging.info("=" * 80)

        self.conn.close()

def main():
    processor = BalancedQueueProcessor()
    processor.process_balanced_queue(max_episodes_per_podcast=15)

if __name__ == "__main__":
    main()