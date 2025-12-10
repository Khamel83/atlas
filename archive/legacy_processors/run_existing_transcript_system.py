#!/usr/bin/env python3
"""
Use the existing transcript source system that's already built
"""

import json
import requests
from bs4 import BeautifulSoup
import sqlite3
from datetime import datetime

def load_podcast_sources():
    """Load existing podcast sources"""
    with open('config/podcast_sources_cache.json', 'r') as f:
        return json.load(f)

def extract_transcript_from_url(url, network_config=None):
    """Extract transcript using existing network configurations"""

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers, timeout=15)

        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.content, 'html.parser')

        # Use network-specific selectors if available
        if network_config and 'selectors' in network_config:
            for selector in network_config['selectors']:
                element = soup.select_one(selector)
                if element:
                    text = element.get_text(separator=' ', strip=True)
                    min_length = network_config.get('min_length', 1000)
                    if len(text) > min_length:
                        return text

        # Try generic transcript selectors
        selectors = [
            '.transcript',
            '#transcript',
            '.episode-transcript',
            '.full-text',
            'article',
            '.content',
            '.entry-content',
            '.post-content'
        ]

        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(separator=' ', strip=True)
                if len(text) > 1000 and 'transcript' in text.lower():
                    return text

        # Final fallback - all text
        all_text = soup.get_text(separator=' ', strip=True)
        if len(all_text) > 2000:
            return all_text

    except Exception as e:
        print(f"Error extracting from {url}: {e}")

    return None

def process_podcast_sources():
    """Process all podcast sources and extract transcripts"""

    sources = load_podcast_sources()

    results = []

    for podcast_key, podcast_data in sources.items():

        podcast_name = podcast_key.split('_')[0]

        print(f"\n=== Processing: {podcast_name} ===")

        # Get sample links to test
        sample_links = podcast_data.get('sample_links', [])
        network_config = podcast_data.get('config', {})

        if not sample_links:
            print(f"  ❌ No sample links for {podcast_name}")
            continue

        # Test first few sample links
        for i, episode_url in enumerate(sample_links[:3]):

            print(f"  Testing episode {i+1}: {episode_url}")

            transcript = extract_transcript_from_url(episode_url, network_config)

            if transcript:
                print(f"    ✅ Found transcript: {len(transcript):,} characters")

                result = {
                    'podcast_name': podcast_name,
                    'episode_url': episode_url,
                    'transcript': transcript,
                    'character_count': len(transcript)
                }

                results.append(result)

                # Store in database
                store_transcript_in_db(result)

                break  # Found one working, move to next podcast

            else:
                print(f"    ❌ No transcript found")

        if not results or results[-1]['podcast_name'] != podcast_name:
            print(f"  ❌ No working transcripts found for {podcast_name}")

    return results

def store_transcript_in_db(result):
    """Store transcript in Atlas database"""

    try:
        conn = sqlite3.connect('data/atlas.db')
        cursor = conn.cursor()

        # Check if exists
        existing = cursor.execute(
            "SELECT id FROM content WHERE url = ?",
            (result['episode_url'],)
        ).fetchone()

        if existing:
            # Update
            cursor.execute("""
                UPDATE content
                SET content = ?, content_type = 'podcast_transcript', updated_at = ?
                WHERE url = ?
            """, (result['transcript'], datetime.now().isoformat(), result['episode_url']))
            print(f"    📝 Updated existing entry")
        else:
            # Insert
            cursor.execute("""
                INSERT INTO content (title, url, content, content_type, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                f"[PODCAST] {result['podcast_name']} Episode",
                result['episode_url'],
                result['transcript'],
                'podcast_transcript',
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            print(f"    ➕ Added new entry")

        conn.commit()
        conn.close()

    except Exception as e:
        print(f"    ❌ Database error: {e}")

def main():
    """Run the existing transcript system"""

    print("RUNNING EXISTING TRANSCRIPT SOURCE SYSTEM")
    print("=" * 50)

    results = process_podcast_sources()

    print(f"\n{'='*50}")
    print("RESULTS SUMMARY")
    print(f"{'='*50}")

    if results:
        print(f"Successfully extracted {len(results)} transcripts:")

        for result in results:
            print(f"✅ {result['podcast_name']}: {result['character_count']:,} chars")

        # Check database
        try:
            conn = sqlite3.connect('data/atlas.db')
            cursor = conn.cursor()

            total_transcripts = cursor.execute("""
                SELECT COUNT(*) FROM content WHERE content_type = 'podcast_transcript'
            """).fetchone()[0]

            print(f"\nTotal transcripts in database: {total_transcripts}")
            conn.close()

        except Exception as e:
            print(f"Database check error: {e}")

    else:
        print("❌ No transcripts extracted")

if __name__ == "__main__":
    main()