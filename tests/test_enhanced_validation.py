"""
Test suite for enhanced configuration validation with specific error guidance.

This module tests the new ConfigValidator class and its detailed error reporting
capabilities, ensuring users get actionable guidance for configuration issues.
"""

import tempfile
from unittest.mock import patch

import pytest

from helpers.validate import (ConfigValidator, ValidationError,
                              print_validation_report,
                              validate_config_enhanced)


class TestConfigValidator:
    """Test the enhanced ConfigValidator class."""

    def setup_method(self):
        """Set up test instance."""
        self.validator = ConfigValidator()

    def test_empty_config_errors(self):
        """Test validation of completely empty configuration."""
        config = {}
        errors, warnings = self.validator.validate_config(config)

        # Should have errors for missing LLM provider
        assert len(errors) > 0
        assert any("llm_provider" in error.field for error in errors)

        # Check that errors have proper structure
        for error in errors:
            assert isinstance(error, ValidationError)
            assert error.field
            assert error.message
            assert error.severity
            assert error.guidance

    def test_valid_openrouter_config(self):
        """Test validation of valid OpenRouter configuration."""
        config = {
            "llm_provider": "openrouter",
            "llm_model": "mistralai/mistral-7b-instruct",
            "OPENROUTER_API_KEY": "sk-or-v1-valid-key-12345678901234567890",
            "data_directory": "output",
            "article_ingestor": {"enabled": True},
            "podcast_ingestor": {"enabled": True},
            "youtube_ingestor": {"enabled": False},
            "instapaper_ingestor": {"enabled": False},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            config["data_directory"] = temp_dir
            errors, warnings = self.validator.validate_config(config)

            # Should have no errors for valid config
            assert len(errors) == 0

    def test_invalid_llm_provider(self):
        """Test validation of invalid LLM provider."""
        config = {"llm_provider": "invalid_provider", "llm_model": "some-model"}

        errors, warnings = self.validator.validate_config(config)

        # Should have error for invalid provider
        provider_errors = [e for e in errors if e.field == "llm_provider"]
        assert len(provider_errors) == 1

        error = provider_errors[0]
        assert "invalid_provider" in error.message
        assert "Valid providers are:" in error.guidance
        assert error.fix_command is not None
        assert "sed -i" in error.fix_command

    def test_missing_openrouter_key(self):
        """Test validation when OpenRouter key is missing."""
        config = {
            "llm_provider": "openrouter",
            "llm_model": "mistralai/mistral-7b-instruct",
        }

        errors, warnings = self.validator.validate_config(config)

        # Should have error for missing API key
        key_errors = [e for e in errors if e.field == "OPENROUTER_API_KEY"]
        assert len(key_errors) == 1

        error = key_errors[0]
        assert "required but not configured" in error.message
        assert "https://openrouter.ai/keys" in error.guidance
        assert error.documentation_url == "https://openrouter.ai/docs/quick-start"

    def test_invalid_openrouter_key_format(self):
        """Test validation of invalid OpenRouter key format."""
        config = {
            "llm_provider": "openrouter",
            "llm_model": "mistralai/mistral-7b-instruct",
            "OPENROUTER_API_KEY": "invalid-key-format",
        }

        errors, warnings = self.validator.validate_config(config)

        # Should have error for invalid key format
        key_errors = [e for e in errors if e.field == "OPENROUTER_API_KEY"]
        assert len(key_errors) == 1

        error = key_errors[0]
        assert "format appears invalid" in error.message
        assert "sk-or-v1-" in error.guidance

    def test_deepseek_configuration(self):
        """Test DeepSeek provider configuration validation."""
        config = {
            "llm_provider": "deepseek",
            "llm_model": "deepseek-ai/deepseek-chat",
            "DEEPSEEK_API_KEY": "valid-deepseek-key",
        }

        errors, warnings = self.validator.validate_config(config)

        # Should have no errors for valid DeepSeek config
        deepseek_errors = [e for e in errors if "DEEPSEEK" in e.field]
        assert len(deepseek_errors) == 0

    def test_missing_deepseek_key(self):
        """Test validation when DeepSeek key is missing."""
        config = {"llm_provider": "deepseek", "llm_model": "deepseek-ai/deepseek-chat"}

        errors, warnings = self.validator.validate_config(config)

        # Should have error for missing API key
        key_errors = [e for e in errors if e.field == "DEEPSEEK_API_KEY"]
        assert len(key_errors) == 1

        error = key_errors[0]
        assert "required but not configured" in error.message
        assert "platform.deepseek.com" in error.guidance

    def test_youtube_ingestor_validation(self):
        """Test YouTube ingestor configuration validation."""
        config = {
            "llm_provider": "openrouter",
            "OPENROUTER_API_KEY": "sk-or-v1-valid-key-12345678901234567890",
            "youtube_ingestor": {"enabled": True},
        }

        errors, warnings = self.validator.validate_config(config)

        # Should have error for missing YouTube API key
        youtube_errors = [e for e in errors if e.field == "YOUTUBE_API_KEY"]
        assert len(youtube_errors) == 1

        error = youtube_errors[0]
        assert "YouTube API key is required" in error.message
        assert "console.cloud.google.com" in error.guidance
        assert "YOUTUBE_INGESTOR_ENABLED=false" in error.guidance

    def test_instapaper_credentials_validation(self):
        """Test Instapaper credentials validation."""
        config = {
            "llm_provider": "openrouter",
            "OPENROUTER_API_KEY": "sk-or-v1-valid-key-12345678901234567890",
            "instapaper_ingestor": {"enabled": True},
            "INSTAPAPER_LOGIN": "user@example.com",
            # Missing INSTAPAPER_PASSWORD
        }

        errors, warnings = self.validator.validate_config(config)

        # Should have error for incomplete credentials
        instapaper_errors = [e for e in errors if e.field == "INSTAPAPER_CREDENTIALS"]
        assert len(instapaper_errors) == 1

        error = instapaper_errors[0]
        assert "incomplete" in error.message
        assert "INSTAPAPER_LOGIN and INSTAPAPER_PASSWORD" in error.guidance

    def test_nyt_credentials_validation(self):
        """Test NYT credentials validation."""
        config = {
            "llm_provider": "openrouter",
            "OPENROUTER_API_KEY": "sk-or-v1-valid-key-12345678901234567890",
            "USE_PLAYWRIGHT_FOR_NYT": True,
            "NYT_USERNAME": "user@example.com",
            # Missing NYT_PASSWORD
        }

        errors, warnings = self.validator.validate_config(config)

        # Should have error for incomplete credentials
        nyt_errors = [e for e in errors if e.field == "NYT_CREDENTIALS"]
        assert len(nyt_errors) == 1

        error = nyt_errors[0]
        assert "NYT credentials are required" in error.message
        assert "NYT_USERNAME and NYT_PASSWORD" in error.guidance

    def test_data_directory_validation(self):
        """Test data directory accessibility validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test with valid directory
            config = {
                "llm_provider": "openrouter",
                "OPENROUTER_API_KEY": "sk-or-v1-valid-key-12345678901234567890",
                "data_directory": temp_dir,
            }

            errors, warnings = self.validator.validate_config(config)

            # Should have no errors for accessible directory
            dir_errors = [e for e in errors if e.field == "data_directory"]
            assert len(dir_errors) == 0

    def test_data_directory_permission_error(self):
        """Test data directory permission error handling."""
        config = {
            "llm_provider": "openrouter",
            "OPENROUTER_API_KEY": "sk-or-v1-valid-key-12345678901234567890",
            "data_directory": "/root/forbidden",  # Directory that should not be writable
        }

        with patch(
            "pathlib.Path.mkdir", side_effect=PermissionError("Permission denied")
        ):
            errors, warnings = self.validator.validate_config(config)

            # Should have error for inaccessible directory
            dir_errors = [e for e in errors if e.field == "data_directory"]
            assert len(dir_errors) == 1

            error = dir_errors[0]
            assert "not writable" in error.message
            assert "mkdir -p" in error.fix_command

    def test_high_podcast_limit_warning(self):
        """Test warning for high podcast episode limit."""
        config = {
            "llm_provider": "openrouter",
            "OPENROUTER_API_KEY": "sk-or-v1-valid-key-12345678901234567890",
            "PODCAST_EPISODE_LIMIT": 200,
        }

        errors, warnings = self.validator.validate_config(config)

        # Should have warning for high episode limit
        limit_warnings = [w for w in warnings if w.field == "PODCAST_EPISODE_LIMIT"]
        assert len(limit_warnings) == 1

        warning = limit_warnings[0]
        assert "may impact performance" in warning.message
        assert "Consider a lower limit" in warning.guidance

    def test_privacy_warning_12ft_io(self):
        """Test privacy warning for 12ft.io usage."""
        config = {
            "llm_provider": "openrouter",
            "OPENROUTER_API_KEY": "sk-or-v1-valid-key-12345678901234567890",
            "USE_12FT_IO_FALLBACK": True,
        }

        errors, warnings = self.validator.validate_config(config)

        # Should have warning for privacy concern
        privacy_warnings = [w for w in warnings if w.field == "USE_12FT_IO_FALLBACK"]
        assert len(privacy_warnings) == 1

        warning = privacy_warnings[0]
        assert "privacy concern" in warning.message
        assert "third-party service" in warning.guidance

    def test_placeholder_credential_detection(self):
        """Test detection of placeholder credentials."""
        config = {
            "llm_provider": "openrouter",
            "OPENROUTER_API_KEY": "your_key_here",
            "YOUTUBE_API_KEY": "test_youtube_key",
        }

        errors, warnings = self.validator.validate_config(config)

        # Should have warnings for placeholder values
        placeholder_warnings = [
            w for w in warnings if "placeholder" in w.message.lower()
        ]
        assert len(placeholder_warnings) >= 1

        # Check that at least one warning mentions updating with real credential
        guidance_texts = [w.guidance for w in placeholder_warnings]
        assert any("real credential" in guidance.lower() for guidance in guidance_texts)

    def test_expensive_model_warning(self):
        """Test warning for expensive model configuration."""
        config = {
            "llm_provider": "openrouter",
            "OPENROUTER_API_KEY": "sk-or-v1-valid-key-12345678901234567890",
            "llm_model": "anthropic/claude-3-opus",
            # No budget model configured
        }

        errors, warnings = self.validator.validate_config(config)

        # Should have warnings about expensive configuration
        cost_warnings = [
            w
            for w in warnings
            if "expensive" in w.message.lower() or "cost" in w.message.lower()
        ]
        assert len(cost_warnings) >= 1

    def test_model_budget_suggestion(self):
        """Test suggestion to configure budget model."""
        config = {
            "llm_provider": "openrouter",
            "OPENROUTER_API_KEY": "sk-or-v1-valid-key-12345678901234567890",
            "llm_model": "anthropic/claude-3-sonnet",
            # No budget model
        }

        errors, warnings = self.validator.validate_config(config)

        # Should have warning about missing budget model
        budget_warnings = [w for w in warnings if w.field == "llm_model_budget"]
        assert len(budget_warnings) == 1

        warning = budget_warnings[0]
        assert "budget model" in warning.message
        assert "reduce costs" in warning.guidance

    def test_deepseek_reasoner_validation(self):
        """Test DeepSeek reasoner model validation."""
        config = {
            "llm_provider": "deepseek",
            "DEEPSEEK_API_KEY": "valid-key",
            "llm_model_reasoner": "deepseek-ai/deepseek-chat",  # Not a reasoner model
        }

        errors, warnings = self.validator.validate_config(config)

        # Should have warning about non-reasoner model
        reasoner_warnings = [w for w in warnings if w.field == "llm_model_reasoner"]
        assert len(reasoner_warnings) == 1

        warning = reasoner_warnings[0]
        assert "may not be a reasoning model" in warning.message
        assert "deepseek-reasoner" in warning.guidance


class TestValidationErrorStructure:
    """Test ValidationError data structure."""

    def test_validation_error_creation(self):
        """Test ValidationError object creation."""
        error = ValidationError(
            field="test_field",
            message="Test message",
            severity="error",
            guidance="Test guidance",
            fix_command="echo 'test'",
            documentation_url="https://example.com",
        )

        assert error.field == "test_field"
        assert error.message == "Test message"
        assert error.severity == "error"
        assert error.guidance == "Test guidance"
        assert error.fix_command == "echo 'test'"
        assert error.documentation_url == "https://example.com"

    def test_validation_error_optional_fields(self):
        """Test ValidationError with optional fields."""
        error = ValidationError(
            field="test_field",
            message="Test message",
            severity="warning",
            guidance="Test guidance",
        )

        assert error.fix_command is None
        assert error.documentation_url is None


class TestValidationReporting:
    """Test validation report formatting."""

    def test_format_validation_report_no_issues(self):
        """Test report formatting when no issues found."""
        validator = ConfigValidator()
        report = validator.format_validation_report([], [])

        assert "✅ Configuration validation passed" in report
        assert "no issues found" in report

    def test_format_validation_report_with_errors(self):
        """Test report formatting with errors."""
        validator = ConfigValidator()
        errors = [
            ValidationError(
                field="test_field",
                message="Test error",
                severity="error",
                guidance="Fix this issue",
                fix_command="echo 'fix'",
            )
        ]

        report = validator.format_validation_report(errors, [])

        assert "❌ ERRORS" in report
        assert "test_field" in report
        assert "Test error" in report
        assert "Fix this issue" in report
        assert "echo 'fix'" in report

    def test_format_validation_report_with_warnings(self):
        """Test report formatting with warnings."""
        validator = ConfigValidator()
        warnings = [
            ValidationError(
                field="test_field",
                message="Test warning",
                severity="warning",
                guidance="Consider this improvement",
            )
        ]

        report = validator.format_validation_report([], warnings)

        assert "⚠️  WARNINGS" in report
        assert "test_field" in report
        assert "Test warning" in report
        assert "Consider this improvement" in report


class TestValidationFunctions:
    """Test validation utility functions."""

    def test_validate_config_enhanced(self):
        """Test enhanced validation function."""
        config = {"llm_provider": "invalid"}

        errors, warnings = validate_config_enhanced(config)

        assert isinstance(errors, list)
        assert isinstance(warnings, list)
        assert len(errors) > 0
        assert all(isinstance(error, ValidationError) for error in errors)

    def test_print_validation_report(self, capsys):
        """Test print validation report function."""
        config = {}  # Empty config will have errors

        result = print_validation_report(config)
        captured = capsys.readouterr()

        assert result is False  # Should return False for invalid config
        assert "Configuration Validation Report" in captured.out
        assert "ERRORS" in captured.out


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
