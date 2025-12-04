#!/usr/bin/env python3
"""
Test Gmail IMAP authentication
"""

import os
import imaplib
import email
from dotenv import load_dotenv
import ssl

def test_gmail_imap():
    """Test Gmail IMAP connection and authentication"""
    print("🔧 Testing Gmail IMAP Authentication")
    print("=" * 50)

    # Load environment variables
    load_dotenv()

    # Get configuration
    email_address = os.getenv('GMAIL_EMAIL_ADDRESS')
    app_password = os.getenv('GMAIL_APP_PASSWORD')
    imap_host = os.getenv('GMAIL_IMAP_HOST', 'imap.gmail.com')
    imap_port = int(os.getenv('GMAIL_IMAP_PORT', 993))
    folder = os.getenv('GMAIL_FOLDER', 'INBOX')

    print(f"Email Address: {email_address}")
    print(f"IMAP Host: {imap_host}")
    print(f"IMAP Port: {imap_port}")
    print(f"Folder: {folder}")

    if not email_address:
        print("❌ GMAIL_EMAIL_ADDRESS not set in .env")
        return False

    if app_password == 'YOUR_16_CHARACTER_APP_PASSWORD_HERE' or not app_password:
        print("❌ Please set your Gmail app password in .env")
        print("   Go to: https://myaccount.google.com/apppasswords")
        print("   Generate an app password for 'Mail' -> 'Atlas Gmail'")
        return False

    print(f"\n🔑 Testing IMAP connection...")

    try:
        # Create SSL context
        context = ssl.create_default_context()

        # Connect to Gmail IMAP server
        print(f"   Connecting to {imap_host}:{imap_port}...")
        mail = imaplib.IMAP4_SSL(imap_host, imap_port, ssl_context=context)

        # Login
        print(f"   Authenticating as {email_address}...")
        mail.login(email_address, app_password)
        print("   ✅ Authentication successful!")

        # Select folder
        print(f"   Selecting folder: {folder}...")
        status, messages = mail.select(folder)
        if status == 'OK':
            print(f"   ✅ Folder selected successfully")
            print(f"   📧 Total messages in {folder}: {messages[0].decode('utf-8')}")

            # Search for recent emails
            print(f"   🔍 Searching for recent emails...")
            status, email_ids = mail.search(None, 'ALL')
            if status == 'OK':
                email_ids = email_ids[0].split()
                print(f"   ✅ Found {len(email_ids)} emails")

                if len(email_ids) > 0:
                    # Get latest email
                    latest_email_id = email_ids[-1]
                    status, msg_data = mail.fetch(latest_email_id, '(RFC822)')

                    if status == 'OK':
                        # Parse email
                        raw_email = msg_data[0][1]
                        msg = email.message_from_bytes(raw_email)

                        # Get email details
                        subject = msg.get('Subject', 'No Subject')
                        from_addr = msg.get('From', 'No From')
                        date = msg.get('Date', 'No Date')

                        print(f"   📄 Latest email:")
                        print(f"      From: {from_addr}")
                        print(f"      Subject: {subject}")
                        print(f"      Date: {date}")

            # Logout
            mail.logout()
            print("   ✅ Logged out successfully")

            print(f"\n🎉 GMAIL IMAP AUTHENTICATION SUCCESSFUL!")
            print(f"📧 Your Gmail integration is ready!")
            return True

        else:
            print(f"   ❌ Failed to select folder {folder}")
            return False

    except imaplib.IMAP4.error as e:
        print(f"   ❌ IMAP error: {e}")
        if "Invalid credentials" in str(e) or "Authentication failed" in str(e):
            print(f"   💡 Check your app password - it should be 16 characters")
        return False
    except Exception as e:
        print(f"   ❌ Connection error: {e}")
        return False

if __name__ == "__main__":
    success = test_gmail_imap()

    if not success:
        print(f"\n🔧 TROUBLESHOOTING:")
        print(f"1. Make sure 2-Step Verification is enabled on your Google Account")
        print(f"2. Generate a new app password: https://myaccount.google.com/apppasswords")
        print(f"3. Select 'Mail' -> 'Other (Custom name)' -> 'Atlas Gmail'")
        print(f"4. Copy the 16-character password (without spaces)")
        print(f"5. Update GMAIL_APP_PASSWORD in your .env file")