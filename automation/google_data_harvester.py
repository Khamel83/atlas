#!/usr/bin/env python3
"""
Google Data Harvester - Automated Email, Drive, and Service Access
Extracts Gmail newsletters, Drive documents, and other Google services data
"""
import os
import json
import time
import logging
import email
import base64
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from pathlib import Path

# Google API imports
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print("Google API libraries not installed. Run: pip install google-auth google-auth-oauthlib google-api-python-client")
    raise

# Selenium for fallback web scraping
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    print("Selenium not installed. Run: pip install selenium webdriver-manager")
    raise

import requests
from bs4 import BeautifulSoup

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Google API scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/youtube.readonly'
]

@dataclass
class EmailData:
    """Email data structure"""
    message_id: str
    subject: str
    sender: str
    date: str
    body: str
    html_body: Optional[str] = None
    attachments: List[str] = None
    labels: List[str] = None
    is_newsletter: bool = False

@dataclass
class DriveFile:
    """Google Drive file data structure"""
    file_id: str
    name: str
    mime_type: str
    created_time: str
    modified_time: str
    size: Optional[int] = None
    content: Optional[str] = None
    download_url: Optional[str] = None

class GoogleDataHarvester:
    """Automated Google services data harvester"""

    def __init__(self, credentials_file: str = "credentials.json", token_file: str = "token.json"):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.creds = None
        self.gmail_service = None
        self.drive_service = None
        self.calendar_service = None

        # Newsletter detection patterns
        self.newsletter_patterns = [
            'newsletter', 'digest', 'weekly', 'daily', 'update',
            'substack', 'mailchimp', 'constantcontact', 'unsubscribe',
            'morning brew', 'the hustle', 'techcrunch', 'hacker news'
        ]

        # Common newsletter senders
        self.newsletter_senders = [
            '@substack.com', '@mailchimp.com', '@constantcontact.com',
            '@morning-brew.com', '@thehustle.co', '@techcrunch.com',
            'noreply@', 'newsletter@', 'digest@'
        ]

    def authenticate(self) -> bool:
        """Authenticate with Google APIs using OAuth2"""
        try:
            # Load existing credentials
            if os.path.exists(self.token_file):
                self.creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)

            # Refresh or get new credentials
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    self.creds.refresh(Request())
                else:
                    if not os.path.exists(self.credentials_file):
                        logger.error(f"Credentials file {self.credentials_file} not found")
                        logger.info("Please download credentials.json from Google Cloud Console")
                        return False

                    flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, SCOPES)
                    self.creds = flow.run_local_server(port=0)

                # Save credentials for next run
                with open(self.token_file, 'w') as token:
                    token.write(self.creds.to_json())

            # Initialize services
            self.gmail_service = build('gmail', 'v1', credentials=self.creds)
            self.drive_service = build('drive', 'v3', credentials=self.creds)
            self.calendar_service = build('calendar', 'v3', credentials=self.creds)

            logger.info("Successfully authenticated with Google APIs")
            return True

        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False

    def get_gmail_newsletters(self, days_back: int = 30, max_emails: int = 1000) -> List[EmailData]:
        """Extract newsletter emails from Gmail"""
        try:
            logger.info(f"Fetching newsletters from last {days_back} days...")

            # Calculate date range
            after_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y/%m/%d')
            query = f'after:{after_date}'

            # Get message list
            result = self.gmail_service.users().messages().list(
                userId='me', q=query, maxResults=max_emails
            ).execute()

            messages = result.get('messages', [])
            logger.info(f"Found {len(messages)} emails to process")

            newsletter_emails = []

            for i, message in enumerate(messages):
                try:
                    # Get full message
                    msg = self.gmail_service.users().messages().get(
                        userId='me', id=message['id'], format='full'
                    ).execute()

                    email_data = self._parse_email_message(msg)

                    # Check if it's a newsletter
                    if self._is_newsletter(email_data):
                        newsletter_emails.append(email_data)
                        logger.debug(f"Found newsletter: {email_data.subject[:50]}...")

                    if (i + 1) % 100 == 0:
                        logger.info(f"Processed {i + 1} emails, found {len(newsletter_emails)} newsletters")

                except Exception as e:
                    logger.debug(f"Error processing email {message['id']}: {e}")
                    continue

            logger.info(f"Found {len(newsletter_emails)} newsletters")
            return newsletter_emails

        except Exception as e:
            logger.error(f"Failed to fetch Gmail newsletters: {e}")
            return []

    def _parse_email_message(self, msg: Dict) -> EmailData:
        """Parse Gmail API message into EmailData"""
        headers = {h['name']: h['value'] for h in msg['payload'].get('headers', [])}

        subject = headers.get('Subject', 'No Subject')
        sender = headers.get('From', 'Unknown Sender')
        date = headers.get('Date', '')
        labels = [label for label in msg.get('labelIds', [])]

        # Extract body
        body = ''
        html_body = None

        try:
            body, html_body = self._extract_email_body(msg['payload'])
        except Exception as e:
            logger.debug(f"Error extracting email body: {e}")

        return EmailData(
            message_id=msg['id'],
            subject=subject,
            sender=sender,
            date=date,
            body=body,
            html_body=html_body,
            labels=labels
        )

    def _extract_email_body(self, payload: Dict) -> tuple[str, Optional[str]]:
        """Extract text and HTML body from email payload"""
        body = ''
        html_body = None

        if 'parts' in payload:
            for part in payload['parts']:
                mime_type = part.get('mimeType', '')

                if mime_type == 'text/plain' and 'data' in part['body']:
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                elif mime_type == 'text/html' and 'data' in part['body']:
                    html_body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    if not body:  # Use HTML as fallback for text
                        soup = BeautifulSoup(html_body, 'html.parser')
                        body = soup.get_text()
        else:
            # Single part message
            if 'data' in payload.get('body', {}):
                body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')

        return body, html_body

    def _is_newsletter(self, email_data: EmailData) -> bool:
        """Determine if an email is a newsletter"""
        subject_lower = email_data.subject.lower()
        sender_lower = email_data.sender.lower()
        body_lower = email_data.body.lower() if email_data.body else ''

        # Check sender patterns
        for sender_pattern in self.newsletter_senders:
            if sender_pattern in sender_lower:
                return True

        # Check subject patterns
        for pattern in self.newsletter_patterns:
            if pattern in subject_lower:
                return True

        # Check body for newsletter indicators
        if any(pattern in body_lower for pattern in ['unsubscribe', 'newsletter', 'weekly digest']):
            return True

        return False

    def get_drive_documents(self, days_back: int = 30, max_files: int = 100) -> List[DriveFile]:
        """Extract recent documents from Google Drive"""
        try:
            logger.info(f"Fetching Drive documents from last {days_back} days...")

            # Calculate date range
            after_date = (datetime.now() - timedelta(days=days_back)).isoformat()

            # Query for documents
            query = f"modifiedTime > '{after_date}' and (mimeType contains 'document' or mimeType contains 'presentation' or mimeType contains 'spreadsheet')"

            result = self.drive_service.files().list(
                q=query,
                pageSize=max_files,
                fields="files(id, name, mimeType, createdTime, modifiedTime, size)"
            ).execute()

            files = result.get('files', [])
            logger.info(f"Found {len(files)} Drive documents")

            drive_files = []

            for file_data in files:
                try:
                    # Get file content if it's a Google Doc/Sheet/Slide
                    content = None
                    if 'document' in file_data['mimeType']:
                        content = self._get_google_doc_content(file_data['id'])

                    drive_file = DriveFile(
                        file_id=file_data['id'],
                        name=file_data['name'],
                        mime_type=file_data['mimeType'],
                        created_time=file_data['createdTime'],
                        modified_time=file_data['modifiedTime'],
                        size=file_data.get('size'),
                        content=content
                    )

                    drive_files.append(drive_file)

                except Exception as e:
                    logger.debug(f"Error processing Drive file {file_data['name']}: {e}")
                    continue

            return drive_files

        except Exception as e:
            logger.error(f"Failed to fetch Drive documents: {e}")
            return []

    def _get_google_doc_content(self, file_id: str) -> Optional[str]:
        """Extract text content from Google Doc"""
        try:
            # Export as plain text
            content = self.drive_service.files().export(
                fileId=file_id,
                mimeType='text/plain'
            ).execute()

            return content.decode('utf-8')

        except Exception as e:
            logger.debug(f"Error extracting Google Doc content: {e}")
            return None

    def save_to_atlas(self, emails: List[EmailData], drive_files: List[DriveFile],
                     atlas_url: str = "http://localhost:8000") -> bool:
        """Save extracted data to Atlas"""
        try:
            total_items = len(emails) + len(drive_files)
            logger.info(f"Saving {total_items} items to Atlas ({len(emails)} emails, {len(drive_files)} drive files)...")

            saved_count = 0

            # Save emails
            for email_data in emails:
                try:
                    content_data = {
                        "url": f"https://mail.google.com/mail/u/0/#inbox/{email_data.message_id}",
                        "title": email_data.subject,
                        "content": f"From: {email_data.sender}\nDate: {email_data.date}\nSubject: {email_data.subject}\n\n{email_data.body}",
                        "source": "gmail-newsletter-harvester",
                        "metadata": {
                            "message_id": email_data.message_id,
                            "sender": email_data.sender,
                            "date": email_data.date,
                            "labels": email_data.labels,
                            "is_newsletter": email_data.is_newsletter,
                            "platform": "gmail"
                        }
                    }

                    response = requests.post(
                        f"{atlas_url}/api/v1/content/save",
                        json=content_data,
                        headers={"Content-Type": "application/json"}
                    )

                    if response.status_code == 200:
                        saved_count += 1

                except Exception as e:
                    logger.debug(f"Error saving email {email_data.subject}: {e}")

            # Save Drive files
            for drive_file in drive_files:
                try:
                    content_data = {
                        "url": f"https://drive.google.com/file/d/{drive_file.file_id}/view",
                        "title": drive_file.name,
                        "content": drive_file.content or f"Google Drive File: {drive_file.name}\nType: {drive_file.mime_type}\nModified: {drive_file.modified_time}",
                        "source": "google-drive-harvester",
                        "metadata": {
                            "file_id": drive_file.file_id,
                            "mime_type": drive_file.mime_type,
                            "created_time": drive_file.created_time,
                            "modified_time": drive_file.modified_time,
                            "size": drive_file.size,
                            "platform": "google-drive"
                        }
                    }

                    response = requests.post(
                        f"{atlas_url}/api/v1/content/save",
                        json=content_data,
                        headers={"Content-Type": "application/json"}
                    )

                    if response.status_code == 200:
                        saved_count += 1

                except Exception as e:
                    logger.debug(f"Error saving Drive file {drive_file.name}: {e}")

            logger.info(f"Successfully saved {saved_count}/{total_items} items to Atlas")
            return saved_count == total_items

        except Exception as e:
            logger.error(f"Failed to save to Atlas: {e}")
            return False

    def export_to_json(self, emails: List[EmailData], drive_files: List[DriveFile],
                      filename: str = None) -> str:
        """Export data to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"google_data_export_{timestamp}.json"

        export_data = {
            "export_date": datetime.now().isoformat(),
            "total_emails": len(emails),
            "total_drive_files": len(drive_files),
            "emails": [
                {
                    "message_id": email.message_id,
                    "subject": email.subject,
                    "sender": email.sender,
                    "date": email.date,
                    "body": email.body[:1000] + "..." if len(email.body) > 1000 else email.body,
                    "labels": email.labels,
                    "is_newsletter": email.is_newsletter
                }
                for email in emails
            ],
            "drive_files": [
                {
                    "file_id": file.file_id,
                    "name": file.name,
                    "mime_type": file.mime_type,
                    "created_time": file.created_time,
                    "modified_time": file.modified_time,
                    "size": file.size,
                    "content_preview": file.content[:500] + "..." if file.content and len(file.content) > 500 else file.content
                }
                for file in drive_files
            ]
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Exported data to {filename}")
        return filename

def main():
    """Main function for command-line usage"""
    import argparse

    parser = argparse.ArgumentParser(description="Google Data Harvester")
    parser.add_argument('--days-back', type=int, default=30, help='Days back to harvest data')
    parser.add_argument('--max-emails', type=int, default=1000, help='Maximum emails to process')
    parser.add_argument('--max-drive-files', type=int, default=100, help='Maximum Drive files to process')
    parser.add_argument('--atlas-url', default='http://localhost:8000', help='Atlas server URL')
    parser.add_argument('--export-only', action='store_true', help='Only export to JSON, do not save to Atlas')
    parser.add_argument('--credentials', default='credentials.json', help='Google credentials file')
    parser.add_argument('--token', default='token.json', help='Google token file')
    parser.add_argument('--emails-only', action='store_true', help='Only harvest emails')
    parser.add_argument('--drive-only', action='store_true', help='Only harvest Drive files')

    args = parser.parse_args()

    harvester = GoogleDataHarvester(args.credentials, args.token)

    try:
        # Authenticate
        if not harvester.authenticate():
            logger.error("Authentication failed")
            return

        emails = []
        drive_files = []

        # Harvest emails
        if not args.drive_only:
            emails = harvester.get_gmail_newsletters(
                days_back=args.days_back,
                max_emails=args.max_emails
            )

        # Harvest Drive files
        if not args.emails_only:
            drive_files = harvester.get_drive_documents(
                days_back=args.days_back,
                max_files=args.max_drive_files
            )

        if not emails and not drive_files:
            logger.warning("No data found")
            return

        # Export to JSON
        json_file = harvester.export_to_json(emails, drive_files)
        logger.info(f"Exported data to {json_file}")

        # Save to Atlas
        if not args.export_only:
            if harvester.save_to_atlas(emails, drive_files, args.atlas_url):
                logger.info("Successfully saved all data to Atlas")
            else:
                logger.error("Failed to save some data to Atlas")

    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()