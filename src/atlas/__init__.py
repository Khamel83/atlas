"""
Atlas v4 - Personal Knowledge Automation System

A simple, modular system for ingesting and archiving digital content
into Markdown+YAML files compatible with Obsidian.

Core Philosophy:
- Tools, not frameworks
- Simple functions over complex classes
- File-based persistence
- Stateless operations where possible
"""

__version__ = "4.0.0"
__author__ = "Omar"

from .config import load_config
from .logging import setup_logging

__all__ = [
    "load_config",
    "setup_logging",
    "__version__",
]