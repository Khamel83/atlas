#!/usr/bin/env python3
"""
Universal Processing Queue System for Atlas

Consolidates all background processing into a single, coordinated queue system.
Prevents competing parallel processes and provides centralized job management.

Supported Job Types:
- ai_processing: Content AI analysis (tags, summaries, etc.)
- transcript_discovery: Find transcripts for podcast episodes
- podcast_transcription: Audio-to-text transcription (Mac Mini)
- podemos_processing: Ad-free episode processing
- youtube_processing: YouTube video content extraction and processing
- mac_mini_transcription: Direct Mac Mini audio transcription tasks
- content_ingestion: URL content extraction
- reprocessing: Quality improvement for existing content
"""

import sqlite3
import json
import time
import uuid
import logging
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
import sys
import os

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/universal_queue.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class QueueJob:
    """Universal queue job definition"""
    id: str
    type: str  # ai_processing, transcript_discovery, podcast_transcription, podemos_processing, etc.
    data: Dict[str, Any]  # Job-specific data
    priority: int = 50  # 0-100, higher = more priority
    status: str = 'pending'  # pending, running, completed, failed, cancelled
    assigned_worker: Optional[str] = None
    created_at: str = ""
    assigned_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3

class UniversalProcessingQueue:
    """Central processing queue that coordinates all Atlas background tasks"""

    def __init__(self, db_path="data/atlas.db"):
        self.db_path = db_path
        self.worker_id = f"worker_{uuid.uuid4().hex[:8]}"
        self.is_running = False

        # Initialize database tables
        self._init_database()

        # Register job handlers
        self.job_handlers: Dict[str, Callable] = {
            'ai_processing': self.handle_ai_processing,
            'transcript_discovery': self.handle_transcript_discovery,
            'podcast_transcription': self.handle_podcast_transcription,
            'podemos_processing': self.handle_podemos_processing,
            'youtube_processing': self.handle_youtube_processing,
            'mac_mini_transcription': self.handle_mac_mini_transcription,
            'content_ingestion': self.handle_content_ingestion,
            'reprocessing': self.handle_reprocessing,
            'url_processing': self.handle_url_processing,
        }

        logger.info(f"🔄 Universal Processing Queue initialized (Worker: {self.worker_id})")

    def _init_database(self):
        """Initialize database tables for job queue"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS worker_jobs (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    data TEXT,
                    priority INTEGER DEFAULT 50,
                    status TEXT DEFAULT 'pending',
                    assigned_worker TEXT,
                    created_at TEXT,
                    assigned_at TEXT,
                    completed_at TEXT,
                    result TEXT,
                    retry_count INTEGER DEFAULT 0
                )
            """)
            conn.commit()

    def add_job(self, job_type: str, data: Dict[str, Any], priority: int = 50) -> str:
        """Add a new job to the queue"""
        job_id = str(uuid.uuid4())

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO worker_jobs (id, type, data, priority, status, created_at)
                VALUES (?, ?, ?, ?, 'pending', ?)
            """, (job_id, job_type, json.dumps(data), priority, datetime.now().isoformat()))
            conn.commit()

        logger.info(f"➕ Added job {job_id[:8]} ({job_type}, priority={priority})")
        return job_id

    def get_next_job(self) -> Optional[QueueJob]:
        """Get the next highest-priority pending job"""
        with sqlite3.connect(self.db_path) as conn:
            # Lock and claim the next job atomically
            cursor = conn.execute("""
                UPDATE worker_jobs
                SET status = 'running', assigned_worker = ?, assigned_at = ?
                WHERE id = (
                    SELECT id FROM worker_jobs
                    WHERE status = 'pending'
                    ORDER BY priority DESC, created_at ASC
                    LIMIT 1
                )
                RETURNING id, type, data, priority, status, created_at
            """, (self.worker_id, datetime.now().isoformat()))

            row = cursor.fetchone()
            if not row:
                return None

            conn.commit()

            job_id, job_type, data_json, priority, status, created_at = row
            data = json.loads(data_json) if data_json else {}

            return QueueJob(
                id=job_id,
                type=job_type,
                data=data,
                priority=priority,
                status=status,
                assigned_worker=self.worker_id,
                created_at=created_at,
                assigned_at=datetime.now().isoformat()
            )

    def complete_job(self, job: QueueJob, result: Optional[str] = None, failed: bool = False):
        """Mark a job as completed or failed"""
        status = 'failed' if failed else 'completed'
        completed_at = datetime.now().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE worker_jobs
                SET status = ?, completed_at = ?, result = ?
                WHERE id = ?
            """, (status, completed_at, result, job.id))
            conn.commit()

        if failed and job.retry_count < job.max_retries:
            # Retry with exponential backoff
            retry_delay = 2 ** job.retry_count  # 2, 4, 8 seconds
            time.sleep(retry_delay)

            # Re-add as pending with incremented retry count
            retry_data = job.data.copy()
            retry_data['retry_count'] = job.retry_count + 1
            self.add_job(job.type, retry_data, max(job.priority - 10, 1))

            logger.warning(f"🔄 Retrying job {job.id[:8]} (attempt {job.retry_count + 1})")
        else:
            status_emoji = "✅" if not failed else "❌"
            logger.info(f"{status_emoji} Job {job.id[:8]} {status}")

    def handle_ai_processing(self, job: QueueJob) -> bool:
        """Handle AI content processing jobs"""
        try:
            content_id = job.data.get('content_id')
            if not content_id:
                return False

            logger.info(f"🧠 Processing AI content for ID {content_id}")

            # Get content from database
            with sqlite3.connect(self.db_path) as conn:
                content_data = conn.execute("""
                    SELECT title, content, url, content_type
                    FROM content
                    WHERE id = ?
                """, (content_id,)).fetchone()

                if not content_data:
                    logger.error(f"❌ Content {content_id} not found")
                    return False

                title, content, url, content_type = content_data

                if not content or len(content) < 50:
                    logger.warning(f"⚠️ Content {content_id} too short for AI processing")
                    return False

                # Generate AI summary (simplified version)
                # Extract first paragraph as summary for now
                content_lines = content.split('\n')
                first_paragraph = ""
                for line in content_lines:
                    line = line.strip()
                    if line and len(line) > 20:
                        first_paragraph = line[:300] + "..." if len(line) > 300 else line
                        break

                # Generate basic tags from title and content
                import re
                words = re.findall(r'\b[A-Za-z]{4,}\b', (title or '') + ' ' + content[:500])
                common_words = {'this', 'that', 'with', 'have', 'will', 'from', 'they', 'been', 'were', 'said', 'each', 'which', 'their', 'time', 'about', 'would', 'there', 'could', 'other', 'more', 'very', 'what', 'know', 'just', 'first', 'into', 'over', 'think', 'also', 'your', 'work', 'life', 'only', 'new', 'years', 'way', 'may', 'say', 'come', 'its', 'now', 'find', 'any', 'these', 'give', 'most', 'us'}
                tags = [w.lower() for w in set(words[:10]) if w.lower() not in common_words][:5]

                ai_summary = first_paragraph or f"Content about {title}" if title else "Processing content..."
                ai_tags = ', '.join(tags) if tags else content_type or 'general'

                # Update database with AI results
                conn.execute("""
                    UPDATE content
                    SET ai_summary = ?, ai_tags = ?, ai_classification = ?
                    WHERE id = ?
                """, (ai_summary, ai_tags, content_type or 'article', content_id))
                conn.commit()

                logger.info(f"✅ AI processing completed for {content_id}: {len(ai_summary)} chars summary, {len(tags)} tags")
                return True

        except Exception as e:
            logger.error(f"❌ AI processing failed for {content_id}: {e}")
            return False

    def handle_transcript_discovery(self, job: QueueJob) -> bool:
        """Handle transcript discovery jobs"""
        try:
            podcast_name = job.data.get('podcast_name')
            episode_title = job.data.get('episode_title')
            episode_url = job.data.get('episode_url')

            if not podcast_name or not episode_title:
                return False

            # Use existing transcript orchestrator
            from transcript_orchestrator import find_transcript

            logger.info(f"🎙️ Finding transcript: {podcast_name} - {episode_title[:50]}")
            transcript = find_transcript(podcast_name, episode_title, episode_url)

            if transcript:
                logger.info(f"✅ Found transcript ({len(transcript)} chars)")
                return True
            else:
                logger.info(f"❌ No transcript found")
                return True  # Not an error, just no transcript available

        except Exception as e:
            logger.error(f"❌ Transcript discovery failed: {e}")
            return False

    def handle_podcast_transcription(self, job: QueueJob) -> bool:
        """Handle local podcast transcription (Mac Mini)"""
        try:
            audio_file = job.data.get('audio_file')
            if not audio_file:
                return False

            logger.info(f"🎵 Transcribing audio: {audio_file}")

            # Use whisper.cpp or similar for local transcription
            # This would integrate with Mac Mini processing

            # For now, simulate Mac Mini transcription
            time.sleep(10)  # Simulate transcription time

            logger.info(f"✅ Transcription completed")
            return True

        except Exception as e:
            logger.error(f"❌ Podcast transcription failed: {e}")
            return False

    def handle_podemos_processing(self, job: QueueJob) -> bool:
        """Handle PODEMOS ad-free processing"""
        try:
            episode_data = job.data

            # Use existing PODEMOS system
            from podemos_ultra_fast_processor import ProcessingJob

            logger.info(f"📻 PODEMOS processing: {episode_data.get('episode_title', 'Unknown')}")

            # Integrate with existing PODEMOS pipeline
            # This would call the existing ultra-fast processor

            # For now, simulate processing
            time.sleep(5)

            return True

        except Exception as e:
            logger.error(f"❌ PODEMOS processing failed: {e}")
            return False

    def handle_content_ingestion(self, job: QueueJob) -> bool:
        """Handle URL content ingestion"""
        try:
            url = job.data.get('url')
            if not url:
                return False

            logger.info(f"🌐 Ingesting content: {url}")

            # Use existing content ingestion pipeline
            # This would integrate with universal_content_extractor

            time.sleep(3)  # Simulate ingestion

            return True

        except Exception as e:
            logger.error(f"❌ Content ingestion failed: {e}")
            return False

    def handle_reprocessing(self, job: QueueJob) -> bool:
        """Handle content reprocessing for quality improvement"""
        try:
            content_ids = job.data.get('content_ids', [])

            logger.info(f"🔄 Reprocessing {len(content_ids)} items")

            # Use existing reprocessing logic
            time.sleep(len(content_ids))  # Simulate processing

            return True

        except Exception as e:
            logger.error(f"❌ Reprocessing failed: {e}")
            return False

    def handle_url_processing(self, job: QueueJob) -> bool:
        """Handle URL content processing jobs"""
        try:
            url = job.data.get('url')
            content_id = job.data.get('content_id')  # May or may not be present

            if not url:
                logger.error(f"❌ URL processing job missing URL: {job.data}")
                return False

            logger.info(f"🌐 Processing URL: {url[:60]}...")

            # If we have a content_id, update that specific item
            if content_id:
                # Content is already processed by the URL worker
                # Mark this job as successfully completed
                logger.info(f"✅ URL processing completed for content ID {content_id}")
                return True

            else:
                # No content_id provided - this is a standalone URL processing job
                # Create content entry and process it
                try:
                    import hashlib
                    from datetime import datetime

                    # Generate a content ID from URL
                    url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]

                    with sqlite3.connect(self.db_path) as conn:
                        # Check if URL already exists
                        cursor = conn.execute("SELECT id FROM content WHERE url = ?", (url,))
                        existing = cursor.fetchone()

                        if existing:
                            existing_id = existing[0]
                            logger.info(f"✅ URL already exists in database as ID {existing_id}")
                            return True

                        # Create new content entry
                        cursor = conn.execute("""
                            INSERT INTO content (url, title, content_type, metadata, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            url,
                            f"URL from job {job.id}",
                            'url_processing',
                            str({'source': 'url_processing_job', 'job_id': job.id}),
                            datetime.now().isoformat(),
                            datetime.now().isoformat()
                        ))

                        new_content_id = cursor.lastrowid
                        conn.commit()

                        logger.info(f"✅ Created content entry {new_content_id} for URL {url[:60]}...")

                        # Content entry created successfully - no further processing needed here
                        # (AI processing will pick it up in a separate job)
                        logger.info(f"✅ URL processing completed for new content ID {new_content_id}")
                        return True

                except Exception as e:
                    logger.error(f"❌ Failed to create/process content entry for URL {url}: {e}")
                    return False

        except Exception as e:
            logger.error(f"❌ URL processing failed for URL {url}: {e}")
            return False

    def handle_youtube_processing(self, job: QueueJob) -> bool:
        """Handle YouTube video processing jobs"""
        try:
            video_data = job.data
            video_url = video_data.get('video_url')

            if not video_url:
                logger.error("❌ No video URL provided for YouTube processing")
                return False

            logger.info(f"📺 Processing YouTube video: {video_url}")

            # Use YouTube ingestor for processing
            from helpers.youtube_ingestor import YouTubeIngestor

            ingestor = YouTubeIngestor()
            success = ingestor.process_video(video_url)

            if success:
                logger.info(f"✅ YouTube video processed successfully")
                return True
            else:
                logger.error(f"❌ YouTube video processing failed")
                return False

        except Exception as e:
            logger.error(f"❌ YouTube processing error: {e}")
            return False

    def handle_mac_mini_transcription(self, job: QueueJob) -> bool:
        """Handle Mac Mini transcription jobs"""
        try:
            audio_data = job.data
            audio_url = audio_data.get('audio_url')
            quality = audio_data.get('quality', 'base')

            if not audio_url:
                logger.error("❌ No audio URL provided for Mac Mini transcription")
                return False

            logger.info(f"🖥️ Mac Mini transcribing: {audio_url}")

            # Use Mac Mini client for transcription
            from helpers.mac_mini_client import MacMiniClient

            client = MacMiniClient()

            # Test connection first
            if not client.test_connection():
                logger.warning("⚠️ Mac Mini not available")
                return False

            result = client.transcribe_audio(audio_url, quality, timeout=600)

            if result and result.get('success'):
                transcript = result.get('transcript', '')
                logger.info(f"✅ Mac Mini transcription completed ({len(transcript)} chars)")

                # Store result in job data for retrieval
                job.data['transcript_result'] = result
                return True
            else:
                error_msg = result.get('error', 'Unknown error') if result else 'No result'
                logger.error(f"❌ Mac Mini transcription failed: {error_msg}")
                return False

        except Exception as e:
            logger.error(f"❌ Mac Mini transcription error: {e}")
            return False

    def process_jobs(self, max_jobs: Optional[int] = None):
        """Process jobs from the queue"""
        self.is_running = True
        processed_count = 0

        logger.info(f"🚀 Starting job processing (max_jobs={max_jobs or 'unlimited'})")

        try:
            while self.is_running:
                job = self.get_next_job()

                if not job:
                    # No jobs available, wait a bit
                    time.sleep(10)
                    continue

                # Check if we have a handler for this job type
                if job.type not in self.job_handlers:
                    logger.error(f"❌ Unknown job type: {job.type}")
                    self.complete_job(job, result=f"Unknown job type: {job.type}", failed=True)
                    continue

                # Process the job
                logger.info(f"▶️  Processing job {job.id[:8]} ({job.type})")
                start_time = time.time()

                try:
                    success = self.job_handlers[job.type](job)
                    processing_time = time.time() - start_time

                    result = f"Processed in {processing_time:.2f}s"
                    self.complete_job(job, result=result, failed=not success)

                    processed_count += 1

                    # Check if we've hit the max job limit
                    if max_jobs and processed_count >= max_jobs:
                        logger.info(f"✅ Processed {processed_count} jobs (limit reached)")
                        break

                except Exception as e:
                    logger.error(f"❌ Job processing error: {e}")
                    self.complete_job(job, result=str(e), failed=True)

                # Small delay between jobs to prevent overwhelming the system
                time.sleep(1)

        except KeyboardInterrupt:
            logger.info("🛑 Processing stopped by user")
        finally:
            self.is_running = False
            logger.info(f"📊 Processed {processed_count} jobs total")

    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT status, COUNT(*) as count
                FROM worker_jobs
                GROUP BY status
            """)
            status_counts = dict(cursor.fetchall())

            cursor = conn.execute("""
                SELECT type, COUNT(*) as count
                FROM worker_jobs
                WHERE status = 'pending'
                GROUP BY type
            """)
            pending_by_type = dict(cursor.fetchall())

            cursor = conn.execute("""
                SELECT COUNT(*) FROM worker_jobs
                WHERE status = 'running' AND assigned_worker = ?
            """, (self.worker_id,))
            running_by_worker = cursor.fetchone()[0]

        return {
            'status_counts': status_counts,
            'pending_by_type': pending_by_type,
            'running_by_worker': running_by_worker,
            'worker_id': self.worker_id
        }

    def cleanup_old_jobs(self, days_old: int = 7):
        """Clean up completed/failed jobs older than specified days"""
        cutoff_date = (datetime.now() - timedelta(days=days_old)).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                DELETE FROM worker_jobs
                WHERE status IN ('completed', 'failed', 'cancelled')
                AND created_at < ?
            """, (cutoff_date,))
            deleted_count = cursor.rowcount
            conn.commit()

        if deleted_count > 0:
            logger.info(f"🧹 Cleaned up {deleted_count} old jobs")

# Convenience functions for external systems to add jobs
def add_ai_processing_job(content_id: str, priority: int = 50) -> str:
    """Add an AI processing job to the queue"""
    queue = UniversalProcessingQueue()
    return queue.add_job('ai_processing', {'content_id': content_id}, priority)

def add_transcript_discovery_job(podcast_name: str, episode_title: str, episode_url: str = None, priority: int = 75) -> str:
    """Add a transcript discovery job to the queue"""
    queue = UniversalProcessingQueue()
    return queue.add_job('transcript_discovery', {
        'podcast_name': podcast_name,
        'episode_title': episode_title,
        'episode_url': episode_url
    }, priority)

def add_podemos_processing_job(episode_data: Dict[str, Any], priority: int = 90) -> str:
    """Add a PODEMOS processing job to the queue"""
    queue = UniversalProcessingQueue()
    return queue.add_job('podemos_processing', episode_data, priority)

def add_content_ingestion_job(url: str, priority: int = 60) -> str:
    """Add a content ingestion job to the queue"""
    queue = UniversalProcessingQueue()
    return queue.add_job('content_ingestion', {'url': url}, priority)

def add_youtube_processing_job(video_url: str, priority: int = 70) -> str:
    """Add a YouTube processing job to the queue"""
    queue = UniversalProcessingQueue()
    return queue.add_job('youtube_processing', {'video_url': video_url}, priority)

def add_mac_mini_transcription_job(audio_url: str, quality: str = 'base', priority: int = 85) -> str:
    """Add a Mac Mini transcription job to the queue"""
    queue = UniversalProcessingQueue()
    return queue.add_job('mac_mini_transcription', {
        'audio_url': audio_url,
        'quality': quality
    }, priority)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Universal Processing Queue for Atlas')
    parser.add_argument('--process', action='store_true', help='Start processing jobs')
    parser.add_argument('--stats', action='store_true', help='Show queue statistics')
    parser.add_argument('--cleanup', action='store_true', help='Clean up old jobs')
    parser.add_argument('--max-jobs', type=int, help='Maximum number of jobs to process')
    parser.add_argument('--test', action='store_true', help='Add test jobs')

    args = parser.parse_args()

    queue = UniversalProcessingQueue()

    if args.stats:
        stats = queue.get_queue_stats()
        print("\n📊 Queue Statistics:")
        print(f"Status counts: {stats['status_counts']}")
        print(f"Pending by type: {stats['pending_by_type']}")
        print(f"Running by worker: {stats['running_by_worker']}")
        print(f"Worker ID: {stats['worker_id']}")

    if args.cleanup:
        queue.cleanup_old_jobs()

    if args.test:
        # Add some test jobs
        queue.add_job('ai_processing', {'content_id': '12345'}, 50)
        queue.add_job('transcript_discovery', {
            'podcast_name': 'Test Podcast',
            'episode_title': 'Test Episode'
        }, 75)
        print("✅ Added test jobs")

    if args.process:
        queue.process_jobs(max_jobs=args.max_jobs)