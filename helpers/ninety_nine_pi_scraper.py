#!/usr/bin/env python3
"""
99% Invisible Transcript Scraper

Scrapes transcripts from 99percentinvisible.org for episodes with available transcripts.
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

class NinetyNinePITranscriptScraper:
    """Scraper for 99% Invisible transcripts from 99percentinvisible.org"""

    def __init__(self, base_url: str = "https://99percentinvisible.org"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

    def get_episode_list(self, limit: int = 50) -> List[Dict]:
        """Get list of recent episodes from 99% Invisible"""
        try:
            # Try episodes page first
            episodes_url = f"{self.base_url}/episodes/"
            response = self.session.get(episodes_url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            episodes = []

            # Find episode links - 99PI uses various patterns
            episode_links = soup.find_all('a', href=re.compile(r'/episode/'))

            for link in episode_links[:limit]:
                href = link.get('href')
                if href:
                    episode_url = urljoin(self.base_url, href)

                    # Extract episode number from title or URL
                    title = link.get_text(strip=True)
                    episode_num = None

                    # Try to extract episode number from title (e.g., "501- Title")
                    episode_match = re.search(r'(\d+)[\s\-–]', title)
                    if not episode_match:
                        # Try extracting from URL
                        episode_match = re.search(r'/episode/(\d+)', href)

                    if episode_match:
                        episode_num = int(episode_match.group(1))

                    if episode_num:  # Only include episodes with numbers
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
            logger.error(f"Failed to get 99PI episode list: {e}")
            return []

    def scrape_episode_transcript(self, episode_url: str) -> Optional[Dict]:
        """Scrape transcript from individual 99PI episode page"""
        try:
            response = self.session.get(episode_url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Find transcript content - 99PI has various structures
            transcript_content = None

            # Try different selectors for transcript content
            transcript_selectors = [
                '.transcript',
                '#transcript',
                '.episode-transcript',
                '.field-name-field-transcript',
                '.field-type-text-long',
                '[class*="transcript"]',
                '.story-transcript',
                '.entry-content .transcript',
                '.post-content .transcript'
            ]

            for selector in transcript_selectors:
                transcript_elem = soup.select_one(selector)
                if transcript_elem:
                    transcript_content = transcript_elem.get_text(separator='\n', strip=True)
                    if len(transcript_content) > 500:  # Only accept substantial content
                        break
                    else:
                        transcript_content = None

            # Fallback: look for transcript links or sections
            if not transcript_content:
                # Look for "Transcript" sections or links
                transcript_headers = soup.find_all(['h2', 'h3', 'h4'], string=re.compile(r'[Tt]ranscript', re.IGNORECASE))
                for header in transcript_headers:
                    # Get the content after the transcript header
                    content_after = []
                    for sibling in header.find_next_siblings():
                        if sibling.name in ['h1', 'h2', 'h3'] and 'transcript' not in sibling.get_text().lower():
                            break  # Stop at next major heading
                        content_after.append(sibling.get_text())

                    transcript_candidate = '\n'.join(content_after)
                    if len(transcript_candidate) > 1000:
                        transcript_content = transcript_candidate
                        break

            # Another fallback: check main content for large text blocks
            if not transcript_content:
                main_content = soup.find('main') or soup.find('article') or soup.find('.entry-content') or soup.find('.post-content')
                if main_content:
                    # Look for large paragraphs that might contain transcript
                    all_text = main_content.get_text(separator='\n', strip=True)
                    if len(all_text) > 2000:
                        # Check if it contains transcript-like content
                        transcript_indicators = ['roman mars', 'narrator', 'speaker', 'interviewer', 'interviewee']
                        if any(indicator in all_text.lower() for indicator in transcript_indicators):
                            transcript_content = all_text

            if transcript_content and len(transcript_content) > 500:  # Minimum length check
                # Extract episode metadata
                title_elem = soup.find('h1') or soup.find('.episode-title') or soup.find('.entry-title') or soup.find('.post-title')
                title = title_elem.get_text(strip=True) if title_elem else "Unknown Episode"

                # Extract episode number from title or URL
                episode_num = None
                episode_match = re.search(r'(\d+)', title) or re.search(r'/episode/(\d+)', episode_url)
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
                    "scraped_from": "99percentinvisible.org"
                }

            logger.warning(f"No substantial transcript found for {episode_url}")
            return None

        except Exception as e:
            logger.error(f"Failed to scrape 99PI transcript from {episode_url}: {e}")
            return None

    def _clean_transcript_content(self, content: str) -> str:
        """Clean and normalize transcript content"""
        # Remove excessive whitespace
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
        content = re.sub(r'[ \t]+', ' ', content)

        # Remove common website navigation text
        content = re.sub(r'Skip to content.*?Menu', '', content, flags=re.IGNORECASE)
        content = re.sub(r'Search.*?Submit', '', content, flags=re.IGNORECASE)
        content = re.sub(r'Subscribe.*?Apple Podcasts', '', content, flags=re.IGNORECASE)

        # Remove social media and sharing text
        content = re.sub(r'Share this.*?Facebook.*?Twitter', '', content, flags=re.IGNORECASE)
        content = re.sub(r'Follow.*?@99.*?invisible', '', content, flags=re.IGNORECASE)

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
                        "source": "99percentinvisible.org"
                    }
                }
            else:
                return {
                    "success": False,
                    "error": "No transcript found on 99% Invisible page"
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"99PI transcript scraping failed: {str(e)}"
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
            logger.error(f"Failed to search 99PI episodes: {e}")
            return None

def main():
    """Test the 99% Invisible transcript scraper"""
    scraper = NinetyNinePITranscriptScraper()

    print("🎙️ Testing 99% Invisible transcript scraper...")

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
    search_result = scraper.search_episode_by_title("design")
    if search_result:
        print(f"Found episode: {search_result['title']}")
    else:
        print("No episodes found matching search")

if __name__ == "__main__":
    main()