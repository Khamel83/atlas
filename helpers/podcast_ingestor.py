# helpers/podcast_ingestor.py
import os
from datetime import datetime
from typing import Dict, Any

import feedparser
import requests

from helpers.base_ingestor import BaseIngestor
from helpers.dedupe import link_uid
from helpers.metadata_manager import ContentType
from helpers.path_manager import PathType
from helpers.podcast_space_manager import should_download_audio, check_disk_space_before_download
from helpers.transcription import transcribe_audio
from helpers.utils import generate_markdown_summary, log_error, log_info

USER_AGENT = "AtlasIngestor/1.0 (+https://github.com/yourrepo/atlas)"


class PodcastIngestor(BaseIngestor):
    def get_content_type(self):
        return ContentType.PODCAST

    def get_module_name(self):
        return "podcast_ingestor"

    def __init__(self, config):
        super().__init__(config, ContentType.PODCAST, "podcast_ingestor")
        self.user_agent = USER_AGENT

    def fetch_content(self, feed_url, metadata):
        # Parse the feed and return entries
        feed = feedparser.parse(
            feed_url, request_headers={"User-Agent": self.user_agent}
        )
        if not feed.entries:
            self.error_handler.handle_error(
                Exception(f"No entries found in feed: {feed_url}"), self.log_path
            )
            return False, None
        return True, feed.entries

    def process_feed(self, feed_url):
        """
        Fetches and processes all entries from a podcast feed URL.
        Handles errors and logs progress for each entry.
        """
        metadata = {"source": feed_url}
        success, entries = self.fetch_content(feed_url, metadata)
        if not success or not entries:
            log_error(self.log_path, f"Failed to fetch entries for feed: {feed_url}")
            return False
        for entry in entries:
            try:
                self.process_content(entry, metadata)
            except Exception as e:
                self.error_handler.handle_error(
                    Exception(f"Error processing entry in feed {feed_url}: {e}"),
                    self.log_path,
                )
        return True

    def process_content(self, entry, metadata):
        # Assign title early for reliable logging
        title = entry.get("title", "Untitled Episode")

        # Robust audio URL extraction
        audio_url = None
        if hasattr(entry, "enclosures") and entry.enclosures:
            audio_url = entry.enclosures[0].href
        elif hasattr(entry, "links") and entry.links:
            for link in entry.links:
                if link.get("type", "").startswith("audio"):
                    audio_url = link.get("href")
                    break
        if not audio_url:
            self.error_handler.handle_error(
                Exception(f"No audio URL found for entry: {title}"), self.log_path
            )
            return False

        # --- UID Generation ---
        # Use the podcast's official guid if available, otherwise use the audio URL.
        # This is the key to deduplication.
        try:
            unique_identifier = entry.get("guid", audio_url)
            if not unique_identifier:
                self.error_handler.handle_error(
                    Exception(
                        f"Could not determine a unique identifier for entry: {title}"
                    ),
                    self.log_path,
                )
                return False

            # Use the standardized link_uid function
            file_id = link_uid(unique_identifier)
        except Exception as e:
            self.error_handler.handle_error(
                Exception(f"Error generating file ID for entry {title}: {e}"),
                self.log_path,
            )
            return False

        # Use the path_manager to get all required paths
        paths = self.path_manager.get_path_set(self.content_type, file_id)
        audio_path = paths.get_path(PathType.AUDIO)
        paths.get_path(PathType.METADATA)
        transcript_path = paths.get_path(PathType.TRANSCRIPT)
        md_path = paths.get_path(PathType.MARKDOWN)

        # CAPTURE ALL METADATA - Never lose any information!
        # Extract every available field from the RSS entry
        podcast_metadata = self._extract_all_podcast_metadata(entry, audio_url)

        meta = self.create_metadata(
            source=metadata["source"],
            title=entry.title,
            type_specific=podcast_metadata["type_specific"],
        )
        # Override the generated UID with our specific one for deduplication
        meta.uid = file_id

        # Save raw RSS entry data for complete preservation
        self.save_raw_data(entry, meta, "rss_entry")
        try:
            # Check if we should download audio based on space management settings
            download_audio = should_download_audio(title, self.config)

            if download_audio:
                # Check disk space before downloading
                check_disk_space_before_download()

                if not os.path.exists(audio_path):
                    log_info(self.log_path, f"Downloading: {title}")
                    with requests.get(audio_url, stream=True, timeout=30) as r:
                        r.raise_for_status()
                        with open(audio_path, "wb") as f:
                            for chunk in r.iter_content(chunk_size=8192):
                                f.write(chunk)
                    meta.status = "success"
                else:
                    meta.status = "already_downloaded"
            else:
                log_info(self.log_path, f"Skipping audio download for: {title} (transcript-first mode)")
                meta.status = "transcript_only"

            transcript_text = None
            run_transcription = self.config.get("run_transcription", False)
            if run_transcription:
                transcript_text = transcribe_audio(audio_path, self.log_path)
                meta.transcript_path = transcript_path if transcript_text else None
            else:
                log_info(
                    self.log_path, "Transcription is disabled via config. Skipping."
                )
                meta.transcript_path = None
                # If transcription is off, check if an old transcript exists
                if os.path.exists(transcript_path):
                    with open(transcript_path, "r", encoding="utf-8") as tf:
                        transcript_text = tf.read()

            # Generate Markdown summary file first
            md = generate_markdown_summary(
                title=entry.title,
                source=metadata["source"],
                date=meta.date,
                tags=[],
                notes=[],
                content=transcript_text,
            )
            with open(md_path, "w", encoding="utf-8") as mdf:
                mdf.write(md)
            meta.content_path = md_path

            # --- Run Evaluations ---
            if transcript_text:
                self.run_evaluations(transcript_text, meta)

        except Exception as e:
            self.handle_error(
                f"Failed to download or process podcast: {e}",
                source=audio_url,
                should_retry=True,
            )
            meta.set_error(str(e))

        # Save metadata regardless of success/failure
        self.save_metadata(meta)

        return meta.status == "success"

        return True  # Indicate success for the ingestor

    def _extract_all_podcast_metadata(self, entry, audio_url):
        """
        Extract ALL available metadata from RSS feed entry.
        CORE PRINCIPLE: Never lose any data - capture everything!
        """
        # Raw entry data - preserve the complete source
        raw_entry = {}

        # Convert feedparser entry to dict, handling all possible fields
        for key in entry.keys():
            try:
                value = entry[key]
                # Handle complex objects by converting to serializable format
                if hasattr(value, "__dict__"):
                    raw_entry[key] = str(value)
                elif isinstance(value, (list, dict)):
                    raw_entry[key] = value
                else:
                    raw_entry[key] = str(value) if value is not None else None
            except Exception as e:
                raw_entry[key] = f"<extraction_error: {str(e)}>"

        # Extract structured podcast-specific metadata
        podcast_data = {
            # Core episode information
            "episode_number": entry.get("itunes_episode"),
            "season_number": entry.get("itunes_season"),
            "episode_type": entry.get("itunes_episodetype", "full"),
            # Content descriptions (often contain show notes!)
            "summary": entry.get("summary", ""),
            "subtitle": entry.get("subtitle", ""),
            "description": entry.get("description", ""),
            # Publication information
            "published": entry.get("published", ""),
            "published_parsed": str(entry.get("published_parsed", "")),
            "updated": entry.get("updated", ""),
            # Author/Creator information
            "author": entry.get("author", ""),
            "authors": entry.get("authors", []),
            "creator": entry.get("creator", ""),
            "publisher": entry.get("publisher", ""),
            # Media information
            "duration": entry.get("itunes_duration", ""),
            "explicit": entry.get("itunes_explicit"),
            "language": entry.get("language", ""),
            # Links and references
            "link": entry.get("link", ""),
            "links": entry.get("links", []),
            "guid": entry.get("guid", ""),
            "id": entry.get("id", ""),
            # Visual content
            "image": entry.get("image", {}),
            "thumbnail": entry.get("thumbnail", ""),
            # Categorization
            "tags": entry.get("tags", []),
            "categories": entry.get("categories", []),
            "keywords": entry.get("keywords", []),
            # Technical metadata
            "enclosures": entry.get("enclosures", []),
            "content": entry.get("content", []),
            # Copyright and legal
            "copyright": entry.get("copyright", ""),
            "rights": entry.get("rights", ""),
            # Audio URL (redundant but explicit)
            "audio_url": audio_url,
        }

        # Handle iTunes-specific fields (there may be many!)
        itunes_fields = {}
        for key in entry.keys():
            if key.startswith("itunes_"):
                itunes_fields[key] = entry.get(key)

        # Handle any custom namespaced fields (spotify:, google:, etc.)
        custom_fields = {}
        for key in entry.keys():
            if ":" in key and not key.startswith("itunes_"):
                custom_fields[key] = entry.get(key)

        # Store everything in type_specific metadata
        return {
            "type_specific": {
                "podcast": podcast_data,
                "itunes_metadata": itunes_fields,
                "custom_fields": custom_fields,
                "raw_entry": raw_entry,  # Complete original data
                "extraction_timestamp": datetime.now().isoformat(),
                "feedparser_version": getattr(feedparser, "__version__", "unknown"),
            }
        }


def ingest_podcasts(config: dict, opml_path: str = "inputs/podcasts.opml"):
    ingestor = PodcastIngestor(config)

    if not os.path.exists(opml_path):
        log_error(ingestor.log_path, f"OPML file not found: {opml_path}")
        return

    with open(opml_path, "r") as f:
        lines = f.read().splitlines()

    feed_urls = [
        line.split("xmlUrl=")[-1].split('"')[1] for line in lines if "xmlUrl=" in line
    ]

    for feed_url in feed_urls:
        log_info(ingestor.log_path, f"Processing feed: {feed_url}")
        # The fetch_content method handles its own error logging and retry queue
        ingestor.process_feed(feed_url)

    log_info(ingestor.log_path, "Podcast ingestion complete.")


def process_podcast(url: str, config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Process individual podcast URL - Core function for Block 1 validation.

    Args:
        url: Podcast RSS feed URL or episode URL
        config: Configuration dictionary

    Returns:
        Dict with processing result
    """
    try:
        config = config or {}
        ingestor = PodcastIngestor(config)

        # Process podcast feed
        success = ingestor.process_feed(url)

        if success:
            return {
                'success': True,
                'url': url,
                'message': 'Podcast processed successfully'
            }
        else:
            return {
                'success': False,
                'url': url,
                'error': 'Podcast processing failed'
            }

    except Exception as e:
        return {
            'success': False,
            'url': url,
            'error': str(e)
        }
