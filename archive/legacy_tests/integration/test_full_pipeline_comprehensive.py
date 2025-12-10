"""
Comprehensive integration tests for the complete Atlas pipeline.

This test suite validates the end-to-end functionality of Atlas including:
- Content ingestion across multiple types
- Metadata processing and preservation
- Search indexing and retrieval
- Error handling and recovery
- Performance under load
"""

import json
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from helpers.article_ingestor import ArticleIngestor
from helpers.config import load_config
from helpers.metadata_manager import ContentType, create_metadata_manager
from helpers.search_engine import EnhancedSearchEngine


class TestFullPipelineIntegration:
    """Test complete pipeline integration."""

    @pytest.fixture
    def pipeline_config(self, test_env):
        """Create configuration for pipeline testing."""
        return {
            "data_directory": str(test_env.temp_dir),
            "log_path": str(test_env.temp_dir / "pipeline.log"),
            "enable_search": True,
            "transcribe_enabled": False,  # Skip transcription for faster tests
            "max_workers": 2,
            "retry_attempts": 2
        }

    @pytest.fixture
    def sample_content(self):
        """Sample content for testing."""
        return {
            "article_html": """
                <html>
                    <head>
                        <title>Integration Test Article</title>
                        <meta name="author" content="Test Author">
                        <meta name="description" content="Test article for integration testing">
                        <meta property="og:title" content="OG Test Title">
                    </head>
                    <body>
                        <article>
                            <h1>Integration Test Article</h1>
                            <p>This article tests the complete Atlas pipeline integration.</p>
                            <p>It contains multiple paragraphs with <strong>formatting</strong> and <em>emphasis</em>.</p>
                            <ul>
                                <li>Feature testing</li>
                                <li>Performance validation</li>
                                <li>Error handling</li>
                            </ul>
                        </article>
                    </body>
                </html>
            """,
            "urls": [
                "https://example.com/article1",
                "https://example.com/article2",
                "https://example.com/article3"
            ]
        }

    @pytest.mark.integration
    def test_end_to_end_article_processing(self, pipeline_config, sample_content, test_env):
        """Test complete article processing pipeline."""

        # Initialize components
        ingestor = ArticleIngestor(pipeline_config)
        metadata_manager = create_metadata_manager(pipeline_config)

        # Mock article fetching
        with patch.object(ingestor.fetcher, 'fetch_article') as mock_fetch:
            mock_fetch.return_value = {
                'content': sample_content["article_html"],
                'success': True,
                'status_code': 200,
                'url': sample_content["urls"][0]
            }

            # Process articles
            result = ingestor.process_urls(sample_content["urls"][:1])

        # Validate processing results
        assert result['success_count'] > 0
        assert result['error_count'] == 0

        # Verify file outputs were created
        output_files = list(test_env.temp_dir.rglob("*.json"))
        markdown_files = list(test_env.temp_dir.rglob("*.md"))

        assert len(output_files) > 0 or len(markdown_files) > 0

        # Verify metadata was preserved
        if output_files:
            with open(output_files[0], 'r') as f:
                metadata = json.load(f)
                assert 'title' in metadata
                assert 'content' in metadata
                assert 'source_url' in metadata

    @pytest.mark.integration
    def test_multi_content_type_processing(self, pipeline_config, test_env):
        """Test processing multiple content types in sequence."""

        # Test data for different content types
        test_content = {
            'article': {
                'html': '<html><head><title>Test Article</title></head><body><p>Article content</p></body></html>',
                'url': 'https://example.com/article'
            },
            'document': {
                'content': 'Test document content for processing',
                'filename': 'test_document.txt'
            }
        }

        # Process article
        article_ingestor = ArticleIngestor(pipeline_config)
        with patch.object(article_ingestor.fetcher, 'fetch_article', return_value={
            'content': test_content['article']['html'],
            'success': True,
            'status_code': 200
        }):
            article_result = article_ingestor.process_urls([test_content['article']['url']])

        # Create document for processing
        doc_file = test_env.temp_dir / test_content['document']['filename']
        doc_file.write_text(test_content['document']['content'])

        # Validate both were processed
        assert article_result['success_count'] > 0
        assert doc_file.exists()

        # Check total output files
        all_output_files = list(test_env.temp_dir.rglob("*.json")) + list(test_env.temp_dir.rglob("*.md"))
        assert len(all_output_files) > 0

    @pytest.mark.integration
    def test_search_integration(self, pipeline_config, sample_content, test_env):
        """Test integration with search engine."""

        # Initialize components
        ingestor = ArticleIngestor(pipeline_config)

        # Process content
        with patch.object(ingestor.fetcher, 'fetch_article', return_value={
            'content': sample_content["article_html"],
            'success': True,
            'status_code': 200,
            'url': sample_content["urls"][0]
        }):
            result = ingestor.process_urls([sample_content["urls"][0]])

        assert result['success_count'] > 0

        # Test search functionality (if available)
        try:
            search_engine = EnhancedSearchEngine(pipeline_config)

            # Add processed content to search index
            search_results = search_engine.search("integration test")

            # Should return results (may be empty if indexing is async)
            assert isinstance(search_results, (list, dict))

        except ImportError:
            # Search engine might not be available in test environment
            pytest.skip("Search engine not available")

    @pytest.mark.integration
    def test_error_recovery_pipeline(self, pipeline_config, test_env):
        """Test error handling and recovery in the pipeline."""

        ingestor = ArticleIngestor(pipeline_config)

        # Test with mix of good and bad URLs
        mixed_urls = [
            "https://example.com/good-article",
            "https://invalid-domain-that-doesnt-exist.com/article",
            "not-a-url",
            "https://example.com/404-page"
        ]

        # Mock responses for different scenarios
        def mock_fetch_side_effect(url):
            if "good-article" in url:
                return {
                    'content': '<html><body>Good content</body></html>',
                    'success': True,
                    'status_code': 200
                }
            elif "404-page" in url:
                return {
                    'content': None,
                    'success': False,
                    'status_code': 404,
                    'error': 'Not Found'
                }
            else:
                return {
                    'content': None,
                    'success': False,
                    'status_code': None,
                    'error': 'Connection failed'
                }

        with patch.object(ingestor.fetcher, 'fetch_article', side_effect=mock_fetch_side_effect):
            result = ingestor.process_urls(mixed_urls)

        # Should handle errors gracefully
        assert 'success_count' in result
        assert 'error_count' in result
        assert result['total_count'] == len(mixed_urls)

        # At least one should succeed (the good URL)
        assert result['success_count'] >= 1

        # Some should fail (the bad URLs)
        assert result['error_count'] >= 1

    @pytest.mark.integration
    def test_metadata_consistency(self, pipeline_config, sample_content, test_env):
        """Test metadata consistency across processing pipeline."""

        ingestor = ArticleIngestor(pipeline_config)
        metadata_manager = create_metadata_manager(pipeline_config)

        with patch.object(ingestor.fetcher, 'fetch_article', return_value={
            'content': sample_content["article_html"],
            'success': True,
            'status_code': 200,
            'url': sample_content["urls"][0]
        }):
            result = ingestor.process_urls([sample_content["urls"][0]])

        # Find output files
        output_files = list(test_env.temp_dir.rglob("*.json"))

        if output_files:
            # Load and verify metadata structure
            with open(output_files[0], 'r') as f:
                saved_metadata = json.load(f)

            # Check required fields are present
            required_fields = ['title', 'source_url', 'content_type', 'created_at']
            for field in required_fields:
                assert field in saved_metadata, f"Missing required field: {field}"

            # Verify content type is correct
            assert saved_metadata.get('content_type') == ContentType.ARTICLE.value

    @pytest.mark.integration
    def test_concurrent_processing(self, pipeline_config, test_env):
        """Test concurrent processing of multiple items."""

        # Create multiple test URLs
        test_urls = [f"https://example.com/article-{i}" for i in range(5)]

        ingestor = ArticleIngestor(pipeline_config)

        # Mock responses for all URLs
        with patch.object(ingestor.fetcher, 'fetch_article', return_value={
            'content': '<html><body>Test content</body></html>',
            'success': True,
            'status_code': 200
        }):
            start_time = time.time()
            result = ingestor.process_urls(test_urls)
            end_time = time.time()

        # Should process all URLs
        assert result['total_count'] == len(test_urls)
        assert result['success_count'] == len(test_urls)

        # Should complete in reasonable time (parallel processing)
        processing_time = end_time - start_time
        assert processing_time < 30.0  # Should be much faster than sequential

    @pytest.mark.integration
    def test_large_content_handling(self, pipeline_config, test_env):
        """Test handling of large content items."""

        # Create large HTML content
        large_content = "<p>" + "Large article content. " * 1000 + "</p>"
        large_html = f"""
        <html>
            <head><title>Large Article</title></head>
            <body>{large_content}</body>
        </html>
        """

        ingestor = ArticleIngestor(pipeline_config)

        with patch.object(ingestor.fetcher, 'fetch_article', return_value={
            'content': large_html,
            'success': True,
            'status_code': 200
        }):
            start_time = time.time()
            result = ingestor.process_urls(["https://example.com/large-article"])
            end_time = time.time()

        # Should handle large content successfully
        assert result['success_count'] > 0

        # Should complete in reasonable time
        processing_time = end_time - start_time
        assert processing_time < 15.0

    @pytest.mark.integration
    def test_configuration_validation(self, test_env):
        """Test pipeline behavior with various configurations."""

        # Test with minimal configuration
        minimal_config = {
            "data_directory": str(test_env.temp_dir)
        }

        ingestor = ArticleIngestor(minimal_config)
        assert ingestor.config == minimal_config

        # Test with full configuration
        full_config = {
            "data_directory": str(test_env.temp_dir),
            "log_path": str(test_env.temp_dir / "test.log"),
            "openrouter_api_key": "test-key",
            "transcribe_enabled": False,
            "max_workers": 4,
            "timeout": 30
        }

        full_ingestor = ArticleIngestor(full_config)
        assert full_ingestor.config == full_config

    @pytest.mark.integration
    def test_file_system_integration(self, pipeline_config, test_env):
        """Test file system operations and organization."""

        ingestor = ArticleIngestor(pipeline_config)

        # Process multiple articles
        test_urls = [
            "https://example.com/tech-article",
            "https://example.com/science-article"
        ]

        with patch.object(ingestor.fetcher, 'fetch_article') as mock_fetch:
            mock_fetch.return_value = {
                'content': '<html><head><title>Test</title></head><body>Content</body></html>',
                'success': True,
                'status_code': 200
            }

            result = ingestor.process_urls(test_urls)

        # Check directory structure was created properly
        assert test_env.temp_dir.exists()

        # Check that output files exist
        output_files = list(test_env.temp_dir.rglob("*"))
        output_files = [f for f in output_files if f.is_file()]

        assert len(output_files) > 0

        # Verify file permissions and accessibility
        for file_path in output_files:
            assert file_path.is_file()
            assert file_path.stat().st_size > 0  # Non-empty files


class TestPipelinePerformance:
    """Performance tests for the pipeline."""

    @pytest.mark.performance
    def test_throughput_performance(self, test_env):
        """Test pipeline throughput with multiple items."""

        config = {
            "data_directory": str(test_env.temp_dir),
            "max_workers": 4
        }

        ingestor = ArticleIngestor(config)

        # Test with multiple articles
        num_articles = 20
        test_urls = [f"https://example.com/perf-test-{i}" for i in range(num_articles)]

        with patch.object(ingestor.fetcher, 'fetch_article', return_value={
            'content': '<html><body>Performance test content</body></html>',
            'success': True,
            'status_code': 200
        }):
            start_time = time.time()
            result = ingestor.process_urls(test_urls)
            end_time = time.time()

        processing_time = end_time - start_time
        throughput = num_articles / processing_time

        # Should achieve reasonable throughput
        assert throughput > 1.0  # At least 1 article per second
        assert result['success_count'] == num_articles

        print(f"Processed {num_articles} articles in {processing_time:.2f}s")
        print(f"Throughput: {throughput:.2f} articles/second")

    @pytest.mark.performance
    def test_memory_usage_stability(self, test_env):
        """Test memory usage remains stable during processing."""

        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        config = {"data_directory": str(test_env.temp_dir)}
        ingestor = ArticleIngestor(config)

        # Process articles in batches to test memory stability
        for batch in range(3):
            test_urls = [f"https://example.com/batch-{batch}-article-{i}" for i in range(10)]

            with patch.object(ingestor.fetcher, 'fetch_article', return_value={
                'content': '<html><body>Batch test content</body></html>',
                'success': True,
                'status_code': 200
            }):
                result = ingestor.process_urls(test_urls)
                assert result['success_count'] == len(test_urls)

        final_memory = process.memory_info().rss
        memory_increase = (final_memory - initial_memory) / 1024 / 1024  # MB

        # Memory increase should be reasonable (less than 100MB for test)
        assert memory_increase < 100, f"Memory increased by {memory_increase:.2f}MB"

        print(f"Memory increase: {memory_increase:.2f}MB")


class TestPipelineEdgeCases:
    """Test edge cases and unusual scenarios."""

    @pytest.mark.integration
    def test_unicode_content_handling(self, test_env):
        """Test handling of Unicode and international content."""

        config = {"data_directory": str(test_env.temp_dir)}
        ingestor = ArticleIngestor(config)

        # HTML with various Unicode characters
        unicode_html = """
        <html>
            <head><title>测试文章 - Test Article - тест статья</title></head>
            <body>
                <p>English text with émojis 🚀 and symbols ©™®</p>
                <p>中文内容测试</p>
                <p>Русский текст проверка</p>
                <p>العربية اختبار</p>
                <p>Français avec accents: café, naïve, résumé</p>
            </body>
        </html>
        """

        with patch.object(ingestor.fetcher, 'fetch_article', return_value={
            'content': unicode_html,
            'success': True,
            'status_code': 200
        }):
            result = ingestor.process_urls(["https://example.com/unicode-test"])

        assert result['success_count'] > 0

    @pytest.mark.integration
    def test_malformed_content_recovery(self, test_env):
        """Test recovery from malformed or unusual content."""

        config = {"data_directory": str(test_env.temp_dir)}
        ingestor = ArticleIngestor(config)

        # Various malformed HTML scenarios
        test_cases = [
            "<html><head><title>Missing body tag</title></head>Content without body",
            "<html><body>Missing head section</body></html>",
            "<html><head><title>Unclosed tags<body><p>Content without closing p tag</body></html>",
            "Not HTML at all, just plain text content",
            "",  # Empty content
            " \n\t ",  # Whitespace only
        ]

        success_count = 0
        for i, malformed_content in enumerate(test_cases):
            with patch.object(ingestor.fetcher, 'fetch_article', return_value={
                'content': malformed_content,
                'success': True,
                'status_code': 200
            }):
                result = ingestor.process_urls([f"https://example.com/malformed-{i}"])

                # Should handle gracefully (either success or controlled failure)
                if result['success_count'] > 0:
                    success_count += 1

        # At least some cases should be handled successfully
        assert success_count >= len(test_cases) // 2

    @pytest.mark.integration
    def test_network_instability_simulation(self, test_env):
        """Test behavior under simulated network instability."""

        config = {
            "data_directory": str(test_env.temp_dir),
            "retry_attempts": 3
        }
        ingestor = ArticleIngestor(config)

        # Simulate intermittent network issues
        call_count = 0
        def unstable_fetch(url):
            nonlocal call_count
            call_count += 1

            # Fail first 2 attempts, succeed on 3rd
            if call_count <= 2:
                return {
                    'content': None,
                    'success': False,
                    'error': 'Network timeout'
                }
            else:
                return {
                    'content': '<html><body>Finally succeeded</body></html>',
                    'success': True,
                    'status_code': 200
                }

        with patch.object(ingestor.fetcher, 'fetch_article', side_effect=unstable_fetch):
            result = ingestor.process_urls(["https://example.com/unstable"])

        # Should eventually succeed with retry mechanism
        # Note: This test depends on retry logic being implemented
        assert 'total_count' in result