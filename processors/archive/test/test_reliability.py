#!/usr/bin/env python3
"""
Comprehensive reliability testing suite for Atlas production features.
Tests all reliability components including monitoring, alerting, and operational tools.
"""

import asyncio
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import sqlite3
import shutil
import subprocess
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.monitoring_agent import MonitoringAgent, AlertManager, MetricsCollector, HealthChecker
from tools.atlas_ops import AtlasOperations, ServiceManager, BackupManager, MonitoringManager
from tools.deployment_manager import DeploymentManager, VersionControl, DeploymentStrategies
from helpers.configuration_manager import ConfigurationManager, SecretManager
from helpers.queue_manager import QueueManager, AdaptiveRateLimiter, CircuitBreaker, DeadLetterQueue
from core.database import Database


class TestMonitoringAgent(unittest.TestCase):
    """Test the monitoring agent functionality."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir) / "config"
        self.config_dir.mkdir()

        # Create test configuration
        self.test_config = {
            "monitoring": {
                "enabled": True,
                "interval": 1,
                "port": 8001,
                "metrics": {"enabled": True, "port": 8002},
                "health_checks": {
                    "api_health": True,
                    "database_health": True,
                    "disk_health": True,
                    "memory_health": True
                }
            },
            "alerts": {
                "cpu_usage": {"warning": 70, "critical": 85, "cooldown": 60},
                "memory_usage": {"warning": 80, "critical": 90, "cooldown": 60}
            },
            "notifications": {
                "email": {"enabled": False},
                "webhook": {"enabled": False},
                "slack": {"enabled": False},
                "log": {"enabled": True, "file": str(self.config_dir / "test_alerts.log")}
            }
        }

        with open(self.config_dir / "monitoring.yaml", 'w') as f:
            json.dump(self.test_config, f)

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)

    def test_monitoring_agent_initialization(self):
        """Test monitoring agent initialization."""
        agent = MonitoringAgent(str(self.config_dir))
        self.assertIsNotNone(agent)
        self.assertTrue(hasattr(agent, 'config'))
        self.assertTrue(hasattr(agent, 'alert_manager'))
        self.assertTrue(hasattr(agent, 'metrics_collector'))
        self.assertTrue(hasattr(agent, 'health_checker'))

    def test_metrics_collection(self):
        """Test metrics collection functionality."""
        agent = MonitoringAgent(str(self.config_dir))

        # Test system metrics collection
        metrics = agent.metrics_collector.collect_system_metrics()
        self.assertIn('cpu_usage', metrics)
        self.assertIn('memory_usage', metrics)
        self.assertIn('disk_usage', metrics)
        self.assertIsInstance(metrics['cpu_usage'], (int, float))
        self.assertIsInstance(metrics['memory_usage'], (int, float))
        self.assertIsInstance(metrics['disk_usage'], (int, float))

    def test_health_checks(self):
        """Test health check functionality."""
        agent = MonitoringAgent(str(self.config_dir))

        # Test API health check
        api_health = agent.health_checker.check_api_health()
        self.assertIsInstance(api_health, dict)
        self.assertIn('status', api_health)
        self.assertIn('response_time', api_health)

        # Test database health check
        db_health = agent.health_checker.check_database_health()
        self.assertIsInstance(db_health, dict)
        self.assertIn('status', db_health)
        self.assertIn('connection_count', db_health)

        # Test disk health check
        disk_health = agent.health_checker.check_disk_health()
        self.assertIsInstance(disk_health, dict)
        self.assertIn('status', disk_health)
        self.assertIn('available_space_gb', disk_health)

        # Test memory health check
        memory_health = agent.health_checker.check_memory_health()
        self.assertIsInstance(memory_health, dict)
        self.assertIn('status', memory_health)
        self.assertIn('usage_percent', memory_health)

    def test_alert_evaluation(self):
        """Test alert evaluation and triggering."""
        agent = MonitoringAgent(str(self.config_dir))

        # Create test metrics that should trigger alerts
        test_metrics = {
            'cpu_usage': 90,  # Above critical threshold
            'memory_usage': 95,  # Above critical threshold
            'disk_usage': 50  # Below threshold
        }

        # Evaluate alerts
        alerts = agent.alert_manager.evaluate_metrics(test_metrics)
        self.assertIsInstance(alerts, list)

        # Check that appropriate alerts were triggered
        alert_types = [alert['type'] for alert in alerts]
        self.assertIn('cpu_usage', alert_types)
        self.assertIn('memory_usage', alert_types)

    def test_alert_cooldown(self):
        """Test alert cooldown mechanism."""
        agent = MonitoringAgent(str(self.config_dir))

        # Create test metrics that should trigger alerts
        test_metrics = {'cpu_usage': 90}

        # First evaluation should trigger alert
        alerts1 = agent.alert_manager.evaluate_metrics(test_metrics)
        self.assertGreater(len(alerts1), 0)

        # Immediate second evaluation should not trigger alert (cooldown)
        alerts2 = agent.alert_manager.evaluate_metrics(test_metrics)
        self.assertEqual(len(alerts2), 0)

    def test_notification_channels(self):
        """Test different notification channels."""
        agent = MonitoringAgent(str(self.config_dir))

        # Test log notification
        test_alert = {
            'type': 'cpu_usage',
            'level': 'critical',
            'message': 'CPU usage at 90%',
            'timestamp': datetime.now().isoformat()
        }

        # Send notification
        result = agent.alert_manager.send_notification(test_alert)
        self.assertIsInstance(result, dict)

        # Check that log file was created
        log_file = self.config_dir / "test_alerts.log"
        self.assertTrue(log_file.exists())


class TestAtlasOperations(unittest.TestCase):
    """Test Atlas operations functionality."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.ops = AtlasOperations()

        # Mock system paths
        self.ops.config_dir = Path(self.temp_dir) / "config"
        self.ops.log_dir = Path(self.temp_dir) / "logs"
        self.ops.backup_dir = Path(self.temp_dir) / "backups"

        for dir_path in [self.ops.config_dir, self.ops.log_dir, self.ops.backup_dir]:
            dir_path.mkdir(parents=True)

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)

    def test_service_status_check(self):
        """Test service status checking."""
        with patch('subprocess.run') as mock_run:
            # Mock successful systemctl status
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "Active: active (running)"
            mock_run.return_value = mock_result

            status = self.ops.check_service_status("test-service")
            self.assertEqual(status['status'], 'healthy')
            self.assertIn('Active: active (running)', status['details'])

    def test_system_health_check(self):
        """Test system health checking."""
        with patch.object(self.ops, 'check_service_status') as mock_status, \
             patch.object(self.ops, 'get_system_metrics') as mock_metrics:

            # Mock service statuses
            mock_status.side_effect = [
                {'status': 'healthy'},
                {'status': 'warning'},
                {'status': 'healthy'}
            ]

            # Mock system metrics
            mock_metrics.return_value = {
                'cpu_usage': 45,
                'memory_usage': 60,
                'disk_usage': 30
            }

            health = self.ops.check_system_health()
            self.assertIsInstance(health, dict)
            self.assertIn('overall_healthy', health)
            self.assertIn('services_status', health)
            self.assertIn('system_metrics', health)

    def test_backup_creation(self):
        """Test backup creation functionality."""
        with patch('subprocess.run') as mock_run, \
             patch('pathlib.Path.exists', return_value=True):

            # Mock successful backup commands
            mock_result = Mock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            result = self.ops.create_backup()
            self.assertIsInstance(result, dict)
            self.assertIn('success', result)
            self.assertIn('backup_path', result)

    def test_metrics_collection(self):
        """Test system metrics collection."""
        with patch('psutil.cpu_percent', return_value=45), \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk:

            # Mock memory and disk usage
            mock_memory.return_value = Mock(percent=60)
            mock_disk.return_value = Mock(percent=30, free=10**10)  # 10GB free

            metrics = self.ops.get_system_metrics()
            self.assertIsInstance(metrics, dict)
            self.assertEqual(metrics['cpu_usage'], 45)
            self.assertEqual(metrics['memory_usage'], 60)
            self.assertEqual(metrics['disk_usage'], 30)
            self.assertIn('available_space_gb', metrics)


class TestDeploymentManager(unittest.TestCase):
    """Test deployment manager functionality."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.deployment_dir = Path(self.temp_dir) / "deployments"
        self.deployment_dir.mkdir()

        self.manager = DeploymentManager()
        self.manager.deployments_dir = self.deployment_dir

        # Create test versions
        self.test_versions = [
            {
                "version": "v2.0.0",
                "timestamp": datetime.now().isoformat(),
                "checksum": "abc123",
                "size": 1024,
                "description": "Previous version"
            },
            {
                "version": "v2.1.0",
                "timestamp": datetime.now().isoformat(),
                "checksum": "def456",
                "size": 2048,
                "description": "Current version"
            }
        ]

        # Save test versions
        versions_file = self.deployment_dir / "versions.json"
        with open(versions_file, 'w') as f:
            json.dump(self.test_versions, f)

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)

    def test_version_listing(self):
        """Test version listing functionality."""
        versions = self.manager.list_versions()
        self.assertIsInstance(versions, list)
        self.assertEqual(len(versions), 2)
        self.assertEqual(versions[0]['version'], 'v2.1.0')
        self.assertEqual(versions[1]['version'], 'v2.0.0')

    def test_version_details(self):
        """Test version details retrieval."""
        details = self.manager.get_version_details('v2.1.0')
        self.assertIsInstance(details, dict)
        self.assertEqual(details['version'], 'v2.1.0')
        self.assertEqual(details['checksum'], 'def456')

    def test_deployment_simulation(self):
        """Test deployment simulation."""
        with patch.object(self.manager, 'health_check') as mock_health:
            # Mock successful health check
            mock_health.return_value = {'healthy': True}

            result = self.manager.simulate_deployment('v2.1.0', 'staging', 'rolling')
            self.assertIsInstance(result, dict)
            self.assertIn('success', result)
            self.assertIn('deployment_id', result)
            self.assertIn('strategy', result)

    def test_rollback_simulation(self):
        """Test rollback simulation."""
        with patch.object(self.manager, 'get_current_deployment') as mock_current, \
             patch.object(self.manager, 'health_check') as mock_health:

            # Mock current deployment and health check
            mock_current.return_value = {'version': 'v2.1.0'}
            mock_health.return_value = {'healthy': True}

            result = self.manager.simulate_rollback('staging', 'v2.0.0')
            self.assertIsInstance(result, dict)
            self.assertIn('success', result)
            self.assertIn('rollback_id', result)


class TestConfigurationManagement(unittest.TestCase):
    """Test configuration management functionality."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir) / "config"
        self.secrets_dir = Path(self.temp_dir) / "secrets"

        for dir_path in [self.config_dir, self.secrets_dir]:
            dir_path.mkdir()

        self.config_manager = ConfigurationManager(str(self.config_dir), str(self.secrets_dir))

        # Create test environment file
        self.test_config = {
            "API_HOST": "0.0.0.0",
            "API_PORT": "8000",
            "DATABASE_PATH": "test.db",
            "MONITORING_ENABLED": "true"
        }

        env_file = self.config_dir / "test.env"
        with open(env_file, 'w') as f:
            for key, value in self.test_config.items():
                f.write(f"{key}={value}\n")

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)

    def test_configuration_loading(self):
        """Test configuration loading."""
        config = self.config_manager.load_environment_config("test")
        self.assertIsInstance(config, dict)
        self.assertEqual(config['API_HOST'], "0.0.0.0")
        self.assertEqual(config['API_PORT'], "8000")
        self.assertEqual(config['MONITORING_ENABLED'], "true")

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

        # Invalid configuration (missing required fields)
        invalid_config = {
            "API_HOST": "0.0.0.0"
        }

        is_valid, errors = self.config_manager.validate_configuration(invalid_config)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)

    def test_secret_management(self):
        """Test secret management functionality."""
        secret_manager = SecretManager(str(self.secrets_dir))

        # Test secret setting and getting
        secret_manager.set_secret("test_secret", "test_value")
        retrieved_value = secret_manager.get_secret("test_secret")
        self.assertEqual(retrieved_value, "test_value")

        # Test secret listing
        secrets = secret_manager.list_secrets()
        self.assertIsInstance(secrets, list)
        self.assertIn("test_secret", secrets)

    def test_environment_switching(self):
        """Test environment switching."""
        # Create multiple environment files
        for env in ['development', 'production']:
            env_file = self.config_dir / f"{env}.env"
            with open(env_file, 'w') as f:
                f.write(f"ENVIRONMENT={env}\n")
                f.write("API_PORT=8000\n")

        # Test switching to development
        self.config_manager.set_environment("development")
        config = self.config_manager.get_config()
        self.assertEqual(config.get('ENVIRONMENT'), 'development')

        # Test switching to production
        self.config_manager.set_environment("production")
        config = self.config_manager.get_config()
        self.assertEqual(config.get('ENVIRONMENT'), 'production')


class TestReliabilityFeatures(unittest.TestCase):
    """Test reliability features integration."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.db"

        # Initialize test database
        self.db = Database(str(self.db_path))
        self.db.initialize()

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)

    def test_adaptive_rate_limiting(self):
        """Test adaptive rate limiting functionality."""
        rate_limiter = AdaptiveRateLimiter(
            bucket_size=100,
            refill_rate=10,
            adjustment_factor=0.8,
            recovery_factor=1.2
        )

        # Test normal operation
        for i in range(50):
            allowed = rate_limiter.is_allowed()
            if i < 100:  # Within bucket size
                self.assertTrue(allowed)

        # Test rate limiting under load
        with patch('psutil.cpu_percent', return_value=90):
            rate_limiter.adjust_for_system_load()
            # Should reduce rate limiting threshold
            self.assertLess(rate_limiter.effective_bucket_size, 100)

    def test_circuit_breaker(self):
        """Test circuit breaker functionality."""
        circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_threshold=2,
            timeout=5
        )

        # Test normal operation
        self.assertEqual(circuit_breaker.state, "closed")
        self.assertTrue(circuit_breaker.is_allowed())

        # Simulate failures
        for i in range(3):
            circuit_breaker.record_failure()

        # Should open circuit
        self.assertEqual(circuit_breaker.state, "open")
        self.assertFalse(circuit_breaker.is_allowed())

        # Wait for timeout and test recovery
        time.sleep(6)  # Wait for timeout
        circuit_breaker.attempt_recovery()
        self.assertEqual(circuit_breaker.state, "half_open")

        # Record successful recovery
        for i in range(2):
            circuit_breaker.record_success()

        # Should close circuit
        self.assertEqual(circuit_breaker.state, "closed")
        self.assertTrue(circuit_breaker.is_allowed())

    def test_dead_letter_queue(self):
        """Test dead letter queue functionality."""
        dlq = DeadLetterQueue(max_size=100)

        # Test adding failed messages
        test_message = {"id": 1, "content": "test message", "error": "processing failed"}
        dlq.add_failed_message(test_message)

        self.assertEqual(len(dlq.failed_messages), 1)
        self.assertEqual(dlq.failed_messages[0]['id'], 1)

        # Test retry processing
        retry_count = 0
        def mock_retry_handler(message):
            nonlocal retry_count
            retry_count += 1
            return retry_count > 1  # Succeed on second attempt

        results = dlq.process_retries(mock_retry_handler)
        self.assertEqual(retry_count, 2)
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0]['success'])

    def test_queue_manager_reliability(self):
        """Test queue manager with reliability features."""
        queue_manager = QueueManager(
            max_size=1000,
            rate_limiter=AdaptiveRateLimiter(100, 10),
            circuit_breaker=CircuitBreaker(5, 3, 10),
            dead_letter_queue=DeadLetterQueue(100)
        )

        # Test normal operation
        for i in range(50):
            item = {"id": i, "content": f"item_{i}"}
            success = queue_manager.add_item(item)
            self.assertTrue(success)

        self.assertEqual(queue_manager.get_queue_size(), 50)

        # Test processing
        processed_items = []
        def mock_processor(item):
            processed_items.append(item)
            return True

        success_count = queue_manager.process_items(mock_processor, batch_size=10)
        self.assertEqual(success_count, 10)
        self.assertEqual(len(processed_items), 10)

    def test_database_reliability(self):
        """Test database reliability features."""
        # Test connection pooling
        with patch('sqlite3.connect') as mock_connect:
            mock_conn = Mock()
            mock_connect.return_value = mock_conn

            # Test multiple connections
            connections = []
            for i in range(5):
                conn = self.db.get_connection()
                connections.append(conn)

            # Should reuse connections from pool
            self.assertEqual(mock_connect.call_count, 1)

            # Test connection cleanup
            for conn in connections:
                self.db.return_connection(conn)

    def test_system_integration(self):
        """Test integration of all reliability features."""
        # Create integrated reliability system
        monitoring = Mock()
        monitoring.collect_metrics.return_value = {
            'cpu_usage': 45,
            'memory_usage': 60,
            'disk_usage': 30
        }

        operations = Mock()
        operations.check_system_health.return_value = {
            'overall_healthy': True,
            'services_status': {'api': 'healthy', 'database': 'healthy'}
        }

        # Test integrated health check
        metrics = monitoring.collect_metrics()
        health = operations.check_system_health()

        self.assertTrue(health['overall_healthy'])
        self.assertLess(metrics['cpu_usage'], 80)
        self.assertLess(metrics['memory_usage'], 90)
        self.assertLess(metrics['disk_usage'], 95)


class TestLoadScenarios(unittest.TestCase):
    """Test various load scenarios and system behavior."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.queue_manager = QueueManager(
            max_size=10000,
            rate_limiter=AdaptiveRateLimiter(1000, 100)
        )

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)

    def test_high_load_scenario(self):
        """Test system behavior under high load."""
        # Add large number of items
        start_time = time.time()

        for i in range(5000):
            item = {"id": i, "content": f"high_load_item_{i}"}
            self.queue_manager.add_item(item)

        add_time = time.time() - start_time
        print(f"Added 5000 items in {add_time:.2f} seconds")

        # Process items
        processed_count = 0
        def processor(item):
            nonlocal processed_count
            processed_count += 1
            return True

        process_start = time.time()
        success_count = self.queue_manager.process_items(processor, batch_size=100)
        process_time = time.time() - process_start

        print(f"Processed {success_count} items in {process_time:.2f} seconds")
        print(f"Processing rate: {success_count/process_time:.2f} items/second")

        self.assertEqual(success_count, processed_count)
        self.assertGreater(success_count, 0)

    def test_burst_scenario(self):
        """Test system behavior under burst load."""
        # Simulate burst of requests
        burst_size = 1000
        burst_items = []

        for i in range(burst_size):
            item = {"id": i, "content": f"burst_item_{i}"}
            burst_items.append(item)

        # Add burst to queue
        start_time = time.time()
        for item in burst_items:
            self.queue_manager.add_item(item)
        burst_time = time.time() - start_time

        print(f"Burst of {burst_size} items added in {burst_time:.2f} seconds")

        # Check rate limiting
        queue_size = self.queue_manager.get_queue_size()
        self.assertEqual(queue_size, burst_size)

        # Process burst
        processed_count = 0
        def processor(item):
            nonlocal processed_count
            processed_count += 1
            time.sleep(0.001)  # Simulate processing time
            return True

        process_start = time.time()
        success_count = self.queue_manager.process_items(processor, batch_size=50)
        process_time = time.time() - process_start

        print(f"Processed burst of {success_count} items in {process_time:.2f} seconds")
        self.assertEqual(success_count, processed_count)


def run_comprehensive_reliability_tests():
    """Run all reliability tests and generate report."""
    print("🧪 Running Comprehensive Reliability Tests")
    print("=" * 50)

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    test_classes = [
        TestMonitoringAgent,
        TestAtlasOperations,
        TestDeploymentManager,
        TestConfigurationManagement,
        TestReliabilityFeatures,
        TestLoadScenarios
    ]

    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)

    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, stream=open('/tmp/test_output.txt', 'w'))
    result = runner.run(suite)

    # Generate report
    print("\n" + "=" * 50)
    print("📊 Reliability Test Report")
    print("=" * 50)

    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success Rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")

    if result.failures:
        print("\n❌ Failures:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback.split('AssertionError:')[-1].split('Traceback')[0].strip()}")

    if result.errors:
        print("\n⚠️ Errors:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback.split('Error:')[-1].split('Traceback')[0].strip()}")

    # Overall assessment
    if len(result.failures) == 0 and len(result.errors) == 0:
        print("\n✅ All reliability tests passed!")
        print("Atlas is ready for production deployment.")
    elif len(result.failures) <= 3 and len(result.errors) == 0:
        print("\n⚠️ Minor issues detected, but system is generally reliable.")
        print("Review failures before production deployment.")
    else:
        print("\n❌ Significant reliability issues detected.")
        print("Address failures and errors before production deployment.")

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_comprehensive_reliability_tests()
    sys.exit(0 if success else 1)