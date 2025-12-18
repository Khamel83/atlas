#!/usr/bin/env python3
"""
PODEMOS Real-time Podcast Feed Monitoring System

Ultra-fast podcast feed monitoring with minimal latency:
- Imports Overcast OPML automatically
- Polls feeds every 1-2 minutes
- Immediate download triggering on new episodes
- Integration with existing Atlas infrastructure
- Target: 2AM release detected by 2:01AM
"""

import sys
import xml.etree.ElementTree as ET
import sqlite3
import asyncio
import aiohttp
import time
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import feedparser

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from helpers.config import load_config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class PodcastFeed:
    """Podcast feed configuration"""
    name: str
    xml_url: str
    apple_id: Optional[str] = None
    last_check: Optional[str] = None
    last_episode_guid: Optional[str] = None
    check_interval: int = 90  # seconds
    enabled: bool = True
    priority: int = 5  # 1-10, higher is more frequent checking

@dataclass
class Episode:
    """Episode metadata"""
    guid: str
    title: str
    description: str
    pub_date: str
    audio_url: str
    duration: Optional[str] = None
    podcast_name: str = ""
    feed_url: str = ""
    detected_at: Optional[str] = None

class PodemosFeedMonitor:
    """Real-time podcast feed monitoring system"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or load_config()
        self.data_dir = Path(self.config.get("data_directory", "data"))
        self.podemos_dir = self.data_dir / "podemos"
        self.podemos_dir.mkdir(exist_ok=True)

        # Database for feed monitoring
        self.monitor_db = self.podemos_dir / "feed_monitor.db"
        self.init_database()

        # Processing queue integration
        self.processing_db = self.data_dir / "processing_queue.db"

        # Performance tracking
        self.performance_stats = {
            'feeds_checked': 0,
            'new_episodes_found': 0,
            'average_check_time': 0.0,
            'errors_count': 0,
            'last_full_cycle': None
        }

        # Load feeds from OPML
        self.feeds = self.load_feeds_from_opml()
        logger.info(f"Loaded {len(self.feeds)} podcast feeds from OPML")

    def init_database(self):
        """Initialize monitoring database"""
        with sqlite3.connect(self.monitor_db) as conn:
            # Feed metadata table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS podcast_feeds (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    xml_url TEXT UNIQUE NOT NULL,
                    apple_id TEXT,
                    last_check TEXT,
                    last_episode_guid TEXT,
                    check_interval INTEGER DEFAULT 90,
                    enabled BOOLEAN DEFAULT 1,
                    priority INTEGER DEFAULT 5,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Episode detection log
            conn.execute("""
                CREATE TABLE IF NOT EXISTS episode_detections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    podcast_name TEXT NOT NULL,
                    episode_guid TEXT NOT NULL,
                    episode_title TEXT NOT NULL,
                    pub_date TEXT NOT NULL,
                    audio_url TEXT NOT NULL,
                    feed_url TEXT NOT NULL,
                    detected_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    processing_triggered BOOLEAN DEFAULT 0,
                    processing_started_at TEXT,
                    processing_completed_at TEXT
                )
            """)

            # Performance monitoring
            conn.execute("""
                CREATE TABLE IF NOT EXISTS monitor_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                    feeds_checked INTEGER,
                    new_episodes INTEGER,
                    check_duration_ms INTEGER,
                    errors_count INTEGER
                )
            """)

            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_feed_url ON podcast_feeds(xml_url)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_episode_guid ON episode_detections(episode_guid)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_detected_at ON episode_detections(detected_at)")

    def load_feeds_from_opml(self) -> List[PodcastFeed]:
        """Load podcast feeds from OPML file"""
        opml_file = Path("inputs/podcasts.opml")
        feeds = []

        if not opml_file.exists():
            logger.error(f"OPML file not found: {opml_file}")
            return feeds

        try:
            tree = ET.parse(opml_file)
            root = tree.getroot()

            # Find all RSS outline elements
            for outline in root.findall(".//outline[@type='rss']"):
                name = outline.get('text', 'Unknown Podcast')
                xml_url = outline.get('xmlUrl')
                apple_id = outline.get('applePodcastsID')

                if xml_url:
                    # Determine priority based on name patterns
                    priority = self.calculate_feed_priority(name)

                    feed = PodcastFeed(
                        name=name,
                        xml_url=xml_url,
                        apple_id=apple_id,
                        check_interval=max(60, 180 - (priority * 15)),  # Higher priority = more frequent
                        priority=priority
                    )
                    feeds.append(feed)

            logger.info(f"Loaded {len(feeds)} podcast feeds from OPML")
            return feeds

        except Exception as e:
            logger.error(f"Error loading OPML file: {e}")
            return []

    def calculate_feed_priority(self, podcast_name: str) -> int:
        """Calculate feed checking priority based on podcast name/type"""
        # High priority podcasts (check more frequently)
        high_priority_keywords = [
            'breaking', 'news', 'daily', 'today', 'morning', 'npr politics',
            'journal', 'intelligence', 'hard fork', 'stratechery', 'acquired'
        ]

        # Medium priority
        medium_priority_keywords = [
            'weekly', 'tech', 'business', 'economics', 'planet money'
        ]

        name_lower = podcast_name.lower()

        # Check for high priority indicators
        for keyword in high_priority_keywords:
            if keyword in name_lower:
                return 9  # High priority

        # Check for medium priority indicators
        for keyword in medium_priority_keywords:
            if keyword in name_lower:
                return 7  # Medium-high priority

        # Default priority
        return 5

    def sync_feeds_to_database(self):
        """Sync loaded feeds to database"""
        with sqlite3.connect(self.monitor_db) as conn:
            for feed in self.feeds:
                conn.execute("""
                    INSERT OR REPLACE INTO podcast_feeds
                    (name, xml_url, apple_id, check_interval, priority, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    feed.name,
                    feed.xml_url,
                    feed.apple_id,
                    feed.check_interval,
                    feed.priority,
                    datetime.now().isoformat()
                ))

    async def monitor_feeds_continuously(self, max_workers: int = 20):
        """Main monitoring loop with async processing"""
        logger.info("🚀 Starting continuous feed monitoring...")
        self.sync_feeds_to_database()

        # Create session for HTTP requests
        timeout = aiohttp.ClientTimeout(total=30)
        connector = aiohttp.TCPConnector(limit=50, limit_per_host=10)

        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            cycle_count = 0

            while True:
                cycle_start = time.time()
                cycle_count += 1

                logger.info(f"🔄 Starting monitoring cycle #{cycle_count}")

                # Get feeds that need checking
                feeds_to_check = self.get_feeds_to_check()
                logger.info(f"Checking {len(feeds_to_check)} feeds this cycle")

                if feeds_to_check:
                    # Process feeds in batches
                    batch_size = max_workers
                    batches = [feeds_to_check[i:i + batch_size]
                              for i in range(0, len(feeds_to_check), batch_size)]

                    total_new_episodes = 0
                    total_errors = 0

                    for batch in batches:
                        tasks = [
                            self.check_feed_for_new_episodes(session, feed)
                            for feed in batch
                        ]

                        results = await asyncio.gather(*tasks, return_exceptions=True)

                        for result in results:
                            if isinstance(result, Exception):
                                total_errors += 1
                                logger.error(f"Feed check error: {result}")
                            else:
                                new_episodes, _ = result
                                total_new_episodes += new_episodes

                # Update performance stats
                cycle_duration = time.time() - cycle_start
                self.performance_stats.update({
                    'feeds_checked': len(feeds_to_check),
                    'new_episodes_found': total_new_episodes,
                    'errors_count': total_errors,
                    'last_full_cycle': datetime.now().isoformat(),
                    'cycle_duration': cycle_duration
                })

                # Log stats
                logger.info(f"✅ Cycle #{cycle_count} complete: "
                           f"{total_new_episodes} new episodes found, "
                           f"{total_errors} errors, "
                           f"{cycle_duration:.1f}s duration")

                # Save stats to database
                self.save_monitoring_stats(len(feeds_to_check), total_new_episodes,
                                         cycle_duration, total_errors)

                # Wait before next cycle (adaptive based on activity)
                sleep_time = 30 if total_new_episodes > 0 else 60  # Check more frequently if active
                await asyncio.sleep(sleep_time)

    def get_feeds_to_check(self) -> List[PodcastFeed]:
        """Get feeds that need checking based on their intervals"""
        feeds_to_check = []

        with sqlite3.connect(self.monitor_db) as conn:
            cursor = conn.cursor()

            # Get feeds that haven't been checked recently or never checked
            cursor.execute("""
                SELECT name, xml_url, apple_id, last_check, check_interval, priority
                FROM podcast_feeds
                WHERE enabled = 1
                AND (
                    last_check IS NULL
                    OR datetime(last_check) < datetime('now', '-' || check_interval || ' seconds')
                )
                ORDER BY priority DESC, last_check ASC NULLS FIRST
            """)

            rows = cursor.fetchall()

            for row in rows:
                name, xml_url, apple_id, last_check, check_interval, priority = row

                feed = PodcastFeed(
                    name=name,
                    xml_url=xml_url,
                    apple_id=apple_id,
                    last_check=last_check,
                    check_interval=check_interval,
                    priority=priority
                )
                feeds_to_check.append(feed)

        return feeds_to_check

    async def check_feed_for_new_episodes(self, session: aiohttp.ClientSession,
                                        feed: PodcastFeed) -> tuple[int, List[Episode]]:
        """Check a single feed for new episodes"""
        new_episodes = []

        try:
            # Fetch RSS feed
            async with session.get(feed.xml_url) as response:
                if response.status != 200:
                    logger.warning(f"HTTP {response.status} for {feed.name}: {feed.xml_url}")
                    return 0, []

                content = await response.text()

            # Parse RSS content
            parsed_feed = feedparser.parse(content)

            if parsed_feed.bozo:
                logger.warning(f"Malformed RSS for {feed.name}: {parsed_feed.bozo_exception}")

            # Check for new episodes
            for entry in parsed_feed.entries[:5]:  # Check only recent episodes
                episode_guid = self.get_episode_guid(entry)

                if self.is_new_episode(feed.xml_url, episode_guid):
                    # Extract episode data
                    episode = self.extract_episode_data(entry, feed)
                    new_episodes.append(episode)

                    # Trigger processing immediately
                    await self.trigger_episode_processing(episode)

            # Update feed check timestamp
            self.update_feed_check_time(feed.xml_url, datetime.now().isoformat())

            if new_episodes:
                logger.info(f"🎉 {len(new_episodes)} new episodes found for {feed.name}")
                for episode in new_episodes:
                    logger.info(f"   📻 {episode.title[:60]}...")

            return len(new_episodes), new_episodes

        except asyncio.TimeoutError:
            logger.warning(f"Timeout checking {feed.name}")
            return 0, []
        except Exception as e:
            logger.error(f"Error checking feed {feed.name}: {e}")
            return 0, []

    def get_episode_guid(self, entry) -> str:
        """Extract unique episode identifier"""
        # Try different GUID sources
        if hasattr(entry, 'guid') and entry.guid:
            return entry.guid
        if hasattr(entry, 'id') and entry.id:
            return entry.id
        if hasattr(entry, 'link') and entry.link:
            return entry.link

        # Fallback to title + pubdate hash
        title = getattr(entry, 'title', '')
        pub_date = getattr(entry, 'published', '')
        return hashlib.md5(f"{title}{pub_date}".encode()).hexdigest()

    def is_new_episode(self, feed_url: str, episode_guid: str) -> bool:
        """Check if episode is new (not seen before)"""
        with sqlite3.connect(self.monitor_db) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT COUNT(*) FROM episode_detections
                WHERE episode_guid = ? AND feed_url = ?
            """, (episode_guid, feed_url))

            count = cursor.fetchone()[0]
            return count == 0

    def extract_episode_data(self, entry, feed: PodcastFeed) -> Episode:
        """Extract episode data from RSS entry"""
        # Get audio URL from enclosure
        audio_url = ""
        if hasattr(entry, 'enclosures') and entry.enclosures:
            for enclosure in entry.enclosures:
                if enclosure.type and 'audio' in enclosure.type:
                    audio_url = enclosure.href
                    break

        # Fallback: try links
        if not audio_url and hasattr(entry, 'links'):
            for link in entry.links:
                if link.get('type') and 'audio' in link.get('type', ''):
                    audio_url = link.get('href', '')
                    break

        return Episode(
            guid=self.get_episode_guid(entry),
            title=getattr(entry, 'title', 'Unknown Episode'),
            description=getattr(entry, 'description', ''),
            pub_date=getattr(entry, 'published', datetime.now().isoformat()),
            audio_url=audio_url,
            duration=getattr(entry, 'duration', None),
            podcast_name=feed.name,
            feed_url=feed.xml_url,
            detected_at=datetime.now().isoformat()
        )

    async def trigger_episode_processing(self, episode: Episode):
        """Immediately trigger processing for new episode"""
        try:
            # Save episode detection
            with sqlite3.connect(self.monitor_db) as conn:
                conn.execute("""
                    INSERT INTO episode_detections
                    (podcast_name, episode_guid, episode_title, pub_date, audio_url,
                     feed_url, detected_at, processing_triggered)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                """, (
                    episode.podcast_name,
                    episode.guid,
                    episode.title,
                    episode.pub_date,
                    episode.audio_url,
                    episode.feed_url,
                    episode.detected_at
                ))

            # Add to Atlas processing queue for ultra-fast processing
            await self.add_to_processing_queue(episode)

            logger.info(f"⚡ Triggered processing for: {episode.podcast_name} - {episode.title[:50]}...")

        except Exception as e:
            logger.error(f"Error triggering processing for episode: {e}")

    async def add_to_processing_queue(self, episode: Episode):
        """Add episode to Atlas universal processing queue"""
        try:
            with sqlite3.connect(self.processing_db) as conn:
                conn.execute("""
                    INSERT OR IGNORE INTO processing_queue
                    (podcast_name, episode_title, episode_url, audio_url, priority,
                     status, needs_audio, processing_type, created_at)
                    VALUES (?, ?, ?, ?, 10, 'pending', 1, 'podemos_fast_processing', ?)
                """, (
                    episode.podcast_name,
                    episode.title,
                    episode.feed_url,  # Use feed URL as episode URL
                    episode.audio_url,
                    datetime.now().isoformat()
                ))

            logger.info(f"📋 Added to processing queue: {episode.title[:40]}...")

        except Exception as e:
            logger.error(f"Error adding to processing queue: {e}")

    def update_feed_check_time(self, feed_url: str, check_time: str):
        """Update last check time for feed"""
        with sqlite3.connect(self.monitor_db) as conn:
            conn.execute("""
                UPDATE podcast_feeds
                SET last_check = ?, updated_at = ?
                WHERE xml_url = ?
            """, (check_time, check_time, feed_url))

    def save_monitoring_stats(self, feeds_checked: int, new_episodes: int,
                            duration: float, errors: int):
        """Save monitoring performance stats"""
        with sqlite3.connect(self.monitor_db) as conn:
            conn.execute("""
                INSERT INTO monitor_stats
                (feeds_checked, new_episodes, check_duration_ms, errors_count)
                VALUES (?, ?, ?, ?)
            """, (feeds_checked, new_episodes, int(duration * 1000), errors))

    def get_monitoring_stats(self) -> Dict[str, Any]:
        """Get current monitoring statistics"""
        stats = self.performance_stats.copy()

        # Add database stats
        with sqlite3.connect(self.monitor_db) as conn:
            cursor = conn.cursor()

            # Total episodes detected today
            cursor.execute("""
                SELECT COUNT(*) FROM episode_detections
                WHERE date(detected_at) = date('now')
            """)
            stats['episodes_today'] = cursor.fetchone()[0]

            # Average detection latency (estimate)
            cursor.execute("""
                SELECT AVG(check_duration_ms) FROM monitor_stats
                WHERE timestamp > datetime('now', '-1 hour')
            """)
            result = cursor.fetchone()
            stats['avg_check_time_ms'] = result[0] if result[0] else 0

            # Feed status
            cursor.execute("SELECT COUNT(*) FROM podcast_feeds WHERE enabled = 1")
            stats['active_feeds'] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM podcast_feeds")
            stats['total_feeds'] = cursor.fetchone()[0]

        return stats

def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="PODEMOS Real-time Feed Monitor")
    parser.add_argument("--monitor", action="store_true", help="Start continuous monitoring")
    parser.add_argument("--stats", action="store_true", help="Show monitoring statistics")
    parser.add_argument("--test-feed", type=str, help="Test specific feed URL")
    parser.add_argument("--workers", type=int, default=20, help="Max concurrent workers")

    args = parser.parse_args()

    monitor = PodemosFeedMonitor()

    if args.stats:
        stats = monitor.get_monitoring_stats()
        print("📊 PODEMOS Feed Monitor Statistics:")
        print("=" * 40)
        print(f"Active Feeds: {stats.get('active_feeds', 0)}")
        print(f"Total Feeds: {stats.get('total_feeds', 0)}")
        print(f"Episodes Today: {stats.get('episodes_today', 0)}")
        print(f"Average Check Time: {stats.get('avg_check_time_ms', 0):.0f}ms")
        print(f"Last Cycle: {stats.get('last_full_cycle', 'Never')}")
        print(f"New Episodes (last cycle): {stats.get('new_episodes_found', 0)}")

    elif args.test_feed:
        async def test_single_feed():
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                feed = PodcastFeed(name="Test Feed", xml_url=args.test_feed)
                new_count, episodes = await monitor.check_feed_for_new_episodes(session, feed)
                print(f"Found {new_count} new episodes")
                for episode in episodes:
                    print(f"  - {episode.title}")

        asyncio.run(test_single_feed())

    elif args.monitor:
        print("🚀 Starting PODEMOS real-time feed monitoring...")
        print(f"Monitoring {len(monitor.feeds)} podcast feeds")
        print("Target: 2AM release detected by 2:01AM")
        asyncio.run(monitor.monitor_feeds_continuously(args.workers))

    else:
        parser.print_help()

if __name__ == "__main__":
    main()