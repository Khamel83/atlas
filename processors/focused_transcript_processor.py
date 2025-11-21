#!/usr/bin/env python3
"""
Focused Transcript Processor
Process transcripts from validated working sources
Starts with highest quality, most reliable sources
"""

import asyncio
import json
import sqlite3
from pathlib import Path
from datetime import datetime
import logging
import re

import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FocusedTranscriptProcessor:
    """Process transcripts from validated sources, starting with best ones"""

    def __init__(self):
        self.root_dir = Path("/home/ubuntu/dev/atlas")
        self.transcripts_dir = self.root_dir / "transcripts"
        self.transcripts_dir.mkdir(exist_ok=True)

        # Load validation results
        with open(self.root_dir / "validation_results_20251117_221622.json", "r") as f:
            self.validation_results = json.load(f)

        # Load podcast sources
        with open(self.root_dir / "podcast_transcript_sources.json", "r") as f:
            self.podcast_sources = json.load(f)

        # Database connection
        self.db_path = self.root_dir / "podcast_processing.db"

        # Focus on top-tier sources first (reliable + good indicators)
        self.top_tier_sources = self.get_top_tier_sources()

        # Processing stats
        self.processed_count = 0

    def get_top_tier_sources(self):
        """Get the best sources to process first"""
        top_tier = []

        for podcast_name, result in self.validation_results['results'].items():
            if (result['status'] == 'SUCCESS' and
                result['reliable'] and
                len(result.get('indicators', [])) >= 3):

                top_tier.append(podcast_name)

        logger.info(f"🎯 Top-tier sources: {len(top_tier)}")
        return top_tier

    def get_podcast_episodes(self, podcast_name, limit=5):
        """Get recent episodes for processing"""
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

    def process_lex_fridman_episode(self, episode_title):
        """Process a single Lex Fridman episode"""
        # Extract episode number
        episode_match = re.search(r'#(\d+)', episode_title)
        if not episode_match:
            return None

        episode_num = episode_match.group(1)

        # Create transcript URL pattern
        guest_match = re.search(r'– (.+?)(?:\s*–|$)', episode_title)
        if guest_match:
            guest = guest_match.group(1).strip()
            guest_slug = guest.lower().replace(' ', '-').replace('.', '').replace(',', '')
            transcript_url = f"https://lexfridman.com/podcast/{episode_num.lower()}/{guest_slug}/"
        else:
            transcript_url = f"https://lexfridman.com/podcast/{episode_num.lower()}/"

        # Fetch transcript content
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
            response = requests.get(transcript_url, headers=headers, timeout=10)

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')

                # Extract transcript content
                content = ""
                for element in soup.find_all(['p', 'div']):
                    text = element.get_text().strip()
                    if len(text) > 100 and not text.startswith('Listen'):
                        content += text + "\n\n"

                if len(content.strip()) > 500:
                    return {
                        'content': content.strip(),
                        'source_url': transcript_url,
                        'method': 'lex_fridman_direct'
                    }

        except Exception as e:
            logger.error(f"Error processing Lex Fridman episode {episode_title}: {e}")

        return None

    def process_econtalk_episode(self, episode_title):
        """Process a single EconTalk episode"""
        # Search EconTalk for episode
        search_url = f"https://www.econlib.org/?s={episode_title.replace(' ', '+')}"

        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
            response = requests.get(search_url, headers=headers, timeout=10)

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')

                # Look for transcript links
                for link in soup.find_all('a', href=True):
                    href = link.get('href')
                    if 'transcript' in href.lower() or 'econtalk' in href.lower():
                        # Get the transcript content
                        try:
                            transcript_response = requests.get(href, headers=headers, timeout=10)
                            if transcript_response.status_code == 200:
                                transcript_soup = BeautifulSoup(transcript_response.content, 'html.parser')

                                content = ""
                                for element in transcript_soup.find_all(['p', 'div']):
                                    text = element.get_text().strip()
                                    if len(text) > 50:
                                        content += text + "\n\n"

                                if len(content.strip()) > 500:
                                    return {
                                        'content': content.strip(),
                                        'source_url': href,
                                        'method': 'econtalk_search'
                                    }
                        except:
                            continue

        except Exception as e:
            logger.error(f"Error processing EconTalk episode {episode_title}: {e}")

        return None

    def process_99_invisible_episode(self, episode_title):
        """Process a 99% Invisible episode"""
        # This would need custom logic for 99% Invisible
        # For now, return None as it would require more complex scraping
        return None

    def save_transcript(self, episode_id, podcast_name, episode_title, transcript_data):
        """Save transcript to file and database"""
        if not transcript_data or len(transcript_data['content']) < 200:
            return False

        # Create safe filename
        safe_title = re.sub(r'[^\w\s-]', '', episode_title[:60])
        filename = f"{episode_id} - {safe_title}.md"
        filepath = self.transcripts_dir / filename

        # Create markdown content
        markdown_content = f"""# {episode_title}

**Podcast:** {podcast_name}
**Episode ID:** {episode_id}
**Source URL:** {transcript_data['source_url']}
**Method:** {transcript_data['method']}
**Downloaded:** {datetime.now().isoformat()}

## Transcript

{transcript_data['content']}
"""

        # Save file
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(markdown_content)

            # Update database
            self.update_transcript_status(episode_id, True, transcript_data['source_url'])

            logger.info(f"✅ Saved: {episode_title}")
            return True
        except Exception as e:
            logger.error(f"Error saving transcript: {e}")
            return False

    def update_transcript_status(self, episode_id, found, source_url=None):
        """Update transcript status in database"""
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute("""
                UPDATE episodes
                SET transcript_found = ?, transcript_source = ?
                WHERE id = ?
            """, (found, source_url, episode_id))
            conn.commit()
        except Exception as e:
            logger.error(f"Error updating transcript status: {e}")
        finally:
            conn.close()

    async def process_top_tier_sources(self):
        """Process transcripts from top-tier sources"""
        logger.info(f"🚀 Processing transcripts from {len(self.top_tier_sources)} top-tier sources")

        total_processed = 0

        for podcast_name in self.top_tier_sources[:5]:  # Start with first 5
            logger.info(f"\n🎯 Processing: {podcast_name}")

            episodes = self.get_podcast_episodes(podcast_name, limit=3)  # Test with 3 episodes first
            if not episodes:
                logger.info(f"⚠️ No pending episodes for {podcast_name}")
                continue

            podcast_processed = 0

            for episode_id, episode_title, actual_podcast_name in episodes:
                logger.info(f"📚 Episode: {episode_title}")

                transcript_data = None

                # Use appropriate processing method
                if "Lex Fridman" in podcast_name:
                    transcript_data = self.process_lex_fridman_episode(episode_title)
                elif "EconTalk" in podcast_name:
                    transcript_data = self.process_econtalk_episode(episode_title)
                elif "99% Invisible" in podcast_name:
                    transcript_data = self.process_99_invisible_episode(episode_title)
                else:
                    logger.info(f"⏭️ Skipping {podcast_name} - method not implemented")
                    continue

                if transcript_data:
                    success = self.save_transcript(
                        episode_id, actual_podcast_name, episode_title, transcript_data
                    )
                    if success:
                        podcast_processed += 1
                        total_processed += 1
                else:
                    logger.warning(f"❌ No transcript found: {episode_title}")

                # Small delay
                await asyncio.sleep(1)

            logger.info(f"✅ {podcast_name}: {podcast_processed} transcripts processed")

        logger.info(f"\n🏆 Total transcripts processed: {total_processed}")
        return total_processed

async def main():
    processor = FocusedTranscriptProcessor()
    total = await processor.process_top_tier_sources()
    print(f"\n🎉 Focused processing complete! {total} transcripts downloaded")

if __name__ == "__main__":
    asyncio.run(main())