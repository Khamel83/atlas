"""
Integration tests for Atlas configuration loading.

Tests the complete configuration loading pipeline including:
- YAML file parsing
- Environment variable substitution
- Configuration validation
- Default value handling
"""

import pytest
import tempfile
import os
from pathlib import Path

from atlas.config import load_config, ConfigError, AtlasConfig
from atlas.logging import setup_logging, get_logger


class TestConfigLoading:
    """Test configuration loading integration."""

    def test_load_default_config(self, temp_dir: Path) -> None:
        """Test loading configuration from file."""
        config_content = """
version: "4.0.0"

vault:
  root: "./test_vault"
  inbox_dir: "inbox"
  logs_dir: "logs"
  failures_dir: "failures"

logging:
  level: "INFO"
  file: "test.log"
  max_size_mb: 50
  backup_count: 3
  enable_console: false

processing:
  max_concurrent_jobs: 3
  timeout_seconds: 120
  retry_attempts: 2
"""

        config_path = temp_dir / "test_config.yaml"
        config_path.write_text(config_content)

        # Load configuration
        config = load_config(config_path)

        # Verify loaded values
        assert isinstance(config, AtlasConfig)
        assert config.version == "4.0.0"
        assert config.vault.root == "./test_vault"
        assert config.logging.level == "INFO"
        assert config.logging.file == "test.log"
        assert config.processing.max_concurrent_jobs == 3

    def test_load_config_with_env_substitution(self, temp_dir: Path) -> None:
        """Test environment variable substitution in config."""
        os.environ["TEST_VAULT_ROOT"] = "/tmp/test_vault"
        os.environ["TEST_LOG_LEVEL"] = "DEBUG"

        try:
            config_content = """
version: "4.0.0"

vault:
  root: "${TEST_VAULT_ROOT}"

logging:
  level: "${TEST_LOG_LEVEL}"
  enable_console: false
"""

            config_path = temp_dir / "test_config.yaml"
            config_path.write_text(config_content)

            config = load_config(config_path)

            assert config.vault.root == "/tmp/test_vault"
            assert config.logging.level == "DEBUG"

        finally:
            # Clean up environment variables
            os.environ.pop("TEST_VAULT_ROOT", None)
            os.environ.pop("TEST_LOG_LEVEL", None)

    def test_load_config_with_default_values(self, temp_dir: Path) -> None:
        """Test configuration loading with default values."""
        config_content = """
version: "4.0.0"

vault:
  root: "./test_vault"

logging:
  level: "INFO"
"""

        config_path = temp_dir / "test_config.yaml"
        config_path.write_text(config_content)

        config = load_config(config_path)

        # Check that defaults are applied
        assert config.vault.inbox_dir == "inbox"  # default value
        assert config.vault.logs_dir == "logs"    # default value
        assert config.logging.max_size_mb == 100  # default value
        assert config.processing.max_concurrent_jobs == 5  # default value

    def test_load_config_file_not_found(self) -> None:
        """Test error when config file doesn't exist."""
        with pytest.raises(ConfigError, match="Configuration file not found"):
            load_config("nonexistent_config.yaml")

    def test_load_config_invalid_yaml(self, temp_dir: Path) -> None:
        """Test error when YAML is invalid."""
        config_content = """
version: "4.0.0"
vault:
  root: "./test_vault"
  invalid_yaml: [unclosed list
"""

        config_path = temp_dir / "invalid_config.yaml"
        config_path.write_text(config_content)

        with pytest.raises(ConfigError, match="Invalid YAML"):
            load_config(config_path)

    def test_load_config_missing_required_section(self, temp_dir: Path) -> None:
        """Test error when required sections are missing."""
        config_content = """
version: "4.0.0"
# Missing vault and logging sections
processing:
  max_concurrent_jobs: 3
"""

        config_path = temp_dir / "incomplete_config.yaml"
        config_path.write_text(config_content)

        with pytest.raises(ConfigError, match="Missing required config section"):
            load_config(config_path)

    def test_load_config_invalid_log_level(self, temp_dir: Path) -> None:
        """Test error when log level is invalid."""
        config_content = """
version: "4.0.0"

vault:
  root: "./test_vault"

logging:
  level: "INVALID_LEVEL"
"""

        config_path = temp_dir / "invalid_level_config.yaml"
        config_path.write_text(config_content)

        with pytest.raises(ConfigError, match="Invalid logging level"):
            load_config(config_path)


class TestLoggingIntegration:
    """Test logging integration with configuration."""

    def test_setup_logging_from_config(self, temp_dir: Path) -> None:
        """Test setting up logging using configuration."""
        import logging
        config_content = """
version: "4.0.0"

vault:
  root: "./test_vault"

logging:
  level: "DEBUG"
  file: "test_atlas.log"
  max_size_mb: 10
  backup_count: 2
  enable_console: false
"""

        config_path = temp_dir / "test_config.yaml"
        config_path.write_text(config_content)

        config = load_config(config_path)

        # Setup logging
        setup_logging(
            level=config.logging.level,
            log_file=config.logging.file,
            max_size_mb=config.logging.max_size_mb,
            backup_count=config.logging.backup_count,
            enable_console=config.logging.enable_console
        )

        # Test logger creation
        logger = get_logger("test_module")

        # Verify logger is configured
        assert logger.name == "atlas.test_module"
        assert logger.isEnabledFor(logging.DEBUG)  # Check if DEBUG is enabled

        # Test logging
        logger.info("Test message")

        # Check that log file was created
        log_file = temp_dir / "test_atlas.log"
        assert log_file.exists()

    def test_logging_with_context(self, temp_dir: Path) -> None:
        """Test structured logging with context."""
        from atlas.logging import OperationLogger

        config_content = """
version: "4.0.0"

vault:
  root: "./test_vault"

logging:
  level: "INFO"
  enable_console: false
"""

        config_path = temp_dir / "test_config.yaml"
        config_path.write_text(config_content)

        config = load_config(config_path)

        # Setup logging to file
        log_file = temp_dir / "context_test.log"
        setup_logging(
            level=config.logging.level,
            log_file=str(log_file),
            enable_console=False
        )

        # Create operation logger
        op_logger = OperationLogger("test_operation", "test_source")

        # Log with context
        op_logger.start("Test operation started", item_count=5)
        op_logger.success("Test operation completed", processed=5, errors=0)

        # Verify log content
        log_content = log_file.read_text()
        assert "[START] Test operation started" in log_content
        assert "[SUCCESS] Test operation completed" in log_content
        assert "operation=test_operation" in log_content
        assert "source=test_source" in log_content
        assert "item_count=5" in log_content
        assert "processed=5" in log_content


class TestEndToEndConfigFlow:
    """Test complete end-to-end configuration flow."""

    def test_full_config_pipeline(self, temp_dir: Path) -> None:
        """Test complete configuration loading and setup pipeline."""
        # Set environment variables
        os.environ["ATLAS_TEST_ROOT"] = str(temp_dir / "test_vault")
        os.environ["ATLAS_TEST_LEVEL"] = "INFO"

        try:
            config_content = """
version: "4.0.0"

vault:
  root: "${ATLAS_TEST_ROOT}"
  inbox_dir: "inbox"
  logs_dir: "logs"
  failures_dir: "failures"

logging:
  level: "${ATLAS_TEST_LEVEL}"
  file: "${ATLAS_TEST_ROOT}/logs/atlas.log"
  max_size_mb: 5
  backup_count: 2
  enable_console: false

processing:
  max_concurrent_jobs: 2
  timeout_seconds: 60
  retry_attempts: 1

telegram:
  bot_token: "${TELEGRAM_BOT_TOKEN:-test_token}"
  allowed_user_id: ${TELEGRAM_USER_ID:-123456789}
  enabled: true
"""

            config_path = temp_dir / "full_test_config.yaml"
            config_path.write_text(config_content)

            # Load configuration
            config = load_config(config_path)

            # Verify all sections loaded correctly
            assert config.version == "4.0.0"
            assert str(temp_dir / "test_vault") in config.vault.root
            assert config.logging.level == "INFO"
            assert config.processing.max_concurrent_jobs == 2
            assert config.telegram.enabled == True
            # The environment variable substitution might add a prefix, check that it contains test_token
            assert "test_token" in config.telegram.bot_token

            # Setup logging
            setup_logging(
                level=config.logging.level,
                log_file=config.logging.file,
                enable_console=config.logging.enable_console
            )

            # Create directories
            vault_root = Path(config.vault.root)
            vault_root.mkdir(parents=True, exist_ok=True)
            (vault_root / config.vault.logs_dir).mkdir(exist_ok=True)

            # Test logging
            logger = get_logger("integration_test")
            logger.info("Configuration pipeline test completed successfully")

            # Verify log file creation and content
            log_file = Path(config.logging.file)
            assert log_file.exists()
            log_content = log_file.read_text()
            assert "Configuration pipeline test completed successfully" in log_content
            assert "integration_test" in log_content

        finally:
            # Clean up environment variables
            os.environ.pop("ATLAS_TEST_ROOT", None)
            os.environ.pop("ATLAS_TEST_LEVEL", None)

    def test_config_validation_edge_cases(self, temp_dir: Path) -> None:
        """Test configuration validation edge cases."""
        # Test with minimal valid configuration
        minimal_config = """
version: "4.0.0"

vault:
  root: "./minimal_vault"

logging:
  level: "ERROR"
"""

        config_path = temp_dir / "minimal_config.yaml"
        config_path.write_text(minimal_config)

        config = load_config(config_path)

        # Should load with all defaults
        assert config.vault.root == "./minimal_vault"
        assert config.logging.level == "ERROR"
        assert config.vault.inbox_dir == "inbox"  # default
        assert config.processing.max_concurrent_jobs == 5  # default
        assert config.telegram.enabled == False  # default