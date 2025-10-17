"""
RSS feed ingestor for Atlas v4.

Fetches content from RSS/Atom feeds including articles, newsletters, and podcasts.
Supports content extraction, deduplication, and feed type detection.
"""

import feedparser
import requests
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
import re
import logging
from pathlib import Path
import time

from .base import BaseIngestor
from ..core.url_normalizer import is_youtube_url, extract_youtube_video_id


class RSSIngestor(BaseIngestor):
    """
    RSS/Atom feed ingestor.

    Supports:
    - RSS and Atom feeds
    - Content extraction with readability
    - Podcast episodes
    - Newsletter feeds
    - YouTube RSS feeds
    """

    def ingest(self) -> List[Dict[str, Any]]:
        """Ingest content from RSS feeds."""
        items = []
        feeds = self.source_config.get("feeds", [])

        if not feeds:
            self.logger.warning("No feeds configured for RSS ingestor")
            return items

        total_processed = 0

        for feed_config in feeds:
            try:
                feed_url = feed_config.get("url")
                feed_type = feed_config.get("type", "auto")
                feed_name = feed_config.get("name", feed_url)

                if not feed_url:
                    self.logger.warning(f"Feed missing URL: {feed_name}")
                    continue

                self.logger.info(f"Processing RSS feed: {feed_name} ({feed_url})")

                # Parse feed
                feed_data = self._parse_feed(feed_url)
                if not feed_data:
                    continue

                # Detect feed type if auto
                if feed_type == "auto":
                    feed_type = self._detect_feed_type(feed_data)

                # Process entries
                feed_items = self._process_feed_entries(
                    feed_data, feed_type, feed_config
                )
                items.extend(feed_items)
                total_processed += len(feed_items)

                self.logger.info(
                    f"Processed {len(feed_items)} items from {feed_name} "
                    f"(type: {feed_type})"
                )

                # Rate limiting between feeds
                time.sleep(1)

            except Exception as e:
                self.logger.error(
                    f"Failed to process feed {feed_config.get('name', 'unknown')}: {str(e)}"
                )

        self.logger.info(f"RSS ingestion completed: {total_processed} total items")
        return items

    def _parse_feed(self, feed_url: str) -> Optional[Dict[str, Any]]:
        """Parse RSS/Atom feed with proper error handling."""
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; Atlas/4.0; +https://github.com/omar/atlas)"
        }

        try:
            # Parse feed with feedparser
            parsed = feedparser.parse(feed_url, request_headers=headers)

            # Check for feedparser bozo errors
            if parsed.get("bozo", 0) == 1:
                bozo_exception = parsed.get("bozo_exception")
                if bozo_exception:
                    if "not well-formed" in str(bozo_exception).lower():
                        self.logger.error(f"Malformed feed XML: {feed_url}")
                        return None
                    elif "403" in str(bozo_exception) or "forbidden" in str(bozo_exception).lower():
                        self.logger.error(f"Access forbidden (403): {feed_url}")
                        return None
                    elif "404" in str(bozo_exception):
                        self.logger.error(f"Feed not found (404): {feed_url}")
                        return None
                    else:
                        self.logger.warning(f"Feed parsing warning: {feed_url}: {str(bozo_exception)}")

            # Check HTTP status
            status = parsed.get("status")
            if status and status >= 400:
                if status == 404:
                    self.logger.error(f"Feed not found (404): {feed_url}")
                elif status == 403:
                    self.logger.error(f"Access forbidden (403): {feed_url}")
                elif status >= 500:
                    self.logger.error(f"Server error ({status}): {feed_url}")
                return None

            # Validate entries
            if not hasattr(parsed, "entries") or len(parsed.entries) == 0:
                self.logger.warning(f"No entries found in feed: {feed_url}")
                return None

            return parsed

        except Exception as e:
            self.logger.error(f"Failed to parse feed {feed_url}: {str(e)}")
            return None

    def _detect_feed_type(self, feed_data: Dict[str, Any]) -> str:
        """Detect feed type based on content."""
        if not feed_data or not feed_data.entries:
            return "article"

        # Check for YouTube URLs
        youtube_count = 0
        for entry in feed_data.entries:
            url = entry.get("link", "")
            if is_youtube_url(url):
                youtube_count += 1

        if youtube_count > len(feed_data.entries) * 0.7:  # 70% YouTube content
            return "youtube"

        # Check for podcast content (audio enclosures)
        audio_count = 0
        for entry in feed_data.entries:
            if hasattr(entry, "enclosures") and entry.enclosures:
                for enclosure in entry.enclosures:
                    mime_type = enclosure.get("type", "").lower()
                    if mime_type.startswith("audio/"):
                        audio_count += 1
                        break

        if audio_count > len(feed_data.entries) * 0.7:  # 70% audio content
            return "podcast"

        # Check for newsletter indicators
        feed_title = feed_data.feed.get("title", "").lower()
        feed_desc = feed_data.feed.get("description", "").lower()
        newsletter_keywords = ["newsletter", "digest", "daily", "weekly"]

        if any(keyword in feed_title or keyword in feed_desc for keyword in newsletter_keywords):
            return "newsletter"

        # Default to article
        return "article"

    def _process_feed_entries(
        self,
        feed_data: Dict[str, Any],
        feed_type: str,
        feed_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Process feed entries based on feed type."""
        items = []

        for entry in feed_data.entries:
            try:
                # Extract basic entry data
                entry_data = self._extract_entry_data(entry)

                # Skip if doesn't meet basic requirements
                if not self._should_include_entry(entry_data, feed_config):
                    continue

                # Process based on feed type
                if feed_type == "youtube":
                    item = self._process_youtube_entry(entry_data, feed_data.feed)
                elif feed_type == "podcast":
                    item = self._process_podcast_entry(entry_data, feed_data.feed)
                elif feed_type == "newsletter":
                    item = self._process_newsletter_entry(entry_data, feed_data.feed)
                else:  # article
                    item = self._process_article_entry(entry_data, feed_data.feed)

                if item:
                    items.append(item)

            except Exception as e:
                self.logger.error(f"Failed to process entry: {str(e)}")

        return items

    def _extract_entry_data(self, entry) -> Dict[str, Any]:
        """Extract standardized data from feedparser entry."""
        # Handle dates
        published = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                published = datetime(*entry.published_parsed[:6])
            except Exception:
                pass
        elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
            try:
                published = datetime(*entry.updated_parsed[:6])
            except Exception:
                pass

        if not published:
            published = datetime.now()

        # Extract enclosure information
        enclosure_url = None
        enclosure_type = None
        if hasattr(entry, "enclosures") and entry.enclosures:
            enclosure = entry.enclosures[0]
            enclosure_url = enclosure.get("href", "")
            enclosure_type = enclosure.get("type", "")

        return {
            "uid": entry.get("id", entry.get("link", "")),
            "title": entry.get("title", ""),
            "link": entry.get("link", ""),
            "description": entry.get("description", entry.get("summary", "")),
            "content": self._get_entry_content(entry),
            "published": published,
            "author": entry.get("author", ""),
            "tags": self._extract_tags(entry),
            "enclosure_url": enclosure_url,
            "enclosure_type": enclosure_type,
            "duration": entry.get("itunes_duration", ""),
            "image": self._extract_image(entry)
        }

    def _get_entry_content(self, entry) -> str:
        """Extract content from entry."""
        # Try content field first
        if hasattr(entry, "content") and entry.content:
            for content_item in entry.content:
                if content_item.get("type") == "text/html":
                    return content_item.get("value", "")
                elif content_item.get("type") == "text/plain":
                    return content_item.get("value", "")

        # Fallback to description/summary
        description = entry.get("description", "")
        summary = entry.get("summary", "")
        return description or summary or ""

    def _extract_tags(self, entry) -> List[str]:
        """Extract tags from entry."""
        tags = []
        if hasattr(entry, "tags") and entry.tags:
            for tag in entry.tags:
                term = tag.get("term", "")
                if term and isinstance(term, str):
                    tags.append(term)
        return tags

    def _extract_image(self, entry) -> Optional[str]:
        """Extract image URL from entry."""
        # Try various image fields
        if hasattr(entry, "image") and entry.image:
            if isinstance(entry.image, dict):
                return entry.image.get("href", "")
            else:
                return str(entry.image)

        # Look for media thumbnails
        if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
            return entry.media_thumbnail[0].get("url", "")

        return None

    def _should_include_entry(self, entry_data: Dict[str, Any], feed_config: Dict[str, Any]) -> bool:
        """Check if entry should be included based on filters."""
        # Check minimum content length
        content = entry_data.get("content", "")
        min_length = feed_config.get("min_content_length", 100)
        if len(content) < min_length:
            return False

        # Check title
        title = entry_data.get("title", "")
        if not title.strip():
            return False

        # Check age filter
        max_age_days = feed_config.get("max_age_days")
        if max_age_days:
            published = entry_data.get("published")
            if published:
                age_days = (datetime.now() - published).days
                if age_days > max_age_days:
                    return False

        return True

    def _process_youtube_entry(self, entry_data: Dict[str, Any], feed_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process YouTube RSS entry."""
        url = entry_data.get("link", "")
        if not is_youtube_url(url):
            return None

        video_id = extract_youtube_video_id(url)
        if not video_id:
            return None

        # Create content
        content = f"# {entry_data['title']}\n\n"
        content += f"**Channel:** {feed_info.get('title', 'Unknown')}\n"
        content += f"**Duration:** {entry_data['duration']} seconds\n"
        content += f"**Published:** {entry_data['published'].strftime('%Y-%m-%d')}\n\n"

        if entry_data.get("description"):
            content += f"## Description\n\n{entry_data['description']}\n\n"

        content += f"**Video URL:** {url}\n"
        content += f"**Video ID:** {video_id}\n"

        return self._create_base_item(
            title=entry_data["title"],
            content=content,
            url=url,
            author=feed_info.get("title", "Unknown"),
            date=entry_data["published"],
            guid=entry_data["uid"],
            tags=["youtube", "video"] + entry_data["tags"],
            video_id=video_id,
            duration=entry_data["duration"],
            channel=feed_info.get("title", "Unknown")
        )

    def _process_podcast_entry(self, entry_data: Dict[str, Any], feed_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process podcast RSS entry."""
        content = f"# {entry_data['title']}\n\n"
        content += f"**Podcast:** {feed_info.get('title', 'Unknown')}\n"
        content += f"**Published:** {entry_data['published'].strftime('%Y-%m-%d')}\n"
        content += f"**Duration:** {entry_data['duration']} seconds\n\n"

        if entry_data.get("description"):
            content += f"## Description\n\n{entry_data['description']}\n\n"

        if entry_data.get("enclosure_url"):
            content += f"**Audio URL:** {entry_data['enclosure_url']}\n"

        return self._create_base_item(
            title=entry_data["title"],
            content=content,
            url=entry_data["link"],
            author=feed_info.get("title", "Unknown"),
            date=entry_data["published"],
            guid=entry_data["uid"],
            tags=["podcast", "episode"] + entry_data["tags"],
            audio_url=entry_data.get("enclosure_url"),
            duration=entry_data["duration"],
            podcast=feed_info.get("title", "Unknown")
        )

    def _process_newsletter_entry(self, entry_data: Dict[str, Any], feed_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process newsletter RSS entry."""
        # Use description as main content
        content = entry_data.get("description", entry_data.get("content", ""))
        if not content:
            return None

        # Add newsletter header
        header = f"# {entry_data['title']}\n\n"
        header += f"**Source:** {feed_info.get('title', 'Unknown Newsletter')}\n"
        header += f"**Published:** {entry_data['published'].strftime('%Y-%m-%d')}\n\n"

        content = header + content

        return self._create_base_item(
            title=entry_data["title"],
            content=content,
            url=entry_data["link"],
            author=entry_data.get("author") or feed_info.get("title", "Unknown"),
            date=entry_data["published"],
            guid=entry_data["uid"],
            tags=["newsletter", "digest"] + entry_data["tags"],
            newsletter=feed_info.get("title", "Unknown")
        )

    def _process_article_entry(self, entry_data: Dict[str, Any], feed_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process article RSS entry."""
        # Try to fetch full article content
        content = self._fetch_article_content(entry_data["link"])

        if not content:
            # Fallback to description
            content = entry_data.get("description", entry_data.get("content", ""))

        if not content:
            return None

        # Add article header
        header = f"# {entry_data['title']}\n\n"
        if entry_data.get("author"):
            header += f"**Author:** {entry_data['author']}\n"
        header += f"**Published:** {entry_data['published'].strftime('%Y-%m-%d')}\n"
        header += f"**Source:** {feed_info.get('title', 'Unknown')}\n\n"

        content = header + content

        return self._create_base_item(
            title=entry_data["title"],
            content=content,
            url=entry_data["link"],
            author=entry_data.get("author"),
            date=entry_data["published"],
            guid=entry_data["uid"],
            tags=["article", "rss"] + entry_data["tags"]
        )

    def _fetch_article_content(self, url: str) -> Optional[str]:
        """Fetch full article content using readability."""
        try:
            from readability import Document
            import requests

            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; Atlas/4.0; +https://github.com/omar/atlas)"
            }

            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            doc = Document(response.content)
            return doc.summary()

        except Exception as e:
            self.logger.debug(f"Failed to fetch full article content from {url}: {str(e)}")
            return None

    def _standardize_item(self, raw_item: Dict[str, Any]) -> Dict[str, Any]:
        """Standardize RSS item to Atlas format."""
        return raw_item  # RSS items are already standardized in processing methods

    @classmethod
    def get_required_config_keys(cls) -> List[str]:
        """Get required configuration keys for RSS ingestor."""
        return ['name', 'type'] + BaseIngestor.get_required_config_keys()

    @classmethod
    def get_optional_config_keys(cls) -> List[str]:
        """Get optional configuration keys for RSS ingestor."""
        return [
            'feeds',      # List of feed configurations
            'validation'  # Validation rules
        ] + BaseIngestor.get_optional_config_keys()


# Standalone execution support
def main():
    """Run RSS ingestor as standalone script."""
    import sys
    import os
    from pathlib import Path

    # Add src to path for standalone execution
    src_path = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(src_path))

    from atlas.config import load_config
    from atlas.logging import setup_logging

    # Setup logging
    setup_logging(level="INFO", enable_console=True)

    # Load configuration
    config_path = os.getenv("ATLAS_CONFIG", "config/sources/rss_feeds.yaml")
    try:
        config = load_config(config_path)
    except Exception as e:
        print(f"Failed to load configuration: {e}")
        return 1

    # Run ingestor
    try:
        ingestor = RSSIngestor(config)
        result = ingestor.run()

        print(f"RSS ingestion completed:")
        print(f"  Success: {result.success}")
        print(f"  Items processed: {result.items_processed}")
        print(f"  Errors: {len(result.errors)}")

        if result.errors:
            print("\nErrors:")
            for error in result.errors:
                print(f"  - {error}")

        return 0 if result.success else 1

    except Exception as e:
        print(f"RSS ingestion failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())