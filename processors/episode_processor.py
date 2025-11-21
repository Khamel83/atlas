#!/usr/bin/env python3
"""
Episode Processor - Phase 2 Implementation
Systematically processes episodes from the queue with transcript extraction
"""

import sqlite3
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import random
import json

class EpisodeProcessor:
    def __init__(self):
        self.conn = sqlite3.connect('data/atlas.db')
        self.cursor = self.conn.cursor()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

        # Load existing sources cache
        try:
            with open('config/podcast_sources_cache.json', 'r') as f:
                self.sources_cache = json.load(f)
        except:
            self.sources_cache = {}

    def get_next_episode(self):
        """Get next pending episode from queue"""
        episode = self.cursor.execute("""
            SELECT * FROM episode_queue
            WHERE status = 'pending'
            ORDER BY created_at ASC
            LIMIT 1
        """).fetchone()

        if episode:
            return {
                'id': episode[0],
                'podcast_name': episode[1],
                'episode_title': episode[2],
                'episode_url': episode[3],
                'rss_url': episode[4]
            }
        return None

    def update_episode_status(self, episode_id, status, transcript_source=None, transcript_url=None, content_length=None, quality_score=None):
        """Update episode status in queue"""
        self.cursor.execute("""
            UPDATE episode_queue
            SET status = ?, transcript_source = ?, transcript_url = ?,
                content_length = ?, quality_score = ?, updated_at = ?
            WHERE id = ?
        """, (status, transcript_source, transcript_url, content_length, quality_score, datetime.now().isoformat(), episode_id))
        self.conn.commit()

    def extract_transcript_strategies(self, episode):
        """Try multiple transcript extraction strategies"""

        url = episode['episode_url']
        podcast_name = episode['podcast_name']

        try:
            response = self.session.get(url, timeout=15)
            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.content, 'html.parser')

            # Strategy 1: Use cached network patterns
            for podcast_key, podcast_data in self.sources_cache.items():
                if podcast_name.lower() in podcast_key.lower():
                    network_config = podcast_data.get('config', {})
                    if 'selectors' in network_config:
                        for selector in network_config['selectors']:
                            element = soup.select_one(selector)
                            if element:
                                text = element.get_text(separator=' ', strip=True)
                                min_length = network_config.get('min_length', 1000)
                                if len(text) > min_length:
                                    return {
                                        'text': text,
                                        'source': f"network_pattern:{podcast_key}",
                                        'quality_score': min(len(text) // 1000, 10)
                                    }

            # Strategy 2: Generic transcript selectors
            selectors = [
                '.transcript', '#transcript', '.episode-transcript',
                '.full-text', '[class*="transcript"]', '[id*="transcript"]'
            ]

            for selector in selectors:
                element = soup.select_one(selector)
                if element:
                    text = element.get_text(separator=' ', strip=True)
                    if len(text) > 1000 and 'transcript' in text.lower():
                        return {
                            'text': text,
                            'source': f"generic_selector:{selector}",
                            'quality_score': min(len(text) // 1000, 10)
                        }

            # Strategy 3: Content area analysis
            content_areas = soup.select('article, .content, .post-content, .entry-content, main')
            for area in content_areas:
                text = area.get_text(separator=' ', strip=True)
                if (len(text) > 3000 and
                    'transcript' in text.lower() and
                    any(word in text.lower() for word in ['speaker', 'host', ':', 'said', 'says'])):
                    return {
                        'text': text,
                        'source': 'content_area_analysis',
                        'quality_score': min(len(text) // 1000, 10)
                    }

        except Exception as e:
            print(f"    ❌ Extraction error: {e}")

        return None

    def store_transcript(self, episode, transcript_data):
        """Store transcript in content table"""
        try:
            # Check if already exists
            existing = self.cursor.execute(
                "SELECT id FROM content WHERE url = ?",
                (episode['episode_url'],)
            ).fetchone()

            if existing:
                return False

            # Insert new transcript
            self.cursor.execute("""
                INSERT INTO content (title, url, content, content_type, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                f"[{episode['podcast_name']}] {episode['episode_title']}",
                episode['episode_url'],
                transcript_data['text'],
                'podcast_transcript',
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            self.conn.commit()
            return True

        except Exception as e:
            print(f"    ❌ Database storage error: {e}")
            return False

    def process_episode(self, episode):
        """Process a single episode"""
        print(f"\n🎯 Processing: {episode['podcast_name']}")
        print(f"   Episode: {episode['episode_title'][:60]}...")
        print(f"   URL: {episode['episode_url']}")

        # Mark as processing
        self.update_episode_status(episode['id'], 'processing')

        # Try to extract transcript
        transcript_data = self.extract_transcript_strategies(episode)

        if transcript_data:
            print(f"   ✅ Transcript found! Source: {transcript_data['source']}")
            print(f"   Length: {len(transcript_data['text']):,} characters")
            print(f"   Quality score: {transcript_data['quality_score']}")

            # Store transcript
            success = self.store_transcript(episode, transcript_data)
            if success:
                self.update_episode_status(
                    episode['id'], 'found',
                    transcript_source=transcript_data['source'],
                    content_length=len(transcript_data['text']),
                    quality_score=transcript_data['quality_score']
                )
                print(f"   ✅ Stored in database")
                return True
            else:
                print(f"   ❌ Failed to store transcript")
                self.update_episode_status(episode['id'], 'error')
                return False
        else:
            print(f"   ❌ No transcript found")
            self.update_episode_status(episode['id'], 'not_found')
            return False

    def process_batch(self, batch_size=10):
        """Process a batch of episodes"""
        print(f"EPISODE PROCESSOR - Processing {batch_size} episodes")
        print("=" * 60)

        processed = 0
        found = 0
        not_found = 0
        errors = 0

        for i in range(batch_size):
            episode = self.get_next_episode()
            if not episode:
                print("No more episodes in queue")
                break

            print(f"\n[{i+1}/{batch_size}] Processing episode {episode['id']}")

            success = self.process_episode(episode)
            processed += 1

            if success:
                found += 1
            else:
                # Check if it was marked as not_found or error
                status = self.cursor.execute(
                    "SELECT status FROM episode_queue WHERE id = ?",
                    (episode['id'],)
                ).fetchone()[0]

                if status == 'not_found':
                    not_found += 1
                else:
                    errors += 1

            # Rate limiting
            time.sleep(random.uniform(1, 2))

        # Show batch summary
        print(f"\n{'='*60}")
        print("BATCH PROCESSING COMPLETE")
        print(f"{'='*60}")
        print(f"Processed: {processed}")
        print(f"Found: {found}")
        print(f"Not found: {not_found}")
        print(f"Errors: {errors}")
        print(f"Success rate: {found/processed*100:.1f}%" if processed > 0 else "N/A")

        # Check queue status
        remaining = self.cursor.execute(
            "SELECT COUNT(*) FROM episode_queue WHERE status = 'pending'"
        ).fetchone()[0]
        print(f"Remaining in queue: {remaining}")

        return {
            'processed': processed,
            'found': found,
            'not_found': not_found,
            'errors': errors,
            'remaining': remaining
        }

    def get_queue_summary(self):
        """Get current queue status"""
        summary = self.cursor.execute("""
            SELECT
                status,
                COUNT(*) as count
            FROM episode_queue
            GROUP BY status
            ORDER BY count DESC
        """).fetchall()

        print("\nQUEUE STATUS:")
        print("-" * 30)
        total = 0
        for status, count in summary:
            print(f"{status:<12}: {count:>6}")
            total += count
        print(f"{'total':<12}: {total:>6}")

        # Show top podcasts by pending episodes
        print(f"\nTOP PODCASTS BY PENDING EPISODES:")
        top_podcasts = self.cursor.execute("""
            SELECT podcast_name, COUNT(*) as pending_count
            FROM episode_queue
            WHERE status = 'pending'
            GROUP BY podcast_name
            ORDER BY pending_count DESC
            LIMIT 10
        """).fetchall()

        for podcast, count in top_podcasts:
            print(f"  {podcast}: {count} episodes")

def main():
    processor = EpisodeProcessor()

    # Show current queue status
    processor.get_queue_summary()

    # Process a batch
    results = processor.process_batch(batch_size=10)

    processor.conn.close()
    return results

if __name__ == "__main__":
    main()