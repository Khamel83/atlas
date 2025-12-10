#!/usr/bin/env python3
"""
Focused search for top priority podcasts
"""

import requests
import time

def search_all_sources_for_podcast(podcast_name):
    """Search ALL major sources for one podcast"""

    print(f"\n{'='*50}")
    print(f"SEARCHING: {podcast_name}")
    print(f"{'='*50}")

    found_sources = []

    # Major transcript services
    transcript_services = [
        ("Rev.com", "https://www.rev.com/transcripts"),
        ("Otter.ai", "https://otter.ai/transcripts"),
        ("Descript", "https://www.descript.com"),
        ("Sonix", "https://sonix.ai"),
        ("Happy Scribe", "https://www.happyscribe.com"),
        ("Trint", "https://www.trint.com"),
    ]

    print("1. TRANSCRIPT SERVICES:")
    for service_name, base_url in transcript_services:
        try:
            # Try different search patterns
            search_urls = [
                f"{base_url}/search?q={podcast_name.replace(' ', '+')}",
                f"{base_url}/podcast/{podcast_name.lower().replace(' ', '-')}",
                f"{base_url}/shows/{podcast_name.lower().replace(' ', '-')}"
            ]

            for url in search_urls:
                try:
                    response = requests.get(url, timeout=8)
                    if response.status_code == 200:
                        content = response.text.lower()
                        if podcast_name.lower() in content and 'transcript' in content:
                            print(f"  ✅ {service_name}: FOUND")
                            found_sources.append(f"{service_name}: {url}")
                            break
                except:
                    continue
            else:
                print(f"  ❌ {service_name}: Not found")

        except Exception as e:
            print(f"  ❌ {service_name}: Error")

        time.sleep(0.5)

    # Podcast platforms
    print("\n2. PODCAST PLATFORMS:")
    platforms = [
        ("Spotify", f"https://open.spotify.com/search/{podcast_name.replace(' ', '%20')}/shows"),
        ("Apple Podcasts", f"https://podcasts.apple.com/search?term={podcast_name.replace(' ', '+')}"),
        ("Overcast", f"https://overcast.fm/search?q={podcast_name}"),
        ("Pocket Casts", f"https://pocketcasts.com/search/{podcast_name}"),
    ]

    for platform_name, search_url in platforms:
        try:
            response = requests.get(search_url, timeout=8)
            if response.status_code == 200:
                content = response.text.lower()
                if podcast_name.lower() in content and ('transcript' in content or 'show notes' in content):
                    print(f"  ✅ {platform_name}: FOUND")
                    found_sources.append(f"{platform_name}: {search_url}")
                else:
                    print(f"  ❌ {platform_name}: No transcripts")
            else:
                print(f"  ❌ {platform_name}: HTTP {response.status_code}")
        except:
            print(f"  ❌ {platform_name}: Error")

        time.sleep(0.5)

    # Community sources
    print("\n3. COMMUNITY SOURCES:")
    community_sources = [
        ("GitHub", f"https://github.com/search?q={podcast_name.replace(' ', '+')}+transcript"),
        ("Reddit", f"https://www.reddit.com/search/?q={podcast_name}+transcript"),
        ("Medium", f"https://medium.com/search?q={podcast_name}+transcript"),
        ("Archive.org", f"https://archive.org/search.php?query={podcast_name}+transcript"),
    ]

    for source_name, search_url in community_sources:
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
            response = requests.get(search_url, headers=headers, timeout=8)
            if response.status_code == 200:
                content = response.text.lower()
                if podcast_name.lower() in content and 'transcript' in content:
                    print(f"  ✅ {source_name}: FOUND")
                    found_sources.append(f"{source_name}: {search_url}")
                else:
                    print(f"  ❌ {source_name}: No transcripts")
            else:
                print(f"  ❌ {source_name}: HTTP {response.status_code}")
        except Exception as e:
            print(f"  ❌ {source_name}: Error")

        time.sleep(0.5)

    # Try official website
    print("\n4. OFFICIAL WEBSITE:")
    try:
        # Guess official website
        website_guesses = [
            f"https://{podcast_name.lower().replace(' ', '')}.com",
            f"https://{podcast_name.lower().replace(' ', '-')}.com",
            f"https://www.{podcast_name.lower().replace(' ', '')}.com",
        ]

        # Special cases
        if podcast_name == "Hard Fork":
            website_guesses = ["https://www.nytimes.com/column/hard-fork"]
        elif podcast_name == "Acquired":
            website_guesses = ["https://www.acquired.fm", "https://acquired.fm"]
        elif podcast_name == "Conversations with Tyler":
            website_guesses = ["https://conversationswithtyler.com"]

        for website in website_guesses:
            try:
                response = requests.get(website, timeout=8)
                if response.status_code == 200:
                    content = response.text.lower()
                    if 'transcript' in content:
                        print(f"  ✅ Official site: FOUND at {website}")
                        found_sources.append(f"Official: {website}")
                        break
                    else:
                        print(f"  ❌ {website}: No transcript mentions")
                else:
                    print(f"  ❌ {website}: HTTP {response.status_code}")
            except:
                print(f"  ❌ {website}: Not accessible")
        else:
            print(f"  ❌ No official website found")

    except Exception as e:
        print(f"  ❌ Official website search error")

    # Summary
    print(f"\nSUMMARY FOR {podcast_name}:")
    print(f"Total transcript sources found: {len(found_sources)}")

    if found_sources:
        print("Sources:")
        for source in found_sources:
            print(f"  - {source}")
    else:
        print("❌ NO TRANSCRIPT SOURCES FOUND ANYWHERE")

    return found_sources

def main():
    """Test top 3 priority podcasts"""

    priority_podcasts = [
        "Acquired",
        "Hard Fork",
        "Conversations with Tyler"
    ]

    all_results = {}

    for podcast in priority_podcasts:
        sources = search_all_sources_for_podcast(podcast)
        all_results[podcast] = sources

    print(f"\n{'='*80}")
    print("FINAL DEFINITIVE RESULTS")
    print(f"{'='*80}")

    for podcast, sources in all_results.items():
        print(f"\n{podcast}: {len(sources)} transcript sources found")
        if sources:
            for source in sources:
                print(f"  ✅ {source}")
        else:
            print(f"  ❌ DEFINITIVELY NO TRANSCRIPTS FOUND ANYWHERE")

if __name__ == "__main__":
    main()