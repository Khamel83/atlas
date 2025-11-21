#!/usr/bin/env python3
"""
Test script for Atlas Semantic Search Engine
"""

import sys
import os
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_semantic_search_engine():
    """Test the semantic search engine"""
    print("Testing Semantic Search Engine...")

    try:
        from search.semantic_search import SemanticSearchEngine

        # Create search engine
        search_engine = SemanticSearchEngine()

        # Test document addition
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
        assert search_engine.document_count == 2

        # Test semantic search
        results = search_engine.search('python programming')
        assert isinstance(results, list)

        # Test semantic filtering
        filtered_results = search_engine.semantic_filter(
            'data',
            filters={'category': 'programming'}
        )
        assert isinstance(filtered_results, list)

        # Test index stats
        stats = search_engine.get_index_stats()
        assert isinstance(stats, dict)
        assert 'document_count' in stats
        assert 'embedding_dimension' in stats
        assert 'indexed_documents' in stats

        print("✅ Semantic Search Engine test passed!")
        return True

    except Exception as e:
        print(f"❌ Semantic Search Engine test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("Running Atlas Semantic Search Engine Tests")
    print("=" * 45)

    tests = [
        test_semantic_search_engine
    ]

    passed = 0
    failed = 0

    for test in tests:
        if test():
            passed += 1
        else:
            failed += 1

    print("\n" + "=" * 45)
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