"""
Unit tests for the url_utils module.
"""

import os
import sys
from urllib.parse import urlparse


# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from helpers.url_utils import normalize_url


class TestUrlUtils:
    """Test cases for the url_utils module."""

    def test_normalize_url_basic(self):
        """Test basic URL normalization."""
        url = "https://example.com/path"
        normalized = normalize_url(url)
        assert normalized == "http://example.com/path"

    def test_normalize_url_with_www(self):
        """Test URL normalization with www prefix."""
        url = "https://www.example.com/path"
        normalized = normalize_url(url)
        assert normalized == "http://example.com/path"

    def test_normalize_url_with_default_ports(self):
        """Test URL normalization with default ports."""
        url1 = "http://example.com:80/path"
        url2 = "https://example.com:443/path"

        normalized1 = normalize_url(url1)
        normalized2 = normalize_url(url2)

        assert normalized1 == "http://example.com/path"
        assert (
            normalized2 == "http://example.com/path"
        )  # Note: https gets normalized to http

    def test_normalize_url_with_tracking_params(self):
        """Test URL normalization with tracking parameters."""
        url = "https://example.com/path?utm_source=twitter&id=123&utm_medium=social"
        normalized = normalize_url(url)

        # Parse the normalized URL to check query parameters
        parsed = urlparse(normalized)
        query = parsed.query

        assert "utm_source" not in query
        assert "utm_medium" not in query
        assert "id=123" in query
        assert normalized == "http://example.com/path?id=123"

    def test_normalize_url_with_multiple_slashes(self):
        """Test URL normalization with multiple slashes in path."""
        url = "https://example.com//path///subpath"
        normalized = normalize_url(url)
        assert normalized == "http://example.com/path/subpath"

    def test_normalize_url_with_empty_input(self):
        """Test URL normalization with empty input."""
        url = ""
        normalized = normalize_url(url)
        assert normalized == ""

    def test_normalize_url_with_none_input(self):
        """Test URL normalization with None input."""
        url = None
        normalized = normalize_url(url)
        assert normalized is None

    def test_normalize_url_case_sensitivity(self):
        """Test URL normalization with mixed case."""
        url = "HTTPS://ExAmPlE.CoM/PaTh"
        normalized = normalize_url(url)
        assert (
            normalized == "http://example.com/PaTh"
        )  # Path should remain case-sensitive

    def test_normalize_url_with_fbclid(self):
        """Test URL normalization with Facebook click ID."""
        url = "https://example.com/path?fbclid=123&param=value"
        normalized = normalize_url(url)
        assert normalized == "http://example.com/path?param=value"

    def test_normalize_url_with_gclid(self):
        """Test URL normalization with Google click ID."""
        url = "https://example.com/path?gclid=123&param=value"
        normalized = normalize_url(url)
        assert normalized == "http://example.com/path?param=value"

    def test_normalize_url_query_param_order(self):
        """Test URL normalization preserves query parameter order."""
        url = "https://example.com/path?b=2&a=1&c=3"
        normalized = normalize_url(url)
        assert normalized == "http://example.com/path?a=1&b=2&c=3"  # Should be sorted
