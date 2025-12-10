#!/usr/bin/env python3
"""
Simple YouTube Authentication and History Collection

This script will help you log into YouTube and collect your watch history.
"""

import sys
import os
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleYouTubeAuth:
    def __init__(self):
        self.driver = None
        self.wait = None

    def setup_driver(self):
        """Setup Chrome driver with user-friendly options"""
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # Use regular browser (not headless) so user can interact
        service = Service(ChromeDriverManager().install())

        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.wait = WebDriverWait(self.driver, 30)

        logger.info("Chrome driver setup complete")

    def login_to_youtube(self):
        """Guide user through YouTube login process"""
        print("🎬 YouTube Authentication")
        print("=" * 40)
        print()
        print("🌐 Browser opening... Please follow these steps:")
        print("1. Log into your Google account when prompted")
        print("2. Go to YouTube")
        print("3. Navigate to your History page (click on Menu > History)")
        print("4. Once you can see your watch history, press Enter here")
        print()

        # Go to YouTube
        self.driver.get("https://www.youtube.com")

        # Wait for user to complete login
        input("Press Enter after you've logged in and can see your YouTube history...")

        print("✅ Login complete!")

    def get_recently_watched(self, max_videos=10):
        """Extract recently watched videos from current page"""
        videos = []

        try:
            # Wait for video elements to load
            video_elements = self.wait.until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "ytd-video-renderer"))
            )

            print(f"📺 Found {len(video_elements)} videos on page")

            for i, video in enumerate(video_elements[:max_videos]):
                try:
                    # Extract video information
                    title_element = video.find_element(By.CSS_SELECTOR, "#video-title")
                    channel_element = video.find_element(By.CSS_SELECTOR, "#channel-name .yt-formatted-string")

                    title = title_element.get_attribute("title") or title_element.text
                    channel = channel_element.text
                    url = title_element.get_attribute("href")

                    if title and url:
                        videos.append({
                            'title': title,
                            'channel': channel,
                            'url': url,
                            'watched_at': 'Just now'  # Since we're looking at current history
                        })

                        print(f"{i+1}. {title}")
                        print(f"   Channel: {channel}")
                        print(f"   URL: {url}")
                        print()

                except Exception as e:
                    logger.warning(f"Error extracting video {i}: {e}")
                    continue

        except TimeoutException:
            print("❌ Timeout waiting for videos to load")
        except Exception as e:
            print(f"❌ Error getting videos: {e}")

        return videos

    def cleanup(self):
        """Clean up resources"""
        if self.driver:
            self.driver.quit()

def main():
    """Main authentication and collection process"""
    auth = SimpleYouTubeAuth()

    try:
        # Setup browser
        auth.setup_driver()

        # Guide user through login
        auth.login_to_youtube()

        # Collect recently watched videos
        print("🔍 Extracting your recently watched videos...")
        videos = auth.get_recently_watched()

        if videos:
            print(f"🎉 Successfully collected {len(videos)} recently watched videos!")
            print()
            print("📋 Summary:")
            for i, video in enumerate(videos, 1):
                print(f"{i}. {video['title']} - {video['channel']}")
                print(f"   {video['url']}")
        else:
            print("❌ No videos found")

    except Exception as e:
        print(f"❌ Error: {e}")
        logger.error(f"Authentication failed: {e}")
    finally:
        auth.cleanup()

if __name__ == "__main__":
    main()