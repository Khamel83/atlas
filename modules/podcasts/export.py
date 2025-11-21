#!/usr/bin/env python3
"""
Export functionality for transcript content.
Handles saving transcripts as markdown files and integrating with Atlas data structure.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
import re

from modules.podcasts.store import Episode, Podcast

logger = logging.getLogger(__name__)


class TranscriptExporter:
    """Export transcripts to Atlas data structure"""

    def __init__(self, base_path: str = "data/podcasts"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def export_transcript(
        self,
        podcast: Podcast,
        episode: Episode,
        transcript_content: str,
        source_url: str = "",
        metadata: Dict[str, Any] = None,
    ) -> str:
        """
        Export transcript to markdown file following Atlas structure

        Returns the file path where transcript was saved
        """
        try:
            # Create podcast directory structure
            podcast_dir = self.base_path / podcast.slug
            transcripts_dir = podcast_dir / "transcripts"
            metadata_dir = podcast_dir / "metadata"

            # Ensure directories exist
            transcripts_dir.mkdir(parents=True, exist_ok=True)
            metadata_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename from episode
            filename = self._generate_filename(episode)
            transcript_path = transcripts_dir / f"{filename}.md"
            metadata_path = metadata_dir / f"{filename}.json"

            # Create markdown content
            markdown_content = self._create_markdown(
                podcast, episode, transcript_content, source_url, metadata or {}
            )

            # Save transcript markdown
            with open(transcript_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)

            # Save episode metadata
            episode_metadata = self._create_episode_metadata(
                podcast, episode, source_url, metadata or {}
            )

            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(episode_metadata, f, indent=2, default=str)

            # Update episodes.jsonl
            self._update_episodes_jsonl(podcast_dir, episode, str(transcript_path))

            logger.info(f"Exported transcript: {transcript_path}")
            return str(transcript_path)

        except Exception as e:
            logger.error(f"Error exporting transcript for {episode.title}: {e}")
            raise

    def _generate_filename(self, episode: Episode) -> str:
        """Generate safe filename from episode data"""
        # Start with episode title
        if episode.title:
            filename = episode.title
        else:
            filename = f"episode_{episode.id}"

        # Clean filename
        filename = re.sub(r"[^\w\s-]", "", filename)
        filename = re.sub(r"[-\s]+", "-", filename)
        filename = filename.strip("-").lower()

        # Add publish date if available
        if episode.publish_date:
            try:
                if isinstance(episode.publish_date, str):
                    pub_date = datetime.fromisoformat(
                        episode.publish_date.replace("Z", "+00:00")
                    )
                else:
                    pub_date = episode.publish_date

                date_str = pub_date.strftime("%Y-%m-%d")
                filename = f"{date_str}_{filename}"
            except Exception:
                pass

        # Limit length
        if len(filename) > 100:
            filename = filename[:100]

        return filename

    def _create_markdown(
        self,
        podcast: Podcast,
        episode: Episode,
        transcript_content: str,
        source_url: str,
        metadata: Dict[str, Any],
    ) -> str:
        """Create markdown content with frontmatter"""

        # Create frontmatter
        frontmatter = {
            "title": episode.title,
            "podcast": podcast.name,
            "episode_url": episode.url,
            "publish_date": episode.publish_date,
            "transcript_source": source_url,
            "fetched_at": datetime.now().isoformat(),
            "guid": episode.guid,
            "duration": metadata.get("duration"),
            "description": metadata.get("description", ""),
        }

        # Remove None values and empty strings
        frontmatter = {
            k: v for k, v in frontmatter.items() if v is not None and v != ""
        }

        # Build markdown
        lines = ["---"]
        for key, value in frontmatter.items():
            if isinstance(value, str) and "\n" in value:
                # Multi-line string
                lines.append(f"{key}: |")
                for line in value.split("\n"):
                    lines.append(f"  {line}")
            else:
                lines.append(
                    f"{key}: {json.dumps(value) if isinstance(value, (dict, list)) else value}"
                )
        lines.append("---")
        lines.append("")

        # Add transcript content
        lines.append(f"# {episode.title}")
        lines.append("")
        lines.append(transcript_content)

        return "\n".join(lines)

    def _create_episode_metadata(
        self,
        podcast: Podcast,
        episode: Episode,
        source_url: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create complete episode metadata"""
        return {
            "episode_id": episode.id,
            "podcast_id": podcast.id,
            "podcast_name": podcast.name,
            "podcast_slug": podcast.slug,
            "title": episode.title,
            "guid": episode.guid,
            "url": episode.url,
            "publish_date": episode.publish_date,
            "transcript_url": source_url,
            "transcript_status": episode.transcript_status,
            "transcript_fetched_at": datetime.now().isoformat(),
            "audio_url": metadata.get("audio_url"),
            "duration": metadata.get("duration"),
            "description": metadata.get("description"),
            "content_length": metadata.get("content_length"),
            "resolver_used": metadata.get("resolver"),
            "confidence_score": metadata.get("confidence"),
            "original_metadata": episode.metadata or {},
        }

    def _update_episodes_jsonl(
        self, podcast_dir: Path, episode: Episode, transcript_path: str
    ):
        """Update episodes.jsonl with episode info"""
        jsonl_path = podcast_dir / "episodes.jsonl"

        episode_entry = {
            "id": episode.id,
            "guid": episode.guid,
            "title": episode.title,
            "url": episode.url,
            "publish_date": episode.publish_date,
            "transcript_status": episode.transcript_status,
            "transcript_path": transcript_path,
            "updated_at": datetime.now().isoformat(),
        }

        # Read existing entries
        existing_entries = {}
        if jsonl_path.exists():
            try:
                with open(jsonl_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            entry = json.loads(line)
                            existing_entries[entry["guid"]] = entry
            except Exception as e:
                logger.warning(f"Error reading existing episodes.jsonl: {e}")

        # Update entry
        existing_entries[episode.guid] = episode_entry

        # Write back
        try:
            with open(jsonl_path, "w", encoding="utf-8") as f:
                for entry in existing_entries.values():
                    f.write(json.dumps(entry, default=str) + "\n")
        except Exception as e:
            logger.error(f"Error updating episodes.jsonl: {e}")

    def get_podcast_summary(self, podcast_slug: str) -> Dict[str, Any]:
        """Get summary statistics for a podcast"""
        podcast_dir = self.base_path / podcast_slug

        summary = {
            "slug": podcast_slug,
            "transcripts_dir": str(podcast_dir / "transcripts"),
            "metadata_dir": str(podcast_dir / "metadata"),
            "total_episodes": 0,
            "transcripts_available": 0,
            "transcript_files": [],
            "last_updated": None,
        }

        if not podcast_dir.exists():
            return summary

        # Count transcript files
        transcripts_dir = podcast_dir / "transcripts"
        if transcripts_dir.exists():
            transcript_files = list(transcripts_dir.glob("*.md"))
            summary["transcripts_available"] = len(transcript_files)
            summary["transcript_files"] = [f.name for f in transcript_files]

        # Check episodes.jsonl
        jsonl_path = podcast_dir / "episodes.jsonl"
        if jsonl_path.exists():
            try:
                with open(jsonl_path, "r", encoding="utf-8") as f:
                    episodes = [json.loads(line) for line in f if line.strip()]
                    summary["total_episodes"] = len(episodes)

                    # Find last update
                    if episodes:
                        last_updated = max(
                            episode.get("updated_at", "") for episode in episodes
                        )
                        summary["last_updated"] = last_updated

            except Exception as e:
                logger.warning(f"Error reading episodes.jsonl for {podcast_slug}: {e}")

        return summary

    def list_all_podcasts(self) -> List[Dict[str, Any]]:
        """List all podcast directories and their summaries"""
        summaries = []

        if not self.base_path.exists():
            return summaries

        for podcast_dir in self.base_path.iterdir():
            if podcast_dir.is_dir():
                summary = self.get_podcast_summary(podcast_dir.name)
                summaries.append(summary)

        return sorted(summaries, key=lambda x: x["slug"])
