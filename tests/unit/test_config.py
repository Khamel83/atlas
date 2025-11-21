"""
Unit tests for the config module.
"""

import os
import unittest
from unittest.mock import mock_open, patch

import pytest

from helpers.config import load_categories, load_config


class TestConfig(unittest.TestCase):
    """Test cases for config module functions."""

    @pytest.mark.unit
    def test_load_categories_success(self):
        """Test successful loading of categories from YAML."""
        mock_yaml_content = """
        tier_1:
          - Technology
          - Science
        tier_2:
          - AI/ML
          - Web Development
        """

        with patch("builtins.open", mock_open(read_data=mock_yaml_content)):
            with patch("os.path.exists", return_value=True):
                categories = load_categories()

        self.assertIn("tier_1", categories)
        self.assertIn("tier_2", categories)
        self.assertEqual(categories["tier_1"], ["Technology", "Science"])

    @pytest.mark.unit
    def test_load_categories_file_not_found(self):
        """Test handling of missing categories file."""
        with patch("builtins.open", side_effect=FileNotFoundError):
            categories = load_categories()

        self.assertEqual(categories, {})

    @pytest.mark.unit
    def test_load_categories_yaml_error(self):
        """Test handling of invalid YAML content."""
        invalid_yaml = "invalid: yaml: content: ["

        with patch("builtins.open", mock_open(read_data=invalid_yaml)):
            with patch("os.path.exists", return_value=True):
                categories = load_categories()

        self.assertEqual(categories, {})

    @pytest.mark.unit
    def test_load_config_with_env_vars(self):
        """Test config loading with environment variables."""
        test_env_vars = {
            "DATA_DIRECTORY": "/test/data",
            "OPENROUTER_API_KEY": "test_key",
            "TRANSCRIBE_ENABLED": "true",
            "LOG_LEVEL": "DEBUG",
        }

        with patch.dict(os.environ, test_env_vars):
            config = load_config()

        self.assertEqual(config["data_directory"], "/test/data")
        self.assertEqual(config["openrouter_api_key"], "test_key")
        self.assertTrue(config["transcribe_enabled"])
        self.assertEqual(config["log_level"], "DEBUG")

    @pytest.mark.unit
    def test_load_config_defaults(self):
        """Test config loading with default values."""
        # Clear relevant env vars

        with patch.dict(os.environ, {}, clear=True):
            config = load_config()

        self.assertEqual(config["data_directory"], "output")
        self.assertFalse(config["transcribe_enabled"])
        self.assertEqual(config["log_level"], "INFO")

    def test_load_config_boolean_conversion(self):
        """Test proper boolean conversion from string env vars."""
        test_cases = [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("false", False),
            ("False", False),
            ("FALSE", False),
            ("", False),
            ("anything_else", False),
        ]

        for env_value, expected in test_cases:
            with patch.dict(os.environ, {"TRANSCRIBE_ENABLED": env_value}):
                config = load_config()
                self.assertEqual(
                    config["transcribe_enabled"],
                    expected,
                    f"Failed for env_value: {env_value}",
                )

    def test_load_config_path_expansion(self):
        """Test path expansion for directory configurations."""
        with patch.dict(os.environ, {"DATA_DIRECTORY": "~/test_data"}):
            config = load_config()

        # Should expand ~ to home directory
        self.assertNotIn("~", config["data_directory"])
        self.assertTrue(os.path.isabs(config["data_directory"]))


if __name__ == "__main__":
    unittest.main()
