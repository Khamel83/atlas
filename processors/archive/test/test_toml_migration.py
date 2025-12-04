#!/usr/bin/env python3
"""
TOML Migration Test Suite
Tests the TOML migration to ensure compatibility and fallback mechanisms work
"""

import os
import json
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any

# Import our config manager
from config_manager import AtlasConfig

class TOMLMigrationTest:
    """Test suite for TOML migration functionality"""

    def __init__(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="atlas_toml_test_"))
        self.original_dir = Path.cwd()
        self.backup_files = {}

    def setup_test_environment(self):
        """Create a test environment with sample configuration"""
        print("🔧 Setting up test environment...")

        # Change to test directory
        os.chdir(self.test_dir)

        # Create sample JSON config
        sample_config = {
            "service_name": "Test Atlas Integration",
            "version": "1.0.0",
            "created": "2025-11-12T00:00:00.000000",
            "atlas": {
                "database_path": str(self.test_dir / "test.db"),
                "podcasts_count": 10,
                "episodes_count": 100
            },
            "relayq": {
                "repository": "test/relayq",
                "workflow_file": "test_workflow.yml",
                "job_labels": ["test-atlas", "test-transcript"],
                "auto_schedule": "0 */6 * * *"
            },
            "processing": {
                "batch_size": 5,
                "retry_attempts": 2,
                "priority_levels": 3,
                "supported_tasks": [
                    "test-transcript-discovery",
                    "test-episode-backlog"
                ]
            },
            "endpoints": {
                "github_api": "https://api.github.com",
                "relayq_repo": "https://github.com/test/relayq",
                "atlas_status": f"sqlite:///{self.test_dir}/test.db"
            }
        }

        # Write JSON config
        with open("atlas_relayq_config.json", 'w') as f:
            json.dump(sample_config, f, indent=2)

        # Create a dummy database file
        (self.test_dir / "test.db").touch()

        print(f"   ✅ Test environment ready: {self.test_dir}")
        return sample_config

    def test_toml_loading(self) -> bool:
        """Test TOML configuration loading"""
        print("\n📋 Testing TOML loading...")

        try:
            # Import TOML support
            try:
                import tomllib  # Python 3.11+
            except ImportError:
                import tomli as tomllib

            # Test direct TOML loading
            with open("../atlas_config.toml", 'rb') as f:
                config = tomllib.load(f)

            # Validate structure
            required_sections = ["service", "atlas", "relayq", "processing", "endpoints"]
            for section in required_sections:
                if section not in config:
                    print(f"   ❌ Missing section: {section}")
                    return False

            print("   ✅ TOML structure valid")
            print(f"   ✅ Service name: {config['service']['name']}")
            print(f"   ✅ Atlas podcasts: {config['atlas']['podcasts_count']}")
            return True

        except Exception as e:
            print(f"   ❌ TOML loading failed: {e}")
            return False

    def test_config_manager_fallback(self) -> bool:
        """Test configuration manager fallback mechanism"""
        print("\n🔄 Testing fallback mechanism...")

        try:
            # Initialize config manager
            config_manager = AtlasConfig()

            # Test with no TOML file (should fallback to JSON)
            if Path("atlas_config.toml").exists():
                Path("atlas_config.toml").unlink()

            config = config_manager.load_config(prefer_toml=True)
            format_used = config_manager.get_source_format()

            if format_used != "json":
                print(f"   ❌ Expected JSON fallback, got: {format_used}")
                return False

            print("   ✅ JSON fallback working")

            # Copy TOML from parent directory and test
            shutil.copy("../atlas_config.toml", "atlas_config.toml")

            config_manager = AtlasConfig()  # Reinitialize
            config = config_manager.load_config(prefer_toml=True)
            format_used = config_manager.get_source_format()

            if format_used != "toml":
                print(f"   ❌ Expected TOML, got: {format_used}")
                return False

            print("   ✅ TOML preference working")
            return True

        except Exception as e:
            print(f"   ❌ Fallback test failed: {e}")
            return False

    def test_migration_functionality(self) -> bool:
        """Test JSON to TOML migration functionality"""
        print("\n🔀 Testing migration functionality...")

        try:
            # Start with clean state (only JSON)
            if Path("atlas_config.toml").exists():
                Path("atlas_config.toml").unlink()

            config_manager = AtlasConfig()

            # Test migration
            success = config_manager.migrate_to_toml(backup=True)

            if not success:
                print("   ❌ Migration failed")
                return False

            # Verify TOML was created
            if not Path("atlas_config.toml").exists():
                print("   ❌ TOML file not created")
                return False

            # Verify backup was created
            backup_dir = Path("config_backup")
            if not backup_dir.exists():
                print("   ❌ Backup directory not created")
                return False

            # Load and validate migrated config
            config = config_manager.load_config(prefer_toml=True)
            if not config_manager.validate_config(config):
                print("   ❌ Migrated config validation failed")
                return False

            print("   ✅ Migration successful")
            print("   ✅ Backup created")
            print("   ✅ Migrated config valid")
            return True

        except Exception as e:
            print(f"   ❌ Migration test failed: {e}")
            return False

    def test_pyproject_toml(self) -> bool:
        """Test pyproject.toml structure and dependencies"""
        print("\n📦 Testing pyproject.toml...")

        try:
            # Import TOML support
            try:
                import tomllib  # Python 3.11+
            except ImportError:
                import tomli as tomllib

            # Load pyproject.toml
            with open("../pyproject.toml", 'rb') as f:
                pyproject = tomllib.load(f)

            # Validate required sections
            if "project" not in pyproject:
                print("   ❌ Missing [project] section")
                return False

            if "build-system" not in pyproject:
                print("   ❌ Missing [build-system] section")
                return False

            # Check project metadata
            project = pyproject["project"]
            required_fields = ["name", "version", "description"]
            for field in required_fields:
                if field not in project:
                    print(f"   ❌ Missing project.{field}")
                    return False

            # Check dependencies
            if "dependencies" not in project:
                print("   ❌ Missing dependencies")
                return False

            dependencies = project["dependencies"]
            if not any("tomli" in dep for dep in dependencies):
                print("   ⚠️  tomli dependency missing (needed for Python <3.11)")

            print("   ✅ pyproject.toml structure valid")
            print(f"   ✅ Project name: {project['name']}")
            print(f"   ✅ Project version: {project['version']}")
            print(f"   ✅ Dependencies: {len(dependencies)} packages")
            return True

        except Exception as e:
            print(f"   ❌ pyproject.toml test failed: {e}")
            return False

    def test_existing_functionality(self) -> bool:
        """Test that existing Atlas functionality still works"""
        print("\n🧪 Testing existing functionality...")

        try:
            # Test relayq_service_setup.py can import our changes
            import sys
            sys.path.insert(0, "..")

            from relayq_service_setup import RelayQServiceSetup

            # Initialize setup class
            setup = RelayQServiceSetup()

            # Test that it can load configuration
            config_manager = setup.config_manager
            config = config_manager.load_config()

            # Test basic methods
            podcast_count = setup._get_podcast_count()
            episode_count = setup._get_episode_count()

            print("   ✅ relayq_service_setup.py imports work")
            print("   ✅ Configuration loading works")
            print("   ✅ Database methods work")
            return True

        except Exception as e:
            print(f"   ❌ Existing functionality test failed: {e}")
            return False

    def run_all_tests(self) -> bool:
        """Run all tests and return overall success"""
        print("🚀 Starting TOML Migration Test Suite")
        print("=" * 50)

        # Setup
        original_config = self.setup_test_environment()

        # Run tests
        tests = [
            ("TOML Loading", self.test_toml_loading),
            ("Fallback Mechanism", self.test_config_manager_fallback),
            ("Migration Functionality", self.test_migration_functionality),
            ("pyproject.toml", self.test_pyproject_toml),
            ("Existing Functionality", self.test_existing_functionality)
        ]

        results = []
        for test_name, test_func in tests:
            try:
                result = test_func()
                results.append((test_name, result))
            except Exception as e:
                print(f"   ❌ {test_name} crashed: {e}")
                results.append((test_name, False))

        # Results summary
        print("\n" + "=" * 50)
        print("📊 TEST RESULTS")
        print("=" * 50)

        passed = 0
        total = len(results)

        for test_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status:<8} {test_name}")
            if result:
                passed += 1

        print(f"\nOverall: {passed}/{total} tests passed")

        # Cleanup
        os.chdir(self.original_dir)
        shutil.rmtree(self.test_dir)

        return passed == total

if __name__ == "__main__":
    test = TOMLMigrationTest()
    success = test.run_all_tests()

    if success:
        print("\n🎉 ALL TESTS PASSED! TOML migration is working correctly.")
    else:
        print("\n💥 SOME TESTS FAILED! Please review the migration.")

    exit(0 if success else 1)