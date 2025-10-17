#!/usr/bin/env python3
"""
Smart Transcription Pipeline with Mac Mini Processing

Intelligent podcast transcription system that:
1. Checks Transcript_Only flag per podcast from prioritized.csv
2. Searches for existing transcripts first
3. Only downloads audio if transcript unavailable AND needed
4. Mac Mini local transcription processing
5. Universal processing queue (no competing parallel processes)
6. Respects exact episode counts from prioritized.csv
"""

import os
import csv
import json
import logging
import sqlite3
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import feedparser # Added this import

from helpers.config import load_config
from helpers.metadata_manager import MetadataManager
from helpers.utils import log_info, log_error

# Optional imports for full functionality
try:
    from helpers.podcast_transcript_ingestor import PodcastTranscriptIngestor
    TRANSCRIPT_INGESTOR_AVAILABLE = True
except ImportError:
    TRANSCRIPT_INGESTOR_AVAILABLE = False
    PodcastTranscriptIngestor = None

logger = logging.getLogger(__name__)

class SmartTranscriptionPipeline:
    """Smart pipeline for podcast transcription with Mac Mini processing"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or load_config()
        self.data_dir = Path(self.config.get("data_directory", "data"))
        self.podcast_data_dir = self.data_dir / "podcasts"
        self.transcript_ingestor = PodcastTranscriptIngestor(self.config) if TRANSCRIPT_INGESTOR_AVAILABLE else None
        self.metadata_manager = MetadataManager(self.config)

        # Processing queue database
        self.queue_db = self.data_dir / "processing_queue.db"
        self._init_queue_database()

        # Mac Mini configuration
        self.mac_mini_config = self._load_mac_mini_config()

        # Set up logging first
        self.log_path = self.podcast_data_dir / "smart_transcription.log"
        os.makedirs(self.podcast_data_dir, exist_ok=True)

        # Load prioritized podcasts configuration
        self.prioritized_podcasts = self._load_prioritized_podcasts()

    def _init_queue_database(self):
        """Initialize universal processing queue database"""
        with sqlite3.connect(self.queue_db) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processing_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    podcast_name TEXT NOT NULL,
                    episode_title TEXT NOT NULL,
                    episode_url TEXT UNIQUE NOT NULL,
                    audio_url TEXT,
                    priority INTEGER DEFAULT 5,
                    status TEXT DEFAULT 'pending',
                    transcript_only BOOLEAN DEFAULT 0,
                    needs_audio BOOLEAN DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    started_at TEXT,
                    completed_at TEXT,
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    processing_type TEXT DEFAULT 'transcript'
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_status ON processing_queue(status)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_priority ON processing_queue(priority DESC)
            """)

    def _load_mac_mini_config(self) -> Dict[str, Any]:
        """Load Mac Mini configuration for local transcription"""
        mac_config_file = Path("config/mac_mini.json")
        if mac_config_file.exists():
            with open(mac_config_file) as f:
                return json.load(f)

        # Default Mac Mini configuration
        return {
            "enabled": False,
            "host": "mac-mini.local",
            "user": "atlas",
            "transcription_model": "whisper-large-v3",
            "concurrent_jobs": 2,
            "ssh_key": "~/.ssh/mac_mini_key"
        }

    def _load_prioritized_podcasts(self) -> Dict[str, Dict[str, Any]]:
        """Load prioritized podcasts configuration from CSV"""
        prioritized_file = Path("config/podcasts_prioritized_cleaned.csv")
        podcasts = {}

        if not prioritized_file.exists():
            log_error(self.log_path, f"Prioritized podcasts file not found: {prioritized_file}")
            return podcasts

        try:
            with open(prioritized_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = row.get('Podcast Name', '').strip()
                    if name:
                        podcasts[name] = {
                            'category': row.get('Category', ''),
                            'count': int(row.get('Count', 0)),
                            'future': bool(int(row.get('Future', 0))),
                            'transcript_only': bool(int(row.get('Transcript_Only', 0))),
                            'exclude': bool(int(row.get('Exclude', 0))),
                            'rss_url': row.get('RSS_URL', '') # Add RSS_URL
                        }

            log_info(self.log_path, f"Loaded {len(podcasts)} prioritized podcasts")
            return podcasts

        except Exception as e:
            log_error(self.log_path, f"Error loading prioritized podcasts: {e}")
            return {}

    def process_prioritized_podcasts(self):
        """Main entry point: process all prioritized podcasts according to their configuration"""
        log_info(self.log_path, "🚀 Starting smart transcription pipeline for prioritized podcasts")

        total_processed = 0
        for podcast_name, config in self.prioritized_podcasts.items():
            if config['exclude']:
                log_info(self.log_path, f"⏭️  Skipping excluded podcast: {podcast_name}")
                continue

            log_info(self.log_path, f"🎙️  Processing podcast: {podcast_name}")
            log_info(self.log_path, f"   Config: {config}")

            try:
                processed_count = self._process_single_podcast(podcast_name, config)
                total_processed += processed_count

                log_info(self.log_path, f"✅ Completed {podcast_name}: {processed_count} episodes")

            except Exception as e:
                log_error(self.log_path, f"❌ Error processing {podcast_name}: {e}")

        log_info(self.log_path, f"🎉 Smart transcription pipeline completed: {total_processed} total episodes processed")
        return total_processed

    def _process_single_podcast(self, podcast_name: str, config: Dict[str, Any]) -> int:
        """Process a single podcast according to its configuration"""
        # 1. Find or discover episodes for this podcast
        episodes = self._discover_podcast_episodes(podcast_name, config['count'])

        if not episodes:
            log_info(self.log_path, f"No episodes found for {podcast_name}")
            return 0

        processed_count = 0

        for episode in episodes[:config['count']]:  # Respect exact episode count
            try:
                # 2. Check if we already have this episode processed
                if self._episode_already_processed(episode['url']):
                    log_info(self.log_path, f"   ✅ Already processed: {episode['title'][:50]}...")
                    continue

                # 3. Smart processing based on transcript_only flag
                if config['transcript_only']:
                    success = self._process_transcript_only(podcast_name, episode)
                else:
                    success = self._process_with_audio_download(podcast_name, episode, episode.get('audio_url'))

                if success:
                    processed_count += 1
                    log_info(self.log_path, f"   ✅ Processed: {episode['title'][:50]}...")
                else:
                    log_error(self.log_path, f"   ❌ Failed: {episode['title'][:50]}...")

            except Exception as e:
                log_error(self.log_path, f"Error processing episode {episode.get('title', 'Unknown')}: {e}")

        return processed_count

    def _discover_podcast_episodes(self, podcast_name: str, max_count: int) -> List[Dict[str, Any]]:
        """Discover episodes for a podcast by parsing its RSS feed."""
        log_info(self.log_path, f"   🔍 Discovering episodes for {podcast_name} (max: {max_count})")

        podcast_config = self.prioritized_podcasts.get(podcast_name)
        if not podcast_config or not podcast_config.get('rss_url'):
            log_error(self.log_path, f"No RSS URL found for podcast: {podcast_name}")
            return []

        rss_url = podcast_config['rss_url']
        episodes = []
        try:
            feed = feedparser.parse(rss_url)
            if feed.bozo:
                log_error(self.log_path, f"Malformed feed detected for {rss_url}: {feed.bozo_exception}")

            for entry in feed.entries:
                episodes.append({
                    'title': entry.title,
                    'url': entry.link,
                    'podcast_name': podcast_name,
                    'published': getattr(entry, 'published', ''), # Use getattr for robustness
                    'audio_url': self._extract_audio_url_from_entry(entry) # New helper for audio URL
                })

            log_info(self.log_path, f"   📊 Found {len(episodes)} episodes for {podcast_name} from RSS.")

        except Exception as e:
            log_error(self.log_path, f"Error fetching or parsing RSS feed for {podcast_name} ({rss_url}): {e}")

        return episodes

    def _extract_audio_url_from_entry(self, entry: Any) -> Optional[str]:
        """Extracts the direct audio URL from a feedparser entry."""
        if hasattr(entry, 'enclosures') and entry.enclosures:
            for enclosure in entry.enclosures:
                if enclosure.type.startswith('audio/'):
                    return enclosure.href
        # Fallback: sometimes the audio URL is directly in the link or a specific field
        # This might need more sophisticated parsing for some feeds
        return None

    def _episode_already_processed(self, episode_url: str) -> bool:
        """Check if episode is already processed in Atlas"""
        try:
            db_path = self.data_dir / "atlas.db"
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM content WHERE url = ?", (episode_url,))
                count = cursor.fetchone()[0]
                return count > 0
        except Exception as e:
            log_error(self.log_path, f"Error checking if episode processed: {e}")
            return False

    def _process_transcript_only(self, podcast_name: str, episode: Dict[str, Any]) -> bool:
        """Process episode that only needs transcript (no audio download)"""
        log_info(self.log_path, f"   📝 Transcript-only processing: {episode['title'][:50]}...")

        # 1. Search for existing transcript first
        transcript_text = self._search_existing_transcript(episode)

        if transcript_text:
            log_info(self.log_path, f"   ✅ Found existing transcript ({len(transcript_text)} chars)")
            return self._save_transcript_to_atlas(podcast_name, episode, transcript_text)

        # 2. Try to find transcript online (web scraping, etc.)
        transcript_text = self._fetch_transcript_from_web(episode)

        if transcript_text:
            log_info(self.log_path, f"   ✅ Fetched transcript from web ({len(transcript_text)} chars)")
            return self._save_transcript_to_atlas(podcast_name, episode, transcript_text)

        log_info(self.log_path, "   ⚠️  No transcript found for transcript-only episode")
        return False

    def _process_with_audio_download(self, podcast_name: str, episode: Dict[str, Any], audio_url: Optional[str]) -> bool:
        """Process episode that may need audio download for transcription"""
        log_info(self.log_path, f"   🎵 Audio processing: {episode['title'][:50]}...")

        # 1. First try to find existing transcript
        transcript_text = self._search_existing_transcript(episode)

        if transcript_text:
            log_info(self.log_path, "   ✅ Found existing transcript, skipping audio download")
            return self._save_transcript_to_atlas(podcast_name, episode, transcript_text)

        # 2. Audio download and transcription needed
        return self._queue_for_transcription(podcast_name, episode, audio_url)

    def _search_existing_transcript(self, episode: Dict[str, Any]) -> Optional[str]:
        """Search for existing transcripts in various locations"""
        # Search in Atlas database
        try:
            with sqlite3.connect(self.data_dir / "atlas.db") as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT content FROM content
                    WHERE url = ? AND content IS NOT NULL
                    AND length(content) > 1000
                """, (episode['url'],))

                result = cursor.fetchone()
                if result:
                    return result[0]

        except Exception as e:
            log_error(self.log_path, f"Error searching Atlas database: {e}")

        # Search in local transcript files
        transcript_dir = self.podcast_data_dir / "transcripts"
        if transcript_dir.exists():
            for transcript_file in transcript_dir.rglob("*.txt"):
                try:
                    with open(transcript_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if episode['title'][:20] in content or episode['url'] in content:
                            return content
                except Exception:
                    continue

        return None

    def _validate_transcript_quality(self, transcript: str, episode_title: str) -> Dict[str, Any]:
        """Validate transcript quality and completeness using character-per-minute heuristic"""
        length = len(transcript)
        word_count = len(transcript.split())
        sentences = transcript.count('.') + transcript.count('!') + transcript.count('?')

        # Character per minute heuristic (based on analysis of Lex Fridman episodes)
        # Conservative: ~1559 chars/minute for full transcripts

        # Check for obvious spam first (very specific patterns)
        spam_patterns = [
            "buy discount ozempic", "click this link now", "order cheap pills",
            "pharmacy discount", "viagra cialis", "weight loss pills"
        ]
        has_spam = any(pattern.lower() in transcript.lower() for pattern in spam_patterns)

        if has_spam:
            quality = "spam"
            reason = "Contains obvious spam content"
            score = 0
        elif length < 2000:
            quality = "very_poor"
            reason = "Too short - definitely not a full transcript"
            score = 1
        elif length < 15000:
            quality = "poor"
            reason = "Short - likely summary or excerpt (< 10 min episode)"
            score = 2
        elif length < 40000:
            quality = "medium"
            reason = "Medium - could be short episode (15-25 min)"
            score = 3
        elif length < 75000:
            quality = "good"
            reason = "Good length - likely 30-45 min episode"
            score = 4
        elif length < 110000:
            quality = "excellent"
            reason = "Very good - likely 45-70 min episode"
            score = 5
        else:
            quality = "excellent"
            reason = "Excellent - definitely full long-form episode (70+ min)"
            score = 5

        # Additional quality indicators
        chars_per_word = length / max(word_count, 1)
        estimated_duration_minutes = length / 1559  # Using our heuristic

        return {
            "quality": quality,
            "score": score,
            "reason": reason,
            "length": length,
            "word_count": word_count,
            "sentences": sentences,
            "chars_per_word": round(chars_per_word, 1),
            "estimated_minutes": round(estimated_duration_minutes, 1),
            "is_spam": has_spam
        }

    def _fetch_transcript_from_web(self, episode: Dict[str, Any]) -> Optional[str]:
        """Try to fetch transcript from web sources with quality validation"""
        try:
            # Import the transcript finder
            from universal_transcript_finder import UniversalTranscriptFinder
            finder = UniversalTranscriptFinder()

            # Extract podcast name from episode if available
            podcast_name = episode.get('podcast_name', '')

            log_info(self.log_path, "   🌐 Searching for transcript on web...")

            # Try universal transcript search
            transcript = finder.find_transcript_universal(
                podcast_name=podcast_name,
                episode_title=episode['title'],
                episode_url=episode['url'],
                audio_url=episode.get('audio_url')
            )

            if transcript:
                # Validate transcript quality
                quality_info = self._validate_transcript_quality(transcript, episode['title'])

                # Only accept good quality transcripts (score 3+)
                if quality_info['score'] >= 3:
                    log_info(self.log_path,
                        f"   ✅ Found {quality_info['quality']} transcript from web ({quality_info['length']} chars, {quality_info['word_count']} words)")
                    return transcript
                else:
                    log_info(self.log_path,
                        f"   ❌ Rejected transcript: {quality_info['quality']} ({quality_info['reason']}, {quality_info['length']} chars)")
                    return None
            else:
                log_info(self.log_path, "   ❌ No transcript found on web")
                return None

        except ImportError:
            log_error(self.log_path, "   ❌ UniversalTranscriptFinder not available")
            return None
        except Exception as e:
            log_error(self.log_path, f"   ❌ Error in web transcript search: {e}")
            return None

    def _save_transcript_to_atlas(self, podcast_name: str, episode: Dict[str, Any], transcript_text: str) -> bool:
        """Save transcript to Atlas database"""
        try:
            with sqlite3.connect(self.data_dir / "atlas.db") as conn:
                cursor = conn.cursor()

                # Create enhanced title for transcript
                title = f"[TRANSCRIPT] {episode['title']}"
                content = f"Podcast: {podcast_name}\n\n{transcript_text}"

                cursor.execute("""
                    INSERT OR REPLACE INTO content
                    (url, title, content, content_type, metadata, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    episode['url'],
                    title[:500],  # Limit title length
                    content,
                    'podcast',
                    json.dumps({
                        'podcast_name': podcast_name,
                        'episode_title': episode['title'],
                        'processing_type': 'transcript_only',
                        'processed_by': 'smart_transcription_pipeline'
                    }),
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))

                conn.commit()
                return True

        except Exception as e:
            log_error(self.log_path, f"Error saving transcript to Atlas: {e}")
            return False

    def _queue_for_transcription(self, podcast_name: str, episode: Dict[str, Any], audio_url: Optional[str]) -> bool:
        """Queue episode for audio download and Mac Mini transcription"""
        try:
            with sqlite3.connect(self.queue_db) as conn:
                cursor = conn.cursor()

                # Add to universal processing queue
                cursor.execute("""
                    INSERT OR IGNORE INTO processing_queue
                    (podcast_name, episode_title, episode_url, audio_url, needs_audio, processing_type)
                    VALUES (?, ?, ?, ?, 1, 'audio_transcription')
                """, (podcast_name, episode['title'], episode['url'], audio_url))

                conn.commit()

            log_info(self.log_path, f"   📋 Queued for transcription: {episode['title'][:50]}...")
            return True

        except Exception as e:
            log_error(self.log_path, f"Error queuing for transcription: {e}")
            return False

    def process_transcription_queue(self, max_concurrent: int = 2) -> int:
        """Process the transcription queue with Mac Mini integration"""
        log_info(self.log_path, "🔄 Processing transcription queue...")

        if not self.mac_mini_config.get('enabled', False):
            log_info(self.log_path, "Mac Mini transcription not enabled, skipping queue processing")
            return 0

        processed = 0

        try:
            with sqlite3.connect(self.queue_db) as conn:
                cursor = conn.cursor()

                # Get pending items from queue
                cursor.execute("""
                    SELECT id, podcast_name, episode_title, episode_url, audio_url
                    FROM processing_queue
                    WHERE status = 'pending' AND needs_audio = 1
                    ORDER BY priority DESC, created_at
                    LIMIT ?
                """, (max_concurrent,))

                items = cursor.fetchall()

                for item_id, podcast_name, episode_title, episode_url, audio_url in items:
                    try:
                        # Mark as processing
                        cursor.execute("""
                            UPDATE processing_queue
                            SET status = 'processing', started_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        """, (item_id,))
                        conn.commit()

                        # Process with Mac Mini
                        success = self._process_with_mac_mini(
                            podcast_name, episode_title, episode_url, audio_url
                        )

                        if success:
                            cursor.execute("""
                                UPDATE processing_queue
                                SET status = 'completed', completed_at = CURRENT_TIMESTAMP
                                WHERE id = ?
                            """, (item_id,))
                            processed += 1
                        else:
                            cursor.execute("""
                                UPDATE processing_queue
                                SET status = 'error', retry_count = retry_count + 1
                                WHERE id = ?
                            """, (item_id,))

                        conn.commit()

                    except Exception as e:
                        log_error(self.log_path, f"Error processing queue item {item_id}: {e}")

        except Exception as e:
            log_error(self.log_path, f"Error processing transcription queue: {e}")

        log_info(self.log_path, f"✅ Processed {processed} items from transcription queue")
        return processed

    def _process_with_mac_mini(self, podcast_name: str, episode_title: str,
                               episode_url: str, audio_url: str) -> bool:
        """Process episode with Mac Mini local transcription"""
        log_info(self.log_path, f"   🖥️  Mac Mini processing: {episode_title[:50]}...")

        try:
            # 1. Download audio if needed
            if not audio_url:
                audio_url = self._extract_audio_url(episode_url)
                if not audio_url:
                    log_error(self.log_path, f"Could not extract audio URL for {episode_title}")
                    return False

            # 2. Create Mac Mini transcription job
            mac_script = f"""
            cd /tmp/atlas-transcription
            curl -L -o "episode.mp3" "{audio_url}"
            whisper episode.mp3 --model {self.mac_mini_config['transcription_model']} --output_format txt
            cat episode.txt
            rm episode.mp3 episode.txt
            """

            # 3. Execute on Mac Mini via SSH
            ssh_command = [
                "ssh", "-i", os.path.expanduser(self.mac_mini_config['ssh_key']),
                f"{self.mac_mini_config['user']}@{self.mac_mini_config['host']}",
                mac_script
            ]

            result = subprocess.run(
                ssh_command,
                capture_output=True,
                text=True,
                timeout=1800  # 30 minute timeout
            )

            if result.returncode == 0 and result.stdout.strip():
                transcript_text = result.stdout.strip()
                log_info(self.log_path, f"   ✅ Mac Mini transcription complete ({len(transcript_text)} chars)")

                # Save transcript to Atlas
                return self._save_transcript_to_atlas(
                    podcast_name,
                    {'title': episode_title, 'url': episode_url},
                    transcript_text
                )
            else:
                log_error(self.log_path, f"Mac Mini transcription failed: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            log_error(self.log_path, f"Mac Mini transcription timed out for {episode_title}")
            return False
        except Exception as e:
            log_error(self.log_path, f"Mac Mini processing error: {e}")
            return False



    def get_queue_status(self) -> Dict[str, Any]:
        """Get status of the processing queue"""
        try:
            with sqlite3.connect(self.queue_db) as conn:
                cursor = conn.cursor()

                # Get counts by status
                cursor.execute("""
                    SELECT status, COUNT(*)
                    FROM processing_queue
                    GROUP BY status
                """)

                status_counts = dict(cursor.fetchall())

                # Get recent activity
                cursor.execute("""
                    SELECT podcast_name, episode_title, status, created_at
                    FROM processing_queue
                    ORDER BY created_at DESC
                    LIMIT 10
                """)

                recent_items = [
                    {
                        'podcast_name': row[0],
                        'episode_title': row[1],
                        'status': row[2],
                        'created_at': row[3]
                    }
                    for row in cursor.fetchall()
                ]

                return {
                    'status_counts': status_counts,
                    'recent_items': recent_items,
                    'mac_mini_enabled': self.mac_mini_config.get('enabled', False),
                    'prioritized_podcasts_count': len(self.prioritized_podcasts)
                }

        except Exception as e:
            log_error(self.log_path, f"Error getting queue status: {e}")
            return {'error': str(e)}

def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Smart Transcription Pipeline")
    parser.add_argument("--process-all", action="store_true", help="Process all prioritized podcasts")
    parser.add_argument("--process-queue", action="store_true", help="Process transcription queue")
    parser.add_argument("--status", action="store_true", help="Show queue status")
    parser.add_argument("--max-concurrent", type=int, default=2, help="Max concurrent transcription jobs")

    args = parser.parse_args()

    pipeline = SmartTranscriptionPipeline()

    if args.status:
        status = pipeline.get_queue_status()
        print("📊 Smart Transcription Pipeline Status:")
        print(json.dumps(status, indent=2, default=str))

    elif args.process_queue:
        processed = pipeline.process_transcription_queue(args.max_concurrent)
        print(f"✅ Processed {processed} items from queue")

    elif args.process_all:
        total = pipeline.process_prioritized_podcasts()
        print(f"✅ Processed {total} total episodes")

    else:
        parser.print_help()

if __name__ == "__main__":
    main()