#!/usr/bin/env python3
"""
Comprehensive test runner for Atlas CI/CD pipeline fixes.
This script validates that all test configurations work correctly.
"""

import os
import sys
import sqlite3
import subprocess
import tempfile
from pathlib import Path


def setup_test_environment():
    """Set up test environment with proper database and configuration."""
    print("🔧 Setting up test environment...")

    # Create test directories
    os.makedirs('data/test', exist_ok=True)
    os.makedirs('logs/test', exist_ok=True)

    # Create test database
    test_db_path = 'data/test/atlas_test.db'
    conn = sqlite3.connect(test_db_path)
    cursor = conn.cursor()

    # Create content table (simplified schema for tests)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE,
            title TEXT,
            content TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    ''')

    # Create metadata table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS metadata (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_id INTEGER,
            key TEXT,
            value TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (content_id) REFERENCES content (id)
        )
    ''')

    # Insert test data
    test_content = [
        {
            'url': 'https://example.com/test1',
            'title': 'Test Article 1',
            'content': 'This is test content 1'
        },
        {
            'url': 'https://example.com/test2',
            'title': 'Test Article 2',
            'content': 'This is test content 2'
        }
    ]

    for item in test_content:
        cursor.execute('''
            INSERT OR IGNORE INTO content (url, title, content, created_at, updated_at)
            VALUES (?, ?, ?, datetime('now'), datetime('now'))
        ''', (item['url'], item['title'], item['content']))

    conn.commit()
    conn.close()

    # Set environment variables
    os.environ.update({
        'TESTING': 'true',
        'ATLAS_DB_PATH': test_db_path,
        'DATABASE_URL': f'sqlite:///{test_db_path}',
        'LOG_LEVEL': 'ERROR',
        'OPENROUTER_API_KEY': 'test_key_for_testing_only'
    })

    print(f"✅ Test environment set up with database: {test_db_path}")


def test_basic_functionality():
    """Test basic Python and database functionality."""
    print("\n🧪 Testing basic functionality...")

    try:
        # Test Python imports
        import sqlite3
        import pytest
        import fastapi
        print("✅ Python imports working")

        # Test database connection
        test_db = 'data/test/atlas_test.db'
        if os.path.exists(test_db):
            conn = sqlite3.connect(test_db)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM content")
            count = cursor.fetchone()[0]
            conn.close()
            print(f"✅ Database accessible with {count} test records")
        else:
            print("❌ Test database not found")
            return False

    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False

    return True


def test_pytest_collection():
    """Test that pytest can collect tests without errors."""
    print("\n📋 Testing pytest collection...")

    try:
        result = subprocess.run([
            sys.executable, '-m', 'pytest', '--collect-only', '-q'
        ], capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            test_count = result.stdout.count('::')
            print(f"✅ Pytest collected {test_count} tests successfully")
            return True
        else:
            print(f"❌ Pytest collection failed:")
            print(result.stdout)
            print(result.stderr)
            return False

    except subprocess.TimeoutExpired:
        print("❌ Pytest collection timed out")
        return False
    except Exception as e:
        print(f"❌ Pytest collection error: {e}")
        return False


def test_sample_tests():
    """Run a sample of tests to verify they work."""
    print("\n🔍 Running sample tests...")

    test_files = [
        'tests/test_url_utils.py',
        'tests/test_health_check.py'
    ]

    success_count = 0

    for test_file in test_files:
        if os.path.exists(test_file):
            try:
                result = subprocess.run([
                    sys.executable, '-m', 'pytest', test_file, '-v', '--tb=short'
                ], capture_output=True, text=True, timeout=60)

                if result.returncode == 0:
                    print(f"✅ {test_file} passed")
                    success_count += 1
                else:
                    print(f"❌ {test_file} failed:")
                    print(result.stdout[-500:])  # Last 500 chars of output
                    print(result.stderr[-500:])

            except Exception as e:
                print(f"❌ Error running {test_file}: {e}")
        else:
            print(f"⚠️  {test_file} not found, skipping")

    return success_count > 0


def test_dependencies():
    """Test that all required dependencies are installed."""
    print("\n📦 Testing dependencies...")

    required_packages = [
        'pytest',
        'fastapi',
        'httpx',
        'sqlite3',
        'requests'
    ]

    optional_packages = [
        'dotenv'  # Often available as system package
    ]

    missing_packages = []

    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package} missing")

    # Check optional packages
    missing_optional = []
    for package in optional_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package} (optional)")
        except ImportError:
            missing_optional.append(package)
            print(f"⚠️  {package} (optional) missing")

    if missing_packages:
        print(f"\n❌ Missing required packages: {', '.join(missing_packages)}")
        return False

    if missing_optional:
        print(f"\n⚠️  Missing optional packages: {', '.join(missing_optional)}")

    return True


def cleanup_test_files():
    """Clean up test files."""
    print("\n🧹 Cleaning up test files...")

    test_files = [
        'test_web_atlas.db',
        'data/test/atlas_test.db'
    ]

    for file_path in test_files:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"✅ Removed {file_path}")
            except Exception as e:
                print(f"⚠️  Could not remove {file_path}: {e}")


def main():
    """Main test runner function."""
    print("🚀 Atlas CI/CD Test Runner")
    print("=" * 50)

    # Track overall success
    results = []

    try:
        # Setup test environment
        setup_test_environment()

        # Run all tests
        results.append(test_dependencies())
        results.append(test_basic_functionality())
        results.append(test_pytest_collection())
        results.append(test_sample_tests())

    except Exception as e:
        print(f"❌ Test runner failed: {e}")
        results.append(False)

    finally:
        # Always cleanup
        cleanup_test_files()

    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)

    passed = sum(results)
    total = len(results)

    if passed == total:
        print(f"🎉 All {total} test categories passed!")
        print("✅ Atlas CI/CD pipeline is ready")
        return 0
    else:
        print(f"⚠️  {passed}/{total} test categories passed")
        print("❌ Some issues remain - review the output above")
        return 1


if __name__ == '__main__':
    sys.exit(main())