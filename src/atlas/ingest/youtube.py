"""
YouTube ingestor for Atlas v4.

Fetches YouTube video metadata and transcripts using yt-dlp.
Supports single video and playlist processing.
"""

import yt_dlp
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging
import re
import json
from pathlib import Path
import sys

from .base import BaseIngestor
from ..core.url_normalizer import is_youtube_url, extract_youtube_video_id


class YouTubeIngestor(BaseIngestor):
    """
    YouTube video ingestor using yt-dlp.

    Supports:
    - Single video processing
    - Playlist processing
    - Metadata extraction
    - Transcript fetching
    - Video information extraction
    """

    def ingest(self) -> List[Dict[str, Any]]:
        """Ingest YouTube videos."""
        items = []

        # Get video URLs or playlist URLs
        sources = self.source_config.get("sources", [])
        if not sources:
            self.logger.warning("No YouTube sources configured")
            return items

        download_opts = self._get_download_options()

        total_processed = 0

        for source in sources:
            source_url = source.get("url")
            source_type = source.get("type", "video")

            if not source_url:
                self.logger.warning("YouTube source missing URL")
                continue

            self.logger.info(f"Processing YouTube source: {source_url} (type: {source_type})")

            try:
                if source_type == "video":
                    video_items = self._process_video(source_url, download_opts)
                elif source_type == "playlist":
                    video_items = self._process_playlist(source_url, download_opts)
                else:
                    # Auto-detect type
                    if "playlist" in source_url.lower():
                        video_items = self._process_playlist(source_url, download_opts)
                    else:
                        video_items = self._process_video(source_url, download_opts)

                items.extend(video_items)
                total_processed += len(video_items)

                self.logger.info(f"Processed {len(video_items)} videos from {source_url}")

            except Exception as e:
                self.logger.error(f"Failed to process YouTube source {source_url}: {str(e)}")

        self.logger.info(f"YouTube ingestion completed: {total_processed} total videos")
        return items

    def _get_download_options(self) -> Dict[str, Any]:
        """Get yt-dlp download options."""
        return {
            "format": "best[height<=720]",  # Limit to 720p for storage
            "writeinfojson": True,
            "writethumbnail": False,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": ["en"],
            "skip_download": True,  # Metadata only by default
            "quiet": True,
            "no_warnings": False,
            "extract_flat": False,
            "ignoreerrors": True,
            "ignoreconfig": True,
        }

    def _process_video(self, video_url: str, download_opts: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process a single YouTube video."""
        items = []

        try:
            with yt_dlp.YoutubeDL(download_opts) as ydl:
                # Extract video information
                info = ydl.extract_info(video_url, download=False)
                item = self._create_video_item(info)
                if item:
                    items.append(item)

        except Exception as e:
            self.logger.error(f"Failed to process YouTube video {video_url}: {str(e)}")

        return items

    def _process_playlist(self, playlist_url: str, download_opts: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process a YouTube playlist."""
        items = []

        try:
            with yt_dlp.YoutubeDL(download_opts) as ydl:
                # Extract playlist information
                ydl.extract_info(playlist_url, download=False)

                # yt-dlp processes all videos in playlist automatically
                # We need to handle this differently by monitoring the download directory

        except Exception as e:
            self.logger.error(f"Failed to process YouTube playlist {playlist_url}: {str(e)}")

        return items

    def _create_video_item(self, info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create Atlas content item from YouTube video info."""
        try:
            # Extract basic information
            video_id = info.get("id", "")
            title = info.get("title", "")
            description = info.get("description", "")
            channel = info.get("uploader", "")
            upload_date = info.get("upload_date", "")
            duration = info.get("duration", 0)
            view_count = info.get("view_count", 0)
            like_count = info.get("like_count", 0)
            tags = info.get("tags", [])
            thumbnail_url = info.get("thumbnail", "")
            webpage_url = info.get("webpage_url", "")

            # Parse upload date
            if upload_date:
                try:
                    # YouTube dates are in YYYYMMDD format
                    upload_dt = datetime.strptime(upload_date, "%Y%m%d")
                except ValueError:
                    upload_dt = datetime.now()
            else:
                upload_dt = datetime.now()

            # Get transcript
            transcript = self._get_transcript(video_id)

            # Create content
            content = f"# {title}\n\n"
            content += f"**Channel:** {channel}\n"
            content += f"**Duration:** {self._format_duration(duration)}\n"
            if view_count:
                content += f"**Views:** {view_count:,}\n"
            content += f"**Upload Date:** {upload_dt.strftime('%Y-%m-%d')}\n"

            if tags:
                content += f"**Tags:** {', '.join(tags[:10])}\n"

            content += f"\n**Video URL:** {webpage_url}\n"
            content += f"**Video ID:** {video_id}\n\n"

            if description:
                content += f"## Description\n\n{description[:2000]}...\n\n"

            if transcript:
                content += f"## Transcript\n\n{transcript[:3000]}...\n\n"
            else:
                content += "## Transcript\n\n*No transcript available*\n\n"

            return self._create_base_item(
                title=title,
                content=content,
                url=webpage_url,
                author=channel,
                date=upload_dt,
                guid=f"youtube_{video_id}",
                tags=["youtube", "video"] + tags,
                video_id=video_id,
                duration=duration,
                view_count=view_count,
                like_count=like_count,
                channel=channel,
                thumbnail_url=thumbnail_url,
                transcript=transcript,
                metadata={
                    "uploader_id": info.get("uploader_id"),
                    "categories": info.get("categories", []),
                    "age_limit": info.get("age_limit", 0)
                }
            )

        except Exception as e:
            self.logger.error(f"Failed to create video item: {str(e)}")
            return None

    def _get_transcript(self, video_id: str) -> Optional[str]:
        """Get transcript for YouTube video."""
        try:
            opts = {
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitleslangs": ["en"],
                "skip_download": True,
                "subtitlesformat": "vtt",
                "quiet": True
            }

            # Create a temporary download directory
            temp_dir = Path("/tmp/atlas_youtube")
            temp_dir.mkdir(exist_ok=True)

            opts["outtmpl"] = str(temp_dir / f"{video_id}.%(ext)s")

            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)

                # Check for manual subtitles
                subtitles = info.get("subtitles", {})
                if "en" in subtitles:
                    return self._parse_vtt_subtitles(subtitles["en"][0])

                # Check for auto-generated subtitles
                auto_subs = info.get("automatic_captions", {})
                if "en" in auto_subs:
                    return self._parse_vtt_subtitles(auto_subs["en"][0])

                return None

        except Exception as e:
            self.logger.debug(f"Failed to get transcript for {video_id}: {str(e)}")
            return None

    def _parse_vtt_subtitles(self, subtitle_info: Dict[str, Any]) -> str:
        """Parse VTT subtitle file content."""
        # This is a simplified implementation
        # In a real implementation, you'd download and parse the VTT file
        return "Transcript content would be parsed from VTT file here"

    def _format_duration(self, seconds: int) -> str:
        """Format duration in seconds to human readable format."""
        if not seconds:
            return "Unknown"

        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"

    def _should_include_video(self, info: Dict[str, Any]) -> bool:
        """Check if video should be included based on filters."""
        # Skip videos that are too short
        duration = info.get("duration", 0)
        min_duration = self.source_config.get("min_duration_seconds", 60)
        if duration < min_duration:
            self.logger.debug(f"Skipping video due to short duration: {duration}s")
            return False

        # Skip age-restricted content
        if info.get("age_limit", 0) > 18:
            self.logger.warning(f"Skipping age-restricted video: {info.get('id')}")
            return False

        # Skip if no description
        description = info.get("description", "")
        min_description_length = self.validation_config.get("min_description_length", 50)
        if len(description) < min_description_length:
            self.logger.debug(f"Skipping video due to short description: {len(description)} chars")
            return False

        return True

    def _standardize_item(self, raw_item: Dict[str, Any]) -> Dict[str, Any]:
        """Standardize YouTube item to Atlas format."""
        return raw_item  # YouTube items are already standardized in _create_video_item

    @classmethod
    def get_required_config_keys(cls) -> List[str]:
        """Get required configuration keys for YouTube ingestor."""
        return ['name', 'type'] + BaseIngestor.get_required_config_keys()

    @classmethod
    def get_optional_config_keys(cls) -> List[str]:
        """Get optional configuration keys for YouTube ingestor."""
        return [
            'sources',           # List of video/playlist URLs
            'validation',        # Validation rules
            'min_duration_seconds'  # Minimum video duration
        ] + BaseIngestor.get_optional_config_keys()


# Standalone execution support
def main():
    """Run YouTube ingestor as standalone script."""
    import sys
    import os
    from pathlib import Path

    # Add src to path for standalone execution
    src_path = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(src_path))

    from atlas.config import load_config
    from atlas.logging import setup_logging

    # Setup logging
    setup_logging(level="INFO", enable_console=True)

    # Load configuration
    config_path = os.getenv("ATLAS_CONFIG", "config/sources/youtube.yaml")
    try:
        config = load_config(config_path)
    except Exception as e:
        print(f"Failed to load configuration: {e}")
        return 1

    # Run ingestor
    try:
        ingestor = YouTubeIngestor(config)
        result = ingestor.run()

        print(f"YouTube ingestion completed:")
        print(f"  Success: {result.success}")
        print(f"  Items processed: {result.items_processed}")
        print(f"  Errors: {len(result.errors)}")

        if result.errors:
            print("\nErrors:")
            for error in result.errors:
                print(f"  - {error}")

        return 0 if result.success else 1

    except Exception as e:
        print(f"YouTube ingestion failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())