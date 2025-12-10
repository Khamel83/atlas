#!/usr/bin/env python3
"""
Retry failed episodes with improved extraction patterns
"""

import sys
import sqlite3
import json
import logging
from datetime import datetime
from single_episode_processor import process_episode

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/retry_failed.log'),
        logging.StreamHandler()
    ]
)

def retry_failed_episodes(batch_size=50):
    """Retry failed episodes with improved extraction patterns"""

    conn = sqlite3.connect('data/atlas.db')
    cursor = conn.cursor()

    try:
        # Get episodes to retry (prioritize pending, then not_found, then error)
        cursor.execute("""
            SELECT episode_url, podcast_name, status
            FROM episode_queue
            WHERE status IN ('pending', 'not_found', 'error')
            ORDER BY
                CASE status
                    WHEN 'pending' THEN 1
                    WHEN 'not_found' THEN 2
                    WHEN 'error' THEN 3
                END,
                created_at ASC
            LIMIT ?
        """, (batch_size,))

        episodes = cursor.fetchall()

        if not episodes:
            logging.info("No episodes to retry")
            return 0

        logging.info(f"Retrying {len(episodes)} episodes...")

        success_count = 0

        for i, (episode_url, podcast_name, current_status) in enumerate(episodes, 1):
            logging.info(f"Processing {i}/{len(episodes)}: {podcast_name}")

            try:
                result = process_episode(i, episode_url, podcast_name)

                if result:
                    # Update status to found
                    cursor.execute("""
                        UPDATE episode_queue
                        SET status = 'found', updated_at = ?
                        WHERE episode_url = ?
                    """, (datetime.now().isoformat(), episode_url))
                    success_count += 1
                    logging.info(f"✓ Successfully extracted transcript for {podcast_name}")
                else:
                    # Keep current status but update timestamp
                    cursor.execute("""
                        UPDATE episode_queue
                        SET updated_at = ?
                        WHERE episode_url = ?
                    """, (datetime.now().isoformat(), episode_url))
                    logging.info(f"✗ No transcript found for {podcast_name}")

                conn.commit()

            except Exception as e:
                logging.error(f"Error processing {episode_url}: {e}")

                # Mark as error if failed
                cursor.execute("""
                    UPDATE episode_queue
                    SET status = 'error', updated_at = ?
                    WHERE episode_url = ?
                """, (datetime.now().isoformat(), episode_url))
                conn.commit()

        logging.info(f"Retry complete: {success_count}/{len(episodes)} successful")
        return success_count

    except Exception as e:
        logging.error(f"Error in retry_failed_episodes: {e}")
        return 0
    finally:
        conn.close()

def get_queue_stats():
    """Get current queue statistics"""
    conn = sqlite3.connect('data/atlas.db')
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM episode_queue
            GROUP BY status
            ORDER BY count DESC
        """)

        stats = dict(cursor.fetchall())

        cursor.execute("SELECT COUNT(*) FROM content WHERE content_type = 'podcast_transcript'")
        total_transcripts = cursor.fetchone()[0]

        logging.info(f"Queue Stats: {stats}")
        logging.info(f"Total Transcripts: {total_transcripts}")

        return stats, total_transcripts

    finally:
        conn.close()

if __name__ == "__main__":
    import os

    # Ensure logs directory exists
    os.makedirs('logs', exist_ok=True)

    # Show initial stats
    logging.info("=== Starting Retry Process ===")
    get_queue_stats()

    # Retry episodes
    batch_size = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    success_count = retry_failed_episodes(batch_size)

    # Show final stats
    logging.info("=== Retry Process Complete ===")
    get_queue_stats()

    logging.info(f"Successfully extracted {success_count} new transcripts in this batch")