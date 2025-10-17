#!/usr/bin/env python3
"""
OOS Podcast Transcript Extractor
Integrates Atlas podcast extraction capabilities with OOS system
"""

import sqlite3
import requests
import feedparser
import time
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from transcript_quality import is_real_transcript

class PodcastExtractor:
    """Podcast transcript extraction with OOS integration"""

    def __init__(self, db_path: str = "data/atlas.db"):
        self.db_path = db_path
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def extract_from_rss(self, podcast_name: str, rss_url: str, max_episodes: int = 25) -> List[Dict]:
        """Extract transcripts from RSS feed"""
        try:
            feed = feedparser.parse(rss_url)
            episodes = []

            for i, entry in enumerate(feed.entries[:max_episodes]):
                title = entry.get('title', f'Episode {i+1}')

                # Try to extract transcript from episode
                transcript = self._extract_transcript_from_entry(entry)

                if transcript and is_real_transcript(transcript):
                    episodes.append({
                        'podcast': podcast_name,
                        'title': title,
                        'content': transcript,
                        'url': entry.get('link', ''),
                        'published': entry.get('published', ''),
                        'quality_score': len(transcript)
                    })

                time.sleep(1)  # Rate limiting

            return episodes

        except Exception as e:
            print(f"Error processing RSS feed {rss_url}: {e}")
            return []

    def _extract_transcript_from_entry(self, entry) -> Optional[str]:
        """Extract transcript from RSS entry"""
        # Check for transcript in various fields
        transcript_fields = [
            'content', 'summary', 'description', 'subtitle'
        ]

        for field in transcript_fields:
            content = entry.get(field, '')
            if isinstance(content, list):
                content = ' '.join(str(item) for item in content)
            elif hasattr(content, 'value'):
                content = content.value

            content = str(content).strip()
            if len(content) > 5000:  # Potential real transcript
                return content

        # Try to fetch from episode URL
        episode_url = entry.get('link', '')
        if episode_url:
            return self._fetch_transcript_from_url(episode_url)

        return None

    def _fetch_transcript_from_url(self, url: str) -> Optional[str]:
        """Fetch transcript from episode URL"""
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                # Simple text extraction (can be enhanced)
                text = response.text
                if 'transcript' in text.lower() and len(text) > 10000:
                    return text[:50000]  # Limit size
        except:
            pass
        return None

    def process_podcast_feeds(self, feeds_file: str = "config/podcast_rss_feeds.csv") -> Dict:
        """Process all podcast feeds and extract transcripts"""
        import csv

        results = {
            'total_feeds': 0,
            'successful_extractions': 0,
            'total_episodes': 0,
            'quality_transcripts': 0,
            'podcasts': {}
        }

        try:
            with open(feeds_file, 'r') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 2:
                        podcast_name, rss_url = row[0].strip('"'), row[1].strip('"')
                        results['total_feeds'] += 1

                        print(f"Processing: {podcast_name}")
                        episodes = self.extract_from_rss(podcast_name, rss_url)

                        if episodes:
                            results['successful_extractions'] += 1
                            results['total_episodes'] += len(episodes)

                            quality_count = sum(1 for ep in episodes if is_real_transcript(ep['content']))
                            results['quality_transcripts'] += quality_count

                            results['podcasts'][podcast_name] = {
                                'episodes': len(episodes),
                                'quality_episodes': quality_count,
                                'avg_length': sum(len(ep['content']) for ep in episodes) // len(episodes) if episodes else 0
                            }

                            # Store in database
                            self._store_episodes(episodes)

        except Exception as e:
            print(f"Error processing feeds: {e}")

        return results

    def _store_episodes(self, episodes: List[Dict]):
        """Store episodes in Atlas database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            for episode in episodes:
                cursor.execute('''
                    INSERT OR REPLACE INTO content (title, content, content_type, url, created_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    f"[{episode['podcast']}] {episode['title']}",
                    episode['content'],
                    'podcast_transcript',
                    episode['url'],
                    datetime.now().isoformat()
                ))

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"Error storing episodes: {e}")

    def get_quality_stats(self) -> Dict:
        """Get quality statistics for stored transcripts"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get all transcripts
            transcripts = cursor.execute('''
                SELECT title, content, LENGTH(content) as char_count
                FROM content
                WHERE content_type = 'podcast_transcript'
                ORDER BY char_count DESC
            ''').fetchall()

            total = len(transcripts)
            quality_count = sum(1 for _, content, _ in transcripts if is_real_transcript(content))

            # Get podcast breakdown
            podcast_stats = cursor.execute('''
                SELECT
                    CASE
                        WHEN title LIKE '[%]%' THEN SUBSTRING(title, 2, INSTR(title, ']') - 2)
                        ELSE 'Unknown'
                    END as podcast_name,
                    COUNT(*) as episode_count,
                    AVG(LENGTH(content)) as avg_chars
                FROM content
                WHERE content_type = 'podcast_transcript'
                GROUP BY podcast_name
                ORDER BY episode_count DESC
            ''').fetchall()

            conn.close()

            return {
                'total_transcripts': total,
                'quality_transcripts': quality_count,
                'quality_rate': (quality_count / total * 100) if total > 0 else 0,
                'podcasts': [
                    {
                        'name': name,
                        'episodes': count,
                        'avg_length': int(avg_chars)
                    }
                    for name, count, avg_chars in podcast_stats
                ]
            }

        except Exception as e:
            print(f"Error getting stats: {e}")
            return {}

# CLI interface for OOS integration
if __name__ == "__main__":
    import sys

    extractor = PodcastExtractor()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "extract":
            print("🎙️ Starting podcast transcript extraction...")
            results = extractor.process_podcast_feeds()
            print(f"📊 Results: {results}")

        elif command == "stats":
            print("📊 Quality Statistics:")
            stats = extractor.get_quality_stats()
            print(f"Total transcripts: {stats.get('total_transcripts', 0)}")
            print(f"Quality transcripts: {stats.get('quality_transcripts', 0)}")
            print(f"Quality rate: {stats.get('quality_rate', 0):.1f}%")

        elif command == "clean":
            print("🧹 Cleaning fake transcripts...")
            # Import and use the quality module
            from transcript_quality import is_real_transcript

            conn = sqlite3.connect(extractor.db_path)
            cursor = conn.cursor()

            # Get all transcripts
            transcripts = cursor.execute('''
                SELECT id, content FROM content WHERE content_type = 'podcast_transcript'
            ''').fetchall()

            deleted = 0
            for transcript_id, content in transcripts:
                if not is_real_transcript(content):
                    cursor.execute('DELETE FROM content WHERE id = ?', (transcript_id,))
                    deleted += 1

            conn.commit()
            conn.close()

            print(f"🗑️ Deleted {deleted} fake transcripts")

    else:
        print("Usage: python podcast_extractor.py [extract|stats|clean]")