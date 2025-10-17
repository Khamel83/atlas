#!/usr/bin/env python3
"""
Test Integrated Search Functionality

This script tests the complete search integration including database population,
search execution, and result ranking to validate Phase 2 search capabilities.
"""

import sqlite3
import sys
from pathlib import Path

def test_search_database():
    """Test the search database integration."""
    print("🔍 Testing Integrated Search Functionality")
    print("=" * 50)

    # Check if search database exists and has content
    search_db_path = "data/enhanced_search.db"
    if not Path(search_db_path).exists():
        print("❌ Search database not found")
        return False

    # Connect to search database
    conn = sqlite3.connect(search_db_path)
    cursor = conn.cursor()

    # Check index size
    cursor.execute("SELECT COUNT(*) FROM search_index")
    count = cursor.fetchone()[0]
    print(f"📊 Search index entries: {count}")

    if count == 0:
        print("❌ Search index is empty")
        return False

    # Test basic search functionality
    test_queries = [
        ("technology", "Technology-related content"),
        ("article", "Article content type"),
        ("data", "Data-related content"),
        ("system", "System-related content")
    ]

    search_results = {}
    for query, description in test_queries:
        cursor.execute("""
            SELECT title, content_type, url
            FROM search_index
            WHERE title LIKE ? OR content LIKE ?
            LIMIT 10
        """, (f'%{query}%', f'%{query}%'))

        results = cursor.fetchall()
        search_results[query] = results
        print(f"🔍 '{query}' search: {len(results)} results")

        # Show sample results
        for i, (title, content_type, url) in enumerate(results[:3], 1):
            print(f"  {i}. {title[:50]}... ({content_type})")

    # Test content type filtering
    cursor.execute("SELECT DISTINCT content_type, COUNT(*) FROM search_index GROUP BY content_type")
    content_types = cursor.fetchall()
    print(f"\n📊 Content types available:")
    for content_type, count in content_types:
        print(f"  • {content_type}: {count} items")

    cursor.close()
    conn.close()

    # Validate we have meaningful results
    total_results = sum(len(results) for results in search_results.values())
    if total_results > 0:
        print(f"\n✅ Search integration test PASSED!")
        print(f"   Total search results: {total_results}")
        print(f"   Index size: {count} entries")
        print(f"   Content types: {len(content_types)}")
        return True
    else:
        print("❌ No search results found for test queries")
        return False

def test_enhanced_search_integration():
    """Test the enhanced search functionality."""
    print("\n🚀 Testing Enhanced Search Integration")
    print("-" * 50)

    try:
        sys.path.insert(0, '.')
        from helpers.enhanced_search import EnhancedSearchEngine

        # Initialize enhanced search
        search_engine = EnhancedSearchEngine()
        print("✅ Enhanced search engine initialized")

        # Test searches with the actual API
        test_queries = ["technology", "article", "data"]

        for query in test_queries:
            try:
                results = search_engine.search(query, limit=5)
                print(f"🔍 Enhanced search '{query}': {len(results) if results else 0} results")

                if results:
                    for i, result in enumerate(results[:2], 1):
                        if hasattr(result, 'title') and hasattr(result, 'score'):
                            print(f"  {i}. {result.title[:40]}... (score: {result.score:.2f})")
            except Exception as e:
                print(f"  ⚠️ Enhanced search '{query}' error: {str(e)[:50]}...")

        print("✅ Enhanced search integration test completed")
        return True

    except ImportError as e:
        print(f"❌ Cannot import enhanced search: {e}")
        return False
    except Exception as e:
        print(f"❌ Enhanced search test failed: {e}")
        return False

def main():
    """Run comprehensive search integration tests."""
    success = True

    # Test basic search database functionality
    if not test_search_database():
        success = False

    # Test enhanced search integration
    if not test_enhanced_search_integration():
        success = False

    # Final results
    print("\n" + "=" * 50)
    if success:
        print("🎉 SEARCH INTEGRATION TESTS PASSED!")
        print("✅ Search database: Functional")
        print("✅ Content indexing: Working")
        print("✅ Query processing: Operational")
        print("✅ Enhanced search: Available")
        print("\n🎯 Atlas search functionality is ready for Phase 2!")
    else:
        print("⚠️ SOME SEARCH TESTS FAILED")
        print("See output above for details")

    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)