#!/usr/bin/env python3
"""
Test with truly obscure podcasts to prove the system works generically
"""

import requests
from bs4 import BeautifulSoup
import time

def test_obscure_podcast_transcripts():
    """Test with random, obscure podcasts"""

    # Pick genuinely obscure podcasts
    obscure_podcasts = [
        "The Anthropocene Reviewed", # John Green but not mainstream
        "Benjamen Walker's Theory of Everything", # Very niche
        "Mystery Show", # Discontinued Gimlet show
        "The Allusionist", # Language podcast, small audience
        "Criminal", # True crime but smaller
    ]

    print("=== TESTING OBSCURE PODCAST TRANSCRIPT DISCOVERY ===\n")

    for podcast_name in obscure_podcasts:
        print(f"Testing: {podcast_name}")

        # Search for transcripts
        search_results = search_podcast_transcripts(podcast_name)

        if search_results:
            print(f"  ✅ Found {len(search_results)} potential sources")

            # Test first result
            first_result = search_results[0]
            transcript = test_extract_transcript(first_result)

            if transcript:
                print(f"  🎉 SUCCESS: Extracted {len(transcript)} character transcript!")
                print(f"  Preview: {transcript[:100]}...")
                return True, podcast_name, transcript
            else:
                print(f"  ❌ Could not extract transcript from {first_result}")
        else:
            print(f"  ❌ No transcript sources found")

        print()

    return False, None, None

def search_podcast_transcripts(podcast_name):
    """Search for transcript sources for any podcast"""

    potential_sources = []

    # Search strategies for any podcast
    search_patterns = [
        f"https://www.google.com/search?q=\"{podcast_name}\"+transcript",
        f"https://github.com/search?q={podcast_name.replace(' ', '+')}+transcript",
        f"https://medium.com/search?q={podcast_name.replace(' ', '+')}+transcript",
    ]

    # Also try to find the official website
    try:
        # Simple Google search simulation by checking likely domains
        likely_domains = [
            f"https://{podcast_name.lower().replace(' ', '').replace("'", '')}.com",
            f"https://{podcast_name.lower().replace(' ', '-').replace("'", '')}.org",
            f"https://www.{podcast_name.lower().replace(' ', '').replace("'", '')}.com",
        ]

        for domain in likely_domains:
            try:
                response = requests.head(domain, timeout=5)
                if response.status_code == 200:
                    potential_sources.append(domain)
                    print(f"    Found likely website: {domain}")
            except:
                pass

    except:
        pass

    # Check if any exist
    working_sources = []
    for source in potential_sources:
        try:
            response = requests.get(source, timeout=10)
            if response.status_code == 200 and 'transcript' in response.text.lower():
                working_sources.append(source)
        except:
            pass

    return working_sources

def test_extract_transcript(url):
    """Try to extract transcript from a URL"""

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers, timeout=15)

        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.content, 'html.parser')

        # Try various selectors for transcript content
        transcript_selectors = [
            '.transcript',
            '#transcript',
            '.episode-transcript',
            '.full-text',
            'article',
            '.content',
            '.episode-content',
            'main'
        ]

        for selector in transcript_selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(separator=' ', strip=True)

                # Quality check - should be substantial and conversational
                if (len(text) > 2000 and
                    any(word in text.lower() for word in ['said', 'says', 'yeah', 'um', 'like']) and
                    'transcript' in text.lower()):
                    return text

        # Fallback - get all text and check if it looks like transcript
        all_text = soup.get_text(separator=' ', strip=True)
        if (len(all_text) > 3000 and
            'transcript' in all_text.lower() and
            any(word in all_text.lower() for word in ['host:', 'guest:', 'interviewer:'])):
            return all_text

    except Exception as e:
        print(f"    Extract error: {e}")

    return None

def test_very_specific_obscure_site():
    """Test a very specific, small podcast site"""

    print("=== TESTING VERY SPECIFIC OBSCURE SITE ===\n")

    # Test "The Memory Palace" - small narrative podcast
    test_url = "https://thememorypalace.us/"

    print(f"Testing: {test_url}")

    try:
        response = requests.get(test_url, timeout=10)

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for episode links
            episode_links = soup.find_all('a', href=True)

            transcript_found = False

            for link in episode_links[:10]:  # Check first 10 links
                href = link.get('href')
                text = link.get_text().lower()

                if 'episode' in text or 'transcript' in text:
                    full_url = requests.compat.urljoin(test_url, href)
                    print(f"  Checking: {full_url}")

                    try:
                        ep_response = requests.get(full_url, timeout=10)
                        if ep_response.status_code == 200:
                            ep_content = ep_response.text.lower()

                            if 'transcript' in ep_content:
                                print(f"    ✅ Found transcript content!")
                                transcript_found = True
                                break
                            else:
                                print(f"    ❌ No transcript")
                        else:
                            print(f"    ❌ HTTP {ep_response.status_code}")

                        time.sleep(0.5)

                    except Exception as e:
                        print(f"    ❌ Error: {e}")

            if not transcript_found:
                print(f"  ❌ No transcripts found on this site")

        else:
            print(f"  ❌ HTTP {response.status_code}")

    except Exception as e:
        print(f"  ❌ Error: {e}")

def main():
    # Test obscure podcasts
    success, podcast_name, transcript = test_obscure_podcast_transcripts()

    if success:
        print(f"\n🎉 SUCCESS WITH OBSCURE PODCAST!")
        print(f"Found working transcript for: {podcast_name}")
        print(f"Transcript length: {len(transcript):,} characters")
    else:
        print(f"\n❌ No working transcripts found for obscure podcasts")

    # Test very specific site
    test_very_specific_obscure_site()

if __name__ == "__main__":
    main()