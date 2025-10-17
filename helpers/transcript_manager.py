#!/usr/bin/env python3
"""
Unified Transcript Manager

Consolidates all transcript processing functionality:
- ATP transcript scraping
- Network transcript scrapers
- Universal transcript discovery
- Transcript processing and enhancement
- Search indexing and ranking
- Podcast transcript ingestion

This single module replaces 10+ separate transcript processing files
with unified deduplication logic to prevent re-processing.
"""

import os
import json
import logging
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

try:
    import frontmatter
except ImportError:
    frontmatter = None

# Import existing functionality we're consolidating
try:
    from helpers.config import load_config
    from helpers.metadata_manager import ContentType
    from helpers.path_manager import PathType
    from helpers.dedupe import link_uid
    from helpers.utils import log_info, log_error
except ImportError:
    # Fallback for testing/standalone usage
    def load_config():
        return {}
    def log_info(msg):
        logging.info(msg)
    def log_error(msg):
        logging.error(msg)
    def link_uid(url):
        """Simple UID generation fallback"""
        import hashlib
        return hashlib.md5(url.encode()).hexdigest()[:16]

logger = logging.getLogger(__name__)

@dataclass
class TranscriptInfo:
    """Standardized transcript information"""
    url: str
    title: str
    episode_number: Optional[str] = None
    podcast_name: Optional[str] = None
    transcript_url: Optional[str] = None
    content: Optional[str] = None
    metadata: Dict[str, Any] = None
    source: str = "unknown"
    processed: bool = False
    uid: Optional[str] = None

    def __post_init__(self):
        if not self.uid:
            self.uid = link_uid(self.url)
        if not self.metadata:
            self.metadata = {}

class TranscriptManager:
    """
    Unified transcript processing manager.

    Consolidates functionality from:
    - atp_transcript_scraper.py
    - network_transcript_scrapers.py
    - universal_transcript_discoverer.py
    - transcript_first_processor.py
    - transcript_lookup.py
    - transcript_parser.py
    - transcript_search_indexer.py
    - transcript_search_ranking.py
    - podcast_transcript_ingestor.py
    - atp_enhanced_transcript.py
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or load_config()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

        # Output directory
        self.output_dir = Path(self.config.get('output_dir', 'output'))

        # State tracking for deduplication
        self.processed_urls: Set[str] = set()
        self.processed_file = self.output_dir / "processed_transcripts.json"
        self._load_processed_state()

        # Initialize scrapers and processors
        self.scrapers = {
            'atp': self._init_atp_scraper(),
            'network': self._init_network_scrapers(),
            'universal': self._init_universal_discoverer()
        }
        self.transcripts_dir = self.output_dir / 'transcripts'
        self.transcripts_dir.mkdir(parents=True, exist_ok=True)

    def _load_processed_state(self):
        """Load previously processed transcript URLs to prevent duplication"""
        if self.processed_file.exists():
            try:
                with open(self.processed_file, 'r') as f:
                    data = json.load(f)
                    self.processed_urls = set(data.get('processed_urls', []))
                    log_info(f"Loaded {len(self.processed_urls)} processed transcript URLs")
            except Exception as e:
                log_error(f"Error loading processed state: {e}")
                self.processed_urls = set()

    def _save_processed_state(self):
        """Save processed URLs to prevent future duplication"""
        try:
            self.processed_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.processed_file, 'w') as f:
                json.dump({
                    'processed_urls': list(self.processed_urls),
                    'last_updated': datetime.now().isoformat(),
                    'total_processed': len(self.processed_urls)
                }, f, indent=2)
        except Exception as e:
            log_error(f"Error saving processed state: {e}")

    def _init_atp_scraper(self):
        """Initialize ATP transcript scraper"""
        return {
            'base_url': 'https://catatp.fm',
            'episodes_url': 'https://catatp.fm/episodes/',
            'name': 'ATP (Accidental Tech Podcast)'
        }

    def _init_network_scrapers(self):
        """Initialize network-specific scrapers"""
        return {
            'npr': {
                'base_url': 'https://www.thisamericanlife.org',
                'transcript_pattern': r'/transcript',
                'name': 'NPR Network'
            },
            'radiolab': {
                'base_url': 'https://radiolab.org',
                'transcript_pattern': r'/transcript',
                'name': 'Radiolab/WNYC'
            },
            'slate': {
                'base_url': 'https://slate.com',
                'transcript_pattern': r'/transcript',
                'name': 'Slate Podcast Network'
            }
        }

    def _init_universal_discoverer(self):
        """Initialize universal transcript discovery patterns"""
        return {
            'patterns': [
                r'transcript',
                r'full-text',
                r'show-notes',
                r'episode-transcript'
            ],
            'indicators': [
                'transcript available',
                'full transcript',
                'episode transcript',
                'read transcript'
            ]
        }

    def already_processed(self, url: str) -> bool:
        """Check if URL has already been processed to prevent duplication"""
        uid = link_uid(url)
        return uid in self.processed_urls or url in self.processed_urls

    def mark_processed(self, url: str):
        """Mark URL as processed"""
        uid = link_uid(url)
        self.processed_urls.add(uid)
        self.processed_urls.add(url)
        self._save_processed_state()

    def discover_transcripts(self, source_type: str = 'auto', **kwargs) -> List[TranscriptInfo]:
        """
        Universal transcript discovery across all sources.

        Args:
            source_type: 'atp', 'network', 'universal', or 'auto'
            **kwargs: Additional arguments for specific scrapers

        Returns:
            List of TranscriptInfo objects
        """
        log_info(f"Discovering transcripts using {source_type} method")

        transcripts = []

        if source_type == 'atp' or source_type == 'auto':
            transcripts.extend(self._discover_atp_transcripts(**kwargs))

        if source_type == 'network' or source_type == 'auto':
            transcripts.extend(self._discover_network_transcripts(**kwargs))

        if source_type == 'universal' or source_type == 'auto':
            transcripts.extend(self._discover_universal_transcripts(**kwargs))

        # Filter out already processed
        new_transcripts = []
        for transcript in transcripts:
            if not self.already_processed(transcript.url):
                new_transcripts.append(transcript)
            else:
                log_info(f"Skipping already processed: {transcript.url}")

        log_info(f"Discovered {len(new_transcripts)} new transcripts (filtered {len(transcripts) - len(new_transcripts)} duplicates)")
        return new_transcripts

    def _discover_atp_transcripts(self, limit: int = 50) -> List[TranscriptInfo]:
        """Discover ATP transcripts from catatp.fm"""
        transcripts = []

        try:
            atp_config = self.scrapers['atp']
            response = self.session.get(atp_config['episodes_url'])
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            episode_links = soup.find_all('a', href=True)

            processed_count = 0
            for link in episode_links:
                if processed_count >= limit:
                    break

                href = link.get('href')
                if href and '/episodes/' in href:
                    episode_url = urljoin(atp_config['base_url'], href)

                    transcript_info = TranscriptInfo(
                        url=episode_url,
                        title=link.get_text(strip=True) or f"ATP Episode {href.split('/')[-1]}",
                        podcast_name="Accidental Tech Podcast",
                        source="atp"
                    )

                    transcripts.append(transcript_info)
                    processed_count += 1

        except Exception as e:
            log_error(f"Error discovering ATP transcripts: {e}")

        return transcripts

    def _discover_network_transcripts(self, networks: List[str] = None) -> List[TranscriptInfo]:
        """Discover transcripts from podcast networks"""
        if networks is None:
            networks = list(self.scrapers['network'].keys())

        transcripts = []

        for network in networks:
            if network not in self.scrapers['network']:
                continue

            try:
                network_config = self.scrapers['network'][network]
                # Network-specific discovery logic would go here
                # For now, placeholder
                log_info(f"Discovering transcripts from {network_config['name']}")

            except Exception as e:
                log_error(f"Error discovering {network} transcripts: {e}")

        return transcripts

    def _discover_universal_transcripts(self, urls: List[str] = None) -> List[TranscriptInfo]:
        """Universal transcript discovery using patterns"""
        if not urls:
            return []

        transcripts = []

        for url in urls:
            try:
                response = self.session.get(url)
                response.raise_for_status()

                soup = BeautifulSoup(response.content, 'html.parser')

                # Look for transcript indicators
                universal_config = self.scrapers['universal']
                for indicator in universal_config['indicators']:
                    if indicator.lower() in response.text.lower():
                        transcript_info = TranscriptInfo(
                            url=url,
                            title=self._extract_title(soup),
                            source="universal",
                            transcript_url=url
                        )
                        transcripts.append(transcript_info)
                        break

            except Exception as e:
                log_error(f"Error in universal discovery for {url}: {e}")

        return transcripts

    def fetch_transcript(self, transcript_info: TranscriptInfo, strategy: str = 'auto') -> Optional[TranscriptInfo]:
        """
        Fetch transcript content using best available strategy.

        Args:
            transcript_info: TranscriptInfo object
            strategy: 'auto', 'atp', 'network', or 'universal'

        Returns:
            TranscriptInfo with content populated, or None if failed
        """
        if self.already_processed(transcript_info.url):
            log_info(f"Transcript already processed: {transcript_info.url}")
            return None

        log_info(f"Fetching transcript: {transcript_info.title}")

        try:
            # Determine strategy based on source or use auto-detection
            if strategy == 'auto':
                if transcript_info.source == 'atp':
                    content = self._fetch_atp_transcript(transcript_info)
                elif transcript_info.source in self.scrapers['network']:
                    content = self._fetch_network_transcript(transcript_info)
                else:
                    content = self._fetch_universal_transcript(transcript_info)
            else:
                # Use specified strategy
                if strategy == 'atp':
                    content = self._fetch_atp_transcript(transcript_info)
                elif strategy == 'network':
                    content = self._fetch_network_transcript(transcript_info)
                else:
                    content = self._fetch_universal_transcript(transcript_info)

            if content:
                transcript_info.content = content
                transcript_info.processed = True
                self.mark_processed(transcript_info.url)

                # Save transcript to disk
                self._save_transcript(transcript_info)

                log_info(f"Successfully fetched transcript: {transcript_info.title} ({len(content)} chars)")
                return transcript_info
            else:
                log_error(f"Failed to fetch transcript content: {transcript_info.url}")
                return None

        except Exception as e:
            log_error(f"Error fetching transcript {transcript_info.url}: {e}")
            return None

    def _fetch_atp_transcript(self, transcript_info: TranscriptInfo) -> Optional[str]:
        """Fetch ATP transcript from catatp.fm"""
        try:
            response = self.session.get(transcript_info.url)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract transcript content from ATP's structure
            transcript_div = soup.find('div', class_='transcript') or soup.find('div', id='transcript')

            if transcript_div:
                return transcript_div.get_text(separator='\n', strip=True)

            # Fallback: look for content in common containers
            content_areas = soup.find_all(['div', 'article', 'section'], class_=lambda x: x and any(
                term in x.lower() for term in ['content', 'transcript', 'episode', 'text']
            ))

            for area in content_areas:
                text = area.get_text(separator='\n', strip=True)
                if len(text) > 1000:  # Reasonable transcript length
                    return text

            return None

        except Exception as e:
            log_error(f"Error fetching ATP transcript: {e}")
            return None

    def _fetch_network_transcript(self, transcript_info: TranscriptInfo) -> Optional[str]:
        """Fetch transcript from podcast networks"""
        # Placeholder for network-specific transcript fetching
        return self._fetch_universal_transcript(transcript_info)

    def _fetch_universal_transcript(self, transcript_info: TranscriptInfo) -> Optional[str]:
        """Universal transcript fetching"""
        try:
            response = self.session.get(transcript_info.transcript_url or transcript_info.url)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Remove navigation, ads, etc.
            for element in soup(['nav', 'header', 'footer', 'aside', 'script', 'style']):
                element.decompose()

            # Find main content
            main_content = (
                soup.find('main') or
                soup.find('article') or
                soup.find('div', class_=lambda x: x and 'content' in x.lower()) or
                soup.find('div', id='content') or
                soup.body
            )

            if main_content:
                return main_content.get_text(separator='\n', strip=True)

            return None

        except Exception as e:
            log_error(f"Error in universal transcript fetch: {e}")
            return None

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract title from HTML"""
        title_element = soup.find('title')
        if title_element:
            return title_element.get_text(strip=True)

        h1 = soup.find('h1')
        if h1:
            return h1.get_text(strip=True)

        return "Unknown Title"

    def _save_transcript(self, transcript_info: TranscriptInfo):
        """Save transcript to disk with metadata"""
        try:
            # Create filename from UID
            filename = f"{transcript_info.uid}.json"
            filepath = self.transcripts_dir / filename

            # Prepare data
            data = {
                'url': transcript_info.url,
                'title': transcript_info.title,
                'episode_number': transcript_info.episode_number,
                'podcast_name': transcript_info.podcast_name,
                'source': transcript_info.source,
                'content': transcript_info.content,
                'metadata': transcript_info.metadata,
                'processed_date': datetime.now().isoformat(),
                'uid': transcript_info.uid
            }

            # Save JSON
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            log_info(f"Saved transcript: {filepath}")

        except Exception as e:
            log_error(f"Error saving transcript: {e}")

    def bulk_process_transcripts(self, transcript_urls: List[str], max_concurrent: int = 5) -> List[TranscriptInfo]:
        """
        Bulk process multiple transcript URLs.

        Args:
            transcript_urls: List of URLs to process
            max_concurrent: Maximum concurrent processing

        Returns:
            List of successfully processed TranscriptInfo objects
        """
        log_info(f"Starting bulk processing of {len(transcript_urls)} transcript URLs")

        processed = []

        # First discover transcripts
        discovered = self._discover_universal_transcripts(transcript_urls)

        # Then fetch content
        for transcript_info in discovered:
            result = self.fetch_transcript(transcript_info)
            if result:
                processed.append(result)

            # Rate limiting
            time.sleep(0.5)

            if len(processed) >= max_concurrent:
                log_info(f"Processed {len(processed)} transcripts, continuing...")

        log_info(f"Bulk processing complete: {len(processed)} transcripts processed")
        return processed

    def search_transcripts(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search processed transcripts.

        Args:
            query: Search query
            max_results: Maximum results to return

        Returns:
            List of search results with relevance scores
        """
        results = []

        try:
            # Simple text-based search through saved transcripts
            for transcript_file in self.transcripts_dir.glob('*.json'):
                try:
                    with open(transcript_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    content = data.get('content', '')
                    title = data.get('title', '')

                    # Simple relevance scoring
                    query_lower = query.lower()
                    content_lower = content.lower()
                    title_lower = title.lower()

                    score = 0
                    if query_lower in title_lower:
                        score += 10
                    if query_lower in content_lower:
                        score += content_lower.count(query_lower)

                    if score > 0:
                        results.append({
                            'url': data.get('url'),
                            'title': title,
                            'score': score,
                            'preview': self._create_preview(content, query),
                            'source': data.get('source'),
                            'uid': data.get('uid')
                        })

                except Exception as e:
                    log_error(f"Error searching {transcript_file}: {e}")

            # Sort by relevance and limit results
            results.sort(key=lambda x: x['score'], reverse=True)
            return results[:max_results]

        except Exception as e:
            log_error(f"Error in transcript search: {e}")
            return []

    def _create_preview(self, content: str, query: str, context_length: int = 200) -> str:
        """Create search result preview with query context"""
        query_lower = query.lower()
        content_lower = content.lower()

        # Find first occurrence of query
        index = content_lower.find(query_lower)
        if index == -1:
            return content[:context_length] + "..."

        # Extract context around query
        start = max(0, index - context_length // 2)
        end = min(len(content), index + len(query) + context_length // 2)

        preview = content[start:end]
        if start > 0:
            preview = "..." + preview
        if end < len(content):
            preview = preview + "..."

        return preview

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return {
            'total_processed': len(self.processed_urls),
            'stored_transcripts': len(list(self.transcripts_dir.glob('*.json'))),
            'output_directory': str(self.transcripts_dir),
            'last_updated': datetime.now().isoformat()
        }

    def health_check(self) -> Dict[str, Any]:
        """System health check"""
        return {
            'status': 'healthy',
            'processed_state_loaded': len(self.processed_urls) > 0,
            'output_directory_exists': self.transcripts_dir.exists(),
            'session_active': self.session is not None,
            'scrapers_initialized': len(self.scrapers) == 3
        }

# Convenience functions for backward compatibility
def find_transcripts(source: str = 'auto', **kwargs) -> List[TranscriptInfo]:
    """Convenience function for transcript discovery"""
    manager = TranscriptManager()
    return manager.discover_transcripts(source, **kwargs)

def scrape_transcript(url: str) -> Optional[TranscriptInfo]:
    """Convenience function for single transcript scraping"""
    manager = TranscriptManager()
    transcript_info = TranscriptInfo(url=url, title="Unknown", source="universal")
    return manager.fetch_transcript(transcript_info)

def search_transcripts(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """Convenience function for transcript search"""
    manager = TranscriptManager()
    return manager.search_transcripts(query, max_results)

if __name__ == '__main__':
    # Example usage
    manager = TranscriptManager()

    # Discover ATP transcripts
    transcripts = manager.discover_transcripts('atp', limit=5)
    print(f"Discovered {len(transcripts)} ATP transcripts")

    # Process first transcript
    if transcripts:
        result = manager.fetch_transcript(transcripts[0])
        if result:
            print(f"Processed: {result.title}")

    # Show stats
    stats = manager.get_processing_stats()
    print(f"Processing stats: {stats}")