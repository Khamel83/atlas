#!/usr/bin/env python3
"""
Test script for Atlas Source Analyzer
"""

import sys
import os
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_source_analyzer():
    """Test the source analyzer"""
    print("Testing Source Analyzer...")

    try:
        from discovery.source_analyzer import SourceAnalyzer

        # Create analyzer
        analyzer = SourceAnalyzer()

        # Sample content with GitHub URLs
        content = """
        Check out these great repositories:
        - https://github.com/python/cpython for the Python interpreter
        - https://github.com/facebook/react for the React library
        - https://github.com/tensorflow/tensorflow for machine learning

        Also see the official documentation:
        - https://docs.python.org/3/ for Python documentation
        - https://reactjs.org/docs/getting-started.html for React documentation

        And these technical resources:
        - https://stackoverflow.com/questions/12345678 for Python questions
        - https://medium.com/@user/python-tutorial for tutorials
        """

        # Analyze content
        analysis = analyzer.analyze_content(content)

        # Check that analysis contains expected keys
        expected_keys = [
            'github_repos', 'documentation_links', 'technical_resources',
            'code_examples', 'technical_terms', 'related_repositories',
            'related_tutorials', 'related_articles', 'analysis_timestamp'
        ]

        for key in expected_keys:
            assert key in analysis, f"Missing key: {key}"

        # Check data types
        assert isinstance(analysis['github_repos'], list)
        assert isinstance(analysis['documentation_links'], list)
        assert isinstance(analysis['technical_resources'], list)
        assert isinstance(analysis['code_examples'], list)
        assert isinstance(analysis['technical_terms'], list)
        assert isinstance(analysis['related_repositories'], list)
        assert isinstance(analysis['related_tutorials'], list)
        assert isinstance(analysis['related_articles'], list)

        # Check that GitHub repos were detected
        assert len(analysis['github_repos']) > 0, "No GitHub repos detected"

        # Check that documentation links were detected
        assert len(analysis['documentation_links']) > 0, "No documentation links detected"

        # Check that technical resources were detected
        assert len(analysis['technical_resources']) > 0, "No technical resources detected"

        print("✅ Source Analyzer test passed!")
        return True

    except Exception as e:
        print(f"❌ Source Analyzer test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("Running Atlas Source Analyzer Tests")
    print("=" * 35)

    tests = [
        test_source_analyzer
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