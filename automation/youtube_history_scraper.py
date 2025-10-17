#!/usr/bin/env python3
"""
YouTube History Scraper - Automated Headless Browser
Extracts YouTube watch history, liked videos, and subscriptions
"""
import os
import json
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import requests
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class YouTubeVideo:
    """YouTube video data structure"""
    video_id: str
    title: str
    channel: str
    url: str
    watched_at: Optional[str] = None
    duration: Optional[str] = None
    description: Optional[str] = None
    view_count: Optional[str] = None

class YouTubeHistoryScraper:
    """Automated YouTube history scraper using headless browser"""

    def __init__(self, headless: bool = True, timeout: int = 30):
        self.headless = headless
        self.timeout = timeout
        self.driver = None
        self.wait = None
        self.videos: List[YouTubeVideo] = []

    def setup_driver(self) -> None:
        """Initialize Chrome webdriver with appropriate options"""
        chrome_options = Options()

        if self.headless:
            chrome_options.add_argument('--headless')

        # Standard Chrome options for automation
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--disable-features=VizDisplayCompositor')

        # User agent to avoid detection
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

        # Use unique profile directory to avoid conflicts
        import uuid
        profile_path = Path(f'/tmp/atlas_chrome_profile_{uuid.uuid4().hex[:8]}')
        profile_path.mkdir(parents=True, exist_ok=True)
        chrome_options.add_argument(f'--user-data-dir={profile_path}')
        chrome_options.add_argument('--disable-software-rasterizer')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--no-default-browser-check')
        chrome_options.add_argument('--disable-background-mode')
        chrome_options.add_argument('--disable-background-timer-throttling')
        chrome_options.add_argument('--disable-renderer-backgrounding')
        chrome_options.add_argument('--disable-features=TranslateUI')
        chrome_options.add_argument('--disable-ipc-flooding-protection')

        try:
            # Try system Chrome driver first
            import subprocess
            try:
                # Check if chromedriver is available in PATH
                result = subprocess.run(['which', 'chromedriver'], capture_output=True, text=True)
                if result.returncode == 0:
                    chromedriver_path = result.stdout.strip()
                    service = Service(executable_path=chromedriver_path)
                else:
                    # Fallback to ChromeDriverManager
                    service = Service(ChromeDriverManager().install())
            except:
                # Fallback to ChromeDriverManager
                service = Service(ChromeDriverManager().install())

            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.wait = WebDriverWait(self.driver, self.timeout)
            logger.info("Chrome webdriver initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize webdriver: {e}")
            # Try one more time with basic setup
            try:
                chrome_options.add_argument('--remote-debugging-port=9222')
                self.driver = webdriver.Chrome(options=chrome_options)
                self.wait = WebDriverWait(self.driver, self.timeout)
                logger.info("Chrome webdriver initialized with basic setup")
            except Exception as e2:
                logger.error(f"Basic setup also failed: {e2}")
                raise

    def login_to_google(self, email: str = None, interactive: bool = True) -> bool:
        """Login to Google account (interactive or with stored session)"""
        try:
            self.driver.get('https://accounts.google.com')
            time.sleep(3)

            # Check if already logged in
            try:
                profile_button = self.driver.find_element(By.CSS_SELECTOR, '[data-gb-analytics-id="TBHOnb"]')
                if profile_button:
                    logger.info("Already logged in to Google")
                    return True
            except NoSuchElementException:
                pass

            if interactive:
                logger.info("Please log in to Google in the browser window")
                logger.info("Waiting for login completion...")

                # Wait for successful login (profile button appears)
                try:
                    self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-gb-analytics-id="TBHOnb"]')))
                    logger.info("Successfully logged in to Google")
                    return True
                except TimeoutException:
                    logger.error("Login timeout - please try again")
                    return False
            else:
                logger.warning("Non-interactive login not implemented - session must exist")
                return False

        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False

    def navigate_to_youtube_history(self) -> bool:
        """Navigate to YouTube watch history"""
        try:
            logger.info("Navigating to YouTube history")
            self.driver.get('https://www.youtube.com/feed/history')
            time.sleep(5)

            # Check if we need to enable watch history
            try:
                enable_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Turn on')]")
                if enable_button:
                    logger.warning("Watch history is disabled. Please enable it manually.")
                    return False
            except NoSuchElementException:
                pass

            # Verify we're on the history page
            try:
                self.wait.until(EC.presence_of_element_located((By.ID, 'contents')))
                logger.info("Successfully navigated to YouTube history")
                return True
            except TimeoutException:
                logger.error("Failed to load YouTube history page")
                return False

        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return False

    def scrape_history_videos(self, max_videos: int = 1000, days_back: int = 30) -> List[YouTubeVideo]:
        """Scrape videos from YouTube history"""
        videos = []
        scroll_pause_time = 2
        last_height = self.driver.execute_script("return document.documentElement.scrollHeight")
        videos_scraped = 0

        logger.info(f"Starting to scrape up to {max_videos} videos from last {days_back} days")

        try:
            while videos_scraped < max_videos:
                # Find video elements
                video_elements = self.driver.find_elements(By.CSS_SELECTOR, 'div#dismissible')

                for element in video_elements[videos_scraped:]:
                    try:
                        # Extract video data
                        video_data = self._extract_video_data(element)
                        if video_data:
                            videos.append(video_data)
                            videos_scraped += 1

                            if videos_scraped % 50 == 0:
                                logger.info(f"Scraped {videos_scraped} videos...")

                            if videos_scraped >= max_videos:
                                break

                    except Exception as e:
                        logger.debug(f"Error extracting video data: {e}")
                        continue

                # Scroll down to load more videos
                self.driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
                time.sleep(scroll_pause_time)

                # Check if we've reached the end
                new_height = self.driver.execute_script("return document.documentElement.scrollHeight")
                if new_height == last_height:
                    logger.info("Reached end of history")
                    break
                last_height = new_height

        except KeyboardInterrupt:
            logger.info("Scraping interrupted by user")
        except Exception as e:
            logger.error(f"Error during scraping: {e}")

        logger.info(f"Scraped {len(videos)} videos total")
        return videos

    def _extract_video_data(self, element) -> Optional[YouTubeVideo]:
        """Extract data from a single video element"""
        try:
            # Video title and URL
            title_element = element.find_element(By.CSS_SELECTOR, 'a#video-title')
            title = title_element.get_attribute('title') or title_element.text
            url = title_element.get_attribute('href')

            if not url or 'watch?v=' not in url:
                return None

            video_id = url.split('watch?v=')[1].split('&')[0]

            # Channel name
            try:
                channel_element = element.find_element(By.CSS_SELECTOR, 'a.yt-simple-endpoint.style-scope.yt-formatted-string')
                channel = channel_element.text
            except:
                channel = "Unknown Channel"

            # Watch time (if available)
            watched_at = None
            try:
                time_element = element.find_element(By.CSS_SELECTOR, 'span.style-scope.ytd-video-meta-block')
                watched_at = time_element.text
            except:
                pass

            return YouTubeVideo(
                video_id=video_id,
                title=title,
                channel=channel,
                url=url,
                watched_at=watched_at
            )

        except Exception as e:
            logger.debug(f"Failed to extract video data: {e}")
            return None

    def save_to_atlas(self, videos: List[YouTubeVideo], atlas_url: str = "http://localhost:8000") -> bool:
        """Save scraped videos to Atlas"""
        try:
            logger.info(f"Saving {len(videos)} videos to Atlas...")

            for i, video in enumerate(videos):
                # Prepare content with embedded metadata
                content_with_metadata = f"""YouTube Video: {video.title}
Channel: {video.channel}
Video ID: {video.video_id}
Watched: {video.watched_at or 'Unknown'}
Platform: YouTube
Source: youtube-history-scraper

URL: {video.url}"""

                # Prepare data for Atlas (BookmarkletSave format)
                content_data = {
                    "title": video.title,
                    "url": video.url,
                    "content": content_with_metadata,
                    "content_type": "youtube_video"  # Critical: proper content type
                }

                # Send to Atlas
                response = requests.post(
                    f"{atlas_url}/api/v1/content/save",
                    json=content_data,
                    headers={"Content-Type": "application/json"}
                )

                if response.status_code == 200:
                    if (i + 1) % 100 == 0:
                        logger.info(f"Saved {i + 1} videos to Atlas...")
                else:
                    logger.warning(f"Failed to save video {video.title}: {response.status_code}")

            logger.info(f"Successfully saved {len(videos)} videos to Atlas")
            return True

        except Exception as e:
            logger.error(f"Failed to save to Atlas: {e}")
            return False

    def export_to_json(self, videos: List[YouTubeVideo], filename: str = None) -> str:
        """Export videos to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"youtube_history_{timestamp}.json"

        # Convert videos to dict for JSON serialization
        videos_data = [
            {
                "video_id": video.video_id,
                "title": video.title,
                "channel": video.channel,
                "url": video.url,
                "watched_at": video.watched_at,
                "duration": video.duration,
                "description": video.description,
                "view_count": video.view_count
            }
            for video in videos
        ]

        export_data = {
            "export_date": datetime.now().isoformat(),
            "total_videos": len(videos),
            "videos": videos_data
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Exported {len(videos)} videos to {filename}")
        return filename

    def close(self) -> None:
        """Close the webdriver"""
        if self.driver:
            self.driver.quit()
            logger.info("WebDriver closed")

def main():
    """Main function for command-line usage"""
    import argparse

    parser = argparse.ArgumentParser(description="YouTube History Scraper")
    parser.add_argument('--max-videos', type=int, default=1000, help='Maximum videos to scrape')
    parser.add_argument('--days-back', type=int, default=30, help='Days back to scrape')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    parser.add_argument('--atlas-url', default='http://localhost:8000', help='Atlas server URL')
    parser.add_argument('--export-only', action='store_true', help='Only export to JSON, do not save to Atlas')
    parser.add_argument('--interactive', action='store_true', help='Interactive login mode')

    args = parser.parse_args()

    scraper = YouTubeHistoryScraper(headless=args.headless)

    try:
        # Setup and login
        scraper.setup_driver()

        if not scraper.login_to_google(interactive=args.interactive):
            logger.error("Failed to login to Google")
            return

        # Navigate to YouTube history
        if not scraper.navigate_to_youtube_history():
            logger.error("Failed to navigate to YouTube history")
            return

        # Scrape videos
        videos = scraper.scrape_history_videos(
            max_videos=args.max_videos,
            days_back=args.days_back
        )

        if not videos:
            logger.warning("No videos found")
            return

        # Export to JSON
        json_file = scraper.export_to_json(videos)
        logger.info(f"Exported data to {json_file}")

        # Save to Atlas
        if not args.export_only:
            if scraper.save_to_atlas(videos, args.atlas_url):
                logger.info("Successfully saved all videos to Atlas")
            else:
                logger.error("Failed to save videos to Atlas")

    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        scraper.close()

if __name__ == "__main__":
    main()