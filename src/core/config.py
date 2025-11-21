"""
Configuration management for Atlas

Centralized configuration loading with validation and hot reload support.
"""

import yaml
import os
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, field
import logging


@dataclass
class DatabaseConfig:
    """Database configuration"""
    db_path: str = "data/atlas.db"
    backup_path: str = "backups/atlas.db.bak"
    max_size_mb: int = 1000
    max_connections: int = 10
    min_connections: int = 2
    timeout_seconds: int = 30
    health_check_interval: int = 300
    cache_enabled: bool = True
    cache_size: int = 1000
    ttl_seconds: int = 3600
    wal_mode: bool = True
    foreign_keys: bool = True
    synchronous: str = "NORMAL"
    temp_store: str = "MEMORY"
    mmap_size: int = 268435456

    @classmethod
    def load(cls, config_path: str) -> 'DatabaseConfig':
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)

            if 'database' in config_data:
                db_config = config_data['database']
                conn_config = config_data.get('connection_pool', {})
                cache_config = config_data.get('cache', {})
                perf_config = config_data.get('performance', {})

                return cls(
                    db_path=db_config.get('path', 'data/atlas.db'),
                    backup_path=db_config.get('backup_path', 'backups/atlas.db.bak'),
                    max_size_mb=db_config.get('max_size_mb', 1000),
                    max_connections=conn_config.get('max_connections', 10),
                    min_connections=conn_config.get('min_connections', 2),
                    timeout_seconds=conn_config.get('timeout_seconds', 30),
                    health_check_interval=conn_config.get('health_check_interval', 300),
                    cache_enabled=cache_config.get('enabled', True),
                    cache_size=cache_config.get('max_size', 1000),
                    ttl_seconds=cache_config.get('ttl_seconds', 3600),
                    wal_mode=perf_config.get('wal_mode', True),
                    foreign_keys=perf_config.get('foreign_keys', True),
                    synchronous=perf_config.get('synchronous', 'NORMAL'),
                    temp_store=perf_config.get('temp_store', 'MEMORY'),
                    mmap_size=perf_config.get('mmap_size', 268435456)
                )
            else:
                # Return default config if file doesn't have database section
                return cls()

        except FileNotFoundError:
            logging.warning(f"Config file not found: {config_path}, using defaults")
            return cls()
        except Exception as e:
            logging.error(f"Failed to load config from {config_path}: {e}")
            return cls()


@dataclass
class ProcessingConfig:
    """Content processing configuration"""
    content_types: Dict[str, Any] = field(default_factory=dict)
    default_stages: Dict[str, list] = field(default_factory=dict)
    retry_attempts: int = 3
    retry_delay: int = 5
    timeout_seconds: int = 300
    max_content_size: int = 10485760  # 10MB

    @classmethod
    def load(cls, config_path: str) -> 'ProcessingConfig':
        """Load processing configuration"""
        try:
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)

            return cls(
                content_types=config_data.get('content_types', {}),
                default_stages=config_data.get('default_stages', {}),
                retry_attempts=config_data.get('retry_attempts', 3),
                retry_delay=config_data.get('retry_delay', 5),
                timeout_seconds=config_data.get('timeout_seconds', 300),
                max_content_size=config_data.get('max_content_size', 10485760)
            )
        except Exception as e:
            logging.error(f"Failed to load processing config from {config_path}: {e}")
            return cls()


@dataclass
class APIConfig:
    """API configuration"""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    cors_enabled: bool = True
    rate_limit: int = 100  # requests per minute
    api_key: Optional[str] = None
    auth_enabled: bool = False

    @classmethod
    def load(cls, config_path: str) -> 'APIConfig':
        """Load API configuration"""
        try:
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)

            api_config = config_data.get('api', {})
            return cls(
                host=api_config.get('host', '0.0.0.0'),
                port=api_config.get('port', 8000),
                debug=api_config.get('debug', False),
                cors_enabled=api_config.get('cors_enabled', True),
                rate_limit=api_config.get('rate_limit', 100),
                api_key=api_config.get('api_key'),
                auth_enabled=api_config.get('auth_enabled', False)
            )
        except Exception as e:
            logging.error(f"Failed to load API config from {config_path}: {e}")
            return cls()


class ConfigManager:
    """Centralized configuration management"""

    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self._configs = {}
        self._watchers = {}

    def get_database_config(self) -> DatabaseConfig:
        """Get database configuration"""
        if 'database' not in self._configs:
            config_path = self.config_dir / "database.yaml"
            self._configs['database'] = DatabaseConfig.load(str(config_path))
        return self._configs['database']

    def get_processing_config(self) -> ProcessingConfig:
        """Get processing configuration"""
        if 'processing' not in self._configs:
            config_path = self.config_dir / "processing.yaml"
            self._configs['processing'] = ProcessingConfig.load(str(config_path))
        return self._configs['processing']

    def get_api_config(self) -> APIConfig:
        """Get API configuration"""
        if 'api' not in self._configs:
            config_path = self.config_dir / "api.yaml"
            self._configs['api'] = APIConfig.load(str(config_path))
        return self._configs['api']

    def reload_config(self, config_type: str):
        """Reload specific configuration"""
        if config_type in self._configs:
            del self._configs[config_type]

        if config_type == 'database':
            return self.get_database_config()
        elif config_type == 'processing':
            return self.get_processing_config()
        elif config_type == 'api':
            return self.get_api_config()
        else:
            raise ValueError(f"Unknown config type: {config_type}")

    def get_all_configs(self) -> Dict[str, Any]:
        """Get all configurations as dictionary"""
        return {
            'database': self.get_database_config(),
            'processing': self.get_processing_config(),
            'api': self.get_api_config()
        }


# Global configuration instance
config_manager = ConfigManager()

def get_config() -> ConfigManager:
    """Get global configuration manager"""
    return config_manager