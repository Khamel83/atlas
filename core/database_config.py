"""
Database configuration for Atlas system
"""

from dataclasses import dataclass, field
from typing import Optional
import yaml
import logging
from pathlib import Path


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