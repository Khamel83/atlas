#!/usr/bin/env python3
"""Check recent emails and their Gmail labels."""
import imaplib
import os
import email
from email.header import decode_header

def main():
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(os.environ["GMAIL_EMAIL_ADDRESS"], os.environ["GMAIL_APP_PASSWORD"])
    mail.select("INBOX")

    # Get ALL emails and take the last 100
    status, data = mail.search(None, "ALL")
    all_ids = data[0].split()
    email_ids = all_ids[-100:]  # last 100

    print(f"Checking last {len(email_ids)} emails (total: {len(all_ids)})")
    print()

    for eid in email_ids:
        status, labels_response = mail.fetch(eid, "(X-GM-LABELS)")
        status, msg_data = mail.fetch(eid, "(RFC822)")

        if status != "OK":
            continue

        # Parse labels
        try:
            labels_str = str(labels_response[0])
        except:
            labels_str = "parse error"

        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)

        # Decode subject
        subject = msg.get("Subject", "No Subject")
        try:
            decoded = decode_header(subject)
            if decoded and isinstance(decoded[0][0], bytes):
                charset = decoded[0][1] or "utf-8"
                if charset == "unknown-8bit":
                    charset = "utf-8"
                subject = decoded[0][0].decode(charset, errors="ignore")
        except:
            pass

        date = msg.get("Date", "Unknown")

        # Highlight Atlas-labeled emails
        if "Atlas" in labels_str or "atlas" in labels_str:
            print(f"*** ATLAS ***")

        print(f"ID: {eid.decode()}")
        print(f"Subject: {subject[:80]}")
        print(f"Date: {date}")
        print(f"Labels: {labels_str}")
        print("-" * 70)

    mail.logout()

if __name__ == "__main__":
    main()
