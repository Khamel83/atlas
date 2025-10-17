#!/usr/bin/env python3
"""
YouTube Modules Integration

This module integrates both YouTube utilities into the numeric stage system:
1. YouTube History Scraper - for collecting watched videos
2. YouTube Podcast Fallback - for transcript extraction

These are utility modules that can be called from different stages.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

# Import YouTube modules
try:
    from automation.youtube_history_scraper import YouTubeHistoryScraper, YouTubeVideo
    from helpers.youtube_podcast_fallback import YouTubePodcastFallback
    YOUTUBE_MODULES_AVAILABLE = True
except ImportError as e:
    YOUTUBE_MODULES_AVAILABLE = False
    logging.warning(f"YouTube modules not available: {e}")

from helpers.numeric_stages import NumericStage
from helpers.content_transactions import TransactionTimer
from helpers.database_config import get_database_connection

logger = logging.getLogger(__name__)

class YouTubeIntegrationManager:
    """Manages YouTube module integration with the numeric stage system"""

    def __init__(self):
        self.youtube_scraper = None
        self.youtube_fallback = None
        self.session_valid = False

        if YOUTUBE_MODULES_AVAILABLE:
            self._initialize_modules()

    def _initialize_modules(self):
        """Initialize YouTube modules"""
        try:
            # Initialize YouTube fallback (for podcast transcripts)
            self.youtube_fallback = YouTubePodcastFallback()

            # YouTube scraper will be initialized on demand (requires browser)
            logger.info("YouTube integration manager initialized")
        except Exception as e:
            logger.error(f"Failed to initialize YouTube modules: {e}")

    def collect_watched_videos(self, max_videos: int = 200, days_back: int = 7) -> Dict[str, Any]:
        """
        Collect recently watched YouTube videos
        Can be called from content acquisition stages (100-199)

        Args:
            max_videos (int): Maximum videos to collect
            days_back (int): How many days back to look

        Returns:
            Dict[str, Any]: Collection result with video data
        """
        if not YOUTUBE_MODULES_AVAILABLE:
            return {
                'success': False,
                'error': 'YouTube modules not available',
                'videos_collected': 0
            }

        try:
            # Initialize scraper if needed
            if not self.youtube_scraper:
                self.youtube_scraper = YouTubeHistoryScraper(headless=True, timeout=60)

            # Setup and authenticate
            self.youtube_scraper.setup_driver()

            # Try to use existing session
            if not self.youtube_scraper.login_to_google(interactive=False):
                return {
                    'success': False,
                    'error': 'No valid YouTube session. Please run setup_youtube_scraper.py first.',
                    'videos_collected': 0
                }

            # Navigate to history
            if not self.youtube_scraper.navigate_to_youtube_history():
                return {
                    'success': False,
                    'error': 'Failed to access YouTube history',
                    'videos_collected': 0
                }

            # Scrape videos
            videos = self.youtube_scraper.scrape_history_videos(
                max_videos=max_videos,
                days_back=days_back
            )

            # Convert to Atlas-compatible format
            atlas_videos = []
            for video in videos:
                video_data = {
                    'url': video.url,
                    'title': video.title,
                    'content_type': 'youtube_video',
                    'source': 'youtube_history',
                    'metadata': {
                        'video_id': video.video_id,
                        'channel': video.channel,
                        'watched_at': video.watched_at,
                        'duration': video.duration,
                        'description': video.description,
                        'view_count': video.view_count,
                        'collected_at': datetime.now().isoformat()
                    }
                }
                atlas_videos.append(video_data)

            # Store videos for processing
            stored_count = self._store_youtube_videos(atlas_videos)

            # Timer metadata captured automatically

            result = {
                'success': True,
                'videos_collected': len(videos),
                'videos_stored': stored_count,
                'days_back': days_back,
                'collection_time': datetime.now().isoformat()
            }

            logger.info(f"Collected {len(videos)} YouTube videos, stored {stored_count}")
            return result

        except Exception as e:
            logger.error(f"YouTube history collection failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'videos_collected': 0
            }
        finally:
            if hasattr(self, 'youtube_scraper') and self.youtube_scraper:
                try:
                    self.youtube_scraper.close_driver()
                except:
                    pass

    def get_podcast_transcript_fallback(self, podcast_name: str, episode_title: str) -> Dict[str, Any]:
        """
        Get podcast transcript from YouTube as fallback
        Can be called from transcript extraction stages (300-399)

        Args:
            podcast_name (str): Name of the podcast
            episode_title (str): Title of the episode

        Returns:
            Dict[str, Any]: Transcript result
        """
        if not self.youtube_fallback or not self.youtube_fallback.enabled:
            return {
                'success': False,
                'error': 'YouTube fallback not enabled',
                'source': 'youtube'
            }

        try:
            result = self.youtube_fallback.get_podcast_transcript_fallback(
                podcast_name, episode_title
            )

            if result['success']:
                logger.info(f"YouTube fallback successful for {podcast_name} - {episode_title}")
            else:
                logger.warning(f"YouTube fallback failed for {podcast_name} - {episode_title}")

            return result

        except Exception as e:
            logger.error(f"YouTube transcript fallback failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'source': 'youtube'
            }

    def search_youtube_for_content(self, query: str, content_type: str = "general") -> Dict[str, Any]:
        """
        Search YouTube for content related to a query
        Can be called from content discovery stages (50-99)

        Args:
            query (str): Search query
            content_type (str): Type of content (podcast, general, etc.)

        Returns:
            Dict[str, Any]: Search results
        """
        if not self.youtube_fallback or not self.youtube_fallback.enabled:
            return {
                'success': False,
                'error': 'YouTube search not enabled',
                'results': []
            }

        try:
            if content_type == "podcast":
                results = self.youtube_fallback.search_podcast_channel(query, max_results=10)
            else:
                # For general search, we'd need to implement it
                # For now, return empty
                results = []

            return {
                'success': True,
                'results': [
                    {
                        'video_id': r.video_id,
                        'title': r.title,
                        'channel': r.channel,
                        'url': r.url,
                        'published_at': r.published_at
                    }
                    for r in results
                ],
                'query': query,
                'content_type': content_type
            }

        except Exception as e:
            logger.error(f"YouTube search failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'results': []
            }

    def _store_youtube_videos(self, videos: List[Dict[str, Any]]) -> int:
        """Store collected YouTube videos in Atlas database"""
        try:
            conn = get_database_connection()
            cursor = conn.cursor()

            stored_count = 0

            for video in videos:
                try:
                    # Check if video already exists
                    cursor.execute("""
                        SELECT COUNT(*) FROM content
                        WHERE content_type = 'youtube_video'
                        AND url = ?
                    """, (video['url'],))

                    if cursor.fetchone()[0] > 0:
                        continue  # Skip duplicates

                    # Insert video
                    cursor.execute("""
                        INSERT INTO content (
                            title, url, content, content_type, metadata,
                            created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        video['title'],
                        video['url'],
                        f"YouTube Video: {video['title']}\nChannel: {video['metadata']['channel']}\nSource: YouTube History",
                        'youtube_video',
                        json.dumps(video['metadata']),
                        datetime.now().isoformat(),
                        datetime.now().isoformat()
                    ))

                    stored_count += 1

                except Exception as e:
                    logger.error(f"Failed to store YouTube video {video['url']}: {e}")
                    continue

            conn.commit()
            conn.close()

            logger.info(f"Stored {stored_count} new YouTube videos in Atlas database")
            return stored_count

        except Exception as e:
            logger.error(f"Failed to store YouTube videos in database: {e}")
            return 0

    def get_youtube_collection_status(self) -> Dict[str, Any]:
        """Get status of YouTube integration"""
        return {
            'modules_available': YOUTUBE_MODULES_AVAILABLE,
            'fallback_enabled': bool(self.youtube_fallback and self.youtube_fallback.enabled),
            'session_valid': self.session_valid,
            'last_collection': None  # TODO: Track last collection time
        }

# Global instance for workflow system use
youtube_integration = YouTubeIntegrationManager()

# Convenience functions for workflow integration
def collect_youtube_history(max_videos: int = 200, days_back: int = 7) -> Dict[str, Any]:
    """Convenience function for workflow system"""
    return youtube_integration.collect_watched_videos(max_videos, days_back)

def get_youtube_podcast_transcript(podcast_name: str, episode_title: str) -> Dict[str, Any]:
    """Convenience function for workflow system"""
    return youtube_integration.get_podcast_transcript_fallback(podcast_name, episode_title)

def search_youtube_content(query: str, content_type: str = "general") -> Dict[str, Any]:
    """Convenience function for workflow system"""
    return youtube_integration.search_youtube_for_content(query, content_type)

if __name__ == "__main__":
    # Test YouTube integration
    print("🎬 YouTube Integration Test")
    print("=" * 40)

    integration = YouTubeIntegrationManager()

    # Test status
    status = integration.get_youtube_collection_status()
    print(f"Modules available: {status['modules_available']}")
    print(f"Fallback enabled: {status['fallback_enabled']}")

    if status['fallback_enabled']:
        # Test podcast fallback
        print("\n🎙️ Testing podcast transcript fallback...")
        result = get_youtube_podcast_transcript("Huberman Lab", "sleep")
        print(f"Success: {result['success']}")
        if result['success']:
            print(f"Title: {result.get('title', 'N/A')}")
            print(f"Transcript length: {len(result.get('transcript', ''))}")

    # Test history collection (will likely fail without setup)
    print("\n📺 Testing history collection...")
    history_result = collect_youtube_history(max_videos=5, days_back=1)
    print(f"Success: {history_result['success']}")
    if not history_result['success']:
        print(f"Error: {history_result['error']}")