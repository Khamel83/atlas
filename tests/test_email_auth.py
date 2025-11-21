#!/usr/bin/env python3
"""
Test script for Email Authentication Manager
"""

import sys
import os
from pathlib import Path

# Add the helpers directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.email_auth_manager import EmailAuthManager

def test_email_auth():
    """Test the EmailAuthManager"""
    print("Testing Email Authentication Manager...")

    # Initialize the auth manager
    auth_manager = EmailAuthManager()

    # Check if already authenticated
    if auth_manager.is_authenticated():
        print("Already authenticated!")
        service = auth_manager.get_service()
    else:
        print("Starting authentication flow...")
        try:
            service = auth_manager.authenticate()
            print("Authentication successful!")
        except Exception as e:
            print(f"Authentication failed: {e}")
            return False

    # Test the service
    try:
        profile = service.users().getProfile(userId='me').execute()
        print(f"Authenticated user: {profile['emailAddress']}")
        print("Service test successful!")
        return True
    except Exception as e:
        print(f"Service test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_email_auth()
    if success:
        print("All tests passed!")
    else:
        print("Some tests failed!")
        sys.exit(1)