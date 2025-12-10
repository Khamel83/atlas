"""
Test Atlas Observability System
Comprehensive tests for monitoring, logging, metrics, and alerting capabilities.
"""

import pytest
import time
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
import json
import tempfile
import os

from helpers.metrics_collector import (
    MetricsCollector,
    get_metrics_collector,
    get_prometheus_metrics,
    get_health_summary
)
from helpers.logging_config import (
    AtlasLogger,
    PerformanceLogger,
    get_logger,
    setup_journald_persistence
)
from helpers.alerting_service import (
    AlertingService,
    Alert,
    AlertInstance,
    get_alerting_service
)
from helpers.monitoring_dashboard_service import (
    ConnectionManager,
    get_all_metrics,
    get_realtime_metrics
)


class TestMetricsCollector:
    """Test metrics collection functionality."""

    def setup_method(self):
        """Setup test environment."""
        self.collector = MetricsCollector()

    def test_initialization(self):
        """Test metrics collector initialization."""
        assert len(self.collector._metrics) > 0
        assert "atlas_queue_pending_total" in self.collector._metrics
        assert "atlas_transcription_rate" in self.collector._metrics
        assert not self.collector._running

    def test_metric_recording(self):
        """Test metric recording functionality."""
        self.collector.record_metric("atlas_queue_pending_total", 100)
        value = self.collector.get_metric_value("atlas_queue_pending_total")
        assert value == 100

    def test_metric_with_labels(self):
        """Test metric recording with labels."""
        labels = {"worker": "transcription"}
        self.collector.record_metric("atlas_queue_pending_total", 50, labels=labels)
        value = self.collector.get_metric_value("atlas_queue_pending_total", labels)
        assert value == 50

    def test_prometheus_export(self):
        """Test Prometheus metrics export."""
        self.collector.record_metric("atlas_queue_pending_total", 100)
        self.collector.record_metric("atlas_transcription_rate", 5.5)

        prometheus_output = self.collector.get_prometheus_metrics()
        assert "# HELP atlas_queue_pending_total" in prometheus_output
        assert "# TYPE atlas_queue_pending_total gauge" in prometheus_output
        assert "atlas_queue_pending_total 100" in prometheus_output

    def test_alert_conditions(self):
        """Test alert condition checking."""
        # Simulate high queue depth
        self.collector.record_metric("atlas_queue_pending_total", 600)
        self.collector.record_metric("atlas_transcription_rate", 0)

        alerts = self.collector.get_alert_conditions()
        assert len(alerts) > 0

        # Check for specific alerts
        queue_alerts = [a for a in alerts if a["condition"] == "high_queue_depth"]
        assert len(queue_alerts) > 0

    def test_health_summary(self):
        """Test health summary generation."""
        self.collector.record_metric("atlas_queue_pending_total", 50)
        self.collector.record_metric("atlas_transcription_rate", 2.5)

        health_summary = self.collector.get_health_summary()
        assert "status" in health_summary
        assert "alerts" in health_summary
        assert "metrics_collected" in health_summary

    @patch('helpers.metrics_collector.psutil')
    def test_system_metrics_collection(self, mock_psutil):
        """Test system metrics collection."""
        # Mock psutil
        mock_process = Mock()
        mock_process.memory_info.return_value = Mock(rss=1024 * 1024 * 100)  # 100MB
        mock_psutil.Process.return_value = mock_process

        mock_psutil.disk_usage.return_value = Mock(free=1024 * 1024 * 1024 * 10)  # 10GB

        self.collector._collect_system_metrics(time.time())

        # Check that metrics were recorded
        memory_value = self.collector.get_metric_value("atlas_memory_usage_bytes")
        assert memory_value is not None


class TestLoggingSystem:
    """Test logging configuration and functionality."""

    def setup_method(self):
        """Setup test environment."""
        self.logger = AtlasLogger("test_component")
        self.temp_dir = tempfile.mkdtemp()
        self.logger.log_dir = self.temp_dir

    def teardown_method(self):
        """Cleanup test environment."""
        # Clean up temporary files
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_logger_initialization(self):
        """Test logger initialization."""
        assert self.logger.component_name == "test_component"
        assert self.logger.logger is not None

    def test_json_logging(self):
        """Test JSON log formatting."""
        self.logger.info("Test message", test_key="test_value")

        # Check log file was created
        log_file = self.temp_dir / "test_component.json.log"
        assert log_file.exists()

        # Check log content
        with open(log_file, 'r') as f:
            log_content = f.read()
            log_entry = json.loads(log_content.strip())

        assert log_entry["message"] == "Test message"
        assert log_entry["component"] == "test_component"
        assert log_entry["level"] == "INFO"

    def test_error_logging(self):
        """Test error logging."""
        self.logger.error("Error message", error_code=500)

        # Check error log file
        error_file = self.temp_dir / "test_component.error.log"
        assert error_file.exists()

    def test_performance_logging(self):
        """Test performance logging."""
        perf_logger = PerformanceLogger()
        perf_logger.logger = self.logger  # Use test logger

        # Mock metrics
        with patch.object(perf_logger, 'metrics') as mock_metrics:
            mock_metrics.get_metric_value.side_effect = lambda metric, default=0: {
                "atlas_disk_free_bytes": 1024 * 1024 * 1024 * 10,
                "atlas_queue_pending_total": 50,
                "atlas_queue_processing_total": 5,
                "atlas_articles_processed_total": 1000,
                "atlas_system_uptime_seconds": 3600
            }.get(metric, default)

            perf_logger.log_performance_snapshot(force=True)

        # Check performance snapshot was logged
        log_file = self.temp_dir / "performance.json.log"
        assert log_file.exists()


class TestAlertingService:
    """Test alerting service functionality."""

    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = self.temp_dir / "alerting.yaml"

        # Create test config
        test_config = {
            "alerts": [
                {
                    "id": "test_alert",
                    "name": "Test Alert",
                    "severity": "warning",
                    "condition": "test_metric > 10",
                    "description": "Test alert condition",
                    "metric_name": "test_metric",
                    "threshold": 10,
                    "operator": "gt",
                    "duration": 60,
                    "cooldown": 300,
                    "enabled": True,
                    "channels": ["log"]
                }
            ],
            "notifications": {}
        }

        with open(self.config_file, 'w') as f:
            json.dump(test_config, f)

        self.alerting_service = AlertingService(str(self.config_file))

    def teardown_method(self):
        """Cleanup test environment."""
        import shutil
        self.alerting_service.stop_alerting()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_alert_loading(self):
        """Test alert configuration loading."""
        assert len(self.alerting_service.alerts) == 1
        assert "test_alert" in self.alerting_service.alerts

    def test_alert_creation(self):
        """Test creating new alerts."""
        new_alert = Alert(
            id="new_test_alert",
            name="New Test Alert",
            severity="critical",
            condition="new_metric > 5",
            description="New test alert",
            metric_name="new_metric",
            threshold=5,
            operator="gt",
            duration=30,
            cooldown=120
        )

        self.alerting_service.add_alert(new_alert)
        assert "new_test_alert" in self.alerting_service.alerts

    def test_alert_removal(self):
        """Test removing alerts."""
        self.alerting_service.remove_alert("test_alert")
        assert "test_alert" not in self.alerting_service.alerts

    def test_alert_evaluation(self):
        """Test alert condition evaluation."""
        alert = self.alerting_service.alerts["test_alert"]

        # Test condition evaluation
        assert self.alerting_service._evaluate_condition(15, alert)  # 15 > 10
        assert not self.alerting_service._evaluate_condition(5, alert)  # 5 <= 10

    @pytest.mark.asyncio
    async def test_alert_triggering(self):
        """Test alert triggering logic."""
        # Mock metrics collector
        with patch('helpers.alerting_service.get_metrics_collector') as mock_get_metrics:
            mock_collector = Mock()
            mock_collector.get_metric_value.return_value = 15  # Above threshold
            mock_get_metrics.return_value = mock_collector

            # Trigger alert check
            await self.alerting_service._check_all_alerts()

            # Check alert was triggered
            assert "test_alert" in self.alerting_service.active_alerts

    @pytest.mark.asyncio
    async def test_alert_resolution(self):
        """Test alert resolution logic."""
        # First trigger an alert
        with patch('helpers.alerting_service.get_metrics_collector') as mock_get_metrics:
            mock_collector = Mock()
            mock_collector.get_metric_value.return_value = 15  # Above threshold
            mock_get_metrics.return_value = mock_collector

            await self.alerting_service._check_all_alerts()
            assert "test_alert" in self.alerting_service.active_alerts

            # Now resolve it
            mock_collector.get_metric_value.return_value = 5  # Below threshold
            await self.alerting_service._check_all_alerts()
            assert "test_alert" not in self.alerting_service.active_alerts

    def test_alert_status(self):
        """Test alert status reporting."""
        status = self.alerting_service.get_alert_status()
        assert "total_alerts" in status
        assert "enabled_alerts" in status
        assert "active_alerts" in status
        assert "alerts_by_severity" in status

    @pytest.mark.asyncio
    async def test_log_notification(self):
        """Test log notification channel."""
        alert = self.alerting_service.alerts["test_alert"]
        alert_instance = AlertInstance(
            alert_id="test_alert",
            triggered_at=time.time(),
            current_value=15
        )

        await self.alerting_service._log_notification(alert, alert_instance)
        # Log notification should complete without errors


class TestMonitoringDashboard:
    """Test monitoring dashboard functionality."""

    def setup_method(self):
        """Setup test environment."""
        self.connection_manager = ConnectionManager()

    def test_connection_manager(self):
        """Test WebSocket connection manager."""
        assert len(self.connection_manager.active_connections) == 0

    @patch('helpers.monitoring_dashboard_service.get_metrics_collector')
    @patch('helpers.monitoring_dashboard_service.get_health_summary')
    @patch('helpers.monitoring_dashboard_service.get_queue_status')
    def test_metrics_data_generation(self, mock_queue, mock_health, mock_metrics):
        """Test metrics data generation for dashboard."""
        # Mock data
        mock_metrics.return_value.get_metric_value.side_effect = lambda metric: {
            "atlas_queue_pending_total": 100,
            "atlas_transcription_rate": 5.5,
            "atlas_memory_usage_bytes": 1024 * 1024 * 100,
            "atlas_system_uptime_seconds": 3600
        }.get(metric, 0)

        mock_health.return_value = {
            "status": "healthy",
            "alerts": []
        }

        mock_queue.return_value = {
            "queue_counts": {"pending": 100, "processing": 5}
        }

        data = get_realtime_metrics()
        assert "type" in data
        assert "data" in data
        assert data["type"] == "metrics_update"

    @patch('helpers.monitoring_dashboard_service.get_metrics_collector')
    def test_all_metrics_collection(self, mock_metrics):
        """Test all metrics collection."""
        mock_metrics.return_value._metrics = {
            "test_metric": Mock(
                metric_type="gauge",
                help_text="Test metric",
                points=[]
            )
        }
        mock_metrics.return_value.get_metric_value.return_value = 10

        metrics = get_all_metrics(mock_metrics.return_value)
        assert "test_metric" in metrics
        assert metrics["test_metric"]["value"] == 10


class TestObservabilityIntegration:
    """Integration tests for observability components."""

    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Cleanup test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_end_to_end_metrics_flow(self):
        """Test complete metrics flow from collection to export."""
        collector = MetricsCollector()

        # Record some metrics
        collector.record_metric("atlas_queue_pending_total", 150)
        collector.record_metric("atlas_transcription_rate", 3.2)

        # Check they were recorded
        assert collector.get_metric_value("atlas_queue_pending_total") == 150
        assert collector.get_metric_value("atlas_transcription_rate") == 3.2

        # Check Prometheus export
        prometheus_output = collector.get_prometheus_metrics()
        assert "atlas_queue_pending_total 150" in prometheus_output
        assert "atlas_transcription_rate 3.2" in prometheus_output

        # Check health summary
        health = collector.get_health_summary()
        assert health["status"] in ["healthy", "warning", "critical"]

    def test_logging_with_metrics(self):
        """Test logging with integrated metrics."""
        logger = AtlasLogger("integration_test")
        logger.log_dir = self.temp_dir

        # Log a message
        logger.info("Integration test message", test_value=123)

        # Check log file
        log_file = self.temp_dir / "integration_test.json.log"
        assert log_file.exists()

        with open(log_file, 'r') as f:
            log_entry = json.loads(f.read().strip())

        assert log_entry["message"] == "Integration test message"
        assert log_entry["test_value"] == 123

    @pytest.mark.asyncio
    async def test_alerting_with_metrics(self):
        """Test alerting system with real metrics."""
        config_file = self.temp_dir / "alerting.yaml"
        test_config = {
            "alerts": [
                {
                    "id": "integration_test_alert",
                    "name": "Integration Test Alert",
                    "severity": "warning",
                    "condition": "queue_depth > 100",
                    "description": "Test condition",
                    "metric_name": "atlas_queue_pending_total",
                    "threshold": 100,
                    "operator": "gt",
                    "duration": 0,
                    "cooldown": 0,
                    "enabled": True,
                    "channels": ["log"]
                }
            ],
            "notifications": {}
        }

        with open(config_file, 'w') as f:
            json.dump(test_config, f)

        alerting_service = AlertingService(str(config_file))

        # Mock metrics to trigger alert
        with patch('helpers.alerting_service.get_metrics_collector') as mock_get_metrics:
            mock_collector = Mock()
            mock_collector.get_metric_value.return_value = 150  # Above threshold
            mock_get_metrics.return_value = mock_collector

            await alerting_service._check_all_alerts()

            # Check alert was triggered
            assert "integration_test_alert" in alerting_service.active_alerts

        alerting_service.stop_alerting()

    def test_global_instances(self):
        """Test global service instances."""
        # Test metrics collector
        metrics1 = get_metrics_collector()
        metrics2 = get_metrics_collector()
        assert metrics1 is metrics2  # Same instance

        # Test alerting service
        alerting1 = get_alerting_service()
        alerting2 = get_alerting_service()
        assert alerting1 is alerting2  # Same instance

        # Test logger
        logger1 = get_logger("test")
        logger2 = get_logger("test")
        assert logger1 is logger2  # Same instance for same component


if __name__ == "__main__":
    pytest.main([__file__, "-v"])