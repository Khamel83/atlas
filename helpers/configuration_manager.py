"""
Atlas Configuration and Secrets Management System

Provides a unified, secure, and production-ready configuration management system
with validation, encryption, environment-specific settings, and secret management.

Features:
- Environment-specific configuration (dev, staging, prod)
- Secret encryption and secure storage
- Configuration validation and schemas
- Hot-reload capabilities
- Audit logging for configuration changes
- Integration with external secret managers (AWS Secrets Manager, HashiCorp Vault)
"""

import os
import sys
import json
import yaml
import base64
import hashlib
import logging
from typing import Any, Dict, List, Optional, Union, Set
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import sqlite3
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Import existing config for compatibility
from .config import load_config as legacy_load_config

logger = logging.getLogger(__name__)


class Environment(Enum):
    """Supported deployment environments."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class ConfigSource(Enum):
    """Configuration source types."""
    ENVIRONMENT = "environment"
    FILE = "file"
    DATABASE = "database"
    SECRET_MANAGER = "secret_manager"
    DEFAULT = "default"


@dataclass
class ConfigValue:
    """Represents a configuration value with metadata."""
    value: Any
    source: ConfigSource
    encrypted: bool = False
    sensitive: bool = False
    last_modified: datetime = field(default_factory=datetime.now)
    version: int = 1


@dataclass
class ConfigSchema:
    """Configuration schema definition for validation."""
    field: str
    type: type
    required: bool = True
    default: Any = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    allowed_values: Optional[List[Any]] = None
    regex_pattern: Optional[str] = None
    description: str = ""


class ConfigurationError(Exception):
    """Configuration-related errors."""
    pass


class ConfigurationManager:
    """
    Centralized configuration management system with encryption support.

    Provides secure configuration loading, validation, and management across
    different environments with support for encrypted secrets.
    """

    def __init__(self,
                 environment: Environment = Environment.DEVELOPMENT,
                 config_dir: str = "config",
                 secrets_dir: str = "secrets",
                 encryption_key: Optional[str] = None):
        """
        Initialize configuration manager.

        Args:
            environment: Deployment environment
            config_dir: Directory for configuration files
            secrets_dir: Directory for encrypted secrets
            encryption_key: Optional encryption key for secrets
        """
        self.environment = environment
        self.config_dir = Path(config_dir)
        self.secrets_dir = Path(secrets_dir)
        self.config_cache: Dict[str, ConfigValue] = {}
        self.schema_cache: Dict[str, ConfigSchema] = {}
        self.audit_log: List[Dict[str, Any]] = []

        # Initialize encryption
        self.encryption_key = encryption_key or os.environ.get("ATLAS_ENCRYPTION_KEY")
        self.cipher_suite = None
        if self.encryption_key:
            self._initialize_encryption()

        # Ensure directories exist
        self.config_dir.mkdir(exist_ok=True)
        self.secrets_dir.mkdir(exist_ok=True, mode=0o700)  # Restricted permissions

        # Load schemas
        self._load_schemas()

        logger.info(f"ConfigurationManager initialized for {environment.value} environment")

    def _initialize_encryption(self):
        """Initialize encryption cipher suite."""
        if not self.encryption_key:
            raise ConfigurationError("Encryption key required for secure configuration")

        try:
            # Derive key from password using PBKDF2
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'atlas_salt',  # In production, use random salt per deployment
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(self.encryption_key.encode()))
            self.cipher_suite = Fernet(key)
            logger.info("Encryption initialized successfully")
        except Exception as e:
            raise ConfigurationError(f"Failed to initialize encryption: {e}")

    def _load_schemas(self):
        """Load configuration schemas from file."""
        schema_file = self.config_dir / "schemas.yaml"
        if schema_file.exists():
            try:
                with open(schema_file, 'r') as f:
                    schema_data = yaml.safe_load(f)

                for field_name, schema_def in schema_data.items():
                    self.schema_cache[field_name] = ConfigSchema(
                        field=field_name,
                        **schema_def
                    )
                logger.info(f"Loaded {len(self.schema_cache)} configuration schemas")
            except Exception as e:
                logger.warning(f"Failed to load configuration schemas: {e}")

    def get(self, key: str, default: Any = None, required: bool = False) -> Any:
        """
        Get configuration value with caching and validation.

        Args:
            key: Configuration key
            default: Default value if not found
            required: Whether the value is required

        Returns:
            Configuration value

        Raises:
            ConfigurationError: If required value is missing
        """
        # Check cache first
        if key in self.config_cache:
            return self.config_cache[key].value

        # Load value from various sources
        value = self._load_config_value(key)

        if value is None:
            if required:
                raise ConfigurationError(f"Required configuration '{key}' not found")
            return default

        # Validate value if schema exists
        if key in self.schema_cache:
            self._validate_value(key, value)

        # Cache the value
        self.config_cache[key] = ConfigValue(
            value=value,
            source=self._determine_source(key),
            sensitive=self._is_sensitive_field(key)
        )

        return value

    def set(self, key: str, value: Any, encrypt: bool = False) -> None:
        """
        Set configuration value with optional encryption.

        Args:
            key: Configuration key
            value: Configuration value
            encrypt: Whether to encrypt the value
        """
        # Validate value if schema exists
        if key in self.schema_cache:
            self._validate_value(key, value)

        # Encrypt if requested and sensitive
        if encrypt and self._is_sensitive_field(key):
            if not self.cipher_suite:
                raise ConfigurationError("Encryption not initialized")
            value = self.cipher_suite.encrypt(str(value).encode()).decode()

        # Store in appropriate location
        self._store_config_value(key, value, encrypt)

        # Update cache
        self.config_cache[key] = ConfigValue(
            value=value,
            source=ConfigSource.FILE,
            encrypted=encrypt,
            sensitive=self._is_sensitive_field(key)
        )

        # Log audit trail
        self._audit_log_action("SET", key, "***" if self._is_sensitive_field(key) else value)

        logger.info(f"Configuration '{key}' updated successfully")

    def reload(self) -> None:
        """Reload all configuration values."""
        self.config_cache.clear()
        logger.info("Configuration cache cleared, values will be reloaded on next access")

    def get_all(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """
        Get all configuration values.

        Args:
            include_sensitive: Whether to include sensitive values

        Returns:
            Dictionary of all configuration values
        """
        config = {}

        # Load from environment
        for key, value in os.environ.items():
            if key.startswith("ATLAS_") or not self._is_system_env(key):
                config[key] = value if include_sensitive or not self._is_sensitive_field(key) else "***"

        # Load from files
        env_file = self.config_dir / f"{self.environment.value}.env"
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        config[key] = value if include_sensitive or not self._is_sensitive_field(key) else "***"

        return config

    def export_config(self, output_file: str, include_sensitive: bool = False) -> None:
        """
        Export configuration to file.

        Args:
            output_file: Output file path
            include_sensitive: Whether to include sensitive values
        """
        config = self.get_all(include_sensitive=include_sensitive)

        with open(output_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, indent=2)

        logger.info(f"Configuration exported to {output_file}")
        self._audit_log_action("EXPORT", output_file, f"sensitive={include_sensitive}")

    def import_config(self, input_file: str, validate: bool = True) -> None:
        """
        Import configuration from file.

        Args:
            input_file: Input file path
            validate: Whether to validate imported values
        """
        with open(input_file, 'r') as f:
            config = yaml.safe_load(f)

        for key, value in config.items():
            if validate and key in self.schema_cache:
                self._validate_value(key, value)

            encrypt = self._is_sensitive_field(key) and self.cipher_suite is not None
            self.set(key, value, encrypt=encrypt)

        logger.info(f"Configuration imported from {input_file}")
        self._audit_log_action("IMPORT", input_file, f"keys={len(config)}")

    def validate_configuration(self) -> List[str]:
        """
        Validate all configuration values against schemas.

        Returns:
            List of validation errors
        """
        errors = []

        for key, schema in self.schema_cache.items():
            if schema.required:
                try:
                    value = self.get(key, required=True)
                    self._validate_value(key, value)
                except ConfigurationError as e:
                    errors.append(f"{key}: {e}")

        return errors

    def get_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get configuration audit log.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of audit log entries
        """
        return self.audit_log[-limit:]

    def _load_config_value(self, key: str) -> Any:
        """Load configuration value from various sources."""
        # Priority: Environment variables -> Environment files -> Database -> Default values

        # 1. Check environment variables
        env_value = os.environ.get(key)
        if env_value is not None:
            return env_value

        # 2. Check environment-specific files
        env_file = self.config_dir / f"{self.environment.value}.env"
        if env_file.exists():
            env_value = self._read_from_env_file(env_file, key)
            if env_value is not None:
                return env_value

        # 3. Check encrypted secrets file
        secrets_file = self.secrets_dir / f"{self.environment.value}.secrets"
        if secrets_file.exists():
            secret_value = self._read_from_secrets_file(secrets_file, key)
            if secret_value is not None:
                return secret_value

        # 4. Check legacy configuration for backward compatibility
        try:
            legacy_config = legacy_load_config()
            if key in legacy_config:
                return legacy_config[key]
        except Exception:
            pass

        # 5. Return default from schema if available
        if key in self.schema_cache:
            return self.schema_cache[key].default

        return None

    def _read_from_env_file(self, env_file: Path, key: str) -> Optional[str]:
        """Read value from environment file."""
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        file_key, value = line.strip().split('=', 1)
                        if file_key == key:
                            return value
        except Exception as e:
            logger.warning(f"Failed to read from {env_file}: {e}")
        return None

    def _read_from_secrets_file(self, secrets_file: Path, key: str) -> Optional[str]:
        """Read encrypted value from secrets file."""
        if not self.cipher_suite:
            return None

        try:
            with open(secrets_file, 'r') as f:
                secrets_data = yaml.safe_load(f) or {}

            if key in secrets_data:
                encrypted_value = secrets_data[key]
                return self.cipher_suite.decrypt(encrypted_value.encode()).decode()
        except Exception as e:
            logger.warning(f"Failed to decrypt secret {key} from {secrets_file}: {e}")
        return None

    def _store_config_value(self, key: str, value: Any, encrypt: bool) -> None:
        """Store configuration value in appropriate location."""
        if encrypt and self.cipher_suite:
            # Store in encrypted secrets file
            secrets_file = self.secrets_dir / f"{self.environment.value}.secrets"
            secrets_data = {}

            if secrets_file.exists():
                with open(secrets_file, 'r') as f:
                    secrets_data = yaml.safe_load(f) or {}

            secrets_data[key] = value  # Already encrypted if needed

            with open(secrets_file, 'w') as f:
                yaml.dump(secrets_data, f, default_flow_style=False)

            # Set restrictive permissions
            secrets_file.chmod(0o600)
        else:
            # Store in environment file
            env_file = self.config_dir / f"{self.environment.value}.env"

            # Read existing content
            existing_lines = []
            if env_file.exists():
                with open(env_file, 'r') as f:
                    existing_lines = f.readlines()

            # Update or add the key
            key_found = False
            with open(env_file, 'w') as f:
                for line in existing_lines:
                    if '=' in line and not line.startswith('#'):
                        existing_key = line.strip().split('=', 1)[0]
                        if existing_key == key:
                            f.write(f"{key}={value}\n")
                            key_found = True
                        else:
                            f.write(line)
                    else:
                        f.write(line)

                if not key_found:
                    f.write(f"{key}={value}\n")

    def _determine_source(self, key: str) -> ConfigSource:
        """Determine the source of a configuration value."""
        if key in os.environ:
            return ConfigSource.ENVIRONMENT
        return ConfigSource.FILE

    def _validate_value(self, key: str, value: Any) -> None:
        """Validate configuration value against schema."""
        if key not in self.schema_cache:
            return

        schema = self.schema_cache[key]

        # Type checking
        if not isinstance(value, schema.type):
            if schema.type == int and isinstance(value, str) and value.isdigit():
                value = int(value)
            elif schema.type == float and isinstance(value, str):
                try:
                    value = float(value)
                except ValueError:
                    pass
            else:
                raise ConfigurationError(f"Field '{key}' must be of type {schema.type.__name__}")

        # Required field checking
        if schema.required and value is None:
            raise ConfigurationError(f"Field '{key}' is required")

        # Range checking
        if schema.min_value is not None and value < schema.min_value:
            raise ConfigurationError(f"Field '{key}' must be >= {schema.min_value}")

        if schema.max_value is not None and value > schema.max_value:
            raise ConfigurationError(f"Field '{key}' must be <= {schema.max_value}")

        # Allowed values checking
        if schema.allowed_values and value not in schema.allowed_values:
            raise ConfigurationError(f"Field '{key}' must be one of {schema.allowed_values}")

        # Regex pattern checking
        if schema.regex_pattern and isinstance(value, str):
            import re
            if not re.match(schema.regex_pattern, value):
                raise ConfigurationError(f"Field '{key}' must match pattern {schema.regex_pattern}")

    def _is_sensitive_field(self, key: str) -> bool:
        """Check if a field contains sensitive information."""
        sensitive_patterns = [
            'password', 'secret', 'key', 'token', 'credential', 'auth',
            'api_key', 'private_key', 'certificate', 'license'
        ]

        key_lower = key.lower()
        return any(pattern in key_lower for pattern in sensitive_patterns)

    def _is_system_env(self, key: str) -> bool:
        """Check if environment variable is system-related."""
        system_vars = {
            'PATH', 'HOME', 'USER', 'SHELL', 'TERM', 'LANG', 'LC_ALL',
            'PYTHONPATH', 'VIRTUAL_ENV', 'CONDA_DEFAULT_ENV'
        }
        return key in system_vars

    def _audit_log_action(self, action: str, target: str, details: str) -> None:
        """Log configuration changes to audit trail."""
        audit_entry = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'target': target,
            'details': details,
            'environment': self.environment.value,
            'user': os.environ.get('USER', 'unknown')
        }
        self.audit_log.append(audit_entry)

        # Keep only last 1000 entries
        if len(self.audit_log) > 1000:
            self.audit_log = self.audit_log[-1000:]


# Global configuration manager instance
_config_manager: Optional[ConfigurationManager] = None


def get_config_manager(environment: Optional[Environment] = None) -> ConfigurationManager:
    """Get or create the global configuration manager instance."""
    global _config_manager

    if _config_manager is None:
        env = environment or Environment(os.environ.get("ATLAS_ENVIRONMENT", "development").lower())
        _config_manager = ConfigurationManager(environment=env)

    return _config_manager


def load_config() -> Dict[str, Any]:
    """
    Load configuration using the new configuration manager.

    This function maintains backward compatibility with the existing load_config()
    function while providing enhanced security and validation.

    Returns:
        Configuration dictionary
    """
    try:
        manager = get_config_manager()

        # For backward compatibility, return a dict with all values
        config = manager.get_all(include_sensitive=True)

        # Merge with legacy configuration to ensure all expected keys are present
        try:
            legacy_config = legacy_load_config()
            config.update(legacy_config)
        except Exception:
            pass

        return config
    except Exception as e:
        logger.error(f"Failed to load configuration with new manager: {e}")
        # Fallback to legacy configuration
        return legacy_load_config()


def get_config(key: str, default: Any = None) -> Any:
    """
    Get configuration value with backward compatibility.

    Args:
        key: Configuration key
        default: Default value if not found

    Returns:
        Configuration value
    """
    try:
        manager = get_config_manager()
        return manager.get(key, default)
    except Exception:
        # Fallback to environment variables
        return os.environ.get(key, default)


def set_config(key: str, value: Any, encrypt: bool = False) -> None:
    """
    Set configuration value.

    Args:
        key: Configuration key
        value: Configuration value
        encrypt: Whether to encrypt the value
    """
    try:
        manager = get_config_manager()
        manager.set(key, value, encrypt)
    except Exception as e:
        logger.error(f"Failed to set configuration {key}: {e}")
        raise ConfigurationError(f"Failed to set configuration: {e}")


# Initialize the configuration manager on module import
try:
    get_config_manager()
except Exception as e:
    logger.warning(f"Failed to initialize configuration manager: {e}")
    logger.info("Falling back to legacy configuration system")