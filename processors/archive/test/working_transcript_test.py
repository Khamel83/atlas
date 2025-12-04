#!/usr/bin/env python3
"""
Quick test of working transcript finder
"""

import requests
import sqlite3
from bs4 import BeautifulSoup
import os

def extract_transcript_from_url(url):
    """Extract transcript from URL"""
    try:
        response = requests.get(url, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')

        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header']):
            element.decompose()

        text = soup.get_text()
        lines = [line.strip() for line in text.split('\n') if line.strip() and len(line.strip()) > 10]
        clean_text = ' '.join(lines)

        # Check if it looks like a transcript
        if len(clean_text) > 1000 and ':' in clean_text:
            return clean_text[:15000]
        return None
    except Exception as e:
        print(f"Error extracting: {e}")
        return None

def test_transcript_finder():
    """Test finding and extracting transcripts"""

    # Test Tavily search
    tavily_key = "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"

    url = "https://api.tavily.com/search"
    payload = {
        "api_key": tavily_key,
        "query": "lex fridman donald trump transcript",
        "max_results": 3
    }

    print("🔍 Testing Tavily search...")
    response = requests.post(url, json=payload, timeout=15)
    data = response.json()

    print(f"📊 Found {len(data.get('results', []))} results")

    for i, result in enumerate(data.get('results', [])[:2]):
        url = result['url']
        title = result['title']

        print(f"\n📄 {i+1}. {title[:60]}...")
        print(f"🔗 {url}")

        # Try to extract transcript
        transcript = extract_transcript_from_url(url)
        if transcript:
            print(f"✅ SUCCESS! Extracted {len(transcript)} characters")

            # Save to database
            conn = sqlite3.connect("podcast_processing.db")
            conn.execute("""
                UPDATE episodes
                SET processing_status = 'completed',
                    transcript_found = 1,
                    transcript_text = ?,
                    transcript_source = 'tavily_extraction',
                    transcript_url = ?,
                    last_attempt = CURRENT_TIMESTAMP
                WHERE id = (SELECT id FROM episodes WHERE title LIKE '%Lex Fridman%' AND title LIKE '%Trump%' LIMIT 1)
            """, (transcript, url))
            conn.commit()
            conn.close()

            print("💾 Saved to database")
            return True
        else:
            print("❌ Could not extract transcript")

    return False

if __name__ == "__main__":
    test_transcript_finder()