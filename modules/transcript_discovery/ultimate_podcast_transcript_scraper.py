#!/usr/bin/env python3
"""
Ultimate Crawl4AI Podcast Transcript Scraper
Using Crawl4AI best practices for bulk data ingestion from web podcast sources
"""

import os
import time
import json
import sqlite3
import asyncio
from pathlib import Path
from datetime import datetime
import logging
from typing import List, Dict, Any

import requests
from bs4 import BeautifulSoup

# Crawl4AI imports
from crawl4ai import AsyncWebCrawler
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from crawl4ai.chunking_strategy import RegexChunking

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UltimateCrawl4AIScraper:
    """Ultimate Crawl4AI podcast transcript scraper using best practices"""

    def __init__(self):
        self.root_dir = Path("/home/ubuntu/dev/atlas")
        self.transcripts_dir = self.root_dir / "transcripts"
        self.transcripts_dir.mkdir(exist_ok=True)

        # Database
        self.db_path = self.root_dir / "podcast_processing.db"

        # Crawl4AI crawler
        self.crawler = None

        # Podcast sources with structured extraction instructions
        self.podcast_sources = {
            "Lex Fridman Podcast": {
                "archive_url": "https://lexfridman.com/category/transcripts/",
                "pattern": r"/podcast/\d+",
                "css_selector": ".post-title a, .entry-title a, .title a",
                "content_selector": ".entry-content, .post-content",
                "max_depth": 50,
                "quality": "excellent",
                "chunking": RegexChunking(
                    patterns=[r'\n\n', r'\n'],  # Split on double newlines
                    overlap=100
                )
            },
            "EconTalk": {
                "archive_url": "https://www.econlib.org/econtalk-archives-by-date/",
                "pattern": r"/archives/episodes/",
                "css_selector": ".entry-title a, .post-title a",
                "content_selector": ".entry-content",
                "max_depth": 100,
                "quality": "excellent",
                "chunking": RegexChunking(patterns=[r'\n\n', r'\n'])
            },
            "99% Invisible": {
                "archive_url": "https://99percentinvisible.org/episodes/",
                "pattern": r"/episode/",
                "css_selector": ".episode-title a, .post-title a",
                "content_selector": ".entry-content",
                "max_depth": 80,
                "quality": "good",
                "chunking": RegexChunking(patterns=[r'\n\n', r'\n'])
            }
        }

    async def initialize_crawler(self):
        """Initialize AsyncWebCrawler with optimized settings"""
        self.crawler = AsyncWebCrawler(
            headless=True,
            verbose=False,
            browser_type="chromium",
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            # Performance optimizations
            delay_between_requests=1.5,
            max_concurrent_requests=3,
            # Memory management
            browser_cache_path=str(self.root_dir / ".cache"),
            keep_browser_open=True,
        )

    async def cleanup_crawler(self):
        """Cleanup resources"""
        if self.crawler:
            await self.crawler.close()

    def get_podcast_stats(self, podcast_name: str) -> Dict[str, Any]:
        """Get statistics for a podcast"""
        conn = sqlite3.connect(str(self.db_path))

        try:
            # Get episode count
            cursor = conn.execute(f"""
                SELECT COUNT(*) as total,
                       MIN(published_date) as earliest,
                       MAX(published_date) as latest
                FROM episodes e
                JOIN podcasts p ON e.podcast_id = p.id
                WHERE p.name LIKE '%{podcast_name.split()[0]}%'
            """)

            stats = cursor.fetchone()
            return {
                'total_episodes': stats[0] if stats else 0,
                'earliest': stats[1],
                'latest': stats[2]
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {'total_episodes': 0}
        finally:
            conn.close()

    async def discover_transcript_urls(self, podcast_name: str, config: Dict) -> List[Dict]:
        """Discover all transcript URLs for a podcast"""
        logger.info(f"🔍 Discovering URLs for {podcast_name}")

        archive_url = config['archive_url']
        css_selector = config['css_selector']
        max_depth = config['max_depth']

        # Use structured extraction to get all transcript URLs
        extraction_strategy = {
            "type": "json",
            "fields": [
                {
                    "name": "transcript_links",
                    "description": f"Array of transcript URLs and titles from {podcast_name}",
                    "type": "array[string]"
                }
            ]
        }

        try:
            result = await self.crawler.arun(
                url=archive_url,
                css_selector=css_selector,
                extraction_strategy=extraction_strategy,
                wait_for_selector=css_selector,
                delay_before_return_html=1,
                page_timeout=10000
            )

            if result.success and result.extracted_content:
                # Parse the extracted content for URLs
                content = result.extracted_content.get('markdown', '')
                soup = BeautifulSoup(content, 'html.parser')

                transcript_urls = []
                for link in soup.find_all('a', href=True):
                    href = link.get('href', '')
                    title = link.get_text().strip()

                    if config['pattern'] and not re.search(config['pattern'], href):
                        continue

                    # Create full URL
                    if href.startswith('/'):
                        if archive_url.endswith('/'):
                            full_url = archive_url + href[1:]
                        else:
                            full_url = archive_url.rsplit('/', 1)[0] + href
                    else:
                        full_url = href

                    transcript_urls.append({
                        'title': title,
                        'url': full_url
                    })

                # Limit based on max_depth
                transcript_urls = transcript_urls[:max_depth]

                logger.info(f"📊 Found {len(transcript_urls)} transcript URLs for {podcast_name}")
                return transcript_urls

        except Exception as e:
            logger.error(f"❌ Error discovering URLs for {podcast_name}: {e}")
            return []

        return []

    async def batch_process_transcripts(self, podcast_name: str, transcript_urls: List[Dict], config: Dict) -> int:
        """Process transcripts in batches using Crawl4AI best practices"""
        logger.info(f"🚀 Batch processing {len(transcript_urls)} transcripts for {podcast_name}")

        # Prepare URLs for batch processing
        urls = [url['url'] for url in transcript_urls]
        titles = [url['title'] for url in transcript_urls]

        # Create extraction strategy for transcript content
        extraction_strategy = {
            "type": "json",
            "fields": [
                {
                    "name": "transcript_content",
                    "description": "Full transcript text content with speaker labels and timestamps",
                    "type": "string"
                },
                {
                    "name": "episode_metadata",
                    "description": "Episode metadata including guest, date, and episode number",
                    "type": "string"
                }
            ]
        }

        # Process in batches
        batch_size = 10  # Conservative batch size for reliability
        processed_count = 0

        for i in range(0, len(urls), batch_size):
            batch_urls = urls[i:i + batch_size]
            batch_titles = titles[i:i + batch_size]

            logger.info(f"📦 Processing batch {i//batch_size + 1}/{(len(urls)//batch_size) + 1}")

            try:
                # Use arun_many for parallel processing
                results = await self.crawler.arun_many(
                    urls=batch_urls,
                    extraction_strategy=extraction_strategy,
                    css_selector=config.get('content_selector', '.entry-content'),
                    delay_before_return_html=1,
                    page_timeout=15000
                )

                # Process results
                for j, result in enumerate(results):
                    if result.success and result.extracted_content:
                        title = batch_titles[j]
                        content = result.extracted_content

                        # Extract transcript content
                        transcript_text = self.extract_transcript_text(result)
                        if transcript_text:
                            episode_id = self.find_episode_id(podcast_name, title)
                            if episode_id:
                                success = self.save_transcript(
                                    episode_id, podcast_name, title, transcript_text, batch_urls[j]
                                )
                                if success:
                                    processed_count += 1
                                    logger.info(f"✅ Saved: {title}")

                        # Rate limiting between batches
                        if j < len(batch_urls) - 1:
                            await asyncio.sleep(0.5)

                    # Rate limiting between batches
                    if i + batch_size < len(urls):
                        await asyncio.sleep(2)

            except Exception as e:
                logger.error(f"❌ Error processing batch {i//batch_size + 1}: {e}")
                continue

        logger.info(f"🏁 Completed {podcast_name}: {processed_count}/{len(transcript_urls)} transcripts processed")
        return processed_count

    def extract_transcript_text(self, crawl_result) -> str:
        """Extract clean transcript text from crawl result"""
        try:
            # Try extracted content first
            if crawl_result.extracted_content:
                content = crawl_result.extracted_content
                if isinstance(content, dict):
                    transcript = content.get('transcript_content', '')
                    if transcript:
                        return transcript.strip()

            # Fallback to cleaned HTML
            if crawl_result.cleaned_html:
                soup = BeautifulSoup(crawl_result.cleaned_html, 'html.parser')

                # Remove script/style elements
                for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                    element.decompose()

                # Get main content
                content_text = soup.get_text()

                # Clean up whitespace
                lines = [line.strip() for line in content_text.split('\n') if line.strip()]
                cleaned_content = '\n'.join(lines)

                # Filter out very short lines and boilerplate
                filtered_lines = []
                for line in lines:
                    if (len(line) > 50 or
                        any(keyword in line.lower() for keyword in ['transcript', 'episode', 'podcast'])):
                        filtered_lines.append(line)

                return '\n'.join(filtered_lines)

            return ""
        except Exception as e:
            logger.error(f"Error extracting transcript text: {e}")
            return ""

    def find_episode_id(self, podcast_name: str, title: str) -> int:
        """Find episode ID by matching title"""
        conn = sqlite3.connect(str(self.db_path))

        try:
            # Try exact match first
            cursor = conn.execute(f"""
                SELECT e.id FROM episodes e
                JOIN podcasts p ON e.podcast_id = p.id
                WHERE p.name LIKE '%{podcast_name.split()[0]}%'
                AND e.title = ?
                LIMIT 1
            """, (title,))

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
                # Simple text similarity check
                title_words = set(title.lower().split())
                episode_words = set(episode_title.lower().split())
                if title_words & episode_words:  # If any words match
                    return episode_id

            return None

        except Exception as e:
            logger.error(f"Error finding episode ID: {e}")
            return None
        finally:
            conn.close()

    def save_transcript(self, episode_id: int, podcast_name: str, title: str, content: str, source_url: str) -> bool:
        """Save transcript to file"""
        if not content or len(content.strip()) < 200:
            return False

        # Create safe filename
        safe_title = re.sub(r'[^\w\s-]', '', title[:60])
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

    async def process_all_sources(self):
        """Process all reliable podcast sources"""
        await self.initialize_crawler()

        total_processed = 0
        processed_by_podcast = {}

        try:
            for podcast_name, config in self.podcast_sources.items():
                logger.info(f"\n🎯 Starting: {podcast_name}")

                # Get stats
                stats = self.get_podcast_stats(podcast_name)
                logger.info(f"📊 Stats: {stats['total_episodes']} episodes")

                # Discover URLs
                transcript_urls = await self.discover_transcript_urls(podcast_name, config)

                if transcript_urls:
                    # Process transcripts
                    processed = await self.batch_process_transcripts(podcast_name, transcript_urls, config)
                    processed_by_podcast[podcast_name] = processed
                    total_processed += processed
                else:
                    logger.warning(f"⚠️ No transcript URLs found for {podcast_name}")

                # Brief pause between podcasts
                await asyncio.sleep(3)

        finally:
            await self.cleanup_crawler()

        # Final summary
        logger.info("\n🏆 BULK SCRAPING COMPLETE")
        logger.info(f"📊 Total transcripts processed: {total_processed}")
        for podcast, count in processed_by_podcast.items():
            logger.info(f"  📚 {podcast}: {count} transcripts")

        return total_processed

async def main():
    """Main execution"""
    print("🚀 Starting Ultimate Crawl4AI Podcast Transcript Scraper")
    print("📚 Using Crawl4AI best practices for bulk web data ingestion")
    print()

    scraper = UltimateCrawl4AIScraper()
    total = await scraper.process_all_sources()

    print(f"\n🎉 SUCCESS! {total} transcripts downloaded and saved")
    print(f"📁 Location: {scraper.transcripts_dir}")

if __name__ == "__main__":
    import re
    import sys

    # Check for dependencies
    try:
        from crawl4ai import AsyncWebCrawler
    except ImportError:
        print("Installing Crawl4AI...")
        os.system("pip install crawl4ai")
        print("Crawl4AI installed. Please run the script again.")
        sys.exit(1)

    # Run the scraper
    asyncio.run(main())