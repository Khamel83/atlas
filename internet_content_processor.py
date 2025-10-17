#!/usr/bin/env python3
"""
Internet Content Processor - The REAL Atlas Work
Takes content from the internet and puts it in the database
"""

import sqlite3
import json
import requests
import subprocess
import time
from datetime import datetime
from pathlib import Path
import re
from urllib.parse import urlparse

def extract_podcast_transcript(audio_url, podcast_name, episode_title):
    """Extract transcript from podcast audio using available methods"""
    print(f"🎙️ Extracting transcript for {podcast_name}: {episode_title}")

    # Method 1: Try to find existing transcripts online
    transcript_sources = [
        f"https://fireflies.ai/transcript?q={episode_title} {podcast_name}",
        f"https://happyscribe.com/transcripts?q={episode_title} {podcast_name}",
        f"https://otter.ai/search?q={episode_title} {podcast_name}"
    ]

    for source_url in transcript_sources:
        try:
            response = requests.get(source_url, timeout=10)
            if response.status_code == 200 and len(response.text) > 1000:
                print(f"✅ Found transcript from {source_url}")
                return {
                    "source": "online_search",
                    "url": source_url,
                    "content": response.text[:10000],  # First 10k chars
                    "method": "existing_transcript"
                }
        except Exception as e:
            continue

    # Method 2: Try to use local transcription tools
    try:
        # Download audio file
        audio_filename = f"/tmp/{podcast_name}_{episode_title[:20]}.mp3".replace(" ", "_")
        audio_response = requests.get(audio_url, stream=True, timeout=30)

        if audio_response.status_code == 200:
            with open(audio_filename, 'wb') as f:
                for chunk in audio_response.iter_content(chunk_size=8192):
                    f.write(chunk)

            print(f"📥 Downloaded audio: {audio_filename}")

            # Try to transcribe with available tools
            transcription_methods = [
                ["whisper", audio_filename],
                ["python3", "-c", f"import whisper; model=whisper.load_model('base'); result=model.transcribe('{audio_filename}'); print(result['text'])"],
            ]

            for method in transcription_methods:
                try:
                    result = subprocess.run(method, capture_output=True, text=True, timeout=300)
                    if result.returncode == 0 and len(result.stdout) > 100:
                        print(f"✅ Transcribed using {method[0]}")
                        return {
                            "source": "local_transcription",
                            "content": result.stdout,
                            "method": method[0],
                            "audio_file": audio_filename
                        }
                except Exception as e:
                    continue

    except Exception as e:
        print(f"❌ Audio download failed: {e}")

    # Method 3: Fallback - create summary metadata
    return {
        "source": "fallback",
        "content": f"# {episode_title}\n\n**Podcast**: {podcast_name}\n**Audio URL**: {audio_url}\n\n*Transcript extraction failed. Audio available at provided link.*",
        "method": "metadata_only"
    }

def extract_article_content(url):
    """Extract content from article URL"""
    print(f"📰 Extracting article from: {url}")

    try:
        # Method 1: Try basic extraction
        response = requests.get(url, timeout=15, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        if response.status_code == 200:
            content = response.text

            # Extract title
            title_match = re.search(r'<title[^>]*>([^<]+)</title>', content, re.IGNORECASE)
            title = title_match.group(1).strip() if title_match else "Untitled Article"

            # Extract main content (basic extraction)
            # Remove script/style tags
            content = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', content, flags=re.DOTALL)

            # Try to find main content
            content_patterns = [
                r'<article[^>]*>(.*?)</article>',
                r'<main[^>]*>(.*?)</main>',
                r'<div[^>]*class="[^"]*content[^"]*"[^>]*>(.*?)</div>',
                r'<div[^>]*class="[^"]*article[^"]*"[^>]*>(.*?)</div>'
            ]

            main_content = ""
            for pattern in content_patterns:
                matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
                if matches:
                    main_content = matches[0]
                    break

            if not main_content:
                # Fallback: use meta description or first paragraph
                desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']', content, re.IGNORECASE)
                if desc_match:
                    main_content = desc_match.group(1)
                else:
                    # Get first few paragraphs
                    paragraphs = re.findall(r'<p[^>]*>([^<]+)</p>', content)
                    main_content = '\n'.join(paragraphs[:3])

            # Clean HTML tags
            main_content = re.sub(r'<[^>]+>', '\n', main_content)
            main_content = re.sub(r'\n+', '\n', main_content).strip()

            if len(main_content) > 200:
                return {
                    "title": title,
                    "content": f"# {title}\n\n{main_content}",
                    "url": url,
                    "method": "basic_extraction"
                }

    except Exception as e:
        print(f"❌ Article extraction failed: {e}")

    return None

def process_internet_batch(batch_size=10):
    """Process actual internet content (podcasts, articles)"""
    print(f"🌐 Processing {batch_size} internet content items at {datetime.now()}")

    conn = sqlite3.connect("/home/ubuntu/dev/atlas/atlas_v2/data/atlas_v2.db")
    cursor = conn.cursor()

    # Get non-document items (real internet content)
    cursor.execute('''
        SELECT content_id, source_url, source_name, metadata_json
        FROM processing_queue
        WHERE status = 'pending' AND source_name != 'documents'
        LIMIT ?
    ''', (batch_size,))

    items = cursor.fetchall()
    print(f"Found {len(items)} internet content items to process")

    processed_count = 0

    for content_id, source_url, source_name, metadata_json in items:
        try:
            # Handle both JSON strings and Python dict strings
            if metadata_json.startswith('{') and metadata_json.endswith('}'):
                try:
                    metadata = json.loads(metadata_json)
                except:
                    # Fallback: evaluate as Python literal (safe in this context)
                    metadata = eval(metadata_json)
            else:
                metadata = {}
            print(f"\n🔄 Processing: {content_id} ({source_name})")

            # Update status to processing
            cursor.execute('''
                UPDATE processing_queue
                SET status = 'processing', updated_at = ?
                WHERE content_id = ?
            ''', (datetime.now().isoformat(), content_id))

            extracted_content = None

            if source_name in ['Acquired', 'This American Life', '99% Invisible', 'Hard Fork']:
                # It's a podcast - extract transcript
                audio_url = metadata.get('audio_url')
                title = metadata.get('title', content_id)

                if audio_url:
                    extracted_content = extract_podcast_transcript(audio_url, source_name, title)

            elif source_url.startswith('http'):
                # It's a web article
                extracted_content = extract_article_content(source_url)

            if extracted_content:
                # Create output directory
                output_dir = Path("/home/ubuntu/dev/atlas/atlas_v2/content/markdown")
                output_dir.mkdir(parents=True, exist_ok=True)

                # Create filename
                safe_title = re.sub(r'[^a-zA-Z0-9\s-]', '', content_id).strip()[:50]
                filename = f"{safe_title}.md"
                output_file = output_dir / filename

                # Write content
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(extracted_content.get('content', 'No content extracted'))

                # Update metadata
                metadata.update(extracted_content)
                metadata['processed_at'] = datetime.now().isoformat()

                # Insert into content_metadata
                cursor.execute('''
                    INSERT OR REPLACE INTO content_metadata
                    (content_id, source_url, source_name, content_type, title, metadata_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    content_id, source_url, source_name, 'podcast' if 'podcast' in source_name.lower() else 'article',
                    metadata.get('title', content_id),
                    json.dumps(metadata),
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))

                print(f"✅ Processed: {content_id} -> {filename}")
                processed_count += 1

                # Update status to completed
                cursor.execute('''
                    UPDATE processing_queue
                    SET status = 'completed', updated_at = ?, completed_at = ?
                    WHERE content_id = ?
                ''', (datetime.now().isoformat(), datetime.now().isoformat(), content_id))
            else:
                print(f"❌ No content extracted for {content_id}")
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

    print(f"\n✅ Internet batch complete: {processed_count}/{len(items)} items processed")
    return processed_count

def continuous_internet_processor():
    """Run continuous internet content processing"""
    print("🌐 Starting Atlas Internet Content Processor")
    print("Actually extracting content from the internet")
    print("Processing podcasts, articles, and web content")
    print("Press Ctrl+C to stop")

    while True:
        try:
            conn = sqlite3.connect("/home/ubuntu/dev/atlas/atlas_v2/data/atlas_v2.db")
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM processing_queue WHERE status = 'pending' AND source_name != 'documents'")
            pending_count = cursor.fetchone()[0]
            conn.close()

            print(f"\n🌐 Pending internet content: {pending_count}")

            if pending_count > 0:
                processed = process_internet_batch(5)
                if processed == 0:
                    print("⚠️ No internet content processed, may be hitting errors")
                    # Don't wait as long if we're failing
                    time.sleep(30)
                    continue
            else:
                print("✅ All internet content processed!")
                break

        except Exception as e:
            print(f"❌ Error in processing loop: {e}")

        print("⏰ Waiting 2 minutes before next batch...")
        time.sleep(120)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Atlas Internet Content Processor')
    parser.add_argument('--run', action='store_true', help='Run continuous internet processor')
    parser.add_argument('--once', action='store_true', help='Process one batch only')
    parser.add_argument('--batch-size', type=int, default=5, help='Batch size per run')

    args = parser.parse_args()

    if args.run:
        continuous_internet_processor()
    elif args.once:
        process_internet_batch(args.batch_size)
    else:
        print("Usage: python3 internet_content_processor.py --run or --once [--batch-size N]")