#!/usr/bin/env python3
"""
Import completed Whisper transcripts back into the podcast database.

Watches data/whisper_queue/transcripts/ AND audio/ for .txt or .md files
and imports them, updating episode status to 'fetched'.

Expected filename format: {podcast_slug}_{episode_id}.txt
"""

import argparse
import json
import logging
import re
import shutil
from pathlib import Path
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.podcasts.store import PodcastStore

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


def import_transcripts(queue_dir: Path, dry_run: bool = False):
    """Import completed transcripts from watch folder."""

    store = PodcastStore()
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

    # Find transcript files - prefer .md over .txt
    transcript_files = []
    seen_basenames = set()

    # First pass: collect .md files (preprocessed, preferred)
    for search_dir in [transcripts_dir, audio_dir]:
        if search_dir.exists():
            for md_file in search_dir.glob('*.md'):
                basename = md_file.stem
                transcript_files.append(md_file)
                seen_basenames.add(basename)

    # Second pass: add .txt files only if no .md equivalent exists
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
        # Parse filename: {podcast_slug}_{episode_id}_{date}_{title}.txt
        # or simpler: {podcast_slug}_{episode_id}.txt
        # Note: files may have leading digits (1, 2) from MacWhisper batch numbering
        match = re.match(r'^(?:\d+)?([a-z][a-z0-9-]+)_(\d+)(?:_[^.]+)?\.(txt|md|srt)$', tf.name, re.IGNORECASE)
        if not match:
            logger.warning(f"Skipping file with unexpected name format: {tf.name}")
            continue

        podcast_slug = match.group(1)
        episode_id = int(match.group(2))

        if episode_id in processed:
            logger.debug(f"Already processed: {tf.name}")
            continue

        # Get episode info
        episode = store.get_episode_by_id(episode_id)
        if not episode:
            logger.error(f"Episode not found: {episode_id}")
            errors += 1
            continue

        podcast = store.get_podcast(episode.podcast_id)
        if not podcast:
            logger.error(f"Podcast not found for episode: {episode_id}")
            errors += 1
            continue

        # Read transcript
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

            # Update database
            store.update_episode_transcript_status(
                episode_id, 'fetched', str(output_path)
            )

            # Mark as processed
            processed.add(episode_id)

            # Move original to processed folder
            processed_dir = queue_dir / 'processed_files'
            processed_dir.mkdir(exist_ok=True)
            shutil.move(str(tf), str(processed_dir / tf.name))

            logger.info(f"Imported: {episode.title[:50]}...")
            imported += 1

    # Save processed list
    if not dry_run:
        processed_file.write_text(json.dumps(list(processed)))

    print(f"\nImport complete:")
    print(f"  Imported: {imported}")
    print(f"  Errors: {errors}")
    print(f"  Already processed: {len(transcript_files) - imported - errors}")


def main():
    parser = argparse.ArgumentParser(description='Import Whisper transcripts')
    parser.add_argument('--queue-dir', '-q', default='data/whisper_queue',
                        help='Queue directory')
    parser.add_argument('--dry-run', '-n', action='store_true',
                        help='Show what would be done')
    args = parser.parse_args()

    import_transcripts(Path(args.queue_dir), args.dry_run)


if __name__ == '__main__':
    main()
