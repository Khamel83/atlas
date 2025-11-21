#!/usr/bin/env python3
"""
Crawl4AI Bulk Podcast Transcript Scraper
Downloads entire transcript archives from reliable podcast sources
"""

import os
import time
import json
import sqlite3
from pathlib import Path
from datetime import datetime
import logging
import asyncio
from crawl4ai import AsyncWebCrawler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Crawl4AIPodcastScraper:
    """Uses Crawl4AI to download entire transcript archives"""

    def __init__(self):
        self.root_dir = Path("/home/ubuntu/dev/atlas")
        self.transcripts_dir = self.root_dir / "transcripts"
        self.transcripts_dir.mkdir(exist_ok=True)

        # Database connection
        self.db_path = self.root_dir / "podcast_processing.db"

        # Most reliable podcast sources for bulk ingestion
        self.reliable_sources = {
            "Lex Fridman Podcast": {
                "url_pattern": "https://lexfridman.com/category/transcripts/",
                "max_pages": 30,  # Approximate archive depth
                "quality": "excellent"
            },
            "EconTalk": {
                "url_pattern": "https://www.econlib.org/econtalk-archives-by-date/",
                "max_pages": 50,
                "quality": "excellent"
            },
            "99% Invisible": {
                "url_pattern": "https://99percentinvisible.org/episodes/",
                "max_pages": 40,
                "quality": "good"
            },
            "Radiolab": {
                "url_pattern": "https://radiolab.org/podcast",
                "max_pages": 35,
                "quality": "good"
            },
            "This American Life": {
                "url_pattern": "https://www.thisamericanlife.org/archive",
                "max_pages": 25,
                "quality": "excellent"
            },
            "The Ezra Klein Show": {
                "url_pattern": "https://www.nytimes.com/column/ezra-klein-podcast",
                "max_pages": 20,
                "quality": "good"
            },
            "Decoder with Nilay Patel": {
                "url_pattern": "https://www.theverge.com/decoder-podcast-with-nilay-patel",
                "max_pages": 15,
                "quality": "good"
            },
            "The Vergecast": {
                "url_pattern": "https://www.theverge.com/the-vergecast-podcast",
                "max_pages": 15,
                "quality": "good"
            }
        }

        # Initialize Crawl4AI
        self.crawler = None

    async def initialize_crawler(self):
        """Initialize AsyncWebCrawler"""
        self.crawler = AsyncWebCrawler(
            headless=True,
            verbose=True,
            browser_type="chromium",
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )

    async def cleanup_crawler(self):
        """Cleanup crawler"""
        if self.crawler:
            await self.crawler.close()

    def get_podcast_episodes_count(self, podcast_name):
        """Get total episodes for progress tracking"""
        conn = sqlite3.connect(str(self.db_path))

        # Handle podcast name variations
        if "|" in podcast_name:
            parts = podcast_name.split("|")
            where_clause = f"WHERE name LIKE '%{parts[0].strip()}%'"
        else:
            where_clause = f"WHERE name = '{podcast_name}'"

        query = f"""
            SELECT COUNT(*) as total
            FROM episodes e
            JOIN podcasts p ON e.podcast_id = p.id
            {where_clause}
        """

        try:
            cursor = conn.execute(query)
            result = cursor.fetchone()
            return result[0] if result else 0
        except Exception as e:
            logger.error(f"Error getting episode count for {podcast_name}: {e}")
            return 0
        finally:
            conn.close()

    async def scrape_lex_fridman_archive(self):
        """Scrape entire Lex Fridman transcript archive"""
        podcast_name = "Lex Fridman Podcast"
        base_url = "https://lexfridman.com/category/transcripts/"

        logger.info(f"🚀 Starting bulk scrape of {podcast_name}")
        total_episodes = self.get_podcast_episodes_count(podcast_name)
        logger.info(f"📊 Total episodes in database: {total_episodes}")

        scraped_count = 0

        try:
            # Crawl transcript archive page
            result = await self.crawler.arun(
                url=base_url,
                word_count_threshold=10,
                extraction_strategy="None",
                css_selector=".post-title a, .entry-title a, .title a"
            )

            if result.success:
                # Extract transcript URLs from the page
                transcript_urls = []

                # Try different selectors for transcript links
                for link in result.cleaned_html.split('\n'):
                    if '/podcast/' in link and len(link) > 30:
                        # Clean up the URL
                        url = link.strip()
                        if url.startswith('href="'):
                            url = url[6:-1]  # Remove href="
                        elif url.startswith('http'):
                            pass  # Already a full URL
                        else:
                            url = f"https://lexfridman.com{url}"

                        if url and '/podcast/' in url:
                            transcript_urls.append(url)

                logger.info(f"📋 Found {len(transcript_urls)} transcript URLs")

                # Process each transcript
                for i, transcript_url in enumerate(transcript_urls[:30]):  # Limit to first 30 for testing
                    logger.info(f"📄 Processing transcript {i+1}/{min(len(transcript_urls), 30)}: {transcript_url}")

                    try:
                        # Get transcript content
                        transcript_result = await self.crawler.arun(
                            url=transcript_url,
                            word_count_threshold=100,
                            extraction_strategy="LXML",
                            css_selector=".entry-content, .post-content, .transcript-content, .content"
                        )

                        if transcript_result.success and transcript_result.cleaned_text:
                            # Extract episode information
                            title = self.extract_episode_title_from_url(transcript_url, transcript_result.cleaned_text)
                            episode_id = self.find_episode_id_by_title(podcast_name, title)

                            if episode_id:
                                success = self.save_transcript(
                                    episode_id, podcast_name, title,
                                    transcript_result.cleaned_text, transcript_url
                                )
                                if success:
                                    scraped_count += 1
                                logger.info(f"✅ Saved: {title}")
                            else:
                                logger.warning(f"⚠️  Episode not found in database: {title}")

                        # Rate limiting
                        await asyncio.sleep(2)

                    except Exception as e:
                        logger.error(f"❌ Error processing {transcript_url}: {e}")
                        continue

        except Exception as e:
            logger.error(f"❌ Error scraping {podcast_name}: {e}")

        logger.info(f"🏁 {podcast_name} complete: {scraped_count} transcripts scraped")
        return scraped_count

    def extract_episode_title_from_url(self, url, content):
        """Extract episode title from URL or content"""
        # Extract from URL pattern: /podcast/123-guest-name/
        import re

        # Try to get from URL
        url_match = re.search(r'/podcast/(\d+)(?:-|.*)', url)
        if url_match:
            # Try to get title from content first lines
            lines = content.split('\n')[:5]
            for line in lines:
                if len(line.strip()) > 10 and not line.startswith('Listen'):
                    return line.strip()

        # Fallback: use first non-empty line
        for line in content.split('\n')[:10]:
            if len(line.strip()) > 10:
                return line.strip()

        return "Unknown Episode"

    def find_episode_id_by_title(self, podcast_name, title):
        """Find episode ID by matching title"""
        conn = sqlite3.connect(str(self.db_path))

        # Create simplified title for matching
        simplified_title = title[:100].lower().replace('"', '').replace("'", "").replace(":", "")

        try:
            # Try exact match first
            cursor = conn.execute(f"""
                SELECT e.id FROM episodes e
                JOIN podcasts p ON e.podcast_id = p.id
                WHERE p.name LIKE '%{podcast_name.split()[0]}%'
                AND LOWER(e.title) LIKE ?
                LIMIT 1
            """, (f"%{simplified_title}%",))

            result = cursor.fetchone()
            if result:
                return result[0]

            # Try fuzzy matching
            cursor = conn.execute(f"""
                SELECT e.id, e.title FROM episodes e
                JOIN podcasts p ON e.podcast_id = p.id
                WHERE p.name LIKE '%{podcast_name.split()[0]}%'
                ORDER BY e.id DESC
                LIMIT 50
            """)

            episodes = cursor.fetchall()
            for episode_id, episode_title in episodes:
                episode_title_simple = episode_title.lower().replace('"', '').replace("'", "")
                if any(word in episode_title_simple for word in simplified_title.split() if len(word) > 3):
                    return episode_id

            return None

        except Exception as e:
            logger.error(f"Error finding episode ID: {e}")
            return None
        finally:
            conn.close()

    def save_transcript(self, episode_id, podcast_name, title, content, source_url):
        """Save transcript to file"""
        if not content or len(content.strip()) < 200:
            return False

        # Create safe filename
        safe_title = re.sub(r'[^\w\s-]', '', title[:50])
        filename = f"{episode_id} - {safe_title}.md"
        filepath = self.transcripts_dir / filename

        # Create markdown content
        markdown_content = f"""# {title}

**Podcast:** {podcast_name}
**Episode ID:** {episode_id}
**Source URL:** {source_url}
**Downloaded:** {datetime.now().isoformat()}

## Transcript

{content}
"""

        # Save file
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            return True
        except Exception as e:
            logger.error(f"Error saving transcript: {e}")
            return False

    async def process_reliable_sources(self):
        """Process all reliable podcast sources"""
        await self.initialize_crawler()

        total_scraped = 0

        try:
            # Start with Lex Fridman (highest quality source)
            for podcast_name, config in self.reliable_sources.items():
                if podcast_name == "Lex Fridman Podcast":
                    logger.info(f"\n🎯 Bulk scraping: {podcast_name}")
                    scraped = await self.scrape_lex_fridman_archive()
                    total_scraped += scraped

                    # Break after first successful run for testing
                    break

        finally:
            await self.cleanup_crawler()

        logger.info(f"🏆 Total transcripts scraped: {total_scraped}")
        return total_scraped

async def main():
    scraper = Crawl4AIPodcastScraper()
    total = await scraper.process_reliable_sources()
    print(f"\n🎉 Scraping complete! {total} transcripts downloaded")

if __name__ == "__main__":
    # Install Crawl4AI if not available
    try:
        import crawl4ai
    except ImportError:
        print("Installing Crawl4AI...")
        os.system("pip install crawl4ai")
        print("Crawl4AI installed. Please run the script again.")
        exit()

    # Run the scraper
    asyncio.run(main())