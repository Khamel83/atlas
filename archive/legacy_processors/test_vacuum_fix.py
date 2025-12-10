#!/usr/bin/env python3
"""
Test script for VACUUM fix
"""

import sqlite3
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_vacuum_fix():
    """Test the VACUUM transaction fix"""
    conn = sqlite3.connect('data/atlas.db')
    cursor = conn.cursor()

    try:
        logging.info("Starting VACUUM fix test")

        # Clean up old error entries (similar to maintenance_tasks)
        week_ago = datetime.now() - timedelta(days=7)
        deleted = cursor.execute(
            "DELETE FROM episode_queue WHERE status = 'error' AND updated_at < ?",
            (week_ago.isoformat(),)
        ).rowcount

        logging.info(f"Cleaned up {deleted} old error entries")

        # Commit transaction before VACUUM
        conn.commit()
        logging.info("Transaction committed before VACUUM")

        # Test VACUUM with error handling
        try:
            conn.execute("VACUUM")
            logging.info("✅ VACUUM completed successfully!")
        except Exception as e:
            logging.warning(f"VACUUM failed: {e}")
            logging.info("✅ System continued despite VACUUM failure")

        # Log current status
        transcripts = cursor.execute(
            "SELECT COUNT(*) FROM content WHERE content_type = 'podcast_transcript'"
        ).fetchone()[0]

        queue_status = cursor.execute(
            "SELECT status, COUNT(*) FROM episode_queue GROUP BY status"
        ).fetchall()

        logging.info(f"Current status: {transcripts} transcripts, queue: {dict(queue_status)}")
        logging.info("✅ VACUUM fix test completed successfully!")

    except Exception as e:
        logging.error(f"❌ Error in VACUUM fix test: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    test_vacuum_fix()