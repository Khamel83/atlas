#!/usr/bin/env python3
"""
NYT Podcast Transcript Resolver

Fetches transcripts from NYT podcasts using the ?showTranscript=1 query parameter.
Requires NYT authentication cookies for full access.

Supports podcasts like:
- Hard Fork
- The Daily
- Ezra Klein Show
"""

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from modules.podcasts.store import Episode

logger = logging.getLogger(__name__)

# Rate limiting
NYT_RATE_LIMIT_SECONDS = 3.0
_last_nyt_request = 0


class NYTResolver:
    """Resolver that fetches transcripts from NYT podcasts."""

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

        # Load NYT cookies
        self._load_cookies()

    def _load_cookies(self):
        """Load NYT authentication cookies from file or environment."""
        cookies_loaded = False

        # Try environment variable first
        cookie_env = os.environ.get('NYT_COOKIES')
        if cookie_env:
            try:
                cookies = json.loads(cookie_env)
                for name, value in cookies.items():
                    self.session.cookies.set(name, value, domain='.nytimes.com')
                cookies_loaded = True
                logger.debug("Loaded NYT cookies from environment")
            except Exception as e:
                logger.warning(f"Failed to parse NYT_COOKIES env var: {e}")

        # Try config file
        if not cookies_loaded:
            cookie_paths = [
                Path.home() / ".config" / "atlas" / "nyt_cookies.json",
                Path.home() / ".config" / "atlas" / "cookies" / "nytimes.json",
            ]

            for cookie_path in cookie_paths:
                if cookie_path.exists():
                    try:
                        with open(cookie_path) as f:
                            cookies = json.load(f)

                        # Handle different cookie formats
                        if isinstance(cookies, list):
                            # Browser extension format
                            for cookie in cookies:
                                name = cookie.get('name', '')
                                value = cookie.get('value', '')
                                if name and value:
                                    self.session.cookies.set(name, value, domain='.nytimes.com')
                        elif isinstance(cookies, dict):
                            # Simple format
                            for name, value in cookies.items():
                                self.session.cookies.set(name, value, domain='.nytimes.com')

                        cookies_loaded = True
                        logger.debug(f"Loaded NYT cookies from {cookie_path}")
                        break
                    except Exception as e:
                        logger.warning(f"Failed to load cookies from {cookie_path}: {e}")

        if not cookies_loaded:
            logger.warning("No NYT cookies found - transcripts may require subscription")

    def resolve(self, episode: Episode, podcast_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Find transcript on NYT for this episode.

        Returns list of transcript sources with:
        - url: NYT URL with ?showTranscript=1
        - confidence: 0.0-1.0 confidence score
        - resolver: 'nyt'
        - metadata: transcript content and info
        """
        sources = []
        global _last_nyt_request

        if not episode.url:
            return sources

        # Check if this is an NYT URL
        parsed = urlparse(episode.url)
        if 'nytimes.com' not in parsed.netloc and 'nyt.com' not in parsed.netloc:
            return sources

        try:
            # Rate limiting
            elapsed = time.time() - _last_nyt_request
            if elapsed < NYT_RATE_LIMIT_SECONDS:
                time.sleep(NYT_RATE_LIMIT_SECONDS - elapsed)
            _last_nyt_request = time.time()

            # Add ?showTranscript=1 to URL
            transcript_url = self._add_transcript_param(episode.url)

            # Fetch the page
            response = self.session.get(transcript_url, timeout=self.timeout)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract transcript content
            transcript_content = self._extract_transcript(soup)

            if transcript_content and len(transcript_content) > 500:
                confidence = self._calculate_confidence(episode, transcript_content)

                # Also try to extract show notes
                show_notes = self._extract_show_notes(soup)

                sources.append({
                    'url': transcript_url,
                    'confidence': confidence,
                    'resolver': 'nyt',
                    'metadata': {
                        'content': transcript_content,
                        'content_length': len(transcript_content),
                        'source': 'nytimes.com',
                        'accuracy': 'official',
                        'episode_title': episode.title,
                        'show_notes': show_notes if show_notes else None,
                    }
                })

                logger.info(f"Found NYT transcript for: {episode.title}")

        except Exception as e:
            logger.error(f"Error in NYT resolver for {episode.title}: {e}")

        return sources

    def _add_transcript_param(self, url: str) -> str:
        """Add ?showTranscript=1 to URL."""
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        query_params['showTranscript'] = ['1']
        new_query = urlencode(query_params, doseq=True)
        return urlunparse(parsed._replace(query=new_query))

    def _extract_transcript(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract transcript content from NYT page."""
        # NYT transcript selectors
        selectors = [
            'section[data-testid="transcript"]',
            '.StoryBodyCompanionColumn',
            '.ArticleBody',
            'article[data-testid="article-body"]',
            '.story-body-text',
            '[data-component="transcript"]',
        ]

        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                text_parts = []
                for elem in elements:
                    # Remove ads and promotional content
                    for ad in elem.select('[data-testid="ad"], .ad, .promo'):
                        ad.decompose()

                    text = elem.get_text(separator='\n', strip=True)
                    if text and len(text) > 100:
                        text_parts.append(text)

                if text_parts:
                    return self._clean_transcript('\n\n'.join(text_parts))

        return None

    def _extract_show_notes(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract show notes (links, guests, etc.) from NYT page."""
        show_notes_parts = []

        # Look for related links section
        for selector in ['[data-testid="related-links"]', '.related-links', '.episode-links']:
            elem = soup.select_one(selector)
            if elem:
                links = elem.find_all('a', href=True)
                for link in links:
                    text = link.get_text(strip=True)
                    href = link.get('href', '')
                    if text and href:
                        show_notes_parts.append(f"- [{text}]({href})")

        # Look for guest information
        for selector in ['.guest-info', '.episode-guests', '[data-testid="guests"]']:
            elem = soup.select_one(selector)
            if elem:
                show_notes_parts.append(f"\n**Guests:**\n{elem.get_text(strip=True)}")

        return '\n'.join(show_notes_parts) if show_notes_parts else None

    def _clean_transcript(self, text: str) -> str:
        """Clean and normalize transcript text."""
        if not text:
            return ""

        # Remove common UI elements
        patterns_to_remove = [
            r'Listen to.*?(?=\n|$)',
            r'Subscribe.*?(?=\n|$)',
            r'Share this.*?(?=\n|$)',
            r'This transcript was.*?(?=\n|$)',
            r'Advertisement\s*',
            r'ADVERTISEMENT\s*',
        ]

        for pattern in patterns_to_remove:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)

        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
        text = re.sub(r' +', ' ', text)

        return text.strip()

    def _calculate_confidence(self, episode: Episode, content: str) -> float:
        """Calculate confidence score for matched transcript."""
        confidence = 0.9  # High base confidence for NYT official transcripts

        # Check title word overlap
        if episode.title:
            title_words = set(word.lower() for word in re.findall(r'\w+', episode.title) if len(word) > 3)
            content_lower = content.lower()

            matches = sum(1 for word in title_words if word in content_lower)
            if matches >= len(title_words) * 0.5:
                confidence += 0.05

        return min(confidence, 0.98)


def create_resolver() -> NYTResolver:
    """Factory function to create resolver instance."""
    return NYTResolver()
