#!/usr/bin/env python3
"""
Tapesearch.com Transcript Resolver

Fetches AI-generated transcripts from tapesearch.com.
Tapesearch provides timestamped transcripts for many podcasts.
"""

import logging
import re
import time
import requests
from typing import List, Dict, Any, Optional
from urllib.parse import quote
from bs4 import BeautifulSoup

from modules.podcasts.store import Episode

logger = logging.getLogger(__name__)

# Rate limiting
TAPESEARCH_RATE_LIMIT_SECONDS = 3.0
_last_tapesearch_request = 0

# Mapping of our podcast slugs to Tapesearch podcast IDs (Apple Podcast IDs)
TAPESEARCH_MAPPING = {
    'land-of-the-giants': '1465767420',
    'the-vergecast': '430333725',
    'decoder-with-nilay-patel': '1011668648',
    # Add more as discovered - format is our-slug: apple-podcast-id
}


class TapesearchResolver:
    """Resolver that fetches transcripts from tapesearch.com"""

    def __init__(self, user_agent: str = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)", timeout: int = 30):
        self.user_agent = user_agent
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        })
        self.base_url = "https://www.tapesearch.com"

    def resolve(self, episode: Episode, podcast_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Find transcript on Tapesearch for this episode.

        Returns list of transcript sources with:
        - url: Tapesearch URL
        - confidence: 0.0-1.0 confidence score
        - resolver: 'tapesearch'
        - metadata: transcript content and info
        """
        sources = []
        global _last_tapesearch_request

        try:
            # Rate limiting
            elapsed = time.time() - _last_tapesearch_request
            if elapsed < TAPESEARCH_RATE_LIMIT_SECONDS:
                time.sleep(TAPESEARCH_RATE_LIMIT_SECONDS - elapsed)
            _last_tapesearch_request = time.time()

            # Get podcast ID from config or mapping
            podcast_slug = podcast_config.get('slug', '')
            tapesearch_id = TAPESEARCH_MAPPING.get(podcast_slug)

            if not tapesearch_id:
                logger.debug(f"No Tapesearch mapping for podcast: {podcast_slug}")
                return sources

            # Search for the episode on the podcast page
            episode_url = self._find_episode_url(episode, podcast_slug, tapesearch_id)

            if episode_url:
                # Fetch the transcript
                transcript_content = self._fetch_transcript(episode_url)

                if transcript_content and len(transcript_content) > 500:
                    confidence = self._calculate_confidence(episode, transcript_content)

                    sources.append({
                        'url': episode_url,
                        'confidence': confidence,
                        'resolver': 'tapesearch',
                        'metadata': {
                            'content': transcript_content,
                            'content_length': len(transcript_content),
                            'source': 'tapesearch.com',
                            'accuracy': 'ai_generated',
                            'episode_title': episode.title,
                        }
                    })

                    logger.info(f"Found Tapesearch transcript for: {episode.title}")

        except Exception as e:
            logger.error(f"Error in Tapesearch resolver for {episode.title}: {e}")

        return sources

    def _find_episode_url(self, episode: Episode, podcast_slug: str, tapesearch_id: str) -> Optional[str]:
        """Find the Tapesearch URL for an episode"""

        # Get the podcast page
        podcast_url = f"{self.base_url}/podcast/{podcast_slug}/{tapesearch_id}"

        try:
            response = self.session.get(podcast_url, timeout=self.timeout)
            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.content, 'html.parser')

            # Get title words for matching
            title_words = set(word.lower() for word in re.findall(r'\w+', episode.title) if len(word) > 3)

            # Find episode links
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                if '/episode/' in href:
                    link_text = link.get_text().lower()
                    link_words = set(word.lower() for word in re.findall(r'\w+', link_text) if len(word) > 3)

                    # Also check href for words
                    href_words = set(word.lower() for word in re.findall(r'\w+', href) if len(word) > 3)
                    combined_words = link_words | href_words

                    overlap = len(title_words & combined_words)
                    if overlap >= min(3, len(title_words) * 0.4):
                        if href.startswith('/'):
                            return self.base_url + href
                        return href

        except Exception as e:
            logger.debug(f"Error searching Tapesearch: {e}")

        return None

    def _fetch_transcript(self, url: str) -> Optional[str]:
        """Fetch transcript content from a Tapesearch episode page"""
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Find transcript table
            transcript_parts = []

            # Look for transcript table rows
            for row in soup.find_all('tr'):
                cells = row.find_all('td')
                if len(cells) >= 2:
                    # Second cell typically has the transcript text
                    text_cell = cells[1]
                    text = text_cell.get_text(strip=True)
                    if text and len(text) > 5:
                        transcript_parts.append(text)

            if transcript_parts:
                return '\n\n'.join(transcript_parts)

            # Fallback: look for any transcript container
            for selector in ['[class*="transcript"]', '.mantine-Table-tbody', 'table']:
                elem = soup.select_one(selector)
                if elem:
                    text = elem.get_text(separator='\n', strip=True)
                    if len(text) > 500:
                        return self._clean_transcript(text)

        except Exception as e:
            logger.error(f"Error fetching Tapesearch transcript from {url}: {e}")

        return None

    def _clean_transcript(self, text: str) -> str:
        """Clean and normalize transcript text"""
        if not text:
            return ""

        # Remove timestamps like "0:00.0"
        text = re.sub(r'\d+:\d+\.\d+\s*', '', text)

        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r' +', ' ', text)

        return text.strip()

    def _calculate_confidence(self, episode: Episode, content: str) -> float:
        """Calculate confidence score for matched transcript"""
        confidence = 0.75  # Base confidence for Tapesearch

        # Check title word overlap
        if episode.title:
            title_words = set(word.lower() for word in re.findall(r'\w+', episode.title) if len(word) > 3)
            content_lower = content.lower()

            matches = sum(1 for word in title_words if word in content_lower)
            if matches >= len(title_words) * 0.5:
                confidence += 0.1

        # Length bonus
        if len(content) > 10000:
            confidence += 0.1
        elif len(content) > 5000:
            confidence += 0.05

        return min(confidence, 0.95)


def create_resolver() -> TapesearchResolver:
    """Factory function to create resolver instance."""
    return TapesearchResolver()
