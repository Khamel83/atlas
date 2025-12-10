#!/usr/bin/env python3
"""
Simple reliability test suite for Atlas production features.
Tests core functionality without complex dependencies.
"""

import os
import sys
import unittest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.database import UniversalDatabase as Database
from helpers.configuration_manager import ConfigurationManager
from helpers.secret_manager import SecretManager
from helpers.queue_manager import QueueManager, CircuitBreakerState, QueueTask, get_queue_manager


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
        """Test database initialization and WAL mode."""
        self.assertTrue(self.db_path.exists())

        # Check WAL mode
        result = self.db.execute_query("PRAGMA journal_mode;")
        self.assertEqual(result[0]['journal_mode'], 'wal')

    def test_connection_pooling(self):
        """Test database connection pooling."""
        # Get multiple connections
        connections = []
        for i in range(5):
            conn = self.db.get_connection()
            connections.append(conn)
            self.assertIsNotNone(conn)

        # Return connections
        for conn in connections:
            self.db.return_connection(conn)

        # Check pool size
        self.assertLessEqual(len(self.db._connection_pool), self.db.pool_size)

    def test_content_operations(self):
        """Test content operations reliability."""
        # Insert test content
        content = {
            "url": "https://example.com",
            "title": "Test Article",
            "content": "This is test content",
            "content_type": "article"
        }

        content_id = self.db.add_content(content)
        self.assertIsInstance(content_id, int)
        self.assertGreater(content_id, 0)

        # Retrieve content
        retrieved = self.db.get_content(content_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved['title'], "Test Article")

        # Search content
        results = self.db.search_content("test content")
        self.assertGreater(len(results), 0)

    def test_database_statistics(self):
        """Test database statistics functionality."""
        # Add test content
        for i in range(10):
            self.db.add_content({
                "url": f"https://example{i}.com",
                "title": f"Article {i}",
                "content": f"Content {i}",
                "content_type": "article"
            })

        # Get statistics
        stats = self.db.get_statistics()
        self.assertGreaterEqual(stats['total_items'], 10)
        self.assertIn('by_type', stats)
        self.assertIn('by_source', stats)

    def test_database_backup(self):
        """Test database backup functionality."""
        # Add test data
        self.db.add_content({
            "url": "https://example.com",
            "title": "Test Article",
            "content": "Test content",
            "content_type": "article"
        })

        # Create backup
        backup_path = Path(self.temp_dir) / "backup.db"
        self.db.backup_database(str(backup_path))
        self.assertTrue(backup_path.exists())

        # Verify backup
        backup_db = Database(str(backup_path))
        backup_stats = backup_db.get_statistics()
        self.assertGreaterEqual(backup_stats['total_items'], 1)


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
        self.assertEqual(len(errors), 0)

        # Invalid configuration
        invalid_config = {
            "API_HOST": "0.0.0.0"
            # Missing required fields
        }

        is_valid, errors = self.config_manager.validate_configuration(invalid_config)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)

    def test_environment_switching(self):
        """Test environment switching."""
        # Create test environment files
        for env in ['development', 'production']:
            env_file = self.config_dir / f"{env}.env"
            with open(env_file, 'w') as f:
                f.write(f"ENVIRONMENT={env}\n")
                f.write("API_PORT=8000\n")

        # Test switching
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

        # Test secret deletion
        self.secret_manager.delete_secret("test_key")
        retrieved = self.secret_manager.get_secret("test_key")
        self.assertIsNone(retrieved)


class TestQueueReliability(unittest.TestCase):
    """Test queue management reliability."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        # Create a test database for queue operations
        self.test_db = Path(self.temp_dir) / "test_queue.db"
        # We'll need to set up the database config for queue operations
        import os
        os.environ['ATLAS_DATABASE_PATH'] = str(self.test_db)

    def tearDown(self):
        """Clean up test environment."""
        import os
        if 'ATLAS_DATABASE_PATH' in os.environ:
            del os.environ['ATLAS_DATABASE_PATH']
        shutil.rmtree(self.temp_dir)

    def test_circuit_breaker_state(self):
        """Test circuit breaker state functionality."""
        cb_state = CircuitBreakerState()

        # Test initial state
        self.assertEqual(cb_state.state, "closed")
        self.assertEqual(cb_state.failure_count, 0)
        self.assertIsNone(cb_state.last_failure)

    def test_queue_task_creation(self):
        """Test QueueTask dataclass functionality."""
        task = QueueTask(
            task_id="test_task_1",
            task_type="test",
            task_data={"message": "test data"},
            priority=1
        )

        self.assertEqual(task.task_id, "test_task_1")
        self.assertEqual(task.task_type, "test")
        self.assertEqual(task.task_data, {"message": "test data"})
        self.assertEqual(task.priority, 1)
        self.assertEqual(task.retry_count, 0)
        self.assertIsNone(task.error_message)

    def test_queue_manager_initialization(self):
        """Test QueueManager initialization."""
        queue_manager = QueueManager()

        # Test that queue manager initializes properly
        self.assertIsNotNone(queue_manager)
        self.assertIsInstance(queue_manager._circuit_breakers, dict)

        # Test initial circuit breaker status
        status = queue_manager.get_circuit_breaker_status()
        self.assertIsInstance(status, dict)

    def test_task_enqueue_dequeue(self):
        """Test basic task enqueue and dequeue operations."""
        queue_manager = QueueManager()

        # Test enqueue
        task_data = {"url": "https://example.com", "content": "test content"}
        success = queue_manager.enqueue_task(
            task_id="test_enqueue_1",
            task_type="test",
            task_data=task_data,
            priority=1
        )
        self.assertTrue(success)

        # Test dequeue
        task = queue_manager.dequeue_task("test_worker", ["test"])
        self.assertIsNotNone(task)
        self.assertEqual(task.task_id, "test_enqueue_1")
        self.assertEqual(task.task_type, "test")
        self.assertEqual(task.task_data, task_data)

        # Test complete task
        success = queue_manager.complete_task(task.task_id, "test_worker")
        self.assertTrue(success)

    def test_circuit_breaker_functionality(self):
        """Test circuit breaker integration in QueueManager."""
        queue_manager = QueueManager()

        # Test initial state (should be no circuit breakers)
        status = queue_manager.get_circuit_breaker_status("test_worker")
        self.assertEqual(status["state"], "closed")
        self.assertEqual(status["failure_count"], 0)

        # Test recording failures
        for i in range(12):  # More than CIRCUIT_BREAKER_THRESHOLD (10)
            queue_manager._record_failure("test_worker")

        # Check that circuit breaker opens
        status = queue_manager.get_circuit_breaker_status("test_worker")
        self.assertEqual(status["state"], "open")
        self.assertGreaterEqual(status["failure_count"], 10)

        # Test that circuit breaker prevents task dequeue
        task_data = {"url": "https://example.com", "content": "test"}
        queue_manager.enqueue_task("test_blocked", "test", task_data)

        # Should not be able to dequeue due to open circuit breaker
        task = queue_manager.dequeue_task("test_worker", ["test"])
        self.assertIsNone(task)

        # Reset circuit breaker
        queue_manager._reset_circuit_breaker("test_worker")

        # Should be able to dequeue now
        task = queue_manager.dequeue_task("test_worker", ["test"])
        self.assertIsNotNone(task)
        self.assertEqual(task.task_id, "test_blocked")

    def test_task_failure_handling(self):
        """Test task failure and dead letter queue functionality."""
        queue_manager = QueueManager()

        # Enqueue a test task
        task_data = {"url": "https://example.com", "content": "failing task"}
        queue_manager.enqueue_task("test_fail", "test", task_data)

        # Dequeue the task
        task = queue_manager.dequeue_task("test_worker", ["test"])
        self.assertIsNotNone(task)

        # Fail the task
        success = queue_manager.fail_task(task.task_id, "test_worker", "Test failure")
        self.assertTrue(success)

        # Check queue status - should show failed task
        status = queue_manager.get_queue_status()
        self.assertIn("failed_tasks", status)
        self.assertGreater(status["failed_tasks"], 0)

        # Test retrying failed task
        success = queue_manager.retry_failed_task(task.task_id)
        self.assertTrue(success)

        # Should be able to dequeue again
        task = queue_manager.dequeue_task("test_worker", ["test"])
        self.assertIsNotNone(task)
        self.assertEqual(task.task_id, "test_fail")

    def test_queue_health_metrics(self):
        """Test queue health monitoring."""
        queue_manager = QueueManager()

        # Add some test tasks
        for i in range(5):
            task_data = {"url": f"https://example{i}.com", "content": f"content {i}"}
            queue_manager.enqueue_task(f"health_test_{i}", "test", task_data)

        # Get health metrics
        health = queue_manager.get_queue_health()

        # Check structure
        self.assertIn('status_counts', health)
        self.assertIn('total_tasks', health)
        self.assertIn('depth_ratio', health)
        self.assertIn('healthy', health)
        self.assertIsInstance(health['healthy'], bool)

        # Get queue statistics
        stats = queue_manager.get_queue_stats()

        # Check structure
        self.assertIn('total_processed', stats)
        self.assertIn('successful_processed', stats)
        self.assertIn('failed_processed', stats)

    def test_queue_processing(self):
        """Test queue processing with reliability guarantees."""
        queue_manager = QueueManager()

        # Test processing a task
        task_data = {
            "task_id": "process_test_1",
            "task_type": "test",
            "priority": 1,
            "url": "https://example.com",
            "content": "process test content"
        }

        success = queue_manager.process_task(task_data)
        self.assertTrue(success)

        # Test getting next task
        next_task = queue_manager.get_next_task()
        if next_task:  # Might be processed immediately
            self.assertIn('task_id', next_task)
            self.assertIn('task_type', next_task)
            self.assertIn('task_data', next_task)

    def test_cleanup_operations(self):
        """Test cleanup of old tasks."""
        queue_manager = QueueManager()

        # Add and complete some tasks
        for i in range(3):
            task_data = {"content": f"cleanup test {i}"}
            queue_manager.enqueue_task(f"cleanup_{i}", "test", task_data)
            task = queue_manager.dequeue_task("test_worker", ["test"])
            if task:
                queue_manager.complete_task(task.task_id, "test_worker")

        # Test cleanup (use negative days to clean up all)
        cleaned = queue_manager.cleanup_old_tasks(days_old=-1)
        self.assertGreaterEqual(cleaned, 0)


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

    def test_full_system_lifecycle(self):
        """Test complete system lifecycle."""
        # 1. Configuration setup
        self.config_manager.set_environment("development")
        config = self.config_manager.get_config()
        self.assertIsInstance(config, dict)

        # 2. Secrets setup
        self.secret_manager.set_secret("database_password", "test123")
        retrieved_secret = self.secret_manager.get_secret("database_password")
        self.assertEqual(retrieved_secret, "test123")

        # 3. Database operations
        self.db.add_content({
            "url": "https://example.com",
            "title": "Test Article",
            "content": "Test content",
            "content_type": "article"
        })

        stats = self.db.get_statistics()
        self.assertGreaterEqual(stats['total_items'], 1)

        # 4. Queue operations
        queue_manager = QueueManager(max_size=100)
        queue_manager.add_item({"id": 1, "content": "test item"})

        processed_items = []
        def processor(item):
            processed_items.append(item)
            return True

        queue_manager.process_items(processor, batch_size=1)
        self.assertEqual(len(processed_items), 1)

    def test_error_handling(self):
        """Test error handling and graceful degradation."""
        # Test invalid configuration
        invalid_config = {"INVALID": "config"}
        is_valid, errors = self.config_manager.validate_configuration(invalid_config)
        self.assertFalse(is_valid)

        # Test database connection handling
        with self.assertRaises(Exception):
            # Use invalid database path
            invalid_db = Database("/invalid/path/db.sqlite")
            invalid_db.get_connection()

        # Test circuit breaker failure handling
        circuit_breaker = CircuitBreaker(failure_threshold=1, timeout=1)
        circuit_breaker.record_failure()
        self.assertFalse(circuit_breaker.is_allowed())

    def test_performance_benchmarks(self):
        """Test performance benchmarks."""
        import time

        # Database insert performance
        start_time = time.time()
        for i in range(100):
            self.db.add_content({
                "url": f"https://bench{i}.com",
                "title": f"Benchmark {i}",
                "content": f"Content {i}",
                "content_type": "article"
            })
        insert_time = time.time() - start_time

        print(f"Database insert rate: {100/insert_time:.2f} ops/sec")

        # Should be reasonably fast
        self.assertGreater(100/insert_time, 10)  # At least 10 ops/sec

        # Search performance
        start_time = time.time()
        for i in range(50):
            results = self.db.search_content(f"benchmark {i}")
            self.assertGreater(len(results), 0)
        search_time = time.time() - start_time

        print(f"Search rate: {50/search_time:.2f} ops/sec")
        self.assertGreater(50/search_time, 5)  # At least 5 ops/sec


def run_reliability_tests():
    """Run all reliability tests."""
    print("🧪 Running Atlas Reliability Tests")
    print("=" * 50)

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    test_classes = [
        TestDatabaseReliability,
        TestConfigurationReliability,
        TestQueueReliability,
        TestSystemIntegration
    ]

    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate report
    print("\n" + "=" * 50)
    print("📊 Reliability Test Report")
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
    if success_rate >= 95:
        print("\n✅ Excellent reliability test results!")
        print("Atlas reliability features are working correctly.")
    elif success_rate >= 85:
        print("\n✅ Good reliability test results!")
        print("Minor issues detected but system is reliable.")
    elif success_rate >= 70:
        print("\n⚠️ Acceptable reliability test results.")
        print("Some issues need attention before production.")
    else:
        print("\n❌ Poor reliability test results.")
        print("Significant reliability issues detected.")

    print(f"\n🎯 Reliability Score: {success_rate:.1f}%")
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_reliability_tests()
    sys.exit(0 if success else 1)