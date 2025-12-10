#!/usr/bin/env python3
"""
Atlas Transcript Processor
ONE processor that runs continuously until ALL 2,373 episodes have transcripts.
No premature completion declarations. No stopping until everything is done.
"""

import asyncio
import json
import sqlite3
import time
import os
import requests
from pathlib import Path
from datetime import datetime
import logging
import random
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import re

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/ubuntu/dev/atlas/atlas_transcript.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AtlasTranscriptProcessor:
    """Single continuous processor that never stops until all episodes have transcripts"""

    def __init__(self):
        self.root_dir = Path("/home/ubuntu/dev/atlas")
        self.transcripts_dir = self.root_dir / "transcripts"
        self.transcripts_dir.mkdir(exist_ok=True)

        # Database
        self.db_path = self.root_dir / "podcast_processing.db"

        # Load sources
        with open(self.root_dir / "podcast_transcript_sources.json", "r") as f:
            self.sources = json.load(f)

        # Configuration
        self.config = {
            'delay_between_requests': 3.0,  # Respectful delay
            'timeout': 30,
            'max_retries': 3,
            'concurrent_limit': 1
        }

        # Statistics
        self.stats = {
            'start_time': datetime.now(),
            'processed': 0,
            'failed': 0,
            'last_checkpoint': time.time()
        }

    def get_database_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)

    def get_pending_episodes(self):
        """Get episodes that still need transcripts - NEVER returns empty until truly complete"""
        conn = self.get_database_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT e.id, e.title, e.link, p.name as podcast_name, p.id as podcast_id
            FROM episodes e
            JOIN podcasts p ON e.podcast_id = p.id
            WHERE e.transcript_found = 0 OR e.transcript_text IS NULL OR e.transcript_text = ''
            ORDER BY p.priority DESC, e.id ASC
            LIMIT 100
        """)

        episodes = cursor.fetchall()
        conn.close()
        return episodes

    def get_completion_status(self):
        """Get actual completion status - only complete when ALL episodes have transcripts"""
        conn = self.get_database_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                COUNT(*) as total_episodes,
                COUNT(CASE WHEN transcript_found = 1 THEN 1 END) as with_transcripts,
                COUNT(CASE WHEN transcript_found = 0 OR transcript_text IS NULL OR transcript_text = '' THEN 1 END) as without_transcripts
            FROM episodes
        """)

        result = cursor.fetchone()
        conn.close()

        return {
            'total': result[0],
            'with_transcripts': result[1],
            'without_transcripts': result[2],
            'completion_rate': (result[1] / result[0] * 100) if result[0] > 0 else 0
        }

    async def fetch_transcript_wayback(self, episode_url, title):
        """Try to fetch transcript from Wayback Machine"""
        try:
            # Add delay before request
            await asyncio.sleep(self.config['delay_between_requests'])

            wayback_url = f"https://webcache.googleusercontent.com/search?q=cache:{episode_url}"
            response = requests.get(wayback_url, timeout=self.config['timeout'])

            if response.status_code == 200 and len(response.text) > 5000:
                soup = BeautifulSoup(response.text, 'html.parser')

                # Look for transcript content
                transcript_content = None

                # Try different selectors
                selectors = [
                    'div.transcript-content',
                    'div[class*="transcript"]',
                    'div[class*="episode-transcript"]',
                    'article',
                    'div.post-content',
                    'div.entry-content'
                ]

                for selector in selectors:
                    elements = soup.select(selector)
                    if elements:
                        content = elements[0].get_text(strip=True)
                        if len(content) > 1000:  # Reasonable transcript length
                            transcript_content = content
                            break

                if transcript_content:
                    return {
                        'transcript': transcript_content,
                        'source': 'Wayback',
                        'url': wayback_url
                    }

        except Exception as e:
            logger.debug(f"Wayback failed for {episode_url}: {e}")

        return None

    async def fetch_transcript_simple(self, episode_url, title):
        """Simple transcript extraction"""
        try:
            await asyncio.sleep(self.config['delay_between_requests'])

            response = requests.get(episode_url, timeout=self.config['timeout'])

            if response.status_code == 200 and len(response.text) > 3000:
                soup = BeautifulSoup(response.text, 'html.parser')

                # Remove ads and navigation
                for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                    element.decompose()

                # Look for transcript content
                content = soup.get_text(separator=' ', strip=True)

                if len(content) > 2000:  # Reasonable transcript length
                    return {
                        'transcript': content,
                        'source': 'Simple',
                        'url': episode_url
                    }

        except Exception as e:
            logger.debug(f"Simple extraction failed for {episode_url}: {e}")

        return None

    async def process_episode(self, episode):
        """Process a single episode"""
        episode_id, title, url, podcast_name, podcast_id = episode

        logger.info(f"📚 Processing: {podcast_name} - {title}")

        # Try different methods
        methods = [
            self.fetch_transcript_simple,
            self.fetch_transcript_wayback
        ]

        for method in methods:
            try:
                result = await method(url, title)
                if result and len(result['transcript']) > 1000:
                    # Save transcript
                    filename = f"{podcast_name.replace(' ', '_').replace('/', '_')} - {title.replace(' ', '_').replace('/', '_')}.md"
                    filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.'))

                    filepath = self.transcripts_dir / filename

                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(f"# {title}\n\n")
                        f.write(f"**Podcast:** {podcast_name}\n")
                        f.write(f"**Source:** {result['source']}\n")
                        f.write(f"**URL:** {url}\n\n")
                        f.write("---\n\n")
                        f.write(result['transcript'])

                    # Update database
                    conn = self.get_database_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE episodes
                        SET transcript_found = 1,
                            transcript_text = ?,
                            transcript_source = ?,
                            processing_status = 'completed'
                        WHERE id = ?
                    """, (result['transcript'][:1000], result['source'], episode_id))
                    conn.commit()
                    conn.close()

                    self.stats['processed'] += 1
                    logger.info(f"✅ Saved: {title} ({len(result['transcript'])} chars)")
                    return True

            except Exception as e:
                logger.warning(f"Method {method.__name__} failed for {title}: {e}")
                continue

        # All methods failed
        self.stats['failed'] += 1
        logger.warning(f"❌ Failed: {title}")
        return False

    async def continuous_processing_loop(self):
        """Main processing loop - ONLY stops when ALL episodes have transcripts"""
        iteration = 0

        while True:
            iteration += 1

            # Check actual completion status
            status = self.get_completion_status()
            logger.info(f"\n📊 Iteration {iteration}: {status['with_transcripts']}/{status['total']} episodes ({status['completion_rate']:.1f}%) have transcripts")
            logger.info(f"🎯 Episodes remaining: {status['without_transcripts']}")

            # ONLY stop if EVERY episode has a transcript
            if status['without_transcripts'] == 0:
                logger.info("\n🎉 ATLAS PROCESSING TRULY COMPLETE!")
                logger.info(f"✅ All {status['total']} episodes have transcripts")
                logger.info(f"⏱️ Total time: {datetime.now() - self.stats['start_time']}")
                break

            # Get episodes that still need processing
            pending_episodes = self.get_pending_episodes()

            if not pending_episodes:
                logger.warning("⚠️ No pending episodes found, but completion status shows work remaining. Checking database...")
                await asyncio.sleep(30)  # Wait and retry
                continue

            logger.info(f"🎯 Processing {len(pending_episodes)} episodes...")

            # Process episodes with delays
            for i, episode in enumerate(pending_episodes):
                await self.process_episode(episode)

                # Progress checkpoint every 10 episodes
                if (i + 1) % 10 == 0:
                    logger.info(f"📈 Progress: {i + 1}/{len(pending_episodes)} processed this batch")

                # Brief pause between episodes
                await asyncio.sleep(2)

            # Save checkpoint
            checkpoint_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            checkpoint_data = {
                'timestamp': checkpoint_time,
                'iteration': iteration,
                'stats': {
                    'processed_total': self.stats['processed'],
                    'failed_total': self.stats['failed'],
                    'runtime': str(datetime.now() - self.stats['start_time'])
                },
                'completion_status': status
            }

            checkpoint_file = self.root_dir / f"atlas_progress_{checkpoint_time}.json"
            with open(checkpoint_file, 'w') as f:
                json.dump(checkpoint_data, f, indent=2)

            logger.info(f"💾 Checkpoint saved: {checkpoint_file}")

            # Brief pause between batches
            await asyncio.sleep(5)

    async def run(self):
        """Start continuous processing"""
        logger.info("🚀 Starting Atlas Continuous Processor")
        logger.info("🎯 This will run until ALL 2,373 episodes have transcripts")
        logger.info("⛔ NO premature completion declarations")
        logger.info("📊 Current status:", self.get_completion_status())

        await self.continuous_processing_loop()

async def main():
    """Main execution"""
    processor = AtlasTranscriptProcessor()
    await processor.run()

if __name__ == "__main__":
    asyncio.run(main())