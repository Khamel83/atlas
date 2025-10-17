#!/usr/bin/env python3
"""
YouTube Podcast Transcript Fallback Module

This module uses the YouTube Data API v3 to:
1. Search for podcasts on YouTube
2. Extract transcripts when podcast transcripts aren't available elsewhere
3. Provide backup transcript source for the workflow system

Integrates with the numeric stage system as a utility module.
"""

import os
import logging
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# YouTube API imports
try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    YOUTUBE_API_AVAILABLE = True
except ImportError:
    YOUTUBE_API_AVAILABLE = False
    logging.warning("Google API client not available - YouTube fallback disabled")

# Transcript extraction
try:
    from youtube_transcript_api import YouTubeTranscriptApi
    TRANSCRIPT_API_AVAILABLE = True
except ImportError:
    TRANSCRIPT_API_AVAILABLE = False
    logging.warning("youtube-transcript-api not available")

@dataclass
class YouTubePodcastResult:
    """YouTube podcast search result"""
    video_id: str
    title: str
    channel: str
    url: str
    published_at: str
    duration: Optional[str] = None
    transcript: Optional[str] = None
    description_links: List[str] = None

class YouTubePodcastFallback:
    """YouTube API fallback for podcast transcripts"""

    def __init__(self, api_key: str = None):
        """
        Initialize YouTube podcast fallback

        Args:
            api_key (str): YouTube Data API v3 key
        """
        self.api_key = api_key or os.getenv('YOUTUBE_API_KEY')
        self.youtube_service = None
        self.enabled = bool(self.api_key and YOUTUBE_API_AVAILABLE)

        if self.enabled:
            try:
                self.youtube_service = build('youtube', 'v3', developerKey=self.api_key)
                logging.info("YouTube podcast fallback initialized")
            except Exception as e:
                logging.error(f"Failed to initialize YouTube service: {e}")
                self.enabled = False
        else:
            logging.warning("YouTube podcast fallback disabled - missing API key or dependencies")

    def search_podcast_episode(self, podcast_name: str, episode_title: str,
                              max_results: int = 5) -> List[YouTubePodcastResult]:
        """
        Search for a specific podcast episode on YouTube

        Args:
            podcast_name (str): Name of the podcast
            episode_title (str): Title or partial title of the episode
            max_results (int): Maximum number of results to return

        Returns:
            List[YouTubePodcastResult]: Matching YouTube videos
        """
        if not self.enabled:
            return []

        try:
            # Construct search query
            search_query = f"{podcast_name} {episode_title}"

            # Search for videos
            search_response = self.youtube_service.search().list(
                q=search_query,
                part='snippet',
                type='video',
                maxResults=max_results,
                order='relevance'
            ).execute()

            results = []
            for item in search_response.get('items', []):
                video_id = item['id']['videoId']
                snippet = item['snippet']

                result = YouTubePodcastResult(
                    video_id=video_id,
                    title=snippet['title'],
                    channel=snippet['channelTitle'],
                    url=f"https://www.youtube.com/watch?v={video_id}",
                    published_at=snippet['publishedAt'],
                    description_links=[]
                )

                results.append(result)

            logging.info(f"Found {len(results)} YouTube results for '{search_query}'")
            return results

        except HttpError as e:
            logging.error(f"YouTube API error searching for podcast: {e}")
            return []
        except Exception as e:
            logging.error(f"Failed to search YouTube for podcast: {e}")
            return []

    def search_podcast_channel(self, podcast_name: str,
                               max_results: int = 10) -> List[YouTubePodcastResult]:
        """
        Search for recent episodes from a podcast channel

        Args:
            podcast_name (str): Name of the podcast/channel
            max_results (int): Maximum number of episodes to return

        Returns:
            List[YouTubePodcastResult]: Recent episodes from the channel
        """
        if not self.enabled:
            return []

        try:
            # Search for channel content
            search_response = self.youtube_service.search().list(
                q=podcast_name,
                part='snippet',
                type='video',
                maxResults=max_results,
                order='date'
            ).execute()

            results = []
            for item in search_response.get('items', []):
                video_id = item['id']['videoId']
                snippet = item['snippet']

                result = YouTubePodcastResult(
                    video_id=video_id,
                    title=snippet['title'],
                    channel=snippet['channelTitle'],
                    url=f"https://www.youtube.com/watch?v={video_id}",
                    published_at=snippet['publishedAt'],
                    description_links=[]
                )

                results.append(result)

            logging.info(f"Found {len(results)} recent episodes from '{podcast_name}'")
            return results

        except HttpError as e:
            logging.error(f"YouTube API error searching for channel: {e}")
            return []
        except Exception as e:
            logging.error(f"Failed to search YouTube for channel: {e}")
            return []

    def get_video_transcript(self, video_id: str) -> Optional[str]:
        """
        Extract transcript from a YouTube video

        Args:
            video_id (str): YouTube video ID

        Returns:
            Optional[str]: Transcript text if available
        """
        if not TRANSCRIPT_API_AVAILABLE:
            logging.warning("YouTube transcript API not available")
            return None

        try:
            # Get transcript
            transcript_api = YouTubeTranscriptApi()
            transcript_list = transcript_api.fetch(video_id)

            # Combine all text segments
            transcript_text = " ".join([entry['text'] for entry in transcript_list])

            logging.info(f"Extracted transcript for video {video_id} ({len(transcript_text)} chars)")
            return transcript_text

        except Exception as e:
            logging.warning(f"Failed to get transcript for video {video_id}: {e}")
            return None

    def extract_description_links(self, video_id: str) -> List[str]:
        """
        Extract URLs from video description

        Args:
            video_id (str): YouTube video ID

        Returns:
            List[str]: URLs found in description
        """
        if not self.enabled:
            return []

        try:
            # Get video details including description
            video_response = self.youtube_service.videos().list(
                part='snippet',
                id=video_id
            ).execute()

            if not video_response.get('items'):
                return []

            description = video_response['items'][0]['snippet']['description']

            # Simple URL extraction
            import re
            url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
            urls = re.findall(url_pattern, description)

            logging.info(f"Found {len(urls)} URLs in description for video {video_id}")
            return urls

        except Exception as e:
            logging.warning(f"Failed to extract description links for video {video_id}: {e}")
            return []

    def get_podcast_transcript_fallback(self, podcast_name: str, episode_title: str) -> Dict[str, Any]:
        """
        Complete fallback: search for podcast episode and extract transcript

        Args:
            podcast_name (str): Name of the podcast
            episode_title (str): Title of the episode

        Returns:
            Dict[str, Any]: Result with transcript and metadata
        """
        if not self.enabled:
            return {
                'success': False,
                'error': 'YouTube fallback not enabled',
                'source': 'youtube'
            }

        try:
            # Search for the episode
            results = self.search_podcast_episode(podcast_name, episode_title)

            if not results:
                return {
                    'success': False,
                    'error': f'No YouTube results found for {podcast_name} - {episode_title}',
                    'source': 'youtube'
                }

            # Try the best match
            best_match = results[0]

            # Get transcript
            transcript = self.get_video_transcript(best_match.video_id)

            # Extract description links
            links = self.extract_description_links(best_match.video_id)

            result = {
                'success': bool(transcript),
                'source': 'youtube',
                'video_id': best_match.video_id,
                'title': best_match.title,
                'channel': best_match.channel,
                'url': best_match.url,
                'transcript': transcript,
                'description_links': links,
                'published_at': best_match.published_at,
                'fallback_type': 'youtube_podcast_video'
            }

            if transcript:
                logging.info(f"Successfully got YouTube transcript for {podcast_name} - {episode_title}")
            else:
                logging.warning(f"YouTube video found but no transcript available for {podcast_name} - {episode_title}")

            return result

        except Exception as e:
            logging.error(f"YouTube fallback failed for {podcast_name} - {episode_title}: {e}")
            return {
                'success': False,
                'error': str(e),
                'source': 'youtube'
            }

# Integration function for workflow system
def get_youtube_transcript_fallback(podcast_name: str, episode_title: str) -> Dict[str, Any]:
    """
    Convenience function for workflow system integration

    Args:
        podcast_name (str): Name of the podcast
        episode_title (str): Title of the episode

    Returns:
        Dict[str, Any]: Fallback result
    """
    fallback = YouTubePodcastFallback()
    return fallback.get_podcast_transcript_fallback(podcast_name, episode_title)

if __name__ == "__main__":
    # Test the YouTube podcast fallback
    fallback = YouTubePodcastFallback()

    if fallback.enabled:
        print("🎬 YouTube Podcast Fallback Test")
        print("=" * 40)

        # Test search
        test_podcast = "Huberman Lab"
        test_episode = "sleep"

        print(f"\n🔍 Searching for: {test_podcast} - {test_episode}")
        results = fallback.search_podcast_episode(test_podcast, test_episode)

        print(f"Found {len(results)} results:")
        for i, result in enumerate(results[:3], 1):
            print(f"{i}. {result.title}")
            print(f"   Channel: {result.channel}")
            print(f"   URL: {result.url}")
            print()

        # Test transcript extraction
        if results:
            print(f"\n📝 Testing transcript extraction for first result...")
            transcript_result = fallback.get_podcast_transcript_fallback(test_podcast, test_episode)

            if transcript_result['success']:
                print(f"✅ Transcript extracted ({len(transcript_result['transcript'])} chars)")
                print(f"   Links found: {len(transcript_result['description_links'])}")
            else:
                print(f"❌ Failed to extract transcript: {transcript_result['error']}")
    else:
        print("❌ YouTube fallback not enabled - check API key")