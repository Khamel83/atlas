#!/usr/bin/env python3
"""
Batch Transcript Fetcher

Directly fetches all the transcript URLs we already found instead of
complex episode matching that fails. We have 46 episodes with transcript URLs
from RSS extraction - let's just fetch them all!

Usage:
    python scripts/batch_transcript_fetcher.py --limit 50
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

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.database_config import get_database_path, get_database_connection
from transcript_orchestrator import TranscriptOrchestrator

class BatchTranscriptFetcher:
    """Directly fetch transcripts from found URLs"""

    def __init__(self):
        self.db_path = get_database_path()
        self.orchestrator = TranscriptOrchestrator()

    def fetch_lex_fridman_transcripts(self, limit: int = 50) -> List[Tuple[str, str]]:
        """Get all available Lex Fridman transcript URLs by pattern"""
        base_urls = [
            "https://lexfridman.com/dave-hone-transcript",
            "https://lexfridman.com/keyu-jin-transcript",
            "https://lexfridman.com/jack-weatherford-transcript",
            "https://lexfridman.com/demis-hassabis-2-transcript",
            "https://lexfridman.com/dhh-david-heinemeier-hansson-transcript",
            "https://lexfridman.com/iran-war-debate-transcript",
            "https://lexfridman.com/terence-tao-transcript",
            "https://lexfridman.com/sundar-pichai-transcript",
            "https://lexfridman.com/james-holland-transcript",
            "https://lexfridman.com/oliver-anthony-transcript",
            "https://lexfridman.com/janna-levin-transcript",
            "https://lexfridman.com/tim-sweeney-transcript",
            "https://lexfridman.com/jeffrey-wasserstrom-transcript",
            "https://lexfridman.com/robert-rodriguez-transcript",
            "https://lexfridman.com/dave-smith-transcript",
            "https://lexfridman.com/douglas-murray-2-transcript",
            "https://lexfridman.com/ezra-klein-and-derek-thompson-transcript",
            "https://lexfridman.com/narendra-modi-transcript",
            "https://lexfridman.com/deepseek-dylan-patel-nathan-lambert-transcript",
            "https://lexfridman.com/marc-andreessen-2-transcript",
            "https://lexfridman.com/jennifer-burns-transcript",
            "https://lexfridman.com/volodymyr-zelenskyy-transcript",
            "https://lexfridman.com/adam-frank-transcript",
            "https://lexfridman.com/saagar-enjeti-2-transcript",
            "https://lexfridman.com/javier-milei-transcript",
            "https://lexfridman.com/dario-amodei-transcript",
            "https://lexfridman.com/rick-spence-transcript",
            "https://lexfridman.com/bernie-sanders-transcript",
            "https://lexfridman.com/jordan-peterson-2-transcript",
            "https://lexfridman.com/cursor-team-transcript",
            "https://lexfridman.com/ed-barnhart-transcript",
            "https://lexfridman.com/vivek-ramaswamy-transcript",
            "https://lexfridman.com/vejas-liulevicius-transcript",
            "https://lexfridman.com/gregory-aldrete-transcript",
            "https://lexfridman.com/donald-trump-transcript",
            "https://lexfridman.com/cenk-uygur-transcript",
            "https://lexfridman.com/pieter-levels-transcript",
            "https://lexfridman.com/craig-jones-2-transcript",
            "https://lexfridman.com/elon-musk-and-neuralink-team-transcript",
            "https://lexfridman.com/jordan-jonas-transcript",
            "https://lexfridman.com/ivanka-trump-transcript",
            "https://lexfridman.com/andrew-huberman-5-transcript",
            "https://lexfridman.com/aravind-srinivas-transcript",
            "https://lexfridman.com/sara-walker-3-transcript",
            "https://lexfridman.com/kevin-spacey-transcript",
            "https://lexfridman.com/roman-yampolskiy-transcript"
        ]

        return [(url, url.split('/')[-1].replace('-transcript', '')) for url in base_urls[:limit]]

    def fetch_transcript_from_url(self, url: str) -> str:
        """Fetch transcript content from URL"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }

            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Find transcript content - try multiple selectors
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

    def save_transcript_to_atlas(self, title: str, url: str, transcript_text: str) -> bool:
        """Save transcript to Atlas content database"""
        if not transcript_text or len(transcript_text) < 5000:
            return False

        try:
            conn = get_database_connection()
            cursor = conn.cursor()

            # Insert into content table
            cursor.execute('''
                INSERT OR REPLACE INTO content
                (title, url, content, content_type, created_at, updated_at)
                VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))
            ''', (
                f"[TRANSCRIPT] {title}",
                url,
                transcript_text,
                "podcast_transcript"
            ))

            conn.commit()
            conn.close()

            print(f"    ✅ Saved transcript ({len(transcript_text):,} chars)")
            return True

        except Exception as e:
            print(f"    ❌ Error saving transcript: {e}")
            return False

    def batch_fetch_transcripts(self, limit: int = 50) -> dict:
        """Fetch transcripts in batch"""
        transcript_urls = self.fetch_lex_fridman_transcripts(limit)

        print(f"🚀 Batch fetching {len(transcript_urls)} Lex Fridman transcripts")
        print("=" * 70)

        results = {"processed": 0, "saved": 0, "failed": 0}

        for url, episode_name in transcript_urls:
            print(f"📄 Fetching: {episode_name}")

            results["processed"] += 1

            transcript_text = self.fetch_transcript_from_url(url)

            if transcript_text:
                title = f"Lex Fridman Podcast - {episode_name.replace('-', ' ').title()}"
                success = self.save_transcript_to_atlas(title, url, transcript_text)

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
    parser = argparse.ArgumentParser(description='Batch Transcript Fetcher')
    parser.add_argument('--limit', type=int, default=50, help='Number of transcripts to fetch')

    args = parser.parse_args()

    fetcher = BatchTranscriptFetcher()
    fetcher.batch_fetch_transcripts(args.limit)

if __name__ == "__main__":
    main()