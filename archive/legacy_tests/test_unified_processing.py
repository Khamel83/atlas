#!/usr/bin/env python3
"""
Integration tests for unified content processing

Tests the complete workflow combining ArticleManager + ContentPipeline
through the ContentIntegration layer.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from helpers.content_integration import (
    process_article_with_pipeline,
    bulk_process_articles_with_pipeline,
    UnifiedContentProcessor,
    create_unified_processor
)
from helpers.article_manager import ArticleResult
from helpers.content_pipeline import ContentResult, ProcessingStage


class TestUnifiedProcessing:
    """Test unified article + content processing workflow."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = {
            'stats_file': str(Path(self.temp_dir) / 'test_unified_stats.json'),
            'enable_summarization': True,
            'enable_clustering': True
        }

    @patch('helpers.content_integration._integration.article_manager')
    @patch('helpers.content_integration._integration.pipeline')
    def test_single_article_full_workflow(self, mock_pipeline, mock_article_manager):
        """Test complete single article processing workflow."""
        # Mock article manager response
        mock_article_result = ArticleResult(
            success=True,
            url="https://example.com/test",
            content="This is test article content about machine learning and AI.",
            title="Test Article",
            method="direct",
            processing_time=1.2
        )
        mock_article_manager.process_article.return_value = mock_article_result

        # Mock pipeline response
        mock_content_result = ContentResult(
            content="This is test article content about machine learning and AI.",
            title="Test Article",
            url="https://example.com/test",
            content_type="article",
            classification={'category': 'technology', 'confidence': 0.85},
            summary="Article about ML and AI",
            topics=['machine learning', 'artificial intelligence'],
            quality_score=0.8
        )
        mock_content_result.processing_stages = [
            Mock(stage=ProcessingStage.DETECT_TYPE, success=True),
            Mock(stage=ProcessingStage.CLASSIFY_CONTENT, success=True),
            Mock(stage=ProcessingStage.SUMMARIZE_CONTENT, success=True)
        ]
        mock_pipeline.process_content.return_value = mock_content_result

        # Test the unified workflow
        article_result, content_result = process_article_with_pipeline(
            "https://example.com/test",
            self.config
        )

        # Verify article manager was called correctly
        mock_article_manager.process_article.assert_called_once_with(
            "https://example.com/test",
            log_path=""
        )

        # Verify pipeline was called correctly
        mock_pipeline.process_content.assert_called_once_with(
            content="This is test article content about machine learning and AI.",
            title="Test Article",
            url="https://example.com/test",
            log_path=""
        )

        # Verify results
        assert article_result.success is True
        assert article_result.method == "direct"
        assert content_result.classification['category'] == 'technology'
        assert content_result.quality_score == 0.8

    @patch('helpers.content_integration._integration.article_manager')
    def test_article_fetch_failure(self, mock_article_manager):
        """Test handling of article fetch failure."""
        # Mock failed article fetch
        mock_article_result = ArticleResult(
            success=False,
            url="https://example.com/failed",
            error="All strategies failed",
            method="direct",
            processing_time=2.1
        )
        mock_article_manager.process_article.return_value = mock_article_result

        # Test the workflow
        article_result, content_result = process_article_with_pipeline(
            "https://example.com/failed"
        )

        # Should return failed article result and None content result
        assert article_result.success is False
        assert article_result.error == "All strategies failed"
        assert content_result is None

    @patch('helpers.content_integration._integration.article_manager')
    @patch('helpers.content_integration._integration.pipeline')
    def test_bulk_processing_workflow(self, mock_pipeline, mock_article_manager):
        """Test bulk article processing workflow."""
        # Mock bulk article results
        urls = [
            "https://example.com/1",
            "https://example.com/2",
            "https://example.com/3"
        ]

        mock_article_results = {
            urls[0]: ArticleResult(success=True, url=urls[0], content="Content 1", title="Title 1", method="direct"),
            urls[1]: ArticleResult(success=True, url=urls[1], content="Content 2", title="Title 2", method="auth"),
            urls[2]: ArticleResult(success=False, url=urls[2], error="Failed", method="direct")
        }
        mock_article_manager.bulk_process_articles.return_value = mock_article_results

        # Mock pipeline bulk results (only for successful articles)
        mock_content_results = [
            ContentResult(content="Content 1", title="Title 1", url=urls[0]),
            ContentResult(content="Content 2", title="Title 2", url=urls[1])
        ]
        mock_pipeline.bulk_process_content.return_value = mock_content_results

        # Test bulk workflow
        results = bulk_process_articles_with_pipeline(urls, self.config)

        assert len(results) == 3

        # Check first result (successful)
        article_result1, content_result1 = results[0]
        assert article_result1.success is True
        assert content_result1 is not None
        assert content_result1.content == "Content 1"

        # Check second result (successful)
        article_result2, content_result2 = results[1]
        assert article_result2.success is True
        assert content_result2 is not None
        assert content_result2.content == "Content 2"

        # Check third result (failed article, no content processing)
        article_result3, content_result3 = results[2]
        assert article_result3.success is False
        assert content_result3 is None

        # Verify bulk_process_content was called only with successful articles
        mock_pipeline.bulk_process_content.assert_called_once()
        call_args = mock_pipeline.bulk_process_content.call_args[0][0]
        assert len(call_args) == 2  # Only 2 successful articles


class TestUnifiedContentProcessor:
    """Test UnifiedContentProcessor class."""

    def setup_method(self):
        """Set up test environment."""
        self.config = {
            'enable_summarization': True,
            'max_concurrent': 2
        }
        self.processor = UnifiedContentProcessor(self.config)

    def test_processor_initialization(self):
        """Test processor initialization."""
        assert self.processor.config == self.config

    @patch('helpers.content_integration._integration.article_manager')
    @patch('helpers.content_integration._integration.pipeline')
    def test_process_article_url(self, mock_pipeline, mock_article_manager):
        """Test processing article from URL."""
        # Setup mocks
        mock_article_result = ArticleResult(
            success=True,
            url="https://example.com/test",
            content="Test content",
            title="Test Title",
            method="direct"
        )
        mock_article_manager.process_article.return_value = mock_article_result

        mock_content_result = ContentResult(
            content="Test content",
            title="Test Title",
            summary="Test summary"
        )
        mock_pipeline.process_content.return_value = mock_content_result

        # Test processing
        article_result, content_result = self.processor.process_article_url(
            "https://example.com/test"
        )

        assert article_result.success is True
        assert content_result.summary == "Test summary"

    @patch('helpers.content_integration._integration.pipeline')
    def test_process_raw_content(self, mock_pipeline):
        """Test processing raw content."""
        mock_result = ContentResult(
            content="Raw test content",
            summary="Raw summary"
        )
        mock_pipeline.process_content.return_value = mock_result

        result = self.processor.process_raw_content("Raw test content", title="Raw Title")

        mock_pipeline.process_content.assert_called_once_with(
            content="Raw test content",
            title="Raw Title"
        )
        assert result.summary == "Raw summary"

    @patch('helpers.content_integration._integration.article_manager')
    @patch('helpers.content_integration._integration.pipeline')
    def test_bulk_process_urls(self, mock_pipeline, mock_article_manager):
        """Test bulk URL processing."""
        urls = ["https://example.com/1", "https://example.com/2"]

        # Mock responses
        mock_article_results = {
            urls[0]: ArticleResult(success=True, url=urls[0], content="Content 1", method="direct"),
            urls[1]: ArticleResult(success=True, url=urls[1], content="Content 2", method="direct")
        }
        mock_article_manager.bulk_process_articles.return_value = mock_article_results

        mock_content_results = [
            ContentResult(content="Content 1", url=urls[0]),
            ContentResult(content="Content 2", url=urls[1])
        ]
        mock_pipeline.bulk_process_content.return_value = mock_content_results

        results = self.processor.bulk_process_urls(urls)

        assert len(results) == 2
        for article_result, content_result in results:
            assert article_result.success is True
            assert content_result is not None

    @patch('helpers.content_integration._integration.pipeline')
    def test_bulk_process_content(self, mock_pipeline):
        """Test bulk content processing."""
        content_items = [
            {'content': 'Content 1', 'title': 'Title 1'},
            {'content': 'Content 2', 'title': 'Title 2'}
        ]

        mock_results = [
            ContentResult(content="Content 1", title="Title 1"),
            ContentResult(content="Content 2", title="Title 2")
        ]
        mock_pipeline.bulk_process_content.return_value = mock_results

        results = self.processor.bulk_process_content(content_items)

        assert len(results) == 2
        mock_pipeline.bulk_process_content.assert_called_once_with(content_items)

    @patch('helpers.content_integration._integration.article_manager')
    @patch('helpers.content_integration._integration.pipeline')
    def test_get_processing_stats(self, mock_pipeline, mock_article_manager):
        """Test getting combined processing statistics."""
        # Mock stats from both components
        mock_article_stats = {'total_attempts': 10, 'total_successes': 8}
        mock_pipeline_stats = {'total_processed': 12, 'overall_success_rate': 0.75}

        mock_article_manager.get_processing_stats.return_value = mock_article_stats
        mock_pipeline.get_pipeline_stats.return_value = mock_pipeline_stats

        stats = self.processor.get_processing_stats()

        assert 'article_processing' in stats
        assert 'content_pipeline' in stats
        assert 'integration_stats' in stats

        assert stats['article_processing'] == mock_article_stats
        assert stats['content_pipeline'] == mock_pipeline_stats

    @patch('helpers.content_integration._integration.article_manager')
    @patch('helpers.content_integration._integration.pipeline')
    def test_reset_all_stats(self, mock_pipeline, mock_article_manager):
        """Test resetting all statistics."""
        self.processor.reset_all_stats()

        mock_article_manager.reset_stats.assert_called_once()
        mock_pipeline.reset_stats.assert_called_once()


class TestFactoryFunctions:
    """Test factory functions and utilities."""

    def test_create_unified_processor(self):
        """Test unified processor factory function."""
        config = {'test': 'config'}
        processor = create_unified_processor(config)

        assert isinstance(processor, UnifiedContentProcessor)
        assert processor.config == config

    def test_create_unified_processor_no_config(self):
        """Test factory with no config."""
        processor = create_unified_processor()

        assert isinstance(processor, UnifiedContentProcessor)
        assert processor.config == {}


class TestConfigurationIntegration:
    """Test configuration handling across components."""

    @patch('helpers.content_integration._integration.article_manager')
    @patch('helpers.content_integration._integration.pipeline')
    def test_config_propagation(self, mock_pipeline, mock_article_manager):
        """Test that configuration is properly propagated to components."""
        config = {
            'max_concurrent': 5,
            'enable_summarization': True,
            'preferred_strategies': ['direct', 'auth']
        }

        # Mock config attributes
        mock_article_manager.config = {}
        mock_pipeline.config = {}

        mock_article_result = ArticleResult(success=True, url="test", content="test")
        mock_content_result = ContentResult(content="test")

        mock_article_manager.process_article.return_value = mock_article_result
        mock_pipeline.process_content.return_value = mock_content_result

        # Process with config
        process_article_with_pipeline("https://example.com/test", config)

        # Verify config was updated on both components
        assert mock_article_manager.config.update.called
        assert mock_pipeline.config.update.called


class TestErrorHandlingIntegration:
    """Test error handling in integrated workflows."""

    @patch('helpers.content_integration._integration.article_manager')
    def test_article_manager_exception(self, mock_article_manager):
        """Test handling of article manager exceptions."""
        # Make article manager raise exception
        mock_article_manager.process_article.side_effect = Exception("Article manager failed")

        # Should not crash, should handle gracefully
        with pytest.raises(Exception):
            process_article_with_pipeline("https://example.com/test")

    @patch('helpers.content_integration._integration.article_manager')
    @patch('helpers.content_integration._integration.pipeline')
    def test_pipeline_exception(self, mock_pipeline, mock_article_manager):
        """Test handling of pipeline exceptions."""
        # Successful article fetch
        mock_article_result = ArticleResult(
            success=True,
            url="https://example.com/test",
            content="test",
            title="test"
        )
        mock_article_manager.process_article.return_value = mock_article_result

        # Pipeline raises exception
        mock_pipeline.process_content.side_effect = Exception("Pipeline failed")

        # Should handle gracefully
        with pytest.raises(Exception):
            process_article_with_pipeline("https://example.com/test")


class TestBackwardCompatibility:
    """Test backward compatibility with legacy interfaces."""

    def test_legacy_function_imports(self):
        """Test that legacy function imports work."""
        from helpers.content_integration import enhanced_article_processing
        from helpers.content_integration import process_content_comprehensive

        # Should be importable (will show deprecation warnings when called)
        assert enhanced_article_processing is not None
        assert process_content_comprehensive is not None

    @patch('helpers.content_integration._integration.article_manager')
    @patch('helpers.content_integration._integration.pipeline')
    def test_legacy_enhanced_article_processing(self, mock_pipeline, mock_article_manager):
        """Test legacy enhanced article processing function."""
        from helpers.content_integration import enhanced_article_processing

        # Setup mocks
        mock_article_result = ArticleResult(
            success=True,
            url="https://example.com/test",
            content="test content",
            title="test title",
            method="direct",
            error=None
        )
        mock_article_manager.process_article.return_value = mock_article_result

        mock_content_result = ContentResult(
            content="test content",
            classification={'category': 'test'},
            summary="test summary",
            quality_score=0.75
        )
        mock_pipeline.process_content.return_value = mock_content_result

        # Call legacy function (should show deprecation warning)
        with pytest.warns(DeprecationWarning):
            result = enhanced_article_processing("https://example.com/test")

        # Verify legacy format
        assert result['success'] is True
        assert result['url'] == "https://example.com/test"
        assert result['content'] == "test content"
        assert result['title'] == "test title"
        assert result['method'] == "direct"
        assert result['classification'] == {'category': 'test'}
        assert result['summary'] == "test summary"
        assert result['quality_score'] == 0.75


def run_unified_processing_tests():
    """Run all unified processing tests."""
    pytest.main([__file__, "-v"])


if __name__ == "__main__":
    run_unified_processing_tests()