#!/usr/bin/env python3
"""
TRUSTED QUEUE PROCESSOR - Process entire queue with transparency
Builds trust through real-time monitoring and progress tracking
"""

import sqlite3
import subprocess
import time
import json
import os
from datetime import datetime, timedelta
import threading
import signal
import sys
from pathlib import Path

class TrustedQueueProcessor:
    """Process entire queue with complete transparency and trust-building"""

    def __init__(self):
        self.db_path = "data/atlas.db"
        self.log_file = "logs/trusted_processor.log"
        self.progress_file = "logs/processing_progress.json"
        self.running = False
        self.start_time = None
        self.processed_count = 0
        self.success_count = 0
        self.failed_count = 0

        # Create logs directory if it doesn't exist
        os.makedirs("logs", exist_ok=True)

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        print(f"\n🛑 Received signal {signum}, shutting down gracefully...")
        self.running = False
        self._save_progress()

    def _log(self, message, level="INFO"):
        """Log with timestamp and level"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}"

        # Write to log file
        with open(self.log_file, "a") as f:
            f.write(log_entry + "\n")

        # Print to console
        print(log_entry)

    def _save_progress(self):
        """Save current progress to file"""
        progress = {
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "last_update": datetime.now().isoformat(),
            "running": self.running,
            "processed_count": self.processed_count,
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "current_batch": getattr(self, 'current_batch', 0),
            "current_podcast": getattr(self, 'current_podcast', None)
        }

        with open(self.progress_file, "w") as f:
            json.dump(progress, f, indent=2)

    def _get_queue_stats(self):
        """Get current queue statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Overall stats
        cursor.execute("SELECT status, COUNT(*) FROM episode_queue GROUP BY status")
        status_counts = dict(cursor.fetchall())

        # Pending episodes details
        cursor.execute("""
            SELECT podcast_name, COUNT(*) as count
            FROM episode_queue
            WHERE status = 'pending'
            GROUP BY podcast_name
            ORDER BY count DESC
            LIMIT 10
        """)
        top_pending = cursor.fetchall()

        conn.close()

        return {
            "status_counts": status_counts,
            "top_pending": top_pending,
            "total_pending": status_counts.get('pending', 0)
        }

    def _get_next_batch(self, batch_size=50):
        """Get next batch of pending episodes"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, episode_url, podcast_name, episode_title
            FROM episode_queue
            WHERE status = 'pending'
            ORDER BY id
            LIMIT ?
        """, (batch_size,))

        episodes = cursor.fetchall()
        conn.close()

        return episodes

    def _process_episode(self, episode_id, url, podcast_name, episode_title):
        """Process a single episode"""
        try:
            self._log(f"Processing {podcast_name} - Episode {episode_id}")

            # Run the single episode processor
            result = subprocess.run([
                'python3', 'single_episode_processor.py',
                str(episode_id), url, podcast_name
            ], capture_output=True, text=True, timeout=120)

            self.processed_count += 1

            if result.returncode == 0:
                # Check if transcript was found
                if "TRANSCRIPT FOUND AND STORED" in result.stdout:
                    self.success_count += 1
                    self._log(f"✅ SUCCESS: {podcast_name} Episode {episode_id}")

                    # Extract quality score if available
                    for line in result.stdout.split('\n'):
                        if "Quality Score:" in line:
                            try:
                                score = float(line.split('%')[0].split()[-1].strip())
                                self._log(f"   📊 Quality: {score}%")
                            except:
                                pass
                else:
                    self.failed_count += 1
                    self._log(f"❌ NO TRANSCRIPT: {podcast_name} Episode {episode_id}")
            else:
                self.failed_count += 1
                self._log(f"❌ PROCESSING ERROR: {podcast_name} Episode {episode_id}")

        except subprocess.TimeoutExpired:
            self.failed_count += 1
            self._log(f"⏰ TIMEOUT: {podcast_name} Episode {episode_id}")
        except Exception as e:
            self.failed_count += 1
            self._log(f"💥 CRASH: {podcast_name} Episode {episode_id} - {e}")

    def _print_progress_report(self):
        """Print detailed progress report"""
        if not self.start_time:
            return

        runtime = datetime.now() - self.start_time
        hours, remainder = divmod(runtime.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)

        success_rate = (self.success_count / self.processed_count * 100) if self.processed_count > 0 else 0

        stats = self._get_queue_stats()

        print("\n" + "="*80)
        print(f"🎯 TRUSTED PROCESSOR PROGRESS REPORT")
        print("="*80)
        print(f"⏱️  Runtime: {int(hours)}h {int(minutes)}m {int(seconds)}s")
        print(f"📊 Processed: {self.processed_count:,} episodes")
        print(f"✅ Success: {self.success_count:,} ({success_rate:.1f}%)")
        print(f"❌ Failed: {self.failed_count:,}")
        print(f"📋 Remaining: {stats['total_pending']:,} episodes")

        if self.processed_count > 0:
            eps = self.processed_count / runtime.total_seconds() * 3600
            eta_seconds = stats['total_pending'] / eps if eps > 0 else 0
            eta_hours, eta_remainder = divmod(eta_seconds, 3600)
            eta_minutes, eta_seconds = divmod(eta_remainder, 60)

            print(f"⚡ Speed: {eps:.1f} episodes/hour")
            print(f"🕐 ETA: {int(eta_hours)}h {int(eta_minutes)}m {int(eta_seconds)}s")

        print(f"\n🏆 TOP PENDING PODCASTS:")
        for podcast, count in stats['top_pending'][:5]:
            print(f"   {podcast}: {count:,} episodes")

        print("="*80 + "\n")

    def run_continuous_processing(self):
        """Run continuous processing with real-time updates"""
        self.running = True
        self.start_time = datetime.now()

        self._log("🚀 STARTING TRUSTED QUEUE PROCESSOR")
        self._log(f"📋 Initial queue: {self._get_queue_stats()['total_pending']:,} pending episodes")

        last_report_time = time.time()
        report_interval = 300  # Report every 5 minutes

        try:
            while self.running:
                stats = self._get_queue_stats()

                if stats['total_pending'] == 0:
                    self._log("🎉 QUEUE COMPLETE - No more pending episodes!")
                    break

                # Get next batch
                episodes = self._get_next_batch(50)  # Process 50 at a time

                if not episodes:
                    self._log("⚠️  No episodes found in batch - possible database issue")
                    break

                self._log(f"🔄 Processing batch of {len(episodes)} episodes...")

                # Process each episode in batch
                for i, (episode_id, url, podcast_name, episode_title) in enumerate(episodes):
                    if not self.running:
                        break

                    self.current_podcast = podcast_name
                    self.current_batch = i + 1

                    self._process_episode(episode_id, url, podcast_name, episode_title)

                    # Save progress after each episode
                    self._save_progress()

                    # Brief pause to be respectful to sources
                    time.sleep(0.5)

                # Print progress report every 5 minutes
                current_time = time.time()
                if current_time - last_report_time >= report_interval:
                    self._print_progress_report()
                    last_report_time = current_time

                # Small break between batches
                time.sleep(2)

        except KeyboardInterrupt:
            self._log("🛑 INTERRUPTED by user")
        except Exception as e:
            self._log(f"💥 CRITICAL ERROR: {e}")
        finally:
            self.running = False
            self._save_progress()
            self._print_final_report()

    def _print_final_report(self):
        """Print final processing report"""
        runtime = datetime.now() - self.start_time if self.start_time else timedelta(0)
        hours, remainder = divmod(runtime.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)

        stats = self._get_queue_stats()

        print("\n" + "="*80)
        print(f"🎉 FINAL PROCESSING REPORT")
        print("="*80)
        print(f"⏱️  Total Runtime: {int(hours)}h {int(minutes)}m {int(seconds)}s")
        print(f"📊 Episodes Processed: {self.processed_count:,}")
        print(f"✅ Transcripts Found: {self.success_count:,}")
        print(f"❌ Processing Failed: {self.failed_count:,}")

        if self.processed_count > 0:
            success_rate = self.success_count / self.processed_count * 100
            print(f"📈 Success Rate: {success_rate:.1f}%")

        print(f"📋 Queue Status: {stats['total_pending']:,} remaining")

        # Estimate transcripts found this session vs existing
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM content WHERE content_type = 'podcast_transcript'")
        total_transcripts = cursor.fetchone()[0]
        conn.close()

        print(f"🗄️  Total Transcripts in DB: {total_transcripts:,}")
        print("="*80)

        self._log(f"🎉 PROCESSING COMPLETE: {self.success_count:,} new transcripts found")

def monitor_progress():
    """Monitor progress in real-time"""
    progress_file = "logs/processing_progress.json"
    log_file = "logs/trusted_processor.log"

    if not os.path.exists(progress_file):
        print("❌ No processing progress file found")
        print("   Run: python3 trusted_queue_processor.py")
        return

    try:
        while True:
            # Read progress
            with open(progress_file, "r") as f:
                progress = json.load(f)

            # Read last few log lines
            if os.path.exists(log_file):
                with open(log_file, "r") as f:
                    lines = f.readlines()
                    last_lines = lines[-10:] if len(lines) > 10 else lines

            # Clear screen and display
            os.system('clear' if os.name == 'posix' else 'cls')

            print("🎯 ATLAS TRUSTED PROCESSOR MONITOR")
            print("="*50)

            if progress.get('running'):
                print("🟢 STATUS: RUNNING")
            else:
                print("🔴 STATUS: STOPPED")

            print(f"📊 Processed: {progress.get('processed_count', 0):,}")
            print(f"✅ Success: {progress.get('success_count', 0):,}")
            print(f"❌ Failed: {progress.get('failed_count', 0):,}")

            if progress.get('start_time'):
                start = datetime.fromisoformat(progress['start_time'])
                runtime = datetime.now() - start
                hours, remainder = divmod(runtime.total_seconds(), 3600)
                minutes, seconds = divmod(remainder, 60)
                print(f"⏱️  Runtime: {int(hours)}h {int(minutes)}m {int(seconds)}s")

            if progress.get('current_podcast'):
                print(f"🎙️  Currently: {progress['current_podcast']}")

            print(f"\n📋 RECENT LOGS:")
            for line in last_lines[-5:]:
                print(f"   {line.strip()}")

            print(f"\nPress Ctrl+C to exit monitor")

            time.sleep(5)

    except KeyboardInterrupt:
        print("\n👋 Monitor stopped")
    except Exception as e:
        print(f"❌ Monitor error: {e}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Trusted Queue Processor")
    parser.add_argument("--monitor", action="store_true", help="Monitor progress only")
    parser.add_argument("--status", action="store_true", help="Show current status only")

    args = parser.parse_args()

    processor = TrustedQueueProcessor()

    if args.monitor:
        monitor_progress()
    elif args.status:
        stats = processor._get_queue_stats()
        print(f"📋 Queue Status: {stats['total_pending']:,} pending episodes")
        if os.path.exists(processor.progress_file):
            with open(processor.progress_file, "r") as f:
                progress = json.load(f)
            print(f"📊 Processed: {progress.get('processed_count', 0):,}")
            print(f"✅ Success: {progress.get('success_count', 0):,}")
    else:
        processor.run_continuous_processing()