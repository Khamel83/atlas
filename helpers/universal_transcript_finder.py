#!/usr/bin/env python3
"""
Universal Podcast Transcript Finder

Uses Google search to find transcript sources for ANY podcast.
Creates a repeatable, scalable system that works for all podcasts.
"""

import requests
import time
import logging
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse, quote
from bs4 import BeautifulSoup
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class TranscriptSource:
    url: str
    site_name: str
    reliability_score: int  # 1-10
    coverage_type: str  # "official", "fan", "service", "community"
    access_method: str  # "direct", "scrape", "api"

class UniversalTranscriptFinder:
    """Find transcript sources for any podcast using Google search"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        # Known transcript hosting patterns
        self.transcript_indicators = [
            r"transcript",
            r"full text",
            r"complete text",
            r"verbatim",
            r"show notes",
            r"episode text"
        ]

        # Reliable transcript sources (ranked by quality)
        self.known_sources = {
            "rev.com": {"score": 9, "type": "service"},
            "otter.ai": {"score": 8, "type": "service"},
            "scribd.com": {"score": 7, "type": "service"},
            "medium.com": {"score": 6, "type": "community"},
            "substack.com": {"score": 6, "type": "community"},
            "reddit.com": {"score": 5, "type": "community"},
            "github.com": {"score": 8, "type": "community"},
            "notion.so": {"score": 6, "type": "community"},
            "docs.google.com": {"score": 5, "type": "community"}
        }

    def find_transcript_sources(self, podcast_name: str, episode_title: str = None) -> List[TranscriptSource]:
        """Find all available transcript sources for a podcast"""
        sources = []

        # Strategy 1: Official website search
        official_sources = self._search_official_website(podcast_name)
        sources.extend(official_sources)

        # Strategy 2: Google search for transcripts
        google_sources = self._google_search_transcripts(podcast_name, episode_title)
        sources.extend(google_sources)

        # Strategy 3: Check known transcript services
        service_sources = self._check_transcript_services(podcast_name)
        sources.extend(service_sources)

        # Strategy 4: Community/fan sources
        community_sources = self._find_community_transcripts(podcast_name)
        sources.extend(community_sources)

        # Deduplicate and rank
        unique_sources = self._deduplicate_sources(sources)
        ranked_sources = sorted(unique_sources, key=lambda x: x.reliability_score, reverse=True)

        return ranked_sources

    def _google_search_transcripts(self, podcast_name: str, episode_title: str = None) -> List[TranscriptSource]:
        """Use Google to find transcript sources"""
        sources = []

        # Multiple search strategies
        queries = [
            f'"{podcast_name}" transcript',
            f'"{podcast_name}" full text episode',
            f'"{podcast_name}" verbatim transcript',
            f'"{podcast_name}" episode transcript site:reddit.com',
            f'"{podcast_name}" transcript site:medium.com',
            f'"{podcast_name}" transcript site:substack.com',
            f'"{podcast_name}" transcript site:github.com',
        ]

        if episode_title:
            queries.extend([
                f'"{podcast_name}" "{episode_title}" transcript',
                f'"{episode_title}" full text transcript'
            ])

        for query in queries[:5]:  # Limit to avoid rate limiting
            try:
                search_results = self._perform_google_search(query)
                for result in search_results:
                    source = self._analyze_search_result(result, podcast_name)
                    if source:
                        sources.append(source)

                time.sleep(1)  # Rate limiting

            except Exception as e:
                logger.warning(f"Google search failed for '{query}': {e}")

        return sources

    def _perform_google_search(self, query: str) -> List[Dict]:
        """Perform Google search and extract results"""
        # Use Google Custom Search API or scraping (implement based on your setup)
        # For now, return empty list - this needs actual Google API integration
        return []

    def _search_official_website(self, podcast_name: str) -> List[TranscriptSource]:
        """Search the podcast's official website for transcripts"""
        sources = []

        # Try to find official website
        website_url = self._find_podcast_website(podcast_name)
        if not website_url:
            return sources

        try:
            # Search for transcript pages
            transcript_urls = self._crawl_for_transcripts(website_url)

            for url in transcript_urls:
                sources.append(TranscriptSource(
                    url=url,
                    site_name=urlparse(website_url).netloc,
                    reliability_score=10,  # Official is highest
                    coverage_type="official",
                    access_method="direct"
                ))

        except Exception as e:
            logger.warning(f"Failed to search official website {website_url}: {e}")

        return sources

    def _check_transcript_services(self, podcast_name: str) -> List[TranscriptSource]:
        """Check known transcript services for the podcast"""
        sources = []

        service_urls = [
            f"https://www.rev.com/transcripts/{podcast_name.lower().replace(' ', '-')}",
            f"https://otter.ai/s/{podcast_name.lower().replace(' ', '_')}",
            f"https://www.scribd.com/search?query={quote(podcast_name + ' transcript')}",
            f"https://podscribe.com/shows/{podcast_name.lower().replace(' ', '-')}",
        ]

        for url in service_urls:
            try:
                response = self.session.head(url, timeout=10)
                if response.status_code == 200:
                    domain = urlparse(url).netloc
                    source_info = self.known_sources.get(domain, {"score": 7, "type": "service"})

                    sources.append(TranscriptSource(
                        url=url,
                        site_name=domain,
                        reliability_score=source_info["score"],
                        coverage_type=source_info["type"],
                        access_method="scrape"
                    ))

            except Exception as e:
                logger.debug(f"Service check failed for {url}: {e}")

        return sources

    def _find_community_transcripts(self, podcast_name: str) -> List[TranscriptSource]:
        """Find community-created transcripts"""
        sources = []

        # Check GitHub for transcript repositories
        github_search = f"https://api.github.com/search/repositories?q={quote(podcast_name + ' transcript')}"

        try:
            response = self.session.get(github_search, timeout=10)
            if response.status_code == 200:
                data = response.json()
                for repo in data.get('items', [])[:5]:
                    sources.append(TranscriptSource(
                        url=repo['html_url'],
                        site_name="github.com",
                        reliability_score=8,
                        coverage_type="community",
                        access_method="direct"
                    ))

        except Exception as e:
            logger.warning(f"GitHub search failed: {e}")

        return sources

    def _find_podcast_website(self, podcast_name: str) -> Optional[str]:
        """Find the official website for a podcast"""
        # This would use search engines or podcast directories
        # For now, return None - implement based on your requirements
        return None

    def _crawl_for_transcripts(self, website_url: str) -> List[str]:
        """Crawl a website looking for transcript pages"""
        transcript_urls = []

        try:
            response = self.session.get(website_url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for transcript-related links
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                text = link.get_text().lower()

                # Check if link text or href suggests transcripts
                if any(indicator in text for indicator in self.transcript_indicators):
                    full_url = urljoin(website_url, href)
                    transcript_urls.append(full_url)

        except Exception as e:
            logger.warning(f"Failed to crawl {website_url}: {e}")

        return transcript_urls

    def _analyze_search_result(self, result: Dict, podcast_name: str) -> Optional[TranscriptSource]:
        """Analyze a search result to determine if it's a good transcript source"""
        url = result.get('url', '')
        title = result.get('title', '').lower()
        snippet = result.get('snippet', '').lower()

        # Check if result is relevant
        if podcast_name.lower() not in (title + snippet):
            return None

        # Check if it mentions transcripts
        has_transcript_indicators = any(
            indicator in (title + snippet)
            for indicator in self.transcript_indicators
        )

        if not has_transcript_indicators:
            return None

        # Determine source quality
        domain = urlparse(url).netloc
        source_info = self.known_sources.get(domain, {"score": 5, "type": "unknown"})

        return TranscriptSource(
            url=url,
            site_name=domain,
            reliability_score=source_info["score"],
            coverage_type=source_info["type"],
            access_method="scrape"
        )

    def _deduplicate_sources(self, sources: List[TranscriptSource]) -> List[TranscriptSource]:
        """Remove duplicate sources"""
        seen_urls = set()
        unique_sources = []

        for source in sources:
            if source.url not in seen_urls:
                seen_urls.add(source.url)
                unique_sources.append(source)

        return unique_sources

    def test_transcript_extraction(self, source: TranscriptSource, episode_info: Dict) -> Tuple[bool, Optional[str]]:
        """Test if we can actually extract transcript from a source"""
        try:
            response = self.session.get(source.url, timeout=15)
            if response.status_code != 200:
                return False, None

            soup = BeautifulSoup(response.content, 'html.parser')

            # Try to find transcript content
            transcript_text = self._extract_transcript_text(soup)

            if transcript_text and len(transcript_text) > 500:  # Minimum length check
                return True, transcript_text

        except Exception as e:
            logger.warning(f"Failed to extract from {source.url}: {e}")

        return False, None

    def _extract_transcript_text(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract transcript text from a webpage"""
        # Try common transcript containers
        selectors = [
            '.transcript',
            '#transcript',
            '.episode-transcript',
            '.full-text',
            '.verbatim',
            'article',
            '.content',
            '.entry-content',
            '.post-content'
        ]

        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                if len(text) > 500:  # Reasonable transcript length
                    return text

        return None

# Main function for testing
def main():
    finder = UniversalTranscriptFinder()

    # Test podcasts
    test_podcasts = [
        "Hard Fork",
        "Conversations with Tyler",
        "Acquired",
        "Accidental Tech Podcast"
    ]

    for podcast in test_podcasts:
        print(f"\n=== Finding transcripts for: {podcast} ===")
        sources = finder.find_transcript_sources(podcast)

        for source in sources[:3]:  # Top 3 sources
            print(f"Source: {source.site_name}")
            print(f"URL: {source.url}")
            print(f"Score: {source.reliability_score}")
            print(f"Type: {source.coverage_type}")
            print("-" * 50)

if __name__ == "__main__":
    main()