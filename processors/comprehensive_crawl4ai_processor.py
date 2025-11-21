#!/usr/bin/env python3
"""
Comprehensive Crawl4AI Transcript Processor
Handles rate limiting, multiple sessions, and reliable bulk processing
Processes all working podcast sources slowly and systematically
"""

import asyncio
import json
import sqlite3
import time
import os
from pathlib import Path
from datetime import datetime, timedelta
import logging
import random
from typing import List, Dict, Any, Optional

from crawl4ai import AsyncWebCrawler
from crawl4ai.extraction_strategy import LLMExtractionStrategy, JsonCssExtractionStrategy
from crawl4ai.chunking_strategy import RegexChunking

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ComprehensiveCrawl4AIProcessor:
    """Comprehensive transcript processor using Crawl4AI with rate limiting and multi-session support"""

    def __init__(self):
        self.root_dir = Path("/home/ubuntu/dev/atlas")
        self.transcripts_dir = self.root_dir / "transcripts"
        self.transcripts_dir.mkdir(exist_ok=True)

        # Database
        self.db_path = self.root_dir / "podcast_processing.db"

        # Load updated sources
        with open(self.root_dir / "podcast_transcript_sources.json", "r") as f:
            self.sources = json.load(f)

        # Processing state
        self.crawler = None
        self.session_stats = {
            'processed': 0,
            'failed': 0,
            'start_time': datetime.now(),
            'last_save': datetime.now()
        }

        # Rate limiting configuration
        self.config = {
            'delay_between_requests': 3.0,  # Base delay in seconds
            'max_concurrent_requests': 2,   # Conservative concurrency
            'session_duration_hours': 4,    # 4-hour sessions
            'daily_limit': 200,              # Daily transcript limit
            'batch_size': 5,                 # Small batches for reliability
            'retry_attempts': 3,             # Retry failed attempts
            'progress_save_interval': 10     # Save progress every 10 transcripts
        }

    async def initialize_crawler(self):
        """Initialize Crawl4AI crawler with rate-limiting settings"""
        self.crawler = AsyncWebCrawler(
            headless=True,
            verbose=False,
            browser_type="chromium",
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            # Rate limiting settings
            delay_between_requests=self.config['delay_between_requests'],
            max_concurrent_requests=self.config['max_concurrent_requests'],
            # Memory and performance
            browser_cache_path=str(self.root_dir / ".crawl4ai_cache"),
            keep_browser_open=True,
            # Timeout settings
            page_timeout=30000,  # 30 seconds
            request_timeout=15000  # 15 seconds
        )

    async def cleanup_crawler(self):
        """Clean up crawler resources"""
        if self.crawler:
            await self.crawler.close()

    def get_working_podcasts(self) -> List[str]:
        """Get list of working podcast sources"""
        working = []
        for podcast_name, config in self.sources['podcast_sources'].items():
            if (config.get('reliable', False) or
                config.get('status') != 'no_consistent_transcript_source'):
                working.append(podcast_name)
        return working

    def get_podcast_episodes(self, podcast_name: str, limit: int = 10) -> List[tuple]:
        """Get episodes for a podcast that need transcripts"""
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

    async def crawl_directory(self, base_url: str, podcast_name: str, max_episodes: int = 50) -> List[Dict]:
        """Crawl directory pages to find transcript URLs (like Conversations with Tyler)"""
        logger.info(f"🔍 Crawling directory: {base_url}")

        try:
            # Start with the main page
            result = await self.crawler.arun(
                url=base_url,
                wait_for_selector="a[href*='/episodes/'], a[href*='/podcast/']",
                delay_before_return_html=2,
                word_count_threshold=10
            )

            if not result.success:
                return []

            # Extract all episode links
            episode_links = []
            soup = self.crawler.browser_page.content() if hasattr(self.crawler, 'browser_page') else None

            if result.cleaned_html:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(result.cleaned_html, 'html.parser')

                for link in soup.find_all('a', href=True):
                    href = link.get('href')
                    title = link.get_text().strip()

                    # Look for episode links
                    if any(indicator in href.lower() for indicator in ['episode', 'transcript']):
                        full_url = href if href.startswith('http') else f"{base_url.rstrip('/')}/{href.lstrip('/')}"
                        episode_links.append({
                            'url': full_url,
                            'title': title,
                            'podcast': podcast_name
                        })

            # Limit episodes
            episode_links = episode_links[:max_episodes]
            logger.info(f"📋 Found {len(episode_links)} episode pages for {podcast_name}")

            return episode_links

        except Exception as e:
            logger.error(f"❌ Error crawling directory {base_url}: {e}")
            return []

    async def process_podcast_source(self, podcast_name: str, config: Dict) -> int:
        """Process a single podcast source with appropriate strategy"""
        logger.info(f"\n🎯 Processing: {podcast_name}")

        processed_count = 0
        episodes = self.get_podcast_episodes(podcast_name, limit=self.config['batch_size'])

        if not episodes:
            logger.info(f"⚠️ No pending episodes for {podcast_name}")
            return 0

        # Choose processing strategy based on source configuration
        crawl_strategy = config.get('crawl_strategy')

        if crawl_strategy == 'directory_crawl':
            # For sources like Conversations with Tyler
            transcript_urls = await self.crawl_directory(config['primary'], podcast_name)
            for episode_data in transcript_urls:
                if processed_count >= len(episodes):
                    break

                # Try to match with database episodes
                episode = episodes[processed_count]
                success = await self.extract_transcript_from_url(
                    episode_data['url'], episode[0], podcast_name, episode[1]
                )
                if success:
                    processed_count += 1

        else:
            # Standard processing for individual episode pages
            for episode_id, episode_title, actual_podcast_name in episodes:
                success = await self.process_single_episode(
                    episode_id, actual_podcast_name, episode_title, config
                )
                if success:
                    processed_count += 1

                # Rate limiting between episodes
                await asyncio.sleep(self.config['delay_between_requests'])

        logger.info(f"✅ {podcast_name}: {processed_count} transcripts processed")
        return processed_count

    async def process_single_episode(self, episode_id: int, podcast_name: str,
                                   episode_title: str, config: Dict) -> bool:
        """Process a single episode transcript"""
        sources_to_try = []

        # Add primary, secondary, tertiary sources
        for key in ['primary', 'secondary', 'tertiary']:
            if key in config and config[key]:
                sources_to_try.append(config[key])

        for source_url in sources_to_try:
            try:
                success = await self.extract_transcript_from_url(
                    source_url, episode_id, podcast_name, episode_title
                )
                if success:
                    return True

                # Small delay between sources
                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"❌ Error with source {source_url}: {e}")
                continue

        return False

    async def extract_transcript_from_url(self, url: str, episode_id: int,
                                        podcast_name: str, episode_title: str) -> bool:
        """Extract transcript from a specific URL"""
        try:
            # Dynamic delay to be respectful
            delay = self.config['delay_between_requests'] + random.uniform(0, 2)
            await asyncio.sleep(delay)

            # Configure extraction strategy based on URL pattern
            if 'transcriptforest.com' in url or 'musixmatch.com' in url:
                extraction_strategy = JsonCssExtractionStrategy(
                    schema={
                        "name": "transcript_extractor",
                        "baseSelector": "main, .content, .transcript",
                        "fields": [
                            {
                                "name": "content",
                                "selector": "p, div",
                                "type": "text",
                                "multiple": True
                            }
                        ]
                    }
                )
            else:
                # Generic text extraction
                extraction_strategy = None

            result = await self.crawler.arun(
                url=url,
                extraction_strategy=extraction_strategy,
                word_count_threshold=100,
                delay_before_return_html=2,
                page_timeout=20000
            )

            if result.success and (result.cleaned_text or result.markdown):
                content = result.cleaned_text or result.markdown or ""
                transcript_content = self.clean_transcript_content(content)

                if len(transcript_content) > 500:  # Minimum content threshold
                    return self.save_transcript(
                        episode_id, podcast_name, episode_title,
                        transcript_content, url
                    )
                else:
                    logger.warning(f"⚠️ Content too short: {len(transcript_content)} chars")
            else:
                logger.warning(f"⚠️ Failed to extract from {url}")

        except Exception as e:
            logger.error(f"❌ Error extracting from {url}: {e}")

        return False

    def clean_transcript_content(self, content: str) -> str:
        """Clean and normalize transcript content"""
        if not content:
            return ""

        # Basic cleaning
        lines = content.split('\n')
        cleaned_lines = []

        for line in lines:
            line = line.strip()
            if len(line) > 20 and not line.lower().startswith(('cookie', 'privacy', 'terms')):
                cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)

    def save_transcript(self, episode_id: int, podcast_name: str, episode_title: str,
                       content: str, source_url: str) -> bool:
        """Save transcript to file and update database"""
        try:
            import re

            # Create safe filename
            safe_title = re.sub(r'[^\w\s-]', '', episode_title[:60])
            filename = f"{episode_id} - {safe_title}.md"
            filepath = self.transcripts_dir / filename

            # Create markdown content
            markdown_content = f"""# {episode_title}

**Podcast:** {podcast_name}
**Episode ID:** {episode_id}
**Source URL:** {source_url}
**Method:** Crawl4AI
**Downloaded:** {datetime.now().isoformat()}

## Transcript

{content}
"""

            # Save file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(markdown_content)

            # Update database
            self.update_transcript_status(episode_id, True, source_url)

            # Update session stats
            self.session_stats['processed'] += 1

            logger.info(f"✅ Saved: {episode_title}")
            return True

        except Exception as e:
            logger.error(f"❌ Error saving transcript: {e}")
            self.session_stats['failed'] += 1
            return False

    def update_transcript_status(self, episode_id: int, found: bool, source_url: str = None):
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

    def save_session_progress(self):
        """Save current session progress"""
        progress_file = self.root_dir / f"crawl_progress_{datetime.now().strftime('%Y%m%d')}.json"

        progress_data = {
            'timestamp': datetime.now().isoformat(),
            'stats': self.session_stats,
            'config': self.config
        }

        with open(progress_file, 'w') as f:
            json.dump(progress_data, f, indent=2)

        logger.info(f"💾 Progress saved: {progress_file}")

    async def run_comprehensive_processing(self):
        """Run comprehensive processing of all working sources"""
        await self.initialize_crawler()

        try:
            working_podcasts = self.get_working_podcasts()
            logger.info(f"🚀 Starting comprehensive processing of {len(working_podcasts)} working sources")

            total_processed = 0
            session_start = datetime.now()

            for i, podcast_name in enumerate(working_podcasts, 1):
                # Check daily limit
                if self.session_stats['processed'] >= self.config['daily_limit']:
                    logger.info(f"🛑 Daily limit reached: {self.config['daily_limit']} transcripts")
                    break

                # Check session duration
                if (datetime.now() - session_start).total_seconds() > (self.config['session_duration_hours'] * 3600):
                    logger.info(f"🛑 Session duration reached: {self.config['session_duration_hours']} hours")
                    break

                logger.info(f"\n📊 Progress: {i}/{len(working_podcasts)} | "
                          f"Processed: {self.session_stats['processed']} | "
                          f"Failed: {self.session_stats['failed']}")

                config = self.sources['podcast_sources'].get(podcast_name, {})

                # Skip if no reliable sources
                if config.get('status') == 'no_consistent_transcript_source':
                    logger.info(f"⏭️ Skipping {podcast_name} - no reliable source")
                    continue

                processed = await self.process_podcast_source(podcast_name, config)
                total_processed += processed

                # Save progress periodically
                if total_processed % self.config['progress_save_interval'] == 0:
                    self.save_session_progress()

                # Break between podcasts
                await asyncio.sleep(5)

            # Final summary
            logger.info("\n" + "="*60)
            logger.info("🏆 COMPREHENSIVE PROCESSING COMPLETE")
            logger.info(f"📊 Total transcripts processed: {total_processed}")
            logger.info(f"⏱️ Session duration: {datetime.now() - session_start}")
            logger.info(f"✅ Success rate: {self.session_stats['processed']/(self.session_stats['processed'] + self.session_stats['failed'])*100:.1f}%")

            # Save final progress
            self.save_session_progress()

            return total_processed

        finally:
            await self.cleanup_crawler()

async def main():
    """Main execution"""
    processor = ComprehensiveCrawl4AIProcessor()
    total = await processor.run_comprehensive_processing()

    logger.info(f"\n🎉 Comprehensive processing complete! {total} transcripts downloaded")
    logger.info("📁 Check the transcripts directory for results")

if __name__ == "__main__":
    # Check for Crawl4AI installation
    try:
        from crawl4ai import AsyncWebCrawler
    except ImportError:
        print("Installing Crawl4AI...")
        os.system("pip install crawl4ai")
        print("Crawl4AI installed. Please run the script again.")
        exit()

    # Run the comprehensive processor
    asyncio.run(main())