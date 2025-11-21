#!/usr/bin/env python3
"""
Actually run the transcript extraction and show results
"""

import requests
import time
import random
from bs4 import BeautifulSoup
import sqlite3
from datetime import datetime
import json

class TranscriptExtractor:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })

    def extract_tyler_cowen_episode(self, episode_url):
        """Extract transcript from Tyler Cowen episode"""

        print(f"Extracting: {episode_url}")

        try:
            # Add delay to avoid rate limiting
            time.sleep(random.uniform(1, 3))

            response = self.session.get(episode_url, timeout=15)

            if response.status_code != 200:
                print(f"  ❌ HTTP {response.status_code}")
                return None

            soup = BeautifulSoup(response.content, 'html.parser')

            # Get episode title
            title_elem = soup.find('h1') or soup.find('title')
            title = title_elem.get_text(strip=True) if title_elem else "Unknown Episode"

            # Find transcript content
            all_text = soup.get_text(separator=' ', strip=True)

            if len(all_text) > 5000 and 'tyler' in all_text.lower():
                print(f"  ✅ Found transcript: {len(all_text)} chars")
                print(f"  Title: {title[:60]}...")
                return {
                    'title': title,
                    'url': episode_url,
                    'transcript': all_text,
                    'length': len(all_text)
                }
            else:
                print(f"  ❌ No valid transcript content")
                return None

        except Exception as e:
            print(f"  ❌ Error: {e}")
            return None

    def test_extraction(self):
        """Test on a few Tyler Cowen episodes"""

        test_urls = [
            "https://conversationswithtyler.com/episodes/seamus-murphy/",
            "https://conversationswithtyler.com/episodes/david-commins/",
            "https://conversationswithtyler.com/episodes/david-brooks-2/"
        ]

        results = []

        print("=== TESTING TRANSCRIPT EXTRACTION ===\n")

        for url in test_urls:
            result = self.extract_tyler_cowen_episode(url)
            if result:
                results.append(result)
            print()

        return results

    def store_in_database(self, results):
        """Store results in Atlas database"""

        if not results:
            print("No results to store")
            return

        try:
            conn = sqlite3.connect('data/atlas.db')
            cursor = conn.cursor()

            stored_count = 0

            for result in results:
                # Check if already exists
                existing = cursor.execute(
                    "SELECT id FROM content WHERE url = ?",
                    (result['url'],)
                ).fetchone()

                if existing:
                    # Update existing
                    cursor.execute("""
                        UPDATE content
                        SET content = ?,
                            content_type = 'podcast_transcript',
                            updated_at = ?,
                            metadata = ?
                        WHERE url = ?
                    """, (
                        result['transcript'],
                        datetime.now().isoformat(),
                        json.dumps({
                            'podcast_name': 'Conversations with Tyler',
                            'transcript_source': 'conversationswithtyler.com',
                            'character_count': result['length']
                        }),
                        result['url']
                    ))
                    print(f"✅ Updated existing: {result['title'][:50]}...")
                else:
                    # Insert new
                    cursor.execute("""
                        INSERT INTO content (
                            title, url, content, content_type,
                            created_at, updated_at, metadata, stage
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        f"[PODCAST] {result['title']}",
                        result['url'],
                        result['transcript'],
                        'podcast_transcript',
                        datetime.now().isoformat(),
                        datetime.now().isoformat(),
                        json.dumps({
                            'podcast_name': 'Conversations with Tyler',
                            'transcript_source': 'conversationswithtyler.com',
                            'character_count': result['length']
                        }),
                        400  # TRANSCRIPT_STORED
                    ))
                    print(f"✅ Inserted new: {result['title'][:50]}...")

                stored_count += 1

            conn.commit()
            conn.close()

            print(f"\n🎉 Successfully stored {stored_count} transcripts in database")

        except Exception as e:
            print(f"❌ Database error: {e}")

def main():
    extractor = TranscriptExtractor()

    # Test extraction
    results = extractor.test_extraction()

    if results:
        print(f"\n=== EXTRACTION SUMMARY ===")
        print(f"Successfully extracted: {len(results)} transcripts")

        for result in results:
            print(f"- {result['title'][:50]}... ({result['length']:,} chars)")

        # Store in database
        print(f"\n=== STORING IN DATABASE ===")
        extractor.store_in_database(results)

        # Verify storage
        print(f"\n=== VERIFICATION ===")
        try:
            conn = sqlite3.connect('data/atlas.db')
            cursor = conn.cursor()

            count = cursor.execute("""
                SELECT COUNT(*) FROM content
                WHERE content_type = 'podcast_transcript'
                AND JSON_EXTRACT(metadata, '$.podcast_name') = 'Conversations with Tyler'
            """).fetchone()[0]

            print(f"Tyler Cowen transcripts in database: {count}")
            conn.close()

        except Exception as e:
            print(f"Verification error: {e}")

    else:
        print("❌ No transcripts extracted")

if __name__ == "__main__":
    main()