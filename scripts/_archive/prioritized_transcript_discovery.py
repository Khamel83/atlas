#!/usr/bin/env python3
"""
Prioritized Transcript Discovery

Focuses on high-value episodes from harvested database, not bulk random processing.
Processes episodes by priority configuration, avoiding 3270+ episode nonsense.

Usage:
    python scripts/prioritized_transcript_discovery.py
    python scripts/prioritized_transcript_discovery.py --podcast "Lex Fridman Podcast" --limit 50
"""

import os
import sys
import csv
import sqlite3
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.database_config import get_database_path, get_database_connection
from transcript_orchestrator import TranscriptOrchestrator

class PrioritizedTranscriptDiscovery:
    """Focus on high-value episodes from harvested database"""

    def __init__(self):
        self.db_path = get_database_path()
        self.orchestrator = TranscriptOrchestrator()

    def load_podcast_priorities(self) -> Dict[str, int]:
        """Load podcast priorities from config"""
        config_path = Path(__file__).parent.parent / "config" / "podcasts_prioritized_cleaned.csv"
        priorities = {}

        with open(config_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                podcast_name = row['Podcast Name'].strip()
                # Use Count as priority limit (4 = process 4 episodes, not 925)
                count = int(row.get('Count', 0))
                priorities[podcast_name] = count

        return priorities

    def get_prioritized_episodes(self, podcast_name: Optional[str] = None, limit: Optional[int] = None) -> List[Tuple]:
        """Get episodes by priority configuration"""
        conn = get_database_connection()
        priorities = self.load_podcast_priorities()

        try:
            cursor = conn.cursor()

            if podcast_name:
                # Single podcast with limit
                priority_limit = priorities.get(podcast_name, limit or 10)
                actual_limit = min(priority_limit, limit) if limit else priority_limit

                cursor.execute('''
                    SELECT id, podcast_name, title, audio_url, published_date
                    FROM podcast_episodes
                    WHERE podcast_name = ?
                    AND transcript_attempted = 0
                    ORDER BY published_date DESC
                    LIMIT ?
                ''', (podcast_name, actual_limit))

            else:
                # All podcasts by priority
                episodes = []
                for podcast, max_count in priorities.items():
                    if max_count == 0:
                        continue  # Skip excluded podcasts

                    # Reasonable limit - avoid 3270 episode nonsense
                    reasonable_limit = min(max_count, 50)  # Even faster processing

                    cursor.execute('''
                        SELECT id, podcast_name, title, audio_url, published_date
                        FROM podcast_episodes
                        WHERE podcast_name = ?
                        AND transcript_attempted = 0
                        ORDER BY published_date DESC
                        LIMIT ?
                    ''', (podcast, reasonable_limit))

                    episodes.extend(cursor.fetchall())

                return episodes

            return cursor.fetchall()

        finally:
            conn.close()

    def process_episode(self, episode_id: int, podcast_name: str, title: str, audio_url: str) -> bool:
        """Process single episode for transcript discovery"""
        print(f"🔍 Processing: {podcast_name} - {title[:50]}...")

        # Try transcript discovery using the correct method
        transcript = self.orchestrator.find_transcript(
            podcast_name=podcast_name,
            episode_title=title,
            episode_url=audio_url
        )

        success = transcript is not None

        # Update database
        conn = get_database_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE podcast_episodes
                SET transcript_attempted = 1, transcript_found = ?
                WHERE id = ?
            ''', (1 if success else 0, episode_id))
            conn.commit()
        finally:
            conn.close()

        if success:
            print(f"   ✅ Transcript found!")
        else:
            print(f"   ❌ No transcript found")

        return success

    def run_prioritized_discovery(self, podcast_name: Optional[str] = None, limit: Optional[int] = None) -> Dict[str, int]:
        """Run prioritized transcript discovery"""
        episodes = self.get_prioritized_episodes(podcast_name, limit)

        if not episodes:
            print("📭 No episodes to process")
            return {}

        print(f"🎯 Processing {len(episodes)} prioritized episodes")
        print("=" * 60)

        results = {"processed": 0, "found": 0, "failed": 0}

        for episode_id, podcast_name, title, audio_url, published_date in episodes:
            try:
                success = self.process_episode(episode_id, podcast_name, title, audio_url)

                results["processed"] += 1
                if success:
                    results["found"] += 1
                else:
                    results["failed"] += 1

            except Exception as e:
                print(f"   💥 Error processing episode: {e}")
                results["failed"] += 1
                continue

        print("=" * 60)
        print(f"📊 Results: {results['processed']} processed, {results['found']} found, {results['failed']} failed")
        return results

    def get_discovery_stats(self) -> Dict[str, int]:
        """Get transcript discovery statistics"""
        conn = get_database_connection()

        try:
            cursor = conn.cursor()

            # Total episodes
            cursor.execute('SELECT COUNT(*) FROM podcast_episodes')
            total = cursor.fetchone()[0]

            # Attempted
            cursor.execute('SELECT COUNT(*) FROM podcast_episodes WHERE transcript_attempted = 1')
            attempted = cursor.fetchone()[0]

            # Found
            cursor.execute('SELECT COUNT(*) FROM podcast_episodes WHERE transcript_found = 1')
            found = cursor.fetchone()[0]

            return {
                'total_episodes': total,
                'attempted': attempted,
                'found': found,
                'remaining': total - attempted
            }

        finally:
            conn.close()

def main():
    parser = argparse.ArgumentParser(description='Prioritized Transcript Discovery')
    parser.add_argument('--podcast', help='Process specific podcast')
    parser.add_argument('--limit', type=int, help='Limit episodes per podcast')
    parser.add_argument('--stats', action='store_true', help='Show statistics')
    parser.add_argument('--continuous', action='store_true', help='Run continuously in background')

    args = parser.parse_args()

    discovery = PrioritizedTranscriptDiscovery()

    if args.stats:
        stats = discovery.get_discovery_stats()
        print("📊 Transcript Discovery Statistics:")
        print(f"   Total episodes: {stats['total_episodes']:,}")
        print(f"   Attempted: {stats['attempted']:,}")
        print(f"   Found: {stats['found']:,}")
        print(f"   Remaining: {stats['remaining']:,}")
        return

    if args.continuous:
        print("🔄 Running continuous prioritized discovery...")
        print("Press Ctrl+C to stop")

        import time
        try:
            while True:
                # Process in small batches to avoid overwhelming
                results = discovery.run_prioritized_discovery(limit=5)
                if results["processed"] == 0:
                    print("⏳ All priority episodes processed, waiting...")
                    time.sleep(300)  # Wait 5 minutes
                else:
                    time.sleep(30)  # Short break between batches
        except KeyboardInterrupt:
            print("\n🛑 Stopping continuous discovery")
    else:
        discovery.run_prioritized_discovery(args.podcast, args.limit)

if __name__ == "__main__":
    main()