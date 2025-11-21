#!/usr/bin/env python3
"""
Atlas Backup Service

Automated backup of database and important files.
"""

import os
import sqlite3
import shutil
import logging
import sys
from datetime import datetime
from pathlib import Path
import gzip
import json

# Add parent directory to path
sys.path.insert(0, '..')

from core.database import get_database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AtlasBackup:
    """Backup service for Atlas data"""

    def __init__(self):
        self.base_dir = Path('..')
        self.data_dir = self.base_dir / 'data'
        self.backup_dir = self.base_dir / 'backups'
        self.backup_dir.mkdir(exist_ok=True)

    def create_backup(self):
        """Create a complete backup"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"atlas_backup_{timestamp}"
        backup_path = self.backup_dir / backup_name
        backup_path.mkdir(exist_ok=True)

        logger.info(f"🔄 Creating backup: {backup_name}")

        try:
            # Backup main database
            self._backup_database(backup_path, timestamp)

            # Backup configuration files
            self._backup_config(backup_path, timestamp)

            # Create backup manifest
            self._create_manifest(backup_path, timestamp)

            # Compress backup
            compressed_path = self._compress_backup(backup_path, timestamp)

            # Clean up old backups
            self._cleanup_old_backups()

            logger.info(f"✅ Backup completed: {compressed_path}")
            return str(compressed_path)

        except Exception as e:
            logger.error(f"🚨 Backup failed: {e}")
            # Clean up partial backup
            if backup_path.exists():
                shutil.rmtree(backup_path)
            raise

    def _backup_database(self, backup_path: Path, timestamp: str):
        """Backup the main SQLite database"""
        try:
            logger.info("📦 Backing up database...")

            # Get database path from config
            db_path = self.data_dir / 'atlas.db'
            if not db_path.exists():
                logger.warning("⚠️ No database file found")
                return

            backup_db_path = backup_path / 'atlas.db'

            # Use SQLite backup API for consistent backup
            source_conn = sqlite3.connect(str(db_path))
            backup_conn = sqlite3.connect(str(backup_db_path))

            with backup_conn:
                source_conn.backup(backup_conn)

            source_conn.close()
            backup_conn.close()

            logger.info(f"✅ Database backed up: {backup_db_path}")

        except Exception as e:
            logger.error(f"🚨 Database backup failed: {e}")
            raise

    def _backup_config(self, backup_path: Path, timestamp: str):
        """Backup configuration files"""
        try:
            logger.info("📦 Backing up configuration...")

            config_files = [
                '.env',
                'config/*.yaml',
                'systemd/*.service',
                'systemd/*.timer'
            ]

            config_backup_dir = backup_path / 'config'
            config_backup_dir.mkdir(exist_ok=True)

            for pattern in config_files:
                if '*' in pattern:
                    # Handle glob patterns
                    dir_part, file_part = pattern.split('/')
                    source_dir = self.base_dir / dir_part
                    if source_dir.exists():
                        dest_dir = config_backup_dir / dir_part
                        dest_dir.mkdir(exist_ok=True)

                        for file_path in source_dir.glob(file_part):
                            shutil.copy2(file_path, dest_dir / file_path.name)
                            logger.info(f"📦 Backed up config: {file_path}")
                else:
                    # Handle single files
                    source_path = self.base_dir / pattern
                    if source_path.exists():
                        shutil.copy2(source_path, config_backup_dir / pattern)
                        logger.info(f"📦 Backed up config: {pattern}")

        except Exception as e:
            logger.error(f"🚨 Configuration backup failed: {e}")
            raise

    def _create_manifest(self, backup_path: Path, timestamp: str):
        """Create backup manifest file"""
        try:
            logger.info("📋 Creating backup manifest...")

            manifest = {
                'backup_name': f"atlas_backup_{timestamp}",
                'timestamp': timestamp,
                'created_at': datetime.now().isoformat(),
                'version': '1.0',
                'files': []
            }

            # List all backed up files
            for file_path in backup_path.rglob('*'):
                if file_path.is_file():
                    relative_path = file_path.relative_to(backup_path)
                    file_info = {
                        'path': str(relative_path),
                        'size': file_path.stat().st_size,
                        'modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                    }
                    manifest['files'].append(file_info)

            # Save manifest
            manifest_path = backup_path / 'manifest.json'
            with open(manifest_path, 'w') as f:
                json.dump(manifest, f, indent=2)

            logger.info(f"📋 Manifest created: {manifest_path}")

        except Exception as e:
            logger.error(f"🚨 Manifest creation failed: {e}")
            raise

    def _compress_backup(self, backup_path: Path, timestamp: str) -> Path:
        """Compress backup directory"""
        try:
            logger.info("🗜️ Compressing backup...")

            compressed_path = backup_path.parent / f"{backup_path.name}.tar.gz"

            # Create tar.gz archive
            shutil.make_archive(
                str(backup_path),
                'gztar',
                backup_path.parent,
                backup_path.name
            )

            # Remove uncompressed directory
            shutil.rmtree(backup_path)

            logger.info(f"🗜️ Backup compressed: {compressed_path}")
            return compressed_path

        except Exception as e:
            logger.error(f"🚨 Backup compression failed: {e}")
            raise

    def _cleanup_old_backups(self):
        """Clean up old backup files"""
        try:
            logger.info("🧹 Cleaning up old backups...")

            # Keep last 7 daily backups
            # Keep last 4 weekly backups
            # Keep last 12 monthly backups

            backup_files = sorted(self.backup_dir.glob('atlas_backup_*.tar.gz'))

            if len(backup_files) <= 7:
                return

            # Remove oldest backups beyond the retention policy
            files_to_remove = backup_files[:-7]

            for backup_file in files_to_remove:
                backup_file.unlink()
                logger.info(f"🧹 Removed old backup: {backup_file}")

        except Exception as e:
            logger.error(f"🚨 Backup cleanup failed: {e}")

    def restore_backup(self, backup_path: str):
        """Restore from a backup file"""
        try:
            logger.info(f"🔄 Restoring from backup: {backup_path}")

            backup_file = Path(backup_path)
            if not backup_file.exists():
                raise FileNotFoundError(f"Backup file not found: {backup_path}")

            # Extract backup
            extract_dir = self.backup_dir / 'restore'
            extract_dir.mkdir(exist_ok=True)

            shutil.unpack_archive(backup_file, extract_dir)

            # Find the backup directory (should be the only directory)
            backup_dirs = [d for d in extract_dir.iterdir() if d.is_dir()]
            if not backup_dirs:
                raise ValueError("No backup directory found in archive")

            backup_dir = backup_dirs[0]

            # Restore database
            db_backup = backup_dir / 'atlas.db'
            if db_backup.exists():
                target_db = self.data_dir / 'atlas.db'
                shutil.copy2(db_backup, target_db)
                logger.info(f"✅ Database restored: {target_db}")

            # Restore configuration
            config_backup = backup_dir / 'config'
            if config_backup.exists():
                self._restore_config(config_backup)

            logger.info("✅ Backup restoration completed")

            # Clean up extracted files
            shutil.rmtree(extract_dir)

        except Exception as e:
            logger.error(f"🚨 Backup restoration failed: {e}")
            raise

    def _restore_config(self, config_backup_dir: Path):
        """Restore configuration files"""
        try:
            logger.info("📦 Restoring configuration files...")

            for item in config_backup_dir.rglob('*'):
                if item.is_file():
                    relative_path = item.relative_to(config_backup_dir)
                    target_path = self.base_dir / relative_path

                    # Create parent directory if needed
                    target_path.parent.mkdir(parents=True, exist_ok=True)

                    # Backup existing file if it exists
                    if target_path.exists():
                        backup_suffix = f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        target_path.rename(target_path.with_suffix(target_path.suffix + backup_suffix))

                    shutil.copy2(item, target_path)
                    logger.info(f"📦 Restored config: {target_path}")

        except Exception as e:
            logger.error(f"🚨 Configuration restoration failed: {e}")
            raise

    def health_check(self) -> dict:
        """Health check for backup service"""
        try:
            # Check if backup directory exists and is writable
            backup_space = shutil.disk_usage(self.backup_dir)
            recent_backups = len(list(self.backup_dir.glob('atlas_backup_*.tar.gz')))

            return {
                'status': 'healthy',
                'backup_directory': str(self.backup_dir),
                'free_space_gb': backup_space.free // (1024**3),
                'recent_backups': recent_backups,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

def main():
    """Main entry point"""
    backup_service = AtlasBackup()

    try:
        backup_path = backup_service.create_backup()
        print(f"✅ Backup created: {backup_path}")

        # Print health check
        health = backup_service.health_check()
        print(f"🏥 Backup service health: {health}")

    except Exception as e:
        logger.error(f"🚨 Backup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()