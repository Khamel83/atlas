#!/usr/bin/env python3
"""
Archive.org Integration for Atlas
Searches for historical transcripts and archived content
"""

import requests
import json
import re
import time
from typing import List, Dict, Optional, Set
from urllib.parse import urljoin, quote
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

class ArchiveOrgScraper:
    """Search Archive.org for podcast transcripts and archived content"""

    def __init__(self):
        self.base_url = "https://archive.org"
        self.search_url = "https://archive.org/advancedsearch.php"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def search_transcripts(self, podcast_name: str, episode_title: str) -> List[Dict]:
        """Search Archive.org for podcast transcripts"""
        try:
            # Build search query
            search_terms = [podcast_name, episode_title, "transcript", "podcast"]
            query = " ".join(search_terms)

            # Search parameters
            params = {
                'q': query,
                'fl[]': ['identifier', 'title', 'description', 'format', 'year'],
                'rows': 20,
                'page': 1,
                'output': 'json',
                'sort[]': 'downloads desc'
            }

            response = self.session.get(self.search_url, params=params)
            response.raise_for_status()

            data = response.json()
            results = []

            if 'response' in data and 'docs' in data['response']:
                for doc in data['response']['docs']:
                    result = {
                        'identifier': doc.get('identifier', ''),
                        'title': doc.get('title', ''),
                        'description': doc.get('description', ''),
                        'formats': doc.get('format', []),
                        'year': doc.get('year', ''),
                        'url': f"{self.base_url}/details/{doc.get('identifier', '')}",
                        'relevance_score': self._calculate_relevance_score(
                            podcast_name, episode_title, doc.get('title', ''), doc.get('description', '')
                        )
                    }

                    # Filter for text content and high relevance
                    if result['relevance_score'] > 0.3 and any(fmt in result['formats'] for fmt in ['Text', 'PDF', 'HTML']):
                        results.append(result)

            # Sort by relevance
            results.sort(key=lambda x: x['relevance_score'], reverse=True)
            return results

        except Exception as e:
            logger.error(f"Archive.org search failed: {e}")
            return []

    def _calculate_relevance_score(self, podcast_name: str, episode_title: str,
                                   archive_title: str, archive_description: str) -> float:
        """Calculate relevance score for archive results"""
        score = 0.0
        title_lower = archive_title.lower()
        desc_lower = (archive_description or "").lower()
        podcast_lower = podcast_name.lower()
        episode_lower = episode_title.lower()

        # Direct podcast name match
        if podcast_lower in title_lower:
            score += 0.4

        # Episode title terms
        episode_terms = re.findall(r'\b\w{4,}\b', episode_lower)
        for term in episode_terms:
            if term in title_lower or term in desc_lower:
                score += 0.1

        # Transcript indicators
        transcript_keywords = ['transcript', 'text', 'script', 'captions', 'subtitles']
        for keyword in transcript_keywords:
            if keyword in title_lower or keyword in desc_lower:
                score += 0.2

        # Podcast indicators
        podcast_keywords = ['podcast', 'episode', 'show', 'audio', 'interview']
        for keyword in podcast_keywords:
            if keyword in title_lower or keyword in desc_lower:
                score += 0.1

        return min(score, 1.0)

    def get_item_content(self, identifier: str) -> Optional[str]:
        """Get content from an Archive.org item"""
        try:
            # Get item metadata
            metadata_url = f"{self.base_url}/metadata/{identifier}"
            response = self.session.get(metadata_url)
            response.raise_for_status()

            metadata = response.json()

            # Look for downloadable text files
            files = metadata.get('files', {})
            text_files = []

            for filename, fileinfo in files.items():
                if any(filename.endswith(ext) for ext in ['.txt', '.md', '.html', '.htm']):
                    if fileinfo.get('format') in ['Text', 'HTML']:
                        text_files.append((filename, fileinfo))

            if not text_files:
                # Try to extract text from PDF or other formats
                return self._extract_text_from_item(identifier)

            # Try text files first
            for filename, fileinfo in text_files:
                content_url = f"https://archive.org/download/{identifier}/{filename}"
                try:
                    content_response = self.session.get(content_url)
                    if content_response.status_code == 200:
                        content = content_response.text
                        if len(content) > 500:  # Minimum length check
                            return content
                except Exception:
                    continue

            return None

        except Exception as e:
            logger.error(f"Failed to get Archive.org content for {identifier}: {e}")
            return None

    def _extract_text_from_item(self, identifier: str) -> Optional[str]:
        """Extract text from item using web scraping"""
        try:
            item_url = f"{self.base_url}/details/{identifier}"
            response = self.session.get(item_url)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for text content in the page
            text_blocks = []

            # Try different selectors
            selectors = [
                '.book-text',
                '.text-content',
                '#text-content',
                '.content',
                '#content',
                'main',
                '.main'
            ]

            for selector in selectors:
                element = soup.select_one(selector)
                if element:
                    text = element.get_text(separator=' ', strip=True)
                    if len(text) > 500:
                        text_blocks.append(text)

            # Also try to find the largest text block
            if not text_blocks:
                all_text = soup.get_text(separator=' ', strip=True)
                if len(all_text) > 1000:
                    # Clean up common navigation elements
                    lines = [line.strip() for line in all_text.split('\n') if line.strip()]
                    clean_text = ' '.join(lines)
                    text_blocks.append(clean_text)

            if text_blocks:
                # Return the longest text block
                return max(text_blocks, key=len)

            return None

        except Exception as e:
            logger.error(f"Failed to extract text from {identifier}: {e}")
            return None

    def search_web_archive(self, original_url: str) -> Optional[str]:
        """Search Wayback Machine for archived version of the original URL"""
        try:
            # Check Wayback Machine availability
            wayback_url = f"http://web.archive.org/web/*/{original_url}"
            response = self.session.get(wayback_url)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for archived versions
            archive_links = soup.select('.version-link')
            if archive_links:
                # Try the most recent archive first
                latest_archive = archive_links[0].get('href')
                if latest_archive:
                    archive_url = f"http://web.archive.org{latest_archive}"
                    archive_response = self.session.get(archive_url)
                    if archive_response.status_code == 200:
                        archive_soup = BeautifulSoup(archive_response.content, 'html.parser')
                        content = archive_soup.get_text(separator=' ', strip=True)
                        if len(content) > 1000:
                            return content

            return None

        except Exception as e:
            logger.error(f"Wayback Machine search failed for {original_url}: {e}")
            return None

    def find_transcript(self, podcast_name: str, episode_title: str, original_url: str) -> Optional[Dict]:
        """Main method to find transcript via Archive.org"""
        try:
            logger.info(f"Searching Archive.org for transcript: {podcast_name} - {episode_title}")

            # Strategy 1: Search Archive.org collections
            search_results = self.search_transcripts(podcast_name, episode_title)

            for result in search_results[:5]:  # Try top 5 results
                logger.info(f"Trying Archive.org item: {result['title']} (score: {result['relevance_score']})")

                content = self.get_item_content(result['identifier'])
                if content:
                    logger.info(f"Found transcript via Archive.org: {result['title']}")
                    return {
                        'transcript': content,
                        'source': 'archive_org',
                        'archive_url': result['url'],
                        'archive_title': result['title'],
                        'relevance_score': result['relevance_score']
                    }

            # Strategy 2: Try Wayback Machine for original URL
            logger.info("Trying Wayback Machine for original URL...")
            wayback_content = self.search_web_archive(original_url)
            if wayback_content:
                logger.info("Found transcript via Wayback Machine")
                return {
                    'transcript': wayback_content,
                    'source': 'wayback_machine',
                    'archive_url': f"http://web.archive.org/web/*/{original_url}",
                    'archive_title': f"Archived: {original_url}",
                    'relevance_score': 0.5
                }

            logger.info("No transcripts found via Archive.org")
            return None

        except Exception as e:
            logger.error(f"Archive.org transcript search failed: {e}")
            return None

# Test function
def test_archive_scraper():
    """Test the Archive.org scraper"""
    scraper = ArchiveOrgScraper()

    # Test with a known podcast
    result = scraper.find_transcript(
        "This American Life",
        "The Giant Pool of Money",
        "https://www.thisamericanlife.org/355/the-giant-pool-of-money"
    )

    if result:
        print(f"✅ Found transcript via Archive.org: {len(result['transcript'])} chars")
        print(f"   Source: {result['archive_url']}")
    else:
        print("❌ No transcript found via Archive.org")

if __name__ == "__main__":
    test_archive_scraper()