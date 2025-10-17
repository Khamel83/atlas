#!/usr/bin/env python3
"""
Optimized Podcast Transcript Discovery
Systematic approach: RSS for episode lists, Google/aggregators for transcripts
"""

import requests
import feedparser
import sqlite3
import time
import json
import re
from urllib.parse import urljoin, urlparse
from typing import Dict, List, Optional, Tuple

class PodcastTranscriptDiscovery:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.db_path = "data/atlas.db"
        self.source_database = "config/podcast_transcript_sources.json"

    def discover_transcript_sources_for_podcast(self, podcast_name: str) -> Dict:
        """
        Step 1: For each podcast, find where transcripts live on the internet
        """
        print(f"🔍 Discovering transcript sources for: {podcast_name}")

        sources = {
            "podcast_name": podcast_name,
            "transcript_sites": [],
            "episode_pattern": None,
            "last_updated": time.time()
        }

        # Search Google for transcript sources
        google_queries = [
            f'"{podcast_name}" transcript site:',
            f'"{podcast_name}" full transcript',
            f'"{podcast_name}" episode transcript',
            f'"{podcast_name}" transcript archive'
        ]

        for query in google_queries:
            print(f"  Searching: {query}")
            results = self._google_search(query)

            for result in results[:10]:  # Top 10 results per query
                source_info = self._analyze_transcript_source(result['url'], podcast_name)
                if source_info:
                    sources["transcript_sites"].append(source_info)
                    print(f"    ✅ Found source: {source_info['domain']}")

        # Deduplicate by domain
        seen_domains = set()
        unique_sources = []
        for source in sources["transcript_sites"]:
            if source['domain'] not in seen_domains:
                unique_sources.append(source)
                seen_domains.add(source['domain'])

        sources["transcript_sites"] = unique_sources
        return sources

    def _google_search(self, query: str) -> List[Dict]:
        """Mock Google search - replace with actual Google API"""
        # TODO: Replace with actual Google Custom Search API
        # For now, return common transcript aggregator sites
        common_sites = [
            {"url": "https://podscripts.co", "title": "Podscripts"},
            {"url": "https://podsights.com", "title": "Podsights"},
            {"url": "https://happyscribe.com", "title": "Happy Scribe"},
            {"url": "https://otter.ai", "title": "Otter.ai"},
            {"url": "https://scribie.com", "title": "Scribie"},
            {"url": "https://github.com", "title": "GitHub"},
            {"url": "https://medium.com", "title": "Medium"},
            {"url": "https://substack.com", "title": "Substack"}
        ]
        return common_sites

    def _analyze_transcript_source(self, url: str, podcast_name: str) -> Optional[Dict]:
        """
        Analyze a potential transcript source to understand its structure
        """
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code != 200:
                return None

            content = response.text.lower()
            domain = urlparse(url).netloc

            # Check if this site has transcripts for this podcast
            podcast_indicators = [
                podcast_name.lower(),
                podcast_name.lower().replace(" ", "-"),
                podcast_name.lower().replace(" ", "_")
            ]

            transcript_indicators = [
                "transcript", "full text", "episode text",
                "read along", "show notes", "episode notes"
            ]

            has_podcast = any(indicator in content for indicator in podcast_indicators)
            has_transcripts = any(indicator in content for indicator in transcript_indicators)

            if has_podcast and has_transcripts:
                # Try to deduce episode pattern
                episode_pattern = self._deduce_episode_pattern(content, podcast_name)

                return {
                    "domain": domain,
                    "base_url": url,
                    "episode_pattern": episode_pattern,
                    "confidence": 0.8 if episode_pattern else 0.5,
                    "last_tested": time.time()
                }

        except Exception as e:
            print(f"    Error analyzing {url}: {e}")

        return None

    def _deduce_episode_pattern(self, content: str, podcast_name: str) -> Optional[str]:
        """
        Try to figure out how episodes are organized on this site
        """
        # Look for common patterns
        patterns = [
            r'episode-(\d+)',           # episode-123
            r'episode/(\d+)',           # episode/123
            r'ep-(\d+)',                # ep-123
            r'(\d+)-',                  # 123-episode-name
            r'/(\d+)/',                 # /123/
            r'#(\d+)',                  # #123
        ]

        for pattern in patterns:
            if re.search(pattern, content):
                return pattern

        return None

    def extract_episodes_from_source(self, podcast_name: str, source: Dict, episodes: List[Dict]) -> List[Dict]:
        """
        Step 2: For each episode, search the known transcript source
        """
        print(f"📄 Extracting from {source['domain']} for {podcast_name}")

        found_transcripts = []

        for episode in episodes[:10]:  # Test first 10 episodes
            episode_title = episode.get('title', '')
            episode_number = self._extract_episode_number(episode_title)

            # Try different search strategies
            search_urls = self._generate_episode_search_urls(source, episode_title, episode_number)

            for search_url in search_urls:
                transcript = self._fetch_transcript_from_url(search_url)
                if transcript and len(transcript) > 5000:
                    found_transcripts.append({
                        "title": episode_title,
                        "content": transcript,
                        "source_url": search_url,
                        "source_domain": source['domain']
                    })
                    print(f"    ✅ Found transcript: {episode_title[:50]}... ({len(transcript)} chars)")
                    break

            time.sleep(1)  # Rate limiting

        return found_transcripts

    def _extract_episode_number(self, title: str) -> Optional[str]:
        """Extract episode number from title"""
        # Common patterns
        patterns = [
            r'#(\d+)',           # #123
            r'Episode (\d+)',    # Episode 123
            r'Ep\.? (\d+)',      # Ep 123, Ep. 123
            r'(\d+):',           # 123: Title
            r'^(\d+)\s',         # 123 Title
        ]

        for pattern in patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def _generate_episode_search_urls(self, source: Dict, title: str, episode_number: Optional[str]) -> List[str]:
        """Generate possible URLs for this episode on this source"""
        base_url = source['base_url']
        domain = source['domain']

        search_urls = []

        # Strategy 1: Use episode number if available
        if episode_number:
            search_urls.extend([
                f"{base_url}/episode-{episode_number}",
                f"{base_url}/ep-{episode_number}",
                f"{base_url}/{episode_number}",
                f"{base_url}/episodes/{episode_number}",
            ])

        # Strategy 2: Use title-based URLs
        clean_title = title.lower().replace(' ', '-').replace(':', '').replace(',', '')
        search_urls.extend([
            f"{base_url}/{clean_title}",
            f"{base_url}/episodes/{clean_title}",
            f"{base_url}/transcript/{clean_title}",
        ])

        # Strategy 3: Search pages on the domain
        if 'github.com' in domain:
            search_urls.append(f"https://github.com/search?q={title.replace(' ', '+')}")
        elif 'medium.com' in domain:
            search_urls.append(f"https://medium.com/search?q={title.replace(' ', '+')}")

        return search_urls

    def _fetch_transcript_from_url(self, url: str) -> Optional[str]:
        """Fetch and extract transcript from URL"""
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                # Simple text extraction - can be enhanced
                content = response.text

                # Look for transcript content
                if len(content) > 10000 and any(word in content.lower() for word in ['transcript', 'speaker', 'host']):
                    return content[:100000]  # Limit size

        except Exception:
            pass

        return None

    def systematic_discovery_process(self):
        """
        Complete systematic process for all podcasts
        """
        print("🚀 Starting Systematic Podcast Transcript Discovery")

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

        source_database = {}
        total_transcripts_found = 0

        for i, podcast in enumerate(podcasts[:20]):  # Start with first 20
            print(f"\n[{i+1}/{len(podcasts[:20])}] Processing: {podcast['name']}")

            # Step 1: Discover transcript sources for this podcast
            sources = self.discover_transcript_sources_for_podcast(podcast['name'])

            if sources['transcript_sites']:
                # Step 2: Get episode list from RSS
                episodes = self._get_episodes_from_rss(podcast['rss_url'])

                # Step 3: Extract transcripts from each source
                for source in sources['transcript_sites']:
                    transcripts = self.extract_episodes_from_source(
                        podcast['name'], source, episodes
                    )

                    if transcripts:
                        total_transcripts_found += len(transcripts)
                        # Store transcripts in database
                        self._store_transcripts(transcripts)

                # Step 4: Save source mapping
                source_database[podcast['name']] = sources

            time.sleep(2)  # Rate limiting between podcasts

        # Save source database for future use
        with open(self.source_database, 'w') as f:
            json.dump(source_database, f, indent=2)

        print(f"\n🎉 Discovery Complete!")
        print(f"📊 Total transcripts found: {total_transcripts_found}")
        print(f"💾 Source database saved to: {self.source_database}")

    def _get_episodes_from_rss(self, rss_url: str) -> List[Dict]:
        """Get episode list from RSS feed"""
        try:
            feed = feedparser.parse(rss_url)
            episodes = []

            for entry in feed.entries[:50]:  # First 50 episodes
                episodes.append({
                    'title': entry.get('title', ''),
                    'link': entry.get('link', ''),
                    'published': entry.get('published', '')
                })

            return episodes
        except Exception as e:
            print(f"    Error parsing RSS: {e}")
            return []

    def _store_transcripts(self, transcripts: List[Dict]):
        """Store transcripts in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            for transcript in transcripts:
                cursor.execute('''
                    INSERT OR REPLACE INTO content (title, content, content_type, url, created_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    transcript['title'],
                    transcript['content'],
                    'podcast_transcript',
                    transcript['source_url'],
                    time.strftime('%Y-%m-%d %H:%M:%S')
                ))

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"Error storing transcripts: {e}")

if __name__ == "__main__":
    discovery = PodcastTranscriptDiscovery()
    discovery.systematic_discovery_process()