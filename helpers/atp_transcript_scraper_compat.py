#!/usr/bin/env python3
"""
DEPRECATED: ATP Transcript Scraper - Compatibility Layer

This file maintains backward compatibility while the system migrates
to the unified TranscriptManager. All functionality is now provided
by helpers.transcript_manager.TranscriptManager.

NEW CODE SHOULD USE: from helpers.transcript_manager import TranscriptManager
"""

import warnings
from helpers.transcript_manager import TranscriptManager, TranscriptInfo
from typing import Dict, List, Optional

# Show deprecation warning
warnings.warn(
    "atp_transcript_scraper is deprecated. Use TranscriptManager instead. "
    "This compatibility layer will be removed after migration is complete.",
    DeprecationWarning,
    stacklevel=2
)

class ATPTranscriptScraper:
    """Compatibility wrapper for ATPTranscriptScraper"""

    def __init__(self, base_url: str = "https://catatp.fm"):
        self.base_url = base_url
        self.manager = TranscriptManager()
        warnings.warn(
            "ATPTranscriptScraper is deprecated. Use TranscriptManager instead.",
            DeprecationWarning,
            stacklevel=2
        )

    def scrape_transcript(self, url: str) -> Optional[str]:
        """Scrape single transcript - compatibility method"""
        transcript_info = TranscriptInfo(url=url, title="ATP Episode", source="atp")
        result = self.manager.fetch_transcript(transcript_info)
        return result.content if result else None

    def discover_episodes(self, limit: int = 50) -> List[Dict]:
        """Discover ATP episodes - compatibility method"""
        transcripts = self.manager.discover_transcripts('atp', limit=limit)

        # Convert to old format for compatibility
        episodes = []
        for transcript in transcripts:
            episodes.append({
                'url': transcript.url,
                'title': transcript.title,
                'episode_number': transcript.episode_number
            })

        return episodes

    def get_episode_transcript(self, episode_url: str) -> Optional[str]:
        """Get episode transcript - compatibility method"""
        return self.scrape_transcript(episode_url)

# Module-level convenience functions for backward compatibility
def scrape_atp_transcript(url: str) -> Optional[str]:
    """Module-level function for backward compatibility"""
    warnings.warn(
        "scrape_atp_transcript is deprecated. Use TranscriptManager.fetch_transcript instead.",
        DeprecationWarning,
        stacklevel=2
    )
    scraper = ATPTranscriptScraper()
    return scraper.scrape_transcript(url)

def discover_atp_episodes(limit: int = 50) -> List[Dict]:
    """Module-level function for backward compatibility"""
    warnings.warn(
        "discover_atp_episodes is deprecated. Use TranscriptManager.discover_transcripts instead.",
        DeprecationWarning,
        stacklevel=2
    )
    scraper = ATPTranscriptScraper()
    return scraper.discover_episodes(limit)