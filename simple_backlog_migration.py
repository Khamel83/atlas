#!/usr/bin/env python3
"""
Simple Atlas v1 → v2 Backlog Migration
"""

import sqlite3
import re
from datetime import datetime

def create_slug(text):
    """Create URL-safe slug from text"""
    if not text:
        return "unknown"
    slug = re.sub(r'[^\w\s-]', '', text.lower())
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug[:50]

def migrate_backlog():
    """Migrate backlog directly to Atlas v2 database"""
    print("🚀 Starting backlog migration...")

    # Connect to databases
    v1_conn = sqlite3.connect("output/processing_queue.db")
    v2_conn = sqlite3.connect("atlas_v2/data/atlas_v2.db")

    try:
        # Get pending episodes from Atlas v1
        cursor = v1_conn.execute("""
            SELECT
                episode_url,
                episode_title,
                podcast_name,
                audio_url,
                created_at,
                priority
            FROM processing_queue
            WHERE status = 'pending'
            ORDER BY created_at ASC
        """)

        episodes = cursor.fetchall()
        print(f"📊 Found {len(episodes)} pending episodes to migrate")

        migrated = 0
        for episode in episodes:
            episode_url, episode_title, podcast_name, audio_url, created_at, priority = episode

            # Create content ID
            title = episode_title or 'unknown'
            slug = create_slug(title)
            date_str = datetime.now().strftime('%Y-%m-%d')
            content_id = f"podcast-{date_str}-{slug}"

            # Create metadata
            metadata = {
                'title': episode_title,
                'podcast_name': podcast_name,
                'audio_url': audio_url,
                'migrated_from': 'atlas_v1',
                'original_priority': priority
            }

            # Insert into Atlas v2 queue
            try:
                v2_conn.execute('''
                    INSERT OR IGNORE INTO processing_queue
                    (content_id, source_url, source_name, content_type, status, priority, metadata_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    content_id,
                    episode_url,
                    podcast_name,
                    'podcast',
                    'pending',
                    'high',
                    str(metadata),
                    created_at,
                    datetime.now().isoformat()
                ))

                migrated += 1
                if migrated % 25 == 0:
                    print(f"📊 Migrated {migrated} episodes...")

            except Exception as e:
                print(f"❌ Error migrating {episode_title}: {e}")

        v2_conn.commit()
        print(f"✅ Migration complete! Successfully migrated {migrated} episodes")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        v1_conn.close()
        v2_conn.close()

if __name__ == "__main__":
    migrate_backlog()