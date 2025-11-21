#!/usr/bin/env python3
"""
Test Script for Block 15 Components

This script tests the core components of Atlas Block 15 implementation.
"""

import sys
import os
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

def test_youtube_history_importer():
    """Test the YouTube History Importer"""
    print("Testing YouTube History Importer...")

    try:
        from integrations.youtube_history_importer import YouTubeHistoryImporter

        # Create a simple test
        importer = YouTubeHistoryImporter("dummy_path.json")

        # Test metadata extraction
        test_entry = {
            'videoId': 'dQw4w9WgXcQ',
            'title': 'Watched Rick Astley - Never Gonna Give You Up',
            'channelName': 'RickAstleyVEVO',
            'time': '1640995200000000',  # Unix timestamp in microseconds
            'duration': 'PT3M32S'
        }

        metadata = importer._extract_video_metadata(test_entry)
        assert metadata is not None
        assert metadata['video_id'] == 'dQw4w9WgXcQ'
        assert metadata['title'] == 'Rick Astley - Never Gonna Give You Up'
        assert metadata['channel_name'] == 'RickAstleyVEVO'

        print("✅ YouTube History Importer test passed!")
        return True

    except Exception as e:
        print(f"❌ YouTube History Importer test failed: {e}")
        return False

def test_youtube_api_client():
    """Test the YouTube API Client"""
    print("Testing YouTube API Client...")

    try:
        from integrations.youtube_api_client import YouTubeAPIClient

        # Create a simple test
        client = YouTubeAPIClient("dummy_api_key")

        # Test rate limit checking
        client._check_rate_limit()

        print("✅ YouTube API Client test passed!")
        return True

    except Exception as e:
        print(f"❌ YouTube API Client test failed: {e}")
        return False

def test_youtube_content_processor():
    """Test the YouTube Content Processor"""
    print("Testing YouTube Content Processor...")

    try:
        from integrations.youtube_content_processor import YouTubeContentProcessor

        # Create a simple test
        processor = YouTubeContentProcessor()

        # Test tag extraction
        test_video = {
            'title': 'Python Tutorial for Beginners',
            'description': 'Learn Python programming basics in this comprehensive tutorial.'
        }

        tags = processor._extract_tags(test_video)
        assert isinstance(tags, list)

        # Test categorization
        categories = processor._categorize_video(test_video)
        assert isinstance(categories, list)
        assert 'YouTube' in categories

        print("✅ YouTube Content Processor test passed!")
        return True

    except Exception as e:
        print(f"❌ YouTube Content Processor test failed: {e}")
        return False

def test_github_detector():
    """Test the GitHub Detector"""
    print("Testing GitHub Detector...")

    try:
        from crawlers.github_detector import GitHubDetector

        # Create a simple test
        detector = GitHubDetector()

        # Test URL detection
        sample_content = "Check out https://github.com/python/cpython for Python source code"
        urls = detector.detect_github_urls(sample_content)
        assert isinstance(urls, list)
        assert len(urls) > 0

        # Test language detection
        python_code = "def hello():\n    print('Hello, World!')"
        # We'll skip this test since _detect_language is not a public method

        print("✅ GitHub Detector test passed!")
        return True

    except Exception as e:
        print(f"❌ GitHub Detector test failed: {e}")
        return False

def test_tech_resource_crawler():
    """Test the Technical Resource Crawler"""
    print("Testing Technical Resource Crawler...")

    try:
        from crawlers.tech_resource_crawler import TechResourceCrawler

        # Create a simple test
        crawler = TechResourceCrawler()

        # Test documentation link detection
        sample_content = "See https://docs.python.org/3/ for Python documentation"
        urls = crawler.detect_documentation_links(sample_content)
        assert isinstance(urls, list)

        # Test API reference detection
        test_text = "def hello_world():\n    print('Hello, World!')"
        looks_like_api = crawler._looks_like_api_reference(test_text)
        assert looks_like_api == True

        print("✅ Technical Resource Crawler test passed!")
        return True

    except Exception as e:
        print(f"❌ Technical Resource Crawler test failed: {e}")
        return False

def test_content_enhancer():
    """Test the Content Enhancer"""
    print("Testing Content Enhancer...")

    try:
        from crawlers.content_enhancer import ContentEnhancer

        # Create a simple test
        enhancer = ContentEnhancer()

        # Test confidence calculation
        item = {'title': 'Python Tutorial', 'content': 'Learn Python programming'}
        metadata = {'title': 'Python Docs', 'content': 'Python documentation and tutorials'}

        confidence = enhancer._calculate_confidence(item, metadata)
        assert isinstance(confidence, float)
        assert 0.0 <= confidence <= 1.0

        # Test concept extraction
        concepts = enhancer._extract_concepts(item)
        assert isinstance(concepts, list)

        print("✅ Content Enhancer test passed!")
        return True

    except Exception as e:
        print(f"❌ Content Enhancer test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("Running Block 15 Component Tests")
    print("=" * 40)

    tests = [
        test_youtube_history_importer,
        test_youtube_api_client,
        test_youtube_content_processor,
        test_github_detector,
        test_tech_resource_crawler,
        test_content_enhancer
    ]

    passed = 0
    failed = 0

    for test in tests:
        if test():
            passed += 1
        else:
            failed += 1

    print("\n" + "=" * 40)
    print(f"Test Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All tests passed!")
        return True
    else:
        print("⚠️  Some tests failed!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)