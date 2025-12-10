#!/usr/bin/env python3
"""
Test ATP transcript integration workflow
"""

import sqlite3
import sys
import os
sys.path.append('/home/ubuntu/dev/atlas')

from helpers.podcast_transcript_lookup import PodcastTranscriptLookup

def test_atp_episode():
    """Test processing one ATP episode"""

    # Get one ATP episode from queue
    conn = sqlite3.connect('data/atlas.db')
    cursor = conn.cursor()

    result = cursor.execute("""
        SELECT episode_url, podcast_name, episode_title
        FROM episode_queue
        WHERE (podcast_name LIKE '%Accidental%' OR podcast_name LIKE '%ATP%')
        AND status = 'pending'
        LIMIT 1
    """).fetchone()

    if not result:
        print("No ATP episodes found in queue")
        return False

    episode_url, podcast_name, episode_title = result
    print(f"Testing ATP episode: {podcast_name} - {episode_title}")
    print(f"URL: {episode_url}")

    # Test the transcript lookup
    lookup = PodcastTranscriptLookup()

    print("\n--- Starting transcript lookup ---")
    result = lookup.lookup_transcript(podcast_name, episode_title, episode_url)

    print(f"\nResult success: {result.success}")
    if result.success:
        print(f"Source: {result.source}")
        print(f"Transcript length: {len(result.transcript)} characters")
        print(f"First 200 chars: {result.transcript[:200]}...")

        # Update episode status to found
        cursor.execute("""
            UPDATE episode_queue
            SET status = 'found', processed_at = datetime('now')
            WHERE episode_url = ? AND podcast_name = ?
        """, (episode_url, podcast_name))
        conn.commit()
        print(f"✅ Updated episode status to 'found'")

    else:
        print(f"❌ Failed: {result.error_message}")

    conn.close()
    return result.success

if __name__ == "__main__":
    print("🎯 Testing ATP Integration")
    print("=" * 50)

    success = test_atp_episode()

    print("\n" + "=" * 50)
    if success:
        print("✅ ATP integration test PASSED")
    else:
        print("❌ ATP integration test FAILED")