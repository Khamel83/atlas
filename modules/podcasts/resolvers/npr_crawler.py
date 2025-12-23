#!/usr/bin/env python3
"""
NPR Network Podcast Transcript Crawler

Crawls transcripts from NPR network podcasts using their consistent pattern:
- Episode URLs: npr.org/[date]/nx-s1-[id]/[slug]
- Transcript URLs: npr.org/transcripts/nx-s1-[id]

Supports: Planet Money, Radiolab, Hidden Brain, Fresh Air, TED Radio Hour,
         Throughline, How I Built This, The Indicator, etc.
"""

import asyncio
import aiohttp
import feedparser
import logging
import re
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


def _normalize_title(title: str) -> str:
    """Normalize title for fuzzy matching"""
    title = title.lower()
    title = re.sub(r'[^\w\s]', ' ', title)
    title = ' '.join(title.split())
    for prefix in ['episode ', 'ep ', '#', 'transcript ']:
        if title.startswith(prefix):
            title = title[len(prefix):]
    return title.strip()


def _fuzzy_match_score(a: str, b: str) -> float:
    """Calculate fuzzy match score between two strings"""
    return SequenceMatcher(None, _normalize_title(a), _normalize_title(b)).ratio()


# NPR Podcast configurations
NPR_PODCASTS = {
    'planet-money': {
        'name': 'Planet Money',
        'rss_url': 'https://feeds.npr.org/510289/podcast.xml',
        'archive_url': 'https://www.npr.org/podcasts/510289/planet-money',
        'slug': 'planet-money',
        'episodes_per_page': 24,
    },
    'radiolab': {
        'name': 'Radiolab',
        'rss_url': 'https://feeds.feedburner.com/radiolab',
        'archive_url': 'https://radiolab.org/podcast',
        'slug': 'radiolab',
    },
    'hidden-brain': {
        'name': 'Hidden Brain',
        'rss_url': 'https://feeds.npr.org/510308/podcast.xml',
        'archive_url': 'https://www.npr.org/podcasts/510308/hidden-brain',
        'slug': 'hidden-brain',
    },
    'fresh-air': {
        'name': 'Fresh Air',
        'rss_url': 'https://feeds.npr.org/381444908/podcast.xml',
        'archive_url': 'https://www.npr.org/programs/fresh-air',
        'slug': 'fresh-air',
    },
    'ted-radio-hour': {
        'name': 'TED Radio Hour',
        'rss_url': 'https://feeds.npr.org/510298/podcast.xml',
        'archive_url': 'https://www.npr.org/programs/ted-radio-hour',
        'slug': 'ted-radio-hour',
    },
    'throughline': {
        'name': 'Throughline',
        'rss_url': 'https://feeds.npr.org/510333/podcast.xml',
        'archive_url': 'https://www.npr.org/podcasts/510333/throughline',
        'slug': 'throughline',
    },
    'how-i-built-this': {
        'name': 'How I Built This',
        'rss_url': 'https://feeds.npr.org/510313/podcast.xml',
        'archive_url': 'https://www.npr.org/podcasts/510313/how-i-built-this',
        'slug': 'how-i-built-this',
    },
    'the-indicator': {
        'name': 'The Indicator from Planet Money',
        'rss_url': 'https://feeds.npr.org/510325/podcast.xml',
        'archive_url': 'https://www.npr.org/podcasts/510325/the-indicator-from-planet-money',
        'slug': 'the-indicator',
    },
    'code-switch': {
        'name': 'Code Switch',
        'rss_url': 'https://feeds.npr.org/510312/podcast.xml',
        'archive_url': 'https://www.npr.org/podcasts/510312/codeswitch',
        'slug': 'code-switch',
    },
    'embedded': {
        'name': 'Embedded',
        'rss_url': 'https://feeds.npr.org/510311/podcast.xml',
        'archive_url': 'https://www.npr.org/podcasts/510311/embedded',
        'slug': 'embedded',
    },
}


class NPRCrawler:
    """Crawler for NPR network podcast transcripts"""

    def __init__(self, output_dir: str = "data/podcasts"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.rate_limit = 1.5  # seconds between requests
        self.session = None

    def extract_episode_id(self, url: str) -> Optional[str]:
        """Extract NPR episode ID from URL"""
        # Pattern: nx-s1-[number] or just [number]
        patterns = [
            r'nx-s1-(\d+)',
            r'/(\d{9,})/',  # 9+ digit IDs
            r'/transcripts/(\d+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def get_transcript_url(self, episode_id: str) -> str:
        """Construct transcript URL from episode ID"""
        # Try nx-s1 format first (newer format)
        if not episode_id.startswith('nx-s1-'):
            return f"https://www.npr.org/transcripts/nx-s1-{episode_id}"
        return f"https://www.npr.org/transcripts/{episode_id}"

    async def discover_episodes_from_rss(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Discover episodes from RSS feed"""
        episodes = []
        try:
            feed = feedparser.parse(config['rss_url'])

            for entry in feed.entries:
                episode = {
                    'title': entry.get('title', 'Unknown'),
                    'url': entry.get('link', ''),
                    'published': entry.get('published', ''),
                    'id': None,
                }

                # Extract episode ID
                if episode['url']:
                    episode['id'] = self.extract_episode_id(episode['url'])

                if episode['id']:
                    episodes.append(episode)

            logger.info(f"Discovered {len(episodes)} episodes from RSS for {config['name']}")

        except Exception as e:
            logger.error(f"Error parsing RSS feed: {e}")

        return episodes

    async def discover_episodes_from_archive(self, config: Dict[str, Any],
                                              max_pages: int = 20) -> List[Dict[str, Any]]:
        """Discover episodes by crawling archive pages"""
        episodes = []
        seen_ids = set()

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        async with aiohttp.ClientSession(headers=headers) as session:
            for page in range(1, max_pages + 1):
                try:
                    # NPR archive pagination
                    if page == 1:
                        url = config['archive_url']
                    else:
                        url = f"{config['archive_url']}?page={page}"

                    async with session.get(url, timeout=30) as response:
                        if response.status != 200:
                            logger.warning(f"Page {page} returned {response.status}")
                            break

                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')

                        # Find episode links
                        page_episodes = 0
                        for link in soup.find_all('a', href=True):
                            href = link['href']
                            ep_id = self.extract_episode_id(href)

                            if ep_id and ep_id not in seen_ids:
                                seen_ids.add(ep_id)
                                title = link.get_text(strip=True) or f"Episode {ep_id}"
                                episodes.append({
                                    'title': title[:200],  # Truncate long titles
                                    'url': href if href.startswith('http') else f"https://www.npr.org{href}",
                                    'id': ep_id,
                                })
                                page_episodes += 1

                        print(f"  Page {page}: Found {page_episodes} new episodes (total: {len(episodes)})")

                        if page_episodes == 0:
                            # No new episodes found, stop paginating
                            break

                        await asyncio.sleep(self.rate_limit)

                except Exception as e:
                    logger.error(f"Error fetching page {page}: {e}")
                    break

        return episodes

    async def fetch_transcript(self, episode: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Fetch transcript for a single episode"""
        if not episode.get('id'):
            return None

        transcript_url = self.get_transcript_url(episode['id'])

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(transcript_url, timeout=30) as response:
                    if response.status == 404:
                        # Try without nx-s1 prefix
                        alt_url = f"https://www.npr.org/transcripts/{episode['id']}"
                        async with session.get(alt_url, timeout=30) as alt_response:
                            if alt_response.status != 200:
                                return None
                            html = await alt_response.text()
                    elif response.status != 200:
                        return None
                    else:
                        html = await response.text()

                    soup = BeautifulSoup(html, 'html.parser')

                    # Find transcript content
                    # NPR transcripts are in <article> or specific transcript divs
                    content = None
                    for selector in ['article', '.transcript', '#transcript',
                                    '.storytext', '.story-text', 'main']:
                        element = soup.select_one(selector)
                        if element:
                            content = element.get_text(separator='\n', strip=True)
                            if len(content) > 500:
                                break

                    if not content or len(content) < 500:
                        return None

                    # Clean up content
                    # Remove common NPR footer elements
                    lines = content.split('\n')
                    clean_lines = []
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        # Skip common footer/nav text
                        if any(skip in line.lower() for skip in [
                            'copyright', 'all rights reserved', 'subscribe to',
                            'sponsor message', 'advertisement', 'click here'
                        ]):
                            continue
                        clean_lines.append(line)

                    content = '\n\n'.join(clean_lines)

                    return {
                        'title': episode['title'],
                        'url': transcript_url,
                        'episode_url': episode.get('url', ''),
                        'content': content,
                        'content_length': len(content),
                        'episode_id': episode['id'],
                        'crawled_at': datetime.now().isoformat(),
                    }

        except Exception as e:
            logger.error(f"Error fetching transcript {transcript_url}: {e}")
            return None

    async def crawl_podcast(self, podcast_key: str, max_episodes: int = 0,
                            use_archive: bool = False) -> Dict[str, Any]:
        """Crawl all transcripts for an NPR podcast"""
        if podcast_key not in NPR_PODCASTS:
            return {'error': f"Unknown podcast: {podcast_key}"}

        config = NPR_PODCASTS[podcast_key]
        transcript_dir = self.output_dir / config['slug'] / "transcripts"
        transcript_dir.mkdir(parents=True, exist_ok=True)

        results = {
            'podcast': config['name'],
            'slug': config['slug'],
            'episodes_found': 0,
            'transcripts_saved': 0,
            'skipped_existing': 0,
            'no_transcript': 0,
            'synced_to_db': 0,
            'errors': [],
        }
        saved_files = []  # Track for DB sync

        print(f"\n{'='*60}")
        print(f"Crawling {config['name']} (NPR)")
        print(f"{'='*60}\n")

        # Discover episodes
        print("Discovering episodes...")
        if use_archive:
            episodes = await self.discover_episodes_from_archive(config)
        else:
            episodes = await self.discover_episodes_from_rss(config)

        results['episodes_found'] = len(episodes)

        if max_episodes > 0:
            episodes = episodes[:max_episodes]

        print(f"\nFound {len(episodes)} episodes. Fetching transcripts...\n")

        # Fetch transcripts
        for i, episode in enumerate(episodes, 1):
            try:
                # Generate filename
                safe_id = episode['id']
                filename = f"{safe_id}.md"
                filepath = transcript_dir / filename

                # Skip existing
                if filepath.exists():
                    results['skipped_existing'] += 1
                    if i % 50 == 0:
                        print(f"  [{i}/{len(episodes)}] Skipped {results['skipped_existing']} existing...")
                    continue

                print(f"  [{i}/{len(episodes)}] Fetching: {episode['title'][:50]}...")

                transcript = await self.fetch_transcript(episode)

                if transcript and transcript.get('content'):
                    # Save transcript
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(f"# {transcript['title']}\n\n")
                        f.write(f"Source: {transcript['url']}\n")
                        f.write(f"Episode: {transcript.get('episode_url', 'N/A')}\n")
                        f.write(f"Crawled: {transcript['crawled_at']}\n\n")
                        f.write("---\n\n")
                        f.write(transcript['content'])

                    results['transcripts_saved'] += 1
                    saved_files.append({
                        'filepath': str(filepath),
                        'title': transcript['title'],
                        'url': transcript['url']
                    })
                    print(f"    ✓ Saved ({transcript['content_length']} chars)")
                else:
                    results['no_transcript'] += 1
                    print(f"    ✗ No transcript available")

                await asyncio.sleep(self.rate_limit)

            except Exception as e:
                results['errors'].append(str(e))
                logger.error(f"Error processing episode: {e}")

        # Sync to database
        if saved_files:
            synced = self._sync_to_database(config['slug'], saved_files)
            results['synced_to_db'] = synced

        print(f"\n{'='*60}")
        print(f"COMPLETE: {config['name']}")
        print(f"  Episodes found: {results['episodes_found']}")
        print(f"  Transcripts saved: {results['transcripts_saved']}")
        print(f"  Skipped existing: {results['skipped_existing']}")
        print(f"  No transcript: {results['no_transcript']}")
        print(f"  Synced to DB: {results['synced_to_db']}")
        if results['errors']:
            print(f"  Errors: {len(results['errors'])}")
        print(f"{'='*60}\n")

        return results

    def _sync_to_database(self, podcast_slug: str, saved_files: List[Dict[str, str]]) -> int:
        """Sync saved transcripts to the SQLite database"""
        try:
            from modules.podcasts.store import PodcastStore

            store = PodcastStore()
            podcast = store.get_podcast_by_slug(podcast_slug)

            if not podcast:
                logger.warning(f"Podcast '{podcast_slug}' not in database, skipping sync")
                return 0

            episodes = store.get_episodes(podcast.id)
            if not episodes:
                logger.warning(f"No episodes found for '{podcast_slug}' in database")
                return 0

            episode_by_title = {}
            for ep in episodes:
                normalized = _normalize_title(ep.title)
                episode_by_title[normalized] = ep

            synced_count = 0
            for saved in saved_files:
                title = saved['title']
                filepath = saved['filepath']

                normalized_title = _normalize_title(title)
                episode = episode_by_title.get(normalized_title)

                if not episode:
                    best_score = 0
                    best_match = None
                    for ep in episodes:
                        score = _fuzzy_match_score(title, ep.title)
                        if score > best_score and score >= 0.7:
                            best_score = score
                            best_match = ep
                    episode = best_match

                if episode:
                    if episode.transcript_status == 'fetched' and episode.transcript_path:
                        continue
                    store.update_episode_transcript_status(
                        episode.id,
                        status='fetched',
                        transcript_path=filepath
                    )
                    synced_count += 1

            return synced_count

        except ImportError as e:
            logger.warning(f"Could not import store module: {e}")
            return 0
        except Exception as e:
            logger.error(f"Error syncing to database: {e}")
            return 0

    async def crawl_all(self, max_episodes_per_podcast: int = 0) -> List[Dict[str, Any]]:
        """Crawl all NPR podcasts"""
        results = []

        for podcast_key in NPR_PODCASTS:
            result = await self.crawl_podcast(podcast_key, max_episodes_per_podcast)
            results.append(result)
            await asyncio.sleep(5)  # Pause between podcasts

        return results


async def main():
    """CLI entrypoint"""
    import sys

    crawler = NPRCrawler()

    if len(sys.argv) < 2:
        print("Usage: python -m modules.podcasts.resolvers.npr_crawler <podcast> [max_episodes]")
        print("\nAvailable NPR podcasts:")
        for key, config in NPR_PODCASTS.items():
            print(f"  {key}: {config['name']}")
        print("\n  all: Crawl all NPR podcasts")
        sys.exit(1)

    podcast = sys.argv[1]
    max_episodes = int(sys.argv[2]) if len(sys.argv) > 2 else 0

    if podcast == 'all':
        results = await crawler.crawl_all(max_episodes)
        total_saved = sum(r.get('transcripts_saved', 0) for r in results)
        print(f"\n{'='*60}")
        print(f"ALL NPR PODCASTS COMPLETE")
        print(f"Total transcripts saved: {total_saved}")
        print(f"{'='*60}\n")
    elif podcast in NPR_PODCASTS:
        await crawler.crawl_podcast(podcast, max_episodes)
    else:
        print(f"Unknown podcast: {podcast}")
        print(f"Available: {', '.join(NPR_PODCASTS.keys())}, all")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
