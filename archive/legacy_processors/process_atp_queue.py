#!/usr/bin/env python3
"""
Process ATP Episodes from Processing Queue

This script processes ATP episodes from the processing queue using the new
transcript lookup workflow with integrated ATP scraper.
"""

import sqlite3
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add the helpers directory to the path
sys.path.append('/home/ubuntu/dev/atlas')
sys.path.append('/home/ubuntu/dev/atlas/helpers')

from helpers.podcast_transcript_lookup import lookup_podcast_transcript

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_atp_episodes_from_queue() -> List[Dict[str, Any]]:
    """Get all ATP episodes from the processing queue"""

    db_path = "/home/ubuntu/dev/atlas/output/processing_queue.db"

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get all ATP episodes
        cursor.execute("""
            SELECT podcast_name, episode_title, episode_url, status, id
            FROM processing_queue
            WHERE podcast_name LIKE '%Accidental%' OR podcast_name LIKE '%ATP%'
            ORDER BY episode_title
        """)

        episodes = []
        for row in cursor.fetchall():
            episodes.append({
                'podcast_name': row[0],
                'episode_title': row[1],
                'episode_url': row[2],
                'status': row[3],
                'queue_id': row[4]
            })

        conn.close()
        return episodes

    except Exception as e:
        logger.error(f"Failed to get ATP episodes from queue: {e}")
        return []

def update_queue_status(queue_id: str, status: str, result_message: str = None):
    """Update the status of an episode in the processing queue"""

    db_path = "/home/ubuntu/dev/atlas/output/processing_queue.db"

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        if result_message:
            cursor.execute("""
                UPDATE processing_queue
                SET status = ?, result = ?
                WHERE id = ?
            """, (status, result_message, queue_id))
        else:
            cursor.execute("""
                UPDATE processing_queue
                SET status = ?
                WHERE id = ?
            """, (status, queue_id))

        conn.commit()
        conn.close()

        logger.info(f"Updated queue item {queue_id} to status: {status}")

    except Exception as e:
        logger.error(f"Failed to update queue status for {queue_id}: {e}")

def process_atp_episodes():
    """Process ATP episodes through the new transcript lookup workflow"""

    logger.info("🎙️ Starting ATP episode processing...")

    # Get ATP episodes from queue
    episodes = get_atp_episodes_from_queue()

    if not episodes:
        logger.warning("No ATP episodes found in processing queue")
        return

    logger.info(f"Found {len(episodes)} ATP episodes to process")

    results = {
        'total': len(episodes),
        'successful': 0,
        'failed': 0,
        'details': []
    }

    # Process each episode
    for i, episode in enumerate(episodes, 1):
        podcast_name = episode['podcast_name']
        episode_title = episode['episode_title']
        episode_url = episode['episode_url']
        queue_id = episode['queue_id']

        logger.info(f"[{i}/{len(episodes)}] Processing: {episode_title}")

        try:
            # Mark as processing
            update_queue_status(queue_id, "processing")

            # Use the new transcript lookup workflow
            result = lookup_podcast_transcript(podcast_name, episode_title, episode_url)

            if result.success:
                logger.info(f"✅ Success: {episode_title}")
                logger.info(f"   Source: {result.source}")
                logger.info(f"   Transcript length: {len(result.transcript) if result.transcript else 0} chars")

                # Update queue status to completed
                update_queue_status(
                    queue_id,
                    "completed",
                    f"Transcript found via {result.source}"
                )

                results['successful'] += 1
                results['details'].append({
                    'episode': episode_title,
                    'success': True,
                    'source': result.source,
                    'transcript_length': len(result.transcript) if result.transcript else 0
                })

            else:
                logger.warning(f"❌ Failed: {episode_title}")
                logger.warning(f"   Error: {result.error_message}")

                # Update queue status to failed
                update_queue_status(
                    queue_id,
                    "failed",
                    f"Transcript lookup failed: {result.error_message}"
                )

                results['failed'] += 1
                results['details'].append({
                    'episode': episode_title,
                    'success': False,
                    'error': result.error_message
                })

        except Exception as e:
            logger.error(f"❌ Exception processing {episode_title}: {e}")

            # Update queue status to failed
            update_queue_status(
                queue_id,
                "failed",
                f"Processing exception: {str(e)}"
            )

            results['failed'] += 1
            results['details'].append({
                'episode': episode_title,
                'success': False,
                'error': str(e)
            })

    # Summary
    logger.info("🎯 Processing Complete!")
    logger.info(f"Total episodes: {results['total']}")
    logger.info(f"Successful: {results['successful']}")
    logger.info(f"Failed: {results['failed']}")
    logger.info(f"Success rate: {results['successful']/results['total']*100:.1f}%")

    # Show successful episodes
    successful_episodes = [d for d in results['details'] if d['success']]
    if successful_episodes:
        logger.info("\n✅ Successfully processed episodes:")
        for episode in successful_episodes:
            logger.info(f"  • {episode['episode']} -> {episode['source']} ({episode['transcript_length']} chars)")

    # Show failed episodes
    failed_episodes = [d for d in results['details'] if not d['success']]
    if failed_episodes:
        logger.info("\n❌ Failed episodes:")
        for episode in failed_episodes:
            logger.info(f"  • {episode['episode']} -> {episode['error']}")

    return results

def main():
    """Main execution function"""
    try:
        results = process_atp_episodes()

        if results and results['successful'] > 0:
            print(f"\n🎉 Successfully processed {results['successful']} ATP episodes!")
            print("These episodes should now have transcripts from catatp.fm instead of being queued for audio transcription.")
        else:
            print("\n⚠️ No episodes were successfully processed.")

    except Exception as e:
        logger.error(f"Script execution failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()