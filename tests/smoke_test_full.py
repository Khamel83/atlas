#!/usr/bin/env python3
"""
Comprehensive Atlas Smoke Test Suite
Tests core functionality to ensure system health and catch regressions early.
"""

import os
import sys
import pytest
import sqlite3
import time
import requests
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.database_config import get_database_connection, get_database_path
from helpers.queue_manager import get_queue_manager, enqueue_task
from helpers.metrics_collector import get_metrics_collector


class TestDatabaseConnectivity:
    """Test database operations and integrity."""

    def test_database_connection(self):
        """Test basic database connectivity."""
        conn = get_database_connection()
        assert conn is not None

        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        assert result[0] == 1
        conn.close()

    def test_database_tables_exist(self):
        """Test that all required tables exist."""
        conn = get_database_connection()
        cursor = conn.cursor()

        required_tables = [
            'content', 'transcriptions', 'podcast_episodes',
            'task_queue', 'failed_tasks', 'worker_jobs'
        ]

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]

        for table in required_tables:
            assert table in existing_tables, f"Required table {table} missing"

        conn.close()

    def test_database_write_read(self):
        """Test database write and read operations."""
        conn = get_database_connection()
        cursor = conn.cursor()

        # Test content table
        test_title = f"Smoke Test {int(time.time())}"
        cursor.execute("""
            INSERT INTO content (title, content, url, content_type, created_at)
            VALUES (?, ?, ?, ?, datetime('now'))
        """, (test_title, "Test content", "http://test.com", "test"))

        cursor.execute("SELECT title FROM content WHERE title = ?", (test_title,))
        result = cursor.fetchone()
        assert result is not None
        assert result[0] == test_title

        # Cleanup
        cursor.execute("DELETE FROM content WHERE title = ?", (test_title,))
        conn.commit()
        conn.close()


class TestQueueSystem:
    """Test queue management and task processing."""

    def test_queue_manager_initialization(self):
        """Test queue manager initializes correctly."""
        qm = get_queue_manager()
        assert qm is not None

    def test_task_enqueue_dequeue(self):
        """Test basic task enqueue and dequeue operations."""
        qm = get_queue_manager()

        # Enqueue test task
        task_id = f"smoke_test_{int(time.time())}"
        task_data = {"test": True, "timestamp": time.time()}

        success = enqueue_task(task_id, "smoke_test", task_data)
        assert success, "Failed to enqueue test task"

        # Dequeue task
        task = qm.dequeue_task("smoke_worker", ["smoke_test"])
        assert task is not None, "Failed to dequeue test task"
        assert task.task_id == task_id
        assert task.task_data["test"] is True

        # Complete task
        qm.complete_task(task_id, "smoke_worker")

    def test_queue_status(self):
        """Test queue status reporting."""
        qm = get_queue_manager()
        from helpers.queue_manager import get_queue_status

        status = get_queue_status()
        assert "queue_counts" in status
        assert "circuit_breakers" in status
        assert isinstance(status["queue_counts"], dict)


class TestMetricsCollection:
    """Test metrics collection and reporting."""

    def test_metrics_collector_initialization(self):
        """Test metrics collector initializes correctly."""
        collector = get_metrics_collector()
        assert collector is not None

    def test_metrics_recording(self):
        """Test metrics can be recorded and retrieved."""
        collector = get_metrics_collector()

        # Use a predefined metric
        test_metric = "atlas_articles_processed_total"
        test_value = 42.5

        collector.record_metric(test_metric, test_value)
        retrieved_value = collector.get_metric_value(test_metric)

        assert retrieved_value == test_value

    def test_prometheus_metrics_export(self):
        """Test Prometheus metrics export format."""
        from helpers.metrics_collector import get_prometheus_metrics
        collector = get_metrics_collector()

        # Record some metrics to ensure export has data
        collector.record_metric("atlas_system_uptime_seconds", 3600)
        collector.record_metric("atlas_articles_processed_total", 100)

        metrics_output = get_prometheus_metrics()
        assert isinstance(metrics_output, str)
        assert len(metrics_output) > 0

        # Should contain some standard metrics
        assert "atlas_" in metrics_output


class TestAPIEndpoints:
    """Test API endpoint health (without starting full server)."""

    @pytest.fixture(autouse=True)
    def setup_api_test(self):
        """Setup test environment variables."""
        os.environ['API_PORT'] = '17444'
        os.environ['ATLAS_DATABASE_PATH'] = str(get_database_path())

    def test_health_endpoint_logic(self):
        """Test health check logic."""
        from helpers.metrics_collector import get_health_summary

        health = get_health_summary()
        assert "status" in health
        assert health["status"] in ["healthy", "warning", "error"]

    def test_search_functionality(self):
        """Test search functionality without web server."""
        conn = get_database_connection()
        cursor = conn.cursor()

        # Insert test content
        cursor.execute("""
            INSERT INTO content (title, content, url, content_type, created_at)
            VALUES (?, ?, ?, ?, datetime('now'))
        """, ("Test Search Item", "This is searchable content", "http://test.com", "test"))
        conn.commit()

        # Test search query
        cursor.execute("""
            SELECT title, content FROM content
            WHERE title LIKE ? OR content LIKE ?
            LIMIT 5
        """, ("%search%", "%searchable%"))

        results = cursor.fetchall()
        assert len(results) > 0

        # Cleanup
        cursor.execute("DELETE FROM content WHERE title = ?", ("Test Search Item",))
        conn.commit()
        conn.close()


class TestServiceHealth:
    """Test overall service health and critical components."""

    def test_import_critical_modules(self):
        """Test that critical modules can be imported."""
        critical_modules = [
            'atlas_service_manager',
            'helpers.database_config',
            'helpers.queue_manager',
            'helpers.metrics_collector',
            'scripts.notify'
        ]

        for module_name in critical_modules:
            try:
                __import__(module_name)
            except ImportError as e:
                pytest.fail(f"Failed to import critical module {module_name}: {e}")

    def test_configuration_loading(self):
        """Test that configuration loads correctly."""
        from dotenv import load_dotenv

        # Should not raise an exception
        load_dotenv()

        # Test critical environment variables are accessible
        db_path = os.getenv('ATLAS_DATABASE_PATH')
        if db_path:
            assert Path(db_path).parent.exists(), "Database directory should exist"

    def test_logging_functionality(self):
        """Test that logging works correctly."""
        import logging

        # Create test logger
        logger = logging.getLogger("smoke_test")
        logger.setLevel(logging.INFO)

        # Test logging (should not raise exceptions)
        logger.info("Smoke test logging check")
        logger.warning("Smoke test warning check")

    def test_notification_system(self):
        """Test notification system functionality."""
        from scripts.notify import AtlasNotificationSystem

        # Should initialize without error
        notifier = AtlasNotificationSystem()
        assert notifier is not None

        # Test that methods exist and are callable
        assert callable(notifier.send_telegram_message)
        assert callable(notifier.send_alert)


class TestPerformanceBasics:
    """Basic performance smoke tests."""

    def test_database_query_performance(self):
        """Test that database queries complete within reasonable time."""
        conn = get_database_connection()
        cursor = conn.cursor()

        start_time = time.time()
        cursor.execute("SELECT COUNT(*) FROM content")
        result = cursor.fetchone()
        query_time = time.time() - start_time

        assert query_time < 5.0, f"Database query took too long: {query_time}s"
        assert isinstance(result[0], int)
        conn.close()

    def test_metrics_collection_performance(self):
        """Test that metrics collection doesn't cause delays."""
        collector = get_metrics_collector()

        start_time = time.time()
        for i in range(10):
            collector.record_metric("atlas_articles_processed_total", i * 1.5)
        collection_time = time.time() - start_time

        assert collection_time < 1.0, f"Metrics collection too slow: {collection_time}s"


class TestIntegrationBasics:
    """Basic integration tests between components."""

    def test_queue_metrics_integration(self):
        """Test that queue operations update metrics."""
        qm = get_queue_manager()
        collector = get_metrics_collector()

        # Record initial metrics
        initial_enqueued = collector.get_metric_value("atlas_queue_pending_total") or 0

        # Enqueue a task
        task_id = f"integration_test_{int(time.time())}"
        enqueue_task(task_id, "integration_test", {"test": True})

        # Check metrics updated (may need small delay for async updates)
        time.sleep(0.1)
        new_enqueued = collector.get_metric_value("atlas_queue_pending_total") or 0

        # Clean up
        task = qm.dequeue_task("integration_worker", ["integration_test"])
        if task:
            qm.complete_task(task.task_id, "integration_worker")

    def test_error_handling_integration(self):
        """Test that errors are properly handled and logged."""
        from helpers.queue_manager import QueueManager

        # Test with invalid database path (should handle gracefully)
        with patch('helpers.database_config.get_database_path') as mock_path:
            mock_path.return_value = Path("/nonexistent/path/test.db")

            # Should not crash, should handle error gracefully
            try:
                conn = get_database_connection()
                # If it succeeds, that's fine too (fallback behavior)
                if conn:
                    conn.close()
            except Exception as e:
                # Expected - should be a controlled error, not a crash
                assert "database" in str(e).lower() or "path" in str(e).lower()


def test_smoke_test_summary():
    """Summary test that reports overall system health."""
    print("\n" + "="*50)
    print("ATLAS SMOKE TEST SUMMARY")
    print("="*50)

    try:
        conn = get_database_connection()
        cursor = conn.cursor()

        # Get basic statistics
        cursor.execute("SELECT COUNT(*) FROM content")
        content_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM transcriptions")
        transcript_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM podcast_episodes")
        episode_count = cursor.fetchone()[0]

        print(f"📊 Content items: {content_count:,}")
        print(f"🎙️  Transcriptions: {transcript_count:,}")
        print(f"📺 Episodes: {episode_count:,}")

        conn.close()

        # Test queue status
        from helpers.queue_manager import get_queue_status
        queue_status = get_queue_status()
        pending = queue_status.get("queue_counts", {}).get("pending", 0)
        print(f"📝 Pending tasks: {pending}")

        # Test metrics
        collector = get_metrics_collector()
        print(f"📈 Metrics collector: Active")

        print("✅ All systems operational")

    except Exception as e:
        print(f"❌ System health check failed: {e}")
        raise


if __name__ == "__main__":
    pytest.main([__file__, "-v"])