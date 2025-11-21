#!/usr/bin/env python3
"""
RSS Link Resolver

Discovers transcript URLs directly from RSS feed links and metadata.
"""

import logging
from typing import List, Dict, Any
from urllib.parse import urljoin, urlparse
import re

from modules.podcasts.store import Episode

logger = logging.getLogger(__name__)


class RSSLinkResolver:
    """Resolver that finds transcript links directly in RSS feeds"""

    def __init__(self, user_agent: str = "Atlas-Pod/1.0", timeout: int = 30):
        self.user_agent = user_agent
        self.timeout = timeout

    def resolve(
        self, episode: Episode, podcast_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Find transcript sources from RSS metadata

        Returns list of transcript sources with:
        - url: transcript URL
        - confidence: 0.0-1.0 confidence score
        - resolver: 'rss_link'
        - metadata: additional info
        """
        sources = []

        try:
            # Check episode metadata for transcript links
            metadata = episode.metadata or {}
            transcript_links = metadata.get("transcript_links", [])

            if transcript_links:
                for link in transcript_links:
                    confidence = self._calculate_confidence(link, episode)

                    sources.append(
                        {
                            "url": link,
                            "confidence": confidence,
                            "resolver": "rss_link",
                            "metadata": {
                                "source": "rss_feed",
                                "episode_title": episode.title,
                                "found_in": "rss_transcript_links",
                            },
                        }
                    )

            # Also check episode description for transcript URLs
            description = metadata.get("description", "")
            if description:
                description_links = self._extract_transcript_urls_from_text(
                    description, episode.url
                )

                for link in description_links:
                    # Avoid duplicates
                    if not any(s["url"] == link for s in sources):
                        confidence = self._calculate_confidence(link, episode)

                        sources.append(
                            {
                                "url": link,
                                "confidence": confidence,
                                "resolver": "rss_link",
                                "metadata": {
                                    "source": "rss_description",
                                    "episode_title": episode.title,
                                    "found_in": "episode_description",
                                },
                            }
                        )

            logger.info(
                f"RSS resolver found {len(sources)} transcript sources for: {episode.title}"
            )

        except Exception as e:
            logger.error(f"Error in RSS resolver for episode {episode.title}: {e}")

        return sources

    def _calculate_confidence(self, url: str, episode: Episode) -> float:
        """Calculate confidence score for transcript URL"""
        confidence = 0.0
        url_lower = url.lower()

        # High confidence indicators
        if "transcript" in url_lower:
            confidence += 0.8
        elif "transcription" in url_lower:
            confidence += 0.7
        elif "full-text" in url_lower:
            confidence += 0.6

        # Medium confidence indicators
        if any(word in url_lower for word in ["show-notes", "episode-text", "text"]):
            confidence += 0.4

        # Episode-specific URL
        if episode.guid and episode.guid in url:
            confidence += 0.2
        elif any(word in url_lower for word in ["episode", "ep-"]):
            confidence += 0.2

        # Domain reputation boost
        domain = urlparse(url).netloc.lower()
        if any(
            trusted in domain
            for trusted in ["rev.com", "otter.ai", "transcript.com", "transcripts.com"]
        ):
            confidence += 0.3

        return min(confidence, 1.0)

    def _extract_transcript_urls_from_text(self, text: str, base_url: str) -> List[str]:
        """Extract transcript URLs from text content"""
        urls = []

        # Look for URLs with transcript-related keywords
        url_pattern = r'https?://[^\s<>"\']+(?:transcript|transcription|show-notes|full-text)[^\s<>"\']*'
        matches = re.findall(url_pattern, text, re.IGNORECASE)

        for match in matches:
            # Clean up URL (remove trailing punctuation)
            url = match.rstrip(".,;)")
            if self._is_valid_url(url):
                urls.append(url)

        # Look for "transcript:" or "read transcript:" followed by URL
        transcript_pattern = r'(?:transcript|read\s+transcript|full\s+transcript)[:\s]*(?:<a[^>]*href=["\']([^"\']+)["\'][^>]*>|https?://[^\s<>"\']+)'
        matches = re.findall(transcript_pattern, text, re.IGNORECASE)

        for match in matches:
            if match:
                url = urljoin(base_url, match) if match.startswith("/") else match
                if self._is_valid_url(url):
                    urls.append(url)

        # NEW: Look for HTML href links with transcript-related text
        href_pattern = r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>([^<]*(?:transcript|transcription|full\s+transcript)[^<]*)</a>'
        href_matches = re.findall(href_pattern, text, re.IGNORECASE)

        for url, link_text in href_matches:
            # Clean up URL and convert relative to absolute
            url = url.strip()
            if url.startswith("/"):
                url = urljoin(base_url, url)
            elif url.startswith("http"):
                pass  # Already absolute
            else:
                continue  # Skip invalid URLs

            if self._is_valid_url(url):
                urls.append(url)
                logger.debug(
                    f"Found transcript link in HTML: {url} (text: '{link_text.strip()}')"
                )

        return list(set(urls))  # Remove duplicates

    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid"""
        try:
            result = urlparse(url)
            return bool(result.scheme and result.netloc)
        except Exception:
            return False
