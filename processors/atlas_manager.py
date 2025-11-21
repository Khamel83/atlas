#!/usr/bin/env python3
"""
ATLAS MANAGEMENT SYSTEM - LOG-STREAM VERSION
High-performance continuous processing using log-stream architecture
Replaces database bottlenecks with fast file-based operations
"""

import threading
import time
import subprocess
import os
import signal
import sys
from datetime import datetime, timedelta
import json
import logging

# Import the log-stream processor
from atlas_log_processor import AtlasLogProcessor

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/atlas_manager.log'),
        logging.StreamHandler()
    ]
)

class AtlasManager:
    """High-performance Atlas manager using log-stream architecture"""

    def __init__(self):
        self.running = True
        self.processor = AtlasLogProcessor()

        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        # Performance tracking
        self.start_time = time.time()
        self.total_episodes_processed = 0
        self.last_batch_time = time.time()

        # Schedule intervals (in seconds)
        self.rss_discovery_interval = 300  # 5 minutes
        self.batch_processing_interval = 60   # 1 minute
        self.metrics_interval = 300         # 5 minutes

        logging.info("🚀 Atlas Log-Stream Manager initialized")
        self.processor.logger.metrics("system", "atlas_manager", {
            "event": "startup",
            "start_time": datetime.utcnow().isoformat(),
            "rss_feeds": len(self.processor.rss_feeds),
            "podcast_configs": len(self.processor.podcast_config),
            "processed_episodes": len(self.processor.processed_episodes)
        })

    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logging.info(f"🛑 Received signal {signum}, shutting down gracefully...")
        self.running = False
        self.processor.logger.metrics("system", "atlas_manager", {
            "event": "shutdown",
            "signal": signum,
            "uptime_seconds": time.time() - self.start_time,
            "total_processed": self.total_episodes_processed
        })

    def process_continuous_batch(self):
        """Process continuous batch of episodes"""
        try:
            result = self.processor.process_batch(limit=100)

            # Update performance metrics
            self.total_episodes_processed += result['success']
            self.last_batch_time = time.time()

            logging.info(f"📊 Batch completed: {result['success']} success, {result['failed']} failed in {result['duration']:.2f}s")

            return result

        except Exception as e:
            logging.error(f"❌ Batch processing error: {e}")
            self.processor.logger.fail("system", "atlas_manager", "batch_processing", {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
            return None

    def generate_metrics_report(self):
        """Generate performance metrics report"""
        uptime = time.time() - self.start_time
        uptime_hours = uptime / 3600

        eps = self.total_episodes_processed / uptime if uptime > 0 else 0

        metrics = {
            "uptime_hours": round(uptime_hours, 2),
            "total_episodes_processed": self.total_episodes_processed,
            "episodes_per_hour": round(eps * 3600, 2),
            "rss_feeds": len(self.processor.rss_feeds),
            "podcast_configs": len(self.processor.podcast_config),
            "processed_episodes": len(self.processor.processed_episodes),
            "last_batch_time": datetime.fromtimestamp(self.last_batch_time).isoformat(),
            "timestamp": datetime.utcnow().isoformat()
        }

        # Log metrics
        self.processor.logger.metrics("system", "atlas_manager", metrics)

        # Print summary
        logging.info(f"📈 Atlas Metrics Report:")
        logging.info(f"   Uptime: {metrics['uptime_hours']} hours")
        logging.info(f"   Episodes Processed: {metrics['total_episodes_processed']}")
        logging.info(f"   Episodes/Hour: {metrics['episodes_per_hour']}")
        logging.info(f"   RSS Feeds: {metrics['rss_feeds']}")
        logging.info(f"   Success Rate: {(self.total_episodes_processed / max(1, self.total_episodes_processed + 1)) * 100:.1f}%")

        return metrics

    def run_continuous_processing(self):
        """Main continuous processing loop"""
        logging.info("🔄 Starting continuous processing loop...")

        last_discovery = time.time()
        last_metrics = time.time()

        while self.running:
            try:
                current_time = time.time()

                # RSS Discovery (every 5 minutes)
                if current_time - last_discovery >= self.rss_discovery_interval:
                    logging.info("🔍 Running RSS discovery...")
                    episodes = self.processor.discover_episodes(limit=50)
                    logging.info(f"📡 Discovered {len(episodes)} new episodes")
                    last_discovery = current_time

                # Batch Processing (every 1 minute)
                if current_time - self.last_batch_time >= self.batch_processing_interval:
                    result = self.process_continuous_batch()
                    if result and result['discovered'] > 0:
                        logging.info(f"✅ Processed batch: {result['success']}/{result['discovered']} successful")

                # Metrics Report (every 5 minutes)
                if current_time - last_metrics >= self.metrics_interval:
                    self.generate_metrics_report()
                    last_metrics = current_time

                # Sleep for a short interval to prevent high CPU usage
                time.sleep(10)

            except KeyboardInterrupt:
                logging.info("🛑 Received keyboard interrupt, shutting down...")
                break
            except Exception as e:
                logging.error(f"❌ Error in main processing loop: {e}")
                self.processor.logger.fail("system", "atlas_manager", "main_loop", {
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                })
                time.sleep(60)  # Wait before retrying

    def run_single_batch(self, limit: int = 100):
        """Run a single batch for testing"""
        logging.info(f"🎯 Running single batch with limit {limit}...")
        result = self.processor.process_batch(limit=limit)

        logging.info(f"📊 Single Batch Results:")
        logging.info(f"   Discovered: {result['discovered']}")
        logging.info(f"   Success: {result['success']}")
        logging.info(f"   Failed: {result['failed']}")
        logging.info(f"   Duration: {result['duration']:.2f}s")
        logging.info(f"   Episodes/sec: {result['eps']:.2f}")

        return result

    def cleanup_old_logs(self, days: int = 7):
        """Clean up old log files"""
        try:
            cutoff_time = time.time() - (days * 24 * 3600)
            log_dir = "logs"

            cleaned_count = 0
            for filename in os.listdir(log_dir):
                filepath = os.path.join(log_dir, filename)
                if os.path.isfile(filepath) and os.path.getmtime(filepath) < cutoff_time:
                    os.remove(filepath)
                    cleaned_count += 1

            logging.info(f"🧹 Cleaned up {cleaned_count} old log files")

        except Exception as e:
            logging.error(f"❌ Error cleaning up logs: {e}")

def main():
    """Main entry point"""
    print("🚀 ATLAS LOG-STREAM MANAGEMENT SYSTEM")
    print("=" * 50)

    manager = AtlasManager()

    try:
        if len(sys.argv) > 1 and sys.argv[1] == "--single-batch":
            # Run single batch for testing
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 100
            manager.run_single_batch(limit)
        else:
            # Run continuous processing
            manager.run_continuous_processing()

    except KeyboardInterrupt:
        logging.info("🛑 Atlas Manager stopped by user")
    except Exception as e:
        logging.error(f"❌ Atlas Manager crashed: {e}")
        manager.processor.logger.fail("system", "atlas_manager", "crash", {
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        })
    finally:
        # Generate final metrics
        manager.generate_metrics_report()
        logging.info("🏁 Atlas Manager shutdown complete")

if __name__ == "__main__":
    main()