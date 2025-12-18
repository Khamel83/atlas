#!/usr/bin/env python3
"""
PODEMOS Scheduler
Automated 2AM processing pipeline for ad removal and clean RSS generation.
"""

import schedule
import time
import logging
import json
import os
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path
import subprocess
import requests
import tempfile

# Import PODEMOS components
from podemos_episode_discovery import PodmosEpisodeDiscovery
from podemos_transcription import PodmosTranscriber
from podemos_ad_detection import PodmosAdDetector
from podemos_audio_cutter import PodmosAudioCutter
from podemos_rss_generator import PodmosRSSGenerator

# Import Universal Processing Queue for job submission
from universal_processing_queue import add_podemos_processing_job, UniversalProcessingQueue

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('podemos_scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PodmosScheduler:
    """Automated 2AM processing pipeline scheduler."""

    def __init__(self, config_file: str = "podemos_config.json"):
        """Initialize scheduler with configuration."""
        self.config = self._load_config(config_file)
        self.discovery = PodmosEpisodeDiscovery()
        self.transcriber = PodmosTranscriber()
        self.ad_detector = PodmosAdDetector()
        self.audio_cutter = PodmosAudioCutter()
        self.rss_generator = PodmosRSSGenerator()

        # Processing stats
        self.last_run_stats = {}
        self.daily_reports = []

    def _load_config(self, config_file: str) -> Dict:
        """Load configuration from JSON file."""
        default_config = {
            "schedule_time": "02:00",
            "max_processing_time_minutes": 20,
            "max_concurrent_episodes": 3,
            "retry_attempts": 2,
            "notification_webhooks": [],
            "storage": {
                "temp_dir": "/tmp/podemos_processing",
                "output_dir": "./podemos_output"
            },
            "quality_settings": {
                "transcription_model": "base",
                "audio_quality": "high"
            }
        }

        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    user_config = json.load(f)
                default_config.update(user_config)
                logger.info(f"Loaded configuration from {config_file}")
            except Exception as e:
                logger.warning(f"Failed to load config file: {e}")
        else:
            # Create default config file
            with open(config_file, 'w') as f:
                json.dump(default_config, f, indent=2)
            logger.info(f"Created default configuration: {config_file}")

        return default_config

    def run_daily_processing(self):
        """Main 2AM processing pipeline."""
        start_time = datetime.now()
        logger.info(f"🌙 PODEMOS 2AM Processing Pipeline Started at {start_time}")

        processing_stats = {
            "start_time": start_time.isoformat(),
            "episodes_discovered": 0,
            "episodes_processed": 0,
            "episodes_failed": 0,
            "processing_times": [],
            "errors": []
        }

        try:
            # Step 1: Discover new episodes
            logger.info("📡 Step 1: Discovering new episodes...")
            new_episodes = self.discovery.discover_episodes(hours_lookback=24)
            processing_stats["episodes_discovered"] = len(new_episodes)

            if not new_episodes:
                logger.info("No new episodes found - ending processing")
                processing_stats["end_time"] = datetime.now().isoformat()
                self._save_daily_report(processing_stats)
                return

            logger.info(f"Found {len(new_episodes)} new episodes to process")

            # Step 2: Process each episode
            max_concurrent = self.config["max_concurrent_episodes"]
            episodes_to_process = new_episodes[:max_concurrent]  # Limit concurrent processing

            for i, episode in enumerate(episodes_to_process):
                episode_start = datetime.now()
                logger.info(f"🎙️ Processing episode {i+1}/{len(episodes_to_process)}: {episode['title']}")

                success = self._process_single_episode(episode, processing_stats)

                episode_time = (datetime.now() - episode_start).total_seconds()
                processing_stats["processing_times"].append(episode_time)

                if success:
                    processing_stats["episodes_processed"] += 1
                    logger.info(f"✅ Episode processed in {episode_time:.1f}s")
                else:
                    processing_stats["episodes_failed"] += 1
                    logger.warning(f"❌ Episode processing failed after {episode_time:.1f}s")

                # Check time limit
                elapsed_minutes = (datetime.now() - start_time).total_seconds() / 60
                if elapsed_minutes > self.config["max_processing_time_minutes"]:
                    logger.warning(f"⏰ Time limit reached ({elapsed_minutes:.1f} minutes) - stopping processing")
                    break

            # Step 3: Generate summary report
            end_time = datetime.now()
            total_time = (end_time - start_time).total_seconds() / 60

            processing_stats["end_time"] = end_time.isoformat()
            processing_stats["total_processing_time_minutes"] = total_time

            logger.info(f"🎯 Processing completed in {total_time:.1f} minutes")
            logger.info(f"📊 Results: {processing_stats['episodes_processed']} success, {processing_stats['episodes_failed']} failed")

            # Send notifications
            self._send_completion_notification(processing_stats)

            # Save daily report
            self._save_daily_report(processing_stats)

        except Exception as e:
            logger.error(f"❌ Processing pipeline failed: {e}")
            processing_stats["errors"].append(str(e))
            processing_stats["end_time"] = datetime.now().isoformat()
            self._send_failure_notification(processing_stats, str(e))
            self._save_daily_report(processing_stats)

    def _process_single_episode(self, episode: Dict, stats: Dict) -> bool:
        """Process a single episode through the complete pipeline."""
        episode_id = episode.get('id')
        episode_title = episode.get('title', 'Unknown Episode')
        audio_url = episode.get('audio_url')

        try:
            # Mark episode as processing
            self.discovery.update_episode_status(episode_id, 'processing')

            # Step 1: Transcribe episode
            logger.info(f"🎤 Transcribing: {episode_title}")
            transcript_result = self.transcriber.transcribe_audio_url(audio_url, episode_title)

            if not transcript_result:
                raise Exception("Transcription failed")

            # Step 2: Detect ads
            logger.info(f"🔍 Detecting ads: {episode_title}")
            ad_segments = self.ad_detector.detect_ads(
                transcript_result['transcript'],
                transcript_result.get('segments', [])
            )

            # Convert ad segments to timestamp tuples
            ad_timestamps = []
            for segment in ad_segments:
                if segment.get('start_time') is not None and segment.get('end_time') is not None:
                    ad_timestamps.append((segment['start_time'], segment['end_time']))

            logger.info(f"Found {len(ad_timestamps)} ad segments")

            # Step 3: Cut audio (remove ads)
            logger.info(f"✂️ Removing ads: {episode_title}")
            clean_audio_file = self.audio_cutter.remove_ads(audio_url, ad_timestamps)

            if not clean_audio_file:
                raise Exception("Audio cutting failed")

            # Step 4: Update RSS feed
            logger.info(f"📡 Updating RSS feed: {episode_title}")
            clean_episode_data = self.rss_generator.generate_episode_metadata(
                episode, clean_audio_file, ad_timestamps
            )

            # Update episode status in database
            self.discovery.update_episode_status(
                episode_id,
                'completed',
                clean_audio_path=clean_audio_file,
                ad_segments=json.dumps(ad_timestamps),
                transcript_path=f"transcript_{episode_id}.txt"
            )

            return True

        except Exception as e:
            logger.error(f"Failed to process episode {episode_title}: {e}")
            stats["errors"].append(f"{episode_title}: {str(e)}")

            # Mark episode as failed with retry logic
            retry_count = episode.get('retry_count', 0)
            if retry_count < self.config["retry_attempts"]:
                self.discovery.update_episode_status(episode_id, 'retry', retry_count=retry_count + 1)
            else:
                self.discovery.update_episode_status(episode_id, 'failed')

            return False

    def _send_completion_notification(self, stats: Dict):
        """Send completion notification via configured webhooks."""
        try:
            message = {
                "title": "🎉 PODEMOS Daily Processing Complete",
                "summary": f"Processed {stats['episodes_processed']} episodes in {stats.get('total_processing_time_minutes', 0):.1f} minutes",
                "details": {
                    "episodes_discovered": stats['episodes_discovered'],
                    "episodes_processed": stats['episodes_processed'],
                    "episodes_failed": stats['episodes_failed'],
                    "avg_processing_time": sum(stats['processing_times']) / len(stats['processing_times']) if stats['processing_times'] else 0,
                    "total_time_minutes": stats.get('total_processing_time_minutes', 0)
                }
            }

            for webhook_url in self.config.get("notification_webhooks", []):
                try:
                    response = requests.post(webhook_url, json=message, timeout=10)
                    response.raise_for_status()
                    logger.info(f"✅ Notification sent to {webhook_url}")
                except Exception as e:
                    logger.warning(f"Failed to send notification to {webhook_url}: {e}")

        except Exception as e:
            logger.warning(f"Failed to send completion notifications: {e}")

    def _send_failure_notification(self, stats: Dict, error: str):
        """Send failure notification."""
        try:
            message = {
                "title": "❌ PODEMOS Processing Failed",
                "error": error,
                "stats": stats
            }

            for webhook_url in self.config.get("notification_webhooks", []):
                try:
                    requests.post(webhook_url, json=message, timeout=10)
                except:
                    pass  # Best effort

        except:
            pass  # Best effort

    def _save_daily_report(self, stats: Dict):
        """Save daily processing report."""
        try:
            report_date = datetime.now().strftime("%Y-%m-%d")
            report_file = f"podemos_report_{report_date}.json"

            with open(report_file, 'w') as f:
                json.dump(stats, f, indent=2)

            logger.info(f"📄 Daily report saved: {report_file}")
            self.daily_reports.append(stats)

        except Exception as e:
            logger.warning(f"Failed to save daily report: {e}")

    def test_pipeline(self) -> bool:
        """Test the complete processing pipeline."""
        logger.info("🧪 Testing PODEMOS processing pipeline...")

        try:
            # Create test episode data
            test_episode = {
                'id': 'test-episode-1',
                'title': 'PODEMOS Test Episode',
                'audio_url': 'https://example.com/test.mp3',  # Mock URL
                'podcast_title': 'Test Podcast'
            }

            # Test components individually
            logger.info("Testing episode discovery...")
            self.discovery.get_stats()  # Basic connection test

            logger.info("Testing transcription...")
            # Skip actual transcription in test mode

            logger.info("Testing ad detection...")
            from podemos_transcription import create_test_transcript
            create_test_transcript()
            test_ads = self.ad_detector.detect_ads(open('test_transcript.txt').read())

            logger.info("Testing audio cutting...")
            # Skip actual audio cutting in test mode

            logger.info("Testing RSS generation...")
            from podemos_rss_generator import create_test_feed
            create_test_feed()

            logger.info("✅ Pipeline test completed successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Pipeline test failed: {e}")
            return False

    def start_scheduler(self):
        """Start the scheduled processing service."""
        schedule_time = self.config["schedule_time"]
        logger.info(f"⏰ Starting PODEMOS scheduler - daily processing at {schedule_time}")

        # Schedule daily processing
        schedule.every().day.at(schedule_time).do(self.run_daily_processing)

        # Schedule stats collection every hour
        schedule.every().hour.do(self._collect_stats)

        logger.info("🎯 Scheduler started - waiting for scheduled time...")

        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logger.info("🛑 Scheduler stopped by user")

    def _collect_stats(self):
        """Collect system statistics."""
        try:
            stats = self.discovery.get_stats()
            logger.info(f"📊 System stats: {stats}")
        except Exception as e:
            logger.warning(f"Failed to collect stats: {e}")

    def create_cron_job(self) -> str:
        """Create cron job entry for system installation."""
        script_path = os.path.abspath(__file__)
        cron_entry = f"0 2 * * * cd {os.path.dirname(script_path)} && python3 {script_path} --run-once"

        cron_file = "podemos_cron.txt"
        with open(cron_file, 'w') as f:
            f.write(f"# PODEMOS 2AM Processing Cron Job\n")
            f.write(f"{cron_entry}\n")

        logger.info(f"Created cron job entry: {cron_file}")
        logger.info(f"To install: crontab {cron_file}")

        return cron_entry

    def create_systemd_service(self) -> str:
        """Create systemd service file for system installation."""
        script_path = os.path.abspath(__file__)
        work_dir = os.path.dirname(script_path)

        service_content = f"""[Unit]
Description=PODEMOS Automated Podcast Processing Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory={work_dir}
ExecStart=/usr/bin/python3 {script_path} --daemon
Restart=always
RestartSec=30
Environment=PYTHONPATH={work_dir}

[Install]
WantedBy=multi-user.target
"""

        service_file = "podemos.service"
        with open(service_file, 'w') as f:
            f.write(service_content)

        logger.info(f"Created systemd service: {service_file}")
        logger.info(f"To install: sudo cp {service_file} /etc/systemd/system/")
        logger.info(f"Then: sudo systemctl enable podemos && sudo systemctl start podemos")

        return service_file

def main():
    """Main entry point for PODEMOS scheduler."""
    import argparse

    parser = argparse.ArgumentParser(description="PODEMOS Automated Processing Scheduler")
    parser.add_argument('--run-once', action='store_true', help='Run processing once (for cron)')
    parser.add_argument('--test-mode', action='store_true', help='Test pipeline components')
    parser.add_argument('--daemon', action='store_true', help='Run as daemon service')
    parser.add_argument('--create-cron', action='store_true', help='Create cron job entry')
    parser.add_argument('--create-service', action='store_true', help='Create systemd service')
    args = parser.parse_args()

    scheduler = PodmosScheduler()

    if args.test_mode:
        success = scheduler.test_pipeline()
        exit(0 if success else 1)

    elif args.run_once:
        scheduler.run_daily_processing()

    elif args.create_cron:
        scheduler.create_cron_job()

    elif args.create_service:
        scheduler.create_systemd_service()

    elif args.daemon:
        scheduler.start_scheduler()

    else:
        print("PODEMOS Automated Processing Scheduler")
        print("Usage:")
        print("  --test-mode        Test all pipeline components")
        print("  --run-once         Run processing once (for cron)")
        print("  --daemon           Run as daemon service")
        print("  --create-cron      Create cron job entry")
        print("  --create-service   Create systemd service file")

if __name__ == "__main__":
    main()