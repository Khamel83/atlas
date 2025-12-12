#!/usr/bin/env python3
"""
HappyScribe Podcast Transcript Resolver

Fetches AI-generated transcripts from podcasts.happyscribe.com.

Supports podcasts like:
- The Knowledge Project with Shane Parrish
"""

import logging
import re
import time
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

from modules.podcasts.store import Episode

logger = logging.getLogger(__name__)

# Rate limiting
HAPPYSCRIBE_RATE_LIMIT_SECONDS = 3.0
_last_happyscribe_request = 0

# Mapping of our podcast slugs to HappyScribe podcast slugs
HAPPYSCRIBE_MAPPING = {
    'the-knowledge-project-with-shane-parrish': 'the-knowledge-project-with-shane-parrish',
}


class HappyScribeResolver:
    """Resolver that fetches transcripts from podcasts.happyscribe.com."""

    def __init__(self, user_agent: str = None, timeout: int = 30):
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        })
        self.base_url = "https://podcasts.happyscribe.com"

    def resolve(self, episode: Episode, podcast_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Find transcript on HappyScribe for this episode.

        Returns list of transcript sources with:
        - url: HappyScribe URL
        - confidence: 0.0-1.0 confidence score
        - resolver: 'happyscribe'
        - metadata: transcript content and info
        """
        sources = []
        global _last_happyscribe_request

        try:
            # Rate limiting
            elapsed = time.time() - _last_happyscribe_request
            if elapsed < HAPPYSCRIBE_RATE_LIMIT_SECONDS:
                time.sleep(HAPPYSCRIBE_RATE_LIMIT_SECONDS - elapsed)
            _last_happyscribe_request = time.time()

            # Get podcast slug from config or mapping
            podcast_slug = podcast_config.get('slug', '')
            config_section = podcast_config.get('config', {})
            happyscribe_slug = config_section.get('happyscribe_id')

            if not happyscribe_slug:
                happyscribe_slug = HAPPYSCRIBE_MAPPING.get(podcast_slug)

            if not happyscribe_slug:
                logger.debug(f"No HappyScribe mapping for podcast: {podcast_slug}")
                return sources

            # Find the episode on HappyScribe
            episode_url = self._find_episode_url(episode, happyscribe_slug)

            if episode_url:
                # Fetch the transcript
                transcript_content = self._fetch_transcript(episode_url)

                if transcript_content and len(transcript_content) > 500:
                    confidence = self._calculate_confidence(episode, transcript_content)

                    sources.append({
                        'url': episode_url,
                        'confidence': confidence,
                        'resolver': 'happyscribe',
                        'metadata': {
                            'content': transcript_content,
                            'content_length': len(transcript_content),
                            'source': 'happyscribe.com',
                            'accuracy': 'ai_generated',
                            'episode_title': episode.title,
                        }
                    })

                    logger.info(f"Found HappyScribe transcript for: {episode.title}")

        except Exception as e:
            logger.error(f"Error in HappyScribe resolver for {episode.title}: {e}")

        return sources

    def _find_episode_url(self, episode: Episode, happyscribe_slug: str) -> Optional[str]:
        """Find the HappyScribe URL for an episode by searching/matching."""

        # Get the podcast page
        podcast_url = f"{self.base_url}/{happyscribe_slug}"

        try:
            response = self.session.get(podcast_url, timeout=self.timeout)
            if response.status_code != 200:
                logger.debug(f"HappyScribe podcast page not found: {podcast_url}")
                return None

            soup = BeautifulSoup(response.content, 'html.parser')

            # Get title words for matching
            title_words = set(word.lower() for word in re.findall(r'\w+', episode.title) if len(word) > 3)

            # Find episode links
            episode_links = []
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                # Look for episode links
                if f'/{happyscribe_slug}/' in href and href != podcast_url:
                    link_text = link.get_text().lower()
                    episode_links.append((href, link_text))

            # Try to match by title word overlap
            best_match = None
            best_score = 0

            for href, link_text in episode_links:
                link_words = set(word.lower() for word in re.findall(r'\w+', link_text) if len(word) > 3)
                # Also check href
                href_words = set(word.lower() for word in re.findall(r'\w+', href) if len(word) > 3)
                combined_words = link_words | href_words

                overlap = len(title_words & combined_words)
                if overlap > best_score and overlap >= min(3, len(title_words) * 0.4):
                    best_score = overlap
                    best_match = href

            if best_match:
                if best_match.startswith('/'):
                    return self.base_url + best_match
                return best_match

        except Exception as e:
            logger.debug(f"Error searching HappyScribe: {e}")

        return None

    def _fetch_transcript(self, url: str) -> Optional[str]:
        """Fetch transcript content from a HappyScribe episode page."""
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # HappyScribe transcript selectors
            transcript_selectors = [
                '.transcript',
                '.transcript-content',
                '.episode-transcript',
                '[class*="transcript"]',
                '.content',
                'article',
                'main',
            ]

            for selector in transcript_selectors:
                elem = soup.select_one(selector)
                if elem:
                    text = elem.get_text(separator='\n', strip=True)
                    if len(text) > 500:
                        return self._clean_transcript(text)

        except Exception as e:
            logger.error(f"Error fetching HappyScribe transcript from {url}: {e}")

        return None

    def _clean_transcript(self, text: str) -> str:
        """Clean and normalize transcript text."""
        if not text:
            return ""

        # Remove timestamps like "00:00:00" or "0:00"
        text = re.sub(r'\d+:\d+(?::\d+)?\s*', '', text)

        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r' +', ' ', text)

        # Remove common UI elements
        patterns_to_remove = [
            r'Listen on.*?(?=\n|$)',
            r'Subscribe.*?(?=\n|$)',
            r'Share this.*?(?=\n|$)',
            r'Copyright.*?(?=\n|$)',
        ]

        for pattern in patterns_to_remove:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)

        return text.strip()

    def _calculate_confidence(self, episode: Episode, content: str) -> float:
        """Calculate confidence score for matched transcript."""
        confidence = 0.75  # Base confidence for HappyScribe (AI-generated)

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


def create_resolver() -> HappyScribeResolver:
    """Factory function to create resolver instance."""
    return HappyScribeResolver()
