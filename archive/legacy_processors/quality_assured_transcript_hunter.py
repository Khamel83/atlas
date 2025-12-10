#!/usr/bin/env python3
"""
QUALITY-ASSURED TRANSCRIPT HUNTER
Enhanced version that rigorously validates transcript quality at every step
Ensures we only store real, high-quality transcripts - not garbage content
"""

import requests
import json
import time
import csv
import sqlite3
import os
from typing import List, Dict, Optional
from urllib.parse import urlparse
from transcript_quality_validator import TranscriptQualityValidator

class QualityAssuredTranscriptHunter:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        # Initialize quality validator
        self.validator = TranscriptQualityValidator()

        # API Keys from environment
        self.tavily_api_key = os.getenv("TAVILY_API_KEY")
        self.google_api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
        self.google_engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID")

        self.db_path = "data/atlas.db"

        # Quality thresholds
        self.min_quality_score = 0.6  # Minimum quality score to accept
        self.excellent_threshold = 0.8  # Score for excellent transcripts

        # Known high-success transcript sites (validated)
        self.transcript_sites = [
            "fireflies.ai",
            "happyscribe.com",
            "otter.ai",
            "rev.com",
            "scribie.com",
            "sonix.ai",
            "podscripts.co",
            "github.com",
            "medium.com",
            "substack.com"
        ]

    def quality_assured_hunt(self, podcast_name: str) -> List[Dict]:
        """
        QUALITY-ASSURED HUNT: Only return validated, high-quality transcripts
        """
        print(f"\n🎯 QUALITY-ASSURED HUNT: {podcast_name}")
        print("=" * 70)

        all_transcripts = []
        total_tested = 0
        quality_rejected = 0

        # STEP 1: Google API - Site-specific searches with quality validation
        print("1️⃣ Google API - Quality validated search...")
        google_transcripts = self._google_quality_search(podcast_name)
        all_transcripts.extend(google_transcripts)
        print(f"   ✅ Google found {len(google_transcripts)} quality transcripts")

        # STEP 2: Tavily AI Search with quality validation
        print("2️⃣ Tavily AI - Quality validated search...")
        tavily_transcripts = self._tavily_quality_search(podcast_name)
        all_transcripts.extend(tavily_transcripts)
        print(f"   ✅ Tavily found {len(tavily_transcripts)} quality transcripts")

        # STEP 3: Quality assessment summary
        total_found = len(all_transcripts)
        if total_found > 0:
            avg_score = sum(t['quality']['score'] for t in all_transcripts) / total_found
            excellent_count = sum(1 for t in all_transcripts if t['quality']['score'] >= self.excellent_threshold)

            print(f"\n📊 QUALITY SUMMARY:")
            print(f"   Total quality transcripts: {total_found}")
            print(f"   Excellent quality (≥{self.excellent_threshold}): {excellent_count}")
            print(f"   Average quality score: {avg_score:.2f}")
            print(f"   Quality rejection rate: {quality_rejected}/{total_tested} ({(quality_rejected/max(total_tested,1)*100):.1f}%)")

        return all_transcripts

    def _google_quality_search(self, podcast_name: str) -> List[Dict]:
        """Google search with immediate quality validation"""
        if not self.google_api_key or not self.google_engine_id:
            print("   ⚠️  Google API not configured")
            return []

        quality_transcripts = []

        # Focus on highest-success sites first
        high_success_sites = ["fireflies.ai", "happyscribe.com", "otter.ai"]

        for site in high_success_sites:
            print(f"   🔍 Searching {site}...")

            # Test multiple query patterns for this site
            queries = [
                f'"{podcast_name}" transcript site:{site}',
                f'"{podcast_name}" full transcript site:{site}',
                f'{podcast_name} episode transcript site:{site}'
            ]

            for query in queries:
                results = self._execute_google_search(query, max_results=5)

                for result in results:
                    print(f"     Testing: {result['title'][:50]}...")

                    # QUALITY VALIDATION AT POINT OF DISCOVERY
                    quality_result = self.validator.test_url_for_quality_transcript(result['link'])

                    if quality_result:
                        quality_transcripts.append({
                            'url': result['link'],
                            'title': result['title'],
                            'content': quality_result['content'],
                            'quality': quality_result['quality'],
                            'source': 'google_validated',
                            'domain': site,
                            'podcast_name': podcast_name
                        })

                        score = quality_result['quality']['score']
                        category = quality_result['quality']['category']
                        length = quality_result['quality']['content_length']

                        print(f"     ✅ QUALITY VALIDATED: {score:.2f} ({category}) - {length:,} chars")
                    else:
                        print(f"     ❌ Quality validation failed")

                time.sleep(0.5)  # Rate limiting

        return quality_transcripts

    def _tavily_quality_search(self, podcast_name: str) -> List[Dict]:
        """Tavily search with immediate quality validation"""
        if not self.tavily_api_key:
            print("   ⚠️  Tavily API not configured")
            return []

        quality_transcripts = []

        # Advanced Tavily queries
        queries = [
            f'"{podcast_name}" complete transcript text',
            f'"{podcast_name}" full episode transcription',
            f'{podcast_name} transcript conversation',
            f'where find {podcast_name} transcripts'
        ]

        for query in queries:
            print(f"   🔍 Tavily: {query[:50]}...")
            results = self._execute_tavily_search(query, max_results=5)

            for result in results:
                print(f"     Testing: {result['title'][:50]}...")

                # QUALITY VALIDATION AT POINT OF DISCOVERY
                quality_result = self.validator.test_url_for_quality_transcript(result['url'])

                if quality_result:
                    quality_transcripts.append({
                        'url': result['url'],
                        'title': result['title'],
                        'content': quality_result['content'],
                        'quality': quality_result['quality'],
                        'source': 'tavily_validated',
                        'domain': urlparse(result['url']).netloc,
                        'podcast_name': podcast_name
                    })

                    score = quality_result['quality']['score']
                    category = quality_result['quality']['category']
                    length = quality_result['quality']['content_length']

                    print(f"     ✅ QUALITY VALIDATED: {score:.2f} ({category}) - {length:,} chars")
                else:
                    print(f"     ❌ Quality validation failed")

            time.sleep(0.5)

        return quality_transcripts

    def _execute_google_search(self, query: str, max_results: int = 10) -> List[Dict]:
        """Execute Google Custom Search API query"""
        try:
            url = "https://customsearch.googleapis.com/customsearch/v1"
            params = {
                'key': self.google_api_key,
                'cx': self.google_engine_id,
                'q': query,
                'num': max_results
            }

            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                return data.get('items', [])
            else:
                return []
        except Exception:
            return []

    def _execute_tavily_search(self, query: str, max_results: int = 10) -> List[Dict]:
        """Execute Tavily Search API query"""
        try:
            payload = {
                "api_key": self.tavily_api_key,
                "query": query,
                "search_depth": "advanced",
                "include_answer": False,
                "include_raw_content": True,
                "max_results": max_results
            }

            response = requests.post("https://api.tavily.com/search", json=payload)
            if response.status_code == 200:
                data = response.json()
                return data.get("results", [])
            else:
                return []
        except Exception:
            return []

    def process_priority_podcasts_with_quality_assurance(self):
        """Process priority podcasts with rigorous quality assurance"""
        print("🚀 QUALITY-ASSURED PODCAST TRANSCRIPT HUNT")
        print("Only validated, high-quality transcripts will be stored")
        print("=" * 70)

        # Priority podcasts (user's focus list)
        priority_podcasts = [
            "Acquired",
            "Hard Fork",
            "EconTalk",
            "Conversations with Tyler",
            "Lex Fridman Podcast",
            "Practical AI",
            "Planet Money",
            "99% Invisible",
            "This American Life",
            "The Tim Ferriss Show"
        ]

        results = {}
        total_quality_transcripts = 0
        total_podcasts_with_transcripts = 0

        for i, podcast_name in enumerate(priority_podcasts):
            print(f"\n[{i+1}/{len(priority_podcasts)}] PROCESSING: {podcast_name}")

            quality_transcripts = self.quality_assured_hunt(podcast_name)

            if quality_transcripts:
                results[podcast_name] = {
                    "transcripts": quality_transcripts,
                    "count": len(quality_transcripts),
                    "avg_quality": sum(t['quality']['score'] for t in quality_transcripts) / len(quality_transcripts),
                    "excellent_count": sum(1 for t in quality_transcripts if t['quality']['score'] >= self.excellent_threshold)
                }

                total_quality_transcripts += len(quality_transcripts)
                total_podcasts_with_transcripts += 1

                # Store in database immediately
                self._store_quality_transcripts(podcast_name, quality_transcripts)

                print(f"🎯 SUCCESS: {len(quality_transcripts)} quality transcripts stored!")
            else:
                print(f"❌ NO QUALITY TRANSCRIPTS FOUND")

            # Rate limiting between podcasts
            time.sleep(2)

        # Save results summary
        output_file = "config/quality_assured_results.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        # Final summary
        print(f"\n🎉 QUALITY-ASSURED HUNT COMPLETE!")
        print(f"📊 Results:")
        print(f"   Podcasts with quality transcripts: {total_podcasts_with_transcripts}/{len(priority_podcasts)}")
        print(f"   Total quality transcripts found: {total_quality_transcripts}")
        print(f"   Average transcripts per successful podcast: {total_quality_transcripts/max(total_podcasts_with_transcripts,1):.1f}")
        print(f"   Results saved to: {output_file}")

        return results

    def _store_quality_transcripts(self, podcast_name: str, transcripts: List[Dict]):
        """Store only validated, quality transcripts in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            for transcript in transcripts:
                quality_info = transcript['quality']

                # Create rich metadata
                metadata = {
                    "quality_score": quality_info['score'],
                    "quality_category": quality_info['category'],
                    "content_length": quality_info['content_length'],
                    "source": transcript['source'],
                    "domain": transcript['domain'],
                    "validation_details": quality_info['details']
                }

                cursor.execute('''
                    INSERT OR REPLACE INTO content (title, content, content_type, url, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    f"{podcast_name} - {transcript['title']}",
                    transcript['content'],
                    'quality_podcast_transcript',
                    transcript['url'],
                    time.strftime('%Y-%m-%d %H:%M:%S'),
                    json.dumps(metadata)
                ))

            conn.commit()
            conn.close()

            avg_score = sum(t['quality']['score'] for t in transcripts) / len(transcripts)
            print(f"   💾 Stored {len(transcripts)} quality transcripts (avg score: {avg_score:.2f})")

        except Exception as e:
            print(f"   ❌ Database error: {e}")

if __name__ == "__main__":
    hunter = QualityAssuredTranscriptHunter()
    hunter.process_priority_podcasts_with_quality_assurance()