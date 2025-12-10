#!/usr/bin/env python3
"""
Exhaustive search for transcripts across ALL possible sources
"""

import requests
from bs4 import BeautifulSoup
import time
import json
from urllib.parse import quote, urljoin

class ExhaustiveTranscriptSearcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

        # ALL major transcript services and aggregators
        self.transcript_services = [
            "rev.com",
            "otter.ai",
            "trint.com",
            "sonix.ai",
            "descript.com",
            "happy-scribe.com",
            "transcribe.wreally.com",
            "gotranscript.com",
            "transcribeme.com",
            "podscribe.com",
            "podscribe.ai",
            "transcripts.fm",
            "podcasttranscripts.org"
        ]

        # Podcast platforms that might have transcripts
        self.podcast_platforms = [
            "spotify.com",
            "apple.com/podcasts",
            "google.com/podcasts",
            "overcast.fm",
            "pocketcasts.com",
            "castbox.fm",
            "podcast.app",
            "podchaser.com",
            "listennotes.com"
        ]

        # Ad networks and analytics that transcribe
        self.ad_networks = [
            "midroll.com",
            "advertisecast.com",
            "podcast.ad",
            "veritone.com",
            "chartable.com",
            "podsights.com",
            "claritas.com"
        ]

        # Community/fan sources
        self.community_sources = [
            "reddit.com",
            "github.com",
            "medium.com",
            "substack.com",
            "notion.so",
            "docs.google.com",
            "archive.org"
        ]

    def exhaustive_search(self, podcast_name):
        """Exhaustively search ALL sources for podcast transcripts"""

        print(f"\n{'='*60}")
        print(f"EXHAUSTIVE SEARCH: {podcast_name}")
        print(f"{'='*60}")

        results = {
            'podcast_name': podcast_name,
            'transcript_services': {},
            'podcast_platforms': {},
            'ad_networks': {},
            'community_sources': {},
            'total_sources_found': 0
        }

        # Search transcript services
        print(f"\n1. TRANSCRIPT SERVICES ({len(self.transcript_services)} services)")
        for service in self.transcript_services:
            found = self._search_transcript_service(service, podcast_name)
            results['transcript_services'][service] = found
            if found:
                results['total_sources_found'] += 1

        # Search podcast platforms
        print(f"\n2. PODCAST PLATFORMS ({len(self.podcast_platforms)} platforms)")
        for platform in self.podcast_platforms:
            found = self._search_podcast_platform(platform, podcast_name)
            results['podcast_platforms'][platform] = found
            if found:
                results['total_sources_found'] += 1

        # Search ad networks
        print(f"\n3. AD NETWORKS & ANALYTICS ({len(self.ad_networks)} networks)")
        for network in self.ad_networks:
            found = self._search_ad_network(network, podcast_name)
            results['ad_networks'][network] = found
            if found:
                results['total_sources_found'] += 1

        # Search community sources
        print(f"\n4. COMMUNITY SOURCES ({len(self.community_sources)} sources)")
        for source in self.community_sources:
            found = self._search_community_source(source, podcast_name)
            results['community_sources'][source] = found
            if found:
                results['total_sources_found'] += 1

        return results

    def _search_transcript_service(self, service, podcast_name):
        """Search a specific transcript service"""

        search_urls = [
            f"https://{service}/search?q={quote(podcast_name)}",
            f"https://www.{service}/search?q={quote(podcast_name)}",
            f"https://{service}/podcasts/{quote(podcast_name.lower().replace(' ', '-'))}",
            f"https://www.{service}/shows/{quote(podcast_name.lower().replace(' ', '-'))}"
        ]

        for url in search_urls:
            try:
                response = self.session.get(url, timeout=10)

                if response.status_code == 200:
                    content = response.text.lower()

                    # Look for podcast name + transcript indicators
                    if (podcast_name.lower() in content and
                        any(indicator in content for indicator in ['transcript', 'transcription', 'episode'])):

                        print(f"  ✅ {service}: Found at {url}")
                        return {'status': 'found', 'url': url, 'source_type': 'transcript_service'}

                elif response.status_code == 404:
                    continue
                else:
                    print(f"  ⚠️  {service}: HTTP {response.status_code}")

            except Exception as e:
                continue

        print(f"  ❌ {service}: Not found")
        return {'status': 'not_found'}

    def _search_podcast_platform(self, platform, podcast_name):
        """Search podcast platforms for transcripts"""

        # Different search patterns for each platform
        if "spotify" in platform:
            search_url = f"https://open.spotify.com/search/{quote(podcast_name)}/shows"
        elif "apple" in platform:
            search_url = f"https://podcasts.apple.com/search?term={quote(podcast_name)}"
        elif "google" in platform:
            search_url = f"https://podcasts.google.com/search/{quote(podcast_name)}"
        else:
            search_url = f"https://{platform}/search?q={quote(podcast_name)}"

        try:
            response = self.session.get(search_url, timeout=10)

            if response.status_code == 200:
                content = response.text.lower()

                if (podcast_name.lower() in content and
                    any(indicator in content for indicator in ['transcript', 'show notes', 'full text'])):

                    print(f"  ✅ {platform}: Found transcripts")
                    return {'status': 'found', 'url': search_url, 'source_type': 'platform'}

            print(f"  ❌ {platform}: No transcripts found")

        except Exception as e:
            print(f"  ❌ {platform}: Error - {str(e)[:50]}")

        return {'status': 'not_found'}

    def _search_ad_network(self, network, podcast_name):
        """Search ad networks that might transcribe for analytics"""

        search_urls = [
            f"https://{network}/podcast/{quote(podcast_name.lower().replace(' ', '-'))}",
            f"https://www.{network}/shows/{quote(podcast_name)}",
            f"https://{network}/analytics/{quote(podcast_name)}"
        ]

        for url in search_urls:
            try:
                response = self.session.get(url, timeout=10)

                if response.status_code == 200:
                    content = response.text.lower()

                    if (podcast_name.lower() in content and
                        any(indicator in content for indicator in ['transcript', 'text analysis', 'content analysis'])):

                        print(f"  ✅ {network}: Found at {url}")
                        return {'status': 'found', 'url': url, 'source_type': 'ad_network'}

            except Exception as e:
                continue

        print(f"  ❌ {network}: Not found")
        return {'status': 'not_found'}

    def _search_community_source(self, source, podcast_name):
        """Search community sources like Reddit, GitHub, etc."""

        if "reddit" in source:
            search_url = f"https://www.reddit.com/search/?q={quote(podcast_name + ' transcript')}"
        elif "github" in source:
            search_url = f"https://github.com/search?q={quote(podcast_name + ' transcript')}"
        elif "medium" in source:
            search_url = f"https://medium.com/search?q={quote(podcast_name + ' transcript')}"
        elif "substack" in source:
            search_url = f"https://substack.com/search/{quote(podcast_name + ' transcript')}"
        else:
            search_url = f"https://{source}/search?q={quote(podcast_name + ' transcript')}"

        try:
            response = self.session.get(search_url, timeout=10)

            if response.status_code == 200:
                content = response.text.lower()

                if (podcast_name.lower() in content and
                    'transcript' in content):

                    print(f"  ✅ {source}: Found community transcripts")
                    return {'status': 'found', 'url': search_url, 'source_type': 'community'}

            print(f"  ❌ {source}: No community transcripts")

        except Exception as e:
            print(f"  ❌ {source}: Error accessing")

        return {'status': 'not_found'}

def main():
    """Run exhaustive search on user's priority podcasts"""

    # User's priority podcasts from config
    priority_podcasts = [
        "Acquired",
        "Hard Fork",
        "Conversations with Tyler",
        "Accidental Tech Podcast",
        "Stratechery",
        "Sharp Tech with Ben Thompson",
        "Dithering",
        "Planet Money",
        "99% Invisible",
        "Radiolab"
    ]

    searcher = ExhaustiveTranscriptSearcher()

    all_results = []

    print("EXHAUSTIVE TRANSCRIPT SEARCH FOR ALL PRIORITY PODCASTS")
    print("=" * 80)

    for podcast in priority_podcasts:
        result = searcher.exhaustive_search(podcast)
        all_results.append(result)

        print(f"\nSUMMARY: {podcast}")
        print(f"Total sources found: {result['total_sources_found']}")

        time.sleep(2)  # Rate limiting

    # Final report
    print(f"\n{'='*80}")
    print("FINAL EXHAUSTIVE SEARCH REPORT")
    print(f"{'='*80}")

    for result in all_results:
        podcast = result['podcast_name']
        total = result['total_sources_found']

        print(f"\n{podcast}: {total} transcript sources found")

        if total > 0:
            # Show where found
            for category, sources in result.items():
                if category != 'podcast_name' and category != 'total_sources_found':
                    found_in_category = sum(1 for s in sources.values() if s.get('status') == 'found')
                    if found_in_category > 0:
                        print(f"  {category}: {found_in_category} sources")

    # Save results
    with open('exhaustive_transcript_search_results.json', 'w') as f:
        json.dump(all_results, f, indent=2)

    print(f"\nDetailed results saved to: exhaustive_transcript_search_results.json")

if __name__ == "__main__":
    main()