#!/usr/bin/env python3
"""
Fix Gmail authentication by using proper redirect URI
"""

import os
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def create_fixed_auth():
    """Create authentication flow with proper redirect URI"""
    print("🔧 Fixing Gmail Authentication")
    print("=" * 50)

    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()

    # Check configuration
    credentials_path = os.getenv('GMAIL_CREDENTIALS_PATH', 'config/gmail_credentials.json')
    token_path = os.getenv('GMAIL_TOKEN_PATH', 'data/gmail_token.json')
    email_address = os.getenv('GMAIL_EMAIL_ADDRESS')

    print(f"Email Address: {email_address}")
    print(f"Credentials Path: {credentials_path}")

    # Load credentials
    try:
        with open(credentials_path, 'r') as f:
            credentials = json.load(f)
    except Exception as e:
        print(f"❌ Error loading credentials: {e}")
        return False

    # Try multiple common redirect URIs
    redirect_uris = [
        "http://localhost:8080/",
        "http://localhost:8000/",
        "http://localhost:5000/",
        "http://localhost:3000/",
        "http://localhost:9000/",
        "http://127.0.0.1:8080/",
        "http://127.0.0.1:8000/",
        "urn:ietf:wg:oauth:2.0:oob"  # Special out-of-band URI for manual copy
    ]

    print(f"\n🔍 Testing redirect URIs...")

    for redirect_uri in redirect_uris:
        print(f"\nTrying redirect URI: {redirect_uri}")

        try:
            from google_auth_oauthlib.flow import Flow

            # Create flow configuration
            flow_config = {
                "web": {
                    "client_id": credentials['web']['client_id'],
                    "client_secret": credentials['web']['client_secret'],
                    "auth_uri": credentials['web']['auth_uri'],
                    "token_uri": credentials['web']['token_uri'],
                    "redirect_uris": [redirect_uri]
                }
            }

            # Create flow
            flow = Flow.from_client_config(flow_config, [
                "https://www.googleapis.com/auth/gmail.readonly",
                "https://www.googleapis.com/auth/gmail.modify"
            ])

            flow.redirect_uri = redirect_uri

            # Get authorization URL
            auth_url, state = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent'
            )

            print(f"✅ Successfully created auth URL for: {redirect_uri}")

            if "urn:ietf:wg:oauth:2.0:oob" in redirect_uri:
                print(f"\n📱 USE THIS AUTHENTICATION METHOD")
                print("=" * 50)
                print(f"Visit this URL to authenticate:")
                print(f"\n{auth_url}\n")
                print("After authorizing, you'll get a code.")
                print("Copy that code and paste it below.")
                print("=" * 50)

                # Get authorization code
                auth_code = input("\nEnter the authorization code: ").strip()

                if auth_code:
                    try:
                        flow.fetch_token(code=auth_code)

                        # Save credentials
                        os.makedirs(os.path.dirname(token_path), exist_ok=True)
                        with open(token_path, 'w') as token_file:
                            token_file.write(flow.credentials.to_json())

                        # Test the authenticated service
                        from googleapiclient.discovery import build
                        service = build('gmail', 'v1', credentials=flow.credentials)
                        profile = service.users().getProfile(userId='me').execute()
                        print(f"✅ Authentication successful!")
                        print(f"✅ Authenticated as: {profile.get('emailAddress')}")
                        print(f"✅ Messages total: {profile.get('messagesTotal')}")

                        if profile.get('emailAddress') != email_address:
                            print(f"⚠️  Warning: Authenticated email ({profile.get('emailAddress')}) != configured email ({email_address})")

                        return True
                    except Exception as e:
                        print(f"❌ Error exchanging code: {e}")
                        continue
            else:
                print(f"\n📱 AUTHENTICATION REQUIRED")
                print("=" * 50)
                print(f"Visit this URL to authenticate:")
                print(f"\n{auth_url}\n")
                print("After authorizing, copy the full redirect URL")
                print("and paste it below.")
                print("=" * 50)

                # Get authorization URL from user
                auth_code = input("\nEnter the full redirect URL: ").strip()

                if "code=" in auth_code:
                    try:
                        code_start = auth_code.find("code=") + 5
                        code_end = auth_code.find("&", code_start) if "&" in auth_code[code_start:] else len(auth_url)
                        code = auth_code[code_start:code_end]

                        flow.fetch_token(code=code)

                        # Save credentials
                        os.makedirs(os.path.dirname(token_path), exist_ok=True)
                        with open(token_path, 'w') as token_file:
                            token_file.write(flow.credentials.to_json())

                        # Test the authenticated service
                        from googleapiclient.discovery import build
                        service = build('gmail', 'v1', credentials=flow.credentials)
                        profile = service.users().getProfile(userId='me').execute()
                        print(f"✅ Authentication successful!")
                        print(f"✅ Authenticated as: {profile.get('emailAddress')}")

                        if profile.get('emailAddress') != email_address:
                            print(f"⚠️  Warning: Authenticated email ({profile.get('emailAddress')}) != configured email ({email_address})")

                        return True
                    except Exception as e:
                        print(f"❌ Error exchanging code: {e}")
                        continue

        except Exception as e:
            print(f"❌ Error with {redirect_uri}: {e}")
            continue

    print(f"\n❌ All redirect URIs failed")
    print(f"\n🔧 SOLUTION: Update Google Cloud Console")
    print(f"You need to add one of these redirect URIs to your Google Cloud Console:")
    for uri in redirect_uris:
        print(f"  - {uri}")
    print(f"\nGo to: https://console.cloud.google.com/apis/credentials")
    print(f"Find your OAuth 2.0 Client ID and add the redirect URI")

    return False

if __name__ == "__main__":
    success = create_fixed_auth()
    if success:
        print("\n🎉 GMAIL AUTHENTICATION SUCCESSFUL!")
    else:
        print("\n❌ GMAIL AUTHENTICATION FAILED")
        print("Please update your Google Cloud Console redirect URIs as shown above.")