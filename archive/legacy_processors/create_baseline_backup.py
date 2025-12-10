#!/usr/bin/env python3
"""
Atlas Baseline Backup Script
Creates comprehensive backup of current working system before refactor
"""

import os
import sys
import shutil
import sqlite3
import json
import gzip
import hashlib
from datetime import datetime
from pathlib import Path
import subprocess
import tarfile

class AtlasBaselineBackup:
    """Create comprehensive baseline backup of Atlas system"""

    def __init__(self, backup_dir=None):
        self.backup_dir = Path(backup_dir or f"backup_baseline_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        self.backup_dir.mkdir(exist_ok=True)
        self.source_dir = Path.cwd()
        self.backup_log = []

    def log(self, message):
        """Log backup progress"""
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)
        self.backup_log.append(log_entry)

    def backup_database(self):
        """Backup main database with verification"""
        self.log("🔄 Backing up main database...")

        # Get database stats
        db_path = self.source_dir / "data" / "atlas.db"
        if not db_path.exists():
            self.log("❌ Main database not found!")
            return False

        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Get content counts
            cursor.execute("SELECT COUNT(*) FROM content")
            total_content = cursor.fetchone()[0]

            # Get content types breakdown
            cursor.execute("SELECT content_type, COUNT(*) FROM content GROUP BY content_type")
            content_types = dict(cursor.fetchall())

            # Get recent activity
            cursor.execute("SELECT COUNT(*) FROM content WHERE created_at >= datetime('now', '-7 days')")
            recent_content = cursor.fetchone()[0]

            conn.close()

            # Copy database file
            backup_db = self.backup_dir / "data" / "atlas.db"
            backup_db.parent.mkdir(exist_ok=True)
            shutil.copy2(db_path, backup_db)

            # Verify backup
            if backup_db.stat().st_size == db_path.stat().st_size:
                self.log(f"✅ Database backed up: {total_content:,} total items, {recent_content:,} recent")
                self.log(f"   Content types: {content_types}")
                return True
            else:
                self.log("❌ Database backup size mismatch!")
                return False

        except Exception as e:
            self.log(f"❌ Database backup failed: {e}")
            return False

    def backup_configuration(self):
        """Backup configuration files"""
        self.log("🔄 Backing up configuration...")

        config_files = [
            ".env",
            ".env.template",
            "requirements.txt",
            "requirements-dev.txt",
            "VERSION",
            ".gitignore"
        ]

        backup_configs = self.backup_dir / "config"
        backup_configs.mkdir(exist_ok=True)

        for config_file in config_files:
            source = self.source_dir / config_file
            if source.exists():
                dest = backup_configs / config_file
                shutil.copy2(source, dest)
                self.log(f"✅ Config: {config_file}")
            else:
                self.log(f"⚠️  Config not found: {config_file}")

    def backup_key_scripts(self):
        """Backup key Python scripts and services"""
        self.log("🔄 Backing up key scripts...")

        key_scripts = [
            "atlas_comprehensive_service.py",
            "atlas_service_manager.py",
            "atlas_status.py",
            "universal_processing_queue.py",
            "simple_url_worker.py",
            "helpers/simple_database.py",
            "helpers/source_inventory.py",
            "helpers/podcast_transcript_lookup_simple.py",
            "transcript_orchestrator.py"
        ]

        backup_scripts = self.backup_dir / "scripts"
        backup_scripts.mkdir(exist_ok=True)

        for script in key_scripts:
            source = self.source_dir / script
            if source.exists():
                dest = backup_scripts / Path(script).name
                dest.parent.mkdir(exist_ok=True)
                shutil.copy2(source, dest)
                self.log(f"✅ Script: {script}")
            else:
                self.log(f"⚠️  Script not found: {script}")

    def backup_data_directory(self):
        """Backup additional data files"""
        self.log("🔄 Backing up additional data...")

        data_files = [
            "scheduler.db",
            "uploads",
            "output",
            "logs",
            "content"
        ]

        backup_data = self.backup_dir / "additional_data"
        backup_data.mkdir(exist_ok=True)

        for data_item in data_files:
            source = self.source_dir / "data" / data_item
            if source.exists():
                dest = backup_data / data_item
                if source.is_file():
                    shutil.copy2(source, dest)
                else:
                    shutil.copytree(source, dest, ignore=shutil.ignore_patterns('*.log', '*.tmp'))
                self.log(f"✅ Data: {data_item}")

    def backup_workflow_files(self):
        """Sample backup of workflow files (not all due to large number)"""
        self.log("🔄 Sampling workflow files...")

        workflow_dir = self.source_dir
        workflow_files = list(workflow_dir.glob("workflow_*"))

        # Take a sample of recent workflow files
        sample_size = min(10, len(workflow_files))
        sampled_workflows = sorted(workflow_files, key=lambda x: x.stat().st_mtime)[-sample_size:]

        backup_workflows = self.backup_dir / "workflows_sample"
        backup_workflows.mkdir(exist_ok=True)

        for workflow in sampled_workflows:
            shutil.copy2(workflow, backup_workflows / workflow.name)

        self.log(f"✅ Sampled {len(sampled_workflows)} workflow files")

    def create_system_snapshot(self):
        """Create system snapshot with current state"""
        self.log("🔄 Creating system snapshot...")

        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "backup_version": "1.0",
            "system_info": {},
            "git_status": {},
            "file_counts": {},
            "database_stats": {}
        }

        # Get system info
        try:
            snapshot["system_info"]["python_version"] = sys.version
            snapshot["system_info"]["platform"] = sys.platform
        except:
            pass

        # Get git status
        try:
            result = subprocess.run(['git', 'log', '--oneline', '-5'],
                                 capture_output=True, text=True, cwd=self.source_dir)
            snapshot["git_status"]["recent_commits"] = result.stdout.strip().split('\n')

            result = subprocess.run(['git', 'status', '--porcelain'],
                                 capture_output=True, text=True, cwd=self.source_dir)
            snapshot["git_status"]["modified_files"] = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
        except:
            pass

        # Count files by type
        file_counts = {}
        for ext in ['.py', '.md', '.txt', '.json', '.yml', '.yaml', '.sql', '.html', '.css']:
            count = len(list(self.source_dir.rglob(f"*{ext}")))
            if count > 0:
                file_counts[ext] = count
        snapshot["file_counts"] = file_counts

        # Database stats
        try:
            db_path = self.source_dir / "data" / "atlas.db"
            if db_path.exists():
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()

                cursor.execute("SELECT COUNT(*) FROM content")
                snapshot["database_stats"]["total_content"] = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM content WHERE content_type = 'article'")
                snapshot["database_stats"]["articles"] = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM content WHERE content_type = 'podcast'")
                snapshot["database_stats"]["podcasts"] = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM content WHERE ai_summary IS NOT NULL AND ai_summary != ''")
                snapshot["database_stats"]["with_ai_summary"] = cursor.fetchone()[0]

                conn.close()
        except Exception as e:
            snapshot["database_stats"]["error"] = str(e)

        # Save snapshot
        snapshot_file = self.backup_dir / "system_snapshot.json"
        with open(snapshot_file, 'w') as f:
            json.dump(snapshot, f, indent=2)

        self.log("✅ System snapshot created")

    def create_compressed_archive(self):
        """Create compressed archive of backup"""
        self.log("🔄 Creating compressed archive...")

        archive_name = f"atlas_baseline_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tar.gz"
        archive_path = self.source_dir / archive_name

        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(self.backup_dir, arcname=self.backup_dir.name)

        # Calculate checksum
        with open(archive_path, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()

        self.log(f"✅ Archive created: {archive_name}")
        self.log(f"   Size: {archive_path.stat().st_size / (1024*1024):.1f} MB")
        self.log(f"   SHA256: {file_hash[:16]}...")

        return archive_path, file_hash

    def create_restore_script(self):
        """Create script to restore from backup"""
        self.log("🔄 Creating restore script...")

        restore_script = f"""#!/bin/bash
# Atlas Backup Restore Script
# Created: {datetime.now().isoformat()}

BACKUP_DIR="{self.backup_dir.name}"
ARCHIVE_FILE="atlas_baseline_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tar.gz"

echo "🔄 Restoring Atlas from backup: $BACKUP_DIR"
echo "⚠️  This will overwrite current system files!"
read -p "Continue? (y/N): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Extract backup
    tar -xzf $ARCHIVE_FILE

    # Restore database
    if [ -f "$BACKUP_DIR/data/atlas.db" ]; then
        cp "$BACKUP_DIR/data/atlas.db" data/atlas.db
        echo "✅ Database restored"
    fi

    # Restore configs
    if [ -d "$BACKUP_DIR/config" ]; then
        cp -r "$BACKUP_DIR/config/"* . 2>/dev/null || true
        echo "✅ Configs restored"
    fi

    # Restore scripts
    if [ -d "$BACKUP_DIR/scripts" ]; then
        cp -r "$BACKUP_DIR/scripts/"* . 2>/dev/null || true
        echo "✅ Scripts restored"
    fi

    echo "✅ Restore complete!"
    echo "📊 System restored to backup timestamp: {datetime.now().isoformat()}"
else
    echo "❌ Restore cancelled"
fi
"""

        script_file = self.source_dir / f"restore_from_{self.backup_dir.name}.sh"
        with open(script_file, 'w') as f:
            f.write(restore_script)

        os.chmod(script_file, 0o755)
        self.log(f"✅ Restore script: {script_file.name}")

    def run_backup(self):
        """Execute complete backup process"""
        self.log("🚀 Starting Atlas baseline backup...")
        self.log(f"📁 Backup directory: {self.backup_dir}")

        success = True

        # Execute all backup steps
        success &= self.backup_database()
        self.backup_configuration()
        self.backup_key_scripts()
        self.backup_data_directory()
        self.backup_workflow_files()
        self.create_system_snapshot()
        self.create_restore_script()

        # Create final archive
        try:
            archive_path, checksum = self.create_compressed_archive()
            self.log("🎉 Baseline backup completed successfully!")
            self.log(f"📦 Archive: {archive_path}")
            self.log(f"🔐 Checksum: {checksum}")
        except Exception as e:
            self.log(f"❌ Archive creation failed: {e}")
            success = False

        # Save backup log
        log_file = self.backup_dir / "backup_log.txt"
        with open(log_file, 'w') as f:
            f.write('\n'.join(self.backup_log))

        return success

if __name__ == "__main__":
    backup = AtlasBaselineBackup()
    success = backup.run_backup()

    if success:
        print("\n🎉 Backup completed successfully!")
        print(f"📁 Backup location: {backup.backup_dir}")
        print("📋 You can now proceed with the refactor safely!")
    else:
        print("\n❌ Backup failed! Check log for details.")
        sys.exit(1)