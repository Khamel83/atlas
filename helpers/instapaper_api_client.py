import json
import os
from typing import Any, Dict, List

import requests
from requests_oauthlib import OAuth1Session


class InstapaperAPIClient:
    BASE_URL = "https://www.instapaper.com/api/1/"

    def __init__(self, consumer_key: str, consumer_secret: str):
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.oauth = None

    def authenticate(self, username: str, password: str) -> bool:
        """
        Authenticates with Instapaper using xAuth to obtain an access token.
        """
        url = self.BASE_URL + "oauth/access_token"

        # OAuth1Session for xAuth
        oauth_session = OAuth1Session(
            self.consumer_key,
            client_secret=self.consumer_secret,
            resource_owner_key=username,  # xAuth uses username as resource_owner_key
            resource_owner_secret=password,  # xAuth uses password as resource_owner_secret
        )

        try:
            response = oauth_session.post(url)
            response.raise_for_status()  # Raise an exception for HTTP errors

            # Parse the response to get the access token and secret
            # The response is typically in the format "oauth_token=xxx&oauth_token_secret=yyy"
            params = dict(item.split("=") for item in response.text.split("&"))

            access_token = params.get("oauth_token")
            access_token_secret = params.get("oauth_token_secret")

            if access_token and access_token_secret:
                self.oauth = OAuth1Session(
                    self.consumer_key,
                    client_secret=self.consumer_secret,
                    resource_owner_key=access_token,
                    resource_owner_secret=access_token_secret,
                )
                return True
            else:
                print(
                    f"Authentication failed: Missing tokens in response. Response: {response.text}"
                )
                return False
        except requests.exceptions.RequestException as e:
            print(f"Authentication failed: {e}")
            return False

    def list_bookmarks(
        self, limit: int = 25, folder: str = "unread"
    ) -> List[Dict[str, Any]]:
        """
        Lists bookmarks from Instapaper.

        Args:
            limit: The maximum number of bookmarks to return (default 25, max 500).
            folder: The folder to retrieve bookmarks from (e.g., "unread", "archive", "starred").

        Returns:
            A list of dictionaries, each representing a bookmark.
        """
        if not self.oauth:
            print("Not authenticated. Please call authenticate() first.")
            return []

        url = self.BASE_URL + "bookmarks/list"
        params = {
            "limit": min(limit, 500),  # Instapaper API limit is 500
            "folder": folder,
        }

        try:
            response = self.oauth.post(url, data=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Failed to list bookmarks: {e}")
            return []
        except json.JSONDecodeError:
            print(f"Failed to decode JSON response: {response.text}")
            return []


# Example Usage (for testing purposes, not part of the main application flow)
if __name__ == "__main__":
    # Replace with your actual consumer key, secret, username, and password
    # These should ideally come from environment variables or a config file
    CONSUMER_KEY = os.environ.get("INSTAPAPER_CONSUMER_KEY", "YOUR_CONSUMER_KEY")
    CONSUMER_SECRET = os.environ.get(
        "INSTAPAPER_CONSUMER_SECRET", "YOUR_CONSUMER_SECRET"
    )
    INSTAPAPER_USERNAME = os.environ.get(
        "INSTAPAPER_USERNAME", "YOUR_INSTAPAPER_USERNAME"
    )
    INSTAPAPER_PASSWORD = os.environ.get(
        "INSTAPAPER_PASSWORD", "YOUR_INSTAPAPER_PASSWORD"
    )

    client = InstapaperAPIClient(CONSUMER_KEY, CONSUMER_SECRET)

    if client.authenticate(INSTAPAPER_USERNAME, INSTAPAPER_PASSWORD):
        print("Authentication successful!")
        bookmarks = client.list_bookmarks(limit=5)
        if bookmarks:
            print(f"Found {len(bookmarks)} bookmarks:")
            for bookmark in bookmarks:
                print(f"- Title: {bookmark.get('title')}, URL: {bookmark.get('url')}")
        else:
            print("No bookmarks found or an error occurred.")
    else:
        print("Authentication failed.")
