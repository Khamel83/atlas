#!/usr/bin/env python3
"""
Find more transcript sources using search
"""

import requests
from bs4 import BeautifulSoup
import time
import random

def search_for_transcripts(podcast_name):
    """Search for transcript sources for a podcast"""

    print(f"\n=== Searching for {podcast_name} transcripts ===")

    # Known transcript-hosting sites to check
    sites_to_check = [
        f"https://www.podscribe.com/search?q={podcast_name.replace(' ', '+')}",
        f"https://medium.com/search?q={podcast_name.replace(' ', '+')}+transcript",
        f"https://substack.com/search/{podcast_name.replace(' ', '%20')}%20transcript",
    ]

    found_sources = []

    # Also try direct site searches
    podcast_sites = {
        "Hard Fork": ["nytimes.com/column/hard-fork"],
        "Acquired": ["acquired.fm", "acquired.co"],
        "Accidental Tech Podcast": ["atp.fm"],
        "99% Invisible": ["99percentinvisible.org"],
    }

    if podcast_name in podcast_sites:
        for site in podcast_sites[podcast_name]:
            sites_to_check.append(f"https://{site}")

    for site_url in sites_to_check:
        try:
            print(f"Checking: {site_url}")

            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }

            response = requests.get(site_url, headers=headers, timeout=10)

            if response.status_code == 200:
                content = response.text.lower()

                if 'transcript' in content:
                    print(f"  ✅ Found 'transcript' mention!")
                    found_sources.append(site_url)
                else:
                    print(f"  ❌ No transcript mentions")
            else:
                print(f"  ❌ HTTP {response.status_code}")

            time.sleep(random.uniform(1, 2))

        except Exception as e:
            print(f"  ❌ Error: {e}")

    return found_sources

def check_known_transcript_sites():
    """Check known sites that aggregate transcripts"""

    print("=== Checking Known Transcript Aggregators ===")

    known_sites = [
        "https://www.rev.com/blog/transcript-category/podcast-transcripts",
        "https://otter.ai/transcripts",
    ]

    for site in known_sites:
        try:
            print(f"\nChecking: {site}")

            response = requests.get(site, timeout=10)

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')

                # Look for podcast names
                text = soup.get_text().lower()

                podcasts_to_check = ["hard fork", "acquired", "accidental tech", "conversations with tyler"]

                found_podcasts = []
                for podcast in podcasts_to_check:
                    if podcast in text:
                        found_podcasts.append(podcast)

                if found_podcasts:
                    print(f"  ✅ Found: {', '.join(found_podcasts)}")
                else:
                    print(f"  ❌ No target podcasts found")

            else:
                print(f"  ❌ HTTP {response.status_code}")

        except Exception as e:
            print(f"  ❌ Error: {e}")

def test_specific_podcast_sites():
    """Test specific known podcast sites for transcripts"""

    print("\n=== Testing Specific Podcast Sites ===")

    sites_to_test = [
        ("ATP", "https://atp.fm/"),
        ("99% Invisible", "https://99percentinvisible.org/"),
        ("Planet Money", "https://www.npr.org/sections/money/"),
    ]

    for podcast_name, site_url in sites_to_test:
        try:
            print(f"\nTesting {podcast_name}: {site_url}")

            response = requests.get(site_url, timeout=10)

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')

                # Look for episode links
                episode_links = []

                link_selectors = ['a[href*="episode"]', 'a[href*="/episodes/"]', '.episode a']

                for selector in link_selectors:
                    links = soup.select(selector)
                    episode_links.extend(links[:5])  # Limit to 5 for testing

                print(f"  Found {len(episode_links)} episode links")

                # Test first episode for transcript
                if episode_links:
                    first_link = episode_links[0]
                    episode_url = requests.compat.urljoin(site_url, first_link.get('href', ''))

                    print(f"  Testing episode: {episode_url}")

                    episode_response = requests.get(episode_url, timeout=10)
                    if episode_response.status_code == 200:
                        episode_content = episode_response.text.lower()

                        if 'transcript' in episode_content:
                            print(f"    ✅ Episode has transcript content!")
                        else:
                            print(f"    ❌ No transcript on episode page")
                    else:
                        print(f"    ❌ Episode HTTP {episode_response.status_code}")

            else:
                print(f"  ❌ HTTP {response.status_code}")

            time.sleep(1)

        except Exception as e:
            print(f"  ❌ Error: {e}")

def main():
    print("=== SEARCHING FOR MORE TRANSCRIPT SOURCES ===")

    # Test known sites
    check_known_transcript_sites()

    # Test specific podcasts
    podcasts_to_search = ["Hard Fork", "Acquired", "Accidental Tech Podcast"]

    all_sources = []

    for podcast in podcasts_to_search:
        sources = search_for_transcripts(podcast)
        all_sources.extend(sources)

    # Test specific sites
    test_specific_podcast_sites()

    print(f"\n=== SUMMARY ===")
    print(f"Found {len(all_sources)} potential transcript sources")

    for source in all_sources:
        print(f"  - {source}")

if __name__ == "__main__":
    main()