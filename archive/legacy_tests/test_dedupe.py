"""
Unit tests for the dedupe module.
"""

import hashlib
import os
import sys


# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from helpers.dedupe import link_uid
from helpers.url_utils import normalize_url


class TestDedupe:
    """Test cases for the dedupe module."""

    def test_link_uid_basic(self):
        """Test basic link_uid functionality."""
        url = "https://example.com/path"
        uid = link_uid(url)

        # Verify it's a 16-character hex string
        assert len(uid) == 16
        assert all(c in "0123456789abcdef" for c in uid)

    def test_link_uid_consistency(self):
        """Test that link_uid returns consistent results for the same URL."""
        url = "https://example.com/path?param=value"
        uid1 = link_uid(url)
        uid2 = link_uid(url)

        assert uid1 == uid2

    def test_link_uid_normalization(self):
        """Test that link_uid normalizes URLs before generating UIDs."""
        url1 = "https://example.com/path?utm_source=twitter"
        url2 = "http://www.example.com/path"
        url3 = "https://example.com:443/path"

        uid1 = link_uid(url1)
        uid2 = link_uid(url2)
        uid3 = link_uid(url3)

        # All these URLs should normalize to the same canonical form
        assert uid1 == uid2
        assert uid2 == uid3

    def test_link_uid_different_urls(self):
        """Test that link_uid generates different UIDs for different URLs."""
        url1 = "https://example.com/path1"
        url2 = "https://example.com/path2"

        uid1 = link_uid(url1)
        uid2 = link_uid(url2)

        assert uid1 != uid2

    def test_link_uid_implementation(self):
        """Test that link_uid is implemented as expected (SHA-1 hash of normalized URL)."""
        url = "https://www.example.com/path?utm_source=twitter"
        normalized = normalize_url(url)
        expected_uid = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:16]

        uid = link_uid(url)

        assert uid == expected_uid

    def test_link_uid_with_empty_input(self):
        """Test link_uid with empty input."""
        url = ""
        uid = link_uid(url)

        # Should still return a valid hash
        assert len(uid) == 16
        assert all(c in "0123456789abcdef" for c in uid)

    def test_link_uid_with_non_url_input(self):
        """Test link_uid with non-URL input."""
        # link_uid should work with any string, not just URLs
        text = "This is not a URL"
        uid = link_uid(text)

        # Should still return a valid hash
        assert len(uid) == 16
        assert all(c in "0123456789abcdef" for c in uid)

    def test_link_uid_with_unicode(self):
        """Test link_uid with Unicode characters."""
        url = "https://example.com/path/üñîçøðé"
        uid = link_uid(url)

        # Should handle Unicode properly
        assert len(uid) == 16
        assert all(c in "0123456789abcdef" for c in uid)
