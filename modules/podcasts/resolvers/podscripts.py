#!/usr/bin/env python3
"""
Podscripts.co Transcript Resolver

Fetches free AI-generated transcripts from podscripts.co.
This is a third-party service that provides transcripts for many popular podcasts.

Uses requests + BeautifulSoup for simple pages, falls back to headless browser
for JS-heavy pages when needed.
"""

import logging
import os
import re
import time
import requests
from typing import List, Dict, Any, Optional
from urllib.parse import quote, urljoin
from bs4 import BeautifulSoup

from modules.podcasts.store import Episode

logger = logging.getLogger(__name__)

# Rate limiting - Podscripts blocks IPs that request too fast
# Can be overridden via environment variable
PODSCRIPTS_RATE_LIMIT_SECONDS = float(os.environ.get('PODSCRIPTS_RATE_LIMIT_SECONDS', '4.0'))
_last_podscripts_request = 0

# Mapping of our podcast slugs to Podscripts podcast identifiers
PODSCRIPTS_MAPPING = {
    # Tech/Business
    'pivot': 'pivot',
    'all-in-podcast': 'all-in-with-chamath-jason-sacks-friedberg',
    'prof-g': 'the-prof-g-pod-with-scott-galloway',
    'hard-fork': 'hard-fork',
    'acquired': 'acquired',
    'invest-like-the-best': 'invest-like-the-best-with-patrick-oshaughnessy',
    'invest-like-the-best-with-patrick-oaposshaughnessy': 'invest-like-the-best-with-patrick-oshaughnessy',
    'a16z-podcast': 'a16z-podcast',
    'stratechery': 'stratechery',

    # Economics/Finance
    'odd-lots': 'oddlots',
    'macro-voices': 'macro-voices',
    'animal-spirits-podcast': 'animal-spirits',

    # Knowledge/Education
    'no-such-thing-as-a-fish': 'no-such-thing-as-a-fish',
    'revisionist-history': 'revisionist-history',
    'cortex': 'cortex',
    'radiolab': 'radiolab',
    'conan-obrien-needs-a-friend': 'conan-obrien-needs-a-friend',
    'ezra-klein-show': 'the-ezra-klein-show',
    'we-can-do-hard-things': 'we-can-do-hard-things',
    'smartless': 'smartless',
    'freakonomics-radio': 'freakonomics-radio',
    'hidden-brain': 'hidden-brain',
    'planet-money': 'planet-money',
    'the-daily': 'the-daily',
    'how-i-built-this': 'how-i-built-this-with-guy-raz',
    'stuff-you-should-know': 'stuff-you-should-know',
    'lex-fridman-podcast': 'lex-fridman-podcast',
    'huberman-lab': 'huberman-lab',
    'tim-ferriss-show': 'the-tim-ferriss-show',
    'joe-rogan-experience': 'the-joe-rogan-experience',
    'call-her-daddy': 'call-her-daddy',
    'armchair-expert': 'armchair-expert-with-dax-shepard',
    'crime-junkie': 'crime-junkie',
    'my-favorite-murder': 'my-favorite-murder-with-karen-kilgariff-and-georgia-hardstark',
    'serial': 'serial',
    's-town': 's-town',
    'reply-all': 'reply-all',
    'this-american-life': 'this-american-life',
    'npr-politics-podcast': 'the-npr-politics-podcast',
    'pod-save-america': 'pod-save-america',
    '99-invisible': '99-invisible',
    'decoder-with-nilay-patel': 'decoder-with-nilay-patel',
    'vergecast': 'the-vergecast',
    'accidental-tech-podcast': 'accidental-tech-podcast',
    'upgrade': 'upgrade',
    'connected': 'connected',
    'mac-power-users': 'mac-power-users',
    'atp': 'accidental-tech-podcast',
}


class PodscriptsResolver:
    """Resolver that fetches transcripts from podscripts.co"""

    def __init__(self, user_agent: str = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)", timeout: int = 30):
        self.user_agent = user_agent
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        })
        self.base_url = "https://podscripts.co"
        self.backoff_count = 0  # Track consecutive 429s for backoff

    def resolve(self, episode: Episode, podcast_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Find transcript on Podscripts for this episode.

        Returns list of transcript sources with:
        - url: Podscripts URL
        - confidence: 0.0-1.0 confidence score
        - resolver: 'podscripts'
        - metadata: transcript content and info
        """
        sources = []
        global _last_podscripts_request

        try:
            # Rate limiting with exponential backoff for 429 errors
            base_delay = PODSCRIPTS_RATE_LIMIT_SECONDS * (2 ** self.backoff_count)
            elapsed = time.time() - _last_podscripts_request
            if elapsed < base_delay:
                wait_time = base_delay - elapsed
                logger.debug(f"Rate limiting: waiting {wait_time:.1f}s before Podscripts request")
                time.sleep(wait_time)
            _last_podscripts_request = time.time()

            # Get podcast slug from config or try to match
            podcast_slug = podcast_config.get('slug', '')

            # First check if podscripts_id is explicitly configured in mapping.yml
            config_section = podcast_config.get('config', {})
            podscripts_id = config_section.get('podscripts_id')

            # If not in config, try the mapping
            if not podscripts_id:
                podscripts_id = PODSCRIPTS_MAPPING.get(podcast_slug)

            # Last resort: try to find by name
            if not podscripts_id:
                podcast_name = podcast_config.get('name', '').lower()
                for our_slug, ps_id in PODSCRIPTS_MAPPING.items():
                    if our_slug in podcast_name.replace(' ', '-').lower():
                        podscripts_id = ps_id
                        break

            if not podscripts_id:
                logger.debug(f"No Podscripts mapping for podcast: {podcast_slug}")
                return sources

            logger.debug(f"Using Podscripts ID '{podscripts_id}' for podcast '{podcast_slug}'")

            # Try to find the episode on Podscripts
            episode_url = self._find_episode_url(episode, podscripts_id)

            if episode_url:
                # Fetch the transcript
                transcript_content = self._fetch_transcript(episode_url)

                if transcript_content and len(transcript_content) > 500:
                    confidence = self._calculate_confidence(episode, transcript_content)

                    sources.append({
                        'url': episode_url,
                        'confidence': confidence,
                        'resolver': 'podscripts',
                        'metadata': {
                            'content': transcript_content,
                            'content_length': len(transcript_content),
                            'source': 'podscripts.co',
                            'accuracy': 'ai_generated',
                            'episode_title': episode.title,
                        }
                    })

                    logger.info(f"Found Podscripts transcript for: {episode.title}")

        except Exception as e:
            logger.error(f"Error in Podscripts resolver for {episode.title}: {e}")

        return sources

    def _find_episode_url(self, episode: Episode, podscripts_id: str) -> Optional[str]:
        """Find the Podscripts URL for an episode by searching/matching"""

        # Create episode slug from title
        episode_slug = self._create_slug(episode.title)

        # Try direct URL construction first
        potential_urls = [
            f"{self.base_url}/podcasts/{podscripts_id}/{episode_slug}",
            f"{self.base_url}/podcasts/{podscripts_id}/{episode_slug}/",
        ]

        for url in potential_urls:
            try:
                response = self.session.head(url, timeout=10, allow_redirects=True)
                if response.status_code == 200:
                    return url
            except Exception:
                continue

        # Try searching within the podcast's page
        search_url = f"{self.base_url}/podcasts/{podscripts_id}/"
        try:
            response = self.session.get(search_url, timeout=self.timeout)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')

                # Look for links that might match our episode
                title_words = set(word.lower() for word in re.findall(r'\w+', episode.title) if len(word) > 3)

                for link in soup.find_all('a', href=True):
                    href = link.get('href', '')
                    link_text = link.get_text().lower()

                    # Check if this link matches our episode
                    if podscripts_id in href and href != search_url:
                        link_words = set(word.lower() for word in re.findall(r'\w+', link_text) if len(word) > 3)

                        # Calculate word overlap
                        overlap = len(title_words & link_words)
                        if overlap >= min(3, len(title_words) * 0.5):
                            full_url = urljoin(self.base_url, href)
                            return full_url

        except Exception as e:
            logger.debug(f"Error searching Podscripts: {e}")

        return None

    def _fetch_transcript(self, url: str) -> Optional[str]:
        """Fetch transcript content from a Podscripts episode page"""
        try:
            response = self.session.get(url, timeout=self.timeout)

            # Handle rate limiting with exponential backoff
            if response.status_code == 429:
                self.backoff_count = min(self.backoff_count + 1, 4)  # Max 4x backoff (64s)
                wait_time = PODSCRIPTS_RATE_LIMIT_SECONDS * (2 ** self.backoff_count)
                logger.warning(f"Podscripts rate limited (429). Backing off {wait_time:.0f}s...")
                time.sleep(wait_time)
                # Retry once after backoff
                response = self.session.get(url, timeout=self.timeout)
            else:
                # Success - reset backoff
                self.backoff_count = max(0, self.backoff_count - 1)

            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Podscripts transcript selectors
            transcript_selectors = [
                '.podcast-transcript',
                '.transcript-text',
                '.single-sentence',
                '#transcript',
                'div[class*="transcript"]',
            ]

            for selector in transcript_selectors:
                elements = soup.select(selector)
                if elements:
                    # Combine all matching elements
                    text_parts = []
                    for elem in elements:
                        text = elem.get_text(separator=' ', strip=True)
                        if text and len(text) > 20:
                            text_parts.append(text)

                    if text_parts:
                        full_text = '\n\n'.join(text_parts)
                        return self._clean_transcript(full_text)

            # Fallback: try to get main content
            main_content = soup.find('main') or soup.find('article') or soup.find('body')
            if main_content:
                # Remove nav, header, footer, scripts
                for tag in main_content.find_all(['nav', 'header', 'footer', 'script', 'style', 'aside']):
                    tag.decompose()

                text = main_content.get_text(separator='\n', strip=True)
                if len(text) > 1000:
                    return self._clean_transcript(text)

        except Exception as e:
            logger.error(f"Error fetching Podscripts transcript from {url}: {e}")

        return None

    def _clean_transcript(self, text: str) -> str:
        """Clean and normalize transcript text"""
        if not text:
            return ""

        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r' +', ' ', text)

        # Remove common UI elements
        patterns_to_remove = [
            r'Listen on.*?(?=\n|$)',
            r'Subscribe.*?(?=\n|$)',
            r'Share this episode.*?(?=\n|$)',
            r'Rate and review.*?(?=\n|$)',
            r'Follow us on.*?(?=\n|$)',
            r'Join our.*?(?=\n|$)',
            r'Copyright.*?(?=\n|$)',
            r'All rights reserved.*?(?=\n|$)',
        ]

        for pattern in patterns_to_remove:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)

        return text.strip()

    def _create_slug(self, title: str) -> str:
        """Create a URL slug from episode title"""
        # Remove special characters, convert to lowercase
        slug = title.lower()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[-\s]+', '-', slug)
        slug = slug.strip('-')
        return slug[:100]  # Limit length

    def _calculate_confidence(self, episode: Episode, content: str) -> float:
        """Calculate confidence score for matched transcript"""
        confidence = 0.7  # Base confidence for Podscripts (AI-generated)

        # Check title word overlap
        if episode.title:
            title_words = set(word.lower() for word in re.findall(r'\w+', episode.title) if len(word) > 3)
            content_lower = content.lower()

            matches = sum(1 for word in title_words if word in content_lower)
            if matches >= len(title_words) * 0.5:
                confidence += 0.15

        # Length bonus
        if len(content) > 10000:
            confidence += 0.1
        elif len(content) > 5000:
            confidence += 0.05

        return min(confidence, 0.95)


def create_resolver() -> PodscriptsResolver:
    """Factory function to create resolver instance."""
    return PodscriptsResolver()
