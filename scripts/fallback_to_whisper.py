#!/usr/bin/env python3
"""
Fallback to Whisper for failed podcast transcripts.

If a podcast transcript fetch fails AND we have the audio file downloaded,
mark it for Whisper transcription instead of leaving it failed.

This creates a self-healing loop:
1. Try podscripts/website/etc first (automated)
2. If fails + audio exists → mark 'local' for Whisper
3. Whisper transcribes on Mac Mini
4. Import picks it up

Run:
    python scripts/fallback_to_whisper.py          # Dry run
    python scripts/fallback_to_whisper.py --apply  # Apply changes
"""

import argparse
import sqlite3
import re
from pathlib import Path


def extract_episode_id(filename: str) -> str | None:
    """Extract episode ID from audio filename.

    Format: {slug}_{episode_id}_{date}_{title}.mp3
    """
    # Try to find a numeric ID in the filename
    match = re.search(r'_(\d{5,7})_', filename)
    if match:
        return match.group(1)
    return None


def main():
    parser = argparse.ArgumentParser(description='Fallback failed episodes to Whisper')
    parser.add_argument('--apply', action='store_true', help='Apply changes')
    args = parser.parse_args()

    db_path = Path(__file__).parent.parent / 'data/podcasts/atlas_podcasts.db'
    audio_dir = Path(__file__).parent.parent / 'data/whisper_queue/audio'

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Get all failed episodes
    cur.execute('''
        SELECT e.id, e.guid, e.title, p.slug
        FROM episodes e
        JOIN podcasts p ON e.podcast_id = p.id
        WHERE e.transcript_status = 'failed'
    ''')

    failed_episodes = cur.fetchall()

    # Build index of audio files by episode ID
    audio_files = {}
    if audio_dir.exists():
        for f in audio_dir.glob('*.mp3'):
            ep_id = extract_episode_id(f.name)
            if ep_id:
                audio_files[ep_id] = f

    print(f"Failed episodes: {len(failed_episodes)}")
    print(f"Audio files available: {len(audio_files)}")
    print()

    recoverable = []
    for ep_id, guid, title, slug in failed_episodes:
        # Check if we have audio for this episode
        # Try matching by episode ID in guid or filename patterns
        guid_id = re.search(r'(\d{5,7})', guid or '')
        if guid_id and guid_id.group(1) in audio_files:
            recoverable.append({
                'id': ep_id,
                'title': title[:50],
                'slug': slug,
                'audio': audio_files[guid_id.group(1)].name
            })

    print(f"Recoverable with audio: {len(recoverable)}")
    print()

    if recoverable:
        print("EPISODES TO FALLBACK TO WHISPER:")
        print("-" * 70)
        for ep in recoverable[:20]:
            print(f"  {ep['slug'][:25]:<25} {ep['title'][:40]}")
        if len(recoverable) > 20:
            print(f"  ... and {len(recoverable) - 20} more")

        if args.apply:
            print()
            print("APPLYING CHANGES...")
            for ep in recoverable:
                cur.execute(
                    "UPDATE episodes SET transcript_status = 'local' WHERE id = ?",
                    (ep['id'],)
                )
            conn.commit()
            print(f"Marked {len(recoverable)} episodes for Whisper transcription")
        else:
            print()
            print("DRY RUN - use --apply to make changes")
    else:
        print("No failed episodes with available audio to recover.")

    conn.close()


if __name__ == '__main__':
    main()
