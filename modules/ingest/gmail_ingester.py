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
class EmailAttachment:
    """Email attachment."""
    filename: str
    content_type: str
    data: bytes


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
    attachments: List[EmailAttachment] = None

    def __post_init__(self):
        if self.attachments is None:
            self.attachments = []


class GmailIngester:
    """Ingest emails from Gmail via IMAP."""

    # Labels to watch
    WATCH_LABELS = ["atlas", "Atlas", "Newsletter", "newsletter"]

    # URL patterns to skip - tracking links, redirects, marketing junk
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
        # Tracking/redirect URLs
        r"substack\.com/redirect",
        r"bloom\.bg/",
        r"bit\.ly/",
        r"tinyurl\.com/",
        r"t\.co/",
        r"ow\.ly/",
        r"clicks\.",
        r"click\.",
        r"track\.",
        r"tracking\.",
        r"redirect\.",
        r"links\.message\.",
        r"email\.mg\.",
        r"mailchi\.mp/",
        r"list-manage\.com",
        r"campaign-archive\.com",
        r"utm_",
        r"email\..*\.com/e/",  # Generic email tracking
        r"/beacon",
        r"/pixel",
        r"/open\?",
        r"/click\?",
        r"404media\.co/r/",  # 404media tracking redirects
        r"puck\.news.*utm",  # Puck tracking links
        r"customeriomail\.com",
        r"assets\.",  # Asset/image servers
    ]

    # Newsletter senders where the email body IS the content
    # Skip URL processing for these - don't chase tracking links
    NEWSLETTER_SENDERS_SKIP_URLS = [
        "bloomberg.com",
        "bloom.bg",
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
            # Select All Mail to find labeled emails anywhere (not just inbox)
            self.mail.select('"[Gmail]/All Mail"')

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

        # Save attachments
        if parsed.attachments:
            attachments_dir = item_dir / "attachments"
            attachments_dir.mkdir(exist_ok=True)
            for attachment in parsed.attachments:
                attachment_path = attachments_dir / attachment.filename
                with open(attachment_path, "wb") as f:
                    f.write(attachment.data)
                logger.info(f"Saved attachment: {attachment_path}")
                self.stats["attachments_saved"] = self.stats.get("attachments_saved", 0) + 1

                # Process PDFs for text extraction
                if attachment.content_type == "application/pdf":
                    self._process_pdf_attachment(attachment, email_content_id, item_dir)

        # Check if this is a newsletter where the email body IS the content
        # Skip URL processing for these senders - their tracking links fail anyway
        skip_url_processing = any(
            sender in parsed.from_addr.lower()
            for sender in self.NEWSLETTER_SENDERS_SKIP_URLS
        )

        if skip_url_processing:
            logger.info(f"Skipping URL processing for newsletter from {parsed.from_addr}")
            return

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

        # Extract body, URLs, and attachments
        body_text = ""
        body_html = ""
        urls = []
        attachments = []

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))

                try:
                    payload = part.get_payload(decode=True)
                    if not payload:
                        continue

                    # Check if this is an attachment - save ANY file with a filename
                    filename = part.get_filename()
                    if filename or "attachment" in content_disposition:
                        if not filename:
                            # Generate filename from content type
                            ext = content_type.split("/")[-1] if "/" in content_type else "bin"
                            filename = f"attachment.{ext}"
                        # Decode filename if needed
                        decoded_filename = decode_header(filename)
                        if decoded_filename and isinstance(decoded_filename[0][0], bytes):
                            filename = decoded_filename[0][0].decode(
                                decoded_filename[0][1] or "utf-8", errors="ignore"
                            )
                        attachments.append(EmailAttachment(
                            filename=filename,
                            content_type=content_type,
                            data=payload,
                        ))
                        logger.info(f"Found attachment: {filename} ({content_type})")
                        continue

                    # Extract text content
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
            attachments=attachments,
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

        if parsed.attachments:
            content += "\n## Attachments\n\n"
            for att in parsed.attachments:
                content += f"- {att.filename} ({att.content_type})\n"

        return content

    def _process_pdf_attachment(self, attachment: EmailAttachment, parent_id: str, item_dir) -> None:
        """Extract text from PDF attachment and index it."""
        try:
            import pymupdf  # PyMuPDF
        except ImportError:
            logger.warning("PyMuPDF not installed, skipping PDF text extraction")
            return

        try:
            # Extract text from PDF
            doc = pymupdf.open(stream=attachment.data, filetype="pdf")
            text_parts = []
            for page in doc:
                text_parts.append(page.get_text())
            doc.close()

            pdf_text = "\n\n".join(text_parts)
            if not pdf_text.strip():
                logger.info(f"PDF {attachment.filename} has no extractable text (may be scanned)")
                return

            # Save extracted text alongside the PDF
            text_path = item_dir / "attachments" / f"{attachment.filename}.txt"
            with open(text_path, "w", encoding="utf-8") as f:
                f.write(pdf_text)

            logger.info(f"Extracted {len(pdf_text)} chars from PDF {attachment.filename}")

        except Exception as e:
            logger.error(f"Error extracting text from PDF {attachment.filename}: {e}")


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
