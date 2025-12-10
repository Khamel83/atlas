#!/usr/bin/env python3
"""
Test script for Atlas Analytics Engine
"""

import sys
import os
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_analytics_engine():
    """Test the analytics engine"""
    print("Testing Analytics Engine...")

    try:
        from helpers.analytics_engine import AnalyticsEngine

        # Create analytics engine
        engine = AnalyticsEngine()

        # Test content analysis
        content = "Python is a high-level programming language with dynamic semantics. It is used for web development, data science, and automation."
        metadata = {
            'title': 'Introduction to Python Programming',
            'author': 'John Doe',
            'categories': ['programming', 'technology'],
            'tags': ['python', 'beginner', 'tutorial']
        }

        analysis = engine.analyze_content(content, metadata)

        # Check that analysis contains expected keys
        expected_keys = [
            'word_count', 'char_count', 'sentence_count', 'paragraph_count',
            'readability_score', 'keywords', 'categories', 'sentiment',
            'quality_score', 'analysis_timestamp'
        ]

        for key in expected_keys:
            assert key in analysis, f"Missing key: {key}"

        # Check data types
        assert isinstance(analysis['word_count'], int)
        assert isinstance(analysis['char_count'], int)
        assert isinstance(analysis['sentence_count'], int)
        assert isinstance(analysis['paragraph_count'], int)
        assert isinstance(analysis['readability_score'], float)
        assert isinstance(analysis['keywords'], list)
        assert isinstance(analysis['categories'], list)
        assert isinstance(analysis['sentiment'], dict)
        assert isinstance(analysis['quality_score'], float)

        # Test user engagement tracking
        engagement_data = {
            'reading_time': 15,
            'word_count': analysis['word_count'],
            'categories': analysis['categories'],
            'completed': True
        }

        user_stats = engine.track_user_engagement('test_user', 'test_content', engagement_data)
        assert isinstance(user_stats, dict)
        assert 'user_id' in user_stats
        assert user_stats['user_id'] == 'test_user'

        # Test user analytics retrieval
        retrieved_stats = engine.get_user_analytics('test_user')
        assert retrieved_stats is not None
        assert retrieved_stats['user_id'] == 'test_user'

        # Test report generation
        report = engine.generate_report()
        assert isinstance(report, dict)
        assert 'report_generated' in report
        assert 'user_statistics' in report
        assert 'content_statistics' in report
        assert 'processing_statistics' in report

        print("✅ Analytics Engine test passed!")
        return True

    except Exception as e:
        print(f"❌ Analytics Engine test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("Running Atlas Analytics Engine Tests")
    print("=" * 40)

    tests = [
        test_analytics_engine
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