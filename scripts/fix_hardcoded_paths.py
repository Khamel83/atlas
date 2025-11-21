#!/usr/bin/env python3
"""
Automated Hardcoded Path Fix Script

This script fixes the most critical hardcoded paths identified by detect_hardcoded_paths.py
by replacing them with configurable environment variables and proper path resolution.

Priority: Fix high-impact paths that prevent Atlas from being portable.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple


class HardcodedPathFixer:
    """Automated fixes for critical hardcoded paths."""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.fixes_applied = []

    def get_project_root_replacement(self) -> str:
        """Get the standard project root replacement pattern."""
        return "Path(__file__).resolve().parent.parent"

    def fix_restore_system_paths(self) -> None:
        """Fix hardcoded paths in backup/restore_system.py"""
        file_path = self.project_root / "backup/restore_system.py"
        if not file_path.exists():
            return

        print("🔧 Fixing restore_system.py...")
        content = file_path.read_text()

        replacements = [
            # Key path
            ('key_path = "/home/ubuntu/dev/atlas/backup/.backup_key"',
             'key_path = os.environ.get("ATLAS_BACKUP_KEY_PATH", str(Path(__file__).parent / ".backup_key"))'),

            # Atlas root path
            ('os.path.join("/home/ubuntu/dev/atlas", config_file)',
             'os.path.join(os.environ.get("ATLAS_ROOT", str(Path(__file__).resolve().parent.parent)), config_file)'),

            # Backup directory
            ('backup_dir = "/home/ubuntu/dev/atlas/backups"',
             'backup_dir = os.environ.get("ATLAS_BACKUP_DIR", str(Path(__file__).resolve().parent.parent / "backups"))'),

            # Backup paths in functions
            ('os.path.join("/home/ubuntu/dev/atlas/backups", backup)',
             'os.path.join(backup_dir, backup)'),

            ('os.path.join("/home/ubuntu/dev/atlas/backups", backup_file)',
             'os.path.join(backup_dir, backup_file)'),

            # Configuration restore path
            ('restore_configuration("/home/ubuntu/dev/atlas/backups/latest")',
             'restore_configuration(os.path.join(backup_dir, "latest"))'),
        ]

        for old, new in replacements:
            if old in content:
                content = content.replace(old, new)
                self.fixes_applied.append(f"restore_system.py: {old[:50]}... -> environment variable")

        # Ensure necessary imports
        if "from pathlib import Path" not in content:
            content = content.replace("import os", "import os\nfrom pathlib import Path")

        file_path.write_text(content)
        print(f"  ✅ Fixed {len([f for f in self.fixes_applied if 'restore_system' in f])} hardcoded paths")

    def fix_block14_progress(self) -> None:
        """Fix hardcoded paths in BLOCK_14_PROGRESS.py"""
        file_path = self.project_root / "BLOCK_14_PROGRESS.py"
        if not file_path.exists():
            return

        print("🔧 Fixing BLOCK_14_PROGRESS.py...")
        content = file_path.read_text()

        # Replace hardcoded atlas path with configurable root
        old_pattern = 'if os.path.exists(f"/home/ubuntu/dev/atlas/{file}"):'
        new_pattern = 'atlas_root = os.environ.get("ATLAS_ROOT", str(Path(__file__).resolve().parent))\n        if os.path.exists(os.path.join(atlas_root, file)):'

        if old_pattern in content:
            content = content.replace(old_pattern, new_pattern)
            self.fixes_applied.append("BLOCK_14_PROGRESS.py: hardcoded atlas path -> ATLAS_ROOT env var")

        # Ensure necessary imports
        if "from pathlib import Path" not in content:
            content = content.replace("import os", "import os\nfrom pathlib import Path")

        file_path.write_text(content)
        print("  ✅ Fixed BLOCK_14_PROGRESS.py hardcoded path")

    def fix_verification_tests(self) -> None:
        """Fix hardcoded paths in test files"""
        file_path = self.project_root / "tests/final_verification_block14.py"
        if not file_path.exists():
            return

        print("🔧 Fixing final_verification_block14.py...")
        content = file_path.read_text()

        replacements = [
            ('grafana_file = Path("/home/ubuntu/dev/atlas/monitoring/grafana_config/setup.py")',
             'atlas_root = os.environ.get("ATLAS_ROOT", str(Path(__file__).resolve().parent.parent))\n        grafana_file = Path(atlas_root) / "monitoring/grafana_config/setup.py"'),

            ('metrics_file = Path("/home/ubuntu/dev/atlas/monitoring/atlas_metrics_exporter.py")',
             'metrics_file = Path(atlas_root) / "monitoring/atlas_metrics_exporter.py"'),
        ]

        for old, new in replacements:
            if old in content:
                content = content.replace(old, new)
                self.fixes_applied.append(f"verification_tests: {old[:30]}... -> ATLAS_ROOT")

        # Ensure necessary imports
        if "import os" not in content:
            content = content.replace("import sys", "import sys\nimport os")

        file_path.write_text(content)
        print("  ✅ Fixed verification test hardcoded paths")

    def fix_backup_scripts_temp_paths(self) -> None:
        """Fix /tmp hardcoded paths in backup scripts"""
        backup_files = [
            "backup/database_backup.py",
            "backup/local_sync_backup.py",
            "backup/oci_storage_backup.py"
        ]

        for file_name in backup_files:
            file_path = self.project_root / file_name
            if not file_path.exists():
                continue

            print(f"🔧 Fixing {file_name}...")
            content = file_path.read_text()

            # Replace hardcoded /tmp paths
            old_pattern = 'with open("/tmp/new_crontab", "w") as f:'
            new_pattern = '''temp_dir = os.environ.get("ATLAS_TEMP_DIR", "/tmp")
        crontab_file = os.path.join(temp_dir, "new_crontab")
        with open(crontab_file, "w") as f:'''

            if old_pattern in content:
                content = content.replace(old_pattern, new_pattern)
                # Also fix the subprocess call
                content = content.replace('subprocess.run(["crontab", "/tmp/new_crontab"]',
                                        'subprocess.run(["crontab", crontab_file]')
                self.fixes_applied.append(f"{file_name}: /tmp/new_crontab -> configurable temp dir")

            # Fix ~/.ssh paths in local_sync_backup.py
            if "local_sync_backup.py" in file_name:
                ssh_replacements = [
                    ('ssh_dir = "~/.ssh"',
                     'ssh_dir = os.environ.get("ATLAS_SSH_DIR", os.path.expanduser("~/.ssh"))'),

                    ('"~/.ssh/atlas_backup"',
                     'os.path.join(ssh_dir, "atlas_backup")'),
                ]

                for old, new in ssh_replacements:
                    if old in content:
                        content = content.replace(old, new)
                        self.fixes_applied.append(f"{file_name}: {old} -> configurable")

            file_path.write_text(content)
            print(f"  ✅ Fixed {file_name}")

    def create_env_template_updates(self) -> None:
        """Update env.template with new configuration options"""
        env_template_path = self.project_root / "env.template"

        new_configs = """
# Path Configuration (for portability)
ATLAS_ROOT=/home/ubuntu/dev/atlas
ATLAS_BACKUP_DIR=${ATLAS_ROOT}/backups
ATLAS_BACKUP_KEY_PATH=${ATLAS_BACKUP_DIR}/.backup_key
ATLAS_TEMP_DIR=/tmp
ATLAS_SSH_DIR=~/.ssh
"""

        if env_template_path.exists():
            content = env_template_path.read_text()
            if "ATLAS_ROOT=" not in content:
                content += new_configs
                env_template_path.write_text(content)
                print("✅ Updated env.template with path configuration options")
        else:
            env_template_path.write_text(new_configs.strip())
            print("✅ Created env.template with path configuration")

    def generate_portability_guide(self) -> None:
        """Generate documentation for making Atlas portable"""
        guide_content = """# Atlas Portability Guide

## Environment Variables for Path Configuration

Atlas now supports configurable paths through environment variables for better portability:

### Core Paths
- `ATLAS_ROOT`: Main Atlas directory (default: `/home/ubuntu/dev/atlas`)
- `ATLAS_BACKUP_DIR`: Backup storage directory (default: `${ATLAS_ROOT}/backups`)
- `ATLAS_BACKUP_KEY_PATH`: Encryption key location (default: `${ATLAS_BACKUP_DIR}/.backup_key`)
- `ATLAS_TEMP_DIR`: Temporary files directory (default: `/tmp`)
- `ATLAS_SSH_DIR`: SSH configuration directory (default: `~/.ssh`)

### Usage for Different Environments

#### Development Environment
```bash
export ATLAS_ROOT="/Users/username/atlas"
export ATLAS_BACKUP_DIR="/Users/username/atlas-backups"
```

#### Production Environment
```bash
export ATLAS_ROOT="/opt/atlas"
export ATLAS_BACKUP_DIR="/var/backups/atlas"
export ATLAS_TEMP_DIR="/var/tmp/atlas"
```

#### Docker Environment
```bash
export ATLAS_ROOT="/app/atlas"
export ATLAS_BACKUP_DIR="/data/backups"
export ATLAS_TEMP_DIR="/tmp/atlas"
```

## Files Modified for Portability

The following files have been updated to use environment variables:
- `backup/restore_system.py` - Backup and restore paths
- `BLOCK_14_PROGRESS.py` - Progress tracking paths
- `tests/final_verification_block14.py` - Test file paths
- `backup/database_backup.py` - Temporary file paths
- `backup/local_sync_backup.py` - SSH and temporary paths
- `backup/oci_storage_backup.py` - Temporary file paths

## Benefits

- ✅ **Portable**: Works in any directory structure
- ✅ **Configurable**: Easy to adapt for different environments
- ✅ **Secure**: SSH and key paths can be customized
- ✅ **Docker-friendly**: No hardcoded host paths
- ✅ **Multi-user**: Each user can configure their own paths
"""

        guide_path = self.project_root / "docs/PORTABILITY_GUIDE.md"
        guide_path.parent.mkdir(exist_ok=True)
        guide_path.write_text(guide_content)
        print("📖 Created docs/PORTABILITY_GUIDE.md")

    def run_all_fixes(self) -> None:
        """Run all hardcoded path fixes"""
        print("🚀 Starting automated hardcoded path fixes...")

        # Apply fixes in order of priority
        self.fix_restore_system_paths()
        self.fix_block14_progress()
        self.fix_verification_tests()
        self.fix_backup_scripts_temp_paths()

        # Update configuration
        self.create_env_template_updates()

        # Generate documentation
        self.generate_portability_guide()

        # Summary
        print("\n" + "="*60)
        print("📊 HARDCODED PATH FIX SUMMARY")
        print("="*60)
        print(f"✅ Total fixes applied: {len(self.fixes_applied)}")
        print("\n📋 Fixes applied:")
        for i, fix in enumerate(self.fixes_applied, 1):
            print(f"  {i}. {fix}")

        print("\n🎯 Next Steps:")
        print("1. Update your .env file with custom paths if needed")
        print("2. Test the system with: python3 BLOCK_14_PROGRESS.py")
        print("3. Review docs/PORTABILITY_GUIDE.md for configuration options")
        print("4. Consider running the backup scripts to test portability")


def main():
    """Run the hardcoded path fixer"""
    fixer = HardcodedPathFixer()
    fixer.run_all_fixes()
    return len(fixer.fixes_applied)


if __name__ == "__main__":
    main()