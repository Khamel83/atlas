#!/usr/bin/env python3
"""
Atlas Setup Check

A simple script that new users can run to verify their Atlas installation
is working correctly. This provides a quick go/no-go assessment.

Usage:
    python scripts/setup_check.py
"""

import subprocess
import sys
from pathlib import Path


def print_status(message, status="info"):
    """Print status message with appropriate icon."""
    icons = {"success": "✅", "error": "❌", "warning": "⚠️", "info": "ℹ️"}
    print(f"{icons.get(status, 'ℹ️')} {message}")


def check_python_version():
    """Check Python version requirement."""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 9:
        print_status(
            f"Python {version.major}.{version.minor}.{version.micro} meets requirements",
            "success",
        )
        return True
    else:
        print_status(
            f"Python {version.major}.{version.minor} is too old (need 3.9+)", "error"
        )
        return False


def check_project_files():
    """Check essential project files exist."""
    required_files = ["run.py", "requirements.txt", "helpers/config.py", ".env.example"]
    missing_files = []

    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)

    if missing_files:
        print_status(f"Missing required files: {', '.join(missing_files)}", "error")
        print_status("Make sure you're in the Atlas project directory", "info")
        return False
    else:
        print_status("All required project files found", "success")
        return True


def check_dependencies():
    """Check if critical dependencies are installed."""
    critical_deps = ["requests", "beautifulsoup4", "pyyaml", "python-dotenv"]
    missing_deps = []

    for dep in critical_deps:
        try:
            __import__(dep.replace("-", "_"))
        except ImportError:
            missing_deps.append(dep)

    if missing_deps:
        print_status(f"Missing dependencies: {', '.join(missing_deps)}", "error")
        print_status("Run: pip3 install -r requirements.txt", "info")
        return False
    else:
        print_status("All critical dependencies installed", "success")
        return True


def check_configuration():
    """Check if configuration exists."""
    config_path = Path("config/.env")

    if not config_path.exists():
        print_status("Configuration file not found", "error")
        print_status("Run: cp .env.example config/.env", "info")
        return False
    else:
        print_status("Configuration file found", "success")
        return True


def check_atlas_import():
    """Check if Atlas modules can be imported."""
    try:
        from helpers.config import load_config

        print_status("Atlas modules can be imported", "success")

        # Try to load config
        try:
            load_config()
            print_status("Configuration loads successfully", "success")
            return True
        except Exception as e:
            print_status(f"Configuration loading failed: {e}", "error")
            print_status("Check your .env file for errors", "info")
            return False

    except ImportError as e:
        print_status(f"Cannot import Atlas modules: {e}", "error")
        print_status("Install dependencies: pip3 install -r requirements.txt", "info")
        return False


def check_basic_functionality():
    """Test basic Atlas functionality."""
    try:
        result = subprocess.run(
            [sys.executable, "run.py", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            print_status("Atlas command-line interface works", "success")
            return True
        else:
            print_status("Atlas CLI has issues", "error")
            print_status(f"Error: {result.stderr[:100]}...", "info")
            return False
    except Exception as e:
        print_status(f"Cannot test Atlas CLI: {e}", "error")
        return False


def main():
    """Run complete setup verification."""
    print("🔍 Atlas Setup Check")
    print("=" * 50)

    checks = [
        ("Python Version", check_python_version),
        ("Project Files", check_project_files),
        ("Dependencies", check_dependencies),
        ("Configuration", check_configuration),
        ("Atlas Import", check_atlas_import),
        ("Basic Functionality", check_basic_functionality),
    ]

    passed = 0
    total = len(checks)

    for check_name, check_func in checks:
        print(f"\n🔎 Checking {check_name}...")
        if check_func():
            passed += 1
        else:
            # If a check fails, provide guidance
            if check_name == "Dependencies":
                print_status("Try: pip3 install -r requirements.txt", "info")
            elif check_name == "Configuration":
                print_status("Try: cp .env.example config/.env", "info")
                print_status("Then edit config/.env with your settings", "info")

    print("\n" + "=" * 50)
    print(f"📊 Setup Check Results: {passed}/{total} checks passed")

    if passed == total:
        print_status("🎉 Atlas setup is complete and ready to use!", "success")
        print_status("Try: python run.py --help", "info")
        return True
    else:
        print_status(f"⚠️ {total - passed} issues need to be resolved", "warning")
        print_status(
            "For detailed diagnostics, run: python scripts/diagnose_environment.py",
            "info",
        )
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
