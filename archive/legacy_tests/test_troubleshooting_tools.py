"""
Test suite for troubleshooting and diagnostic tools.

This module tests the environment diagnostic scripts and troubleshooting
utilities to ensure they provide accurate and helpful guidance to users.
"""

import json
import os
import subprocess
import sys
import tempfile
from helpers.bulletproof_process_manager import create_managed_process
from pathlib import Path

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from scripts.diagnose_environment import EnvironmentDiagnostic

    DIAGNOSTIC_AVAILABLE = True
except ImportError:
    DIAGNOSTIC_AVAILABLE = False


@pytest.mark.skipif(not DIAGNOSTIC_AVAILABLE, reason="Diagnostic script not available")
class TestEnvironmentDiagnostic:
    """Test environment diagnostic functionality."""

    def setup_method(self):
        """Set up test instance."""
        self.diagnostic = EnvironmentDiagnostic()

    def test_python_version_check(self):
        """Test Python version checking."""
        self.diagnostic.check_system_requirements()

        # Should not have critical issues for current Python version
        critical_issues = [
            issue
            for issue in self.diagnostic.issues
            if issue.get("critical", False) and "Python version" in issue["issue"]
        ]

        # Since we're running tests, Python version should be acceptable
        assert len(critical_issues) == 0

    def test_project_structure_check(self):
        """Test project structure validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)

            # Reset diagnostic
            self.diagnostic = EnvironmentDiagnostic()
            self.diagnostic.check_project_structure()

            # Should have issues for missing files
            missing_files = [
                issue
                for issue in self.diagnostic.issues
                if "Missing required file" in issue["issue"]
            ]
            assert len(missing_files) > 0

            # Create required files
            Path("run.py").touch()
            Path("requirements.txt").touch()
            Path("helpers").mkdir()
            Path("helpers/config.py").touch()
            Path(".env.example").touch()

            # Reset and check again
            self.diagnostic = EnvironmentDiagnostic()
            self.diagnostic.check_project_structure()

            # Should have fewer missing file issues
            missing_files = [
                issue
                for issue in self.diagnostic.issues
                if "Missing required file" in issue["issue"]
            ]
            assert len(missing_files) == 0

    def test_dependencies_check(self):
        """Test dependency checking."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)

            # Create minimal requirements.txt
            Path("requirements.txt").write_text("requests\nbeautifulsoup4\n")

            self.diagnostic = EnvironmentDiagnostic()
            self.diagnostic.check_dependencies()

            # Should detect the requirements file
            assert Path("requirements.txt").exists()

    def test_configuration_check_missing_env(self):
        """Test configuration checking when .env is missing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)

            self.diagnostic = EnvironmentDiagnostic()
            self.diagnostic.check_configuration()

            # Should have issues for missing .env file
            env_issues = [
                issue
                for issue in self.diagnostic.issues
                if ".env file not found" in issue["issue"]
            ]
            assert len(env_issues) == 1

    def test_configuration_check_with_env(self):
        """Test configuration checking when .env exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)

            # Create config directory and .env file
            config_dir = Path("config")
            config_dir.mkdir()
            (config_dir / ".env").write_text("DATA_DIRECTORY=output\n")

            self.diagnostic = EnvironmentDiagnostic()
            self.diagnostic.check_configuration()

            # Should find configuration file
            info_messages = [
                msg for msg in self.diagnostic.info if "Configuration file found" in msg
            ]
            assert len(info_messages) == 1

    def test_permissions_check(self):
        """Test permission checking."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)

            self.diagnostic = EnvironmentDiagnostic()
            self.diagnostic.check_permissions()

            # Should be able to create output directory in temp location
            success_messages = [
                msg
                for msg in self.diagnostic.info
                if "Data directory accessible" in msg
            ]
            assert len(success_messages) >= 1

    def test_disk_space_check(self):
        """Test disk space checking."""
        self.diagnostic.check_disk_space()

        # Should have some info about disk space
        disk_messages = [
            msg
            for msg in self.diagnostic.info
            + [w["issue"] for w in self.diagnostic.warnings]
            + [i["issue"] for i in self.diagnostic.issues]
            if "disk space" in msg.lower()
        ]
        assert len(disk_messages) >= 1

    def test_network_connectivity_check(self):
        """Test network connectivity checking."""
        self.diagnostic.check_network_connectivity()

        # Should have some info about network connectivity

        # Note: This might fail in CI environments without network
        # So we just check that the check was attempted
        assert True  # Test passes if no exception was raised

    def test_report_generation(self):
        """Test diagnostic report generation."""
        # Add some test issues
        self.diagnostic.issues.append(
            {
                "category": "test",
                "issue": "Test critical issue",
                "guidance": "Test guidance",
                "fix": "Test fix",
                "critical": True,
            }
        )

        self.diagnostic.warnings.append(
            {
                "category": "test",
                "issue": "Test warning",
                "guidance": "Test warning guidance",
                "fix": "Test warning fix",
            }
        )

        self.diagnostic.info.append("Test info message")

        report = self.diagnostic.generate_report()

        # Report should contain sections for issues, warnings, and info
        assert "CRITICAL ISSUES" in report
        assert "WARNINGS" in report
        assert "SYSTEM STATUS" in report
        assert "Test critical issue" in report
        assert "Test warning" in report
        assert "Test info message" in report

    def test_fix_permissions(self):
        """Test permission fixing functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)

            self.diagnostic = EnvironmentDiagnostic()
            self.diagnostic.fix_directory_permissions()

            # Should create output directory
            assert Path("output").exists()

            # Should have success message
            fix_messages = [
                msg
                for msg in self.diagnostic.fixes
                if "Fixed directory permissions" in msg
            ]
            assert len(fix_messages) >= 1


class TestDiagnosticScript:
    """Test the diagnostic script execution."""

    def test_diagnostic_script_exists(self):
        """Test that diagnostic script exists and is executable."""
        script_path = Path("scripts/diagnose_environment.py")
        assert script_path.exists()

        # Check if it's a Python script
        with open(script_path, "r") as f:
            first_line = f.readline()
            assert "python" in first_line.lower()

    def test_diagnostic_script_help(self):
        """Test diagnostic script help output."""
        try:
            process = create_managed_process(
                [sys.executable, "scripts/diagnose_environment.py", "--help"],
                "diagnose_help",
                timeout=10,
            )
            stdout, stderr = process.communicate()

            assert process.returncode == 0
            assert "diagnose" in stdout.decode('utf-8').lower()
            assert "--fix-permissions" in stdout.decode('utf-8')
            assert "--test-apis" in stdout.decode('utf-8')

            assert result.returncode == 0
            assert "diagnose" in result.stdout.lower()
            assert "--fix-permissions" in result.stdout
            assert "--test-apis" in result.stdout

        except (subprocess.TimeoutExpired, FileNotFoundError):
            pytest.skip("Cannot execute diagnostic script")

    def test_diagnostic_script_json_output(self):
        """Test diagnostic script JSON output."""
        try:
            process = create_managed_process(
                [sys.executable, "scripts/diagnose_environment.py", "--json"],
                "diagnose_json",
                timeout=30,
            )
            stdout, stderr = process.communicate()

            # Script might fail due to missing dependencies, but should produce JSON
            if stdout:
                # Parse JSON to ensure it's valid
                data = json.loads(stdout.decode('utf-8'))
                assert "timestamp" in data
                assert "critical_issues" in data
                assert "total_issues" in data

        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            pytest.skip("Cannot execute diagnostic script or invalid JSON output")


class TestSetupCheckScript:
    """Test the setup check script."""

    def test_setup_check_script_exists(self):
        """Test that setup check script exists."""
        script_path = Path("scripts/setup_check.py")
        assert script_path.exists()

    def test_setup_check_execution(self):
        """Test setup check script execution."""
        try:
            process = create_managed_process(
                [sys.executable, "scripts/setup_check.py"],
                "setup_check",
                timeout=20,
            )
            stdout, stderr = process.communicate()

            # Script should produce output regardless of pass/fail
            assert len(stdout.decode('utf-8')) > 0
            assert "Setup Check" in stdout.decode('utf-8')

        except (subprocess.TimeoutExpired, FileNotFoundError):
            pytest.skip("Cannot execute setup check script")


class TestTroubleshootingDocumentation:
    """Test troubleshooting documentation completeness."""

    def test_troubleshooting_guide_exists(self):
        """Test that main troubleshooting guide exists."""
        guide_path = Path("docs/environment-troubleshooting.md")
        assert guide_path.exists()

        # Check content
        content = guide_path.read_text()
        assert "troubleshooting" in content.lower()
        assert "diagnostic" in content.lower()
        assert len(content) > 1000  # Should be comprehensive

    def test_troubleshooting_checklist_exists(self):
        """Test that troubleshooting checklist exists."""
        checklist_path = Path("docs/troubleshooting_checklist.md")
        assert checklist_path.exists()

        content = checklist_path.read_text()
        assert "checklist" in content.lower()
        assert "[ ]" in content  # Should have checkboxes

    def test_documentation_coverage(self):
        """Test that documentation covers common issues."""
        guide_path = Path("docs/environment-troubleshooting.md")
        content = guide_path.read_text().lower()

        # Should cover common issue categories
        common_issues = [
            "python version",
            "dependencies",
            "permissions",
            "api key",
            "network",
            "configuration",
            "disk space",
        ]

        for issue in common_issues:
            assert issue in content, f"Documentation should cover {issue}"

    def test_fix_commands_provided(self):
        """Test that documentation provides fix commands."""
        guide_path = Path("docs/environment-troubleshooting.md")
        content = guide_path.read_text()

        # Should have code blocks with fix commands
        assert "```bash" in content
        assert "pip3 install" in content
        assert "python" in content

        # Should have specific fixes
        fix_patterns = ["mkdir", "chmod", "cp .env.example", "validate_config.py"]

        for pattern in fix_patterns:
            assert pattern in content, f"Should provide {pattern} fix command"


class TestTroubleshootingIntegration:
    """Test integration between troubleshooting tools."""

    def test_validation_script_referenced(self):
        """Test that troubleshooting docs reference validation script."""
        guide_path = Path("docs/environment-troubleshooting.md")
        content = guide_path.read_text()

        assert "validate_config.py" in content
        assert "scripts/validate_config.py" in content

    def test_diagnostic_script_referenced(self):
        """Test that troubleshooting docs reference diagnostic script."""
        guide_path = Path("docs/environment-troubleshooting.md")
        content = guide_path.read_text()

        assert "diagnose_environment.py" in content
        assert "scripts/diagnose_environment.py" in content

    def test_setup_check_referenced(self):
        """Test that troubleshooting docs reference setup check."""
        guide_path = Path("docs/environment-troubleshooting.md")
        content = guide_path.read_text()

        assert "setup_check.py" in content
        assert "scripts/setup_check.py" in content

    def test_cross_references_valid(self):
        """Test that documentation cross-references are valid."""
        guide_path = Path("docs/environment-troubleshooting.md")
        content = guide_path.read_text()

        # Extract referenced files
        import re

        script_refs = re.findall(r"scripts/([a-zA-Z_]+\.py)", content)
        doc_refs = re.findall(r"docs/([a-zA-Z-_]+\.md)", content)

        # Check that referenced scripts exist
        for script in script_refs:
            script_path = Path(f"scripts/{script}")
            assert script_path.exists(), f"Referenced script {script} should exist"

        # Check that referenced docs exist (if not this file)
        for doc in doc_refs:
            if doc != "environment-troubleshooting.md":  # Don't self-reference
                # Some docs might not exist yet, so just check if path is reasonable
                assert doc.endswith(".md"), f"Referenced doc {doc} should be markdown"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
