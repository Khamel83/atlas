#!/usr/bin/env python3
"""
Atlas Telegram Manager
Interactive Telegram bot that can manage Atlas via commands
"""

import os
import requests
import time
import json
import subprocess
import logging
from pathlib import Path
from datetime import datetime
import threading

# Configuration from environment
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8208417039:AAFLpW5zfByJEvROgPuirHoH_BGMjmDXwvA")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "7884781716")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/ubuntu/dev/atlas/atlas_telegram_manager.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AtlasTelegramManager:
    """Interactive Telegram manager for Atlas"""

    def __init__(self):
        self.bot_token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.root_dir = Path("/home/ubuntu/dev/atlas")
        self.status_file = self.root_dir / "atlas_manager_status.json"

        # Command handlers
        self.commands = {
            '/start': self.cmd_start,
            '/help': self.cmd_help,
            '/status': self.cmd_status,
            '/restart': self.cmd_restart,
            '/stop': self.cmd_stop,
            '/progress': self.cmd_progress,
            '/logs': self.cmd_logs,
            '/health': self.cmd_health
        }

        # Initialize status
        self.load_status()
        logger.info("Atlas Telegram Manager initialized")

    def load_status(self):
        """Load current status from file"""
        try:
            if self.status_file.exists():
                with open(self.status_file, 'r') as f:
                    self.status = json.load(f)
            else:
                self.status = {
                    'started_at': datetime.now().isoformat(),
                    'commands_handled': 0,
                    'last_restart': None,
                    'last_stop': None
                }
        except Exception as e:
            logger.error(f"Error loading status: {e}")
            self.status = {
                'started_at': datetime.now().isoformat(),
                'commands_handled': 0,
                'last_restart': None,
                'last_stop': None
            }

    def save_status(self):
        """Save current status to file"""
        try:
            with open(self.status_file, 'w') as f:
                json.dump(self.status, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving status: {e}")

    def send_message(self, message):
        """Send message to Telegram"""
        try:
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }

            response = requests.post(f"{self.api_url}/sendMessage", json=payload, timeout=10)

            if response.status_code == 200:
                logger.info(f"✅ Telegram message sent")
                return True
            else:
                logger.error(f"❌ Failed to send Telegram message: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"❌ Error sending Telegram message: {e}")
            return False

    def get_atlas_processes(self):
        """Get all Atlas processes"""
        try:
            result = subprocess.run(
                ['ps', 'aux'],
                capture_output=True,
                text=True
            )

            processes = []
            for line in result.stdout.split('\n'):
                if 'atlas' in line.lower() and 'grep' not in line:
                    processes.append(line.strip())

            return processes
        except Exception as e:
            logger.error(f"Error getting processes: {e}")
            return []

    def get_database_progress(self):
        """Get processing progress from database"""
        try:
            db_path = self.root_dir / "podcast_processing.db"
            if not db_path.exists():
                return None

            result = subprocess.run([
                'sqlite3', str(db_path),
                "SELECT COUNT(*) FROM episodes WHERE processing_status = 'completed' OR transcript_found = TRUE;"
            ], capture_output=True, text=True)

            if result.returncode == 0:
                completed = int(result.stdout.strip() or 0)

                result = subprocess.run([
                    'sqlite3', str(db_path),
                    "SELECT COUNT(*) FROM episodes;"
                ], capture_output=True, text=True)

                if result.returncode == 0:
                    total = int(result.stdout.strip() or 0)
                    return {'completed': completed, 'total': total}

            return None
        except Exception as e:
            logger.error(f"Error getting database progress: {e}")
            return None

    def cmd_start(self, message_text):
        """Handle /start command"""
        response = "🤖 <b>Atlas Manager</b>\n\n"
        response += "I can manage your Atlas system via Telegram!\n\n"
        response += "<b>Available commands:</b>\n"
        response += "/help - Show this help\n"
        response += "/status - Check Atlas system status\n"
        response += "/progress - Show processing progress\n"
        response += "/restart - Restart Atlas processor\n"
        response += "/stop - Stop Atlas processor\n"
        response += "/logs - Show recent log entries\n"
        response += "/health - System health check\n\n"
        response += "Send any command to control Atlas!"
        return self.send_message(response)

    def cmd_help(self, message_text):
        """Handle /help command"""
        response = "🔧 <b>Atlas Commands</b>\n\n"
        response += "<b>Status Commands:</b>\n"
        response += "/status - System status\n"
        response += "/progress - Processing progress\n"
        response += "/health - Health check\n"
        response += "/logs - Recent logs\n\n"
        response += "<b>Control Commands:</b>\n"
        response += "/restart - Restart processor\n"
        response += "/stop - Stop processor\n\n"
        response += "<b>Info:</b>\n"
        response += "/start - Welcome message"
        return self.send_message(response)

    def cmd_status(self, message_text):
        """Handle /status command"""
        processes = self.get_atlas_processes()

        response = "📊 <b>Atlas Status</b>\n\n"

        if processes:
            response += f"🟢 <b>Running Processes: {len(processes)}</b>\n\n"
            for proc in processes[:5]:  # Show first 5 processes
                parts = proc.split()
                if len(parts) > 10:
                    pid = parts[1]
                    cmd = ' '.join(parts[10:])
                    response += f"• PID {pid}: {cmd[:50]}...\n"
        else:
            response += "🔴 <b>No Atlas processes running</b>\n"

        return self.send_message(response)

    def cmd_progress(self, message_text):
        """Handle /progress command"""
        progress = self.get_database_progress()

        response = "📈 <b>Processing Progress</b>\n\n"

        if progress:
            completed = progress['completed']
            total = progress['total']
            percentage = (completed / total * 100) if total > 0 else 0
            remaining = total - completed

            response += f"📝 Episodes with transcripts: <b>{completed:,}</b>\n"
            response += f"🎯 Total episodes: <b>{total:,}</b>\n"
            response += f"📊 Progress: <b>{percentage:.1f}%</b>\n"
            response += f"⏳ Remaining: <b>{remaining:,}</b>\n"
        else:
            response += "❌ Could not get progress information\n"
            response += "Database may be inaccessible"

        return self.send_message(response)

    def cmd_restart(self, message_text):
        """Handle /restart command"""
        try:
            response = "🔄 <b>Restarting Atlas...</b>\n\n"

            # Kill existing Atlas processes
            result = subprocess.run(
                ['pkill', '-f', 'atlas_transcript_processor.py'],
                capture_output=True
            )

            if result.returncode == 0:
                response += "✅ Stopped existing processes\n"
            else:
                response += "ℹ️ No existing processes to stop\n"

            # Start the processor
            os.chdir(self.root_dir)
            subprocess.Popen([
                'python3', 'atlas_transcript_processor.py'
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            response += "🚀 Started Atlas transcript processor\n\n"
            response += "⏱️ Give it 30 seconds to initialize..."

            # Update status
            self.status['last_restart'] = datetime.now().isoformat()
            self.save_status()

            return self.send_message(response)

        except Exception as e:
            error_msg = f"❌ Error restarting Atlas: {e}"
            return self.send_message(error_msg)

    def cmd_stop(self, message_text):
        """Handle /stop command"""
        try:
            response = "⏹️ <b>Stopping Atlas...</b>\n\n"

            # Kill Atlas processes
            result = subprocess.run(
                ['pkill', '-f', 'atlas_transcript_processor.py'],
                capture_output=True
            )

            if result.returncode == 0:
                response += "✅ Atlas processes stopped"
            else:
                response += "ℹ️ No Atlas processes were running"

            # Update status
            self.status['last_stop'] = datetime.now().isoformat()
            self.save_status()

            return self.send_message(response)

        except Exception as e:
            error_msg = f"❌ Error stopping Atlas: {e}"
            return self.send_message(error_msg)

    def cmd_logs(self, message_text):
        """Handle /logs command"""
        try:
            log_file = self.root_dir / "atlas_transcript.log"

            response = "📋 <b>Recent Atlas Logs</b>\n\n"

            if log_file.exists():
                # Get last 10 lines
                result = subprocess.run([
                    'tail', '-10', str(log_file)
                ], capture_output=True, text=True)

                if result.returncode == 0:
                    logs = result.stdout.strip().split('\n')
                    for log in logs[-8:]:  # Show last 8 lines
                        if log.strip():
                            response += f"• {log.strip()}\n"
                else:
                    response += "Could not read log file"
            else:
                response += "No log file found"

            return self.send_message(response)

        except Exception as e:
            error_msg = f"❌ Error getting logs: {e}"
            return self.send_message(error_msg)

    def cmd_health(self, message_text):
        """Handle /health command"""
        try:
            response = "🏥 <b>Atlas Health Check</b>\n\n"

            # Check processes
            processes = self.get_atlas_processes()
            response += f"🔄 Processes: {len(processes)} running\n"

            # Check database
            db_path = self.root_dir / "podcast_processing.db"
            response += f"💾 Database: {'✅ OK' if db_path.exists() else '❌ Missing'}\n"

            # Check log file
            log_file = self.root_dir / "atlas_transcript.log"
            if log_file.exists():
                # Check if log is recent (last 10 minutes)
                last_modified = log_file.stat().st_mtime
                current_time = time.time()
                if current_time - last_modified < 600:
                    response += "📝 Logs: ✅ Active\n"
                else:
                    response += "📝 Logs: ⚠️ Stale\n"
            else:
                response += "📝 Logs: ❌ Missing\n"

            # Check disk space
            result = subprocess.run(['df', '-h', '/home'], capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                if len(lines) > 1:
                    parts = lines[1].split()
                    if len(parts) > 4:
                        usage = parts[4]
                        response += f"💽 Disk: {usage} used\n"

            return self.send_message(response)

        except Exception as e:
            error_msg = f"❌ Health check error: {e}"
            return self.send_message(error_msg)

    def handle_message(self, message):
        """Handle incoming message"""
        try:
            text = message.get('text', '')
            message_id = message.get('message_id')

            logger.info(f"Received message: {text}")

            # Check if it's a command
            for cmd, handler in self.commands.items():
                if text.startswith(cmd):
                    self.status['commands_handled'] += 1
                    self.save_status()
                    handler(text)
                    return

            # Unknown command
            if text.startswith('/'):
                response = f"❓ Unknown command: {text}\n\n"
                response += "Use /help to see available commands"
                self.send_message(response)

        except Exception as e:
            logger.error(f"Error handling message: {e}")
            self.send_message(f"❌ Error: {e}")

    def get_updates(self, offset=None):
        """Get updates from Telegram"""
        try:
            params = {'timeout': 30}
            if offset:
                params['offset'] = offset

            response = requests.get(
                f"{self.api_url}/getUpdates",
                params=params,
                timeout=35
            )

            if response.status_code == 200:
                data = response.json()
                return data.get('result', [])
            else:
                logger.error(f"Error getting updates: {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"Error getting updates: {e}")
            return []

    def run_once(self):
        """Run a single command check"""
        logger.info("Checking for new messages...")

        # Get last message
        updates = self.get_updates()

        if updates:
            last_update = updates[-1]
            message = last_update.get('message', {})

            # Only process if it's from our chat
            if message.get('chat', {}).get('id') == int(self.chat_id):
                self.handle_message(message)

def main():
    """Main execution"""
    import argparse

    parser = argparse.ArgumentParser(description='Atlas Telegram Manager')
    parser.add_argument('--check-once', action='store_true',
                       help='Check for messages once and exit')

    args = parser.parse_args()

    manager = AtlasTelegramManager()

    if args.check_once:
        manager.run_once()
    else:
        # Continuous mode (for future use)
        logger.info("Starting continuous mode...")
        while True:
            manager.run_once()
            time.sleep(30)  # Check every 30 seconds

if __name__ == "__main__":
    main()