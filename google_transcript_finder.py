#!/usr/bin/env python3
"""
Google-powered systematic transcript discovery
Uses Google Custom Search API to find transcript sources
"""

import requests
import json
import time
import sqlite3
from typing import List, Dict, Optional

class GoogleTranscriptFinder:
    def __init__(self, api_key: str = None, search_engine_id: str = None):
        # Set up Tavily Search API (better for AI-powered search)
        import os
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")
        self.base_url = "https://api.tavily.com/search"

        self.session = requests.Session()
        self.db_path = "data/atlas.db"

        # Known transcript aggregator sites
        self.transcript_sites = [
            "podscripts.co",
            "podsights.com",
            "happyscribe.com",
            "otter.ai",
            "scribie.com",
            "github.com",
            "medium.com",
            "substack.com",
            "archive.org",
            "youtube.com"
        ]

    def find_transcript_sources_for_podcast(self, podcast_name: str) -> List[Dict]:
        """
        Systematically find where transcripts exist for this podcast
        """
        print(f"🔍 Searching Google for '{podcast_name}' transcript sources...")

        all_sources = []

        # Strategy 1: Search each known aggregator site
        for site in self.transcript_sites:
            query = f'"{podcast_name}" transcript site:{site}'
            results = self._google_search(query)

            for result in results:
                source_info = {
                    "url": result["link"],
                    "title": result["title"],
                    "domain": site,
                    "snippet": result.get("snippet", ""),
                    "confidence": self._calculate_confidence(result, podcast_name)
                }

                if source_info["confidence"] > 0.5:
                    all_sources.append(source_info)
                    print(f"  ✅ Found on {site}: {result['title'][:60]}...")

            time.sleep(1)  # Rate limiting

        # Strategy 2: General Google search for transcripts
        general_queries = [
            f'"{podcast_name}" "full transcript"',
            f'"{podcast_name}" "episode transcript"',
            f'"{podcast_name}" "transcript archive"',
            f'"{podcast_name}" transcript -youtube'  # Exclude YouTube initially
        ]

        for query in general_queries:
            results = self._google_search(query)

            for result in results[:5]:  # Top 5 for each query
                if not any(source["url"] == result["link"] for source in all_sources):
                    source_info = {
                        "url": result["link"],
                        "title": result["title"],
                        "domain": self._extract_domain(result["link"]),
                        "snippet": result.get("snippet", ""),
                        "confidence": self._calculate_confidence(result, podcast_name)
                    }

                    if source_info["confidence"] > 0.3:
                        all_sources.append(source_info)
                        print(f"  ✅ General search: {result['title'][:60]}...")

            time.sleep(1)

        # Sort by confidence
        all_sources.sort(key=lambda x: x["confidence"], reverse=True)
        return all_sources[:10]  # Top 10 sources

    def _google_search(self, query: str, num_results: int = 10) -> List[Dict]:
        """
        Execute Tavily Search API query
        """
        try:
            payload = {
                "api_key": self.api_key,
                "query": query,
                "search_depth": "advanced",
                "include_answer": False,
                "include_raw_content": True,
                "max_results": num_results
            }

            response = requests.post(self.base_url, json=payload)

            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])

                # Convert Tavily format to Google-like format
                converted_results = []
                for result in results:
                    converted_results.append({
                        "link": result.get("url", ""),
                        "title": result.get("title", ""),
                        "snippet": result.get("content", "")[:200]  # Limit snippet
                    })

                return converted_results
            else:
                print(f"    Tavily API error: {response.status_code}")
                return []

        except Exception as e:
            print(f"    Search error: {e}")
            return []

    def _calculate_confidence(self, result: Dict, podcast_name: str) -> float:
        """
        Calculate confidence that this result contains transcripts
        """
        title = result.get("title", "").lower()
        snippet = result.get("snippet", "").lower()
        url = result.get("link", "").lower()

        confidence = 0.0

        # Podcast name match
        if podcast_name.lower() in title:
            confidence += 0.4
        if podcast_name.lower() in snippet:
            confidence += 0.2

        # Transcript indicators
        transcript_words = ["transcript", "full text", "episode text", "read along"]
        for word in transcript_words:
            if word in title:
                confidence += 0.3
            if word in snippet:
                confidence += 0.2

        # URL structure
        if "transcript" in url:
            confidence += 0.2
        if "episode" in url:
            confidence += 0.1

        # Known good domains
        domain = self._extract_domain(url)
        if domain in ["github.com", "medium.com", "substack.com"]:
            confidence += 0.1

        return min(confidence, 1.0)

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            from urllib.parse import urlparse
            return urlparse(url).netloc
        except:
            return url

    def build_podcast_source_database(self, limit: int = None) -> Dict:
        """
        Build complete database of transcript sources for all podcasts
        """
        print("🚀 Building comprehensive podcast transcript source database...")

        # Load podcast list
        import csv
        podcasts = []
        with open('config/podcast_rss_feeds.csv', 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2:
                    podcasts.append({
                        'name': row[0].strip('"'),
                        'rss_url': row[1].strip('"')
                    })

        if limit:
            podcasts = podcasts[:limit]

        source_database = {}

        for i, podcast in enumerate(podcasts):
            print(f"\n[{i+1}/{len(podcasts)}] Processing: {podcast['name']}")

            # Find transcript sources for this podcast
            sources = self.find_transcript_sources_for_podcast(podcast['name'])

            if sources:
                source_database[podcast['name']] = {
                    "sources": sources,
                    "last_updated": time.time(),
                    "total_sources": len(sources)
                }
                print(f"    📊 Found {len(sources)} potential sources")
            else:
                print(f"    ❌ No transcript sources found")

            # Rate limiting - be respectful to Google API
            time.sleep(2)

        # Save database
        output_file = "config/google_transcript_sources.json"
        with open(output_file, 'w') as f:
            json.dump(source_database, f, indent=2)

        print(f"\n🎉 Source database complete!")
        print(f"💾 Saved to: {output_file}")
        print(f"📊 Total podcasts with sources: {len([p for p in source_database.values() if p['sources']])}")

        return source_database

    def test_sources_and_extract_samples(self, source_database: Dict) -> Dict:
        """
        Test each source and extract sample transcripts to validate
        """
        print("🧪 Testing sources and extracting sample transcripts...")

        results = {}

        for podcast_name, data in source_database.items():
            print(f"\n📄 Testing sources for: {podcast_name}")
            results[podcast_name] = {"working_sources": [], "failed_sources": []}

            for source in data["sources"][:3]:  # Test top 3 sources
                print(f"  Testing: {source['domain']}")

                # Try to fetch and analyze the source
                transcript_sample = self._test_source_for_transcripts(source["url"])

                if transcript_sample:
                    source["sample_transcript"] = transcript_sample[:1000]  # First 1000 chars
                    source["sample_length"] = len(transcript_sample)
                    results[podcast_name]["working_sources"].append(source)
                    print(f"    ✅ Working! Sample: {len(transcript_sample)} chars")
                else:
                    results[podcast_name]["failed_sources"].append(source)
                    print(f"    ❌ No transcripts found")

                time.sleep(1)

        return results

    def _test_source_for_transcripts(self, url: str) -> Optional[str]:
        """
        Test if a source actually contains transcripts
        """
        try:
            response = self.session.get(url, timeout=10)
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

# CLI interface
if __name__ == "__main__":
    import sys

    # You need to get these from Google Cloud Console
    API_KEY = "YOUR_GOOGLE_API_KEY"  # Replace with actual key
    SEARCH_ENGINE_ID = "YOUR_SEARCH_ENGINE_ID"  # Replace with actual ID

    finder = GoogleTranscriptFinder(API_KEY, SEARCH_ENGINE_ID)

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "build":
            # Build source database for first 20 podcasts (testing)
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
            finder.build_podcast_source_database(limit)

        elif command == "test":
            # Load and test existing database
            with open("config/google_transcript_sources.json", 'r') as f:
                source_db = json.load(f)
            results = finder.test_sources_and_extract_samples(source_db)

            # Save test results
            with open("config/tested_transcript_sources.json", 'w') as f:
                json.dump(results, f, indent=2)

        elif command == "search":
            # Search for specific podcast
            podcast_name = sys.argv[2] if len(sys.argv) > 2 else "Acquired"
            sources = finder.find_transcript_sources_for_podcast(podcast_name)
            print(f"\n📊 Found {len(sources)} sources for '{podcast_name}':")
            for source in sources:
                print(f"  {source['confidence']:.2f}: {source['title'][:60]}...")

    else:
        print("""
Usage: python3 google_transcript_finder.py [build|test|search] [args]

Commands:
  build [limit]     - Build source database (default: 20 podcasts)
  test              - Test existing sources and extract samples
  search [podcast]  - Search for specific podcast sources

Examples:
  python3 google_transcript_finder.py build 50
  python3 google_transcript_finder.py search "Acquired"
  python3 google_transcript_finder.py test
        """)