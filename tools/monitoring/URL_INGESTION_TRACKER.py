#!/usr/bin/env python3
"""
URL Ingestion Tracker
Tracks every successful URL, source, and ingestion method
Creates comprehensive database of what works and where transcripts come from
"""

import json
import sqlite3
import time
from pathlib import Path
from datetime import datetime
import logging
from urllib.parse import urlparse, urljoin

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/ubuntu/dev/atlas/url_ingestion_tracking.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class URLIngestionTracker:
    """Track all successful URL ingestions and their sources"""

    def __init__(self):
        self.root_dir = Path("/home/ubuntu/dev/atlas")

        # Tracking database
        self.tracking_db = self.root_dir / "url_ingestion.db"
        self.init_tracking_db()

        # Master CSV for easy review
        self.master_csv = self.root_dir / "master_url_ingestion_log.csv"
        self.init_master_csv()

        # JSON summary for analysis
        self.summary_json = self.root_dir / "url_ingestion_summary.json"

        # Load podcast sources
        with open(self.root_dir / "podcast_transcript_sources.json", "r") as f:
            self.podcast_sources = json.load(f)

    def init_tracking_db(self):
        """Initialize SQLite database for URL tracking"""
        conn = sqlite3.connect(str(self.tracking_db))
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS url_ingestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                episode_id INTEGER NOT NULL,
                podcast_name TEXT NOT NULL,
                episode_title TEXT NOT NULL,
                source_url TEXT NOT NULL,
                source_type TEXT NOT NULL,
                extraction_method TEXT NOT NULL,
                content_length INTEGER NOT NULL,
                success BOOLEAN NOT NULL,
                error_message TEXT,
                user_agent TEXT,
                response_code INTEGER,
                processing_time_seconds REAL,
                transcript_file_path TEXT,
                source_config_key TEXT,
                retry_count INTEGER DEFAULT 0
            )
        ''')

        # Create indexes for fast queries
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_podcast_name ON url_ingestions(podcast_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_source_url ON url_ingestions(source_url)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON url_ingestions(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_success ON url_ingestions(success)')

        conn.commit()
        conn.close()
        logger.info(f"✅ URL tracking database initialized: {self.tracking_db}")

    def init_master_csv(self):
        """Initialize master CSV file"""
        if not self.master_csv.exists():
            with open(self.master_csv, 'w') as f:
                f.write('timestamp,episode_id,podcast_name,episode_title,source_url,source_type,extraction_method,content_length,success,response_code,processing_time_seconds,transcript_file_path,source_config_key,retry_count\n')
            logger.info(f"✅ Master CSV initialized: {self.master_csv}")

    def track_ingestion(self, episode_id, podcast_name, episode_title, source_url,
                       extraction_method, content_length, success, error_message=None,
                       response_code=None, processing_time=0, transcript_file=None,
                       source_config_key=None, retry_count=0):
        """Track a single URL ingestion attempt"""

        # Determine source type
        source_type = self.classify_source_type(source_url)

        # Get current timestamp
        timestamp = datetime.now().isoformat()

        # Save to SQLite
        conn = sqlite3.connect(str(self.tracking_db))
        try:
            cursor = conn.execute('''
                INSERT INTO url_ingestions
                (timestamp, episode_id, podcast_name, episode_title, source_url,
                 source_type, extraction_method, content_length, success, error_message,
                 response_code, processing_time_seconds, transcript_file_path,
                 source_config_key, retry_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (timestamp, episode_id, podcast_name, episode_title, source_url,
                  source_type, extraction_method, content_length, success, error_message,
                  response_code, processing_time, transcript_file, source_config_key, retry_count))
            conn.commit()
        except Exception as e:
            logger.error(f"❌ Error saving to tracking database: {e}")
        finally:
            conn.close()

        # Save to CSV
        self.append_to_csv([
            timestamp, episode_id, podcast_name, episode_title, source_url, source_type,
            extraction_method, content_length, success, response_code, processing_time,
            transcript_file, source_config_key, retry_count
        ])

        logger.info(f"📊 Tracked: {podcast_name} - {episode_title} - {extraction_method} - {'✅' if success else '❌'}")

    def classify_source_type(self, url):
        """Classify the type of source URL"""
        domain = urlparse(url).netloc.lower()

        if 'tapesearch.com' in domain:
            return 'Tapesearch'
        elif 'podscribe.com' in domain:
            return 'Podscribe'
        elif 'transcriptforest.com' in domain:
            return 'TranscriptForest'
        elif 'musixmatch.com' in domain:
            return 'Musixmatch'
        elif 'happyscribe.com' in domain:
            return 'HappyScribe'
        elif 'podscripts.co' in domain:
            return 'Podscripts'
        elif 'wsj.com' in domain:
            return 'WSJ'
        elif 'nytimes.com' in domain:
            return 'NewYorkTimes'
        elif 'lexfridman.com' in domain:
            return 'LexFridman'
        elif 'econlib.org' in domain:
            return 'EconLib'
        elif '99percentinvisible.org' in domain:
            return '99PercentInvisible'
        elif 'theverge.com' in domain:
            return 'TheVerge'
        elif 'stratechery.com' in domain:
            return 'Stratechery'
        elif 'fs.blog' in domain:
            return 'FarnamStreet'
        elif 'sharptech.fm' in domain:
            return 'SharpTech'
        elif 'acquired.fm' in domain:
            return 'Acquired'
        elif 'substack.com' in domain:
            return 'Substack'
        elif 'rephonic.com' in domain:
            return 'Rephonic'
        elif 'wave.co' in domain:
            return 'Wave'
        elif 'player.fm' in domain:
            return 'PlayerFM'
        elif 'conversationswithtyler.com' in domain:
            return 'ConversationsWithTyler'
        elif 'radiolab.org' in domain:
            return 'Radiolab'
        elif 'thisamericanlife.org' in domain:
            return 'ThisAmericanLife'
        elif 'practicalai.fm' in domain:
            return 'PracticalAI'
        elif 'dwarkesh.com' in domain:
            return 'Dwarkesh'
        elif 'metacast.app' in domain:
            return 'Metacast'
        elif 'lennyspodcast.com' in domain:
            return 'LennysPodcast'
        elif 'lennysnewsletter.com' in domain:
            return 'LennysNewsletter'
        elif 'catatp.fm' in domain:
            return 'ATP'
        elif 'marcoshuerta.com' in domain:
            return 'Marcoshuerta'
        elif 'archive.org' in domain or 'web.archive.org' in domain:
            return 'WaybackMachine'
        else:
            return 'Unknown'

    def append_to_csv(self, row_data):
        """Append data to master CSV file"""
        try:
            with open(self.master_csv, 'a', encoding='utf-8') as f:
                f.write(','.join(str(x) if x is not None else '' for x in row_data) + '\n')
        except Exception as e:
            logger.error(f"❌ Error writing to CSV: {e}")

    def update_summary_json(self):
        """Update summary JSON with current statistics"""
        conn = sqlite3.connect(str(self.tracking_db))
        try:
            # Get statistics
            cursor = conn.execute('''
                SELECT
                    COUNT(*) as total,
                    COUNT(CASE WHEN success = 1 THEN 1 END) as successful,
                    COUNT(CASE WHEN success = 0 THEN 1 END) as failed,
                    COUNT(DISTINCT podcast_name) as unique_podcasts,
                    COUNT(DISTINCT source_url) as unique_urls,
                    COUNT(DISTINCT source_type) as unique_source_types,
                    SUM(content_length) as total_chars,
                    AVG(processing_time_seconds) as avg_processing_time
                FROM url_ingestions
            ''')
            stats = cursor.fetchone()

            # Get breakdown by source type
            cursor.execute('''
                SELECT source_type, COUNT(*) as count, COUNT(CASE WHEN success = 1 THEN 1 END) as successful
                FROM url_ingestions
                GROUP BY source_type
                ORDER BY count DESC
            ''')
            by_source = cursor.fetchall()

            # Get breakdown by podcast
            cursor.execute('''
                SELECT podcast_name, COUNT(*) as count, COUNT(CASE WHEN success = 1 THEN 1 END) as successful
                FROM url_ingestions
                GROUP BY podcast_name
                ORDER BY count DESC
            ''')
            by_podcast = cursor.fetchall()

            summary = {
                'timestamp': datetime.now().isoformat(),
                'statistics': {
                    'total_attempts': stats[0],
                    'successful': stats[1],
                    'failed': stats[2],
                    'success_rate': (stats[1] / stats[0] * 100) if stats[0] > 0 else 0,
                    'unique_podcasts': stats[3],
                    'unique_urls': stats[4],
                    'unique_source_types': stats[5],
                    'total_characters': stats[6],
                    'average_processing_time': stats[7]
                },
                'by_source_type': [
                    {'source_type': row[0], 'total': row[1], 'successful': row[2]}
                    for row in by_source
                ],
                'by_podcast': [
                    {'podcast_name': row[0], 'total': row[1], 'successful': row[2]}
                    for row in by_podcast
                ],
                'top_successful_urls': self.get_top_successful_urls(),
                'recent_ingestions': self.get_recent_ingestions()
            }

            with open(self.summary_json, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)

            logger.info(f"✅ Summary JSON updated: {self.summary_json}")

        except Exception as e:
            logger.error(f"❌ Error updating summary JSON: {e}")
        finally:
            conn.close()

    def get_top_successful_urls(self, limit=20):
        """Get top successful URLs"""
        conn = sqlite3.connect(str(self.tracking_db))
        try:
            cursor = conn.execute('''
                SELECT source_url, COUNT(*) as success_count, AVG(content_length) as avg_length
                FROM url_ingestions
                WHERE success = 1
                GROUP BY source_url
                ORDER BY success_count DESC, avg_length DESC
                LIMIT ?
            ''', (limit,))
            return [
                {'url': row[0], 'success_count': row[1], 'avg_content_length': row[2]}
                for row in cursor.fetchall()
            ]
        finally:
            conn.close()

    def get_recent_ingestions(self, limit=50):
        """Get recent successful ingestions"""
        conn = sqlite3.connect(str(self.tracking_db))
        try:
            cursor = conn.execute('''
                SELECT podcast_name, episode_title, source_url, source_type, content_length
                FROM url_ingestions
                WHERE success = 1
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
            return [
                {
                    'podcast': row[0], 'episode': row[1], 'url': row[2],
                    'source_type': row[3], 'content_length': row[4]
                }
                for row in cursor.fetchall()
            ]
        finally:
            conn.close()

    def generate_source_mapping(self):
        """Generate a comprehensive source mapping for reference"""
        mapping = {}

        for podcast_name, config in self.podcast_sources['podcast_sources'].items():
            podcast_urls = []

            for key in ['primary', 'secondary', 'tertiary']:
                if key in config and config[key]:
                    podcast_urls.append({
                        'key': key,
                        'url': config[key],
                        'type': self.classify_source_type(config[key])
                    })

            mapping[podcast_name] = {
                'urls': podcast_urls,
                'priority': config.get('priority', 'normal'),
                'reliable': config.get('reliable', False)
            }

        mapping_file = self.root_dir / "comprehensive_source_mapping.json"
        with open(mapping_file, 'w', encoding='utf-8') as f:
            json.dump(mapping, f, indent=2, ensure_ascii=False)

        logger.info(f"✅ Source mapping saved: {mapping_file}")
        return mapping_file

    def print_current_status(self):
        """Print current tracking status"""
        conn = sqlite3.connect(str(self.tracking_db))
        try:
            cursor = conn.execute('''
                SELECT
                    COUNT(*) as total,
                    COUNT(CASE WHEN success = 1 THEN 1 END) as successful,
                    COUNT(CASE WHEN success = 0 THEN 1 END) as failed,
                    COUNT(DISTINCT podcast_name) as unique_podcasts
                FROM url_ingestions
            ''')
            stats = cursor.fetchone()

            print(f"\n📊 URL INGESTION TRACKING STATUS")
            print("=" * 50)
            print(f"Total Attempts: {stats[0]}")
            print(f"Successful: {stats[1]} ✅")
            print(f"Failed: {stats[2]} ❌")
            print(f"Success Rate: {(stats[1] / stats[0] * 100):.1f}%" if stats[0] > 0 else "N/A")
            print(f"Unique Podcasts: {stats[3]}")
            print(f"Tracking Files: {self.tracking_db}, {self.master_csv}, {self.summary_json}")

        finally:
            conn.close()

    def update_from_existing_transcripts(self):
        """Update tracker with existing transcript files"""
        transcripts_dir = self.root_dir / "transcripts"
        if not transcripts_dir.exists():
            logger.warning(f"⚠️ Transcripts directory not found: {transcripts_dir}")
            return

        transcript_files = list(transcripts_dir.glob("*.md"))
        logger.info(f"📁 Found {len(transcript_files)} existing transcript files")

        # Connect to main podcast database to get episode info
        main_db = self.root_dir / "podcast_processing.db"
        if not main_db.exists():
            logger.warning(f"⚠️ Main database not found: {main_db}")
            return

        main_conn = sqlite3.connect(str(main_db))

        for transcript_file in transcript_files:
            try:
                # Extract episode ID from filename
                filename = transcript_file.name
                if filename.startswith(tuple(map(str, range(1000)))):  # Assuming episode IDs are numeric
                    episode_id_str = filename.split()[0]  # Get first number before space
                    try:
                        episode_id = int(episode_id_str)
                    except ValueError:
                        continue

                    # Get episode info from database
                    cursor = main_conn.execute('''
                        SELECT e.title, p.name as podcast_name
                        FROM episodes e
                        JOIN podcasts p ON e.podcast_id = p.id
                        WHERE e.id = ?
                    ''', (episode_id,))
                    episode_info = cursor.fetchone()

                    if episode_info:
                        episode_title, podcast_name = episode_info

                        # Check file content for source info
                        with open(transcript_file, 'r', encoding='utf-8') as f:
                            content = f.read()

                        # Extract source URL from markdown
                        source_url = "Unknown"
                        extraction_method = "Existing"
                        if "Source URL:" in content:
                            lines = content.split('\n')
                            for i, line in enumerate(lines):
                                if line.startswith('Source URL:'):
                                    source_url = line.split(':', 1)[1].strip()
                                elif line.startswith('Method:'):
                                    extraction_method = line.split(':', 1)[1].strip()

                        # Track this existing ingestion
                        content_length = len(content)

                        self.track_ingestion(
                            episode_id, podcast_name, episode_title, source_url,
                            extraction_method, content_length, True,
                            transcript_file=str(transcript_file)
                        )

            except Exception as e:
                logger.error(f"❌ Error processing {transcript_file}: {e}")
                continue

        main_conn.close()
        logger.info("✅ Completed updating from existing transcripts")

if __name__ == "__main__":
    tracker = URLIngestionTracker()

    # Update from existing transcripts
    tracker.update_from_existing_transcripts()

    # Update summary
    tracker.update_summary_json()

    # Generate source mapping
    tracker.generate_source_mapping()

    # Print status
    tracker.print_current_status()