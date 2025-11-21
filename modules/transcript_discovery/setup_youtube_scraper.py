#!/usr/bin/env python3
"""
YouTube History Scraper Setup

This script sets up and runs the YouTube history scraper for personal video collection.
It handles authentication, history navigation, and video data extraction.
"""

import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from automation.youtube_history_scraper import YouTubeHistoryScraper, YouTubeVideo

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('youtube_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def setup_youtube_scraper():
    """Set up and configure YouTube history scraper"""

    print("🎬 YouTube History Scraper Setup")
    print("=" * 50)

    # Initialize scraper
    scraper = YouTubeHistoryScraper(headless=False, timeout=60)

    try:
        # Setup browser
        print("\n📋 Setting up Chrome browser...")
        scraper.setup_driver()

        # Login to Google (interactive)
        print("\n🔐 Google Account Login Required")
        print("-" * 30)
        print("A browser window will open. Please:")
        print("1. Log in to your Google account")
        print("2. Complete any 2FA if required")
        print("3. Wait for confirmation message")
        print("\nNote: Login session will be saved for future runs")

        input("\nPress Enter when ready to open browser for login...")

        if not scraper.login_to_google(interactive=True):
            print("❌ Login failed!")
            return False

        print("✅ Login successful!")

        # Navigate to YouTube history
        print("\n📺 Navigating to YouTube history...")
        if not scraper.navigate_to_youtube_history():
            print("❌ Failed to navigate to YouTube history!")
            return False

        print("✅ Successfully accessed YouTube history!")

        # Test scrape a few videos
        print("\n🔍 Testing video extraction (first 10 videos)...")
        test_videos = scraper.scrape_history_videos(max_videos=10, days_back=7)

        if test_videos:
            print(f"✅ Successfully scraped {len(test_videos)} test videos!")
            print("\nSample videos:")
            for i, video in enumerate(test_videos[:3], 1):
                print(f"{i}. {video.title}")
                print(f"   Channel: {video.channel}")
                print(f"   URL: {video.url}")
                print(f"   Watched: {video.watched_at or 'Unknown'}")
                print()
        else:
            print("⚠️  No videos found in test scrape")

        # Save test results
        output_file = f"youtube_test_videos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        test_data = [
            {
                'video_id': v.video_id,
                'title': v.title,
                'channel': v.channel,
                'url': v.url,
                'watched_at': v.watched_at,
                'duration': v.duration,
                'description': v.description,
                'view_count': v.view_count
            }
            for v in test_videos
        ]

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(test_data, f, indent=2, ensure_ascii=False)

        print(f"📁 Test results saved to: {output_file}")

        # Close browser
        scraper.close_driver()

        print("\n🎉 Setup completed successfully!")
        print("\nNext steps:")
        print("1. Run the scraper regularly to collect your watched videos")
        print("2. Videos will be processed through the Atlas workflow system")
        print("3. Transcripts and content will be extracted automatically")

        return True

    except Exception as e:
        logger.error(f"Setup failed: {e}")
        if hasattr(scraper, 'driver') and scraper.driver:
            scraper.close_driver()
        return False

def run_youtube_collection(max_videos: int = 500, days_back: int = 30):
    """Run YouTube history collection"""

    print(f"\n🎬 Collecting YouTube History")
    print(f"Max videos: {max_videos}, Days back: {days_back}")

    scraper = YouTubeHistoryScraper(headless=True, timeout=60)

    try:
        scraper.setup_driver()

        # Try to use existing session
        if not scraper.login_to_google(interactive=False):
            print("❌ No active session found. Please run setup first.")
            return False

        if not scraper.navigate_to_youtube_history():
            print("❌ Failed to navigate to YouTube history")
            return False

        # Scrape videos
        videos = scraper.scrape_history_videos(max_videos=max_videos, days_back=days_back)

        if videos:
            print(f"✅ Collected {len(videos)} videos from your history")

            # Save results
            output_file = f"youtube_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            video_data = [
                {
                    'video_id': v.video_id,
                    'title': v.title,
                    'channel': v.channel,
                    'url': v.url,
                    'watched_at': v.watched_at,
                    'duration': v.duration,
                    'description': v.description,
                    'view_count': v.view_count,
                    'collected_at': datetime.now().isoformat()
                }
                for v in videos
            ]

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(video_data, f, indent=2, ensure_ascii=False)

            print(f"📁 Saved to: {output_file}")

            # NOTE: Atlas workflow integration not implemented due to YouTube limitations
            # - Requires browser authentication (doesn't work in headless environment)
            # - Chrome driver issues in server environment
            # - Cannot access user's actual watch history without GUI
            # See CLAUDE.md for details on YouTube integration limitations

            return True
        else:
            print("⚠️  No videos found")
            return False

    except Exception as e:
        logger.error(f"Collection failed: {e}")
        return False
    finally:
        if hasattr(scraper, 'driver') and scraper.driver:
            scraper.close_driver()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "collect":
        # Run collection
        max_videos = int(sys.argv[2]) if len(sys.argv) > 2 else 500
        days_back = int(sys.argv[3]) if len(sys.argv) > 3 else 30
        run_youtube_collection(max_videos, days_back)
    else:
        # Run setup
        setup_youtube_scraper()