"""
Unit tests for Skyvern Enhanced Ingestor

These tests mock Skyvern functionality to test the integration logic
without requiring actual Skyvern API access.
"""

import unittest
from unittest.mock import Mock, patch

import pytest

from helpers.metadata_manager import ContentMetadata, ContentType
from helpers.skyvern_enhanced_ingestor import (
    SkyvernEnhancedIngestor, SkyvernInstapaperEnhancer,
    create_skyvern_enhanced_ingestor)


class TestSkyvernEnhancedIngestor(unittest.TestCase):
    """Test cases for SkyvernEnhancedIngestor."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            "SKYVERN_ENABLED": False,  # Disabled by default for tests
            "SKYVERN_BASE_URL": "https://api.skyvern.com",
            "SKYVERN_API_KEY": "test-key",
            "USE_TRADITIONAL_SCRAPING": True,
            "SKYVERN_MAX_RETRIES": 2,
            "article_output_path": "test_output",
            "data_directory": "test_data",
        }

        self.sample_metadata = ContentMetadata(
            uid="test123",
            content_type=ContentType.ARTICLE,
            source="https://example.com/article",
            title="Test Article",
        )

    def test_init_without_skyvern(self):
        """Test initialization when Skyvern is disabled."""
        ingestor = SkyvernEnhancedIngestor(self.config)

        assert ingestor.content_type == ContentType.ARTICLE
        assert ingestor.module_name == "skyvern_enhanced_ingestor"
        assert not ingestor.skyvern_enabled
        assert ingestor.skyvern_client is None

    def test_init_with_skyvern_enabled(self):
        """Test initialization when Skyvern is enabled."""
        config = self.config.copy()
        config["SKYVERN_ENABLED"] = True

        with patch("helpers.skyvern_enhanced_ingestor.SKYVERN_AVAILABLE", True):
            with patch(
                "helpers.skyvern_enhanced_ingestor.SkyverhClient"
            ) as mock_client:
                ingestor = SkyvernEnhancedIngestor(config)

                assert ingestor.skyvern_enabled
                mock_client.assert_called_once_with(
                    base_url="https://api.skyvern.com", api_key="test-key"
                )

    def test_get_content_type(self):
        """Test content type identification."""
        ingestor = SkyvernEnhancedIngestor(self.config)
        assert ingestor.get_content_type() == ContentType.ARTICLE

    def test_is_supported_source(self):
        """Test source URL validation."""
        ingestor = SkyvernEnhancedIngestor(self.config)

        # Valid URLs
        assert ingestor.is_supported_source("https://example.com")
        assert ingestor.is_supported_source("http://example.com")

        # Invalid URLs
        assert not ingestor.is_supported_source("ftp://example.com")
        assert not ingestor.is_supported_source("file:///local/file.txt")
        assert not ingestor.is_supported_source("invalid-url")

    def test_site_detection_methods(self):
        """Test site detection for complex sites and paywalls."""
        ingestor = SkyvernEnhancedIngestor(self.config)

        # Complex sites
        assert ingestor._is_complex_site("https://medium.com/article")
        assert ingestor._is_complex_site("https://substack.com/article")
        assert not ingestor._is_complex_site("https://simple-blog.com/article")

        # Paywall sites
        assert ingestor._is_paywall_site("https://nytimes.com/article")
        assert ingestor._is_paywall_site("https://wsj.com/article")
        assert not ingestor._is_paywall_site("https://free-news.com/article")

    @patch("requests.get")
    @patch("readability.Document")
    def test_traditional_fetch_success(self, mock_document, mock_get):
        """Test successful traditional content fetching."""
        ingestor = SkyvernEnhancedIngestor(self.config)

        # Mock successful request
        mock_response = Mock()
        mock_response.text = "<html><body>Article content</body></html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Mock readability
        mock_doc = Mock()
        mock_doc.content.return_value = "<div>Clean article content</div>"
        mock_document.return_value = mock_doc

        success, result = ingestor._fetch_traditional(
            "https://example.com", self.sample_metadata
        )

        assert success
        assert result == "<div>Clean article content</div>"
        mock_get.assert_called_once()

    @patch("requests.get")
    def test_traditional_fetch_failure(self, mock_get):
        """Test failed traditional content fetching."""
        ingestor = SkyvernEnhancedIngestor(self.config)

        # Mock failed request
        mock_get.side_effect = Exception("Connection error")

        success, result = ingestor._fetch_traditional(
            "https://example.com", self.sample_metadata
        )

        assert not success
        assert "Traditional fetch failed" in result

    def test_fetch_content_strategy_selection(self):
        """Test content fetching strategy selection."""
        ingestor = SkyvernEnhancedIngestor(self.config)

        with patch.object(ingestor, "_fetch_traditional") as mock_traditional:
            mock_traditional.return_value = (True, "<div>Content</div>")

            success, result = ingestor.fetch_content(
                "https://simple-site.com", self.sample_metadata
            )

            assert success
            assert result == "<div>Content</div>"
            assert self.sample_metadata.fetch_method == "traditional"

    def test_generate_extraction_prompt_generic(self):
        """Test generic extraction prompt generation."""
        ingestor = SkyvernEnhancedIngestor(self.config)

        prompt = ingestor._generate_extraction_prompt(
            "https://unknown-site.com/article", self.sample_metadata
        )

        assert "Navigate to https://unknown-site.com/article" in prompt
        assert "main article content" in prompt
        assert "popups" in prompt

    def test_generate_extraction_prompt_site_specific(self):
        """Test site-specific extraction prompt generation."""
        ingestor = SkyvernEnhancedIngestor(self.config)

        prompt = ingestor._generate_extraction_prompt(
            "https://medium.com/article", self.sample_metadata
        )

        assert "paywall popup" in prompt
        assert "claps, comments" in prompt

    def test_get_site_credentials(self):
        """Test site credential retrieval."""
        config = self.config.copy()
        config["NYTIMES_USERNAME"] = "test@example.com"
        config["NYTIMES_PASSWORD"] = "testpass"

        ingestor = SkyvernEnhancedIngestor(config)

        creds = ingestor._get_site_credentials("nytimes.com")
        assert creds is not None
        assert creds["username"] == "test@example.com"
        assert creds["password"] == "testpass"

        # No credentials for unknown site
        assert ingestor._get_site_credentials("unknown-site.com") is None

    @patch("helpers.skyvern_enhanced_ingestor.convert_html_to_markdown")
    def test_process_content_success(self, mock_convert):
        """Test successful content processing."""
        ingestor = SkyvernEnhancedIngestor(self.config)
        mock_convert.return_value = "# Test Article\n\nContent here"

        success = ingestor.process_content(
            "<div>HTML content</div>", self.sample_metadata
        )

        assert success
        assert "content" in self.sample_metadata.type_specific
        assert "content_length" in self.sample_metadata.type_specific
        assert (
            self.sample_metadata.type_specific["content"]
            == "# Test Article\n\nContent here"
        )


class TestSkyvernInstapaperEnhancer(unittest.TestCase):
    """Test cases for SkyvernInstapaperEnhancer."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            "SKYVERN_ENABLED": False,
            "SKYVERN_BASE_URL": "https://api.skyvern.com",
            "SKYVERN_API_KEY": "test-key",
        }

    def test_init_without_skyvern(self):
        """Test initialization when Skyvern is disabled."""
        enhancer = SkyvernInstapaperEnhancer(self.config)
        assert not enhancer.skyvern_enabled

    def test_scrape_without_skyvern_raises_error(self):
        """Test that scraping without Skyvern raises appropriate error."""
        enhancer = SkyvernInstapaperEnhancer(self.config)

        with pytest.raises(RuntimeError, match="Skyvern not available"):
            enhancer.scrape_instapaper_intelligently("user", "pass")


class TestCreateFunction(unittest.TestCase):
    """Test the factory function."""

    def test_create_skyvern_enhanced_ingestor(self):
        """Test ingestor creation function."""
        config = {"test": "value"}
        ingestor = create_skyvern_enhanced_ingestor(config)

        assert isinstance(ingestor, SkyvernEnhancedIngestor)
        assert ingestor.config == config


class TestIntegrationScenarios(unittest.TestCase):
    """Test realistic integration scenarios."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            "SKYVERN_ENABLED": True,
            "SKYVERN_BASE_URL": "https://api.skyvern.com",
            "SKYVERN_API_KEY": "test-key",
            "USE_TRADITIONAL_SCRAPING": True,
            "article_output_path": "test_output",
            "data_directory": "test_data",
            "NYTIMES_USERNAME": "test@example.com",
            "NYTIMES_PASSWORD": "testpass",
        }

    @patch("helpers.skyvern_enhanced_ingestor.SKYVERN_AVAILABLE", True)
    @patch("helpers.skyvern_enhanced_ingestor.SkyverhClient")
    def test_paywall_site_handling(self, mock_client_class):
        """Test handling of paywall sites with credentials."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Mock successful Skyvern task
        mock_result = Mock()
        mock_result.success = True
        mock_result.extracted_content = "<div>Full article content</div>"
        mock_client.run_task.return_value = mock_result

        ingestor = SkyvernEnhancedIngestor(self.config)
        metadata = ContentMetadata(
            uid="test123",
            content_type=ContentType.ARTICLE,
            source="https://nytimes.com/article",
            title="NYT Article",
        )

        success, result = ingestor._fetch_paywall_content(
            "https://nytimes.com/article", metadata
        )

        assert success
        assert result == "<div>Full article content</div>"

        # Verify Skyvern was called with login prompt
        mock_client.run_task.assert_called_once()
        args, kwargs = mock_client.run_task.call_args
        assert "login credentials" in kwargs["prompt"]
        assert "test@example.com" in kwargs["prompt"]

    @patch("requests.get")
    def test_fallback_strategy(self, mock_get):
        """Test fallback from traditional to Skyvern."""
        # Mock failed traditional request
        mock_get.side_effect = Exception("403 Forbidden")

        ingestor = SkyvernEnhancedIngestor(self.config)
        ingestor.skyvern_enabled = False  # Disable Skyvern for this test

        metadata = ContentMetadata(
            uid="test123",
            content_type=ContentType.ARTICLE,
            source="https://complex-site.com/article",
            title="Complex Article",
        )

        success, result = ingestor.fetch_content(
            "https://complex-site.com/article", metadata
        )

        # Should fail since Skyvern is disabled and traditional failed
        assert not success
        assert "All fetching strategies failed" in result


if __name__ == "__main__":
    unittest.main()
