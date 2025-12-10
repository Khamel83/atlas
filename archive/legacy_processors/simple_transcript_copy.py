#!/usr/bin/env python3
"""
Simple Copy of All Podcast Transcripts from Atlas v1 to v2
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime

def copy_all_transcripts():
    """Copy all podcast transcripts directly"""
    print('🚀 Copying 9,553 podcast transcripts from Atlas v1 to v2...')

    v1_conn = sqlite3.connect('atlas.db')
    v2_conn = sqlite3.connect('atlas_v2/data/atlas_v2.db')

    v1_cursor = v1_conn.cursor()
    v2_cursor = v2_conn.cursor()

    # Get all podcast transcripts
    v1_cursor.execute('SELECT id, title, url, content, metadata FROM content WHERE content_type = "podcast_transcript" AND LENGTH(content) > 1000')
    transcripts = v1_cursor.fetchall()

    print(f'📊 Found {len(transcripts)} podcast transcripts to copy')

    # Create directory
    Path('atlas_v2/content/podcast_transcripts').mkdir(parents=True, exist_ok=True)

    copied = 0
    for i, (transcript_id, title, url, content, metadata) in enumerate(transcripts):
        if i % 1000 == 0:
            print(f'📊 Copying transcript {i:,}/{len(transcripts):,}...')

        try:
            # Create content file
            safe_title = ''.join(c for c in (title or f'transcript_{transcript_id}') if c.isalnum() or c in (' ', '-', '_')).strip()[:50]
            filename = f'{safe_title.replace(" ", "_")}.md'
            filepath = Path(f'atlas_v2/content/podcast_transcripts/{filename}')

            # Write transcript
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f'# {title or "Untitled Transcript"}\n\n')
                f.write(f'**Source**: {url}\n')
                f.write(f'**Atlas ID**: {transcript_id}\n')
                f.write(f'**Migrated**: {datetime.now().isoformat()}\n\n')
                f.write('---\n\n')
                f.write(content)

            # Add to Atlas v2 database
            content_id = f'v1-transcript-{transcript_id}'

            # Parse metadata
            try:
                meta_dict = json.loads(metadata) if metadata else {}
            except:
                meta_dict = {'original_metadata': metadata}

            meta_dict.update({
                'migrated_from_v1': True,
                'v1_transcript_id': transcript_id,
                'migration_timestamp': datetime.now().isoformat()
            })

            # Insert into content_metadata
            v2_cursor.execute('''
                INSERT OR REPLACE INTO content_metadata
                (content_id, source_url, source_name, content_type, title, metadata_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                content_id, url, 'atlas_v1_podcast', 'podcast_transcript',
                title, json.dumps(meta_dict),
                datetime.now().isoformat(), datetime.now().isoformat()
            ))

            # Mark as completed in processing queue
            v2_cursor.execute('''
                INSERT OR REPLACE INTO processing_queue
                (content_id, source_url, source_name, content_type, status, metadata_json, created_at, updated_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                content_id, url, 'atlas_v1_podcast', 'podcast_transcript', 'completed',
                json.dumps(meta_dict), datetime.now().isoformat(), datetime.now().isoformat(), datetime.now().isoformat()
            ))

            copied += 1

        except Exception as e:
            print(f'❌ Error copying transcript {transcript_id}: {e}')

    v2_conn.commit()
    v1_conn.close()
    v2_conn.close()

    print(f'\n✅ Successfully copied {copied:,} podcast transcripts to Atlas v2!')
    print(f'📁 Files saved to: atlas_v2/content/podcast_transcripts/')
    print(f'🗄️ Database entries created in Atlas v2')
    return copied

if __name__ == "__main__":
    copy_all_transcripts()