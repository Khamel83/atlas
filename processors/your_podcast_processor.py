#!/usr/bin/env python3
"""
YOUR Podcast Processing Engine
Processes YOUR specific podcasts using YOUR dedicated sources
"""

import json
import sqlite3
import sys
from pathlib import Path
from datetime import datetime

sys.path.append('.')

from your_podcast_discovery import YourPodcastDiscovery

class YourPodcastProcessor:
    """Processing engine for YOUR specific podcasts"""

    def __init__(self):
        self.db_path = "data/atlas.db"
        self.discovery = YourPodcastDiscovery()

        # Load YOUR priority podcasts
        with open('config/your_priority_podcasts.json', 'r') as f:
            self.your_podcasts = {podcast['name']: podcast for podcast in json.load(f)}

        print(f"✅ Loaded YOUR podcast processing engine")
        print(f"   • Your Priority Podcasts: {len(self.your_podcasts)}")
        print(f"   • Dedicated Sources: {len(self.discovery.your_sources)}")
        print(f"   • Ready to process: {self._count_pending_your_podcasts()} your episodes")

    def _count_pending_your_podcasts(self):
        """Count your pending episodes in queue"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Count pending episodes for your podcasts
        your_podcast_names = list(self.your_podcasts.keys())
        placeholders = ','.join(['?' for _ in your_podcast_names])

        cursor.execute(f"""
            SELECT COUNT(*) FROM episode_queue
            WHERE status = 'pending' AND podcast_name IN ({placeholders})
        """, your_podcast_names)

        count = cursor.fetchone()[0]
        conn.close()
        return count

    def get_next_your_episode(self):
        """Get next episode from your priority queue"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get your priority podcasts ordered by your count field
        your_podcast_names = list(self.your_podcasts.keys())
        placeholders = ','.join(['?' for _ in your_podcast_names])

        cursor.execute(f"""
            SELECT podcast_name, episode_title, episode_url, id
            FROM episode_queue
            WHERE status = 'pending' AND podcast_name IN ({placeholders})
            ORDER BY
                CASE podcast_name
                    {' '.join([f'WHEN ? THEN {i}' for i, name in enumerate(your_podcast_names)])}
                    ELSE 999
                END,
                created_at ASC
            LIMIT 1
        """, your_podcast_names + your_podcast_names)

        result = cursor.fetchone()
        conn.close()

        if result:
            return {
                'podcast_name': result[0],
                'episode_title': result[1],
                'episode_url': result[2],
                'id': result[3]
            }
        return None

    def process_your_episode(self, episode):
        """Process your episode using your discovery system"""
        print(f"🎯 Processing: {episode['podcast_name']} - {episode['episode_title']}")

        # Use your discovery system
        transcript = self.discovery.discover_transcript(
            episode['podcast_name'],
            episode['episode_title'],
            episode['episode_url']
        )

        if transcript:
            # Store transcript in database
            self._store_transcript(episode, transcript)
            self._update_episode_status(episode['id'], 'found')
            print(f"   ✅ SUCCESS: {len(transcript)} characters stored")
            return True
        else:
            self._update_episode_status(episode['id'], 'not_found')
            print(f"   ❌ No transcript found")
            return False

    def _store_transcript(self, episode, transcript):
        """Store transcript in content table"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO content
            (url, title, content, content_type, created_at, updated_at)
            VALUES (?, ?, ?, 'podcast', ?, ?)
        """, (
            episode['episode_url'],
            f"{episode['podcast_name']}: {episode['episode_title']}",
            transcript,
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))

        conn.commit()
        conn.close()

    def _update_episode_status(self, episode_id, status):
        """Update episode status in queue"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE episode_queue
            SET status = ?, updated_at = ?
            WHERE id = ?
        """, (status, datetime.now().isoformat(), episode_id))

        conn.commit()
        conn.close()

    def process_batch(self, batch_size=10):
        """Process a batch of your episodes"""
        print(f"🚀 Processing batch of {batch_size} YOUR episodes...")

        processed = 0
        found = 0

        for i in range(batch_size):
            episode = self.get_next_your_episode()
            if not episode:
                print(f"   No more of your episodes to process")
                break

            if self.process_your_episode(episode):
                found += 1
            processed += 1

        print(f"📊 Batch complete: {found}/{processed} transcripts found")
        return processed, found

    def get_status(self):
        """Get processing status for your podcasts"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        your_podcast_names = list(self.your_podcasts.keys())
        placeholders = ','.join(['?' for _ in your_podcast_names])

        # Status breakdown
        cursor.execute(f"""
            SELECT status, COUNT(*)
            FROM episode_queue
            WHERE podcast_name IN ({placeholders})
            GROUP BY status
        """, your_podcast_names)

        status_counts = dict(cursor.fetchall())

        # Top podcasts by pending count
        cursor.execute(f"""
            SELECT podcast_name, COUNT(*) as count
            FROM episode_queue
            WHERE status = 'pending' AND podcast_name IN ({placeholders})
            GROUP BY podcast_name
            ORDER BY count DESC
            LIMIT 10
        """, your_podcast_names)

        top_podcasts = cursor.fetchall()

        conn.close()

        return {
            'status_counts': status_counts,
            'top_podcasts': top_podcasts,
            'total_priority': len(self.your_podcasts)
        }


def main():
    """Run your podcast processor"""
    print("🎯 YOUR PODCAST PROCESSING ENGINE")
    print("=" * 50)

    processor = YourPodcastProcessor()
    status = processor.get_status()

    print(f"📊 Your Queue Status:")
    print(f"   • Total Priority Podcasts: {status['total_priority']}")
    for status_name, count in status['status_counts'].items():
        print(f"   • {status_name}: {count}")

    print(f"\n🎯 Your Top Pending Podcasts:")
    for podcast_name, count in status['top_podcasts']:
        print(f"   • {podcast_name}: {count} episodes")

    # Process a batch
    print(f"\n🚀 Starting batch processing...")
    processed, found = processor.process_batch(5)

    if processed > 0:
        print(f"✅ YOUR PODCAST PROCESSING WORKING!")
        print(f"   Processed: {processed} episodes")
        print(f"   Found: {found} transcripts")
        print(f"   Ready for continuous operation")
    else:
        print(f"ℹ️  No pending episodes found for your podcasts")


if __name__ == "__main__":
    main()