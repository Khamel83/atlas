import imaplib
import os
import re
from email import policy
from email.parser import BytesParser
from typing import Iterable, Tuple

from vos.ingestion.utils import create_job, save_raw_email

IMAP_HOST = os.getenv("GMAIL_IMAP_HOST", "imap.gmail.com")
IMAP_PORT = int(os.getenv("GMAIL_IMAP_PORT", "993"))
GMAIL_LABELS = [
    label.strip()
    for label in os.getenv("GMAIL_LABELS", "Atlas,Newsletter").split(",")
    if label.strip()
]
GMAIL_USERNAME = os.getenv("GMAIL_USERNAME")
GMAIL_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
LINK_REGEX = re.compile(r"https?://[\w./?&=-]+", re.IGNORECASE)


def parse_text(content: str) -> str:
    return content.strip()


def extract_links(contents: Iterable[str]) -> list[str]:
    links = []
    for text in contents:
        links.extend(LINK_REGEX.findall(text))
    return sorted(set(links))


def fetch_email_message(num: bytes, mail: imaplib.IMAP4_SSL) -> bytes:
    status, data = mail.fetch(num, "(RFC822)")
    if status != "OK":
        raise RuntimeError(f"fetch failed for {num}")
    return data[0][1]


def parse_message(body: bytes) -> Tuple[str, str, str]:
    parser = BytesParser(policy=policy.default)
    msg = parser.parsebytes(body)
    text_parts = []
    html_parts = []
    for part in msg.walk():
        if part.is_multipart():
            continue
        try:
            payload = part.get_content()
        except Exception:
            continue
        if not payload:
            continue
        if part.get_content_type() == "text/plain":
            text_parts.append(parse_text(payload))
        elif part.get_content_type() == "text/html":
            html_parts.append(payload)
    subject = msg.get("Subject") or ""
    return subject, "\n".join(text_parts), "\n".join(html_parts)


def poll_gmail() -> int:
    if not (GMAIL_USERNAME and GMAIL_PASSWORD):
        raise RuntimeError("GMAIL_USERNAME and GMAIL_APP_PASSWORD must be set")
    mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    mail.login(GMAIL_USERNAME, GMAIL_PASSWORD)
    total = 0
    try:
        for label in GMAIL_LABELS:
            if not label:
                continue
            status, _ = mail.select(f'"{label}"')
            if status != "OK":
                continue
            status, data = mail.search(None, "UNSEEN")
            if status != "OK":
                continue
            for num in data[0].split():
                try:
                    body = fetch_email_message(num, mail)
                except RuntimeError:
                    continue
                raw_path = save_raw_email(body, label)
                subject, text, html = parse_message(body)
                links = extract_links([text, html])
                payload = {
                    "subject": subject,
                    "text": text,
                    "html": html,
                    "links": links,
                    "raw_path": str(raw_path),
                }
                create_job("email", "gmail", payload)
                total += 1
                mail.store(num, "+FLAGS", "\\Seen")
    finally:
        try:
            mail.logout()
        except Exception:
            pass
    return total
