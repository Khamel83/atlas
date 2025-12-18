#!/usr/bin/env python3
"""
Atlas Status - Unified system status

Usage:
    ./scripts/atlas_status.py          # Color output
    ./scripts/atlas_status.py --json   # JSON output
    ./scripts/atlas_status.py --no-color  # Plain text

Or via module:
    python -m modules.status
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from modules.status import show_status


def main():
    parser = argparse.ArgumentParser(
        description="Show unified Atlas system status"
    )
    parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Output as JSON"
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable color output"
    )

    args = parser.parse_args()

    # Detect if output is not a terminal
    use_color = not args.no_color and sys.stdout.isatty()

    show_status(color=use_color, as_json=args.json)


if __name__ == "__main__":
    main()
