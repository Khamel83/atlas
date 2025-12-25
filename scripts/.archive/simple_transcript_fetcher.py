#!/usr/bin/env python3
"""
Simple Transcript Fetcher - The MVP

A dead-simple hourly script that:
1. Checks RSS feeds for new episodes
2. Fetches transcript from known source
3. Saves to disk
4. Moves to next podcast

No parallelism. No fancy resolver chains. Just works.

Usage:
    python scripts/simple_transcript_fetcher.py
    python scripts/simple_transcript_fetcher.py --once  # Single run, no loop
    python scripts/simple_transcript_fetcher.py --podcast pivot  # Single podcast
"""

import argparse
import hashlib
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

import requests
import feedparser
from bs4 import BeautifulSoup

# Simple config - just add podcasts here
PODCASTS = {
    # Format: slug -> {rss, source, source_id (optional)}

    # Podscripts podcasts (40+)
    'pivot': {'rss': 'https://feeds.megaphone.fm/pivot', 'source': 'podscripts'},
    'all-in-podcast': {'rss': 'https://feeds.megaphone.fm/all-in-with-chamath-jason-sacks-friedberg', 'source': 'podscripts', 'source_id': 'all-in-with-chamath-jason-sacks-friedberg'},
    'hard-fork': {'rss': 'https://feeds.simplecast.com/l2i9YnTd', 'source': 'podscripts'},
    'acquired': {'rss': 'https://acquired.fm/feed/', 'source': 'podscripts'},
    'lex-fridman-podcast': {'rss': 'https://lexfridman.com/feed/podcast/', 'source': 'podscripts'},
    'huberman-lab': {'rss': 'https://feeds.megaphone.fm/hubermanlab', 'source': 'podscripts'},
    'the-tim-ferriss-show': {'rss': 'https://rss.art19.com/tim-ferriss-show', 'source': 'podscripts', 'source_id': 'the-tim-ferriss-show'},
    'ezra-klein-show': {'rss': 'https://feeds.simplecast.com/82FI35Px', 'source': 'podscripts', 'source_id': 'the-ezra-klein-show'},
    'freakonomics-radio': {'rss': 'https://feeds.simplecast.com/Y8lFbOT4', 'source': 'podscripts'},
    'hidden-brain': {'rss': 'https://feeds.simplecast.com/kwWc0lhf', 'source': 'podscripts'},
    'revisionist-history': {'rss': 'https://feeds.megaphone.fm/revisionisthistory', 'source': 'podscripts'},
    'the-bill-simmons-podcast': {'rss': 'https://feeds.megaphone.fm/the-bill-simmons-podcast', 'source': 'podscripts'},
    'the-big-picture': {'rss': 'https://feeds.megaphone.fm/the-big-picture', 'source': 'podscripts'},
    'the-journal': {'rss': 'https://feeds.megaphone.fm/WSJ8460789702', 'source': 'podscripts'},
    'today-explained': {'rss': 'https://feeds.megaphone.fm/today-explained', 'source': 'podscripts'},

    # Tapesearch podcasts
    'land-of-the-giants': {'rss': 'https://feeds.megaphone.fm/landofthegiants', 'source': 'tapesearch', 'source_id': '1465767420'},
    'the-vergecast': {'rss': 'https://feeds.megaphone.fm/vergecast', 'source': 'tapesearch', 'source_id': '430333725'},
    'decoder-with-nilay-patel': {'rss': 'https://feeds.megaphone.fm/decoder', 'source': 'tapesearch', 'source_id': '1011668648'},

    # Direct HTML (with cookies if needed)
    'stratechery': {'rss': 'https://stratechery.passport.online/feed/rss', 'source': 'direct', 'selector': '.entry-content'},
    'conversations-with-tyler': {'rss': 'https://feeds.megaphone.fm/MWT8026498498', 'source': 'direct', 'selector': '.generic__content'},
}

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class Episode:
    title: str
    url: str
    published: datetime
    guid: str


class SimpleTranscriptFetcher:
    """Simple, reliable transcript fetcher."""

    def __init__(self, output_dir: str = "data/podcasts", state_file: str = "data/fetcher_state.json"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = Path(state_file)
        self.state = self._load_state()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

    def _load_state(self) -> Dict:
        """Load state of what we've already fetched."""
        if self.state_file.exists():
            with open(self.state_file) as f:
                return json.load(f)
        return {'fetched': {}}

    def _save_state(self):
        """Save state to disk."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)

    def _is_fetched(self, podcast_slug: str, episode_guid: str) -> bool:
        """Check if we already fetched this episode."""
        key = f"{podcast_slug}:{hashlib.md5(episode_guid.encode()).hexdigest()[:12]}"
        return key in self.state.get('fetched', {})

    def _mark_fetched(self, podcast_slug: str, episode_guid: str, transcript_path: str):
        """Mark episode as fetched."""
        key = f"{podcast_slug}:{hashlib.md5(episode_guid.encode()).hexdigest()[:12]}"
        if 'fetched' not in self.state:
            self.state['fetched'] = {}
        self.state['fetched'][key] = {
            'path': transcript_path,
            'fetched_at': datetime.now().isoformat()
        }
        self._save_state()

    def get_new_episodes(self, podcast_slug: str, config: Dict, max_age_hours: int = 168) -> List[Episode]:
        """Get episodes from RSS that we haven't fetched yet."""
        episodes = []
        try:
            feed = feedparser.parse(config['rss'])
            cutoff = datetime.now() - timedelta(hours=max_age_hours)

            for entry in feed.entries[:20]:  # Only check recent 20
                # Parse published date
                published = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    published = datetime(*entry.updated_parsed[:6])
                else:
                    published = datetime.now()

                # Skip old episodes
                if published < cutoff:
                    continue

                guid = entry.get('id', entry.get('link', entry.title))

                # Skip if already fetched
                if self._is_fetched(podcast_slug, guid):
                    continue

                # Get episode URL
                url = entry.get('link', '')

                episodes.append(Episode(
                    title=entry.title,
                    url=url,
                    published=published,
                    guid=guid
                ))

        except Exception as e:
            logger.error(f"Error parsing RSS for {podcast_slug}: {e}")

        return episodes

    def fetch_from_podscripts(self, episode: Episode, config: Dict) -> Optional[str]:
        """Fetch transcript from podscripts.co"""
        # Create slug from title
        slug = re.sub(r'[^\w\s-]', '', episode.title.lower())
        slug = re.sub(r'[-\s]+', '-', slug).strip('-')[:100]

        podcast_id = config.get('source_id', config.get('rss', '').split('/')[-1])

        # Try direct URL first
        url = f"https://podscripts.co/podcasts/{podcast_id}/{slug}"

        try:
            response = self.session.get(url, timeout=30)
            if response.status_code == 200 and 'podcast-transcript' in response.text.lower():
                soup = BeautifulSoup(response.content, 'html.parser')

                # Try various selectors
                for selector in ['.podcast-transcript', '.transcript-text', '.single-sentence', '[class*="transcript"]']:
                    elements = soup.select(selector)
                    if elements:
                        text = '\n\n'.join(el.get_text(separator=' ', strip=True) for el in elements)
                        if len(text) > 500:
                            return text

        except Exception as e:
            logger.debug(f"Podscripts fetch failed: {e}")

        return None

    def fetch_from_tapesearch(self, episode: Episode, config: Dict) -> Optional[str]:
        """Fetch transcript from tapesearch.com"""
        source_id = config.get('source_id')
        if not source_id:
            return None

        podcast_slug = config.get('rss', '').split('/')[-1]

        # Get podcast page to find episode
        try:
            podcast_url = f"https://www.tapesearch.com/podcast/{podcast_slug}/{source_id}"
            response = self.session.get(podcast_url, timeout=30)

            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.content, 'html.parser')

            # Find matching episode link
            title_words = set(word.lower() for word in re.findall(r'\w+', episode.title) if len(word) > 3)

            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                if '/episode/' not in href:
                    continue

                link_text = link.get_text().lower()
                link_words = set(word.lower() for word in re.findall(r'\w+', link_text) if len(word) > 3)

                overlap = len(title_words & link_words)
                if overlap >= min(3, len(title_words) * 0.4):
                    # Found it - fetch transcript
                    episode_url = href if href.startswith('http') else f"https://www.tapesearch.com{href}"

                    ep_response = self.session.get(episode_url, timeout=30)
                    if ep_response.status_code == 200:
                        ep_soup = BeautifulSoup(ep_response.content, 'html.parser')

                        # Extract transcript from table
                        transcript_parts = []
                        for row in ep_soup.find_all('tr'):
                            cells = row.find_all('td')
                            if len(cells) >= 2:
                                text = cells[1].get_text(strip=True)
                                if text and len(text) > 5:
                                    transcript_parts.append(text)

                        if transcript_parts:
                            return '\n\n'.join(transcript_parts)
                    break

        except Exception as e:
            logger.debug(f"Tapesearch fetch failed: {e}")

        return None

    def fetch_direct(self, episode: Episode, config: Dict) -> Optional[str]:
        """Fetch transcript directly from episode URL."""
        if not episode.url:
            return None

        selector = config.get('selector', '.entry-content, .post-content, article')

        try:
            response = self.session.get(episode.url, timeout=30)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')

                for sel in selector.split(','):
                    elem = soup.select_one(sel.strip())
                    if elem:
                        text = elem.get_text(separator='\n', strip=True)
                        if len(text) > 1000:
                            return text

        except Exception as e:
            logger.debug(f"Direct fetch failed: {e}")

        return None

    def fetch_transcript(self, episode: Episode, config: Dict) -> Optional[str]:
        """Fetch transcript using configured source."""
        source = config.get('source', 'podscripts')

        if source == 'podscripts':
            return self.fetch_from_podscripts(episode, config)
        elif source == 'tapesearch':
            return self.fetch_from_tapesearch(episode, config)
        elif source == 'direct':
            return self.fetch_direct(episode, config)

        return None

    def save_transcript(self, podcast_slug: str, episode: Episode, content: str) -> str:
        """Save transcript to disk."""
        # Create directory (matches main system: data/podcasts/{slug}/transcripts/)
        podcast_dir = self.output_dir / podcast_slug / "transcripts"
        podcast_dir.mkdir(parents=True, exist_ok=True)

        # Create filename
        date_str = episode.published.strftime('%Y-%m-%d')
        title_slug = re.sub(r'[^\w\s-]', '', episode.title.lower())
        title_slug = re.sub(r'[-\s]+', '-', title_slug).strip('-')[:80]
        filename = f"{date_str}_{title_slug}.md"

        filepath = podcast_dir / filename

        # Write content
        with open(filepath, 'w') as f:
            f.write(f"# {episode.title}\n\n")
            f.write(f"**Date:** {episode.published.strftime('%Y-%m-%d')}\n\n")
            f.write(f"**Source:** {podcast_slug}\n\n")
            f.write("---\n\n")
            f.write(content)

        return str(filepath)

    def process_podcast(self, slug: str, config: Dict) -> int:
        """Process a single podcast. Returns number of transcripts fetched."""
        logger.info(f"Checking {slug}...")

        episodes = self.get_new_episodes(slug, config)

        if not episodes:
            logger.info(f"  No new episodes for {slug}")
            return 0

        fetched = 0
        for episode in episodes:
            logger.info(f"  Found: {episode.title}")

            transcript = self.fetch_transcript(episode, config)

            if transcript and len(transcript) > 500:
                filepath = self.save_transcript(slug, episode, transcript)
                self._mark_fetched(slug, episode.guid, filepath)
                logger.info(f"  ✅ Saved: {filepath}")
                fetched += 1
            else:
                logger.warning(f"  ❌ No transcript found for: {episode.title}")

        return fetched

    def run_once(self, podcast_filter: Optional[str] = None):
        """Run through all podcasts once."""
        total_fetched = 0

        podcasts = PODCASTS
        if podcast_filter:
            podcasts = {k: v for k, v in PODCASTS.items() if k == podcast_filter}

        for slug, config in podcasts.items():
            try:
                fetched = self.process_podcast(slug, config)
                total_fetched += fetched

                # Rate limiting - be gentle
                time.sleep(5)

            except Exception as e:
                logger.error(f"Error processing {slug}: {e}")
                continue

        logger.info(f"Done. Fetched {total_fetched} transcripts.")
        return total_fetched

    def run_loop(self, interval_minutes: int = 60):
        """Run in a loop, checking every interval."""
        logger.info(f"Starting fetcher loop (every {interval_minutes} minutes)")

        while True:
            try:
                self.run_once()
            except Exception as e:
                logger.error(f"Error in run loop: {e}")

            logger.info(f"Sleeping {interval_minutes} minutes...")
            time.sleep(interval_minutes * 60)


def main():
    parser = argparse.ArgumentParser(description='Simple transcript fetcher')
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    parser.add_argument('--podcast', type=str, help='Only process this podcast')
    parser.add_argument('--interval', type=int, default=60, help='Minutes between runs')
    parser.add_argument('--output', type=str, default='data/podcasts', help='Output directory')

    args = parser.parse_args()

    fetcher = SimpleTranscriptFetcher(output_dir=args.output)

    if args.once or args.podcast:
        fetcher.run_once(podcast_filter=args.podcast)
    else:
        fetcher.run_loop(interval_minutes=args.interval)


if __name__ == '__main__':
    main()
