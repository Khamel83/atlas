#!/usr/bin/env python3
"""
YouTube Ingestor for Atlas Content System

Integrates YouTube video processing with Atlas database and content pipeline.
Handles video metadata, transcripts, and proper Atlas content storage.
"""

import os
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# Use centralized database configuration
try:
    from .database_config import get_database_connection
    from .metadata_manager import ContentType
except ImportError:
    # Handle direct execution
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from helpers.database_config import get_database_connection
    from helpers.metadata_manager import ContentType

# YouTube processing imports (conditional based on availability)
try:
    from pytube import YouTube
    PYTUBE_AVAILABLE = True
except ImportError:
    PYTUBE_AVAILABLE = False
    logging.warning("pytube not available - video download disabled")

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    TRANSCRIPT_API_AVAILABLE = True
except ImportError:
    TRANSCRIPT_API_AVAILABLE = False
    logging.warning("youtube-transcript-api not available - transcript extraction disabled")

@dataclass
class YouTubeVideoData:
    """YouTube video metadata structure for Atlas"""
    video_id: str
    title: str
    url: str
    channel_name: str
    channel_id: Optional[str] = None
    description: Optional[str] = None
    upload_date: Optional[datetime] = None
    duration: Optional[int] = None  # in seconds
    view_count: Optional[int] = None
    tags: Optional[List[str]] = None
    transcript: Optional[str] = None
    thumbnail_url: Optional[str] = None
    watched_at: Optional[datetime] = None

class YouTubeIngestor:
    """YouTube content ingestor for Atlas system"""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize YouTube ingestor with Atlas integration"""
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self.processed_videos = []
        self.failed_videos = []

    def ingest_single_video(self, video_url: str, watched_at: datetime = None) -> bool:
        """
        Ingest a single YouTube video into Atlas

        Args:
            video_url: YouTube video URL
            watched_at: When the video was watched (optional)

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.logger.info(f"Ingesting YouTube video: {video_url}")

            # Extract video ID
            video_id = self._extract_video_id(video_url)
            if not video_id:
                self.logger.error(f"Could not extract video ID from URL: {video_url}")
                return False

            # Check if video already exists in Atlas
            if self._video_exists_in_atlas(video_id):
                self.logger.info(f"Video {video_id} already exists in Atlas")
                return True

            # Get video metadata
            video_data = self._get_video_metadata(video_url, video_id, watched_at)
            if not video_data:
                self.logger.error(f"Failed to get metadata for video: {video_id}")
                return False

            # Get transcript if available
            transcript = self._get_video_transcript(video_id)
            if transcript:
                video_data.transcript = transcript
                self.logger.info(f"Retrieved transcript for video: {video_id}")

            # Store in Atlas database
            success = self._store_in_atlas(video_data)

            if success:
                self.processed_videos.append(video_data)
                self.logger.info(f"Successfully ingested video: {video_data.title}")
                self.logger.info(f"Video stored with ID: {video_data.video_id}, URL: {video_data.url}")
                return True
            else:
                self.failed_videos.append(video_data)
                self.logger.error(f"Failed to store video: {video_data.title}")
                return False

        except Exception as e:
            self.logger.error(f"Error ingesting video {video_url}: {e}")
            return False

    def ingest_video_list(self, video_urls: List[str]) -> Dict[str, int]:
        """
        Ingest multiple YouTube videos

        Args:
            video_urls: List of YouTube video URLs

        Returns:
            Dict with success/failure counts
        """
        results = {"success": 0, "failed": 0, "skipped": 0}

        for i, url in enumerate(video_urls):
            try:
                if self.ingest_single_video(url):
                    results["success"] += 1
                else:
                    results["failed"] += 1

                # Progress logging
                if (i + 1) % 10 == 0:
                    self.logger.info(f"Processed {i + 1}/{len(video_urls)} videos")

            except Exception as e:
                self.logger.error(f"Error processing video {url}: {e}")
                results["failed"] += 1

        self.logger.info(f"Ingestion complete: {results}")
        return results

    def _extract_video_id(self, video_url: str) -> Optional[str]:
        """Extract YouTube video ID from URL"""
        try:
            if "youtube.com/watch?v=" in video_url:
                return video_url.split("watch?v=")[1].split("&")[0]
            elif "youtu.be/" in video_url:
                return video_url.split("youtu.be/")[1].split("?")[0]
            else:
                # Try to extract ID from various YouTube URL formats
                for pattern in ["embed/", "v/", "watch/"]:
                    if pattern in video_url:
                        return video_url.split(pattern)[1].split("?")[0].split("&")[0]
                return None
        except Exception:
            return None

    def _video_exists_in_atlas(self, video_id: str) -> bool:
        """Check if video already exists in Atlas database"""
        try:
            conn = get_database_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT COUNT(*) FROM content
                WHERE content_type = 'youtube_video'
                AND url LIKE ?
            """, (f"%{video_id}%",))

            count = cursor.fetchone()[0]
            conn.close()

            return count > 0

        except Exception as e:
            self.logger.error(f"Error checking video existence: {e}")
            return False

    def _get_video_metadata(self, video_url: str, video_id: str, watched_at: datetime = None) -> Optional[YouTubeVideoData]:
        """Get video metadata using pytube or fallback methods"""
        try:
            if PYTUBE_AVAILABLE:
                return self._get_metadata_with_pytube(video_url, video_id, watched_at)
            else:
                return self._get_metadata_fallback(video_url, video_id, watched_at)

        except Exception as e:
            self.logger.error(f"Error getting video metadata: {e}")
            return None

    def _get_metadata_with_pytube(self, video_url: str, video_id: str, watched_at: datetime = None) -> Optional[YouTubeVideoData]:
        """Get metadata using pytube library"""
        try:
            yt = YouTube(video_url)

            return YouTubeVideoData(
                video_id=video_id,
                title=yt.title or f"YouTube Video {video_id}",
                url=video_url,
                channel_name=yt.author or "Unknown Channel",
                channel_id=yt.channel_id,
                description=yt.description,
                upload_date=yt.publish_date,
                duration=yt.length,
                view_count=yt.views,
                tags=yt.keywords,
                thumbnail_url=yt.thumbnail_url,
                watched_at=watched_at or datetime.now()
            )

        except Exception as e:
            self.logger.warning(f"pytube failed for {video_id}: {e}")
            return self._get_metadata_fallback(video_url, video_id, watched_at)

    def _get_metadata_fallback(self, video_url: str, video_id: str, watched_at: datetime = None) -> YouTubeVideoData:
        """Fallback metadata extraction without external libraries"""
        return YouTubeVideoData(
            video_id=video_id,
            title=f"YouTube Video {video_id}",
            url=video_url,
            channel_name="Unknown Channel",
            description="Metadata extraction limited - install pytube for full details",
            upload_date=None,
            watched_at=watched_at or datetime.now()
        )

    def _get_video_transcript(self, video_id: str) -> Optional[str]:
        """Get video transcript using YouTube Transcript API"""
        if not TRANSCRIPT_API_AVAILABLE:
            return None

        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)

            # Combine transcript entries into single text
            transcript_text = " ".join([entry['text'] for entry in transcript_list])

            return transcript_text

        except Exception as e:
            self.logger.debug(f"No transcript available for {video_id}: {e}")
            return None

    def _store_in_atlas(self, video_data: YouTubeVideoData) -> bool:
        """Store video data in Atlas database"""
        try:
            self.logger.info(f"Storing video in Atlas: {video_data.video_id}")
            conn = get_database_connection()
            cursor = conn.cursor()

            # Prepare content
            content_parts = [f"YouTube Video: {video_data.title}"]
            content_parts.append(f"Channel: {video_data.channel_name}")

            if video_data.description:
                content_parts.append(f"\nDescription: {video_data.description}")

            if video_data.transcript:
                content_parts.append(f"\n\nTranscript:\n{video_data.transcript}")

            content = "\n".join(content_parts)

            # Prepare metadata
            metadata = {
                "video_id": video_data.video_id,
                "channel_name": video_data.channel_name,
                "channel_id": video_data.channel_id,
                "upload_date": video_data.upload_date.isoformat() if video_data.upload_date else None,
                "duration": video_data.duration,
                "view_count": video_data.view_count,
                "tags": video_data.tags,
                "thumbnail_url": video_data.thumbnail_url,
                "watched_at": video_data.watched_at.isoformat() if video_data.watched_at else None,
                "platform": "youtube",
                "has_transcript": bool(video_data.transcript)
            }

            # Insert into content table
            cursor.execute("""
                INSERT INTO content (
                    title, url, content, content_type, metadata,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                video_data.title,
                video_data.url,
                content,
                'youtube_video',  # Critical: proper content type
                json.dumps(metadata),
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))

            conn.commit()
            conn.close()

            return True

        except Exception as e:
            self.logger.error(f"Error storing video in Atlas: {e}")
            return False

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return {
            "processed_count": len(self.processed_videos),
            "failed_count": len(self.failed_videos),
            "success_rate": len(self.processed_videos) / max(1, len(self.processed_videos) + len(self.failed_videos)),
            "has_pytube": PYTUBE_AVAILABLE,
            "has_transcript_api": TRANSCRIPT_API_AVAILABLE
        }

    def cleanup(self):
        """Cleanup resources"""
        self.processed_videos.clear()
        self.failed_videos.clear()

def main():
    """Example usage and testing"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python youtube_ingestor.py <youtube_url>")
        sys.exit(1)

    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Test ingestion
    ingestor = YouTubeIngestor()
    video_url = sys.argv[1]

    success = ingestor.ingest_single_video(video_url)
    stats = ingestor.get_processing_stats()

    print(f"Ingestion {'successful' if success else 'failed'}")
    print(f"Stats: {stats}")

if __name__ == "__main__":
    main()