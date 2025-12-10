#!/usr/bin/env python3
"""
Atlas Telegram Monitor
Simple monitoring that sends "ATLAS down" when processing stops
and "ATLAS up" when it restarts.
"""

import os
import requests
import time
import json
import subprocess
import logging
from pathlib import Path
from datetime import datetime

# Configuration from environment
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8208417039:AAFLpW5zfByJEvROgPuirHoH_BGMjmDXwvA")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "7884781716")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/ubuntu/dev/atlas/atlas_telegram.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AtlasTelegramMonitor:
    """Simple Telegram monitor for Atlas status"""

    def __init__(self):
        self.bot_token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        self.root_dir = Path("/home/ubuntu/dev/atlas")
        self.status_file = self.root_dir / "atlas_status.json"

        # Initialize status
        self.load_status()

    def load_status(self):
        """Load current status from file"""
        try:
            if self.status_file.exists():
                with open(self.status_file, 'r') as f:
                    self.status = json.load(f)
            else:
                self.status = {
                    'last_up': None,
                    'last_down': None,
                    'current_state': 'unknown',
                    'total_notifications': 0
                }
        except Exception as e:
            logger.error(f"Error loading status: {e}")
            self.status = {
                'last_up': None,
                'last_down': None,
                'current_state': 'unknown',
                'total_notifications': 0
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

            response = requests.post(self.api_url, json=payload, timeout=10)

            if response.status_code == 200:
                logger.info(f"✅ Telegram message sent: {message}")
                self.status['total_notifications'] += 1
                return True
            else:
                logger.error(f"❌ Failed to send Telegram message: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"❌ Error sending Telegram message: {e}")
            return False

    def send_atlas_up(self):
        """Send ATLAS up notification"""
        if self.status['current_state'] != 'up':
            message = "🟢 <b>ATLAS up</b>\n\nAtlas transcript processor is now running."
            success = self.send_message(message)

            if success:
                self.status['current_state'] = 'up'
                self.status['last_up'] = datetime.now().isoformat()
                self.save_status()

            return success
        else:
            logger.info("Atlas is already marked as up, not sending notification")
            return True

    def send_atlas_down(self):
        """Send ATLAS down notification"""
        if self.status['current_state'] != 'down':
            message = "🔴 <b>ATLAS down</b>\n\nAtlas transcript processor has stopped or is not processing."
            success = self.send_message(message)

            if success:
                self.status['current_state'] = 'down'
                self.status['last_down'] = datetime.now().isoformat()
                self.save_status()

            return success
        else:
            logger.info("Atlas is already marked as down, not sending notification")
            return True

    def is_atlas_running(self):
        """Check if Atlas transcript processor is running"""
        try:
            # Check for the process
            result = subprocess.run(
                ['pgrep', '-f', 'atlas_transcript_processor.py'],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                # Process is running, now check if it's actually processing
                # Check the log file for recent activity
                log_file = self.root_dir / "atlas_transcript.log"
                if log_file.exists():
                    # Check last modification time
                    last_modified = log_file.stat().st_mtime
                    current_time = time.time()

                    # Consider it active if log was updated in last 5 minutes
                    if current_time - last_modified < 300:  # 5 minutes
                        return True

            return False

        except Exception as e:
            logger.error(f"Error checking Atlas status: {e}")
            return False

    def check_and_notify(self):
        """Check Atlas status and send appropriate notification"""
        is_running = self.is_atlas_running()

        if is_running:
            logger.info("Atlas is running")
            return self.send_atlas_up()
        else:
            logger.warning("Atlas is not running")
            return self.send_atlas_down()

    def get_status_summary(self):
        """Get current status summary"""
        return {
            'current_state': self.status['current_state'],
            'last_up': self.status['last_up'],
            'last_down': self.status['last_down'],
            'total_notifications': self.status['total_notifications']
        }

def main():
    """Main execution"""
    import argparse

    parser = argparse.ArgumentParser(description='Atlas Telegram Monitor')
    parser.add_argument('--check', action='store_true',
                       help='Check current status and notify if changed')
    parser.add_argument('--up', action='store_true',
                       help='Send ATLAS up notification')
    parser.add_argument('--down', action='store_true',
                       help='Send ATLAS down notification')
    parser.add_argument('--status', action='store_true',
                       help='Show current status')

    args = parser.parse_args()

    monitor = AtlasTelegramMonitor()

    if args.up:
        monitor.send_atlas_up()
    elif args.down:
        monitor.send_atlas_down()
    elif args.status:
        status = monitor.get_status_summary()
        print(f"Current state: {status['current_state']}")
        print(f"Last up: {status['last_up']}")
        print(f"Last down: {status['last_down']}")
        print(f"Total notifications: {status['total_notifications']}")
    elif args.check:
        monitor.check_and_notify()
    else:
        # Default: check status
        monitor.check_and_notify()

if __name__ == "__main__":
    main()