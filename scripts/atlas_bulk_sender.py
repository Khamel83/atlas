#!/usr/bin/env python3
"""
Atlas Bulk URL Sender
Sends batches of URLs to Gmail for Atlas ingestion

Usage:
    python atlas_bulk_sender.py backlog.txt
    python atlas_bulk_sender.py backlog.txt --batch-size 250 --daily-limit 2000
    python atlas_bulk_sender.py backlog.txt --dry-run  # Test without sending
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import base64
from email.mime.text import MIMEText

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print("ERROR: Required packages not installed!")
    print("Install with: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
    sys.exit(1)

# Gmail API scopes - need send permission
SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly'
]

class BulkSender:
    def __init__(self, credentials_path: str, token_path: str, email_address: str):
        """Initialize the bulk sender with Gmail API credentials."""
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.email_address = email_address
        self.service = None
        self.progress_file = Path('bulk_sender_progress.json')
        self.progress = self.load_progress()

    def load_progress(self) -> Dict:
        """Load progress from file to enable resume."""
        if self.progress_file.exists():
            with open(self.progress_file, 'r') as f:
                return json.load(f)
        return {
            'total_urls': 0,
            'urls_sent': 0,
            'batches_sent': 0,
            'last_sent_date': None,
            'emails_sent_today': 0,
            'failed_batches': [],
            'completed': False
        }

    def save_progress(self):
        """Save progress to file."""
        with open(self.progress_file, 'w') as f:
            json.dump(self.progress, f, indent=2)

    def authenticate(self):
        """Authenticate with Gmail API."""
        creds = None

        # Load existing token
        if Path(self.token_path).exists():
            creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)

        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("🔄 Refreshing expired credentials...")
                creds.refresh(Request())
            else:
                print("🔐 No valid credentials found. Starting authentication flow...")
                print(f"📁 Looking for credentials at: {self.credentials_path}")

                if not Path(self.credentials_path).exists():
                    print(f"❌ ERROR: Credentials file not found at {self.credentials_path}")
                    print("\nTo fix this:")
                    print("1. Go to Google Cloud Console")
                    print("2. Create OAuth 2.0 credentials")
                    print("3. Download as gmail_credentials.json")
                    print("4. Place in ~/dev/atlas/config/")
                    sys.exit(1)

                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)

            # Save credentials for next time
            print(f"💾 Saving credentials to: {self.token_path}")
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())

        self.service = build('gmail', 'v1', credentials=creds)
        print("✅ Gmail API authenticated successfully")
        return True

    def read_urls(self, file_path: str) -> List[str]:
        """Read URLs from file, one per line."""
        print(f"📖 Reading URLs from: {file_path}")

        if not Path(file_path).exists():
            print(f"❌ ERROR: File not found: {file_path}")
            sys.exit(1)

        with open(file_path, 'r') as f:
            urls = [line.strip() for line in f if line.strip() and line.strip().startswith('http')]

        print(f"✅ Read {len(urls)} URLs from file")
        return urls

    def chunk_urls(self, urls: List[str], batch_size: int) -> List[List[str]]:
        """Split URLs into batches."""
        batches = [urls[i:i + batch_size] for i in range(0, len(urls), batch_size)]
        print(f"📦 Split into {len(batches)} batches of {batch_size} URLs each")
        return batches

    def create_email_message(self, urls: List[str], batch_num: int, total_batches: int) -> MIMEText:
        """Create email message with URLs."""
        subject = f"Atlas Bulk Import - Batch {batch_num} of {total_batches}"

        body = f"""Atlas Bulk Import - Batch {batch_num} of {total_batches}

The following URLs are queued for processing:

{chr(10).join(urls)}

---
Total URLs in this batch: {len(urls)}
Auto-generated by atlas_bulk_sender.py
Sent: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        message = MIMEText(body)
        message['to'] = self.email_address
        message['subject'] = subject

        return message

    def send_email(self, message: MIMEText) -> bool:
        """Send email via Gmail API."""
        try:
            # Create message for Gmail API
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            send_message = {'raw': raw_message}

            # Send the message
            result = self.service.users().messages().send(
                userId='me',
                body=send_message
            ).execute()

            # Apply "Atlas" label to the sent message
            message_id = result.get('id')
            self.apply_atlas_label(message_id)

            return True

        except HttpError as error:
            print(f"❌ Error sending email: {error}")
            return False

    def apply_atlas_label(self, message_id: str):
        """Apply 'Atlas' label to message for automatic processing."""
        try:
            # Get or create Atlas label
            labels = self.service.users().labels().list(userId='me').execute()
            atlas_label_id = None

            for label in labels.get('labels', []):
                if label['name'] == 'Atlas':
                    atlas_label_id = label['id']
                    break

            # Create label if it doesn't exist
            if not atlas_label_id:
                label_object = {
                    'name': 'Atlas',
                    'labelListVisibility': 'labelShow',
                    'messageListVisibility': 'show'
                }
                created_label = self.service.users().labels().create(
                    userId='me',
                    body=label_object
                ).execute()
                atlas_label_id = created_label['id']

            # Apply label to message
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'addLabelIds': [atlas_label_id]}
            ).execute()

        except HttpError as error:
            print(f"⚠️  Could not apply Atlas label: {error}")

    def check_daily_limit(self, daily_limit: int) -> bool:
        """Check if we've hit the daily sending limit."""
        today = datetime.now().strftime('%Y-%m-%d')

        # Reset counter if it's a new day
        if self.progress['last_sent_date'] != today:
            self.progress['last_sent_date'] = today
            self.progress['emails_sent_today'] = 0
            self.save_progress()

        # Check if we've hit the limit
        if self.progress['emails_sent_today'] >= daily_limit:
            return False

        return True

    def wait_until_tomorrow(self):
        """Wait until midnight to continue sending."""
        now = datetime.now()
        tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        wait_seconds = (tomorrow - now).total_seconds()

        print(f"\n⏰ Daily limit reached. Waiting until {tomorrow.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   (Sleeping for {wait_seconds/3600:.1f} hours)")

        time.sleep(wait_seconds)

    def send_batches(self, batches: List[List[str]], daily_limit: int = 2000, delay: float = 0.5, dry_run: bool = False):
        """Send all batches with rate limiting."""
        total_batches = len(batches)
        start_batch = self.progress['batches_sent']

        print(f"\n🚀 Starting bulk send:")
        print(f"   Total batches: {total_batches}")
        print(f"   Already sent: {start_batch}")
        print(f"   Remaining: {total_batches - start_batch}")
        print(f"   Daily limit: {daily_limit} emails")
        print(f"   Delay between emails: {delay}s")

        if dry_run:
            print("\n⚠️  DRY RUN MODE - No emails will be sent")

        for i in range(start_batch, total_batches):
            batch_num = i + 1
            urls = batches[i]

            # Check daily limit
            if not self.check_daily_limit(daily_limit):
                self.save_progress()
                self.wait_until_tomorrow()

            # Create and send email
            print(f"\n📧 Batch {batch_num}/{total_batches} ({len(urls)} URLs)")

            if dry_run:
                print(f"   [DRY RUN] Would send email with {len(urls)} URLs")
            else:
                message = self.create_email_message(urls, batch_num, total_batches)

                if self.send_email(message):
                    print(f"   ✅ Sent successfully")
                    self.progress['batches_sent'] += 1
                    self.progress['urls_sent'] += len(urls)
                    self.progress['emails_sent_today'] += 1
                    self.save_progress()
                else:
                    print(f"   ❌ Failed to send")
                    self.progress['failed_batches'].append(batch_num)
                    self.save_progress()

                # Rate limiting delay
                if i < total_batches - 1:
                    time.sleep(delay)

        self.progress['completed'] = True
        self.save_progress()

        print(f"\n✅ Bulk send complete!")
        print(f"   Total URLs sent: {self.progress['urls_sent']}")
        print(f"   Total emails sent: {self.progress['batches_sent']}")
        print(f"   Failed batches: {len(self.progress['failed_batches'])}")


def main():
    parser = argparse.ArgumentParser(
        description='Send bulk URLs to Gmail for Atlas ingestion',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python atlas_bulk_sender.py backlog.txt
  python atlas_bulk_sender.py backlog.txt --batch-size 250
  python atlas_bulk_sender.py backlog.txt --daily-limit 2000
  python atlas_bulk_sender.py backlog.txt --dry-run
  python atlas_bulk_sender.py backlog.txt --reset-progress
        """
    )

    parser.add_argument('input_file', help='File containing URLs (one per line)')
    parser.add_argument('--batch-size', type=int, default=250,
                       help='Number of URLs per email (default: 250)')
    parser.add_argument('--daily-limit', type=int, default=2000,
                       help='Daily email sending limit (default: 2000 for free Gmail)')
    parser.add_argument('--delay', type=float, default=0.5,
                       help='Delay between emails in seconds (default: 0.5)')
    parser.add_argument('--email', type=str, default=None,
                       help='Your Gmail address (default: auto-detect from credentials)')
    parser.add_argument('--credentials', type=str,
                       default='config/gmail_credentials.json',
                       help='Path to Gmail credentials file')
    parser.add_argument('--token', type=str,
                       default='data/gmail_token.json',
                       help='Path to Gmail token file')
    parser.add_argument('--dry-run', action='store_true',
                       help='Test mode - don\'t actually send emails')
    parser.add_argument('--reset-progress', action='store_true',
                       help='Reset progress and start from beginning')

    args = parser.parse_args()

    # Expand paths
    credentials_path = os.path.expanduser(args.credentials)
    token_path = os.path.expanduser(args.token)
    input_file = os.path.expanduser(args.input_file)

    # Auto-detect email if not provided
    email_address = args.email
    if not email_address:
        # Try to get from credentials
        if Path(credentials_path).exists():
            import json
            with open(credentials_path, 'r') as f:
                creds = json.load(f)
                # Try to extract email from credentials
                # For installed app, email might not be in credentials
                # We'll prompt user if needed
                pass

        if not email_address:
            email_address = input("Enter your Gmail address: ").strip()

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║             Atlas Bulk URL Sender                            ║
╚══════════════════════════════════════════════════════════════╝

Configuration:
  Input file:     {input_file}
  Batch size:     {args.batch_size} URLs per email
  Daily limit:    {args.daily_limit} emails/day
  Email address:  {email_address}
  Credentials:    {credentials_path}
  Token:          {token_path}
  Dry run:        {args.dry_run}
""")

    # Initialize sender
    sender = BulkSender(credentials_path, token_path, email_address)

    # Reset progress if requested
    if args.reset_progress:
        print("🔄 Resetting progress...")
        sender.progress_file.unlink(missing_ok=True)
        sender.progress = sender.load_progress()

    # Authenticate with Gmail
    if not sender.authenticate():
        print("❌ Authentication failed")
        sys.exit(1)

    # Read URLs
    urls = sender.read_urls(input_file)

    if not urls:
        print("❌ No URLs found in file")
        sys.exit(1)

    # Update total URLs in progress
    sender.progress['total_urls'] = len(urls)
    sender.save_progress()

    # Chunk URLs into batches
    batches = sender.chunk_urls(urls, args.batch_size)

    # Send batches
    sender.send_batches(batches, args.daily_limit, args.delay, args.dry_run)

    print("\n" + "="*60)
    print("DONE! Your backlog has been sent to Gmail for Atlas processing.")
    print("="*60)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user. Progress has been saved.")
        print("Run the script again to resume from where you left off.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
