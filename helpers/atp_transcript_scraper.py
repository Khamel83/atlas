#!/usr/bin/env python3
"""
ATP Transcript Scraper for catatp.fm

Scrapes existing professional transcripts instead of re-transcribing audio.
This is the smart approach - leverage community work.
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from pathlib import Path
from typing import Dict, List, Optional
import time
from urllib.parse import urljoin
import logging

logger = logging.getLogger(__name__)

class ATPTranscriptScraper:
    """Scrape ATP transcripts from catatp.fm"""

    def __init__(self, base_url: str = "https://catatp.fm"):
        self.base_url = base_url
        self.episodes_url = f"{base_url}/episodes/"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

    def get_episode_list(self) -> List[Dict]:
        """Get list of episodes from catatp.fm/episodes/"""
        try:
            response = self.session.get(self.episodes_url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            episodes = []

            # Find episode links - catatp.fm uses pattern like /2025/08/14/atp652.mp3/
            episode_links = soup.find_all('a', href=re.compile(r'/\d{4}/\d{2}/\d{2}/atp\d+\.mp3/'))

            for link in episode_links:
                href = link.get('href')
                if href:
                    episode_url = urljoin(self.base_url, href)

                    # Extract episode number from URL pattern atp652.mp3
                    episode_match = re.search(r'/atp(\d+)\.mp3/', href)
                    if episode_match:
                        episode_num = int(episode_match.group(1))

                        # Get episode title from link text - format "652: Title"
                        title = link.get_text(strip=True)

                        episodes.append({
                            "number": episode_num,
                            "title": title,
                            "url": episode_url
                        })

            # Sort by episode number (descending for recent first)
            episodes.sort(key=lambda x: x["number"], reverse=True)
            return episodes

        except Exception as e:
            logger.error(f"Failed to get episode list: {e}")
            return []

    def scrape_episode_transcript(self, episode_url: str) -> Optional[Dict]:
        """Scrape transcript from individual episode page"""
        try:
            response = self.session.get(episode_url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Find transcript content - adjust selector based on actual site structure
            transcript_content = None

            # Try different common selectors for transcript content
            for selector in [
                '.post',  # catatp.fm uses this
                '.transcript',
                '#transcript',
                '.episode-transcript',
                '.content .transcript',
                'div[class*="transcript"]',
                '.episode-content'
            ]:
                transcript_elem = soup.select_one(selector)
                if transcript_elem:
                    transcript_content = transcript_elem.get_text(separator='\n', strip=True)
                    break

            if not transcript_content:
                # Fallback: get all text content from main content area
                main_content = soup.find('main') or soup.find('article') or soup.find('.content')
                if main_content:
                    transcript_content = main_content.get_text(separator='\n', strip=True)

            if transcript_content and len(transcript_content) > 1000:  # Minimum length check
                # Extract episode metadata
                title_elem = soup.find('h1') or soup.find('.episode-title')
                title = title_elem.get_text(strip=True) if title_elem else "Unknown Episode"

                # Extract episode number from URL or title
                episode_num = None
                episode_match = re.search(r'(?:episode|atp)\s*#?(\d+)', title.lower())
                if not episode_match:
                    episode_match = re.search(r'/episodes/(\d+)', episode_url)
                if episode_match:
                    episode_num = int(episode_match.group(1))

                return {
                    "episode_number": episode_num,
                    "title": title,
                    "url": episode_url,
                    "transcript": transcript_content,
                    "word_count": len(transcript_content.split()),
                    "scraped_from": "catatp.fm"
                }

            logger.warning(f"No substantial transcript found for {episode_url}")
            return None

        except Exception as e:
            logger.error(f"Failed to scrape transcript from {episode_url}: {e}")
            return None

    def match_to_atlas_episodes(self, atlas_podcasts_dir: Path) -> Dict[int, str]:
        """Match scraped episodes to existing Atlas episode metadata"""
        episode_mapping = {}

        # Find all ATP metadata files
        for metadata_file in atlas_podcasts_dir.glob("*_rss_entry.json"):
            try:
                with open(metadata_file) as f:
                    data = json.load(f)

                if "atp.fm" in data.get("source", ""):
                    # Extract episode number from title
                    title = data.get("raw_data", {}).get("title", "")
                    episode_match = re.search(r'(\d+):', title)  # ATP format: "542: Title"

                    if episode_match:
                        episode_num = int(episode_match.group(1))
                        episode_id = metadata_file.stem.replace("_rss_entry", "")
                        episode_mapping[episode_num] = episode_id

            except Exception as e:
                logger.warning(f"Failed to process {metadata_file}: {e}")

        return episode_mapping

    def scrape_and_save_transcripts(self, atlas_root: Path, min_episode: int = 400) -> Dict:
        """Scrape transcripts and save to Atlas format"""
        results = {
            "episodes_found": 0,
            "transcripts_scraped": 0,
            "transcripts_saved": 0,
            "errors": []
        }

        # Get episode list from catatp.fm
        episodes = self.get_episode_list()
        results["episodes_found"] = len(episodes)

        if not episodes:
            logger.error("No episodes found on catatp.fm")
            return results

        # Filter to episodes >= min_episode (recent episodes)
        recent_episodes = [ep for ep in episodes if ep["number"] >= min_episode]

        # Match to Atlas episodes
        atlas_podcasts_dir = atlas_root / "output" / "podcasts"
        episode_mapping = self.match_to_atlas_episodes(atlas_podcasts_dir)

        logger.info(f"Found {len(recent_episodes)} recent episodes, {len(episode_mapping)} Atlas episodes")

        # Scrape transcripts for episodes we have
        for episode in recent_episodes:
            episode_num = episode["number"]

            if episode_num not in episode_mapping:
                continue  # We don't have this episode in Atlas

            atlas_id = episode_mapping[episode_num]
            transcript_file = atlas_podcasts_dir / "markdown" / f"{atlas_id}.md"

            # Skip if we already have a transcript
            if transcript_file.exists() and transcript_file.stat().st_size > 5000:
                logger.info(f"Transcript already exists for Episode {episode_num}")
                continue

            logger.info(f"Scraping Episode {episode_num}: {episode['title']}")

            # Add delay to be respectful
            time.sleep(2)

            try:
                transcript_data = self.scrape_episode_transcript(episode["url"])
                if transcript_data:
                    results["transcripts_scraped"] += 1

                    # Save to Atlas markdown format
                    markdown_content = self._format_transcript_markdown(transcript_data)

                    # Ensure directory exists
                    transcript_file.parent.mkdir(parents=True, exist_ok=True)

                    with open(transcript_file, 'w', encoding='utf-8') as f:
                        f.write(markdown_content)

                    results["transcripts_saved"] += 1
                    logger.info(f"Saved transcript for Episode {episode_num} ({transcript_data['word_count']} words)")

            except Exception as e:
                error_msg = f"Error processing Episode {episode_num}: {e}"
                logger.error(error_msg)
                results["errors"].append(error_msg)

        return results

    def _format_transcript_markdown(self, transcript_data: Dict) -> str:
        """Format transcript data as markdown for Atlas"""
        return f"""---
title: "ATP {transcript_data.get('episode_number', 'Unknown')}: {transcript_data.get('title', 'Unknown')}"
type: podcast_transcript
source: catatp.fm
episode_number: {transcript_data.get('episode_number', 'Unknown')}
word_count: {transcript_data.get('word_count', 0)}
scraped_at: {time.strftime('%Y-%m-%d %H:%M:%S')}
original_url: {transcript_data.get('url', '')}
---

# {transcript_data.get('title', 'ATP Episode')}

{transcript_data.get('transcript', '')}
"""

    def get_transcript_from_url(self, url: str) -> Dict[str, any]:
        """Get transcript from a specific URL (for integration with main workflow)"""
        try:
            transcript_data = self.scrape_episode_transcript(url)
            if transcript_data:
                return {
                    "success": True,
                    "transcript": transcript_data["transcript"],
                    "metadata": {
                        "episode_number": transcript_data.get("episode_number"),
                        "title": transcript_data.get("title"),
                        "word_count": transcript_data.get("word_count"),
                        "source": "catatp.fm"
                    }
                }
            else:
                return {
                    "success": False,
                    "error": "No transcript found on ATP page"
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"ATP transcript scraping failed: {str(e)}"
            }


def main():
    """Test the ATP transcript scraper"""
    scraper = ATPTranscriptScraper()
    atlas_root = Path("/home/ubuntu/dev/atlas")

    print("🔍 Testing ATP transcript scraper...")

    # Test getting episode list
    episodes = scraper.get_episode_list()
    print(f"Found {len(episodes)} episodes on catatp.fm")

    if episodes:
        print(f"Latest episode: #{episodes[0]['number']} - {episodes[0]['title']}")

        # Test scraping one episode
        if len(episodes) > 0:
            test_episode = episodes[0]  # Latest episode (first in reverse sorted list)
            print(f"\n🔍 Testing transcript scrape for Episode {test_episode['number']}")

            transcript = scraper.scrape_episode_transcript(test_episode['url'])
            if transcript:
                print(f"✅ Successfully scraped {transcript['word_count']} words")
                print(f"Title: {transcript['title']}")
            else:
                print("❌ Failed to scrape transcript")

    print("\n🔍 Checking Atlas episode mapping...")
    episode_mapping = scraper.match_to_atlas_episodes(atlas_root / "output" / "podcasts")
    print(f"Found {len(episode_mapping)} ATP episodes in Atlas")

    if episode_mapping:
        recent_episodes = {k: v for k, v in episode_mapping.items() if k >= 500}
        print(f"Recent episodes (500+): {len(recent_episodes)}")
        print(f"Episode range: {min(episode_mapping.keys())}-{max(episode_mapping.keys())}")


if __name__ == "__main__":
    main()