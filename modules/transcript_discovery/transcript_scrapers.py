#!/usr/bin/env python3
"""
Transcript Scrapers for Different Sources

Specialized scrapers for each transcript source type identified in your system:
- RSS feeds (already working)
- Listen Notes API
- TapeSearch
- PodScripts
- HappyScribe
- Apple Podcasts (via web scraping)
- Spotify (via web scraping)
- YouTube (auto-captions)
"""

import requests
import time
import json
import re
from typing import Dict, List, Optional, Any
from urllib.parse import quote_plus, urljoin
from dataclasses import dataclass
import logging
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

@dataclass
class TranscriptResult:
    """Result from a transcript search"""
    source: str
    found: bool
    transcript_url: Optional[str] = None
    transcript_text: Optional[str] = None
    metadata: Dict[str, Any] = None
    error: Optional[str] = None

class TranscriptScraperBase:
    """Base class for transcript scrapers"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

    def search(self, show_name: str, episode_title: str = None) -> TranscriptResult:
        """Search for transcripts - to be implemented by subclasses"""
        raise NotImplementedError

class RSSFeedScraper(TranscriptScraperBase):
    """Enhanced RSS feed scraper for direct transcript extraction"""

    def search(self, rss_url: str, max_episodes: int = 10) -> TranscriptResult:
        """Check RSS feed for transcript content"""
        try:
            response = self.session.get(rss_url, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'xml')
            items = soup.find_all('item')[:max_episodes]

            transcript_episodes = []

            for item in items:
                title = item.find('title')
                description = item.find('description')
                link = item.find('link')

                if not title or not description:
                    continue

                title_text = title.get_text()
                desc_text = description.get_text()

                # Look for transcript indicators
                transcript_indicators = [
                    'transcript', 'full text', 'show notes',
                    'read the full', 'episode transcript',
                    'complete transcript', 'text version'
                ]

                found_indicators = []
                for indicator in transcript_indicators:
                    if indicator.lower() in desc_text.lower():
                        found_indicators.append(indicator)

                if found_indicators:
                    episode_data = {
                        'title': title_text,
                        'link': link.get_text() if link else None,
                        'indicators': found_indicators,
                        'description_length': len(desc_text)
                    }
                    transcript_episodes.append(episode_data)

            if transcript_episodes:
                return TranscriptResult(
                    source="rss_feed",
                    found=True,
                    metadata={
                        'episodes_with_transcripts': len(transcript_episodes),
                        'total_episodes_checked': len(items),
                        'episodes': transcript_episodes[:5]  # First 5 examples
                    }
                )
            else:
                return TranscriptResult(
                    source="rss_feed",
                    found=False,
                    metadata={'total_episodes_checked': len(items)}
                )

        except Exception as e:
            return TranscriptResult(
                source="rss_feed",
                found=False,
                error=str(e)
            )

class ListenNotesScraper(TranscriptScraperBase):
    """Scraper for Listen Notes search results"""

    def search(self, show_name: str) -> TranscriptResult:
        """Search Listen Notes for transcript availability"""
        try:
            # Use the search URL format from your data
            search_url = f"https://www.listennotes.com/search/?q={quote_plus(show_name)}"

            response = self.session.get(search_url, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for podcast results
            podcast_results = soup.find_all('div', class_=re.compile(r'podcast|result|episode'))

            transcript_info = []
            for result in podcast_results[:5]:  # Check first 5 results
                # Look for transcript mentions
                text = result.get_text().lower()
                if any(word in text for word in ['transcript', 'full text', 'show notes']):
                    link = result.find('a')
                    if link and link.get('href'):
                        transcript_info.append({
                            'url': urljoin(search_url, link.get('href')),
                            'text_preview': text[:200]
                        })

            return TranscriptResult(
                source="listen_notes",
                found=len(transcript_info) > 0,
                metadata={
                    'search_url': search_url,
                    'potential_transcripts': transcript_info
                }
            )

        except Exception as e:
            return TranscriptResult(
                source="listen_notes",
                found=False,
                error=str(e)
            )

class TapeSearchScraper(TranscriptScraperBase):
    """Scraper for TapeSearch - specializes in podcast transcripts"""

    def search(self, show_name: str) -> TranscriptResult:
        """Search TapeSearch for transcripts"""
        try:
            search_url = f"https://www.tapesearch.com/search?q={quote_plus(show_name)}"

            response = self.session.get(search_url, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # TapeSearch shows transcript availability prominently
            results = soup.find_all('div', class_=re.compile(r'result|episode|transcript'))

            transcript_episodes = []
            for result in results[:10]:
                # Look for direct transcript links or indicators
                transcript_links = result.find_all('a', href=re.compile(r'/transcript/|/episode/'))

                for link in transcript_links:
                    episode_url = urljoin(search_url, link.get('href'))
                    episode_title = link.get_text().strip()

                    if episode_title and len(episode_title) > 5:
                        transcript_episodes.append({
                            'title': episode_title,
                            'url': episode_url
                        })

            return TranscriptResult(
                source="tapesearch",
                found=len(transcript_episodes) > 0,
                metadata={
                    'search_url': search_url,
                    'transcript_episodes': transcript_episodes[:5]
                }
            )

        except Exception as e:
            return TranscriptResult(
                source="tapesearch",
                found=False,
                error=str(e)
            )

class PodScriptsScraper(TranscriptScraperBase):
    """Scraper for PodScripts - another transcript aggregator"""

    def search(self, show_name: str) -> TranscriptResult:
        """Search PodScripts for transcripts"""
        try:
            search_url = f"https://podscripts.co/?q={quote_plus(show_name)}"

            response = self.session.get(search_url, timeout=15)
            response.raise_for_status()

            # PodScripts often returns JSON or has a specific structure
            if 'application/json' in response.headers.get('content-type', ''):
                data = response.json()
                # Handle JSON response
                episodes = data.get('episodes', []) if isinstance(data, dict) else []

                return TranscriptResult(
                    source="podscripts",
                    found=len(episodes) > 0,
                    metadata={
                        'search_url': search_url,
                        'episodes_found': len(episodes),
                        'episodes': episodes[:5]
                    }
                )
            else:
                # Handle HTML response
                soup = BeautifulSoup(response.content, 'html.parser')
                episode_links = soup.find_all('a', href=re.compile(r'/episode/|/transcript/'))

                episodes = []
                for link in episode_links[:5]:
                    episodes.append({
                        'title': link.get_text().strip(),
                        'url': urljoin(search_url, link.get('href'))
                    })

                return TranscriptResult(
                    source="podscripts",
                    found=len(episodes) > 0,
                    metadata={
                        'search_url': search_url,
                        'episodes': episodes
                    }
                )

        except Exception as e:
            return TranscriptResult(
                source="podscripts",
                found=False,
                error=str(e)
            )

class HappyScribeScraper(TranscriptScraperBase):
    """Scraper for HappyScribe podcast search"""

    def search(self, show_name: str) -> TranscriptResult:
        """Search HappyScribe for podcast transcripts"""
        try:
            search_url = f"https://podcasts.happyscribe.com/search?q={quote_plus(show_name)}"

            response = self.session.get(search_url, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for podcast results with transcript availability
            podcast_cards = soup.find_all('div', class_=re.compile(r'podcast|card|result'))

            available_transcripts = []
            for card in podcast_cards[:5]:
                title_elem = card.find(['h1', 'h2', 'h3', 'h4', 'a'])
                if title_elem:
                    title = title_elem.get_text().strip()
                    link = card.find('a')

                    if link and link.get('href'):
                        available_transcripts.append({
                            'title': title,
                            'url': urljoin(search_url, link.get('href'))
                        })

            return TranscriptResult(
                source="happyscribe",
                found=len(available_transcripts) > 0,
                metadata={
                    'search_url': search_url,
                    'transcripts': available_transcripts
                }
            )

        except Exception as e:
            return TranscriptResult(
                source="happyscribe",
                found=False,
                error=str(e)
            )

class TranscriptScraperManager:
    """Manages all transcript scrapers and coordinates searches"""

    def __init__(self):
        self.scrapers = {
            'rss_feed': RSSFeedScraper(),
            'listen_notes': ListenNotesScraper(),
            'tapesearch': TapeSearchScraper(),
            'podscripts': PodScriptsScraper(),
            'happyscribe': HappyScribeScraper()
        }

    def search_all_sources(self, show_name: str, rss_feed: str = None,
                          max_sources: int = 3) -> Dict[str, TranscriptResult]:
        """Search multiple sources for transcripts"""
        results = {}

        # Always try RSS feed first if available
        if rss_feed:
            logger.info(f"Checking RSS feed for {show_name}")
            results['rss_feed'] = self.scrapers['rss_feed'].search(rss_feed)
            time.sleep(1)

        # Try other sources based on priority
        source_priority = ['tapesearch', 'podscripts', 'listen_notes', 'happyscribe']

        sources_tried = 1 if rss_feed else 0
        for source in source_priority:
            if sources_tried >= max_sources:
                break

            logger.info(f"Checking {source} for {show_name}")
            try:
                results[source] = self.scrapers[source].search(show_name)
                sources_tried += 1
                time.sleep(2)  # Rate limiting
            except Exception as e:
                logger.warning(f"Error with {source}: {e}")
                results[source] = TranscriptResult(
                    source=source,
                    found=False,
                    error=str(e)
                )

        return results

    def get_best_sources(self, results: Dict[str, TranscriptResult]) -> List[str]:
        """Identify the best sources that found transcripts"""
        found_sources = []

        for source, result in results.items():
            if result.found:
                # Prioritize sources with more concrete evidence
                if source == 'rss_feed' and result.metadata:
                    episodes = result.metadata.get('episodes_with_transcripts', 0)
                    if episodes > 0:
                        found_sources.append((source, episodes))
                elif source in ['tapesearch', 'podscripts'] and result.metadata:
                    episodes = len(result.metadata.get('transcript_episodes', []))
                    if episodes > 0:
                        found_sources.append((source, episodes))
                else:
                    found_sources.append((source, 1))

        # Sort by number of episodes found
        found_sources.sort(key=lambda x: x[1], reverse=True)
        return [source for source, count in found_sources]

def demo_transcript_search(show_name: str, rss_feed: str = None):
    """Demo function to test transcript searching"""
    manager = TranscriptScraperManager()

    print(f"\n=== SEARCHING FOR TRANSCRIPTS: {show_name} ===")

    results = manager.search_all_sources(show_name, rss_feed, max_sources=3)

    for source, result in results.items():
        print(f"\n{source.upper()}:")
        print(f"  Found: {result.found}")
        if result.error:
            print(f"  Error: {result.error}")
        elif result.metadata:
            for key, value in result.metadata.items():
                if isinstance(value, list) and len(value) > 3:
                    print(f"  {key}: {len(value)} items")
                else:
                    print(f"  {key}: {value}")

    best_sources = manager.get_best_sources(results)
    if best_sources:
        print(f"\nBEST SOURCES: {', '.join(best_sources)}")
    else:
        print("\nNO RELIABLE TRANSCRIPT SOURCES FOUND")

if __name__ == "__main__":
    # Test with a high-priority show
    demo_transcript_search(
        "Acquired",
        "https://feeds.transistor.fm/acquired"
    )