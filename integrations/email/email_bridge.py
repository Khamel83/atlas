#!/usr/bin/env python3
"""
Email-to-Atlas Bridge Service
============================

Modern SMTP server that receives emails and forwards URLs to Atlas v3.

Flow:
1. Receives emails on port 2525 (SMTP)
2. Extracts URLs from email body/subject
3. Sends URLs to Atlas v3 ingest endpoint
4. Logs successful processing

Uses aiosmtpd for modern async SMTP handling.
"""

import asyncio
import email
import re
import logging
import requests
import os
import uuid
from datetime import datetime
from aiosmtpd.controller import Controller
from aiosmtpd.handlers import AsyncMessage

# Load environment
from dotenv import load_dotenv
load_dotenv('/home/ubuntu/dev/atlas/.env')

# Configuration
SMTP_HOST = '0.0.0.0'
SMTP_PORT = 2525  # Use non-privileged port first
ATLAS_URL = os.getenv('ATLAS_URL', 'https://atlas.khamel.com')
ATLAS_INGEST_ENDPOINT = os.getenv('ATLAS_INGEST_ENDPOINT', '/ingest')
ATTACHMENTS_DIR = '/home/ubuntu/dev/atlas/attachments'

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/email_atlas_bridge.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# URL extraction regex
URL_REGEX = re.compile(r'https?://\S+')

def send_to_atlas(url, source_email='unknown'):
    """Send URL to Atlas v3 ingest endpoint"""
    try:
        atlas_endpoint = f"{ATLAS_URL.rstrip('/')}{ATLAS_INGEST_ENDPOINT}"

        response = requests.get(f"{atlas_endpoint}?url={url}", timeout=10)

        if response.status_code == 200:
            result = response.json()
            unique_id = result.get('unique_id', 'unknown')
            logger.info(f"✅ Email→Atlas: {url} -> {unique_id} (from: {source_email})")
            return True
        else:
            logger.error(f"❌ Atlas returned {response.status_code}: {response.text}")
            return False

    except Exception as e:
        logger.error(f"❌ Failed to send to Atlas: {url} - {e}")
        return False

def extract_urls(text):
    """Extract URLs from text"""
    if not text:
        return []

    urls = URL_REGEX.findall(text)
    return list(set(urls))  # Remove duplicates

def save_email_attachment(attachment_data, filename, content_type):
    """Save email attachment to attachments directory"""
    try:
        # Generate unique filename
        file_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        safe_filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
        stored_filename = f"email_{file_id}_{safe_filename}"

        # Save file
        file_path = os.path.join(ATTACHMENTS_DIR, stored_filename)
        with open(file_path, 'wb') as f:
            f.write(attachment_data)

        # Create metadata
        metadata = {
            'file_id': file_id,
            'original_filename': filename,
            'stored_filename': stored_filename,
            'content_type': content_type,
            'size': len(attachment_data),
            'uploaded_at': timestamp,
            'file_path': file_path,
            'source': 'email'
        }

        logger.info(f"📎 Saved email attachment: {filename} -> {stored_filename} ({len(attachment_data)} bytes)")
        return metadata

    except Exception as e:
        logger.error(f"❌ Failed to save email attachment {filename}: {e}")
        return None

def extract_email_content_and_attachments(email_message):
    """Extract text content and save attachments from email message"""
    content = ""
    attachments = []

    if email_message.is_multipart():
        for part in email_message.walk():
            content_type = part.get_content_type()

            if content_type == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    content += payload.decode('utf-8', errors='ignore') + "\n"

            # Handle attachments
            elif part.get_filename():
                filename = part.get_filename()
                payload = part.get_payload(decode=True)
                if payload and filename:
                    metadata = save_email_attachment(payload, filename, content_type)
                    if metadata:
                        attachments.append(metadata)

                        # Extract URLs from text attachments
                        if content_type.startswith('text/'):
                            try:
                                text_content = payload.decode('utf-8', errors='ignore')
                                content += f"\n[Attachment: {filename}]\n{text_content}\n"
                            except:
                                pass
    else:
        payload = email_message.get_payload(decode=True)
        if payload:
            content = payload.decode('utf-8', errors='ignore')

    return content, attachments

class AtlasEmailHandler(AsyncMessage):
    """Custom email handler for Atlas URL ingestion"""

    async def handle_message(self, message):
        """Process incoming email and extract URLs"""
        try:
            # Get sender and recipients
            mailfrom = message.get('From', 'unknown')
            subject = message.get('Subject', '')

            logger.info(f"📧 Received email from {mailfrom}")
            logger.info(f"📝 Subject: {subject[:100]}...")

            # Extract body content and process attachments
            body, attachments = extract_email_content_and_attachments(message)

            # Log attachment processing
            if attachments:
                logger.info(f"📎 Processed {len(attachments)} attachment(s)")
                for attachment in attachments:
                    logger.info(f"  📁 {attachment['original_filename']} ({attachment['size']} bytes)")

            # Combine subject and body for URL extraction
            full_text = f"{subject}\n{body}"

            # Extract URLs
            urls = extract_urls(full_text)

            if urls:
                logger.info(f"🔗 Found {len(urls)} URL(s) in email and attachments")
                for url in urls:
                    send_to_atlas(url, mailfrom)
            else:
                if attachments:
                    logger.info("📎 Email with attachments processed (no URLs found)")
                else:
                    logger.info("❌ No URLs or attachments found in email")

        except Exception as e:
            logger.error(f"💥 Error processing email: {e}")

async def main():
    """Start the email server"""
    logger.info(f"🚀 Starting Email-to-Atlas Bridge...")
    logger.info(f"📧 Listening on {SMTP_HOST}:{SMTP_PORT}")
    logger.info(f"🎯 Forwarding to: {ATLAS_URL}{ATLAS_INGEST_ENDPOINT}")
    logger.info(f"💌 Send emails to: ingest@atlas.khamel.com")

    try:
        # Create email handler and controller
        handler = AtlasEmailHandler()
        controller = Controller(handler, hostname=SMTP_HOST, port=SMTP_PORT)

        # Start server
        controller.start()
        logger.info("✅ Email server started successfully!")

        # Keep running
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("🛑 Shutting down email server...")
        controller.stop()
    except Exception as e:
        logger.error(f"💥 Server error: {e}")

if __name__ == "__main__":
    asyncio.run(main())