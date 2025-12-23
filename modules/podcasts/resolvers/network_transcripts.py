"""
Network-specific transcript resolvers for major podcast networks.
Each network has its own transcript URL patterns and extraction methods.
"""

import logging
import re
import time
from typing import List, Optional, Dict, Any, Callable
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)

class NetworkTranscriptResolver:
    """Resolves transcripts from major podcast networks."""

    name = "network_transcripts"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        # Network-specific resolvers
        self.network_resolvers = {
            'npr.org': self._resolve_npr,
            'thisamericanlife.org': self._resolve_tal,
            'radiolab.org': self._resolve_radiolab,
            'wnyc.org': self._resolve_wnyc,
            'slate.com': self._resolve_slate,
            'gimletmedia.com': self._resolve_gimlet,
            'spotify.com': self._resolve_spotify,
            'apple.com': self._resolve_apple,
            'google.com': self._resolve_google,
            'overcast.fm': self._resolve_overcast,
            'pocketcasts.com': self._resolve_pocketcasts
        }

    def resolve(self, episode, podcast_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Standard resolver interface - wraps resolve_for_episode."""
        podcast_name = podcast_config.get('name', '')
        return self.resolve_for_episode(episode.title, podcast_name, episode.url)

    def resolve_for_episode(self, episode_title: str, podcast_name: str, episode_url: str) -> List[Dict[str, Any]]:
        """Main resolver - detect network and use appropriate method."""
        results = []

        if not episode_url:
            return results

        # Detect network from URL
        domain = urlparse(episode_url).netloc.lower()

        # Find matching resolver
        resolver = None
        for network_domain, resolver_func in self.network_resolvers.items():
            if network_domain in domain:
                resolver = resolver_func
                break

        if resolver:
            try:
                network_results = resolver(episode_url, episode_title, podcast_name)
                if network_results:
                    results.extend(network_results)
                    logger.info(f"Found {len(network_results)} network transcripts for '{episode_title}'")
            except Exception as e:
                logger.error(f"Network resolver failed for {domain}: {e}")

        return results

    def _resolve_npr(self, episode_url: str, title: str, podcast: str) -> List[Dict[str, Any]]:
        """NPR network transcript resolver."""
        results = []

        try:
            response = self.session.get(episode_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            # NPR transcript patterns
            transcript_selectors = [
                'div.storytext',
                'div.transcript',
                'div[data-module="Transcript"]',
                'section.transcript',
                '.transcript-content'
            ]

            for selector in transcript_selectors:
                transcript_elem = soup.select_one(selector)
                if transcript_elem:
                    text = self._clean_transcript_text(transcript_elem.get_text())
                    if len(text) > 500:  # Minimum viable transcript
                        results.append({
                            'url': episode_url,
                            'confidence': 0.95,
                            'resolver': 'network_transcripts',
                            'metadata': {
                                'content': text,
                                'content_length': len(text),
                                'accuracy': 'very_high',
                                'method': 'npr_network',
                                'selector': selector
                            }
                        })
                        break

        except Exception as e:
            logger.error(f"NPR resolver failed for {episode_url}: {e}")

        return results

    def _resolve_tal(self, episode_url: str, title: str, podcast: str) -> List[Dict[str, Any]]:
        """This American Life transcript resolver."""
        results = []

        try:
            # TAL has specific transcript URLs
            episode_id = re.search(r'/(\d+)/', episode_url)
            if episode_id:
                transcript_url = f"https://www.thisamericanlife.org/episode/{episode_id.group(1)}/transcript"

                response = self.session.get(transcript_url, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')

                    # TAL transcript content
                    transcript_div = soup.select_one('div.transcript')
                    if transcript_div:
                        text = self._clean_transcript_text(transcript_div.get_text())
                        if len(text) > 1000:
                            results.append({
                                'url': transcript_url,
                                'confidence': 0.95,
                                'resolver': 'network_transcripts',
                                'metadata': {
                                    'content': text,
                                    'content_length': len(text),
                                    'accuracy': 'very_high',
                                    'method': 'tal_official',
                                    'episode_id': episode_id.group(1)
                                }
                            })

        except Exception as e:
            logger.error(f"This American Life resolver failed: {e}")

        return results

    def _resolve_radiolab(self, episode_url: str, title: str, podcast: str) -> List[Dict[str, Any]]:
        """Radiolab/WNYC transcript resolver."""
        results = []

        try:
            # Radiolab has transcripts at /podcast/{slug}/transcript
            # Try appending /transcript to the episode URL first
            transcript_url = episode_url.rstrip('/') + '/transcript'

            response = self.session.get(transcript_url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')

                # Radiolab transcript selectors
                transcript_selectors = [
                    'div.transcript-content',
                    'div.episode-transcript',
                    'section.transcript',
                    'article.transcript',
                    'div[data-transcript]',
                    '.article-text',
                    '.story-text',
                    'main article'
                ]

                for selector in transcript_selectors:
                    transcript_elem = soup.select_one(selector)
                    if transcript_elem:
                        text = self._clean_transcript_text(transcript_elem.get_text())
                        if len(text) > 500:
                            results.append({
                                'url': transcript_url,
                                'confidence': 0.95,
                                'resolver': 'network_transcripts',
                                'metadata': {
                                    'content': text,
                                    'content_length': len(text),
                                    'accuracy': 'very_high',
                                    'method': 'radiolab_transcript_suffix'
                                }
                            })
                            return results

            # Fallback: try the episode page itself
            response = self.session.get(episode_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            # Radiolab transcript patterns on main page
            transcript_selectors = [
                'div.transcript-content',
                'div.episode-transcript',
                'section.transcript',
                'div[data-transcript]'
            ]

            for selector in transcript_selectors:
                transcript_elem = soup.select_one(selector)
                if transcript_elem:
                    text = self._clean_transcript_text(transcript_elem.get_text())
                    if len(text) > 500:
                        results.append({
                            'url': episode_url,
                            'confidence': 0.95,
                            'resolver': 'network_transcripts',
                            'metadata': {
                                'content': text,
                                'content_length': len(text),
                                'accuracy': 'very_high',
                                'method': 'radiolab_wnyc'
                            }
                        })
                        break

        except Exception as e:
            logger.error(f"Radiolab resolver failed: {e}")

        return results

    def _resolve_wnyc(self, episode_url: str, title: str, podcast: str) -> List[Dict[str, Any]]:
        """WNYC network resolver."""
        return self._resolve_radiolab(episode_url, title, podcast)  # Same pattern

    def _resolve_slate(self, episode_url: str, title: str, podcast: str) -> List[Dict[str, Any]]:
        """Slate podcast network resolver."""
        results = []

        try:
            response = self.session.get(episode_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            # Slate transcript patterns
            article_content = soup.select_one('div.slate-article-content, article.post-content')
            if article_content:
                text = self._clean_transcript_text(article_content.get_text())
                if len(text) > 1000:  # Slate articles are longer
                    results.append({
                        'url': episode_url,
                        'confidence': 0.85,
                        'resolver': 'network_transcripts',
                        'metadata': {
                            'content': text,
                            'content_length': len(text),
                            'accuracy': 'high',
                            'method': 'slate_network'
                        }
                    })

        except Exception as e:
            logger.error(f"Slate resolver failed: {e}")

        return results

    def _resolve_gimlet(self, episode_url: str, title: str, podcast: str) -> List[Dict[str, Any]]:
        """Gimlet Media resolver."""
        # Placeholder - Gimlet uses Spotify now
        return self._resolve_spotify(episode_url, title, podcast)

    def _resolve_spotify(self, episode_url: str, title: str, podcast: str) -> List[Dict[str, Any]]:
        """Spotify podcast transcript resolver."""
        # Note: Spotify transcripts require API access, placeholder for now
        results = []
        logger.debug(f"Spotify transcript resolution not yet implemented for {episode_url}")
        return results

    def _resolve_apple(self, episode_url: str, title: str, podcast: str) -> List[Dict[str, Any]]:
        """Apple Podcasts transcript resolver."""
        # Note: Apple Podcasts transcripts require API access
        results = []
        logger.debug(f"Apple Podcasts transcript resolution not yet implemented for {episode_url}")
        return results

    def _resolve_google(self, episode_url: str, title: str, podcast: str) -> List[Dict[str, Any]]:
        """Google Podcasts transcript resolver."""
        # Note: Google Podcasts was discontinued
        results = []
        return results

    def _resolve_overcast(self, episode_url: str, title: str, podcast: str) -> List[Dict[str, Any]]:
        """Overcast transcript resolver."""
        results = []
        logger.debug(f"Overcast transcript resolution not yet implemented for {episode_url}")
        return results

    def _resolve_pocketcasts(self, episode_url: str, title: str, podcast: str) -> List[Dict[str, Any]]:
        """PocketCasts transcript resolver."""
        results = []
        logger.debug(f"PocketCasts transcript resolution not yet implemented for {episode_url}")
        return results

    def _clean_transcript_text(self, text: str) -> str:
        """Clean and normalize transcript text."""
        if not text:
            return ""

        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())

        # Remove common transcript artifacts
        text = re.sub(r'\[MUSIC\]|\[LAUGHTER\]|\[APPLAUSE\]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\[.*?\]', '', text)  # Remove any bracketed stage directions

        # Fix punctuation spacing
        text = re.sub(r'\s+([,.!?])', r'\1', text)
        text = re.sub(r'([.!?])\s*([A-Z])', r'\1 \2', text)

        return text.strip()

def create_resolver() -> NetworkTranscriptResolver:
    """Factory function to create resolver instance."""
    return NetworkTranscriptResolver()