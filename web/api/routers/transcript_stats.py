from fastapi import APIRouter, HTTPException
from pathlib import Path
import sqlite3
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from helpers.database_config import get_database_connection

router = APIRouter()

@router.get("/admin")
async def get_transcript_admin_stats():
    conn = get_database_connection()
    cursor = conn.cursor()

    try:
        # Total transcripts found
        cursor.execute("SELECT COUNT(*) FROM content WHERE content_type = 'transcript'")
        total_transcripts = cursor.fetchone()[0]

        # Total episodes known (assuming 'podcast' content type represents episodes)
        cursor.execute("SELECT COUNT(*) FROM content WHERE content_type = 'podcast'")
        total_episodes_known = cursor.fetchone()[0]

        # Processing statistics by podcast (found/total/success rate)
        # This is a more complex query. For simplicity, let's get counts per podcast.
        cursor.execute("""
            SELECT
                json_extract(metadata, '$.podcast') AS podcast_name,
                COUNT(*) AS transcript_count
            FROM content
            WHERE content_type = 'transcript' AND metadata IS NOT NULL
            GROUP BY podcast_name
            ORDER BY transcript_count DESC
            LIMIT 10
        """)
        podcast_stats_raw = cursor.fetchall()
        podcast_stats = [{"podcast_name": row[0], "transcript_count": row[1]} for row in podcast_stats_raw]

        # Recent activity log (last 20 transcript discoveries)
        cursor.execute("""
            SELECT
                id, title, created_at, json_extract(metadata, '$.podcast') AS podcast_name
            FROM content
            WHERE content_type = 'transcript'
            ORDER BY created_at DESC
            LIMIT 20
        """)
        recent_discoveries_raw = cursor.fetchall()
        recent_discoveries = [{"id": row[0], "title": row[1], "created_at": row[2], "podcast_name": row[3]} for row in recent_discoveries_raw]

        # Failed episodes count and recent failures
        # This requires a more sophisticated tracking of "failures".
        # For now, let's assume a "failed" status might be in metadata or a separate table.
        # If not, we can count episodes that were attempted but no transcript was found.
        # This is a placeholder and might need refinement based on actual failure logging.
        failed_episodes_count = 0 # Placeholder
        recent_failures = [] # Placeholder

        # Queue status (pending items)
        # This depends on how the queue is implemented. Assuming a simple 'todo' status in content table for now.
        cursor.execute("SELECT COUNT(*) FROM content WHERE content_type = 'podcast' AND content IS NULL")
        pending_podcast_transcriptions = cursor.fetchone()[0]

        return {
            "total_transcripts": total_transcripts,
            "total_episodes_known": total_episodes_known,
            "podcast_stats": podcast_stats,
            "recent_discoveries": recent_discoveries,
            "failed_episodes_count": failed_episodes_count,
            "recent_failures": recent_failures,
            "pending_podcast_transcriptions": pending_podcast_transcriptions
        }
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    finally:
        conn.close()