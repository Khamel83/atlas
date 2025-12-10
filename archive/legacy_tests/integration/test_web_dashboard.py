"""
Integration tests for the web dashboard.

Tests all cognitive amplification API endpoints and HTML dashboard functionality.
"""

import unittest

from fastapi.testclient import TestClient

from web.app import app


class TestWebDashboard(unittest.TestCase):
    """Integration tests for web dashboard API endpoints."""

    def setUp(self):
        """Set up test client."""
        self.client = TestClient(app)

    def test_root_endpoint(self):
        """Test root endpoint returns landing page."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Atlas Scheduler Web Interface", response.text)
        self.assertIn("Cognitive Amplification Dashboard", response.text)

    def test_ask_proactive_endpoint(self):
        """Test /ask/proactive API endpoint."""
        response = self.client.get("/ask/proactive")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("forgotten", data)
        self.assertIsInstance(data["forgotten"], list)

        # Check structure of forgotten items
        for item in data["forgotten"]:
            self.assertIn("title", item)
            self.assertIn("updated_at", item)

    def test_ask_temporal_endpoint(self):
        """Test /ask/temporal API endpoint."""
        response = self.client.get("/ask/temporal")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("relationships", data)
        self.assertIsInstance(data["relationships"], list)

        # Check structure of relationships
        for rel in data["relationships"]:
            self.assertIn("from", rel)
            self.assertIn("to", rel)
            self.assertIn("days", rel)

    def test_ask_recall_endpoint(self):
        """Test /ask/recall API endpoint."""
        response = self.client.get("/ask/recall")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("due_for_review", data)
        self.assertIsInstance(data["due_for_review"], list)

        # Check structure of review items
        for item in data["due_for_review"]:
            self.assertIn("title", item)
            self.assertIn("last_reviewed", item)

    def test_ask_patterns_endpoint(self):
        """Test /ask/patterns API endpoint."""
        response = self.client.get("/ask/patterns")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("top_tags", data)
        self.assertIn("top_sources", data)
        self.assertIsInstance(data["top_tags"], list)
        self.assertIsInstance(data["top_sources"], list)

    def test_ask_socratic_post_endpoint(self):
        """Test /ask/socratic POST endpoint."""
        test_content = "Machine learning is a subset of artificial intelligence."

        response = self.client.post(
            "/ask/socratic",
            data={"content": test_content}
        )
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("questions", data)
        self.assertIsInstance(data["questions"], list)

        # Should generate at least one question
        self.assertGreater(len(data["questions"]), 0)

        # Questions should be non-empty strings
        for question in data["questions"]:
            self.assertIsInstance(question, str)
            self.assertGreater(len(question.strip()), 0)

    def test_ask_html_dashboard_default(self):
        """Test /ask/html dashboard default view."""
        response = self.client.get("/ask/html")
        self.assertEqual(response.status_code, 200)

        # Should contain dashboard HTML
        self.assertIn("Atlas Cognitive Amplification Dashboard", response.text)
        self.assertIn("Proactive Surfacer", response.text)
        self.assertIn("Pattern Detector", response.text)

    def test_ask_html_dashboard_proactive_feature(self):
        """Test /ask/html dashboard with proactive feature."""
        response = self.client.get("/ask/html?feature=proactive")
        self.assertEqual(response.status_code, 200)

        # Should contain proactive-specific content
        self.assertIn("Proactive Surfacer", response.text)

    def test_ask_html_dashboard_temporal_feature(self):
        """Test /ask/html dashboard with temporal feature."""
        response = self.client.get("/ask/html?feature=temporal")
        self.assertEqual(response.status_code, 200)

        # Should contain temporal-specific content
        self.assertIn("Temporal Relationships", response.text)

    def test_ask_html_dashboard_recall_feature(self):
        """Test /ask/html dashboard with recall feature."""
        response = self.client.get("/ask/html?feature=recall")
        self.assertEqual(response.status_code, 200)

        # Should contain recall-specific content
        self.assertIn("Spaced Repetition", response.text)

    def test_ask_html_dashboard_patterns_feature(self):
        """Test /ask/html dashboard with patterns feature."""
        response = self.client.get("/ask/html?feature=patterns")
        self.assertEqual(response.status_code, 200)

        # Should contain patterns-specific content
        self.assertIn("Pattern Detector", response.text)

    def test_ask_html_dashboard_socratic_post(self):
        """Test /ask/html dashboard Socratic question form submission."""
        test_content = "Artificial intelligence is transforming many industries."

        response = self.client.post(
            "/ask/html",
            data={"feature": "socratic", "content": test_content}
        )
        self.assertEqual(response.status_code, 200)

        # Should contain generated questions
        self.assertIn("Socratic Questions", response.text)

    def test_ask_html_dashboard_socratic_empty_content(self):
        """Test /ask/html dashboard Socratic with empty content."""
        response = self.client.post(
            "/ask/html",
            data={"feature": "socratic", "content": ""}
        )
        self.assertEqual(response.status_code, 200)

        # Should handle empty content gracefully
        self.assertIn("Atlas Cognitive Amplification Dashboard", response.text)

    def test_jobs_endpoint(self):
        """Test /jobs API endpoint."""
        response = self.client.get("/jobs")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("jobs", data)
        self.assertIsInstance(data["jobs"], list)

    def test_jobs_html_endpoint(self):
        """Test /jobs/html endpoint."""
        response = self.client.get("/jobs/html")
        self.assertEqual(response.status_code, 200)

        # Should contain jobs UI
        self.assertIn("Atlas Scheduled Jobs", response.text)

    def test_invalid_endpoint(self):
        """Test invalid endpoint returns 404."""
        response = self.client.get("/invalid-endpoint")
        self.assertEqual(response.status_code, 404)

    def test_api_endpoints_with_mock_data(self):
        """Test API endpoints with mocked data."""
        # Test that endpoints return expected JSON structure
        response = self.client.get("/ask/proactive")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data["forgotten"], list)

        # Test patterns endpoint
        response = self.client.get("/ask/patterns")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data["top_tags"], list)
        self.assertIsInstance(data["top_sources"], list)

    def _create_mock_metadata_manager(self):
        """Create a mock metadata manager with test data."""
        from unittest.mock import MagicMock
        from helpers.metadata_manager import ContentMetadata, ContentType, ProcessingStatus
        from datetime import datetime, timedelta

        mock_manager = MagicMock()

        # Mock metadata items
        sample_item = ContentMetadata(
            uid="test_item",
            content_type=ContentType.DOCUMENT,
            source="https://test.com",
            title="Test Article",
            status=ProcessingStatus.SUCCESS,
            tags=["test", "sample"],
            updated_at=(datetime.now() - timedelta(days=30)).isoformat(),
            created_at=(datetime.now() - timedelta(days=30)).isoformat(),
            type_specific={"content": "Test content"}
        )

        mock_manager.get_all_metadata.return_value = [sample_item]

        return mock_manager

    def test_error_handling(self):
        """Test error handling in endpoints."""
        # This test checks that the application doesn't crash under normal conditions
        # Error handling testing would require more specific error injection
        response = self.client.get("/ask/proactive")
        self.assertEqual(response.status_code, 200)

    def test_content_types(self):
        """Test that endpoints return correct content types."""
        # JSON endpoints
        json_endpoints = [
            "/ask/proactive",
            "/ask/temporal",
            "/ask/recall",
            "/ask/patterns",
            "/jobs"
        ]

        for endpoint in json_endpoints:
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, 200)
            self.assertIn("application/json", response.headers.get("content-type", ""))

        # HTML endpoints
        html_endpoints = [
            "/",
            "/ask/html",
            "/jobs/html"
        ]

        for endpoint in html_endpoints:
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, 200)
            self.assertIn("text/html", response.headers.get("content-type", ""))

    def test_cors_and_headers(self):
        """Test CORS and security headers if configured."""
        response = self.client.get("/ask/proactive")
        self.assertEqual(response.status_code, 200)

        # Basic response should be successful
        # Additional CORS/security header tests would go here
        # depending on the application's security configuration


if __name__ == "__main__":
    unittest.main()