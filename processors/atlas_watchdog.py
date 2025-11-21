#!/usr/bin/env python3
"""
Atlas Watchdog Service
Continuously monitors Atlas transcript processor and restarts it if it fails.
Sends Telegram notifications when Atlas goes down or comes back up.
"""

import os
import time
import subprocess
import signal
import logging
from pathlib import Path
from datetime import datetime
from atlas_telegram_monitor import AtlasTelegramMonitor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/ubuntu/dev/atlas/atlas_watchdog.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AtlasWatchdog:
    """Watchdog service for Atlas transcript processor"""

    def __init__(self):
        self.root_dir = Path("/home/ubuntu/dev/atlas")
        self.processor_script = self.root_dir / "atlas_transcript_processor.py"
        self.monitor = AtlasTelegramMonitor()
        self.running = True
        self.processor_process = None

        # Set up signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"🛑 Received signal {signum}, shutting down watchdog...")
        self.running = False

        # Kill processor if running
        if self.processor_process:
            self.processor_process.terminate()
            try:
                self.processor_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.processor_process.kill()

    def is_processor_running(self):
        """Check if Atlas processor is currently running"""
        try:
            result = subprocess.run(
                ['pgrep', '-f', 'atlas_transcript_processor.py'],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Error checking processor status: {e}")
            return False

    def start_processor(self):
        """Start the Atlas processor"""
        try:
            logger.info("🚀 Starting Atlas transcript processor...")

            # Kill any existing instances first
            subprocess.run(['pkill', '-f', 'atlas_transcript_processor.py'],
                         capture_output=True)

            # Start the processor
            self.processor_process = subprocess.Popen(
                ['python3', str(self.processor_script)],
                cwd=str(self.root_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )

            # Give it a moment to start
            time.sleep(5)

            if self.processor_process.poll() is None:
                logger.info("✅ Atlas processor started successfully")
                self.monitor.send_atlas_up()
                return True
            else:
                logger.error("❌ Atlas processor failed to start")
                return False

        except Exception as e:
            logger.error(f"❌ Error starting processor: {e}")
            return False

    def stop_processor(self):
        """Stop the Atlas processor"""
        try:
            if self.processor_process:
                logger.info("🛑 Stopping Atlas processor...")
                self.processor_process.terminate()

                try:
                    self.processor_process.wait(timeout=10)
                    logger.info("✅ Atlas processor stopped gracefully")
                except subprocess.TimeoutExpired:
                    logger.warning("⚠️ Processor didn't stop gracefully, killing it...")
                    self.processor_process.kill()
                    self.processor_process.wait()

            # Also kill any stray instances
            subprocess.run(['pkill', '-f', 'atlas_transcript_processor.py'],
                         capture_output=True)

        except Exception as e:
            logger.error(f"Error stopping processor: {e}")

    def monitor_processor(self):
        """Monitor the processor and restart if needed"""
        check_interval = 60  # Check every minute
        restart_cooldown = 300  # Wait 5 minutes between restarts
        last_restart = 0

        logger.info("🐕 Atlas watchdog started")
        logger.info(f"⏱️ Check interval: {check_interval} seconds")
        logger.info("🔄 Monitoring Atlas transcript processor...")

        while self.running:
            try:
                # Check if processor is running
                if not self.is_processor_running():
                    current_time = time.time()

                    if current_time - last_restart >= restart_cooldown:
                        logger.warning("⚠️ Atlas processor is not running!")

                        # Send notification
                        self.monitor.send_atlas_down()

                        # Try to restart
                        if self.start_processor():
                            last_restart = current_time
                            logger.info("🔄 Atlas processor restarted successfully")
                        else:
                            logger.error("❌ Failed to restart Atlas processor")
                            # Wait longer before trying again
                            time.sleep(restart_cooldown)
                    else:
                        logger.info(f"⏳ In restart cooldown ({restart_cooldown - (current_time - last_restart):.0f}s remaining)")
                else:
                    # Processor is running, let's make sure it's actually processing
                    log_file = self.root_dir / "atlas_transcript.log"
                    if log_file.exists():
                        last_modified = log_file.stat().st_mtime
                        current_time = time.time()

                        # If log hasn't been updated in 10 minutes, consider it stuck
                        if current_time - last_modified > 600:  # 10 minutes
                            logger.warning("⚠️ Atlas processor appears stuck (no recent log activity)")

                            # Send notification and restart
                            self.monitor.send_atlas_down()
                            self.stop_processor()

                            if self.start_processor():
                                last_restart = current_time
                                logger.info("🔄 Atlas processor restarted due to stuck detection")
                            else:
                                logger.error("❌ Failed to restart stuck processor")
                                time.sleep(restart_cooldown)

                # Wait before next check
                for _ in range(check_interval):
                    if not self.running:
                        break
                    time.sleep(1)

            except KeyboardInterrupt:
                logger.info("🛑 Keyboard interrupt received")
                break
            except Exception as e:
                logger.error(f"❌ Error in monitoring loop: {e}")
                time.sleep(30)  # Wait after errors

        logger.info("🏁 Atlas watchdog shutting down")

    def run(self):
        """Main watchdog loop"""
        logger.info("🚀 Starting Atlas Watchdog Service")
        logger.info("=" * 50)

        # Initial state check
        if self.is_processor_running():
            logger.info("✅ Atlas processor is already running")
            self.monitor.send_atlas_up()
        else:
            logger.info("⚠️ Atlas processor is not running, starting it...")
            self.start_processor()

        # Start monitoring
        self.monitor_processor()

def main():
    """Main execution"""
    import argparse

    parser = argparse.ArgumentParser(description='Atlas Watchdog Service')
    parser.add_argument('--once', action='store_true',
                       help='Run check once and exit')

    args = parser.parse_args()

    watchdog = AtlasWatchdog()

    if args.once:
        # Single check
        if watchdog.is_processor_running():
            print("✅ Atlas processor is running")
            watchdog.monitor.send_atlas_up()
        else:
            print("❌ Atlas processor is not running")
            watchdog.monitor.send_atlas_down()
            watchdog.start_processor()
    else:
        # Continuous monitoring
        watchdog.run()

if __name__ == "__main__":
    main()