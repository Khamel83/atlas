#!/usr/bin/env python3
"""
Test ArticleFetcher Google Search Fallback Integration

This script tests the Google Search fallback functionality in the ArticleFetcher class.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from helpers.config import load_config
from helpers.article_strategies import ArticleFetcher

def test_article_google_fallback():
    """Test the ArticleFetcher with Google Search fallback"""
    print("🧪 Testing ArticleFetcher Google Search Fallback Integration")
    print("=" * 60)

    # Load configuration
    config = load_config()

    # Create ArticleFetcher instance
    fetcher = ArticleFetcher(config)

    # Test with a broken/non-existent URL that should trigger Google fallback
    test_url = "https://example.com/nonexistent-article-that-does-not-exist-123456"
    log_path = "/tmp/test_article_fallback.log"

    print(f"📄 Testing URL: {test_url}")
    print(f"📝 Log file: {log_path}")
    print()

    # This should go through all strategies and then hit Google fallback
    result = fetcher.fetch_with_fallbacks(test_url, log_path)

    print("🔍 Test Results:")
    print(f"   Success: {result.success}")
    print(f"   Error: {result.error}")
    if hasattr(result, 'metadata') and result.metadata:
        print(f"   Google Fallback Used: {result.metadata.get('google_search_fallback', False)}")
        if result.metadata.get('alternative_url'):
            print(f"   Alternative URL: {result.metadata.get('alternative_url')}")

    # Check log file for Google fallback activity
    if os.path.exists(log_path):
        print("\n📋 Recent log entries:")
        with open(log_path, 'r') as f:
            lines = f.readlines()
            for line in lines[-10:]:  # Show last 10 lines
                if 'Google Search' in line or 'fallback' in line:
                    print(f"   {line.strip()}")

    print("\n✅ Test completed!")

if __name__ == "__main__":
    test_article_google_fallback()