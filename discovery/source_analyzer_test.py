import unittest
from discovery.source_analyzer import SourceAnalyzer


class TestSourceAnalyzer(unittest.TestCase):

    def setUp(self):
        self.analyzer = SourceAnalyzer()

    def test_content_length_assessment(self):
        # Test short content
        short_content = "This is short content."
        score = self.analyzer._assess_content_length(short_content)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

        # Test long content
        long_content = "A" * 10000
        score = self.analyzer._assess_content_length(long_content)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_language_quality_assessment(self):
        # Test good quality content
        good_content = "This is well-written content with proper grammar and structure."
        score = self.analyzer._assess_language_quality(good_content)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_domain_extraction(self):
        url = "https://www.example.com/article"
        domain = self.analyzer._extract_domain(url)
        self.assertEqual(domain, "example.com")

    def test_domain_reputation(self):
        domain = "example.com"
        reputation = self.analyzer.build_domain_reputation(domain)
        self.assertIn("reputation_score", reputation)
        self.assertGreaterEqual(reputation["reputation_score"], 0.0)
        self.assertLessEqual(reputation["reputation_score"], 1.0)


if __name__ == "__main__":
    unittest.main()
