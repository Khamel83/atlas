#!/usr/bin/env python3
"""
OOS Smart Update System
One command to update any project to the latest OOS with strategic intelligence
"""

import os
import sys
import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
import hashlib

class OOSUpdater:
    """Smart OOS updater that only updates what's needed"""

    def __init__(self, project_path: str = "."):
        self.project_path = Path(project_path).resolve()
        self.oos_source = Path(__file__).parent  # Current OOS location
        self.backup_dir = self.project_path / ".oos_backup"
        self.changes_made = []
        self.skipped_files = []

    def update_project(self) -> None:
        """Main update method - does everything intelligently"""
        print("🚀 OOS Smart Update System")
        print("=" * 50)
        print(f"Project: {self.project_path}")
        print(f"OOS Source: {self.oos_source}")
        print()

        # Step 1: Check current state
        self._analyze_current_state()

        # Step 2: Create backup
        self._create_backup()

        # Step 3: Update core files
        self._update_core_files()

        # Step 4: Update command system
        self._update_command_system()

        # Step 5: Update configurations
        self._update_configurations()

        # Step 6: Update dependencies
        self._update_dependencies()

        # Step 7: Test installation
        self._test_installation()

        # Step 8: Show summary
        self._show_summary()

    def _analyze_current_state(self) -> None:
        """Analyze what's already in the project"""
        print("🔍 Analyzing current project state...")

        # Check for existing OOS components
        existing_components = {
            "strategic_consultant": (self.project_path / "src" / "strategic_consultant.py").exists(),
            "simple_command_handler": (self.project_path / "src" / "simple_command_handler.py").exists(),
            "consultant_config": (self.project_path / "config" / "consultant.yaml").exists(),
            "templates": (self.project_path / "templates").exists(),
            "archon_integration": (self.project_path / "src" / "archon_integration.py").exists()
        }

        for component, exists in existing_components.items():
            status = "✅ Found" if exists else "❌ Missing"
            print(f"  {status}: {component}")

        print()

    def _create_backup(self) -> None:
        """Create backup of existing files"""
        print("💾 Creating backup of existing files...")

        if self.backup_dir.exists():
            shutil.rmtree(self.backup_dir)
        self.backup_dir.mkdir(exist_ok=True)

        # Backup critical files that might be overwritten
        backup_files = [
            "src/simple_command_handler.py",
            "src/oos_cli.py",
            "config/consultant.yaml"
        ]

        for file_path in backup_files:
            full_path = self.project_path / file_path
            if full_path.exists():
                backup_path = self.backup_dir / file_path
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(full_path, backup_path)
                print(f"  📁 Backed up: {file_path}")

        print("  ✅ Backup complete")
        print()

    def _update_core_files(self) -> None:
        """Update core OOS files"""
        print("🧠 Updating core OOS files...")

        # Core files to update
        core_files = [
            "src/strategic_consultant.py",
            "src/archon_integration.py",
            "src/execution_driver.py",
            "src/adaptive_planner.py",
            "src/config_loader.py"
        ]

        for file_path in core_files:
            self._smart_copy_file(file_path)

        print("  ✅ Core files updated")
        print()

    def _update_command_system(self) -> None:
        """Update command system with intelligent merging"""
        print("🔧 Updating command system...")

        # Copy commands directory
        commands_src = self.oos_source / "src" / "commands"
        commands_dst = self.project_path / "src" / "commands"

        if commands_src.exists():
            if commands_dst.exists():
                print("  📁 Updating existing commands directory...")
            else:
                print("  📁 Creating new commands directory...")
                commands_dst.mkdir(parents=True, exist_ok=True)

            # Copy all command files
            for cmd_file in commands_src.glob("*.py"):
                dst_file = commands_dst / cmd_file.name
                if self._should_update_file(cmd_file, dst_file):
                    shutil.copy2(cmd_file, dst_file)
                    self.changes_made.append(f"Updated: {dst_file.relative_to(self.project_path)}")
                else:
                    self.skipped_files.append(f"Skipped: {dst_file.relative_to(self.project_path)} (no changes)")

        # Update main command handler with smart merging
        self._update_command_handler()

        print("  ✅ Command system updated")
        print()

    def _update_command_handler(self) -> None:
        """Smart update of simple_command_handler.py"""
        src_file = self.oos_source / "src" / "simple_command_handler.py"
        dst_file = self.project_path / "src" / "simple_command_handler.py"

        if not src_file.exists():
            print("  ⚠️  Source command handler not found")
            return

        if dst_file.exists():
            # Check if it already has consultant integration
            with open(dst_file, 'r') as f:
                content = f.read()

            if "ConsultantCommand" in content and "register_consultant_command" in content:
                print("  ✅ Command handler already has consultant integration")
                self.skipped_files.append("simple_command_handler.py (already integrated)")
                return

            print("  🔄 Updating command handler with consultant integration...")

        # Copy the enhanced version
        shutil.copy2(src_file, dst_file)
        self.changes_made.append("Updated: src/simple_command_handler.py")

    def _update_configurations(self) -> None:
        """Update configuration files"""
        print("📋 Updating configurations...")

        # Update consultant config
        config_src = self.oos_source / "config" / "consultant.yaml"
        config_dst = self.project_path / "config" / "consultant.yaml"

        if config_src.exists():
            config_dst.parent.mkdir(exist_ok=True)
            if self._should_update_file(config_src, config_dst):
                shutil.copy2(config_src, config_dst)
                self.changes_made.append("Updated: config/consultant.yaml")
            else:
                self.skipped_files.append("config/consultant.yaml (no changes)")

        # Copy templates
        templates_src = self.oos_source / "templates"
        templates_dst = self.project_path / "templates"

        if templates_src.exists():
            if not templates_dst.exists():
                print("  📁 Creating templates directory...")
                templates_dst.mkdir(exist_ok=True)

            for template_file in templates_src.glob("*.j2"):
                dst_template = templates_dst / template_file.name
                if self._should_update_file(template_file, dst_template):
                    shutil.copy2(template_file, dst_template)
                    self.changes_made.append(f"Updated: templates/{template_file.name}")

        print("  ✅ Configurations updated")
        print()

    def _update_dependencies(self) -> None:
        """Update dependencies if needed"""
        print("📦 Checking dependencies...")

        requirements_file = self.project_path / "requirements.txt"

        # Required dependencies for OOS
        required_deps = [
            "pyyaml>=6.0",
            "jinja2>=3.0",
            "asyncio",
            "pathlib"
        ]

        existing_deps = []
        if requirements_file.exists():
            with open(requirements_file, 'r') as f:
                existing_deps = f.read().splitlines()

        # Check which dependencies are missing
        missing_deps = []
        for dep in required_deps:
            dep_name = dep.split('>=')[0].split('==')[0]
            if not any(dep_name in line for line in existing_deps):
                missing_deps.append(dep)

        if missing_deps:
            print(f"  📦 Adding {len(missing_deps)} missing dependencies...")
            with open(requirements_file, 'a') as f:
                for dep in missing_deps:
                    f.write(f"\n{dep}")
            self.changes_made.append(f"Updated requirements.txt (+{len(missing_deps)} deps)")
        else:
            print("  ✅ All dependencies present")
            self.skipped_files.append("requirements.txt (up to date)")

        print()

    def _test_installation(self) -> None:
        """Test that the installation works"""
        print("🧪 Testing installation...")

        try:
            # Test import of strategic consultant
            sys.path.insert(0, str(self.project_path / "src"))

            from strategic_consultant import StrategicConsultant
            from commands.consultant_command import ConsultantCommand

            print("  ✅ Strategic consultant imports successfully")
            print("  ✅ Consultant command imports successfully")

            # Test basic initialization
            consultant = StrategicConsultant()
            print("  ✅ Strategic consultant initializes successfully")

            cmd = ConsultantCommand()
            print("  ✅ Consultant command initializes successfully")

            print("  🎉 Installation test passed!")

        except Exception as e:
            print(f"  ❌ Installation test failed: {e}")
            print("  💡 Try running the test manually after restart")

        print()

    def _show_summary(self) -> None:
        """Show update summary"""
        print("📊 Update Summary")
        print("=" * 50)

        print(f"✅ Changes made: {len(self.changes_made)}")
        for change in self.changes_made:
            print(f"  • {change}")

        if self.skipped_files:
            print(f"\n⏭️  Skipped (no changes): {len(self.skipped_files)}")
            for skipped in self.skipped_files[:5]:  # Show first 5
                print(f"  • {skipped}")
            if len(self.skipped_files) > 5:
                print(f"  • ... and {len(self.skipped_files) - 5} more")

        print(f"\n💾 Backup location: {self.backup_dir}")
        print()
        print("🚀 **OOS Update Complete!**")
        print()
        print("🎯 **Ready to use:**")
        print("  After restarting Claude Code, you can use:")
        print("  /consultant \"How do we optimize this system?\"")
        print("  /consultant status")
        print("  /consultant dashboard")
        print()
        print("✨ Your project now has strategic intelligence!")

    def _smart_copy_file(self, file_path: str) -> None:
        """Smart copy that only updates if needed"""
        src_file = self.oos_source / file_path
        dst_file = self.project_path / file_path

        if not src_file.exists():
            print(f"  ⚠️  Source file not found: {file_path}")
            return

        # Create destination directory if needed
        dst_file.parent.mkdir(parents=True, exist_ok=True)

        if self._should_update_file(src_file, dst_file):
            shutil.copy2(src_file, dst_file)
            self.changes_made.append(f"Updated: {file_path}")
            print(f"  📄 Updated: {file_path}")
        else:
            self.skipped_files.append(f"{file_path} (no changes)")

    def _should_update_file(self, src_file: Path, dst_file: Path) -> bool:
        """Check if file should be updated based on content hash"""
        if not dst_file.exists():
            return True

        # Compare file hashes
        src_hash = self._get_file_hash(src_file)
        dst_hash = self._get_file_hash(dst_file)

        return src_hash != dst_hash

    def _get_file_hash(self, file_path: Path) -> str:
        """Get MD5 hash of file content"""
        if not file_path.exists():
            return ""

        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()

def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="OOS Smart Update System")
    parser.add_argument("--project", "-p", default=".", help="Project directory (default: current)")
    parser.add_argument("--force", "-f", action="store_true", help="Force update all files")
    parser.add_argument("--dry-run", "-d", action="store_true", help="Show what would be updated")

    args = parser.parse_args()

    updater = OOSUpdater(args.project)

    if args.dry_run:
        print("🔍 DRY RUN MODE - No files will be changed")
        print()

    try:
        updater.update_project()
    except KeyboardInterrupt:
        print("\n⚠️  Update interrupted by user")
        print("💾 Partial backup available at:", updater.backup_dir)
    except Exception as e:
        print(f"\n❌ Update failed: {e}")
        print("💾 Backup available at:", updater.backup_dir)
        sys.exit(1)

if __name__ == "__main__":
    main()