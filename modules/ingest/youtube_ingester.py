"""
YouTube History Ingester - Import watch history from YouTube.

Requires YouTube Data API OAuth credentials:
- YOUTUBE_CLIENT_ID
- YOUTUBE_CLIENT_SECRET
- YOUTUBE_REFRESH_TOKEN

To get credentials:
1. Go to https://console.cloud.google.com/
2. Create a project (or use existing)
3. Enable YouTube Data API v3
4. Create OAuth 2.0 credentials (Desktop app)
5. Run: python -m modules.ingest.youtube_ingester --setup
"""

import os
import logging
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List

import requests

from modules.storage import FileStore, IndexManager, ContentItem, ContentType, SourceType
from modules.storage.content_types import ProcessingStatus
from modules.pipeline.content_pipeline import ContentPipeline, RateLimiter

logger = logging.getLogger(__name__)

# OAuth endpoints
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"

# Required scopes
SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
]


class YouTubeOAuth:
    """Handle YouTube OAuth authentication."""

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        refresh_token: Optional[str] = None,
    ):
        self.client_id = client_id or os.getenv("YOUTUBE_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("YOUTUBE_CLIENT_SECRET")
        self.refresh_token = refresh_token or os.getenv("YOUTUBE_REFRESH_TOKEN")
        self.access_token = None
        self.token_expiry = None

    def get_auth_url(self, redirect_uri: str = "urn:ietf:wg:oauth:2.0:oob") -> str:
        """Get the authorization URL for user consent."""
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(SCOPES),
            "access_type": "offline",
            "prompt": "consent",
        }
        return f"{GOOGLE_AUTH_URL}?" + "&".join(f"{k}={v}" for k, v in params.items())

    def exchange_code(self, code: str, redirect_uri: str = "urn:ietf:wg:oauth:2.0:oob") -> Dict[str, Any]:
        """Exchange authorization code for tokens."""
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }
        response = requests.post(GOOGLE_TOKEN_URL, data=data)
        response.raise_for_status()
        return response.json()

    def refresh_access_token(self) -> str:
        """Get a fresh access token using the refresh token."""
        if not self.refresh_token:
            raise ValueError("No refresh token available")

        # Check if current token is still valid
        if self.access_token and self.token_expiry:
            if datetime.utcnow() < self.token_expiry - timedelta(minutes=5):
                return self.access_token

        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token",
        }
        response = requests.post(GOOGLE_TOKEN_URL, data=data)
        response.raise_for_status()
        tokens = response.json()

        self.access_token = tokens["access_token"]
        self.token_expiry = datetime.utcnow() + timedelta(seconds=tokens.get("expires_in", 3600))

        return self.access_token

    def is_configured(self) -> bool:
        """Check if OAuth is properly configured."""
        return bool(self.client_id and self.client_secret and self.refresh_token)


class YouTubeIngester:
    """Ingest YouTube watch history."""

    def __init__(self):
        self.oauth = YouTubeOAuth()
        self.file_store = FileStore("data/content")
        self.index_manager = IndexManager("data/indexes/atlas_index.db")
        self.pipeline = ContentPipeline()
        self.rate_limiter = RateLimiter(min_delay=1.0, max_delay=2.0)

        self.stats = {
            "videos_found": 0,
            "videos_processed": 0,
            "duplicates_skipped": 0,
            "errors": 0,
        }

    def ingest_history(self, max_results: int = 50, since_days: int = 365) -> Dict[str, Any]:
        """
        Ingest YouTube watch history.

        Note: YouTube Data API doesn't provide watch history directly.
        We fetch liked videos and subscribed channels' recent videos instead.
        For full watch history, user needs to export via Google Takeout.
        """
        if not self.oauth.is_configured():
            logger.error("YouTube OAuth not configured")
            return self.stats

        try:
            access_token = self.oauth.refresh_access_token()
            headers = {"Authorization": f"Bearer {access_token}"}

            # Get liked videos
            self._process_liked_videos(headers, max_results)

            # Get videos from subscriptions
            self._process_subscriptions(headers, max_results)

        except Exception as e:
            logger.error(f"Error during YouTube ingestion: {e}")
            self.stats["errors"] += 1

        logger.info(f"YouTube ingestion complete: {self.stats}")
        return self.stats

    def _process_liked_videos(self, headers: Dict[str, str], max_results: int):
        """Process user's liked videos."""
        logger.info("Fetching liked videos...")

        url = f"{YOUTUBE_API_BASE}/videos"
        params = {
            "part": "snippet,contentDetails",
            "myRating": "like",
            "maxResults": min(max_results, 50),
        }

        try:
            self.rate_limiter.wait()
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            for item in data.get("items", []):
                self._process_video(item)

        except Exception as e:
            logger.error(f"Error fetching liked videos: {e}")
            self.stats["errors"] += 1

    def _process_subscriptions(self, headers: Dict[str, str], max_results: int):
        """Process recent videos from subscribed channels."""
        logger.info("Fetching subscription videos...")

        # First get subscriptions
        url = f"{YOUTUBE_API_BASE}/subscriptions"
        params = {
            "part": "snippet",
            "mine": "true",
            "maxResults": 20,
        }

        try:
            self.rate_limiter.wait()
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            for sub in data.get("items", [])[:10]:  # Limit to 10 channels
                channel_id = sub["snippet"]["resourceId"]["channelId"]
                self._process_channel_videos(headers, channel_id, max_results=5)

        except Exception as e:
            logger.error(f"Error fetching subscriptions: {e}")
            self.stats["errors"] += 1

    def _process_channel_videos(self, headers: Dict[str, str], channel_id: str, max_results: int):
        """Get recent videos from a channel."""
        url = f"{YOUTUBE_API_BASE}/search"
        params = {
            "part": "snippet",
            "channelId": channel_id,
            "order": "date",
            "type": "video",
            "maxResults": max_results,
        }

        try:
            self.rate_limiter.wait()
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            for item in data.get("items", []):
                # Get full video details
                video_id = item["id"]["videoId"]
                self._process_video_by_id(headers, video_id)

        except Exception as e:
            logger.error(f"Error fetching channel videos: {e}")

    def _process_video_by_id(self, headers: Dict[str, str], video_id: str):
        """Get and process a video by ID."""
        url = f"{YOUTUBE_API_BASE}/videos"
        params = {
            "part": "snippet,contentDetails",
            "id": video_id,
        }

        try:
            self.rate_limiter.wait()
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            for item in data.get("items", []):
                self._process_video(item)

        except Exception as e:
            logger.error(f"Error fetching video {video_id}: {e}")

    def _process_video(self, item: Dict[str, Any]):
        """Process a single video item."""
        self.stats["videos_found"] += 1

        video_id = item.get("id")
        if isinstance(video_id, dict):
            video_id = video_id.get("videoId")

        snippet = item.get("snippet", {})
        content_details = item.get("contentDetails", {})

        video_url = f"https://www.youtube.com/watch?v={video_id}"
        content_id = ContentItem.generate_id(source_url=video_url)

        # Check for duplicate
        if self.file_store.exists(content_id):
            self.stats["duplicates_skipped"] += 1
            return

        # Parse duration
        duration_seconds = None
        duration_str = content_details.get("duration", "")
        if duration_str:
            # ISO 8601 duration: PT#H#M#S
            import re
            match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration_str)
            if match:
                h, m, s = match.groups()
                duration_seconds = int(h or 0) * 3600 + int(m or 0) * 60 + int(s or 0)

        # Parse publish date
        published_at = None
        pub_str = snippet.get("publishedAt")
        if pub_str:
            try:
                published_at = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
            except Exception:
                pass

        item = ContentItem(
            content_id=content_id,
            content_type=ContentType.YOUTUBE,
            source_type=SourceType.YOUTUBE_HISTORY,
            title=snippet.get("title", "Untitled Video"),
            source_url=video_url,
            channel_name=snippet.get("channelTitle"),
            video_id=video_id,
            description=snippet.get("description", "")[:500],
            duration_seconds=duration_seconds,
            created_at=published_at or datetime.utcnow(),
            published_at=published_at,
            status=ProcessingStatus.PENDING,  # May need transcript fetching later
            extra={
                "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url"),
                "channel_id": snippet.get("channelId"),
            },
        )

        # Save to storage
        content = f"""# {item.title}

**Channel:** {item.channel_name}
**URL:** {video_url}
**Published:** {published_at.isoformat() if published_at else 'Unknown'}
**Duration:** {duration_seconds // 60}:{duration_seconds % 60:02d} min

## Description

{snippet.get('description', 'No description')}
"""

        item_dir = self.file_store.save(item, content=content)
        self.index_manager.index_item(item, str(item_dir), search_text=content)

        self.stats["videos_processed"] += 1
        logger.debug(f"Processed: {item.title[:50]}...")


def setup_oauth():
    """Interactive OAuth setup."""
    print("\n" + "=" * 60)
    print("YOUTUBE OAUTH SETUP")
    print("=" * 60)

    client_id = os.getenv("YOUTUBE_CLIENT_ID")
    client_secret = os.getenv("YOUTUBE_CLIENT_SECRET")

    if not client_id or not client_secret:
        print("\nYou need to set up Google Cloud credentials first:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create a project (or select existing)")
        print("3. Enable 'YouTube Data API v3'")
        print("4. Go to Credentials > Create Credentials > OAuth client ID")
        print("5. Select 'Desktop app'")
        print("6. Download the credentials")
        print("\nThen add to your secrets.env.encrypted:")
        print("  YOUTUBE_CLIENT_ID=your-client-id")
        print("  YOUTUBE_CLIENT_SECRET=your-client-secret")
        return

    oauth = YouTubeOAuth(client_id=client_id, client_secret=client_secret)

    print("\nOpen this URL in your browser:")
    print(oauth.get_auth_url())
    print("\nAfter authorizing, you'll get a code. Paste it here:")

    code = input("Authorization code: ").strip()

    try:
        tokens = oauth.exchange_code(code)
        refresh_token = tokens.get("refresh_token")

        if refresh_token:
            print("\nSuccess! Add this to your secrets.env.encrypted:")
            print(f"  YOUTUBE_REFRESH_TOKEN={refresh_token}")
        else:
            print("\nWarning: No refresh token received. You may need to revoke access and try again.")

    except Exception as e:
        print(f"\nError exchanging code: {e}")


def ingest_youtube():
    """CLI entry point."""
    import argparse
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    parser = argparse.ArgumentParser(description="Atlas YouTube Ingester")
    parser.add_argument("--setup", action="store_true", help="Run OAuth setup")
    parser.add_argument("--max-results", type=int, default=50, help="Max videos to fetch")
    parser.add_argument("--since-days", type=int, default=365, help="How far back to look")
    args = parser.parse_args()

    if args.setup:
        setup_oauth()
        return

    ingester = YouTubeIngester()
    stats = ingester.ingest_history(max_results=args.max_results, since_days=args.since_days)

    print("\n" + "=" * 50)
    print("YOUTUBE INGESTION COMPLETE")
    print("=" * 50)
    print(f"Videos found:       {stats['videos_found']}")
    print(f"Videos processed:   {stats['videos_processed']}")
    print(f"Duplicates skipped: {stats['duplicates_skipped']}")
    print(f"Errors:             {stats['errors']}")
    print("=" * 50)


if __name__ == "__main__":
    ingest_youtube()
