"""
Show Notes Extractor - Extract links from podcast episode descriptions (RSS).

Reads episode metadata from the podcast database and extracts links from
the description field (show notes). No HTTP requests - uses cached RSS data.
"""

import sqlite3
import logging
import html
import re
from pathlib import Path
from typing import List, Dict, Optional, Generator
from html.parser import HTMLParser

from modules.links.extractor import LinkExtractor
from modules.links.models import LinkSource

logger = logging.getLogger(__name__)

PODCAST_DB_PATH = Path('data/podcasts/atlas_podcasts.db')
LINK_DB_PATH = Path('data/enrich/link_queue.db')


class HTMLTextExtractor(HTMLParser):
    """Extract text and links from HTML."""

    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.links = []  # (url, anchor_text)
        self._current_link = None
        self._current_anchor = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            attrs_dict = dict(attrs)
            href = attrs_dict.get('href', '')
            if href and href.startswith('http'):
                self._current_link = href
                self._current_anchor = []

    def handle_endtag(self, tag):
        if tag == 'a' and self._current_link:
            anchor = ''.join(self._current_anchor).strip()
            self.links.append((self._current_link, anchor))
            self._current_link = None
            self._current_anchor = []

    def handle_data(self, data):
        self.text_parts.append(data)
        if self._current_link is not None:
            self._current_anchor.append(data)

    def get_text(self) -> str:
        return ' '.join(self.text_parts)

    def get_links(self) -> List[tuple]:
        return self.links


def extract_text_from_html(html_content: str) -> str:
    """Extract plain text from HTML, preserving URLs."""
    if not html_content:
        return ''

    # Decode HTML entities
    text = html.unescape(html_content)

    # Simple HTML tag removal while preserving hrefs
    # Convert <a href="url">text</a> to [text](url)
    text = re.sub(
        r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>([^<]*)</a>',
        r'[\2](\1)',
        text,
        flags=re.IGNORECASE
    )

    # Remove remaining HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)

    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    return text


class ShowNotesExtractor:
    """Extract links from podcast show notes (episode descriptions)."""

    def __init__(
        self,
        podcast_db_path: Path = PODCAST_DB_PATH,
        link_db_path: Path = LINK_DB_PATH
    ):
        self.podcast_db_path = podcast_db_path
        self.link_db_path = link_db_path
        self.extractor = LinkExtractor(db_path=str(link_db_path))

    def get_podcasts(self) -> List[Dict]:
        """Get all podcasts from database."""
        conn = sqlite3.connect(self.podcast_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT id, slug, name FROM podcasts")
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    def get_episodes_with_descriptions(
        self,
        podcast_id: Optional[int] = None,
        limit: Optional[int] = None
    ) -> Generator[Dict, None, None]:
        """
        Get episodes that have descriptions in metadata.

        Yields episode dicts with: id, podcast_id, slug, title, url, description
        """
        conn = sqlite3.connect(self.podcast_db_path)
        conn.row_factory = sqlite3.Row

        query = """
            SELECT e.id, e.podcast_id, p.slug, e.title, e.url, e.metadata
            FROM episodes e
            JOIN podcasts p ON e.podcast_id = p.id
            WHERE e.metadata IS NOT NULL AND e.metadata != '{}'
        """
        params = []

        if podcast_id:
            query += " AND e.podcast_id = ?"
            params.append(podcast_id)

        query += " ORDER BY e.publish_date DESC"

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        cursor = conn.execute(query, params)

        for row in cursor:
            try:
                import json
                metadata = json.loads(row['metadata']) if row['metadata'] else {}
                description = metadata.get('description', '')

                if description:
                    yield {
                        'id': row['id'],
                        'podcast_id': row['podcast_id'],
                        'slug': row['slug'],
                        'title': row['title'],
                        'url': row['url'],
                        'description': description,
                    }
            except (json.JSONDecodeError, TypeError):
                continue

        conn.close()

    def extract_from_episode(self, episode: Dict) -> int:
        """
        Extract links from a single episode's description.

        Returns: Number of new links added
        """
        description = episode.get('description', '')
        if not description:
            return 0

        # Convert HTML to text with markdown-style links
        text = extract_text_from_html(description)

        # Generate content ID
        content_id = f"podcast:{episode['slug']}:{episode['id']}"
        source_path = episode.get('url', '')

        # Extract and save links
        return self.extractor.extract_and_save(
            text=text,
            content_id=content_id,
            source_path=source_path,
            source_type=LinkSource.SHOWNOTES
        )

    def extract_all(
        self,
        podcast_slug: Optional[str] = None,
        limit: Optional[int] = None
    ) -> Dict:
        """
        Extract links from all episode descriptions.

        Args:
            podcast_slug: If provided, only extract from this podcast
            limit: Maximum episodes to process

        Returns:
            Statistics dictionary
        """
        stats = {
            'episodes_processed': 0,
            'episodes_with_links': 0,
            'links_added': 0,
            'by_podcast': {},
        }

        # Get podcast ID if slug provided
        podcast_id = None
        if podcast_slug:
            podcasts = self.get_podcasts()
            for p in podcasts:
                if p['slug'] == podcast_slug:
                    podcast_id = p['id']
                    break
            if not podcast_id:
                logger.error(f"Podcast not found: {podcast_slug}")
                return stats

        # Process episodes
        for episode in self.get_episodes_with_descriptions(podcast_id, limit):
            added = self.extract_from_episode(episode)
            stats['episodes_processed'] += 1

            if added > 0:
                stats['episodes_with_links'] += 1
                stats['links_added'] += added

                # Track by podcast
                slug = episode['slug']
                if slug not in stats['by_podcast']:
                    stats['by_podcast'][slug] = {'episodes': 0, 'links': 0}
                stats['by_podcast'][slug]['episodes'] += 1
                stats['by_podcast'][slug]['links'] += added

            # Progress logging
            if stats['episodes_processed'] % 500 == 0:
                logger.info(f"Processed {stats['episodes_processed']} episodes, {stats['links_added']} links added")

        return stats


def extract_shownotes(podcast_slug: Optional[str] = None, limit: Optional[int] = None) -> Dict:
    """
    Convenience function to extract links from show notes.

    Args:
        podcast_slug: If provided, only extract from this podcast
        limit: Maximum episodes to process

    Returns:
        Statistics dictionary
    """
    extractor = ShowNotesExtractor()
    return extractor.extract_all(podcast_slug=podcast_slug, limit=limit)
