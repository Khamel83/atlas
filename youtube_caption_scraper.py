#!/usr/bin/env python3
"""
YouTube Caption Scraper for Atlas
Extracts auto-generated captions from YouTube videos
"""

import os
import requests
import json
import re
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse, parse_qs
import logging

logger = logging.getLogger(__name__)

class YouTubeCaptionScraper:
    """Extract captions from YouTube videos using API"""

    def __init__(self):
        self.api_key = os.getenv("YOUTUBE_API_KEY")
        if not self.api_key:
            raise ValueError("YOUTUBE_API_KEY not found in environment")

        self.base_url = "https://www.googleapis.com/youtube/v3"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def extract_video_id(self, url: str) -> Optional[str]:
        """Extract YouTube video ID from various URL formats"""
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
            r'^([a-zA-Z0-9_-]{11})$'  # Direct video ID
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def search_podcast_videos(self, podcast_name: str, episode_title: str) -> List[Dict]:
        """Search for YouTube videos matching podcast episode"""
        try:
            # Create search query combining podcast name and episode title
            search_query = f"{podcast_name} {episode_title} podcast"

            # Clean up common patterns that might reduce search quality
            search_query = re.sub(r'\b\d+\s*$', '', search_query)  # Remove trailing numbers
            search_query = re.sub(r'\bepisode\s*\d+\b', '', search_query, flags=re.IGNORECASE)  # Remove episode numbers

            search_url = f"{self.base_url}/search"
            params = {
                'key': self.api_key,
                'q': search_query,
                'part': 'snippet',
                'type': 'video',
                'maxResults': 5,
                'videoDuration': 'medium',  # Medium length videos (more likely to be full episodes)
                'relevanceLanguage': 'en'
            }

            response = self.session.get(search_url, params=params)
            response.raise_for_status()

            data = response.json()
            videos = []

            for item in data.get('items', []):
                video_id = item['id']['videoId']
                title = item['snippet']['title']
                description = item['snippet']['description']
                channel = item['snippet']['channelTitle']

                # Calculate relevance score
                relevance_score = self._calculate_relevance_score(
                    podcast_name, episode_title, title, description, channel
                )

                videos.append({
                    'video_id': video_id,
                    'title': title,
                    'description': description,
                    'channel': channel,
                    'relevance_score': relevance_score,
                    'url': f"https://www.youtube.com/watch?v={video_id}"
                })

            # Sort by relevance score
            videos.sort(key=lambda x: x['relevance_score'], reverse=True)
            return videos

        except Exception as e:
            logger.error(f"YouTube search failed: {e}")
            return []

    def _calculate_relevance_score(self, podcast_name: str, episode_title: str,
                                  video_title: str, video_description: str, channel: str) -> float:
        """Calculate relevance score for search results"""
        score = 0.0

        # Channel name match (highest weight)
        if podcast_name.lower() in channel.lower():
            score += 0.5

        # Title keywords
        title_lower = video_title.lower()
        episode_lower = episode_title.lower()

        # Extract key terms from episode title
        key_terms = re.findall(r'\b\w+\b', episode_lower)
        key_terms = [term for term in key_terms if len(term) > 3]  # Ignore short words

        for term in key_terms:
            if term in title_lower:
                score += 0.1

        # Check for podcast-related keywords
        podcast_keywords = ['podcast', 'episode', 'show', 'interview', 'talk']
        for keyword in podcast_keywords:
            if keyword in title_lower:
                score += 0.05

        # Description relevance
        if any(term in video_description.lower() for term in key_terms):
            score += 0.05

        return min(score, 1.0)  # Cap at 1.0

    def get_video_captions(self, video_id: str) -> Optional[str]:
        """Get captions for a specific video"""
        try:
            # First, check if captions are available
            caption_url = f"{self.base_url}/captions"
            params = {
                'key': self.api_key,
                'videoId': video_id,
                'part': 'snippet'
            }

            response = self.session.get(caption_url, params=params)
            response.raise_for_status()

            caption_data = response.json()

            if not caption_data.get('items'):
                logger.info(f"No captions available for video {video_id}")
                return None

            # Look for English captions first, then any available
            caption_id = None
            for item in caption_data['items']:
                snippet = item['snippet']
                if snippet.get('language') == 'en' or snippet.get('language', '').startswith('en'):
                    caption_id = item['id']
                    break

            if not caption_id:
                # Use first available caption
                caption_id = caption_data['items'][0]['id']

            # Get caption content (this is a simplified approach)
            # Note: YouTube API doesn't directly return caption text, we need to use the caption track
            return self._fetch_caption_content(caption_id)

        except Exception as e:
            logger.error(f"Failed to get captions for video {video_id}: {e}")
            return None

    def _fetch_caption_content(self, caption_id: str) -> Optional[str]:
        """Fetch actual caption content using the caption track"""
        try:
            # This is a simplified implementation
            # In a production system, you'd need to parse the actual caption format
            # For now, we'll use a placeholder approach

            # Extract video ID from caption ID
            video_id_match = re.search(r'([^/]+)$', caption_id)
            if not video_id_match:
                return None

            video_id = video_id_match.group(1)

            # Construct caption URL (this is a simplified approach)
            caption_url = f"https://www.youtube.com/api/timedtext?v={video_id}&lang=en&fmt=srv3"

            response = self.session.get(caption_url)
            if response.status_code == 200:
                return self._parse_caption_xml(response.text)
            else:
                # Try alternative caption formats
                for fmt in ['srv1', 'srv2', 'ttml', 'vtt']:
                    alt_url = f"https://www.youtube.com/api/timedtext?v={video_id}&lang=en&fmt={fmt}"
                    response = self.session.get(alt_url)
                    if response.status_code == 200:
                        return self._parse_caption_xml(response.text)

            return None

        except Exception as e:
            logger.error(f"Failed to fetch caption content: {e}")
            return None

    def _parse_caption_xml(self, xml_content: str) -> str:
        """Parse XML caption content into plain text"""
        try:
            # Simple XML parsing for captions
            import xml.etree.ElementTree as ET

            root = ET.fromstring(xml_content)

            # Extract text from all text elements
            text_parts = []
            for text_elem in root.findall('.//text'):
                if text_elem.text:
                    # Clean up the text
                    clean_text = re.sub(r'\s+', ' ', text_elem.text.strip())
                    if clean_text:
                        text_parts.append(clean_text)

            # Combine with proper spacing
            full_transcript = ' '.join(text_parts)

            # Basic quality check
            if len(full_transcript) < 500:  # Too short for a full episode
                return None

            return full_transcript

        except Exception as e:
            logger.error(f"Failed to parse caption XML: {e}")
            return None

    def find_episode_transcript(self, podcast_name: str, episode_title: str, original_url: str) -> Optional[Dict]:
        """Main method to find transcript via YouTube"""
        try:
            logger.info(f"Searching YouTube for transcript: {podcast_name} - {episode_title}")

            # Step 1: Search for matching videos
            videos = self.search_podcast_videos(podcast_name, episode_title)

            if not videos:
                logger.info("No matching YouTube videos found")
                return None

            # Step 2: Try to get captions for each video (starting with most relevant)
            for video in videos[:3]:  # Try top 3 videos
                logger.info(f"Trying video: {video['title']} (score: {video['relevance_score']})")

                captions = self.get_video_captions(video['video_id'])

                if captions:
                    logger.info(f"Found captions via YouTube for {video['title']}")
                    return {
                        'transcript': captions,
                        'source': 'youtube_captions',
                        'video_url': video['url'],
                        'video_title': video['title'],
                        'channel': video['channel'],
                        'relevance_score': video['relevance_score']
                    }

            logger.info("No captions found for any matching videos")
            return None

        except Exception as e:
            logger.error(f"YouTube transcript search failed: {e}")
            return None

# Test function
def test_youtube_scraper():
    """Test the YouTube caption scraper"""
    scraper = YouTubeCaptionScraper()

    # Test with a known podcast
    result = scraper.find_episode_transcript(
        "Lex Fridman Podcast",
        "Elon Musk: Tesla, SpaceX, and the Future",
        "https://lexfridman.com/elon-musk/"
    )

    if result:
        print(f"✅ Found transcript via YouTube: {len(result['transcript'])} chars")
        print(f"   Source: {result['video_url']}")
    else:
        print("❌ No transcript found via YouTube")

if __name__ == "__main__":
    test_youtube_scraper()