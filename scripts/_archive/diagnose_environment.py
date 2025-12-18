#!/usr/bin/env python3
"""
Atlas Environment Diagnostic Script

This script performs comprehensive environment diagnostics to identify
common setup and configuration issues. It's designed to help users
quickly diagnose problems and get specific guidance for resolution.

Usage:
    python scripts/diagnose_environment.py
    python scripts/diagnose_environment.py --fix-permissions
    python scripts/diagnose_environment.py --test-apis
    python scripts/diagnose_environment.py --full-report
"""

import argparse
import json
import os
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from helpers.config import load_config
    from helpers.validate import ConfigValidator

    CONFIG_AVAILABLE = True
except ImportError as e:
    CONFIG_AVAILABLE = False
    IMPORT_ERROR = str(e)


class EnvironmentDiagnostic:
    """Comprehensive environment diagnostic system."""

    def __init__(self):
        self.issues = []
        self.warnings = []
        self.info = []
        self.fixes = []

    def run_full_diagnostic(self, test_apis=False, fix_permissions=False):
        """Run complete diagnostic suite."""
        self.check_system_requirements()
        self.check_python_environment()
        self.check_project_structure()
        self.check_dependencies()
        self.check_configuration()
        self.check_permissions()

        if fix_permissions:
            self.fix_directory_permissions()

        if test_apis:
            self.test_api_connectivity()

        self.check_disk_space()
        self.check_network_connectivity()

    def check_system_requirements(self):
        """Check basic system requirements."""
        # Python version
        py_version = sys.version_info
        if py_version.major < 3 or (py_version.major == 3 and py_version.minor < 9):
            self.issues.append(
                {
                    "category": "system",
                    "issue": f"Python version {py_version.major}.{py_version.minor} is too old",
                    "guidance": "Atlas requires Python 3.9 or higher",
                    "fix": "Install Python 3.9+ from https://python.org",
                    "critical": True,
                }
            )
        else:
            self.info.append(
                f"✅ Python {py_version.major}.{py_version.minor}.{py_version.micro} meets requirements"
            )

        # Operating system
        os_info = platform.platform()
        self.info.append(f"📋 Operating System: {os_info}")

        # Architecture
        arch = platform.architecture()[0]
        self.info.append(f"🏗️  Architecture: {arch}")

    def check_python_environment(self):
        """Check Python environment and package manager."""
        # Check pip availability
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                self.info.append(f"✅ pip available: {result.stdout.strip()}")
            else:
                self.issues.append(
                    {
                        "category": "python",
                        "issue": "pip is not available",
                        "guidance": "pip is required for installing dependencies",
                        "fix": "Install pip or use python -m ensurepip",
                        "critical": True,
                    }
                )
        except (subprocess.SubprocessError, FileNotFoundError):
            self.issues.append(
                {
                    "category": "python",
                    "issue": "Cannot execute pip",
                    "guidance": "pip might not be installed or not in PATH",
                    "fix": "Install pip or check PATH configuration",
                    "critical": True,
                }
            )

        # Check virtual environment status
        if hasattr(sys, "real_prefix") or (
            hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
        ):
            self.info.append("🌐 Running in virtual environment (recommended)")
        else:
            self.warnings.append(
                {
                    "category": "python",
                    "issue": "Not running in virtual environment",
                    "guidance": "Consider using virtual environment to avoid conflicts",
                    "fix": "python3 -m venv atlas_env && source atlas_env/bin/activate",
                }
            )

    def check_project_structure(self):
        """Check essential project files and directories."""
        required_files = [
            "run.py",
            "requirements.txt",
            "helpers/config.py",
            ".env.example",
        ]

        required_dirs = ["helpers", "tests", "scripts", "docs"]

        project_root = Path.cwd()

        # Check files
        for file_path in required_files:
            full_path = project_root / file_path
            if full_path.exists():
                self.info.append(f"✅ Found required file: {file_path}")
            else:
                self.issues.append(
                    {
                        "category": "structure",
                        "issue": f"Missing required file: {file_path}",
                        "guidance": f"Atlas requires {file_path} to function properly",
                        "fix": f"Ensure you're in the Atlas project directory and {file_path} exists",
                        "critical": file_path in ["run.py", "helpers/config.py"],
                    }
                )

        # Check directories
        for dir_path in required_dirs:
            full_path = project_root / dir_path
            if full_path.exists() and full_path.is_dir():
                self.info.append(f"✅ Found required directory: {dir_path}")
            else:
                self.warnings.append(
                    {
                        "category": "structure",
                        "issue": f"Missing directory: {dir_path}",
                        "guidance": f"Some features may not work without {dir_path}",
                        "fix": f"mkdir -p {dir_path}",
                    }
                )

    def check_dependencies(self):
        """Check Python dependencies."""
        if not Path("requirements.txt").exists():
            self.issues.append(
                {
                    "category": "dependencies",
                    "issue": "requirements.txt not found",
                    "guidance": "Cannot verify dependencies without requirements.txt",
                    "fix": "Ensure you're in the Atlas project directory",
                    "critical": True,
                }
            )
            return

        # Read requirements
        try:
            with open("requirements.txt", "r") as f:
                for line in f:
                    if line.strip() and not line.startswith("#"):
                        pass
        except Exception as e:
            self.issues.append(
                {
                    "category": "dependencies",
                    "issue": f"Cannot read requirements.txt: {e}",
                    "guidance": "File may be corrupted or inaccessible",
                    "fix": "Check file permissions and content",
                    "critical": True,
                }
            )
            return

        # Check critical dependencies
        critical_packages = ["requests", "beautifulsoup4", "pyyaml", "python-dotenv"]

        for package in critical_packages:
            try:
                __import__(package.replace("-", "_"))
                self.info.append(f"✅ {package} is installed")
            except ImportError:
                self.issues.append(
                    {
                        "category": "dependencies",
                        "issue": f"Missing critical package: {package}",
                        "guidance": f"{package} is required for Atlas to function",
                        "fix": f"pip3 install {package}",
                        "critical": True,
                    }
                )

        # Check if we can import Atlas modules
        if not CONFIG_AVAILABLE:
            self.issues.append(
                {
                    "category": "dependencies",
                    "issue": f"Cannot import Atlas configuration: {IMPORT_ERROR}",
                    "guidance": "Atlas modules are not properly installed",
                    "fix": "pip3 install -r requirements.txt",
                    "critical": True,
                }
            )

    def check_configuration(self):
        """Check configuration files and validity."""
        config_dir = Path("config")
        env_file = config_dir / ".env"

        # Check config directory
        if not config_dir.exists():
            self.warnings.append(
                {
                    "category": "config",
                    "issue": "config directory does not exist",
                    "guidance": "Configuration files should be in config/",
                    "fix": "mkdir -p config",
                }
            )

        # Check .env file
        if not env_file.exists():
            self.issues.append(
                {
                    "category": "config",
                    "issue": ".env file not found in config/",
                    "guidance": "Configuration file is required for Atlas to work",
                    "fix": "cp .env.example config/.env",
                    "critical": True,
                }
            )
        else:
            self.info.append("✅ Configuration file found")

            # Validate configuration if possible
            if CONFIG_AVAILABLE:
                try:
                    config = load_config()
                    validator = ConfigValidator()
                    errors, warnings = validator.validate_config(config)

                    if errors:
                        for error in errors:
                            self.issues.append(
                                {
                                    "category": "config",
                                    "issue": f"Config error in {error.field}: {error.message}",
                                    "guidance": error.guidance,
                                    "fix": error.fix_command
                                    or "See configuration documentation",
                                    "critical": True,
                                }
                            )

                    if warnings:
                        for warning in warnings:
                            self.warnings.append(
                                {
                                    "category": "config",
                                    "issue": f"Config warning in {warning.field}: {warning.message}",
                                    "guidance": warning.guidance,
                                    "fix": warning.fix_command
                                    or "Consider optimization",
                                }
                            )

                    if not errors and not warnings:
                        self.info.append("✅ Configuration validation passed")

                except Exception as e:
                    self.issues.append(
                        {
                            "category": "config",
                            "issue": f"Configuration loading failed: {e}",
                            "guidance": "Configuration file may be corrupted",
                            "fix": "Check .env file format and content",
                            "critical": True,
                        }
                    )

    def check_permissions(self):
        """Check file and directory permissions."""
        # Check output directory
        data_dir = "output"  # Default

        if CONFIG_AVAILABLE:
            try:
                config = load_config()
                data_dir = config.get("data_directory", "output")
            except Exception:
                pass

        data_path = Path(data_dir)

        # Test directory creation
        try:
            data_path.mkdir(parents=True, exist_ok=True)
            self.info.append(f"✅ Data directory accessible: {data_dir}")
        except PermissionError:
            self.issues.append(
                {
                    "category": "permissions",
                    "issue": f"Cannot create data directory: {data_dir}",
                    "guidance": "Atlas needs write access to store processed content",
                    "fix": f"mkdir -p {data_dir} && chmod 755 {data_dir}",
                    "critical": True,
                }
            )
        except Exception as e:
            self.issues.append(
                {
                    "category": "permissions",
                    "issue": f"Data directory error: {e}",
                    "guidance": "Unexpected error with data directory",
                    "fix": f"Check path and permissions for {data_dir}",
                    "critical": True,
                }
            )

        # Test write permissions
        if data_path.exists():
            test_file = data_path / ".write_test"
            try:
                test_file.write_text("test")
                test_file.unlink()
                self.info.append("✅ Data directory is writable")
            except Exception:
                self.issues.append(
                    {
                        "category": "permissions",
                        "issue": f"Data directory is not writable: {data_dir}",
                        "guidance": "Atlas cannot save processed content",
                        "fix": f"chmod 755 {data_dir}",
                        "critical": True,
                    }
                )

        # Check subdirectories
        subdirs = ["articles", "podcasts", "youtube", "logs"]
        for subdir in subdirs:
            subdir_path = data_path / subdir
            try:
                subdir_path.mkdir(exist_ok=True)
                self.info.append(f"✅ Subdirectory accessible: {subdir}")
            except Exception:
                self.warnings.append(
                    {
                        "category": "permissions",
                        "issue": f"Cannot create subdirectory: {subdir}",
                        "guidance": f"May cause issues when processing {subdir} content",
                        "fix": f"mkdir -p {data_dir}/{subdir}",
                    }
                )

    def fix_directory_permissions(self):
        """Attempt to fix common directory permission issues."""
        data_dir = "output"

        if CONFIG_AVAILABLE:
            try:
                config = load_config()
                data_dir = config.get("data_directory", "output")
            except Exception:
                pass

        subdirs = ["articles", "podcasts", "youtube", "logs"]

        try:
            # Create main directory
            Path(data_dir).mkdir(parents=True, exist_ok=True)

            # Create subdirectories
            for subdir in subdirs:
                Path(data_dir, subdir).mkdir(exist_ok=True)

            # Set permissions (Unix-like systems only)
            if os.name != "nt":
                os.chmod(data_dir, 0o755)
                for subdir in subdirs:
                    subdir_path = Path(data_dir, subdir)
                    if subdir_path.exists():
                        os.chmod(subdir_path, 0o755)

            self.fixes.append(f"✅ Fixed directory permissions for {data_dir}")

        except Exception as e:
            self.issues.append(
                {
                    "category": "permissions",
                    "issue": f"Cannot fix permissions: {e}",
                    "guidance": "Manual intervention required",
                    "fix": f"Manually create and set permissions for {data_dir}",
                    "critical": False,
                }
            )

    def test_api_connectivity(self):
        """Test connectivity to external APIs."""
        apis = [
            ("OpenRouter", "https://openrouter.ai/api/v1/models"),
            ("DeepSeek", "https://api.deepseek.com/v1/models"),
            ("YouTube", "https://www.googleapis.com/youtube/v3/search"),
            ("Archive.today", "https://archive.today"),
        ]

        for name, url in apis:
            try:
                import requests

                response = requests.get(url, timeout=10)
                if response.status_code < 500:  # Any response is good enough
                    self.info.append(f"✅ {name} API accessible")
                else:
                    self.warnings.append(
                        {
                            "category": "network",
                            "issue": f"{name} API returned error {response.status_code}",
                            "guidance": f"{name} service may be temporarily unavailable",
                            "fix": "Try again later or check service status",
                        }
                    )
            except ImportError:
                self.warnings.append(
                    {
                        "category": "network",
                        "issue": "Cannot test API connectivity - requests module missing",
                        "guidance": "Install requests module to test API connectivity",
                        "fix": "pip3 install requests",
                    }
                )
                break
            except Exception as e:
                self.warnings.append(
                    {
                        "category": "network",
                        "issue": f"Cannot connect to {name}: {e}",
                        "guidance": f"Network issue or {name} service unavailable",
                        "fix": "Check internet connection and firewall settings",
                    }
                )

    def check_disk_space(self):
        """Check available disk space."""
        try:
            import shutil

            total, used, free = shutil.disk_usage(".")
            free_gb = free // (1024**3)

            if free_gb < 1:
                self.issues.append(
                    {
                        "category": "resources",
                        "issue": f"Low disk space: {free_gb}GB available",
                        "guidance": "Atlas needs space to store processed content",
                        "fix": "Free up disk space or choose different DATA_DIRECTORY",
                        "critical": True,
                    }
                )
            elif free_gb < 5:
                self.warnings.append(
                    {
                        "category": "resources",
                        "issue": f"Limited disk space: {free_gb}GB available",
                        "guidance": "Consider freeing up space for long-term use",
                        "fix": "Monitor disk usage regularly",
                    }
                )
            else:
                self.info.append(f"✅ Adequate disk space: {free_gb}GB available")

        except Exception as e:
            self.warnings.append(
                {
                    "category": "resources",
                    "issue": f"Cannot check disk space: {e}",
                    "guidance": "Monitor disk space manually",
                    "fix": "Use system tools to check disk usage",
                }
            )

    def check_network_connectivity(self):
        """Check basic network connectivity."""
        test_hosts = ["google.com", "github.com"]

        for host in test_hosts:
            try:
                import socket

                socket.create_connection((host, 80), timeout=5)
                self.info.append(f"✅ Network connectivity to {host}")
                break
            except ImportError:
                self.warnings.append(
                    {
                        "category": "network",
                        "issue": "Cannot test network connectivity - socket module issue",
                        "guidance": "Check network connectivity manually",
                        "fix": "ping google.com",
                    }
                )
                break
            except Exception:
                continue
        else:
            self.issues.append(
                {
                    "category": "network",
                    "issue": "No network connectivity detected",
                    "guidance": "Atlas needs internet access for external services",
                    "fix": "Check internet connection and proxy settings",
                    "critical": True,
                }
            )

    def generate_report(self, include_fixes=False):
        """Generate comprehensive diagnostic report."""
        report = []
        report.append("=" * 60)
        report.append("Atlas Environment Diagnostic Report")
        report.append("=" * 60)
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append(f"Python: {sys.version}")
        report.append(f"Platform: {platform.platform()}")
        report.append("")

        # Critical issues
        critical_issues = [
            issue for issue in self.issues if issue.get("critical", False)
        ]
        if critical_issues:
            report.append("🚨 CRITICAL ISSUES (Must Fix)")
            report.append("-" * 40)
            for issue in critical_issues:
                report.append(f"❌ {issue['issue']}")
                report.append(f"   💡 {issue['guidance']}")
                report.append(f"   🔨 {issue['fix']}")
                report.append("")

        # Other issues
        other_issues = [
            issue for issue in self.issues if not issue.get("critical", False)
        ]
        if other_issues:
            report.append("⚠️  OTHER ISSUES")
            report.append("-" * 40)
            for issue in other_issues:
                report.append(f"❌ {issue['issue']}")
                report.append(f"   💡 {issue['guidance']}")
                report.append(f"   🔨 {issue['fix']}")
                report.append("")

        # Warnings
        if self.warnings:
            report.append("⚠️  WARNINGS")
            report.append("-" * 40)
            for warning in self.warnings:
                report.append(f"⚠️  {warning['issue']}")
                report.append(f"   💡 {warning['guidance']}")
                report.append(f"   🔨 {warning['fix']}")
                report.append("")

        # Fixes applied
        if include_fixes and self.fixes:
            report.append("🔧 APPLIED FIXES")
            report.append("-" * 40)
            for fix in self.fixes:
                report.append(fix)
            report.append("")

        # Success information
        if self.info:
            report.append("✅ SYSTEM STATUS")
            report.append("-" * 40)
            for info in self.info:
                report.append(info)
            report.append("")

        # Summary
        report.append("📊 SUMMARY")
        report.append("-" * 40)
        report.append(f"Critical Issues: {len(critical_issues)}")
        report.append(f"Other Issues: {len(other_issues)}")
        report.append(f"Warnings: {len(self.warnings)}")
        report.append(f"Applied Fixes: {len(self.fixes)}")

        if critical_issues:
            report.append(
                "\n🚨 Atlas will not work until critical issues are resolved."
            )
        elif other_issues:
            report.append(
                "\n⚠️  Atlas may have limited functionality until issues are resolved."
            )
        else:
            report.append("\n🎉 Environment appears ready for Atlas!")

        report.append("=" * 60)

        return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(description="Diagnose Atlas environment issues")
    parser.add_argument(
        "--fix-permissions",
        action="store_true",
        help="Attempt to fix directory permission issues",
    )
    parser.add_argument(
        "--test-apis", action="store_true", help="Test connectivity to external APIs"
    )
    parser.add_argument(
        "--full-report", action="store_true", help="Generate comprehensive report"
    )
    parser.add_argument(
        "--json", action="store_true", help="Output results in JSON format"
    )

    args = parser.parse_args()

    diagnostic = EnvironmentDiagnostic()
    diagnostic.run_full_diagnostic(
        test_apis=args.test_apis, fix_permissions=args.fix_permissions
    )

    if args.json:
        # JSON output for automation
        result = {
            "timestamp": datetime.now().isoformat(),
            "critical_issues": len(
                [i for i in diagnostic.issues if i.get("critical", False)]
            ),
            "total_issues": len(diagnostic.issues),
            "warnings": len(diagnostic.warnings),
            "fixes_applied": len(diagnostic.fixes),
            "issues": diagnostic.issues,
            "fixes": diagnostic.fixes,
            "info": diagnostic.info,
        }
        print(json.dumps(result, indent=2))
    else:
        # Human-readable report
        report = diagnostic.generate_report(include_fixes=args.fix_permissions)
        print(report)

    # Exit with appropriate code
    critical_issues = len([i for i in diagnostic.issues if i.get("critical", False)])
    if critical_issues > 0:
        sys.exit(2)  # Critical issues
    elif len(diagnostic.issues) > 0:
        sys.exit(1)  # Non-critical issues
    else:
        sys.exit(0)  # All good


if __name__ == "__main__":
    main()
