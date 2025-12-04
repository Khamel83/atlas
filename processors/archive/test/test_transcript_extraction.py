#!/usr/bin/env python3
"""
Quick test of transcript extraction for Tyler Cowen
"""

import requests
from bs4 import BeautifulSoup

def test_tyler_cowen_extraction():
    """Test if we can extract Tyler Cowen transcript"""

    test_url = "https://conversationswithtyler.com/episodes/seamus-murphy/"

    print(f"Testing transcript extraction from: {test_url}")

    try:
        response = requests.get(test_url, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')

        # Try to find transcript content
        selectors = [
            '.transcript',
            '#transcript',
            '.episode-transcript',
            'article',
            '.content',
            '.entry-content',
            '.post-content',
            'main'
        ]

        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(separator=' ', strip=True)

                if len(text) > 1000:
                    print(f"✅ Found transcript using selector: {selector}")
                    print(f"Length: {len(text)} characters")
                    print(f"Preview: {text[:200]}...")
                    return True

        # Try getting all text as fallback
        all_text = soup.get_text(separator=' ', strip=True)
        if len(all_text) > 2000:
            print(f"✅ Found transcript using full page text")
            print(f"Length: {len(all_text)} characters")
            print(f"Preview: {all_text[:200]}...")
            return True

        print("❌ No transcript content found")
        return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_tyler_cowen_extraction()