#!/usr/bin/env python3
"""
Comprehensive RSS Episode Harvester

Pulls ALL episodes from ALL RSS feeds once and builds complete episode database.
Solves the systematic problem of re-fetching RSS feeds repeatedly.

Usage:
    python scripts/rss_episode_harvester.py
    python scripts/rss_episode_harvester.py --podcast-name "Lex Fridman Podcast"
"""

import os
import sys
import csv
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
import requests
import feedparser
from dataclasses import dataclass

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.database_config import get_database_path, get_database_connection

@dataclass
class EpisodeData:
    """Episode metadata from RSS feed"""
    podcast_name: str
    episode_title: str
    episode_url: str
    rss_url: str
    published_date: Optional[datetime]
    description: str
    duration: Optional[str]
    episode_number: Optional[str]
    season: Optional[str]

class RSSEpisodeHarvester:
    """Comprehensive RSS episode harvester"""

    def __init__(self):
        self.db_path = get_database_path()
        self.init_episode_database()

    def init_episode_database(self):
        """Initialize episode database table"""
        conn = get_database_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS podcast_episodes (
                    id INTEGER PRIMARY KEY,
                    title TEXT,
                    audio_url TEXT UNIQUE,
                    podcast_name TEXT,
                    processed BOOLEAN DEFAULT 0,
                    rss_url TEXT,
                    published_date TEXT,
                    description TEXT,
                    duration TEXT,
                    episode_number TEXT,
                    season TEXT,
                    harvested_at TEXT,
                    transcript_attempted BOOLEAN DEFAULT FALSE,
                    transcript_found BOOLEAN DEFAULT FALSE
                )
            ''')

            # Add columns if they don't exist (for existing tables)
            new_columns = [
                ('rss_url', 'TEXT'),
                ('published_date', 'TEXT'),
                ('description', 'TEXT'),
                ('duration', 'TEXT'),
                ('episode_number', 'TEXT'),
                ('season', 'TEXT'),
                ('harvested_at', 'TEXT'),
                ('transcript_attempted', 'BOOLEAN DEFAULT FALSE'),
                ('transcript_found', 'BOOLEAN DEFAULT FALSE')
            ]

            for column_name, column_type in new_columns:
                try:
                    cursor.execute(f'ALTER TABLE podcast_episodes ADD COLUMN {column_name} {column_type}')
                except sqlite3.OperationalError:
                    pass  # Column already exists

            # Add indexes for faster queries
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_podcast_name ON podcast_episodes(podcast_name)')

            # Only create transcript index if columns exist
            try:
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_transcript_status ON podcast_episodes(transcript_attempted, transcript_found)')
            except sqlite3.OperationalError:
                pass  # Columns don't exist yet

            conn.commit()
            print(f"📊 Episode database initialized at {self.db_path}")

        except Exception as e:
            print(f"❌ Database initialization error: {e}")
            raise
        finally:
            conn.close()

    def load_podcast_config(self) -> List[Dict[str, str]]:
        """Load podcast configuration from CSV"""
        config_path = Path(__file__).parent.parent / "config" / "podcasts_prioritized_cleaned.csv"

        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        podcasts = []
        with open(config_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('RSS_URL') and row.get('RSS_URL').strip():
                    podcasts.append({
                        'name': row['Podcast Name'].strip(),
                        'rss_url': row['RSS_URL'].strip(),
                        'category': row.get('Category', '').strip(),
                        'transcript_only': row.get('Transcript_Only', '0') == '1'
                    })

        print(f"📋 Loaded {len(podcasts)} podcasts with RSS URLs")
        return podcasts

    def extract_episodes_from_rss(self, rss_url: str, podcast_name: str) -> List[EpisodeData]:
        """Extract all episodes from RSS feed"""
        episodes = []

        try:
            print(f"📡 Fetching RSS: {podcast_name}")

            # Set user agent to avoid blocking
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }

            response = requests.get(rss_url, headers=headers, timeout=30)
            response.raise_for_status()

            # Parse RSS feed
            feed = feedparser.parse(response.content)

            if not feed.entries:
                print(f"    ⚠️ No episodes found in RSS feed")
                return episodes

            print(f"    📦 Found {len(feed.entries)} episodes")

            for entry in feed.entries:
                try:
                    # Extract episode data
                    episode_title = entry.get('title', '').strip()
                    if not episode_title:
                        continue

                    # Get episode URL (prefer enclosure, fallback to link)
                    episode_url = None
                    if hasattr(entry, 'enclosures') and entry.enclosures:
                        episode_url = entry.enclosures[0].get('href', '')
                    if not episode_url:
                        episode_url = entry.get('link', '')

                    if not episode_url:
                        continue

                    # Parse published date
                    published_date = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        try:
                            published_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                        except:
                            pass

                    # Extract metadata
                    description = entry.get('summary', entry.get('description', ''))
                    duration = entry.get('itunes_duration', '')

                    # Try to extract episode number
                    episode_number = entry.get('itunes_episode', '')
                    season = entry.get('itunes_season', '')

                    episode = EpisodeData(
                        podcast_name=podcast_name,
                        episode_title=episode_title,
                        episode_url=episode_url,
                        rss_url=rss_url,
                        published_date=published_date,
                        description=description,
                        duration=duration,
                        episode_number=episode_number,
                        season=season
                    )

                    episodes.append(episode)

                except Exception as e:
                    print(f"    ⚠️ Error parsing episode: {e}")
                    continue

            print(f"    ✅ Extracted {len(episodes)} valid episodes")
            return episodes

        except Exception as e:
            print(f"    ❌ RSS extraction failed: {e}")
            return []

    def store_episodes(self, episodes: List[EpisodeData]) -> int:
        """Store episodes in database"""
        if not episodes:
            return 0

        conn = get_database_connection()
        stored_count = 0

        try:
            cursor = conn.cursor()
            harvested_at = datetime.now(timezone.utc).isoformat()

            for episode in episodes:
                try:
                    cursor.execute('''
                        INSERT OR IGNORE INTO podcast_episodes
                        (podcast_name, title, audio_url, rss_url,
                         published_date, description, duration, episode_number, season, harvested_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        episode.podcast_name,
                        episode.episode_title,
                        episode.episode_url,
                        episode.rss_url,
                        episode.published_date.isoformat() if episode.published_date else None,
                        episode.description,
                        episode.duration,
                        episode.episode_number,
                        episode.season,
                        harvested_at
                    ))

                    if cursor.rowcount > 0:
                        stored_count += 1

                except Exception as e:
                    print(f"    ⚠️ Error storing episode '{episode.episode_title}': {e}")
                    continue

            conn.commit()
            return stored_count

        except Exception as e:
            print(f"❌ Database storage error: {e}")
            return 0
        finally:
            conn.close()

    def harvest_single_podcast(self, podcast_name: str, rss_url: str) -> Tuple[int, int]:
        """Harvest episodes from single podcast"""
        print(f"\n🎙️ Harvesting: {podcast_name}")
        print(f"   RSS: {rss_url}")

        episodes = self.extract_episodes_from_rss(rss_url, podcast_name)
        stored = self.store_episodes(episodes)

        print(f"   💾 Stored {stored}/{len(episodes)} episodes")
        return len(episodes), stored

    def harvest_all_podcasts(self) -> Dict[str, Tuple[int, int]]:
        """Harvest episodes from all configured podcasts"""
        podcasts = self.load_podcast_config()
        results = {}

        total_episodes = 0
        total_stored = 0

        print(f"🚀 Starting comprehensive RSS harvest for {len(podcasts)} podcasts")
        print(f"📊 Database: {self.db_path}")
        print("=" * 80)

        for i, podcast in enumerate(podcasts, 1):
            try:
                print(f"\n[{i}/{len(podcasts)}] Processing: {podcast['name']}")

                episodes, stored = self.harvest_single_podcast(
                    podcast['name'],
                    podcast['rss_url']
                )

                results[podcast['name']] = (episodes, stored)
                total_episodes += episodes
                total_stored += stored

                print(f"   ✅ Complete ({stored} new episodes)")

            except Exception as e:
                print(f"   ❌ Failed: {e}")
                results[podcast['name']] = (0, 0)
                continue

        print("\n" + "=" * 80)
        print(f"🎯 HARVEST COMPLETE")
        print(f"   📦 Total episodes found: {total_episodes:,}")
        print(f"   💾 New episodes stored: {total_stored:,}")
        print(f"   📊 Database updated: {self.db_path}")

        return results

    def harvest_specific_podcast(self, podcast_name: str) -> Optional[Tuple[int, int]]:
        """Harvest episodes from specific podcast by name"""
        podcasts = self.load_podcast_config()

        for podcast in podcasts:
            if podcast['name'].lower() == podcast_name.lower():
                return self.harvest_single_podcast(podcast['name'], podcast['rss_url'])

        print(f"❌ Podcast not found: {podcast_name}")
        available = [p['name'] for p in podcasts]
        print(f"Available podcasts: {', '.join(available[:5])}...")
        return None

    def get_harvest_stats(self) -> Dict[str, int]:
        """Get harvest statistics"""
        conn = get_database_connection()

        try:
            cursor = conn.cursor()

            # Total episodes
            cursor.execute('SELECT COUNT(*) FROM podcast_episodes')
            total_episodes = cursor.fetchone()[0]

            # Unique podcasts
            cursor.execute('SELECT COUNT(DISTINCT podcast_name) FROM podcast_episodes')
            unique_podcasts = cursor.fetchone()[0]

            # Episodes with transcripts attempted
            cursor.execute('SELECT COUNT(*) FROM podcast_episodes WHERE transcript_attempted = TRUE')
            attempted = cursor.fetchone()[0]

            # Episodes with transcripts found
            cursor.execute('SELECT COUNT(*) FROM podcast_episodes WHERE transcript_found = TRUE')
            found = cursor.fetchone()[0]

            return {
                'total_episodes': total_episodes,
                'unique_podcasts': unique_podcasts,
                'transcript_attempted': attempted,
                'transcript_found': found
            }

        except Exception as e:
            print(f"❌ Stats query error: {e}")
            return {}
        finally:
            conn.close()

def main():
    parser = argparse.ArgumentParser(description='Comprehensive RSS Episode Harvester')
    parser.add_argument('--podcast-name', help='Harvest specific podcast by name')
    parser.add_argument('--stats', action='store_true', help='Show harvest statistics')

    args = parser.parse_args()

    harvester = RSSEpisodeHarvester()

    if args.stats:
        stats = harvester.get_harvest_stats()
        print("📊 Harvest Statistics:")
        print(f"   Total episodes: {stats.get('total_episodes', 0):,}")
        print(f"   Unique podcasts: {stats.get('unique_podcasts', 0)}")
        print(f"   Transcript attempts: {stats.get('transcript_attempted', 0)}")
        print(f"   Transcripts found: {stats.get('transcript_found', 0)}")
        return

    if args.podcast_name:
        result = harvester.harvest_specific_podcast(args.podcast_name)
        if result:
            episodes, stored = result
            print(f"✅ Harvested {stored}/{episodes} episodes for '{args.podcast_name}'")
    else:
        harvester.harvest_all_podcasts()

if __name__ == "__main__":
    main()