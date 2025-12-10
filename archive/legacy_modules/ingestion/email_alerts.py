#!/usr/bin/env python3
"""
Simple Email Alerts for Atlas
Sends daily summaries and error notifications
"""

import smtplib
import sqlite3
import os
import json
import logging
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/email_alerts.log'),
        logging.StreamHandler()
    ]
)

class EmailAlerts:
    def __init__(self):
        self.config = self.load_config()
        self.conn = sqlite3.connect('data/atlas.db')
        self.cursor = self.conn.cursor()

    def load_config(self):
        """Load email configuration from environment or config file"""
        config = {
            'smtp_server': os.environ.get('SMTP_SERVER', 'smtp.gmail.com'),
            'smtp_port': int(os.environ.get('SMTP_PORT', '587')),
            'smtp_user': os.environ.get('SMTP_USER', ''),
            'smtp_password': os.environ.get('SMTP_PASSWORD', ''),
            'from_email': os.environ.get('FROM_EMAIL', ''),
            'to_email': os.environ.get('TO_EMAIL', ''),
            'enabled': os.environ.get('EMAIL_ENABLED', 'false').lower() == 'true'
        }

        # Try to load from config file if environment variables not set
        if not config['enabled'] and os.path.exists('config/email_config.json'):
            try:
                with open('config/email_config.json', 'r') as f:
                    file_config = json.load(f)
                    config.update(file_config)
                    config['enabled'] = True
            except Exception as e:
                logging.warning(f"Could not load email config: {e}")

        return config

    def get_daily_summary(self):
        """Get daily summary statistics"""
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)

        # Get today's processing stats
        today_processed = self.cursor.execute(
            "SELECT COUNT(*) FROM episode_queue WHERE DATE(created_at) = ?",
            [today.isoformat()]
        ).fetchone()[0]

        # Get transcripts found today
        today_found = self.cursor.execute(
            "SELECT COUNT(*) FROM episode_queue WHERE status = 'found' AND DATE(updated_at) = ?",
            [today.isoformat()]
        ).fetchone()[0]

        # Get total stats
        total_transcripts = self.cursor.execute(
            "SELECT COUNT(*) FROM content WHERE content_type = 'podcast_transcript'"
        ).fetchone()[0]

        queue_status = self.cursor.execute(
            "SELECT status, COUNT(*) FROM episode_queue GROUP BY status"
        ).fetchall()
        queue_dict = dict(queue_status)

        # Get recent errors
        recent_errors = self.cursor.execute(
            "SELECT COUNT(*) FROM episode_queue WHERE status = 'error' AND updated_at >= ?",
            [(datetime.now() - timedelta(hours=24)).isoformat()]
        ).fetchone()[0]

        return {
            'date': today.strftime('%Y-%m-%d'),
            'today_processed': today_processed,
            'today_found': today_found,
            'total_transcripts': total_transcripts,
            'queue_status': queue_dict,
            'recent_errors': recent_errors,
            'success_rate': (today_found / today_processed * 100) if today_processed > 0 else 0
        }

    def send_email(self, subject, body):
        """Send email notification"""
        if not self.config['enabled']:
            logging.info("Email alerts disabled, skipping send")
            return False

        try:
            msg = MIMEMultipart()
            msg['From'] = self.config['from_email']
            msg['To'] = self.config['to_email']
            msg['Subject'] = subject

            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(self.config['smtp_server'], self.config['smtp_port'])
            server.starttls()
            server.login(self.config['smtp_user'], self.config['smtp_password'])

            text = msg.as_string()
            server.sendmail(self.config['from_email'], self.config['to_email'], text)
            server.quit()

            logging.info(f"Email sent: {subject}")
            return True

        except Exception as e:
            logging.error(f"Failed to send email: {e}")
            return False

    def send_daily_summary(self):
        """Send daily summary email"""
        summary = self.get_daily_summary()

        subject = f"Atlas Daily Summary - {summary['date']}"

        body = f"""
Atlas Daily Report - {summary['date']}

📊 Today's Processing:
  • Episodes processed: {summary['today_processed']}
  • Transcripts found: {summary['today_found']}
  • Success rate: {summary['success_rate']:.1f}%

📈 Overall Status:
  • Total transcripts: {summary['total_transcripts']:,}
  • Queue status: {summary['queue_status']}
  • Recent errors: {summary['recent_errors']}

🔧 System Health:
  • Atlas Manager is running and processing episodes
  • Database optimization completed
  • Auto-restart monitoring active

💡 Next Steps:
  • Continue processing queued episodes
  • Monitor for any error patterns
  • Regular maintenance scheduled

---
Atlas Automated System
"""

        return self.send_email(subject, body)

    def send_error_alert(self, error_message, error_count=1):
        """Send error alert email"""
        subject = f"Atlas Error Alert - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        body = f"""
Atlas Error Alert

⚠️  Error detected: {error_message}
📈 Error count: {error_count}
🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🔧 Immediate Actions:
  • Check logs: tail -f logs/atlas_manager.log
  • Monitor system: ps aux | grep atlas
  • Restart if needed: ./start_monitoring.sh

Please investigate and resolve any issues.
"""

        return self.send_email(subject, body)

    def check_and_alert(self):
        """Check system status and send alerts if needed"""
        summary = self.get_daily_summary()

        # Send daily summary (once per day)
        last_summary_file = 'logs/last_summary.txt'
        send_summary = True

        if os.path.exists(last_summary_file):
            with open(last_summary_file, 'r') as f:
                last_date = f.read().strip()
                if last_date == summary['date']:
                    send_summary = False

        if send_summary:
            self.send_daily_summary()
            with open(last_summary_file, 'w') as f:
                f.write(summary['date'])

        # Check for high error rates
        if summary['recent_errors'] > 10:  # Alert if more than 10 errors in 24h
            self.send_error_alert(f"High error rate detected: {summary['recent_errors']} errors in 24h", summary['recent_errors'])

    def __del__(self):
        """Cleanup database connection"""
        if hasattr(self, 'conn'):
            self.conn.close()

def main():
    """Main function to run email alerts"""
    # Check if Telegram is configured
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    telegram_chat = os.getenv('TELEGRAM_CHAT_ID')

    if telegram_token and telegram_chat:
        print("📱 Using Telegram alerts instead of email")
        # Import and use Telegram alerts
        from telegram_alerts import SimpleTelegramAlerts
        telegram_alerts = SimpleTelegramAlerts()
        telegram_alerts.run_alerts_check()
        return

    # Original email logic
    alerts = EmailAlerts()
    alerts.check_and_alert()
    print("✅ Email alerts check completed")

if __name__ == "__main__":
    main()