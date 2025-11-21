#!/usr/bin/env python3
"""
Tavily-powered systematic transcript discovery
Uses Tavily Search API to find transcript sources systematically
"""

import requests
import json
import time
import sqlite3
import os
from typing import List, Dict, Optional

class TavilyTranscriptFinder:
    def __init__(self):
        # Set up Tavily Search API
        self.api_key = os.getenv("TAVILY_API_KEY")
        self.base_url = "https://api.tavily.com/search"

        if not self.api_key:
            raise ValueError("TAVILY_API_KEY environment variable required")

        self.session = requests.Session()
        self.db_path = "data/atlas.db"

        # Known transcript aggregator sites
        self.transcript_sites = [
            "github.com",
            "medium.com",
            "substack.com",
            "archive.org",
            "youtube.com",
            "podscripts.co",
            "happyscribe.com"
        ]

    def find_transcript_sources_for_podcast(self, podcast_name: str) -> List[Dict]:
        """
        Systematically find where transcripts exist for this podcast
        """
        print(f"🔍 Searching for '{podcast_name}' transcript sources...")

        all_sources = []

        # Strategy 1: Search each known aggregator site
        for site in self.transcript_sites:
            query = f'"{podcast_name}" transcript site:{site}'
            print(f"  Searching: {query}")
            results = self._tavily_search(query, max_results=3)

            for result in results:
                source_info = {
                    "url": result["url"],
                    "title": result["title"],
                    "domain": site,
                    "snippet": result.get("content", "")[:200],
                    "confidence": self._calculate_confidence(result, podcast_name)
                }

                if source_info["confidence"] > 0.3:
                    all_sources.append(source_info)
                    print(f"    ✅ Found: {result['title'][:50]}... (confidence: {source_info['confidence']:.2f})")

            time.sleep(0.5)  # Rate limiting

        # Strategy 2: General transcript searches
        general_queries = [
            f'"{podcast_name}" "full transcript"',
            f'"{podcast_name}" "episode transcript"',
            f'"{podcast_name}" transcript archive'
        ]

        for query in general_queries:
            print(f"  General search: {query}")
            results = self._tavily_search(query, max_results=5)

            for result in results:
                # Check if already found
                if not any(source["url"] == result["url"] for source in all_sources):
                    source_info = {
                        "url": result["url"],
                        "title": result["title"],
                        "domain": self._extract_domain(result["url"]),
                        "snippet": result.get("content", "")[:200],
                        "confidence": self._calculate_confidence(result, podcast_name)
                    }

                    if source_info["confidence"] > 0.2:
                        all_sources.append(source_info)
                        print(f"    ✅ General: {result['title'][:50]}... (confidence: {source_info['confidence']:.2f})")

            time.sleep(0.5)

        # Sort by confidence
        all_sources.sort(key=lambda x: x["confidence"], reverse=True)
        print(f"  📊 Total sources found: {len(all_sources)}")
        return all_sources[:10]  # Top 10 sources

    def _tavily_search(self, query: str, max_results: int = 10) -> List[Dict]:
        """
        Execute Tavily Search API query
        """
        try:
            payload = {
                "api_key": self.api_key,
                "query": query,
                "search_depth": "advanced",
                "include_answer": False,
                "include_raw_content": False,
                "max_results": max_results
            }

            response = requests.post(self.base_url, json=payload)

            if response.status_code == 200:
                data = response.json()
                return data.get("results", [])
            else:
                print(f"    Tavily API error: {response.status_code} - {response.text[:100]}")
                return []

        except Exception as e:
            print(f"    Search error: {e}")
            return []

    def _calculate_confidence(self, result: Dict, podcast_name: str) -> float:
        """
        Calculate confidence that this result contains transcripts
        """
        title = result.get("title", "").lower()
        content = result.get("content", "").lower()
        url = result.get("url", "").lower()

        confidence = 0.0

        # Podcast name match
        if podcast_name.lower() in title:
            confidence += 0.4
        if podcast_name.lower() in content:
            confidence += 0.2

        # Transcript indicators
        transcript_words = ["transcript", "full text", "episode text", "read along"]
        for word in transcript_words:
            if word in title:
                confidence += 0.3
            if word in content:
                confidence += 0.2

        # URL structure
        if "transcript" in url:
            confidence += 0.2
        if "episode" in url:
            confidence += 0.1

        # Known good domains
        domain = self._extract_domain(url)
        if domain in ["github.com", "medium.com", "substack.com"]:
            confidence += 0.2

        return min(confidence, 1.0)

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            from urllib.parse import urlparse
            return urlparse(url).netloc
        except:
            return url

    def test_found_sources(self, sources: List[Dict]) -> List[Dict]:
        """
        Test each source to see if it actually contains transcripts
        """
        print(f"🧪 Testing {len(sources)} sources for actual transcripts...")

        working_sources = []

        for i, source in enumerate(sources):
            print(f"  [{i+1}/{len(sources)}] Testing: {source['domain']}")

            # Try to fetch and analyze the source
            transcript_sample = self._test_source_for_transcripts(source["url"])

            if transcript_sample:
                source["sample_transcript"] = transcript_sample[:500]  # First 500 chars
                source["sample_length"] = len(transcript_sample)
                source["status"] = "working"
                working_sources.append(source)
                print(f"    ✅ Working! Sample: {len(transcript_sample)} chars")
            else:
                source["status"] = "failed"
                print(f"    ❌ No transcripts found")

            time.sleep(1)

        return working_sources

    def _test_source_for_transcripts(self, url: str) -> Optional[str]:
        """
        Test if a source actually contains transcripts
        """
        try:
            response = self.session.get(url, timeout=15, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })

            if response.status_code == 200:
                content = response.text

                # Check for transcript indicators
                transcript_indicators = [
                    "transcript", "speaker:", "host:", "[music]",
                    "welcome to", "today we", "our guest"
                ]

                indicators_found = sum(1 for indicator in transcript_indicators
                                     if indicator.lower() in content.lower())

                # Must have multiple indicators and reasonable length
                if indicators_found >= 2 and len(content) > 5000:
                    return content

        except Exception as e:
            print(f"      Error testing {url}: {e}")

        return None

    def systematic_podcast_discovery(self, podcast_list: List[str] = None, limit: int = 10):
        """
        Run systematic discovery for multiple podcasts
        """
        if not podcast_list:
            # Load from RSS feeds file
            import csv
            podcast_list = []
            with open('config/podcast_rss_feeds.csv', 'r') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 2:
                        podcast_list.append(row[0].strip('"'))

        if limit:
            podcast_list = podcast_list[:limit]

        results = {}

        for i, podcast_name in enumerate(podcast_list):
            print(f"\n[{i+1}/{len(podcast_list)}] Processing: {podcast_name}")
            print("=" * 60)

            # Find sources
            sources = self.find_transcript_sources_for_podcast(podcast_name)

            if sources:
                # Test sources
                working_sources = self.test_found_sources(sources)

                results[podcast_name] = {
                    "total_sources_found": len(sources),
                    "working_sources": len(working_sources),
                    "sources": working_sources,
                    "timestamp": time.time()
                }

                print(f"✅ {podcast_name}: {len(working_sources)} working sources")
            else:
                results[podcast_name] = {
                    "total_sources_found": 0,
                    "working_sources": 0,
                    "sources": [],
                    "timestamp": time.time()
                }
                print(f"❌ {podcast_name}: No sources found")

            # Rate limiting
            time.sleep(2)

        # Save results
        output_file = "config/discovered_transcript_sources.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"\n🎉 Discovery complete! Results saved to: {output_file}")

        # Summary
        total_podcasts = len(results)
        podcasts_with_sources = len([p for p in results.values() if p['working_sources'] > 0])
        total_working_sources = sum(p['working_sources'] for p in results.values())

        print(f"📊 Summary:")
        print(f"  Podcasts processed: {total_podcasts}")
        print(f"  Podcasts with working sources: {podcasts_with_sources}")
        print(f"  Total working sources: {total_working_sources}")

        return results

# CLI interface
if __name__ == "__main__":
    import sys

    finder = TavilyTranscriptFinder()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "search":
            # Search for specific podcast
            podcast_name = sys.argv[2] if len(sys.argv) > 2 else "Acquired"
            sources = finder.find_transcript_sources_for_podcast(podcast_name)

            if sources:
                print(f"\n📋 Testing {len(sources)} sources...")
                working = finder.test_found_sources(sources)
                print(f"\n✅ {len(working)} working sources found for '{podcast_name}'")
                for source in working:
                    print(f"  {source['confidence']:.2f}: {source['domain']} - {source['title'][:60]}...")
            else:
                print(f"❌ No sources found for '{podcast_name}'")

        elif command == "discover":
            # Run systematic discovery
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
            finder.systematic_podcast_discovery(limit=limit)

        elif command == "test":
            # Test specific URL
            url = sys.argv[2] if len(sys.argv) > 2 else ""
            if url:
                transcript = finder._test_source_for_transcripts(url)
                if transcript:
                    print(f"✅ Found transcript: {len(transcript)} characters")
                    print(f"Sample: {transcript[:200]}...")
                else:
                    print("❌ No transcript found")

    else:
        print("""
Usage: python3 tavily_transcript_finder.py [search|discover|test] [args]

Commands:
  search [podcast]    - Search for transcript sources for specific podcast
  discover [limit]    - Run systematic discovery (default: 20 podcasts)
  test [url]          - Test if specific URL contains transcripts

Examples:
  python3 tavily_transcript_finder.py search "Acquired"
  python3 tavily_transcript_finder.py discover 50
  python3 tavily_transcript_finder.py test "https://github.com/user/repo"
        """)