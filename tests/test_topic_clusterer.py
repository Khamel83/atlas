#!/usr/bin/env python3
"""
Test script for Atlas Topic Clusterer
"""

import sys
import os
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_topic_clusterer():
    """Test the topic clusterer"""
    print("Testing Topic Clusterer...")

    try:
        from content.topic_clusterer import TopicClusterer

        # Create clusterer
        clusterer = TopicClusterer()

        # Sample documents
        documents = [
            {
                'id': 'doc1',
                'content': 'Python is a high-level programming language with dynamic semantics. It is used for web development, data science, and automation.'
            },
            {
                'id': 'doc2',
                'content': 'Machine learning is a subset of artificial intelligence that provides systems the ability to automatically learn and improve from experience.'
            },
            {
                'id': 'doc3',
                'content': 'Data science combines statistics, mathematics, and computer science to extract insights from data. It involves data cleaning, data analysis, and data visualization.'
            }
        ]

        # Add documents
        clusterer.add_documents(documents)
        assert len(clusterer.documents) == 3

        # Perform clustering
        clusters = clusterer.cluster_documents()
        assert isinstance(clusters, list)

        # Check that clusters were created
        assert len(clusters) >= 1

        # Check cluster structure
        for cluster in clusters:
            assert 'id' in cluster
            assert 'documents' in cluster
            assert 'centroid' in cluster
            assert 'keywords' in cluster
            assert isinstance(cluster['documents'], list)
            assert isinstance(cluster['keywords'], list)

        print("✅ Topic Clusterer test passed!")
        return True

    except Exception as e:
        print(f"❌ Topic Clusterer test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("Running Atlas Topic Clusterer Tests")
    print("=" * 35)

    tests = [
        test_topic_clusterer
    ]

    passed = 0
    failed = 0

    for test in tests:
        if test():
            passed += 1
        else:
            failed += 1

    print("\n" + "=" * 35)
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