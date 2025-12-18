#!/usr/bin/env python3
"""
Demo Script for Atlas Block 15

This script demonstrates the core functionality of Atlas Block 15 implementation.
"""

import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

def demo_youtube_integration():
    """Demonstrate YouTube integration functionality"""
    print("🎥 YouTube Integration Demo")
    print("=" * 30)

    try:
        from integrations.youtube_history_importer import YouTubeHistoryImporter
        from integrations.youtube_api_client import YouTubeAPIClient
        from integrations.youtube_content_processor import YouTubeContentProcessor

        # Create sample data
        sample_history = [
            {
                'videoId': 'dQw4w9WgXcQ',
                'title': 'Watched Rick Astley - Never Gonna Give You Up',
                'channelName': 'RickAstleyVEVO',
                'time': '1640995200000000',  # Unix timestamp in microseconds
                'duration': 'PT3M32S'
            },
            {
                'videoId': 'jNQXAC9IVRw',
                'title': 'Watched YouTube History Introduction',
                'channelName': 'YouTube',
                'time': '1640995300000000',
                'duration': 'PT1M45S'
            }
        ]

        # Test YouTube History Importer
        importer = YouTubeHistoryImporter("dummy_path.json")
        videos = []
        for entry in sample_history:
            metadata = importer._extract_video_metadata(entry)
            if metadata:
                videos.append(metadata)

        print(f"✅ Parsed {len(videos)} videos from history")

        # Test YouTube Content Processor
        processor = YouTubeContentProcessor()
        processed_videos = processor.process_historical_videos(videos)
        print(f"✅ Processed {len(processed_videos)} videos through Atlas pipeline")

        # Test analytics generation
        analytics = processor.generate_watch_pattern_analytics(processed_videos)
        print(f"✅ Generated watch pattern analytics")

        return True

    except Exception as e:
        print(f"❌ YouTube integration demo failed: {e}")
        return False

def demo_github_detection():
    """Demonstrate GitHub detection functionality"""
    print("\n🔧 GitHub Detection Demo")
    print("=" * 30)

    try:
        from crawlers.github_detector import GitHubDetector

        # Create sample content with GitHub URLs
        sample_content = """
        Check out these great repositories:
        - https://github.com/python/cpython for the Python interpreter
        - https://github.com/facebook/react for the React library
        - https://github.com/tensorflow/tensorflow for machine learning
        """

        # Test GitHub Detector
        detector = GitHubDetector()
        urls = detector.detect_github_urls(sample_content)
        print(f"✅ Detected {len(urls)} GitHub URLs")

        # Test repository metadata extraction (simulated)
        print("✅ Repository metadata extraction would be performed here")

        return True

    except Exception as e:
        print(f"❌ GitHub detection demo failed: {e}")
        return False

def demo_tech_resource_crawling():
    """Demonstrate technical resource crawling functionality"""
    print("\n📚 Technical Resource Crawling Demo")
    print("=" * 40)

    try:
        from crawlers.tech_resource_crawler import TechResourceCrawler

        # Create sample content with documentation links
        sample_content = """
        For Python development, check out the official docs at https://docs.python.org/3/
        For React development, see https://reactjs.org/docs/getting-started.html
        """

        # Test Technical Resource Crawler
        crawler = TechResourceCrawler()
        urls = crawler.detect_documentation_links(sample_content)
        print(f"✅ Detected {len(urls)} documentation links")

        # Test code snippet extraction
        code_content = """
        Here's a Python code example:
        ```python
        def hello_world():
            print("Hello, World!")
            return True
        ```
        """
        snippets = crawler.extract_code_snippets(code_content)
        print(f"✅ Extracted {len(snippets)} code snippets")

        return True

    except Exception as e:
        print(f"❌ Technical resource crawling demo failed: {e}")
        return False

def demo_content_enhancement():
    """Demonstrate content enhancement functionality"""
    print("\n✨ Content Enhancement Demo")
    print("=" * 30)

    try:
        from crawlers.content_enhancer import ContentEnhancer

        # Create sample content
        sample_articles = [
            {
                'id': 'article_1',
                'title': 'Introduction to Python Programming',
                'content': 'Python is a versatile programming language. It is used for web development, data science, and automation.',
                'type': 'article'
            }
        ]

        # Create sample metadata
        sample_metadata = {
            'github_repos': [
                {
                    'full_name': 'python/cpython',
                    'url': 'https://github.com/python/cpython',
                    'description': 'The Python programming language',
                    'stars': 45000,
                    'language': 'python',
                    'topics': ['python', 'interpreter', 'programming-language']
                }
            ]
        }

        # Test Content Enhancer
        enhancer = ContentEnhancer()
        enhanced_articles = enhancer.enhance_content_with_metadata(sample_articles, sample_metadata)
        print(f"✅ Enhanced {len(enhanced_articles)} articles with metadata")

        # Test cross-reference system
        cross_ref_system = enhancer.create_cross_reference_system(enhanced_articles)
        print(f"✅ Created cross-reference system with {len(cross_ref_system['concepts'])} concepts")

        return True

    except Exception as e:
        print(f"❌ Content enhancement demo failed: {e}")
        return False

def main():
    """Run all demos"""
    print("Atlas Block 15 Demo")
    print("===================")

    demos = [
        demo_youtube_integration,
        demo_github_detection,
        demo_tech_resource_crawling,
        demo_content_enhancement
    ]

    passed = 0
    failed = 0

    for demo in demos:
        if demo():
            passed += 1
        else:
            failed += 1

    print("\n" + "=" * 40)
    print(f"Demo Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All demos completed successfully!")
        print("\nAtlas Block 15 is ready for use!")
        return True
    else:
        print("⚠️  Some demos failed!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)