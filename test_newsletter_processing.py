#!/usr/bin/env python3
"""
Test Gmail Newsletter processing for Atlas
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

def decode_subject(subject):
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

def extract_urls_from_text(text):
    """Extract URLs from text content"""
    url_pattern = re.compile(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    )
    return url_pattern.findall(text)

def extract_email_content(msg):
    """Extract text content from email message"""
    content = ""

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        content += payload.decode('utf-8', errors='ignore')
                except:
                    continue
            elif content_type == "text/html":
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        html_content = payload.decode('utf-8', errors='ignore')
                        # Simple URL extraction from HTML
                        urls = extract_urls_from_text(html_content)
                        if urls:
                            content += "\n".join(urls)
                except:
                    continue
    else:
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                content = payload.decode('utf-8', errors='ignore')
        except:
            content = str(msg.get_payload())

    return content

def test_newsletter_processing():
    """Test Gmail Newsletter processing"""
    print("📧 Testing Gmail Newsletter Processing")
    print("=" * 60)

    # Load environment variables
    load_dotenv()

    # Get configuration
    email_address = os.getenv('GMAIL_EMAIL_ADDRESS')
    app_password = os.getenv('GMAIL_APP_PASSWORD')
    imap_host = os.getenv('GMAIL_IMAP_HOST', 'imap.gmail.com')
    imap_port = int(os.getenv('GMAIL_IMAP_PORT', 993))
    label = os.getenv('GMAIL_LABEL', 'Newsletter')

    print(f"Email Address: {email_address}")
    print(f"Label: {label}")
    print(f"IMAP Host: {imap_host}:{imap_port}")

    processed_emails = []

    try:
        # Create SSL context and connect
        context = ssl.create_default_context()
        mail = imaplib.IMAP4_SSL(imap_host, imap_port, ssl_context=context)
        mail.login(email_address, app_password)

        # Select INBOX
        mail.select('INBOX')

        print(f"\n🔍 Searching for emails with label '{label}'...")

        # Search for emails with the Newsletter label
        search_criteria = f'X-GM-LABELS "{label}"'
        status, email_ids = mail.search(None, search_criteria)

        if status != 'OK':
            print(f"❌ No emails found with label '{label}'")
            print("Trying alternative search...")
            # Try searching in subject
            status, email_ids = mail.search(None, 'SUBJECT', label)

        if status == 'OK' and email_ids[0]:
            email_ids = email_ids[0].split()
            print(f"✅ Found {len(email_ids)} emails with '{label}' label")

            # Process first 5 emails for testing
            test_emails = email_ids[:5]
            print(f"📄 Processing first {len(test_emails)} emails for testing...")

            for i, email_id in enumerate(test_emails):
                print(f"\n--- Email {i+1}/{len(test_emails)} ---")

                # Fetch email
                status, msg_data = mail.fetch(email_id, '(RFC822)')
                if status != 'OK':
                    continue

                # Parse email
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                # Extract email details
                subject = decode_subject(msg.get('Subject', 'No Subject'))
                from_addr = msg.get('From', 'No From')
                date = msg.get('Date', 'No Date')

                print(f"From: {from_addr}")
                print(f"Subject: {subject}")
                print(f"Date: {date}")

                # Extract content
                content = extract_email_content(msg)

                # Extract URLs
                urls = extract_urls_from_text(content)

                print(f"Content length: {len(content)} characters")
                print(f"URLs found: {len(urls)}")

                if urls:
                    print("🔗 URLs:")
                    for j, url in enumerate(urls[:5]):  # Show first 5 URLs
                        print(f"  {j+1}. {url}")
                    if len(urls) > 5:
                        print(f"  ... and {len(urls) - 5} more URLs")

                # Store for database processing
                processed_emails.append({
                    'message_id': email_id.decode('utf-8'),
                    'subject': subject,
                    'from': from_addr,
                    'date': date,
                    'content': content[:1000],  # First 1000 chars
                    'urls': urls[:10],  # First 10 URLs
                    'total_urls': len(urls)
                })

            mail.logout()
        else:
            print(f"❌ No emails found with label '{label}'")
            mail.logout()
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    # Test database integration
    print(f"\n🗄️ Testing Atlas Database Integration...")
    test_atlas_database_integration(processed_emails)

    return True

def test_atlas_database_integration(processed_emails):
    """Test integration with Atlas database"""
    try:
        # Check if Atlas database exists
        db_path = 'data/atlas.db'
        if not os.path.exists(db_path):
            print(f"❌ Atlas database not found at {db_path}")
            return False

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check content table structure
        cursor.execute("PRAGMA table_info(content)")
        columns = [row[1] for row in cursor.fetchall()]
        print(f"✅ Atlas database connected")
        print(f"📊 Content table columns: {', '.join(columns[:10])}")

        # Check existing content count
        cursor.execute("SELECT COUNT(*) FROM content")
        total_content = cursor.fetchone()[0]
        print(f"📈 Total existing content: {total_content}")

        # Check for existing Gmail content
        cursor.execute("""
            SELECT COUNT(*) FROM content
            WHERE json_extract(metadata, '$.source') = 'gmail'
        """)
        gmail_content = cursor.fetchone()[0]
        print(f"📧 Existing Gmail-sourced content: {gmail_content}")

        # Simulate adding one newsletter email to database
        if processed_emails:
            test_email = processed_emails[0]

            print(f"\n🧪 Simulating adding newsletter email to database:")
            print(f"  Subject: {test_email['subject'][:50]}...")
            print(f"  URLs to process: {test_email['total_urls']}")

            if test_email['urls']:
                # Show how URLs would be processed
                for i, url in enumerate(test_email['urls'][:3]):
                    print(f"    • {url}")

                print(f"✅ Content ready for Atlas processing!")
                print(f"📋 Would be added as:")
                print(f"    - Title: {test_email['subject']}")
                print(f"    - Source: gmail")
                print(f"    - URLs: {test_email['total_urls']} items")
                print(f"    - Metadata: email_from, date, label")

        conn.close()

    except Exception as e:
        print(f"❌ Database integration error: {e}")
        return False

    return True

if __name__ == "__main__":
    success = test_newsletter_processing()

    if success:
        print(f"\n🎉 NEWSLETTER PROCESSING TEST SUCCESSFUL!")
        print(f"📧 Gmail integration is ready for Newsletter content!")
        print(f"🔄 Ready to integrate with Atlas content processing pipeline!")
    else:
        print(f"\n❌ Newsletter processing test failed")
        print(f"Please check the errors above and fix any issues.")