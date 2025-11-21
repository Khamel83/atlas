"""
YouTube transcript resolver for podcast episodes.
Searches for YouTube versions of podcast episodes and extracts auto-generated captions.
"""

import logging
import re
import time
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse, parse_qs
import requests
from bs4 import BeautifulSoup

try:
    from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
    YOUTUBE_API_AVAILABLE = True
except ImportError:
    YOUTUBE_API_AVAILABLE = False

logger = logging.getLogger(__name__)

class YouTubeTranscriptResolver:
    """Resolves transcripts from YouTube for podcast episodes."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def find_youtube_episode(self, episode_title: str, podcast_name: str) -> Optional[str]:
        """Search YouTube for the podcast episode and return video URL."""
        # Clean up title for search - be more aggressive
        clean_title = re.sub(r'[^\w\s-]', '', episode_title)
        clean_title = clean_title[:50]  # Limit length

        # Try multiple search variations
        search_queries = [
            f'"{podcast_name}" "{clean_title}"',
            f"{podcast_name} {clean_title}",
            f'"{clean_title}" podcast'
        ]

        for search_query in search_queries:
            try:
                # YouTube search URL
                search_url = f"https://www.youtube.com/results?search_query={search_query.replace(' ', '+')}"

                response = self.session.get(search_url, timeout=15)
                response.raise_for_status()

                # Extract video IDs from search results - try multiple patterns
                patterns = [
                    r'"videoId":"([^"]+)"',
                    r'/watch\?v=([^"&]+)',
                    r'videoId&quot;:&quot;([^&]+)&quot;'
                ]

                for pattern in patterns:
                    video_ids = re.findall(pattern, response.text)
                    if video_ids:
                        # Filter out shorts and live streams
                        for vid_id in video_ids[:3]:  # Check first 3 results
                            if len(vid_id) == 11:  # YouTube video IDs are 11 chars
                                video_url = f"https://www.youtube.com/watch?v={vid_id}"
                                logger.info(f"Found YouTube match for '{episode_title}': {video_url}")
                                return video_url

            except Exception as e:
                logger.debug(f"YouTube search failed for '{search_query}': {e}")
                continue

        return None

    def extract_transcript(self, youtube_url: str) -> Optional[Dict[str, Any]]:
        """Extract transcript from YouTube video using official API."""
        if not YOUTUBE_API_AVAILABLE:
            logger.warning("YouTube transcript API not available")
            return None

        try:
            # Extract video ID
            video_id = self._extract_video_id(youtube_url)
            if not video_id:
                return None

            # Try to get transcript using API
            try:
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'en-US', 'en-GB'])

                # Combine transcript segments
                full_text = ' '.join([entry['text'] for entry in transcript_list])

                # Clean up the text
                clean_text = self._clean_transcript_text(full_text)

                if clean_text and len(clean_text) > 100:
                    return {
                        'text': clean_text,
                        'source': 'youtube_auto_captions',
                        'video_url': youtube_url,
                        'video_id': video_id,
                        'accuracy': 'high',
                        'segments': len(transcript_list)
                    }

            except (TranscriptsDisabled, NoTranscriptFound) as e:
                logger.debug(f"No transcript available for video {video_id}: {e}")
                return None

        except Exception as e:
            logger.error(f"Failed to extract transcript from {youtube_url}: {e}")

        return None

    def _clean_transcript_text(self, text: str) -> str:
        """Clean transcript text."""
        if not text:
            return ""

        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())

        # Remove common auto-caption artifacts
        text = re.sub(r'\[Music\]|\[Applause\]|\[Laughter\]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\[.*?\]', '', text)  # Remove any bracketed content

        # Fix spacing around punctuation
        text = re.sub(r'\s+([,.!?])', r'\1', text)
        text = re.sub(r'([.!?])\s*([A-Z])', r'\1 \2', text)

        return text.strip()

    def _extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from YouTube URL."""
        if 'youtube.com' in url:
            parsed = urlparse(url)
            if parsed.path == '/watch':
                return parse_qs(parsed.query).get('v', [None])[0]
        elif 'youtu.be' in url:
            return urlparse(url).path.lstrip('/')
        return None


    def resolve_for_episode(self, episode_title: str, podcast_name: str, episode_url: str = None) -> List[Dict[str, Any]]:
        """Main resolver method - find and extract YouTube transcript for episode."""
        results = []

        # First try to find YouTube version
        youtube_url = self.find_youtube_episode(episode_title, podcast_name)

        if youtube_url:
            logger.info(f"Found YouTube version for '{episode_title}': {youtube_url}")

            # Extract transcript
            transcript = self.extract_transcript(youtube_url)
            if transcript:
                results.append({
                    'url': youtube_url,
                    'text': transcript['text'],
                    'source': transcript['source'],
                    'metadata': {
                        'video_id': transcript['video_id'],
                        'accuracy': transcript['accuracy'],
                        'method': 'youtube_auto_captions'
                    }
                })
                logger.info(f"Extracted YouTube transcript for '{episode_title}' ({len(transcript['text'])} chars)")
            else:
                logger.debug(f"No transcript available for YouTube video: {youtube_url}")
        else:
            logger.debug(f"No YouTube version found for '{episode_title}'")

        return results

def create_resolver() -> YouTubeTranscriptResolver:
    """Factory function to create resolver instance."""
    return YouTubeTranscriptResolver()