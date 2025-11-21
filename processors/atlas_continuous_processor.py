#!/usr/bin/env python3
"""
Atlas Continuous Processor
Runs continuously, processing new data as it arrives
Handles all errors gracefully and keeps running
"""

import time
import os
import signal
import sys
from pathlib import Path
from datetime import datetime
import logging
from atlas_processor import AtlasProcessor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('atlas_continuous.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AtlasContinuousProcessor:
    """Continuous processor that runs forever"""

    def __init__(self):
        self.processor = AtlasProcessor()
        self.running = True
        self.stats = {
            'total_runs': 0,
            'total_processed': 0,
            'total_duplicates': 0,
            'total_failed': 0,
            'start_time': datetime.now()
        }

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"\n🛑 Received signal {signum}, shutting down gracefully...")
        self.running = False

    def get_new_files_count(self):
        """Count files that haven't been processed yet"""
        try:
            conn = self.processor.db_path
            import sqlite3
            db_conn = sqlite3.connect(str(conn))

            # Get all input files
            all_files = []
            for root, dirs, files in os.walk(self.processor.input_dir):
                for file in files:
                    if not file.startswith('.'):
                        file_path = Path(root) / file
                        if file_path.is_file() and file_path.stat().st_size > 0:
                            all_files.append(str(file_path))

            # Check which ones are already in database
            if all_files:
                placeholders = ','.join(['?' for _ in all_files])
                cursor = db_conn.execute(f"""
                    SELECT COUNT(*) FROM content_tracker
                    WHERE original_path IN ({placeholders})
                """, all_files)
                already_processed = cursor.fetchone()[0]
                db_conn.close()

                return len(all_files) - already_processed
            else:
                db_conn.close()
                return 0

        except Exception as e:
            logger.error(f"Error counting new files: {e}")
            return 0

    def show_current_status(self):
        """Display current processing status"""
        try:
            status = self.processor.get_status()
            runtime = datetime.now() - self.stats['start_time']

            logger.info("📊 ATLAS CONTINUOUS PROCESSOR STATUS")
            logger.info("=" * 50)
            logger.info(f"⏱️  Runtime: {runtime}")
            logger.info(f"🔄 Total runs: {self.stats['total_runs']}")
            logger.info(f"✅ Total processed: {self.stats['total_processed']}")
            logger.info(f"⏭️  Total duplicates: {self.stats['total_duplicates']}")
            logger.info(f"❌ Total failed: {self.stats['total_failed']}")
            logger.info(f"📁 Files waiting: {self.get_new_files_count()}")
            logger.info(f"🗄️  Database status: {status['by_status']}")
            logger.info(f"📂 Processing dir: {status['processing_files']} files")
            logger.info(f"📋 Archive dir: {status['archive_files']} files")
            logger.info(f"💾 Backup dir: {status['backup_files']} files")

        except Exception as e:
            logger.error(f"Error showing status: {e}")

    def run_once(self):
        """Run a single processing cycle"""
        try:
            logger.info("🔄 Starting processing cycle...")
            processed, duplicates, failed = self.processor.process_input_folder()

            self.stats['total_runs'] += 1
            self.stats['total_processed'] += processed
            self.stats['total_duplicates'] += duplicates
            self.stats['total_failed'] += failed

            if processed > 0 or duplicates > 0 or failed > 0:
                logger.info(f"📈 This cycle: {processed} processed, {duplicates} duplicates, {failed} failed")
            else:
                logger.info("💤 No new files to process")

            return processed + duplicates + failed  # Total files touched

        except Exception as e:
            logger.error(f"❌ Error in processing cycle: {e}")
            return 0

    def run_continuous(self, check_interval=30):
        """Run continuously with specified interval"""
        logger.info("🚀 STARTING ATLAS CONTINUOUS PROCESSOR")
        logger.info("=" * 50)
        logger.info(f"⏱️  Check interval: {check_interval} seconds")
        logger.info(f"📁 Input directory: {self.processor.input_dir}")
        logger.info(f"🗄️  Database: {self.processor.db_path}")
        logger.info("💤 Running forever... (Ctrl+C to stop)")
        logger.info("")

        # Show initial status
        self.show_current_status()

        while self.running:
            try:
                # Run processing cycle
                files_touched = self.run_once()

                if self.running:
                    # Show status every 10 cycles or when files are processed
                    if self.stats['total_runs'] % 10 == 0 or files_touched > 0:
                        self.show_current_status()

                    # Wait before next cycle
                    logger.info(f"💤 Sleeping {check_interval}s... (Total runs: {self.stats['total_runs']})")

                    # Sleep in small increments to allow responsive shutdown
                    for _ in range(check_interval):
                        if not self.running:
                            break
                        time.sleep(1)

            except KeyboardInterrupt:
                logger.info("🛑 Keyboard interrupt received")
                self.running = False
                break
            except Exception as e:
                logger.error(f"❌ Unexpected error: {e}")
                logger.info("🔄 Continuing despite error...")
                time.sleep(5)  # Brief pause after serious errors

        # Final status
        logger.info("\n🏁 ATLAS CONTINUOUS PROCESSOR SHUTTING DOWN")
        self.show_final_status()

    def show_final_status(self):
        """Show final processing statistics"""
        runtime = datetime.now() - self.stats['start_time']
        logger.info("📊 FINAL STATISTICS")
        logger.info("=" * 30)
        logger.info(f"⏱️  Total runtime: {runtime}")
        logger.info(f"🔄 Processing cycles: {self.stats['total_runs']}")
        logger.info(f"✅ Files processed: {self.stats['total_processed']}")
        logger.info(f"⏭️  Duplicates skipped: {self.stats['total_duplicates']}")
        logger.info(f"❌ Failed files: {self.stats['total_failed']}")
        logger.info(f"📈 Success rate: {(self.stats['total_processed']/(self.stats['total_processed']+self.stats['total_failed'])*100):.1f}%" if self.stats['total_processed'] + self.stats['total_failed'] > 0 else "N/A")
        logger.info("🎉 Thank you for using Atlas!")

def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Atlas Continuous Processor')
    parser.add_argument('--interval', type=int, default=30,
                       help='Check interval in seconds (default: 30)')
    parser.add_argument('--once', action='store_true',
                       help='Run once instead of continuously')

    args = parser.parse_args()

    processor = AtlasContinuousProcessor()

    if args.once:
        logger.info("🔄 Running single processing cycle...")
        processor.run_once()
        processor.show_final_status()
    else:
        processor.run_continuous(check_interval=args.interval)

if __name__ == "__main__":
    main()