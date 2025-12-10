#!/usr/bin/env python3
"""
Fast Transcript Processor - RSS Only Version
Optimized for speed using only working RSS feed method
"""

import sqlite3
import feedparser
from datetime import datetime
from typing import List, Dict, Optional

class FastTranscriptProcessor:
    def __init__(self):
        self.db_path = "podcast_processing.db"

    def get_pending_episodes(self, limit: int = 50) -> List[Dict]:
        """Get pending episodes prioritized by podcast priority"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        query = """
        SELECT e.*, p.name as podcast_name, p.rss_feed
        FROM episodes e
        JOIN podcasts p ON e.podcast_id = p.id
        WHERE e.processing_status = 'pending'
        AND e.transcript_found = FALSE
        ORDER BY p.priority DESC, e.published_date DESC
        LIMIT ?
        """

        cursor = conn.execute(query, (limit,))
        episodes = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return episodes

    def find_transcript_rss(self, episode: Dict) -> Optional[str]:
        """Try to find transcript in RSS feed content"""
        if not episode.get('rss_feed'):
            return None

        try:
            feed = feedparser.parse(episode['rss_feed'])
            for entry in feed.entries:
                if episode['title'] in entry.title:
                    # Check content for transcript
                    if hasattr(entry, 'content') and entry.content:
                        for content in entry.content:
                            if 'transcript' in content.value.lower() or len(content.value) > 8000:
                                return content.value
                    # Check summary for transcript
                    if hasattr(entry, 'summary') and len(entry.summary) > 8000:
                        return entry.summary
                    break

        except Exception as e:
            print(f"    RSS failed: {e}")

        return None

    def process_episode(self, episode: Dict) -> Dict:
        """Process a single episode for transcript discovery"""
        print(f"Processing: {episode['podcast_name']} - {episode['title'][:50]}...")

        # Try RSS feed only (fastest working method)
        transcript_text = self.find_transcript_rss(episode)

        if transcript_text:
            return {
                'success': True,
                'episode_id': episode['id'],
                'source': 'RSS Feed',
                'transcript_text': transcript_text,
                'character_count': len(transcript_text)
            }
        else:
            return {
                'success': False,
                'episode_id': episode['id'],
                'error': 'No transcript found in RSS feed'
            }

    def save_transcript_to_db(self, result: Dict):
        """Save transcript result to database"""
        conn = sqlite3.connect(self.db_path)

        if result['success']:
            conn.execute("""
                UPDATE episodes SET
                    transcript_found = TRUE,
                    transcript_source = ?,
                    transcript_url = ?,
                    transcript_text = ?,
                    processing_status = 'completed',
                    last_attempt = ?
                WHERE id = ?
            """, (result['source'], '', result['transcript_text'],
                  datetime.now().isoformat(), result['episode_id']))
        else:
            conn.execute("""
                UPDATE episodes SET
                    processing_attempts = processing_attempts + 1,
                    last_attempt = ?,
                    error_message = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), result['error'], result['episode_id']))

        conn.commit()
        conn.close()

    def process_batch(self, limit: int = 50) -> Dict:
        """Process a batch of episodes quickly"""
        print(f"\n🚀 FAST TRANSCRIPT PROCESSOR - RSS ONLY")
        print("=" * 50)
        print(f"Processing {limit} episodes for actual transcripts")
        print()

        episodes = self.get_pending_episodes(limit)
        if not episodes:
            print("✅ No pending episodes found!")
            return {'total': 0, 'successful': 0, 'failed': 0}

        results = []
        successful = 0
        failed = 0

        for i, episode in enumerate(episodes, 1):
            print(f"[{i}/{len(episodes)}] ", end="")

            result = self.process_episode(episode)
            self.save_transcript_to_db(result)
            results.append(result)

            if result['success']:
                successful += 1
                print(f"    ✅ FOUND: {result['character_count']:,} characters")
            else:
                failed += 1
                print(f"    ❌ No transcript")

        print()
        print(f"📊 Batch Results:")
        print(f"   ✅ Successful: {successful}")
        print(f"   ❌ Failed: {failed}")
        print(f"   📝 Total Characters Found: {sum(r.get('character_count', 0) for r in results):,}")

        return {'total': len(episodes), 'successful': successful, 'failed': failed}

if __name__ == "__main__":
    processor = FastTranscriptProcessor()

    # Get current count
    import sqlite3
    conn = sqlite3.connect('podcast_processing.db')
    current_count = conn.execute('SELECT COUNT(*) FROM episodes WHERE transcript_found = 1').fetchone()[0]
    conn.close()

    print(f'📈 Starting from: {current_count} transcripts found')

    # Process in larger batches to reach 100 faster
    target = 100
    while current_count < target:
        # Adjust batch size based on how close we are
        batch_size = min(100, target - current_count + 10)  # Get a few extra

        print(f'\n🎯 Processing {batch_size} episodes to reach {target}...')
        result = processor.process_batch(batch_size)

        # Check actual count
        conn = sqlite3.connect('podcast_processing.db')
        actual_count = conn.execute('SELECT COUNT(*) FROM episodes WHERE transcript_found = 1').fetchone()[0]
        conn.close()

        current_count = actual_count
        print(f'🎯 Progress: {current_count}/{target} transcripts found!')

        if result['successful'] == 0:
            print('⚠️ No transcripts found in this batch')

    print(f'\n🎉 ACHIEVED {current_count} TRANSCRIPTS!')
    print('🚀 Ready to push the rest of the episodes!')