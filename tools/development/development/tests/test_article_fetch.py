#!/usr/bin/env python3
"""
Test Article Fetching - Find out why it's broken
"""

import sys
sys.path.append('/home/ubuntu/dev/atlas')

def test_single_article():
    print("🧪 TESTING SINGLE ARTICLE FETCH")
    print("="*50)

    # Test with ArticleManager instead of article_fetcher
    try:
        from helpers.article_manager import ArticleManager
        from helpers.config import load_config

        config = load_config()
        manager = ArticleManager(config)

        # Test with a simple URL
        test_url = "https://example.com"
        print(f"📰 Testing URL: {test_url}")

        result = manager.process_article(test_url)
        print(f"✅ Result: {result}")

        if result.success:
            print("✅ ARTICLE PROCESSING WORKS!")
        else:
            print(f"❌ Failed: {result.error}")

    except Exception as e:
        print(f"💥 ArticleManager error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_single_article()