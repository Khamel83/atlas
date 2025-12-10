#!/usr/bin/env python3
"""
Simple Telegram Command Handler for Atlas
Manual command execution - send commands via argument
"""

import subprocess
import json
import requests
import os
from pathlib import Path
from datetime import datetime

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8208417039:AAFLpW5zfByJEvROgPuirHoH_BGMjmDXwvA")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "7884781716")

def send_telegram_message(message):
    """Send message to Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'HTML'
        }

        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Error sending message: {e}")
        return False

def get_status():
    """Get Atlas system status"""
    try:
        # Get processes
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        processes = [line for line in result.stdout.split('\n') if 'atlas' in line.lower() and 'grep' not in line]

        response = "📊 <b>Atlas System Status</b>\n\n"
        response += f"🔄 <b>Processes:</b> {len(processes)} running\n\n"

        for proc in processes[:3]:  # Show top 3
            parts = proc.split()
            if len(parts) > 10:
                pid = parts[1]
                cpu = parts[2]
                mem = parts[3]
                cmd = ' '.join(parts[10:])[:40]
                response += f"• PID {pid} | CPU {cpu}% | MEM {mem}%\n  {cmd}...\n\n"

        # Database status
        db_path = Path("podcast_processing.db")
        if db_path.exists():
            response += "💾 <b>Database:</b> ✅ Available\n"

            # Get progress
            try:
                result = subprocess.run([
                    'sqlite3', 'podcast_processing.db',
                    "SELECT COUNT(*) FROM episodes WHERE transcript_found = TRUE;"
                ], capture_output=True, text=True)

                if result.returncode == 0:
                    completed = int(result.stdout.strip() or 0)
                    response += f"📝 <b>Episodes with transcripts:</b> {completed:,}\n"
            except:
                response += "📝 <b>Episodes with transcripts:</b> ❓ Unknown\n"
        else:
            response += "💾 <b>Database:</b> ❌ Missing\n"

        return response

    except Exception as e:
        return f"❌ Error getting status: {e}"

def restart_atlas():
    """Restart Atlas processor"""
    try:
        # Stop existing processes
        subprocess.run(['pkill', '-f', 'atlas_transcript_processor.py'], capture_output=True)

        # Start new one
        subprocess.Popen([
            'python3', 'atlas_transcript_processor.py'
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        return "🔄 <b>Atlas Restarted!</b>\n\n✅ Stopped existing processes\n🚀 Started new transcript processor\n\n⏱️ Give it 30 seconds to initialize..."

    except Exception as e:
        return f"❌ Error restarting Atlas: {e}"

def stop_atlas():
    """Stop Atlas processor"""
    try:
        result = subprocess.run(['pkill', '-f', 'atlas_transcript_processor.py'], capture_output=True)

        if result.returncode == 0:
            return "⏹️ <b>Atlas Stopped!</b>\n\n✅ Transcript processor stopped"
        else:
            return "ℹ️ <b>No Atlas processes running</b>\n\nNothing to stop"

    except Exception as e:
        return f"❌ Error stopping Atlas: {e}"

def get_progress():
    """Get processing progress"""
    try:
        db_path = Path("podcast_processing.db")
        if not db_path.exists():
            return "❌ Database not found"

        # Get completed count
        result = subprocess.run([
            'sqlite3', 'podcast_processing.db',
            "SELECT COUNT(*) FROM episodes WHERE transcript_found = TRUE;"
        ], capture_output=True, text=True)

        if result.returncode != 0:
            return "❌ Error querying database"

        completed = int(result.stdout.strip() or 0)

        # Get total count
        result = subprocess.run([
            'sqlite3', 'podcast_processing.db',
            "SELECT COUNT(*) FROM episodes;"
        ], capture_output=True, text=True)

        if result.returncode != 0:
            return "❌ Error querying database"

        total = int(result.stdout.strip() or 0)
        percentage = (completed / total * 100) if total > 0 else 0
        remaining = total - completed

        response = "📈 <b>Atlas Processing Progress</b>\n\n"
        response += f"📝 <b>Completed:</b> {completed:,} episodes\n"
        response += f"🎯 <b>Total:</b> {total:,} episodes\n"
        response += f"📊 <b>Progress:</b> {percentage:.1f}%\n"
        response += f"⏳ <b>Remaining:</b> {remaining:,} episodes\n"

        if percentage > 0:
            eta_hours = (remaining / (completed / (24 * 60 / 30))) if completed > 0 else 0  # Rough estimate
            response += f"🕐 <b>Est. Time:</b> ~{eta_hours:.0f} hours"

        return response

    except Exception as e:
        return f"❌ Error getting progress: {e}"

def get_health():
    """System health check"""
    try:
        response = "🏥 <b>Atlas Health Check</b>\n\n"

        # Process check
        result = subprocess.run(['pgrep', '-f', 'atlas'], capture_output=True)
        process_count = len(result.stdout.decode().strip().split('\n')) if result.stdout else 0
        response += f"🔄 <b>Processes:</b> {'✅ Good' if process_count > 0 else '⚠️ None'} ({process_count})\n"

        # Database check
        db_path = Path("podcast_processing.db")
        response += f"💾 <b>Database:</b> {'✅ OK' if db_path.exists() else '❌ Missing'}\n"

        # Log file check
        log_path = Path("atlas_transcript.log")
        if log_path.exists():
            import time
            last_modified = log_path.stat().st_mtime
            age_minutes = (time.time() - last_modified) / 60
            if age_minutes < 10:
                response += f"📝 <b>Logs:</b> ✅ Active ({age_minutes:.0f} min old)\n"
            else:
                response += f"📝 <b>Logs:</b> ⚠️ Stale ({age_minutes:.0f} min old)\n"
        else:
            response += "📝 <b>Logs:</b> ❌ Missing\n"

        # Disk space
        try:
            result = subprocess.run(['df', '-h', '/home'], capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                if len(lines) > 1:
                    parts = lines[1].split()
                    if len(parts) > 4:
                        usage = parts[4]
                        response += f"💽 <b>Disk:</b> {usage} used\n"
        except:
            pass

        return response

    except Exception as e:
        return f"❌ Health check error: {e}"

def get_logs():
    """Get recent log entries"""
    try:
        log_path = Path("atlas_transcript.log")

        response = "📋 <b>Recent Atlas Logs</b>\n\n"

        if not log_path.exists():
            return response + "❌ No log file found"

        # Get last 8 lines
        result = subprocess.run(['tail', '-8', str(log_path)], capture_output=True, text=True)

        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if line.strip():
                    response += f"• {line.strip()}\n"
        else:
            response += "❌ Could not read log file"

        return response

    except Exception as e:
        return f"❌ Error getting logs: {e}"

def main():
    """Main execution"""
    import argparse

    parser = argparse.ArgumentParser(description='Atlas Telegram Commands')
    parser.add_argument('command', choices=['status', 'restart', 'stop', 'progress', 'health', 'logs', 'dashboard'],
                       help='Command to execute')

    args = parser.parse_args()

    # Map commands to functions
    commands = {
        'status': get_status,
        'restart': restart_atlas,
        'stop': stop_atlas,
        'progress': get_progress,
        'health': get_health,
        'logs': get_logs,
        'dashboard': get_status  # Alias for status
    }

    # Execute command
    if args.command in commands:
        message = commands[args.command]()
        success = send_telegram_message(message)
        print(f"Message sent: {'✅' if success else '❌'}")
    else:
        print(f"Unknown command: {args.command}")

if __name__ == "__main__":
    main()