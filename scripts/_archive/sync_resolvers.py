#!/usr/bin/env python3
"""
Sync resolver configuration from mapping.yml to database.

The mapping.yml file is the source of truth for podcast resolver configuration.
This script updates the podcasts table to match.

Usage:
    python scripts/sync_resolvers.py           # Dry run
    python scripts/sync_resolvers.py --apply   # Apply changes
"""

import argparse
import sqlite3
from pathlib import Path

import yaml


def main():
    parser = argparse.ArgumentParser(description="Sync resolvers from mapping.yml to database")
    parser.add_argument("--apply", action="store_true", help="Actually apply changes (default is dry-run)")
    args = parser.parse_args()

    # Paths
    mapping_path = Path("config/mapping.yml")
    db_path = Path("data/podcasts/atlas_podcasts.db")

    if not mapping_path.exists():
        print(f"Error: mapping.yml not found at {mapping_path}")
        return 1

    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    # Load mapping.yml
    with open(mapping_path) as f:
        mapping = yaml.safe_load(f)

    # Connect to database
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Get current resolver values
    cursor = conn.execute("SELECT slug, resolver FROM podcasts")
    current_resolvers = {row["slug"]: row["resolver"] for row in cursor.fetchall()}

    # Find changes needed
    changes = []
    for slug, config in mapping.items():
        if not isinstance(config, dict):
            continue

        new_resolver = config.get("resolver")
        if not new_resolver:
            continue

        current = current_resolvers.get(slug)
        if current != new_resolver:
            changes.append({
                "slug": slug,
                "old": current or "(not in DB)",
                "new": new_resolver
            })

    # Report
    if not changes:
        print("No changes needed - all resolvers are in sync.")
        return 0

    print(f"{'Would update' if not args.apply else 'Updating'} {len(changes)} podcast resolvers:\n")

    for change in changes:
        print(f"  {change['slug']}: {change['old']} -> {change['new']}")

    if args.apply:
        for change in changes:
            conn.execute(
                "UPDATE podcasts SET resolver = ? WHERE slug = ?",
                (change["new"], change["slug"])
            )
        conn.commit()
        print(f"\nApplied {len(changes)} changes.")
    else:
        print(f"\nDry run - use --apply to make changes.")

    conn.close()
    return 0


if __name__ == "__main__":
    exit(main())
