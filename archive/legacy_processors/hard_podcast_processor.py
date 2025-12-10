#!/usr/bin/env python3
"""
Hard Podcast Transcript Finder
Focuses on the difficult podcasts that need real transcript extraction
"""

import sqlite3
import requests
import time
from datetime import datetime
import re
from urllib.parse import quote

def find_this_american_life_transcript(episode_title, episode_url):
    """Find This American Life transcript"""
    print(f"🎭 Finding This American Life transcript: {episode_title}")

    # Method 1: Official This American Life website
    if episode_url:
        episode_num = re.search(r'/(\d+)', episode_url)
        if episode_num:
            official_url = f"https://www.thisamericanlife.org/{episode_num.group(1)}/transcript"
            try:
                response = requests.get(official_url, timeout=15)
                if response.status_code == 200:
                    # Extract transcript content
                    content = response.text

                    # Look for transcript content
                    transcript_match = re.search(r'<div[^>]*class="[^"]*transcript[^"]*"[^>]*>(.*?)</div>', content, re.DOTALL | re.IGNORECASE)
                    if transcript_match:
                        transcript = transcript_match.group(1)
                        # Clean HTML
                        transcript = re.sub(r'<[^>]+>', '\n', transcript)
                        transcript = re.sub(r'\n+', '\n', transcript).strip()

                        if len(transcript) > 500:
                            return {
                                "source": "official",
                                "url": official_url,
                                "content": f"# {episode_title}\n\n**Source**: {official_url}\n\n{transcript}",
                                "method": "official_transcript"
                            }
            except Exception as e:
                print(f"Official transcript failed: {e}")

    # Method 2: Search for transcript
    search_terms = f"This American Life {episode_title} transcript"
    search_urls = [
        f"https://www.google.com/search?q={quote(search_terms)}",
        f"https://duckduckgo.com/?q={quote(search_terms)}",
    ]

    for search_url in search_urls:
        try:
            response = requests.get(search_url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })

            if response.status_code == 200:
                # Look for transcript links in search results
                transcript_links = re.findall(r'https?://[^\s<>"\']+(?:transcript|thisamericanlife)[^\s<>"\']*', response.text, re.IGNORECASE)

                for link in transcript_links[:3]:  # Try first 3 links
                    try:
                        transcript_response = requests.get(link, timeout=10)
                        if transcript_response.status_code == 200 and len(transcript_response.text) > 1000:
                            return {
                                "source": "search",
                                "url": link,
                                "content": f"# {episode_title}\n\n**Transcript Source**: {link}\n\n{transcript_response.text[:5000]}",
                                "method": "search_transcript"
                            }
                    except:
                        continue
        except:
            continue

    return None

def find_99_percent_invisible_transcript(episode_title, episode_url):
    """Find 99% Invisible transcript"""
    print(f"🏛️ Finding 99% Invisible transcript: {episode_title}")

    # Method 1: Official 99% Invisible website
    if episode_url:
        # Convert episode URL to transcript URL
        slug = re.search(r'/([^/]+)(?:/)?$', episode_url)
        if slug:
            official_url = f"https://99percentinvisible.org/episode/{slug.group(1)}/transcript/"
            try:
                response = requests.get(official_url, timeout=15)
                if response.status_code == 200:
                    content = response.text

                    # Extract transcript content
                    transcript_match = re.search(r'<div[^>]*class="[^"]*transcript-content[^"]*"[^>]*>(.*?)</div>', content, re.DOTALL | re.IGNORECASE)
                    if not transcript_match:
                        transcript_match = re.search(r'<article[^>]*>(.*?)</article>', content, re.DOTALL | re.IGNORECASE)

                    if transcript_match:
                        transcript = transcript_match.group(1)
                        transcript = re.sub(r'<[^>]+>', '\n', transcript)
                        transcript = re.sub(r'\n+', '\n', transcript).strip()

                        if len(transcript) > 500:
                            return {
                                "source": "official",
                                "url": official_url,
                                "content": f"# {episode_title}\n\n**Source**: {official_url}\n\n{transcript}",
                                "method": "official_transcript"
                            }
            except Exception as e:
                print(f"Official transcript failed: {e}")

    # Method 2: Search for transcript
    search_terms = f"99% Invisible {episode_title} transcript"
    search_urls = [
        f"https://www.google.com/search?q={quote(search_terms)}",
        f"https://duckduckgo.com/?q={quote(search_terms)}",
    ]

    for search_url in search_urls:
        try:
            response = requests.get(search_url, timeout=10)
            if response.status_code == 200:
                # Look for transcript links
                transcript_links = re.findall(r'https?://[^\s<>"\']*(?:99percentinvisible|transcript)[^\s<>"\']*', response.text, re.IGNORECASE)

                for link in transcript_links[:3]:
                    try:
                        transcript_response = requests.get(link, timeout=10)
                        if transcript_response.status_code == 200 and len(transcript_response.text) > 1000:
                            return {
                                "source": "search",
                                "url": link,
                                "content": f"# {episode_title}\n\n**Transcript Source**: {link}\n\n{transcript_response.text[:5000]}",
                                "method": "search_transcript"
                            }
                    except:
                        continue
        except:
            continue

    return None

def find_hard_fork_transcript(episode_title, episode_url):
    """Find Hard Fork transcript"""
    print(f"⚡ Finding Hard Fork transcript: {episode_title}")

    # Hard Fork is from New York Times/Decoder - they have transcripts
    search_terms = f"Hard Fork {episode_title} transcript"

    # Try specific transcript sources
    transcript_sources = [
        f"https://www.nytimes.com/2024/01/01/podcasts/hard-fork-{episode_title.lower().replace(' ', '-')}-transcript.html",
        f"https://decoder.fm/episode/{episode_title.lower().replace(' ', '-')}/transcript",
    ]

    # Add general search
    search_urls = [
        f"https://www.google.com/search?q={quote(search_terms)}",
    ]

    all_urls = transcript_sources + search_urls

    for url in all_urls:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200 and len(response.text) > 1000:
                return {
                    "source": "search",
                    "url": url,
                    "content": f"# {episode_title}\n\n**Transcript Source**: {url}\n\n{response.text[:5000]}",
                    "method": "search_transcript"
                }
        except:
            continue

    return None

def process_hard_podcasts(batch_size=5):
    """Process only the hard podcasts - not Acquired"""
    print(f"🎯 Processing {batch_size} HARD PODCASTS at {datetime.now()}")
    print("Focusing on: This American Life, 99% Invisible, Hard Fork")
    print("IGNORING: Acquired (easy transcripts), Documents (already processed)")

    conn = sqlite3.connect("/home/ubuntu/dev/atlas/atlas_v2/data/atlas_v2.db")
    cursor = conn.cursor()

    # Get ONLY the hard podcasts
    cursor.execute('''
        SELECT content_id, source_url, source_name, metadata_json
        FROM processing_queue
        WHERE status = 'pending'
        AND source_name IN ('This American Life', '99% Invisible', 'Hard Fork')
        LIMIT ?
    ''', (batch_size,))

    items = cursor.fetchall()
    print(f"Found {len(items)} HARD PODCASTS to process")

    if len(items) == 0:
        print("❌ No hard podcasts found in queue!")
        conn.close()
        return 0

    processed_count = 0

    for content_id, source_url, source_name, metadata_json in items:
        try:
            # Parse metadata
            try:
                import json
                metadata = json.loads(metadata_json)
            except:
                metadata = eval(metadata_json)

            title = metadata.get('title', content_id)
            print(f"\n🎯 Processing HARD PODCAST: {content_id} ({source_name}) - {title}")

            # Update status
            cursor.execute('''
                UPDATE processing_queue
                SET status = 'processing', updated_at = ?
                WHERE content_id = ?
            ''', (datetime.now().isoformat(), content_id))

            extracted_content = None

            # Find transcript based on podcast
            if source_name == 'This American Life':
                extracted_content = find_this_american_life_transcript(title, source_url)
            elif source_name == '99% Invisible':
                extracted_content = find_99_percent_invisible_transcript(title, source_url)
            elif source_name == 'Hard Fork':
                extracted_content = find_hard_fork_transcript(title, source_url)

            if extracted_content:
                # Save content
                output_dir = Path("/home/ubuntu/dev/atlas/atlas_v2/content/transcripts")
                output_dir.mkdir(parents=True, exist_ok=True)

                filename = f"{source_name.replace(' ', '_').lower()}_{content_id}.md"
                output_file = output_dir / filename

                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(extracted_content['content'])

                # Update database
                metadata.update(extracted_content)
                metadata['processed_at'] = datetime.now().isoformat()

                cursor.execute('''
                    INSERT OR REPLACE INTO content_metadata
                    (content_id, source_url, source_name, content_type, title, metadata_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    content_id, source_url, source_name, 'podcast_transcript',
                    title, json.dumps(metadata),
                    datetime.now().isoformat(), datetime.now().isoformat()
                ))

                print(f"✅ HARD PODCAST PROCESSED: {content_id} -> {filename}")
                processed_count += 1

                cursor.execute('''
                    UPDATE processing_queue
                    SET status = 'completed', updated_at = ?, completed_at = ?
                    WHERE content_id = ?
                ''', (datetime.now().isoformat(), datetime.now().isoformat(), content_id))
            else:
                print(f"❌ No transcript found for {content_id}")
                cursor.execute('''
                    UPDATE processing_queue
                    SET status = 'failed', updated_at = ?
                    WHERE content_id = ?
                ''', (datetime.now().isoformat(), content_id))

        except Exception as e:
            print(f"❌ Error processing {content_id}: {e}")
            cursor.execute('''
                UPDATE processing_queue
                SET status = 'failed', updated_at = ?
                WHERE content_id = ?
            ''', (datetime.now().isoformat(), content_id))

    conn.commit()
    conn.close()

    print(f"\n🎯 HARD PODCAST batch complete: {processed_count}/{len(items)} processed")
    return processed_count

if __name__ == "__main__":
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(description='Hard Podcast Transcript Finder')
    parser.add_argument('--once', action='store_true', help='Process one batch only')
    parser.add_argument('--run', action='store_true', help='Run continuous processing')
    parser.add_argument('--batch-size', type=int, default=3, help='Batch size')

    args = parser.parse_args()

    if args.once:
        process_hard_podcasts(args.batch_size)
    elif args.run:
        print("🎯 Starting Hard Podcast Processor")
        print("Focusing ONLY on difficult podcasts that need real transcript finding")
        print("IGNORING Acquired (easy) and Documents (already processed)")

        while True:
            processed = process_hard_podcasts(3)
            if processed == 0:
                print("✅ All hard podcasts processed!")
                break
            print("⏰ Waiting 30 seconds...")
            time.sleep(30)
    else:
        print("Usage: python3 hard_podcast_processor.py --once or --run")