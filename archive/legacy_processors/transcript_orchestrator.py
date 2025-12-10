#!/usr/bin/env python3
"""
Atlas Transcript Orchestrator
Coordinates transcript discovery across multiple sources including web scraping,
API calls, and Mac Mini fallback transcription.
"""

import os
import re
import sys
import time
import logging
import sqlite3
import requests
from typing import Optional, Dict, Any, List
from pathlib import Path
from dataclasses import dataclass
from urllib.parse import urlparse, urljoin

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from helpers.mac_mini_client import MacMiniClient
    MAC_MINI_AVAILABLE = True
except ImportError:
    MAC_MINI_AVAILABLE = False

from helpers.database_config import get_database_path, get_database_connection

@dataclass
class TranscriptSource:
    """Represents a source for transcript content"""
    url: str
    content: str
    source_type: str  # 'web', 'api', 'mac_mini'
    confidence: float  # 0.0 to 1.0
    metadata: Dict[str, Any]

class TranscriptOrchestrator:
    """
    Orchestrates transcript discovery from multiple sources:
    1. Direct web scraping (Lex Fridman, Joe Rogan, etc.)
    2. API-based sources
    3. Mac Mini fallback transcription
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or get_database_path()
        self.mac_mini_client = None
        self.logger = logging.getLogger(__name__)

        # Initialize Mac Mini client if available
        if MAC_MINI_AVAILABLE:
            try:
                self.mac_mini_client = MacMiniClient()
                if not self.mac_mini_client.test_connection():
                    self.mac_mini_client = None
                    self.logger.info("Mac Mini not available for fallback transcription")
            except Exception as e:
                self.logger.error(f"Failed to initialize Mac Mini client: {e}")

        # Known transcript URL patterns
        self.transcript_patterns = {
            'lexfridman.com': {
                'base_url': 'https://lexfridman.com/',
                'pattern': r'https://lexfridman\.com/([^/]+)/?',
                'transcript_suffix': '-transcript'
            },
            'jre': {
                'base_url': 'https://jrelibrary.com/transcript/',
                'pattern': r'joe\s*rogan.*#?(\d+)',
                'transcript_format': '{episode_num}-transcript'
            }
        }

    def find_transcript(self, podcast_name: str, episode_title: str,
                       episode_url: Optional[str] = None) -> Optional[str]:
        """
        Find transcript for a given podcast episode using multiple strategies.

        Args:
            podcast_name: Name of the podcast
            episode_title: Title of the episode
            episode_url: Optional URL to the episode

        Returns:
            Transcript content as string, or None if not found
        """
        self.logger.info(f"🔍 Finding transcript: {podcast_name} - {episode_title[:50]}...")

        # Strategy 1: Check cache first
        cached_transcript = self.check_cache(podcast_name, episode_title)
        if cached_transcript:
            self.logger.info("✅ Found transcript in cache")
            return cached_transcript

        # Strategy 2: Web scraping based on podcast patterns
        if podcast_name.lower().find('lex fridman') != -1:
            transcript = self._find_lex_fridman_transcript(episode_title, episode_url)
            if transcript:
                self._cache_transcript(podcast_name, episode_title, transcript, 'web_scraping')
                return transcript

        if podcast_name.lower().find('joe rogan') != -1:
            transcript = self._find_joe_rogan_transcript(episode_title, episode_url)
            if transcript:
                self._cache_transcript(podcast_name, episode_title, transcript, 'web_scraping')
                return transcript

        # Strategy 3: Generic URL-based transcript discovery
        if episode_url:
            transcript = self._find_generic_transcript(episode_url)
            if transcript:
                self._cache_transcript(podcast_name, episode_title, transcript, 'generic_scraping')
                return transcript

        # Strategy 4: Mac Mini fallback transcription (if available)
        if self.mac_mini_client and episode_url:
            self.logger.info("🍎 Attempting Mac Mini fallback transcription...")
            transcript = self._transcribe_with_mac_mini(episode_url)
            if transcript:
                self._cache_transcript(podcast_name, episode_title, transcript, 'mac_mini')
                return transcript

        self.logger.info(f"❌ No transcript found for: {podcast_name} - {episode_title}")
        return None

    def check_cache(self, podcast_name: str, episode_title: str) -> Optional[str]:
        """Check if transcript is already cached in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT content FROM transcriptions
                    WHERE podcast_name = ? AND episode_title = ?
                    AND content IS NOT NULL AND content != ''
                    ORDER BY created_at DESC LIMIT 1
                """, (podcast_name, episode_title))

                result = cursor.fetchone()
                return result[0] if result else None

        except Exception as e:
            self.logger.error(f"Error checking transcript cache: {e}")
            return None

    def _find_lex_fridman_transcript(self, episode_title: str, episode_url: Optional[str] = None) -> Optional[str]:
        """Find transcript from Lex Fridman podcast website"""
        try:
            # Extract guest name or episode identifier
            if episode_url and 'lexfridman.com' in episode_url:
                # Extract from URL: https://lexfridman.com/elon-musk-4/
                match = re.search(r'lexfridman\.com/([^/]+)/?', episode_url)
                if match:
                    slug = match.group(1)
                    transcript_url = f"https://lexfridman.com/{slug}-transcript"

                    response = requests.get(transcript_url, timeout=10)
                    if response.status_code == 200:
                        # Simple HTML parsing to extract transcript
                        content = response.text
                        # Look for transcript content (this would need refinement)
                        if 'transcript' in content.lower():
                            # Extract the main content area
                            transcript_text = self._extract_transcript_from_html(content)
                            if transcript_text and len(transcript_text) > 500:
                                return transcript_text

        except Exception as e:
            self.logger.error(f"Error finding Lex Fridman transcript: {e}")

        return None

    def _find_joe_rogan_transcript(self, episode_title: str, episode_url: Optional[str] = None) -> Optional[str]:
        """Find transcript from Joe Rogan podcast sources"""
        try:
            # Extract episode number from title
            episode_match = re.search(r'#?(\d+)', episode_title)
            if episode_match:
                episode_num = episode_match.group(1)

                # Try JRE Library
                transcript_url = f"https://jrelibrary.com/transcript/{episode_num}"
                response = requests.get(transcript_url, timeout=10)
                if response.status_code == 200:
                    transcript_text = self._extract_transcript_from_html(response.text)
                    if transcript_text and len(transcript_text) > 500:
                        return transcript_text

        except Exception as e:
            self.logger.error(f"Error finding Joe Rogan transcript: {e}")

        return None

    def _find_generic_transcript(self, episode_url: str) -> Optional[str]:
        """Generic transcript discovery from episode URL"""
        try:
            parsed_url = urlparse(episode_url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

            # Common transcript URL patterns
            transcript_urls = [
                episode_url.replace('.html', '-transcript.html'),
                episode_url.replace('.htm', '-transcript.htm'),
                episode_url + '-transcript',
                episode_url.rstrip('/') + '/transcript',
                urljoin(base_url, 'transcript/' + parsed_url.path.split('/')[-1])
            ]

            for transcript_url in transcript_urls:
                try:
                    response = requests.get(transcript_url, timeout=5)
                    if response.status_code == 200:
                        transcript_text = self._extract_transcript_from_html(response.text)
                        if transcript_text and len(transcript_text) > 500:
                            return transcript_text
                except requests.RequestException:
                    continue

        except Exception as e:
            self.logger.error(f"Error in generic transcript discovery: {e}")

        return None

    def _extract_transcript_from_html(self, html_content: str) -> Optional[str]:
        """Extract transcript text from HTML content"""
        try:
            # Simple text extraction (would benefit from BeautifulSoup)
            # Remove HTML tags
            import re
            text = re.sub(r'<[^>]+>', ' ', html_content)

            # Remove extra whitespace
            text = re.sub(r'\s+', ' ', text).strip()

            # Look for transcript sections
            transcript_patterns = [
                r'transcript[:\s]+(.*?)(?:copyright|footer|end|©)',
                r'<article[^>]*>(.*?)</article>',
                r'<main[^>]*>(.*?)</main>',
                r'<div[^>]*class="[^"]*transcript[^"]*"[^>]*>(.*?)</div>'
            ]

            for pattern in transcript_patterns:
                match = re.search(pattern, html_content, re.IGNORECASE | re.DOTALL)
                if match:
                    extracted = re.sub(r'<[^>]+>', ' ', match.group(1))
                    extracted = re.sub(r'\s+', ' ', extracted).strip()
                    if len(extracted) > 500:
                        return extracted

            # Fallback: if text is substantial, return it
            if len(text) > 1000:
                return text

        except Exception as e:
            self.logger.error(f"Error extracting transcript from HTML: {e}")

        return None

    def _transcribe_with_mac_mini(self, episode_url: str) -> Optional[str]:
        """Use Mac Mini for fallback transcription"""
        if not self.mac_mini_client:
            return None

        try:
            self.logger.info(f"🎧 Requesting Mac Mini transcription for: {episode_url}")
            result = self.mac_mini_client.transcribe_audio(episode_url)

            if result.get('success'):
                transcript = result.get('transcript')
                if transcript and len(transcript) > 100:
                    self.logger.info(f"✅ Mac Mini transcription successful ({len(transcript)} chars)")
                    return transcript

            self.logger.warning("Mac Mini transcription failed or returned empty result")

        except Exception as e:
            self.logger.error(f"Error with Mac Mini transcription: {e}")

        return None

    def _cache_transcript(self, podcast_name: str, episode_title: str,
                         transcript: str, source_type: str):
        """Cache transcript in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO transcriptions
                    (podcast_name, episode_title, content, source_type, created_at)
                    VALUES (?, ?, ?, ?, datetime('now'))
                """, (podcast_name, episode_title, transcript, source_type))
                conn.commit()

                self.logger.info(f"📝 Cached transcript: {podcast_name} - {episode_title[:30]}...")

        except Exception as e:
            self.logger.error(f"Error caching transcript: {e}")

    def get_transcript_stats(self) -> Dict[str, Any]:
        """Get statistics about cached transcripts"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT
                        COUNT(*) as total_transcripts,
                        COUNT(DISTINCT podcast_name) as unique_podcasts,
                        AVG(LENGTH(content)) as avg_length,
                        source_type,
                        COUNT(*) as count_by_source
                    FROM transcriptions
                    WHERE content IS NOT NULL AND content != ''
                    GROUP BY source_type
                """)

                results = cursor.fetchall()

                stats = {
                    'total_transcripts': 0,
                    'unique_podcasts': 0,
                    'avg_length': 0,
                    'by_source': {}
                }

                for row in results:
                    if row[3]:  # source_type exists
                        stats['by_source'][row[3]] = row[4]
                    if row[0] > stats['total_transcripts']:
                        stats['total_transcripts'] = row[0]
                        stats['unique_podcasts'] = row[1]
                        stats['avg_length'] = row[2] or 0

                return stats

        except Exception as e:
            self.logger.error(f"Error getting transcript stats: {e}")
            return {'total_transcripts': 0, 'unique_podcasts': 0, 'avg_length': 0, 'by_source': {}}


# Global orchestrator instance
_orchestrator = None

def get_orchestrator() -> TranscriptOrchestrator:
    """Get global transcript orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = TranscriptOrchestrator()
    return _orchestrator

def find_transcript(podcast_name: str, episode_title: str, episode_url: Optional[str] = None) -> Optional[str]:
    """
    Convenience function for finding transcripts.
    This is the main function used by other modules.
    """
    orchestrator = get_orchestrator()
    return orchestrator.find_transcript(podcast_name, episode_title, episode_url)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Atlas Transcript Orchestrator")
    parser.add_argument("--test", action="store_true", help="Run test transcript discovery")
    parser.add_argument("--stats", action="store_true", help="Show transcript statistics")
    parser.add_argument("--podcast", help="Podcast name for testing")
    parser.add_argument("--episode", help="Episode title for testing")
    parser.add_argument("--url", help="Episode URL for testing")

    args = parser.parse_args()

    orchestrator = TranscriptOrchestrator()

    if args.stats:
        stats = orchestrator.get_transcript_stats()
        print("📊 Transcript Statistics:")
        print(f"  Total transcripts: {stats['total_transcripts']}")
        print(f"  Unique podcasts: {stats['unique_podcasts']}")
        print(f"  Average length: {stats['avg_length']:.0f} characters")
        print("  By source:")
        for source, count in stats['by_source'].items():
            print(f"    {source}: {count}")

    elif args.test:
        # Test cases
        test_cases = [
            ("Lex Fridman Podcast", "Elon Musk: Tesla, SpaceX, AI & the Future",
             "https://lexfridman.com/elon-musk-4/"),
            ("Joe Rogan Experience", "JRE #1169 - Elon Musk", None)
        ]

        if args.podcast and args.episode:
            test_cases = [(args.podcast, args.episode, args.url)]

        for podcast, episode, url in test_cases:
            print(f"\n🧪 Testing: {podcast} - {episode}")
            transcript = orchestrator.find_transcript(podcast, episode, url)
            if transcript:
                print(f"✅ Found transcript ({len(transcript)} characters)")
                print(f"Preview: {transcript[:200]}...")
            else:
                print("❌ No transcript found")

    else:
        print("Use --test or --stats. See --help for options.")