#!/usr/bin/env python3
"""
PODEMOS Episode Discovery
Discover new podcast episodes from RSS feeds for ad removal processing.
"""

import sqlite3
import feedparser
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import logging
from pathlib import Path
import hashlib
import time

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PodmosEpisodeDiscovery:
    """Episode discovery service for PODEMOS ad removal system."""

    def __init__(self, db_path: str = "podemos.db"):
        """Initialize episode discovery with database."""
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database for PODEMOS tracking."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Create podcasts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS podemos_podcasts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    rss_url TEXT UNIQUE NOT NULL,
                    website TEXT,
                    description TEXT,
                    last_checked TIMESTAMP,
                    active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Create episodes table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS podemos_episodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    podcast_id INTEGER,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    audio_url TEXT,
                    duration INTEGER,
                    file_size INTEGER,
                    published_date TIMESTAMP,
                    guid TEXT UNIQUE,
                    description TEXT,

                    -- Processing status
                    processing_status TEXT DEFAULT 'discovered',
                    transcription_status TEXT DEFAULT 'pending',
                    ad_detection_status TEXT DEFAULT 'pending',
                    audio_cutting_status TEXT DEFAULT 'pending',

                    -- Processing results
                    transcript_path TEXT,
                    ad_segments TEXT, -- JSON array of ad timestamp ranges
                    clean_audio_path TEXT,
                    clean_rss_url TEXT,

                    -- Timestamps
                    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed_at TIMESTAMP,

                    FOREIGN KEY (podcast_id) REFERENCES podemos_podcasts (id)
                )
            ''')

            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_episodes_published ON podemos_episodes (published_date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_episodes_status ON podemos_episodes (processing_status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_podcasts_active ON podemos_podcasts (active)')

            conn.commit()
            conn.close()
            logger.info(f"Initialized PODEMOS database: {self.db_path}")

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def add_podcasts(self, podcasts: List[Dict[str, str]]) -> int:
        """Add podcasts to tracking database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            added_count = 0
            for podcast in podcasts:
                try:
                    cursor.execute('''
                        INSERT OR IGNORE INTO podemos_podcasts
                        (title, rss_url, website, description)
                        VALUES (?, ?, ?, ?)
                    ''', (
                        podcast['title'],
                        podcast['rss_url'],
                        podcast.get('website', ''),
                        podcast.get('description', '')
                    ))

                    if cursor.rowcount > 0:
                        added_count += 1
                        logger.info(f"Added podcast: {podcast['title']}")

                except Exception as e:
                    logger.warning(f"Failed to add podcast {podcast['title']}: {e}")

            conn.commit()
            conn.close()

            logger.info(f"Added {added_count} new podcasts to database")
            return added_count

        except Exception as e:
            logger.error(f"Failed to add podcasts: {e}")
            return 0

    def discover_episodes(self, max_podcasts: int = None, hours_lookback: int = 48) -> List[Dict]:
        """
        Discover new episodes from tracked podcasts.

        Args:
            max_podcasts: Maximum number of podcasts to check (None = all)
            hours_lookback: How many hours back to look for new episodes

        Returns:
            List of newly discovered episodes
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get active podcasts to check
            query = '''
                SELECT id, title, rss_url, last_checked
                FROM podemos_podcasts
                WHERE active = 1
                ORDER BY COALESCE(last_checked, '1970-01-01') ASC
            '''

            if max_podcasts:
                query += f' LIMIT {max_podcasts}'

            cursor.execute(query)
            podcasts = cursor.fetchall()

            logger.info(f"Checking {len(podcasts)} podcasts for new episodes")

            new_episodes = []
            cutoff_time = datetime.now() - timedelta(hours=hours_lookback)

            for podcast_id, podcast_title, rss_url, last_checked in podcasts:
                try:
                    logger.info(f"Checking episodes for: {podcast_title}")

                    # Fetch RSS feed
                    response = requests.get(rss_url, timeout=30)
                    if response.status_code != 200:
                        logger.warning(f"Failed to fetch RSS ({response.status_code}): {podcast_title}")
                        continue

                    # Parse feed
                    feed = feedparser.parse(response.content)

                    # Check each episode
                    for entry in feed.entries:
                        try:
                            episode = self._parse_episode(entry, podcast_id, podcast_title)
                            if not episode:
                                continue

                            # Skip episodes older than our lookback window
                            if episode['published_date'] < cutoff_time:
                                continue

                            # Generate unique GUID for episode
                            episode_guid = self._generate_episode_guid(episode)
                            episode['guid'] = episode_guid

                            # Check if episode already exists
                            cursor.execute('SELECT id FROM podemos_episodes WHERE guid = ?', (episode_guid,))
                            if cursor.fetchone():
                                continue  # Episode already exists

                            # Add new episode
                            cursor.execute('''
                                INSERT INTO podemos_episodes (
                                    podcast_id, title, url, audio_url, duration, file_size,
                                    published_date, guid, description
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                podcast_id,
                                episode['title'],
                                episode['url'],
                                episode['audio_url'],
                                episode['duration'],
                                episode['file_size'],
                                episode['published_date'],
                                episode['guid'],
                                episode['description']
                            ))

                            new_episodes.append(episode)
                            logger.info(f"  ✅ New episode: {episode['title'][:50]}...")

                        except Exception as e:
                            logger.warning(f"Failed to process episode: {e}")
                            continue

                    # Update last checked timestamp
                    cursor.execute('''
                        UPDATE podemos_podcasts
                        SET last_checked = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (podcast_id,))

                except Exception as e:
                    logger.warning(f"Failed to check podcast {podcast_title}: {e}")
                    continue

            conn.commit()
            conn.close()

            logger.info(f"Discovered {len(new_episodes)} new episodes")
            return new_episodes

        except Exception as e:
            logger.error(f"Failed to discover episodes: {e}")
            return []

    def _parse_episode(self, entry, podcast_id: int, podcast_title: str) -> Optional[Dict]:
        """Parse episode data from RSS feed entry."""
        try:
            # Get basic episode info
            title = entry.get('title', 'Untitled Episode')
            url = entry.get('link', '')
            description = entry.get('description', '')

            # Parse published date
            published_date = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                published_date = datetime(*entry.published_parsed[:6])
            else:
                published_date = datetime.now()

            # Find audio enclosure
            audio_url = None
            duration = None
            file_size = None

            # Look for audio enclosures
            for enclosure in getattr(entry, 'enclosures', []):
                if enclosure.get('type', '').startswith('audio/'):
                    audio_url = enclosure.get('href') or enclosure.get('url')
                    file_size = int(enclosure.get('length', 0)) if enclosure.get('length') else None
                    break

            # Alternative: look in links
            if not audio_url:
                for link in getattr(entry, 'links', []):
                    if link.get('type', '').startswith('audio/'):
                        audio_url = link.get('href')
                        break

            # Parse duration (various formats)
            duration_str = None
            if hasattr(entry, 'itunes_duration'):
                duration_str = entry.itunes_duration
            elif 'duration' in entry:
                duration_str = entry.duration

            if duration_str:
                duration = self._parse_duration(duration_str)

            if not audio_url:
                logger.debug(f"No audio URL found for episode: {title}")
                return None

            return {
                'podcast_id': podcast_id,
                'podcast_title': podcast_title,
                'title': title,
                'url': url,
                'audio_url': audio_url,
                'duration': duration,
                'file_size': file_size,
                'published_date': published_date,
                'description': description
            }

        except Exception as e:
            logger.warning(f"Failed to parse episode: {e}")
            return None

    def _parse_duration(self, duration_str: str) -> Optional[int]:
        """Parse duration string to seconds."""
        try:
            if ':' in duration_str:
                # Format like "1:23:45" or "23:45"
                parts = duration_str.split(':')
                if len(parts) == 3:  # hours:minutes:seconds
                    return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                elif len(parts) == 2:  # minutes:seconds
                    return int(parts[0]) * 60 + int(parts[1])
            else:
                # Assume seconds
                return int(float(duration_str))
        except:
            return None

    def _generate_episode_guid(self, episode: Dict) -> str:
        """Generate unique GUID for episode."""
        # Use audio URL + title + published date for uniqueness
        guid_string = f"{episode['audio_url']}|{episode['title']}|{episode['published_date']}"
        return hashlib.md5(guid_string.encode()).hexdigest()

    def get_episodes_for_processing(self, status: str = 'discovered', limit: int = 10) -> List[Dict]:
        """Get episodes ready for processing."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT e.id, e.title, e.audio_url, e.duration, e.published_date,
                       p.title as podcast_title, e.processing_status
                FROM podemos_episodes e
                JOIN podemos_podcasts p ON e.podcast_id = p.id
                WHERE e.processing_status = ?
                ORDER BY e.published_date DESC
                LIMIT ?
            ''', (status, limit))

            episodes = []
            for row in cursor.fetchall():
                episodes.append({
                    'id': row[0],
                    'title': row[1],
                    'audio_url': row[2],
                    'duration': row[3],
                    'published_date': row[4],
                    'podcast_title': row[5],
                    'processing_status': row[6]
                })

            conn.close()
            return episodes

        except Exception as e:
            logger.error(f"Failed to get episodes for processing: {e}")
            return []

    def update_episode_status(self, episode_id: int, status: str, **kwargs):
        """Update episode processing status and metadata."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Build update query dynamically
            update_fields = ['processing_status = ?']
            values = [status]

            # Add any additional fields
            for field, value in kwargs.items():
                if field in ['transcription_status', 'ad_detection_status', 'audio_cutting_status',
                           'transcript_path', 'ad_segments', 'clean_audio_path', 'clean_rss_url']:
                    update_fields.append(f'{field} = ?')
                    values.append(value)

            values.append(episode_id)

            query = f'''
                UPDATE podemos_episodes
                SET {', '.join(update_fields)}, processed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            '''

            cursor.execute(query, values)
            conn.commit()
            conn.close()

            logger.info(f"Updated episode {episode_id} status to: {status}")

        except Exception as e:
            logger.error(f"Failed to update episode status: {e}")

    def get_stats(self) -> Dict[str, int]:
        """Get processing statistics."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get podcast count
            cursor.execute('SELECT COUNT(*) FROM podemos_podcasts WHERE active = 1')
            podcast_count = cursor.fetchone()[0]

            # Get episode counts by status
            cursor.execute('SELECT processing_status, COUNT(*) FROM podemos_episodes GROUP BY processing_status')
            status_counts = dict(cursor.fetchall())

            # Get recent episodes (last 24 hours)
            cursor.execute('''
                SELECT COUNT(*) FROM podemos_episodes
                WHERE discovered_at > datetime('now', '-24 hours')
            ''')
            recent_episodes = cursor.fetchone()[0]

            conn.close()

            return {
                'active_podcasts': podcast_count,
                'total_episodes': sum(status_counts.values()),
                'recent_episodes_24h': recent_episodes,
                'status_breakdown': status_counts
            }

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {}

def main():
    """Example usage and testing."""
    import argparse
    from podemos_opml_parser import parse_overcast_opml, create_test_opml

    parser = argparse.ArgumentParser(description="PODEMOS Episode Discovery")
    parser.add_argument('--add-opml', help='Add podcasts from OPML file')
    parser.add_argument('--discover', action='store_true', help='Discover new episodes')
    parser.add_argument('--stats', action='store_true', help='Show processing stats')
    parser.add_argument('--test', action='store_true', help='Run with test data')
    args = parser.parse_args()

    discovery = PodmosEpisodeDiscovery()

    if args.test:
        # Create test OPML and add podcasts
        create_test_opml()
        podcasts = parse_overcast_opml('test.opml')
        discovery.add_podcasts(podcasts)
        print("Added test podcasts")

    if args.add_opml:
        podcasts = parse_overcast_opml(args.add_opml)
        count = discovery.add_podcasts(podcasts)
        print(f"Added {count} podcasts from OPML")

    if args.discover:
        episodes = discovery.discover_episodes(max_podcasts=5)
        print(f"Discovered {len(episodes)} new episodes")

        for episode in episodes[:3]:  # Show first 3
            print(f"  - {episode['podcast_title']}: {episode['title']}")

    if args.stats:
        stats = discovery.get_stats()
        print("PODEMOS Processing Stats:")
        print(f"  Active podcasts: {stats.get('active_podcasts', 0)}")
        print(f"  Total episodes: {stats.get('total_episodes', 0)}")
        print(f"  Recent episodes (24h): {stats.get('recent_episodes_24h', 0)}")
        print("  Status breakdown:")
        for status, count in stats.get('status_breakdown', {}).items():
            print(f"    {status}: {count}")

if __name__ == "__main__":
    main()