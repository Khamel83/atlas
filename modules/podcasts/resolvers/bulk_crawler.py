#!/usr/bin/env python3
"""
Bulk Transcript Crawler

For podcasts with dedicated transcript sites (like catatp.fm), this crawler
fetches all transcript pages in bulk.
"""

import asyncio
import aiohttp
import json
import logging
import re
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import requests
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


def _normalize_title(title: str) -> str:
    """Normalize title for fuzzy matching"""
    import re
    title = title.lower()
    title = re.sub(r'[^\w\s]', ' ', title)
    title = ' '.join(title.split())
    # Remove common prefixes
    for prefix in ['episode ', 'ep ', '#', 'transcript ']:
        if title.startswith(prefix):
            title = title[len(prefix):]
    return title.strip()


def _fuzzy_match_score(a: str, b: str) -> float:
    """Calculate fuzzy match score between two strings"""
    return SequenceMatcher(None, _normalize_title(a), _normalize_title(b)).ratio()


class BulkTranscriptCrawler:
    """Bulk crawler for sites with dedicated transcript pages"""

    # Known transcript sites with their configurations
    TRANSCRIPT_SITES = {
        'catatp.fm': {
            'name': 'ATP Transcripts',
            'index_url': 'https://catatp.fm/episodes/',
            'episode_pattern': r'/\d{4}/\d{2}/\d{2}/atp\d+\.mp3/',
            'content_selector': '.transcript-content, article, .episode-content',
            'rate_limit': 0.5,
            'slug': 'accidental-tech-podcast',
        },
        'conversationswithtyler.com': {
            'name': 'Conversations with Tyler',
            'index_url': 'https://conversationswithtyler.com/episodes/',
            'episode_pattern': r'/episodes/[^/]+/$',
            'content_selector': '.transcript, .episode-transcript, .entry-content',
            'rate_limit': 1.0,
            'slug': 'conversations-with-tyler',
        },
        'thisamericanlife.org': {
            'name': 'This American Life',
            'index_url': 'https://www.thisamericanlife.org/archive',
            'episode_pattern': r'/\d+/',
            'content_selector': '.transcript, .act-inner',
            'rate_limit': 1.5,
            'slug': 'this-american-life',
        },
        'lexfridman.com': {
            'name': 'Lex Fridman Podcast',
            'index_url': 'https://lexfridman.com/podcast/',
            'episode_pattern': r'/[a-z0-9-]+-transcript/?$',
            'content_selector': '.entry-content, .transcript, article',
            'rate_limit': 1.0,
            'slug': 'lex-fridman-podcast',
        },
        'econtalk.org': {
            'name': 'EconTalk',
            # Episodes listed on econlib.org archive but hosted on econtalk.org
            'index_url': 'https://www.econlib.org/econtalk-archives-by-date/',
            # Full URLs like https://www.econtalk.org/the-status-game-with-will-storr/
            'episode_pattern': r'https://www\.econtalk\.org/[a-z0-9-]+-[a-z0-9-]+/',
            'content_selector': '.entry-content, .transcript, article',
            'rate_limit': 1.5,
            'slug': 'econtalk',
        },
        'dwarkesh.com': {
            'name': 'Dwarkesh Podcast',
            'index_url': 'https://www.dwarkesh.com/podcast',
            'episode_pattern': r'/p/[^/]+',
            'content_selector': '.body, article, .post-content',
            'rate_limit': 1.0,
            'slug': 'dwarkesh-podcast',
        },
        'freakonomics.com': {
            'name': 'Freakonomics Radio',
            'index_url': 'https://freakonomics.com/series/freakonomics-radio/',
            'episode_pattern': r'/podcast/[^/]+/',
            'content_selector': '.episode-transcript, .entry-content, article',
            'rate_limit': 1.5,
            'slug': 'freakonomics-radio',
        },
        # tim.blog - JavaScript rendered, requires headless browser
        # Alternative: tim.blog/transcripts page may have direct links
        'darknetdiaries.com': {
            'name': 'Darknet Diaries',
            'index_url': 'https://darknetdiaries.com/episode/',
            # Episodes at /episode/166/, transcripts at /transcript/166/
            'episode_pattern': r'/episode/\d+/?$',
            'content_selector': '.entry-content, article, .transcript',
            'rate_limit': 1.0,
            'slug': 'darknet-diaries',
            # Note: Transcripts are at /transcript/{id}/ - need post-processing
        },
        # REMOVED: hubermantranscripts.com - site taken down
        # REMOVED: preposterousuniverse.com (Mindscape) - not needed
        # REMOVED: tim.blog - JavaScript rendered, not needed
        'macrovoices.com': {
            'name': 'Macro Voices',
            'index_url': 'https://www.macrovoices.com/podcast-transcripts',
            'episode_pattern': r'/podcast-transcripts/\d+-[^/]+',
            'content_selector': '.item-page, article, .content',
            'rate_limit': 1.5,
            'slug': 'macro-voices',
        },
        'alieward.com': {
            'name': 'Ologies',
            'index_url': 'https://www.alieward.com/ologies',
            'episode_pattern': r'/ologies/[^/]+',
            'content_selector': '.sqs-block-content, article',
            'rate_limit': 1.5,
            'slug': 'ologies',
        },
        'hiddenbrain.org': {
            'name': 'Hidden Brain',
            'index_url': 'https://www.hiddenbrain.org/',
            'episode_pattern': r'/podcast/[^/]+/',
            'content_selector': '.entry-content, .transcript, article',
            'rate_limit': 1.5,
            'slug': 'hidden-brain',
        },
    }

    def __init__(self, output_dir: str = "data/podcasts"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Encoding': 'gzip, deflate',  # Disable brotli
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })

    def discover_episodes(self, site_config: Dict[str, Any]) -> List[str]:
        """Discover episode URLs from a transcript site index"""
        episode_urls = []

        try:
            response = self.session.get(site_config['index_url'], timeout=60)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            pattern = site_config['episode_pattern']
            base_url = site_config['index_url']

            for link in soup.find_all('a', href=True):
                href = link['href']
                if re.search(pattern, href):
                    full_url = urljoin(base_url, href)
                    episode_urls.append(full_url)

            # Deduplicate and sort
            episode_urls = list(set(episode_urls))
            episode_urls.sort(reverse=True)
            logger.info(f"Discovered {len(episode_urls)} episodes from {site_config['name']}")

        except Exception as e:
            logger.error(f"Error discovering episodes: {e}")

        return episode_urls

    def fetch_transcript(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch a single transcript page"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Get page title
            title_tag = soup.find('title')
            title = title_tag.get_text() if title_tag else url

            # Get main content - try multiple selectors
            content = None
            for selector in ['article', 'main', '.content', '.episode-content', 'body']:
                element = soup.select_one(selector)
                if element:
                    content = element.get_text(separator='\n', strip=True)
                    if len(content) > 500:  # Reasonable transcript length
                        break

            if content and len(content) > 100:
                return {
                    'url': url,
                    'content': content,
                    'content_length': len(content),
                    'title': title,
                    'crawled_at': datetime.now().isoformat(),
                }

        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")

        return None

    async def crawl_site_bulk_async(self, site_key: str, max_episodes: int = None,
                                     concurrency: int = 5) -> List[Dict[str, Any]]:
        """Crawl all transcripts from a site using async"""
        if site_key not in self.TRANSCRIPT_SITES:
            logger.error(f"Unknown site: {site_key}")
            return []

        site_config = self.TRANSCRIPT_SITES[site_key]
        logger.info(f"Starting bulk crawl of {site_config['name']}")

        # Discover episodes (sync, happens once)
        episode_urls = self.discover_episodes(site_config)

        if max_episodes:
            episode_urls = episode_urls[:max_episodes]

        logger.info(f"Crawling {len(episode_urls)} episodes...")

        results = []
        rate_limit = site_config.get('rate_limit', 1.0)

        async def fetch_one(session: aiohttp.ClientSession, url: str) -> Optional[Dict[str, Any]]:
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')

                        title_tag = soup.find('title')
                        title = title_tag.get_text() if title_tag else url

                        content = None
                        for selector in ['article', 'main', '.content', '.episode-content', 'body']:
                            element = soup.select_one(selector)
                            if element:
                                content = element.get_text(separator='\n', strip=True)
                                if len(content) > 500:
                                    break

                        if content and len(content) > 100:
                            return {
                                'url': url,
                                'content': content,
                                'content_length': len(content),
                                'title': title,
                                'crawled_at': datetime.now().isoformat(),
                            }
            except Exception as e:
                logger.debug(f"Error fetching {url}: {e}")
            return None

        connector = aiohttp.TCPConnector(limit=concurrency)
        async with aiohttp.ClientSession(
            connector=connector,
            headers={'User-Agent': 'Atlas-Pod/1.0'}
        ) as session:
            # Process in batches
            batch_size = concurrency * 2
            for i in range(0, len(episode_urls), batch_size):
                batch = episode_urls[i:i + batch_size]
                tasks = [fetch_one(session, url) for url in batch]
                batch_results = await asyncio.gather(*tasks)

                for result in batch_results:
                    if result:
                        results.append(result)
                        logger.info(f"Fetched: {result['title'][:60]}...")

                # Progress update
                logger.info(f"Progress: {min(i + batch_size, len(episode_urls))}/{len(episode_urls)} ({len(results)} successful)")

                # Rate limit between batches
                await asyncio.sleep(rate_limit)

        logger.info(f"Crawled {len(results)} transcripts from {site_config['name']}")
        return results

    def crawl_site_bulk(self, site_key: str, max_episodes: int = None) -> List[Dict[str, Any]]:
        """Synchronous wrapper for bulk crawling"""
        return asyncio.run(self.crawl_site_bulk_async(site_key, max_episodes))

    def save_transcripts(self, results: List[Dict[str, Any]], podcast_slug: str,
                         sync_db: bool = True) -> int:
        """Save crawled transcripts to disk and optionally sync to database

        Args:
            results: List of transcript dictionaries with url, content, title, etc.
            podcast_slug: The podcast slug (e.g., 'lex-fridman-podcast')
            sync_db: If True, also update episode status in SQLite database

        Returns:
            Number of transcripts saved
        """
        transcript_dir = self.output_dir / podcast_slug / "transcripts"
        transcript_dir.mkdir(parents=True, exist_ok=True)

        saved_count = 0
        saved_files = []  # Track for DB sync

        for result in results:
            try:
                # Generate filename from URL
                url_parts = urlparse(result['url'])
                # Extract episode identifier from URL
                path_parts = url_parts.path.strip('/').split('/')
                filename = '_'.join(path_parts[-3:]) if len(path_parts) >= 3 else path_parts[-1]
                filename = re.sub(r'[^\w\-_]', '_', filename)
                filename = f"{filename}.md"

                filepath = transcript_dir / filename

                # Write markdown content
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(f"# {result['title']}\n\n")
                    f.write(f"Source: {result['url']}\n")
                    f.write(f"Crawled: {result['crawled_at']}\n\n")
                    f.write("---\n\n")
                    f.write(result['content'])

                saved_count += 1
                saved_files.append({
                    'filepath': str(filepath),
                    'title': result['title'],
                    'url': result['url']
                })

            except Exception as e:
                logger.error(f"Error saving transcript {result.get('url', 'unknown')}: {e}")

        logger.info(f"Saved {saved_count} transcripts to {transcript_dir}")

        # Sync to database if requested
        if sync_db and saved_files:
            synced = self._sync_to_database(podcast_slug, saved_files)
            logger.info(f"Synced {synced} transcripts to database")

        return saved_count

    def _sync_to_database(self, podcast_slug: str, saved_files: List[Dict[str, str]]) -> int:
        """Sync saved transcripts to the SQLite database

        Matches transcripts to episodes by fuzzy title matching and updates
        transcript_status to 'fetched'.

        Args:
            podcast_slug: The podcast slug
            saved_files: List of dicts with 'filepath', 'title', 'url'

        Returns:
            Number of episodes updated in database
        """
        try:
            from modules.podcasts.store import PodcastStore

            store = PodcastStore()
            podcast = store.get_podcast_by_slug(podcast_slug)

            if not podcast:
                logger.warning(f"Podcast '{podcast_slug}' not in database, skipping sync")
                return 0

            # Get all episodes for this podcast
            episodes = store.get_episodes(podcast.id)
            if not episodes:
                logger.warning(f"No episodes found for '{podcast_slug}' in database")
                return 0

            # Build lookup by normalized title
            episode_by_title = {}
            for ep in episodes:
                normalized = _normalize_title(ep.title)
                episode_by_title[normalized] = ep

            synced_count = 0
            for saved in saved_files:
                title = saved['title']
                filepath = saved['filepath']

                # Try exact normalized match first
                normalized_title = _normalize_title(title)
                episode = episode_by_title.get(normalized_title)

                # If no exact match, try fuzzy matching
                if not episode:
                    best_score = 0
                    best_match = None
                    for ep in episodes:
                        score = _fuzzy_match_score(title, ep.title)
                        if score > best_score and score >= 0.7:  # 70% threshold
                            best_score = score
                            best_match = ep
                    episode = best_match

                if episode:
                    # Skip if already fetched
                    if episode.transcript_status == 'fetched' and episode.transcript_path:
                        continue

                    # Update episode status
                    store.update_episode_transcript_status(
                        episode.id,
                        status='fetched',
                        transcript_path=filepath
                    )
                    synced_count += 1
                    logger.debug(f"Synced: {episode.title[:50]}...")
                else:
                    logger.debug(f"No DB match for: {title[:50]}...")

            return synced_count

        except ImportError as e:
            logger.warning(f"Could not import store module: {e}")
            return 0
        except Exception as e:
            logger.error(f"Error syncing to database: {e}")
            return 0


def crawl_atp_transcripts(max_episodes: int = None):
    """Convenience function to crawl all ATP transcripts"""
    crawler = BulkTranscriptCrawler()
    results = crawler.crawl_site_bulk('catatp.fm', max_episodes)
    slug = crawler.TRANSCRIPT_SITES['catatp.fm']['slug']
    saved = crawler.save_transcripts(results, slug)
    return saved


def crawl_site(site_key: str, max_episodes: int = None):
    """Crawl a specific transcript site"""
    crawler = BulkTranscriptCrawler()
    results = crawler.crawl_site_bulk(site_key, max_episodes)
    slug = crawler.TRANSCRIPT_SITES[site_key]['slug']
    saved = crawler.save_transcripts(results, slug)
    return saved


def list_available_sites():
    """List all available transcript sites"""
    crawler = BulkTranscriptCrawler()
    print("\n" + "="*60)
    print("AVAILABLE TRANSCRIPT SITES FOR BULK CRAWLING")
    print("="*60 + "\n")

    for site_key, config in crawler.TRANSCRIPT_SITES.items():
        print(f"  {site_key}")
        print(f"    Name: {config['name']}")
        print(f"    Slug: {config['slug']}")
        print(f"    Index: {config['index_url']}")
        print()

    print("="*60)
    print("USAGE:")
    print("  python -m modules.podcasts.resolvers.bulk_crawler <site_key> [max_episodes]")
    print("\nEXAMPLES:")
    print("  python -m modules.podcasts.resolvers.bulk_crawler lexfridman.com")
    print("  python -m modules.podcasts.resolvers.bulk_crawler econtalk.org 50")
    print("  python -m modules.podcasts.resolvers.bulk_crawler --list")
    print("="*60 + "\n")


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    # Handle --list flag
    if len(sys.argv) > 1 and sys.argv[1] in ['--list', '-l', 'list']:
        list_available_sites()
        sys.exit(0)

    # Handle --help flag
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h', 'help']:
        print("""
Bulk Transcript Crawler - Crawl dedicated transcript archives

USAGE:
  python -m modules.podcasts.resolvers.bulk_crawler <site_key> [max_episodes]
  python -m modules.podcasts.resolvers.bulk_crawler --list

OPTIONS:
  --list, -l    List all available transcript sites
  --help, -h    Show this help message

EXAMPLES:
  # Crawl all Lex Fridman transcripts
  python -m modules.podcasts.resolvers.bulk_crawler lexfridman.com

  # Crawl first 50 EconTalk episodes
  python -m modules.podcasts.resolvers.bulk_crawler econtalk.org 50

  # List all available sites
  python -m modules.podcasts.resolvers.bulk_crawler --list

AVAILABLE SITES:
  catatp.fm                - ATP Transcripts (DONE: 677 transcripts)
  conversationswithtyler.com - Conversations with Tyler (DONE: 273 transcripts)
  lexfridman.com           - Lex Fridman Podcast
  econtalk.org             - EconTalk
  dwarkesh.com             - Dwarkesh Podcast
  freakonomics.com         - Freakonomics Radio
  tim.blog                 - Tim Ferriss Show
  darknetdiaries.com       - Darknet Diaries
  hubermantranscripts.com  - Huberman Lab
  preposterousuniverse.com - Sean Carroll Mindscape
  macrovoices.com          - Macro Voices
  alieward.com             - Ologies
  hiddenbrain.org          - Hidden Brain
  thisamericanlife.org     - This American Life

OUTPUT:
  Transcripts are saved to: data/podcasts/<slug>/transcripts/
""")
        sys.exit(0)

    # Parse command line args
    site = sys.argv[1] if len(sys.argv) > 1 else 'catatp.fm'
    max_eps = int(sys.argv[2]) if len(sys.argv) > 2 else None

    # Validate site
    crawler = BulkTranscriptCrawler()
    if site not in crawler.TRANSCRIPT_SITES:
        print(f"\nError: Unknown site '{site}'")
        print(f"Run with --list to see available sites\n")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"CRAWLING: {crawler.TRANSCRIPT_SITES[site]['name']}")
    print(f"Max episodes: {max_eps or 'all'}")
    print(f"Output: data/podcasts/{crawler.TRANSCRIPT_SITES[site]['slug']}/transcripts/")
    print(f"{'='*60}\n")

    saved = crawl_site(site, max_eps)

    print(f"\n{'='*60}")
    print(f"COMPLETE: Saved {saved} transcripts")
    print(f"{'='*60}\n")
