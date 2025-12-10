#!/usr/bin/env python3
"""
Test Lex Fridman transcript page extraction
"""

import asyncio
import requests
from bs4 import BeautifulSoup

async def test_lex_fridman_extraction():
    """Test extracting transcript URLs from Lex Fridman archive"""

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    url = "https://lexfridman.com/category/transcripts/"

    print(f"🔍 Fetching: {url}")

    try:
        response = requests.get(url, headers=headers, timeout=15)
        print(f"📊 Status: {response.status_code}")

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            print("🔍 Looking for transcript links...")

            # Find all links that might be transcripts
            transcript_links = []

            # Look for various patterns
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')

                # Check if it's a transcript link
                if '/podcast/' in href:
                    full_url = f"https://lexfridman.com{href}" if href.startswith('/') else href
                    title = link.get_text().strip()

                    print(f"📄 Found transcript: {title}")
                    print(f"🔗 URL: {full_url}")
                    print()

                    transcript_links.append({
                        'title': title,
                        'url': full_url
                    })

            print(f"\n📊 Total transcript links found: {len(transcript_links)}")

            if transcript_links:
                print("\n🎯 First 5 transcripts:")
                for i, link in enumerate(transcript_links[:5]):
                    print(f"{i+1}. {link['title']}")
                    print(f"   {link['url']}")
                    print()
            else:
                print("❌ No transcript links found!")

                # Look at the page structure
                print("\n🔍 Analyzing page structure...")
                links = soup.find_all('a', href=True)[:10]
                for link in links:
                    href = link.get('href', '')
                    text = link.get_text().strip()[:50]
                    if text:
                        print(f"Link: {text} -> {href}")

        else:
            print(f"❌ Failed to fetch page: {response.status_code}")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_lex_fridman_extraction())