#!/usr/bin/env python3
"""
Automated Transcript Fetchers

Based on the discovery pattern, build fetchers for the main transcript sources:
1. HappyScribe (happyscribe.com/public/[podcast-name])
2. Official podcast websites
3. Podscribe (app.podscribe.com)
4. Other services (Tapesearch, Metacast, etc.)
"""

import requests
import re
from urllib.parse import quote_plus, urljoin
from bs4 import BeautifulSoup
import logging
from dataclasses import dataclass
from typing import Optional, Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TranscriptResult:
    """Result from transcript fetching"""
    podcast_name: str
    episode_title: str
    source: str
    found: bool
    transcript_text: Optional[str] = None
    transcript_url: Optional[str] = None
    word_count: Optional[int] = None
    error: Optional[str] = None

class HappyScribeFetcher:
    """Fetch transcripts from HappyScribe"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; TranscriptFetcher/1.0)'
        })
        self.base_url = "https://www.happyscribe.com/public"

    def get_podcast_url(self, podcast_name: str) -> str:
        """Convert podcast name to HappyScribe URL format"""
        # Convert to lowercase, replace spaces with hyphens
        url_name = podcast_name.lower().replace(' ', '-').replace(':', '').replace('|', '').replace('"', '')
        return f"{self.base_url}/{url_name}"

    def fetch_episode_transcript(self, podcast_name: str, episode_title: str) -> TranscriptResult:
        """Fetch transcript for specific episode"""
        try:
            podcast_url = self.get_podcast_url(podcast_name)
            logger.info(f"Checking HappyScribe: {podcast_url}")

            response = self.session.get(podcast_url, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for episode links that match the title
            episode_links = soup.find_all('a', href=True)
            best_match = None
            best_score = 0

            for link in episode_links:
                link_text = link.get_text().strip()
                # Simple similarity check
                if episode_title.lower() in link_text.lower() or link_text.lower() in episode_title.lower():
                    score = len(link_text)
                    if score > best_score:
                        best_match = link
                        best_score = score

            if best_match:
                episode_url = urljoin(podcast_url, best_match.get('href'))
                return self._fetch_transcript_from_episode_page(podcast_name, episode_title, episode_url)

            return TranscriptResult(
                podcast_name=podcast_name,
                episode_title=episode_title,
                source="happyscribe",
                found=False,
                error="Episode not found on HappyScribe"
            )

        except Exception as e:
            return TranscriptResult(
                podcast_name=podcast_name,
                episode_title=episode_title,
                source="happyscribe",
                found=False,
                error=str(e)
            )

    def _fetch_transcript_from_episode_page(self, podcast_name: str, episode_title: str, episode_url: str) -> TranscriptResult:
        """Fetch transcript from episode page"""
        try:
            response = self.session.get(episode_url, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for transcript content (common patterns)
            transcript_selectors = [
                '.transcript-content',
                '.transcript-text',
                '.episode-transcript',
                '[data-transcript]',
                'div.transcript',
                'section.transcript'
            ]

            transcript_text = None
            for selector in transcript_selectors:
                elements = soup.select(selector)
                if elements:
                    transcript_text = '\n'.join([el.get_text().strip() for el in elements])
                    break

            # Fallback: look for large text blocks
            if not transcript_text:
                text_blocks = soup.find_all(['div', 'section', 'article'])
                for block in text_blocks:
                    text = block.get_text().strip()
                    if len(text) > 5000:  # Likely transcript
                        transcript_text = text
                        break

            if transcript_text and len(transcript_text) > 1000:
                return TranscriptResult(
                    podcast_name=podcast_name,
                    episode_title=episode_title,
                    source="happyscribe",
                    found=True,
                    transcript_text=transcript_text,
                    transcript_url=episode_url,
                    word_count=len(transcript_text.split())
                )

            return TranscriptResult(
                podcast_name=podcast_name,
                episode_title=episode_title,
                source="happyscribe",
                found=False,
                error="No substantial transcript found on episode page"
            )

        except Exception as e:
            return TranscriptResult(
                podcast_name=podcast_name,
                episode_title=episode_title,
                source="happyscribe",
                found=False,
                error=f"Error fetching episode page: {str(e)}"
            )

class PodscribeFetcher:
    """Fetch transcripts from Podscribe"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; TranscriptFetcher/1.0)'
        })
        self.base_url = "https://app.podscribe.com"

    def fetch_episode_transcript(self, podcast_name: str, episode_title: str) -> TranscriptResult:
        """Fetch transcript from Podscribe"""
        try:
            # Search for the podcast on Podscribe
            search_url = f"{self.base_url}/search?q={quote_plus(podcast_name)}"

            response = self.session.get(search_url, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for podcast links
            podcast_links = soup.find_all('a', href=re.compile(r'/series/'))

            if podcast_links:
                # Take first podcast match
                series_url = urljoin(self.base_url, podcast_links[0].get('href'))
                return self._search_series_for_episode(podcast_name, episode_title, series_url)

            return TranscriptResult(
                podcast_name=podcast_name,
                episode_title=episode_title,
                source="podscribe",
                found=False,
                error="Podcast not found on Podscribe"
            )

        except Exception as e:
            return TranscriptResult(
                podcast_name=podcast_name,
                episode_title=episode_title,
                source="podscribe",
                found=False,
                error=str(e)
            )

    def _search_series_for_episode(self, podcast_name: str, episode_title: str, series_url: str) -> TranscriptResult:
        """Search series page for specific episode"""
        try:
            response = self.session.get(series_url, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for episode listings
            episode_links = soup.find_all('a', href=re.compile(r'/episode/'))

            for link in episode_links:
                link_text = link.get_text().strip()
                if episode_title.lower() in link_text.lower():
                    episode_url = urljoin(series_url, link.get('href'))
                    return self._fetch_transcript_from_episode(podcast_name, episode_title, episode_url)

            return TranscriptResult(
                podcast_name=podcast_name,
                episode_title=episode_title,
                source="podscribe",
                found=False,
                error="Episode not found in series"
            )

        except Exception as e:
            return TranscriptResult(
                podcast_name=podcast_name,
                episode_title=episode_title,
                source="podscribe",
                found=False,
                error=f"Error searching series: {str(e)}"
            )

    def _fetch_transcript_from_episode(self, podcast_name: str, episode_title: str, episode_url: str) -> TranscriptResult:
        """Fetch transcript from Podscribe episode page"""
        try:
            response = self.session.get(episode_url, timeout=15)
            response.raise_for_status()

            # Podscribe might return JSON or HTML
            if 'application/json' in response.headers.get('content-type', ''):
                data = response.json()
                transcript = data.get('transcript', '')
                if transcript and len(transcript) > 1000:
                    return TranscriptResult(
                        podcast_name=podcast_name,
                        episode_title=episode_title,
                        source="podscribe",
                        found=True,
                        transcript_text=transcript,
                        transcript_url=episode_url,
                        word_count=len(transcript.split())
                    )
            else:
                soup = BeautifulSoup(response.content, 'html.parser')

                # Look for transcript content
                transcript_elem = soup.find(['div', 'section'], class_=re.compile(r'transcript|content'))
                if transcript_elem:
                    transcript_text = transcript_elem.get_text().strip()
                    if len(transcript_text) > 1000:
                        return TranscriptResult(
                            podcast_name=podcast_name,
                            episode_title=episode_title,
                            source="podscribe",
                            found=True,
                            transcript_text=transcript_text,
                            transcript_url=episode_url,
                            word_count=len(transcript_text.split())
                        )

            return TranscriptResult(
                podcast_name=podcast_name,
                episode_title=episode_title,
                source="podscribe",
                found=False,
                error="No transcript content found"
            )

        except Exception as e:
            return TranscriptResult(
                podcast_name=podcast_name,
                episode_title=episode_title,
                source="podscribe",
                found=False,
                error=f"Error fetching transcript: {str(e)}"
            )

class TranscriptFetchManager:
    """Manages multiple transcript fetchers with fallback hierarchy"""

    def __init__(self):
        self.fetchers = [
            HappyScribeFetcher(),
            PodscribeFetcher()
        ]

    def fetch_episode_transcript(self, podcast_name: str, episode_title: str) -> List[TranscriptResult]:
        """Try all fetchers for an episode"""
        results = []

        for fetcher in self.fetchers:
            try:
                result = fetcher.fetch_episode_transcript(podcast_name, episode_title)
                results.append(result)

                # If we found a good transcript, stop trying
                if result.found and result.word_count and result.word_count > 500:
                    logger.info(f"Found transcript from {result.source}: {result.word_count} words")
                    break

            except Exception as e:
                logger.error(f"Error with {fetcher.__class__.__name__}: {str(e)}")

        return results

    def get_best_result(self, results: List[TranscriptResult]) -> Optional[TranscriptResult]:
        """Get the best transcript result"""
        found_results = [r for r in results if r.found]

        if not found_results:
            return None

        # Sort by word count (longer is better for transcripts)
        found_results.sort(key=lambda x: x.word_count or 0, reverse=True)
        return found_results[0]

def test_transcript_fetching():
    """Test transcript fetching with known good examples"""
    manager = TranscriptFetchManager()

    test_cases = [
        ("Hard Fork", "California Regulates A.I. Companions + OpenAI Investigates I"),
        ("This American Life", "This Is the Case of Henry Dee"),
        ("Acquired", "Google: The AI Company")
    ]

    for podcast_name, episode_title in test_cases:
        logger.info(f"\n=== Testing: {podcast_name} - {episode_title[:30]}... ===")

        results = manager.fetch_episode_transcript(podcast_name, episode_title)
        best_result = manager.get_best_result(results)

        if best_result:
            print(f"✓ Found transcript from {best_result.source}")
            print(f"  Word count: {best_result.word_count}")
            print(f"  URL: {best_result.transcript_url}")
            print(f"  Preview: {best_result.transcript_text[:200]}...")
        else:
            print("✗ No transcript found")
            for result in results:
                print(f"  {result.source}: {result.error}")

if __name__ == "__main__":
    test_transcript_fetching()