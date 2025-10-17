#!/usr/bin/env python3
"""
Podcast configuration and matching utilities.
Handles slug creation, mapping configuration, and URL pattern matching.
"""

import re
import yaml
import logging
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def create_slug(name: str) -> str:
    """Create URL-safe slug from podcast name"""
    # Convert to lowercase and replace spaces/special chars with hyphens
    slug = re.sub(r"[^\w\s-]", "", name.lower())
    slug = re.sub(r"[-\s]+", "-", slug)
    slug = slug.strip("-")

    # Handle special cases
    slug_map = {
        "conversations-with-tyler": "conversations-with-tyler",
        "acquired": "acquired",
        "acq2-by-acquired": "acq2-by-acquired",
        "sharp-tech-with-ben-thompson": "sharp-tech",
        "stratechery": "stratechery",
        "political-gabfest": "political-gabfest",
        "the-ezra-klein-show": "ezra-klein-show",
        "planet-money": "planet-money",
        "radiolab": "radiolab",
        "hard-fork": "hard-fork",
    }

    return slug_map.get(slug, slug)


def load_mapping_config(config_path: str) -> Dict[str, Any]:
    """Load podcast mapping configuration from YAML"""
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        logger.info(f"Loaded mapping config for {len(config)} podcasts")
        return config or {}

    except FileNotFoundError:
        logger.warning(f"Mapping config not found: {config_path}")
        return {}
    except Exception as e:
        logger.error(f"Error loading mapping config: {e}")
        return {}


class URLMatcher:
    """URL pattern matching for transcript detection"""

    def __init__(self):
        # Common transcript URL patterns
        self.transcript_patterns = [
            r"transcript",
            r"transcription",
            r"full-text",
            r"show-notes",
            r"episode-text",
            r"/text/",
            r"/transcript/",
            r"/transcripts/",
        ]

        # Site-specific patterns
        self.site_patterns = {
            "slate.com": [
                r"/podcasts/[^/]+/\d{4}/\d{2}/[^/]+\.html",
                r"/transcripts?/",
            ],
            "conversationswithtyler.com": [
                r"/episodes/[^/]+",
                r"/transcript",
            ],
            "acquired.fm": [
                r"/episodes/[^/]+",
            ],
            "stratechery.com": [
                r"/\d{4}/[^/]+",
                r"/premium-posts/",
            ],
        }

    def is_transcript_url(self, url: str, podcast_slug: str = "") -> float:
        """Check if URL likely contains transcript content (0.0-1.0 confidence)"""
        if not url:
            return 0.0

        url_lower = url.lower()
        confidence = 0.0

        # Check general transcript patterns
        for pattern in self.transcript_patterns:
            if re.search(pattern, url_lower):
                confidence += 0.3

        # Check for episode-specific patterns
        if any(word in url_lower for word in ["episode", "ep-", "show"]):
            confidence += 0.2

        # Site-specific boosting
        domain = urlparse(url).netloc.lower()
        if domain in self.site_patterns:
            for pattern in self.site_patterns[domain]:
                if re.search(pattern, url_lower):
                    confidence += 0.4
                    break

        # Boost for known transcript domains
        if any(
            domain.endswith(d) for d in ["transcript.com", "transcripts.com", "rev.com"]
        ):
            confidence += 0.5

        return min(confidence, 1.0)

    def extract_episode_links(
        self, html: str, base_url: str, episode_selector: str = ""
    ) -> List[str]:
        """Extract episode links from HTML using CSS selector"""
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "html.parser")
            links = []

            if episode_selector:
                # Use custom selector
                elements = soup.select(episode_selector)
                for element in elements:
                    href = element.get("href")
                    if href:
                        links.append(self._resolve_url(href, base_url))
            else:
                # Default: look for common episode link patterns
                for link in soup.find_all("a", href=True):
                    href = link.get("href")
                    text = link.get_text().lower()

                    # Check if link looks like an episode
                    if any(word in text for word in ["episode", "ep ", "listen"]):
                        links.append(self._resolve_url(href, base_url))
                    elif any(
                        word in href.lower()
                        for word in ["episode", "ep-", "/episodes/"]
                    ):
                        links.append(self._resolve_url(href, base_url))

            return list(set(links))  # Remove duplicates

        except ImportError:
            logger.error("BeautifulSoup not available for HTML parsing")
            return []
        except Exception as e:
            logger.error(f"Error extracting episode links: {e}")
            return []

    def extract_transcript_content(
        self, html: str, transcript_selector: str = ""
    ) -> Optional[str]:
        """Extract transcript text from HTML"""
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "html.parser")

            if transcript_selector:
                # Use custom selector
                element = soup.select_one(transcript_selector)
                if element:
                    return element.get_text(strip=True)
            else:
                # Default: look for common transcript containers
                selectors = [
                    'section[data-component="Transcript"]',
                    ".transcript",
                    ".episode-transcript",
                    ".show-transcript",
                    "#transcript",
                    'div[class*="transcript"]',
                    'article[class*="transcript"]',
                ]

                for selector in selectors:
                    element = soup.select_one(selector)
                    if element:
                        text = element.get_text(strip=True)
                        if len(text) > 100:  # Reasonable minimum length
                            return text

            return None

        except ImportError:
            logger.error("BeautifulSoup not available for HTML parsing")
            return None
        except Exception as e:
            logger.error(f"Error extracting transcript content: {e}")
            return None

    def _resolve_url(self, url: str, base_url: str) -> str:
        """Resolve relative URLs against base URL"""
        from urllib.parse import urljoin

        try:
            return urljoin(base_url, url)
        except Exception:
            return url


class PodcastMatcher:
    """Match podcast configurations with discovered content"""

    def __init__(self, mapping_config: Dict[str, Any] = None):
        self.mapping_config = mapping_config or {}
        self.url_matcher = URLMatcher()

    def get_podcast_config(self, slug: str) -> Dict[str, Any]:
        """Get configuration for podcast slug"""
        return self.mapping_config.get(slug, {})

    def should_process_url(self, url: str, podcast_slug: str) -> bool:
        """Check if URL should be processed for transcripts"""
        # Skip if URL looks like media file
        if any(url.lower().endswith(ext) for ext in [".mp3", ".mp4", ".wav", ".m4a"]):
            return False

        # Skip if URL looks like RSS/XML
        if any(word in url.lower() for word in ["rss", ".xml", "feed"]):
            return False

        # Check confidence score
        confidence = self.url_matcher.is_transcript_url(url, podcast_slug)
        return confidence > 0.3

    def rank_transcript_candidates(
        self, urls: List[str], podcast_slug: str
    ) -> List[tuple]:
        """Rank URLs by transcript likelihood"""
        candidates = []

        for url in urls:
            confidence = self.url_matcher.is_transcript_url(url, podcast_slug)
            if confidence > 0:
                candidates.append((url, confidence))

        # Sort by confidence (highest first)
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates
