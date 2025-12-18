"""
Link Extractor - Extract and score URLs from any text source.

This module provides the core extraction logic, decoupled from database storage.
Can be used standalone or with the full pipeline.
"""

import re
import sqlite3
import logging
import hashlib
from pathlib import Path
from urllib.parse import urlparse
from typing import List, Dict, Optional, Tuple

from modules.links.models import Link, LinkSource, LinkCategory

logger = logging.getLogger(__name__)


# Domains to skip (ads, social, navigation)
SKIP_DOMAINS = {
    # Social media
    'twitter.com', 'x.com', 'facebook.com', 'instagram.com', 'linkedin.com',
    'tiktok.com', 'pinterest.com', 'reddit.com', 'threads.net',

    # Video/media (we handle separately)
    'youtube.com', 'youtu.be', 'vimeo.com', 'twitch.tv',

    # Podcast platforms
    'spotify.com', 'apple.com', 'podcasts.apple.com', 'overcast.fm',
    'pocketcasts.com', 'castro.fm', 'stitcher.com',

    # Common ads/sponsors
    'squarespace.com', 'mailchimp.com', 'hubspot.com',
    'shopify.com', 'wix.com', 'godaddy.com',
    'audible.com', 'kindle.com', 'amazon.com', 'amzn.to',

    # URL shorteners
    'bit.ly', 'tinyurl.com', 't.co', 'goo.gl', 'ow.ly',

    # Navigation/utility
    'google.com', 'bing.com', 'duckduckgo.com',
    'github.com', 'gitlab.com',  # Code repos (different queue)
    'en.wikipedia.org',  # Reference, not news

    # Payment/commerce
    'paypal.com', 'stripe.com', 'gumroad.com', 'patreon.com',
    'ko-fi.com', 'buymeacoffee.com',
}

# High-value domains (news, research, analysis)
HIGH_VALUE_DOMAINS = {
    # Tech news
    'techcrunch.com', 'theverge.com', 'wired.com', 'arstechnica.com',
    'engadget.com', 'zdnet.com', 'cnet.com', 'macrumors.com',
    '9to5mac.com', '9to5google.com', 'androidcentral.com',

    # Business/finance
    'bloomberg.com', 'wsj.com', 'ft.com', 'reuters.com',
    'economist.com', 'forbes.com', 'businessinsider.com',
    'cnbc.com', 'fortune.com', 'inc.com', 'fastcompany.com',

    # News
    'nytimes.com', 'washingtonpost.com', 'theguardian.com',
    'bbc.com', 'bbc.co.uk', 'npr.org', 'apnews.com',
    'theatlantic.com', 'newyorker.com', 'vox.com',

    # Research/academic
    'arxiv.org', 'nature.com', 'science.org', 'sciencedirect.com',
    'pnas.org', 'cell.com', 'nih.gov', 'pubmed.ncbi.nlm.nih.gov',

    # Tech blogs we follow
    'stratechery.com', 'benthompson.com', 'danluu.com',
    'paulgraham.com', 'joelonsoftware.com', 'daringfireball.net',

    # Substacks (high quality)
    'substack.com',
}

# Context words that indicate valuable links
VALUABLE_CONTEXT = [
    'according to', 'research', 'study', 'report', 'analysis',
    'published', 'wrote', 'reported', 'found that', 'shows that',
    'article', 'piece', 'essay', 'post', 'interview',
    'announced', 'revealed', 'discovered', 'explained',
]

# Context words that indicate low value
LOW_VALUE_CONTEXT = [
    'sponsor', 'ad', 'promo', 'discount', 'offer', 'code',
    'sign up', 'subscribe', 'download', 'buy', 'purchase',
    'click here', 'learn more', 'get started',
]

# Media file extensions to skip (not articles)
MEDIA_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.ico', '.bmp',  # Images
    '.mp3', '.mp4', '.wav', '.m4a', '.ogg', '.flac', '.aac',  # Audio
    '.webm', '.mkv', '.avi', '.mov',  # Video
}


class LinkExtractor:
    """Extract and score links from any text source."""

    # URL patterns
    MD_LINK = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
    BARE_URL = re.compile(r'https?://[^\s<>\[\]\"\')\]]+')

    def __init__(self, db_path: str = "data/enrich/link_queue.db"):
        """Initialize extractor with optional database path."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _ensure_schema(self):
        """Ensure database has required schema including new columns."""
        conn = sqlite3.connect(self.db_path)

        # Create table if not exists
        conn.execute("""
            CREATE TABLE IF NOT EXISTS extracted_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                url_hash TEXT UNIQUE NOT NULL,
                domain TEXT NOT NULL,
                source_content_id TEXT,
                source_path TEXT,
                anchor_text TEXT,
                surrounding_context TEXT,
                score REAL DEFAULT 0.0,
                category TEXT DEFAULT 'unknown',
                status TEXT DEFAULT 'pending',
                source_type TEXT DEFAULT 'unknown',
                approval_rule TEXT,
                extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TIMESTAMP,
                ingested_at TIMESTAMP
            )
        """)

        # Add new columns if they don't exist (migration)
        try:
            conn.execute("ALTER TABLE extracted_links ADD COLUMN source_type TEXT DEFAULT 'unknown'")
        except sqlite3.OperationalError:
            pass  # Column already exists

        try:
            conn.execute("ALTER TABLE extracted_links ADD COLUMN approval_rule TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists

        # Create indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_domain ON extracted_links(domain)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON extracted_links(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_score ON extracted_links(score DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_source_type ON extracted_links(source_type)")

        conn.commit()
        conn.close()

    def extract_from_text(
        self,
        text: str,
        content_id: str = '',
        source_path: str = '',
        source_type: LinkSource = LinkSource.UNKNOWN
    ) -> List[Link]:
        """
        Extract all links from text content.

        Args:
            text: The text to extract links from
            content_id: Identifier for the source content (e.g., 'podcast:acquired:ep-1')
            source_path: File path or URL of the source
            source_type: Type of source (transcript, shownotes, article, etc.)

        Returns:
            List of Link objects with scores and categories
        """
        links = []

        # Extract markdown links with anchor text
        for match in self.MD_LINK.finditer(text):
            anchor = match.group(1)
            url = match.group(2)

            # Get surrounding context
            start = max(0, match.start() - 100)
            end = min(len(text), match.end() + 100)
            context = text[start:end]

            link = self._create_link(url, anchor, context, content_id, source_path, source_type)
            if link:
                links.append(link)

        # Extract bare URLs
        for match in self.BARE_URL.finditer(text):
            url = match.group(0)

            # Skip if already captured as markdown link
            if any(l.url == url for l in links):
                continue

            start = max(0, match.start() - 100)
            end = min(len(text), match.end() + 100)
            context = text[start:end]

            link = self._create_link(url, '', context, content_id, source_path, source_type)
            if link:
                links.append(link)

        return links

    def _create_link(
        self,
        url: str,
        anchor: str,
        context: str,
        content_id: str,
        source_path: str,
        source_type: LinkSource
    ) -> Optional[Link]:
        """Create and score a link."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # Remove www prefix
            if domain.startswith('www.'):
                domain = domain[4:]

            # Skip unwanted domains
            if domain in SKIP_DOMAINS:
                return None

            # Skip internal/relative links
            if not domain or domain.startswith('localhost'):
                return None

            # Categorize and score
            category, score = self._score_link(url, domain, anchor, context)

            # Skip low-value categories
            if category in (LinkCategory.AD, LinkCategory.NAVIGATION, LinkCategory.SOCIAL, LinkCategory.MEDIA):
                return None

            return Link(
                url=url,
                domain=domain,
                source_content_id=content_id,
                source_path=source_path,
                source_type=source_type,
                anchor_text=anchor[:200] if anchor else '',
                surrounding_context=context[:500],
                score=score,
                category=category
            )

        except Exception as e:
            logger.debug(f"Error processing URL {url}: {e}")
            return None

    def _score_link(
        self,
        url: str,
        domain: str,
        anchor: str,
        context: str
    ) -> Tuple[LinkCategory, float]:
        """Score a link's value for ingestion."""
        # Early exit for media files (images, audio, video)
        parsed = urlparse(url)
        path_lower = parsed.path.lower()
        # Check for media extensions anywhere in URL (handles CDN query strings too)
        if any(ext in path_lower for ext in MEDIA_EXTENSIONS):
            return LinkCategory.MEDIA, 0.0

        score = 0.5  # Base score
        category = LinkCategory.UNKNOWN

        context_lower = context.lower()
        anchor_lower = anchor.lower()

        # Domain scoring
        if domain in HIGH_VALUE_DOMAINS:
            score += 0.3
            category = LinkCategory.ARTICLE
        elif domain.endswith('.edu'):
            score += 0.25
            category = LinkCategory.RESEARCH
        elif domain.endswith('.gov'):
            score += 0.2
            category = LinkCategory.RESEARCH
        elif 'substack.com' in domain or 'medium.com' in domain:
            score += 0.15
            category = LinkCategory.ARTICLE

        # Context scoring
        valuable_matches = sum(1 for w in VALUABLE_CONTEXT if w in context_lower)
        score += min(valuable_matches * 0.05, 0.2)

        low_value_matches = sum(1 for w in LOW_VALUE_CONTEXT if w in context_lower)
        score -= low_value_matches * 0.1

        if low_value_matches > valuable_matches:
            category = LinkCategory.AD

        # Anchor text scoring
        if anchor and len(anchor) > 10:
            score += 0.05
        if anchor_lower in ('click here', 'here', 'link', 'this'):
            score -= 0.1

        # URL structure scoring
        if '/article/' in url or '/post/' in url or '/story/' in url:
            score += 0.1
            category = LinkCategory.ARTICLE
        if '/research/' in url or '/paper/' in url or '/study/' in url:
            score += 0.1
            category = LinkCategory.RESEARCH

        # Clamp score
        score = max(0.0, min(1.0, score))

        return category, score

    def save_link(self, link: Link) -> bool:
        """Save a link to the database. Returns True if new."""
        url_hash = hashlib.md5(link.url.encode()).hexdigest()

        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                INSERT OR IGNORE INTO extracted_links
                (url, url_hash, domain, source_content_id, source_path,
                 anchor_text, surrounding_context, score, category, source_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                link.url, url_hash, link.domain, link.source_content_id,
                link.source_path, link.anchor_text, link.surrounding_context,
                link.score, link.category.value, link.source_type.value
            ))
            conn.commit()
            return conn.total_changes > 0
        finally:
            conn.close()

    def save_links(self, links: List[Link]) -> int:
        """Save multiple links to database. Returns count of new links added."""
        added = 0
        for link in links:
            if self.save_link(link):
                added += 1
        return added

    def extract_and_save(
        self,
        text: str,
        content_id: str = '',
        source_path: str = '',
        source_type: LinkSource = LinkSource.UNKNOWN
    ) -> int:
        """Extract links from text and save to database. Returns count added."""
        links = self.extract_from_text(text, content_id, source_path, source_type)
        return self.save_links(links)


def extract_links(
    text: str,
    content_id: str = '',
    source_path: str = '',
    source_type: str = 'unknown'
) -> List[Link]:
    """
    Convenience function to extract links from text.

    Args:
        text: Text to extract links from
        content_id: Identifier for the source content
        source_path: Path or URL of the source
        source_type: One of: transcript, shownotes, article, newsletter, manual, unknown

    Returns:
        List of Link objects
    """
    extractor = LinkExtractor()
    source = LinkSource(source_type) if source_type in [e.value for e in LinkSource] else LinkSource.UNKNOWN
    return extractor.extract_from_text(text, content_id, source_path, source)
