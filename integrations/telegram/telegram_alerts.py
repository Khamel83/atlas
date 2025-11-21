#!/usr/bin/env python3
"""
Simple Telegram Alerts for Atlas
Uses existing .env configuration for Telegram notifications
"""

import os
import logging
import requests
import json
from datetime import datetime
from typing import Dict, Any, Optional
import sqlite3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleTelegramAlerts:
    def __init__(self, db_path: str = 'data/atlas.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()

        # Load Telegram configuration from .env
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')

        self.enabled = bool(self.bot_token and self.chat_id)

        if self.enabled:
            logger.info("Telegram alerts enabled")
        else:
            logger.warning("Telegram alerts disabled - missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID in .env")

    def send_telegram_message(self, message: str) -> bool:
        """Send message via Telegram"""
        if not self.enabled:
            logger.warning("Telegram not configured - message not sent")
            return False

        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }

            response = requests.post(url, json=data, timeout=10)

            if response.status_code == 200:
                logger.info("Telegram message sent successfully")
                return True
            else:
                logger.error(f"Telegram API error: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            return False

    def get_daily_summary(self) -> Dict[str, Any]:
        """Get daily summary statistics"""
        try:
            # Get transcript count
            self.cursor.execute("SELECT COUNT(*) FROM content WHERE content_type = 'podcast_transcript'")
            transcript_count = self.cursor.fetchone()[0]

            # Get queue status
            self.cursor.execute("SELECT status, COUNT(*) FROM episode_queue GROUP BY status")
            queue_status = dict(self.cursor.fetchall())

            # Get today's activity
            today = datetime.now().strftime('%Y-%m-%d')
            self.cursor.execute(
                "SELECT COUNT(*) FROM content WHERE DATE(created_at) = ?",
                [today]
            )
            today_added = self.cursor.fetchone()[0]

            # Calculate success rate
            total_processed = queue_status.get('found', 0) + queue_status.get('not_found', 0)
            success_rate = (queue_status.get('found', 0) / total_processed * 100) if total_processed > 0 else 0

            return {
                'date': today,
                'transcript_count': transcript_count,
                'queue_status': queue_status,
                'today_added': today_added,
                'success_rate': success_rate,
                'total_episodes': sum(queue_status.values())
            }

        except Exception as e:
            logger.error(f"Error getting daily summary: {e}")
            return {}

    def send_daily_summary(self) -> bool:
        """Send daily summary via Telegram"""
        try:
            summary = self.get_daily_summary()
            if not summary:
                return False

            message = f"""📊 <b>Atlas Daily Summary</b>
🗓️ <b>Date:</b> {summary['date']}
📚 <b>Total Transcripts:</b> {summary['transcript_count']:,}
📥 <b>Added Today:</b> {summary['today_added']}
🔄 <b>Queue Status:</b>
  • Pending: {summary['queue_status'].get('pending', 0):,}
  • Found: {summary['queue_status'].get('found', 0):,}
  • Not Found: {summary['queue_status'].get('not_found', 0):,}
  • Error: {summary['queue_status'].get('error', 0):,}
✅ <b>Success Rate:</b> {summary['success_rate']:.1f}%
🎯 <b>Total Episodes:</b> {summary['total_episodes']:,}

<i>Automated report from Atlas</i>"""

            return self.send_telegram_message(message)

        except Exception as e:
            logger.error(f"Error sending daily summary: {e}")
            return False

    def send_error_alert(self, error_message: str, context: str = "") -> bool:
        """Send error alert via Telegram"""
        try:
            message = f"""🚨 <b>Atlas Error Alert</b>

⚠️ <b>Error:</b> {error_message}
📍 <b>Context:</b> {context}
⏰ <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

<i>Please check the system logs for more details</i>"""

            return self.send_telegram_message(message)

        except Exception as e:
            logger.error(f"Error sending error alert: {e}")
            return False

    def send_system_status(self, status: str, details: str = "") -> bool:
        """Send system status update via Telegram"""
        try:
            message = f"""🔧 <b>Atlas System Status</b>

📊 <b>Status:</b> {status}
📝 <b>Details:</b> {details}
⏰ <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

<i>Automated status update from Atlas</i>"""

            return self.send_telegram_message(message)

        except Exception as e:
            logger.error(f"Error sending system status: {e}")
            return False

    def test_telegram_connection(self) -> bool:
        """Test Telegram connection"""
        if not self.enabled:
            logger.warning("Telegram not configured")
            return False

        test_message = f"""🧪 <b>Atlas Telegram Test</b>

✅ Telegram alerts are working!
⏰ <b>Test Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

<i>This is a test message to confirm Telegram notifications are configured correctly</i>"""

        return self.send_telegram_message(test_message)

    def run_alerts_check(self):
        """Run alerts check and send if needed"""
        try:
            if not self.enabled:
                logger.info("Telegram alerts not configured - skipping")
                print("✅ Telegram alerts check completed (not configured)")
                return

            # Test connection
            if self.test_telegram_connection():
                print("✅ Telegram alerts configured and working")

                # Send daily summary
                if self.send_daily_summary():
                    print("✅ Daily summary sent via Telegram")
                else:
                    print("❌ Failed to send daily summary")
            else:
                print("❌ Telegram connection test failed")

        except Exception as e:
            logger.error(f"Error in alerts check: {e}")
            print(f"❌ Error in alerts check: {e}")

def main():
    """Main function to test Telegram alerts"""
    alerts = SimpleTelegramAlerts()

    print("📱 Testing Telegram Alerts System")
    print("=" * 50)

    # Show configuration status
    if alerts.enabled:
        print("✅ Telegram is configured")
        print(f"🤖 Bot Token: {alerts.bot_token[:20]}...")
        print(f"💬 Chat ID: {alerts.chat_id}")
    else:
        print("❌ Telegram is not configured")
        print("Please add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to .env")
        return

    # Test connection
    print("\n🧪 Testing Telegram connection...")
    if alerts.test_telegram_connection():
        print("✅ Telegram connection successful")

        # Send daily summary
        print("\n📊 Sending daily summary...")
        if alerts.send_daily_summary():
            print("✅ Daily summary sent successfully")
        else:
            print("❌ Failed to send daily summary")
    else:
        print("❌ Telegram connection failed")

if __name__ == "__main__":
    main()