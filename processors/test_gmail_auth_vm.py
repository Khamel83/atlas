#!/usr/bin/env python3
"""
Simple Gmail authentication test for VM environment
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_gmail_auth():
    """Test Gmail authentication with proper VM handling"""
    print("🔐 Testing Gmail Authentication (VM Environment)")
    print("=" * 60)

    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()

    # Check Gmail configuration
    print("1. Checking Gmail configuration...")
    gmail_enabled = os.getenv('GMAIL_ENABLED', 'false').lower() == 'true'
    credentials_path = os.getenv('GMAIL_CREDENTIALS_PATH', 'config/gmail_credentials.json')
    token_path = os.getenv('GMAIL_TOKEN_PATH', 'data/gmail_token.json')
    email_address = os.getenv('GMAIL_EMAIL_ADDRESS')

    print(f"   Gmail Enabled: {gmail_enabled}")
    print(f"   Credentials Path: {credentials_path}")
    print(f"   Token Path: {token_path}")
    print(f"   Email Address: {email_address}")

    if not gmail_enabled:
        print("❌ Gmail is not enabled in .env")
        return False

    if not email_address:
        print("❌ Gmail email address not set in .env")
        return False

    # Check credentials file
    print(f"\n2. Checking credentials file...")
    if not os.path.exists(credentials_path):
        print(f"❌ Credentials file not found: {credentials_path}")
        return False

    try:
        import json
        with open(credentials_path, 'r') as f:
            credentials = json.load(f)

        client_id = credentials.get('web', {}).get('client_id')
        project_id = credentials.get('web', {}).get('project_id')

        print(f"   ✅ Credentials loaded")
        print(f"   ✅ Client ID: {client_id}")
        print(f"   ✅ Project ID: {project_id}")

    except Exception as e:
        print(f"❌ Error reading credentials: {e}")
        return False

    # Test authentication
    print(f"\n3. Testing Gmail authentication...")
    try:
        # Use Google OAuth directly for VM environment
        from google_auth_oauthlib.flow import Flow
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build

        # Check if we have existing token
        if os.path.exists(token_path):
            print("   📋 Found existing token file...")
            try:
                creds = Credentials.from_authorized_user_file(token_path, [
                    "https://www.googleapis.com/auth/gmail.readonly",
                    "https://www.googleapis.com/auth/gmail.modify"
                ])

                if creds.valid:
                    print("   ✅ Existing token is valid!")

                    # Test the credentials
                    service = build('gmail', 'v1', credentials=creds)
                    profile = service.users().getProfile(userId='me').execute()
                    print(f"   ✅ Authenticated as: {profile.get('emailAddress')}")
                    print(f"   ✅ Messages total: {profile.get('messagesTotal')}")

                    if profile.get('emailAddress') != email_address:
                        print(f"   ⚠️  Warning: Authenticated email ({profile.get('emailAddress')}) != configured email ({email_address})")

                    return True
                elif creds.expired and creds.refresh_token:
                    print("   🔄 Token expired, attempting refresh...")
                    creds.refresh(Request())

                    # Save refreshed token
                    with open(token_path, 'w') as token_file:
                        token_file.write(creds.to_json())

                    # Test refreshed credentials
                    service = build('gmail', 'v1', credentials=creds)
                    profile = service.users().getProfile(userId='me').execute()
                    print(f"   ✅ Token refreshed! Authenticated as: {profile.get('emailAddress')}")
                    return True
                else:
                    print("   ❌ Token is invalid and cannot be refreshed")
            except Exception as e:
                print(f"   ❌ Error with existing token: {e}")

        # Start new authentication flow
        print("   🔑 Starting new authentication flow...")

        # Create flow configuration
        flow_config = {
            "web": {
                "client_id": credentials['web']['client_id'],
                "client_secret": credentials['web']['client_secret'],
                "auth_uri": credentials['web']['auth_uri'],
                "token_uri": credentials['web']['token_uri'],
                "redirect_uris": ["http://localhost:8080/"]
            }
        }

        # Create flow
        flow = Flow.from_client_config(flow_config, [
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.modify"
        ])

        # For VM, we'll use manual auth code exchange
        flow.redirect_uri = "http://localhost:8080/"

        # Get authorization URL
        auth_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )

        print(f"\n📱 AUTHENTICATION REQUIRED")
        print("=" * 50)
        print(f"Visit this URL to authenticate:")
        print(f"\n{auth_url}\n")
        print("After authorizing, you'll be redirected to an error page.")
        print("Copy the ENTIRE URL from your browser's address bar")
        print("and paste it below.")
        print("\nNote: The 'localhost refused connection' error is expected.")
        print("=" * 50)

        # Get authorization code
        auth_code = input("\nEnter the full authorization URL (including the code parameter): ").strip()

        # Extract code from URL
        if "code=" in auth_code:
            code_start = auth_code.find("code=") + 5
            code_end = auth_code.find("&", code_start) if "&" in auth_code[code_start:] else len(auth_code)
            code = auth_code[code_start:code_end]

            print(f"   📄 Extracted authorization code")

            # Exchange code for token
            flow.fetch_token(code=code)

            # Save credentials
            creds = flow.credentials
            os.makedirs(os.path.dirname(token_path), exist_ok=True)
            with open(token_path, 'w') as token_file:
                token_file.write(creds.to_json())

            print("   ✅ Authentication successful!")

            # Test the authenticated service
            service = build('gmail', 'v1', credentials=creds)
            profile = service.users().getProfile(userId='me').execute()
            print(f"   ✅ Authenticated as: {profile.get('emailAddress')}")
            print(f"   ✅ Messages total: {profile.get('messagesTotal')}")

            if profile.get('emailAddress') != email_address:
                print(f"   ⚠️  Warning: Authenticated email ({profile.get('emailAddress')}) != configured email ({email_address})")

            return True
        else:
            print("   ❌ No authorization code found in URL")
            return False

    except Exception as e:
        print(f"❌ Authentication test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_gmail_auth()

    if success:
        print("\n🎉 GMAIL AUTHENTICATION SUCCESSFUL!")
        print("\n📧 Your Gmail integration is ready!")
        print("📧 Emails sent to your Atlas address will be processed automatically.")
    else:
        print("\n❌ GMAIL AUTHENTICATION FAILED")
        print("Please check the error messages above and fix any issues.")