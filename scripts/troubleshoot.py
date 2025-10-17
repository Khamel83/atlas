#!/usr/bin/env python3
"""
Atlas Troubleshooting Master Script

This is the main troubleshooting script that guides users through
diagnosing and fixing Atlas environment issues. It provides a
menu-driven interface for different troubleshooting scenarios.

Usage:
    python scripts/troubleshoot.py
    python scripts/troubleshoot.py --auto-fix
    python scripts/troubleshoot.py --quick-check
"""

import argparse
import subprocess
import sys
from pathlib import Path


def print_header():
    """Print troubleshooting header."""
    print("=" * 60)
    print("🔧 Atlas Troubleshooting Assistant")
    print("=" * 60)
    print("This tool helps diagnose and fix common Atlas issues.")
    print()


def print_menu():
    """Print main menu options."""
    print("📋 What would you like to do?")
    print()
    print("1. 🚀 Quick Setup Check (recommended for new users)")
    print("2. 🔍 Full Environment Diagnosis")
    print("3. ✅ Configuration Validation")
    print("4. 🔧 Auto-Fix Common Issues")
    print("5. 📖 View Troubleshooting Guide")
    print("6. 🆘 Generate Support Report")
    print("7. ❌ Exit")
    print()


def run_quick_check():
    """Run quick setup check."""
    print("🚀 Running Quick Setup Check...")
    print("-" * 40)

    try:
        result = subprocess.run([sys.executable, "scripts/setup_check.py"], text=True)
        return result.returncode == 0
    except FileNotFoundError:
        print("❌ Setup check script not found")
        return False


def run_full_diagnosis():
    """Run comprehensive environment diagnosis."""
    print("🔍 Running Full Environment Diagnosis...")
    print("-" * 40)

    try:
        subprocess.run(
            [sys.executable, "scripts/diagnose_environment.py", "--test-apis"],
            text=True,
        )
    except FileNotFoundError:
        print("❌ Diagnostic script not found")


def run_config_validation():
    """Run configuration validation."""
    print("✅ Running Configuration Validation...")
    print("-" * 40)

    try:
        subprocess.run([sys.executable, "scripts/validate_config.py"], text=True)
    except FileNotFoundError:
        print("❌ Configuration validation script not found")


def run_auto_fix():
    """Run automatic fixes."""
    print("🔧 Running Automatic Fixes...")
    print("-" * 40)

    print("1. Attempting to fix directory permissions...")
    try:
        subprocess.run(
            [sys.executable, "scripts/diagnose_environment.py", "--fix-permissions"],
            text=True,
        )
    except FileNotFoundError:
        print("❌ Diagnostic script not found")

    print("\n2. Checking if configuration needs setup...")
    config_path = Path("config/.env")
    if not config_path.exists():
        print("Creating configuration from template...")
        try:
            subprocess.run([sys.executable, "scripts/generate_env.py"], text=True)
        except FileNotFoundError:
            print("❌ Environment generation script not found")
            print("Manual fix: cp .env.example config/.env")
    else:
        print("✅ Configuration file already exists")

    print("\n3. Running final validation...")
    run_config_validation()


def show_troubleshooting_guide():
    """Show troubleshooting guide information."""
    print("📖 Troubleshooting Documentation")
    print("-" * 40)

    docs = [
        ("Complete Troubleshooting Guide", "docs/environment-troubleshooting.md"),
        ("Quick Reference Checklist", "docs/troubleshooting_checklist.md"),
        ("Configuration Guide", "docs/configuration-validation.md"),
        ("Quick Start Guide", "QUICK_START.md"),
    ]

    for title, path in docs:
        if Path(path).exists():
            print(f"✅ {title}: {path}")
        else:
            print(f"❌ {title}: {path} (not found)")

    print("\n📚 Most helpful for troubleshooting:")
    print("   cat docs/environment-troubleshooting.md")
    print("   cat docs/troubleshooting_checklist.md")


def generate_support_report():
    """Generate comprehensive support report."""
    print("🆘 Generating Support Report...")
    print("-" * 40)

    report_file = "atlas_support_report.txt"

    try:
        with open(report_file, "w") as f:
            f.write("Atlas Support Report\n")
            f.write("=" * 50 + "\n")
            f.write(
                f"Generated: {subprocess.check_output(['date'], text=True).strip()}\n"
            )
            f.write(f"Python: {sys.version}\n")
            f.write(
                f"Platform: {subprocess.check_output(['uname', '-a'], text=True).strip()}\n\n"
            )

            # Environment diagnosis
            f.write("Environment Diagnosis:\n")
            f.write("-" * 30 + "\n")
            try:
                diag_result = subprocess.run(
                    [sys.executable, "scripts/diagnose_environment.py"],
                    capture_output=True,
                    text=True,
                )
                f.write(diag_result.stdout)
                if diag_result.stderr:
                    f.write("\nErrors:\n" + diag_result.stderr)
            except FileNotFoundError:
                f.write("Diagnostic script not available\n")

            f.write("\n\nConfiguration Validation:\n")
            f.write("-" * 30 + "\n")
            try:
                config_result = subprocess.run(
                    [sys.executable, "scripts/validate_config.py"],
                    capture_output=True,
                    text=True,
                )
                f.write(config_result.stdout)
                if config_result.stderr:
                    f.write("\nErrors:\n" + config_result.stderr)
            except FileNotFoundError:
                f.write("Configuration validation script not available\n")

            f.write("\n\nProject Structure:\n")
            f.write("-" * 30 + "\n")
            try:
                ls_result = subprocess.run(
                    ["ls", "-la"], capture_output=True, text=True
                )
                f.write(ls_result.stdout)
            except Exception:
                f.write("Cannot list directory contents\n")

        print(f"✅ Support report saved to: {report_file}")
        print("\n📤 Include this file when seeking help:")
        print(f"   cat {report_file}")

    except Exception as e:
        print(f"❌ Error generating support report: {e}")


def main():
    """Main troubleshooting interface."""
    parser = argparse.ArgumentParser(description="Atlas troubleshooting assistant")
    parser.add_argument(
        "--auto-fix", action="store_true", help="Run automatic fixes without menu"
    )
    parser.add_argument(
        "--quick-check", action="store_true", help="Run quick setup check only"
    )

    args = parser.parse_args()

    print_header()

    if args.quick_check:
        success = run_quick_check()
        sys.exit(0 if success else 1)

    if args.auto_fix:
        run_auto_fix()
        print("\n🎯 Auto-fix complete. Run quick check to verify:")
        print("   python scripts/setup_check.py")
        return

    # Interactive menu
    while True:
        print_menu()

        try:
            choice = input("Enter your choice (1-7): ").strip()
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break

        print()

        if choice == "1":
            run_quick_check()
        elif choice == "2":
            run_full_diagnosis()
        elif choice == "3":
            run_config_validation()
        elif choice == "4":
            run_auto_fix()
        elif choice == "5":
            show_troubleshooting_guide()
        elif choice == "6":
            generate_support_report()
        elif choice == "7" or choice.lower() == "exit":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please enter 1-7.")

        print("\n" + "─" * 60 + "\n")


if __name__ == "__main__":
    main()
