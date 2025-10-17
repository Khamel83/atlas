import os
import re
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from base64 import urlsafe_b64decode
import email
import logging

# Configuration
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
LABEL_NAME = os.environ.get(
    "GMAIL_LABEL", "YourLabelName"
)  # Replace with your Gmail label
SAVE_FOLDER = os.environ.get(
    "SAVE_FOLDER", "/path/to/save/folder"
)  # e.g., ~/Documents/Emails
TRACKING_FILE = os.path.join(SAVE_FOLDER, "downloaded_ids.txt")

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def get_gmail_service():
    creds = None
    token_path = "token.json"
    credentials_path = "credentials.json"

    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        except Exception as e:
            logging.error(f"Failed to load token from {token_path}: {e}")
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                logging.error(f"Failed to refresh token: {e}")
                creds = None
        else:
            if not os.path.exists(credentials_path):
                logging.error(f"Credentials file not found: {credentials_path}")
                return None
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)
            except Exception as e:
                logging.error(f"Failed to create credentials from file: {e}")
                return None

        if creds:
            try:
                with open(token_path, "w") as token:
                    token.write(creds.to_json())
            except Exception as e:
                logging.error(f"Failed to save token to {token_path}: {e}")
    if not creds:
        logging.error("Could not get credentials.")
        return None
    return build("gmail", "v1", credentials=creds)


def sanitize_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', "", filename)


def download_emails():
    service = get_gmail_service()
    if not service:
        logging.error("Failed to get Gmail service.")
        return

    # Fetch label ID
    try:
        labels = service.users().labels().list(userId="me").execute().get("labels", [])
        label_id = next(
            (label["id"] for label in labels if label["name"] == LABEL_NAME), None
        )
        if not label_id:
            logging.error(f"Label '{LABEL_NAME}' not found.")
            return
    except Exception as e:
        logging.error(f"Failed to fetch labels: {e}")
        return

    # Track downloaded emails
    os.makedirs(SAVE_FOLDER, exist_ok=True)
    downloaded_ids = set()
    if os.path.exists(TRACKING_FILE):
        with open(TRACKING_FILE, "r") as f:
            downloaded_ids = set(f.read().splitlines())

    # Fetch messages
    page_token = None
    while True:
        try:
            response = (
                service.users()
                .messages()
                .list(userId="me", labelIds=[label_id], pageToken=page_token)
                .execute()
            )
            messages = response.get("messages", [])
            for msg in messages:
                msg_id = msg["id"]
                if msg_id in downloaded_ids:
                    continue
                try:
                    msg_data = (
                        service.users()
                        .messages()
                        .get(userId="me", id=msg_id, format="raw")
                        .execute()
                    )
                    raw_email = urlsafe_b64decode(msg_data["raw"].encode("ASCII"))
                    email_msg = email.message_from_bytes(raw_email)
                    subject = email_msg.get("Subject", "NoSubject")
                    date = (
                        email_msg.get("Date", "NoDate")
                        .replace(" ", "_")
                        .replace(":", "-")
                    )
                    filename = f"{sanitize_filename(subject)}_{date}_{msg_id}.eml"
                    filepath = os.path.join(SAVE_FOLDER, filename)
                    with open(filepath, "wb") as f:
                        f.write(raw_email)
                    downloaded_ids.add(msg_id)
                    with open(TRACKING_FILE, "a") as f:
                        f.write(f"{msg_id}\n")
                except Exception as e:
                    logging.error(f"Failed to download {msg_id}: {e}")
            page_token = response.get("nextPageToken")
            if not page_token:
                break
        except Exception as e:
            logging.error(f"Failed to list messages: {e}")
            break


if __name__ == "__main__":
    download_emails()
