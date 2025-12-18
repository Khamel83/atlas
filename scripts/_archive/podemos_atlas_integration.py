#!/usr/bin/env python3
"""
PODEMOS Atlas Integration

Integrates PODEMOS real-time podcast system with Atlas infrastructure.
Shares universal processing queue, configuration, and resource management.
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ingest.queue.processing_queue import ProcessingQueue, Priority
from helpers.database_manager import DatabaseManager
from helpers.config import load_config
from helpers.bulletproof_process_manager import create_managed_process

logger = logging.getLogger(__name__)

class PodemosPodcastItem:
    """Extended queue item for podcast processing"""

    def __init__(self, podcast_name: str, episode_title: str, episode_url: str,
                 transcript_only: bool = False, priority: str = "medium"):
        self.podcast_name = podcast_name
        self.episode_title = episode_title
        self.episode_url = episode_url
        self.transcript_only = transcript_only
        self.priority = self._parse_priority(priority)
        self.item_type = "podcast_episode"

        # Generate unique capture_id
        import hashlib
        self.capture_id = f"podemos_{hashlib.md5(episode_url.encode()).hexdigest()[:8]}"

        # User context for Atlas integration
        self.user_context = {
            "podcast_name": podcast_name,
            "episode_title": episode_title,
            "transcript_only": transcript_only,
            "processing_type": "podemos_realtime",
            "target_latency": 1200  # 20 minutes max
        }

    def _parse_priority(self, priority: str) -> Priority:
        """Convert string priority to Priority enum"""
        priority_map = {
            "critical": Priority.CRITICAL,
            "high": Priority.HIGH,
            "medium": Priority.MEDIUM,
            "low": Priority.LOW
        }
        return priority_map.get(priority.lower(), Priority.MEDIUM)

class AtlasIntegratedQueue:
    """Atlas-integrated processing queue for PODEMOS"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or load_config()
        self.atlas_queue = ProcessingQueue(config)
        self.db_manager = DatabaseManager()

        # PODEMOS-specific configuration
        self.podemos_config = self._load_podemos_config()
        self.mac_mini_config = self._load_mac_mini_config()

        # Processing coordination
        self.max_concurrent_transcriptions = self.mac_mini_config.get("concurrent_jobs", 2)
        self.processing_timeout = self.mac_mini_config.get("timeout_minutes", 30)

    def _load_podemos_config(self) -> Dict:
        """Load PODEMOS feed configuration"""
        config_path = "config/podemos_feeds.json"
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return json.load(f)
        return {"feeds": {}, "server_config": {}}

    def _load_mac_mini_config(self) -> Dict:
        """Load Mac Mini configuration"""
        config_path = "config/mac_mini.json"
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return json.load(f)

        # Default config
        return {
            "enabled": False,
            "host": "mac-mini.local",
            "user": "atlas",
            "concurrent_jobs": 2,
            "timeout_minutes": 30,
            "transcription_model": "large-v3"
        }

    async def add_podcast_episode(self, podcast_item: PodemosPodcastItem) -> bool:
        """Add podcast episode to unified processing queue"""

        # Check if already processed
        if await self._is_episode_processed(podcast_item.episode_url):
            logger.info(f"Episode already processed: {podcast_item.episode_title}")
            return False

        # Add to Atlas processing queue
        success = self.atlas_queue.add_to_queue(
            capture_id=podcast_item.capture_id,
            item_type=podcast_item.item_type,
            source="podemos_monitor",
            user_context=podcast_item.user_context,
            priority=podcast_item.priority
        )

        if success:
            logger.info(f"Added episode to Atlas queue: {podcast_item.episode_title}")

            # Log to PODEMOS processing log
            await self._log_episode_queued(podcast_item)

        return success

    async def get_next_podcast_episode(self, processor_id: str = None) -> Optional[Dict]:
        """Get next podcast episode from Atlas queue"""

        # Get next podcast episode from queue
        queue_item = self.atlas_queue.get_next_item(
            item_types=["podcast_episode"],
            processor_id=processor_id
        )

        if not queue_item:
            return None

        # Convert to PODEMOS processing format
        return {
            "capture_id": queue_item.capture_id,
            "podcast_name": queue_item.user_context.get("podcast_name"),
            "episode_title": queue_item.user_context.get("episode_title"),
            "episode_url": queue_item.source,
            "transcript_only": queue_item.user_context.get("transcript_only", False),
            "priority": queue_item.priority.name,
            "processor_id": queue_item.processor_id,
            "processing_started": queue_item.processing_started,
            "user_context": queue_item.user_context
        }

    async def mark_episode_complete(self, capture_id: str, result_data: Dict) -> bool:
        """Mark episode as completed in Atlas queue"""

        # Prepare result paths for Atlas
        result_paths = {}
        if result_data.get("clean_audio_path"):
            result_paths["clean_audio"] = result_data["clean_audio_path"]
        if result_data.get("transcript_path"):
            result_paths["transcript"] = result_data["transcript_path"]

        # Mark complete in Atlas queue
        success = self.atlas_queue.mark_complete(capture_id, result_paths)

        if success:
            # Save episode data to Atlas database
            await self._save_episode_to_atlas(capture_id, result_data)

            # Log completion
            await self._log_episode_completed(capture_id, result_data)

        return success

    async def mark_episode_failed(self, capture_id: str, error: str) -> bool:
        """Mark episode as failed in Atlas queue"""

        success = self.atlas_queue.mark_failed(capture_id, error)

        if success:
            await self._log_episode_failed(capture_id, error)

        return success

    async def get_processing_status(self) -> Dict:
        """Get comprehensive processing status"""

        # Get Atlas queue status
        atlas_status = self.atlas_queue.get_queue_status()

        # Get PODEMOS-specific stats
        podemos_stats = await self._get_podemos_stats()

        # Mac Mini status
        mac_mini_status = await self._check_mac_mini_status()

        return {
            "atlas_queue": atlas_status,
            "podemos": podemos_stats,
            "mac_mini": mac_mini_status,
            "active_processors": await self._count_active_processors(),
            "timestamp": datetime.now().isoformat()
        }

    async def _is_episode_processed(self, episode_url: str) -> bool:
        """Check if episode already processed"""
        query = """
            SELECT COUNT(*) FROM content
            WHERE url = ? AND content_type IN ('podcast', 'podcast_clean')
        """
        result = await self.db_manager.execute_query(query, (episode_url,))
        return result[0][0] > 0 if result else False

    async def _save_episode_to_atlas(self, capture_id: str, result_data: Dict):
        """Save processed episode to Atlas database"""

        # Prepare content data
        content_data = {
            "title": f"[CLEAN] {result_data.get('episode_title', 'Unknown')}",
            "content": result_data.get("transcript", ""),
            "url": result_data.get("episode_url", ""),
            "content_type": "podcast_clean",
            "metadata": json.dumps({
                "podcast_name": result_data.get("podcast_name"),
                "original_duration": result_data.get("original_duration"),
                "clean_duration": result_data.get("clean_duration"),
                "ads_removed": result_data.get("ads_removed", 0),
                "processing_time": result_data.get("processing_time"),
                "clean_audio_url": result_data.get("clean_audio_url"),
                "podemos_processed": True,
                "capture_id": capture_id,
                "processed_at": datetime.now().isoformat()
            })
        }

        # Insert into Atlas database
        insert_query = """
            INSERT INTO content (title, content, url, content_type, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """

        await self.db_manager.execute_query(
            insert_query,
            (
                content_data["title"],
                content_data["content"],
                content_data["url"],
                content_data["content_type"],
                content_data["metadata"],
                datetime.now().isoformat()
            )
        )

        logger.info(f"Saved clean episode to Atlas: {content_data['title']}")

    async def _get_podemos_stats(self) -> Dict:
        """Get PODEMOS-specific statistics"""

        # Count clean episodes
        clean_count_query = """
            SELECT COUNT(*) FROM content
            WHERE content_type = 'podcast_clean'
            AND JSON_EXTRACT(metadata, '$.podemos_processed') = 1
        """
        clean_count = await self.db_manager.execute_query(clean_count_query)

        # Count episodes by podcast
        podcast_count_query = """
            SELECT JSON_EXTRACT(metadata, '$.podcast_name') as podcast, COUNT(*) as count
            FROM content
            WHERE content_type = 'podcast_clean'
            AND JSON_EXTRACT(metadata, '$.podemos_processed') = 1
            GROUP BY podcast
        """
        podcast_counts = await self.db_manager.execute_query(podcast_count_query)

        return {
            "total_clean_episodes": clean_count[0][0] if clean_count else 0,
            "podcast_counts": dict(podcast_counts) if podcast_counts else {},
            "feeds_configured": len(self.podemos_config.get("feeds", {})),
            "mac_mini_enabled": self.mac_mini_config.get("enabled", False)
        }

    async def _check_mac_mini_status(self) -> Dict:
        """Check Mac Mini availability"""

        if not self.mac_mini_config.get("enabled", False):
            return {"status": "disabled"}

        try:
            # Test SSH connection
            host = self.mac_mini_config.get("host", "mac-mini.local")
            user = self.mac_mini_config.get("user", "atlas")

            # Use bulletproof process manager for SSH test
            ssh_test = await create_managed_process(
                f"ssh -o ConnectTimeout=5 {user}@{host} 'echo connected'",
                operation_name="mac_mini_ssh_test",
                timeout=10
            )

            if ssh_test and "connected" in str(ssh_test):
                return {
                    "status": "connected",
                    "host": host,
                    "concurrent_jobs": self.max_concurrent_transcriptions,
                    "timeout_minutes": self.processing_timeout
                }
            else:
                return {"status": "connection_failed", "host": host}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _count_active_processors(self) -> int:
        """Count active podcast processors"""

        # Count items currently being processed
        queue_status = self.atlas_queue.get_queue_status()
        processing_count = queue_status.get("status_counts", {}).get("processing", 0)

        return processing_count

    async def _log_episode_queued(self, podcast_item: PodemosPodcastItem):
        """Log episode added to queue"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "episode_queued",
            "capture_id": podcast_item.capture_id,
            "podcast_name": podcast_item.podcast_name,
            "episode_title": podcast_item.episode_title,
            "priority": podcast_item.priority.name,
            "transcript_only": podcast_item.transcript_only
        }

        # Write to PODEMOS log
        await self._write_podemos_log(log_entry)

    async def _log_episode_completed(self, capture_id: str, result_data: Dict):
        """Log episode processing completion"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "episode_completed",
            "capture_id": capture_id,
            "podcast_name": result_data.get("podcast_name"),
            "episode_title": result_data.get("episode_title"),
            "processing_time": result_data.get("processing_time"),
            "ads_removed": result_data.get("ads_removed", 0)
        }

        await self._write_podemos_log(log_entry)

    async def _log_episode_failed(self, capture_id: str, error: str):
        """Log episode processing failure"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "episode_failed",
            "capture_id": capture_id,
            "error": error
        }

        await self._write_podemos_log(log_entry)

    async def _write_podemos_log(self, log_entry: Dict):
        """Write entry to PODEMOS processing log"""

        log_path = "data/podemos/processing.log"
        os.makedirs(os.path.dirname(log_path), exist_ok=True)

        try:
            import aiofiles
            async with aiofiles.open(log_path, 'a') as f:
                await f.write(json.dumps(log_entry) + '\n')
        except ImportError:
            # Fallback to sync write
            with open(log_path, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')

class PodemosMacMiniCoordinator:
    """Coordinates Mac Mini processing for PODEMOS episodes"""

    def __init__(self, atlas_queue: AtlasIntegratedQueue):
        self.atlas_queue = atlas_queue
        self.mac_mini_config = atlas_queue.mac_mini_config
        self.active_jobs = {}
        self.max_concurrent = atlas_queue.max_concurrent_transcriptions

    async def process_queue_items(self, max_items: int = None) -> int:
        """Process queued episodes with Mac Mini coordination"""

        if not self.mac_mini_config.get("enabled", False):
            logger.warning("Mac Mini processing disabled")
            return 0

        processed_count = 0
        max_items = max_items or self.max_concurrent

        while len(self.active_jobs) < self.max_concurrent and processed_count < max_items:

            # Get next episode
            episode = await self.atlas_queue.get_next_podcast_episode(
                processor_id=f"mac_mini_{len(self.active_jobs)}"
            )

            if not episode:
                break

            # Start processing job
            job_id = await self._start_processing_job(episode)
            if job_id:
                self.active_jobs[job_id] = episode
                processed_count += 1

        # Check completed jobs
        await self._check_completed_jobs()

        return processed_count

    async def _start_processing_job(self, episode: Dict) -> Optional[str]:
        """Start Mac Mini processing job for episode"""

        import uuid
        job_id = str(uuid.uuid4())[:8]

        try:
            # Import the ultra-fast processor
            from podemos_ultra_fast_processor import PodemoUltraFastProcessor

            processor = PodemoUltraFastProcessor()

            # Start async processing
            asyncio.create_task(
                self._process_episode_async(job_id, episode, processor)
            )

            logger.info(f"Started processing job {job_id} for: {episode['episode_title']}")
            return job_id

        except Exception as e:
            logger.error(f"Failed to start processing job: {e}")

            # Mark as failed
            await self.atlas_queue.mark_episode_failed(
                episode["capture_id"],
                f"Failed to start processing: {e}"
            )

            return None

    async def _process_episode_async(self, job_id: str, episode: Dict, processor):
        """Process episode asynchronously"""

        try:
            # Process the episode
            result = await processor.process_episode(
                episode["episode_url"],
                episode["podcast_name"],
                episode["episode_title"]
            )

            if result and result.get("success"):
                # Mark as complete
                await self.atlas_queue.mark_episode_complete(
                    episode["capture_id"],
                    result
                )

                logger.info(f"Completed job {job_id}: {episode['episode_title']}")
            else:
                error = result.get("error", "Unknown processing error") if result else "Processing failed"
                await self.atlas_queue.mark_episode_failed(
                    episode["capture_id"],
                    error
                )

                logger.error(f"Failed job {job_id}: {error}")

        except Exception as e:
            logger.error(f"Exception in job {job_id}: {e}")
            await self.atlas_queue.mark_episode_failed(
                episode["capture_id"],
                f"Processing exception: {e}"
            )

        finally:
            # Remove from active jobs
            if job_id in self.active_jobs:
                del self.active_jobs[job_id]

    async def _check_completed_jobs(self):
        """Check for completed processing jobs"""

        # Jobs are removed automatically in _process_episode_async
        # This method can be extended for additional cleanup if needed

        logger.debug(f"Active jobs: {len(self.active_jobs)}")

async def main():
    """Main entry point for PODEMOS Atlas integration"""

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "--status":
            # Show integration status
            queue = AtlasIntegratedQueue()
            status = await queue.get_processing_status()

            print("🔗 PODEMOS Atlas Integration Status")
            print("=" * 40)
            print(f"Atlas Queue Items: {status['atlas_queue']['total_items']}")
            print(f"Clean Episodes: {status['podemos']['total_clean_episodes']}")
            print(f"Mac Mini: {status['mac_mini']['status']}")
            print(f"Active Processors: {status['active_processors']}")
            return

        elif command == "--process-queue":
            # Process queued episodes
            max_items = int(sys.argv[2]) if len(sys.argv) > 2 else 10

            queue = AtlasIntegratedQueue()
            coordinator = PodemosMacMiniCoordinator(queue)

            processed = await coordinator.process_queue_items(max_items)
            print(f"✅ Started processing {processed} episodes")
            return

        elif command == "--test-integration":
            # Test integration with sample episode
            queue = AtlasIntegratedQueue()

            # Create test episode
            test_episode = PodemosPodcastItem(
                podcast_name="test_podcast",
                episode_title="Integration Test Episode",
                episode_url="https://example.com/test.mp3",
                transcript_only=True,
                priority="high"
            )

            success = await queue.add_podcast_episode(test_episode)
            if success:
                print("✅ Test episode added to Atlas queue")

                # Get status
                status = await queue.get_processing_status()
                print(f"Queue items: {status['atlas_queue']['total_items']}")
            else:
                print("❌ Failed to add test episode")

            return

    # Default: Show help
    print("PODEMOS Atlas Integration")
    print("Usage:")
    print("  --status              Show integration status")
    print("  --process-queue [N]   Process N queued episodes")
    print("  --test-integration    Test integration with sample episode")

if __name__ == "__main__":
    asyncio.run(main())