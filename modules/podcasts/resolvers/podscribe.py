#!/usr/bin/env python3
"""
Podscribe.com Transcript Resolver

Fetches AI-generated transcripts from app.podscribe.com.
Podscribe is a JS-heavy SPA that requires Playwright for navigation.

Supports podcasts like:
- The Rewatchables (series/530)
- Revisionist History (series/1475)
- Plain English (series/2143152)
"""

import logging
import re
import time
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin

from modules.podcasts.store import Episode

logger = logging.getLogger(__name__)

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not available - Podscribe resolver won't work")

# Mapping of our podcast slugs to Podscribe series IDs
PODSCRIBE_MAPPING = {
    'the-rewatchables': '530',
    'revisionist-history': '1475',
    'plain-english-with-derek-thompson': '2143152',
}

# Rate limiting
PODSCRIBE_RATE_LIMIT_SECONDS = 5.0
_last_podscribe_request = 0


class PodscribeResolver:
    """Resolver that fetches transcripts from app.podscribe.com using Playwright."""

    def __init__(self, user_agent: str = None, timeout: int = 60):
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
        self.timeout = timeout * 1000  # Convert to ms
        self.base_url = "https://app.podscribe.com"

    def resolve(self, episode: Episode, podcast_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Find transcript on Podscribe for this episode.

        Returns list of transcript sources with:
        - url: Podscribe URL
        - confidence: 0.0-1.0 confidence score
        - resolver: 'podscribe'
        - metadata: transcript content and info
        """
        sources = []
        global _last_podscribe_request

        if not PLAYWRIGHT_AVAILABLE:
            logger.debug("Playwright not available, skipping Podscribe resolver")
            return sources

        try:
            # Rate limiting
            elapsed = time.time() - _last_podscribe_request
            if elapsed < PODSCRIBE_RATE_LIMIT_SECONDS:
                time.sleep(PODSCRIBE_RATE_LIMIT_SECONDS - elapsed)
            _last_podscribe_request = time.time()

            # Get series ID from config or mapping
            podcast_slug = podcast_config.get('slug', '')
            config_section = podcast_config.get('config', {})
            series_id = config_section.get('podscribe_series_id')

            if not series_id:
                series_id = PODSCRIBE_MAPPING.get(podcast_slug)

            if not series_id:
                logger.debug(f"No Podscribe mapping for podcast: {podcast_slug}")
                return sources

            # Find the episode on Podscribe
            episode_url, transcript_content = self._find_and_fetch_episode(
                episode, series_id
            )

            if transcript_content and len(transcript_content) > 500:
                confidence = self._calculate_confidence(episode, transcript_content)

                sources.append({
                    'url': episode_url or f"{self.base_url}/series/{series_id}",
                    'confidence': confidence,
                    'resolver': 'podscribe',
                    'metadata': {
                        'content': transcript_content,
                        'content_length': len(transcript_content),
                        'source': 'podscribe.com',
                        'accuracy': 'ai_generated',
                        'episode_title': episode.title,
                    }
                })

                logger.info(f"Found Podscribe transcript for: {episode.title}")

        except Exception as e:
            logger.error(f"Error in Podscribe resolver for {episode.title}: {e}")

        return sources

    def _find_and_fetch_episode(self, episode: Episode, series_id: str) -> tuple[Optional[str], Optional[str]]:
        """Find episode on Podscribe and fetch transcript using Playwright."""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(user_agent=self.user_agent)
                page = context.new_page()

                # Navigate to series page
                series_url = f"{self.base_url}/series/{series_id}"
                page.goto(series_url, wait_until="domcontentloaded", timeout=self.timeout)

                # Wait for episodes to load
                page.wait_for_timeout(3000)

                # Scroll to load more episodes (Podscribe uses infinite scroll)
                for _ in range(5):
                    page.keyboard.press('End')
                    page.wait_for_timeout(1500)

                # Try to find episode by title matching
                title_words = set(word.lower() for word in re.findall(r'\w+', episode.title) if len(word) > 3)

                # Get all episode links on the page
                episode_links = page.query_selector_all('a[href*="/episode/"]')

                best_match_url = None
                best_match_score = 0

                for link in episode_links:
                    link_text = link.inner_text().lower()
                    href = link.get_attribute('href')

                    if not href:
                        continue

                    # Check word overlap
                    link_words = set(word.lower() for word in re.findall(r'\w+', link_text) if len(word) > 3)
                    overlap = len(title_words & link_words)

                    if overlap > best_match_score and overlap >= min(3, len(title_words) * 0.4):
                        best_match_score = overlap
                        best_match_url = href

                if best_match_url:
                    # Navigate to episode page
                    if not best_match_url.startswith('http'):
                        best_match_url = urljoin(self.base_url, best_match_url)

                    page.goto(best_match_url, wait_until="domcontentloaded", timeout=self.timeout)
                    page.wait_for_timeout(3000)

                    # Extract transcript content
                    transcript_content = self._extract_transcript(page)

                    browser.close()
                    return best_match_url, transcript_content

                browser.close()

        except Exception as e:
            logger.error(f"Error fetching from Podscribe: {e}")

        return None, None

    def _extract_transcript(self, page) -> Optional[str]:
        """Extract transcript content from Podscribe episode page."""
        try:
            # Podscribe shows transcript in a table/list format with timestamps
            # Try various selectors
            selectors = [
                '[class*="transcript"]',
                '[class*="Transcript"]',
                'table tbody',
                '.episode-content',
                'main',
            ]

            for selector in selectors:
                try:
                    element = page.query_selector(selector)
                    if element:
                        text = element.inner_text()
                        if text and len(text) > 500:
                            return self._clean_transcript(text)
                except Exception:
                    continue

            # Fallback: get main content
            main = page.query_selector('main')
            if main:
                text = main.inner_text()
                if len(text) > 500:
                    return self._clean_transcript(text)

        except Exception as e:
            logger.error(f"Error extracting Podscribe transcript: {e}")

        return None

    def _clean_transcript(self, text: str) -> str:
        """Clean and normalize transcript text."""
        if not text:
            return ""

        # Remove timestamps like "00:00:00" or "0:00"
        text = re.sub(r'\d+:\d+(?::\d+)?\s*', '', text)

        # Remove [AD] markers and similar
        text = re.sub(r'\[AD\]|\[ad\]|\[Advertisement\]', '', text, flags=re.IGNORECASE)

        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r' +', ' ', text)

        return text.strip()

    def _calculate_confidence(self, episode: Episode, content: str) -> float:
        """Calculate confidence score for matched transcript."""
        confidence = 0.8  # Base confidence for Podscribe (AI-generated with review)

        # Check title word overlap
        if episode.title:
            title_words = set(word.lower() for word in re.findall(r'\w+', episode.title) if len(word) > 3)
            content_lower = content.lower()

            matches = sum(1 for word in title_words if word in content_lower)
            if matches >= len(title_words) * 0.5:
                confidence += 0.1

        # Length bonus
        if len(content) > 10000:
            confidence += 0.05
        elif len(content) > 5000:
            confidence += 0.03

        return min(confidence, 0.95)


def create_resolver() -> PodscribeResolver:
    """Factory function to create resolver instance."""
    return PodscribeResolver()
