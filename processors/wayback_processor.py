#!/usr/bin/env python3
"""
Wayback Machine Processor
Processes failed sources using Internet Archive Wayback Machine
Finds historical transcript pages that may no longer be available
"""

import asyncio
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
import logging
import requests
from urllib.parse import quote
from bs4 import BeautifulSoup
import sqlite3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WaybackMachineProcessor:
    """Process transcripts using Wayback Machine for failed sources"""

    def __init__(self):
        self.root_dir = Path("/home/ubuntu/dev/atlas")
        self.transcripts_dir = self.root_dir / "transcripts"
        self.transcripts_dir.mkdir(exist_ok=True)

        # Database
        self.db_path = self.root_dir / "podcast_processing.db"

        # Failed sources that need Wayback processing
        self.failed_sources = [
            "Channels with Peter Kafka",
            "Conversations with Tyler",
            "Pivot",
            "The Layover",
            "The Town with Matthew Belloni"
        ]

        # Wayback Machine API
        self.wayback_api = "http://web.archive.org/cdx/search/cdx"
        self.wayback_url = "http://web.archive.org/web"

        # Rate limiting
        self.delay_between_requests = 5.0

        # Load sources config
        with open(self.root_dir / "podcast_transcript_sources.json", "r") as f:
            self.sources = json.load(f)

    def get_podcast_episodes(self, podcast_name: str, limit: int = 5):
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

    def search_wayback_for_url(self, url: str, years_back: int = 3) -> list:
        """Search Wayback Machine for snapshots of a URL"""
        logger.info(f"🔍 Searching Wayback for: {url}")

        try:
            # Calculate start date
            end_date = datetime.now()
            start_date = end_date - timedelta(days=years_back * 365)

            params = {
                'url': url,
                'from': start_date.strftime('%Y%m%d'),
                'to': end_date.strftime('%Y%m%d'),
                'statuscode': '200',
                'filter': 'statuscode:200',
                'collapse': 'timestamp:8',
                'limit': 50
            }

            response = requests.get(self.wayback_api, params=params, timeout=30)

            if response.status_code == 200:
                snapshots = []
                for line in response.text.strip().split('\n'):
                    if line:
                        parts = line.split()
                        if len(parts) >= 2:
                            timestamp = parts[1]
                            original_url = parts[2]
                            wayback_url = f"{self.wayback_url}/{timestamp}/{original_url}"
                            snapshots.append({
                                'timestamp': timestamp,
                                'original_url': original_url,
                                'wayback_url': wayback_url
                            })

                logger.info(f"📋 Found {len(snapshots)} Wayback snapshots")
                return snapshots
            else:
                logger.error(f"❌ Wayback API error: {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"❌ Error searching Wayback: {e}")
            return []

    async def extract_transcript_from_wayback(self, wayback_url: str, podcast_name: str, episode_title: str) -> str:
        """Extract transcript content from Wayback Machine URL"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }

            # Add delay to be respectful
            await asyncio.sleep(self.delay_between_requests)

            response = requests.get(wayback_url, headers=headers, timeout=60)

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')

                # Remove script/style elements
                for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                    element.decompose()

                # Try to find transcript content
                content = ""

                # Common transcript content selectors
                content_selectors = [
                    '.transcript-content',
                    '.episode-content',
                    '.post-content',
                    '.entry-content',
                    'main',
                    'article',
                    '.content'
                ]

                for selector in content_selectors:
                    elements = soup.select(selector)
                    if elements:
                        for element in elements:
                            text = element.get_text().strip()
                            if len(text) > 500:  # Substantial content
                                content += text + "\n\n"
                        break

                if not content:
                    # Fallback to body content
                    content = soup.get_text()

                # Clean up the content
                cleaned_content = self.clean_wayback_content(content)

                if len(cleaned_content) > 1000:  # Minimum threshold for transcripts
                    logger.info(f"✅ Extracted {len(cleaned_content)} characters from Wayback")
                    return cleaned_content
                else:
                    logger.warning(f"⚠️ Content too short: {len(cleaned_content)} characters")
                    return ""

            else:
                logger.error(f"❌ Failed to fetch Wayback URL: {response.status_code}")
                return ""

        except Exception as e:
            logger.error(f"❌ Error extracting from Wayback: {e}")
            return ""

    def clean_wayback_content(self, content: str) -> str:
        """Clean content extracted from Wayback Machine"""
        if not content:
            return ""

        # Remove Wayback Machine boilerplate
        lines = content.split('\n')
        cleaned_lines = []

        skip_phrases = [
            'web.archive.org',
            'wayback machine',
            'saved from',
            'captured',
            'internet archive',
            'cache',
            'archived',
            'snapshot'
        ]

        for line in lines:
            line = line.strip()

            # Skip Wayback boilerplate and very short lines
            if (len(line) > 50 and
                not any(phrase in line.lower() for phrase in skip_phrases) and
                not line.lower().startswith(('http', 'www', 'captcha', 'robot'))):
                cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)

    def save_transcript(self, episode_id: int, podcast_name: str, episode_title: str,
                       content: str, source_url: str, wayback_url: str = None) -> bool:
        """Save transcript from Wayback Machine"""
        try:
            import re

            safe_title = re.sub(r'[^\w\s-]', '', episode_title[:60])
            filename = f"{episode_id} - {safe_title} - WAYBACK.md"
            filepath = self.transcripts_dir / filename

            markdown_content = f"""# {episode_title}

**Podcast:** {podcast_name}
**Episode ID:** {episode_id}
**Original URL:** {source_url}
**Wayback URL:** {wayback_url or 'N/A'}
**Method:** Wayback Machine
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
            """, (True, f"Wayback: {source_url}", episode_id))
            conn.commit()
            conn.close()

            logger.info(f"✅ Saved Wayback transcript: {episode_title}")
            return True

        except Exception as e:
            logger.error(f"❌ Error saving Wayback transcript: {e}")
            return False

    async def process_wayback_for_podcast(self, podcast_name: str):
        """Process all episodes for a podcast using Wayback Machine"""
        logger.info(f"\n🎯 Processing Wayback for: {podcast_name}")

        episodes = self.get_podcast_episodes(podcast_name, limit=3)
        if not episodes:
            logger.info(f"⚠️ No pending episodes for {podcast_name}")
            return 0

        processed_count = 0
        podcast_config = self.sources['podcast_sources'].get(podcast_name, {})

        for episode_id, episode_title, actual_podcast_name in episodes:
            logger.info(f"📚 Episode: {episode_title}")

            # Try to find original URLs and search Wayback
            original_urls = []

            if 'primary' in podcast_config:
                original_urls.append(podcast_config['primary'])
            if 'secondary' in podcast_config:
                original_urls.append(podcast_config['secondary'])

            success = False
            for original_url in original_urls:
                if not original_url:
                    continue

                # Search Wayback for this URL
                snapshots = self.search_wayback_for_url(original_url, years_back=5)

                for snapshot in snapshots[:5]:  # Try up to 5 snapshots
                    wayback_url = snapshot['wayback_url']

                    content = await self.extract_transcript_from_wayback(
                        wayback_url, actual_podcast_name, episode_title
                    )

                    if content:
                        success = self.save_transcript(
                            episode_id, actual_podcast_name, episode_title,
                            content, original_url, wayback_url
                        )
                        if success:
                            processed_count += 1
                            break

                    if success:
                        break

                if success:
                    break

            if not success:
                logger.warning(f"❌ No Wayback transcript found for: {episode_title}")

        logger.info(f"✅ {podcast_name}: {processed_count} Wayback transcripts processed")
        return processed_count

    async def run_wayback_processing(self):
        """Run Wayback processing for all failed sources"""
        logger.info("🚀 Starting Wayback Machine processing for failed sources")

        total_processed = 0

        for podcast_name in self.failed_sources:
            processed = await self.process_wayback_for_podcast(podcast_name)
            total_processed += processed

            # Break between podcasts to be respectful
            await asyncio.sleep(10)

        logger.info(f"\n🏆 Wayback processing complete: {total_processed} transcripts recovered")
        return total_processed

async def main():
    """Main execution"""
    processor = WaybackMachineProcessor()
    total = await processor.run_wayback_processing()

    logger.info(f"\n🎉 Wayback Machine processing complete! {total} transcripts recovered")

if __name__ == "__main__":
    asyncio.run(main())