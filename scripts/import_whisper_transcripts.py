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


def import_transcripts(queue_dir: Path, dry_run: bool = False):
    """Import completed transcripts from watch folder."""

    store = PodcastStore()
    transcripts_dir = queue_dir / 'transcripts'
    audio_dir = queue_dir / 'audio'  # MacWhisper outputs here by default
    processed_file = queue_dir / 'processed.json'

    # Load processed list
    processed = set()
    if processed_file.exists():
        processed = set(json.loads(processed_file.read_text()))

    # Find transcript files in both transcripts/ and audio/ folders
    transcript_files = []
    for search_dir in [transcripts_dir, audio_dir]:
        if search_dir.exists():
            transcript_files.extend(search_dir.glob('*.txt'))
            transcript_files.extend(search_dir.glob('*.md'))
    logger.info(f"Found {len(transcript_files)} transcript files")

    imported = 0
    errors = 0

    for tf in transcript_files:
        # Parse filename: {podcast_slug}_{episode_id}_{date}_{title}.txt
        # or simpler: {podcast_slug}_{episode_id}.txt
        match = re.match(r'^(.+?)_(\d+)(?:_[^.]+)?\.(txt|md|srt)$', tf.name)
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
            # Write transcript with metadata header
            header = f"""# {episode.title}

**Podcast:** {podcast.name}
**Date:** {episode.publish_date}
**Source:** MacWhisper Pro (local transcription)

---

"""
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
