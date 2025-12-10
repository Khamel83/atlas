#!/usr/bin/env python3
"""
Simple Overnight Transcript Processor
Robust processor that runs all night with minimal dependencies
Uses multiple strategies: requests, BeautifulSoup, and fallback methods
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
        logging.FileHandler('/home/ubuntu/dev/atlas/overnight_processing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SimpleOvernightProcessor:
    """Simple, robust overnight transcript processor"""

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
            'delay_between_requests': 5.0,  # Conservative delay
            'timeout': 30,  # Request timeout
            'max_retries': 3,
            'session_duration_hours': 8,  # Long sessions
            'batch_size': 3,  # Small batches
            'save_interval': 5  # Save every 5 transcripts
        }

        # Session
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })

        # Stats
        self.stats = {
            'processed': 0,
            'failed': 0,
            'start_time': datetime.now(),
            'last_save': datetime.now()
        }

    def get_podcast_episodes(self, podcast_name: str, limit: int = 10) -> list:
        """Get episodes that need transcripts"""
        conn = sqlite3.connect(str(self.db_path))

        try:
            query = """
                SELECT e.id, e.title, p.name as podcast_name
                FROM episodes e
                JOIN podcasts p ON e.podcast_id = p.id
                WHERE p.name LIKE ?
                AND e.transcript_found = FALSE
                ORDER BY e.id DESC
                LIMIT ?
            """
            cursor = conn.execute(query, (f"%{podcast_name.split()[0]}%", limit))
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting episodes for {podcast_name}: {e}")
            return []
        finally:
            conn.close()

    def fetch_with_retry(self, url: str, retries: int = None) -> requests.Response:
        """Fetch URL with retry logic"""
        retries = retries or self.config['max_retries']

        for attempt in range(retries):
            try:
                # Add random delay to be more respectful
                delay = self.config['delay_between_requests'] + random.uniform(1, 3)
                time.sleep(delay)

                response = self.session.get(url, timeout=self.config['timeout'])

                if response.status_code == 200:
                    return response
                elif response.status_code == 429:  # Rate limited
                    wait_time = 30 * (attempt + 1)
                    logger.warning(f"Rate limited, waiting {wait_time} seconds")
                    time.sleep(wait_time)
                elif response.status_code in [500, 502, 503, 504]:
                    logger.warning(f"Server error {response.status_code}, retrying...")
                    time.sleep(10)
                else:
                    logger.warning(f"HTTP {response.status_code} for {url}")

            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt < retries - 1:
                    time.sleep(10)

        return None

    def extract_transcript_content(self, response: requests.Response, source_config: dict) -> str:
        """Extract transcript content from response"""
        try:
            soup = BeautifulSoup(response.content, 'html.parser')

            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe']):
                element.decompose()

            content = ""

            # Try different content selectors based on source type
            selectors = self.get_content_selectors(response.url)

            for selector in selectors:
                elements = soup.select(selector)
                if elements:
                    for element in elements:
                        text = element.get_text().strip()
                        if len(text) > 100:  # Substantial content
                            content += text + "\n\n"
                    break

            # Fallback to body content
            if not content:
                body = soup.find('body')
                if body:
                    content = body.get_text()

            return self.clean_content(content)

        except Exception as e:
            logger.error(f"Error extracting content: {e}")
            return ""

    def get_content_selectors(self, url: str) -> list:
        """Get appropriate content selectors based on URL"""
        if 'tapesearch.com' in url:
            return ['.transcript-text', '.content', 'article']
        elif 'podscribe.com' in url:
            return ['.episode-content', '.description', '.content']
        elif 'transcriptforest.com' in url:
            return ['.transcript', '.episode-content', 'main']
        elif 'musixmatch.com' in url:
            return ['.lyrics-content', '.content', '.mm-lyrics']
        elif 'wsj.com' in url:
            return ['.article-content', '.wsj-snippet-body', 'main']
        else:
            return ['.transcript-content', '.episode-content', '.post-content', '.entry-content', 'main', 'article']

    def clean_content(self, content: str) -> str:
        """Clean extracted content"""
        if not content:
            return ""

        lines = content.split('\n')
        cleaned_lines = []

        skip_phrases = [
            'cookie', 'privacy policy', 'terms of use', 'subscribe',
            'share this episode', 'transcript provided by',
            'automatic transcript', 'machine generated',
            'web.archive.org', 'wayback machine', 'saved from'
        ]

        for line in lines:
            line = line.strip()

            # Skip very short lines and boilerplate
            if (len(line) > 30 and
                not any(phrase in line.lower() for phrase in skip_phrases) and
                not line.lower().startswith(('http', 'www', '©', '©'))):
                cleaned_lines.append(line)

        # Remove duplicate consecutive lines
        unique_lines = []
        prev_line = ""
        for line in cleaned_lines:
            if line != prev_line:
                unique_lines.append(line)
                prev_line = line

        return '\n'.join(unique_lines)

    def save_transcript(self, episode_id: int, podcast_name: str, episode_title: str,
                       content: str, source_url: str, method: str = "Simple") -> bool:
        """Save transcript to file and database"""
        try:
            if len(content) < 500:  # Minimum threshold
                logger.warning(f"Content too short: {len(content)} characters")
                return False

            safe_title = re.sub(r'[^\w\s-]', '', episode_title[:60])
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{episode_id} - {safe_title} - {method}.md"
            filepath = self.transcripts_dir / filename

            markdown_content = f"""# {episode_title}

**Podcast:** {podcast_name}
**Episode ID:** {episode_id}
**Source URL:** {source_url}
**Method:** {method}
**Downloaded:** {datetime.now().isoformat()}

## Transcript

{content}
"""

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(markdown_content)

            # Update database
            conn = sqlite3.connect(str(self.db_path))
            conn.execute("""
                UPDATE episodes
                SET transcript_found = ?, transcript_source = ?
                WHERE id = ?
            """, (True, f"{method}: {source_url}", episode_id))
            conn.commit()
            conn.close()

            self.stats['processed'] += 1
            logger.info(f"✅ Saved: {episode_title} ({len(content)} chars)")
            return True

        except Exception as e:
            logger.error(f"❌ Error saving transcript: {e}")
            self.stats['failed'] += 1
            return False

    def save_progress(self):
        """Save current progress"""
        progress_file = self.root_dir / f"overnight_progress_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        progress_data = {
            'timestamp': datetime.now().isoformat(),
            'stats': {
                'processed': self.stats['processed'],
                'failed': self.stats['failed'],
                'start_time': self.stats['start_time'].isoformat(),
                'last_save': self.stats['last_save'].isoformat()
            },
            'config': self.config
        }

        with open(progress_file, 'w') as f:
            json.dump(progress_data, f, indent=2)

        logger.info(f"💾 Progress saved: {progress_file}")

    async def process_single_episode(self, episode_id: int, podcast_name: str,
                                   episode_title: str, sources: list) -> bool:
        """Process a single episode with multiple source attempts"""

        for i, source_url in enumerate(sources):
            if not source_url:
                continue

            logger.info(f"📚 Attempt {i+1}/{len(sources)}: {episode_title}")

            # For Conversations with Tyler, try the directory approach
            if 'conversationswithtyler.com' in source_url and '/episodes/' in source_url:
                # Try to find episode-specific page
                search_response = self.fetch_with_retry(source_url)
                if search_response and search_response.status_code == 200:
                    soup = BeautifulSoup(search_response.content, 'html.parser')

                    # Look for episode links
                    for link in soup.find_all('a', href=True):
                        href = link.get('href', '')
                        if 'episode' in href.lower() and episode_title.lower().replace(' ', '-') in href.lower():
                            full_url = urljoin(source_url, href)
                            source_url = full_url
                            break

            response = self.fetch_with_retry(source_url)

            if response and response.status_code == 200:
                content = self.extract_transcript_content(response, {'url': source_url})

                if content and len(content) > 500:
                    method = "Simple" + f"_Attempt{i+1}"
                    success = self.save_transcript(
                        episode_id, podcast_name, episode_title,
                        content, source_url, method
                    )
                    if success:
                        return True
                    else:
                        logger.warning(f"Failed to save transcript content")
                else:
                    logger.warning(f"No substantial content found from {source_url}")
            else:
                logger.warning(f"Failed to fetch {source_url}")

        return False

    async def process_podcast(self, podcast_name: str, config: dict) -> int:
        """Process all episodes for a podcast"""
        logger.info(f"\n🎯 Processing: {podcast_name}")

        # Skip if no reliable sources
        if config.get('status') == 'no_consistent_transcript_source':
            logger.info(f"⏭️ Skipping {podcast_name} - no reliable source")
            return 0

        episodes = self.get_podcast_episodes(podcast_name, self.config['batch_size'])
        if not episodes:
            logger.info(f"⚠️ No pending episodes for {podcast_name}")
            return 0

        # Build source list
        sources = []
        for key in ['primary', 'secondary', 'tertiary']:
            if key in config and config[key]:
                sources.append(config[key])

        processed_count = 0

        for episode_id, episode_title, actual_podcast_name in episodes:
            success = await self.process_single_episode(
                episode_id, actual_podcast_name, episode_title, sources
            )

            if success:
                processed_count += 1
            else:
                self.stats['failed'] += 1

            # Save progress periodically
            if (self.stats['processed'] + self.stats['failed']) % self.config['save_interval'] == 0:
                self.save_progress()

            # Check session duration
            elapsed = (datetime.now() - self.stats['start_time']).total_seconds()
            if elapsed > (self.config['session_duration_hours'] * 3600):
                logger.info("🛑 Session duration reached, stopping")
                break

        logger.info(f"✅ {podcast_name}: {processed_count}/{len(episodes)} transcripts processed")
        return processed_count

    async def run_overnight_processing(self):
        """Run overnight processing of all working sources"""
        logger.info("🚀 Starting simple overnight processing")

        working_podcasts = [
            name for name, config in self.sources['podcast_sources'].items()
            if config.get('reliable') and config.get('status') != 'no_consistent_transcript_source'
        ]

        # Prioritize top-tier sources
        priority_order = [
            "Lex Fridman Podcast", "EconTalk", "The Ezra Klein Show", "Radiolab",
            "This American Life", "99% Invisible", "Decoder with Nilay Patel",
            "Stratechery", "The Knowledge Project with Shane Parrish", "Sharp Tech with Ben Thompson"
        ]

        # Sort with priority first
        working_podcasts.sort(key=lambda x: (
            0 if x in priority_order else 1,
            priority_order.index(x) if x in priority_order else 999
        ))

        total_processed = 0

        for i, podcast_name in enumerate(working_podcasts, 1):
            logger.info(f"\n📊 Progress: {i}/{len(working_podcasts)} | "
                      f"Processed: {self.stats['processed']} | "
                      f"Failed: {self.stats['failed']}")

            config = self.sources['podcast_sources'].get(podcast_name, {})
            processed = await self.process_podcast(podcast_name, config)
            total_processed += processed

            # Break between podcasts
            await asyncio.sleep(10)

        # Final summary
        logger.info("\n" + "="*60)
        logger.info("🏆 OVERNIGHT PROCESSING COMPLETE")
        logger.info(f"📊 Total transcripts processed: {total_processed}")
        logger.info(f"⏱️ Total time: {datetime.now() - self.stats['start_time']}")
        logger.info(f"✅ Success rate: {self.stats['processed']/(self.stats['processed'] + self.stats['failed'])*100:.1f}%")

        self.save_progress()
        return total_processed

async def main():
    """Main execution"""
    processor = SimpleOvernightProcessor()
    total = await processor.run_overnight_processing()

    logger.info(f"\n🎉 Overnight processing complete! {total} transcripts downloaded")

if __name__ == "__main__":
    asyncio.run(main())