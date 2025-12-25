#!/usr/bin/env python3
"""
Podscripts.co Crawler (Headless Browser)

Scrapes free transcripts from podscripts.co - a third-party AI transcription aggregator.
This site provides free public access to AI-generated transcripts for many popular podcasts.

Uses headless browser because podscripts.co is JavaScript-rendered.

Target podcasts from our 73-podcast list that are available:
- Pivot (723 episodes)
- No Such Thing As A Fish (642 episodes)
- All-In Podcast
- Prof G
- Hard Fork
- And more...
"""

import asyncio
import logging
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urljoin
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

# Podcasts available on Podscripts that match our 73 podcast list
# Podscripts uses AI-generated transcripts - free public access
PODSCRIPTS_PODCASTS = {
    # Tech/Business
    'pivot': {
        'name': 'Pivot',
        'url': 'https://podscripts.co/podcasts/pivot/',
        'slug': 'pivot',
        'episodes': 723,
    },
    'all-in-with-chamath-jason-sacks-friedberg': {
        'name': 'All-In Podcast',
        'url': 'https://podscripts.co/podcasts/all-in-with-chamath-jason-sacks-friedberg/',
        'slug': 'all-in-podcast',
        'episodes': 250,
    },
    'the-prof-g-pod-with-scott-galloway': {
        'name': 'Prof G',
        'url': 'https://podscripts.co/podcasts/the-prof-g-pod-with-scott-galloway/',
        'slug': 'prof-g',
        'episodes': 500,
    },
    'hard-fork': {
        'name': 'Hard Fork',
        'url': 'https://podscripts.co/podcasts/hard-fork/',
        'slug': 'hard-fork',
        'episodes': 150,
    },
    'acquired': {
        'name': 'Acquired',
        'url': 'https://podscripts.co/podcasts/acquired/',
        'slug': 'acquired',
        'episodes': 200,
    },
    'invest-like-the-best-with-patrick-oshaughnessy': {
        'name': 'Invest Like the Best',
        'url': 'https://podscripts.co/podcasts/invest-like-the-best-with-patrick-oshaughnessy/',
        'slug': 'invest-like-the-best',
        'episodes': 400,
    },
    'a16z-podcast': {
        'name': 'a16z Podcast',
        'url': 'https://podscripts.co/podcasts/a16z-podcast/',
        'slug': 'a16z-podcast',
        'episodes': 800,
    },

    # Economics/Finance
    'oddlots': {
        'name': 'Odd Lots',
        'url': 'https://podscripts.co/podcasts/odd-lots/',
        'slug': 'odd-lots',
        'episodes': 500,
    },
    'macro-voices': {
        'name': 'Macro Voices',
        'url': 'https://podscripts.co/podcasts/macro-voices/',
        'slug': 'macro-voices',
        'episodes': 400,
    },

    # Knowledge/Education
    'no-such-thing-as-a-fish': {
        'name': 'No Such Thing As A Fish',
        'url': 'https://podscripts.co/podcasts/no-such-thing-as-a-fish/',
        'slug': 'no-such-thing-as-a-fish',
        'episodes': 642,
    },
    'revisionist-history': {
        'name': 'Revisionist History',
        'url': 'https://podscripts.co/podcasts/revisionist-history/',
        'slug': 'revisionist-history',
        'episodes': 100,
    },
    'cortex': {
        'name': 'Cortex',
        'url': 'https://podscripts.co/podcasts/cortex/',
        'slug': 'cortex',
        'episodes': 150,
    },
    'radiolab': {
        'name': 'Radiolab',
        'url': 'https://podscripts.co/podcasts/radiolab/',
        'slug': 'radiolab',
        'episodes': 600,
    },
    'conan-obrien-needs-a-friend': {
        'name': 'Conan O\'Brien Needs A Friend',
        'url': 'https://podscripts.co/podcasts/conan-obrien-needs-a-friend/',
        'slug': 'conan-obrien-needs-a-friend',
        'episodes': 300,
    },
    'the-ezra-klein-show': {
        'name': 'The Ezra Klein Show',
        'url': 'https://podscripts.co/podcasts/the-ezra-klein-show/',
        'slug': 'ezra-klein-show',
        'episodes': 500,
    },
    'we-can-do-hard-things': {
        'name': 'We Can Do Hard Things',
        'url': 'https://podscripts.co/podcasts/we-can-do-hard-things/',
        'slug': 'we-can-do-hard-things',
        'episodes': 400,
    },
    'smartless': {
        'name': 'SmartLess',
        'url': 'https://podscripts.co/podcasts/smartless/',
        'slug': 'smartless',
        'episodes': 200,
    },
}


class PodscriptsCrawler:
    """Crawler for podscripts.co free transcripts using headless browser"""

    def __init__(self, output_dir: str = "data/podcasts"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.base_url = "https://podscripts.co"
        # Robots.txt allows all crawling, but we're polite with 2s between requests
        self.rate_limit = 2.0  # seconds between requests

    async def crawl_podcast(self, podcast_key: str, max_episodes: int = 0) -> Dict[str, Any]:
        """Crawl all transcripts for a podcast using headless browser"""
        from modules.browser import Browser

        if podcast_key not in PODSCRIPTS_PODCASTS:
            print(f"Unknown podcast: {podcast_key}")
            return {'error': f"Unknown podcast: {podcast_key}"}

        config = PODSCRIPTS_PODCASTS[podcast_key]
        slug = config['slug']
        transcript_dir = self.output_dir / slug / "transcripts"
        transcript_dir.mkdir(parents=True, exist_ok=True)

        results = {
            'podcast': config['name'],
            'episodes_found': 0,
            'transcripts_saved': 0,
            'skipped_existing': 0,
            'synced_to_db': 0,
            'errors': [],
        }
        saved_files = []  # Track for DB sync

        print(f"\nCrawling {config['name']} from Podscripts.co (headless browser)...")

        async with Browser(timeout=60000) as browser:
            # Phase 1: Discover all episode URLs using infinite scroll
            all_episode_links = set()

            print(f"  Loading archive page with infinite scroll...")

            # Create a page and scroll to load all episodes
            page = await browser._context.new_page()
            try:
                await page.goto(config['url'], wait_until="load", timeout=60000)

                # Scroll to load more episodes (infinite scroll)
                prev_count = 0
                scroll_attempts = 0
                max_scroll_attempts = 50  # Limit scrolling

                while scroll_attempts < max_scroll_attempts:
                    # Extract all current links
                    links = await page.evaluate("""
                        () => Array.from(document.querySelectorAll('a[href]'))
                            .map(a => a.href)
                            .filter(href => href.includes('/podcasts/""" + podcast_key + """/'))
                    """)

                    # Filter to episode pages
                    for link in links:
                        parts = link.rstrip('/').split('/')
                        if len(parts) >= 5:
                            episode_slug = parts[-1]
                            if episode_slug and episode_slug != 'page' and not episode_slug.isdigit():
                                all_episode_links.add(link)

                    current_count = len(all_episode_links)
                    print(f"    Scroll {scroll_attempts + 1}: Found {current_count} episodes...")

                    # Check if we found new episodes
                    if current_count == prev_count:
                        # Try scrolling more
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await asyncio.sleep(1.5)  # Wait for content to load

                        # Check again after scroll
                        links = await page.evaluate("""
                            () => Array.from(document.querySelectorAll('a[href]'))
                                .map(a => a.href)
                                .filter(href => href.includes('/podcasts/""" + podcast_key + """/'))
                        """)
                        for link in links:
                            parts = link.rstrip('/').split('/')
                            if len(parts) >= 5:
                                episode_slug = parts[-1]
                                if episode_slug and episode_slug != 'page' and not episode_slug.isdigit():
                                    all_episode_links.add(link)

                        if len(all_episode_links) == prev_count:
                            print(f"    No new episodes after scroll, discovery complete")
                            break

                    prev_count = len(all_episode_links)
                    scroll_attempts += 1

                    # Scroll to bottom
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(1.0)

            finally:
                await page.close()

            episode_urls = list(all_episode_links)
            results['episodes_found'] = len(episode_urls)

            if max_episodes > 0:
                episode_urls = episode_urls[:max_episodes]

            print(f"\nDiscovered {len(episode_urls)} episodes. Starting transcript downloads...\n")

            # Phase 2: Fetch each transcript
            for i, url in enumerate(episode_urls, 1):
                try:
                    # Generate filename from URL
                    episode_slug = url.rstrip('/').split('/')[-1]
                    filename = f"{episode_slug}.md"
                    filepath = transcript_dir / filename

                    # Skip if exists
                    if filepath.exists():
                        results['skipped_existing'] += 1
                        if i % 50 == 0:
                            print(f"  [{i}/{len(episode_urls)}] Skipped {results['skipped_existing']} existing...")
                        continue

                    print(f"  [{i}/{len(episode_urls)}] Fetching: {episode_slug}")

                    # Get transcript content using headless browser
                    content = await browser.get_text_content(url, wait_for="load")

                    if content and len(content) > 500:
                        # Try to extract just the transcript portion
                        # Podscripts has the transcript after episode metadata
                        lines = content.split('\n')

                        # Find where the transcript starts (after "Transcript" header)
                        transcript_start = 0
                        for idx, line in enumerate(lines):
                            if 'transcript' in line.lower() and len(line) < 50:
                                transcript_start = idx + 1
                                break

                        if transcript_start > 0:
                            transcript_content = '\n'.join(lines[transcript_start:])
                        else:
                            transcript_content = content

                        # Get title from first line or URL
                        title = lines[0] if lines else episode_slug.replace('-', ' ').title()

                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(f"# {title}\n\n")
                            f.write(f"Source: {url}\n")
                            f.write(f"Crawled: {datetime.now().isoformat()}\n\n")
                            f.write("---\n\n")
                            f.write(transcript_content)

                        results['transcripts_saved'] += 1
                        saved_files.append({
                            'filepath': str(filepath),
                            'title': title,
                            'url': url
                        })
                        print(f"    Saved: {filename} ({len(transcript_content)} chars)")
                    else:
                        results['errors'].append(f"Empty content: {url}")
                        print(f"    Warning: Empty or short content")

                    await asyncio.sleep(self.rate_limit)

                except Exception as e:
                    error_msg = f"Error fetching {url}: {str(e)}"
                    results['errors'].append(error_msg)
                    print(f"    Error: {str(e)}")

        # Sync to database
        if saved_files:
            synced = self._sync_to_database(slug, saved_files)
            results['synced_to_db'] = synced
            print(f"  Synced {synced} transcripts to database")

        print(f"\nCompleted: {results['transcripts_saved']} new, {results['skipped_existing']} skipped, {results['synced_to_db']} synced to DB")
        return results

    def _sync_to_database(self, podcast_slug: str, saved_files: List[Dict[str, str]]) -> int:
        """Sync saved transcripts to the SQLite database

        Matches transcripts to episodes by fuzzy title matching and updates
        transcript_status to 'fetched'.
        """
        try:
            from modules.podcasts.store import PodcastStore

            store = PodcastStore()
            podcast = store.get_podcast_by_slug(podcast_slug)

            if not podcast:
                logger.warning(f"Podcast '{podcast_slug}' not in database, skipping sync")
                return 0

            episodes = store.get_episodes_by_podcast(podcast.id)
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
        """Crawl all podcasts in PODSCRIPTS_PODCASTS"""
        results = []

        for podcast_key in PODSCRIPTS_PODCASTS:
            print(f"\n{'='*60}")
            print(f"Starting {PODSCRIPTS_PODCASTS[podcast_key]['name']}...")
            print(f"{'='*60}")

            result = await self.crawl_podcast(podcast_key, max_episodes_per_podcast)
            results.append(result)
            await asyncio.sleep(5)  # Pause between podcasts

        # Print summary
        total_saved = sum(r.get('transcripts_saved', 0) for r in results)
        total_found = sum(r.get('episodes_found', 0) for r in results)

        print(f"\n{'='*60}")
        print("PODSCRIPTS CRAWL COMPLETE")
        print(f"{'='*60}")
        print(f"Podcasts: {len(results)}")
        print(f"Episodes found: {total_found}")
        print(f"Transcripts saved: {total_saved}")
        print(f"{'='*60}\n")

        return results


async def main():
    """CLI entrypoint"""
    import sys

    crawler = PodscriptsCrawler()

    if len(sys.argv) < 2:
        print("Usage: python -m modules.podcasts.resolvers.podscripts_crawler <podcast> [max_episodes]")
        print("\nAvailable podcasts:")
        for key, config in PODSCRIPTS_PODCASTS.items():
            print(f"  {key}: {config['name']} (~{config['episodes']} episodes)")
        print("\n  all: Crawl all podcasts")
        sys.exit(1)

    podcast = sys.argv[1]
    max_episodes = int(sys.argv[2]) if len(sys.argv) > 2 else 0

    if podcast == 'all':
        await crawler.crawl_all(max_episodes)
    elif podcast in PODSCRIPTS_PODCASTS:
        results = await crawler.crawl_podcast(podcast, max_episodes)

        print(f"\n{'='*60}")
        print(f"Results for {results.get('podcast', 'Unknown')}:")
        print(f"  Episodes found: {results.get('episodes_found', 0)}")
        print(f"  Transcripts saved: {results.get('transcripts_saved', 0)}")
        print(f"  Skipped existing: {results.get('skipped_existing', 0)}")
        if results.get('errors'):
            print(f"  Errors: {len(results['errors'])}")
    else:
        print(f"Unknown podcast: {podcast}")
        print(f"Available: {', '.join(PODSCRIPTS_PODCASTS.keys())}, all")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
