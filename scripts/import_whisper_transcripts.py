#!/usr/bin/env python3
"""
Import completed Whisper/WhisperX transcripts back into the podcast database.

Watches data/whisper_queue/transcripts/ AND audio/ for .txt, .md, or .json files
and imports them, updating episode status to 'fetched'.

Supports:
- .txt files: Raw MacWhisper output (no speakers)
- .md files: Preprocessed transcripts (no speakers)
- .json files: WhisperX output with speaker diarization

Expected filename format: {podcast_slug}_{episode_id}_{date}_{title}.{txt|md|json}
"""

import argparse
import json
import logging
import re
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.podcasts.store import PodcastStore, EpisodeSpeaker
from modules.podcasts.speaker_mapper import SpeakerMapper, SpeakerMapping

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_preprocessor(queue_dir: Path) -> int:
    """Run the preprocessor on any .txt files that don't have .md equivalents."""
    import subprocess

    script_path = Path(__file__).parent / 'preprocess_whisper_transcript.py'
    if not script_path.exists():
        logger.warning("Preprocessor script not found, skipping preprocessing")
        return 0

    result = subprocess.run(
        ['./venv/bin/python', str(script_path), '--queue-dir', str(queue_dir), '--all'],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )

    if result.returncode != 0:
        logger.error(f"Preprocessor failed: {result.stderr}")
        return 0

    # Count how many files were processed
    import re
    matches = re.findall(r'Processed: .+ -> .+', result.stdout)
    return len(matches)


def parse_whisperx_json(json_path: Path) -> Dict:
    """
    Parse WhisperX JSON output file.

    Returns dict with:
    - segments: List of {speaker, text, start, end}
    - num_speakers: Number of unique speakers detected
    - language: Detected language
    """
    with open(json_path) as f:
        data = json.load(f)

    segments = data.get("segments", [])
    speakers = set()

    for seg in segments:
        speaker = seg.get("speaker")
        if speaker:
            speakers.add(speaker)

    return {
        "segments": segments,
        "num_speakers": len(speakers) if speakers else 1,
        "language": data.get("language", "en"),
        "raw": data
    }


def format_diarized_transcript(
    segments: List[Dict],
    speaker_mappings: List[SpeakerMapping]
) -> str:
    """
    Format WhisperX segments into markdown with speaker attribution.

    Args:
        segments: WhisperX segments with 'speaker' and 'text' keys
        speaker_mappings: List of SpeakerMapping objects

    Returns:
        Formatted markdown string
    """
    # Build speaker name lookup
    speaker_names = {m.label: m.name for m in speaker_mappings}

    lines = []
    current_speaker = None
    current_text = []

    for segment in segments:
        speaker = segment.get("speaker", "UNKNOWN")
        text = segment.get("text", "").strip()

        if not text:
            continue

        # New speaker - flush current text and start new paragraph
        if speaker != current_speaker:
            if current_speaker is not None and current_text:
                prev_name = speaker_names.get(current_speaker, current_speaker)
                lines.append(f"**{prev_name}:** {' '.join(current_text)}")
                lines.append("")  # Blank line between speakers

            current_speaker = speaker
            current_text = [text]
        else:
            # Same speaker - accumulate text
            current_text.append(text)

    # Flush final speaker's text
    if current_speaker is not None and current_text:
        speaker_name = speaker_names.get(current_speaker, current_speaker)
        lines.append(f"**{speaker_name}:** {' '.join(current_text)}")

    return "\n".join(lines)


def import_transcripts(queue_dir: Path, dry_run: bool = False):
    """Import completed transcripts from watch folder."""

    store = PodcastStore()
    speaker_mapper = SpeakerMapper()
    transcripts_dir = queue_dir / 'transcripts'
    audio_dir = queue_dir / 'audio'  # MacWhisper outputs here by default
    processed_file = queue_dir / 'processed.json'

    # First, run preprocessor to convert .txt to .md with ad removal
    if not dry_run:
        preprocessed = run_preprocessor(queue_dir)
        if preprocessed > 0:
            logger.info(f"Preprocessed {preprocessed} transcript files")

    # Load processed list
    processed = set()
    if processed_file.exists():
        processed = set(json.loads(processed_file.read_text()))

    # Find transcript files - prefer .json (diarized) > .md > .txt
    transcript_files = []
    seen_basenames = set()

    # First pass: collect .json files (WhisperX diarized, highest priority)
    for search_dir in [transcripts_dir, audio_dir]:
        if search_dir.exists():
            for json_file in search_dir.glob('*.json'):
                # Skip processed.json and other non-transcript files
                if json_file.name in ['processed.json', 'diarization_queue.json']:
                    continue
                basename = json_file.stem
                transcript_files.append(json_file)
                seen_basenames.add(basename)

    # Second pass: collect .md files (preprocessed)
    for search_dir in [transcripts_dir, audio_dir]:
        if search_dir.exists():
            for md_file in search_dir.glob('*.md'):
                basename = md_file.stem
                if basename not in seen_basenames:
                    transcript_files.append(md_file)
                    seen_basenames.add(basename)

    # Third pass: add .txt files only if no .json or .md equivalent exists
    for search_dir in [transcripts_dir, audio_dir]:
        if search_dir.exists():
            for txt_file in search_dir.glob('*.txt'):
                basename = txt_file.stem
                if basename not in seen_basenames:
                    transcript_files.append(txt_file)
                    seen_basenames.add(basename)

    logger.info(f"Found {len(transcript_files)} transcript files")

    imported = 0
    errors = 0

    for tf in transcript_files:
        # Parse filename: {podcast_slug}_{episode_id}_{date}_{title}.{txt|md|json}
        # or simpler: {podcast_slug}_{episode_id}.{txt|md|json}
        # Note: files may have leading digits (1, 2) from MacWhisper batch numbering
        match = re.match(r'^(?:\d+)?([a-z][a-z0-9-]+)_(\d+)(?:_[^.]+)?\.(txt|md|json|srt)$', tf.name, re.IGNORECASE)
        if not match:
            logger.warning(f"Skipping file with unexpected name format: {tf.name}")
            continue

        podcast_slug = match.group(1)
        episode_id = int(match.group(2))
        file_type = match.group(3).lower()

        if episode_id in processed:
            logger.debug(f"Already processed: {tf.name}")
            continue

        # Get episode info - try by ID first, then by title
        episode = store.get_episode_by_id(episode_id)
        if not episode:
            # Fallback: try to find by podcast slug and title from filename
            # Filename format: {slug}_{id}_{date}_{title}.json
            title_match = re.match(r'^(?:\d+)?[a-z][a-z0-9-]+_\d+_\d{4}-\d{2}-\d{2}_(.+)\.(txt|md|json|srt)$', tf.name, re.IGNORECASE)
            if title_match:
                title_slug = title_match.group(1).replace('-', ' ').replace('_', ' ')
                # Try to find episode by slug search
                episodes = store.search_episodes_by_title(podcast_slug, title_slug[:50])
                if episodes:
                    episode = episodes[0]
                    logger.info(f"Found episode by title fallback: {episode.id} - {episode.title}")

            if not episode:
                logger.error(f"Episode not found: {episode_id} (title fallback also failed)")
                errors += 1
                continue

        podcast = store.get_podcast(episode.podcast_id)
        if not podcast:
            logger.error(f"Podcast not found for episode: {episode_id}")
            errors += 1
            continue

        # Handle different file types
        is_diarized = (file_type == 'json')
        speaker_mappings = []
        content = ""

        if is_diarized:
            # Parse WhisperX JSON with speaker diarization
            try:
                whisperx_data = parse_whisperx_json(tf)
                segments = whisperx_data["segments"]
                num_speakers = whisperx_data["num_speakers"]

                # Get description from metadata
                description = episode.metadata.get('description', '') if episode.metadata else ''

                # Map speakers to names (pass segments for self-identification)
                speaker_mappings = speaker_mapper.map_speakers(
                    podcast_slug=podcast.slug,
                    episode_title=episode.title,
                    episode_description=description,
                    num_speakers=num_speakers,
                    segments=segments
                )

                # Format transcript with speaker names
                content = format_diarized_transcript(segments, speaker_mappings)

                logger.info(f"Diarized: {num_speakers} speakers detected")
            except Exception as e:
                logger.error(f"Error parsing WhisperX JSON {tf.name}: {e}")
                errors += 1
                continue
        else:
            # Read plain text/markdown content
            content = tf.read_text(encoding='utf-8')

        # Determine output path (use absolute path from project root)
        project_root = Path(__file__).parent.parent
        transcript_dir = project_root / 'data' / 'podcasts' / podcast.slug / 'transcripts'
        transcript_dir.mkdir(parents=True, exist_ok=True)

        date_str = episode.publish_date[:10] if episode.publish_date else datetime.now().strftime('%Y-%m-%d')
        title_slug = re.sub(r'[^\w\s-]', '', episode.title.lower())
        title_slug = re.sub(r'[\s]+', '-', title_slug)[:80]
        output_filename = f"{date_str}_{title_slug}.md"
        output_path = transcript_dir / output_filename

        if dry_run:
            logger.info(f"Would import: {tf.name} -> {output_path}")
            if is_diarized and speaker_mappings:
                for sm in speaker_mappings:
                    logger.info(f"  {sm.label} -> {sm.name} (conf={sm.confidence:.2f})")
        else:
            # Extract show notes from metadata
            description = episode.metadata.get('description', '') if episode.metadata else ''
            duration = episode.metadata.get('duration', '') if episode.metadata else ''

            # Build header with all available metadata
            header_parts = [
                f"# {episode.title}",
                "",
                f"**Podcast:** {podcast.name}",
                f"**Date:** {episode.publish_date}",
            ]
            if duration:
                header_parts.append(f"**Duration:** {duration}")

            # Different source label for diarized vs non-diarized
            if is_diarized:
                header_parts.append("**Source:** WhisperX (local transcription with diarization)")
            else:
                header_parts.append("**Source:** MacWhisper Pro (local transcription)")

            # Add show notes if available
            if description:
                header_parts.extend([
                    "",
                    "## Show Notes",
                    "",
                    description,
                ])

            header_parts.extend(["", "---", "", "## Transcript", ""])
            header = "\n".join(header_parts) + "\n"
            output_path.write_text(header + content, encoding='utf-8')

            # Update database - episode status
            store.update_episode_transcript_status(
                episode_id, 'fetched', str(output_path)
            )

            # Save speaker mappings to database if diarized
            if is_diarized and speaker_mappings:
                for sm in speaker_mappings:
                    store.add_episode_speaker(EpisodeSpeaker(
                        episode_id=episode_id,
                        speaker_label=sm.label,
                        speaker_name=sm.name,
                        confidence=sm.confidence,
                        source=sm.source
                    ))

            # Mark as processed
            processed.add(episode_id)

            # Move original to processed folder
            processed_dir = queue_dir / 'processed_files'
            processed_dir.mkdir(exist_ok=True)
            shutil.move(str(tf), str(processed_dir / tf.name))

            diarized_tag = " [diarized]" if is_diarized else ""
            logger.info(f"Imported{diarized_tag}: {episode.title[:50]}...")
            imported += 1

    # Save processed list
    if not dry_run:
        processed_file.write_text(json.dumps(list(processed)))

    print(f"\nImport complete:")
    print(f"  Imported: {imported}")
    print(f"  Errors: {errors}")
    print(f"  Already processed: {len(transcript_files) - imported - errors}")


def reprocess_transcripts(queue_dir: Path, dry_run: bool = False, limit: int = 0):
    """
    Re-process already-imported transcripts with updated speaker mapping.

    Reads JSON files from processed_files/ and regenerates the markdown
    transcripts with the new speaker mapping logic.
    """
    store = PodcastStore()
    speaker_mapper = SpeakerMapper()
    processed_dir = queue_dir / 'processed_files'

    if not processed_dir.exists():
        print("No processed_files directory found")
        return

    # Find JSON files (WhisperX diarized transcripts)
    json_files = list(processed_dir.glob('*.json'))
    # Filter out non-transcript files
    json_files = [f for f in json_files if f.name not in ['processed.json', 'diarization_queue.json']]

    if limit > 0:
        json_files = json_files[:limit]

    logger.info(f"Found {len(json_files)} JSON files to reprocess")

    reprocessed = 0
    errors = 0

    for tf in json_files:
        # Parse filename: {podcast_slug}_{episode_id}_{date}_{title}.json
        match = re.match(r'^(?:\d+)?([a-z][a-z0-9-]+)_(\d+)(?:_[^.]+)?\.(json)$', tf.name, re.IGNORECASE)
        if not match:
            logger.warning(f"Skipping file with unexpected name format: {tf.name}")
            continue

        podcast_slug = match.group(1)
        episode_id = int(match.group(2))

        # Get episode info
        episode = store.get_episode_by_id(episode_id)
        if not episode:
            # Try title fallback
            title_match = re.match(r'^(?:\d+)?[a-z][a-z0-9-]+_\d+_\d{4}-\d{2}-\d{2}_(.+)\.json$', tf.name, re.IGNORECASE)
            if title_match:
                title_slug = title_match.group(1).replace('-', ' ').replace('_', ' ')
                episodes = store.search_episodes_by_title(podcast_slug, title_slug[:50])
                if episodes:
                    episode = episodes[0]

            if not episode:
                logger.error(f"Episode not found: {episode_id}")
                errors += 1
                continue

        podcast = store.get_podcast(episode.podcast_id)
        if not podcast:
            logger.error(f"Podcast not found for episode: {episode_id}")
            errors += 1
            continue

        # Parse WhisperX JSON
        try:
            whisperx_data = parse_whisperx_json(tf)
            segments = whisperx_data["segments"]
            num_speakers = whisperx_data["num_speakers"]

            description = episode.metadata.get('description', '') if episode.metadata else ''

            # Map speakers with NEW logic
            speaker_mappings = speaker_mapper.map_speakers(
                podcast_slug=podcast.slug,
                episode_title=episode.title,
                episode_description=description,
                num_speakers=num_speakers,
                segments=segments
            )

            # Format transcript with speaker names
            content = format_diarized_transcript(segments, speaker_mappings)

        except Exception as e:
            logger.error(f"Error parsing {tf.name}: {e}")
            errors += 1
            continue

        # Determine output path
        project_root = Path(__file__).parent.parent
        transcript_dir = project_root / 'data' / 'podcasts' / podcast.slug / 'transcripts'

        date_str = episode.publish_date[:10] if episode.publish_date else datetime.now().strftime('%Y-%m-%d')
        title_slug = re.sub(r'[^\w\s-]', '', episode.title.lower())
        title_slug = re.sub(r'[\s]+', '-', title_slug)[:80]
        output_filename = f"{date_str}_{title_slug}.md"
        output_path = transcript_dir / output_filename

        if dry_run:
            print(f"Would reprocess: {episode.title[:50]}...")
            for sm in speaker_mappings:
                if sm.confidence > 0.5 or not sm.name.startswith('Speaker'):
                    print(f"  {sm.label} -> {sm.name} (conf={sm.confidence:.2f})")
        else:
            # Build header
            duration = episode.metadata.get('duration', '') if episode.metadata else ''
            header_parts = [
                f"# {episode.title}",
                "",
                f"**Podcast:** {podcast.name}",
                f"**Date:** {episode.publish_date}",
            ]
            if duration:
                header_parts.append(f"**Duration:** {duration}")
            header_parts.append("**Source:** WhisperX (local transcription with diarization)")

            if description:
                header_parts.extend(["", "## Show Notes", "", description])
            header_parts.extend(["", "---", "", "## Transcript", ""])
            header = "\n".join(header_parts) + "\n"

            output_path.write_text(header + content, encoding='utf-8')

            # Update speaker mappings in database
            for sm in speaker_mappings:
                store.add_episode_speaker(EpisodeSpeaker(
                    episode_id=episode.id,
                    speaker_label=sm.label,
                    speaker_name=sm.name,
                    confidence=sm.confidence,
                    source=sm.source
                ))

            logger.info(f"Reprocessed: {episode.title[:50]}...")
            reprocessed += 1

    print(f"\nReprocess complete:")
    print(f"  Reprocessed: {reprocessed}")
    print(f"  Errors: {errors}")


def main():
    parser = argparse.ArgumentParser(description='Import Whisper transcripts')
    parser.add_argument('--queue-dir', '-q', default='data/whisper_queue',
                        help='Queue directory')
    parser.add_argument('--dry-run', '-n', action='store_true',
                        help='Show what would be done')
    parser.add_argument('--reprocess', '-r', action='store_true',
                        help='Reprocess already-imported transcripts with updated speaker mapping')
    parser.add_argument('--limit', '-l', type=int, default=0,
                        help='Limit number of files to process (0 = no limit)')
    args = parser.parse_args()

    if args.reprocess:
        reprocess_transcripts(Path(args.queue_dir), args.dry_run, args.limit)
    else:
        import_transcripts(Path(args.queue_dir), args.dry_run)


if __name__ == '__main__':
    main()
