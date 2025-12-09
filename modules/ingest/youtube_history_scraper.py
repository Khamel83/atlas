"""
YouTube Watch History Scraper - Uses yt-dlp to pull complete watch history.

yt-dlp with cookies can pull the full YouTube watch history feed.
This is much more reliable than browser automation.

Usage:
    # Scrape all history
    python -m modules.ingest.youtube_history_scraper --scrape

    # Scrape last N days only
    python -m modules.ingest.youtube_history_scraper --scrape --days 7

    # Scrape max N videos
    python -m modules.ingest.youtube_history_scraper --scrape --max 100
"""

import os
import re
import json
import logging
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
    TRANSCRIPTS_AVAILABLE = True
except ImportError:
    TRANSCRIPTS_AVAILABLE = False

from modules.storage import FileStore, IndexManager, ContentItem, ContentType, SourceType
from modules.storage.content_types import ProcessingStatus

logger = logging.getLogger(__name__)

COOKIES_JSON_PATH = Path("data/youtube_cookies.json")
COOKIES_TXT_PATH = Path("data/youtube_cookies.txt")
HISTORY_URL = "https://www.youtube.com/feed/history"


def convert_cookies_to_netscape():
    """Convert JSON cookies to Netscape format for yt-dlp."""
    if not COOKIES_JSON_PATH.exists():
        logger.error(f"No cookies file at {COOKIES_JSON_PATH}")
        return False

    with open(COOKIES_JSON_PATH, "r") as f:
        cookies = json.load(f)

    lines = ["# Netscape HTTP Cookie File"]
    for c in cookies:
        domain = c.get("domain", "")
        flag = "TRUE" if domain.startswith(".") else "FALSE"
        path = c.get("path", "/")
        secure = "TRUE" if c.get("secure", False) else "FALSE"
        expiry = str(int(c.get("expirationDate", 0)))
        name = c.get("name", "")
        value = c.get("value", "")
        lines.append(f"{domain}\t{flag}\t{path}\t{secure}\t{expiry}\t{name}\t{value}")

    with open(COOKIES_TXT_PATH, "w") as f:
        f.write("\n".join(lines))

    logger.info(f"Converted {len(cookies)} cookies to Netscape format")
    return True


class YouTubeHistoryScraper:
    """Scrape YouTube watch history using yt-dlp."""

    def __init__(self):
        self.file_store = FileStore("data/content")
        self.index_manager = IndexManager("data/indexes/atlas_index.db")
        self.stats = {
            "videos_found": 0,
            "videos_saved": 0,
            "transcripts_fetched": 0,
            "duplicates_skipped": 0,
            "errors": 0,
        }

    def scrape_history(
        self, max_videos: int = 500, since_days: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Scrape watch history using yt-dlp.

        Args:
            max_videos: Maximum videos to scrape
            since_days: Only get videos from last N days (None = all)
        """
        # Ensure cookies are in Netscape format
        if not COOKIES_TXT_PATH.exists() or (
            COOKIES_JSON_PATH.exists()
            and COOKIES_JSON_PATH.stat().st_mtime > COOKIES_TXT_PATH.stat().st_mtime
        ):
            if not convert_cookies_to_netscape():
                return self.stats

        logger.info("Starting YouTube history scrape with yt-dlp...")

        # Use yt-dlp to get video list
        cmd = [
            ".venv/bin/yt-dlp",
            "--cookies",
            str(COOKIES_TXT_PATH),
            "--flat-playlist",
            "--print",
            "%(id)s\t%(title)s\t%(channel)s\t%(upload_date)s",
            HISTORY_URL,
        ]

        if max_videos:
            cmd.extend(["--playlist-end", str(max_videos)])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            if result.returncode != 0:
                logger.error(f"yt-dlp error: {result.stderr}")
                self.stats["errors"] += 1
                return self.stats

            # Parse output
            videos = []
            cutoff_date = None
            if since_days:
                cutoff_date = datetime.now() - timedelta(days=since_days)

            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue

                parts = line.split("\t")
                if len(parts) < 2:
                    continue

                video_id = parts[0]
                title = parts[1] if len(parts) > 1 else ""
                channel = parts[2] if len(parts) > 2 else "Unknown"
                upload_date_str = parts[3] if len(parts) > 3 else None

                # Parse upload date if available
                upload_date = None
                if upload_date_str and upload_date_str != "NA":
                    try:
                        upload_date = datetime.strptime(upload_date_str, "%Y%m%d")
                    except:
                        pass

                videos.append(
                    {
                        "video_id": video_id,
                        "title": title,
                        "channel": channel,
                        "upload_date": upload_date,
                        "url": f"https://www.youtube.com/watch?v={video_id}",
                    }
                )
                self.stats["videos_found"] += 1

            logger.info(f"Found {len(videos)} videos from yt-dlp")

            # Process videos
            for video in videos:
                self._save_video(video)

        except subprocess.TimeoutExpired:
            logger.error("yt-dlp timed out")
            self.stats["errors"] += 1
        except Exception as e:
            logger.error(f"Error running yt-dlp: {e}")
            self.stats["errors"] += 1

        logger.info(f"Scraping complete: {self.stats}")
        return self.stats

    def _get_transcript(self, video_id: str) -> Optional[str]:
        """Fetch transcript for a video using youtube-transcript-api."""
        if not TRANSCRIPTS_AVAILABLE:
            return None

        try:
            api = YouTubeTranscriptApi()
            transcript = api.fetch(video_id)
            # Combine all transcript segments
            full_text = " ".join([seg.text for seg in transcript])
            return full_text
        except (TranscriptsDisabled, NoTranscriptFound):
            logger.debug(f"No transcript available for {video_id}")
            return None
        except Exception as e:
            logger.debug(f"Error fetching transcript for {video_id}: {e}")
            return None

    def _save_video(self, video: Dict[str, Any]):
        """Save a video to storage with transcript if available."""
        content_id = ContentItem.generate_id(source_url=video["url"])

        # Check duplicate
        if self.file_store.exists(content_id):
            self.stats["duplicates_skipped"] += 1
            return

        # Try to get transcript (with rate limiting)
        time.sleep(0.5)  # Small delay between transcript requests
        transcript = self._get_transcript(video["video_id"])
        has_transcript = transcript is not None

        watched_date = video.get("upload_date") or datetime.now()

        item = ContentItem(
            content_id=content_id,
            content_type=ContentType.YOUTUBE,
            source_type=SourceType.YOUTUBE_HISTORY,
            title=video["title"],
            source_url=video["url"],
            channel_name=video["channel"],
            video_id=video["video_id"],
            created_at=watched_date,
            status=ProcessingStatus.COMPLETED if has_transcript else ProcessingStatus.PENDING,
            extra={
                "scraped_at": datetime.now().isoformat(),
                "source": "yt-dlp",
                "has_transcript": has_transcript,
            },
        )

        if has_transcript:
            content = f"""# {video["title"]}

**Channel:** {video["channel"]}
**URL:** {video["url"]}
**Video ID:** {video["video_id"]}

---

## Transcript

{transcript}
"""
        else:
            content = f"""# {video["title"]}

**Channel:** {video["channel"]}
**URL:** {video["url"]}
**Video ID:** {video["video_id"]}

---

*No transcript available for this video*
"""

        item_dir = self.file_store.save(item, content=content)
        self.index_manager.index_item(item, str(item_dir), search_text=content)

        self.stats["videos_saved"] += 1
        if has_transcript:
            self.stats["transcripts_fetched"] += 1
        logger.debug(f"Saved: {video['title'][:50]}... (transcript: {has_transcript})")


def main():
    """CLI entry point."""
    import argparse
    import logging

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    parser = argparse.ArgumentParser(description="YouTube History Scraper")
    parser.add_argument(
        "--scrape", action="store_true", help="Scrape history using saved cookies"
    )
    parser.add_argument("--max", type=int, default=500, help="Max videos to scrape")
    parser.add_argument("--days", type=int, help="Only get videos from last N days")
    args = parser.parse_args()

    scraper = YouTubeHistoryScraper()

    if args.scrape:
        stats = scraper.scrape_history(max_videos=args.max, since_days=args.days)

        print("\n" + "=" * 50)
        print("YOUTUBE HISTORY SCRAPE COMPLETE")
        print("=" * 50)
        print(f"Videos found:       {stats['videos_found']}")
        print(f"Videos saved:       {stats['videos_saved']}")
        print(f"Transcripts:        {stats.get('transcripts_fetched', 0)}")
        print(f"Duplicates skipped: {stats['duplicates_skipped']}")
        print(f"Errors:             {stats['errors']}")
        print("=" * 50)
    else:
        parser.print_help()
        print("\nRun: python -m modules.ingest.youtube_history_scraper --scrape")


if __name__ == "__main__":
    main()
