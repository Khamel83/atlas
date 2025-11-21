#!/usr/bin/env python3
"""
Debug Tyler Cowen page structure
"""

import requests
from bs4 import BeautifulSoup

def debug_page_structure():
    url = "https://conversationswithtyler.com/episodes/seamus-murphy/"

    try:
        response = requests.get(url, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')

        print("=== PAGE TITLE ===")
        title = soup.find('title')
        if title:
            print(title.get_text())

        print("\n=== MAIN CONTENT AREAS ===")
        for tag in ['main', 'article', '.content', '.post', '.entry']:
            elements = soup.select(tag) if tag.startswith('.') else soup.find_all(tag)
            if elements:
                print(f"{tag}: {len(elements)} found")
                for i, elem in enumerate(elements[:2]):
                    text = elem.get_text(strip=True)[:100]
                    print(f"  {i+1}: {text}...")

        print("\n=== LOOKING FOR 'TRANSCRIPT' TEXT ===")
        page_text = soup.get_text().lower()
        if 'transcript' in page_text:
            print("✅ Page contains the word 'transcript'")

            # Find elements containing 'transcript'
            for elem in soup.find_all(text=lambda text: text and 'transcript' in text.lower()):
                parent = elem.parent
                print(f"Found 'transcript' in: {parent.name} - {elem.strip()[:100]}")
        else:
            print("❌ Page does not contain 'transcript'")

        print("\n=== ALL DIV CLASSES ===")
        divs = soup.find_all('div', class_=True)
        classes = set()
        for div in divs:
            for cls in div.get('class', []):
                classes.add(cls)

        for cls in sorted(classes)[:20]:
            print(f"  .{cls}")

        print(f"\n=== TOTAL PAGE TEXT LENGTH ===")
        all_text = soup.get_text(strip=True)
        print(f"Total text: {len(all_text)} characters")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_page_structure()