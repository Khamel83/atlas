#!/usr/bin/env python3
"""
Enhanced test runner script for Atlas project.

This script provides different testing modes:
- Quick: Unit tests only
- Full: All tests with coverage
- Performance: Performance and load tests
- Security: Security-focused tests
"""

import argparse
import os
import sys
from pathlib import Path

import pytest

def setup_test_environment():
    """Set up the test environment."""
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))

    # Ensure test directories exist
    os.makedirs("htmlcov", exist_ok=True)

def run_quick_tests():
    """Run quick unit tests only."""
    return pytest.main([
        "-v",
        "-m", "unit",
        "--tb=short"
    ])

def run_full_tests():
    """Run all tests with coverage reporting."""
    return pytest.main([
        "tests/"
    ])

def run_performance_tests():
    """Run performance and load tests."""
    return pytest.main([
        "-v",
        "-m", "performance",
        "--tb=short"
    ])

def run_security_tests():
    """Run security-focused tests."""
    return pytest.main([
        "-v",
        "-m", "security",
        "--tb=short"
    ])

def run_integration_tests():
    """Run integration tests."""
    return pytest.main([
        "-v",
        "-m", "integration",
        "--tb=short"
    ])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Atlas Test Runner")
    parser.add_argument(
        "mode",
        choices=["quick", "full", "performance", "security", "integration"],
        default="full",
        nargs="?",
        help="Test mode to run"
    )

    args = parser.parse_args()

    setup_test_environment()

    runners = {
        "quick": run_quick_tests,
        "full": run_full_tests,
        "performance": run_performance_tests,
        "security": run_security_tests,
        "integration": run_integration_tests
    }

    print(f"Running {args.mode} tests...")
    exit_code = runners[args.mode]()

    if exit_code == 0:
        print(f"\n✅ {args.mode.title()} tests passed!")
        if args.mode == "full":
            print("📊 Coverage report generated in htmlcov/index.html")
    else:
        print(f"\n❌ {args.mode.title()} tests failed!")

    sys.exit(exit_code)
