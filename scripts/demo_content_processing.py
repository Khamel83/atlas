#!/usr/bin/env python3
"""
Demo script for Atlas Content Processing Modules

This script demonstrates all the content processing capabilities implemented for Atlas.
"""

import sys
import os
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

def demo_multilang_processor():
    """Demo the multi-language processor"""
    print("🌍 Atlas Multi-Language Processor Demo")
    print("=" * 50)

    try:
        from content.multilang_processor import MultiLanguageProcessor, Language

        # Create processor
        processor = MultiLanguageProcessor()

        # Sample multilingual content
        content = {
            'en': 'Python is a high-level programming language with dynamic semantics.',
            'es': 'Python es un lenguaje de programación de alto nivel con semántica dinámica.',
            'fr': 'Python est un langage de programmation de haut niveau avec une sémantique dynamique.',
            'de': 'Python ist eine hochrangige Programmiersprache mit dynamischer Semantik.'
        }

        # Process content
        print("Processing multilingual content...")
        processed_content = processor.process_multilang_content(content)

        # Display results
        for lang_code, text in processed_content.items():
            print(f"  {lang_code.upper()}: {text[:50]}...")

        # Detect language
        unknown_text = "Python è un linguaggio di programmazione di alto livello."
        detected_lang = processor.detect_language(unknown_text)
        print(f"\nDetected language: {detected_lang.name}")

        # Translate text
        translated_text = processor.translate_text(unknown_text, Language.ENGLISH)
        print(f"Translated to English: {translated_text}")

        print("\n✅ Multi-Language Processor demo completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Multi-Language Processor demo failed: {e}")
        return False

def demo_enhanced_summarizer():
    """Demo the enhanced summarizer"""
    print("\n📝 Atlas Enhanced Summarizer Demo")
    print("=" * 50)

    try:
        from content.enhanced_summarizer import EnhancedSummarizer

        # Create summarizer
        summarizer = EnhancedSummarizer()

        # Sample content
        content = """
        Python is a high-level programming language with dynamic semantics.
        It is used for web development, data science, and automation.
        Python has a simple syntax similar to English, making it easy to learn.
        The language supports multiple programming paradigms, including procedural,
        object-oriented, and functional programming.
        Python has a large standard library and a vibrant community that contributes
        to thousands of third-party modules and packages.
        Popular frameworks like Django and Flask make web development with Python straightforward.
        For data science, libraries like NumPy, Pandas, and Matplotlib provide powerful
        tools for analysis and visualization.
        Machine learning practitioners use Python with libraries like TensorFlow,
        PyTorch, and Scikit-learn.
        Python is also popular for automation tasks, scripting, and rapid prototyping.
        The language continues to evolve with regular updates and improvements to
        performance and features.
        """

        # Generate different types of summaries
        print("Generating enhanced content summaries...")

        # Extractive summary
        extractive_summary = summarizer.summarize(content, method='extractive', summary_length=2)
        print(f"\nExtractive Summary:\n{extractive_summary}")

        # Abstractive summary
        abstractive_summary = summarizer.summarize(content, method='abstractive', summary_length=2)
        print(f"\nAbstractive Summary:\n{abstractive_summary}")

        # Keyword-based summary
        keyword_summary = summarizer.summarize(content, method='keyword_based', summary_length=2)
        print(f"\nKeyword-based Summary:\n{keyword_summary}")

        # Sentence scoring summary
        sentence_summary = summarizer.summarize(content, method='sentence_scoring', summary_length=2)
        print(f"\nSentence Scoring Summary:\n{sentence_summary}")

        print("\n✅ Enhanced Summarizer demo completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Enhanced Summarizer demo failed: {e}")
        return False

def demo_topic_clusterer():
    """Demo the topic clusterer"""
    print("\n🔍 Atlas Multi-Perspective Clusterer Demo")
    print("=" * 50)

    try:
        from content.topic_clusterer import MultiPerspectiveSummarizer

        # Create clusterer
        clusterer = MultiPerspectiveSummarizer()

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
        print("Adding documents for clustering...")
        clusterer.add_documents(documents)

        # Perform clustering
        print("Clustering documents...")
        clusters = clusterer.cluster_documents()

        # Display results
        print(f"\nClustering Results ({len(clusters)} clusters):")
        for cluster in clusters:
            print(f"\nCluster {cluster['id']}:")
            print(f"  Documents: {', '.join(cluster['documents'])}")
            print(f"  Keywords: {', '.join(cluster['keywords'])}")

        print("\n✅ Multi-Perspective Clusterer demo completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Multi-Perspective Clusterer demo failed: {e}")
        return False

def demo_smart_recommender():
    """Demo the smart recommender"""
    print("\n🤖 Atlas Smart Recommender Demo")
    print("=" * 50)

    try:
        from content.smart_recommender import ContentRecommender

        # Create recommender
        recommender = ContentRecommender()

        # Sample user profiles
        user_profiles = [
            {
                'id': 'user1',
                'preferences': {'reading_time': 'evening', 'device': 'desktop'},
                'interests': ['python', 'data-science', 'machine-learning'],
                'reading_history': [],
                'skills': ['intermediate'],
                'goals': ['learn-ml', 'career-change']
            },
            {
                'id': 'user2',
                'preferences': {'reading_time': 'morning', 'device': 'mobile'},
                'interests': ['web-development', 'javascript', 'react'],
                'reading_history': [],
                'skills': ['beginner'],
                'goals': ['build-portfolio', 'learn-js']
            }
        ]

        # Add user profiles
        print("Adding user profiles...")
        for profile in user_profiles:
            recommender.add_user_profile(profile['id'], profile)

        # Sample content metadata
        content_items = [
            {
                'id': 'content1',
                'title': 'Introduction to Python Programming',
                'type': 'article',
                'categories': ['programming'],
                'tags': ['python', 'beginner'],
                'authors': ['John Doe'],
                'publication_date': '2023-01-15T10:00:00Z',
                'difficulty': 'beginner',
                'estimated_reading_time': 15,
                'language': 'en',
                'keywords': ['python', 'programming', 'tutorial'],
                'summary': 'Learn Python programming basics in this comprehensive tutorial.'
            },
            {
                'id': 'content2',
                'title': 'Machine Learning with Python',
                'type': 'article',
                'categories': ['data-science', 'machine-learning'],
                'tags': ['python', 'ml', 'scikit-learn'],
                'authors': ['Jane Smith'],
                'publication_date': '2023-02-20T14:30:00Z',
                'difficulty': 'intermediate',
                'estimated_reading_time': 25,
                'language': 'en',
                'keywords': ['machine-learning', 'python', 'data-science'],
                'summary': 'Explore machine learning concepts and implementation with Python.'
            }
        ]

        # Add content metadata
        print("Adding content metadata...")
        for content in content_items:
            recommender.add_content_metadata(content['id'], content)

        # Record sample interactions
        print("Recording user interactions...")
        interactions = [
            ('user1', 'content1', 'read', {'duration': 18}),
            ('user1', 'content2', 'like', {}),
            ('user2', 'content1', 'read', {'duration': 22})
        ]

        for user_id, content_id, interaction_type, data in interactions:
            recommender.record_interaction(user_id, content_id, interaction_type, data)

        # Generate recommendations
        print("\nGenerating content recommendations...")

        # For user1
        user1_recs = recommender.generate_recommendations('user1', num_recommendations=3)
        print(f"\nRecommendations for user1:")
        for rec in user1_recs:
            print(f"  - {rec['content_id']}: Score {rec['score']:.2f}")
            print(f"    Reason: {rec['reason']}")

        # For user2
        user2_recs = recommender.generate_recommendations('user2', num_recommendations=3)
        print(f"\nRecommendations for user2:")
        for rec in user2_recs:
            print(f"  - {rec['content_id']}: Score {rec['score']:.2f}")
            print(f"    Reason: {rec['reason']}")

        print("\n✅ Smart Recommender demo completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Smart Recommender demo failed: {e}")
        return False

def main():
    """Run all demos"""
    print("🚀 Atlas Content Processing Demos")
    print("=" * 50)

    demos = [
        demo_multilang_processor,
        demo_enhanced_summarizer,
        demo_topic_clusterer,
        demo_smart_recommender
    ]

    passed = 0
    failed = 0

    for demo in demos:
        if demo():
            passed += 1
        else:
            failed += 1

    print("\n" + "=" * 50)
    print(f"Demo Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All demos completed successfully!")
        print("\n🎯 Atlas Content Processing is ready for use!")
        return True
    else:
        print("⚠️  Some demos failed!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)