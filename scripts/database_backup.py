#!/usr/bin/env python3
"""
Automated database backup system
"""

import sys
import json
import time
from pathlib import Path

# Add helpers to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from helpers.database_config import DatabaseManager

def main():
    """Main backup script"""
    import argparse

    parser = argparse.ArgumentParser(description="Database Backup Automation")
    parser.add_argument("--db", default="data/oos.db", help="Database path")
    parser.add_argument("--backup-dir", default="data/backups", help="Backup directory")
    parser.add_argument("--force", action="store_true", help="Force backup creation")
    parser.add_argument("--restore", help="Restore from backup name")
    parser.add_argument("--list", action="store_true", help="List available backups")
    parser.add_argument("--cleanup", action="store_true", help="Cleanup old backups")

    args = parser.parse_args()

    db_manager = DatabaseManager(args.db, args.backup_dir)

    try:
        if args.restore:
            print(f"Restoring database from backup: {args.restore}")
            result = db_manager.restore_from_backup(args.restore)
            print(json.dumps(result, indent=2))

        elif args.list:
            print("Available backups:")
            backups = db_manager.list_backups()
            for backup in backups:
                size_mb = backup['size'] / (1024 * 1024)
                print(f"  {backup['name']} - {size_mb:.1f}MB - {backup['created']}")

        elif args.cleanup:
            print("Cleaning up old backups...")
            db_manager._cleanup_old_backups()
            print("Cleanup completed")

        else:
            print("Creating database backup...")
            result = db_manager.create_backup()

            if result['success']:
                size_mb = result['size_bytes'] / (1024 * 1024)
                print(f"✓ Backup created: {result['backup_name']} ({size_mb:.1f}MB)")
            else:
                print(f"✗ Backup failed: {result['error']}")
                sys.exit(1)

    finally:
        db_manager.shutdown()

if __name__ == "__main__":
    main()