"""
Configuration management for Atlas v4.

Handles loading and validation of YAML configuration files
with environment variable substitution and default values.
"""

import os
import re
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, field

from .logging import get_logger

logger = get_logger("config")


@dataclass
class DatabaseConfig:
    """Database configuration."""
    path: str = "data/atlas.db"
    backup_enabled: bool = True
    backup_interval_hours: int = 24
    max_backups: int = 7


@dataclass
class VaultConfig:
    """Vault storage configuration."""
    root: str = "./vault"
    inbox_dir: str = "inbox"
    logs_dir: str = "logs"
    failures_dir: str = "failures"


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    file: Optional[str] = None
    max_size_mb: int = 100
    backup_count: int = 5
    enable_console: bool = True


@dataclass
class TelegramConfig:
    """Telegram bot configuration."""
    bot_token: Optional[str] = None
    allowed_user_id: Optional[int] = None
    enabled: bool = False


@dataclass
class ProcessingConfig:
    """Content processing configuration."""
    max_concurrent_jobs: int = 5
    timeout_seconds: int = 300
    retry_attempts: int = 3


@dataclass
class AtlasConfig:
    """Main Atlas configuration."""
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    vault: VaultConfig = field(default_factory=VaultConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    telegram: TelegramConfig = field(default_factory=TelegramConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)

    # Version tracking
    version: str = "4.0.0"


class ConfigError(Exception):
    """Configuration-related errors."""
    pass


def substitute_env_vars(text: str) -> str:
    """
    Substitute environment variables in configuration values.

    Supports ${VAR_NAME} and ${VAR_NAME:default} syntax.

    Args:
        text: Text containing environment variable placeholders

    Returns:
        Text with environment variables substituted
    """
    if not isinstance(text, str):
        return text

    def replace_var(match):
        var_name = match.group(1)
        default_value = match.group(2) if match.group(2) is not None else ""
        return os.getenv(var_name, default_value)

    # Pattern: ${VAR_NAME} or ${VAR_NAME:default}
    pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'
    return re.sub(pattern, replace_var, text)


def process_config_values(config: Any) -> Any:
    """
    Process configuration values, applying environment variable substitution.

    Args:
        config: Configuration data structure

    Returns:
        Processed configuration
    """
    if isinstance(config, dict):
        return {k: process_config_values(v) for k, v in config.items()}
    elif isinstance(config, list):
        return [process_config_values(item) for item in config]
    elif isinstance(config, str):
        return substitute_env_vars(config)
    else:
        return config


def load_yaml_file(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Load and parse a YAML configuration file.

    Args:
        file_path: Path to YAML file

    Returns:
        Parsed configuration data

    Raises:
        ConfigError: If file cannot be loaded or parsed
    """
    path = Path(file_path)

    if not path.exists():
        raise ConfigError(f"Configuration file not found: {path}")

    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Pre-process for environment variables
        processed_content = substitute_env_vars(content)

        # Parse YAML
        data = yaml.safe_load(processed_content)

        if data is None:
            return {}

        # Process values for nested environment variables
        return process_config_values(data)

    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML in {path}: {str(e)}")
    except Exception as e:
        raise ConfigError(f"Error loading {path}: {str(e)}")


def validate_config(config_data: Dict[str, Any]) -> None:
    """
    Validate configuration structure and required fields.

    Args:
        config_data: Configuration data to validate

    Raises:
        ConfigError: If validation fails
    """
    required_sections = ['vault', 'logging']

    for section in required_sections:
        if section not in config_data:
            raise ConfigError(f"Missing required config section: {section}")

    # Validate vault configuration
    vault_config = config_data.get('vault', {})
    if not vault_config.get('root'):
        raise ConfigError("Vault root directory not specified")

    # Validate logging configuration
    logging_config = config_data.get('logging', {})
    level = logging_config.get('level', 'INFO')
    if level not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
        raise ConfigError(f"Invalid logging level: {level}")


def create_config_from_data(config_data: Dict[str, Any]) -> AtlasConfig:
    """
    Create AtlasConfig object from raw configuration data.

    Args:
        config_data: Raw configuration data

    Returns:
        AtlasConfig instance
    """
    # Extract section configurations
    db_data = config_data.get('database', {})
    vault_data = config_data.get('vault', {})
    logging_data = config_data.get('logging', {})
    telegram_data = config_data.get('telegram', {})
    processing_data = config_data.get('processing', {})

    return AtlasConfig(
        database=DatabaseConfig(**db_data),
        vault=VaultConfig(**vault_data),
        logging=LoggingConfig(**logging_data),
        telegram=TelegramConfig(**telegram_data),
        processing=ProcessingConfig(**processing_data),
        version=config_data.get('version', '4.0.0')
    )


def load_config(
    config_path: Optional[Union[str, Path]] = None,
    *,
    validate: bool = True
) -> AtlasConfig:
    """
    Load Atlas configuration from file.

    Args:
        config_path: Path to configuration file (default: config/config.yaml)
        validate: Whether to validate the configuration

    Returns:
        AtlasConfig instance

    Raises:
        ConfigError: If configuration cannot be loaded or is invalid
    """
    if config_path is None:
        # Try default locations
        default_paths = [
            "config/config.yaml",
            "config.yaml",
            os.getenv("ATLAS_CONFIG", ""),
        ]

        config_path = None
        for path in default_paths:
            if path and Path(path).exists():
                config_path = path
                break

        if config_path is None:
            raise ConfigError("No configuration file found. Tried: config/config.yaml, config.yaml, ATLAS_CONFIG env var")

    logger.info(f"Loading configuration from {config_path}")

    try:
        config_data = load_yaml_file(config_path)

        if validate:
            validate_config(config_data)

        config = create_config_from_data(config_data)

        logger.info(
            f"Configuration loaded successfully: vault_root={config.vault.root}, "
            f"log_level={config.logging.level}, db_path={config.database.path}"
        )

        return config

    except Exception as e:
        logger.error(f"Failed to load configuration: {str(e)}")
        raise


def save_config(config: AtlasConfig, config_path: Union[str, Path]) -> None:
    """
    Save Atlas configuration to YAML file.

    Args:
        config: AtlasConfig instance to save
        config_path: Path where to save the configuration
    """
    path = Path(config_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Convert to dictionary
    config_dict = {
        'version': config.version,
        'database': {
            'path': config.database.path,
            'backup_enabled': config.database.backup_enabled,
            'backup_interval_hours': config.database.backup_interval_hours,
            'max_backups': config.database.max_backups,
        },
        'vault': {
            'root': config.vault.root,
            'inbox_dir': config.vault.inbox_dir,
            'logs_dir': config.vault.logs_dir,
            'failures_dir': config.vault.failures_dir,
        },
        'logging': {
            'level': config.logging.level,
            'file': config.logging.file,
            'max_size_mb': config.logging.max_size_mb,
            'backup_count': config.logging.backup_count,
            'enable_console': config.logging.enable_console,
        },
        'telegram': {
            'bot_token': config.telegram.bot_token,
            'allowed_user_id': config.telegram.allowed_user_id,
            'enabled': config.telegram.enabled,
        },
        'processing': {
            'max_concurrent_jobs': config.processing.max_concurrent_jobs,
            'timeout_seconds': config.processing.timeout_seconds,
            'retry_attempts': config.processing.retry_attempts,
        }
    }

    try:
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(config_dict, f, default_flow_style=False, indent=2, sort_keys=False)

        logger.info(f"Configuration saved to {path}")

    except Exception as e:
        logger.error(f"Failed to save configuration: {str(e)}")
        raise ConfigError(f"Failed to save configuration: {str(e)}")


def get_default_config() -> AtlasConfig:
    """Get default Atlas configuration."""
    return AtlasConfig()


def ensure_vault_structure(config: VaultConfig) -> None:
    """
    Ensure vault directory structure exists.

    Args:
        config: Vault configuration
    """
    vault_root = Path(config.root)

    directories = [
        vault_root,
        vault_root / config.inbox_dir / "newsletters",
        vault_root / config.inbox_dir / "podcasts",
        vault_root / config.inbox_dir / "articles",
        vault_root / config.inbox_dir / "youtube",
        vault_root / config.inbox_dir / "emails",
        vault_root / config.logs_dir,
        vault_root / config.failures_dir,
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

    logger.info(f"Vault structure ensured at {vault_root}")


# Configuration template for initial setup
DEFAULT_CONFIG_TEMPLATE = """
# Atlas v4 Configuration

version: "4.0.0"

# Database settings (optional, for future search/indexing)
database:
  path: "data/atlas.db"
  backup_enabled: true
  backup_interval_hours: 24
  max_backups: 7

# Vault storage settings
vault:
  root: "./vault"
  inbox_dir: "inbox"
  logs_dir: "logs"
  failures_dir: "failures"

# Logging configuration
logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
  file: "vault/logs/atlas.log"
  max_size_mb: 100
  backup_count: 5
  enable_console: true

# Telegram bot configuration
telegram:
  bot_token: "${TELEGRAM_BOT_TOKEN}"  # Set environment variable
  allowed_user_id: ${TELEGRAM_USER_ID:-123456789}
  enabled: false

# Processing settings
processing:
  max_concurrent_jobs: 5
  timeout_seconds: 300
  retry_attempts: 3
"""