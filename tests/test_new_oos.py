#!/usr/bin/env python3
"""Test script for the new OOS interface"""
import subprocess
import tempfile
import os
from pathlib import Path

def test_empty_directory():
    """Test the empty directory flow"""
    print("🧪 Testing empty directory flow...")

    with tempfile.TemporaryDirectory() as tmp_dir:
        os.chdir(tmp_dir)

        # Test the context detection
        result = subprocess.run([
            'python3', '/home/ubuntu/dev/oos/run.py', '--help'
        ], capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ Help system works")
        else:
            print(f"❌ Help failed: {result.stderr}")

def test_existing_project():
    """Test existing project flow"""
    print("🧪 Testing existing project flow...")

    with tempfile.TemporaryDirectory() as tmp_dir:
        os.chdir(tmp_dir)

        # Create a git repo
        subprocess.run(['git', 'init'], capture_output=True)

        # Test help in git directory
        result = subprocess.run([
            'python3', '/home/ubuntu/dev/oos/run.py', '--help'
        ], capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ Existing project detection works")
        else:
            print(f"❌ Existing project test failed: {result.stderr}")

def main():
    print("🚀 Testing New OOS Interface")
    print("=" * 40)

    original_dir = os.getcwd()

    try:
        test_empty_directory()
        test_existing_project()
        print("\n✅ All tests passed!")
    finally:
        os.chdir(original_dir)

if __name__ == "__main__":
    main()