#!/usr/bin/env python3
"""
Simplified Podcast Transcript Lookup System

This is a simplified version that removes the complex timer dependencies.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from helpers.database_config import get_database_connection
from helpers.youtube_podcast_fallback import YouTubePodcastFallback

logger = logging.getLogger(__name__)

@dataclass
class TranscriptLookupResult:
    """Result of transcript lookup operation"""
    success: bool
    podcast_name: str
    episode_title: str
    transcript: Optional[str] = None
    source: Optional[str] = None
    fallback_used: bool = False
    error_message: Optional[str] = None
    retry_scheduled: bool = False
    processing_time: Optional[float] = None

class PodcastTranscriptLookup:
    """Simplified podcast transcript lookup system"""

    def __init__(self):
        self.youtube_fallback = YouTubePodcastFallback()

    def lookup_transcript(self, podcast_name: str, episode_title: str, episode_url: str = None) -> TranscriptLookupResult:
        """
        Look up transcript for a podcast episode with fallback strategies
        """
        start_time = datetime.now()

        try:
            logger.info(f"Starting transcript lookup for {podcast_name} - {episode_title}")

            # Try YouTube fallback first (since we have API configured)
            if self.youtube_fallback.enabled:
                logger.info("🎬 Trying YouTube fallback...")
                youtube_result = self.youtube_fallback.get_podcast_transcript_fallback(podcast_name, episode_title)

                if youtube_result['success']:
                    logger.info("✅ Found transcript via YouTube fallback")
                    return TranscriptLookupResult(
                        success=True,
                        podcast_name=podcast_name,
                        episode_title=episode_title,
                        transcript=youtube_result.get('transcript'),
                        source=youtube_result.get('source', 'youtube'),
                        fallback_used=True,
                        processing_time=(datetime.now() - start_time).total_seconds()
                    )
                else:
                    logger.warning(f"❌ YouTube fallback failed: {youtube_result.get('error', 'Unknown error')}")
            else:
                logger.warning("⚠️ YouTube fallback not enabled")

            # No transcript found
            return TranscriptLookupResult(
                success=False,
                podcast_name=podcast_name,
                episode_title=episode_title,
                error_message="No transcript found via available sources",
                processing_time=(datetime.now() - start_time).total_seconds()
            )

        except Exception as e:
            logger.error(f"❌ Transcript lookup error: {e}")
            return TranscriptLookupResult(
                success=False,
                podcast_name=podcast_name,
                episode_title=episode_title,
                error_message=str(e),
                processing_time=(datetime.now() - start_time).total_seconds()
            )

if __name__ == "__main__":
    # Test the simplified lookup
    lookup = PodcastTranscriptLookup()
    result = lookup.lookup_transcript("Huberman Lab", "sleep")
    print(f"Result: {result.success}")
    if result.success:
        print(f"Transcript length: {len(result.transcript)}")
        print(f"Source: {result.source}")
    else:
        print(f"Error: {result.error_message}")