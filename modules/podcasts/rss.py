#!/usr/bin/env python3
"""
RSS feed parser for podcast discovery.
Extracts episodes and metadata from podcast RSS feeds.
"""

import feedparser
import logging
from datetime import datetime
from typing import List, Optional
from urllib.parse import urljoin, urlparse
import requests
from dataclasses import dataclass


@dataclass
class RSSEpisode:
    """Episode data from RSS feed"""

    guid: str
    title: str
    url: str
    publish_date: Optional[datetime] = None
    description: str = ""
    duration: Optional[str] = None
    audio_url: Optional[str] = None
    transcript_links: List[str] = None

    def __post_init__(self):
        if self.transcript_links is None:
            self.transcript_links = []


class RSSParser:
    """RSS feed parser for podcast episodes"""

    def __init__(self, user_agent: str = "Atlas-Pod/1.0"):
        self.user_agent = user_agent
        self.logger = logging.getLogger(__name__)

    def parse_feed(self, rss_url: str) -> List[RSSEpisode]:
        """Parse RSS feed and extract episodes"""
        try:
            # Fetch feed with custom user agent
            headers = {"User-Agent": self.user_agent}
            response = requests.get(rss_url, headers=headers, timeout=30)
            response.raise_for_status()

            # Parse with feedparser
            feed = feedparser.parse(response.content)

            if not feed.entries:
                self.logger.warning(f"No entries found in feed: {rss_url}")
                return []

            episodes = []
            for entry in feed.entries:
                episode = self._parse_entry(entry, rss_url)
                if episode:
                    episodes.append(episode)

            self.logger.info(f"Parsed {len(episodes)} episodes from {rss_url}")
            return episodes

        except Exception as e:
            self.logger.error(f"Failed to parse RSS feed {rss_url}: {e}")
            return []

    def _parse_entry(self, entry, base_url: str) -> Optional[RSSEpisode]:
        """Parse individual RSS entry into episode"""
        try:
            # Extract basic info
            guid = entry.get("guid", entry.get("id", ""))
            title = entry.get("title", "")

            # Get episode URL - prioritize episode-specific links over generic feed link
            url = self._extract_episode_url(entry, base_url)

            if not guid or not title:
                self.logger.warning(f"Skipping entry without guid/title: {entry}")
                return None

            # Parse publish date
            publish_date = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                try:
                    publish_date = datetime(*entry.published_parsed[:6])
                except (TypeError, ValueError):
                    pass

            # Extract description
            description = entry.get("description", "") or entry.get("summary", "")

            # Extract duration
            duration = None
            if hasattr(entry, "itunes_duration"):
                duration = entry.itunes_duration
            elif hasattr(entry, "duration"):
                duration = entry.duration

            # Extract audio URL
            audio_url = None
            if hasattr(entry, "enclosures") and entry.enclosures:
                for enclosure in entry.enclosures:
                    if enclosure.get("type", "").startswith("audio"):
                        audio_url = enclosure.get("href")
                        break

            # Look for transcript links in description and links
            transcript_links = self._extract_transcript_links(
                entry, description, base_url
            )

            return RSSEpisode(
                guid=guid,
                title=title,
                url=url,
                publish_date=publish_date,
                description=description,
                duration=duration,
                audio_url=audio_url,
                transcript_links=transcript_links,
            )

        except Exception as e:
            self.logger.error(f"Error parsing RSS entry: {e}")
            return None

    def _extract_episode_url(self, entry, base_url: str) -> str:
        """
        Extract the best episode-specific URL from an RSS entry.

        Priority order:
        1. Entry 'link' if it looks episode-specific (has path segments)
        2. 'alternate' link from links array
        3. Page URL from enclosure/media
        4. GUID if it's a URL
        5. Fallback to base_url (worst case)
        """
        # 1. Check the main link - but verify it's not just the homepage
        main_link = entry.get("link", "")
        if main_link and self._is_episode_specific_url(main_link, base_url):
            return main_link

        # 2. Check links array for 'alternate' type (common in Atom feeds)
        if hasattr(entry, "links"):
            for link in entry.links:
                href = link.get("href", "")
                rel = link.get("rel", "")
                link_type = link.get("type", "")

                # Prefer alternate/html links that look episode-specific
                if rel == "alternate" or "html" in link_type:
                    if href and self._is_episode_specific_url(href, base_url):
                        return href

                # Some feeds put episode page in a 'via' or 'related' link
                if rel in ("via", "related") and href:
                    if self._is_episode_specific_url(href, base_url):
                        return href

        # 3. Check for website URL in content/itunes extensions
        for attr in ["itunes_episode_url", "content_url", "feedburner_origlink"]:
            if hasattr(entry, attr):
                url = getattr(entry, attr)
                if url and self._is_episode_specific_url(url, base_url):
                    return url

        # 4. Check if GUID is a usable URL (many podcasts use episode URL as GUID)
        guid = entry.get("guid", entry.get("id", ""))
        if guid and guid.startswith("http") and self._is_episode_specific_url(guid, base_url):
            # Make sure it's not an audio file URL
            if not any(ext in guid.lower() for ext in [".mp3", ".m4a", ".wav", ".ogg"]):
                return guid

        # 5. Return main link even if generic (better than nothing)
        if main_link:
            return main_link

        # 6. Last resort: base URL
        return base_url

    def _is_episode_specific_url(self, url: str, base_url: str) -> bool:
        """Check if a URL appears to be episode-specific vs just a homepage"""
        if not url:
            return False

        try:
            parsed = urlparse(url)
            base_parsed = urlparse(base_url)

            # If it's a different domain entirely, consider it specific
            if parsed.netloc and parsed.netloc != base_parsed.netloc:
                return True

            # Check path depth - episode URLs usually have path segments
            path = parsed.path.strip("/")
            if not path:
                return False  # Just homepage

            # Count path segments
            segments = [s for s in path.split("/") if s]

            # Single segment like "/episodes" is probably a list page, not an episode
            # But "/episodes/123" or "/2024/episode-title" is likely an episode
            if len(segments) >= 2:
                return True

            # Single segment that looks like an episode identifier
            if len(segments) == 1:
                segment = segments[0]
                # Numeric IDs, slugs with hyphens, etc.
                if any([
                    segment.isdigit(),  # /123
                    "-" in segment and len(segment) > 10,  # /my-episode-title
                    "_" in segment,  # /my_episode
                    len(segment) > 20,  # Long slugs are usually episodes
                ]):
                    return True

            return False

        except Exception:
            return False

    def _extract_transcript_links(
        self, entry, description: str, base_url: str
    ) -> List[str]:
        """Extract potential transcript links from RSS entry"""
        transcript_links = []

        # Common transcript link patterns
        transcript_keywords = [
            "transcript",
            "transcription",
            "full text",
            "show notes",
            "read the transcript",
            "episode transcript",
        ]

        # Check entry links
        if hasattr(entry, "links"):
            for link in entry.links:
                href = link.get("href", "")
                rel = link.get("rel", "")
                title = link.get("title", "").lower()

                # Look for transcript-related links
                if any(keyword in title for keyword in transcript_keywords):
                    transcript_links.append(self._resolve_url(href, base_url))
                elif "transcript" in href.lower():
                    transcript_links.append(self._resolve_url(href, base_url))

        # Parse description for transcript links
        if description:
            import re

            # Look for URLs in description that might be transcripts
            url_pattern = r'https?://[^\s<>"\']+(?:transcript|transcription)[^\s<>"\']*'
            urls = re.findall(url_pattern, description, re.IGNORECASE)
            for url in urls:
                transcript_links.append(url.rstrip(".,;)"))

            # Look for "transcript" followed by a link
            transcript_link_pattern = r'transcript[:\s]*(?:<a[^>]*href=["\']([^"\']+)["\'][^>]*>|https?://[^\s<>"\']+)'
            matches = re.findall(transcript_link_pattern, description, re.IGNORECASE)
            for match in matches:
                if match:
                    transcript_links.append(self._resolve_url(match, base_url))

        # Remove duplicates and filter valid URLs
        unique_links = []
        for link in transcript_links:
            if link and link not in unique_links and self._is_valid_url(link):
                unique_links.append(link)

        return unique_links

    def _resolve_url(self, url: str, base_url: str) -> str:
        """Resolve relative URLs against base URL"""
        if not url:
            return ""
        try:
            return urljoin(base_url, url)
        except Exception:
            return url

    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid"""
        try:
            result = urlparse(url)
            return bool(result.scheme and result.netloc)
        except Exception:
            return False
