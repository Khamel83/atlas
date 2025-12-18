"""
Atlas Status Module

Unified status reporting for all Atlas subsystems.

Usage:
    from modules.status import show_status
    show_status()

    # Or get raw data
    from modules.status import get_status
    status = get_status()
"""

import json
import sys
from pathlib import Path

from .collector import AtlasStatus, StatusCollector, collect_status
from .formatter import format_status, format_json


def get_status(data_dir: Path = None) -> AtlasStatus:
    """Get complete Atlas status."""
    return collect_status(data_dir)


def show_status(color: bool = True, as_json: bool = False):
    """Print Atlas status to stdout."""
    status = get_status()

    if as_json:
        print(json.dumps(format_json(status), indent=2))
    else:
        print(format_status(status, color=color))


__all__ = [
    "AtlasStatus",
    "StatusCollector",
    "collect_status",
    "get_status",
    "show_status",
    "format_status",
    "format_json",
]
