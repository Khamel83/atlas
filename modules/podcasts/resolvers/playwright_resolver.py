#!/usr/bin/env python3
"""
Playwright-based Transcript Resolver

Uses headless browser for JS-rendered sites like:
- Dithering (dithering.fm)
- Asianometry (asianometry.passport.online)
- Podscribe (app.podscribe.com)
- Tapesearch (tapesearch.com)
"""

import logging
import re
import time
from typing import List, Dict, Any, Optional
from pathlib import Path

from modules.podcasts.store import Episode

logger = logging.getLogger(__name__)

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not available - JS-rendered sites won't work")


class PlaywrightResolver:
    """Resolver that uses headless browser for JS-rendered transcript pages."""

    def __init__(self, user_agent: str = None, timeout: int = 60):
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
        self.timeout = timeout * 1000  # Convert to ms (60s default for slow JS sites)
        self.rate_limit_seconds = 3.0  # Be gentle with JS sites

    def resolve(self, episode: Episode, podcast_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Fetch transcript from JS-rendered page.

        Returns list of transcript sources with:
        - url: source URL
        - confidence: 0.0-1.0 confidence score
        - resolver: 'playwright'
        - metadata: extracted content
        """
        sources = []

        if not PLAYWRIGHT_AVAILABLE:
            logger.debug("Playwright not available, skipping")
            return sources

        if not episode.url:
            logger.debug(f"No URL for episode: {episode.title}")
            return sources

        try:
            # Rate limiting
            time.sleep(self.rate_limit_seconds)

            # Get transcript selector from config
            transcript_selector = podcast_config.get('transcript_selector', '')

            # Check if we need to transform the URL (e.g., CWT: libsyn -> conversationswithtyler.com)
            fetch_url = episode.url
            url_transform = podcast_config.get('config', {}).get('url_transform', '')
            if url_transform == 'cwt_libsyn':
                # Transform CWT episode title to transcript URL
                # Title: "Niall Ferguson on Why We Study History" -> /episodes/niall-ferguson/
                # Title: "Sam Altman on Trust, Persuasion..." -> /episodes/sam-altman-2/ (repeat guest)
                import re
                # Extract guest name from title (before " on " or " and " or end)
                title = episode.title
                match = re.match(r'^([A-Za-z\s\.\'-]+?)(?:\s+on\s+|\s+and\s+Tyler|\s*$)', title)
                if match:
                    guest_name = match.group(1).strip()
                    # Convert to slug
                    slug = guest_name.lower().replace(' ', '-').replace('.', '').replace("'", '')
                    slug = re.sub(r'-+', '-', slug).strip('-')
                    fetch_url = f"https://conversationswithtyler.com/episodes/{slug}/"
                    logger.info(f"Transformed title '{title}' -> {fetch_url}")

            # Fetch with Playwright
            logger.info(f"Playwright fetching {fetch_url}...")
            html = self._fetch_page(fetch_url)

            if not html:
                logger.info(f"Playwright got no HTML for {episode.title}")
                return sources

            logger.info(f"Playwright got {len(html)} chars of HTML, extracting with selector: {transcript_selector}")
            # Extract transcript content
            content = self._extract_transcript(html, transcript_selector)

            if content and len(content) > 500:
                logger.debug(f"Extracted {len(content)} chars of content")
                confidence = self._calculate_confidence(episode, content)

                sources.append({
                    'url': episode.url,
                    'confidence': confidence,
                    'resolver': 'playwright',
                    'metadata': {
                        'content': content,
                        'content_length': len(content),
                        'episode_title': episode.title,
                        'extraction_method': 'playwright_headless',
                    }
                })

                logger.info(f"Playwright resolver found transcript for: {episode.title}")
            else:
                logger.info(f"Playwright: content too short ({len(content) if content else 0} chars) for {episode.title}")

        except Exception as e:
            logger.error(f"Playwright resolver error for {episode.title}: {e}")

        return sources

    def _fetch_page(self, url: str, wait_time: int = 5000) -> Optional[str]:
        """Fetch page using headless browser."""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(user_agent=self.user_agent)

                page = context.new_page()
                # Use domcontentloaded instead of networkidle - faster and less prone to timeout
                page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)

                # Wait longer for JS to render after DOM is loaded
                page.wait_for_timeout(wait_time)

                # Try to wait for common transcript containers
                try:
                    page.wait_for_selector(
                        '.transcript, .entry-content, article, main, [class*="transcript"]',
                        timeout=10000
                    )
                except Exception:
                    pass  # Continue anyway, content may still be there

                html = page.content()
                browser.close()

                return html

        except Exception as e:
            logger.error(f"Playwright fetch failed for {url}: {e}")
            return None

    def _extract_transcript(self, html: str, selector: str = '') -> Optional[str]:
        """Extract transcript content from HTML."""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')

            # Try configured selector first - check ALL matches, take longest
            if selector:
                for sel in selector.split(','):
                    elements = soup.select(sel.strip())
                    if elements:
                        # Find the element with the most text (likely the transcript)
                        best_text = ""
                        for elem in elements:
                            text = elem.get_text(separator='\n', strip=True)
                            if len(text) > len(best_text):
                                best_text = text
                        if len(best_text) > 500:
                            return self._clean_transcript(best_text)

            # Common transcript selectors for JS sites
            selectors = [
                '.transcript',
                '.episode-transcript',
                '.podcast-transcript',
                '.transcript-text',
                '.single-sentence',
                '[class*="transcript"]',
                '.generic__content',
                '.entry-content',
                '.post-content',
                'article',
                'main',
            ]

            for sel in selectors:
                elements = soup.select(sel)
                if elements:
                    # Find the element with the most text
                    best_text = ""
                    for elem in elements:
                        text = elem.get_text(separator='\n', strip=True)
                        if len(text) > len(best_text) and self._looks_like_transcript(text):
                            best_text = text
                    if len(best_text) > 500:
                        return self._clean_transcript(best_text)

        except Exception as e:
            logger.error(f"Transcript extraction failed: {e}")

        return None

    def _looks_like_transcript(self, text: str) -> bool:
        """Check if text looks like a transcript."""
        if len(text) < 500:
            return False

        # Look for dialog patterns
        dialog_patterns = [
            r'[A-Z][a-z]+\s*:\s*',  # "Speaker: "
            r'[A-Z]+\s*:\s*',  # "HOST: "
            r'>\s*[A-Z][a-z]+',  # "> Speaker"
        ]

        dialog_matches = 0
        for pattern in dialog_patterns:
            matches = re.findall(pattern, text)
            dialog_matches += len(matches)

        return dialog_matches >= 3

    def _clean_transcript(self, text: str) -> str:
        """Clean and normalize transcript text."""
        if not text:
            return ""

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
        """Calculate confidence score."""
        confidence = 0.6  # Base confidence for Playwright (lower than direct HTML)

        # Content length bonus
        if len(content) > 10000:
            confidence += 0.2
        elif len(content) > 5000:
            confidence += 0.1

        # Title word match
        if episode.title:
            title_words = set(word.lower() for word in re.findall(r'\w+', episode.title) if len(word) > 3)
            content_lower = content.lower()
            matches = sum(1 for word in title_words if word in content_lower)
            if matches >= len(title_words) * 0.5:
                confidence += 0.15

        return min(confidence, 0.95)


def create_resolver() -> PlaywrightResolver:
    """Factory function to create resolver instance."""
    return PlaywrightResolver()
