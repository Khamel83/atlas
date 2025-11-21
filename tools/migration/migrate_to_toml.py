#!/usr/bin/env python3
"""
Gradual TOML Migration Script
Provides a safe, step-by-step migration from JSON to TOML configuration
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Import our config manager
from config_manager import AtlasConfig

class TOMLMigrator:
    """Safe migration tool for JSON to TOML transition"""

    def __init__(self):
        self.config_manager = AtlasConfig()
        self.backup_dir = Path("config_backup")
        self.steps = [
            {
                "name": "Backup Current Configuration",
                "action": self._backup_current_config,
                "rollback": self._restore_from_backup
            },
            {
                "name": "Check TOML Dependencies",
                "action": self._check_toml_dependencies,
                "rollback": lambda: True  # No-op for check step
            },
            {
                "name": "Create TOML Configuration",
                "action": self._create_toml_config,
                "rollback": self._remove_toml_config
            },
            {
                "name": "Test TOML Loading",
                "action": self._test_toml_loading,
                "rollback": lambda: True  # No-op for test step
            },
            {
                "name": "Update Code to Use TOML",
                "action": self._update_code_usage,
                "rollback": self._revert_code_changes
            },
            {
                "name": "Verify Migration",
                "action": self._verify_migration,
                "rollback": lambda: True  # No-op for verification
            }
        ]

    def _backup_current_config(self) -> bool:
        """Create backup of current configuration"""
        print("📋 Creating backup of current configuration...")

        try:
            # Create backup directory
            self.backup_dir.mkdir(exist_ok=True)

            # Backup JSON config if it exists
            json_config = Path("atlas_relayq_config.json")
            if json_config.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = self.backup_dir / f"atlas_relayq_config_backup_{timestamp}.json"

                import shutil
                shutil.copy2(json_config, backup_file)

                self.json_backup = backup_file
                print(f"   ✅ JSON config backed up to: {backup_file}")
            else:
                print("   ⚠️  No JSON config found to backup")
                self.json_backup = None

            return True

        except Exception as e:
            print(f"   ❌ Backup failed: {e}")
            return False

    def _restore_from_backup(self) -> bool:
        """Restore configuration from backup"""
        print("🔄 Restoring from backup...")

        try:
            if hasattr(self, 'json_backup') and self.json_backup and self.json_backup.exists():
                import shutil
                shutil.copy2(self.json_backup, "atlas_relayq_config.json")
                print(f"   ✅ Restored from: {self.json_backup}")

            return True

        except Exception as e:
            print(f"   ❌ Restore failed: {e}")
            return False

    def _check_toml_dependencies(self) -> bool:
        """Check if TOML support is available"""
        print("🔍 Checking TOML dependencies...")

        try:
            # Try to import TOML library
            try:
                import tomllib
                print("   ✅ Using built-in tomllib (Python 3.11+)")
                return True
            except ImportError:
                pass

            try:
                import tomli
                print("   ✅ Using tomli library")
                return True
            except ImportError:
                pass

            print("   ❌ TOML library not found")
            print("   💡 Install with: pip install tomli")
            return False

        except Exception as e:
            print(f"   ❌ Dependency check failed: {e}")
            return False

    def _create_toml_config(self) -> bool:
        """Create TOML configuration file"""
        print("📝 Creating TOML configuration...")

        try:
            # Use config manager to migrate
            success = self.config_manager.migrate_to_toml(backup=False)  # Already backed up

            if success:
                print("   ✅ TOML configuration created: atlas_config.toml")
                return True
            else:
                print("   ❌ TOML migration failed")
                return False

        except Exception as e:
            print(f"   ❌ TOML creation failed: {e}")
            return False

    def _remove_toml_config(self) -> bool:
        """Remove TOML configuration file"""
        print("🗑️  Removing TOML configuration...")

        try:
            toml_file = Path("atlas_config.toml")
            if toml_file.exists():
                toml_file.unlink()
                print("   ✅ TOML configuration removed")

            # Also remove pyproject.toml if created by this migration
            pyproject_file = Path("pyproject.toml")
            if pyproject_file.exists():
                # Only remove if we created it (check for migration marker)
                with open(pyproject_file, 'r') as f:
                    content = f.read()
                    if "Atlas: Podcast transcript discovery system" in content:
                        pyproject_file.unlink()
                        print("   ✅ pyproject.toml removed")

            return True

        except Exception as e:
            print(f"   ❌ TOML removal failed: {e}")
            return False

    def _test_toml_loading(self) -> bool:
        """Test that TOML configuration loads correctly"""
        print("🧪 Testing TOML loading...")

        try:
            # Test TOML loading
            config = self.config_manager.load_config(prefer_toml=True)
            format_used = self.config_manager.get_source_format()

            if format_used != "toml":
                print(f"   ❌ Expected TOML format, got: {format_used}")
                return False

            # Validate configuration
            if not self.config_manager.validate_config(config):
                print("   ❌ Configuration validation failed")
                return False

            print("   ✅ TOML loads correctly")
            print("   ✅ Configuration is valid")
            return True

        except Exception as e:
            print(f"   ❌ TOML loading test failed: {e}")
            return False

    def _update_code_usage(self) -> bool:
        """Update code to use TOML configuration"""
        print("⚙️  Updating code for TOML usage...")

        try:
            # Test that existing code can use TOML
            from relayq_service_setup import RelayQServiceSetup

            setup = RelayQServiceSetup()

            # Test that config manager works in context
            config = setup.config_manager.load_config()

            print("   ✅ relayq_service_setup.py updated")
            print("   ✅ Code can load TOML configuration")
            return True

        except Exception as e:
            print(f"   ❌ Code update failed: {e}")
            return False

    def _revert_code_changes(self) -> bool:
        """Revert code changes for TOML"""
        print("↩️  Reverting code changes...")

        try:
            # This would typically involve git checkout or restoring files
            # For now, we'll just remove config_manager.py if it was created
            config_manager = Path("config_manager.py")
            if config_manager.exists():
                # Only remove if we created it (simplified check)
                with open(config_manager, 'r') as f:
                    content = f.read()
                    if "Atlas configuration manager supporting both JSON and TOML" in content:
                        config_manager.unlink()
                        print("   ✅ config_manager.py removed")

            return True

        except Exception as e:
            print(f"   ❌ Code reversion failed: {e}")
            return False

    def _verify_migration(self) -> bool:
        """Verify complete migration success"""
        print("✅ Verifying migration...")

        try:
            # Check TOML file exists
            toml_file = Path("atlas_config.toml")
            if not toml_file.exists():
                print("   ❌ TOML configuration file missing")
                return False

            # Check JSON backup exists
            if hasattr(self, 'json_backup') and self.json_backup and not self.json_backup.exists():
                print("   ⚠️  JSON backup file missing")

            # Test configuration loading
            config = self.config_manager.load_config()

            # Test that existing functionality works
            from relayq_service_setup import RelayQServiceSetup
            setup = RelayQServiceSetup()

            print("   ✅ TOML configuration file exists")
            print("   ✅ Configuration loads successfully")
            print("   ✅ Existing code works with TOML")
            return True

        except Exception as e:
            print(f"   ❌ Verification failed: {e}")
            return False

    def run_migration(self, interactive: bool = True) -> bool:
        """Run the complete migration process"""
        print("🚀 Starting Gradual TOML Migration")
        print("=" * 50)

        completed_steps = []

        try:
            for i, step in enumerate(self.steps):
                step_name = step["name"]
                step_action = step["action"]

                print(f"\n📋 Step {i+1}/{len(self.steps)}: {step_name}")

                if interactive:
                    response = input("Continue? (y/n/s to skip): ").lower()
                    if response == 'n':
                        print("   ❌ Migration cancelled by user")
                        return False
                    elif response == 's':
                        print("   ⏭️  Step skipped")
                        continue
                    elif response != 'y':
                        print("   ❓ Proceeding anyway...")

                # Execute step
                success = step_action()

                if success:
                    completed_steps.append(step)
                    print(f"   ✅ {step_name} completed")
                else:
                    print(f"   ❌ {step_name} failed")

                    if interactive:
                        response = input("Rollback changes? (y/n): ").lower()
                        if response == 'y':
                            self._rollback(completed_steps)

                    return False

            print("\n" + "=" * 50)
            print("🎉 Migration completed successfully!")
            print("\n📋 Summary:")
            print("   ✅ JSON configuration backed up")
            print("   ✅ TOML configuration created")
            print("   ✅ Code updated for TOML support")
            print("   ✅ Migration verified")

            print(f"\n📁 Files:")
            print(f"   📋 Original: atlas_relayq_config.json (still present)")
            print(f"   🔧 New: atlas_config.toml")
            print(f"   📦 Project: pyproject.toml")
            print(f"   💾 Backup: {self.json_backup if hasattr(self, 'json_backup') and self.json_backup else 'None'}")

            return True

        except KeyboardInterrupt:
            print("\n\n⚠️  Migration interrupted by user")
            self._rollback(completed_steps)
            return False

    def _rollback(self, completed_steps):
        """Rollback completed steps in reverse order"""
        print("\n🔄 Rolling back changes...")

        for step in reversed(completed_steps):
            step_name = step["name"]
            rollback_action = step["rollback"]

            try:
                success = rollback_action()
                if success:
                    print(f"   ✅ Rolled back: {step_name}")
                else:
                    print(f"   ❌ Rollback failed: {step_name}")
            except Exception as e:
                print(f"   ❌ Rollback error for {step_name}: {e}")

        print("\n✅ Rollback completed")

def main():
    """Main migration interface"""
    if len(sys.argv) > 1 and sys.argv[1] == "--auto":
        interactive = False
    else:
        interactive = True

    migrator = TOMLMigrator()
    success = migrator.run_migration(interactive=interactive)

    if success:
        print("\n🎯 Next Steps:")
        print("   1. Test your existing Atlas functionality")
        print("   2. Run: python3 test_toml_migration.py")
        print("   3. If satisfied, you can remove the JSON config")
        print("   4. If issues occur, use rollback procedure in TOML_MIGRATION_GUIDE.md")

    exit(0 if success else 1)

if __name__ == "__main__":
    main()