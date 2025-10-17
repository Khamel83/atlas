"""
Command-line interface for Atlas v4.

Provides comprehensive CLI commands for managing Atlas operations:
- Content ingestion from various sources
- Storage management and querying
- System monitoring and diagnostics
- Configuration management
"""

from .main import main, create_cli_parser
from .commands import (
    IngestCommand,
    QueryCommand,
    StatusCommand,
    ConfigCommand,
    CleanupCommand
)

__all__ = [
    "main",
    "create_cli_parser",
    "IngestCommand",
    "QueryCommand",
    "StatusCommand",
    "ConfigCommand",
    "CleanupCommand"
]