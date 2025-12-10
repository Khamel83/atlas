#!/usr/bin/env python3
"""
Test with easier transcript sources
"""

import requests
import sqlite3
from bs4 import BeautifulSoup
from datetime import datetime
import json

def test_lex_fridman():
    """Test with Lex Fridman - we know these work"""

    test_url = "https://lexfridman.com/elon-musk-and-neuralink-team-transcript"

    print(f"Testing Lex Fridman: {test_url}")

    try:
        response = requests.get(test_url, timeout=10)

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            # Get title
            title_elem = soup.find('h1') or soup.find('title')
            title = title_elem.get_text(strip=True) if title_elem else "Unknown"

            # Get transcript content
            all_text = soup.get_text(separator=' ', strip=True)

            print(f"✅ Successfully extracted!")
            print(f"Title: {title}")
            print(f"Length: {len(all_text):,} characters")
            print(f"Preview: {all_text[:150]}...")

            return {
                'title': title,
                'url': test_url,
                'transcript': all_text,
                'length': len(all_text)
            }

        else:
            print(f"❌ HTTP {response.status_code}")

    except Exception as e:
        print(f"❌ Error: {e}")

    return None

def test_npr_transcript():
    """Test with NPR - they usually have transcripts"""

    test_url = "https://www.npr.org/2024/01/15/1224794082/planet-money-indicator-economy"

    print(f"\nTesting NPR: {test_url}")

    try:
        response = requests.get(test_url, timeout=10)

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for transcript section
            transcript_div = soup.find('div', class_='transcript')
            if transcript_div:
                transcript_text = transcript_div.get_text(separator=' ', strip=True)

                title_elem = soup.find('h1')
                title = title_elem.get_text(strip=True) if title_elem else "NPR Episode"

                print(f"✅ Found NPR transcript!")
                print(f"Title: {title}")
                print(f"Length: {len(transcript_text):,} characters")

                return {
                    'title': title,
                    'url': test_url,
                    'transcript': transcript_text,
                    'length': len(transcript_text)
                }
            else:
                print("❌ No transcript section found")

        else:
            print(f"❌ HTTP {response.status_code}")

    except Exception as e:
        print(f"❌ Error: {e}")

    return None

def store_transcript(result):
    """Store result in database"""

    if not result:
        return False

    try:
        conn = sqlite3.connect('data/atlas.db')
        cursor = conn.cursor()

        # Check if exists
        existing = cursor.execute(
            "SELECT id FROM content WHERE url = ?",
            (result['url'],)
        ).fetchone()

        if existing:
            print(f"  📝 Updating existing entry")
            cursor.execute("""
                UPDATE content
                SET content = ?, content_type = 'podcast_transcript', updated_at = ?
                WHERE url = ?
            """, (result['transcript'], datetime.now().isoformat(), result['url']))
        else:
            print(f"  ➕ Creating new entry")
            cursor.execute("""
                INSERT INTO content (title, url, content, content_type, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                f"[PODCAST] {result['title']}",
                result['url'],
                result['transcript'],
                'podcast_transcript',
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))

        conn.commit()
        conn.close()

        print(f"  ✅ Stored in database!")
        return True

    except Exception as e:
        print(f"  ❌ Database error: {e}")
        return False

def main():
    print("=== TESTING EASY TRANSCRIPT SOURCES ===\n")

    # Test Lex Fridman
    lex_result = test_lex_fridman()
    if lex_result:
        store_transcript(lex_result)

    # Test NPR
    npr_result = test_npr_transcript()
    if npr_result:
        store_transcript(npr_result)

    # Check database
    print(f"\n=== DATABASE CHECK ===")
    try:
        conn = sqlite3.connect('data/atlas.db')
        cursor = conn.cursor()

        count = cursor.execute("""
            SELECT COUNT(*) FROM content
            WHERE content_type = 'podcast_transcript'
        """).fetchone()[0]

        print(f"Total podcast transcripts in database: {count}")

        # Show recent additions
        recent = cursor.execute("""
            SELECT title, url, LENGTH(content)
            FROM content
            WHERE content_type = 'podcast_transcript'
            ORDER BY updated_at DESC
            LIMIT 5
        """).fetchall()

        print(f"\nRecent transcripts:")
        for title, url, length in recent:
            print(f"  - {title[:50]}... ({length:,} chars)")

        conn.close()

    except Exception as e:
        print(f"Database check error: {e}")

if __name__ == "__main__":
    main()