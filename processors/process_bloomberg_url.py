#!/usr/bin/env python3
"""
Process specific Bloomberg URL provided by user
"""

import os
import requests
from bs4 import BeautifulSoup
import sqlite3
from datetime import datetime

def process_bloomberg_url(url):
    """Extract and analyze the Bloomberg article"""

    print("📰 Processing Bloomberg URL")
    print("=" * 50)
    print(f"🔗 URL: {url}")
    print()

    try:
        # Fetch the content
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        print(f"✅ Successfully fetched page (Status: {response.status_code})")
        print(f"📏 Content length: {len(response.content):,} bytes")
        print()

        # Parse the HTML
        soup = BeautifulSoup(response.content, 'html.parser')

        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe', 'form']):
            element.decompose()

        # Extract title
        title_elem = soup.find('title') or soup.find('h1')
        title = title_elem.get_text().strip() if title_elem else "Unknown Title"

        # Extract main content
        content = soup.get_text()

        # Clean up text
        lines = [line.strip() for line in content.split('\n') if line.strip() and len(line.strip()) > 10]
        clean_content = '\n'.join(lines)

        print(f"📄 Title: {title}")
        print(f"📏 Clean content length: {len(clean_content):,} characters")
        print(f"📝 Estimated words: {len(clean_content.split()):,}")

        # Extract key topics
        text_lower = clean_content.lower()
        topics = []
        keywords = ['apple', 'iphone', 'mac', 'tesla', 'carplay', 'roadmap', 'pro', 'air']

        for keyword in keywords:
            if keyword in text_lower:
                count = text_lower.count(keyword)
                topics.append(f"{keyword} ({count})")

        if topics:
            print(f"🏷️  Key topics: {', '.join(topics)}")

        # Save to database as a special entry
        conn = sqlite3.connect("podcast_processing.db")

        # Check if this URL already exists
        cursor = conn.execute("SELECT id FROM episodes WHERE link = ?", (url,))
        existing = cursor.fetchone()

        if existing:
            print(f"⚠️  URL already exists in database (ID: {existing[0]})")
        else:
            # Insert as a special episode
            cursor = conn.execute("""
                INSERT INTO episodes (title, link, podcast_id, processing_status, transcript_found, transcript_text, transcript_source, quality_score)
                VALUES (?, ?, 1, 'completed', 1, ?, ?, 8)
            """, (title, url, clean_content, "bloomberg_manual_processing"))

            episode_id = cursor.lastrowid
            conn.commit()
            print(f"✅ Saved to database as episode ID: {episode_id}")

        conn.close()

        # Show preview of content
        print(f"\n📖 Content Preview:")
        print("-" * 30)
        preview = clean_content[:500]
        print(preview + "..." if len(clean_content) > 500 else preview)
        print("-" * 30)

        return clean_content

    except Exception as e:
        print(f"❌ Error processing Bloomberg URL: {e}")
        return None

if __name__ == "__main__":
    url = "https://www.bloomberg.com/news/newsletters/2025-11-16/apple-s-iphone-road-map-iphone-air-2-iphone-18-mac-pro-future-tesla-carplay-mi1q4l2o?srnd=undefined"
    process_bloomberg_url(url)