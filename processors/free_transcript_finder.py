#!/usr/bin/env python3
"""
FREE TRANSCRIPT FINDER
Drop-in replacement for google_powered_transcript_finder.py
Uses 100% free search alternatives instead of expensive Google Custom Search API
"""

import requests
import json
import time
import csv
import sqlite3
import os
import asyncio
from typing import List, Dict, Optional
from urllib.parse import urlparse

# Import OOS free search system
import sys
sys.path.insert(0, './src')
try:
    from free_search_alternatives import search_free
    from perplexity_usage_manager import safe_perplexity_search
except ImportError:
    print("⚠️  OOS search modules not found. Please install OOS first:")
    print("   curl -sSL https://raw.githubusercontent.com/Khamel83/oos/master/install.sh | bash")
    sys.exit(1)


class FreeTranscriptFinder:
    """
    Drop-in replacement for GooglePoweredTranscriptFinder
    Uses free search alternatives instead of expensive Google API
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        self.db_path = "data/atlas.db"

        # Comprehensive list of transcript sites
        self.transcript_sites = [
            "fireflies.ai",
            "happyscribe.com",
            "otter.ai",
            "rev.com",
            "scribie.com",
            "sonix.ai",
            "trint.com",
            "podscripts.co",
            "podsights.com",
            "github.com",
            "medium.com",
            "substack.com",
            "archive.org",
            "youtube.com",
            "docs.google.com",
        ]

        # Tier 1 sites (most likely to have transcripts)
        self.tier1_sites = [
            "otter.ai",
            "rev.com",
            "fireflies.ai",
            "happyscribe.com",
            "github.com"
        ]

        # Search terms that work well
        self.search_terms = [
            "transcript",
            "full transcript",
            "episode transcript",
            "conversation transcript",
            "interview transcript"
        ]

        # Query patterns
        self.query_patterns = [
            '"{podcast}" {term}',
            '"{podcast}" "{term}"',
            '{podcast} {term}',
            '{podcast} transcript site:{site}',
            '"{podcast}" site:{site}'
        ]

        print("✅ Free Transcript Finder initialized")
        print("   💰 Cost: $0.00 (uses free search alternatives)")

    def exhaustive_search(self, podcast_name: str, max_results: int = 10) -> List[Dict]:
        """
        Exhaustive search using FREE alternatives
        Drop-in replacement for exhaustive_google_search()
        """
        return asyncio.run(self._async_exhaustive_search(podcast_name, max_results))

    async def _async_exhaustive_search(self, podcast_name: str, max_results: int = 10) -> List[Dict]:
        """Async implementation of exhaustive search"""
        all_results = []
        search_count = 0

        print(f"\n🔍 FREE Exhaustive Search for: {podcast_name}")
        print("=" * 60)

        # PHASE 1: Site-specific searches (FREE)
        print("1️⃣ PHASE 1: Free site-specific searches...")

        for site in self.tier1_sites:
            for term in self.search_terms[:3]:  # Top 3 terms
                query = f'"{podcast_name}" {term} site:{site}'

                print(f"   Search {search_count+1}: {query[:60]}...")
                search_count += 1

                # Use free search alternatives
                try:
                    results = await search_free(query, max_results=5)

                    for result in results:
                        if any(site_name in result.url for site_name in [site]):
                            transcript_data = self._test_url_for_transcript(result.url)
                            if transcript_data:
                                all_results.append({
                                    'url': result.url,
                                    'title': result.title,
                                    'site': site,
                                    'search_term': term,
                                    'query': query,
                                    'content_length': len(transcript_data),
                                    'source': result.source,
                                    'cost': 0.00
                                })
                                print(f"     ✅ FOUND: {len(transcript_data)} chars from {result.source}")

                    # Stop if we have enough results
                    if len(all_results) >= max_results:
                        break

                except Exception as e:
                    print(f"     ⚠️  Search failed: {e}")

                # Small delay to be respectful
                await asyncio.sleep(0.1)

            if len(all_results) >= max_results:
                break

        # PHASE 2: General free searches (if needed)
        if len(all_results) < max_results and search_count < 20:
            print("2️⃣ PHASE 2: General free searches...")

            for term in ['transcript', 'full transcript']:
                for pattern in [f'"{podcast_name}" {term}', f'{podcast_name} {term}']:
                    query = pattern

                    print(f"   Search {search_count+1}: {query[:60]}...")
                    search_count += 1

                    try:
                        results = await search_free(query, max_results=5)

                        for result in results[:3]:  # Top 3 per query
                            if any(site in result.url for site in self.transcript_sites):
                                transcript_data = self._test_url_for_transcript(result.url)
                                if transcript_data:
                                    all_results.append({
                                        'url': result.url,
                                        'title': result.title,
                                        'site': urlparse(result.url).netloc,
                                        'search_term': term,
                                        'query': query,
                                        'content_length': len(transcript_data),
                                        'source': result.source,
                                        'cost': 0.00
                                    })
                                    print(f"     ✅ FOUND: {len(transcript_data)} chars from {result.source}")

                        if len(all_results) >= max_results:
                            break

                    except Exception as e:
                        print(f"     ⚠️  Search failed: {e}")

                    await asyncio.sleep(0.1)

                if len(all_results) >= max_results:
                    break

        # PHASE 3: Enhanced search with Perplexity (asks permission)
        if len(all_results) < max_results and search_count < 25:
            print("3️⃣ PHASE 3: Enhanced search (Perplexity Pro credits)...")

            enhanced_query = f'"{podcast_name}" transcript full text site:otter.ai OR site:rev.com OR site:fireflies.ai'

            print(f"   Enhanced search: {enhanced_query[:60]}...")

            try:
                success, message, perplexity_results = await safe_perplexity_search(
                    enhanced_query, max_results=5
                )

                if success:
                    print(f"   💡 {message}")
                    for result in perplexity_results:
                        transcript_data = self._test_url_for_transcript(result.url)
                        if transcript_data:
                            all_results.append({
                                'url': result.url,
                                'title': result.title,
                                'site': urlparse(result.url).netloc,
                                'search_term': 'enhanced',
                                'query': enhanced_query,
                                'content_length': len(transcript_data),
                                'source': 'Perplexity',
                                'cost': 0.01  # Estimated Perplexity cost
                            })
                            print(f"     ✅ FOUND: {len(transcript_data)} chars from Perplexity")
                else:
                    print(f"   ⚠️  Enhanced search skipped: {message}")

            except Exception as e:
                print(f"     ⚠️  Enhanced search failed: {e}")

        # Results summary
        print("=" * 60)
        print(f"🎯 SEARCH COMPLETE")
        print(f"   Total searches executed: {search_count}")
        print(f"   Raw results found: {len(all_results)}")

        # Calculate total cost
        total_cost = sum(result.get('cost', 0) for result in all_results)
        print(f"   💰 Total cost: ${total_cost:.2f}")

        # Deduplicate and sort by quality
        unique_results = []
        seen_urls = set()

        for result in sorted(all_results, key=lambda x: x['content_length'], reverse=True):
            if result['url'] not in seen_urls:
                unique_results.append(result)
                seen_urls.add(result['url'])

        print(f"   ✅ Unique transcripts found: {len(unique_results)}")
        return unique_results[:max_results]

    def _test_url_for_transcript(self, url: str) -> Optional[str]:
        """Test if URL contains transcript content (same as original)"""
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                content = response.text.lower()

                # Transcript indicators
                transcript_indicators = [
                    'transcript',
                    'full text',
                    'speaker 1',
                    'speaker 2',
                    '[music]',
                    '[laughter]',
                    'timestamps',
                    '00:00',
                    'interviewer:',
                    'guest:'
                ]

                indicator_count = sum(1 for indicator in transcript_indicators if indicator in content)

                if indicator_count >= 2 and len(content) > 1000:
                    return response.text

        except Exception as e:
            print(f"     ⚠️  URL test failed: {e}")

        return None

    def save_to_database(self, results: List[Dict], podcast_name: str):
        """Save results to database (same interface as original)"""
        try:
            # Ensure data directory exists
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Create table if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transcripts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    podcast_name TEXT,
                    url TEXT UNIQUE,
                    title TEXT,
                    site TEXT,
                    search_term TEXT,
                    query TEXT,
                    content_length INTEGER,
                    source TEXT,
                    cost REAL,
                    found_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Insert results
            for result in results:
                cursor.execute('''
                    INSERT OR REPLACE INTO transcripts
                    (podcast_name, url, title, site, search_term, query, content_length, source, cost)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    podcast_name,
                    result['url'],
                    result['title'],
                    result['site'],
                    result['search_term'],
                    result['query'],
                    result['content_length'],
                    result['source'],
                    result.get('cost', 0.00)
                ))

            conn.commit()
            conn.close()

            print(f"✅ Saved {len(results)} results to database")

        except Exception as e:
            print(f"❌ Database save failed: {e}")


# Drop-in replacement function
def exhaustive_google_search(podcast_name: str, max_results: int = 10) -> List[Dict]:
    """
    Drop-in replacement for the original expensive Google search function
    Uses free alternatives instead of Google Custom Search API
    """
    finder = FreeTranscriptFinder()
    return finder.exhaustive_search(podcast_name, max_results)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        podcast_name = " ".join(sys.argv[1:])
    else:
        podcast_name = "The Tim Ferriss Show"

    print(f"🎙️  Searching for transcripts: {podcast_name}")

    finder = FreeTranscriptFinder()
    results = finder.exhaustive_search(podcast_name, max_results=5)

    if results:
        print(f"\n🎉 Found {len(results)} transcript sources:")
        for i, result in enumerate(results, 1):
            print(f"{i}. {result['title']}")
            print(f"   URL: {result['url']}")
            print(f"   Site: {result['site']}")
            print(f"   Length: {result['content_length']} chars")
            print(f"   Source: {result['source']}")
            print(f"   Cost: ${result.get('cost', 0):.2f}")
            print()

        # Save to database
        finder.save_to_database(results, podcast_name)
    else:
        print("❌ No transcripts found")