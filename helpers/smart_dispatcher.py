"""
Atlas Smart Dispatcher - Decides what to process locally vs offload to Mac Mini
"""

import os
import json
import requests
from urllib.parse import urlparse
from typing import Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class SmartDispatcher:
    def __init__(self, config=None):
        self.config = config or {}
        self.mac_mini_available = self._check_mac_mini_availability()

        # Thresholds for offloading decisions
        self.video_duration_threshold = 600  # 10 minutes
        self.audio_size_threshold = 50 * 1024 * 1024  # 50MB
        self.always_offload_domains = {
            'youtube.com', 'youtu.be', 'vimeo.com',
            'soundcloud.com', 'anchor.fm'
        }

    def _check_mac_mini_availability(self) -> bool:
        """Check if Mac Mini worker is available"""
        try:
            # This would check worker status from database
            return True  # For now, assume available
        except:
            return False

    def should_offload_to_mac_mini(self, content_type: str, url: str, metadata: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Decide if content should be offloaded to Mac Mini
        Returns: (should_offload, reason)
        """
        if not self.mac_mini_available:
            return False, "Mac Mini not available"

        domain = urlparse(url).netloc.lower()

        # Always offload video content
        if content_type == 'youtube':
            duration = metadata.get('duration_seconds', 0)
            if duration > self.video_duration_threshold:
                return True, f"Long video ({duration}s) - save OCI storage & CPU"
            elif any(d in domain for d in self.always_offload_domains):
                return True, f"Video platform ({domain}) - better on Mac Mini"
            else:
                return True, "Video content - default to Mac Mini"

        # Audio content decisions
        if content_type == 'podcast':
            # Check if we have file size info
            file_size = metadata.get('file_size_bytes', 0)
            duration = metadata.get('duration_seconds', 0)

            if file_size > self.audio_size_threshold:
                return True, f"Large audio file ({file_size/1024/1024:.1f}MB)"
            elif duration > self.video_duration_threshold:
                return True, f"Long podcast ({duration/60:.1f}min) - heavy transcription"
            else:
                return False, "Small/medium podcast - process locally"

        # Audio files uploaded to Atlas
        if content_type == 'audio_file':
            return True, "Audio file - Mac Mini better for transcription"

        # Articles and text content - always process locally
        if content_type in ['article', 'text', 'webpage']:
            return False, "Text content - process immediately on Atlas"

        # RSS feeds and metadata - always local
        if content_type in ['rss', 'feed', 'metadata']:
            return False, "Metadata/RSS - lightweight local processing"

        # Unknown content - be conservative, process locally
        return False, f"Unknown content type ({content_type}) - process locally"

    def dispatch_content(self, content_type: str, url: str, metadata: Dict[str, Any], content: str = None) -> Dict[str, Any]:
        """
        Main dispatcher - decides how to handle content
        """
        should_offload, reason = self.should_offload_to_mac_mini(content_type, url, metadata)

        result = {
            'action': 'offload' if should_offload else 'process_local',
            'reason': reason,
            'content_type': content_type,
            'url': url,
            'metadata_stored': False,
            'job_queued': False,
            'processed_locally': False
        }

        try:
            if should_offload:
                # Store metadata immediately, queue job for Mac Mini
                result.update(self._offload_to_mac_mini(content_type, url, metadata))
            else:
                # Process locally on Atlas
                result.update(self._process_locally(content_type, url, metadata, content))

        except Exception as e:
            logger.error(f"Dispatch error for {url}: {e}")
            result['error'] = str(e)

        return result

    def _offload_to_mac_mini(self, content_type: str, url: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Handle offloading to Mac Mini"""
        from helpers.simple_database import SimpleDatabase

        # Always store metadata first - never lose information
        db = SimpleDatabase()

        # Store basic content record with metadata
        content_id = db.store_content(
            content="[Queued for Mac Mini transcription]",
            title=metadata.get('title', 'Unknown'),
            url=url,
            content_type=f"{content_type}_queued",
            metadata={
                **metadata,
                'status': 'queued_for_worker',
                'worker_type': 'mac_mini',
                'queued_at': db._get_current_timestamp()
            }
        )

        # Create worker job
        job_data = self._create_worker_job(content_type, url, metadata, content_id)
        job_id = self._queue_worker_job(job_data)

        return {
            'metadata_stored': True,
            'content_id': content_id,
            'job_queued': True,
            'job_id': job_id,
            'worker_type': 'mac_mini'
        }

    def _process_locally(self, content_type: str, url: str, metadata: Dict[str, Any], content: str) -> Dict[str, Any]:
        """Handle local processing on Atlas"""
        from helpers.content_pipeline import ContentPipeline

        # Use existing Atlas content pipeline
        pipeline = ContentPipeline(self.config)

        result = pipeline.process_content(
            content=content or "",
            title=metadata.get('title', ''),
            url=url,
            metadata=metadata
        )

        return {
            'processed_locally': True,
            'pipeline_result': result,
            'content_id': result.get('content_id')
        }

    def _create_worker_job(self, content_type: str, url: str, metadata: Dict[str, Any], content_id: str) -> Dict[str, Any]:
        """Create worker job data"""
        job_type_mapping = {
            'youtube': 'transcribe_youtube',
            'podcast': 'transcribe_podcast',
            'audio_file': 'transcribe_audio_file'
        }

        job_type = job_type_mapping.get(content_type, 'transcribe_generic')

        return {
            'type': job_type,
            'data': {
                'url': url,
                'title': metadata.get('title', 'Unknown'),
                'content_type': content_type,
                'metadata': metadata,
                'atlas_content_id': content_id,
                'estimated_duration': metadata.get('duration_seconds', 0),
                'file_size': metadata.get('file_size_bytes', 0)
            },
            'priority': self._calculate_job_priority(content_type, metadata),
            'created_by': 'atlas_dispatcher'
        }

    def _calculate_job_priority(self, content_type: str, metadata: Dict[str, Any]) -> int:
        """Calculate job priority (1-10, higher = more urgent)"""
        base_priority = {
            'youtube': 3,      # Not urgent
            'podcast': 4,      # Somewhat important
            'audio_file': 7    # User uploaded - more urgent
        }.get(content_type, 5)

        # Boost priority for shorter content (faster to process)
        duration = metadata.get('duration_seconds', 0)
        if duration < 300:  # 5 minutes
            base_priority += 2
        elif duration > 3600:  # 1 hour
            base_priority -= 1

        return max(1, min(10, base_priority))

    def _queue_worker_job(self, job_data: Dict[str, Any]) -> str:
        """Queue job for worker"""
        try:
            import uuid
            from helpers.simple_database import SimpleDatabase

            job_id = str(uuid.uuid4())

            db = SimpleDatabase()
            conn = db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO worker_jobs (id, type, data, priority, status, created_at)
                VALUES (?, ?, ?, ?, 'pending', ?)
            """, (
                job_id,
                job_data['type'],
                json.dumps(job_data['data']),
                job_data['priority'],
                db._get_current_timestamp()
            ))

            conn.commit()
            conn.close()

            logger.info(f"Queued worker job {job_id}: {job_data['type']}")
            return job_id

        except Exception as e:
            logger.error(f"Failed to queue worker job: {e}")
            return None

    def get_dispatch_stats(self) -> Dict[str, Any]:
        """Get statistics about dispatch decisions"""
        try:
            from helpers.simple_database import SimpleDatabase

            db = SimpleDatabase()
            conn = db.get_connection()
            cursor = conn.cursor()

            # Content processed locally vs queued
            cursor.execute("""
                SELECT
                    CASE WHEN content_type LIKE '%_queued' THEN 'queued_for_worker'
                         ELSE 'processed_locally' END as processing_type,
                    COUNT(*)
                FROM content
                WHERE created_at > datetime('now', '-7 days')
                GROUP BY processing_type
            """)

            processing_stats = dict(cursor.fetchall())

            # Worker job stats
            cursor.execute("""
                SELECT status, COUNT(*)
                FROM worker_jobs
                WHERE created_at > datetime('now', '-7 days')
                GROUP BY status
            """)

            job_stats = dict(cursor.fetchall())

            conn.close()

            return {
                'processing_stats': processing_stats,
                'job_stats': job_stats,
                'mac_mini_available': self.mac_mini_available,
                'offload_thresholds': {
                    'video_duration_minutes': self.video_duration_threshold / 60,
                    'audio_size_mb': self.audio_size_threshold / (1024 * 1024),
                    'always_offload_domains': list(self.always_offload_domains)
                }
            }

        except Exception as e:
            logger.error(f"Error getting dispatch stats: {e}")
            return {'error': str(e)}