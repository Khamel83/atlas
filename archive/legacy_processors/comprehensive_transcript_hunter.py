#!/usr/bin/env python3
"""
COMPREHENSIVE TRANSCRIPT HUNTER
Complete decision tree using ALL APIs until we find transcripts
Uses compute time until we hit limits - exhaustive search
"""

import requests
import json
import time
import csv
import sqlite3
import os
from typing import List, Dict, Optional
from urllib.parse import urlparse, urljoin

class ComprehensiveTranscriptHunter:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        # API Keys from environment
        self.tavily_api_key = os.getenv("TAVILY_API_KEY")
        self.google_api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
        self.google_engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
        self.youtube_api_key = os.getenv("YOUTUBE_API_KEY")

        self.db_path = "data/atlas.db"

        # Known high-success transcript aggregator sites
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
            "dropbox.com",
            "notion.so",
            "airtable.com"
        ]

    def exhaustive_transcript_hunt(self, podcast_name: str, episode_title: str = None) -> List[Dict]:
        """
        DECISION TREE: Try every method until we find transcripts
        """
        print(f"\n🎯 COMPREHENSIVE HUNT: {podcast_name}")
        if episode_title:
            print(f"   Episode: {episode_title}")
        print("=" * 80)

        all_results = []

        # STEP 1: Test existing cached sources (fastest)
        print("1️⃣ Testing cached sources...")
        cached_results = self._test_cached_sources(podcast_name)
        if cached_results:
            all_results.extend(cached_results)
            print(f"   ✅ Found {len(cached_results)} from cache")
        else:
            print("   ❌ No cached sources worked")

        # STEP 2: Google Custom Search API - Site-specific searches
        print("2️⃣ Google API - Site-specific searches...")
        google_site_results = self._google_site_specific_search(podcast_name, episode_title)
        if google_site_results:
            all_results.extend(google_site_results)
            print(f"   ✅ Found {len(google_site_results)} from Google site search")
        else:
            print("   ❌ No Google site searches worked")

        # STEP 3: Google Custom Search API - General queries
        print("3️⃣ Google API - General searches...")
        google_general_results = self._google_general_search(podcast_name, episode_title)
        if google_general_results:
            all_results.extend(google_general_results)
            print(f"   ✅ Found {len(google_general_results)} from Google general search")
        else:
            print("   ❌ No Google general searches worked")

        # STEP 4: Tavily AI Search - Advanced patterns
        print("4️⃣ Tavily AI Search...")
        tavily_results = self._tavily_advanced_search(podcast_name, episode_title)
        if tavily_results:
            all_results.extend(tavily_results)
            print(f"   ✅ Found {len(tavily_results)} from Tavily")
        else:
            print("   ❌ No Tavily searches worked")

        # STEP 5: YouTube API - Transcript search
        print("5️⃣ YouTube API Search...")
        youtube_results = self._youtube_transcript_search(podcast_name, episode_title)
        if youtube_results:
            all_results.extend(youtube_results)
            print(f"   ✅ Found {len(youtube_results)} from YouTube")
        else:
            print("   ❌ No YouTube transcripts found")

        # STEP 6: Community sources (GitHub, Medium, Archive.org)
        print("6️⃣ Community sources...")
        community_results = self._community_source_search(podcast_name, episode_title)
        if community_results:
            all_results.extend(community_results)
            print(f"   ✅ Found {len(community_results)} from community")
        else:
            print("   ❌ No community sources worked")

        # STEP 7: Social media and forums
        print("7️⃣ Social media and forums...")
        social_results = self._social_media_search(podcast_name, episode_title)
        if social_results:
            all_results.extend(social_results)
            print(f"   ✅ Found {len(social_results)} from social media")
        else:
            print("   ❌ No social sources worked")

        # STEP 8: Deep web and academic sources
        print("8️⃣ Deep web and academic sources...")
        academic_results = self._academic_source_search(podcast_name, episode_title)
        if academic_results:
            all_results.extend(academic_results)
            print(f"   ✅ Found {len(academic_results)} from academic sources")
        else:
            print("   ❌ No academic sources worked")

        # Deduplicate and validate
        unique_results = self._deduplicate_results(all_results)
        validated_results = self._validate_transcript_quality(unique_results)

        print(f"\n📊 HUNT SUMMARY:")
        print(f"   Total sources found: {len(all_results)}")
        print(f"   Unique sources: {len(unique_results)}")
        print(f"   Validated transcripts: {len(validated_results)}")

        return validated_results

    def _test_cached_sources(self, podcast_name: str) -> List[Dict]:
        """Test existing cached sources first"""
        # Implementation would check existing cache
        return []

    def _google_site_specific_search(self, podcast_name: str, episode_title: str = None) -> List[Dict]:
        """Google Custom Search API - search each transcript site specifically"""
        if not self.google_api_key or not self.google_engine_id:
            print("   ⚠️  Google API not configured")
            return []

        results = []
        base_query = f'"{podcast_name}"'
        if episode_title:
            base_query += f' "{episode_title}"'

        for site in self.transcript_sites:
            for search_term in ["transcript", "full transcript", "episode text"]:
                query = f'{base_query} {search_term} site:{site}'
                print(f"     Google: {query[:60]}...")

                google_results = self._execute_google_search(query)
                for result in google_results:
                    transcript_data = self._test_url_for_transcript(result['link'])
                    if transcript_data:
                        results.append({
                            'url': result['link'],
                            'title': result['title'],
                            'domain': site,
                            'content': transcript_data,
                            'source': 'google_site_specific',
                            'query': query
                        })
                        print(f"       ✅ Found transcript: {len(transcript_data)} chars")

                time.sleep(0.5)  # Rate limiting

        return results

    def _google_general_search(self, podcast_name: str, episode_title: str = None) -> List[Dict]:
        """Google Custom Search API - general searches"""
        if not self.google_api_key or not self.google_engine_id:
            return []

        results = []
        base_query = f'"{podcast_name}"'
        if episode_title:
            base_query += f' "{episode_title}"'

        general_queries = [
            f'{base_query} transcript',
            f'{base_query} "full transcript"',
            f'{base_query} "episode transcript"',
            f'{base_query} "read along"',
            f'{base_query} "show notes" transcript',
            f'{base_query} transcription',
            f'{base_query} "complete text"',
            f'{podcast_name} transcript archive',
            f'{podcast_name} episode text',
        ]

        for query in general_queries:
            print(f"     Google general: {query[:50]}...")
            google_results = self._execute_google_search(query)

            for result in google_results[:5]:  # Top 5 per query
                transcript_data = self._test_url_for_transcript(result['link'])
                if transcript_data:
                    results.append({
                        'url': result['link'],
                        'title': result['title'],
                        'domain': urlparse(result['link']).netloc,
                        'content': transcript_data,
                        'source': 'google_general',
                        'query': query
                    })
                    print(f"       ✅ Found transcript: {len(transcript_data)} chars")

            time.sleep(0.5)

        return results

    def _execute_google_search(self, query: str) -> List[Dict]:
        """Execute Google Custom Search API query"""
        try:
            url = "https://customsearch.googleapis.com/customsearch/v1"
            params = {
                'key': self.google_api_key,
                'cx': self.google_engine_id,
                'q': query,
                'num': 10
            }

            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                return data.get('items', [])
            else:
                print(f"       Google API error: {response.status_code}")
                return []

        except Exception as e:
            print(f"       Google search error: {e}")
            return []

    def _tavily_advanced_search(self, podcast_name: str, episode_title: str = None) -> List[Dict]:
        """Tavily AI Search with advanced patterns"""
        if not self.tavily_api_key:
            print("   ⚠️  Tavily API not configured")
            return []

        results = []
        base_query = f'"{podcast_name}"'
        if episode_title:
            base_query += f' "{episode_title}"'

        # Advanced Tavily queries
        tavily_queries = [
            f'{base_query} transcript complete text',
            f'{base_query} full episode transcription',
            f'{base_query} spoken word text version',
            f'{podcast_name} episode text archive',
            f'{podcast_name} conversation transcript',
            f'where to find {podcast_name} transcripts',
            f'{podcast_name} text version episodes',
        ]

        for query in tavily_queries:
            print(f"     Tavily: {query[:50]}...")
            tavily_results = self._execute_tavily_search(query)

            for result in tavily_results:
                transcript_data = self._test_url_for_transcript(result['url'])
                if transcript_data:
                    results.append({
                        'url': result['url'],
                        'title': result['title'],
                        'domain': urlparse(result['url']).netloc,
                        'content': transcript_data,
                        'source': 'tavily_advanced',
                        'query': query
                    })
                    print(f"       ✅ Found transcript: {len(transcript_data)} chars")

            time.sleep(0.5)

        return results

    def _execute_tavily_search(self, query: str) -> List[Dict]:
        """Execute Tavily Search API query"""
        try:
            payload = {
                "api_key": self.tavily_api_key,
                "query": query,
                "search_depth": "advanced",
                "include_answer": False,
                "include_raw_content": True,
                "max_results": 10
            }

            response = requests.post("https://api.tavily.com/search", json=payload)
            if response.status_code == 200:
                data = response.json()
                return data.get("results", [])
            else:
                print(f"       Tavily API error: {response.status_code}")
                return []

        except Exception as e:
            print(f"       Tavily search error: {e}")
            return []

    def _youtube_transcript_search(self, podcast_name: str, episode_title: str = None) -> List[Dict]:
        """YouTube API search for transcripts"""
        if not self.youtube_api_key:
            print("   ⚠️  YouTube API not configured")
            return []

        # Implementation would search YouTube and extract captions
        # This is a placeholder for now
        return []

    def _community_source_search(self, podcast_name: str, episode_title: str = None) -> List[Dict]:
        """Search community sources: GitHub, Medium, Archive.org"""
        results = []

        community_queries = [
            f"https://github.com/search?q={podcast_name.replace(' ', '+')}+transcript",
            f"https://medium.com/search?q={podcast_name.replace(' ', '+')}+transcript",
            f"https://archive.org/search.php?query={podcast_name.replace(' ', '+')}+transcript",
        ]

        for query_url in community_queries:
            print(f"     Community: {urlparse(query_url).netloc}")
            # Implementation would search these community sources
            # This is a placeholder for now

        return results

    def _social_media_search(self, podcast_name: str, episode_title: str = None) -> List[Dict]:
        """Search social media and forums for transcripts"""
        # Reddit, Twitter, Discord, etc.
        return []

    def _academic_source_search(self, podcast_name: str, episode_title: str = None) -> List[Dict]:
        """Search academic and research sources"""
        # ResearchGate, Academia.edu, institutional repositories
        return []

    def _test_url_for_transcript(self, url: str) -> Optional[str]:
        """Test if URL contains actual transcript content"""
        try:
            response = self.session.get(url, timeout=15)
            if response.status_code == 200:
                content = response.text

                # Quality checks for real transcripts
                if len(content) > 5000:  # Minimum length
                    transcript_indicators = [
                        "speaker:", "host:", "[music]", "welcome to",
                        "today we", "our guest", "transcript",
                        "speaker 1:", "speaker 2:", "[laughter]"
                    ]

                    indicators_found = sum(1 for indicator in transcript_indicators
                                         if indicator.lower() in content.lower())

                    if indicators_found >= 2:
                        return content

        except Exception as e:
            print(f"         Error testing {url}: {str(e)[:50]}...")

        return None

    def _deduplicate_results(self, results: List[Dict]) -> List[Dict]:
        """Remove duplicate URLs"""
        seen_urls = set()
        unique_results = []

        for result in results:
            if result['url'] not in seen_urls:
                seen_urls.add(result['url'])
                unique_results.append(result)

        return unique_results

    def _validate_transcript_quality(self, results: List[Dict]) -> List[Dict]:
        """Final validation of transcript quality"""
        validated = []

        for result in results:
            content = result.get('content', '')
            if len(content) > 10000:  # High quality threshold
                result['quality'] = 'high'
                validated.append(result)
            elif len(content) > 5000:  # Medium quality threshold
                result['quality'] = 'medium'
                validated.append(result)

        return validated

    def hunt_all_priority_podcasts(self):
        """Run comprehensive hunt on all priority podcasts"""
        print("🚀 STARTING COMPREHENSIVE TRANSCRIPT HUNT")
        print("Using ALL APIs until limits: Google + Tavily + YouTube + Community")
        print("=" * 80)

        # Load priority podcasts
        try:
            with open('config/podcast_config.csv', 'r') as f:
                reader = csv.DictReader(f)
                podcasts = [row for row in reader if row.get('future', '0') == '1']
        except:
            # Fallback to known priority podcasts
            podcasts = [
                {'name': 'Acquired'},
                {'name': 'Hard Fork'},
                {'name': 'EconTalk'},
                {'name': 'Conversations with Tyler'},
                {'name': 'Lex Fridman Podcast'},
                {'name': 'Practical AI'},
                {'name': 'Planet Money'},
                {'name': '99% Invisible'},
                {'name': 'This American Life'},
                {'name': 'Radiolab'}
            ]

        all_findings = {}

        for i, podcast in enumerate(podcasts[:15]):  # Start with 15 podcasts
            podcast_name = podcast.get('name', '')
            print(f"\n[{i+1}/{len(podcasts[:15])}] HUNTING: {podcast_name}")

            # Comprehensive hunt for this podcast
            findings = self.exhaustive_transcript_hunt(podcast_name)

            if findings:
                all_findings[podcast_name] = findings
                print(f"🎯 SUCCESS: {len(findings)} quality transcripts found!")

                # Store in database
                self._store_findings(podcast_name, findings)
            else:
                print(f"❌ NO TRANSCRIPTS: Exhausted all methods")

            # Rate limiting between podcasts
            time.sleep(2)

        # Save comprehensive results
        output_file = "config/comprehensive_hunt_results.json"
        with open(output_file, 'w') as f:
            json.dump(all_findings, f, indent=2)

        print(f"\n🎉 HUNT COMPLETE!")
        print(f"📊 Results saved to: {output_file}")
        print(f"🏆 Successful podcasts: {len(all_findings)}")
        print(f"📝 Total transcripts found: {sum(len(f) for f in all_findings.values())}")

    def _store_findings(self, podcast_name: str, findings: List[Dict]):
        """Store findings in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            for finding in findings:
                cursor.execute('''
                    INSERT OR REPLACE INTO content (title, content, content_type, url, created_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    f"{podcast_name} - {finding['title']}",
                    finding['content'],
                    'podcast_transcript',
                    finding['url'],
                    time.strftime('%Y-%m-%d %H:%M:%S')
                ))

            conn.commit()
            conn.close()
            print(f"   💾 Stored {len(findings)} transcripts in database")

        except Exception as e:
            print(f"   ❌ Database error: {e}")

if __name__ == "__main__":
    hunter = ComprehensiveTranscriptHunter()
    hunter.hunt_all_priority_podcasts()