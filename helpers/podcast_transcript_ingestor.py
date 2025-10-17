#!/usr/bin/env python3
"""
Podcast Transcript Ingestor

Bridges atlas-pod transcript discovery with existing Atlas processing pipeline.
Processes fetched transcript markdown files through Atlas ingestors.
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any
import frontmatter
import sys

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from helpers.base_ingestor import BaseIngestor
from helpers.metadata_manager import ContentType
from helpers.path_manager import PathType
from helpers.dedupe import link_uid
from helpers.utils import log_info, log_error
from helpers.transcript_parser import TranscriptParser
from helpers.transcript_search_indexer import TranscriptSearchIndexer
from helpers.content_processor_enhanced import ContentProcessorEnhanced
from modules.podcasts.cli import AtlasPodCLI
from modules.podcasts.store import PodcastStore

logger = logging.getLogger(__name__)


class PodcastTranscriptIngestor(BaseIngestor):
    """Ingestor that processes podcast transcripts into Atlas system"""

    def get_content_type(self):
        return ContentType.PODCAST

    def get_module_name(self):
        return "podcast_transcript_ingestor"

    def fetch_content(self, source, metadata):
        """Required abstract method - handles transcript file processing"""
        # This ingestor processes already-fetched transcript files
        # rather than fetching content directly from URLs
        return True, "Transcript content processed via atlas-pod CLI"

    def __init__(self, config):
        super().__init__(config, ContentType.PODCAST, "podcast_transcript_ingestor")
        self.atlas_pod_cli = AtlasPodCLI()
        self.atlas_pod_cli.init_store()
        self.transcript_parser = TranscriptParser()
        self.search_indexer = TranscriptSearchIndexer()
        self.enhanced_processor = ContentProcessorEnhanced(config)

    def discover_and_process_transcripts(self, podcast_slugs: List[str] = None):
        """
        Full workflow: discover episodes, fetch transcripts, process through Atlas

        Args:
            podcast_slugs: List of specific podcasts to process, or None for all
        """
        log_info(
            self.log_path, "🎙️  Starting podcast transcript discovery and processing"
        )

        try:
            # Step 1: Discovery - find new episodes
            self._run_discovery(podcast_slugs)

            # Step 2: Fetch transcripts from web
            self._fetch_transcripts(podcast_slugs)

            # Step 3: Process through Atlas pipeline
            self._process_fetched_transcripts(podcast_slugs)

            log_info(self.log_path, "✅ Podcast transcript processing complete")

        except Exception as e:
            log_error(self.log_path, f"Error in transcript discovery/processing: {e}")
            raise

    def _run_discovery(self, podcast_slugs: List[str] = None):
        """Run episode discovery using atlas-pod CLI"""
        log_info(self.log_path, "🔍 Running episode discovery...")

        if podcast_slugs:
            for slug in podcast_slugs:
                self._discover_podcast(slug)
        else:
            self._discover_all_podcasts()

    def _discover_podcast(self, slug: str):
        """Discover episodes for specific podcast"""
        try:
            # Use atlas-pod CLI discovery
            args = type("Args", (), {"slug": slug, "all": False})()
            success = self.atlas_pod_cli.cmd_discover(args)

            if success:
                log_info(self.log_path, f"✅ Discovery completed for {slug}")
            else:
                log_error(self.log_path, f"❌ Discovery failed for {slug}")

        except Exception as e:
            log_error(self.log_path, f"Error discovering {slug}: {e}")

    def _discover_all_podcasts(self):
        """Discover episodes for all registered podcasts"""
        try:
            args = type("Args", (), {"all": True, "slug": None})()
            success = self.atlas_pod_cli.cmd_discover(args)

            if success:
                log_info(self.log_path, "✅ Discovery completed for all podcasts")
            else:
                log_error(self.log_path, "❌ Discovery failed")

        except Exception as e:
            log_error(self.log_path, f"Error in discovery: {e}")

    def _fetch_transcripts(self, podcast_slugs: List[str] = None):
        """Fetch transcripts using atlas-pod CLI"""
        log_info(self.log_path, "📥 Fetching transcripts from web...")

        try:
            if podcast_slugs:
                for slug in podcast_slugs:
                    args = type("Args", (), {"slug": slug, "all": False})()
                    self.atlas_pod_cli.cmd_fetch_transcripts(args)
            else:
                args = type("Args", (), {"all": True, "slug": None})()
                self.atlas_pod_cli.cmd_fetch_transcripts(args)

            log_info(self.log_path, "✅ Transcript fetching completed")

        except Exception as e:
            log_error(self.log_path, f"Error fetching transcripts: {e}")

    def _process_fetched_transcripts(self, podcast_slugs: List[str] = None):
        """Process fetched transcript markdown files through Atlas"""
        log_info(self.log_path, "⚙️  Processing transcripts through Atlas pipeline...")

        try:
            transcript_files = self._find_transcript_files(podcast_slugs)

            processed_count = 0
            error_count = 0

            for transcript_file in transcript_files:
                try:
                    if self._process_transcript_file(transcript_file):
                        processed_count += 1
                    else:
                        error_count += 1

                except Exception as e:
                    log_error(self.log_path, f"Error processing {transcript_file}: {e}")
                    error_count += 1

            log_info(
                self.log_path,
                f"📊 Processed {processed_count} transcripts, {error_count} errors",
            )

        except Exception as e:
            log_error(self.log_path, f"Error in transcript processing: {e}")

    def _find_transcript_files(self, podcast_slugs: List[str] = None) -> List[Path]:
        """Find transcript markdown files to process"""
        transcript_files = []

        base_path = Path("data/podcasts")
        if not base_path.exists():
            return transcript_files

        # Check both possible transcript locations:
        # 1. data/podcasts/transcripts/ (main transcripts directory)
        # 2. data/podcasts/{podcast}/transcripts/ (per-podcast directories)

        # Main transcripts directory
        main_transcripts_dir = base_path / "transcripts"
        if main_transcripts_dir.exists():
            # Process all subdirectories in transcripts/
            for subdir in main_transcripts_dir.iterdir():
                if subdir.is_dir():
                    # Check if we should process this podcast
                    if not podcast_slugs or subdir.name in podcast_slugs:
                        transcript_files.extend(subdir.glob("*.md"))

        # Per-podcast transcript directories
        if podcast_slugs:
            podcast_dirs = [
                base_path / slug
                for slug in podcast_slugs
                if (base_path / slug).exists()
            ]
        else:
            podcast_dirs = [d for d in base_path.iterdir() if d.is_dir() and d.name != "transcripts"]

        # Find transcript files in per-podcast directories
        for podcast_dir in podcast_dirs:
            transcripts_dir = podcast_dir / "transcripts"
            if transcripts_dir.exists():
                transcript_files.extend(transcripts_dir.glob("*.md"))

        # Also check markdown files directly in data/podcasts/markdown/
        markdown_dir = base_path / "markdown"
        if markdown_dir.exists():
            transcript_files.extend(markdown_dir.glob("*.md"))

        return transcript_files

    def _parse_transcript_content(
        self, content: str, metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse transcript content into structured data using TranscriptParser"""
        try:
            # Create parser metadata
            parser_metadata = {
                "episode_title": metadata.get("title"),
                "podcast_name": metadata.get("podcast"),
                "episode_url": metadata.get("episode_url"),
                "duration": metadata.get("duration"),
                "publish_date": metadata.get("publish_date"),
            }

            # Parse the transcript
            parsed_result = self.transcript_parser.parse_transcript(
                content, parser_metadata
            )

            log_info(
                self.log_path,
                f"📝 Parsed transcript: {len(parsed_result.get('segments', []))} segments, "
                f"{len(parsed_result.get('speakers', []))} speakers, "
                f"quality: {parsed_result.get('parse_quality', 'unknown')}",
            )

            return parsed_result

        except Exception as e:
            log_error(self.log_path, f"Error parsing transcript content: {e}")
            # Return minimal structure on error
            return {
                "speakers": [],
                "segments": [],
                "topics": [],
                "parse_quality": "failed",
                "error": str(e),
            }

    def _process_transcript_file(self, transcript_file: Path) -> bool:
        """Process individual transcript markdown file through Atlas"""
        try:
            # Ensure transcript_file is a Path object
            transcript_file = Path(transcript_file)

            # Read markdown with frontmatter
            with open(transcript_file, "r", encoding="utf-8") as f:
                post = frontmatter.load(f)

            # Extract metadata and content
            metadata = post.metadata
            content = post.content

            if not content or len(content) < 100:
                log_error(
                    self.log_path, f"Transcript too short or empty: {transcript_file}"
                )
                return False

            # Parse transcript content into structured data
            parsed_transcript = self._parse_transcript_content(content, metadata)

            # Create Atlas-compatible metadata
            atlas_metadata = self._create_atlas_metadata(
                metadata, transcript_file, parsed_transcript
            )

            # Generate unique ID for deduplication
            unique_id = link_uid(metadata.get("episode_url", str(transcript_file)))

            # Use existing Atlas processing pipeline
            success = self.process_content(
                content, atlas_metadata, unique_id, parsed_transcript
            )

            if success:
                log_info(
                    self.log_path,
                    f"✅ Processed transcript: {metadata.get('title', transcript_file.name)}",
                )
                return True
            else:
                log_error(self.log_path, f"❌ Failed to process: {transcript_file}")
                return False

        except Exception as e:
            log_error(
                self.log_path,
                f"Error processing transcript file {transcript_file}: {e}",
            )
            return False

    def _create_atlas_metadata(
        self,
        transcript_metadata: Dict[str, Any],
        transcript_file: Path,
        parsed_transcript: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Convert transcript metadata to Atlas format"""

        # Extract podcast info from path
        podcast_slug = transcript_file.parent.parent.name

        atlas_metadata = {
            "source": transcript_metadata.get("episode_url", str(transcript_file)),
            "title": transcript_metadata.get("title", "Unknown Episode"),
            "podcast_name": transcript_metadata.get("podcast", "Unknown Podcast"),
            "podcast_slug": podcast_slug,
            "publish_date": transcript_metadata.get("publish_date"),
            "transcript_source": transcript_metadata.get("transcript_source"),
            "fetched_at": transcript_metadata.get("fetched_at"),
            "duration": transcript_metadata.get("duration"),
            "description": transcript_metadata.get("description", ""),
            "guid": transcript_metadata.get("guid"),
            "content_type": "podcast_transcript",
            "transcript_file": str(transcript_file),
        }

        # Add parsed transcript data if available
        if parsed_transcript:
            atlas_metadata["parsed_transcript"] = parsed_transcript
            atlas_metadata["speakers"] = parsed_transcript.get("speakers", [])
            atlas_metadata["parse_quality"] = parsed_transcript.get(
                "parse_quality", "unknown"
            )
            atlas_metadata["segment_count"] = len(parsed_transcript.get("segments", []))
            atlas_metadata["topic_count"] = len(parsed_transcript.get("topics", []))

        # Add type-specific metadata for podcasts
        atlas_metadata["type_specific"] = {
            "podcast_name": atlas_metadata["podcast_name"],
            "podcast_slug": podcast_slug,
            "episode_title": atlas_metadata["title"],
            "episode_url": atlas_metadata["source"],
            "transcript_source": atlas_metadata["transcript_source"],
            "duration": atlas_metadata["duration"],
            "publish_date": atlas_metadata["publish_date"],
            "original_transcript_metadata": transcript_metadata,
        }

        return atlas_metadata

    def process_content(
        self,
        content: str,
        metadata: Dict[str, Any],
        unique_id: str,
        parsed_transcript: Dict[str, Any] = None,
    ) -> bool:
        """Process transcript content through Atlas pipeline"""
        try:
            # Use path manager to get file paths
            paths = self.path_manager.get_path_set(self.content_type, unique_id)

            # Create Atlas metadata object
            meta = self.create_metadata(
                source=metadata["source"],
                title=metadata["title"],
                type_specific=metadata["type_specific"],
            )
            meta.uid = unique_id

            # Save markdown content
            markdown_path = paths.get_path(PathType.MARKDOWN)
            if markdown_path:
                os.makedirs(os.path.dirname(markdown_path), exist_ok=True)
                with open(markdown_path, "w", encoding="utf-8") as f:
                    f.write(content)
                meta.markdown_path = markdown_path

            # Save metadata
            self.save_metadata(meta)

            # Save raw data for preservation
            self.save_raw_data(metadata, meta, "transcript_metadata")

            # Save parsed transcript data if available
            if parsed_transcript:
                self.save_raw_data(parsed_transcript, meta, "parsed_transcript")

                # Index parsed transcript for enhanced search
                try:
                    search_metadata = {
                        "title": metadata["title"],
                        "podcast_name": metadata["podcast_name"],
                        "episode_url": metadata["source"],
                        "publish_date": metadata.get("publish_date"),
                    }

                    self.search_indexer.index_transcript_content(
                        unique_id, parsed_transcript, search_metadata
                    )
                    log_info(
                        self.log_path,
                        f"✅ Indexed transcript for enhanced search: {meta.title}",
                    )

                except Exception as e:
                    log_error(
                        self.log_path, f"Error indexing transcript for search: {e}"
                    )
                    # Don't fail the whole process if search indexing fails

            # Enhanced content processing with structured extraction
            try:
                enhanced_result = self.enhanced_processor.process_content(
                    title=metadata["title"],
                    content=content,
                    url=metadata["source"],
                    source=f"{metadata['podcast_name']} (Podcast)",
                    content_type="podcast",
                    date=metadata.get("publish_date")
                )

                if enhanced_result and enhanced_result.get('status') != 'error':
                    insights = enhanced_result.get('insights', {})
                    quality = insights.extraction_quality if hasattr(insights, 'extraction_quality') else 0.0
                    log_info(
                        self.log_path,
                        f"✅ Enhanced processing completed: {meta.title} (Quality: {quality:.2f})",
                    )

            except Exception as e:
                log_error(
                    self.log_path, f"Error in enhanced processing: {e}"
                )
                # Don't fail the whole process if enhanced processing fails

            # Generate summary if enabled
            if self.config.get("generate_summaries", True):
                try:
                    from helpers.utils import generate_markdown_summary

                    summary = generate_markdown_summary(content, self.log_path)
                    if summary:
                        meta.summary = summary
                        self.save_metadata(meta)  # Update with summary
                except Exception as e:
                    log_error(self.log_path, f"Error generating summary: {e}")

            meta.status = "success"
            log_info(
                self.log_path,
                f"Successfully processed podcast transcript: {meta.title}",
            )
            return True

        except Exception as e:
            log_error(self.log_path, f"Error in Atlas processing: {e}")
            return False

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get statistics about processed transcripts"""
        try:
            store = PodcastStore()
            stats = store.get_stats()

            # Add file system stats
            transcript_files = self._find_transcript_files()
            atlas_processed = len(
                list(Path(self.config["data_directory"]).glob("podcasts/markdown/*.md"))
            )

            stats.update(
                {
                    "transcript_files_found": len(transcript_files),
                    "atlas_processed_count": atlas_processed,
                    "processing_rate": (
                        f"{atlas_processed}/{len(transcript_files)}"
                        if transcript_files
                        else "0/0"
                    ),
                }
            )

            return stats

        except Exception as e:
            log_error(self.log_path, f"Error getting stats: {e}")
            return {}


def main():
    """CLI entry point for podcast transcript processing"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Process podcast transcripts through Atlas"
    )
    parser.add_argument(
        "--podcasts", nargs="*", help="Specific podcast slugs to process"
    )
    parser.add_argument(
        "--discover-only",
        action="store_true",
        help="Only run discovery, no fetching/processing",
    )
    parser.add_argument(
        "--fetch-only",
        action="store_true",
        help="Only fetch transcripts, no processing",
    )
    parser.add_argument(
        "--process-only", action="store_true", help="Only process existing transcripts"
    )
    parser.add_argument(
        "--stats", action="store_true", help="Show processing statistics"
    )

    args = parser.parse_args()

    # Load config
    from helpers.config import load_config

    config = load_config()

    # Create ingestor
    ingestor = PodcastTranscriptIngestor(config)

    if args.stats:
        stats = ingestor.get_processing_stats()
        print("📊 Podcast Transcript Processing Stats:")
        print(json.dumps(stats, indent=2, default=str))
        return

    try:
        if args.discover_only:
            ingestor._run_discovery(args.podcasts)
        elif args.fetch_only:
            ingestor._fetch_transcripts(args.podcasts)
        elif args.process_only:
            ingestor._process_fetched_transcripts(args.podcasts)
        else:
            # Full workflow
            ingestor.discover_and_process_transcripts(args.podcasts)

    except Exception as e:
        logger.error(f"Error in podcast transcript processing: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
