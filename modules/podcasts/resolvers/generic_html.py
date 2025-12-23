#!/usr/bin/env python3
"""
Generic HTML Resolver

Fetches episode pages and extracts transcript content using CSS selectors
and pattern matching.

Supports cookie-based authentication for paywalled sites like Stratechery.
"""

import logging
import requests
import time
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
import re

from modules.podcasts.store import Episode

logger = logging.getLogger(__name__)

# Cookie files for authenticated access (domain -> cookie file path)
COOKIE_FILES = {
    "stratechery.com": Path.home() / ".config/atlas/stratechery_cookies.json",
}


def load_cookies_for_domain(domain: str) -> Optional[Dict[str, str]]:
    """Load cookies for a specific domain from config file"""
    # Find matching cookie file
    cookie_file = None
    for cookie_domain, path in COOKIE_FILES.items():
        if cookie_domain in domain:
            cookie_file = path
            break

    if not cookie_file or not cookie_file.exists():
        return None

    try:
        with open(cookie_file) as f:
            cookies_list = json.load(f)

        # Convert to dict format for requests
        cookies = {}
        for c in cookies_list:
            cookies[c['name']] = c['value']

        logger.debug(f"Loaded {len(cookies)} cookies for {domain}")
        return cookies
    except Exception as e:
        logger.warning(f"Failed to load cookies for {domain}: {e}")
        return None


class GenericHTMLResolver:
    """Resolver that extracts transcripts from HTML pages"""

    name = "generic_html"

    def __init__(self, user_agent: str = "Atlas-Pod/1.0", timeout: int = 30):
        self.user_agent = user_agent
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent})

    def resolve(
        self, episode: Episode, podcast_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Find and extract transcript content from episode HTML pages

        Returns list of transcript sources with:
        - url: source URL
        - confidence: 0.0-1.0 confidence score
        - resolver: 'generic_html'
        - metadata: additional info including extracted content
        """
        sources = []

        try:
            # Get rate limiting config
            rate_limit = podcast_config.get("config", {}).get("rate_limit", 2.0)
            time.sleep(rate_limit)

            # Start with episode URL if available
            urls_to_check = []
            if episode.url:
                urls_to_check.append(episode.url)

            # Add any transcript URLs from metadata
            metadata = episode.metadata or {}
            transcript_links = metadata.get("transcript_links", [])
            urls_to_check.extend(transcript_links)

            # Check each URL for transcript content
            for url in urls_to_check:
                try:
                    transcript_sources = self._extract_from_url(
                        url, episode, podcast_config
                    )
                    sources.extend(transcript_sources)

                except Exception as e:
                    logger.error(f"Error extracting from {url}: {e}")

            logger.info(
                f"HTML resolver found {len(sources)} transcript sources for: {episode.title}"
            )

        except Exception as e:
            logger.error(f"Error in HTML resolver for episode {episode.title}: {e}")

        return sources

    def _extract_from_url(
        self, url: str, episode: Episode, podcast_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Extract transcript content from a specific URL"""
        sources = []

        try:
            # Check for domain-specific cookies (for paywalled sites)
            # Skip cookies if URL already has access_token (Passport auth)
            # Using both causes redirect loops
            domain = urlparse(url).netloc
            if "access_token=" in url:
                cookies = None
                logger.debug(f"URL has access_token, skipping cookies for {domain}")
            else:
                cookies = load_cookies_for_domain(domain)

            # Fetch page content with optional authentication
            response = self.session.get(url, timeout=self.timeout, cookies=cookies)
            response.raise_for_status()

            html = response.text

            # Try to extract transcript using configured selector
            transcript_selector = podcast_config.get("transcript_selector", "")
            transcript_content = None

            if transcript_selector:
                transcript_content = self._extract_with_selector(
                    html, transcript_selector
                )

            # Fallback to generic extraction
            if not transcript_content:
                transcript_content = self._extract_generic(html)

            if transcript_content:
                confidence = self._calculate_confidence(
                    url, transcript_content, episode
                )

                if confidence > 0.3:  # Only include if reasonably confident
                    sources.append(
                        {
                            "url": url,
                            "confidence": confidence,
                            "resolver": "generic_html",
                            "metadata": {
                                "content": transcript_content,
                                "content_length": len(transcript_content),
                                "episode_title": episode.title,
                                "extraction_method": (
                                    "css_selector" if transcript_selector else "generic"
                                ),
                                "selector_used": transcript_selector,
                            },
                        }
                    )

            # DISABLED: Link following was causing infinite loops chasing
            # Wikipedia/encyclopedia links containing "transcript" in the text.
            # The podcasts we care about have transcripts directly on the page.
            # If we need link following later, add strict domain whitelisting.
            #
            # additional_links = self._find_transcript_links(html, url)
            # for link in additional_links:
            #     if link != url:
            #         nested_sources = self._extract_from_url(link, episode, podcast_config)
            #         sources.extend(nested_sources)

        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to fetch {url}: {e}")
        except Exception as e:
            logger.error(f"Error extracting from {url}: {e}")

        return sources

    def _extract_with_selector(self, html: str, selector: str) -> Optional[str]:
        """Extract content using CSS selector"""
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "html.parser")

            # Handle multiple selectors separated by comma
            selectors = [s.strip() for s in selector.split(",")]

            for sel in selectors:
                element = soup.select_one(sel)
                if element:
                    text = element.get_text(separator="\n", strip=True)
                    if len(text) > 100:  # Minimum length check
                        return text

        except ImportError:
            logger.error("BeautifulSoup not available for HTML parsing")
        except Exception as e:
            logger.error(f"Error extracting with selector '{selector}': {e}")

        return None

    def _extract_generic(self, html: str) -> Optional[str]:
        """Generic transcript extraction using common patterns"""
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "html.parser")

            # Common transcript container selectors
            selectors = [
                'section[data-component="Transcript"]',
                ".transcript",
                ".episode-transcript",
                ".show-transcript",
                ".full-transcript",
                "#transcript",
                'div[class*="transcript"]',
                'article[class*="transcript"]',
                ".story-text",
                ".episode-content",
                ".post-content",
                ".entry-content",
                ".StoryBodyCompanionColumn",
                ".ArticleBody",
            ]

            for selector in selectors:
                element = soup.select_one(selector)
                if element:
                    text = element.get_text(separator="\n", strip=True)
                    if len(text) > 200:  # Reasonable minimum for transcript
                        return text

            # Look for text blocks that might be transcripts
            # (large blocks of text, dialog patterns, etc.)
            text_blocks = soup.find_all(
                ["div", "section", "article"], text=lambda t: t and len(t) > 500
            )

            for block in text_blocks:
                text = block.get_text(separator="\n", strip=True)

                # Check if text looks like a transcript
                if self._looks_like_transcript(text):
                    return text

        except ImportError:
            logger.error("BeautifulSoup not available for HTML parsing")
        except Exception as e:
            logger.error(f"Error in generic extraction: {e}")

        return None

    def _looks_like_transcript(self, text: str) -> bool:
        """Check if text looks like a transcript"""
        if len(text) < 500:
            return False

        # Look for dialog patterns
        dialog_patterns = [
            r"[A-Z][a-z]+\s*:\s*",  # "Speaker: "
            r"[A-Z]+\s*:\s*",  # "HOST: "
            r">\s*[A-Z][a-z]+",  # "> Speaker"
        ]

        dialog_matches = 0
        for pattern in dialog_patterns:
            matches = re.findall(pattern, text)
            dialog_matches += len(matches)

        # Should have multiple speaker transitions
        if dialog_matches < 3:
            return False

        # Check for transcript-like keywords
        transcript_keywords = [
            "transcript",
            "interview",
            "conversation",
            "discussion",
            "host",
            "guest",
            "speaker",
            "moderator",
        ]

        keyword_count = sum(
            1 for keyword in transcript_keywords if keyword.lower() in text.lower()
        )

        return keyword_count >= 2

    def _find_transcript_links(self, html: str, base_url: str) -> List[str]:
        """Find transcript links within HTML content"""
        links = []

        # Domains to skip (share buttons, social media, login pages)
        skip_domains = [
            'linkedin.com', 'facebook.com', 'twitter.com', 'x.com',
            'tumblr.com', 'pinterest.com', 'reddit.com', 'instagram.com',
            'mailto:', 'tel:', 'javascript:', 'tg://', '#'
        ]

        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "html.parser")

            # Look for links with transcript-related text or URLs
            for link in soup.find_all("a", href=True):
                href = link.get("href")
                text = link.get_text().lower()

                # Skip share/social links
                if any(skip in href.lower() for skip in skip_domains):
                    continue

                # Skip login/signup/share URLs
                if any(word in href.lower() for word in ['login', 'signup', 'signin', 'share', 'auth']):
                    continue

                # Check link text
                if any(
                    word in text
                    for word in [
                        "transcript",
                        "transcription",
                        "full text",
                        "view transcript",
                        "episode transcript",
                    ]
                ):
                    full_url = urljoin(base_url, href)
                    links.append(full_url)

                # Check URL path
                elif any(
                    word in href.lower()
                    for word in ["transcript", "transcription", "full-text"]
                ):
                    full_url = urljoin(base_url, href)
                    links.append(full_url)

        except ImportError:
            logger.error("BeautifulSoup not available for link extraction")
        except Exception as e:
            logger.error(f"Error finding transcript links: {e}")

        return list(set(links))[:5]  # Remove duplicates, limit to 5 links max

    def _calculate_confidence(self, url: str, content: str, episode: Episode) -> float:
        """Calculate confidence score for extracted content"""
        confidence = 0.0

        # Content length score
        if len(content) > 5000:
            confidence += 0.4
        elif len(content) > 2000:
            confidence += 0.3
        elif len(content) > 500:
            confidence += 0.2

        # Dialog pattern score
        dialog_patterns = [r"[A-Z][a-z]+\s*:\s*", r"[A-Z]+\s*:\s*", r">\s*[A-Z][a-z]+"]

        total_dialog_matches = 0
        for pattern in dialog_patterns:
            matches = re.findall(pattern, content)
            total_dialog_matches += len(matches)

        if total_dialog_matches > 20:
            confidence += 0.3
        elif total_dialog_matches > 10:
            confidence += 0.2
        elif total_dialog_matches > 5:
            confidence += 0.1

        # URL quality score
        url_lower = url.lower()
        if "transcript" in url_lower:
            confidence += 0.2
        elif any(word in url_lower for word in ["episode", "show"]):
            confidence += 0.1

        # Episode title matching
        if episode.title:
            title_words = episode.title.lower().split()
            content_lower = content.lower()

            title_word_matches = sum(
                1 for word in title_words if len(word) > 3 and word in content_lower
            )

            if title_word_matches >= len(title_words) * 0.5:
                confidence += 0.2

        return min(confidence, 1.0)
