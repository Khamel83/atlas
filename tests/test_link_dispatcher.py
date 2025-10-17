"""
Unit tests for the link_dispatcher module.
"""

import os
import sys
from unittest.mock import patch


# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ingest.link_dispatcher import (detect_url_type, dispatch_url,
                                    is_duplicate, process_url_list)


class TestLinkDispatcher:
    """Test cases for the link_dispatcher module."""

    def test_detect_url_type_youtube(self):
        """Test detection of YouTube URLs."""
        youtube_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://www.youtube.com/embed/dQw4w9WgXcQ",
            "https://youtube.com/shorts/dQw4w9WgXcQ",
        ]

        for url in youtube_urls:
            assert detect_url_type(url) == "youtube"

    def test_detect_url_type_podcast(self):
        """Test detection of podcast URLs."""
        podcast_urls = [
            "https://podcasts.apple.com/us/podcast/the-daily/id1200361736",
            "https://open.spotify.com/episode/1234567890abcdef",
            "https://anchor.fm/podcast-name/episodes/episode-title-e12345",
            "https://soundcloud.com/username/track-name",
        ]

        for url in podcast_urls:
            assert detect_url_type(url) == "podcast"

    def test_detect_url_type_article(self):
        """Test detection of article URLs."""
        article_urls = [
            "https://example.com/2023/05/article-title",
            "https://example.com/article/some-long-title-with-hyphens",
            "https://example.com/post/12345",
            "https://example.com/story/article-title",
        ]

        for url in article_urls:
            assert detect_url_type(url) == "article"

    def test_detect_url_type_unknown(self):
        """Test detection of unknown URL types."""
        unknown_urls = ["https://example.com", "https://example.com/", "not-a-url"]

        for url in unknown_urls:
            assert detect_url_type(url) == "unknown"

    @patch("ingest.link_dispatcher.link_uid")
    @patch("os.path.exists")
    def test_is_duplicate(self, mock_exists, mock_link_uid):
        """Test duplicate detection."""
        # Setup
        mock_link_uid.return_value = "1234567890abcdef"
        config = {
            "article_output_path": "output/articles",
            "youtube_output_path": "output/youtube",
            "podcast_output_path": "output/podcasts",
        }

        # Test case 1: URL is a duplicate (article)
        mock_exists.return_value = True
        assert is_duplicate("https://example.com/article", config) is True
        mock_exists.assert_any_call(
            os.path.join("output/articles", "metadata", "1234567890abcdef.json")
        )

        # Reset mock
        mock_exists.reset_mock()

        # Test case 2: URL is not a duplicate
        mock_exists.return_value = False
        assert is_duplicate("https://example.com/article", config) is False

    @patch("ingest.link_dispatcher.is_duplicate")
    @patch("ingest.link_dispatcher.detect_url_type")
    def test_dispatch_url(self, mock_detect_url_type, mock_is_duplicate):
        """Test URL dispatching."""
        config = {"data_directory": "output"}

        # Test case 1: Empty URL
        success, message = dispatch_url("", config)
        assert not success
        assert "Empty URL" in message

        # Test case 2: Duplicate URL
        mock_is_duplicate.return_value = True
        success, message = dispatch_url("https://example.com", config)
        assert success
        assert "duplicate" in message.lower()

        # Reset mocks
        mock_is_duplicate.reset_mock()
        mock_is_duplicate.return_value = False

        # Test case 3: YouTube URL
        mock_detect_url_type.return_value = "youtube"
        with patch("ingest.link_dispatcher.ingest_youtube_video") as mock_ingest:
            mock_ingest.return_value = True
            success, message = dispatch_url("https://youtube.com/watch?v=123", config)
            assert success
            assert "youtube" in message.lower()
            mock_ingest.assert_called_once()

        # Test case 4: Podcast URL
        mock_detect_url_type.return_value = "podcast"
        success, message = dispatch_url(
            "https://podcasts.apple.com/podcast/123", config
        )
        assert not success
        assert "not implemented" in message.lower()

        # Test case 5: Article URL
        mock_detect_url_type.return_value = "article"
        with patch("ingest.link_dispatcher.fetch_and_save_article") as mock_fetch:
            mock_fetch.return_value = True
            success, message = dispatch_url("https://example.com/article", config)
            assert success
            assert "article" in message.lower()
            mock_fetch.assert_called_once()

    @patch("ingest.link_dispatcher.dispatch_url")
    def test_process_url_list(self, mock_dispatch_url):
        """Test processing a list of URLs."""
        urls = [
            "https://example.com/article1",
            "https://example.com/article2",
            "https://youtube.com/watch?v=123",
        ]
        config = {}

        # Setup mock responses
        mock_dispatch_url.side_effect = [
            (True, "Processed as article: True"),
            (True, "Skipped (duplicate)"),
            (False, "Error: Failed to process"),
        ]

        # Call the function
        results = process_url_list(urls, config)

        # Check the results
        assert len(results["successful"]) == 1
        assert len(results["duplicate"]) == 1
        assert len(results["failed"]) == 1
        assert len(results["unknown"]) == 0

        # Check that dispatch_url was called for each URL
        assert mock_dispatch_url.call_count == 3
