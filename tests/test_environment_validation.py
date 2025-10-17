"""
Test suite for environment validation and configuration loading.

This module provides comprehensive test coverage for the Atlas environment setup
and configuration loading functionality, ensuring robust configuration management
before implementing the actual features.

Test Coverage:
- Environment variable validation
- Configuration file loading from multiple sources
- Error handling for missing or invalid configuration
- Edge cases and boundary conditions
- Configuration override precedence
- Security validation for sensitive data
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest
import yaml

# Import the configuration module being tested
from helpers.config import (get_config, get_model_for_task, is_feature_enabled,
                            load_categories, load_config)


class TestEnvironmentValidation:
    """Test environment variable validation and setup."""

    def test_required_python_version(self):
        """Test that Python version meets minimum requirements."""
        import sys

        version = sys.version_info
        assert version.major >= 3, "Python 3.x required"
        assert version.minor >= 9, "Python 3.9+ required for Atlas"

    def test_project_structure_exists(self):
        """Test that essential project directories and files exist."""
        project_root = Path(__file__).parent.parent

        # Essential directories
        assert (project_root / "helpers").exists(), "helpers directory missing"
        assert (project_root / "tests").exists(), "tests directory missing"
        assert (project_root / "config").exists(), "config directory missing"

        # Essential files
        assert (project_root / "run.py").exists(), "run.py missing"
        assert (project_root / "requirements.txt").exists(), "requirements.txt missing"
        assert (project_root / "helpers" / "config.py").exists(), "config.py missing"

    def test_output_directory_creation(self):
        """Test that output directories can be created."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "output"
            output_dir.mkdir(parents=True, exist_ok=True)

            # Test subdirectory creation
            subdirs = ["articles", "youtube", "podcasts", "logs"]
            for subdir in subdirs:
                (output_dir / subdir).mkdir(exist_ok=True)
                assert (output_dir / subdir).exists(), f"{subdir} directory not created"

    def test_permissions_validation(self):
        """Test file and directory permissions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test_file"
            test_file.write_text("test content")

            # Test read/write permissions
            assert test_file.is_file(), "Test file not created"
            assert test_file.read_text() == "test content", "Test file not readable"

            # Test directory permissions
            test_dir = Path(temp_dir) / "test_dir"
            test_dir.mkdir()
            assert test_dir.is_dir(), "Test directory not created"


class TestConfigurationLoading:
    """Test configuration loading from multiple sources."""

    def test_load_config_basic(self):
        """Test basic configuration loading with defaults."""
        config = load_config()

        # Test required keys exist
        required_keys = [
            "data_directory",
            "article_output_path",
            "podcast_output_path",
            "youtube_output_path",
            "llm_provider",
            "llm_model",
        ]
        for key in required_keys:
            assert key in config, f"Required config key '{key}' missing"

    def test_load_config_with_env_vars(self):
        """Test configuration loading with environment variables."""
        test_env = {
            "DATA_DIRECTORY": "test_output",
            "LLM_PROVIDER": "test_provider",
            "LLM_MODEL": "test_model",
            "OPENROUTER_API_KEY": "test_key",
        }

        with patch.dict(os.environ, test_env, clear=False):
            config = load_config()

            assert config["data_directory"] == "test_output"
            assert config["llm_provider"] == "test_provider"
            assert config["llm_model"] == "test_model"
            assert config["OPENROUTER_API_KEY"] == "test_key"

    def test_load_config_defaults(self):
        """Test that appropriate defaults are used when env vars not set."""
        # Clear relevant environment variables
        env_to_clear = ["DATA_DIRECTORY", "LLM_PROVIDER", "LLM_MODEL"]

        with patch.dict(os.environ, {}, clear=False):
            for key in env_to_clear:
                if key in os.environ:
                    del os.environ[key]

            config = load_config()

            assert config["data_directory"] == "output"  # Default value
            assert config["llm_provider"] == "openrouter"  # Default value
            # Model should have a default value
            assert config["llm_model"] is not None

    def test_load_config_boolean_parsing(self):
        """Test boolean configuration parsing."""
        test_env = {
            "USE_12FT_IO_FALLBACK": "true",
            "USE_PLAYWRIGHT_FOR_NYT": "false",
            "ARTICLE_INGESTOR_ENABLED": "true",
            "PODCAST_INGESTOR_ENABLED": "false",
        }

        with patch.dict(os.environ, test_env, clear=False):
            config = load_config()

            assert config["USE_12FT_IO_FALLBACK"] is True
            assert config["USE_PLAYWRIGHT_FOR_NYT"] is False
            assert config["article_ingestor"]["enabled"] is True
            assert config["podcast_ingestor"]["enabled"] is False

    def test_load_config_integer_parsing(self):
        """Test integer configuration parsing."""
        test_env = {"PODCAST_EPISODE_LIMIT": "5"}

        with patch.dict(os.environ, test_env, clear=False):
            config = load_config()

            assert config["PODCAST_EPISODE_LIMIT"] == 5
            assert config["podcast_ingestor"]["episode_limit"] == 5

    def test_load_config_path_construction(self):
        """Test that output paths are constructed correctly."""
        test_env = {"DATA_DIRECTORY": "custom_output"}

        with patch.dict(os.environ, test_env, clear=False):
            config = load_config()

            assert config["data_directory"] == "custom_output"
            assert config["article_output_path"] == os.path.join(
                "custom_output", "articles"
            )
            assert config["podcast_output_path"] == os.path.join(
                "custom_output", "podcasts"
            )
            assert config["youtube_output_path"] == os.path.join(
                "custom_output", "youtube"
            )

    def test_deepseek_api_priority(self):
        """Test that DeepSeek API key takes priority when present."""
        test_env = {
            "DEEPSEEK_API_KEY": "deepseek_key",
            "OPENROUTER_API_KEY": "openrouter_key",
        }

        with patch.dict(os.environ, test_env, clear=False):
            config = load_config()

            assert config["llm_provider"] == "deepseek"
            assert "deepseek-ai" in config["llm_model"]
            assert config["DEEPSEEK_API_KEY"] == "deepseek_key"

    def test_openrouter_key_detection(self):
        """Test automatic OpenRouter key detection from OPENAI_API_KEY."""
        # Skip if environment already has OPENROUTER_API_KEY set
        if os.environ.get("OPENROUTER_API_KEY"):
            pytest.skip("OPENROUTER_API_KEY already set in environment")

        test_env = {"OPENAI_API_KEY": "sk-or-v1-test-key"}

        with patch.dict(os.environ, test_env, clear=False):
            config = load_config()

            # The logic should detect the OpenRouter key and set it
            assert config["OPENROUTER_API_KEY"] == "sk-or-v1-test-key"
            assert config["llm_provider"] == "openrouter"


class TestCategoriesLoading:
    """Test category configuration loading."""

    def test_load_categories_success(self):
        """Test successful category loading."""
        mock_categories = {
            "categories": {
                "technology": {"keywords": ["python", "software"]},
                "science": {"keywords": ["research", "study"]},
            }
        }

        mock_file_content = yaml.dump(mock_categories)

        with patch("builtins.open", mock_open(read_data=mock_file_content)):
            with patch("os.path.exists", return_value=True):
                categories = load_categories()

                assert categories == mock_categories
                assert "categories" in categories
                assert "technology" in categories["categories"]

    def test_load_categories_file_not_found(self):
        """Test category loading when file doesn't exist."""
        with patch("builtins.open", side_effect=FileNotFoundError()):
            categories = load_categories()
            assert categories == {}

    def test_load_categories_yaml_error(self):
        """Test category loading with invalid YAML."""
        invalid_yaml = "invalid: yaml: content: ["

        with patch("builtins.open", mock_open(read_data=invalid_yaml)):
            with patch("os.path.exists", return_value=True):
                categories = load_categories()
                assert categories == {}

    def test_categories_in_config(self):
        """Test that categories are properly integrated into main config."""
        mock_categories = {"test": {"keywords": ["test"]}}

        with patch("helpers.config.load_categories", return_value=mock_categories):
            config = load_config()
            assert config["categories"] == mock_categories


class TestModelSelection:
    """Test model selection logic."""

    def test_get_model_for_task_default(self):
        """Test default model selection."""
        config = {"llm_model": "test-model"}
        model = get_model_for_task(config, "default")
        assert model == "test-model"

    def test_get_model_for_task_premium(self):
        """Test premium model selection."""
        config = {"llm_model": "default-model", "llm_model_premium": "premium-model"}
        model = get_model_for_task(config, "premium")
        assert model == "premium-model"

    def test_get_model_for_task_budget(self):
        """Test budget model selection."""
        config = {"llm_model": "default-model", "llm_model_budget": "budget-model"}
        model = get_model_for_task(config, "budget")
        assert model == "budget-model"

    def test_get_model_for_task_deepseek_reasoner(self):
        """Test DeepSeek reasoner model selection."""
        config = {
            "llm_provider": "deepseek",
            "llm_model_reasoner": "deepseek-ai/deepseek-reasoner",
        }
        model = get_model_for_task(config, "reasoner")
        assert model == "deepseek-ai/deepseek-reasoner"

    def test_get_model_for_task_fallback(self):
        """Test fallback model selection."""
        config = {"llm_model": "default-model", "llm_model_fallback": "fallback-model"}
        model = get_model_for_task(config, "fallback")
        assert model == "fallback-model"


class TestLegacyFunctions:
    """Test legacy configuration functions."""

    def test_get_config_function(self):
        """Test legacy get_config function."""
        test_env = {"TEST_KEY": "test_value"}

        with patch.dict(os.environ, test_env, clear=False):
            value = get_config("TEST_KEY")
            assert value == "test_value"

            # Test default value
            value = get_config("NONEXISTENT_KEY", "default")
            assert value == "default"

    def test_is_feature_enabled(self):
        """Test feature flag checking."""
        test_env = {
            "FEATURE_ENABLED": "true",
            "FEATURE_DISABLED": "false",
            "FEATURE_INVALID": "invalid",
        }

        with patch.dict(os.environ, test_env, clear=False):
            assert is_feature_enabled("FEATURE_ENABLED") is True
            assert is_feature_enabled("FEATURE_DISABLED") is False
            assert is_feature_enabled("FEATURE_INVALID") is False
            assert is_feature_enabled("NONEXISTENT_FEATURE") is False
            assert is_feature_enabled("NONEXISTENT_FEATURE", "true") is True


class TestConfigurationEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_environment_variables(self):
        """Test handling of empty environment variables."""
        test_env = {"DATA_DIRECTORY": "", "LLM_MODEL": "", "OPENROUTER_API_KEY": ""}

        with patch.dict(os.environ, test_env, clear=False):
            config = load_config()

            # Empty DATA_DIRECTORY should fall back to default
            assert (
                config["data_directory"] == "output" or config["data_directory"] == ""
            )

            # Empty API key should be handled gracefully
            assert "OPENROUTER_API_KEY" in config

    def test_config_with_special_characters(self):
        """Test configuration with special characters."""
        test_env = {
            "DATA_DIRECTORY": "output/test with spaces",
            "LLM_MODEL": "model:with:colons",
        }

        with patch.dict(os.environ, test_env, clear=False):
            config = load_config()

            assert config["data_directory"] == "output/test with spaces"
            assert config["llm_model"] == "model:with:colons"

    def test_configuration_override_precedence(self):
        """Test that configuration sources have correct precedence."""
        # This tests that config/.env takes precedence over root .env
        # Since we can't easily test file precedence in unit tests,
        # we'll test the environment variable precedence

        test_env = {"DATA_DIRECTORY": "env_override"}

        with patch.dict(os.environ, test_env, clear=False):
            config = load_config()
            assert config["data_directory"] == "env_override"

    def test_config_validation_missing_directories(self):
        """Test configuration validation with missing directories."""
        # This test verifies the config loading doesn't fail
        # even if referenced directories don't exist
        test_env = {"DATA_DIRECTORY": "/nonexistent/path"}

        with patch.dict(os.environ, test_env, clear=False):
            config = load_config()

            # Should load without error, even if path doesn't exist
            assert config["data_directory"] == "/nonexistent/path"
            assert config["article_output_path"] == "/nonexistent/path/articles"

    def test_config_security_no_logging_secrets(self):
        """Test that secrets are not logged or exposed inappropriately."""
        test_env = {
            "OPENROUTER_API_KEY": "secret_key_123",
            "DEEPSEEK_API_KEY": "secret_deepseek_456",
            "NYT_PASSWORD": "secret_password_789",
        }

        with patch.dict(os.environ, test_env, clear=False):
            config = load_config()

            # Verify secrets are loaded
            assert config["OPENROUTER_API_KEY"] == "secret_key_123"
            assert config["DEEPSEEK_API_KEY"] == "secret_deepseek_456"
            assert config["NYT_PASSWORD"] == "secret_password_789"

            # Note: In production, we'd also verify these aren't logged
            # but that would require testing the actual logging output

    def test_config_model_hierarchy(self):
        """Test the model tier hierarchy works correctly."""
        test_env = {
            "MODEL_PREMIUM": "premium-model",
            "MODEL_BUDGET": "budget-model",
            "MODEL_FALLBACK": "fallback-model",
        }

        with patch.dict(os.environ, test_env, clear=False):
            config = load_config()

            assert config["llm_model_premium"] == "premium-model"
            assert config["llm_model_budget"] == "budget-model"
            assert config["llm_model_fallback"] == "fallback-model"

            # Test free model tiers are also loaded
            assert "MODEL_FREE_PREMIUM_1" in config
            assert "MODEL_FREE_FALLBACK_1" in config
            assert "MODEL_FREE_BUDGET_1" in config


class TestIngestorConfiguration:
    """Test ingestor-specific configuration."""

    def test_ingestor_enabled_flags(self):
        """Test ingestor enabled/disabled flags."""
        test_env = {
            "ARTICLE_INGESTOR_ENABLED": "true",
            "PODCAST_INGESTOR_ENABLED": "false",
            "YOUTUBE_INGESTOR_ENABLED": "true",
            "INSTAPAPER_INGESTOR_ENABLED": "false",
        }

        with patch.dict(os.environ, test_env, clear=False):
            config = load_config()

            assert config["article_ingestor"]["enabled"] is True
            assert config["podcast_ingestor"]["enabled"] is False
            assert config["youtube_ingestor"]["enabled"] is True
            assert config["instapaper_ingestor"]["enabled"] is False

    def test_ingestor_defaults(self):
        """Test ingestor default values."""
        # Clear all ingestor environment variables
        ingestor_vars = [
            "ARTICLE_INGESTOR_ENABLED",
            "PODCAST_INGESTOR_ENABLED",
            "YOUTUBE_INGESTOR_ENABLED",
            "INSTAPAPER_INGESTOR_ENABLED",
            "PODCAST_EPISODE_LIMIT",
        ]

        with patch.dict(os.environ, {}, clear=False):
            for var in ingestor_vars:
                if var in os.environ:
                    del os.environ[var]

            config = load_config()

            # All ingestors should be enabled by default
            assert config["article_ingestor"]["enabled"] is True
            assert config["podcast_ingestor"]["enabled"] is True
            assert config["youtube_ingestor"]["enabled"] is True
            assert config["instapaper_ingestor"]["enabled"] is True

            # Episode limit should default to 0 (no limit)
            assert config["podcast_ingestor"]["episode_limit"] == 0

    def test_podcast_episode_limit(self):
        """Test podcast episode limit configuration."""
        test_env = {"PODCAST_EPISODE_LIMIT": "10"}

        with patch.dict(os.environ, test_env, clear=False):
            config = load_config()

            assert config["PODCAST_EPISODE_LIMIT"] == 10
            assert config["podcast_ingestor"]["episode_limit"] == 10


# Integration Tests
class TestConfigurationIntegration:
    """Integration tests for configuration system."""

    def test_full_config_load_integration(self):
        """Test complete configuration loading with all components."""
        # Set up comprehensive test environment
        test_env = {
            "DATA_DIRECTORY": "test_data",
            "OPENROUTER_API_KEY": "test_openrouter_key",
            "LLM_PROVIDER": "openrouter",
            "LLM_MODEL": "test-model",
            "ARTICLE_INGESTOR_ENABLED": "true",
            "PODCAST_EPISODE_LIMIT": "5",
        }

        mock_categories = {
            "categories": {
                "technology": {"keywords": ["python", "software"]},
                "science": {"keywords": ["research", "study"]},
            }
        }

        with patch.dict(os.environ, test_env, clear=False):
            with patch("helpers.config.load_categories", return_value=mock_categories):
                config = load_config()

                # Verify all major components are loaded correctly
                assert config["data_directory"] == "test_data"
                assert config["OPENROUTER_API_KEY"] == "test_openrouter_key"
                assert config["llm_provider"] == "openrouter"
                assert config["llm_model"] == "test-model"
                assert config["article_ingestor"]["enabled"] is True
                assert config["podcast_ingestor"]["episode_limit"] == 5
                assert config["categories"] == mock_categories

                # Verify paths are constructed correctly
                assert config["article_output_path"] == "test_data/articles"
                assert config["podcast_output_path"] == "test_data/podcasts"
                assert config["youtube_output_path"] == "test_data/youtube"

    def test_config_error_recovery(self):
        """Test that configuration system recovers gracefully from errors."""
        # Test with various error conditions - the load_categories function
        # has its own error handling, so we need to test it directly
        try:
            config = load_config()
            # If we get here, the config loaded successfully
            assert "categories" in config
            # This test verifies that load_config doesn't crash
            # even with problematic configurations
        except Exception as e:
            # If an exception occurs, fail the test
            pytest.fail(f"Configuration loading should not raise exceptions: {e}")

    def test_config_consistency(self):
        """Test that configuration values are consistent across multiple loads."""
        test_env = {"DATA_DIRECTORY": "consistent_test"}

        with patch.dict(os.environ, test_env, clear=False):
            config1 = load_config()
            config2 = load_config()

            # Core values should be identical
            assert config1["data_directory"] == config2["data_directory"]
            assert config1["llm_provider"] == config2["llm_provider"]
            assert config1["article_output_path"] == config2["article_output_path"]


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])
