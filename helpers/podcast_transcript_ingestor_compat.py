#!/usr/bin/env python3
"""
DEPRECATED: Podcast Transcript Ingestor - Compatibility Layer

This file maintains backward compatibility while the system migrates
to the unified TranscriptManager. All functionality is now provided
by helpers.transcript_manager.TranscriptManager.

NEW CODE SHOULD USE: from helpers.transcript_manager import TranscriptManager
"""

import warnings
import logging
from pathlib import Path
from typing import List, Dict, Any
from helpers.transcript_manager import TranscriptManager, TranscriptInfo

logger = logging.getLogger(__name__)

# Show deprecation warning
warnings.warn(
    "podcast_transcript_ingestor is deprecated. Use TranscriptManager instead. "
    "This compatibility layer will be removed after migration is complete.",
    DeprecationWarning,
    stacklevel=2
)

class PodcastTranscriptIngestor:
    """Compatibility wrapper for PodcastTranscriptIngestor"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.manager = TranscriptManager(config)
        warnings.warn(
            "PodcastTranscriptIngestor is deprecated. Use TranscriptManager instead.",
            DeprecationWarning,
            stacklevel=2
        )

    def ingest_transcript_files(self, transcript_dir: str) -> List[Dict]:
        """Ingest transcript files from directory - compatibility method"""
        transcript_path = Path(transcript_dir)
        results = []

        if not transcript_path.exists():
            logger.error(f"Transcript directory not found: {transcript_dir}")
            return results

        # Process markdown files in directory
        for md_file in transcript_path.glob('*.md'):
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Create TranscriptInfo from file content
                transcript_info = TranscriptInfo(
                    url=f"file://{md_file}",
                    title=md_file.stem,
                    content=content,
                    source="file",
                    processed=True
                )

                # Save through TranscriptManager
                self.manager._save_transcript(transcript_info)
                self.manager.mark_processed(transcript_info.url)

                results.append({
                    'file': str(md_file),
                    'title': transcript_info.title,
                    'status': 'success'
                })

            except Exception as e:
                logger.error(f"Error processing {md_file}: {e}")
                results.append({
                    'file': str(md_file),
                    'error': str(e),
                    'status': 'failed'
                })

        return results

    def process_podcast_episodes(self, podcast_urls: List[str]) -> List[Dict]:
        """Process podcast episodes - compatibility method"""
        return self.manager.bulk_process_transcripts(podcast_urls)

    def get_transcript_content(self, episode_url: str) -> Optional[str]:
        """Get transcript content - compatibility method"""
        transcript_info = TranscriptInfo(url=episode_url, title="Episode", source="podcast")
        result = self.manager.fetch_transcript(transcript_info)
        return result.content if result else None

# Module-level convenience functions for backward compatibility
def ingest_podcast_transcripts(transcript_dir: str, config: Dict = None) -> List[Dict]:
    """Module-level function for backward compatibility"""
    warnings.warn(
        "ingest_podcast_transcripts is deprecated. Use TranscriptManager.bulk_process_transcripts instead.",
        DeprecationWarning,
        stacklevel=2
    )
    ingestor = PodcastTranscriptIngestor(config)
    return ingestor.ingest_transcript_files(transcript_dir)

def process_transcript_file(filepath: str) -> Dict:
    """Module-level function for backward compatibility"""
    warnings.warn(
        "process_transcript_file is deprecated. Use TranscriptManager instead.",
        DeprecationWarning,
        stacklevel=2
    )
    ingestor = PodcastTranscriptIngestor()
    results = ingestor.ingest_transcript_files(Path(filepath).parent)

    # Return result for this specific file
    for result in results:
        if filepath in result.get('file', ''):
            return result

    return {'file': filepath, 'status': 'not_found'}