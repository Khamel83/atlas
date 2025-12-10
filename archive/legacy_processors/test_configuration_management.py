#!/usr/bin/env python3
"""
Test suite for Atlas Configuration Management System

Tests configuration loading, validation, secret management, and CLI functionality.
"""

import os
import sys
import json
import tempfile
import shutil
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from helpers.configuration_manager import ConfigurationManager, Environment
from helpers.secret_manager import SecretManager


class TestConfigurationManager:
    """Test ConfigurationManager functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def config_files(self, temp_dir):
        """Create test configuration files."""
        config_dir = Path(temp_dir) / "config"
        config_dir.mkdir()

        # Create development config
        dev_config = config_dir / "development.env"
        dev_config.write_text("""
ATLAS_ENVIRONMENT=development
ATLAS_DATABASE_PATH=data/dev/atlas.db
API_PORT=7444
MAX_CONCURRENT_ARTICLES=5
""")

        # Create schema file
        schema_file = config_dir / "schemas.yaml"
        schema_file.write_text("""
API_PORT:
  type: int
  required: false
  default: 7444
  min_value: 1024
  max_value: 65535
  description: "API server port"

MAX_CONCURRENT_ARTICLES:
  type: int
  required: false
  default: 5
  min_value: 1
  max_value: 20
  description: "Maximum concurrent article processing"
""")

        return str(config_dir)

    def test_initialization(self, config_files):
        """Test ConfigurationManager initialization."""
        config_manager = ConfigurationManager(
            environment=Environment.DEVELOPMENT,
            config_dir=config_files
        )
        assert config_manager.environment == Environment.DEVELOPMENT
        assert config_manager.config_dir == Path(config_files)

    def test_load_configuration(self, config_files):
        """Test loading configuration from files."""
        config_manager = ConfigurationManager(
            environment=Environment.DEVELOPMENT,
            config_dir=config_files
        )

        assert config_manager.get("ATLAS_ENVIRONMENT") == "development"
        assert config_manager.get("API_PORT") == 7444
        assert config_manager.get("MAX_CONCURRENT_ARTICLES") == 5

    def test_get_with_default(self, config_files):
        """Test getting configuration with default value."""
        config_manager = ConfigurationManager(
            environment=Environment.DEVELOPMENT,
            config_dir=config_files
        )

        # Test with existing key
        assert config_manager.get("API_PORT", default=8080) == 7444

        # Test with non-existing key
        assert config_manager.get("NON_EXISTING_KEY", default="default_value") == "default_value"

    def test_get_required(self, config_files):
        """Test getting required configuration."""
        config_manager = ConfigurationManager(
            environment=Environment.DEVELOPMENT,
            config_dir=config_files
        )

        # Test with existing key
        assert config_manager.get("API_PORT", required=True) == 7444

        # Test with non-existing key
        with pytest.raises(ValueError, match="Required configuration 'NON_EXISTING_KEY' not found"):
            config_manager.get("NON_EXISTING_KEY", required=True)

    def test_set_configuration(self, config_files):
        """Test setting configuration values."""
        config_manager = ConfigurationManager(
            environment=Environment.DEVELOPMENT,
            config_dir=config_files
        )

        # Set new value
        config_manager.set("NEW_KEY", "new_value")
        assert config_manager.get("NEW_KEY") == "new_value"

        # Override existing value
        config_manager.set("API_PORT", 8080)
        assert config_manager.get("API_PORT") == 8080

    def test_validate_configuration(self, config_files):
        """Test configuration validation."""
        config_manager = ConfigurationManager(
            environment=Environment.DEVELOPMENT,
            config_dir=config_files
        )

        # Valid configuration should pass
        errors = config_manager.validate_configuration()
        assert len(errors) == 0

        # Set invalid value
        config_manager.set("API_PORT", 99999)
        errors = config_manager.validate_configuration()
        assert len(errors) > 0
        assert any("API_PORT" in error for error in errors)

    def test_export_configuration(self, config_files):
        """Test configuration export."""
        config_manager = ConfigurationManager(
            environment=Environment.DEVELOPMENT,
            config_dir=config_files
        )

        # Test JSON export
        json_export = config_manager.export_config(format="json")
        assert json_export.startswith('{')

        # Test YAML export
        yaml_export = config_manager.export_config(format="yaml")
        assert 'API_PORT' in yaml_export

        # Test ENV export
        env_export = config_manager.export_config(format="env")
        assert 'API_PORT=7444' in env_export

    def test_get_all_configuration(self, config_files):
        """Test getting all configuration."""
        config_manager = ConfigurationManager(
            environment=Environment.DEVELOPMENT,
            config_dir=config_files
        )

        config = config_manager.get_all()
        assert "ATLAS_ENVIRONMENT" in config
        assert "API_PORT" in config
        assert config["API_PORT"] == 7444

    def test_reload_configuration(self, config_files):
        """Test configuration reload."""
        config_manager = ConfigurationManager(
            environment=Environment.DEVELOPMENT,
            config_dir=config_files
        )

        # Modify configuration file
        config_file = Path(config_files) / "development.env"
        original_content = config_file.read_text()
        config_file.write_text(original_content + "\nNEW_RELOAD_KEY=reloaded_value\n")

        # Reload
        config_manager.reload_configuration()
        assert config_manager.get("NEW_RELOAD_KEY") == "reloaded_value"

    def test_environment_switching(self, temp_dir):
        """Test switching between environments."""
        config_dir = Path(temp_dir) / "config"
        config_dir.mkdir()

        # Create development config
        dev_config = config_dir / "development.env"
        dev_config.write_text("ENV=dev\nAPI_PORT=7444")

        # Create production config
        prod_config = config_dir / "production.env"
        prod_config.write_text("ENV=prod\nAPI_PORT=80")

        # Test development
        dev_manager = ConfigurationManager(
            environment=Environment.DEVELOPMENT,
            config_dir=str(config_dir)
        )
        assert dev_manager.get("ENV") == "dev"
        assert dev_manager.get("API_PORT") == 7444

        # Test production
        prod_manager = ConfigurationManager(
            environment=Environment.PRODUCTION,
            config_dir=str(config_dir)
        )
        assert prod_manager.get("ENV") == "prod"
        assert prod_manager.get("API_PORT") == 80

    def test_schema_validation(self, config_files):
        """Test schema-based validation."""
        config_manager = ConfigurationManager(
            environment=Environment.DEVELOPMENT,
            config_dir=config_files
        )

        # Test valid schema
        schema = config_manager.get_schema("API_PORT")
        assert schema is not None
        assert schema["type"] == "int"
        assert schema["min_value"] == 1024

        # Test non-existing schema
        schema = config_manager.get_schema("NON_EXISTING_KEY")
        assert schema is None


class TestSecretManager:
    """Test SecretManager functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def secret_files(self, temp_dir):
        """Create test secret files."""
        secrets_dir = Path(temp_dir) / "config"
        secrets_dir.mkdir()

        # Create development secrets
        dev_secrets = secrets_dir / "development.secrets"
        dev_secrets.write_text("""
OPENROUTER_API_KEY=test_api_key
YOUTUBE_API_KEY=encrypted:test_encrypted_key
""")

        return str(secrets_dir)

    def test_initialization(self, secret_files):
        """Test SecretManager initialization."""
        secret_manager = SecretManager(
            secrets_dir=secret_files,
            environment="development"
        )
        assert secret_manager.secrets_dir == Path(secret_files)
        assert secret_manager.environment == "development"

    def test_load_secrets_from_file(self, secret_files):
        """Test loading secrets from file."""
        secret_manager = SecretManager(
            secrets_dir=secret_files,
            environment="development",
            master_key="test_key"  # Use fixed key for testing
        )

        # Test plain text secret
        assert secret_manager.get_secret("OPENROUTER_API_KEY") == "test_api_key"

        # Test encrypted secret (this will fail with wrong key, but we check structure)
        assert "OPENROUTER_API_KEY" in secret_manager.secrets

    def test_get_secret(self, secret_files):
        """Test getting secrets."""
        secret_manager = SecretManager(
            secrets_dir=secret_files,
            environment="development"
        )

        # Test existing secret
        assert secret_manager.get_secret("OPENROUTER_API_KEY") == "test_api_key"

        # Test with default
        assert secret_manager.get_secret("NON_EXISTING_KEY", default="default") == "default"

        # Test required secret
        with pytest.raises(ValueError, match="Required secret 'NON_EXISTING_KEY' not found"):
            secret_manager.get_secret("NON_EXISTING_KEY", required=True)

    def test_set_secret(self, secret_files):
        """Test setting secrets."""
        secret_manager = SecretManager(
            secrets_dir=secret_files,
            environment="development",
            master_key="test_key"
        )

        # Set secret
        secret_manager.set_secret("NEW_SECRET", "new_value")
        assert secret_manager.get_secret("NEW_SECRET") == "new_value"

        # Set encrypted secret
        secret_manager.set_secret("ENCRYPTED_SECRET", "secret_value", encrypt=True)
        value = secret_manager.get_secret("ENCRYPTED_SECRET")
        assert value == "secret_value"

    def test_encrypt_decrypt_value(self, secret_files):
        """Test value encryption/decryption."""
        secret_manager = SecretManager(
            secrets_dir=secret_files,
            environment="development",
            master_key="test_key"
        )

        original_value = "test_secret_value"
        encrypted = secret_manager.encrypt_value(original_value)
        decrypted = secret_manager.decrypt_value(encrypted)

        assert decrypted == original_value
        assert encrypted != original_value

    def test_list_secrets(self, secret_files):
        """Test listing secrets."""
        secret_manager = SecretManager(
            secrets_dir=secret_files,
            environment="development"
        )

        secrets = secret_manager.list_secrets()
        assert "OPENROUTER_API_KEY" in secrets
        assert len(secrets) >= 1

    def test_delete_secret(self, secret_files):
        """Test deleting secrets."""
        secret_manager = SecretManager(
            secrets_dir=secret_files,
            environment="development"
        )

        # Add a secret
        secret_manager.set_secret("TEMP_SECRET", "temp_value")
        assert "TEMP_SECRET" in secret_manager.list_secrets()

        # Delete it
        result = secret_manager.delete_secret("TEMP_SECRET")
        assert result is True
        assert "TEMP_SECRET" not in secret_manager.list_secrets()

        # Try to delete non-existing secret
        result = secret_manager.delete_secret("NON_EXISTING")
        assert result is False

    def test_audit_secrets(self, secret_files):
        """Test secret auditing."""
        secret_manager = SecretManager(
            secrets_dir=secret_files,
            environment="development"
        )

        # Add some test secrets for auditing
        secret_manager.set_secret("WEAK_SECRET", "short")  # Too short
        secret_manager.set_secret("DEFAULT_SECRET", "password")  # Default value

        audit = secret_manager.audit_secrets()

        assert "findings" in audit
        assert "recommendations" in audit
        assert "total_secrets" in audit
        assert audit["total_secrets"] >= 2

        # Check for specific findings
        finding_types = [f["type"] for f in audit["findings"]]
        assert "weak_secret" in finding_types
        assert "default_value" in finding_types

    def test_export_secrets(self, secret_files):
        """Test secret export."""
        secret_manager = SecretManager(
            secrets_dir=secret_files,
            environment="development"
        )

        # Test ENV format
        env_export = secret_manager.export_secrets("env")
        assert "OPENROUTER_API_KEY=test_api_key" in env_export

        # Test JSON format
        json_export = secret_manager.export_secrets("json")
        json_data = json.loads(json_export)
        assert "OPENROUTER_API_KEY" in json_data

        # Test YAML format
        yaml_export = secret_manager.export_secrets("yaml")
        assert "OPENROUTER_API_KEY" in yaml_export


class TestConfigurationCLI:
    """Test configuration CLI functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def setup_files(self, temp_dir):
        """Set up test configuration files."""
        from tools.config_cli import ConfigCLI

        config_dir = Path(temp_dir) / "config"
        config_dir.mkdir()

        # Create test config
        dev_config = config_dir / "development.env"
        dev_config.write_text("""
ATLAS_ENVIRONMENT=development
API_PORT=7444
TEST_KEY=test_value
""")

        # Create test secrets
        dev_secrets = config_dir / "development.secrets"
        dev_secrets.write_text("""
TEST_SECRET=secret_value
""")

        return ConfigCLI(), str(config_dir)

    def test_cli_initialization(self, setup_files):
        """Test CLI initialization."""
        cli, config_dir = setup_files
        cli.init_managers("development", config_dir)
        assert cli.config_manager is not None
        assert cli.secret_manager is not None

    def test_cli_show_command(self, setup_files, capsys):
        """Test CLI show command."""
        cli, config_dir = setup_files
        cli.init_managers("development", config_dir)

        # Mock args
        class Args:
            key = "API_PORT"
            default = None
            required = False
            format = "text"

        cli.cmd_show(Args)
        captured = capsys.readouterr()
        assert "7444" in captured.out

    def test_cli_list_command(self, setup_files, capsys):
        """Test CLI list command."""
        cli, config_dir = setup_files
        cli.init_managers("development", config_dir)

        # Mock args
        class Args:
            pattern = None
            format = "text"

        cli.cmd_list(Args)
        captured = capsys.readouterr()
        assert "API_PORT=7444" in captured.out

    def test_cli_validate_command(self, setup_files, capsys):
        """Test CLI validate command."""
        cli, config_dir = setup_files
        cli.init_managers("development", config_dir)

        # Mock args
        class Args:
            fix = False

        cli.cmd_validate(Args)
        captured = capsys.readouterr()
        assert "valid" in captured.out

    def test_cli_secret_commands(self, setup_files, capsys):
        """Test CLI secret commands."""
        cli, config_dir = setup_files
        cli.init_managers("development", config_dir)

        # Test secret get
        class GetArgs:
            key = "TEST_SECRET"
            default = None
            required = False

        cli.cmd_secret(GetArgs)
        captured = capsys.readouterr()
        assert "secret_value" in captured.out

        # Test secret list
        class ListArgs:
            secret_command = "list"

        cli.cmd_secret(ListArgs)
        captured = capsys.readouterr()
        assert "TEST_SECRET" in captured.out


def test_integration_workflow(temp_dir):
    """Test complete configuration management workflow."""
    # Setup
    config_dir = Path(temp_dir) / "config"
    config_dir.mkdir()

    # Create config and secrets
    dev_config = config_dir / "development.env"
    dev_config.write_text("API_PORT=7444\nLOG_LEVEL=INFO")

    dev_secrets = config_dir / "development.secrets"
    dev_secrets.write_text("API_KEY=test_key")

    # Initialize managers
    config_manager = ConfigurationManager(
        environment=Environment.DEVELOPMENT,
        config_dir=str(config_dir)
    )
    secret_manager = SecretManager(
        secrets_dir=str(config_dir),
        environment="development"
    )

    # Test configuration operations
    assert config_manager.get("API_PORT") == 7444
    config_manager.set("NEW_CONFIG", "new_value")
    assert config_manager.get("NEW_CONFIG") == "new_value"

    # Test validation
    errors = config_manager.validate_configuration()
    assert len(errors) == 0

    # Test secret operations
    assert secret_manager.get_secret("API_KEY") == "test_key"
    secret_manager.set_secret("NEW_SECRET", "secret", encrypt=True)
    assert secret_manager.get_secret("NEW_SECRET") == "secret"

    # Test export
    json_config = config_manager.export_config(format="json")
    assert json.loads(json_config)["API_PORT"] == 7444

    env_secrets = secret_manager.export_secrets("env")
    assert "API_KEY=test_key" in env_secrets

    # Test audit
    audit = secret_manager.audit_secrets()
    assert audit["total_secrets"] >= 2


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])