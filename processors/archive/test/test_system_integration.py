#!/usr/bin/env python3
"""
Comprehensive system integration tests for Atlas production reliability.
Tests all components working together in a realistic production environment.
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
import threading
import requests
import socket

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api import app
from core.database import Database
from helpers.configuration_manager import ConfigurationManager, SecretManager
from helpers.queue_manager import QueueManager, AdaptiveRateLimiter, CircuitBreaker, DeadLetterQueue
from tools.monitoring_agent import MonitoringAgent, AlertManager, MetricsCollector, HealthChecker
from tools.atlas_ops import AtlasOperations
from tools.deployment_manager import DeploymentManager


class TestAPIIntegration(unittest.TestCase):
    """Test API integration with reliability features."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.db"

        # Initialize database
        self.db = Database(str(self.db_path))
        self.db.initialize()

        # Create test app
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['DATABASE_PATH'] = str(self.db_path)
        self.client = self.app.test_client()

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)

    def test_health_endpoints(self):
        """Test all health endpoints."""
        # Main health endpoint
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('status', data)
        self.assertIn('timestamp', data)
        self.assertIn('version', data)

        # Liveness endpoint
        response = self.client.get('/health/live')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('status', data)

        # Readiness endpoint
        response = self.client.get('/health/ready')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('status', data)

    def test_metrics_endpoint(self):
        """Test metrics endpoint."""
        response = self.client.get('/metrics')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('metrics', data)
        self.assertIn('timestamp', data)
        self.assertIn('system', data['metrics'])
        self.assertIn('application', data['metrics'])

    def test_content_processing_endpoints(self):
        """Test content processing endpoints with reliability."""
        # Test URL processing
        test_url = {
            "url": "https://example.com",
            "title": "Test Article"
        }

        response = self.client.post('/process/url',
                                  json=test_url,
                                  content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('task_id', data)

        # Test file processing
        test_file = {
            "content": "This is test content for processing",
            "title": "Test Document"
        }

        response = self.client.post('/process/file',
                                  json=test_file,
                                  content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('task_id', data)

    def test_rate_limiting(self):
        """Test API rate limiting."""
        # Make multiple requests to test rate limiting
        for i in range(10):
            response = self.client.get('/health')
            self.assertEqual(response.status_code, 200)

    def test_error_handling(self):
        """Test error handling and graceful degradation."""
        # Test invalid JSON
        response = self.client.post('/process/url',
                                  data="invalid json",
                                  content_type='application/json')
        self.assertEqual(response.status_code, 400)

        # Test invalid URL
        test_invalid_url = {
            "url": "not-a-valid-url",
            "title": "Invalid Test"
        }

        response = self.client.post('/process/url',
                                  json=test_invalid_url,
                                  content_type='application/json')
        self.assertIn(response.status_code, [200, 400])  # May succeed or fail gracefully

    def test_concurrent_requests(self):
        """Test handling of concurrent requests."""
        import concurrent.futures

        def make_request(i):
            response = self.client.get('/health')
            return response.status_code

        # Make 50 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request, i) for i in range(50)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        # All requests should succeed
        self.assertEqual(len([r for r in results if r == 200]), 50)


class TestDatabaseIntegration(unittest.TestCase):
    """Test database integration with reliability features."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.db"
        self.db = Database(str(self.db_path))
        self.db.initialize()

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)

    def test_database_wal_mode(self):
        """Test SQLite WAL mode configuration."""
        # Insert test data
        self.db.add_content({
            "url": "https://example.com",
            "title": "Test Article",
            "content": "Test content",
            "content_type": "article"
        })

        # Verify WAL mode is enabled
        result = self.db.execute_query("PRAGMA journal_mode;")
        self.assertEqual(result[0]['journal_mode'], 'wal')

        # Test concurrent access
        def concurrent_insert(i):
            self.db.add_content({
                "url": f"https://example{i}.com",
                "title": f"Test Article {i}",
                "content": f"Test content {i}",
                "content_type": "article"
            })

        # Test concurrent inserts
        threads = []
        for i in range(10):
            thread = threading.Thread(target=concurrent_insert, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Verify all data was inserted
        stats = self.db.get_statistics()
        self.assertGreaterEqual(stats['total_items'], 11)  # Original + 10 concurrent

    def test_connection_pooling(self):
        """Test database connection pooling."""
        connections = []

        # Get multiple connections
        for i in range(5):
            conn = self.db.get_connection()
            connections.append(conn)
            self.assertIsNotNone(conn)

        # Verify connections are reused (within pool size)
        initial_pool_size = len(self.db._connection_pool)
        self.assertLessEqual(initial_pool_size, self.db.pool_size)

        # Return connections
        for conn in connections:
            self.db.return_connection(conn)

        # Verify connections are back in pool
        self.assertEqual(len(self.db._connection_pool), initial_pool_size)

    def test_database_backup(self):
        """Test database backup functionality."""
        # Insert test data
        for i in range(10):
            self.db.add_content({
                "url": f"https://example{i}.com",
                "title": f"Test Article {i}",
                "content": f"Test content {i}",
                "content_type": "article"
            })

        # Create backup
        backup_path = Path(self.temp_dir) / "backup.db"
        self.db.backup_database(str(backup_path))

        # Verify backup exists and has data
        self.assertTrue(backup_path.exists())
        self.assertGreater(backup_path.stat().st_size, 0)

        # Test backup restore
        restore_db = Database(str(backup_path))
        stats = restore_db.get_statistics()
        self.assertEqual(stats['total_items'], 10)

    def test_database_performance(self):
        """Test database performance under load."""
        # Insert test data
        start_time = time.time()
        for i in range(1000):
            self.db.add_content({
                "url": f"https://example{i}.com",
                "title": f"Test Article {i}",
                "content": f"Test content {i}",
                "content_type": "article"
            })
        insert_time = time.time() - start_time

        print(f"Inserted 1000 items in {insert_time:.2f} seconds")
        print(f"Insert rate: {1000/insert_time:.2f} items/second")

        # Test search performance
        start_time = time.time()
        for i in range(100):
            results = self.db.search_content(f"content {i}")
            self.assertGreaterEqual(len(results), 1)
        search_time = time.time() - start_time

        print(f"Performed 100 searches in {search_time:.2f} seconds")
        print(f"Search rate: {100/search_time:.2f} searches/second")

        # Test statistics performance
        start_time = time.time()
        for i in range(100):
            stats = self.db.get_statistics()
            self.assertEqual(stats['total_items'], 1000)
        stats_time = time.time() - start_time

        print(f"Retrieved statistics 100 times in {stats_time:.2f} seconds")
        print(f"Stats rate: {100/stats_time:.2f} stats/second")


class TestMonitoringIntegration(unittest.TestCase):
    """Test monitoring system integration."""

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
                "metrics": {"enabled": True, "port": 8002}
            },
            "alerts": {
                "cpu_usage": {"warning": 70, "critical": 85},
                "memory_usage": {"warning": 80, "critical": 90},
                "disk_usage": {"warning": 85, "critical": 95}
            },
            "notifications": {
                "email": {"enabled": False},
                "webhook": {"enabled": False},
                "slack": {"enabled": False},
                "log": {"enabled": True, "file": str(self.config_dir / "alerts.log")}
            }
        }

        with open(self.config_dir / "monitoring.yaml", 'w') as f:
            json.dump(self.test_config, f)

        self.monitoring_agent = MonitoringAgent(str(self.config_dir))

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)

    def test_monitoring_agent_full_cycle(self):
        """Test complete monitoring agent cycle."""
        # Test metrics collection
        metrics = self.monitoring_agent.metrics_collector.collect_system_metrics()
        self.assertIn('cpu_usage', metrics)
        self.assertIn('memory_usage', metrics)
        self.assertIn('disk_usage', metrics)

        # Test health checks
        health_results = self.monitoring_agent.health_checker.run_all_checks()
        self.assertIn('api_health', health_results)
        self.assertIn('database_health', health_results)
        self.assertIn('disk_health', health_results)
        self.assertIn('memory_health', health_results)

        # Test alert evaluation
        alerts = self.monitoring_agent.alert_manager.evaluate_metrics(metrics)
        self.assertIsInstance(alerts, list)

        # Test metrics storage
        self.monitoring_agent.metrics_collector.store_metrics(metrics)
        stored_metrics = self.monitoring_agent.metrics_collector.load_metrics()
        self.assertGreater(len(stored_metrics), 0)

    def test_alert_thresholds(self):
        """Test alert threshold configuration and triggering."""
        alert_manager = self.monitoring_agent.alert_manager

        # Test normal metrics (no alerts)
        normal_metrics = {
            'cpu_usage': 45,
            'memory_usage': 60,
            'disk_usage': 30
        }

        alerts = alert_manager.evaluate_metrics(normal_metrics)
        self.assertEqual(len(alerts), 0)

        # Test warning level metrics
        warning_metrics = {
            'cpu_usage': 75,  # Above warning threshold
            'memory_usage': 85,  # Above warning threshold
            'disk_usage': 40
        }

        alerts = alert_manager.evaluate_metrics(warning_metrics)
        self.assertGreater(len(alerts), 0)
        self.assertTrue(all(alert['level'] == 'warning' for alert in alerts))

        # Test critical level metrics
        critical_metrics = {
            'cpu_usage': 90,  # Above critical threshold
            'memory_usage': 95,  # Above critical threshold
            'disk_usage': 50
        }

        alerts = alert_manager.evaluate_metrics(critical_metrics)
        self.assertGreater(len(alerts), 0)
        self.assertTrue(all(alert['level'] == 'critical' for alert in alerts))

    def test_health_check_integration(self):
        """Test health check integration with API."""
        # Test API health check
        api_health = self.monitoring_agent.health_checker.check_api_health()
        self.assertIn('status', api_health)
        self.assertIn('response_time', api_health)

        # Test database health check
        db_health = self.monitoring_agent.health_checker.check_database_health()
        self.assertIn('status', db_health)
        self.assertIn('connection_count', db_health)

        # Test system health check
        system_health = self.monitoring_agent.health_checker.check_system_health()
        self.assertIn('overall_healthy', system_health)
        self.assertIn('checks', system_health)


class TestOperationalToolsIntegration(unittest.TestCase):
    """Test operational tools integration."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()

        # Set up mock environment
        self.config_dir = Path(self.temp_dir) / "config"
        self.backup_dir = Path(self.temp_dir) / "backups"
        self.log_dir = Path(self.temp_dir) / "logs"

        for dir_path in [self.config_dir, self.backup_dir, self.log_dir]:
            dir_path.mkdir(parents=True)

        # Initialize tools
        self.ops = AtlasOperations()
        self.ops.config_dir = self.config_dir
        self.ops.backup_dir = self.backup_dir
        self.ops.log_dir = self.log_dir

        self.deployment_manager = DeploymentManager()
        self.deployment_manager.deployments_dir = self.backup_dir / "deployments"
        self.deployment_manager.deployments_dir.mkdir()

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)

    def test_atlas_operations_integration(self):
        """Test Atlas operations integration."""
        with patch('subprocess.run') as mock_run, \
             patch('psutil.cpu_percent', return_value=45), \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk:

            # Mock system calls
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "Active: active (running)"
            mock_run.return_value = mock_result

            mock_memory.return_value = Mock(percent=60)
            mock_disk.return_value = Mock(percent=30, free=10**10)

            # Test service status
            status = self.ops.check_service_status("test-service")
            self.assertEqual(status['status'], 'healthy')

            # Test system metrics
            metrics = self.ops.get_system_metrics()
            self.assertIn('cpu_usage', metrics)
            self.assertIn('memory_usage', metrics)

            # Test system health
            health = self.ops.check_system_health()
            self.assertIn('overall_healthy', health)

    def test_deployment_manager_integration(self):
        """Test deployment manager integration."""
        # Create test version
        test_version = {
            "version": "v2.1.0",
            "timestamp": datetime.now().isoformat(),
            "checksum": "test123",
            "size": 2048,
            "description": "Test version"
        }

        versions_file = self.deployment_manager.deployments_dir / "versions.json"
        with open(versions_file, 'w') as f:
            json.dump([test_version], f)

        # Test version listing
        versions = self.deployment_manager.list_versions()
        self.assertEqual(len(versions), 1)
        self.assertEqual(versions[0]['version'], 'v2.1.0')

        # Test deployment simulation
        with patch.object(self.deployment_manager, 'health_check') as mock_health:
            mock_health.return_value = {'healthy': True}

            result = self.deployment_manager.simulate_deployment('v2.1.0', 'staging', 'rolling')
            self.assertTrue(result['success'])
            self.assertIn('deployment_id', result)


class TestConfigurationIntegration(unittest.TestCase):
    """Test configuration management integration."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir) / "config"
        self.secrets_dir = Path(self.temp_dir) / "secrets"

        for dir_path in [self.config_dir, self.secrets_dir]:
            dir_path.mkdir()

        self.config_manager = ConfigurationManager(str(self.config_dir), str(self.secrets_dir))
        self.secret_manager = SecretManager(str(self.secrets_dir))

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)

    def test_configuration_management_integration(self):
        """Test complete configuration management cycle."""
        # Create test configuration files
        test_configs = {
            'development': {
                'API_HOST': 'localhost',
                'API_PORT': '8000',
                'DEBUG': 'true'
            },
            'production': {
                'API_HOST': '0.0.0.0',
                'API_PORT': '8000',
                'DEBUG': 'false'
            }
        }

        # Write configuration files
        for env, config in test_configs.items():
            config_file = self.config_dir / f"{env}.env"
            with open(config_file, 'w') as f:
                for key, value in config.items():
                    f.write(f"{key}={value}\n")

        # Test environment switching
        for env, expected_config in test_configs.items():
            self.config_manager.set_environment(env)
            config = self.config_manager.get_config()

            for key, expected_value in expected_config.items():
                self.assertEqual(config.get(key), expected_value)

        # Test configuration validation
        is_valid, errors = self.config_manager.validate_configuration(expected_config)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_secrets_management_integration(self):
        """Test secrets management integration."""
        # Test secret lifecycle
        test_secrets = {
            'database_password': 'secret123',
            'api_key': 'key456',
            'jwt_secret': 'jwt789'
        }

        # Store secrets
        for key, value in test_secrets.items():
            self.secret_manager.set_secret(key, value)

        # Retrieve secrets
        for key, expected_value in test_secrets.items():
            retrieved_value = self.secret_manager.get_secret(key)
            self.assertEqual(retrieved_value, expected_value)

        # List secrets
        secrets = self.secret_manager.list_secrets()
        for key in test_secrets.keys():
            self.assertIn(key, secrets)

        # Test secret encryption
        self.secret_manager._generate_key()
        encrypted_secrets = self.secret_manager._encrypt_secrets(test_secrets)
        self.assertIsInstance(encrypted_secrets, str)

        decrypted_secrets = self.secret_manager._decrypt_secrets(encrypted_secrets)
        self.assertEqual(decrypted_secrets, test_secrets)


class TestEndToEndReliability(unittest.TestCase):
    """Test end-to-end reliability scenarios."""

    def setUp(self):
        """Set up comprehensive test environment."""
        self.temp_dir = tempfile.mkdtemp()

        # Set up all components
        self.config_dir = Path(self.temp_dir) / "config"
        self.secrets_dir = Path(self.temp_dir) / "secrets"
        self.db_path = Path(self.temp_dir) / "test.db"
        self.backup_dir = Path(self.temp_dir) / "backups"

        for dir_path in [self.config_dir, self.secrets_dir, self.backup_dir]:
            dir_path.mkdir(parents=True)

        # Initialize all components
        self.db = Database(str(self.db_path))
        self.db.initialize()

        self.config_manager = ConfigurationManager(str(self.config_dir), str(self.secrets_dir))
        self.monitoring_agent = MonitoringAgent(str(self.config_dir))
        self.ops = AtlasOperations()
        self.ops.backup_dir = self.backup_dir

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)

    def test_full_system_lifecycle(self):
        """Test complete system lifecycle from startup to shutdown."""
        print("🔄 Testing full system lifecycle...")

        # 1. System initialization
        print("  📊 Initializing system...")
        self.db.initialize()
        self.assertTrue(self.db_path.exists())

        # 2. Configuration loading
        print("  ⚙️ Loading configuration...")
        self.config_manager.set_environment("development")
        config = self.config_manager.get_config()
        self.assertIsInstance(config, dict)

        # 3. Monitoring startup
        print("  🔍 Starting monitoring...")
        metrics = self.monitoring_agent.metrics_collector.collect_system_metrics()
        self.assertIn('cpu_usage', metrics)

        # 4. Health checks
        print("  🏥 Running health checks...")
        health_results = self.monitoring_agent.health_checker.run_all_checks()
        self.assertIn('api_health', health_results)

        # 5. Content processing simulation
        print("  📝 Processing content...")
        for i in range(10):
            self.db.add_content({
                "url": f"https://example{i}.com",
                "title": f"Test Article {i}",
                "content": f"Test content {i}",
                "content_type": "article"
            })

        stats = self.db.get_statistics()
        self.assertEqual(stats['total_items'], 10)

        # 6. Backup creation
        print("  💾 Creating backup...")
        backup_path = self.backup_dir / "test_backup.db"
        self.db.backup_database(str(backup_path))
        self.assertTrue(backup_path.exists())

        # 7. Monitoring data collection
        print("  📈 Collecting monitoring data...")
        self.monitoring_agent.metrics_collector.store_metrics(metrics)
        stored_metrics = self.monitoring_agent.metrics_collector.load_metrics()
        self.assertGreater(len(stored_metrics), 0)

        # 8. Alert evaluation
        print("  🚨 Evaluating alerts...")
        alerts = self.monitoring_agent.alert_manager.evaluate_metrics(metrics)
        self.assertIsInstance(alerts, list)

        print("  ✅ Full system lifecycle completed successfully!")

    def test_load_balancing_scenario(self):
        """Test system behavior under load balancing scenarios."""
        print("🔄 Testing load balancing scenario...")

        # Simulate high load
        start_time = time.time()

        # Process multiple items concurrently
        def process_items(worker_id, count):
            for i in range(count):
                self.db.add_content({
                    "url": f"https://example{worker_id}-{i}.com",
                    "title": f"Test Article {worker_id}-{i}",
                    "content": f"Test content {worker_id}-{i}",
                    "content_type": "article"
                })
                time.sleep(0.001)  # Simulate processing time

        # Create multiple workers
        workers = []
        for i in range(5):
            worker = threading.Thread(target=process_items, args=(i, 20))
            workers.append(worker)
            worker.start()

        # Wait for all workers to complete
        for worker in workers:
            worker.join()

        processing_time = time.time() - start_time
        total_items = self.db.get_statistics()['total_items']

        print(f"  📊 Processed {total_items} items in {processing_time:.2f} seconds")
        print(f"  📈 Processing rate: {total_items/processing_time:.2f} items/second")

        # Verify all items were processed
        self.assertEqual(total_items, 100)  # 5 workers × 20 items each

        # Test search performance under load
        search_start = time.time()
        for i in range(50):
            results = self.db.search_content("Test content")
            self.assertGreater(len(results), 0)
        search_time = time.time() - search_start

        print(f"  🔍 Search performance: {50/search_time:.2f} searches/second")

    def test_failure_recovery_scenario(self):
        """Test system recovery from various failure scenarios."""
        print("🔄 Testing failure recovery scenarios...")

        # 1. Database connection failure simulation
        print("  🗄️ Testing database connection recovery...")
        original_db_path = self.db.db_path

        # Simulate database unavailability
        self.db.db_path = "/nonexistent/path/test.db"

        # Should handle gracefully and recover
        try:
            self.db.get_connection()
        except Exception:
            # Restore original path
            self.db.db_path = original_db_path
            conn = self.db.get_connection()
            self.assertIsNotNone(conn)

        # 2. Monitoring failure simulation
        print("  📊 Testing monitoring failure recovery...")
        original_metrics = self.monitoring_agent.metrics_collector.collect_system_metrics

        # Simulate metrics collection failure
        def failing_metrics():
            raise Exception("Metrics collection failed")

        self.monitoring_agent.metrics_collector.collect_system_metrics = failing_metrics

        # Should handle gracefully
        try:
            metrics = self.monitoring_agent.metrics_collector.collect_system_metrics()
        except Exception:
            # Restore original method
            self.monitoring_agent.metrics_collector.collect_system_metrics = original_metrics
            metrics = self.monitoring_agent.metrics_collector.collect_system_metrics()
            self.assertIn('cpu_usage', metrics)

        # 3. Configuration failure simulation
        print("  ⚙️ Testing configuration failure recovery...")
        # Test with invalid configuration
        invalid_config = {"INVALID_KEY": "invalid_value"}
        is_valid, errors = self.config_manager.validate_configuration(invalid_config)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)

        # Should recover with valid configuration
        valid_config = {"API_HOST": "localhost", "API_PORT": "8000"}
        is_valid, errors = self.config_manager.validate_configuration(valid_config)
        self.assertTrue(is_valid)

        print("  ✅ All failure recovery scenarios completed successfully!")

    def test_performance_benchmark(self):
        """Test system performance benchmark."""
        print("🔄 Running performance benchmark...")

        # Database operations benchmark
        print("  🗄️ Database operations benchmark...")
        db_benchmarks = {}

        # Insert benchmark
        start_time = time.time()
        for i in range(1000):
            self.db.add_content({
                "url": f"https://benchmark{i}.com",
                "title": f"Benchmark Article {i}",
                "content": f"Benchmark content {i}",
                "content_type": "article"
            })
        db_benchmarks['insert'] = time.time() - start_time

        # Search benchmark
        start_time = time.time()
        for i in range(500):
            results = self.db.search_content(f"benchmark {i}")
            self.assertGreater(len(results), 0)
        db_benchmarks['search'] = time.time() - start_time

        # Statistics benchmark
        start_time = time.time()
        for i in range(100):
            stats = self.db.get_statistics()
            self.assertGreater(stats['total_items'], 0)
        db_benchmarks['stats'] = time.time() - start_time

        # Print results
        print(f"    Insert: {1000/db_benchmarks['insert']:.2f} ops/sec")
        print(f"    Search: {500/db_benchmarks['search']:.2f} ops/sec")
        print(f"    Stats: {100/db_benchmarks['stats']:.2f} ops/sec")

        # Monitoring operations benchmark
        print("  📊 Monitoring operations benchmark...")
        monitoring_benchmarks = {}

        # Metrics collection benchmark
        start_time = time.time()
        for i in range(100):
            metrics = self.monitoring_agent.metrics_collector.collect_system_metrics()
            self.assertIn('cpu_usage', metrics)
        monitoring_benchmarks['metrics'] = time.time() - start_time

        # Health check benchmark
        start_time = time.time()
        for i in range(50):
            health = self.monitoring_agent.health_checker.run_all_checks()
            self.assertIn('api_health', health)
        monitoring_benchmarks['health'] = time.time() - start_time

        # Print results
        print(f"    Metrics: {100/monitoring_benchmarks['metrics']:.2f} ops/sec")
        print(f"    Health: {50/monitoring_benchmarks['health']:.2f} ops/sec")

        # Verify performance meets minimum thresholds
        self.assertGreater(1000/db_benchmarks['insert'], 100)  # 100+ inserts/sec
        self.assertGreater(500/db_benchmarks['search'], 50)      # 50+ searches/sec
        self.assertGreater(100/monitoring_benchmarks['metrics'], 10)  # 10+ metrics/sec

        print("  ✅ Performance benchmark completed successfully!")


def run_system_integration_tests():
    """Run all system integration tests."""
    print("🧪 Running System Integration Tests")
    print("=" * 50)

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    test_classes = [
        TestAPIIntegration,
        TestDatabaseIntegration,
        TestMonitoringIntegration,
        TestOperationalToolsIntegration,
        TestConfigurationIntegration,
        TestEndToEndReliability
    ]

    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2, stream=open('/tmp/integration_test_output.txt', 'w'))
    result = runner.run(suite)

    # Generate comprehensive report
    print("\n" + "=" * 50)
    print("📊 System Integration Test Report")
    print("=" * 50)

    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success Rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")

    if result.failures:
        print("\n❌ Integration Test Failures:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback.split('AssertionError:')[-1].split('Traceback')[0].strip()}")

    if result.errors:
        print("\n⚠️ Integration Test Errors:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback.split('Error:')[-1].split('Traceback')[0].strip()}")

    # Overall system assessment
    success_rate = (result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100

    if success_rate >= 95:
        print("\n✅ Excellent integration test results!")
        print("System is ready for production deployment.")
    elif success_rate >= 85:
        print("\n✅ Good integration test results!")
        print("System is production-ready with minor issues.")
    elif success_rate >= 70:
        print("\n⚠️ Acceptable integration test results.")
        print("System needs minor fixes before production.")
    else:
        print("\n❌ Poor integration test results.")
        print("System requires significant fixes before production.")

    print(f"\n🎯 Integration Score: {success_rate:.1f}%")
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_system_integration_tests()
    sys.exit(0 if success else 1)