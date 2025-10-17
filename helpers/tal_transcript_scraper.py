#!/usr/bin/env python3
"""
This American Life Transcript Scraper

Scrapes transcripts from thisamericanlife.org for episodes with available transcripts.
This leverages professional transcripts instead of re-transcribing audio.
"""

import requests
from bs4 import BeautifulSoup
import json
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse
import logging

logger = logging.getLogger(__name__)

class TALTranscriptScraper:
    """Scraper for This American Life transcripts from thisamericanlife.org"""

    def __init__(self, base_url: str = "https://www.thisamericanlife.org"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

    def get_episode_list(self, limit: int = 50) -> List[Dict]:
        """Get list of recent episodes from This American Life"""
        try:
            archive_url = f"{self.base_url}/archive"
            response = self.session.get(archive_url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            episodes = []

            # Find episode links - TAL uses various patterns for episode listings
            episode_links = soup.find_all('a', href=re.compile(r'/\d+/'))

            for link in episode_links[:limit]:
                href = link.get('href')
                if href and '/episode/' not in href:  # Skip non-episode pages
                    continue

                if href:
                    episode_url = urljoin(self.base_url, href)

                    # Extract episode number from URL pattern /785/title
                    episode_match = re.search(r'/(\d+)/', href)
                    if episode_match:
                        episode_num = int(episode_match.group(1))

                        # Get episode title from link text
                        title = link.get_text(strip=True)

                        episodes.append({
                            "number": episode_num,
                            "title": title,
                            "url": episode_url
                        })

            # Sort by episode number (descending for recent first)
            episodes = list({ep['number']: ep for ep in episodes}.values())  # Deduplicate
            episodes.sort(key=lambda x: x["number"], reverse=True)
            return episodes[:limit]

        except Exception as e:
            logger.error(f"Failed to get TAL episode list: {e}")
            return []

    def scrape_episode_transcript(self, episode_url: str) -> Optional[Dict]:
        """Scrape transcript from individual TAL episode page"""
        try:
            response = self.session.get(episode_url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Find transcript content - TAL has various structures
            transcript_content = None

            # Try different selectors for transcript content
            transcript_selectors = [
                '.transcript',
                '#transcript',
                '.episode-transcript',
                '.story-transcript',
                '[class*="transcript"]',
                '.act-transcript',
                '.field-name-field-transcript',
                '.field-type-text-long'
            ]

            for selector in transcript_selectors:
                transcript_elem = soup.select_one(selector)
                if transcript_elem:
                    transcript_content = transcript_elem.get_text(separator='\n', strip=True)
                    break

            # Fallback: look for transcript links or alternative structures
            if not transcript_content:
                # Look for "Read the Transcript" links
                transcript_links = soup.find_all('a', string=re.compile(r'[Tt]ranscript', re.IGNORECASE))
                for transcript_link in transcript_links:
                    transcript_href = transcript_link.get('href')
                    if transcript_href:
                        transcript_url = urljoin(episode_url, transcript_href)
                        transcript_content = self._scrape_transcript_page(transcript_url)
                        if transcript_content:
                            break

            # Fallback: check if transcript is embedded in main content
            if not transcript_content:
                main_content = soup.find('main') or soup.find('article') or soup.find('.content')
                if main_content:
                    # Look for large text blocks that might be transcripts
                    text_blocks = main_content.find_all(['p', 'div'], string=re.compile(r'.{500,}'))
                    for block in text_blocks:
                        text = block.get_text(strip=True)
                        if len(text) > 1000 and ('ira glass' in text.lower() or 'act one' in text.lower()):
                            transcript_content = text
                            break

            if transcript_content and len(transcript_content) > 500:  # Minimum length check
                # Extract episode metadata
                title_elem = soup.find('h1') or soup.find('.episode-title') or soup.find('.page-title')
                title = title_elem.get_text(strip=True) if title_elem else "Unknown Episode"

                # Extract episode number from URL or title
                episode_num = None
                episode_match = re.search(r'(\d+)', episode_url)
                if episode_match:
                    episode_num = int(episode_match.group(1))

                # Clean up transcript content
                transcript_content = self._clean_transcript_content(transcript_content)

                return {
                    "episode_number": episode_num,
                    "title": title,
                    "url": episode_url,
                    "transcript": transcript_content,
                    "word_count": len(transcript_content.split()),
                    "scraped_from": "thisamericanlife.org"
                }

            logger.warning(f"No substantial transcript found for {episode_url}")
            return None

        except Exception as e:
            logger.error(f"Failed to scrape TAL transcript from {episode_url}: {e}")
            return None

    def _scrape_transcript_page(self, transcript_url: str) -> Optional[str]:
        """Scrape transcript from a dedicated transcript page"""
        try:
            response = self.session.get(transcript_url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Get main content from transcript page
            main_content = soup.find('main') or soup.find('article') or soup.find('.content')
            if main_content:
                transcript_text = main_content.get_text(separator='\n', strip=True)
                if len(transcript_text) > 500:
                    return transcript_text

            return None

        except Exception as e:
            logger.error(f"Failed to scrape transcript page {transcript_url}: {e}")
            return None

    def _clean_transcript_content(self, content: str) -> str:
        """Clean and normalize transcript content"""
        # Remove excessive whitespace
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
        content = re.sub(r'[ \t]+', ' ', content)

        # Remove common website navigation text
        content = re.sub(r'Skip to main content.*?Menu', '', content, flags=re.IGNORECASE)
        content = re.sub(r'Search.*?Submit', '', content, flags=re.IGNORECASE)

        return content.strip()

    def get_transcript_from_url(self, url: str) -> Dict[str, Any]:
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
                        "source": "thisamericanlife.org"
                    }
                }
            else:
                return {
                    "success": False,
                    "error": "No transcript found on This American Life page"
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"TAL transcript scraping failed: {str(e)}"
            }

    def search_episode_by_title(self, episode_title: str) -> Optional[Dict]:
        """Search for an episode by title similarity"""
        try:
            episodes = self.get_episode_list()

            # Simple title matching - look for episodes with similar titles
            episode_title_clean = re.sub(r'[^\w\s]', '', episode_title.lower())
            episode_words = set(episode_title_clean.split())

            best_match = None
            best_score = 0

            for episode in episodes:
                episode_clean = re.sub(r'[^\w\s]', '', episode['title'].lower())
                episode_ep_words = set(episode_clean.split())

                # Calculate word overlap score
                if episode_words and episode_ep_words:
                    intersection = episode_words.intersection(episode_ep_words)
                    union = episode_words.union(episode_ep_words)
                    score = len(intersection) / len(union) if union else 0

                    if score > best_score and score > 0.3:  # Minimum similarity threshold
                        best_score = score
                        best_match = episode

            return best_match

        except Exception as e:
            logger.error(f"Failed to search TAL episodes: {e}")
            return None

def main():
    """Test the TAL transcript scraper"""
    scraper = TALTranscriptScraper()

    print("🎙️ Testing This American Life transcript scraper...")

    # Test getting episode list
    episodes = scraper.get_episode_list(limit=10)
    print(f"Found {len(episodes)} recent episodes")

    if episodes:
        print(f"Latest episode: #{episodes[0]['number']} - {episodes[0]['title']}")

        # Test scraping one episode
        test_episode = episodes[0]
        print(f"\n🔍 Testing transcript scrape for Episode {test_episode['number']}")

        transcript = scraper.scrape_episode_transcript(test_episode['url'])
        if transcript:
            print(f"✅ Successfully scraped {transcript['word_count']} words")
            print(f"Title: {transcript['title']}")
            print(f"Preview: {transcript['transcript'][:200]}...")
        else:
            print("❌ Failed to scrape transcript")

    # Test search functionality
    print(f"\n🔍 Testing episode search...")
    search_result = scraper.search_episode_by_title("Serial")
    if search_result:
        print(f"Found episode: {search_result['title']}")
    else:
        print("No episodes found matching search")

if __name__ == "__main__":
    main()