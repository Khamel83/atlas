#!/usr/bin/env python3
"""
REAL-TIME MONITORING DASHBOARD
Watch the trusted processor work live
"""

import time
import json
import os
import sqlite3
from datetime import datetime
import subprocess

def clear_screen():
    os.system('clear' if os.name == 'posix' else 'cls')

def get_database_stats():
    """Get current database statistics"""
    try:
        conn = sqlite3.connect('data/atlas.db')
        cursor = conn.cursor()

        # Get transcript count
        cursor.execute("SELECT COUNT(*) FROM content WHERE content_type = 'podcast_transcript'")
        total_transcripts = cursor.fetchone()[0]

        # Get queue stats
        cursor.execute("SELECT status, COUNT(*) FROM episode_queue GROUP BY status")
        queue_stats = dict(cursor.fetchall())

        # Get success rate from recent processing
        cursor.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN status = 'found' THEN 1 ELSE 0 END) as found
            FROM episode_queue
            WHERE updated_at >= datetime('now', '-1 hour')
        """)
        recent_stats = cursor.fetchone()

        conn.close()

        return {
            'total_transcripts': total_transcripts,
            'queue_stats': queue_stats,
            'recent_total': recent_stats[0] if recent_stats else 0,
            'recent_found': recent_stats[1] if recent_stats else 0
        }
    except Exception as e:
        return {'error': str(e)}

def get_progress_data():
    """Get progress from the processing file"""
    try:
        if os.path.exists('logs/processing_progress.json'):
            with open('logs/processing_progress.json', 'r') as f:
                return json.load(f)
    except:
        pass
    return {}

def get_recent_logs():
    """Get recent log entries"""
    try:
        if os.path.exists('logs/trusted_processor.log'):
            with open('logs/trusted_processor.log', 'r') as f:
                lines = f.readlines()
                return lines[-20:]  # Last 20 lines
    except:
        pass
    return []

def check_processor_running():
    """Check if the processor is still running"""
    try:
        result = subprocess.run(['pgrep', '-f', 'python3 trusted_queue_processor.py'],
                              capture_output=True, text=True)
        return result.returncode == 0
    except:
        return False

def monitor_dashboard():
    """Main monitoring dashboard"""
    print("🎯 STARTING REAL-TIME MONITORING...")
    time.sleep(2)

    try:
        while True:
            clear_screen()

            # Header
            print("🎯 ATLAS TRUSTED PROCESSOR - REAL-TIME MONITOR")
            print("=" * 80)
            print(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print()

            # Processor Status
            running = check_processor_running()
            status_color = "🟢" if running else "🔴"
            print(f"{status_color} PROCESSOR STATUS: {'RUNNING' if running else 'STOPPED'}")
            print()

            # Progress Data
            progress = get_progress_data()
            if progress:
                processed = progress.get('processed_count', 0)
                success = progress.get('success_count', 0)
                failed = progress.get('failed_count', 0)

                print("📊 PROCESSING PROGRESS:")
                print(f"   Episodes Processed: {processed:,}")
                print(f"   ✅ Transcripts Found: {success:,}")
                print(f"   ❌ Processing Failed: {failed:,}")

                if processed > 0:
                    success_rate = (success / processed) * 100
                    print(f"   📈 Success Rate: {success_rate:.1f}%")

                if progress.get('start_time'):
                    start_time = datetime.fromisoformat(progress['start_time'])
                    runtime = datetime.now() - start_time
                    hours = runtime.total_seconds() / 3600
                    print(f"   ⏱️  Runtime: {hours:.1f} hours")

                    if hours > 0:
                        eps = processed / hours
                        print(f"   ⚡ Speed: {eps:.1f} episodes/hour")

                current_podcast = progress.get('current_podcast')
                if current_podcast:
                    print(f"   🎙️  Currently Processing: {current_podcast}")

            print()

            # Database Stats
            db_stats = get_database_stats()
            if 'error' not in db_stats:
                print("🗄️  DATABASE STATUS:")
                print(f"   Total Transcripts: {db_stats['total_transcripts']:,}")

                queue_stats = db_stats['queue_stats']
                pending = queue_stats.get('pending', 0)
                print(f"   Queue Remaining: {pending:,}")

                if db_stats['recent_total'] > 0:
                    recent_rate = (db_stats['recent_found'] / db_stats['recent_total']) * 100
                    print(f"   Recent Success Rate: {recent_rate:.1f}% (last hour)")

            print()

            # Recent Activity
            logs = get_recent_logs()
            if logs:
                print("📝 RECENT ACTIVITY:")
                for log in logs[-5:]:  # Show last 5 entries
                    # Remove timestamp for cleaner display
                    if ' - ' in log:
                        clean_log = log.split(' - ', 1)[1].strip()
                        print(f"   {clean_log}")
                    else:
                        print(f"   {log.strip()}")

            print()

            # Commands
            print("💡 COMMANDS:")
            print("   • ./monitor_processing.sh   - Quick status check")
            print("   • tail -f logs/trusted_processor.log  - Live logs")
            print("   • pkill -f trusted_queue_processor  - Stop processing")
            print("   • Ctrl+C to exit monitor")

            # Update every 10 seconds
            time.sleep(10)

    except KeyboardInterrupt:
        print("\n👋 Monitor stopped")

if __name__ == "__main__":
    monitor_dashboard()