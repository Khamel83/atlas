#!/usr/bin/env python3
"""
Enhanced Progress Watchdog for Atlas
Monitors transcript processing progress and auto-restarts on stall.

Logic: If podcast_episodes > 0 AND no new transcriptions in last 30 minutes,
then restart relevant services and send alerts.
"""

import os
import sys
import sqlite3
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.database_config import get_database_connection
from helpers.metrics_collector import get_metrics_collector
from scripts.alert_manager import AlertManager


class EnhancedProgressWatchdog:
    """Monitor transcript processing and auto-heal stalls"""

    def __init__(self):
        self.stall_threshold_minutes = 30
        self.log_lines_to_dump = 200

    def check_transcript_progress(self) -> dict:
        """Check transcript processing progress"""
        try:
            conn = get_database_connection()
            cursor = conn.cursor()

            # Get episode and transcription counts
            cursor.execute("SELECT COUNT(*) FROM podcast_episodes")
            episodes_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM transcriptions")
            transcriptions_count = cursor.fetchone()[0]

            # Get latest transcription timestamp
            cursor.execute("SELECT MAX(created_at) FROM transcriptions WHERE created_at IS NOT NULL")
            latest_transcription = cursor.fetchone()[0]

            # Calculate time since last transcription
            minutes_since_last = None
            if latest_transcription:
                try:
                    # Handle both datetime formats
                    if 'T' in latest_transcription:
                        last_time = datetime.fromisoformat(latest_transcription.replace('Z', '+00:00'))
                    else:
                        last_time = datetime.strptime(latest_transcription, '%Y-%m-%d %H:%M:%S')

                    minutes_since_last = (datetime.now() - last_time).total_seconds() / 60
                except Exception as e:
                    print(f"⚠️ Error parsing timestamp {latest_transcription}: {e}")
                    minutes_since_last = 999  # Assume very old
            else:
                minutes_since_last = 999  # No transcriptions yet

            conn.close()

            # Update metrics
            metrics_collector = get_metrics_collector()
            metrics_collector.record_metric("atlas_episodes_total", episodes_count)
            metrics_collector.record_metric("atlas_transcriptions_total", transcriptions_count)
            metrics_collector.record_metric("atlas_minutes_since_last_transcription", minutes_since_last)

            # Calculate transcription rate for metrics
            transcription_rate = 0
            if minutes_since_last < 60:  # Recent activity
                # Estimate rate based on recent progress
                transcription_rate = 60 / max(minutes_since_last, 1)  # per hour
            metrics_collector.record_metric("atlas_transcription_rate", transcription_rate)

            return {
                'episodes_count': episodes_count,
                'transcriptions_count': transcriptions_count,
                'latest_transcription': latest_transcription,
                'minutes_since_last': minutes_since_last,
                'is_stalled': episodes_count > 0 and minutes_since_last > self.stall_threshold_minutes
            }

        except Exception as e:
            print(f"❌ Error checking transcript progress: {e}")
            return {'error': str(e)}

    def get_log_excerpts(self) -> dict:
        """Get recent log excerpts from relevant services"""
        log_files = {
            'atlas_service': '/home/ubuntu/dev/atlas/logs/atlas_service.log',
            'scheduler': '/home/ubuntu/dev/atlas/logs/atlas_scheduler.log',
            'transcript_discovery': '/home/ubuntu/dev/atlas/logs/transcript_discovery.log',
            'enhanced_transcript_discovery': '/home/ubuntu/dev/atlas/logs/enhanced_transcript_discovery.log'
        }

        excerpts = {}

        for log_name, log_path in log_files.items():
            try:
                if os.path.exists(log_path):
                    result = subprocess.run(
                        ['tail', '-n', str(self.log_lines_to_dump), log_path],
                        capture_output=True, text=True, timeout=10
                    )
                    if result.returncode == 0:
                        excerpts[log_name] = result.stdout[-2000:]  # Limit to 2KB
                    else:
                        excerpts[log_name] = f"Error reading log: {result.stderr}"
                else:
                    excerpts[log_name] = "Log file not found"
            except Exception as e:
                excerpts[log_name] = f"Error accessing log: {e}"

        return excerpts

    def restart_transcript_services(self) -> dict:
        """Restart transcript-related services"""
        services_to_restart = [
            'atlas.service',
            # Add more service names as they're created
        ]

        results = {}

        for service in services_to_restart:
            try:
                print(f"🔄 Restarting {service}...")
                result = subprocess.run(
                    ['sudo', 'systemctl', 'restart', service],
                    capture_output=True, text=True, timeout=30
                )

                if result.returncode == 0:
                    print(f"✅ {service} restarted successfully")
                    results[service] = 'restarted'
                else:
                    print(f"❌ Failed to restart {service}: {result.stderr}")
                    results[service] = f'failed: {result.stderr}'

            except Exception as e:
                print(f"💥 Error restarting {service}: {e}")
                results[service] = f'error: {e}'

        return results

    def send_stall_alert(self, progress_info: dict, log_excerpts: dict, restart_results: dict):
        """Send alert about stall and restart"""
        try:
            # Format alert message
            title = "Atlas Transcript Processing Stalled"

            message = f"""**Transcript Processing Stalled**

**Statistics:**
• Episodes: {progress_info.get('episodes_count', 'Unknown'):,}
• Transcriptions: {progress_info.get('transcriptions_count', 'Unknown'):,}
• Last Activity: {progress_info.get('minutes_since_last', 'Unknown'):.0f} minutes ago
• Latest: {progress_info.get('latest_transcription', 'None')}

**Restart Results:**
"""

            for service, result in restart_results.items():
                status_emoji = "✅" if result == 'restarted' else "❌"
                message += f"• {status_emoji} {service}: {result}\n"

            message += "\n**Recent Log Activity:**\n"
            for log_name, excerpt in log_excerpts.items():
                if excerpt and excerpt != "Log file not found":
                    # Get last few lines only for alert
                    lines = excerpt.strip().split('\n')[-5:]
                    message += f"\n_{log_name}_:\n```\n" + '\n'.join(lines) + "\n```\n"

            # Use new alert manager for centralized alerting
            alert_manager = AlertManager()
            alert_manager.send_alert(title, message, "critical")

        except Exception as e:
            print(f"💥 Error sending stall alert: {e}")

    def send_recovery_alert(self, progress_info: dict):
        """Send recovery alert when processing resumes"""
        try:
            title = "Atlas Transcript Processing Recovered"
            message = f"""**Processing has resumed!**

• Transcriptions: {progress_info.get('transcriptions_count', 'Unknown'):,}
• Latest: {progress_info.get('latest_transcription', 'None')}
• System is now healthy ✅
"""

            # Use new alert manager for centralized alerting
            alert_manager = AlertManager()
            alert_manager.send_alert(title, message, "recovery")

        except Exception as e:
            print(f"💥 Error sending recovery alert: {e}")

    def run_watchdog_check(self):
        """Run a single watchdog check"""
        print(f"🔍 Running transcript progress check at {datetime.now()}")

        # Check progress
        progress_info = self.check_transcript_progress()

        if 'error' in progress_info:
            print(f"❌ Cannot check progress: {progress_info['error']}")
            return

        print(f"📊 Episodes: {progress_info['episodes_count']:,}, "
              f"Transcriptions: {progress_info['transcriptions_count']:,}, "
              f"Last activity: {progress_info['minutes_since_last']:.0f}m ago")

        if progress_info['is_stalled']:
            print("🚨 STALL DETECTED - Taking action")

            # Get log excerpts
            log_excerpts = self.get_log_excerpts()

            # Restart services
            restart_results = self.restart_transcript_services()

            # Send alert
            self.send_stall_alert(progress_info, log_excerpts, restart_results)

            # Mark that we've taken action (could store this in a file)
            with open('/tmp/atlas_last_restart', 'w') as f:
                f.write(str(datetime.now()))

        else:
            print("✅ Progress is healthy")

            # Check if we recently restarted and should send recovery alert
            if os.path.exists('/tmp/atlas_last_restart'):
                try:
                    with open('/tmp/atlas_last_restart', 'r') as f:
                        last_restart = datetime.fromisoformat(f.read().strip())

                    # If last restart was recent and we're now healthy, send recovery
                    if (datetime.now() - last_restart).total_seconds() < 3600:  # Within last hour
                        self.send_recovery_alert(progress_info)
                        os.remove('/tmp/atlas_last_restart')  # Clear flag

                except Exception as e:
                    print(f"⚠️ Error checking restart flag: {e}")

    def run_continuous_monitoring(self, check_interval_minutes: int = 5):
        """Run continuous monitoring"""
        print(f"🔄 Starting continuous transcript progress monitoring (every {check_interval_minutes}m)")
        print("Press Ctrl+C to stop")

        try:
            while True:
                self.run_watchdog_check()
                time.sleep(check_interval_minutes * 60)

        except KeyboardInterrupt:
            print("\n🛑 Stopping watchdog monitoring")


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Enhanced Progress Watchdog')
    parser.add_argument('--continuous', action='store_true', help='Run continuously')
    parser.add_argument('--interval', type=int, default=5, help='Check interval in minutes')
    parser.add_argument('--threshold', type=int, default=30, help='Stall threshold in minutes')

    args = parser.parse_args()

    watchdog = EnhancedProgressWatchdog()
    watchdog.stall_threshold_minutes = args.threshold

    if args.continuous:
        watchdog.run_continuous_monitoring(args.interval)
    else:
        watchdog.run_watchdog_check()


if __name__ == "__main__":
    main()