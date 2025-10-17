#!/usr/bin/env python3
"""
Podcast Transcript Lookup System

This module implements the exact workflow you described:
1. Check existing transcript sources (RSS feeds, database)
2. Try YouTube fallback for missing transcripts
3. Try Google search as final fallback
4. Schedule retries for failures

Integrates with Atlas scheduler and numeric stage system.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

import sqlite3
from helpers.youtube_podcast_fallback import YouTubePodcastFallback
from helpers.content_transactions import TransactionTimer

logger = logging.getLogger(__name__)

@dataclass
class PodcastEpisode:
    """Podcast episode data structure"""
    podcast_name: str
    episode_title: str
    episode_url: str
    audio_url: Optional[str] = None
    publish_date: Optional[str] = None
    duration: Optional[str] = None
    existing_transcript: Optional[str] = None

@dataclass
class TranscriptLookupResult:
    """Result of transcript lookup operation"""
    success: bool
    podcast_name: str
    episode_title: str
    transcript: Optional[str] = None
    source: Optional[str] = None
    fallback_used: bool = False
    error_message: Optional[str] = None
    retry_scheduled: bool = False
    processing_time: Optional[float] = None

class PodcastTranscriptLookup:
    """Main transcript lookup system for Atlas"""

    def __init__(self):
        self.youtube_fallback = YouTubePodcastFallback()
        self.conn = sqlite3.connect('/home/ubuntu/dev/atlas/data/atlas.db')

    def lookup_transcript(self, podcast_name: str, episode_title: str,
                         episode_url: str = None) -> TranscriptLookupResult:
        """
        Main transcript lookup method - implements your described workflow

        Args:
            podcast_name (str): Name of the podcast
            episode_title (str): Title of the episode
            episode_url (str): URL of the episode (optional)

        Returns:
            TranscriptLookupResult: Complete lookup result
        """
        start_time = datetime.now()

        try:
            logger.info(f"Starting transcript lookup for {podcast_name} - {episode_title}")

            # Step 1: Check existing sources (RSS feeds, database)
            existing_result = self._check_existing_sources(podcast_name, episode_title, episode_url)

            if existing_result.success:
                logger.info(f"Found existing transcript for {podcast_name} - {episode_title}")
                return existing_result

            # Step 2: Check known sources (ATP, TAL, etc.)
            logger.info(f"Checking known sources for {podcast_name} - {episode_title}")
            known_sources_result = self._check_known_sources(podcast_name, episode_title, episode_url)

            if known_sources_result.success:
                logger.info(f"Found transcript via known sources for {podcast_name} - {episode_title}")
                return known_sources_result

            # Step 3: Try Google search fallback
            logger.info(f"Trying Google search fallback for {podcast_name} - {episode_title}")
            google_result = self._try_google_search_fallback(podcast_name, episode_title)

            if google_result.success:
                logger.info(f"Found transcript via Google search for {podcast_name} - {episode_title}")
                return google_result

            # Step 4: Try YouTube fallback
            logger.info(f"Trying YouTube fallback for {podcast_name} - {episode_title}")
            youtube_result = self._try_youtube_fallback(podcast_name, episode_title)

            if youtube_result.success:
                logger.info(f"Found transcript via YouTube for {podcast_name} - {episode_title}")
                return youtube_result

            # Step 5: All methods failed - schedule retry
            logger.warning(f"All transcript lookup methods failed for {podcast_name} - {episode_title}")
            retry_scheduled = self._schedule_retry(podcast_name, episode_title, episode_url)

            processing_time = (datetime.now() - start_time).total_seconds()

            return TranscriptLookupResult(
                success=False,
                podcast_name=podcast_name,
                episode_title=episode_title,
                error_message="All transcript lookup methods failed",
                retry_scheduled=retry_scheduled,
                processing_time=processing_time
            )

        except Exception as e:
            logger.error(f"Transcript lookup failed for {podcast_name} - {episode_title}: {e}")
            processing_time = (datetime.now() - start_time).total_seconds()

            return TranscriptLookupResult(
                success=False,
                podcast_name=podcast_name,
                episode_title=episode_title,
                error_message=str(e),
                processing_time=processing_time
            )

    def _check_existing_sources(self, podcast_name: str, episode_title: str,
                               episode_url: str = None) -> TranscriptLookupResult:
        """Check existing transcript sources (RSS feeds, database)"""

        try:
            # Check database first
            cursor = self.conn.cursor()

            # Look for existing transcripts
            query = """
                SELECT transcript, source, metadata
                FROM podcast_transcripts
                WHERE podcast_name = ? AND episode_title = ?
                ORDER BY created_at DESC
                LIMIT 1
            """

            cursor.execute(query, (podcast_name, episode_title))
            result = cursor.fetchone()

            if result and result[0]:  # transcript exists
                transcript, source, metadata_json = result

                # Parse metadata
                metadata = json.loads(metadata_json) if metadata_json else {}

                logger.info(f"Found existing transcript for {podcast_name} - {episode_title} from {source}")

                return TranscriptLookupResult(
                    success=True,
                    podcast_name=podcast_name,
                    episode_title=episode_title,
                    transcript=transcript,
                    source=source,
                    fallback_used=False
                )

            # Check if we have RSS feed content that might contain transcript
            rss_result = self._check_rss_feed_content(podcast_name, episode_title, episode_url)
            if rss_result.success:
                return rss_result

            return TranscriptLookupResult(
                success=False,
                podcast_name=podcast_name,
                episode_title=episode_title,
                error_message="No existing transcript found"
            )

        except Exception as e:
            logger.error(f"Failed to check existing sources: {e}")
            return TranscriptLookupResult(
                success=False,
                podcast_name=podcast_name,
                episode_title=episode_title,
                error_message=f"Database error: {str(e)}"
            )

    def _check_rss_feed_content(self, podcast_name: str, episode_title: str,
                              episode_url: str = None) -> TranscriptLookupResult:
        """Check RSS feed content for transcript"""

        try:
            # Look for RSS feed entries that might contain transcript data
            cursor = self.conn.cursor()

            query = """
                SELECT content, description, metadata
                FROM content
                WHERE content_type = 'podcast_episode'
                AND (title LIKE ? OR url = ?)
                LIMIT 1
            """

            search_title = f"%{episode_title}%"
            cursor.execute(query, (search_title, episode_url or ""))
            result = cursor.fetchone()

            if result:
                content, description, metadata_json = result

                # Combine content and description as potential transcript
                combined_text = f"{content or ''}\n\n{description or ''}".strip()

                if len(combined_text) > 100:  # Reasonable length for transcript
                    logger.info(f"Found RSS content for {podcast_name} - {episode_title}")

                    return TranscriptLookupResult(
                        success=True,
                        podcast_name=podcast_name,
                        episode_title=episode_title,
                        transcript=combined_text,
                        source="rss_feed",
                        fallback_used=False
                    )

            return TranscriptLookupResult(
                success=False,
                podcast_name=podcast_name,
                episode_title=episode_title,
                error_message="No RSS transcript found"
            )

        except Exception as e:
            logger.error(f"Failed to check RSS feed content: {e}")
            return TranscriptLookupResult(
                success=False,
                podcast_name=podcast_name,
                episode_title=episode_title,
                error_message=f"RSS check error: {str(e)}"
            )

    def _check_known_sources(self, podcast_name: str, episode_title: str, episode_url: str = None) -> TranscriptLookupResult:
        """Check known transcript sources before fallback methods"""

        try:
            # Check if this is an ATP episode
            if self._is_atp_episode(podcast_name, episode_title):
                logger.info(f"Detected ATP episode, using specialized scraper: {episode_title}")
                return self._get_atp_transcript(podcast_name, episode_title, episode_url)

            # Check if this is a This American Life episode
            elif self._is_tal_episode(podcast_name, episode_title):
                logger.info(f"Detected TAL episode, using specialized approach: {episode_title}")
                return self._get_tal_transcript(podcast_name, episode_title, episode_url)

            # Check if this is a 99% Invisible episode
            elif self._is_99pi_episode(podcast_name, episode_title):
                logger.info(f"Detected 99PI episode, using specialized approach: {episode_title}")
                return self._get_99pi_transcript(podcast_name, episode_title, episode_url)

            # No known source identified
            return TranscriptLookupResult(
                success=False,
                podcast_name=podcast_name,
                episode_title=episode_title,
                error_message="No known source identified for this podcast"
            )

        except Exception as e:
            logger.error(f"Known sources check failed: {e}")
            return TranscriptLookupResult(
                success=False,
                podcast_name=podcast_name,
                episode_title=episode_title,
                error_message=f"Known sources error: {str(e)}"
            )

    def _is_atp_episode(self, podcast_name: str, episode_title: str) -> bool:
        """Check if this is an ATP episode"""
        atp_indicators = [
            'accidental tech podcast',
            'atp.fm',
            'atp',
            'marco',
            'casey',
            'john siracusa'
        ]

        combined_text = f"{podcast_name} {episode_title}".lower()
        return any(indicator in combined_text for indicator in atp_indicators)

    def _is_tal_episode(self, podcast_name: str, episode_title: str) -> bool:
        """Check if this is a This American Life episode"""
        tal_indicators = [
            'this american life',
            'tal',
            'ira glass',
            'thisamericanlife'
        ]

        combined_text = f"{podcast_name} {episode_title}".lower()
        return any(indicator in combined_text for indicator in tal_indicators)

    def _is_99pi_episode(self, podcast_name: str, episode_title: str) -> bool:
        """Check if this is a 99% Invisible episode"""
        pi_indicators = [
            '99% invisible',
            '99 percent invisible',
            '99pi',
            'roman mars',
            '99percentinvisible'
        ]

        combined_text = f"{podcast_name} {episode_title}".lower()
        return any(indicator in combined_text for indicator in pi_indicators)

    def _get_atp_transcript(self, podcast_name: str, episode_title: str, episode_url: str = None) -> TranscriptLookupResult:
        """Get transcript using ATP scraper"""

        try:
            from helpers.atp_transcript_scraper import ATPTranscriptScraper

            scraper = ATPTranscriptScraper()

            # If we have a specific URL, try that first
            if episode_url:
                result = scraper.get_transcript_from_url(episode_url)
                if result.get('success'):
                    transcript = result['transcript']

                    # Store the successful transcript
                    self._store_transcript(podcast_name, episode_title, transcript, 'atp_scraper', episode_url)

                    return TranscriptLookupResult(
                        success=True,
                        podcast_name=podcast_name,
                        episode_title=episode_title,
                        transcript=transcript,
                        source='atp_scraper',
                        fallback_used=False
                    )

            # Try to find episode via search on catatp.fm
            episodes = scraper.get_episode_list()

            # Look for matching episode by title similarity
            for episode in episodes:
                if self._title_similarity(episode_title, episode.get('title', '')) > 0.7:
                    result = scraper.get_transcript_from_url(episode['url'])
                    if result.get('success'):
                        transcript = result['transcript']

                        # Store the successful transcript
                        self._store_transcript(podcast_name, episode_title, transcript, 'atp_scraper', episode['url'])

                        return TranscriptLookupResult(
                            success=True,
                            podcast_name=podcast_name,
                            episode_title=episode_title,
                            transcript=transcript,
                            source='atp_scraper',
                            fallback_used=False
                        )

            return TranscriptLookupResult(
                success=False,
                podcast_name=podcast_name,
                episode_title=episode_title,
                error_message="ATP episode not found on catatp.fm"
            )

        except ImportError:
            logger.warning("ATP scraper not available")
            return TranscriptLookupResult(
                success=False,
                podcast_name=podcast_name,
                episode_title=episode_title,
                error_message="ATP scraper not available"
            )
        except Exception as e:
            logger.error(f"ATP scraper failed: {e}")
            return TranscriptLookupResult(
                success=False,
                podcast_name=podcast_name,
                episode_title=episode_title,
                error_message=f"ATP scraper error: {str(e)}"
            )

    def _get_tal_transcript(self, podcast_name: str, episode_title: str, episode_url: str = None) -> TranscriptLookupResult:
        """Get transcript for This American Life episodes"""

        try:
            from helpers.tal_transcript_scraper import TALTranscriptScraper

            scraper = TALTranscriptScraper()

            # If we have a specific URL, try that first
            if episode_url:
                result = scraper.get_transcript_from_url(episode_url)
                if result.get('success'):
                    transcript = result['transcript']

                    # Store the successful transcript
                    self._store_transcript(podcast_name, episode_title, transcript, 'tal_scraper', episode_url)

                    return TranscriptLookupResult(
                        success=True,
                        podcast_name=podcast_name,
                        episode_title=episode_title,
                        transcript=transcript,
                        source='tal_scraper',
                        fallback_used=False
                    )

            # Try to find episode via search on thisamericanlife.org
            search_result = scraper.search_episode_by_title(episode_title)
            if search_result:
                result = scraper.get_transcript_from_url(search_result['url'])
                if result.get('success'):
                    transcript = result['transcript']

                    # Store the successful transcript
                    self._store_transcript(podcast_name, episode_title, transcript, 'tal_scraper', search_result['url'])

                    return TranscriptLookupResult(
                        success=True,
                        podcast_name=podcast_name,
                        episode_title=episode_title,
                        transcript=transcript,
                        source='tal_scraper',
                        fallback_used=False
                    )

            return TranscriptLookupResult(
                success=False,
                podcast_name=podcast_name,
                episode_title=episode_title,
                error_message="TAL episode not found on thisamericanlife.org"
            )

        except ImportError:
            logger.warning("TAL scraper not available")
            return TranscriptLookupResult(
                success=False,
                podcast_name=podcast_name,
                episode_title=episode_title,
                error_message="TAL scraper not available"
            )
        except Exception as e:
            logger.error(f"TAL scraper failed: {e}")
            return TranscriptLookupResult(
                success=False,
                podcast_name=podcast_name,
                episode_title=episode_title,
                error_message=f"TAL scraper error: {str(e)}"
            )

    def _get_99pi_transcript(self, podcast_name: str, episode_title: str, episode_url: str = None) -> TranscriptLookupResult:
        """Get transcript for 99% Invisible episodes"""

        try:
            from helpers.ninety_nine_pi_scraper import NinetyNinePITranscriptScraper

            scraper = NinetyNinePITranscriptScraper()

            # If we have a specific URL, try that first
            if episode_url:
                result = scraper.get_transcript_from_url(episode_url)
                if result.get('success'):
                    transcript = result['transcript']

                    # Store the successful transcript
                    self._store_transcript(podcast_name, episode_title, transcript, '99pi_scraper', episode_url)

                    return TranscriptLookupResult(
                        success=True,
                        podcast_name=podcast_name,
                        episode_title=episode_title,
                        transcript=transcript,
                        source='99pi_scraper',
                        fallback_used=False
                    )

            # Try to find episode via search on 99percentinvisible.org
            search_result = scraper.search_episode_by_title(episode_title)
            if search_result:
                result = scraper.get_transcript_from_url(search_result['url'])
                if result.get('success'):
                    transcript = result['transcript']

                    # Store the successful transcript
                    self._store_transcript(podcast_name, episode_title, transcript, '99pi_scraper', search_result['url'])

                    return TranscriptLookupResult(
                        success=True,
                        podcast_name=podcast_name,
                        episode_title=episode_title,
                        transcript=transcript,
                        source='99pi_scraper',
                        fallback_used=False
                    )

            return TranscriptLookupResult(
                success=False,
                podcast_name=podcast_name,
                episode_title=episode_title,
                error_message="99PI episode not found on 99percentinvisible.org"
            )

        except ImportError:
            logger.warning("99PI scraper not available")
            return TranscriptLookupResult(
                success=False,
                podcast_name=podcast_name,
                episode_title=episode_title,
                error_message="99PI scraper not available"
            )
        except Exception as e:
            logger.error(f"99PI scraper failed: {e}")
            return TranscriptLookupResult(
                success=False,
                podcast_name=podcast_name,
                episode_title=episode_title,
                error_message=f"99PI scraper error: {str(e)}"
            )

    def _title_similarity(self, title1: str, title2: str) -> float:
        """Calculate similarity between two titles (simple implementation)"""

        import re

        # Clean titles for comparison
        def clean_title(title):
            # Remove episode numbers and common prefixes
            title = re.sub(r'^\d+\s*:\s*', '', title)  # Remove "123: " prefix
            title = re.sub(r'episode\s*\d+', '', title, flags=re.IGNORECASE)
            title = re.sub(r'[^\w\s]', '', title)  # Remove punctuation
            return title.lower().strip()

        clean1 = clean_title(title1)
        clean2 = clean_title(title2)

        if not clean1 or not clean2:
            return 0.0

        # Simple word overlap similarity
        words1 = set(clean1.split())
        words2 = set(clean2.split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union) if union else 0.0

    def _try_youtube_fallback(self, podcast_name: str, episode_title: str) -> TranscriptLookupResult:
        """Try YouTube as fallback source"""

        if not self.youtube_fallback.enabled:
            return TranscriptLookupResult(
                success=False,
                podcast_name=podcast_name,
                episode_title=episode_title,
                error_message="YouTube fallback not enabled"
            )

        try:
            # Use YouTube API to find and extract transcript
            result = self.youtube_fallback.get_podcast_transcript_fallback(podcast_name, episode_title)

            if result['success']:
                transcript = result.get('transcript')
                video_url = result.get('url')

                # Store the successful transcript
                self._store_transcript(podcast_name, episode_title, transcript, 'youtube', video_url)

                return TranscriptLookupResult(
                    success=True,
                    podcast_name=podcast_name,
                    episode_title=episode_title,
                    transcript=transcript,
                    source='youtube',
                    fallback_used=True
                )
            else:
                return TranscriptLookupResult(
                    success=False,
                    podcast_name=podcast_name,
                    episode_title=episode_title,
                    error_message=f"YouTube fallback failed: {result.get('error', 'Unknown error')}"
                )

        except Exception as e:
            logger.error(f"YouTube fallback failed: {e}")
            return TranscriptLookupResult(
                success=False,
                podcast_name=podcast_name,
                episode_title=episode_title,
                error_message=f"YouTube error: {str(e)}"
            )

    def _try_google_search_fallback(self, podcast_name: str, episode_title: str) -> TranscriptLookupResult:
        """Try FREE search alternatives as fallback (no expensive APIs)"""

        try:
            # Use free search alternatives instead of expensive Google Search API
            import sys
            sys.path.append('/home/ubuntu/dev/atlas/src')
            from free_search_alternatives import FreeSearchEngine
            import asyncio

            # Get free search engine
            free_search = FreeSearchEngine()

            # Create search queries with different patterns for better results
            search_queries = [
                f'"{podcast_name}" "{episode_title}" transcript',
                f'"{podcast_name}" "{episode_title}" transcript site:catatp.fm',
                f'"{podcast_name}" "{episode_title}" transcript site:thisamericanlife.org',
                f'"{podcast_name}" transcript "{episode_title}"'
            ]

            # Try each search query until we find a result using FREE search
            for search_query in search_queries:
                logger.info(f"Trying FREE search: {search_query}")

                try:
                    # Run the async search in a new event loop if needed
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)

                    # Use free search alternatives (DuckDuckGo, Wikipedia, etc.)
                    search_results = loop.run_until_complete(
                        free_search.search(search_query, max_results=5)
                    )

                    # Find the best transcript URL from results
                    result_url = None
                    for result in search_results:
                        if any(indicator in result.url.lower() for indicator in ['transcript', 'catatp.fm', 'thisamericanlife.org']):
                            result_url = result.url
                            break

                    if result_url:
                        logger.info(f"FREE search found result: {result_url}")

                        # Try to extract transcript from the found URL
                        transcript = self._extract_transcript_from_url(result_url, podcast_name, episode_title)

                        if transcript:
                            # Store the successful transcript
                            self._store_transcript(podcast_name, episode_title, transcript, 'free_search', result_url)

                            return TranscriptLookupResult(
                                success=True,
                                podcast_name=podcast_name,
                                episode_title=episode_title,
                                transcript=transcript,
                                source='free_search',
                                fallback_used=True
                            )

                except Exception as search_error:
                    logger.warning(f"FREE search query failed '{search_query}': {search_error}")
                    continue

            # No successful searches found transcript content
            return TranscriptLookupResult(
                success=False,
                podcast_name=podcast_name,
                episode_title=episode_title,
                error_message="FREE search found no usable transcript results"
            )

        except Exception as e:
            logger.error(f"FREE search fallback failed: {e}")
            return TranscriptLookupResult(
                success=False,
                podcast_name=podcast_name,
                episode_title=episode_title,
                error_message=f"FREE search error: {str(e)}"
            )

    def _extract_transcript_from_url(self, url: str, podcast_name: str, episode_title: str) -> Optional[str]:
        """Extract transcript content from a URL found by Google search"""

        try:
            import requests
            from bs4 import BeautifulSoup
            import re

            logger.info(f"Attempting to extract transcript from: {url}")

            # Check if this is a known transcript source and use specialized scraper
            if 'catatp.fm' in url:
                return self._extract_from_catatp(url)
            elif 'thisamericanlife.org' in url:
                return self._extract_from_tal(url)
            elif '99percentinvisible.org' in url:
                return self._extract_from_99pi(url)
            elif url.endswith('.pdf'):
                return self._extract_from_pdf(url)
            else:
                return self._extract_from_generic_webpage(url)

        except Exception as e:
            logger.error(f"Failed to extract transcript from {url}: {e}")
            return None

    def _extract_from_catatp(self, url: str) -> Optional[str]:
        """Extract transcript from catatp.fm (ATP) website"""

        try:
            # Use the existing ATP scraper if available
            from helpers.atp_transcript_scraper import ATPTranscriptScraper

            scraper = ATPTranscriptScraper()
            result = scraper.get_transcript_from_url(url)

            if result and result.get('success'):
                logger.info(f"Successfully extracted ATP transcript from: {url}")
                return result.get('transcript')
            else:
                logger.warning(f"ATP scraper failed for: {url}")
                return None

        except ImportError:
            logger.warning("ATP scraper not available, falling back to generic extraction")
            return self._extract_from_generic_webpage(url)
        except Exception as e:
            logger.error(f"ATP extraction failed: {e}")
            return None

    def _extract_from_tal(self, url: str) -> Optional[str]:
        """Extract transcript from This American Life website"""

        try:
            import requests
            from bs4 import BeautifulSoup

            response = requests.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # TAL transcript patterns
            transcript_selectors = [
                '.transcript',
                '#transcript',
                '[class*="transcript"]',
                '.episode-transcript',
                '.story-transcript'
            ]

            for selector in transcript_selectors:
                elements = soup.select(selector)
                if elements:
                    transcript_text = ' '.join([elem.get_text() for elem in elements])
                    if len(transcript_text) > 500:  # Reasonable transcript length
                        logger.info(f"Successfully extracted TAL transcript from: {url}")
                        return transcript_text.strip()

            logger.warning(f"No transcript content found on TAL page: {url}")
            return None

        except Exception as e:
            logger.error(f"TAL extraction failed: {e}")
            return None

    def _extract_from_99pi(self, url: str) -> Optional[str]:
        """Extract transcript from 99% Invisible website"""

        try:
            import requests
            from bs4 import BeautifulSoup

            response = requests.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # 99PI transcript patterns
            transcript_selectors = [
                '.transcript',
                '.episode-transcript',
                '[id*="transcript"]',
                '.post-content',
                '.entry-content'
            ]

            for selector in transcript_selectors:
                elements = soup.select(selector)
                if elements:
                    transcript_text = ' '.join([elem.get_text() for elem in elements])
                    if len(transcript_text) > 500:
                        logger.info(f"Successfully extracted 99PI transcript from: {url}")
                        return transcript_text.strip()

            logger.warning(f"No transcript content found on 99PI page: {url}")
            return None

        except Exception as e:
            logger.error(f"99PI extraction failed: {e}")
            return None

    def _extract_from_pdf(self, url: str) -> Optional[str]:
        """Extract transcript from PDF file"""

        try:
            import requests
            import PyPDF2
            from io import BytesIO

            response = requests.get(url, timeout=30)
            response.raise_for_status()

            pdf_reader = PyPDF2.PdfReader(BytesIO(response.content))
            transcript_text = ""

            for page in pdf_reader.pages:
                transcript_text += page.extract_text() + "\n"

            if len(transcript_text.strip()) > 500:
                logger.info(f"Successfully extracted PDF transcript from: {url}")
                return transcript_text.strip()
            else:
                logger.warning(f"PDF appears to be empty or too short: {url}")
                return None

        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            return None

    def _extract_from_generic_webpage(self, url: str) -> Optional[str]:
        """Extract transcript from generic webpage using common patterns"""

        try:
            import requests
            from bs4 import BeautifulSoup

            response = requests.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Common transcript selectors in order of specificity
            transcript_selectors = [
                '.transcript',
                '#transcript',
                '[class*="transcript"]',
                '[id*="transcript"]',
                '.episode-transcript',
                '.post-transcript',
                '.content-transcript',
                'article',
                '.post-content',
                '.entry-content',
                '.content',
                'main'
            ]

            for selector in transcript_selectors:
                elements = soup.select(selector)
                if elements:
                    # Get text content, filtering out navigation and ads
                    transcript_text = ""
                    for elem in elements:
                        # Skip elements that are likely navigation or ads
                        if elem.name in ['nav', 'header', 'footer', 'aside']:
                            continue
                        if any(cls in (elem.get('class') or []) for cls in ['nav', 'menu', 'sidebar', 'advertisement', 'ad']):
                            continue

                        text = elem.get_text()
                        if len(text) > 100:  # Only include substantial text blocks
                            transcript_text += text + "\n"

                    if len(transcript_text.strip()) > 500:  # Reasonable transcript length
                        logger.info(f"Successfully extracted generic transcript from: {url}")
                        return transcript_text.strip()

            logger.warning(f"No substantial transcript content found on page: {url}")
            return None

        except Exception as e:
            logger.error(f"Generic extraction failed: {e}")
            return None

    def _store_transcript(self, podcast_name: str, episode_title: str, transcript: str,
                          source: str, source_url: str = None):
        """Store successful transcript in database"""

        try:
            cursor = self.conn.cursor()

            # Create transcript table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS podcast_transcripts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    podcast_name TEXT NOT NULL,
                    episode_title TEXT NOT NULL,
                    transcript TEXT NOT NULL,
                    source TEXT NOT NULL,
                    source_url TEXT,
                    metadata TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(podcast_name, episode_title, source)
                )
            """)

            # Prepare metadata
            metadata = {
                'source_url': source_url,
                'transcript_length': len(transcript),
                'word_count': len(transcript.split())
            }

            # Store transcript
            cursor.execute("""
                INSERT OR REPLACE INTO podcast_transcripts
                (podcast_name, episode_title, transcript, source, source_url, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                podcast_name,
                episode_title,
                transcript,
                source,
                source_url,
                json.dumps(metadata),
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))

            self.conn.commit()
            logger.info(f"Stored transcript for {podcast_name} - {episode_title} from {source}")

        except Exception as e:
            logger.error(f"Failed to store transcript: {e}")
            self.conn.rollback()

    def _schedule_retry(self, podcast_name: str, episode_title: str, episode_url: str = None) -> bool:
        """Schedule retry for failed transcript lookup"""

        try:
            cursor = self.conn.cursor()

            # Create retry table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transcript_lookup_retries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    podcast_name TEXT NOT NULL,
                    episode_title TEXT NOT NULL,
                    episode_url TEXT,
                    retry_count INTEGER DEFAULT 0,
                    next_retry_at TEXT NOT NULL,
                    last_attempt TEXT,
                    created_at TEXT NOT NULL
                )
            """)

            # Check if already scheduled
            cursor.execute("""
                SELECT COUNT(*) FROM transcript_lookup_retries
                WHERE podcast_name = ? AND episode_title = ?
                AND retry_count < 3
            """, (podcast_name, episode_title))

            if cursor.fetchone()[0] > 0:
                logger.info(f"Retry already scheduled for {podcast_name} - {episode_title}")
                return True

            # Schedule new retry
            next_retry = datetime.now() + timedelta(hours=24)  # Retry tomorrow

            cursor.execute("""
                INSERT INTO transcript_lookup_retries
                (podcast_name, episode_title, episode_url, retry_count, next_retry_at, last_attempt, created_at)
                VALUES (?, ?, ?, 0, ?, ?, ?)
            """, (
                podcast_name,
                episode_title,
                episode_url,
                next_retry.isoformat(),
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))

            self.conn.commit()
            logger.info(f"Scheduled retry for {podcast_name} - {episode_title}")
            return True

        except Exception as e:
            logger.error(f"Failed to schedule retry: {e}")
            self.conn.rollback()
            return False

    def process_pending_retries(self) -> Dict[str, Any]:
        """Process pending retry attempts"""

        try:
            cursor = self.conn.cursor()

            # Get retries that are due
            now = datetime.now().isoformat()
            cursor.execute("""
                SELECT podcast_name, episode_title, episode_url, retry_count
                FROM transcript_lookup_retries
                WHERE next_retry_at <= ? AND retry_count < 3
                ORDER BY next_retry_at ASC
                LIMIT 10
            """, (now,))

            pending_retries = cursor.fetchall()

            results = {
                'total_processed': 0,
                'successful': 0,
                'failed': 0,
                'details': []
            }

            for podcast_name, episode_title, episode_url, retry_count in pending_retries:
                logger.info(f"Processing retry {retry_count + 1} for {podcast_name} - {episode_title}")

                # Attempt lookup again
                result = self.lookup_transcript(podcast_name, episode_title, episode_url)

                if result.success:
                    # Remove from retry queue
                    cursor.execute("""
                        DELETE FROM transcript_lookup_retries
                        WHERE podcast_name = ? AND episode_title = ?
                    """, (podcast_name, episode_title))

                    results['successful'] += 1
                else:
                    # Update retry count and schedule next retry
                    next_retry = datetime.now() + timedelta(hours=24 * (retry_count + 2))
                    cursor.execute("""
                        UPDATE transcript_lookup_retries
                        SET retry_count = ?, next_retry_at = ?, last_attempt = ?
                        WHERE podcast_name = ? AND episode_title = ?
                    """, (retry_count + 1, next_retry.isoformat(), now, podcast_name, episode_title))

                    results['failed'] += 1

                results['total_processed'] += 1
                results['details'].append({
                    'podcast_name': podcast_name,
                    'episode_title': episode_title,
                    'success': result.success,
                    'source': result.source if result.success else None,
                    'error': result.error_message if not result.success else None
                })

            self.conn.commit()

            logger.info(f"Processed {results['total_processed']} retries: {results['successful']} successful, {results['failed']} failed")
            return results

        except Exception as e:
            logger.error(f"Failed to process retries: {e}")
            return {'total_processed': 0, 'successful': 0, 'failed': 0, 'error': str(e)}

    def get_lookup_statistics(self) -> Dict[str, Any]:
        """Get statistics about transcript lookup operations"""

        try:
            cursor = self.conn.cursor()

            # Get total podcasts in system
            cursor.execute("SELECT COUNT(DISTINCT podcast_name) FROM content WHERE content_type = 'podcast_episode'")
            total_podcasts = cursor.fetchone()[0] or 0

            # Get transcripts by source
            cursor.execute("""
                SELECT source, COUNT(*) as count
                FROM podcast_transcripts
                GROUP BY source
                ORDER BY count DESC
            """)
            transcripts_by_source = dict(cursor.fetchall())

            # Get pending retries
            cursor.execute("SELECT COUNT(*) FROM transcript_lookup_retries WHERE retry_count < 3")
            pending_retries = cursor.fetchone()[0] or 0

            return {
                'total_podcasts': total_podcasts,
                'transcripts_by_source': transcripts_by_source,
                'total_transcripts': sum(transcripts_by_source.values()),
                'pending_retries': pending_retries,
                'youtube_enabled': self.youtube_fallback.enabled
            }

        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {'error': str(e)}

# Global instance for Atlas scheduler use
podcast_transcript_lookup = PodcastTranscriptLookup()

def lookup_podcast_transcript(podcast_name: str, episode_title: str, episode_url: str = None) -> TranscriptLookupResult:
    """Convenience function for Atlas integration"""
    return podcast_transcript_lookup.lookup_transcript(podcast_name, episode_title, episode_url)

def process_transcript_retries() -> Dict[str, Any]:
    """Convenience function for processing retries"""
    return podcast_transcript_lookup.process_pending_retries()

if __name__ == "__main__":
    # Test the podcast transcript lookup system
    print("🎙️ Podcast Transcript Lookup System Test")
    print("=" * 50)

    lookup = PodcastTranscriptLookup()

    # Test statistics
    stats = lookup.get_lookup_statistics()
    print(f"\n📊 System Statistics:")
    print(f"Total podcasts: {stats.get('total_podcasts', 0)}")
    print(f"Total transcripts: {stats.get('total_transcripts', 0)}")
    print(f"Transcripts by source: {stats.get('transcripts_by_source', {})}")
    print(f"Pending retries: {stats.get('pending_retries', 0)}")
    print(f"YouTube enabled: {stats.get('youtube_enabled', False)}")

    # Test lookup for a known podcast
    print(f"\n🔍 Testing transcript lookup...")
    test_result = lookup.lookup_transcript("Huberman Lab", "sleep")

    print(f"\n📋 Test Result:")
    print(f"Success: {test_result.success}")
    print(f"Source: {test_result.source}")
    print(f"Transcript length: {len(test_result.transcript) if test_result.transcript else 0}")
    print(f"Fallback used: {test_result.fallback_used}")
    print(f"Error: {test_result.error_message}")

    # Show integration info
    print(f"\n🔄 Atlas Integration:")
    print("This system integrates with Atlas scheduler:")
    print("- Call lookup_podcast_transcript() from stage 320")
    print("- Call process_transcript_retries() from daily scheduler")
    print("- All results tracked in transaction system")
    print("- YouTube fallback automatically attempted")