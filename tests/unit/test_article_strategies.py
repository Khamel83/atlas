"""
Unit tests for helpers.article_strategies module.

Tests all article fetching strategies, content analysis, and orchestration logic.
"""

from unittest.mock import patch

import pytest

# Import the module under test
from helpers.article_strategies import (ArchiveTodayStrategy, ArticleFetcher,
                                        ContentAnalyzer,
                                        DirectFetchStrategy, FetchResult,
                                        GooglebotStrategy, PlaywrightStrategy,
                                        WaybackMachineStrategy)


class TestFetchResult:
    """Test the FetchResult data class."""

    @pytest.mark.unit
    def test_fetch_result_creation(self):
        """Test FetchResult creation with all parameters."""
        result = FetchResult(
            success=True,
            content="Test content",
            title="Test Title",
            strategy="direct",
            error=None,
            metadata={"key": "value"},
        )

        assert result.success is True
        assert result.content == "Test content"
        assert result.title == "Test Title"
        assert result.strategy == "direct"
        assert result.error is None
        assert result.metadata == {"key": "value"}

    @pytest.mark.unit
    def test_fetch_result_defaults(self):
        """Test FetchResult with default values."""
        result = FetchResult(success=False, strategy="test")

        assert result.success is False
        assert result.content is None
        assert result.title is None
        assert result.strategy == "test"
        assert result.error is None
        assert result.metadata == {}


class TestContentAnalyzer:
    """Test the ContentAnalyzer class."""

    @pytest.fixture
    def analyzer(self):
        """Create ContentAnalyzer instance."""
        return ContentAnalyzer()

    @pytest.mark.unit
    def test_is_likely_paywall_keywords(self, analyzer):
        """Test paywall detection by keywords."""
        paywall_content = "Please subscribe to continue reading this article"
        assert analyzer.is_likely_paywall(paywall_content) is True

        normal_content = "This is a normal article with regular content"
        assert analyzer.is_likely_paywall(normal_content) is False

    @pytest.mark.unit
    def test_is_likely_paywall_length(self, analyzer):
        """Test paywall detection by content length."""
        short_content = "Short"
        assert analyzer.is_likely_paywall(short_content) is True

        long_content = "This is a much longer article " * 20
        assert analyzer.is_likely_paywall(long_content) is False

    @pytest.mark.unit
    def test_is_likely_paywall_word_count(self, analyzer):
        """Test paywall detection by word count."""
        few_words = "Only few words here"
        assert analyzer.is_likely_paywall(few_words) is True

        many_words = " ".join(["word"] * 100)
        assert analyzer.is_likely_paywall(many_words) is False

    @pytest.mark.unit
    def test_extract_title_from_html(self, analyzer):
        """Test title extraction from HTML."""
        html = """
        <html>
        <head><title>Test Title</title></head>
        <body>Content</body>
        </html>
        """
        assert analyzer.extract_title_from_html(html) == "Test Title"

    @pytest.mark.unit
    def test_extract_title_from_h1(self, analyzer):
        """Test title extraction from H1 tag."""
        html = """
        <html>
        <body><h1>H1 Title</h1><p>Content</p></body>
        </html>
        """
        assert analyzer.extract_title_from_html(html) == "H1 Title"

    @pytest.mark.unit
    def test_extract_title_fallback(self, analyzer):
        """Test title extraction fallback."""
        html = "<html><body>No title</body></html>"
        assert analyzer.extract_title_from_html(html) == "Untitled"


class TestDirectFetchStrategy:
    """Test the DirectFetchStrategy class."""

    @pytest.fixture
    def strategy(self):
        """Create DirectFetchStrategy instance."""
        return DirectFetchStrategy()

    @pytest.mark.unit
    def test_fetch_success(self, strategy, mock_requests, sample_article_html):
        """Test successful direct fetch."""
        url = "https://example.com/article"
        mock_requests["get"].return_value.text = sample_article_html
        mock_requests["get"].return_value.status_code = 200

        result = strategy.fetch(url)

        assert result.success is True
        assert result.strategy == "direct"
        assert result.content is not None
        assert result.title == "Test Article Title"

        # Verify request was made correctly
        mock_requests["get"].assert_called_once_with(
            url, headers=strategy.headers, timeout=30, allow_redirects=True
        )

    @pytest.mark.unit
    def test_fetch_http_error(self, strategy, mock_requests):
        """Test fetch with HTTP error."""
        url = "https://example.com/article"
        mock_requests["get"].return_value.status_code = 404
        mock_requests["get"].return_value.raise_for_status.side_effect = Exception(
            "404 Not Found"
        )

        result = strategy.fetch(url)

        assert result.success is False
        assert result.strategy == "direct"
        assert result.error is not None
        assert "404 Not Found" in str(result.error)

    @pytest.mark.unit
    def test_fetch_network_error(self, strategy, mock_requests):
        """Test fetch with network error."""
        url = "https://example.com/article"
        mock_requests["get"].side_effect = Exception("Network error")

        result = strategy.fetch(url)

        assert result.success is False
        assert result.strategy == "direct"
        assert result.error is not None
        assert "Network error" in str(result.error)


class TestTwelveFtStrategy:
    """Test the TwelveFtStrategy class."""

    @pytest.fixture
    def strategy(self):
        """Create TwelveFtStrategy instance."""
        return TwelveFtStrategy()

    @pytest.mark.unit
    def test_fetch_success(self, strategy, mock_requests, sample_article_html):
        """Test successful 12ft.io fetch."""
        url = "https://example.com/article"
        expected_url = f"https://12ft.io/{url}"
        mock_requests["get"].return_value.text = sample_article_html
        mock_requests["get"].return_value.status_code = 200

        result = strategy.fetch(url)

        assert result.success is True
        assert result.strategy == "12ft.io"
        assert result.content is not None

        # Verify correct URL was used
        mock_requests["get"].assert_called_once_with(
            expected_url, headers=strategy.headers, timeout=30, allow_redirects=True
        )


class TestArchiveTodayStrategy:
    """Test the ArchiveTodayStrategy class."""

    @pytest.fixture
    def strategy(self):
        """Create ArchiveTodayStrategy instance."""
        return ArchiveTodayStrategy()

    @pytest.mark.unit
    def test_fetch_success(self, strategy, mock_requests, sample_article_html):
        """Test successful archive.today fetch."""
        url = "https://example.com/article"
        expected_url = f"https://archive.today/{url}"
        mock_requests["get"].return_value.text = sample_article_html
        mock_requests["get"].return_value.status_code = 200

        result = strategy.fetch(url)

        assert result.success is True
        assert result.strategy == "archive.today"
        assert result.content is not None

        # Verify correct URL was used
        mock_requests["get"].assert_called_once_with(
            expected_url, headers=strategy.headers, timeout=30, allow_redirects=True
        )


class TestGooglebotStrategy:
    """Test the GooglebotStrategy class."""

    @pytest.fixture
    def strategy(self):
        """Create GooglebotStrategy instance."""
        return GooglebotStrategy()

    @pytest.mark.unit
    def test_fetch_success(self, strategy, mock_requests, sample_article_html):
        """Test successful Googlebot fetch."""
        url = "https://example.com/article"
        mock_requests["get"].return_value.text = sample_article_html
        mock_requests["get"].return_value.status_code = 200

        result = strategy.fetch(url)

        assert result.success is True
        assert result.strategy == "googlebot"
        assert result.content is not None

        # Verify Googlebot user agent was used
        call_args = mock_requests["get"].call_args
        assert "Googlebot" in call_args[1]["headers"]["User-Agent"]


class TestPlaywrightStrategy:
    """Test the PlaywrightStrategy class."""

    @pytest.fixture
    def strategy(self):
        """Create PlaywrightStrategy instance."""
        return PlaywrightStrategy()

    @pytest.mark.unit
    def test_fetch_success(self, strategy, mock_playwright, sample_article_html):
        """Test successful Playwright fetch."""
        url = "https://example.com/article"
        mock_playwright["page"].content.return_value = sample_article_html
        mock_playwright["page"].title.return_value = "Test Article Title"

        result = strategy.fetch(url)

        assert result.success is True
        assert result.strategy == "playwright"
        assert result.content is not None
        assert result.title == "Test Article Title"

        # Verify Playwright methods were called
        mock_playwright["page"].goto.assert_called_once_with(
            url, wait_until="networkidle"
        )
        mock_playwright["page"].content.assert_called_once()
        mock_playwright["page"].title.assert_called_once()

    @pytest.mark.unit
    def test_fetch_error(self, strategy, mock_playwright):
        """Test Playwright fetch with error."""
        url = "https://example.com/article"
        mock_playwright["page"].goto.side_effect = Exception("Navigation failed")

        result = strategy.fetch(url)

        assert result.success is False
        assert result.strategy == "playwright"
        assert result.error is not None
        assert "Navigation failed" in str(result.error)


class TestWaybackMachineStrategy:
    """Test the WaybackMachineStrategy class."""

    @pytest.fixture
    def strategy(self):
        """Create WaybackMachineStrategy instance."""
        return WaybackMachineStrategy()

    @pytest.mark.unit
    def test_fetch_success(self, strategy, mock_requests, sample_article_html):
        """Test successful Wayback Machine fetch."""
        url = "https://example.com/article"
        expected_url = f"https://web.archive.org/web/{url}"
        mock_requests["get"].return_value.text = sample_article_html
        mock_requests["get"].return_value.status_code = 200

        result = strategy.fetch(url)

        assert result.success is True
        assert result.strategy == "wayback"
        assert result.content is not None

        # Verify correct URL was used
        mock_requests["get"].assert_called_once_with(
            expected_url, headers=strategy.headers, timeout=30, allow_redirects=True
        )


class TestArticleFetcher:
    """Test the ArticleFetcher orchestrator class."""

    @pytest.fixture
    def fetcher(self):
        """Create ArticleFetcher instance."""
        return ArticleFetcher()

    @pytest.mark.unit
    def test_fetch_success_first_strategy(
        self, fetcher, mock_requests, sample_article_html
    ):
        """Test successful fetch with first strategy."""
        url = "https://example.com/article"
        mock_requests["get"].return_value.text = sample_article_html
        mock_requests["get"].return_value.status_code = 200

        result = fetcher.fetch_article(url)

        assert result.success is True
        assert result.strategy == "direct"
        assert result.content is not None
        assert result.title == "Test Article Title"

    @pytest.mark.unit
    def test_fetch_fallback_strategies(
        self, fetcher, mock_requests, sample_article_html
    ):
        """Test fallback to other strategies when first fails."""
        url = "https://example.com/article"

        # First call fails, second succeeds
        mock_requests["get"].side_effect = [
            Exception("Network error"),  # Direct strategy fails
            mock_requests["response"],  # 12ft.io succeeds
        ]
        mock_requests["response"].text = sample_article_html
        mock_requests["response"].status_code = 200

        result = fetcher.fetch_article(url)

        assert result.success is True
        assert result.strategy == "12ft.io"
        assert result.content is not None

        # Verify multiple strategies were tried
        assert mock_requests["get"].call_count == 2

    @pytest.mark.unit
    def test_fetch_all_strategies_fail(self, fetcher, mock_requests):
        """Test when all strategies fail."""
        url = "https://example.com/article"
        mock_requests["get"].side_effect = Exception("Network error")

        with patch("helpers.article_strategies.sync_playwright") as mock_playwright:
            mock_playwright.return_value.__enter__.return_value.chromium.launch.side_effect = Exception(
                "Browser error"
            )

            result = fetcher.fetch_article(url)

        assert result.success is False
        assert result.error is not None
        assert "All strategies failed" in str(result.error)

    @pytest.mark.unit
    def test_fetch_paywall_detection(self, fetcher, mock_requests):
        """Test paywall detection and strategy escalation."""
        url = "https://example.com/article"
        paywall_content = "Please subscribe to continue reading"

        # First strategy returns paywall content
        mock_requests["get"].return_value.text = paywall_content
        mock_requests["get"].return_value.status_code = 200

        # Mock the content analyzer to detect paywall
        with patch.object(fetcher.analyzer, "is_likely_paywall", return_value=True):
            fetcher.fetch_article(url)

        # Should try multiple strategies due to paywall detection
        assert mock_requests["get"].call_count > 1

    @pytest.mark.unit
    def test_get_available_strategies(self, fetcher):
        """Test getting list of available strategies."""
        strategies = fetcher.get_available_strategies()

        expected_strategies = [
            "direct",
            "12ft.io",
            "archive.today",
            "googlebot",
            "playwright",
            "wayback",
        ]
        assert strategies == expected_strategies

    @pytest.mark.unit
    def test_fetch_with_specific_strategy(
        self, fetcher, mock_requests, sample_article_html
    ):
        """Test fetching with a specific strategy."""
        url = "https://example.com/article"
        mock_requests["get"].return_value.text = sample_article_html
        mock_requests["get"].return_value.status_code = 200

        result = fetcher.fetch_article(url, strategy="12ft.io")

        assert result.success is True
        assert result.strategy == "12ft.io"

        # Verify only the specified strategy was used
        expected_url = f"https://12ft.io/{url}"
        mock_requests["get"].assert_called_once_with(
            expected_url,
            headers=fetcher.strategies[1].headers,
            timeout=30,
            allow_redirects=True,
        )

    @pytest.mark.unit
    def test_fetch_with_invalid_strategy(self, fetcher):
        """Test fetching with invalid strategy name."""
        url = "https://example.com/article"

        with pytest.raises(ValueError, match="Unknown strategy"):
            fetcher.fetch_article(url, strategy="invalid")

    @pytest.mark.unit
    def test_metadata_extraction(self, fetcher, mock_requests):
        """Test metadata extraction from fetched content."""
        url = "https://example.com/article"
        html_with_metadata = """
        <html>
        <head>
            <title>Test Article</title>
            <meta name="author" content="Test Author">
            <meta name="description" content="Test description">
            <meta property="article:published_time" content="2024-01-01">
        </head>
        <body>
            <article>Content here</article>
        </body>
        </html>
        """
        mock_requests["get"].return_value.text = html_with_metadata
        mock_requests["get"].return_value.status_code = 200

        result = fetcher.fetch_article(url)

        assert result.success is True
        assert result.metadata is not None
        assert "author" in result.metadata
        assert "description" in result.metadata
        assert "published_time" in result.metadata


class TestArticleStrategiesIntegration:
    """Integration tests for article strategies."""

    @pytest.mark.integration
    def test_full_article_fetch_pipeline(self, mock_requests, sample_article_html):
        """Test complete article fetching pipeline."""
        url = "https://example.com/article"
        mock_requests["get"].return_value.text = sample_article_html
        mock_requests["get"].return_value.status_code = 200

        fetcher = ArticleFetcher()
        result = fetcher.fetch_article(url)

        # Verify complete result
        assert result.success is True
        assert result.content is not None
        assert result.title == "Test Article Title"
        assert result.strategy == "direct"
        assert result.metadata is not None
        assert result.error is None

    @pytest.mark.integration
    def test_strategy_fallback_chain(self, mock_requests, sample_article_html):
        """Test complete strategy fallback chain."""
        url = "https://example.com/article"

        # Simulate different failure modes
        responses = [
            Exception("Direct fetch failed"),
            Exception("12ft.io failed"),
            Exception("Archive.today failed"),
            Exception("Googlebot failed"),
            Exception("Playwright failed"),
            mock_requests["response"],  # Wayback succeeds
        ]

        mock_requests["get"].side_effect = responses
        mock_requests["response"].text = sample_article_html
        mock_requests["response"].status_code = 200

        with patch("helpers.article_strategies.sync_playwright") as mock_playwright:
            mock_playwright.return_value.__enter__.return_value.chromium.launch.side_effect = Exception(
                "Browser error"
            )

            fetcher = ArticleFetcher()
            result = fetcher.fetch_article(url)

        assert result.success is True
        assert result.strategy == "wayback"
        assert result.content is not None
