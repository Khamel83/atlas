#!/usr/bin/env python3
"""
Email Authentication Manager for Atlas

This module handles Gmail API OAuth2 authentication flow,
secure credential storage, token refresh and validation.
"""

import os
import json
import logging
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Scopes required for Gmail API access
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

class EmailAuthManager:
    """Manages Gmail API authentication for Atlas"""

    def __init__(self, credentials_file='credentials.json', token_file='token.json'):
        """
        Initialize the EmailAuthManager

        Args:
            credentials_file (str): Path to the credentials JSON file
            token_file (str): Path to the token JSON file
        """
        self.credentials_file = Path(credentials_file)
        self.token_file = Path(token_file)
        self.creds = None
        self.service = None

    def authenticate(self):
        """
        Set up Gmail API OAuth2 authentication flow

        Returns:
            googleapiclient.discovery.Resource: Authenticated Gmail service
        """
        # Load existing credentials
        if self.token_file.exists():
            self.creds = Credentials.from_authorized_user_file(str(self.token_file), SCOPES)

        # If there are no (valid) credentials available, let the user log in
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                # Refresh expired credentials
                self.creds.refresh(Request())
            else:
                # Run OAuth2 flow
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_file), SCOPES)
                self.creds = flow.run_local_server(port=0)

            # Save the credentials for the next run
            with open(self.token_file, 'w') as token:
                token.write(self.creds.to_json())

        # Build the Gmail service
        self.service = build('gmail', 'v1', credentials=self.creds)
        return self.service

    def refresh_token(self):
        """
        Refresh the authentication token if expired

        Returns:
            bool: True if token was refreshed, False otherwise
        """
        if self.creds and self.creds.expired and self.creds.refresh_token:
            try:
                self.creds.refresh(Request())
                # Save the refreshed credentials
                with open(self.token_file, 'w') as token:
                    token.write(self.creds.to_json())
                return True
            except Exception as e:
                logging.error(f"Failed to refresh token: {e}")
                return False
        return False

    def is_authenticated(self):
        """
        Check if we have valid authentication credentials

        Returns:
            bool: True if authenticated, False otherwise
        """
        return self.creds is not None and self.creds.valid

    def get_service(self):
        """
        Get the authenticated Gmail service

        Returns:
            googleapiclient.discovery.Resource: Authenticated Gmail service
        """
        if not self.is_authenticated():
            self.authenticate()
        return self.service

    def store_credentials(self, credentials_path):
        """
        Store credentials in Atlas environment securely

        Args:
            credentials_path (str): Path to store credentials
        """
        # In a real implementation, we would:
        # 1. Encrypt the credentials
        # 2. Store them in a secure location
        # 3. Set appropriate file permissions
        pass

    def validate_token(self):
        """
        Validate the current authentication token

        Returns:
            bool: True if token is valid, False otherwise
        """
        if not self.creds:
            return False

        try:
            # Test the credentials by making a simple API call
            service = build('gmail', 'v1', credentials=self.creds)
            service.users().getProfile(userId='me').execute()
            return True
        except Exception as e:
            logging.error(f"Token validation failed: {e}")
            return False

def main():
    """Example usage of EmailAuthManager"""
    auth_manager = EmailAuthManager()

    try:
        service = auth_manager.authenticate()
        print("Authentication successful!")

        # Test the service
        profile = service.users().getProfile(userId='me').execute()
        print(f"Authenticated user: {profile['emailAddress']}")

    except Exception as e:
        print(f"Authentication failed: {e}")

if __name__ == "__main__":
    main()