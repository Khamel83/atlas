#!/usr/bin/env python3
"""
Export episodes needing local Whisper transcription.

Creates a queue file with audio URLs and metadata for the Mac Mini
to download and transcribe using MacWhisper Pro.

Output structure:
  data/whisper_queue/
    queue.json          - List of episodes to process
    audio/              - Downloaded audio files (Mac downloads these)
    transcripts/        - Completed transcripts (Mac writes here)
    processed.json      - Episodes that have been processed
"""

import argparse
import json
import logging
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


def export_queue(output_dir: Path, limit: int = 0, status: str = 'local'):
    """Export episodes needing local transcription to queue file."""

    store = PodcastStore()
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / 'audio').mkdir(exist_ok=True)
    (output_dir / 'transcripts').mkdir(exist_ok=True)

    queue_file = output_dir / 'queue.json'
    processed_file = output_dir / 'processed.json'

    # Load existing processed list
    processed = set()
    if processed_file.exists():
        processed = set(json.loads(processed_file.read_text()))

    # Get episodes needing transcription
    episodes = []
    podcasts = store.get_all_podcasts()

    for podcast in podcasts:
        pod_episodes = store.get_episodes_by_podcast(podcast.id)
        for ep in pod_episodes:
            if ep.transcript_status == status and ep.id not in processed:
                # Get audio URL from the episode URL or enclosure
                audio_url = ep.url  # This is usually the audio file

                episodes.append({
                    'id': ep.id,
                    'podcast_slug': podcast.slug,
                    'title': ep.title,
                    'audio_url': audio_url,
                    'publish_date': ep.publish_date,
                    'filename': f"{podcast.slug}_{ep.id}.mp3"
                })

                if limit and len(episodes) >= limit:
                    break
        if limit and len(episodes) >= limit:
            break

    # Write queue
    queue_data = {
        'exported_at': datetime.now().isoformat(),
        'total_count': len(episodes),
        'episodes': episodes
    }

    queue_file.write_text(json.dumps(queue_data, indent=2))
    logger.info(f"Exported {len(episodes)} episodes to {queue_file}")

    # Summary by podcast
    by_podcast = {}
    for ep in episodes:
        slug = ep['podcast_slug']
        by_podcast[slug] = by_podcast.get(slug, 0) + 1

    print("\nExported episodes by podcast:")
    for slug, count in sorted(by_podcast.items(), key=lambda x: -x[1]):
        print(f"  {slug}: {count}")

    return episodes


def main():
    parser = argparse.ArgumentParser(description='Export episodes for Whisper transcription')
    parser.add_argument('--output', '-o', default='data/whisper_queue',
                        help='Output directory')
    parser.add_argument('--limit', '-l', type=int, default=0,
                        help='Limit number of episodes (0=all)')
    parser.add_argument('--status', '-s', default='local',
                        help='Status to export (default: local)')
    args = parser.parse_args()

    output_dir = Path(args.output)
    export_queue(output_dir, args.limit, args.status)


if __name__ == '__main__':
    main()
