#!/usr/bin/env python3
"""
Atlas Unified Processor - ONE Process to Rule Them All
Continuous while loop that handles ALL Atlas inputs:
1. Gmail newsletters (including Atlas-labeled emails)
2. RSS feed URLs
3. Input directory dumps
4. Podcast transcripts (main focus)
ZERO external APIs - pure web scraping only
"""

import os
import json
import sqlite3
import time
import subprocess
import signal
import sys
import requests
from pathlib import Path
from datetime import datetime, timedelta
import logging
import imaplib
import email
import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from email.header import decode_header
import hashlib

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/ubuntu/dev/atlas/atlas_unified.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AtlasUnified:
    """ONE unified processor that handles everything"""

    def __init__(self):
        self.root_dir = Path("/home/ubuntu/dev/atlas")
        self.content_dir = self.root_dir / "content" / "markdown"
        self.content_dir.mkdir(parents=True, exist_ok=True)
        self.input_dir = self.root_dir / "input"

        # Database
        self.db_path = self.root_dir / "podcast_processing.db"

        # Load podcast sources
        with open(self.root_dir / "podcast_transcript_sources.json", "r") as f:
            self.podcast_sources = json.load(f)

        # Configuration
        self.config = {
            'sleep_between_cycles': 30,  # 30 seconds between cycles
            'sleep_between_podcasts': 60,  # 1 minute between podcasts
            'sleep_between_requests': 5,  # 5 seconds between requests
            'batch_size': 10
        }

        # Gmail settings
        load_dotenv()
        self.gmail_address = os.getenv('GMAIL_EMAIL_ADDRESS')
        self.gmail_password = os.getenv('GMAIL_APP_PASSWORD')

        # Runtime state
        self.running = True
        self.start_time = datetime.now()
        self.last_gmail_check = 0
        self.last_input_check = 0
        self.last_podcast_check = 0

        # Set up signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        logger.info("🚀 Atlas Unified Processor initialized")
        self.send_telegram("🟢 <b>Atlas Unified Started</b>\n\nProcessing Gmail, RSS, inputs, and podcasts")

    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"🛑 Received signal {signum}, shutting down gracefully...")
        self.running = False

    def send_telegram(self, message):
        """Send Telegram message"""
        try:
            bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "8208417039:AAFLpW5zfByJEvROgPuirHoH_BGMjmDXwvA")
            chat_id = os.getenv("TELEGRAM_CHAT_ID", "7884781716")

            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }

            requests.post(url, json=payload, timeout=10)
            logger.info("✅ Telegram message sent")
        except Exception as e:
            logger.error(f"❌ Telegram error: {e}")

    def process_gmail_emails(self):
        """Process Gmail newsletters and Atlas-labeled emails"""
        try:
            now = time.time()
            if now - self.last_gmail_check < 300:  # Check every 5 minutes
                return

            self.last_gmail_check = now
            logger.info("📧 Processing Gmail emails...")

            if not self.gmail_address or not self.gmail_password:
                logger.error("❌ Gmail credentials missing")
                return

            mail = imaplib.IMAP4_SSL('imap.gmail.com')
            mail.login(self.gmail_address, self.gmail_password)
            mail.select('INBOX')

            processed_count = 0
            all_email_ids = []

            # First get Atlas emails sent to zoheri+atlas@gmail.com
            try:
                search_criteria = 'TO "zoheri+atlas@gmail.com"'
                status, email_ids = mail.search(None, search_criteria)

                if status == 'OK':
                    email_ids_list = email_ids[0].split()
                    all_email_ids.extend(email_ids_list)
                    logger.info(f"📧 Found {len(email_ids_list)} emails sent to zoheri+atlas@gmail.com")
                else:
                    # Fallback: try label search
                    search_criteria = f'X-GM-LABELS "label:atlas"'
                    status, email_ids = mail.search(None, search_criteria)
                    if status == 'OK':
                        email_ids_list = email_ids[0].split()
                        all_email_ids.extend(email_ids_list)
                        logger.info(f"📧 Found {len(email_ids_list)} emails with 'label:atlas'")
            except Exception as e:
                logger.error(f"⚠️  Error with Atlas email search: {e}")

            # Then get newsletter emails by label
            try:
                search_criteria = f'X-GM-LABELS "newsletter"'
                status, email_ids = mail.search(None, search_criteria)

                if status == 'OK':
                    email_ids_list = email_ids[0].split()
                    all_email_ids.extend(email_ids_list)
                    logger.info(f"📧 Found {len(email_ids_list)} emails with 'newsletter' label")
            except Exception as e:
                logger.error(f"⚠️  Error with newsletter label: {e}")

            # Process all found emails
            for email_id in all_email_ids[-10:]:  # Process last 10 emails
                try:
                    status, msg_data = mail.fetch(email_id, '(RFC822)')
                    if status == 'OK':
                        email_body = msg_data[0][1]
                        email_message = email.message_from_bytes(email_body)

                        # Extract subject and content
                        subject = decode_header(email_message["subject"])[0][0]
                        if isinstance(subject, bytes):
                            subject = subject.decode()

                        # Extract URLs from email body
                        urls = []
                        if email_message.is_multipart():
                            for part in email_message.walk():
                                if part.get_content_type() == "text/plain":
                                    body = part.get_payload(decode=True).decode()
                                    urls.extend(re.findall(r'http[s]?://[^\s<>"{}|\\^`\[\]]+', body))

                        # Process each URL
                        for url in urls:
                            if self.process_url(url, source=f"gmail_{label}"):
                                processed_count += 1
                                time.sleep(2)  # Rate limiting

                except Exception as e:
                    logger.error(f"❌ Error processing email {email_id}: {e}")

                except Exception as e:
                    logger.error(f"❌ Error with label '{label}': {e}")

            mail.logout()
            logger.info(f"✅ Gmail processing complete: {processed_count} URLs processed")

        except Exception as e:
            logger.error(f"❌ Gmail processing error: {e}")

    def process_input_directory(self):
        """Process files in input directory"""
        try:
            now = time.time()
            if now - self.last_input_check < 600:  # Check every 10 minutes
                return

            self.last_input_check = now
            logger.info("📁 Processing input directory...")

            if not self.input_dir.exists():
                return

            processed_files = 0
            for file_path in self.input_dir.iterdir():
                if file_path.is_file() and file_path.suffix in ['.txt', '.csv', '.json', '.md']:
                    try:
                        # Read file and extract URLs
                        content = file_path.read_text()
                        urls = re.findall(r'http[s]?://[^\s<>"{}|\\^`\[\]]+', content)

                        for url in urls:
                            if self.process_url(url, source=f"input_{file_path.name}"):
                                processed_files += 1
                                time.sleep(2)

                        # Move processed file to avoid reprocessing
                        processed_dir = self.input_dir / "processed"
                        processed_dir.mkdir(exist_ok=True)
                        file_path.rename(processed_dir / file_path.name)

                    except Exception as e:
                        logger.error(f"❌ Error processing {file_path}: {e}")

            logger.info(f"✅ Input directory processing complete: {processed_files} files processed")

        except Exception as e:
            logger.error(f"❌ Input directory error: {e}")

    def process_url(self, url, source="unknown"):
        """Process individual URL and save content"""
        try:
            # Check if already processed
            url_hash = hashlib.md5(url.encode()).hexdigest()
            existing_file = self.content_dir / f"content_{url_hash}.md"

            if existing_file.exists():
                return False  # Already processed

            # Fetch content
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                # Parse content
                soup = BeautifulSoup(response.text, 'html.parser')

                # Extract title
                title = soup.find('title')
                title_text = title.get_text() if title else url

                # Extract main content
                content = ""
                for tag in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'article']):
                    content += tag.get_text() + "\n\n"

                # Create markdown file
                markdown_content = f"# {title_text}\n\n"
                markdown_content += f"**Source:** {url}\n"
                markdown_content += f"**Processed:** {datetime.now().isoformat()}\n"
                markdown_content += f"**Source Type:** {source}\n\n"
                markdown_content += f"## Content\n\n{content}"

                existing_file.write_text(markdown_content)
                logger.info(f"✅ Processed URL: {title_text[:50]}...")
                return True

            return False

        except Exception as e:
            logger.error(f"❌ Error processing URL {url}: {e}")
            return False

    def process_podcast_transcripts(self):
        """Process podcast transcripts - MAIN FOCUS"""
        try:
            now = time.time()
            if now - self.last_podcast_check < 1800:  # Check every 30 minutes
                return

            self.last_podcast_check = now
            logger.info("🎙️ Processing podcast transcripts...")

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get all podcasts
            cursor.execute("SELECT id, name FROM podcasts ORDER BY priority ASC")
            podcasts = cursor.fetchall()

            transcripts_found = 0

            for podcast_id, podcast_name in podcasts:
                if not self.running:
                    break

                logger.info(f"🎯 Processing podcast: {podcast_name}")

                # Check if this podcast has a source
                if podcast_name in self.podcast_sources.get("podcast_sources", {}):
                    source_info = self.podcast_sources["podcast_sources"][podcast_name]
                    primary_url = source_info.get("primary", "")

                    if primary_url:
                        found = self.crawl_podcast_transcripts(podcast_id, podcast_name, primary_url)
                        transcripts_found += found

                # Sleep between podcasts
                time.sleep(self.config['sleep_between_podcasts'])

            conn.close()
            logger.info(f"✅ Podcast transcript processing complete: {transcripts_found} found")

        except Exception as e:
            logger.error(f"❌ Podcast processing error: {e}")

    def crawl_podcast_transcripts(self, podcast_id, podcast_name, base_url):
        """Crawl transcripts for a specific podcast"""
        try:
            logger.info(f"🔍 Crawling {podcast_name} at {base_url}")

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.get(base_url, headers=headers, timeout=30)
            if response.status_code != 200:
                logger.error(f"❌ Failed to fetch {base_url}")
                return 0

            soup = BeautifulSoup(response.text, 'html.parser')

            # Find episode links
            episode_links = []
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                if href and ('episode' in href.lower() or '/' in href):
                    full_url = urljoin(base_url, href)
                    if full_url not in episode_links:
                        episode_links.append(full_url)

            logger.info(f"🔗 Found {len(episode_links)} episode links")

            transcripts_found = 0
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            for episode_url in episode_links[:10]:  # Limit to first 10 for testing
                if not self.running:
                    break

                try:
                    # Fetch episode page
                    ep_response = requests.get(episode_url, headers=headers, timeout=30)
                    if ep_response.status_code == 200:
                        ep_soup = BeautifulSoup(ep_response.text, 'html.parser')

                        # Look for transcript content
                        transcript_content = self.extract_transcript_content(ep_soup)

                        if transcript_content:
                            # Try to match to database episode
                            episode_title = ep_soup.find('title')
                            title_text = episode_title.get_text() if episode_title else episode_url

                            # Find matching episode in database
                            cursor.execute("""
                                SELECT id FROM episodes
                                WHERE podcast_id = ? AND (title LIKE ? OR title LIKE ?)
                            """, (podcast_id, f"%{title_text[:30]}%", f"%{title_text[-30:]}%"))

                            matching_episode = cursor.fetchone()

                            if matching_episode:
                                episode_id = matching_episode[0]

                                # Update database with transcript
                                cursor.execute("""
                                    UPDATE episodes
                                    SET transcript_found = 1,
                                        transcript_text = ?,
                                        transcript_source = ?,
                                        processing_status = 'completed'
                                    WHERE id = ?
                                """, (transcript_content, f"web_crawl_{podcast_name}", episode_id))

                                conn.commit()
                                transcripts_found += 1
                                logger.info(f"✅ Found transcript for episode {episode_id}")

                    # Rate limiting
                    time.sleep(self.config['sleep_between_requests'])

                except Exception as e:
                    logger.error(f"❌ Error processing episode {episode_url}: {e}")

            conn.close()
            return transcripts_found

        except Exception as e:
            logger.error(f"❌ Error crawling {podcast_name}: {e}")
            return 0

    def extract_transcript_content(self, soup):
        """Extract transcript content from page"""
        try:
            # Look for common transcript indicators
            transcript_selectors = [
                '[class*="transcript"]',
                '[id*="transcript"]',
                '.transcript-content',
                '.episode-transcript',
                'div:contains("transcript")'
            ]

            for selector in transcript_selectors:
                element = soup.select_one(selector)
                if element:
                    return element.get_text(strip=True)

            # If no explicit transcript, look for large text blocks
            text_blocks = soup.find_all(['p', 'div'])
            for block in text_blocks:
                text = block.get_text(strip=True)
                if len(text) > 1000:  # Assume large text blocks might be transcripts
                    return text

            return None

        except Exception as e:
            logger.error(f"❌ Error extracting transcript: {e}")
            return None

    def get_status(self):
        """Get current status"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM episodes WHERE transcript_found = 1")
            completed = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM episodes")
            total = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM episodes WHERE transcript_found = 0 OR transcript_found IS NULL")
            pending = cursor.fetchone()[0]

            conn.close()

            return {
                'completed': completed,
                'total': total,
                'pending': pending,
                'percentage': (completed / total * 100) if total > 0 else 0
            }

        except Exception as e:
            logger.error(f"❌ Error getting status: {e}")
            return {'completed': 0, 'total': 0, 'pending': 0, 'percentage': 0}

    def run_forever(self):
        """Main infinite while loop - NEVER STOPS"""
        logger.info("🔄 Starting infinite while loop...")

        cycle_count = 0

        while self.running:
            try:
                cycle_count += 1
                logger.info(f"🔄 Cycle {cycle_count} - {datetime.now()}")

                # 1. Process Gmail emails
                self.process_gmail_emails()

                # 2. Process input directory
                self.process_input_directory()

                # 3. Process podcast transcripts (main focus)
                self.process_podcast_transcripts()

                # 4. Status check every 10 cycles
                if cycle_count % 10 == 0:
                    status = self.get_status()
                    uptime = datetime.now() - self.start_time
                    logger.info(f"📊 Status: {status['percentage']:.1f}% complete | Uptime: {uptime}")

                    # Send progress report every hour
                    if cycle_count % 120 == 0:  # Every ~2 hours
                        self.send_telegram(f"📊 <b>Atlas Status</b>\n\nProgress: {status['percentage']:.1f}%\nCompleted: {status['completed']:,}\nRemaining: {status['pending']:,}\nUptime: {uptime}")

                # Sleep between cycles
                time.sleep(self.config['sleep_between_cycles'])

            except KeyboardInterrupt:
                logger.info("🛑 Keyboard interrupt")
                break
            except Exception as e:
                logger.error(f"❌ Error in main loop: {e}")
                self.send_telegram(f"🚨 <b>Atlas Error</b>\n\n{str(e)}")
                time.sleep(30)  # Wait before retrying

        logger.info("🏁 Atlas unified processor stopped")

def main():
    """Main entry point"""
    processor = AtlasUnified()
    processor.run_forever()

if __name__ == "__main__":
    main()