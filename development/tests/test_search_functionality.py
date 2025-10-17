#!/usr/bin/env python3
"""
Test search functionality to understand the issues
"""
import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_search_engines():
    """Test different search engines to understand the issues"""
    print("Testing search engines...")

    # Test 1: SearchPerformanceOptimizer
    try:
        from helpers.search_performance_optimizer import SearchPerformanceOptimizer
        optimizer = SearchPerformanceOptimizer()
        print("✅ SearchPerformanceOptimizer instantiated successfully")

        # Try a simple search
        try:
            results = optimizer.optimized_search("test", limit=1)
            print(f"✅ SearchPerformanceOptimizer search returned {len(results)} results")
        except Exception as e:
            print(f"❌ SearchPerformanceOptimizer search failed: {e}")

    except Exception as e:
        print(f"❌ SearchPerformanceOptimizer instantiation failed: {e}")

    # Test 2: AtlasSearchEngine
    try:
        from helpers.search_engine import AtlasSearchEngine
        search_engine = AtlasSearchEngine()
        print("✅ AtlasSearchEngine instantiated successfully")

        # Try a simple search
        try:
            results = search_engine.search("test", limit=1)
            print(f"✅ AtlasSearchEngine search returned {len(results.get('hits', []))} results")
        except Exception as e:
            print(f"❌ AtlasSearchEngine search failed: {e}")

    except Exception as e:
        print(f"❌ AtlasSearchEngine instantiation failed: {e}")

    # Test 3: EnhancedSearchEngine
    try:
        from helpers.enhanced_search import EnhancedSearchEngine
        enhanced_engine = EnhancedSearchEngine()
        print("✅ EnhancedSearchEngine instantiated successfully")

        # Try a simple search
        try:
            results = enhanced_engine.search("test", limit=1)
            print(f"✅ EnhancedSearchEngine search returned {len(results)} results")
        except Exception as e:
            print(f"❌ EnhancedSearchEngine search failed: {e}")

    except Exception as e:
        print(f"❌ EnhancedSearchEngine instantiation failed: {e}")

def test_advanced_search():
    """Test the advanced_search function directly"""
    print("\nTesting advanced_search function...")

    try:
        from helpers.enhanced_search import advanced_search
        results = advanced_search("test", limit=1)
        print(f"✅ advanced_search returned {len(results)} results")
        return True
    except Exception as e:
        print(f"❌ advanced_search failed: {e}")
        return False

def main():
    """Run all search tests"""
    print("🧪 Testing Atlas Search Functionality")
    print("=" * 40)

    test_search_engines()
    success = test_advanced_search()

    print("=" * 40)
    if success:
        print("🎉 Search functionality test completed!")
        return 0
    else:
        print("⚠️  Search functionality test failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())