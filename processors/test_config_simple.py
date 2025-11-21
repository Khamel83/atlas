#!/usr/bin/env python3
"""
Simple test for configuration management system.
"""

import sys
import tempfile
import shutil
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from helpers.configuration_manager import ConfigurationManager, Environment
from helpers.secret_manager import SecretManager


def test_basic_functionality():
    """Test basic configuration management functionality."""
    print("Testing basic configuration management...")

    # Create temporary directory
    temp_dir = tempfile.mkdtemp()
    try:
        config_dir = Path(temp_dir) / "config"
        config_dir.mkdir()

        # Create simple config file
        dev_config = config_dir / "development.env"
        dev_config.write_text("""
ATLAS_ENVIRONMENT=development
API_PORT=7444
TEST_KEY=test_value
LOG_LEVEL=DEBUG
""")

        # Test configuration manager
        config_manager = ConfigurationManager(
            environment=Environment.DEVELOPMENT,
            config_dir=str(config_dir)
        )

        # Test getting values
        env = config_manager.get("ATLAS_ENVIRONMENT")
        port = config_manager.get("API_PORT")
        test_key = config_manager.get("TEST_KEY")

        print(f"✓ Environment: {env}")
        print(f"✓ Port: {port}")
        print(f"✓ Test Key: {test_key}")

        assert env == "development"
        assert port == "7444"  # Will be string initially
        assert test_key == "test_value"

        # Test setting values
        config_manager.set("NEW_KEY", "new_value")
        new_value = config_manager.get("NEW_KEY")
        print(f"✓ New Key: {new_value}")
        assert new_value == "new_value"

        # Test getting all config
        all_config = config_manager.get_all()
        print(f"✓ Total config items: {len(all_config)}")
        assert "ATLAS_ENVIRONMENT" in all_config
        assert "NEW_KEY" in all_config

        print("✅ Configuration manager tests passed!")

    finally:
        shutil.rmtree(temp_dir)


def test_secret_manager():
    """Test secret manager functionality."""
    print("\nTesting secret manager...")

    # Create temporary directory
    temp_dir = tempfile.mkdtemp()
    try:
        secrets_dir = Path(temp_dir) / "config"
        secrets_dir.mkdir()

        # Create secrets file
        dev_secrets = secrets_dir / "development.secrets"
        dev_secrets.write_text("""
API_KEY=test_api_key
DB_PASSWORD=secret123
""")

        # Test secret manager
        secret_manager = SecretManager(
            secrets_dir=str(secrets_dir),
            environment="development"
        )

        # Test getting secrets
        api_key = secret_manager.get_secret("API_KEY")
        db_password = secret_manager.get_secret("DB_PASSWORD")

        print(f"✓ API Key: {api_key}")
        print(f"✓ DB Password: {db_password}")

        assert api_key == "test_api_key"
        assert db_password == "secret123"

        # Test setting secrets
        secret_manager.set_secret("NEW_SECRET", "secret_value")
        new_secret = secret_manager.get_secret("NEW_SECRET")
        print(f"✓ New Secret: {new_secret}")
        assert new_secret == "secret_value"

        # Test listing secrets
        secrets = secret_manager.list_secrets()
        print(f"✓ Total secrets: {len(secrets)}")
        assert "API_KEY" in secrets
        assert "NEW_SECRET" in secrets

        # Test encryption/decryption
        test_value = "test_encrypt_value"
        encrypted = secret_manager.encrypt_value(test_value)
        decrypted = secret_manager.decrypt_value(encrypted)
        print(f"✓ Encryption/Decryption works")
        assert decrypted == test_value
        assert encrypted != test_value

        # Test export
        exported = secret_manager.export_secrets("env")
        print(f"✓ Export successful")
        assert "API_KEY=test_api_key" in exported

        print("✅ Secret manager tests passed!")

    finally:
        shutil.rmtree(temp_dir)


def test_cli_tool():
    """Test CLI tool."""
    print("\nTesting CLI tool...")

    # Create temporary directory
    temp_dir = tempfile.mkdtemp()
    try:
        config_dir = Path(temp_dir) / "config"
        secrets_dir = Path(temp_dir) / "secrets"
        config_dir.mkdir()
        secrets_dir.mkdir()

        # Create config file
        dev_config = config_dir / "development.env"
        dev_config.write_text("""
TEST_CLI_KEY=cli_value
API_PORT=7444
""")

        # Create secrets file in separate directory
        dev_secrets = secrets_dir / "development.secrets"
        dev_secrets.write_text("""
TEST_CLI_SECRET=cli_secret_value
""")

        # Import CLI
        from tools.config_cli import ConfigCLI

        cli = ConfigCLI()
        cli.init_managers("development", str(config_dir), str(secrets_dir))

        # Test CLI functionality
        config_value = cli.config_manager.get("TEST_CLI_KEY")
        secret_value = cli.secret_manager.get_secret("TEST_CLI_SECRET")

        print(f"✓ CLI Config: {config_value}")
        print(f"✓ CLI Secret: {secret_value}")

        assert config_value == "cli_value"
        assert secret_value == "cli_secret_value"

        print("✅ CLI tool tests passed!")

    finally:
        shutil.rmtree(temp_dir)


def main():
    """Run all tests."""
    print("🚀 Starting configuration management tests...\n")

    try:
        test_basic_functionality()
        test_secret_manager()
        test_cli_tool()

        print("\n🎉 All tests passed! Configuration management system is working correctly.")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()