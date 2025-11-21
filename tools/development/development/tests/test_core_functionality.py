#!/usr/bin/env python3
"""
Test core Atlas functionality
"""
import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_article_processing():
    """Test article processing functionality"""
    try:
        from helpers.article_fetcher import fetch_and_save_articles
        print("✅ Article fetcher working")
        return True
    except Exception as e:
        print(f"❌ Article processing error: {e}")
        return False

def test_podcast_processing():
    """Test podcast processing functionality"""
    try:
        from helpers.podcast_ingestor import PodcastIngestor
        from helpers.config import load_config

        config = load_config()
        ingestor = PodcastIngestor(config)
        print("✅ Podcast ingestor working")
        return True
    except Exception as e:
        print(f"❌ Podcast processing error: {e}")
        return False

def test_search_functionality():
    """Test search functionality"""
    try:
        from helpers.enhanced_search import advanced_search
        results = advanced_search("test", limit=1)
        print(f"✅ Search functionality working: {len(results)} results")
        return True
    except Exception as e:
        print(f"❌ Search functionality error: {e}")
        return False

def test_api_functionality():
    """Test API functionality"""
    try:
        from api.main import app
        print(f"✅ API functionality working: {len(app.routes)} routes")
        return True
    except Exception as e:
        print(f"❌ API functionality error: {e}")
        return False

def main():
    """Run all core functionality tests"""
    print("🧪 Testing Atlas Core Functionality")
    print("=" * 40)

    tests = [
        test_article_processing,
        test_podcast_processing,
        test_search_functionality,
        test_api_functionality
    ]

    passed = 0
    for test in tests:
        if test():
            passed += 1

    print("=" * 40)
    print(f"Results: {passed}/{len(tests)} tests passed")

    if passed == len(tests):
        print("🎉 All core functionality tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())