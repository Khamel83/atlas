#!/usr/bin/env python3
"""
Atlas Status - Unified system status

Usage:
    ./scripts/atlas_status.py              # System overview
    ./scripts/atlas_status.py --podcasts   # Per-podcast breakdown
    ./scripts/atlas_status.py --json       # JSON output
    ./scripts/atlas_status.py --no-color   # Plain text

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
    parser.add_argument(
        "--podcasts", "-p",
        action="store_true",
        help="Show per-podcast transcript status"
    )
    parser.add_argument(
        "--urls", "-u",
        action="store_true",
        help="Show per-domain URL fetcher status"
    )
    parser.add_argument(
        "--brief", "-b",
        action="store_true",
        help="Brief output (summary only)"
    )

    args = parser.parse_args()

    # Detect if output is not a terminal
    use_color = not args.no_color and sys.stdout.isatty()

    if args.podcasts:
        # Import and run podcast status
        from scripts.podcast_status import get_podcast_status, print_report
        import json as json_module
        podcasts = get_podcast_status()
        if args.json:
            data = {
                'podcasts': [
                    {
                        'slug': p.slug,
                        'fetched': p.fetched,
                        'pending': p.pending,
                        'failed': p.failed,
                        'total': p.total,
                        'pct': round(p.pct, 1),
                        'category': p.category
                    }
                    for p in podcasts
                ]
            }
            print(json_module.dumps(data, indent=2))
        else:
            print_report(podcasts, brief=args.brief)
    elif args.urls:
        # Import and run URL status
        from scripts.url_status import get_url_status, print_report
        import json as json_module
        domains = get_url_status()
        if args.json:
            data = {
                'domains': [
                    {
                        'domain': d.domain,
                        'fetched': d.fetched,
                        'failed': d.failed,
                        'total': d.total,
                        'success_rate': round(d.success_rate, 1),
                        'category': d.category
                    }
                    for d in domains if d.total >= 5
                ]
            }
            print(json_module.dumps(data, indent=2))
        else:
            print_report(domains, brief=args.brief)
    else:
        show_status(color=use_color, as_json=args.json)


if __name__ == "__main__":
    main()
