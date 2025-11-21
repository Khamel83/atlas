#!/usr/bin/env python3
"""
Atlas Data Provider for RelayQ
Provides episode data to RelayQ runners and accepts results back
"""

import json
import sqlite3
import os
from datetime import datetime
from typing import Dict, List, Optional

class AtlasDataProvider:
    def __init__(self):
        self.db_path = "/home/ubuntu/dev/atlas/podcast_processing.db"
        self.ensure_database()

    def ensure_database(self):
        """Make sure database exists and is accessible"""
        if not os.path.exists(self.db_path):
            raise Exception(f"Atlas database not found: {self.db_path}")

    def get_pending_episodes(self, limit: int = 10, podcast_name: str = None) -> List[Dict]:
        """Get pending episodes from Atlas database"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        query = """
        SELECT e.*, p.name as podcast_name
        FROM episodes e
        JOIN podcasts p ON e.podcast_id = p.id
        WHERE e.processing_status = 'pending'
        AND e.transcript_found = FALSE
        """

        params = []
        if podcast_name:
            query += " AND p.name LIKE ?"
            params.append(f"%{podcast_name}%")

        query += " ORDER BY p.priority DESC, e.published_date DESC LIMIT ?"
        params.append(limit)

        cursor = conn.execute(query, params)
        episodes = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return episodes

    def mark_episode_processing(self, episode_id: int, status: str = 'processing'):
        """Mark episode as being processed"""
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "UPDATE episodes SET processing_status = ?, last_attempt = ? WHERE id = ?",
            (status, datetime.now().isoformat(), episode_id)
        )
        conn.commit()
        conn.close()

    def mark_episode_completed(self, episode_id: int, transcript_text: str, source_url: str, quality_score: int = 5):
        """Mark episode as completed with transcript"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            UPDATE episodes SET
                processing_status = 'completed',
                transcript_found = TRUE,
                transcript_text = ?,
                transcript_source = ?,
                transcript_url = ?,
                processing_attempts = COALESCE(processing_attempts, 0) + 1,
                last_attempt = ?
            WHERE id = ?
        """, (transcript_text, "RelayQ Discovery", source_url, quality_score, datetime.now().isoformat(), episode_id))
        conn.commit()
        conn.close()
        conn.close()

    def mark_episode_failed(self, episode_id: int, error_message: str):
        """Mark episode as failed"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            UPDATE episodes SET
                processing_status = 'failed',
                processing_attempts = processing_attempts + 1,
                last_attempt = ?,
                error_message = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), error_message, episode_id))
        conn.close()

    def get_podcast_stats(self) -> Dict:
        """Get statistics about podcasts"""
        conn = sqlite3.connect(self.db_path)

        stats = {
            'total_podcasts': conn.execute("SELECT COUNT(*) FROM podcasts").fetchone()[0],
            'total_episodes': conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0],
            'pending_episodes': conn.execute("SELECT COUNT(*) FROM episodes WHERE processing_status = 'pending'").fetchone()[0],
            'processing_episodes': conn.execute("SELECT COUNT(*) FROM episodes WHERE processing_status = 'processing'").fetchone()[0],
            'completed_episodes': conn.execute("SELECT COUNT(*) FROM episodes WHERE transcript_found = 1").fetchone()[0],
            'failed_episodes': conn.execute("SELECT COUNT(*) FROM episodes WHERE processing_status = 'failed'").fetchone()[0]
        }

        conn.close()
        return stats

# CLI interface for RelayQ runners
if __name__ == "__main__":
    import sys

    provider = AtlasDataProvider()
    command = sys.argv[1] if len(sys.argv) > 1 else "help"

    if command == "get_episodes":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        podcast_name = sys.argv[3] if len(sys.argv) > 3 else None

        episodes = provider.get_pending_episodes(limit, podcast_name)
        print(json.dumps({
            "episodes": episodes,
            "count": len(episodes),
            "podcast_filter": podcast_name
        }, indent=2))

    elif command == "start_processing":
        episode_id = int(sys.argv[2])
        provider.mark_episode_processing(episode_id)
        print(json.dumps({
            "status": "processing_started",
            "episode_id": episode_id,
            "timestamp": datetime.now().isoformat()
        }, indent=2))

    elif command == "complete_episode":
        episode_id = int(sys.argv[2])
        transcript_text = sys.argv[3] if len(sys.argv) > 3 else ""
        source_url = sys.argv[4] if len(sys.argv) > 4 else ""

        provider.mark_episode_completed(episode_id, transcript_text, source_url)
        print(json.dumps({
            "status": "completed",
            "episode_id": episode_id,
            "timestamp": datetime.now().isoformat()
        }, indent=2))

    elif command == "fail_episode":
        episode_id = int(sys.argv[2])
        error_message = sys.argv[3] if len(sys.argv) > 3 else "Unknown error"

        provider.mark_episode_failed(episode_id, error_message)
        print(json.dumps({
            "status": "failed",
            "episode_id": episode_id,
            "error": error_message,
            "timestamp": datetime.now().isoformat()
        }, indent=2))

    elif command == "stats":
        stats = provider.get_podcast_stats()
        print(json.dumps(stats, indent=2))

    else:
        print("Atlas Data Provider for RelayQ")
        print("Commands:")
        print("  python3 atlas_data_provider.py get_episodes [limit] [podcast_filter]")
        print("  python3 atlas_data_provider.py start_processing <episode_id>")
        print("  python3 atlas_data_provider.py complete_episode <episode_id> <transcript> <source>")
        print("  python3 atlas_data_provider.py fail_episode <episode_id> <error>")
        print("  python3 atlas_data_provider.py stats")