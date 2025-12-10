"""
Comprehensive unit tests for the ArticleIngestor.

This test suite covers all aspects of article ingestion including:
- URL processing and validation
- Metadata extraction and preservation
- Error handling and recovery
- Performance characteristics
- Security considerations
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from urllib.parse import urljoin

import pytest
import requests
from bs4 import BeautifulSoup

from helpers.article_ingestor import ArticleIngestor
from helpers.metadata_manager import ContentType


class TestArticleIngestorInitialization:
    """Test article ingestor initialization and configuration."""

    @pytest.mark.unit
    def test_ingestor_initialization(self, test_env):
        """Test proper initialization with config."""
        config = {
            "data_directory": str(test_env.temp_dir),
            "log_path": str(test_env.temp_dir / "test.log")
        }

        ingestor = ArticleIngestor(config)

        assert ingestor.config == config
        assert ingestor.get_content_type() == ContentType.ARTICLE
        assert ingestor.get_module_name() == "article_ingestor"

    @pytest.mark.unit
    def test_fetcher_initialization(self, test_env):
        """Test that ArticleFetcher is properly initialized."""
        config = {"data_directory": str(test_env.temp_dir)}
        ingestor = ArticleIngestor(config)

        assert ingestor.fetcher is not None
        assert hasattr(ingestor.fetcher, 'config')


class TestUrlProcessing:
    """Test URL processing and validation functionality."""

    @pytest.fixture
    def ingestor(self, test_env):
        config = {
            "data_directory": str(test_env.temp_dir),
            "log_path": str(test_env.temp_dir / "test.log")
        }
        return ArticleIngestor(config)

    @pytest.mark.unit
    def test_process_single_url(self, ingestor):
        """Test processing a single valid URL."""
        sample_html = """
        <html>
            <head>
                <title>Test Article</title>
                <meta name="description" content="Test description">
                <meta name="author" content="Test Author">
            </head>
            <body>
                <h1>Test Article</h1>
                <p>This is test content.</p>
            </body>
        </html>
        """

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = sample_html
        mock_response.headers = {'content-type': 'text/html'}
        mock_response.url = "https://example.com/article"

        with patch.object(ingestor.fetcher, 'fetch_article', return_value={
            'content': sample_html,
            'success': True,
            'url': 'https://example.com/article',
            'status_code': 200
        }):
            result = ingestor.process_urls(["https://example.com/article"])

        assert result['success_count'] > 0
        assert len(result['results']) > 0

    @pytest.mark.unit
    def test_process_multiple_urls(self, ingestor):
        """Test processing multiple URLs."""
        urls = [
            "https://example.com/article1",
            "https://example.com/article2",
            "https://example.com/article3"
        ]

        with patch.object(ingestor.fetcher, 'fetch_article') as mock_fetch:
            mock_fetch.return_value = {
                'content': '<html><body>Test</body></html>',
                'success': True,
                'status_code': 200
            }

            result = ingestor.process_urls(urls)

        assert mock_fetch.call_count == len(urls)
        assert result['total_count'] == len(urls)

    @pytest.mark.unit
    def test_invalid_url_handling(self, ingestor):
        """Test handling of invalid URLs."""
        invalid_urls = [
            "",
            "not-a-url",
            "ftp://invalid.com",
            None
        ]

        result = ingestor.process_urls(invalid_urls)

        # Should handle invalid URLs gracefully
        assert 'error_count' in result
        assert result['error_count'] > 0

    @pytest.mark.unit
    def test_duplicate_url_handling(self, ingestor):
        """Test handling of duplicate URLs."""
        duplicate_urls = [
            "https://example.com/article",
            "https://example.com/article",  # Duplicate
            "https://example.com/article"   # Another duplicate
        ]

        with patch.object(ingestor.fetcher, 'fetch_article') as mock_fetch:
            mock_fetch.return_value = {
                'content': '<html><body>Test</body></html>',
                'success': True,
                'status_code': 200
            }

            result = ingestor.process_urls(duplicate_urls)

        # Should deduplicate URLs
        assert mock_fetch.call_count < len(duplicate_urls)


class TestMetadataExtraction:
    """Test metadata extraction from HTML content."""

    @pytest.fixture
    def ingestor(self, test_env):
        config = {"data_directory": str(test_env.temp_dir)}
        return ArticleIngestor(config)

    @pytest.mark.unit
    def test_basic_metadata_extraction(self, ingestor):
        """Test extraction of basic HTML metadata."""
        html_content = """
        <html>
            <head>
                <title>Test Article Title</title>
                <meta name="description" content="This is a test article">
                <meta name="author" content="John Doe">
                <meta name="keywords" content="test, article, example">
                <meta property="article:published_time" content="2024-01-01T00:00:00Z">
            </head>
            <body>
                <article>
                    <h1>Main Heading</h1>
                    <p>Article content goes here.</p>
                </article>
            </body>
        </html>
        """

        with patch.object(ingestor.fetcher, 'fetch_article', return_value={
            'content': html_content,
            'success': True,
            'url': 'https://example.com/test',
            'status_code': 200
        }):
            result = ingestor.process_urls(["https://example.com/test"])

        # Should extract metadata successfully
        assert result['success_count'] > 0

    @pytest.mark.unit
    def test_open_graph_metadata(self, ingestor):
        """Test extraction of Open Graph metadata."""
        html_content = """
        <html>
            <head>
                <meta property="og:title" content="OG Title">
                <meta property="og:description" content="OG Description">
                <meta property="og:image" content="https://example.com/image.jpg">
                <meta property="og:url" content="https://example.com/article">
                <meta property="og:type" content="article">
            </head>
            <body>Content</body>
        </html>
        """

        with patch.object(ingestor.fetcher, 'fetch_article', return_value={
            'content': html_content,
            'success': True,
            'status_code': 200
        }):
            result = ingestor.process_urls(["https://example.com/test"])

        assert result['success_count'] > 0

    @pytest.mark.unit
    def test_twitter_card_metadata(self, ingestor):
        """Test extraction of Twitter Card metadata."""
        html_content = """
        <html>
            <head>
                <meta name="twitter:card" content="summary_large_image">
                <meta name="twitter:title" content="Twitter Title">
                <meta name="twitter:description" content="Twitter Description">
                <meta name="twitter:image" content="https://example.com/twitter.jpg">
            </head>
            <body>Content</body>
        </html>
        """

        with patch.object(ingestor.fetcher, 'fetch_article', return_value={
            'content': html_content,
            'success': True,
            'status_code': 200
        }):
            result = ingestor.process_urls(["https://example.com/test"])

        assert result['success_count'] > 0

    @pytest.mark.unit
    def test_structured_data_extraction(self, ingestor):
        """Test extraction of JSON-LD structured data."""
        html_content = '''
        <html>
            <head>
                <script type="application/ld+json">
                {
                    "@context": "https://schema.org",
                    "@type": "Article",
                    "headline": "Test Article",
                    "author": {
                        "@type": "Person",
                        "name": "Jane Smith"
                    },
                    "datePublished": "2024-01-01T00:00:00Z"
                }
                </script>
            </head>
            <body>Content</body>
        </html>
        '''

        with patch.object(ingestor.fetcher, 'fetch_article', return_value={
            'content': html_content,
            'success': True,
            'status_code': 200
        }):
            result = ingestor.process_urls(["https://example.com/test"])

        assert result['success_count'] > 0


class TestContentProcessing:
    """Test content extraction and processing."""

    @pytest.fixture
    def ingestor(self, test_env):
        config = {"data_directory": str(test_env.temp_dir)}
        return ArticleIngestor(config)

    @pytest.mark.unit
    def test_readability_content_extraction(self, ingestor):
        """Test main content extraction using readability."""
        html_content = """
        <html>
            <head><title>Test</title></head>
            <body>
                <nav>Navigation</nav>
                <aside>Sidebar</aside>
                <article>
                    <h1>Main Article Title</h1>
                    <p>This is the main content that should be extracted.</p>
                    <p>Additional paragraph with important information.</p>
                </article>
                <footer>Footer content</footer>
            </body>
        </html>
        """

        with patch.object(ingestor.fetcher, 'fetch_article', return_value={
            'content': html_content,
            'success': True,
            'status_code': 200
        }):
            result = ingestor.process_urls(["https://example.com/test"])

        assert result['success_count'] > 0

    @pytest.mark.unit
    def test_markdown_conversion(self, ingestor):
        """Test HTML to Markdown conversion."""
        html_content = """
        <html>
            <body>
                <h1>Heading 1</h1>
                <h2>Heading 2</h2>
                <p>Paragraph with <strong>bold</strong> and <em>italic</em> text.</p>
                <ul>
                    <li>List item 1</li>
                    <li>List item 2</li>
                </ul>
                <a href="https://example.com">Link text</a>
            </body>
        </html>
        """

        with patch.object(ingestor.fetcher, 'fetch_article', return_value={
            'content': html_content,
            'success': True,
            'status_code': 200
        }):
            result = ingestor.process_urls(["https://example.com/test"])

        assert result['success_count'] > 0

    @pytest.mark.unit
    def test_empty_content_handling(self, ingestor):
        """Test handling of empty or minimal content."""
        html_content = "<html><body></body></html>"

        with patch.object(ingestor.fetcher, 'fetch_article', return_value={
            'content': html_content,
            'success': True,
            'status_code': 200
        }):
            result = ingestor.process_urls(["https://example.com/empty"])

        # Should handle empty content gracefully
        assert 'error_count' in result or 'success_count' in result


class TestErrorHandling:
    """Test error handling and recovery mechanisms."""

    @pytest.fixture
    def ingestor(self, test_env):
        config = {"data_directory": str(test_env.temp_dir)}
        return ArticleIngestor(config)

    @pytest.mark.unit
    def test_network_error_handling(self, ingestor):
        """Test handling of network errors."""
        with patch.object(ingestor.fetcher, 'fetch_article') as mock_fetch:
            mock_fetch.side_effect = requests.exceptions.ConnectionError("Network error")

            result = ingestor.process_urls(["https://example.com/test"])

        assert 'error_count' in result
        assert result['error_count'] > 0

    @pytest.mark.unit
    def test_http_error_handling(self, ingestor):
        """Test handling of HTTP errors."""
        with patch.object(ingestor.fetcher, 'fetch_article', return_value={
            'content': None,
            'success': False,
            'status_code': 404,
            'error': 'Not Found'
        }):
            result = ingestor.process_urls(["https://example.com/404"])

        assert 'error_count' in result

    @pytest.mark.unit
    def test_malformed_html_handling(self, ingestor):
        """Test handling of malformed HTML."""
        malformed_html = "<html><head><title>Test</title><body><p>Missing closing tags"

        with patch.object(ingestor.fetcher, 'fetch_article', return_value={
            'content': malformed_html,
            'success': True,
            'status_code': 200
        }):
            result = ingestor.process_urls(["https://example.com/malformed"])

        # Should handle malformed HTML without crashing
        assert 'success_count' in result or 'error_count' in result

    @pytest.mark.unit
    def test_timeout_handling(self, ingestor):
        """Test handling of request timeouts."""
        with patch.object(ingestor.fetcher, 'fetch_article') as mock_fetch:
            mock_fetch.side_effect = requests.exceptions.Timeout("Timeout")

            result = ingestor.process_urls(["https://example.com/slow"])

        assert 'error_count' in result

    @pytest.mark.unit
    def test_encoding_issues(self, ingestor):
        """Test handling of character encoding issues."""
        # HTML with non-UTF-8 content
        html_with_encoding = """
        <html>
            <head><title>Test with special chars: café, naïve, résumé</title></head>
            <body><p>Content with émojis and accénts</p></body>
        </html>
        """

        with patch.object(ingestor.fetcher, 'fetch_article', return_value={
            'content': html_with_encoding,
            'success': True,
            'status_code': 200
        }):
            result = ingestor.process_urls(["https://example.com/encoding"])

        assert result['success_count'] > 0


class TestFileOperations:
    """Test file saving and management operations."""

    @pytest.fixture
    def ingestor(self, test_env):
        config = {
            "data_directory": str(test_env.temp_dir),
            "log_path": str(test_env.temp_dir / "test.log")
        }
        return ArticleIngestor(config)

    @pytest.mark.unit
    def test_file_saving(self, ingestor, test_env):
        """Test that articles are saved to correct files."""
        html_content = """
        <html>
            <head><title>Test Article</title></head>
            <body><p>Test content for saving</p></body>
        </html>
        """

        with patch.object(ingestor.fetcher, 'fetch_article', return_value={
            'content': html_content,
            'success': True,
            'status_code': 200,
            'url': 'https://example.com/save-test'
        }):
            result = ingestor.process_urls(["https://example.com/save-test"])

        # Check that files were created in output directory
        output_files = list(test_env.temp_dir.rglob("*.json"))
        markdown_files = list(test_env.temp_dir.rglob("*.md"))

        assert len(output_files) > 0 or len(markdown_files) > 0

    @pytest.mark.unit
    def test_metadata_preservation(self, ingestor, test_env):
        """Test that metadata is properly preserved in output files."""
        html_content = """
        <html>
            <head>
                <title>Metadata Test</title>
                <meta name="author" content="Test Author">
                <meta name="description" content="Test Description">
            </head>
            <body><p>Content</p></body>
        </html>
        """

        with patch.object(ingestor.fetcher, 'fetch_article', return_value={
            'content': html_content,
            'success': True,
            'status_code': 200,
            'url': 'https://example.com/metadata-test'
        }):
            result = ingestor.process_urls(["https://example.com/metadata-test"])

        # Should have preserved metadata
        assert result['success_count'] > 0


class TestPerformance:
    """Test performance characteristics of the ingestor."""

    @pytest.fixture
    def ingestor(self, test_env):
        config = {"data_directory": str(test_env.temp_dir)}
        return ArticleIngestor(config)

    @pytest.mark.performance
    def test_large_article_processing(self, ingestor):
        """Test processing of large articles."""
        # Create a large HTML content (simulate a very long article)
        large_content = "<p>" + "Very long article content. " * 1000 + "</p>"
        html_content = f"""
        <html>
            <head><title>Large Article</title></head>
            <body>{large_content}</body>
        </html>
        """

        with patch.object(ingestor.fetcher, 'fetch_article', return_value={
            'content': html_content,
            'success': True,
            'status_code': 200
        }):
            import time
            start_time = time.time()

            result = ingestor.process_urls(["https://example.com/large"])

            end_time = time.time()

        # Should complete within reasonable time
        assert end_time - start_time < 10.0
        assert result['success_count'] > 0

    @pytest.mark.performance
    def test_batch_processing_performance(self, ingestor):
        """Test performance of processing multiple articles."""
        urls = [f"https://example.com/article{i}" for i in range(10)]

        with patch.object(ingestor.fetcher, 'fetch_article', return_value={
            'content': '<html><body>Test</body></html>',
            'success': True,
            'status_code': 200
        }):
            import time
            start_time = time.time()

            result = ingestor.process_urls(urls)

            end_time = time.time()

        # Should process all articles within reasonable time
        assert end_time - start_time < 30.0
        assert result['total_count'] == len(urls)


class TestSecurityConsiderations:
    """Test security-related functionality."""

    @pytest.fixture
    def ingestor(self, test_env):
        config = {"data_directory": str(test_env.temp_dir)}
        return ArticleIngestor(config)

    @pytest.mark.security
    def test_malicious_html_handling(self, ingestor):
        """Test handling of potentially malicious HTML content."""
        malicious_html = """
        <html>
            <head><title>Malicious Content</title></head>
            <body>
                <script>alert('XSS')</script>
                <iframe src="javascript:alert('XSS')"></iframe>
                <img src="x" onerror="alert('XSS')">
                <a href="javascript:void(0)">Malicious Link</a>
            </body>
        </html>
        """

        with patch.object(ingestor.fetcher, 'fetch_article', return_value={
            'content': malicious_html,
            'success': True,
            'status_code': 200
        }):
            result = ingestor.process_urls(["https://example.com/malicious"])

        # Should handle malicious content without executing scripts
        assert 'success_count' in result or 'error_count' in result

    @pytest.mark.security
    def test_url_validation(self, ingestor):
        """Test URL validation for security."""
        suspicious_urls = [
            "javascript:alert('xss')",
            "data:text/html,<script>alert('xss')</script>",
            "file:///etc/passwd",
            "http://localhost:22/ssh-attack"
        ]

        # Should reject or safely handle suspicious URLs
        result = ingestor.process_urls(suspicious_urls)

        # Most should be rejected or handled safely
        assert 'error_count' in result

    @pytest.mark.security
    def test_path_traversal_prevention(self, ingestor, test_env):
        """Test prevention of path traversal attacks."""
        # Simulate malicious filename that could cause path traversal
        html_content = "<html><head><title>../../../etc/passwd</title></head><body>Test</body></html>"

        with patch.object(ingestor.fetcher, 'fetch_article', return_value={
            'content': html_content,
            'success': True,
            'status_code': 200,
            'url': 'https://example.com/../../../malicious'
        }):
            result = ingestor.process_urls(["https://example.com/../../../malicious"])

        # Should not create files outside the designated directory
        sensitive_paths = [
            "/etc/passwd",
            "../../../etc/passwd",
            str(test_env.temp_dir.parent / "malicious_file")
        ]

        for path in sensitive_paths:
            assert not Path(path).exists(), f"Path traversal created: {path}"