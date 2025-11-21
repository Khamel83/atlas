#!/usr/bin/env python3
"""
Simple Email Ingestester - Just gets emails into Atlas
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
import requests
from bs4 import BeautifulSoup
import time

def ingest_emails():
    """Just ingest emails into Atlas immediately"""
    print("📧 EMAIL INGESTION START")

    load_dotenv()

    email_address = os.getenv('GMAIL_EMAIL_ADDRESS')
    app_password = os.getenv('GMAIL_APP_PASSWORD')

    if not email_address or not app_password:
        print("❌ Missing Gmail credentials")
        return

    try:
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        mail.login(email_address, app_password)
        mail.select('INBOX')

        # Get emails from Atlas and newsletter labels
        all_email_ids = []

        # ALL Newsletter emails - get thousands, not just recent ones
        try:
            search_criteria = f'X-GM-LABELS "newsletter"'
            status, email_ids = mail.search(None, search_criteria)
            if status == 'OK':
                email_ids_list = email_ids[0].split()
                all_email_ids.extend(email_ids_list)
                print(f"📧 Found {len(email_ids_list)} TOTAL newsletter emails (processing all)")
        except Exception as e:
            print(f"⚠️  Error with newsletter label search: {e}")

        # Also get ALL emails from last 2 years to catch any missed newsletters
        try:
            search_criteria = 'SINCE "1-Jan-2023"'
            status, email_ids = mail.search(None, search_criteria)
            if status == 'OK':
                email_ids_list = email_ids[0].split()
                print(f"📧 Found {len(email_ids_list)} total emails since 2023")
                # Add any that aren't already in the list
                existing_ids = set(all_email_ids)
                new_ids = [eid for eid in email_ids_list if eid not in existing_ids]
                all_email_ids.extend(new_ids)
                print(f"📧 Added {len(new_ids)} additional emails to process")
        except Exception as e:
            print(f"⚠️  Error with broad email search: {e}")

        # Atlas emails by label
        try:
            search_criteria = f'X-GM-LABELS "atlas"'
            status, email_ids = mail.search(None, search_criteria)
            if status == 'OK':
                email_ids_list = email_ids[0].split()
                all_email_ids.extend(email_ids_list)
                print(f"📧 Found {len(email_ids_list)} emails with 'atlas' label")
        except Exception as e:
            print(f"⚠️  Error with atlas label search: {e}")

        # Also check zoheri+atlas@gmail.com emails
        try:
            search_criteria = 'FROM "zoheri+atlas@gmail.com"'
            status, email_ids = mail.search(None, search_criteria)
            if status == 'OK':
                email_ids_list = email_ids[0].split()
                all_email_ids.extend(email_ids_list)
                print(f"📧 Found {len(email_ids_list)} emails from zoheri+atlas@gmail.com")
        except Exception as e:
            print(f"⚠️  Error with zoheri+atlas search: {e}")

        # Remove duplicates
        all_email_ids = list(set(all_email_ids))
        print(f"📧 Total unique emails: {len(all_email_ids)}")

        ingested = 0

        # Process ALL emails - no limits, get everything
        for i, email_id in enumerate(all_email_ids):  # Process ALL found emails
            try:
                status, msg_data = mail.fetch(email_id, '(RFC822)')
                if status == 'OK':
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)

                    # Get basic info
                    subject = decode_header(msg.get('Subject', ''))[0][0]
                    if isinstance(subject, bytes):
                        subject = subject.decode('utf-8', errors='ignore')

                    from_addr = msg.get('From', '')
                    date = msg.get('Date', '')
                    labels = msg.get('X-Gmail-Labels', '')

                    # Debug: Show labels for first few emails
                    if ingested < 3:
                        print(f"📧 Email {ingested + 1} labels: {labels}")

                    # Check if email is from 13 days ago (Nov 5, 2025)
                    from datetime import datetime, timedelta
                    email_date = email.utils.parsedate_to_datetime(date) if date else None
                    target_date = datetime(2025, 11, 5)  # 13 days ago from today (Nov 18)
                    is_target_date = email_date and email_date.date() == target_date.date()

                    if is_target_date:
                        print(f"🗓️ Found email from Nov 5: {subject[:50]}...")

                    # Extract URLs
                    urls = []
                    if msg.is_multipart():
                        for part in msg.walk():
                            try:
                                payload = part.get_payload(decode=True)
                                if payload:
                                    content = payload.decode('utf-8', errors='ignore')
                                    # Find URLs
                                    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
                                    urls.extend(re.findall(url_pattern, content))
                            except:
                                continue
                    else:
                        try:
                            payload = msg.get_payload(decode=True)
                            if payload:
                                content = payload.decode('utf-8', errors='ignore')
                                url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
                                urls.extend(re.findall(url_pattern, content))
                        except:
                            pass

                    # Add email content to Atlas
                    conn = sqlite3.connect('podcast_processing.db')

                    # Add basic email record
                    conn.execute("""
                        INSERT OR IGNORE INTO atlas_queue
                        (source_url, title, content, source_type)
                        VALUES (?, ?, ?, ?)
                    """, (
                        f'email://{email_id.decode("utf-8")}',
                        subject[:100],
                        f"Email from {from_addr}\nSubject: {subject}\nDate: {date}\nURLs found: {len(urls)}",
                        'email'
                    ))

                    # Add each URL as separate item
                    for url in urls:  # NO LIMIT - extract ALL URLs
                        # Skip obvious non-content URLs
                        skip_words = ['unsubscribe', 'preferences', 'twitter.com', 'facebook.com', 'linkedin.com']
                        if not any(skip in url.lower() for skip in skip_words):
                            # Check for New Yorker URLs from 13 days ago
                            if 'newyorker.com' in url and is_target_date:
                                print(f"🎯 FOUND NEW YORKER URL from Nov 5: {url}")

                            conn.execute("""
                                INSERT OR IGNORE INTO atlas_queue
                                (source_url, title, content, source_type)
                                VALUES (?, ?, ?, ?)
                            """, (
                                url,
                                f"URL from email: {subject[:50]}",
                                f"Found in email from {from_addr} with subject: {subject}",
                                'article'
                            ))

                    conn.commit()
                    conn.close()

                    ingested += 1
                    print(f"   ✅ Ingested email {i+1}: {subject[:50]}...")

            except Exception as e:
                print(f"   ❌ Error processing email {i+1}: {e}")
                continue

        mail.logout()

        print(f"\n🎉 Email ingestion complete: {ingested} emails processed")

    except Exception as e:
        print(f"❌ Email ingestion failed: {e}")

if __name__ == "__main__":
    ingest_emails()