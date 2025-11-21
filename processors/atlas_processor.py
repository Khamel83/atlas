#!/usr/bin/env python3
"""
Atlas Podcast Processor
REAL working system that processes pending episodes continuously
Uses web scraping to find transcripts for podcasts
"""

import sqlite3
import requests
import time
import json
import logging
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import signal
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/ubuntu/dev/atlas/atlas_processor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AtlasProcessor:
    """Real Atlas processor that finds transcripts for pending episodes"""

    def __init__(self):
        self.root_dir = Path("/home/ubuntu/dev/atlas")
        self.db_path = self.root_dir / "podcast_processing.db"
        self.running = True

        # Configuration
        self.config = {
            'batch_size': 10,           # Process 10 episodes per cycle
            'sleep_between_cycles': 10,  # 10 seconds between cycles
            'sleep_between_requests': 3, # 3 seconds between requests
            'max_processing_time': 300,  # 5 minutes max per episode
        }

        # Handle signals
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        logger.info("🚀 Atlas Processor initialized")
        logger.info(f"📊 Batch size: {self.config['batch_size']} episodes")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info("🛑 Signal received, shutting down...")
        self.running = False

    def get_pending_episodes(self, limit=None):
        """Get pending episodes from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            limit_clause = f"LIMIT {limit}" if limit else ""
            query = f"""
                SELECT e.id, e.title, e.link, e.audio_url, e.processing_attempts, p.name as podcast_name
                FROM episodes e
                JOIN podcasts p ON e.podcast_id = p.id
                WHERE e.processing_status = 'pending'
                AND e.transcript_found = FALSE
                ORDER BY p.priority DESC, e.published_date DESC
                {limit_clause}
            """

            cursor.execute(query)
            episodes = []
            for row in cursor.fetchall():
                episodes.append({
                    'id': row[0],
                    'title': row[1],
                    'link': row[2],
                    'audio_url': row[3],
                    'attempts': row[4],
                    'podcast_name': row[5]
                })

            conn.close()
            return episodes

        except Exception as e:
            logger.error(f"❌ Error getting pending episodes: {e}")
            return []

    def mark_episode_processing(self, episode_id, status='processing', error=None):
        """Update episode status in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if status == 'processing':
                cursor.execute("""
                    UPDATE episodes
                    SET processing_status = 'processing',
                        processing_attempts = processing_attempts + 1,
                        last_attempt = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (episode_id,))
            elif status == 'completed':
                cursor.execute("""
                    UPDATE episodes
                    SET processing_status = 'completed'
                    WHERE id = ?
                """, (episode_id,))
            elif status == 'failed':
                cursor.execute("""
                    UPDATE episodes
                    SET processing_status = 'failed',
                        error_message = ?
                    WHERE id = ?
                """, (error, episode_id))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"❌ Error updating episode {episode_id}: {e}")

    def save_transcript(self, episode_id, transcript_text, source_url, quality_score=5):
        """Save transcript to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE episodes
                SET transcript_found = TRUE,
                    transcript_text = ?,
                    transcript_source = ?,
                    transcript_url = ?,
                    quality_score = ?,
                    processing_status = 'completed'
                WHERE id = ?
            """, (transcript_text, source_url, source_url, quality_score, episode_id))

            conn.commit()
            conn.close()

            logger.info(f"✅ Saved transcript for episode {episode_id}")

        except Exception as e:
            logger.error(f"❌ Error saving transcript for episode {episode_id}: {e}")

    def find_transcript(self, episode):
        """Find transcript for an episode using web scraping"""
        try:
            episode_id = episode['id']
            title = episode['title']
            podcast_name = episode['podcast_name']

            logger.info(f"🔍 Finding transcript for: {title}")

            # Strategy 1: Check episode link if available
            if episode['link'] and episode['link'].strip():
                transcript = self._scrape_episode_page(episode['link'])
                if transcript:
                    self.save_transcript(episode_id, transcript, episode['link'], 8)
                    return True

            # Strategy 2: Search for transcript on known podcast sites
            if podcast_name == "ACQ2 by Acquired":
                transcript = self._search_acq2_transcript(title)
                if transcript:
                    self.save_transcript(episode_id, transcript, "acq2_search", 7)
                    return True
            elif podcast_name == "Acquired":
                transcript = self._search_acquired_transcript(title)
                if transcript:
                    self.save_transcript(episode_id, transcript, "acquired_search", 7)
                    return True

            # Strategy 3: Generic web search for "[podcast] [title] transcript"
            transcript = self._generic_transcript_search(title, podcast_name)
            if transcript:
                self.save_transcript(episode_id, transcript, "web_search", 5)
                return True

            logger.info(f"❌ No transcript found for episode {episode_id}")
            return False

        except Exception as e:
            logger.error(f"❌ Error finding transcript for episode {episode['id']}: {e}")
            return False

    def _scrape_episode_page(self, url):
        """Scrape transcript from episode page"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.text, 'html.parser')

            # Look for transcript indicators
            transcript_selectors = [
                '[class*="transcript"]',
                '[id*="transcript"]',
                '.transcript-content',
                '.episode-transcript',
                'div:contains("transcript")',
                'div:contains("Transcript")'
            ]

            for selector in transcript_selectors:
                element = soup.select_one(selector)
                if element:
                    text = element.get_text(strip=True)
                    if len(text) > 1000:  # Assume long text is transcript
                        return text

            # Look for large text blocks
            text_blocks = soup.find_all(['p', 'div'])
            for block in text_blocks:
                text = block.get_text(strip=True)
                if len(text) > 2000 and 'transcript' in text.lower():
                    return text

            return None

        except Exception as e:
            logger.error(f"❌ Error scraping {url}: {e}")
            return None

    def _search_acq2_transcript(self, title):
        """Search for ACQ2 transcript specifically"""
        try:
            # Try known ACQ2 transcript sources
            search_urls = [
                "https://acquired.fm/category/acq2/",
                "https://podscribe.app/series/2147553"
            ]

            for base_url in search_urls:
                try:
                    response = requests.get(base_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=30)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')

                        # Look for links that might match the episode title
                        links = soup.find_all('a', href=True)
                        for link in links:
                            if title.lower() in link.get_text().lower():
                                episode_url = urljoin(base_url, link['href'])
                                transcript = self._scrape_episode_page(episode_url)
                                if transcript:
                                    return transcript

                except:
                    continue

            return None

        except Exception as e:
            logger.error(f"❌ Error searching ACQ2 transcript: {e}")
            return None

    def _search_acquired_transcript(self, title):
        """Search for Acquired transcript specifically"""
        try:
            # Try known Acquired transcript sources
            search_urls = [
                "https://www.acquired.fm/",
                "https://acquired.fm/episodes"
            ]

            for base_url in search_urls:
                try:
                    response = requests.get(base_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=30)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')

                        # Look for links that might match the episode title
                        links = soup.find_all('a', href=True)
                        for link in links:
                            if title.lower() in link.get_text().lower():
                                episode_url = urljoin(base_url, link['href'])
                                transcript = self._scrape_episode_page(episode_url)
                                if transcript:
                                    return transcript

                except:
                    continue

            return None

        except Exception as e:
            logger.error(f"❌ Error searching Acquired transcript: {e}")
            return None

    def _generic_transcript_search(self, title, podcast_name):
        """Generic web search for transcript"""
        # For now, return None - would need actual search API implementation
        return None

    def get_status(self):
        """Get current processing status"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get counts by status
            cursor.execute("""
                SELECT processing_status, COUNT(*)
                FROM episodes
                GROUP BY processing_status
            """)
            status_counts = dict(cursor.fetchall())

            # Get transcript found counts
            cursor.execute("""
                SELECT transcript_found, COUNT(*)
                FROM episodes
                GROUP BY transcript_found
            """)
            transcript_counts = dict(cursor.fetchall())

            conn.close()

            total = status_counts.get('pending', 0) + status_counts.get('completed', 0) + status_counts.get('failed', 0)
            completed = status_counts.get('completed', 0)
            pending = status_counts.get('pending', 0)

            return {
                'total': total,
                'completed': completed,
                'pending': pending,
                'failed': status_counts.get('failed', 0),
                'transcripts_found': transcript_counts.get(1, 0),
                'percentage': (completed / total * 100) if total > 0 else 0
            }

        except Exception as e:
            logger.error(f"❌ Error getting status: {e}")
            return {'total': 0, 'completed': 0, 'pending': 0, 'failed': 0, 'transcripts_found': 0, 'percentage': 0}

    def process_episode_batch(self):
        """Process a batch of episodes"""
        episodes = self.get_pending_episodes(limit=self.config['batch_size'])

        if not episodes:
            logger.info("📝 No pending episodes to process")
            return 0

        logger.info(f"🎯 Processing {len(episodes)} episodes...")

        processed = 0
        transcripts_found = 0

        for episode in episodes:
            if not self.running:
                break

            episode_id = episode['id']

            # Skip if too many attempts
            if episode['attempts'] >= 3:
                logger.warning(f"⚠️ Skipping episode {episode_id} - too many attempts ({episode['attempts']})")
                self.mark_episode_processing(episode_id, 'failed', 'Too many processing attempts')
                continue

            # Mark as processing
            self.mark_episode_processing(episode_id, 'processing')

            # Try to find transcript
            try:
                if self.find_transcript(episode):
                    transcripts_found += 1
                processed += 1

            except Exception as e:
                logger.error(f"❌ Error processing episode {episode_id}: {e}")
                self.mark_episode_processing(episode_id, 'failed', str(e))

            # Rate limiting
            time.sleep(self.config['sleep_between_requests'])

        logger.info(f"✅ Batch complete: {processed} processed, {transcripts_found} transcripts found")
        return transcripts_found

    def run_forever(self):
        """Main processing loop"""
        logger.info("🚀 Starting Atlas Processor...")

        cycle_count = 0

        while self.running:
            try:
                cycle_count += 1
                start_time = time.time()

                logger.info(f"🔄 Cycle {cycle_count} - {datetime.now()}")

                # Process batch of episodes
                transcripts_found = self.process_episode_batch()

                # Status check every 5 cycles
                if cycle_count % 5 == 0:
                    status = self.get_status()
                    logger.info(f"📊 Status: {status['completed']:,} completed, {status['pending']:,} pending ({status['percentage']:.1f}%)")
                    logger.info(f"🎯 Transcripts found: {status['transcripts_found']:,}")

                # Sleep between cycles
                cycle_time = time.time() - start_time
                sleep_time = max(0, self.config['sleep_between_cycles'] - cycle_time)
                time.sleep(sleep_time)

            except KeyboardInterrupt:
                logger.info("🛑 Keyboard interrupt")
                break
            except Exception as e:
                logger.error(f"❌ Error in processing loop: {e}")
                time.sleep(30)  # Wait before retrying

        logger.info("🏁 Atlas Processor stopped")

def main():
    """Main entry point"""
    processor = AtlasProcessor()
    processor.run_forever()

if __name__ == "__main__":
    main()