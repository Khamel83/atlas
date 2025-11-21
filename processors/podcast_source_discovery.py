#!/usr/bin/env python3
"""
Podcast Source Discovery System

Strategy: Pick one episode per podcast and systematically test all transcript sources
until we find which source works for each podcast. Once we find a working source
for a podcast, we can batch process all episodes from that podcast using that source.

This is much more efficient than testing every source for every episode.
"""

import sqlite3
import pandas as pd
import json
from datetime import datetime
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PodcastSourceDiscovery:
    """Manages the systematic discovery of transcript sources per podcast"""

    def __init__(self, db_path: str = "podcast_processing.db"):
        self.db_path = db_path

    def get_test_episodes_per_podcast(self) -> List[Dict]:
        """Get one test episode per podcast for source discovery"""

        conn = sqlite3.connect(self.db_path)

        # Get one episode per podcast (preferably a recent one)
        query = """
        SELECT
            p.name as podcast_name,
            p.id as podcast_id,
            p.target_transcripts,
            e.id as episode_id,
            e.title as episode_title,
            q.id as queue_id,
            q.priority,
            ROW_NUMBER() OVER (PARTITION BY p.id ORDER BY q.id) as episode_rank
        FROM podcasts p
        JOIN episodes e ON p.id = e.podcast_id
        JOIN processing_queue q ON e.id = q.episode_id
        WHERE q.status = 'queued'
        ORDER BY p.id, q.id
        """

        df = pd.read_sql_query(query, conn)
        conn.close()

        # Get first episode per podcast
        test_episodes = df[df['episode_rank'] == 1].to_dict('records')

        logger.info(f"Selected {len(test_episodes)} test episodes across {len(test_episodes)} podcasts")

        return test_episodes

    def create_source_discovery_queue(self) -> str:
        """Create a focused queue for source discovery"""

        test_episodes = self.get_test_episodes_per_podcast()

        # Prioritize by target transcripts (high-value podcasts first)
        test_episodes.sort(key=lambda x: x['target_transcripts'], reverse=True)

        discovery_queue = {
            'created_at': datetime.now().isoformat(),
            'total_podcasts': len(test_episodes),
            'strategy': 'one_episode_per_podcast_source_discovery',
            'test_episodes': test_episodes
        }

        # Save the discovery queue
        filename = f"source_discovery_queue_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(discovery_queue, f, indent=2)

        logger.info(f"Source discovery queue saved to: {filename}")

        # Show summary
        print("=== PODCAST SOURCE DISCOVERY QUEUE ===")
        print(f"Total podcasts to test: {len(test_episodes)}")
        print(f"Strategy: Test one episode per podcast to identify working sources")
        print()

        print("=== TOP 20 PRIORITY PODCASTS FOR TESTING ===")
        for i, episode in enumerate(test_episodes[:20], 1):
            print(f"{i:2d}. {episode['podcast_name']} (target: {episode['target_transcripts']})")
            print(f"    Test episode: {episode['episode_title'][:60]}...")
            print(f"    Queue UID: {episode['queue_id']}")
            print()

        if len(test_episodes) > 20:
            print(f"... and {len(test_episodes) - 20} more podcasts")

        return filename

    def show_available_transcript_sources(self):
        """Show what transcript sources we have available"""

        print("\n=== AVAILABLE TRANSCRIPT SOURCES ===")
        print("Based on transcript_scrapers.py, we have these sources:")
        print("1. TapeSearch (tapesearch.com)")
        print("2. PodScripts (podscripts.com)")
        print("3. [We should add more sources like:]")
        print("   - Rev.com")
        print("   - Otter.ai")
        print("   - AssemblyAI")
        print("   - Podcast websites directly")
        print("   - YouTube (for video podcasts)")

        print("\n=== NEXT STEPS ===")
        print("1. Test each source systematically against our test episodes")
        print("2. Build a mapping: podcast -> working_source")
        print("3. Batch process all episodes per podcast using their working source")

def main():
    """Run the source discovery setup"""

    discovery = PodcastSourceDiscovery()

    # Create the discovery queue
    queue_file = discovery.create_source_discovery_queue()

    # Show available sources
    discovery.show_available_transcript_sources()

    return queue_file

if __name__ == "__main__":
    queue_file = main()