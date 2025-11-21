"""
Gmail IMAP ingestor for Atlas v4.

Fetches emails from Gmail accounts and converts them to standardized Atlas content.
Supports app password authentication and basic filtering.
"""

import imaplib
import email
import email.message
from email.header import decode_header
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import re
import logging
from pathlib import Path

from .base import BaseIngestor, create_ingest_result


class GmailIngestor(BaseIngestor):
    """
    Gmail email ingestor using IMAP.

    Supports:
    - IMAP authentication with app passwords
    - Subject/content filtering
    - Since date filtering
    - HTML/plain text extraction
    """

    def ingest(self) -> List[Dict[str, Any]]:
        """Ingest emails from Gmail account."""
        items = []

        # Get connection settings
        connection_config = self.source_config.get("connection", {})
        imap_host = connection_config.get("imap_host", "imap.gmail.com")
        imap_port = connection_config.get("imap_port", 993)
        email_addr = connection_config.get("email")
        app_password = connection_config.get("app_password")

        if not all([imap_host, email_addr, app_password]):
            raise ValueError("Missing required Gmail connection configuration")

        # Get filter settings
        filters = self.source_config.get("filters", {})
        subject_contains = filters.get("subject_contains", [])
        since_days = filters.get("since_days", 7)

        try:
            # Connect to Gmail
            with imaplib.IMAP4_SSL(imap_host, imap_port) as imap:
                # Login
                imap.login(email_addr, app_password)
                self.logger.info(f"Logged in to Gmail account: {email_addr}")

                # Select inbox
                imap.select("INBOX")

                # Calculate date filter
                since_date = (datetime.now() - timedelta(days=since_days)).strftime("%d-%b-%Y")
                search_criteria = f'(SINCE {since_date})'
                self.logger.info(f"Searching for emails since: {since_date}")

                # Search for emails
                status, messages = imap.search(None, search_criteria)
                if status != "OK":
                    self.logger.error(f"Failed to search emails: {messages}")
                    return items

                email_ids = messages[0].split()
                total_emails = len(email_ids)
                self.logger.info(f"Found {total_emails} emails to process")

                # Process each email
                for i, email_id in enumerate(email_ids):
                    try:
                        # Fetch email
                        status, msg_data = imap.fetch(email_id, "(RFC822)")
                        if status != "OK":
                            continue

                        # Parse email
                        raw_email = msg_data[0][1]
                        msg = email.message_from_bytes(raw_email)
                        processed = self._process_email(msg)

                        # Apply filters
                        if self._passes_filters(processed, subject_contains):
                            items.append(processed)

                        # Log progress
                        if i > 0 and i % 50 == 0:
                            self._log_progress(i, total_emails)

                    except Exception as e:
                        self.logger.error(f"Failed to process email {email_id}: {str(e)}")

                self.logger.info(f"Processed {total_emails} emails, kept {len(items)} after filtering")

        except Exception as e:
            self.logger.error(f"Gmail ingestion failed: {str(e)}")
            raise

        return items

    def _process_email(self, msg: email.message.EmailMessage) -> Dict[str, Any]:
        """Process a single email message."""
        # Extract basic fields
        subject = self._decode_header(msg.get("Subject", ""))
        from_addr = self._decode_header(msg.get("From", ""))
        to_addr = self._decode_header(msg.get("To", ""))
        date_str = msg.get("Date", "")

        # Parse date
        try:
            date_tuple = email.utils.parsedate_tz(date_str)
            if date_tuple:
                date = datetime.fromtimestamp(email.utils.mktime_tz(date_tuple))
            else:
                date = datetime.now()
        except Exception:
            date = datetime.now()

        # Extract content
        content = self._extract_content(msg)

        # Extract URL from Gmail message
        gmail_url = f"https://mail.google.com/mail/u/0/#inbox/{msg.get('Message-ID', '')}"

        return self._create_base_item(
            title=subject or f"Email from {from_addr}",
            content=content,
            url=gmail_url,
            author=from_addr,
            date=date,
            tags=["email", "gmail"],
            from_address=from_addr,
            to_addresses=to_addr.split(", ") if to_addr else [],
            subject=subject,
            message_id=msg.get("Message-ID", "")
        )

    def _extract_content(self, msg: email.message.EmailMessage) -> str:
        """Extract text content from email message."""
        content_parts = []

        # Try to get plain text first
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    try:
                        charset = part.get_content_charset() or "utf-8"
                        content = part.get_payload(decode=True).decode(charset, errors="ignore")
                        content_parts.append(content)
                        break
                    except Exception as e:
                        self.logger.warning(f"Failed to extract plain text content: {str(e)}")
                elif content_type == "text/html":
                    # Fallback to HTML if no plain text
                    try:
                        charset = part.get_content_charset() or "utf-8"
                        html_content = part.get_payload(decode=True).decode(charset, errors="ignore")
                        plain_content = self._extract_text_from_html(html_content)
                        content_parts.append(plain_content)
                    except Exception as e:
                        self.logger.warning(f"Failed to extract HTML content: {str(e)}")
        else:
            # Single part message
            content_type = msg.get_content_type()
            charset = msg.get_content_charset() or "utf-8"
            try:
                content = msg.get_payload(decode=True).decode(charset, errors="ignore")
                if content_type == "text/html":
                    content = self._extract_text_from_html(content)
                content_parts.append(content)
            except Exception as e:
                self.logger.warning(f"Failed to extract content: {str(e)}")

        return "\n\n".join(content_parts)

    def _decode_header(self, header_value: str) -> str:
        """Decode email header value."""
        if not header_value:
            return ""

        try:
            decoded_parts = decode_header(header_value)
            if decoded_parts:
                result = []
                for part, encoding in decoded_parts:
                    if isinstance(part, bytes):
                        if encoding:
                            result.append(part.decode(encoding, errors="ignore"))
                        else:
                            result.append(part.decode("utf-8", errors="ignore"))
                    else:
                        result.append(str(part))
                return "".join(result)
            else:
                return header_value
        except Exception:
            return header_value

    def _passes_filters(self, email_item: Dict[str, Any], subject_contains: List[str]) -> bool:
        """Check if email passes configured filters."""
        # Check subject filters
        if subject_contains:
            subject = email_item.get("subject", "").lower()
            if not any(term.lower() in subject for term in subject_contains):
                return False

        # Check minimum length
        content = email_item.get("content", "")
        min_length = self.validation_config.get("min_length", 50)
        if len(content) < min_length:
            return False

        return True

    def _standardize_item(self, raw_item: Dict[str, Any]) -> Dict[str, Any]:
        """Standardize Gmail item to Atlas format."""
        return raw_item  # Gmail items are already standardized in _process_email

    @classmethod
    def get_required_config_keys(cls) -> List[str]:
        """Get required configuration keys for Gmail ingestor."""
        return ['name', 'type'] + BaseIngestor.get_required_config_keys()

    @classmethod
    def get_optional_config_keys(cls) -> List[str]:
        """Get optional configuration keys for Gmail ingestor."""
        return [
            'connection',  # imap_host, imap_port, email, app_password
            'filters',    # subject_contains, since_days
            'validation'
        ] + BaseIngestor.get_optional_config_keys()


# Standalone execution support
def main():
    """Run Gmail ingestor as standalone script."""
    import sys
    import os
    from pathlib import Path

    # Add src to path for standalone execution
    src_path = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(src_path))

    from atlas.config import load_config
    from atlas.logging import setup_logging

    # Setup logging
    setup_logging(level="INFO", enable_console=True)

    # Load configuration
    config_path = os.getenv("ATLAS_CONFIG", "config/sources/gmail.yaml")
    try:
        config = load_config(config_path)
    except Exception as e:
        print(f"Failed to load configuration: {e}")
        return 1

    # Run ingestor
    try:
        ingestor = GmailIngestor(config)
        result = ingestor.run()

        print(f"Gmail ingestion completed:")
        print(f"  Success: {result.success}")
        print(f"  Items processed: {result.items_processed}")
        print(f"  Errors: {len(result.errors)}")

        if result.errors:
            print("\nErrors:")
            for error in result.errors:
                print(f"  - {error}")

        return 0 if result.success else 1

    except Exception as e:
        print(f"Gmail ingestion failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())