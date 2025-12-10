#!/usr/bin/env python3
"""
Test script for Atlas Prometheus Setup
"""

import sys
import os
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_prometheus_setup():
    """Test the Prometheus setup module"""
    print("Testing Prometheus Setup Module...")

    try:
        from monitoring.prometheus_setup import (
            install_prometheus,
            configure_prometheus,
            create_atlas_metrics_exporter,
            setup_node_exporter,
            configure_prometheus_retention,
            create_prometheus_service
        )

        # Test that functions exist
        assert callable(install_prometheus)
        assert callable(configure_prometheus)
        assert callable(create_atlas_metrics_exporter)
        assert callable(setup_node_exporter)
        assert callable(configure_prometheus_retention)
        assert callable(create_prometheus_service)

        print("✅ Prometheus Setup Module test passed!")
        return True

    except Exception as e:
        print(f"❌ Prometheus Setup Module test failed: {e}")
        return False

def test_topic_clusterer():
    """Test the topic clusterer"""
    print("Testing Topic Clusterer...")

    try:
        from content.topic_clusterer import MultiPerspectiveSummarizer

        # Create clusterer
        clusterer = MultiPerspectiveSummarizer()

        # Test that the clusterer was created successfully
        assert clusterer is not None

        # Test summarization (since this is actually a summarizer)
        content = "Python is a high-level programming language with dynamic semantics. It is used for web development, data science, and automation."
        summary = clusterer.summarize_multiple_perspectives(content)
        assert isinstance(summary, dict)
        assert len(summary) > 0

        print("✅ Topic Clusterer test passed!")
        return True

    except Exception as e:
        print(f"❌ Topic Clusterer test failed: {e}")
        return False

def test_smart_recommender():
    """Test the smart recommender"""
    print("Testing Smart Recommender...")

    try:
        from content.smart_recommender import ContentRecommender

        # Create recommender
        recommender = ContentRecommender()

        # Test user profile addition
        user_profile = {
            'id': 'test_user',
            'preferences': {'reading_time': 'evening'},
            'interests': ['python', 'data-science'],
            'skills': ['intermediate'],
            'goals': ['learn-ml', 'career-change']
        }

        recommender.add_user_profile('test_user', user_profile)
        assert 'test_user' in recommender.user_profiles

        # Test content metadata addition
        content_metadata = {
            'id': 'test_content',
            'title': 'Python Programming Guide',
            'type': 'article',
            'categories': ['programming'],
            'tags': ['python', 'beginner'],
            'authors': ['John Doe'],
            'publication_date': '2023-05-01T10:00:00Z',
            'difficulty': 'beginner',
            'estimated_reading_time': 15,
            'language': 'en',
            'keywords': ['python', 'programming', 'tutorial'],
            'summary': 'Learn Python programming basics in this comprehensive tutorial.'
        }

        recommender.add_content_metadata('test_content', content_metadata)
        assert 'test_content' in recommender.content_metadata

        # Test interaction recording
        recommender.record_interaction('test_user', 'test_content', 'read', {'duration': 18})
        assert len(recommender.interaction_history['test_user']) == 1

        # Test recommendation generation
        recommendations = recommender.generate_recommendations('test_user', num_recommendations=5)
        assert isinstance(recommendations, list)

        print("✅ Smart Recommender test passed!")
        return True

    except Exception as e:
        print(f"❌ Smart Recommender test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("Running Atlas Prometheus Setup Tests")
    print("=" * 40)

    tests = [
        test_prometheus_setup,
        test_topic_clusterer,
        test_smart_recommender
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