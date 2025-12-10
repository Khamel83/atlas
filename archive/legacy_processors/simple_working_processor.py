#!/usr/bin/env python3
"""
Simple Working Atlas Processor
While loop + tool calls that actually work
"""

import sqlite3
import requests
import time
import json
import re
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import quote_plus
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleTranscriptFinder:
    """Simple tool calls for transcript discovery"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

    def google_search(self, podcast_name, episode_title):
        """Tool call: Google search for transcripts"""
        search_query = f"{podcast_name} {episode_title} transcript"
        url = f"https://www.google.com/search?q={quote_plus(search_query)}"

        try:
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for transcript links
            links = []
            for a in soup.find_all('a', href=True):
                href = a['href']
                # Fix relative URLs
                if href.startswith('/'):
                    href = 'https://www.google.com' + href
                if any(term in href.lower() for term in ['transcript', 'show-notes', 'show notes']):
                    links.append(href)

            return {'found': len(links) > 0, 'links': links[:3]}
        except Exception as e:
            logger.error(f"Google search failed: {e}")
            return {'found': False, 'error': str(e)}

    def youtube_search(self, podcast_name, episode_title):
        """Tool call: YouTube search for transcripts"""
        search_query = f"{podcast_name} {episode_title}"
        url = f"https://www.youtube.com/results?search_query={quote_plus(search_query)}"

        try:
            response = self.session.get(url, timeout=10)
            # Look for video links
            video_ids = re.findall(r'watch\?v=([^&"]+)', response.text)
            return {'found': len(video_ids) > 0, 'video_ids': video_ids[:3]}
        except Exception as e:
            logger.error(f"YouTube search failed: {e}")
            return {'found': False, 'error': str(e)}

    def scrape_page(self, url):
        """Tool call: Scrape page for transcript content"""
        try:
            response = self.session.get(url, timeout=15)
            soup = BeautifulSoup(response.content, 'html.parser')

            # Remove script/style elements
            for script in soup(["script", "style"]):
                script.decompose()

            text = soup.get_text()

            # Look for transcript indicators
            transcript_words = ['transcript', 'speaker', 'interviewer', 'guest', 'question:', 'answer:']
            transcript_score = sum(1 for word in transcript_words if word.lower() in text.lower())

            # Check if it looks like a transcript
            is_transcript = (
                len(text) > 1000 and  # Reasonable length
                transcript_score >= 3 and  # Has transcript indicators
                ':' in text  # Has Q&A format
            )

            return {
                'found': is_transcript,
                'text': text[:5000] if is_transcript else None,  # First 5000 chars
                'full_length': len(text),
                'transcript_score': transcript_score
            }
        except Exception as e:
            logger.error(f"Page scrape failed for {url}: {e}")
            return {'found': False, 'error': str(e)}

class SimpleWorkingProcessor:
    """Simple while loop processor that actually works"""

    def __init__(self):
        self.db_path = "podcast_processing.db"
        self.finder = SimpleTranscriptFinder()

    def get_pending_episodes(self, limit=10):
        """Get pending episodes from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT id, title, link, description, podcast_id
            FROM episodes
            WHERE processing_status = 'pending'
            ORDER BY id
            LIMIT ?
        """, (limit,))
        episodes = cursor.fetchall()
        conn.close()
        return episodes

    def update_episode_status(self, episode_id, status, transcript=None, source=None):
        """Update episode processing status"""
        conn = sqlite3.connect(self.db_path)
        if transcript and source:
            conn.execute("""
                UPDATE episodes
                SET processing_status = ?, transcript_found = 1,
                    transcript_text = ?, transcript_source = ?,
                    last_attempt = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status, transcript, source, episode_id))
        else:
            conn.execute("""
                UPDATE episodes
                SET processing_status = ?, last_attempt = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status, episode_id))
        conn.commit()
        conn.close()

    def process_episode(self, episode):
        """Process single episode with tool calls"""
        episode_id, title, link, description, podcast_id = episode

        print(f"\n🎯 Processing: {title[:60]}...")

        # Get podcast name
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT name FROM podcasts WHERE id = ?", (podcast_id,))
        podcast_name = cursor.fetchone()[0]
        conn.close()

        tools_to_try = [
            ("Google Search", lambda: self.finder.google_search(podcast_name, title)),
            ("YouTube Search", lambda: self.finder.youtube_search(podcast_name, title)),
        ]

        # Try each tool
        for tool_name, tool_func in tools_to_try:
            print(f"  🔧 Trying {tool_name}...")
            result = tool_func()

            if result.get('found'):
                print(f"  ✅ {tool_name} found something!")

                # If we found links, try scraping them
                if 'links' in result:
                    for link in result['links']:
                        print(f"  📄 Scraping: {link[:80]}...")
                        scrape_result = self.finder.scrape_page(link)

                        if scrape_result.get('found'):
                            print(f"  🎉 SUCCESS: Found transcript via {tool_name} + scrape")
                            self.update_episode_status(
                                episode_id, 'completed',
                                scrape_result['text'],
                                f"{tool_name} + scrape"
                            )
                            return True

                # If YouTube found videos, we could process them here
                if 'video_ids' in result:
                    print(f"  📺 Found YouTube videos - need transcript extraction")
                    # TODO: Add YouTube transcript extraction

        print(f"  ❌ No transcript found for this episode")
        self.update_episode_status(episode_id, 'failed')
        return False

    def run(self):
        """Main processing loop"""
        print("🚀 Starting Simple Working Atlas Processor")
        print("=" * 50)

        processed_count = 0
        success_count = 0

        while True:
            # Get next batch of episodes
            episodes = self.get_pending_episodes(5)

            if not episodes:
                print("\n🎉 No more pending episodes!")
                break

            print(f"\n📋 Processing {len(episodes)} episodes...")

            # Process each episode
            for episode in episodes:
                processed_count += 1
                if self.process_episode(episode):
                    success_count += 1

                # Small delay between episodes
                time.sleep(2)

            # Show progress
            print(f"\n📊 Progress: {processed_count} processed, {success_count} successful")
            print(f"📈 Success rate: {(success_count/processed_count)*100:.1f}%")

            # Check if we should continue
            remaining = self.get_pending_episodes(1)
            if not remaining:
                break

        print(f"\n🏁 Processing complete!")
        print(f"📊 Final stats: {processed_count} processed, {success_count} successful")

if __name__ == "__main__":
    processor = SimpleWorkingProcessor()
    processor.run()