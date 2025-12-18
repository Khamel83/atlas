#!/usr/bin/env python3
"""
Fixed Transcript Worker
Properly saves transcripts to the transcriptions table instead of content table.
"""

import os
import sys
import sqlite3
import argparse
from pathlib import Path
from typing import List, Tuple
import requests
from bs4 import BeautifulSoup
import re
import json

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.database_config import get_database_path, get_database_connection


class FixedTranscriptWorker:
    """Proper transcript worker that saves to transcriptions table"""

    def __init__(self):
        self.db_path = get_database_path()

    def fetch_transcript_from_url(self, url: str) -> str:
        """Fetch transcript content from URL"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }

            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Find transcript content
            transcript_text = ""

            # Try common transcript containers
            selectors = [
                'div.transcript-content',
                'div.entry-content',
                'div.post-content',
                'article .content',
                'main .content',
                '.transcript',
                'p'  # Fallback to paragraphs
            ]

            for selector in selectors:
                elements = soup.select(selector)
                if elements:
                    text_parts = []
                    for elem in elements:
                        text = elem.get_text(strip=True)
                        if len(text) > 50:  # Only substantial text
                            text_parts.append(text)

                    if text_parts:
                        transcript_text = '\n\n'.join(text_parts)
                        break

            # Clean up the transcript
            if transcript_text:
                # Remove excessive whitespace
                transcript_text = re.sub(r'\n\s*\n', '\n\n', transcript_text)
                transcript_text = re.sub(r' +', ' ', transcript_text)

                # Minimum length check
                if len(transcript_text) > 5000:
                    return transcript_text

            return ""

        except Exception as e:
            print(f"    ❌ Error fetching {url}: {e}")
            return ""

    def save_transcript_to_transcriptions_table(self, filename: str, transcript_text: str, source: str, metadata: dict = None) -> bool:
        """Save transcript to transcriptions table (correct table)"""
        if not transcript_text or len(transcript_text) < 1000:
            return False

        try:
            conn = get_database_connection()
            cursor = conn.cursor()

            # Insert into transcriptions table
            cursor.execute('''
                INSERT INTO transcriptions
                (filename, transcript, source, metadata, created_at, processed)
                VALUES (?, ?, ?, ?, datetime('now'), 1)
            ''', (
                filename,
                transcript_text,
                source,
                json.dumps(metadata) if metadata else '{}'
            ))

            conn.commit()
            conn.close()

            print(f"    ✅ Saved to transcriptions table ({len(transcript_text):,} chars)")
            return True

        except Exception as e:
            print(f"    ❌ Error saving transcript: {e}")
            return False

    def get_lex_fridman_transcript_urls(self, limit: int = 10) -> List[Tuple[str, str]]:
        """Get a few Lex Fridman transcript URLs for testing"""
        base_urls = [
            "https://lexfridman.com/dhh-david-heinemeier-hansson-transcript",
            "https://lexfridman.com/terence-tao-transcript",
            "https://lexfridman.com/sundar-pichai-transcript",
            "https://lexfridman.com/james-holland-transcript",
            "https://lexfridman.com/oliver-anthony-transcript",
            "https://lexfridman.com/tim-sweeney-transcript",
            "https://lexfridman.com/robert-rodriguez-transcript",
            "https://lexfridman.com/marc-andreessen-2-transcript",
            "https://lexfridman.com/jordan-peterson-2-transcript",
            "https://lexfridman.com/bernie-sanders-transcript"
        ]

        return [(url, url.split('/')[-1].replace('-transcript', '')) for url in base_urls[:limit]]

    def process_transcript_batch(self, limit: int = 10) -> dict:
        """Process a batch of transcripts and save to proper table"""
        transcript_urls = self.get_lex_fridman_transcript_urls(limit)

        print(f"🚀 Processing {len(transcript_urls)} transcripts to transcriptions table")
        print("=" * 70)

        results = {"processed": 0, "saved": 0, "failed": 0}

        for url, episode_name in transcript_urls:
            print(f"📄 Processing: {episode_name}")

            results["processed"] += 1

            transcript_text = self.fetch_transcript_from_url(url)

            if transcript_text:
                filename = f"lex_fridman_{episode_name.replace('-', '_')}.txt"
                metadata = {
                    "podcast": "Lex Fridman Podcast",
                    "episode": episode_name.replace('-', ' ').title(),
                    "source_url": url,
                    "processing_method": "direct_fetch",
                    "processed_at": str(datetime.now())
                }

                success = self.save_transcript_to_transcriptions_table(
                    filename, transcript_text, "lex_fridman_website", metadata
                )

                if success:
                    results["saved"] += 1
                else:
                    results["failed"] += 1
            else:
                print(f"    ❌ No transcript content found")
                results["failed"] += 1

        print("=" * 70)
        print(f"📊 Results: {results['processed']} processed, {results['saved']} saved, {results['failed']} failed")

        return results


def main():
    parser = argparse.ArgumentParser(description='Fixed Transcript Worker')
    parser.add_argument('--limit', type=int, default=10, help='Number of transcripts to process')

    args = parser.parse_args()

    worker = FixedTranscriptWorker()
    worker.process_transcript_batch(args.limit)


if __name__ == "__main__":
    # Import datetime here for use in metadata
    from datetime import datetime
    main()