#!/usr/bin/env python3
"""
Comprehensive Gmail Newsletter processor for Atlas
Processes full newsletter content, not just URLs
"""

import os
import imaplib
import email
import re
import json
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
from email.header import decode_header
import ssl
from bs4 import BeautifulSoup
import requests
from urllib.parse import urljoin, urlparse
import time

class NewsletterProcessor:
    def __init__(self):
        load_dotenv()

        # Gmail configuration
        self.email_address = os.getenv('GMAIL_EMAIL_ADDRESS')
        self.app_password = os.getenv('GMAIL_APP_PASSWORD')
        self.imap_host = os.getenv('GMAIL_IMAP_HOST', 'imap.gmail.com')
        self.imap_port = int(os.getenv('GMAIL_IMAP_PORT', 993))
        self.label = os.getenv('GMAIL_LABEL', 'Newsletter')

        # Atlas database
        self.db_path = os.getenv('ATLAS_DB_PATH', 'data/atlas.db')

        # Processing settings
        self.max_content_length = 50000  # Max characters per content item
        self.min_content_length = 500    # Minimum content to be worth saving

    def decode_subject(self, subject):
        """Decode email subject"""
        if subject:
            decoded_parts = decode_header(subject)
            subject_str = ""
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    subject_str += part.decode(encoding or 'utf-8', errors='ignore')
                else:
                    subject_str += part
            return subject_str
        return "No Subject"

    def clean_html_content(self, html_content):
        """Extract clean text from HTML content"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Get text
            text = soup.get_text()

            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)

            return text
        except Exception as e:
            print(f"HTML cleaning error: {e}")
            return html_content

    def extract_full_email_content(self, msg):
        """Extract full content from email, preferring text over HTML"""
        content = ""
        content_type = "unknown"

        if msg.is_multipart():
            # Try to get text/plain first
            text_part = None
            html_part = None

            for part in msg.walk():
                if part.get_content_type() == "text/plain" and not text_part:
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            text_part = payload.decode('utf-8', errors='ignore')
                    except (UnicodeDecodeError, LookupError, TypeError) as e:
                        logger.debug(f"Error decoding text/plain part: {e}")
                        continue
                elif part.get_content_type() == "text/html" and not html_part:
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            html_part = payload.decode('utf-8', errors='ignore')
                    except (UnicodeDecodeError, LookupError, TypeError) as e:
                        logger.debug(f"Error decoding text/html part: {e}")
                        continue

            # Use text if available, otherwise clean HTML
            if text_part and len(text_part.strip()) > self.min_content_length:
                content = text_part
                content_type = "text"
            elif html_part:
                content = self.clean_html_content(html_part)
                content_type = "html"
            elif text_part:
                content = text_part
                content_type = "text"
        else:
            # Single part message
            try:
                payload = msg.get_payload(decode=True)
                if payload:
                    content = payload.decode('utf-8', errors='ignore')
                    content_type = msg.get_content_type()
            except (UnicodeDecodeError, LookupError, TypeError) as e:
                logger.debug(f"Error decoding single-part message: {e}")
                content = str(msg.get_payload())
                content_type = "plain"

        # Clean up content
        content = re.sub(r'\s+', ' ', content).strip()

        # Check if content is truncated (contains "click here", "read more", etc.)
        truncation_indicators = [
            r'click here',
            r'read more',
            r'view in browser',
            r'full article',
            r'continue reading',
            r'more\.+$',
            r'\.\.\.$'
        ]

        is_truncated = any(re.search(pattern, content, re.IGNORECASE) for pattern in truncation_indicators)

        # Extract URLs from content for potential full article fetching
        urls = self.extract_urls(content)

        return {
            'content': content,
            'content_type': content_type,
            'is_truncated': is_truncated,
            'urls': urls,
            'length': len(content)
        }

    def extract_urls(self, text):
        """Extract URLs from text"""
        url_pattern = re.compile(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        )
        return list(set(url_pattern.findall(text)))  # Remove duplicates

    def fetch_full_article(self, url, timeout=30):
        """Try to fetch full article content from URL"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()

            # Extract content from article
            soup = BeautifulSoup(response.text, 'html.parser')

            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                element.decompose()

            # Try to find main content
            content_selectors = [
                'article',
                '[role="main"]',
                '.content',
                '.post-content',
                '.entry-content',
                '.article-content',
                'main'
            ]

            content = ""
            for selector in content_selectors:
                elements = soup.select(selector)
                if elements:
                    content = ' '.join([elem.get_text() for elem in elements])
                    break

            # Fallback to body if no specific content found
            if not content or len(content.strip()) < self.min_content_length:
                body = soup.find('body')
                if body:
                    content = body.get_text()

            # Clean content
            content = re.sub(r'\s+', ' ', content).strip()

            if len(content) > self.min_content_length:
                return content[:self.max_content_length]

        except Exception as e:
            print(f"Error fetching article from {url}: {e}")

        return None

    def connect_gmail(self):
        """Connect to Gmail IMAP"""
        try:
            context = ssl.create_default_context()
            mail = imaplib.IMAP4_SSL(self.imap_host, self.imap_port, ssl_context=context)
            mail.login(self.email_address, self.app_password)
            return mail
        except Exception as e:
            print(f"Gmail connection error: {e}")
            return None

    def get_newsletter_emails(self, limit=None):
        """Get newsletter emails from Gmail"""
        mail = self.connect_gmail()
        if not mail:
            return []

        try:
            mail.select('INBOX')

            # Search for emails with Newsletter label
            search_criteria = f'X-GM-LABELS "{self.label}"'
            status, email_ids = mail.search(None, search_criteria)

            if status != 'OK':
                print(f"No emails found with label '{self.label}'")
                return []

            email_ids = email_ids[0].split()
            print(f"Found {len(email_ids)} emails with '{self.label}' label")

            # Limit if specified
            if limit:
                email_ids = email_ids[:limit]
                print(f"Processing first {len(email_ids)} emails")

            emails = []
            for email_id in email_ids:
                status, msg_data = mail.fetch(email_id, '(RFC822)')
                if status == 'OK':
                    emails.append({
                        'message_id': email_id.decode('utf-8'),
                        'raw_email': msg_data[0][1]
                    })

            mail.logout()
            return emails

        except Exception as e:
            logger.error(f"Error fetching emails: {e}")
            try:
                mail.logout()
            except Exception:
                pass  # Ignore logout errors during cleanup
            return []

    def process_email(self, email_data):
        """Process a single email into Atlas content"""
        try:
            # Parse email
            msg = email.message_from_bytes(email_data['raw_email'])

            # Extract email details
            subject = self.decode_subject(msg.get('Subject', 'No Subject'))
            from_addr = msg.get('From', 'No From')
            date = msg.get('Date', 'No Date')

            # Extract content
            content_data = self.extract_full_email_content(msg)

            # Skip if content is too short
            if content_data['length'] < self.min_content_length:
                return {
                    'success': False,
                    'reason': 'Content too short',
                    'length': content_data['length']
                }

            # Create content item
            content_item = {
                'title': subject,
                'content': content_data['content'][:self.max_content_length],
                'content_type': 'newsletter',
                'url': None,  # Newsletters don't have a single URL
                'metadata': {
                    'source': 'gmail',
                    'email_from': from_addr,
                    'email_date': date,
                    'gmail_label': self.label,
                    'message_id': email_data['message_id'],
                    'original_content_type': content_data['content_type'],
                    'is_truncated': content_data['is_truncated'],
                    'processed_at': datetime.now().isoformat(),
                    'urls_found': content_data['urls'][:10]  # Store first 10 URLs
                }
            }

            # If content is truncated, try to fetch full article from first URL
            if content_data['is_truncated'] and content_data['urls']:
                print(f"  Content appears truncated, trying to fetch full article...")
                full_content = self.fetch_full_article(content_data['urls'][0])
                if full_content and len(full_content) > content_data['length']:
                    content_item['content'] = full_content
                    content_item['metadata']['full_article_fetched'] = True
                    content_item['metadata']['full_article_url'] = content_data['urls'][0]
                    print(f"  ✅ Fetched full article ({len(full_content)} chars)")

            return {
                'success': True,
                'content_item': content_item,
                'stats': {
                    'content_length': len(content_item['content']),
                    'urls_found': len(content_data['urls']),
                    'was_truncated': content_data['is_truncated']
                }
            }

        except Exception as e:
            return {
                'success': False,
                'reason': f'Processing error: {e}'
            }

    def save_to_atlas(self, content_item):
        """Save content item to Atlas database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Insert content
            cursor.execute("""
                INSERT INTO content (title, content, content_type, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                content_item['title'],
                content_item['content'],
                content_item['content_type'],
                json.dumps(content_item['metadata']),
                datetime.now(),
                datetime.now()
            ))

            content_id = cursor.lastrowid
            conn.commit()
            conn.close()

            return content_id

        except Exception as e:
            print(f"Database save error: {e}")
            return None

    def process_newsletters(self, limit=None):
        """Process newsletter emails and save to Atlas"""
        print(f"📧 Starting Newsletter Processing")
        print(f"=" * 50)

        # Get emails
        emails = self.get_newsletter_emails(limit=limit)
        if not emails:
            print("No emails to process")
            return

        processed = 0
        successful = 0
        failed = 0

        for i, email_data in enumerate(emails):
            print(f"\n--- Processing Email {i+1}/{len(emails)} ---")

            # Process email
            result = self.process_email(email_data)

            if result['success']:
                # Save to Atlas
                content_id = self.save_to_atlas(result['content_item'])

                if content_id:
                    successful += 1
                    stats = result['stats']
                    print(f"✅ SUCCESS: '{result['content_item']['title'][:50]}...'")
                    print(f"   Content ID: {content_id}")
                    print(f"   Length: {stats['content_length']} chars")
                    print(f"   URLs found: {stats['urls_found']}")
                    if stats['was_truncated']:
                        print(f"   ⚠️  Was truncated, attempted full fetch")
                else:
                    failed += 1
                    print(f"❌ FAILED to save to database")
            else:
                failed += 1
                print(f"❌ FAILED: {result['reason']}")

            processed += 1

            # Small delay to avoid overwhelming Gmail
            time.sleep(0.1)

        print(f"\n" + "=" * 50)
        print(f"🎉 PROCESSING COMPLETE")
        print(f"📊 Summary:")
        print(f"   Total processed: {processed}")
        print(f"   Successful: {successful}")
        print(f"   Failed: {failed}")
        print(f"   Success rate: {(successful/processed*100):.1f}%")

if __name__ == "__main__":
    processor = NewsletterProcessor()

    # Test with a few emails first
    print("🧪 TESTING: Processing 3 newsletter emails")
    processor.process_newsletters(limit=3)

    # Ask user if they want to process all
    response = input("\nProcess all 3,253 newsletter emails? (y/N): ").strip().lower()
    if response == 'y':
        processor.process_newsletters()
    else:
        print("Processing complete. Run again to process more emails.")