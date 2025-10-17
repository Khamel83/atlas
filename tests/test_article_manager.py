#!/usr/bin/env python3
"""
Test suite for ArticleManager

Tests unified article processing with strategy cascade, statistics tracking,
and bulk processing capabilities.
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from helpers.article_manager import ArticleManager, ArticleResult, ProcessingStats
from helpers.base_article_strategy import BaseArticleStrategy, StrategyMetadata, FetchResult


class MockStrategy(BaseArticleStrategy):
    """Mock strategy for testing."""

    def __init__(self, name="mock", success=True, content="Mock content", error=None):
        super().__init__()
        self.strategy_name = name
        self.should_succeed = success
        self.mock_content = content
        self.mock_error = error
        self.call_count = 0

    def get_metadata(self) -> StrategyMetadata:
        from helpers.base_article_strategy import StrategyPriority, StrategyCapability
        return StrategyMetadata(
            name=self.strategy_name,
            priority=StrategyPriority.MEDIUM,
            capabilities=[StrategyCapability.BASIC_FETCH],
            estimated_success_rate=0.8
        )

    def fetch(self, url: str, log_path: str = "", **kwargs) -> FetchResult:
        self.call_count += 1

        if self.should_succeed:
            return FetchResult(
                success=True,
                url=url,
                content=self.mock_content,
                title="Mock Title",
                method=self.strategy_name,
                strategy=self.strategy_name
            )
        else:
            return FetchResult(
                success=False,
                url=url,
                error=self.mock_error or "Mock error",
                method=self.strategy_name,
                strategy=self.strategy_name
            )


class TestArticleManager:
    """Test cases for ArticleManager."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = {
            'stats_file': str(Path(self.temp_dir) / 'test_stats.json'),
            'max_concurrent': 2
        }
        self.manager = ArticleManager(self.config)

    def test_initialization(self):
        """Test ArticleManager initialization."""
        assert self.manager is not None
        assert self.manager.config == self.config
        assert isinstance(self.manager.stats, ProcessingStats)
        assert self.manager.max_concurrent == 2

    @patch('helpers.article_manager.ArticleManager._initialize_strategies')
    def test_strategy_initialization(self, mock_init_strategies):
        """Test strategy initialization."""
        # Mock strategies
        mock_strategies = [
            ('mock1', MockStrategy('mock1', True)),
            ('mock2', MockStrategy('mock2', False))
        ]
        mock_init_strategies.return_value = mock_strategies

        manager = ArticleManager(self.config)
        strategies = manager.strategies

        assert len(strategies) == 2
        assert strategies[0][0] == 'mock1'
        assert strategies[1][0] == 'mock2'

    def test_single_article_processing_success(self):
        """Test successful single article processing."""
        # Mock the strategy initialization
        with patch.object(self.manager, '_initialize_strategies') as mock_init:
            mock_strategy = MockStrategy('test_strategy', success=True, content="Test content")
            mock_init.return_value = [('test_strategy', mock_strategy)]

            # Reset strategies to trigger re-initialization
            self.manager._strategies = None

            result = self.manager.process_article("https://example.com/test")

            assert result.success is True
            assert result.url == "https://example.com/test"
            assert result.content == "Test content"
            assert result.title == "Mock Title"
            assert result.method == "test_strategy"
            assert result.strategy == "test_strategy"
            assert result.processing_time > 0
            assert mock_strategy.call_count == 1

    def test_single_article_processing_failure(self):
        """Test failed single article processing."""
        with patch.object(self.manager, '_initialize_strategies') as mock_init:
            mock_strategy = MockStrategy('test_strategy', success=False, error="Test error")
            mock_init.return_value = [('test_strategy', mock_strategy)]

            # Reset strategies to trigger re-initialization
            self.manager._strategies = None

            result = self.manager.process_article("https://example.com/test")

            assert result.success is False
            assert result.url == "https://example.com/test"
            assert "Test error" in result.error
            assert result.processing_time > 0
            assert mock_strategy.call_count == 1

    def test_strategy_cascade(self):
        """Test strategy cascade with fallback."""
        with patch.object(self.manager, '_initialize_strategies') as mock_init:
            # First strategy fails, second succeeds
            failing_strategy = MockStrategy('failing', success=False, error="First failed")
            success_strategy = MockStrategy('success', success=True, content="Success content")

            mock_init.return_value = [
                ('failing', failing_strategy),
                ('success', success_strategy)
            ]

            # Reset strategies
            self.manager._strategies = None

            result = self.manager.process_article("https://example.com/test")

            assert result.success is True
            assert result.content == "Success content"
            assert result.method == "success"

            # Both strategies should have been tried
            assert failing_strategy.call_count == 1
            assert success_strategy.call_count == 1

    def test_preferred_strategies(self):
        """Test preferred strategy selection."""
        with patch.object(self.manager, '_initialize_strategies') as mock_init:
            strategy1 = MockStrategy('strategy1', success=True, content="Content 1")
            strategy2 = MockStrategy('strategy2', success=True, content="Content 2")

            mock_init.return_value = [
                ('strategy1', strategy1),
                ('strategy2', strategy2)
            ]

            # Reset strategies
            self.manager._strategies = None

            # Test with preferred strategies
            result = self.manager.process_article(
                "https://example.com/test",
                preferred_strategies=['strategy2']
            )

            assert result.success is True
            assert result.method == "strategy2"
            assert result.content == "Content 2"

            # Only strategy2 should have been tried
            assert strategy1.call_count == 0
            assert strategy2.call_count == 1

    def test_bulk_processing(self):
        """Test bulk article processing."""
        with patch.object(self.manager, '_initialize_strategies') as mock_init:
            mock_strategy = MockStrategy('bulk_test', success=True, content="Bulk content")
            mock_init.return_value = [('bulk_test', mock_strategy)]

            # Reset strategies
            self.manager._strategies = None

            urls = [
                "https://example.com/1",
                "https://example.com/2",
                "https://example.com/3"
            ]

            results = self.manager.bulk_process_articles(urls, max_concurrent=2)

            assert len(results) == 3

            for url in urls:
                assert url in results
                result = results[url]
                assert result.success is True
                assert result.content == "Bulk content"
                assert result.method == "bulk_test"

            # Strategy should have been called 3 times
            assert mock_strategy.call_count == 3

    def test_failed_article_recovery(self):
        """Test recovery for failed articles."""
        with patch.object(self.manager, '_initialize_strategies') as mock_init:
            # Setup strategies with different success patterns
            auth_strategy = MockStrategy('auth', success=True, content="Auth content")
            wayback_strategy = MockStrategy('wayback_enhanced', success=True, content="Archive content")

            mock_init.return_value = [
                ('direct', MockStrategy('direct', success=False)),
                ('auth', auth_strategy),
                ('wayback_enhanced', wayback_strategy)
            ]

            # Reset strategies
            self.manager._strategies = None

            failed_urls = ["https://example.com/failed1", "https://example.com/failed2"]

            results = self.manager.recover_failed_articles(failed_urls)

            assert len(results) == 2

            for url in failed_urls:
                result = results[url]
                assert result.success is True
                # Should use auth strategy first in recovery
                assert result.method == "auth"

    def test_statistics_tracking(self):
        """Test processing statistics tracking."""
        with patch.object(self.manager, '_initialize_strategies') as mock_init:
            mock_strategy = MockStrategy('stats_test', success=True)
            mock_init.return_value = [('stats_test', mock_strategy)]

            # Reset strategies
            self.manager._strategies = None

            # Process some articles
            urls = ["https://example.com/1", "https://example.com/2"]

            for url in urls:
                self.manager.process_article(url)

            stats = self.manager.get_processing_stats()

            assert stats['total_attempts'] == 2
            assert stats['total_successes'] == 2
            assert stats['total_failures'] == 0
            assert stats['overall_success_rate'] == 1.0

            # Strategy-specific stats
            assert 'stats_test' in stats['strategy_success_rates']
            strategy_stats = stats['strategy_success_rates']['stats_test']
            assert strategy_stats['success_rate'] == 1.0
            assert strategy_stats['attempts'] == 2

    def test_stats_persistence(self):
        """Test statistics persistence to disk."""
        with patch.object(self.manager, '_initialize_strategies') as mock_init:
            mock_strategy = MockStrategy('persist_test', success=True)
            mock_init.return_value = [('persist_test', mock_strategy)]

            # Reset strategies
            self.manager._strategies = None

            # Process an article to generate stats
            self.manager.process_article("https://example.com/persist")

            # Check that stats file was created
            stats_file = Path(self.config['stats_file'])
            assert stats_file.exists()

            # Load stats from file
            with open(stats_file, 'r') as f:
                saved_stats = json.load(f)

            assert saved_stats['total_attempts'] == 1
            assert saved_stats['total_successes'] == 1
            assert 'persist_test' in saved_stats['strategy_stats']

    def test_strategy_ordering_by_success_rate(self):
        """Test strategy ordering based on historical success rates."""
        # Create manager with pre-existing stats
        initial_stats = ProcessingStats()
        initial_stats.strategy_stats = {
            'low_success': {'attempts': 10, 'successes': 2, 'failures': 8},  # 20%
            'high_success': {'attempts': 10, 'successes': 9, 'failures': 1}   # 90%
        }

        self.manager.stats = initial_stats

        with patch.object(self.manager, '_initialize_strategies') as mock_init:
            low_strategy = MockStrategy('low_success', success=True)
            high_strategy = MockStrategy('high_success', success=True)

            mock_init.return_value = [
                ('low_success', low_strategy),
                ('high_success', high_strategy)
            ]

            # Reset strategies
            self.manager._strategies = None

            # Get strategy order (should prioritize high_success)
            strategy_order = self.manager._get_strategy_order()

            # High success strategy should come first
            assert strategy_order[0][0] == 'high_success'
            assert strategy_order[1][0] == 'low_success'

    def test_export_stats(self):
        """Test statistics export functionality."""
        with patch.object(self.manager, '_initialize_strategies') as mock_init:
            mock_strategy = MockStrategy('export_test', success=True)
            mock_init.return_value = [('export_test', mock_strategy)]

            # Reset strategies and process article
            self.manager._strategies = None
            self.manager.process_article("https://example.com/export")

            # Export stats
            export_path = self.manager.export_stats()

            assert Path(export_path).exists()

            # Load and verify exported stats
            with open(export_path, 'r') as f:
                exported_stats = json.load(f)

            assert exported_stats['total_attempts'] == 1
            assert exported_stats['overall_success_rate'] == 1.0
            assert 'export_test' in exported_stats['strategy_success_rates']


class TestArticleResultDataClass:
    """Test ArticleResult data class."""

    def test_article_result_creation(self):
        """Test ArticleResult creation and properties."""
        result = ArticleResult(
            success=True,
            url="https://example.com/test",
            content="Test content",
            title="Test Title",
            method="test_method"
        )

        assert result.success is True
        assert result.url == "https://example.com/test"
        assert result.content == "Test content"
        assert result.title == "Test Title"
        assert result.method == "test_method"
        assert result.strategy == "test_method"  # Should sync
        assert result.metadata == {}
        assert result.timestamp is not None

    def test_method_strategy_sync(self):
        """Test method and strategy synchronization."""
        # Test method -> strategy sync
        result1 = ArticleResult(success=True, url="test", method="test_method")
        assert result1.strategy == "test_method"

        # Test strategy -> method sync
        result2 = ArticleResult(success=True, url="test", strategy="test_strategy")
        assert result2.method == "test_strategy"


class TestBackwardCompatibility:
    """Test backward compatibility with legacy ArticleFetcher."""

    def test_legacy_article_fetcher(self):
        """Test legacy ArticleFetcher compatibility."""
        from helpers.article_manager import ArticleFetcher

        # Should create with deprecation warning
        with pytest.warns(DeprecationWarning):
            fetcher = ArticleFetcher({'test': 'config'})

        assert fetcher.manager is not None
        assert isinstance(fetcher.manager, ArticleManager)

    def test_legacy_fetch_with_fallbacks(self):
        """Test legacy fetch_with_fallbacks method."""
        from helpers.article_manager import ArticleFetcher

        with pytest.warns(DeprecationWarning):
            fetcher = ArticleFetcher()

        # Mock the manager's process_article method
        mock_result = ArticleResult(
            success=True,
            url="https://example.com/test",
            content="Test content",
            title="Test Title",
            method="test_method"
        )

        fetcher.manager.process_article = Mock(return_value=mock_result)

        # Call legacy method
        result = fetcher.fetch_with_fallbacks("https://example.com/test", "")

        # Should return FetchResult in old format
        from helpers.article_strategies import FetchResult
        assert isinstance(result, FetchResult)
        assert result.success is True
        assert result.content == "Test content"
        assert result.method == "test_method"


def run_article_manager_tests():
    """Run all ArticleManager tests."""
    pytest.main([__file__, "-v"])


if __name__ == "__main__":
    run_article_manager_tests()