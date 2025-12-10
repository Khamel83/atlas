#!/usr/bin/env python3
"""
PROCESS EVERY SINGLE EPISODE IN THE DATABASE QUEUE - NO BATCHING, NO LIMITS
"""

import sqlite3
import json
import time
import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import random
from urllib.parse import urljoin, urlparse

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/process_entire_queue.log'),
        logging.StreamHandler()
    ]
)

class CompleteQueueProcessor:
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

    def process_single_episode(self, episode_id, title, url):
        """Process a single episode from the database"""

        self.episodes_processed += 1

        logging.info(f"\n📝 [{self.episodes_processed}/980] Processing: {title[:80]}...")
        logging.info(f"  🔗 URL: {url}")

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

    def process_entire_queue(self):
        """Process every single episode in the database queue"""

        logging.info("🚀 STARTING COMPLETE QUEUE PROCESSING")
        logging.info("=" * 80)
        logging.info(f"📊 Total episodes to process: 980")
        logging.info("🎯 Goal: Process EVERY SINGLE episode")
        logging.info("=" * 80)

        # Get all podcast episodes from database
        self.cursor.execute('''
            SELECT id, title, url FROM content
            WHERE content_type = 'podcast_episode'
            ORDER BY created_at
        ''')

        episodes = self.cursor.fetchall()
        logging.info(f"📋 Found {len(episodes)} episodes in database queue")

        if len(episodes) != 980:
            logging.warning(f"⚠️  Expected 980 episodes, found {len(episodes)}")

        # Process every single episode
        for i, (episode_id, title, url) in enumerate(episodes, 1):
            logging.info(f"\n🎯 Progress: {i}/{len(episodes)} ({(i/len(episodes)*100):.1f}%)")

            success = self.process_single_episode(episode_id, title, url)

            # Rate limiting to avoid getting blocked
            time.sleep(random.uniform(1.0, 3.0))

            # Progress update every 10 episodes
            if i % 10 == 0:
                logging.info(f"📈 STATUS: {self.transcripts_found}/{i} transcripts found so far")

        # Final summary
        logging.info("\n" + "=" * 80)
        logging.info("🎉 COMPLETE QUEUE PROCESSING FINISHED")
        logging.info("=" * 80)
        logging.info(f"📊 Total episodes processed: {self.episodes_processed}")
        logging.info(f"🎯 Total transcripts found: {self.transcripts_found}")
        logging.info(f"📈 Success rate: {(self.transcripts_found/self.episodes_processed*100):.1f}%")
        logging.info("=" * 80)

        self.conn.close()

def main():
    processor = CompleteQueueProcessor()
    processor.process_entire_queue()

if __name__ == "__main__":
    main()