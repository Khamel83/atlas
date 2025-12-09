"""
Gmail Ingester - Process emails from Gmail labels.

Watches for emails with specific labels:
- atlas, Atlas (direct submissions)
- Newsletter, newsletter (newsletter content)

Uses IMAP with app password for access.
"""

import os
import re
import imaplib
import email
import logging
import time
from datetime import datetime, timedelta
from email.header import decode_header
from email.utils import parsedate_to_datetime
from typing import Optional, List, Dict, Any, Set, Tuple
from dataclasses import dataclass

from modules.storage import FileStore, IndexManager, ContentItem, ContentType, SourceType
from modules.storage.content_types import ProcessingStatus
from modules.pipeline.content_pipeline import ContentPipeline, RateLimiter

logger = logging.getLogger(__name__)


@dataclass
class EmailMessage:
    """Parsed email message."""
    email_id: str
    subject: str
    from_addr: str
    to_addr: str
    date: Optional[datetime]
    labels: List[str]
    body_text: str
    body_html: str
    urls: List[str]


class GmailIngester:
    """Ingest emails from Gmail via IMAP."""

    # Labels to watch
    WATCH_LABELS = ["atlas", "Atlas", "Newsletter", "newsletter"]

    # URL patterns to skip
    SKIP_URL_PATTERNS = [
        r"unsubscribe",
        r"preferences",
        r"twitter\.com",
        r"facebook\.com",
        r"linkedin\.com",
        r"instagram\.com",
        r"mailto:",
        r"tel:",
        r"javascript:",
        r"#$",
        r"\.gif$",
        r"\.png$",
        r"\.jpg$",
    ]

    def __init__(
        self,
        email_address: Optional[str] = None,
        app_password: Optional[str] = None,
    ):
        self.email_address = email_address or os.getenv("GMAIL_EMAIL_ADDRESS")
        self.app_password = app_password or os.getenv("GMAIL_APP_PASSWORD")

        self.file_store = FileStore("data/content")
        self.index_manager = IndexManager("data/indexes/atlas_index.db")
        self.pipeline = ContentPipeline()
        self.rate_limiter = RateLimiter(min_delay=2.0, max_delay=3.0)

        self.mail = None
        self.stats = {
            "emails_processed": 0,
            "urls_extracted": 0,
            "urls_processed": 0,
            "duplicates_skipped": 0,
            "errors": 0,
        }

    def connect(self) -> bool:
        """Connect to Gmail IMAP server."""
        if not self.email_address or not self.app_password:
            logger.error("Missing Gmail credentials")
            return False

        try:
            self.mail = imaplib.IMAP4_SSL("imap.gmail.com")
            self.mail.login(self.email_address, self.app_password)
            logger.info(f"Connected to Gmail as {self.email_address}")
            return True
        except imaplib.IMAP4.error as e:
            logger.error(f"Gmail login failed: {e}")
            return False

    def disconnect(self):
        """Disconnect from Gmail."""
        if self.mail:
            try:
                self.mail.logout()
            except Exception:
                pass
            self.mail = None

    def process_all_labels(self, since_days: int = 365) -> Dict[str, Any]:
        """
        Process all watched labels.

        Args:
            since_days: How far back to look (default 1 year)

        Returns:
            Processing statistics
        """
        if not self.connect():
            return self.stats

        try:
            all_email_ids: Set[bytes] = set()

            # Collect email IDs from all labels
            for label in self.WATCH_LABELS:
                email_ids = self._get_emails_by_label(label, since_days)
                all_email_ids.update(email_ids)
                logger.info(f"Found {len(email_ids)} emails with label '{label}'")

            logger.info(f"Total unique emails to process: {len(all_email_ids)}")

            # Process each email
            for i, email_id in enumerate(all_email_ids):
                try:
                    self._process_email(email_id)
                    self.stats["emails_processed"] += 1

                    if (i + 1) % 50 == 0:
                        logger.info(f"Processed {i + 1}/{len(all_email_ids)} emails...")

                except Exception as e:
                    logger.error(f"Error processing email {email_id}: {e}")
                    self.stats["errors"] += 1

        finally:
            self.disconnect()

        logger.info(f"Gmail ingestion complete: {self.stats}")
        return self.stats

    def _get_emails_by_label(self, label: str, since_days: int) -> List[bytes]:
        """Get email IDs for a Gmail label."""
        email_ids = []

        try:
            # Select inbox first
            self.mail.select("INBOX")

            # Search by label
            since_date = (datetime.now() - timedelta(days=since_days)).strftime("%d-%b-%Y")
            search_criteria = f'(X-GM-LABELS "{label}" SINCE "{since_date}")'

            status, data = self.mail.search(None, search_criteria)
            if status == "OK" and data[0]:
                email_ids = data[0].split()

        except Exception as e:
            logger.warning(f"Error searching label '{label}': {e}")

        return email_ids

    def _process_email(self, email_id: bytes):
        """Process a single email."""
        # Fetch email
        status, msg_data = self.mail.fetch(email_id, "(RFC822)")
        if status != "OK":
            return

        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)

        # Parse email
        parsed = self._parse_email(email_id, msg)

        # Check for duplicate
        email_content_id = ContentItem.generate_id(
            source_url=f"email://{parsed.email_id}",
            title=parsed.subject,
        )

        if self.file_store.exists(email_content_id):
            self.stats["duplicates_skipped"] += 1
            return

        # Determine if this is a newsletter or direct submission
        is_newsletter = any(
            label.lower() == "newsletter"
            for label in parsed.labels
        )

        content_type = ContentType.NEWSLETTER if is_newsletter else ContentType.EMAIL
        source_type = SourceType.NEWSLETTER if is_newsletter else SourceType.EMAIL_INGEST

        # Create email record
        email_item = ContentItem(
            content_id=email_content_id,
            content_type=content_type,
            source_type=source_type,
            title=parsed.subject or "No Subject",
            source_url=f"email://{parsed.email_id}",
            source_email=parsed.from_addr,
            description=f"From: {parsed.from_addr}",
            created_at=parsed.date or datetime.utcnow(),
            status=ProcessingStatus.COMPLETED,
            extra={
                "labels": parsed.labels,
                "to": parsed.to_addr,
                "url_count": len(parsed.urls),
            },
        )

        # Save email with body as content
        content = self._format_email_content(parsed)
        item_dir = self.file_store.save(email_item, content=content)
        self.index_manager.index_item(email_item, str(item_dir), search_text=content)

        # Process URLs from email
        self.stats["urls_extracted"] += len(parsed.urls)

        for url in parsed.urls:
            if not self._should_skip_url(url):
                try:
                    # Rate limit external requests
                    self.rate_limiter.wait()

                    result = self.pipeline.process_url(
                        url,
                        source_type=source_type,
                        extra={"parent_email_id": email_content_id},
                    )
                    if result:
                        self.stats["urls_processed"] += 1

                except Exception as e:
                    logger.error(f"Error processing URL {url}: {e}")
                    self.stats["errors"] += 1

    def _parse_email(self, email_id: bytes, msg) -> EmailMessage:
        """Parse email message."""
        # Decode subject
        subject = ""
        raw_subject = msg.get("Subject", "")
        if raw_subject:
            decoded = decode_header(raw_subject)
            parts = []
            for data, charset in decoded:
                if isinstance(data, bytes):
                    parts.append(data.decode(charset or "utf-8", errors="ignore"))
                else:
                    parts.append(data)
            subject = "".join(parts)

        # Get addresses
        from_addr = msg.get("From", "")
        to_addr = msg.get("To", "")

        # Parse date
        date = None
        date_str = msg.get("Date")
        if date_str:
            try:
                date = parsedate_to_datetime(date_str)
            except Exception:
                pass

        # Get labels
        labels = []
        gmail_labels = msg.get("X-Gmail-Labels", "")
        if gmail_labels:
            labels = [l.strip() for l in gmail_labels.split(",")]

        # Extract body and URLs
        body_text = ""
        body_html = ""
        urls = []

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                try:
                    payload = part.get_payload(decode=True)
                    if not payload:
                        continue

                    charset = part.get_content_charset() or "utf-8"
                    text = payload.decode(charset, errors="ignore")

                    if content_type == "text/plain":
                        body_text += text
                    elif content_type == "text/html":
                        body_html += text

                    urls.extend(self._extract_urls(text))
                except Exception:
                    continue
        else:
            try:
                payload = msg.get_payload(decode=True)
                if payload:
                    charset = msg.get_content_charset() or "utf-8"
                    text = payload.decode(charset, errors="ignore")
                    if msg.get_content_type() == "text/html":
                        body_html = text
                    else:
                        body_text = text
                    urls.extend(self._extract_urls(text))
            except Exception:
                pass

        # Deduplicate URLs
        urls = list(dict.fromkeys(urls))

        return EmailMessage(
            email_id=email_id.decode("utf-8") if isinstance(email_id, bytes) else str(email_id),
            subject=subject,
            from_addr=from_addr,
            to_addr=to_addr,
            date=date,
            labels=labels,
            body_text=body_text,
            body_html=body_html,
            urls=urls,
        )

    def _extract_urls(self, text: str) -> List[str]:
        """Extract URLs from text."""
        url_pattern = r'https?://[^\s<>"\')\]]+[^\s<>"\')\].,;:!?]'
        urls = re.findall(url_pattern, text)
        return urls

    def _should_skip_url(self, url: str) -> bool:
        """Check if URL should be skipped."""
        url_lower = url.lower()
        for pattern in self.SKIP_URL_PATTERNS:
            if re.search(pattern, url_lower):
                return True
        return False

    def _format_email_content(self, parsed: EmailMessage) -> str:
        """Format email as markdown content."""
        content = f"""# {parsed.subject}

**From:** {parsed.from_addr}
**To:** {parsed.to_addr}
**Date:** {parsed.date.isoformat() if parsed.date else 'Unknown'}
**Labels:** {', '.join(parsed.labels)}

---

{parsed.body_text or parsed.body_html}

---

## Extracted URLs

"""
        for url in parsed.urls:
            skip = self._should_skip_url(url)
            marker = "[skipped]" if skip else ""
            content += f"- {url} {marker}\n"

        return content


def ingest_gmail():
    """CLI entry point for Gmail ingestion."""
    import argparse
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    parser = argparse.ArgumentParser(description="Atlas Gmail Ingester")
    parser.add_argument(
        "--since-days",
        type=int,
        default=365,
        help="How far back to look (default: 365 days)"
    )
    args = parser.parse_args()

    ingester = GmailIngester()
    stats = ingester.process_all_labels(since_days=args.since_days)

    print("\n" + "=" * 50)
    print("GMAIL INGESTION COMPLETE")
    print("=" * 50)
    print(f"Emails processed:    {stats['emails_processed']}")
    print(f"URLs extracted:      {stats['urls_extracted']}")
    print(f"URLs processed:      {stats['urls_processed']}")
    print(f"Duplicates skipped:  {stats['duplicates_skipped']}")
    print(f"Errors:              {stats['errors']}")
    print("=" * 50)

    return stats


if __name__ == "__main__":
    ingest_gmail()
