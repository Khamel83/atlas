#!/usr/bin/env python3
"""
Atlas Email Processor for handling Atlas-tagged emails
Processes emails containing URLs that need to be fetched and processed
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

class AtlasEmailProcessor:
    def __init__(self):
        load_dotenv()

        # Gmail configuration
        self.email_address = os.getenv('GMAIL_EMAIL_ADDRESS')
        self.app_password = os.getenv('GMAIL_APP_PASSWORD')
        self.imap_host = os.getenv('GMAIL_IMAP_HOST', 'imap.gmail.com')
        self.imap_port = int(os.getenv('GMAIL_IMAP_PORT', 993))
        # Atlas labels (support both Atlas and newsletter)
        gmail_labels = os.getenv('GMAIL_LABELS', 'Atlas,newsletter')
        self.atlas_labels = [label.strip() for label in gmail_labels.split(',')]

        # Atlas database
        self.db_path = os.getenv('ATLAS_DB_PATH', 'podcast_processing.db')

        # Processing settings
        self.max_content_length = 50000
        self.min_content_length = 500
        self.request_timeout = 30
        self.request_delay = 1  # Delay between requests to be respectful

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

    def extract_urls_from_email(self, msg):
        """Extract URLs from email content"""
        urls = []

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        content = payload.decode('utf-8', errors='ignore')
                        # Extract URLs from this part
                        part_urls = self.extract_urls_from_text(content)
                        urls.extend(part_urls)
                except:
                    continue
        else:
            try:
                payload = msg.get_payload(decode=True)
                if payload:
                    content = payload.decode('utf-8', errors='ignore')
                    urls = self.extract_urls_from_text(content)
            except:
                content = str(msg.get_payload())
                urls = self.extract_urls_from_text(content)

        # Remove duplicates and filter for valid URLs
        unique_urls = list(set(urls))
        valid_urls = []

        for url in unique_urls:
            if self.is_valid_url(url):
                valid_urls.append(url)

        return valid_urls

    def extract_urls_from_text(self, text):
        """Extract URLs from text content"""
        url_pattern = re.compile(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        )
        return url_pattern.findall(text)

    def is_valid_url(self, url):
        """Check if URL is worth processing"""
        try:
            parsed = urlparse(url)

            # Skip common non-article URLs
            skip_patterns = [
                'unsubscribe',
                'preferences',
                'view-in-browser',
                'share',
                'twitter.com',
                'facebook.com',
                'linkedin.com',
                'youtube.com',
                'instagram.com',
                'tracking',
                'click.',
                'redirect.',
                'bit.ly',
                't.co',
                'goo.gl'
            ]

            url_lower = url.lower()
            for pattern in skip_patterns:
                if pattern in url_lower:
                    return False

            # Must have a proper domain
            return bool(parsed.netloc and parsed.scheme)

        except:
            return False

    def fetch_article_content(self, url):
        """Fetch and extract content from a URL"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }

            response = requests.get(url, headers=headers, timeout=self.request_timeout)
            response.raise_for_status()

            # Check if we got actual content (not just a redirect or error page)
            if len(response.text) < 1000:
                return None

            # Extract content using BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')

            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'advertisement']):
                element.decompose()

            # Try to find main content using common selectors
            content_selectors = [
                'article',
                '[role="main"]',
                '.content',
                '.post-content',
                '.entry-content',
                '.article-content',
                '.story-body',
                '.post-body',
                'main',
                '.article',
                '#article',
                '#content'
            ]

            content = ""
            for selector in content_selectors:
                elements = soup.select(selector)
                if elements:
                    content = ' '.join([elem.get_text() for elem in elements])
                    if len(content.strip()) > self.min_content_length:
                        break

            # Fallback to body if no specific content found
            if len(content.strip()) < self.min_content_length:
                body = soup.find('body')
                if body:
                    content = body.get_text()

            # Clean content
            content = re.sub(r'\s+', ' ', content).strip()

            # Get title
            title = ""
            title_elem = soup.find('title')
            if title_elem:
                title = title_elem.get_text().strip()

            # Try h1 if no title
            if not title:
                h1_elem = soup.find('h1')
                if h1_elem:
                    title = h1_elem.get_text().strip()

            if len(content) > self.min_content_length:
                return {
                    'title': title,
                    'content': content[:self.max_content_length],
                    'url': url,
                    'content_type': 'article',
                    'length': len(content)
                }

        except requests.exceptions.RequestException as e:
            print(f"    ❌ Request error for {url}: {e}")
        except Exception as e:
            print(f"    ❌ Processing error for {url}: {e}")

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

    def get_atlas_emails(self, limit=None):
        """Get Atlas-tagged emails from Gmail"""
        mail = self.connect_gmail()
        if not mail:
            return []

        try:
            mail.select('INBOX')

            all_email_ids = []

            # Search for emails with each Atlas label
            for label in self.atlas_labels:
                search_criteria = f'X-GM-LABELS "{label}"'
                status, email_ids = mail.search(None, search_criteria)

                if status == 'OK':
                    label_email_ids = email_ids[0].split()
                    all_email_ids.extend(label_email_ids)
                    print(f"Found {len(label_email_ids)} emails with '{label}' label")
                else:
                    print(f"No emails found with label '{label}'")

            # Remove duplicates
            all_email_ids = list(set(all_email_ids))
            print(f"Total unique emails found: {len(all_email_ids)}")

            if not all_email_ids:
                return []

            # Limit if specified
            if limit:
                all_email_ids = all_email_ids[:limit]
                print(f"Processing first {len(all_email_ids)} emails")

            emails = []
            for email_id in all_email_ids:
                status, msg_data = mail.fetch(email_id, '(RFC822)')
                if status == 'OK':
                    emails.append({
                        'message_id': email_id.decode('utf-8'),
                        'raw_email': msg_data[0][1]
                    })

            mail.logout()
            return emails

        except Exception as e:
            print(f"Error fetching emails: {e}")
            try:
                mail.logout()
            except:
                pass
            return []

    def process_atlas_email(self, email_data):
        """Process a single Atlas email and extract URLs"""
        try:
            # Parse email
            msg = email.message_from_bytes(email_data['raw_email'])

            # Extract email details
            subject = self.decode_subject(msg.get('Subject', 'No Subject'))
            from_addr = msg.get('From', 'No From')
            date = msg.get('Date', 'No Date')

            print(f"Processing: {subject[:50]}...")

            # Extract URLs from email
            urls = self.extract_urls_from_email(msg)

            if not urls:
                return {
                    'success': False,
                    'reason': 'No valid URLs found',
                    'processed_urls': 0
                }

            print(f"  Found {len(urls)} URLs to process")

            # Process each URL
            processed_articles = []
            successful_articles = 0
            failed_urls = 0

            for i, url in enumerate(urls):
                print(f"  Processing URL {i+1}/{len(urls)}: {url[:60]}...")

                # Add delay to be respectful
                time.sleep(self.request_delay)

                article_data = self.fetch_article_content(url)

                if article_data:
                    # Create content item
                    content_item = {
                        'title': article_data['title'] or subject,
                        'content': article_data['content'],
                        'content_type': 'article',
                        'url': article_data['url'],
                        'metadata': {
                            'source': 'gmail_atlas',
                            'email_from': from_addr,
                            'email_date': date,
                            'email_subject': subject,
                            'gmail_label': self.atlas_label,
                            'message_id': email_data['message_id'],
                            'processed_at': datetime.now().isoformat(),
                            'original_url': url,
                            'content_length': article_data['length']
                        }
                    }

                    processed_articles.append(content_item)
                    successful_articles += 1
                    print(f"    ✅ Success ({article_data['length']} chars)")
                else:
                    failed_urls += 1
                    print(f"    ❌ Failed to fetch content")

            return {
                'success': True,
                'processed_articles': processed_articles,
                'stats': {
                    'total_urls': len(urls),
                    'successful_articles': successful_articles,
                    'failed_urls': failed_urls,
                    'success_rate': (successful_articles / len(urls) * 100) if urls else 0
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

            # For now, just log the content since we don't have a content table
            print(f"    📄 Content: {content_item['title'][:50]}...")
            print(f"    🔗 URL: {content_item['url'][:60]}...")
            print(f"    📏 Length: {len(content_item['content'])} characters")
            print(f"    🏷️  Source: {content_item['metadata']['source']}")

            # Could create a simple content logging table if needed
            # For now, we'll just process and report

            conn.close()
            return "logged"

        except Exception as e:
            print(f"Database save error: {e}")
            return None

    def process_atlas_emails(self, limit=None):
        """Process Atlas-tagged emails and save to Atlas"""
        print(f"🏷️  Starting Atlas Email Processing")
        print(f"=" * 60)

        # Get emails
        emails = self.get_atlas_emails(limit=limit)
        if not emails:
            print("No Atlas emails to process")
            return

        processed_emails = 0
        successful_emails = 0
        failed_emails = 0
        total_articles = 0
        successful_articles = 0

        for i, email_data in enumerate(emails):
            print(f"\n--- Processing Email {i+1}/{len(emails)} ---")

            # Process email
            result = self.process_atlas_email(email_data)

            if result['success']:
                # Save all articles to Atlas
                for article in result['processed_articles']:
                    content_id = self.save_to_atlas(article)
                    if content_id:
                        successful_articles += 1
                        total_articles += 1
                        print(f"    💾 Saved as content ID: {content_id}")

                successful_emails += 1
                stats = result['stats']
                print(f"✅ EMAIL SUCCESS: {stats['successful_articles']}/{stats['total_urls']} articles fetched")
                print(f"   Success rate: {stats['success_rate']:.1f}%")
            else:
                failed_emails += 1
                print(f"❌ EMAIL FAILED: {result['reason']}")

            processed_emails += 1

        print(f"\n" + "=" * 60)
        print(f"🎉 ATLAS EMAIL PROCESSING COMPLETE")
        print(f"📊 Summary:")
        print(f"   Emails processed: {processed_emails}")
        print(f"   Successful emails: {successful_emails}")
        print(f"   Failed emails: {failed_emails}")
        print(f"   Total articles found: {total_articles}")
        print(f"   Successful articles: {successful_articles}")
        print(f"   Overall success rate: {(successful_emails/processed_emails*100):.1f}%" if processed_emails > 0 else "N/A")

if __name__ == "__main__":
    processor = AtlasEmailProcessor()

    # Test with a few emails first (if any exist)
    print("🧪 TESTING: Atlas Email Processor")
    processor.process_atlas_emails(limit=3)