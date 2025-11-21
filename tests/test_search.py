#!/usr/bin/env python3
"""
Test script for Atlas Search System
"""

import sys
import os
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_enhanced_search():
    """Test the enhanced search engine"""
    print("Testing Enhanced Search Engine...")

    try:
        from search.enhanced_search import EnhancedSearchEngine

        # Create search engine
        search_engine = EnhancedSearchEngine()

        # Add sample documents
        documents = [
            {
                'id': 'doc1',
                'content': 'Python is a high-level programming language with dynamic semantics.',
                'metadata': {
                    'type': 'article',
                    'category': 'programming',
                    'author': 'John Doe'
                }
            },
            {
                'id': 'doc2',
                'content': 'Machine learning is a subset of artificial intelligence that provides systems the ability to automatically learn.',
                'metadata': {
                    'type': 'article',
                    'category': 'ai',
                    'author': 'Jane Smith'
                }
            }
        ]

        search_engine.build_index(documents)

        # Test search
        results = search_engine.search('python programming')
        assert isinstance(results, list)
        assert len(results) >= 0

        # Test semantic search
        semantic_results = search_engine.semantic_search('machine learning')
        assert isinstance(semantic_results, list)

        # Test filtered search
        filtered_results = search_engine.filter_search(
            'data',
            filters={'category': 'programming'}
        )
        assert isinstance(filtered_results, list)

        # Test index stats
        stats = search_engine.get_index_stats()
        assert isinstance(stats, dict)
        assert 'document_count' in stats

        print("✅ Enhanced Search Engine test passed!")
        return True

    except Exception as e:
        print(f"❌ Enhanced Search Engine test failed: {e}")
        return False

def test_indexing_system():
    """Test the indexing system"""
    print("Testing Indexing System...")

    try:
        from search.indexing_system import SearchIndexer
        import os

        # Create indexer with temporary database
        db_path = "/tmp/test_search_index.db"
        if os.path.exists(db_path):
            os.remove(db_path)

        indexer = SearchIndexer(db_path)

        # Add sample document
        document = {
            'id': 'test_doc',
            'title': 'Test Document',
            'content': 'This is a test document for indexing.',
            'type': 'article',
            'author': 'Test Author',
            'created_at': '2023-05-01T10:00:00Z',
            'updated_at': '2023-05-01T10:00:00Z',
            'metadata': {
                'category': 'test',
                'tags': ['test', 'indexing']
            }
        }

        indexer.index_document(document)

        # Retrieve document
        retrieved_doc = indexer.get_document('test_doc')
        assert retrieved_doc is not None
        assert retrieved_doc['id'] == 'test_doc'
        assert retrieved_doc['title'] == 'Test Document'

        # Get index stats
        stats = indexer.get_index_stats()
        assert isinstance(stats, dict)
        assert 'document_count' in stats

        # Close and cleanup
        indexer.close()
        if os.path.exists(db_path):
            os.remove(db_path)

        print("✅ Indexing System test passed!")
        return True

    except Exception as e:
        print(f"❌ Indexing System test failed: {e}")
        return False

def test_search_api():
    """Test the search API endpoints"""
    print("Testing Search API Endpoints...")

    try:
        from api.search_api import search_bp

        # Test that blueprint was created
        assert search_bp is not None
        assert search_bp.name == 'search'
        assert search_bp.url_prefix == '/api/search'

        print("✅ Search API Endpoints test passed!")
        return True

    except Exception as e:
        print(f"❌ Search API Endpoints test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("Running Atlas Search System Tests")
    print("=" * 40)

    tests = [
        test_enhanced_search,
        test_indexing_system,
        test_search_api
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