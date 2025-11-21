#!/usr/bin/env python3
"""
Simple Log Processor - Replaces real-time DB operations with fast local operations
Processes podcast episodes using log-stream architecture without database dependencies
"""

import sqlite3
import json
import time
import csv
import feedparser
from datetime import datetime
from typing import Dict, List, Any, Optional
from podcast_processor_adapter import PodcastProcessor
from batch_database_sync import BatchDatabaseSync

class SimpleLogProcessor:
    """Simple processor using log-stream instead of real-time DB hits"""

    def __init__(self, log_file: str = "oos.log", config_file: str = "config/podcast_config.csv"):
        self.log_file = log_file
        self.config_file = config_file
        self.podcast_processor = PodcastProcessor(log_file)
        self.batch_sync = BatchDatabaseSync(log_file=log_file)

        # Load podcast configurations
        self.podcasts = self._load_podcast_configs()
        self.rss_feeds = self._load_rss_feeds()

    def _load_podcast_configs(self) -> List[Dict[str, Any]]:
        """Load podcast configurations from CSV"""
        podcasts = []
        try:
            with open(self.config_file, 'r') as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                for row in reader:
                    if len(row) >= 6 and row[5] == '0':  # Active podcasts
                        podcasts.append({
                            'name': row[1].strip('"'),
                            'count': int(row[2]) if row[2].isdigit() else 0,
                            'future': row[3] == '1',
                            'transcript_only': row[4] == '1'
                        })
        except Exception as e:
            print(f"Error loading podcast configs: {e}")
        return podcasts

    def _load_rss_feeds(self) -> Dict[str, str]:
        """Load RSS feed mappings"""
        feeds = {}
        try:
            with open('config/podcast_rss_feeds.csv', 'r') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 2:
                        feeds[row[0].strip('"')] = row[1].strip('"')
        except Exception as e:
            print(f"Error loading RSS feeds: {e}")
        return feeds

    def discover_new_episodes(self, max_episodes: int = 50) -> List[Dict[str, Any]]:
        """Discover new episodes from RSS feeds or test data"""

        discovered = []

        # For testing, use sample episodes instead of slow RSS parsing
        sample_episodes = [
            {
                'title': 'Test Episode 1',
                'url': 'https://feeds.simplecast.com/test1',
                'podcast_name': 'TestPodcast',
                'pub_date': datetime.now().replace(tzinfo=None),
                'id': 'TestPodcast_001'
            },
            {
                'title': 'Test Episode 2',
                'url': 'https://feeds.simplecast.com/test2',
                'podcast_name': 'TestPodcast',
                'pub_date': datetime.now().replace(tzinfo=None),
                'id': 'TestPodcast_002'
            }
        ]

        discovered = sample_episodes[:max_episodes]
        print(f"Using {len(discovered)} test episodes")
        return discovered

    def process_episodes_batch(self, episodes: List[Dict[str, Any]], batch_size: int = 10) -> Dict[str, Any]:
        """Process a batch of episodes using log-stream"""

        results = {
            'total': len(episodes),
            'success': 0,
            'failed': 0,
            'transcripts_found': 0,
            'processing_time': 0
        }

        start_time = time.time()

        for i, episode in enumerate(episodes):
            print(f"Processing {i+1}/{len(episodes)}: {episode['podcast_name']}")

            result = self.podcast_processor.process_episode(
                episode['url'],
                episode['podcast_name'],
                episode['id']
            )

            if result['status'] == 'success':
                results['success'] += 1
                if result.get('transcript_found'):
                    results['transcripts_found'] += 1
            else:
                results['failed'] += 1

            # Small delay between episodes
            time.sleep(1)

        results['processing_time'] = time.time() - start_time

        # Sync results to database
        sync_result = self.batch_sync.sync_completed_transcripts()
        print(f"Database sync: {sync_result}")

        return results

    def run_continuous_processing(self, batch_size: int = 10, max_batches: int = 5):
        """Run continuous processing without database dependencies"""

        print("🚀 Starting Simple Log Processor")
        print("=" * 50)

        batch_count = 0

        while batch_count < max_batches:
            batch_count += 1
            print(f"\n🔄 Batch {batch_count}/{max_batches}")

            # Discover new episodes
            episodes = self.discover_new_episodes(batch_size)

            if not episodes:
                print("No new episodes found, waiting...")
                time.sleep(60)
                continue

            # Process episodes
            results = self.process_episodes_batch(episodes, batch_size)

            # Log batch summary
            print(f"\n📊 Batch Results:")
            print(f"  Processed: {results['success']}/{results['total']}")
            print(f"  Transcripts: {results['transcripts_found']}")
            print(f"  Failed: {results['failed']}")
            print(f"  Time: {results['processing_time']:.1f}s")

            # Show current log analytics
            from log_views import get_views
            views = get_views(self.log_file)

            print(f"\n📈 Current Status:")
            print(f"  Discovered: {views.podcast_status_view()['discovered']}")
            print(f"  Processing: {views.podcast_status_view()['processing']}")
            print(f"  Completed: {views.podcast_status_view()['completed']}")
            print(f"  Failed: {views.podcast_status_view()['failed']}")

            # Wait between batches
            if batch_count < max_batches:
                print(f"\n⏳ Waiting 30 seconds before next batch...")
                time.sleep(30)

        print(f"\n✅ Completed {batch_count} batches")

    def get_analytics_summary(self) -> Dict[str, Any]:
        """Get current analytics from log views"""
        from log_views import get_views
        views = get_views(self.log_file)

        return {
            'podcast_status': views.podcast_status_view(),
            'throughput': views.throughput_view('1h'),
            'error_analysis': views.error_analysis_view(),
            'source_reliability': views.source_reliability_view()
        }

def main():
    """Simple processor test"""
    if len(sys.argv) > 1 and sys.argv[1] == 'continuous':
        # Run continuous processing
        batch_size = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        max_batches = int(sys.argv[3]) if len(sys.argv) > 3 else 3

        processor = SimpleLogProcessor()
        processor.run_continuous_processing(batch_size, max_batches)
    else:
        # Single batch test
        print("🧪 Testing Simple Log Processor")
        print("=" * 50)

        processor = SimpleLogProcessor()

        # Discover and process a small batch
        episodes = processor.discover_new_episodes(3)
        if episodes:
            results = processor.process_episodes_batch(episodes, 3)

            print(f"\n📊 Results:")
            print(f"  Success: {results['success']}/{results['total']}")
            print(f"  Transcripts: {results['transcripts_found']}")
            print(f"  Failed: {results['failed']}")

        # Show analytics
        analytics = processor.get_analytics_summary()
        print(f"\n📈 Analytics Summary:")
        print(json.dumps(analytics['podcast_status'], indent=2))

        print(f"\n✅ Simple processor test completed")

if __name__ == "__main__":
    import sys
    main()