#!/usr/bin/env python3
"""
Headless Browser Crawler for JavaScript-rendered podcast sites

Uses Playwright to fetch transcripts from sites that require JavaScript rendering.
Currently supports: Dwarkesh Podcast (Substack), 99% Invisible, Colossus
"""

import asyncio
import logging
import re
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)

# Sites that require headless browser
HEADLESS_SITES = {
    'dwarkesh.com': {
        'name': 'Dwarkesh Podcast',
        'index_url': 'https://www.dwarkesh.com/podcast',
        'archive_url': 'https://www.dwarkesh.com/podcast/archive',
        'episode_pattern': r'/p/[^/]+',
        'slug': 'dwarkesh-podcast',
        'rate_limit': 2.0,  # seconds between requests
    },
    '99percentinvisible.org': {
        'name': '99% Invisible',
        'index_url': 'https://99percentinvisible.org/episodes/',
        'episode_pattern': r'/episode/[^/]+/transcript',
        'slug': '99-percent-invisible',
        'rate_limit': 2.0,
    },
    'joincolossus.com': {
        'name': 'Invest Like the Best',
        'index_url': 'https://www.joincolossus.com/episodes',
        'episode_pattern': r'/episodes/[^/]+',
        'slug': 'invest-like-the-best',
        'rate_limit': 2.0,
    },
}


class HeadlessCrawler:
    """Crawler for JavaScript-rendered podcast transcript sites"""

    def __init__(self, output_dir: str = "data/podcasts"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def crawl_dwarkesh(self, max_episodes: int = 100) -> Dict[str, Any]:
        """
        Crawl all Dwarkesh Podcast episodes using headless browser.

        Dwarkesh uses Substack which is fully JavaScript rendered.
        The /podcast/archive page lists all episodes.
        """
        from modules.browser import Browser

        config = HEADLESS_SITES['dwarkesh.com']
        slug = config['slug']
        transcript_dir = self.output_dir / slug / "transcripts"
        transcript_dir.mkdir(parents=True, exist_ok=True)

        results = {
            'podcast': config['name'],
            'episodes_found': 0,
            'transcripts_saved': 0,
            'errors': [],
        }

        print(f"Crawling {config['name']} with headless browser...")

        async with Browser(timeout=60000) as browser:
            # First, get the archive page to find all episode links
            archive_url = config['archive_url']
            print(f"Fetching archive page: {archive_url}")

            all_links = await browser.get_all_links(archive_url, pattern=r"/p/", wait_for="load")

            # Filter to only episode pages (not profile, about, etc.)
            episode_links = [
                link for link in all_links
                if re.search(r'/p/[a-z0-9-]+$', link) and 'subscribe' not in link.lower()
            ]

            # Remove duplicates
            episode_links = list(set(episode_links))
            results['episodes_found'] = len(episode_links)

            print(f"Found {len(episode_links)} episode links")

            # Limit to max_episodes
            episode_links = episode_links[:max_episodes]

            # Fetch each episode
            for i, url in enumerate(episode_links, 1):
                try:
                    print(f"  [{i}/{len(episode_links)}] Fetching: {url}")

                    # Get the page content - Substack has transcript in the page
                    content = await browser.get_text_content(url, wait_for="load")

                    if content and len(content) > 500:  # Minimum content length
                        # Extract title from URL
                        slug_match = re.search(r'/p/([^/]+)$', url)
                        episode_slug = slug_match.group(1) if slug_match else f"episode-{i}"

                        # Generate filename
                        filename = f"{episode_slug}.md"
                        filepath = transcript_dir / filename

                        # Save transcript
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(f"# {episode_slug.replace('-', ' ').title()}\n\n")
                            f.write(f"Source: {url}\n")
                            f.write(f"Crawled: {datetime.now().isoformat()}\n\n")
                            f.write("---\n\n")
                            f.write(content)

                        results['transcripts_saved'] += 1
                        print(f"    Saved: {filename} ({len(content)} chars)")
                    else:
                        results['errors'].append(f"Empty content: {url}")
                        print(f"    Warning: Empty or short content")

                    # Rate limiting
                    await asyncio.sleep(config['rate_limit'])

                except Exception as e:
                    error_msg = f"Error fetching {url}: {str(e)}"
                    results['errors'].append(error_msg)
                    print(f"    Error: {str(e)}")

        print(f"\nCompleted: {results['transcripts_saved']}/{results['episodes_found']} transcripts saved")
        return results

    async def crawl_99pi(self, max_episodes: int = 100, max_pages: int = 66) -> Dict[str, Any]:
        """
        Crawl 99% Invisible episodes with full pagination.

        Episodes are at /episode/{slug}/, transcripts at /episode/{slug}/transcript
        The archive has 66 pages of episodes (~780+ total).
        """
        from modules.browser import Browser

        config = HEADLESS_SITES['99percentinvisible.org']
        slug = config['slug']
        transcript_dir = self.output_dir / slug / "transcripts"
        transcript_dir.mkdir(parents=True, exist_ok=True)

        results = {
            'podcast': config['name'],
            'episodes_found': 0,
            'transcripts_saved': 0,
            'skipped_existing': 0,
            'errors': [],
        }

        print(f"Crawling {config['name']} with headless browser...")
        print(f"  Will crawl up to {max_pages} archive pages")

        async with Browser(timeout=60000) as browser:
            # Collect episode links from all paginated archive pages
            all_episode_links = set()

            for page_num in range(1, max_pages + 1):
                if page_num == 1:
                    page_url = config['index_url']
                else:
                    page_url = f"{config['index_url']}page/{page_num}/"

                print(f"  Fetching page {page_num}/{max_pages}: {page_url}")

                try:
                    links = await browser.get_all_links(page_url, pattern=r"/episode/", wait_for="load")

                    # Filter to episode pages
                    page_episodes = 0
                    for link in links:
                        if re.search(r'/episode/[^/]+/?$', link) and 'download' not in link and 'transcript' not in link:
                            transcript_url = link.rstrip('/') + '/transcript'
                            if transcript_url not in all_episode_links:
                                all_episode_links.add(transcript_url)
                                page_episodes += 1

                    print(f"    Found {page_episodes} new episodes (total: {len(all_episode_links)})")

                    # Stop if we have enough episodes
                    if len(all_episode_links) >= max_episodes:
                        print(f"  Reached max_episodes limit ({max_episodes})")
                        break

                    # Rate limit between archive pages
                    await asyncio.sleep(1.0)

                except Exception as e:
                    print(f"    Error fetching page {page_num}: {str(e)}")
                    # If page doesn't exist, we've hit the end
                    if "404" in str(e) or page_num > 66:
                        break

            episode_links = list(all_episode_links)[:max_episodes]
            results['episodes_found'] = len(episode_links)

            print(f"\nFound {len(episode_links)} total episode links")
            print(f"Starting transcript downloads...\n")

            # Fetch each transcript
            for i, url in enumerate(episode_links, 1):
                try:
                    # Extract slug from URL to check if already exists
                    slug_match = re.search(r'/episode/([^/]+)/', url)
                    episode_slug = slug_match.group(1) if slug_match else f"episode-{i}"
                    filename = f"{episode_slug}.md"
                    filepath = transcript_dir / filename

                    # Skip if already exists
                    if filepath.exists():
                        results['skipped_existing'] += 1
                        if i % 50 == 0:
                            print(f"  [{i}/{len(episode_links)}] Skipped {results['skipped_existing']} existing...")
                        continue

                    print(f"  [{i}/{len(episode_links)}] Fetching: {url}")

                    content = await browser.get_text_content(url, wait_for="load")

                    if content and len(content) > 500:
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(f"# {episode_slug.replace('-', ' ').title()}\n\n")
                            f.write(f"Source: {url}\n")
                            f.write(f"Crawled: {datetime.now().isoformat()}\n\n")
                            f.write("---\n\n")
                            f.write(content)

                        results['transcripts_saved'] += 1
                        print(f"    Saved: {filename} ({len(content)} chars)")
                    else:
                        results['errors'].append(f"Empty content: {url}")
                        print(f"    Warning: Empty or short content")

                    await asyncio.sleep(config['rate_limit'])

                except Exception as e:
                    error_msg = f"Error fetching {url}: {str(e)}"
                    results['errors'].append(error_msg)
                    print(f"    Error: {str(e)}")

        print(f"\nCompleted: {results['transcripts_saved']} new, {results['skipped_existing']} skipped")
        return results


async def main():
    """CLI entrypoint"""
    import sys

    crawler = HeadlessCrawler()

    if len(sys.argv) < 2:
        print("Usage: python -m modules.podcasts.resolvers.headless_crawler <site>")
        print("\nAvailable sites:")
        for key, config in HEADLESS_SITES.items():
            print(f"  {key}: {config['name']}")
        sys.exit(1)

    site = sys.argv[1]
    max_episodes = int(sys.argv[2]) if len(sys.argv) > 2 else 100

    if 'dwarkesh' in site.lower():
        results = await crawler.crawl_dwarkesh(max_episodes)
    elif '99' in site.lower() or 'invisible' in site.lower():
        # For 99PI, max_episodes=0 means all episodes (default 800)
        episodes = max_episodes if max_episodes > 0 else 800
        results = await crawler.crawl_99pi(max_episodes=episodes, max_pages=66)
    else:
        print(f"Unknown site: {site}")
        print("Available: dwarkesh, 99pi")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"Results for {results['podcast']}:")
    print(f"  Episodes found: {results['episodes_found']}")
    print(f"  Transcripts saved: {results['transcripts_saved']}")
    if results['errors']:
        print(f"  Errors: {len(results['errors'])}")


if __name__ == "__main__":
    asyncio.run(main())
