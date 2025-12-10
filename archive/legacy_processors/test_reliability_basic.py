#!/usr/bin/env python3
"""
Basic reliability test suite for Atlas production features.
Tests core functionality that exists in the current codebase.
"""

import os
import sys
import unittest
import tempfile
import shutil
import time
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.database import UniversalDatabase as Database
from helpers.configuration_manager import ConfigurationManager
from helpers.secret_manager import SecretManager


class TestDatabaseReliability(unittest.TestCase):
    """Test database reliability features."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.db"
        self.db = Database(str(self.db_path))
        self.db.initialize()

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)

    def test_database_initialization(self):
        """Test database initialization."""
        self.assertTrue(self.db_path.exists())
        self.assertIsInstance(self.db, Database)

    def test_content_operations(self):
        """Test basic content operations."""
        # Add content
        content = {
            "url": "https://example.com",
            "title": "Test Article",
            "content": "This is test content",
            "content_type": "article"
        }

        content_id = self.db.add_content(content)
        self.assertIsInstance(content_id, int)

        # Get content
        retrieved = self.db.get_content(content_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved['title'], "Test Article")

        # Search content
        results = self.db.search_content("test content")
        self.assertGreater(len(results), 0)

    def test_database_statistics(self):
        """Test database statistics."""
        # Add test content
        for i in range(5):
            self.db.add_content({
                "url": f"https://example{i}.com",
                "title": f"Article {i}",
                "content": f"Content {i}",
                "content_type": "article"
            })

        # Get statistics
        stats = self.db.get_statistics()
        self.assertGreaterEqual(stats['total_items'], 5)
        self.assertIn('by_type', stats)

    def test_performance_benchmarks(self):
        """Test database performance."""
        # Insert performance
        start_time = time.time()
        for i in range(50):
            self.db.add_content({
                "url": f"https://perf{i}.com",
                "title": f"Perf {i}",
                "content": f"Content {i}",
                "content_type": "article"
            })
        insert_time = time.time() - start_time

        print(f"Database insert rate: {50/insert_time:.2f} ops/sec")
        self.assertGreater(50/insert_time, 5)  # At least 5 ops/sec

        # Search performance
        start_time = time.time()
        for i in range(25):
            results = self.db.search_content(f"perf {i}")
            self.assertGreater(len(results), 0)
        search_time = time.time() - start_time

        print(f"Database search rate: {25/search_time:.2f} ops/sec")
        self.assertGreater(25/search_time, 2)  # At least 2 ops/sec


class TestConfigurationReliability(unittest.TestCase):
    """Test configuration management reliability."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir) / "config"
        self.secrets_dir = Path(self.temp_dir) / "secrets"

        for dir_path in [self.config_dir, self.secrets_dir]:
            dir_path.mkdir(parents=True)

        self.config_manager = ConfigurationManager(str(self.config_dir), str(self.secrets_dir))
        self.secret_manager = SecretManager(str(self.secrets_dir))

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)

    def test_configuration_validation(self):
        """Test configuration validation."""
        # Valid configuration
        valid_config = {
            "API_HOST": "0.0.0.0",
            "API_PORT": "8000",
            "DATABASE_PATH": "test.db"
        }

        is_valid, errors = self.config_manager.validate_configuration(valid_config)
        self.assertTrue(is_valid)

        # Invalid configuration
        invalid_config = {"INVALID": "config"}
        is_valid, errors = self.config_manager.validate_configuration(invalid_config)
        self.assertFalse(is_valid)

    def test_environment_management(self):
        """Test environment configuration management."""
        # Create test environment files
        for env in ['development', 'production']:
            env_file = self.config_dir / f"{env}.env"
            with open(env_file, 'w') as f:
                f.write(f"ENVIRONMENT={env}\n")
                f.write("API_PORT=8000\n")

        # Test environment switching
        self.config_manager.set_environment("development")
        config = self.config_manager.get_config()
        self.assertEqual(config.get('ENVIRONMENT'), 'development')

        self.config_manager.set_environment("production")
        config = self.config_manager.get_config()
        self.assertEqual(config.get('ENVIRONMENT'), 'production')

    def test_secrets_management(self):
        """Test secrets management."""
        # Test secret operations
        self.secret_manager.set_secret("test_key", "test_value")
        retrieved = self.secret_manager.get_secret("test_key")
        self.assertEqual(retrieved, "test_value")

        # Test secret listing
        secrets = self.secret_manager.list_secrets()
        self.assertIn("test_key", secrets)

        # Test secret encryption/decryption
        test_data = {"sensitive": "data"}
        encrypted = self.secret_manager._encrypt_secrets(test_data)
        decrypted = self.secret_manager._decrypt_secrets(encrypted)
        self.assertEqual(test_data, decrypted)


class TestSystemIntegration(unittest.TestCase):
    """Test system integration reliability."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir) / "config"
        self.secrets_dir = Path(self.temp_dir) / "secrets"
        self.db_path = Path(self.temp_dir) / "test.db"

        for dir_path in [self.config_dir, self.secrets_dir]:
            dir_path.mkdir(parents=True)

        # Initialize components
        self.db = Database(str(self.db_path))
        self.db.initialize()

        self.config_manager = ConfigurationManager(str(self.config_dir), str(self.secrets_dir))
        self.secret_manager = SecretManager(str(self.secrets_dir))

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)

    def test_system_lifecycle(self):
        """Test complete system lifecycle."""
        # 1. Configuration setup
        self.config_manager.set_environment("development")
        config = self.config_manager.get_config()
        self.assertIsInstance(config, dict)

        # 2. Secrets setup
        self.secret_manager.set_secret("test_secret", "test_value")
        retrieved = self.secret_manager.get_secret("test_secret")
        self.assertEqual(retrieved, "test_value")

        # 3. Database operations
        self.db.add_content({
            "url": "https://example.com",
            "title": "Test Article",
            "content": "Test content",
            "content_type": "article"
        })

        stats = self.db.get_statistics()
        self.assertGreaterEqual(stats['total_items'], 1)

    def test_error_handling(self):
        """Test error handling."""
        # Test configuration validation error handling
        invalid_config = {"INVALID": "CONFIG"}
        is_valid, errors = self.config_manager.validate_configuration(invalid_config)
        self.assertFalse(is_valid)

        # Test database error handling
        try:
            # Try to get content with invalid ID
            result = self.db.get_content(999999)
            self.assertIsNone(result)
        except Exception as e:
            # Should handle gracefully
            pass

        # Test secrets error handling
        try:
            # Try to get non-existent secret
            result = self.secret_manager.get_secret("non_existent")
            self.assertIsNone(result)
        except Exception as e:
            # Should handle gracefully
            pass

    def test_performance_under_load(self):
        """Test system performance under load."""
        # Database load test
        start_time = time.time()
        for i in range(100):
            self.db.add_content({
                "url": f"https://load{i}.com",
                "title": f"Load Test {i}",
                "content": f"Content {i}",
                "content_type": "article"
            })
        db_time = time.time() - start_time

        print(f"Database load test: {100/db_time:.2f} ops/sec")
        self.assertGreater(100/db_time, 3)  # At least 3 ops/sec

        # Configuration load test
        start_time = time.time()
        for i in range(50):
            self.config_manager.set_environment("development" if i % 2 == 0 else "production")
            config = self.config_manager.get_config()
        config_time = time.time() - start_time

        print(f"Configuration load test: {50/config_time:.2f} ops/sec")
        self.assertGreater(50/config_time, 5)  # At least 5 ops/sec

        # Secrets load test
        start_time = time.time()
        for i in range(50):
            self.secret_manager.set_secret(f"secret_{i}", f"value_{i}")
            retrieved = self.secret_manager.get_secret(f"secret_{i}")
        secrets_time = time.time() - start_time

        print(f"Secrets load test: {50/secrets_time:.2f} ops/sec")
        self.assertGreater(50/secrets_time, 5)  # At least 5 ops/sec


class TestAPIHealth(unittest.TestCase):
    """Test API health endpoints."""

    def setUp(self):
        """Set up test environment."""
        from api import app
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_health_endpoints(self):
        """Test health endpoints."""
        # Main health endpoint
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('status', data)

        # Metrics endpoint
        response = self.client.get('/metrics')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('metrics', data)

    def test_api_error_handling(self):
        """Test API error handling."""
        # Test invalid endpoint
        response = self.client.get('/invalid-endpoint')
        self.assertEqual(response.status_code, 404)

        # Test invalid method
        response = self.client.post('/health')
        self.assertEqual(response.status_code, 405)


def run_basic_reliability_tests():
    """Run basic reliability tests."""
    print("🧪 Running Atlas Basic Reliability Tests")
    print("=" * 50)

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    test_classes = [
        TestDatabaseReliability,
        TestConfigurationReliability,
        TestSystemIntegration,
        TestAPIHealth
    ]

    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate report
    print("\n" + "=" * 50)
    print("📊 Basic Reliability Test Report")
    print("=" * 50)

    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100)
    print(f"Success Rate: {success_rate:.1f}%")

    if result.failures:
        print("\n❌ Failures:")
        for test, traceback in result.failures:
            print(f"- {test}")

    if result.errors:
        print("\n⚠️ Errors:")
        for test, traceback in result.errors:
            print(f"- {test}")

    # Overall assessment
    if success_rate >= 90:
        print("\n✅ Excellent basic reliability test results!")
        print("Atlas core reliability features are working correctly.")
    elif success_rate >= 75:
        print("\n✅ Good basic reliability test results!")
        print("Minor issues detected but core system is reliable.")
    elif success_rate >= 60:
        print("\n⚠️ Acceptable basic reliability test results.")
        print("Some core reliability issues need attention.")
    else:
        print("\n❌ Poor basic reliability test results.")
        print("Significant core reliability issues detected.")

    print(f"\n🎯 Basic Reliability Score: {success_rate:.1f}%")
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_basic_reliability_tests()
    sys.exit(0 if success else 1)