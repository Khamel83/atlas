#!/usr/bin/env python3
"""Direct test of Lex Fridman transcript extraction"""

import requests
from bs4 import BeautifulSoup
import re
import sqlite3
import hashlib
from datetime import datetime
import os

# Ensure data directory exists
os.makedirs("data", exist_ok=True)

# Known recent Lex Fridman episodes to test
test_episodes = [
    "#480 – Dave Hone: T-Rex, Dinosaurs, Extinction, Evolution, and Jurassic Park",
    "#479 – Dave Plummer: Programming, Autism, and Old-School Microsoft Stories",
    "#478 – Charlie Wilson: Ukraine War, China, Iran, and Foreign Policy",
    "#477 – Jordan Peterson: The Poverty of Psychoanalysis",
    "#476 – Jan Leike: Scalable AI Alignment & Superalignment"
]

# Initialize database
def init_db():
    conn = sqlite3.connect("data/atlas.db")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS content (
            id TEXT PRIMARY KEY,
            title TEXT,
            content TEXT,
            content_type TEXT DEFAULT 'transcript',
            url TEXT,
            podcast_name TEXT,
            episode_title TEXT,
            created_date TEXT,
            processed INTEGER DEFAULT 1
        )
    """)
    return conn

def extract_lex_transcript(title):
    """Extract transcript using our proven pattern"""
    # Extract guest name
    guest_match = re.search(r'#\d+\s*[-–]\s*([^:]+)', title)
    if not guest_match:
        return None

    guest_name = guest_match.group(1).strip()
    # Create URL-friendly slug
    slug = re.sub(r'[^\w\s-]', '', guest_name.lower())
    slug = re.sub(r'[-\s]+', '-', slug).strip('-')

    transcript_url = f"https://lexfridman.com/{slug}-transcript"
    print(f"🔍 Trying: {transcript_url}")

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })

    try:
        response = session.get(transcript_url, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')

            # Try different content extraction methods
            content = None

            # Method 1: Look for transcript-specific elements
            transcript_div = soup.find('div', class_='transcript') or soup.find('div', {'id': 'transcript'})
            if transcript_div:
                content = transcript_div.get_text(strip=True)

            # Method 2: Look for main content
            if not content or len(content) < 5000:
                main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='content')
                if main_content:
                    content = main_content.get_text(strip=True)

            # Method 3: Get all text from body
            if not content or len(content) < 5000:
                content = soup.get_text(strip=True)

            # Validate content length
            if content and len(content) > 5000:
                print(f"✅ Found transcript: {len(content)} characters")
                return content, transcript_url
            else:
                print(f"❌ Content too short: {len(content) if content else 0} characters")

    except Exception as e:
        print(f"❌ Error: {e}")

    return None

def save_transcript(conn, title, content, url):
    """Save transcript to database"""
    content_id = hashlib.sha256(f"lex_{title}_{url}".encode()).hexdigest()[:16]

    conn.execute("""
        INSERT OR REPLACE INTO content (
            id, title, content, content_type, url, created_date, processed
        ) VALUES (?, ?, ?, 'transcript', ?, ?, 1)
    """, (
        content_id, f"Transcript: {title}", content, url,
        datetime.now().isoformat()
    ))
    conn.commit()
    print(f"💾 Saved to database with ID: {content_id}")

# Main execution
print("🚀 Direct Lex Fridman transcript test")
conn = init_db()
found_count = 0

for episode_title in test_episodes:
    print(f"\n🎯 Processing: {episode_title}")

    result = extract_lex_transcript(episode_title)
    if result:
        content, url = result
        save_transcript(conn, episode_title, content, url)
        found_count += 1
    else:
        print("   No transcript found")

conn.close()

print(f"\n📊 Results: Found {found_count} transcripts out of {len(test_episodes)} attempts")