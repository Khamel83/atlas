import os
import re
from base64 import urlsafe_b64decode
import email
import logging
from email import policy
import json

try:
    from googleapiclient.discovery import build
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from bs4 import BeautifulSoup
except ImportError as e:
    print(
        f"Failed to import required modules: {e}. Please ensure you have installed the required packages. You can install them by running: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib beautifulsoup4"
    )
    exit()

# Configuration
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
LABEL_NAME = "Newsletter"
SAVE_FOLDER = os.environ.get(
    "SAVE_FOLDER",
    "/Users/macmini/Library/Mobile Documents/com~apple~CloudDocs/Code/email downloads/saved_emails",
)
SAVE_HTML_FOLDER = "/Users/macmini/Library/Mobile Documents/com~apple~CloudDocs/Code/email downloads/saved_html"
TRACKING_FILE = os.path.join(SAVE_FOLDER, "downloaded_ids.txt")
CONVERTED_TRACKING_FILE = os.path.join(SAVE_HTML_FOLDER, "converted_ids.txt")
STATUS_FILE = os.path.join(SAVE_FOLDER, "email_status.json")

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def get_gmail_service():
    creds = None
    token_path = "/Users/macmini/Library/Mobile Documents/com~apple~CloudDocs/Code/email downloads/token.json"
    credentials_path = "/Users/macmini/Library/Mobile Documents/com~apple~CloudDocs/Code/email downloads/credentials.json"

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
                with open(token_path, "w") as token:
                    token.write(creds.to_json())
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


def eml_to_html(eml_file, email_status):
    filename = os.path.basename(eml_file)
    html_file = os.path.join(SAVE_HTML_FOLDER, os.path.splitext(filename)[0] + ".html")

    try:
        with open(eml_file, "r", encoding="utf-8") as file:
            msg = email.message_from_file(file, policy=policy.default)

        body = ""
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                body = part.get_payload(decode=True).decode(
                    part.get_content_charset(), errors="ignore"
                )
                break
            elif part.get_content_type() == "text/plain":
                body = part.get_payload(decode=True).decode(
                    part.get_content_charset(), errors="ignore"
                )

        if body:
            body = BeautifulSoup(body, "html.parser").prettify()

        os.makedirs(SAVE_HTML_FOLDER, exist_ok=True)
        with open(html_file, "w", encoding="utf-8") as file:
            file.write(body)

        logging.info(f"Converted: {html_file}")
        email_status[filename]["converted"] = True

    except Exception as e:
        logging.error(f"Failed to convert {eml_file} to HTML: {e}")
        email_status[filename]["converted"] = False


def download_emails():
    service = get_gmail_service()
    if not service:
        logging.error("Failed to get Gmail service.")
        return

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

    os.makedirs(SAVE_FOLDER, exist_ok=True)
    email_status = {}

    # Load existing email status
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE, "r") as f:
                email_status = json.load(f)
        except Exception as e:
            logging.error(f"Failed to load email status from {STATUS_FILE}: {e}")
            email_status = {}

    downloaded_ids = set()
    if os.path.exists(TRACKING_FILE):
        try:
            with open(TRACKING_FILE, "r") as f:
                downloaded_ids = set(f.read().splitlines())
        except Exception as e:
            logging.error(f"Failed to read tracking file: {e}")

    os.makedirs(SAVE_HTML_FOLDER, exist_ok=True)
    converted_ids = set()
    if os.path.exists(CONVERTED_TRACKING_FILE):
        try:
            with open(CONVERTED_TRACKING_FILE, "r") as f:
                converted_ids = set(f.read().splitlines())
        except Exception as e:
            logging.error(f"Failed to read converted tracking file: {e}")

    page_token = None
    while True:
        try:
            response = (
                service.users()
                .messages()
                .list(userId="me", labelIds=[label_id], pageToken=page_token)
                .execute()
            )
        except Exception as e:
            logging.error(f"Failed to list messages: {e}")
            break

        messages = response.get("messages", [])
        if not messages:
            logging.info("No messages found.")
            break

        for msg in messages:
            msg_id = msg["id"]
            if msg_id in downloaded_ids:
                logging.info(f"Message {msg_id} already downloaded, skipping.")
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
                    email_msg.get("Date", "NoDate").replace(" ", "_").replace(":", "-")
                )
                filename = f"{sanitize_filename(subject)}_{date}_{msg_id}.eml"
                filepath = os.path.join(SAVE_FOLDER, filename)
                with open(filepath, "wb") as f:
                    f.write(raw_email)
                downloaded_ids.add(msg_id)

                # Update email status
                email_status[filename] = {"downloaded": True, "converted": False}

                try:
                    with open(TRACKING_FILE, "a") as f:
                        f.write(f"{msg_id}\n")
                except Exception as e:
                    logging.error(f"Failed to write to tracking file: {e}")

                eml_to_html(filepath, email_status)

            except Exception as e:
                if "access_denied" in str(e):
                    logging.error(
                        "Access blocked: Gmail downloads has not completed the Google verification process. Please add zoheri@gmail.com as a test user in the Google Cloud Console."
                    )
                else:
                    logging.error(f"Failed to download {msg_id}: {e}")
                    # Update email status even if download fails
                    # email_status[filename] = {'downloaded': False, 'converted': False}

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    # Save email status
    try:
        with open(STATUS_FILE, "w") as f:
            json.dump(email_status, f, indent=4)
    except Exception as e:
        logging.error(f"Failed to save email status to {STATUS_FILE}: {e}")


def check_and_convert_emails():
    logging.info("Checking and converting emails...")

    # Load existing email status
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE, "r") as f:
                email_status = json.load(f)
        except Exception as e:
            logging.error(f"Failed to load email status from {STATUS_FILE}: {e}")
            return

        for filename, status in email_status.items():
            if status["downloaded"]:
                eml_file = os.path.join(SAVE_FOLDER, filename)
                if os.path.exists(eml_file):
                    logging.info(f"Converting {filename}...")
                    eml_to_html(eml_file, email_status)
                else:
                    logging.warning(f"EML file not found: {eml_file}")
            elif not status["downloaded"]:
                logging.warning(f"Email {filename} not downloaded.")
    else:
        logging.info("No email status file found.")

    # Save email status
    try:
        with open(STATUS_FILE, "w") as f:
            json.dump(email_status, f, indent=4)
    except Exception as e:
        logging.error(f"Failed to save email status to {STATUS_FILE}: {e}")


def final_check_and_convert():
    logging.info("Running final check and conversion...")
    email_status = {}
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE, "r") as f:
                email_status = json.load(f)
        except Exception as e:
            logging.error(f"Failed to load email status from {STATUS_FILE}: {e}")
            return

    for filename in os.listdir(SAVE_FOLDER):
        if filename.endswith(".eml"):
            eml_file = os.path.join(SAVE_FOLDER, filename)
            html_file = os.path.join(
                SAVE_HTML_FOLDER, os.path.splitext(filename)[0] + ".html"
            )

            if not os.path.exists(html_file):
                logging.info(f"HTML file missing for {filename}, converting...")

                if filename not in email_status:
                    email_status[filename] = {"downloaded": True, "converted": False}

                eml_to_html(eml_file, email_status)

    try:
        with open(STATUS_FILE, "w") as f:
            json.dump(email_status, f, indent=4)
    except Exception as e:
        logging.error(f"Failed to save email status to {STATUS_FILE}: {e}")


if __name__ == "__main__":
    download_emails()
    check_and_convert_emails()
    final_check_and_convert()
