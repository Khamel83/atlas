#!/usr/bin/env python3
"""
Test script to verify expensive APIs are disabled
"""

import os
import sys
import subprocess

def main():
    print("🔍 Testing API key environment...")

    # Clear environment
    api_keys = [
        'GOOGLE_SEARCH_API_KEY',
        'GOOGLE_SEARCH_ENGINE_ID',
        'OPENAI_API_KEY',
        'ANTHROPIC_API_KEY'
    ]

    for key in api_keys:
        if key in os.environ:
            del os.environ[key]
            print(f"🚫 Cleared {key}")
        else:
            print(f"✅ {key} not set")

    print("\n🧪 Testing transcript lookup without expensive APIs...")

    # Run a fresh Python process to test
    test_script = '''
import os
from helpers.podcast_transcript_lookup import PodcastTranscriptLookup

print("Environment check:")
for key in ["GOOGLE_SEARCH_API_KEY", "GOOGLE_SEARCH_ENGINE_ID"]:
    print(f"  {key}: {bool(os.getenv(key))}")

print("\\nGoogle fallback status:")
from helpers.google_search_fallback import get_google_search_fallback
google = get_google_search_fallback()
print(f"  Enabled: {google.enabled}")
print(f"  API key: {bool(google.api_key)}")

print("\\nTesting transcript lookup...")
lookup = PodcastTranscriptLookup()
result = lookup.lookup_transcript("Accidental Tech Podcast", "656: A Lot of Apple Stuff")
print(f"  Success: {result.success}")
print(f"  Source: {result.source}")
print(f"  Error: {result.error_message}")
'''

    result = subprocess.run(
        [sys.executable, "-c", test_script],
        capture_output=True,
        text=True,
        cwd="/home/ubuntu/dev/atlas"
    )

    print("Test output:")
    print(result.stdout)

    if result.stderr:
        print("Test errors:")
        print(result.stderr)

    # Check if it's still using Google Search
    if "Source: google_search" in result.stdout:
        print("\n❌ Google Search is still being used!")
        print("💡 This suggests there's a cached instance or configuration issue.")
        return 1
    else:
        print("\n✅ Google Search appears to be properly disabled!")
        return 0

if __name__ == "__main__":
    sys.exit(main())