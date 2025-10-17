#!/usr/bin/env python3
"""
YouTube API Client for Atlas

This module sets up the YouTube Data API v3 client to fetch subscribed channels,
playlists, and monitor new videos from subscribed channels.
"""

import os
import sys
import logging
from typing import List, Dict, Any, Optional
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json
from datetime import datetime, timedelta

# Add parent directory to path for Atlas integration
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from helpers.database_config import get_database_connection

class YouTubeAPIClient:
    """YouTube Data API v3 client for Atlas"""

    def __init__(self, api_key: str, credentials_file: Optional[str] = None):
        """
        Initialize the YouTube API client

        Args:
            api_key (str): YouTube Data API v3 key
            credentials_file (str, optional): Path to OAuth2 credentials file
        """
        self.api_key = api_key
        self.credentials_file = credentials_file
        self.service = None
        self.cache = {}
        self.rate_limit_remaining = 10000  # Default quota
        self.last_request_time = None

    def authenticate(self) -> None:
        """
        Set up YouTube Data API v3 client
        """
        try:
            if self.credentials_file and os.path.exists(self.credentials_file):
                # Use OAuth2 authentication
                from google.auth.transport.requests import Request
                from google.oauth2.credentials import Credentials
                from google_auth_oauthlib.flow import InstalledAppFlow

                creds = None
                # Load existing credentials
                if os.path.exists('token.json'):
                    creds = Credentials.from_authorized_user_file('token.json')

                # If there are no valid credentials, request authorization
                if not creds or not creds.valid:
                    if creds and creds.expired and creds.refresh_token:
                        creds.refresh(Request())
                    else:
                        flow = InstalledAppFlow.from_client_secrets_file(
                            self.credentials_file,
                            ['https://www.googleapis.com/auth/youtube.readonly']
                        )
                        creds = flow.run_local_server(port=0)

                    # Save credentials for next run
                    with open('token.json', 'w') as token:
                        token.write(creds.to_json())

                self.service = build('youtube', 'v3', credentials=creds)
            else:
                # Use API key authentication
                self.service = build('youtube', 'v3', developerKey=self.api_key)

        except Exception as e:
            logging.error(f"Failed to authenticate with YouTube API: {e}")
            raise

    def fetch_subscribed_channels(self) -> List[Dict[str, Any]]:
        """
        Fetch subscribed channels and playlists

        Returns:
            List[Dict[str, Any]]: List of subscribed channels with metadata
        """
        if not self.service:
            self.authenticate()

        self._check_rate_limit()

        try:
            # Fetch subscribed channels
            request = self.service.subscriptions().list(
                part='snippet,contentDetails',
                mine=True,
                maxResults=50
            )
            response = request.execute()

            channels = []
            for item in response.get('items', []):
                channel = {
                    'channel_id': item['snippet']['resourceId']['channelId'],
                    'title': item['snippet']['title'],
                    'description': item['snippet']['description'],
                    'published_at': item['snippet']['publishedAt'],
                    'thumbnails': item['snippet']['thumbnails'],
                    'playlist_id': item['contentDetails']['activityType']
                }
                channels.append(channel)

            # Cache results
            self.cache['subscribed_channels'] = channels
            self._update_rate_limit(response)

            return channels

        except HttpError as e:
            logging.error(f"YouTube API error fetching channels: {e}")
            raise
        except Exception as e:
            logging.error(f"Failed to fetch subscribed channels: {e}")
            raise

    def monitor_new_videos(self, channel_ids: List[str] = None) -> List[Dict[str, Any]]:
        """
        Monitor new videos from subscribed channels

        Args:
            channel_ids (List[str], optional): Specific channel IDs to monitor

        Returns:
            List[Dict[str, Any]]: List of new videos
        """
        if not self.service:
            self.authenticate()

        self._check_rate_limit()

        try:
            # If no specific channels provided, get all subscribed channels
            if not channel_ids:
                if 'subscribed_channels' in self.cache:
                    channel_ids = [ch['channel_id'] for ch in self.cache['subscribed_channels']]
                else:
                    channels = self.fetch_subscribed_channels()
                    channel_ids = [ch['channel_id'] for ch in channels]

            # Fetch recent videos from each channel
            all_videos = []
            for channel_id in channel_ids[:10]:  # Limit to avoid rate limits
                videos = self._fetch_channel_videos(channel_id)
                all_videos.extend(videos)

            # Sort by publish date (newest first)
            all_videos.sort(key=lambda x: x['published_at'], reverse=True)

            # Cache results
            self.cache['recent_videos'] = all_videos
            self._update_rate_limit()

            return all_videos

        except Exception as e:
            logging.error(f"Failed to monitor new videos: {e}")
            raise

    def _fetch_channel_videos(self, channel_id: str) -> List[Dict[str, Any]]:
        """
        Fetch recent videos from a specific channel

        Args:
            channel_id (str): YouTube channel ID

        Returns:
            List[Dict[str, Any]]: List of videos from the channel
        """
        try:
            # Search for recent videos from channel
            request = self.service.search().list(
                part='snippet',
                channelId=channel_id,
                order='date',
                type='video',
                maxResults=10
            )
            response = request.execute()

            videos = []
            for item in response.get('items', []):
                video = {
                    'video_id': item['id']['videoId'],
                    'title': item['snippet']['title'],
                    'description': item['snippet']['description'],
                    'channel_id': item['snippet']['channelId'],
                    'channel_title': item['snippet']['channelTitle'],
                    'published_at': item['snippet']['publishedAt'],
                    'thumbnails': item['snippet']['thumbnails'],
                    'url': f"https://www.youtube.com/watch?v={item['id']['videoId']}"
                }
                videos.append(video)

            self._update_rate_limit(response)
            return videos

        except HttpError as e:
            logging.warning(f"YouTube API error fetching videos for channel {channel_id}: {e}")
            return []
        except Exception as e:
            logging.warning(f"Failed to fetch videos for channel {channel_id}: {e}")
            return []

    def extract_video_transcripts(self, video_ids: List[str]) -> Dict[str, str]:
        """
        Extract video transcripts when available

        Args:
            video_ids (List[str]): List of YouTube video IDs

        Returns:
            Dict[str, str]: Mapping of video IDs to transcripts
        """
        # Note: YouTube Data API v3 does not provide transcripts directly
        # This would require using the YouTube Transcript API or similar service
        transcripts = {}

        # Simulate transcript extraction
        for video_id in video_ids[:5]:  # Limit to avoid issues
            # In a real implementation, we would use a library like youtube-transcript-api
            # transcript = YouTubeTranscriptApi.get_transcript(video_id)
            # transcripts[video_id] = " ".join([entry['text'] for entry in transcript])
            transcripts[video_id] = f"Transcript for video {video_id} would be extracted here."

        return transcripts

    def _check_rate_limit(self) -> None:
        """
        Check if we're approaching rate limits and delay if necessary
        """
        # Simple rate limiting implementation
        if self.last_request_time:
            time_since_last = datetime.now() - self.last_request_time
            if time_since_last < timedelta(seconds=1):
                # Wait to avoid hitting rate limits
                import time
                time.sleep(1)

    def _update_rate_limit(self, response: Dict = None) -> None:
        """
        Update rate limit tracking based on API response

        Args:
            response (Dict, optional): API response with quota information
        """
        self.last_request_time = datetime.now()
        if response and 'quota' in response:
            self.rate_limit_remaining = response['quota'].get('remaining', self.rate_limit_remaining)

    def cache_metadata(self, metadata: Dict[str, Any]) -> None:
        """
        Cache channel and video metadata locally

        Args:
            metadata (Dict[str, Any]): Metadata to cache
        """
        # In a real implementation, this would store metadata in a local database
        cache_file = 'youtube_metadata_cache.json'
        try:
            if os.path.exists(cache_file):
                with open(cache_file, 'r') as f:
                    existing_cache = json.load(f)
                existing_cache.update(metadata)
                cache_data = existing_cache
            else:
                cache_data = metadata

            with open(cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)

        except Exception as e:
            logging.warning(f"Failed to cache metadata: {e}")

    def store_videos_in_atlas(self, videos: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Store discovered videos in Atlas database

        Args:
            videos: List of video dictionaries from API

        Returns:
            Dict with success/failure counts
        """
        results = {"success": 0, "failed": 0, "duplicate": 0}

        try:
            conn = get_database_connection()
            cursor = conn.cursor()

            for video in videos:
                try:
                    video_id = video['video_id']

                    # Check if video already exists
                    cursor.execute("""
                        SELECT COUNT(*) FROM content
                        WHERE content_type = 'youtube_video'
                        AND url LIKE ?
                    """, (f"%{video_id}%",))

                    if cursor.fetchone()[0] > 0:
                        results["duplicate"] += 1
                        continue

                    # Prepare content
                    content = f"""YouTube Video: {video['title']}
Channel: {video['channel_title']}
Video ID: {video_id}
Published: {video['published_at']}
Platform: YouTube
Source: youtube-api-client

Description:
{video.get('description', 'No description available')}

URL: {video['url']}"""

                    # Prepare metadata JSON
                    metadata = {
                        "video_id": video_id,
                        "channel_id": video['channel_id'],
                        "channel_title": video['channel_title'],
                        "published_at": video['published_at'],
                        "thumbnails": video.get('thumbnails', {}),
                        "platform": "youtube",
                        "source": "youtube-api-client"
                    }

                    # Insert into database
                    cursor.execute("""
                        INSERT INTO content (
                            title, url, content, content_type, metadata,
                            created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        video['title'],
                        video['url'],
                        content,
                        'youtube_video',
                        json.dumps(metadata),
                        datetime.now().isoformat(),
                        datetime.now().isoformat()
                    ))

                    results["success"] += 1

                except Exception as e:
                    logging.error(f"Failed to store video {video.get('video_id', 'unknown')}: {e}")
                    results["failed"] += 1

            conn.commit()
            conn.close()

            logging.info(f"Stored videos in Atlas: {results}")
            return results

        except Exception as e:
            logging.error(f"Failed to store videos in Atlas: {e}")
            return {"success": 0, "failed": len(videos), "duplicate": 0}

def main():
    """Example usage of YouTubeAPIClient"""
    # Example usage (requires valid API key)
    api_key = os.environ.get('YOUTUBE_API_KEY', 'YOUR_API_KEY_HERE')

    client = YouTubeAPIClient(api_key)

    try:
        # Authenticate
        client.authenticate()
        print("YouTube API client authenticated successfully!")

        # Fetch subscribed channels
        print("Fetching subscribed channels...")
        channels = client.fetch_subscribed_channels()
        print(f"Found {len(channels)} subscribed channels")

        # Monitor new videos
        print("Monitoring new videos...")
        videos = client.monitor_new_videos()
        print(f"Found {len(videos)} recent videos")

        # Store videos in Atlas database
        if videos:
            print("Storing videos in Atlas database...")
            storage_results = client.store_videos_in_atlas(videos)
            print(f"Storage results: {storage_results}")

        # Extract transcripts (simulated)
        if videos:
            video_ids = [v['video_id'] for v in videos[:3]]
            transcripts = client.extract_video_transcripts(video_ids)
            print(f"Extracted transcripts for {len(transcripts)} videos")

        print("YouTube API client demo completed successfully!")

    except Exception as e:
        print(f"Failed to use YouTube API client: {e}")

if __name__ == "__main__":
    main()