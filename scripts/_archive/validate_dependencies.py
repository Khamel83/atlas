#!/usr/bin/env python3
"""
Dependency validation script for Atlas.

This script validates that all required dependencies are installed and properly
configured, providing helpful error messages and suggestions for resolution.

Usage:
    python scripts/validate_dependencies.py [--fix] [--verbose] [--json]

Options:
    --fix: Attempt to fix common dependency issues automatically
    --verbose: Show detailed validation information
    --json: Output results in JSON format
"""

import argparse
import importlib
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict


class PythonVersionResult(TypedDict):
    status: str
    details: Dict[str, Any]


class PackagesResult(TypedDict):
    status: str
    details: Dict[str, Any]


class SystemDependenciesResult(TypedDict):
    status: str
    details: Dict[str, Any]


class ConfigurationResult(TypedDict):
    status: str
    details: Dict[str, Any]


class DirectoriesResult(TypedDict):
    status: str
    details: Dict[str, Any]


class PermissionsResult(TypedDict):
    status: str
    details: Dict[str, Any]


class OverallResult(TypedDict):
    status: str
    issues: List[Dict[str, Any]]
    suggestions: List[str]
    failed_categories: List[str]
    total_issues: int


class ValidationResults(TypedDict):
    python_version: PythonVersionResult
    required_packages: PackagesResult
    optional_packages: PackagesResult
    system_dependencies: SystemDependenciesResult
    configuration: ConfigurationResult
    directories: DirectoriesResult
    permissions: PermissionsResult
    overall: OverallResult


class DependencyValidator:
    """Validates Atlas dependencies with helpful error messages."""

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.results: ValidationResults = {
            "python_version": {"status": "unknown", "details": {}},
            "required_packages": {"status": "unknown", "details": {}},
            "optional_packages": {"status": "unknown", "details": {}},
            "system_dependencies": {"status": "unknown", "details": {}},
            "configuration": {"status": "unknown", "details": {}},
            "directories": {"status": "unknown", "details": {}},
            "permissions": {"status": "unknown", "details": {}},
            "overall": {"status": "unknown", "issues": [], "suggestions": [], "failed_categories": [], "total_issues": 0},
        }

        # Required Python packages from requirements.txt
        # Format: (package_name, import_name)
        self.required_packages = [
            ("fastapi", "fastapi"),
            ("uvicorn", "uvicorn"),
            ("requests", "requests"),
            ("beautifulsoup4", "bs4"),
            ("pydantic", "pydantic"),
            ("python-dotenv", "dotenv"),
            ("pyyaml", "yaml"),
            ("feedparser", "feedparser"),
            ("apscheduler", "apscheduler"),
        ]

        # Optional packages that enhance functionality
        self.optional_packages = [
            "pytest",
            "black",
            "isort",
            "mypy",
            "playwright",
            "redis",
            "openai",
        ]

        # System dependencies
        self.system_dependencies = [
            {"name": "git", "command": "git --version", "required": True},
            {"name": "curl", "command": "curl --version", "required": False},
            {
                "name": "redis-server",
                "command": "redis-server --version",
                "required": False,
            },
        ]

    def validate_all(
        self, fix_issues: bool = False, verbose: bool = False
    ) -> Dict[str, Any]:
        """
        Run complete dependency validation.

        Args:
            fix_issues: Attempt to fix common issues automatically
            verbose: Include detailed validation information

        Returns:
            Dict containing validation results
        """

        if verbose:
            print("🔍 Starting Atlas dependency validation...")
            print(f"📁 Project root: {self.project_root}")
            print(f"🐍 Python: {sys.version}")
            print(f"💻 Platform: {platform.system()} {platform.release()}")
            print()

        # Validate Python version
        self._validate_python_version(verbose)

        # Validate required packages
        self._validate_required_packages(fix_issues, verbose)

        # Validate optional packages
        self._validate_optional_packages(verbose)

        # Validate system dependencies
        self._validate_system_dependencies(verbose)

        # Validate configuration
        self._validate_configuration(fix_issues, verbose)

        # Validate directories
        self._validate_directories(fix_issues, verbose)

        # Validate permissions
        self._validate_permissions(fix_issues, verbose)

        # Generate overall assessment
        self._generate_overall_assessment(verbose)

        return self.results

    def _validate_python_version(self, verbose: bool):
        """Validate Python version meets requirements."""
        if verbose:
            print("🐍 Checking Python version...")

        try:
            version = sys.version_info
            required_major = 3
            required_minor = 9

            if version.major >= required_major and version.minor >= required_minor:
                self.results["python_version"] = {
                    "status": "pass",
                    "details": {
                        "version": f"{version.major}.{version.minor}.{version.micro}",
                        "required": f"{required_major}.{required_minor}+",
                        "location": sys.executable,
                    },
                }
                if verbose:
                    print(f"  ✓ Python {version.major}.{version.minor}.{version.micro}")
            else:
                self.results["python_version"] = {
                    "status": "fail",
                    "details": {
                        "version": f"{version.major}.{version.minor}.{version.micro}",
                        "required": f"{required_major}.{required_minor}+",
                        "location": sys.executable,
                        "error": f"Python {required_major}.{required_minor}+ required, found {version.major}.{version.minor}",
                        "suggestion": f"Install Python {required_major}.{required_minor}+ from https://python.org",
                    },
                }
                if verbose:
                    print(
                        f"  ❌ Python {version.major}.{version.minor}.{version.micro} (need {required_major}.{required_minor}+)"
                    )

        except Exception as e:
            self.results["python_version"] = {
                "status": "error",
                "details": {"error": str(e)},
            }

    def _validate_required_packages(self, fix_issues: bool, verbose: bool):
        """Validate required Python packages are installed."""
        if verbose:
            print("\n📦 Checking required packages...")

        missing_packages = []
        installed_packages = {}
        package_errors = {}

        for package_info in self.required_packages:
            if isinstance(package_info, tuple):
                package_name, import_name = package_info
            else:
                package_name = import_name = package_info

            try:
                module = importlib.import_module(import_name.replace("-", "_"))
                version = getattr(module, "__version__", "unknown")
                installed_packages[package_name] = version
                if verbose:
                    print(f"  ✓ {package_name} ({version})")
            except ImportError as e:
                missing_packages.append(package_name)
                package_errors[package_name] = str(e)
                if verbose:
                    print(f"  ❌ {package_name} (not installed)")

        if missing_packages:
            if fix_issues:
                if verbose:
                    print("\n🔧 Attempting to install missing packages...")
                self._install_packages(missing_packages, verbose)
                # Re-validate after installation attempt
                remaining_missing = []
                for package_name in missing_packages:
                    # Find the import name for this package
                    import_name = package_name
                    for pkg_info in self.required_packages:
                        if isinstance(pkg_info, tuple) and pkg_info[0] == package_name:
                            import_name = pkg_info[1]
                            break

                    if not self._is_package_installed_by_import(import_name):
                        remaining_missing.append(package_name)

                missing_packages = remaining_missing

        self.results["required_packages"] = {
            "status": "pass" if not missing_packages else "fail",
            "details": {
                "installed": installed_packages,
                "missing": missing_packages,
                "errors": package_errors,
                "total_required": len(self.required_packages),
                "total_installed": len(installed_packages),
            },
        }

        if missing_packages:
            self.results["required_packages"]["details"][
                "suggestion"
            ] = f"Install missing packages: pip install {' '.join(missing_packages)}"

    def _validate_optional_packages(self, verbose: bool):
        """Validate optional packages for enhanced functionality."""
        if verbose:
            print("\n🔧 Checking optional packages...")

        installed_packages = {}
        missing_packages = []

        for package in self.optional_packages:
            try:
                module = importlib.import_module(package.replace("-", "_"))
                version = getattr(module, "__version__", "unknown")
                installed_packages[package] = version
                if verbose:
                    print(f"  ✓ {package} ({version})")
            except ImportError:
                missing_packages.append(package)
                if verbose:
                    print(f"  - {package} (optional, not installed)")

        self.results["optional_packages"] = {
            "status": "pass",  # Optional packages don't cause failure
            "details": {
                "installed": installed_packages,
                "missing": missing_packages,
                "total_optional": len(self.optional_packages),
                "total_installed": len(installed_packages),
            },
        }

        if missing_packages:
            self.results["optional_packages"]["details"][
                "suggestion"
            ] = f"For enhanced functionality: pip install {' '.join(missing_packages)}"

    def _validate_system_dependencies(self, verbose: bool):
        """Validate system-level dependencies."""
        if verbose:
            print("\n🖥️  Checking system dependencies...")

        available_deps = {}
        missing_deps = []

        for dep in self.system_dependencies:
            name = dep["name"]
            command = dep["command"]
            required = dep["required"]

            try:
                result = subprocess.run(
                    command.split(), capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    # Extract version from output
                    version_line = result.stdout.split("\n")[0]
                    available_deps[name] = version_line
                    if verbose:
                        status = "✓" if required else "+"
                        print(f"  {status} {name} ({version_line})")
                else:
                    missing_deps.append({"name": name, "required": required})
                    if verbose:
                        status = "❌" if required else "-"
                        print(f"  {status} {name} (not available)")

            except (subprocess.TimeoutExpired, FileNotFoundError):
                missing_deps.append({"name": name, "required": required})
                if verbose:
                    status = "❌" if required else "-"
                    print(f"  {status} {name} (not found)")

        required_missing = [dep for dep in missing_deps if dep["required"]]

        self.results["system_dependencies"] = {
            "status": "pass" if not required_missing else "fail",
            "details": {
                "available": available_deps,
                "missing": missing_deps,
                "required_missing": required_missing,
            },
        }

    def _validate_configuration(self, fix_issues: bool, verbose: bool):
        """Validate configuration files and settings."""
        if verbose:
            print("\n⚙️  Checking configuration...")

        config_issues = []
        config_status = {}

        # Check for .env file
        env_path = self.project_root / ".env"
        if env_path.exists():
            config_status["env_file"] = "exists"
            if verbose:
                print("  ✓ .env file exists")

            # Check .env file permissions
            if oct(env_path.stat().st_mode)[-3:] != "600":
                config_issues.append(
                    {
                        "type": "permissions",
                        "file": ".env",
                        "issue": "File permissions too permissive",
                        "suggestion": "Run: chmod 600 .env",
                    }
                )
                if verbose:
                    print("  ⚠ .env file permissions should be 600")

                if fix_issues:
                    try:
                        os.chmod(env_path, 0o600)
                        if verbose:
                            print("    🔧 Fixed .env permissions")
                    except Exception as e:
                        config_issues.append(
                            {
                                "type": "permissions",
                                "file": ".env",
                                "issue": f"Failed to fix permissions: {e}",
                                "suggestion": "Manually run: chmod 600 .env",
                            }
                        )
        else:
            config_issues.append(
                {
                    "type": "missing_file",
                    "file": ".env",
                    "issue": ".env file not found",
                    "suggestion": "Run: python scripts/generate_env.py",
                }
            )
            config_status["env_file"] = "missing"
            if verbose:
                print("  ❌ .env file missing")

        # Check for requirements.txt
        req_path = self.project_root / "requirements.txt"
        if req_path.exists():
            config_status["requirements_file"] = "exists"
            if verbose:
                print("  ✓ requirements.txt exists")
        else:
            config_issues.append(
                {
                    "type": "missing_file",
                    "file": "requirements.txt",
                    "issue": "requirements.txt file not found",
                    "suggestion": "Restore requirements.txt from repository",
                }
            )
            config_status["requirements_file"] = "missing"

        # Try to load configuration
        try:
            sys.path.insert(0, str(self.project_root))
            from helpers.config import load_config

            load_config()
            config_status["config_loading"] = "success"
            if verbose:
                print("  ✓ Configuration loads successfully")
        except Exception as e:
            config_issues.append(
                {
                    "type": "config_error",
                    "file": "helpers/config.py",
                    "issue": f"Configuration loading failed: {e}",
                    "suggestion": "Check configuration files and fix syntax errors",
                }
            )
            config_status["config_loading"] = "error"
            if verbose:
                print(f"  ❌ Configuration loading failed: {e}")

        self.results["configuration"] = {
            "status": "pass" if not config_issues else "fail",
            "details": {"status": config_status, "issues": config_issues},
        }

    def _validate_directories(self, fix_issues: bool, verbose: bool):
        """Validate required directories exist."""
        if verbose:
            print("\n📂 Checking directories...")

        required_dirs = [
            "output",
            "output/articles",
            "output/youtube",
            "output/podcasts",
            "config",
            "logs",
            "tests",
        ]

        dir_status = {}
        dir_issues = []

        for dir_name in required_dirs:
            dir_path = self.project_root / dir_name

            if dir_path.exists():
                if dir_path.is_dir():
                    dir_status[dir_name] = "exists"
                    if verbose:
                        print(f"  ✓ {dir_name}/")
                else:
                    dir_issues.append(
                        {
                            "type": "not_directory",
                            "path": dir_name,
                            "issue": f"{dir_name} exists but is not a directory",
                            "suggestion": f"Remove file and create directory: rm {dir_name} && mkdir -p {dir_name}",
                        }
                    )
                    dir_status[dir_name] = "blocked"
            else:
                dir_issues.append(
                    {
                        "type": "missing_directory",
                        "path": dir_name,
                        "issue": f"Directory {dir_name} does not exist",
                        "suggestion": f"Create directory: mkdir -p {dir_name}",
                    }
                )
                dir_status[dir_name] = "missing"
                if verbose:
                    print(f"  ❌ {dir_name}/ (missing)")

                if fix_issues:
                    try:
                        dir_path.mkdir(parents=True, exist_ok=True)
                        dir_status[dir_name] = "created"
                        if verbose:
                            print(f"    🔧 Created {dir_name}/")
                    except Exception as e:
                        dir_issues.append(
                            {
                                "type": "creation_error",
                                "path": dir_name,
                                "issue": f"Failed to create {dir_name}: {e}",
                                "suggestion": f"Manually create: mkdir -p {dir_name}",
                            }
                        )

        self.results["directories"] = {
            "status": "pass" if not dir_issues else "fail",
            "details": {
                "status": dir_status,
                "issues": dir_issues,
                "required": required_dirs,
            },
        }

    def _validate_permissions(self, fix_issues: bool, verbose: bool):
        """Validate file and directory permissions."""
        if verbose:
            print("\n🔒 Checking permissions...")

        permission_issues = []
        permission_status = {}

        # Check that we can write to key directories
        writable_dirs = ["output", "logs", "config"]

        for dir_name in writable_dirs:
            dir_path = self.project_root / dir_name

            if dir_path.exists():
                if os.access(dir_path, os.W_OK):
                    permission_status[dir_name] = "writable"
                    if verbose:
                        print(f"  ✓ {dir_name}/ (writable)")
                else:
                    permission_issues.append(
                        {
                            "type": "not_writable",
                            "path": dir_name,
                            "issue": f"Cannot write to {dir_name} directory",
                            "suggestion": f"Fix permissions: chmod u+w {dir_name}",
                        }
                    )
                    permission_status[dir_name] = "not_writable"
                    if verbose:
                        print(f"  ❌ {dir_name}/ (not writable)")
            else:
                permission_status[dir_name] = "missing"

        # Check script executability
        script_files = ["scripts/generate_env.py"]

        for script in script_files:
            script_path = self.project_root / script

            if script_path.exists():
                if os.access(script_path, os.X_OK):
                    permission_status[script] = "executable"
                    if verbose:
                        print(f"  ✓ {script} (executable)")
                else:
                    permission_issues.append(
                        {
                            "type": "not_executable",
                            "path": script,
                            "issue": f"Script {script} is not executable",
                            "suggestion": f"Make executable: chmod +x {script}",
                        }
                    )
                    permission_status[script] = "not_executable"

                    if fix_issues:
                        try:
                            os.chmod(script_path, 0o755)
                            permission_status[script] = "fixed"
                            if verbose:
                                print(f"    🔧 Made {script} executable")
                        except Exception as e:
                            permission_issues.append(
                                {
                                    "type": "chmod_error",
                                    "path": script,
                                    "issue": f"Failed to make executable: {e}",
                                    "suggestion": f"Manually run: chmod +x {script}",
                                }
                            )

        self.results["permissions"] = {
            "status": "pass" if not permission_issues else "fail",
            "details": {"status": permission_status, "issues": permission_issues},
        }

    def _generate_overall_assessment(self, verbose: bool):
        """Generate overall validation assessment."""
        if verbose:
            print("\n📊 Overall Assessment...")

        issues = []
        suggestions = []

        # Collect issues from all validation categories
        for category, result in self.results.items():
            if category == "overall":
                continue

            if result["status"] == "fail":
                category_issues = result["details"].get("issues", [])
                issues.extend(category_issues)

                # Add suggestions
                if "suggestion" in result["details"]:
                    suggestions.append(result["details"]["suggestion"])

        # Determine overall status
        failed_categories = [
            category
            for category, result in self.results.items()
            if category != "overall" and result["status"] == "fail"
        ]

        if failed_categories:
            overall_status = "fail"
        else:
            overall_status = "pass"

        self.results["overall"] = {
            "status": overall_status,
            "issues": issues,
            "suggestions": suggestions,
            "failed_categories": failed_categories,
            "total_issues": len(issues),
        }

        if verbose:
            if overall_status == "pass":
                print("  ✅ All dependencies validated successfully!")
            else:
                print(
                    f"  ❌ {len(issues)} issues found in {len(failed_categories)} categories"
                )

    def _install_packages(self, packages: List[str], verbose: bool):
        """Attempt to install missing packages."""
        try:
            cmd = [sys.executable, "-m", "pip", "install"] + packages
            if verbose:
                print(f"    Running: {' '.join(cmd)}")

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                if verbose:
                    print("    ✓ Installation completed")
            else:
                if verbose:
                    print(f"    ❌ Installation failed: {result.stderr}")
        except Exception as e:
            if verbose:
                print(f"    ❌ Installation error: {e}")

    def _is_package_installed(self, package: str) -> bool:
        """Check if a package is installed."""
        try:
            importlib.import_module(package.replace("-", "_"))
            return True
        except ImportError:
            return False

    def _is_package_installed_by_import(self, import_name: str) -> bool:
        """Check if a package is installed by its import name."""
        try:
            importlib.import_module(import_name.replace("-", "_"))
            return True
        except ImportError:
            return False

    def print_results(self, verbose: bool = False):
        """Print human-readable validation results."""
        overall = self.results["overall"]

        if overall["status"] == "pass":
            print("✅ Atlas dependency validation: PASSED")
            print("All required dependencies are properly configured.")
        else:
            print("❌ Atlas dependency validation: FAILED")
            print(f"Found {overall['total_issues']} issues that need attention:")

            for i, issue in enumerate(overall["issues"], 1):
                print(f"\n{i}. {issue.get('issue', 'Unknown issue')}")
                if "suggestion" in issue:
                    print(f"   💡 {issue['suggestion']}")

        if verbose:
            print("\n📋 Detailed Results:")
            for category, result in self.results.items():
                if category == "overall":
                    continue

                status_icon = "✅" if result["status"] == "pass" else "❌"
                print(
                    f"  {status_icon} {category.replace('_', ' ').title()}: {result['status'].upper()}"
                )

    def export_json(self) -> str:
        """Export results as JSON."""
        return json.dumps(self.results, indent=2)


def main():
    """Main entry point for the dependency validation script."""
    parser = argparse.ArgumentParser(
        description="Validate Atlas dependencies",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--fix",
        action="store_true",
        help="Attempt to fix common dependency issues automatically",
    )

    parser.add_argument(
        "--verbose", action="store_true", help="Show detailed validation information"
    )

    parser.add_argument(
        "--json", action="store_true", help="Output results in JSON format"
    )

    args = parser.parse_args()

    # Run validation
    validator = DependencyValidator()
    results = validator.validate_all(fix_issues=args.fix, verbose=args.verbose)

    if args.json:
        print(validator.export_json())
    else:
        validator.print_results(verbose=args.verbose)

    # Exit with appropriate code
    sys.exit(0 if results["overall"]["status"] == "pass" else 1)


if __name__ == "__main__":
    main()
