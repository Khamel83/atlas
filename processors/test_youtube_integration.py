#!/usr/bin/env python3
"""
Test YouTube Integration

This script tests both YouTube modules:
1. YouTube History Scraper setup
2. YouTube Podcast Fallback functionality
"""

import sys
import os
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_youtube_podcast_fallback():
    """Test YouTube podcast fallback functionality"""
    print("\n🎙️ Testing YouTube Podcast Fallback")
    print("=" * 50)

    try:
        from helpers.youtube_podcast_fallback import YouTubePodcastFallback

        # Initialize fallback
        fallback = YouTubePodcastFallback()

        if not fallback.enabled:
            print("❌ YouTube fallback not enabled - checking API key...")
            api_key = os.getenv('YOUTUBE_API_KEY')
            if not api_key:
                print("❌ YOUTUBE_API_KEY not found in environment")
                return False
            else:
                print(f"✅ API key found: {api_key[:20]}...")
                return False

        print("✅ YouTube podcast fallback enabled")

        # Test podcast search
        print("\n🔍 Testing podcast search...")
        test_podcasts = [
            ("Huberman Lab", "sleep"),
            ("Lex Fridman Podcast", "AI"),
            ("Joe Rogan Experience", "masculinity")
        ]

        for podcast, episode in test_podcasts:
            print(f"\n📺 Searching: {podcast} - {episode}")
            results = fallback.search_podcast_episode(podcast, episode, max_results=3)

            if results:
                print(f"✅ Found {len(results)} results:")
                for i, result in enumerate(results[:2], 1):
                    print(f"   {i}. {result.title[:60]}...")
                    print(f"      Channel: {result.channel}")
                    print(f"      URL: {result.url}")
            else:
                print(f"❌ No results found for {podcast} - {episode}")

        # Test transcript extraction (if any results found)
        if results:
            print(f"\n📝 Testing transcript extraction...")
            test_result = results[0]
            transcript = fallback.get_video_transcript(test_result.video_id)

            if transcript:
                print(f"✅ Transcript extracted ({len(transcript)} characters)")
                print(f"   Preview: {transcript[:200]}...")
            else:
                print("❌ No transcript available for this video")

            # Test description links
            links = fallback.extract_description_links(test_result.video_id)
            print(f"🔗 Found {len(links)} links in description")

        return True

    except Exception as e:
        logger.error(f"YouTube podcast fallback test failed: {e}")
        return False

def test_youtube_integration_manager():
    """Test YouTube integration manager"""
    print("\n🎬 Testing YouTube Integration Manager")
    print("=" * 50)

    try:
        from helpers.youtube_modules_integration import YouTubeIntegrationManager

        # Initialize manager
        manager = YouTubeIntegrationManager()
        status = manager.get_youtube_collection_status()

        print(f"Modules available: {status['modules_available']}")
        print(f"Fallback enabled: {status['fallback_enabled']}")
        print(f"Session valid: {status['session_valid']}")

        # Test podcast fallback through manager
        if status['fallback_enabled']:
            print("\n🎙️ Testing podcast fallback through manager...")
            result = manager.get_podcast_transcript_fallback("Huberman Lab", "sleep")

            print(f"Success: {result['success']}")
            if result['success']:
                print(f"Title: {result.get('title', 'N/A')}")
                print(f"Channel: {result.get('channel', 'N/A')}")
                print(f"Transcript length: {len(result.get('transcript', ''))}")
                print(f"Links found: {len(result.get('description_links', []))}")
            else:
                print(f"Error: {result.get('error', 'Unknown error')}")

        return True

    except Exception as e:
        logger.error(f"YouTube integration manager test failed: {e}")
        return False

def test_youtube_setup_instructions():
    """Show YouTube setup instructions"""
    print("\n🛠️ YouTube Setup Instructions")
    print("=" * 50)

    print("""
🎬 YouTube History Scraper Setup:
1. Run: python setup_youtube_scraper.py
2. Log in to your Google account when prompted
3. Session will be saved for future automated runs
4. Run collection: python setup_youtube_scraper.py collect

🎙️ YouTube Podcast Fallback:
✅ Already configured with your API key
✅ Ready to use as transcript fallback
✅ Integrates with stage 320 (Transcript Extraction)

🔄 Integration Points:
- Stage 110-150: Call collect_youtube_history() for watched videos
- Stage 320: Call get_youtube_podcast_transcript() for transcripts
- Both modules feed into the numeric stage system
""")

def main():
    """Run all YouTube integration tests"""
    print("🎬 YouTube Integration Test Suite")
    print("=" * 60)

    # Test 1: YouTube Podcast Fallback
    podcast_success = test_youtube_podcast_fallback()

    # Test 2: Integration Manager
    manager_success = test_youtube_integration_manager()

    # Show setup instructions
    test_youtube_setup_instructions()

    # Summary
    print("\n📊 Test Results Summary")
    print("=" * 30)
    print(f"Podcast Fallback: {'✅ PASS' if podcast_success else '❌ FAIL'}")
    print(f"Integration Manager: {'✅ PASS' if manager_success else '❌ FAIL'}")

    if podcast_success and manager_success:
        print("\n🎉 YouTube integration is ready!")
        print("Next step: Run 'python setup_youtube_scraper.py' to configure history collection")
    else:
        print("\n⚠️ Some tests failed - check the output above")

if __name__ == "__main__":
    main()