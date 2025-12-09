"""
YouTube transcript resolver for podcast episodes.
Searches for YouTube versions of podcast episodes and extracts auto-generated captions.

Supports cookie authentication for bypassing IP blocks when running from home network.
Set YOUTUBE_COOKIES_PATH environment variable to path of cookies.txt file.
Use browser extension like "Get cookies.txt LOCALLY" to export cookies from youtube.com.
"""

import logging
import os
import re
import time
from pathlib import Path
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse, parse_qs
import requests
from bs4 import BeautifulSoup

try:
    from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
    from youtube_transcript_api.proxies import GenericProxyConfig
    YOUTUBE_API_AVAILABLE = True
except ImportError:
    YOUTUBE_API_AVAILABLE = False
    GenericProxyConfig = None

logger = logging.getLogger(__name__)

# Cookie file path for YouTube authentication
# Set via environment variable or use default location
YOUTUBE_COOKIES_PATH = os.environ.get(
    'YOUTUBE_COOKIES_PATH',
    os.path.expanduser('~/.config/atlas/youtube_cookies.txt')
)

# Proxy configuration for YouTube
# Format: socks5://user:pass@host:port or http://user:pass@host:port
YOUTUBE_PROXY_URL = os.environ.get('YOUTUBE_PROXY_URL', '')

# Rate limiting - YouTube blocks IPs that request too fast
# Default: 30 seconds between requests (safe), set to 0 to disable
YOUTUBE_RATE_LIMIT_SECONDS = int(os.environ.get('YOUTUBE_RATE_LIMIT_SECONDS', '30'))
_last_youtube_request = 0

class YouTubeTranscriptResolver:
    """Resolves transcripts from YouTube for podcast episodes."""

    def __init__(self, cookies_path: str = None):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        # Load cookies if available
        self.cookies_path = cookies_path or YOUTUBE_COOKIES_PATH
        self.cookies_loaded = self._load_cookies()

    def _load_cookies(self) -> bool:
        """Load cookies from file for authenticated requests."""
        cookies_file = Path(self.cookies_path)

        if not cookies_file.exists():
            logger.debug(f"No YouTube cookies file found at {self.cookies_path}")
            return False

        try:
            # Parse Netscape cookies.txt format
            with open(cookies_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue

                    parts = line.split('\t')
                    if len(parts) >= 7:
                        domain, _, path, secure, expires, name, value = parts[:7]
                        self.session.cookies.set(
                            name=name,
                            value=value,
                            domain=domain,
                            path=path
                        )

            logger.info(f"Loaded YouTube cookies from {self.cookies_path}")
            return True

        except Exception as e:
            logger.warning(f"Failed to load YouTube cookies: {e}")
            return False

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
        global _last_youtube_request

        if not YOUTUBE_API_AVAILABLE:
            logger.warning("YouTube transcript API not available")
            return None

        try:
            # Extract video ID
            video_id = self._extract_video_id(youtube_url)
            if not video_id:
                return None

            # Rate limiting to avoid IP bans
            if YOUTUBE_RATE_LIMIT_SECONDS > 0:
                elapsed = time.time() - _last_youtube_request
                if elapsed < YOUTUBE_RATE_LIMIT_SECONDS:
                    wait_time = YOUTUBE_RATE_LIMIT_SECONDS - elapsed
                    logger.debug(f"Rate limiting: waiting {wait_time:.1f}s before YouTube request")
                    time.sleep(wait_time)
                _last_youtube_request = time.time()

            # Try to get transcript using API (v1.2.3+ uses fetch() method)
            # Use cookies/proxy if available to bypass IP blocks
            try:
                # Configure proxy if available
                proxy_config = None
                if YOUTUBE_PROXY_URL and GenericProxyConfig:
                    logger.debug(f"Using proxy for YouTube API")
                    proxy_config = GenericProxyConfig(
                        http_url=YOUTUBE_PROXY_URL,
                        https_url=YOUTUBE_PROXY_URL,
                    )
                    api = YouTubeTranscriptApi(proxy_config=proxy_config)
                else:
                    api = YouTubeTranscriptApi()

                # If we have cookies, use them
                cookies_file = Path(self.cookies_path)
                if cookies_file.exists():
                    logger.debug(f"Using cookies from {self.cookies_path} for YouTube API")
                    transcript = api.fetch(
                        video_id,
                        languages=['en', 'en-US', 'en-GB'],
                        cookies=str(cookies_file)
                    )
                else:
                    transcript = api.fetch(video_id, languages=['en', 'en-US', 'en-GB'])

                # Combine transcript segments
                full_text = ' '.join([entry.text for entry in transcript])

                # Clean up the text
                clean_text = self._clean_transcript_text(full_text)

                if clean_text and len(clean_text) > 100:
                    return {
                        'text': clean_text,
                        'source': 'youtube_auto_captions',
                        'video_url': youtube_url,
                        'video_id': video_id,
                        'accuracy': 'high',
                        'segments': len(transcript)
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


    def resolve(self, episode, podcast_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Standard resolver interface - wraps resolve_for_episode."""
        podcast_name = podcast_config.get('name', '')
        return self.resolve_for_episode(episode.title, podcast_name, episode.url)

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
                    'confidence': 0.9,  # YouTube auto-captions are reliable
                    'resolver': 'youtube_transcript',
                    'metadata': {
                        'content': transcript['text'],
                        'content_length': len(transcript['text']),
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