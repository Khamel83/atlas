#!/usr/bin/env python3
"""
Podcast Transcription Script
Downloads and transcribes podcast audio files from metadata
"""

import json
import os
import sys
import tempfile
import requests
import whisper
from pathlib import Path
import hashlib
from urllib.parse import urlparse
import sqlite3
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

class PodcastTranscriber:
    def __init__(self):
        self.whisper_model = whisper.load_model("base")  # Use base model for speed
        self.output_dir = Path("output/podcasts/transcripts")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = "atlas.db"

    def init_database(self):
        """Initialize database table for transcripts"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transcriptions (
                id INTEGER PRIMARY KEY,
                podcast_id TEXT UNIQUE,
                title TEXT,
                audio_url TEXT,
                transcript_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def download_audio(self, url, max_size_mb=200):
        """Download audio file with size limit"""
        try:
            # Check if already downloaded
            url_hash = hashlib.md5(url.encode()).hexdigest()
            temp_path = Path(f"/tmp/podcast_{url_hash}.mp3")

            if temp_path.exists():
                return str(temp_path)

            print(f"Downloading: {url}")

            # Stream download with size check
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()

            # Check content length
            content_length = response.headers.get('content-length')
            if content_length:
                size_mb = int(content_length) / (1024 * 1024)
                if size_mb > max_size_mb:
                    print(f"Skipping large file: {size_mb:.1f}MB (limit: {max_size_mb}MB)")
                    return None

            # Download to temp file
            downloaded_size = 0
            with open(temp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        # Check size limit during download
                        if downloaded_size > max_size_mb * 1024 * 1024:
                            print(f"Download exceeded size limit, stopping")
                            temp_path.unlink()  # Delete partial file
                            return None

            print(f"Downloaded {downloaded_size / (1024*1024):.1f}MB")
            return str(temp_path)

        except Exception as e:
            print(f"Download failed: {e}")
            return None

    def transcribe_audio(self, audio_path):
        """Transcribe audio file using Whisper"""
        try:
            print(f"Transcribing: {audio_path}")
            result = self.whisper_model.transcribe(audio_path)
            return result["text"]
        except Exception as e:
            print(f"Transcription failed: {e}")
            return None

    def process_podcast_file(self, json_path):
        """Process a single podcast metadata file"""
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)

            # Extract podcast info
            raw_data = data.get('raw_data', {})
            title = raw_data.get('title', 'Unknown')
            podcast_id = Path(json_path).stem  # Use filename as ID

            # Find audio URL
            links = raw_data.get('links', [])
            audio_url = None

            for link in links:
                if link.get('type', '').startswith('audio/') and link.get('href'):
                    audio_url = link['href']
                    break

            if not audio_url:
                print(f"No audio URL found in {json_path}")
                return False

            # Check if already transcribed
            transcript_path = self.output_dir / f"{podcast_id}_transcript.txt"
            if transcript_path.exists():
                print(f"Already transcribed: {title}")
                return True

            print(f"Processing: {title}")
            print(f"Audio URL: {audio_url}")

            # Download audio
            temp_audio = self.download_audio(audio_url)
            if not temp_audio:
                return False

            # Transcribe
            transcript = self.transcribe_audio(temp_audio)
            if not transcript:
                return False

            # Save transcript
            with open(transcript_path, 'w') as f:
                f.write(f"Title: {title}\n")
                f.write(f"URL: {audio_url}\n")
                f.write(f"Transcribed: {datetime.now().isoformat()}\n")
                f.write(f"\n--- TRANSCRIPT ---\n\n")
                f.write(transcript)

            # Save to database
            self.save_to_database(podcast_id, title, audio_url, str(transcript_path))

            # Cleanup temp file
            if os.path.exists(temp_audio):
                os.remove(temp_audio)

            print(f"✅ Completed: {title}")
            return True

        except Exception as e:
            print(f"Error processing {json_path}: {e}")
            return False

    def save_to_database(self, podcast_id, title, audio_url, transcript_path):
        """Save transcript info to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO transcriptions
                (podcast_id, title, audio_url, transcript_path)
                VALUES (?, ?, ?, ?)
            """, (podcast_id, title, audio_url, transcript_path))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Database save failed: {e}")

    def process_all_podcasts(self, limit=None):
        """Process all podcast metadata files"""
        self.init_database()

        podcast_files = list(Path("output/podcasts").glob("*_rss_entry.json"))
        print(f"Found {len(podcast_files)} podcast files")

        if limit:
            podcast_files = podcast_files[:limit]
            print(f"Processing first {limit} files")

        successful = 0
        failed = 0

        for i, podcast_file in enumerate(podcast_files, 1):
            print(f"\n[{i}/{len(podcast_files)}] Processing {podcast_file.name}")

            if self.process_podcast_file(podcast_file):
                successful += 1
            else:
                failed += 1

            # Progress update
            if i % 5 == 0:
                print(f"\nProgress: {i}/{len(podcast_files)} - Success: {successful}, Failed: {failed}")

        print(f"\n🎉 Transcription complete!")
        print(f"✅ Successful: {successful}")
        print(f"❌ Failed: {failed}")
        print(f"📁 Transcripts saved to: {self.output_dir}")

def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Transcribe podcast audio files")
    parser.add_argument("--limit", type=int, help="Limit number of files to process (for testing)")
    parser.add_argument("--test", action="store_true", help="Process only 3 files for testing")

    args = parser.parse_args()

    transcriber = PodcastTranscriber()

    if args.test:
        print("🧪 Test mode: Processing 3 files")
        transcriber.process_all_podcasts(limit=3)
    else:
        transcriber.process_all_podcasts(limit=args.limit)

if __name__ == "__main__":
    main()