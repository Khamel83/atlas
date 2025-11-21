#!/usr/bin/env python3
"""
Podcast Transcript Scraper
Uses user-provided sources to find and download transcripts
"""

import requests
import time
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from datetime import datetime
import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PodcastTranscriptScraper:
    """Downloads transcripts from user-provided sources"""

    def __init__(self):
        self.root_dir = Path("/home/ubuntu/dev/atlas")
        self.transcripts_dir = self.root_dir / "transcripts"
        self.transcripts_dir.mkdir(exist_ok=True)

        # Load podcast sources
        with open(self.root_dir / "podcast_transcript_sources.json", "r") as f:
            self.sources = json.load(f)

        # Database connection
        self.db_path = self.root_dir / "podcast_processing.db"

        # User agent
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        # Rate limiting
        self.delay_between_requests = 2

    def get_podcast_episodes(self, podcast_name, limit=10):
        """Get episodes for a specific podcast"""
        conn = sqlite3.connect(str(self.db_path))

        # Handle special characters in podcast names
        if "|" in podcast_name:
            # Handle names with OR conditions
            parts = podcast_name.split("|")
            where_clause = f"WHERE name LIKE '%{parts[0].strip()}%'"
        else:
            where_clause = f"WHERE name = '{podcast_name}'"

        query = f"""
            SELECT e.id, e.title, p.name as podcast_name
            FROM episodes e
            JOIN podcasts p ON e.podcast_id = p.id
            {where_clause}
            LIMIT {limit}
        """

        try:
            cursor = conn.execute(query)
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error fetching episodes for {podcast_name}: {e}")
            return []
        finally:
            conn.close()

    def search_econlib_transcripts(self, episode_title):
        """Search EconTalk transcripts"""
        base_url = "https://www.econlib.org"
        search_url = f"{base_url}/?s={episode_title.replace(' ', '+')}"

        try:
            response = requests.get(search_url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')

                # Look for transcript links
                for link in soup.find_all('a', href=True):
                    href = link.get('href')
                    if 'transcript' in href.lower() or 'econtalk' in href.lower():
                        full_url = urljoin(base_url, href)
                        return self.get_econlib_transcript_content(full_url)

            return None
        except Exception as e:
            logger.error(f"Error searching EconLib: {e}")
            return None

    def get_econlib_transcript_content(self, transcript_url):
        """Get transcript content from EconLib URL"""
        try:
            response = requests.get(transcript_url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')

                # Extract transcript content
                content = ""
                for element in soup.find_all(['p', 'div']):
                    text = element.get_text().strip()
                    if len(text) > 50:  # Skip very short elements
                        content += text + "\n\n"

                return content.strip()
            return None
        except Exception as e:
            logger.error(f"Error fetching EconLib transcript: {e}")
            return None

    def search_lex_fridman_transcripts(self, episode_title):
        """Search Lex Fridman transcripts"""
        base_url = "https://lexfridman.com"

        # Extract episode number if present
        episode_match = re.search(r'#(\d+)', episode_title)
        if episode_match:
            episode_num = episode_match.group(1)
            # Try direct transcript URL pattern
            transcript_url = f"{base_url}/podcast/{episode_num.lower()}-"

            # Get guest name from title
            guest_match = re.search(r'– (.+?)(?:\s*–|$)', episode_title)
            if guest_match:
                guest = guest_match.group(1).strip()
                transcript_url += guest.lower().replace(' ', '-').replace('.', '').replace(',', '')
                transcript_url += "/"

                return self.get_lex_fridman_transcript_content(transcript_url)

        # Fallback: search the site
        return self.search_lex_fridman_site(episode_title)

    def search_lex_fridman_site(self, episode_title):
        """Search Lex Fridman site for transcript"""
        search_url = f"https://lexfridman.com/?s={episode_title.replace(' ', '+')}"

        try:
            response = requests.get(search_url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')

                for link in soup.find_all('a', href=True):
                    href = link.get('href')
                    if '/podcast/' in href:
                        full_url = urljoin("https://lexfridman.com", href)
                        return self.get_lex_fridman_transcript_content(full_url)

            return None
        except Exception as e:
            logger.error(f"Error searching Lex Fridman: {e}")
            return None

    def get_lex_fridman_transcript_content(self, transcript_url):
        """Get Lex Fridman transcript content"""
        try:
            response = requests.get(transcript_url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')

                # Find transcript section
                content = ""
                # Look for typical transcript sections
                for element in soup.find_all(['p', 'div', 'article']):
                    text = element.get_text().strip()
                    if len(text) > 100 and not text.startswith('Listen to this episode'):
                        content += text + "\n\n"

                return content.strip()
            return None
        except Exception as e:
            logger.error(f"Error fetching Lex Fridman transcript: {e}")
            return None

    def save_transcript(self, episode_id, podcast_name, episode_title, transcript_content, source_url):
        """Save transcript to file and database"""
        if not transcript_content or len(transcript_content) < 100:
            return False

        # Create filename
        safe_title = re.sub(r'[^\w\s-]', '', episode_title)[:50]
        filename = f"{episode_id} - {safe_title}.md"
        filepath = self.transcripts_dir / filename

        # Create markdown content
        markdown_content = f"""# {episode_title}

**Podcast:** {podcast_name}
**Episode ID:** {episode_id}
**Source URL:** {source_url}
**Downloaded:** {datetime.now().isoformat()}

## Transcript

{transcript_content}
"""

        # Save file
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            logger.info(f"✅ Saved transcript: {filename}")
            return True
        except Exception as e:
            logger.error(f"Error saving transcript: {e}")
            return False

    def process_priority_podcasts(self):
        """Process high-priority podcasts first"""
        priority_podcasts = self.sources['priority_podcasts']

        for podcast_name in priority_podcasts:
            logger.info(f"\n🎯 Processing: {podcast_name}")
            episodes = self.get_podcast_episodes(podcast_name, limit=5)

            if not episodes:
                logger.warning(f"No episodes found for {podcast_name}")
                continue

            for episode_id, episode_title, actual_podcast_name in episodes:
                logger.info(f"📚 Episode: {episode_title}")

                transcript_content = None
                source_url = None

                # Choose scraping method based on podcast
                if "EconTalk" in podcast_name:
                    transcript_content = self.search_econlib_transcripts(episode_title)
                    source_url = f"https://www.econlib.org/?s={episode_title.replace(' ', '+')}"
                elif "Lex Fridman" in podcast_name:
                    transcript_content = self.search_lex_fridman_site(episode_title)
                    source_url = "https://lexfridman.com"
                else:
                    # TODO: Add more podcast-specific scrapers
                    logger.info(f"⏭️  Skipping {podcast_name} - scraper not implemented")
                    continue

                if transcript_content:
                    success = self.save_transcript(
                        episode_id, actual_podcast_name, episode_title,
                        transcript_content, source_url
                    )
                    if success:
                        logger.info(f"✅ Success: {episode_title}")
                    else:
                        logger.warning(f"❌ Failed to save: {episode_title}")
                else:
                    logger.warning(f"❌ No transcript found: {episode_title}")

                # Rate limiting
                time.sleep(self.delay_between_requests)

def main():
    scraper = PodcastTranscriptScraper()
    scraper.process_priority_podcasts()

if __name__ == "__main__":
    main()