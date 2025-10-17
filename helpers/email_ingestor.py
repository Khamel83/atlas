#!/usr/bin/env python3
"""
Email Ingestor for Atlas

This module handles downloading emails from Gmail,
extracting metadata, and integrating with the Atlas content pipeline.
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from googleapiclient.discovery import build
from helpers.email_auth_manager import EmailAuthManager

class EmailIngestor:
    """Handles downloading and processing emails from Gmail"""

    def __init__(self, auth_manager):
        """
        Initialize the EmailIngestor

        Args:
            auth_manager (EmailAuthManager): Authenticated Gmail service manager
        """
        self.auth_manager = auth_manager
        self.service = auth_manager.get_service()
        self.download_tracker = {}
        self.load_download_tracker()

    def load_download_tracker(self):
        """Load download tracking information from file"""
        tracker_file = Path('email_download_tracker.json')
        if tracker_file.exists():
            with open(tracker_file, 'r') as f:
                self.download_tracker = json.load(f)

    def save_download_tracker(self):
        """Save download tracking information to file"""
        tracker_file = Path('email_download_tracker.json')
        with open(tracker_file, 'w') as f:
            json.dump(self.download_tracker, f, indent=2)

    def get_new_emails(self, label='INBOX', max_results=100):
        """
        Download new emails from Gmail

        Args:
            label (str): Gmail label to filter emails
            max_results (int): Maximum number of emails to download

        Returns:
            list: List of email messages
        """
        try:
            # Get the last message ID we've processed
            last_message_id = self.download_tracker.get('last_message_id', '')

            # Query for emails
            query = ''
            if last_message_id:
                # Only get emails newer than the last processed email
                query = f"after:{last_message_id}"

            # Get list of messages
            results = self.service.users().messages().list(
                userId='me',
                labelIds=[label],
                q=query,
                maxResults=max_results
            ).execute()

            messages = results.get('messages', [])

            # Process each message
            emails = []
            for message in messages:
                email_data = self.process_message(message['id'])
                if email_data:
                    emails.append(email_data)

                    # Update tracker with latest message ID
                    if message['id'] > last_message_id:
                        last_message_id = message['id']
                        self.download_tracker['last_message_id'] = last_message_id
                        self.save_download_tracker()

            return emails

        except Exception as e:
            logging.error(f"Failed to download emails: {e}")
            return []

    def process_message(self, message_id):
        """
        Process a single email message

        Args:
            message_id (str): Gmail message ID

        Returns:
            dict: Processed email data or None if failed
        """
        try:
            # Get the message
            message = self.service.users().messages().get(
                userId='me',
                id=message_id
            ).execute()

            # Extract metadata
            headers = message['payload'].get('headers', [])
            email_data = {
                'id': message_id,
                'threadId': message.get('threadId', ''),
                'historyId': message.get('historyId', ''),
                'internalDate': message.get('internalDate', ''),
                'sender': self.extract_header(headers, 'From'),
                'subject': self.extract_header(headers, 'Subject'),
                'date': self.extract_header(headers, 'Date'),
                'to': self.extract_header(headers, 'To'),
                'cc': self.extract_header(headers, 'Cc'),
                'bcc': self.extract_header(headers, 'Bcc'),
                'content': self.extract_content(message),
                'labels': message.get('labelIds', []),
                'size': message.get('sizeEstimate', 0)
            }

            return email_data

        except Exception as e:
            logging.error(f"Failed to process message {message_id}: {e}")
            return None

    def extract_header(self, headers, name):
        """
        Extract a specific header from email headers

        Args:
            headers (list): List of email headers
            name (str): Name of header to extract

        Returns:
            str: Header value or empty string if not found
        """
        for header in headers:
            if header.get('name', '').lower() == name.lower():
                return header.get('value', '')
        return ''

    def extract_content(self, message):
        """
        Extract content from email message

        Args:
            message (dict): Gmail message object

        Returns:
            str: Email content or empty string if not found
        """
        try:
            # Get the message parts
            payload = message['payload']
            parts = payload.get('parts', [])

            # If no parts, try getting body directly
            if not parts:
                body = payload.get('body', {})
                data = body.get('data', '')
                if data:
                    # Decode base64 content
                    import base64
                    return base64.urlsafe_b64decode(data).decode('utf-8')
                return ''

            # Look for text/plain or text/html parts
            for part in parts:
                if part.get('mimeType', '') == 'text/plain':
                    body = part.get('body', {})
                    data = body.get('data', '')
                    if data:
                        import base64
                        return base64.urlsafe_b64decode(data).decode('utf-8')
                elif part.get('mimeType', '') == 'text/html':
                    body = part.get('body', {})
                    data = body.get('data', '')
                    if data:
                        import base64
                        return base64.urlsafe_b64decode(data).decode('utf-8')

            return ''

        except Exception as e:
            logging.error(f"Failed to extract content: {e}")
            return ''

    def filter_newsletters(self, emails):
        """
        Filter emails to identify newsletters

        Args:
            emails (list): List of email data

        Returns:
            list: Filtered list of newsletter emails
        """
        newsletters = []

        for email in emails:
            # Simple heuristic to identify newsletters
            # In a real implementation, this would be more sophisticated
            subject = email.get('subject', '').lower()
            sender = email.get('sender', '').lower()

            # Check for common newsletter indicators
            if any(keyword in subject for keyword in ['newsletter', 'digest', 'weekly', 'monthly']) or \
               any(domain in sender for domain in ['noreply', 'news', 'digest']):
                newsletters.append(email)

        return newsletters

    def integrate_with_atlas_pipeline(self, emails):
        """
        Integrate downloaded emails with Atlas content pipeline

        Args:
            emails (list): List of email data to process
        """
        # In a real implementation, this would:
        # 1. Convert emails to Atlas content format
        # 2. Add to processing queue
        # 3. Handle deduplication
        # 4. Track processing status
        pass

    def handle_rate_limits(self):
        """Handle Gmail API rate limits gracefully"""
        # In a real implementation, this would:
        # 1. Monitor API usage
        # 2. Implement exponential backoff
        # 3. Queue requests when limits are reached
        pass

    def track_download_progress(self, total, processed):
        """
        Track download progress

        Args:
            total (int): Total number of emails to process
            processed (int): Number of emails processed
        """
        # In a real implementation, this would:
        # 1. Update progress tracking
        # 2. Log progress information
        # 3. Handle resume functionality
        pass

def main():
    """Example usage of EmailIngestor"""
    # Initialize authentication
    auth_manager = EmailAuthManager()

    try:
        # Authenticate
        service = auth_manager.authenticate()
        print("Authentication successful!")

        # Initialize ingestor
        ingestor = EmailIngestor(auth_manager)

        # Download new emails
        print("Downloading new emails...")
        emails = ingestor.get_new_emails()

        print(f"Downloaded {len(emails)} emails")

        # Filter for newsletters
        newsletters = ingestor.filter_newsletters(emails)
        print(f"Identified {len(newsletters)} newsletters")

        # Integrate with Atlas pipeline
        ingestor.integrate_with_atlas_pipeline(newsletters)

    except Exception as e:
        print(f"Email ingestion failed: {e}")

if __name__ == "__main__":
    main()