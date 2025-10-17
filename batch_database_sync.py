#!/usr/bin/env python3
"""
Batch Database Sync for OOS Log-Stream System
Syncs log events to database in batches instead of real-time
"""

import sqlite3
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from contextlib import contextmanager
from log_views import get_views

class BatchDatabaseSync:
    """Batch sync of log events to database"""

    def __init__(self, db_path: str = "data/oos.db", log_file: str = "oos.log"):
        self.db_path = db_path
        self.log_file = log_file
        self.views = get_views(log_file)
        self.last_sync_position = 0

    @contextmanager
    def db_operation(self, max_retries=3):
        """Context manager for database operations with retry logic"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA busy_timeout=30000')

        try:
            for attempt in range(max_retries):
                try:
                    yield conn
                    conn.commit()
                    return
                except sqlite3.OperationalError as e:
                    if "database is locked" in str(e) and attempt < max_retries - 1:
                        time.sleep(1)
                    else:
                        raise
                except Exception as e:
                    raise
        finally:
            conn.close()

    def sync_completed_transcripts(self, batch_size: int = 100) -> Dict[str, Any]:
        """Sync completed transcripts to database"""

        # Get completed transcripts from log views
        podcast_status = self.views.podcast_status_view()
        completed_count = podcast_status['completed']

        if completed_count == 0:
            return {"status": "no_new_transcripts", "synced": 0}

        # Read log events to find completed transcripts
        events = self.views._read_log_events()

        synced_count = 0
        transcripts_to_sync = []

        for event in events:
            if (event['event_type'] == 'COMPLETE' and
                event['content_type'] == 'podcast' and
                event['data'].get('transcript_file')):

                # Extract transcript data
                data = event['data']
                transcript_info = {
                    'url': data.get('url', ''),
                    'title': f"Episode from {event['source']}",
                    'content': data.get('transcript_file', ''),
                    'content_type': 'podcast_transcript',
                    'source': event['source'],
                    'word_count': data.get('word_count', 0),
                    'duration': data.get('duration', 0),
                    'processed_at': data.get('completed_at', event['timestamp'].isoformat()),
                    'item_id': event['item_id']
                }

                transcripts_to_sync.append(transcript_info)

                if len(transcripts_to_sync) >= batch_size:
                    break

        # Sync to database
        if transcripts_to_sync:
            synced_count = self._insert_transcripts_batch(transcripts_to_sync)

        return {
            "status": "success",
            "synced": synced_count,
            "remaining": max(0, completed_count - synced_count)
        }

    def _insert_transcripts_batch(self, transcripts: List[Dict[str, Any]]) -> int:
        """Insert a batch of transcripts into database"""

        inserted = 0
        with self.db_operation() as conn:
            cursor = conn.cursor()

            for transcript in transcripts:
                try:
                    # Check if already exists
                    existing = cursor.execute(
                        "SELECT id FROM content WHERE url = ?",
                        (transcript['url'],)
                    ).fetchone()

                    if not existing:
                        # Insert new transcript
                        cursor.execute("""
                            INSERT INTO content
                            (url, title, content, content_type, source, word_count, duration, processed_at, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            transcript['url'],
                            transcript['title'],
                            transcript['content'],
                            transcript['content_type'],
                            transcript['source'],
                            transcript['word_count'],
                            transcript['duration'],
                            transcript['processed_at'],
                            datetime.now().isoformat()
                        ))
                        inserted += 1

                except Exception as e:
                    print(f"Error inserting transcript {transcript['item_id']}: {e}")

        return inserted

    def sync_processing_stats(self) -> Dict[str, Any]:
        """Sync processing statistics to database"""

        # Get stats from log views
        podcast_status = self.views.podcast_status_view()
        error_analysis = self.views.error_analysis_view()
        source_reliability = self.views.source_reliability_view()

        # Create stats record
        stats = {
            'timestamp': datetime.now().isoformat(),
            'podcast_status': podcast_status,
            'error_analysis': error_analysis,
            'source_reliability': source_reliability
        }

        # Store in database
        with self.db_operation() as conn:
            cursor = conn.cursor()

            # Create processing_stats table if doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processing_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    stats_json TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Insert stats
            cursor.execute("""
                INSERT INTO processing_stats (timestamp, stats_json)
                VALUES (?, ?)
            """, (stats['timestamp'], json.dumps(stats)))

        return {"status": "success", "stats": stats}

    def cleanup_old_log_entries(self, days_to_keep: int = 30) -> Dict[str, Any]:
        """Clean up old log entries, keeping recent activity"""

        cutoff_date = datetime.now() - timedelta(days=days_to_keep)

        # Read current log entries
        events = self.views._read_log_events()

        # Keep recent entries and completed/finalized entries
        kept_entries = []
        removed_count = 0

        for event in events:
            if (event['timestamp'] > cutoff_date or
                event['event_type'] in ['COMPLETE', 'FAIL']):
                kept_entries.append(event['raw_line'])
            else:
                removed_count += 1

        # Rewrite log file with kept entries
        if removed_count > 0:
            try:
                with open(self.log_file, 'w', encoding='utf-8') as f:
                    for entry in kept_entries:
                        f.write(entry + '\n')
            except Exception as e:
                return {"status": "error", "error": str(e), "removed": 0}

        return {"status": "success", "removed": removed_count, "kept": len(kept_entries)}

    def full_sync(self) -> Dict[str, Any]:
        """Perform complete sync operation"""

        results = {
            "timestamp": datetime.now().isoformat(),
            "transcripts": self.sync_completed_transcripts(),
            "stats": self.sync_processing_stats(),
            "cleanup": self.cleanup_old_log_entries()
        }

        return results

def main():
    """Test the batch database sync"""
    print("🔄 Testing Batch Database Sync")
    print("=" * 50)

    sync = BatchDatabaseSync()

    # Test sync
    results = sync.full_sync()

    print(f"📊 Sync Results:")
    print(f"  Transcripts: {results['transcripts']}")
    print(f"  Stats: {results['stats']['status']}")
    print(f"  Cleanup: {results['cleanup']['status']}")

    # Test individual components
    print(f"\n📈 Processing Stats:")
    print(json.dumps(sync.sync_processing_stats()['stats'], indent=2))

    print(f"\n✅ Batch sync test completed")

if __name__ == "__main__":
    main()