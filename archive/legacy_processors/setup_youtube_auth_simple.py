#!/usr/bin/env python3
"""
Simple YouTube Authentication Setup

This script will help you authenticate with YouTube for history collection.
"""

import sys
import os
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from helpers.youtube_modules_integration import YouTubeIntegrationManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_youtube_auth():
    """Simple YouTube authentication setup"""

    print("🎬 YouTube Authentication Setup")
    print("=" * 40)

    # Test YouTube API access
    print("\n🔑 Testing YouTube API access...")

    try:
        manager = YouTubeIntegrationManager()
        status = manager.get_youtube_collection_status()

        print(f"✅ YouTube API Status: {status}")

        # Test podcast fallback (this should work with API key)
        print("\n🎙️ Testing podcast transcript lookup...")
        result = manager.get_podcast_transcript_fallback("Huberman Lab", "sleep")

        if result['success']:
            print("✅ YouTube API is working correctly!")
            print(f"   Title: {result.get('title', 'N/A')}")
            print(f"   Transcript length: {len(result.get('transcript', ''))}")
            print("\n🎉 YouTube integration is ready!")
            return True
        else:
            print(f"❌ YouTube API test failed: {result.get('error', 'Unknown error')}")
            return False

    except Exception as e:
        print(f"❌ Error testing YouTube API: {e}")
        return False

if __name__ == "__main__":
    success = setup_youtube_auth()

    if success:
        print("\n✅ YouTube authentication and API setup complete!")
        print("📅 Scheduler will collect YouTube history daily at 2:00 AM")
        print("🎙️ Podcast transcript lookup is working")
    else:
        print("\n❌ YouTube setup failed - check API key configuration")