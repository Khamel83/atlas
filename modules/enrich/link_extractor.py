"""
Link Extractor - Find and queue URLs from content for potential ingestion.

Extracts URLs from Atlas content and evaluates them for potential inclusion:
1. Extract all URLs from podcasts, articles, newsletters
2. Filter out obvious garbage (ads, social media, etc.)
3. Score relevance based on context and domain
4. Queue high-quality links for review/ingestion

Output: data/enrich/link_queue.db (SQLite)
"""

import re
import sqlite3
import logging
import hashlib
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass
from collections import Counter

logger = logging.getLogger(__name__)


@dataclass
class ExtractedLink:
    """A link extracted from content."""
    url: str
    domain: str
    source_content_id: str
    source_path: str
    anchor_text: str
    surrounding_context: str
    score: float
    category: str  # 'article', 'research', 'social', 'ad', 'navigation', 'unknown'


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


class LinkDatabase:
    """SQLite database for extracted links."""

    def __init__(self, db_path: str = "data/enrich/link_queue.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
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
                extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TIMESTAMP,
                ingested_at TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_domain ON extracted_links(domain)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON extracted_links(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_score ON extracted_links(score DESC)")
        conn.commit()
        conn.close()

    def add_link(self, link: ExtractedLink) -> bool:
        """Add a link to the queue. Returns True if new."""
        url_hash = hashlib.md5(link.url.encode()).hexdigest()

        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                INSERT OR IGNORE INTO extracted_links
                (url, url_hash, domain, source_content_id, source_path,
                 anchor_text, surrounding_context, score, category)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                link.url, url_hash, link.domain, link.source_content_id,
                link.source_path, link.anchor_text, link.surrounding_context,
                link.score, link.category
            ))
            conn.commit()
            return conn.total_changes > 0
        finally:
            conn.close()

    def get_pending(self, min_score: float = 0.5, limit: int = 100) -> List[Dict]:
        """Get high-scoring pending links for review."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("""
            SELECT * FROM extracted_links
            WHERE status = 'pending' AND score >= ?
            ORDER BY score DESC
            LIMIT ?
        """, (min_score, limit))
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    def get_stats(self) -> Dict:
        """Get queue statistics."""
        conn = sqlite3.connect(self.db_path)
        stats = {}

        # Total by status
        cursor = conn.execute("""
            SELECT status, COUNT(*) FROM extracted_links GROUP BY status
        """)
        stats['by_status'] = dict(cursor.fetchall())

        # Top domains
        cursor = conn.execute("""
            SELECT domain, COUNT(*) as cnt FROM extracted_links
            WHERE status = 'pending'
            GROUP BY domain ORDER BY cnt DESC LIMIT 20
        """)
        stats['top_domains'] = dict(cursor.fetchall())

        # Score distribution
        cursor = conn.execute("""
            SELECT
                CASE
                    WHEN score >= 0.8 THEN 'high'
                    WHEN score >= 0.5 THEN 'medium'
                    ELSE 'low'
                END as tier,
                COUNT(*)
            FROM extracted_links WHERE status = 'pending'
            GROUP BY tier
        """)
        stats['score_tiers'] = dict(cursor.fetchall())

        conn.close()
        return stats

    def mark_status(self, url: str, status: str):
        """Update link status (reviewed, ingested, rejected)."""
        url_hash = hashlib.md5(url.encode()).hexdigest()
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            UPDATE extracted_links SET status = ?,
            reviewed_at = CASE WHEN ? IN ('approved', 'rejected') THEN CURRENT_TIMESTAMP ELSE reviewed_at END,
            ingested_at = CASE WHEN ? = 'ingested' THEN CURRENT_TIMESTAMP ELSE ingested_at END
            WHERE url_hash = ?
        """, (status, status, status, url_hash))
        conn.commit()
        conn.close()


class LinkExtractor:
    """Extract and score links from content."""

    # URL patterns
    MD_LINK = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
    BARE_URL = re.compile(r'https?://[^\s<>\[\]\"\')\]]+')

    def __init__(self):
        self.db = LinkDatabase()

    def extract_from_text(
        self,
        text: str,
        content_id: str,
        source_path: str
    ) -> List[ExtractedLink]:
        """Extract all links from text content."""
        links = []

        # Extract markdown links with anchor text
        for match in self.MD_LINK.finditer(text):
            anchor = match.group(1)
            url = match.group(2)

            # Get surrounding context
            start = max(0, match.start() - 100)
            end = min(len(text), match.end() + 100)
            context = text[start:end]

            link = self._create_link(url, anchor, context, content_id, source_path)
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

            link = self._create_link(url, '', context, content_id, source_path)
            if link:
                links.append(link)

        return links

    def _create_link(
        self,
        url: str,
        anchor: str,
        context: str,
        content_id: str,
        source_path: str
    ) -> Optional[ExtractedLink]:
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
            if category in ('ad', 'navigation', 'social'):
                return None

            return ExtractedLink(
                url=url,
                domain=domain,
                source_content_id=content_id,
                source_path=source_path,
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
    ) -> Tuple[str, float]:
        """Score a link's value for ingestion."""
        score = 0.5  # Base score
        category = 'unknown'

        context_lower = context.lower()
        anchor_lower = anchor.lower()

        # Domain scoring
        if domain in HIGH_VALUE_DOMAINS:
            score += 0.3
            category = 'article'
        elif domain.endswith('.edu'):
            score += 0.25
            category = 'research'
        elif domain.endswith('.gov'):
            score += 0.2
            category = 'research'
        elif 'substack.com' in domain or 'medium.com' in domain:
            score += 0.15
            category = 'article'

        # Context scoring
        valuable_matches = sum(1 for w in VALUABLE_CONTEXT if w in context_lower)
        score += min(valuable_matches * 0.05, 0.2)

        low_value_matches = sum(1 for w in LOW_VALUE_CONTEXT if w in context_lower)
        score -= low_value_matches * 0.1

        if low_value_matches > valuable_matches:
            category = 'ad'

        # Anchor text scoring
        if anchor and len(anchor) > 10:
            # Descriptive anchor text is good
            score += 0.05
        if anchor_lower in ('click here', 'here', 'link', 'this'):
            score -= 0.1

        # URL structure scoring
        if '/article/' in url or '/post/' in url or '/story/' in url:
            score += 0.1
            category = 'article'
        if '/research/' in url or '/paper/' in url or '/study/' in url:
            score += 0.1
            category = 'research'

        # Clamp score
        score = max(0.0, min(1.0, score))

        return category, score

    def extract_from_file(self, filepath: Path, content_id: str) -> int:
        """Extract links from a file and add to queue."""
        try:
            text = filepath.read_text(encoding='utf-8')
            links = self.extract_from_text(text, content_id, str(filepath))

            added = 0
            for link in links:
                if self.db.add_link(link):
                    added += 1

            return added

        except Exception as e:
            logger.error(f"Error extracting from {filepath}: {e}")
            return 0

    def extract_from_clean(self, limit: int = None) -> Dict:
        """Extract links from all clean content."""
        clean_dir = Path('data/clean')
        files = list(clean_dir.rglob('*.md'))

        if limit:
            files = files[:limit]

        stats = {
            'files_processed': 0,
            'links_found': 0,
            'links_added': 0,
        }

        for f in files:
            # Generate content_id from path
            rel_path = f.relative_to(clean_dir)
            parts = rel_path.parts
            if len(parts) >= 2:
                content_id = f"{parts[0]}:{parts[-1].replace('.md', '')}"
            else:
                content_id = str(rel_path)

            added = self.extract_from_file(f, content_id)
            stats['files_processed'] += 1
            stats['links_added'] += added

            if stats['files_processed'] % 1000 == 0:
                print(f"  Progress: {stats['files_processed']}/{len(files)}")

        return stats


# CLI
if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Extract and queue links from content')
    parser.add_argument('--extract', action='store_true', help='Extract links from clean/')
    parser.add_argument('--stats', action='store_true', help='Show queue statistics')
    parser.add_argument('--pending', action='store_true', help='Show pending high-value links')
    parser.add_argument('--limit', type=int, default=50, help='Limit results')
    parser.add_argument('--min-score', type=float, default=0.6, help='Minimum score for pending')
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    extractor = LinkExtractor()

    if args.extract:
        print('Extracting links from data/clean/...')
        stats = extractor.extract_from_clean()
        print(f"\nDone!")
        print(f"Files processed: {stats['files_processed']}")
        print(f"Links added to queue: {stats['links_added']}")

    elif args.stats:
        stats = extractor.db.get_stats()
        print("LINK QUEUE STATISTICS")
        print("=" * 50)
        print("\nBy Status:")
        for status, count in stats.get('by_status', {}).items():
            print(f"  {status}: {count}")

        print("\nScore Tiers (pending):")
        for tier, count in stats.get('score_tiers', {}).items():
            print(f"  {tier}: {count}")

        print("\nTop Domains (pending):")
        for domain, count in list(stats.get('top_domains', {}).items())[:15]:
            print(f"  {count:>5}  {domain}")

    elif args.pending:
        links = extractor.db.get_pending(min_score=args.min_score, limit=args.limit)
        print(f"TOP {len(links)} PENDING LINKS (score >= {args.min_score})")
        print("=" * 70)
        for link in links:
            print(f"\nScore: {link['score']:.2f} | {link['category']} | {link['domain']}")
            print(f"URL: {link['url'][:80]}...")
            if link['anchor_text']:
                print(f"Anchor: {link['anchor_text'][:60]}")
            print(f"Source: {link['source_content_id']}")

    else:
        parser.print_help()
