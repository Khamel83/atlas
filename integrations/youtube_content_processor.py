#!/usr/bin/env python3
"""
YouTube Content Processor for Atlas

This module processes historical YouTube videos through the Atlas pipeline,
extracts transcripts, and creates relationships between content.
"""

import os
import logging
from typing import List, Dict, Any
from datetime import datetime
import json

class YouTubeContentProcessor:
    """Processes YouTube videos through the Atlas content pipeline"""

    def __init__(self):
        """Initialize the YouTube content processor"""
        self.processed_count = 0
        self.failed_count = 0
        self.relationships = []

    def process_historical_videos(self, videos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process historical YouTube videos through Atlas pipeline

        Args:
            videos (List[Dict[str, Any]]): List of video metadata

        Returns:
            List[Dict[str, Any]]: List of processed videos with Atlas metadata
        """
        processed_videos = []

        print(f"Processing {len(videos)} historical videos...")

        for i, video in enumerate(videos):
            try:
                # Process individual video
                processed_video = self._process_single_video(video)
                if processed_video:
                    processed_videos.append(processed_video)
                    self.processed_count += 1
                else:
                    self.failed_count += 1

                # Progress tracking
                if (i + 1) % 10 == 0:
                    print(f"Processed {i + 1}/{len(videos)} videos...")

            except Exception as e:
                logging.error(f"Failed to process video {video.get('video_id', 'unknown')}: {e}")
                self.failed_count += 1

        print(f"Processing complete: {self.processed_count} processed, {self.failed_count} failed")
        return processed_videos

    def _process_single_video(self, video: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single YouTube video

        Args:
            video (Dict[str, Any]): Video metadata

        Returns:
            Dict[str, Any]: Processed video with Atlas metadata
        """
        try:
            # Apply Atlas content processing
            processed_video = {
                'id': f"youtube_{video['video_id']}",
                'type': 'youtube_video',
                'title': video['title'],
                'url': video['url'],
                'source': 'YouTube',
                'author': video['channel_name'],
                'created_at': video.get('watch_datetime', datetime.now()),
                'watched_at': video.get('watch_datetime', datetime.now()),
                'duration': video.get('duration', ''),
                'channel_id': video.get('channel_id', ''),
                'channel_url': video.get('channel_url', ''),
                'description': video.get('description', ''),
                'thumbnails': video.get('thumbnails', {}),
                'transcript': self._extract_transcript(video),
                'tags': self._extract_tags(video),
                'categories': self._categorize_video(video),
                'relationships': self._find_relationships(video),
                'atlas_metadata': {
                    'imported_at': datetime.now(),
                    'processing_status': 'completed',
                    'word_count': len(video['title'].split()) + len(video.get('description', '').split())
                }
            }

            return processed_video

        except Exception as e:
            logging.error(f"Failed to process video {video.get('video_id', 'unknown')}: {e}")
            return None

    def _extract_transcript(self, video: Dict[str, Any]) -> str:
        """
        Extract transcript for a video (placeholder implementation)

        Args:
            video (Dict[str, Any]): Video metadata

        Returns:
            str: Video transcript or placeholder text
        """
        # In a real implementation, this would use the YouTube Transcript API
        # or similar service to extract actual transcripts
        video_id = video.get('video_id', '')
        if video_id:
            return f"Transcript for YouTube video {video_id} would be extracted here."
        return "No transcript available."

    def _extract_tags(self, video: Dict[str, Any]) -> List[str]:
        """
        Extract tags from video metadata

        Args:
            video (Dict[str, Any]): Video metadata

        Returns:
            List[str]: List of extracted tags
        """
        tags = []

        # Extract tags from title and description
        title = video.get('title', '').lower()
        description = video.get('description', '').lower()

        # Simple keyword extraction (in a real implementation, this would use NLP)
        keywords = ['python', 'javascript', 'tutorial', 'review', 'news', 'tech', 'programming',
                   'ai', 'machine learning', 'data science', 'web development']

        for keyword in keywords:
            if keyword in title or keyword in description:
                tags.append(keyword)

        # Add channel-based tags
        channel_name = video.get('channel_name', '').lower()
        if 'tech' in channel_name:
            tags.append('technology')
        if 'programming' in channel_name:
            tags.append('coding')

        return list(set(tags))  # Remove duplicates

    def _categorize_video(self, video: Dict[str, Any]) -> List[str]:
        """
        Create YouTube-specific content categorization

        Args:
            video (Dict[str, Any]): Video metadata

        Returns:
            List[str]: List of categories
        """
        categories = ['YouTube']

        # Categorize based on content
        title = video.get('title', '').lower()
        description = video.get('description', '').lower()

        if any(word in title or word in description for word in ['tutorial', 'learn', 'course']):
            categories.append('Tutorial')
        if any(word in title or word in description for word in ['review', 'unboxing']):
            categories.append('Review')
        if any(word in title or word in description for word in ['news', 'update']):
            categories.append('News')
        if any(word in title or word in description for word in ['interview', 'talk']):
            categories.append('Interview')
        if any(word in title or word in description for word in ['music', 'song']):
            categories.append('Music')

        return categories

    def _find_relationships(self, video: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Link watched videos to related articles/podcasts

        Args:
            video (Dict[str, Any]): Video metadata

        Returns:
            List[Dict[str, Any]]: List of relationship metadata
        """
        # In a real implementation, this would search for related content
        # in the Atlas database and create links
        relationships = []

        # Simulate finding related content
        video_id = video.get('video_id', '')
        if video_id:
            # This would be replaced with actual database queries
            related_content = [
                {
                    'type': 'article',
                    'id': f'article_{video_id[:8]}',
                    'title': f"Related article to {video['title'][:20]}...",
                    'confidence': 0.8
                },
                {
                    'type': 'podcast',
                    'id': f'podcast_{video_id[:8]}',
                    'title': f"Related podcast to {video['title'][:20]}...",
                    'confidence': 0.7
                }
            ]
            relationships.extend(related_content)
            self.relationships.extend(related_content)

        return relationships

    def generate_watch_pattern_analytics(self, videos: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate watch pattern analytics

        Args:
            videos (List[Dict[str, Any]]): List of processed videos

        Returns:
            Dict[str, Any]: Analytics data
        """
        if not videos:
            return {}

        # Basic analytics
        analytics = {
            'total_videos': len(videos),
            'date_range': {
                'earliest': min(v.get('watched_at', datetime.now()) for v in videos),
                'latest': max(v.get('watched_at', datetime.now()) for v in videos)
            },
            'categories': {},
            'channels': {},
            'peak_hours': {},
            'average_duration': '00:00:00'
        }

        # Category distribution
        for video in videos:
            for category in video.get('categories', []):
                analytics['categories'][category] = analytics['categories'].get(category, 0) + 1

        # Channel distribution
        for video in videos:
            channel = video.get('author', 'Unknown')
            analytics['channels'][channel] = analytics['channels'].get(channel, 0) + 1

        # Peak viewing hours (simplified)
        hours = {}
        for video in videos:
            if 'watched_at' in video:
                hour = video['watched_at'].hour
                hours[hour] = hours.get(hour, 0) + 1
        analytics['peak_hours'] = hours

        return analytics

def main():
    """Example usage of YouTubeContentProcessor"""
    # Example video data
    sample_videos = [
        {
            'video_id': 'dQw4w9WgXcQ',
            'title': 'Learn Python Programming Tutorial',
            'channel_name': 'Programming Tutorials',
            'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'description': 'Learn Python programming basics in this comprehensive tutorial.',
            'watch_datetime': datetime.now()
        },
        {
            'video_id': 'jNQXAC9IVRw',
            'title': 'JavaScript Framework Review 2025',
            'channel_name': 'Tech Reviews',
            'url': 'https://www.youtube.com/watch?v=jNQXAC9IVRw',
            'description': 'Review of the latest JavaScript frameworks and libraries.',
            'watch_datetime': datetime.now()
        }
    ]

    # Process videos
    processor = YouTubeContentProcessor()
    processed_videos = processor.process_historical_videos(sample_videos)

    # Generate analytics
    analytics = processor.generate_watch_pattern_analytics(processed_videos)
    print(f"Generated analytics: {json.dumps(analytics, indent=2, default=str)}")

    print("YouTube content processing demo completed successfully!")

if __name__ == "__main__":
    main()