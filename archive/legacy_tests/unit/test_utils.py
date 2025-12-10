"""
Comprehensive unit tests for helpers.utils module.

Tests all utility functions with various input scenarios including
edge cases, error conditions, and performance considerations.
"""

import logging
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from helpers.utils import (
    calculate_hash,
    convert_html_to_markdown,
    ensure_directory,
    extract_video_id,
    generate_markdown_summary,
    log_error,
    log_info,
    log_message,
    sanitize_filename,
    setup_logging,
)


class TestConvertHtmlToMarkdown:
    """Test HTML to Markdown conversion functionality."""

    @pytest.mark.unit
    def test_basic_conversion(self):
        """Test basic HTML to Markdown conversion."""
        html = "<h1>Title</h1><p>Content</p>"
        result = convert_html_to_markdown(html)

        assert "# Title" in result
        assert "Content" in result

    @pytest.mark.unit
    def test_empty_html(self):
        """Test conversion with empty HTML."""
        result = convert_html_to_markdown("")
        assert result == ""

    @pytest.mark.unit
    def test_none_input(self):
        """Test conversion with None input."""
        result = convert_html_to_markdown(None)
        assert result == ""

    @pytest.mark.unit
    def test_with_base_url(self):
        """Test conversion with base URL for relative links."""
        html = '<a href="/page">Link</a>'
        base_url = "https://example.com"
        result = convert_html_to_markdown(html, base_url)

        assert "https://example.com/page" in result or "[Link](/page)" in result

    @pytest.mark.unit
    @patch('helpers.utils.md')
    def test_conversion_error_fallback(self, mock_md):
        """Test fallback when conversion fails."""
        mock_md.side_effect = Exception("Conversion failed")
        html = "<h1>Test</h1>"

        result = convert_html_to_markdown(html)
        assert result == html  # Should return original content


class TestEnsureDirectory:
    """Test directory creation functionality."""

    @pytest.mark.unit
    def test_create_directory(self, temp_dir):
        """Test creating a new directory."""
        new_dir = temp_dir / "new_directory"
        assert not new_dir.exists()

        ensure_directory(str(new_dir))
        assert new_dir.exists()
        assert new_dir.is_dir()

    @pytest.mark.unit
    def test_existing_directory(self, temp_dir):
        """Test with already existing directory."""
        ensure_directory(str(temp_dir))  # Should not raise error
        assert temp_dir.exists()

    @pytest.mark.unit
    def test_nested_directories(self, temp_dir):
        """Test creating nested directories."""
        nested_path = temp_dir / "level1" / "level2" / "level3"
        ensure_directory(str(nested_path))

        assert nested_path.exists()
        assert nested_path.is_dir()

    @pytest.mark.unit
    def test_empty_path(self):
        """Test with empty path."""
        ensure_directory("")  # Should not raise error

    @pytest.mark.unit
    @patch('os.makedirs')
    def test_permission_error(self, mock_makedirs):
        """Test handling of permission errors."""
        mock_makedirs.side_effect = OSError("Permission denied")

        with pytest.raises(OSError):
            ensure_directory("/root/test")


class TestSetupLogging:
    """Test logging configuration."""

    @pytest.mark.unit
    def test_setup_logging(self, temp_dir):
        """Test basic logging setup."""
        log_file = temp_dir / "test.log"
        setup_logging(str(log_file))

        # Test that logging works
        logging.info("Test message")

        assert log_file.exists()
        content = log_file.read_text()
        assert "Test message" in content

    @pytest.mark.unit
    def test_setup_logging_creates_directory(self, temp_dir):
        """Test that logging setup creates parent directories."""
        log_file = temp_dir / "logs" / "app.log"
        setup_logging(str(log_file))

        assert log_file.parent.exists()


class TestSanitizeFilename:
    """Test filename sanitization."""

    @pytest.mark.unit
    def test_basic_sanitization(self):
        """Test basic filename sanitization."""
        result = sanitize_filename("My Article Title")
        assert result == "my_article_title"

    @pytest.mark.unit
    def test_special_characters(self):
        """Test removal of special characters."""
        result = sanitize_filename("Title! @#$%^&*()_+={}[]|\\:;\"'<>,.?/~`")
        assert result == "title"

    @pytest.mark.unit
    def test_multiple_spaces(self):
        """Test handling of multiple spaces."""
        result = sanitize_filename("Title   with    multiple     spaces")
        assert result == "title_with_multiple_spaces"

    @pytest.mark.unit
    def test_mixed_case(self):
        """Test case conversion."""
        result = sanitize_filename("CamelCaseTitle")
        assert result == "camelcasetitle"

    @pytest.mark.unit
    def test_empty_string(self):
        """Test empty string input."""
        result = sanitize_filename("")
        assert result == "unnamed"

    @pytest.mark.unit
    def test_none_input(self):
        """Test None input."""
        result = sanitize_filename(None)
        assert result == "unnamed"

    @pytest.mark.unit
    def test_only_special_chars(self):
        """Test string with only special characters."""
        result = sanitize_filename("!@#$%^&*()")
        assert result == "unnamed"


class TestExtractVideoId:
    """Test YouTube video ID extraction."""

    @pytest.mark.unit
    def test_standard_youtube_url(self):
        """Test standard youtube.com watch URL."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        result = extract_video_id(url)
        assert result == "dQw4w9WgXcQ"

    @pytest.mark.unit
    def test_shortened_url(self):
        """Test shortened youtu.be URL."""
        url = "https://youtu.be/dQw4w9WgXcQ"
        result = extract_video_id(url)
        assert result == "dQw4w9WgXcQ"

    @pytest.mark.unit
    def test_embed_url(self):
        """Test embed URL format."""
        url = "https://www.youtube.com/embed/dQw4w9WgXcQ"
        result = extract_video_id(url)
        assert result == "dQw4w9WgXcQ"

    @pytest.mark.unit
    def test_shorts_url(self):
        """Test YouTube Shorts URL."""
        url = "https://www.youtube.com/shorts/dQw4w9WgXcQ"
        result = extract_video_id(url)
        assert result == "dQw4w9WgXcQ"

    @pytest.mark.unit
    def test_invalid_url(self):
        """Test invalid URL."""
        result = extract_video_id("https://example.com/invalid")
        assert result is None

    @pytest.mark.unit
    def test_empty_url(self):
        """Test empty URL."""
        result = extract_video_id("")
        assert result is None

    @pytest.mark.unit
    def test_none_url(self):
        """Test None URL."""
        result = extract_video_id(None)
        assert result is None


class TestGenerateMarkdownSummary:
    """Test Markdown summary generation."""

    @pytest.mark.unit
    def test_basic_summary(self):
        """Test basic summary generation."""
        result = generate_markdown_summary(
            "Test Title",
            "https://example.com",
            "2024-01-01"
        )

        assert "title: Test Title" in result
        assert "source: https://example.com" in result
        assert "date: 2024-01-01" in result
        assert "---" in result

    @pytest.mark.unit
    def test_with_tags(self):
        """Test summary with tags."""
        result = generate_markdown_summary(
            "Title",
            "https://example.com",
            "2024-01-01",
            tags=["tech", "ai"]
        )

        assert "'tech'" in result
        assert "'ai'" in result

    @pytest.mark.unit
    def test_with_content(self):
        """Test summary with content."""
        content = "This is the article content."
        result = generate_markdown_summary(
            "Title",
            "https://example.com",
            "2024-01-01",
            content=content
        )

        assert content in result
        assert result.endswith(content + "\n")

    @pytest.mark.unit
    def test_with_all_parameters(self):
        """Test summary with all parameters."""
        result = generate_markdown_summary(
            "Full Test",
            "https://example.com",
            "2024-01-01",
            tags=["tag1", "tag2"],
            notes=["note1", "note2"],
            content="Content here"
        )

        assert "Full Test" in result
        assert "tag1" in result
        assert "note1" in result
        assert "Content here" in result


class TestLogFunctions:
    """Test logging utility functions."""

    @pytest.mark.unit
    def test_log_message(self, temp_dir):
        """Test basic log message function."""
        log_file = temp_dir / "test.log"
        log_message(str(log_file), "INFO", "Test message")

        assert log_file.exists()
        content = log_file.read_text()
        assert "INFO: Test message" in content

    @pytest.mark.unit
    def test_log_info(self, temp_dir):
        """Test log_info convenience function."""
        log_file = temp_dir / "test.log"
        log_info(str(log_file), "Info message")

        content = log_file.read_text()
        assert "INFO: Info message" in content

    @pytest.mark.unit
    def test_log_error(self, temp_dir):
        """Test log_error convenience function."""
        log_file = temp_dir / "test.log"
        log_error(str(log_file), "Error message")

        content = log_file.read_text()
        assert "ERROR: Error message" in content

    @pytest.mark.unit
    def test_empty_log_path(self):
        """Test logging with empty path."""
        # Should not raise errors
        log_message("", "INFO", "message")
        log_info("", "message")
        log_error("", "message")


class TestCalculateHash:
    """Test file hash calculation."""

    @pytest.mark.unit
    def test_hash_calculation(self, temp_dir):
        """Test basic hash calculation."""
        test_file = temp_dir / "test.txt"
        test_file.write_text("Hello, World!")

        hash_value = calculate_hash(str(test_file))

        # SHA256 hash should be 64 characters
        assert len(hash_value) == 64
        assert isinstance(hash_value, str)

    @pytest.mark.unit
    def test_consistent_hashing(self, temp_dir):
        """Test that same content produces same hash."""
        test_file1 = temp_dir / "test1.txt"
        test_file2 = temp_dir / "test2.txt"
        content = "Identical content"

        test_file1.write_text(content)
        test_file2.write_text(content)

        hash1 = calculate_hash(str(test_file1))
        hash2 = calculate_hash(str(test_file2))

        assert hash1 == hash2

    @pytest.mark.unit
    def test_different_content_different_hash(self, temp_dir):
        """Test that different content produces different hashes."""
        test_file1 = temp_dir / "test1.txt"
        test_file2 = temp_dir / "test2.txt"

        test_file1.write_text("Content 1")
        test_file2.write_text("Content 2")

        hash1 = calculate_hash(str(test_file1))
        hash2 = calculate_hash(str(test_file2))

        assert hash1 != hash2

    @pytest.mark.unit
    def test_large_file_hashing(self, temp_dir):
        """Test hashing of larger files (chunk reading)."""
        test_file = temp_dir / "large.txt"
        # Create a file larger than the chunk size (4096 bytes)
        content = "A" * 10000
        test_file.write_text(content)

        hash_value = calculate_hash(str(test_file))
        assert len(hash_value) == 64

    @pytest.mark.unit
    def test_nonexistent_file(self):
        """Test hash calculation for non-existent file."""
        with pytest.raises(IOError):
            calculate_hash("/nonexistent/file.txt")

    @pytest.mark.unit
    def test_empty_file(self, temp_dir):
        """Test hashing empty file."""
        test_file = temp_dir / "empty.txt"
        test_file.write_text("")

        hash_value = calculate_hash(str(test_file))
        assert len(hash_value) == 64
        # Empty file should have consistent hash
        assert hash_value == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


@pytest.mark.performance
class TestPerformance:
    """Performance tests for utility functions."""

    def test_large_html_conversion_performance(self):
        """Test HTML conversion performance with large content."""
        import time

        # Generate large HTML content
        html = "<p>" + "Large content " * 1000 + "</p>"

        start_time = time.time()
        result = convert_html_to_markdown(html)
        end_time = time.time()

        # Should complete within reasonable time (adjust as needed)
        assert end_time - start_time < 5.0
        assert len(result) > 0

    def test_multiple_directory_creation_performance(self, temp_dir):
        """Test performance of creating many directories."""
        import time

        start_time = time.time()

        for i in range(100):
            dir_path = temp_dir / f"dir_{i}"
            ensure_directory(str(dir_path))

        end_time = time.time()

        # Should complete quickly
        assert end_time - start_time < 2.0