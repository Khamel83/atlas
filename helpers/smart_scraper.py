#!/usr/bin/env python3
"""
Smart Scraper that bypasses bot detection
"""

import requests
import time
import random
from bs4 import BeautifulSoup
from urllib.parse import urljoin

class SmartScraper:
    """Scraper with bot detection avoidance"""

    def __init__(self):
        self.session = requests.Session()

        # Rotate between multiple realistic user agents
        self.user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15'
        ]

        self._setup_session()

    def _setup_session(self):
        """Setup session with realistic headers"""
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })

    def get_page(self, url, retries=3):
        """Get page with bot detection avoidance"""

        for attempt in range(retries):
            try:
                # Rotate user agent
                self.session.headers['User-Agent'] = random.choice(self.user_agents)

                # Add random delay
                time.sleep(random.uniform(1, 3))

                # Make request
                response = self.session.get(url, timeout=15)

                if response.status_code == 200:
                    return response

                elif response.status_code == 403:
                    print(f"403 Forbidden on attempt {attempt + 1}, trying different approach...")

                    # Try with referrer
                    self.session.headers['Referer'] = 'https://www.google.com/'
                    time.sleep(random.uniform(2, 5))

                    response = self.session.get(url, timeout=15)
                    if response.status_code == 200:
                        return response

            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                time.sleep(random.uniform(2, 5))

        return None

def test_smart_scraper():
    """Test the smart scraper on Tyler Cowen"""

    scraper = SmartScraper()
    url = "https://conversationswithtyler.com/episodes/seamus-murphy/"

    print(f"Testing smart scraper on: {url}")

    response = scraper.get_page(url)

    if response:
        soup = BeautifulSoup(response.content, 'html.parser')

        # Get all text
        all_text = soup.get_text(strip=True)
        print(f"✅ Successfully retrieved page!")
        print(f"Page length: {len(all_text)} characters")

        if 'transcript' in all_text.lower():
            print("✅ Page contains transcript content")

            # Try to find transcript section
            for elem in soup.find_all(text=lambda text: text and 'full transcript' in text.lower()):
                parent = elem.parent
                print(f"Found transcript section in: {parent.name}")

                # Look for content after "Read full transcript"
                next_elements = parent.find_next_siblings()
                for next_elem in next_elements[:3]:
                    text = next_elem.get_text(strip=True)
                    if len(text) > 500:
                        print(f"Found transcript content: {len(text)} characters")
                        print(f"Preview: {text[:200]}...")
                        return True

        else:
            print("❌ No transcript content found")

    else:
        print("❌ Failed to retrieve page")

    return False

if __name__ == "__main__":
    test_smart_scraper()