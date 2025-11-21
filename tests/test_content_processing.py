#!/usr/bin/env python3
"""
Test script for Atlas Content Processing Modules
"""

import sys
import os
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_multilang_processor():
    """Test the multi-language processor"""
    print("Testing Multi-Language Processor...")

    try:
        from content.multilang_processor import MultiLanguageProcessor, Language

        # Create processor
        processor = MultiLanguageProcessor()

        # Test language detection
        english_text = "Python is a high-level programming language."
        detected_lang = processor.detect_language(english_text)
        assert detected_lang == Language.ENGLISH

        # Test text processing
        multilingual_content = {
            'en': 'Python is a high-level programming language.',
            'es': 'Python es un lenguaje de programación de alto nivel.',
            'fr': 'Python est un langage de programmation de haut niveau.'
        }

        processed_content = processor.process_multilingual_content(multilingual_content)
        assert isinstance(processed_content, dict)
        assert 'en' in processed_content
        assert 'es' in processed_content
        assert 'fr' in processed_content

        # Test translation
        translated_text = processor.translate_text(english_text, Language.SPANISH)
        assert isinstance(translated_text, str)
        assert len(translated_text) > 0

        print("✅ Multi-Language Processor test passed!")
        return True

    except Exception as e:
        print(f"❌ Multi-Language Processor test failed: {e}")
        return False

def test_enhanced_summarizer():
    """Test the enhanced summarizer"""
    print("Testing Enhanced Summarizer...")

    try:
        from content.enhanced_summarizer import EnhancedSummarizer

        # Create summarizer
        summarizer = EnhancedSummarizer()

        # Test content summarization
        content = """
        Python is a high-level programming language with dynamic semantics.
        It is used for web development, data science, and automation.
        Python has a simple syntax similar to English, making it easy to learn.
        The language supports multiple programming paradigms, including procedural,
        object-oriented, and functional programming.
        """

        # Test extractive summarization
        extractive_summary = summarizer.summarize(content, method='extractive', summary_length=2)
        assert isinstance(extractive_summary, str)
        assert len(extractive_summary) > 0

        # Test abstractive summarization
        abstractive_summary = summarizer.summarize(content, method='abstractive', summary_length=2)
        assert isinstance(abstractive_summary, str)
        assert len(abstractive_summary) > 0

        # Test keyword-based summarization
        keyword_summary = summarizer.summarize(content, method='keyword_based', summary_length=2)
        assert isinstance(keyword_summary, str)
        assert len(keyword_summary) > 0

        # Test sentence scoring summarization
        sentence_summary = summarizer.summarize(content, method='sentence_scoring', summary_length=2)
        assert isinstance(sentence_summary, str)
        assert len(sentence_summary) > 0

        print("✅ Enhanced Summarizer test passed!")
        return True

    except Exception as e:
        print(f"❌ Enhanced Summarizer test failed: {e}")
        return False

def test_topic_clusterer():
    """Test the multi-perspective summarizer (formerly topic clusterer)"""
    print("Testing Multi-Perspective Summarizer...")

    try:
        from content.topic_clusterer import MultiPerspectiveSummarizer

        # Create summarizer
        summarizer = MultiPerspectiveSummarizer()

        # Test multi-perspective summarization
        content = "Python is a high-level programming language with dynamic semantics. It is used for web development, data science, and automation. Python has a simple syntax similar to English, making it easy to learn. The language supports multiple programming paradigms, including procedural, object-oriented, and functional programming."

        # Test different perspectives
        perspectives = ['technical', 'business', 'academic']
        summaries = summarizer.summarize_multiple_perspectives(content, perspectives, summary_length=2)

        assert isinstance(summaries, dict)
        assert len(summaries) == len(perspectives)

        for perspective in perspectives:
            assert perspective in summaries
            assert isinstance(summaries[perspective], str)
            assert len(summaries[perspective]) > 0

        print("✅ Multi-Perspective Summarizer test passed!")
        return True

    except Exception as e:
        print(f"❌ Multi-Perspective Summarizer test failed: {e}")
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
            'reading_history': [],
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
    print("Running Atlas Content Processing Tests")
    print("=" * 40)

    tests = [
        test_multilang_processor,
        test_enhanced_summarizer,
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