#!/usr/bin/env python3
"""
Test script for Atlas AI Summarizer
"""

import sys
import os
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_ai_summarizer():
    """Test the AI summarizer"""
    print("Testing AI Summarizer...")

    try:
        from processing.ai_summarizer import AISummarizer

        # Create summarizer
        summarizer = AISummarizer()

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

        # Test multiple summaries generation
        all_summaries = summarizer.generate_multiple_summaries(content)
        assert isinstance(all_summaries, dict)
        assert len(all_summaries) > 0

        print("✅ AI Summarizer test passed!")
        return True

    except Exception as e:
        print(f"❌ AI Summarizer test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("Running Atlas AI Summarizer Tests")
    print("=" * 35)

    tests = [
        test_ai_summarizer
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