"""
Core Atlas System

Contains the essential components of the simplified Atlas system:
- Universal Database Service
- Configuration Management
- Data Models
"""

from .database import UniversalDatabase, Content, get_database
from .config import ConfigManager, get_config, DatabaseConfig, ProcessingConfig, APIConfig

__all__ = [
    'UniversalDatabase',
    'Content',
    'get_database',
    'ConfigManager',
    'get_config',
    'DatabaseConfig',
    'ProcessingConfig',
    'APIConfig'
]