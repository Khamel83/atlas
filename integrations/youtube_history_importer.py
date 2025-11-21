#!/usr/bin/env python3
"""
YouTube History Importer for Atlas

This module parses Google Takeout JSON files to extract YouTube watch history
and integrates it with the Atlas content pipeline.
"""

import json
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

class YouTubeHistoryImporter:
    """Imports YouTube watch history from Google Takeout JSON files"""

    def __init__(self, history_file_path: str):
        """
        Initialize the YouTube history importer

        Args:
            history_file_path (str): Path to the Google Takeout JSON file
        """
        self.history_file_path = Path(history_file_path)
        self.history_data = []
        self.duplicate_count = 0
        self.imported_count = 0

    def parse_history_file(self) -> List[Dict[str, Any]]:
        """
        Parse the YouTube history JSON file

        Returns:
            List[Dict[str, Any]]: List of video entries with metadata
        """
        if not self.history_file_path.exists():
            raise FileNotFoundError(f"History file not found: {self.history_file_path}")

        try:
            with open(self.history_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Parse video entries
            videos = []
            for entry in data:
                video = self._extract_video_metadata(entry)
                if video:
                    videos.append(video)

            self.history_data = videos
            return videos

        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse JSON file: {e}")
            raise
        except Exception as e:
            logging.error(f"Failed to parse history file: {e}")
            raise

    def _extract_video_metadata(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract metadata from a single history entry

        Args:
            entry (Dict[str, Any]): Single history entry from JSON

        Returns:
            Dict[str, Any]: Extracted metadata or None if invalid entry
        """
        try:
            # Extract core metadata
            video_data = {
                'video_id': entry.get('videoId', ''),
                'title': entry.get('title', '').replace('Watched ', ''),
                'channel_name': entry.get('channelName', ''),
                'channel_url': entry.get('channelUrl', ''),
                'watch_date': entry.get('time', ''),
                'duration': entry.get('duration', ''),
                'url': f"https://www.youtube.com/watch?v={entry.get('videoId', '')}"
            }

            # Parse watch date if available
            if video_data['watch_date']:
                try:
                    # Convert from microseconds to seconds if needed
                    timestamp = int(video_data['watch_date'])
                    if timestamp > 1000000000000:  # Likely microseconds
                        timestamp = timestamp // 1000000
                    video_data['watch_datetime'] = datetime.fromtimestamp(timestamp)
                except (ValueError, OSError):
                    video_data['watch_datetime'] = None

            # Validate required fields
            if not video_data['video_id'] or not video_data['title']:
                return None

            return video_data

        except Exception as e:
            logging.warning(f"Failed to extract metadata from entry: {e}")
            return None

    def integrate_with_atlas_pipeline(self) -> None:
        """
        Integrate parsed YouTube history with existing Atlas content pipeline
        """
        # In a real implementation, this would:
        # 1. Convert videos to Atlas content format
        # 2. Add to processing queue
        # 3. Handle deduplication
        # 4. Track processing status

        print(f"Integrating {len(self.history_data)} videos with Atlas pipeline...")

        # Simple simulation of integration
        for video in self.history_data:
            # Check for duplicates (simplified)
            # In a real implementation, this would check against existing content
            if self._is_duplicate(video):
                self.duplicate_count += 1
                continue

            # Add to Atlas pipeline (simulated)
            self._add_to_pipeline(video)
            self.imported_count += 1

    def _is_duplicate(self, video: Dict[str, Any]) -> bool:
        """
        Check if a video is a duplicate of existing content

        Args:
            video (Dict[str, Any]): Video metadata

        Returns:
            bool: True if duplicate, False otherwise
        """
        # In a real implementation, this would check against existing content
        # For now, we'll just return False to simulate no duplicates
        return False

    def _add_to_pipeline(self, video: Dict[str, Any]) -> None:
        """
        Add a video to the Atlas processing pipeline

        Args:
            video (Dict[str, Any]): Video metadata
        """
        # In a real implementation, this would:
        # 1. Convert to Atlas content format
        # 2. Add to processing queue
        # 3. Store metadata in database
        print(f"Added video to pipeline: {video['title']}")

    def get_progress_stats(self) -> Dict[str, int]:
        """
        Get progress statistics for the import process

        Returns:
            Dict[str, int]: Progress statistics
        """
        return {
            'total_videos': len(self.history_data),
            'imported_count': self.imported_count,
            'duplicate_count': self.duplicate_count,
            'remaining_count': len(self.history_data) - self.imported_count - self.duplicate_count
        }

    def validate_import(self) -> bool:
        """
        Validate the import process

        Returns:
            bool: True if validation passes, False otherwise
        """
        stats = self.get_progress_stats()

        # Basic validation checks
        if stats['total_videos'] == 0:
            logging.warning("No videos found in history file")
            return False

        if stats['imported_count'] + stats['duplicate_count'] != stats['total_videos']:
            logging.warning("Import count mismatch")
            return False

        print(f"Import validation passed: {stats}")
        return True

def main():
    """Example usage of YouTubeHistoryImporter"""
    # Example usage
    importer = YouTubeHistoryImporter("youtube_history.json")

    try:
        # Parse history file
        videos = importer.parse_history_file()
        print(f"Parsed {len(videos)} videos from history file")

        # Integrate with Atlas pipeline
        importer.integrate_with_atlas_pipeline()

        # Get progress stats
        stats = importer.get_progress_stats()
        print(f"Import stats: {stats}")

        # Validate import
        if importer.validate_import():
            print("YouTube history import completed successfully!")
        else:
            print("YouTube history import validation failed!")

    except Exception as e:
        print(f"Failed to import YouTube history: {e}")

if __name__ == "__main__":
    main()