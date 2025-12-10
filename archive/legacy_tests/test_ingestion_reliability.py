"""
Test Atlas Ingestion Reliability Manager
Production-grade reliability tests for ingestion system.
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from helpers.ingestion_reliability_manager import (
    IngestionReliabilityManager,
    AdaptiveRateLimiter,
    PredictiveScaling,
    HealthStatus
)


class TestAdaptiveRateLimiter:
    """Test adaptive rate limiter functionality."""

    def test_initial_state(self):
        """Test initial rate limiter state."""
        limiter = AdaptiveRateLimiter(initial_rate=100, burst_size=50)
        assert limiter.max_rate == 100
        assert limiter.burst_size == 50
        assert limiter.current_tokens == 50
        assert limiter.refill_rate == 100 / 60.0

    def test_single_token_acquisition(self):
        """Test single token acquisition."""
        limiter = AdaptiveRateLimiter(initial_rate=100, burst_size=50)
        assert limiter.acquire(1) == True
        assert limiter.current_tokens == 49

    def test_burst_acquisition(self):
        """Test burst token acquisition."""
        limiter = AdaptiveRateLimiter(initial_rate=100, burst_size=50)
        assert limiter.acquire(30) == True
        assert limiter.current_tokens == 20

    def test_burst_limit_exceeded(self):
        """Test burst limit exceeded."""
        limiter = AdaptiveRateLimiter(initial_rate=100, burst_size=50)
        assert limiter.acquire(60) == False
        assert limiter.current_tokens == 50

    def test_rate_adjustment(self):
        """Test rate adjustment."""
        limiter = AdaptiveRateLimiter(initial_rate=100, burst_size=50)
        limiter.adjust_rate(200)
        assert limiter.max_rate == 200
        assert limiter.refill_rate == 200 / 60.0

    def test_token_refill(self):
        """Test token refill over time."""
        limiter = AdaptiveRateLimiter(initial_rate=60, burst_size=10)  # 1 token per second
        limiter.acquire(10)  # Use all tokens
        assert limiter.acquire(1) == False

        # Wait for 2 seconds to get 2 tokens
        time.sleep(2)
        assert limiter.acquire(1) == True
        assert abs(limiter.current_tokens - 1.0) < 0.1


class TestPredictiveScaling:
    """Test predictive scaling functionality."""

    def test_initial_state(self):
        """Test initial predictive scaling state."""
        scaling = PredictiveScaling(history_window=100)
        assert scaling.processing_history == []
        assert scaling.history_window == 100
        assert scaling.prediction_window == 5

    def test_record_processing_time(self):
        """Test recording processing times."""
        scaling = PredictiveScaling(history_window=5)

        # Record some processing times
        for i in range(5):
            scaling.record_processing_time(1.0 + i * 0.5)

        assert len(scaling.processing_history) == 5
        assert scaling.processing_history[0]['duration'] == 1.0
        assert scaling.processing_history[-1]['duration'] == 3.0

    def test_history_window_limit(self):
        """Test history window limit."""
        scaling = PredictiveScaling(history_window=3)

        # Record more than window size
        for i in range(5):
            scaling.record_processing_time(1.0 + i)

        assert len(scaling.processing_history) == 3
        assert scaling.processing_history[0]['duration'] == 3.0  # Oldest removed
        assert scaling.processing_history[-1]['duration'] == 5.0  # Newest kept

    def test_predict_load_insufficient_data(self):
        """Test load prediction with insufficient data."""
        scaling = PredictiveScaling()
        prediction = scaling.predict_load()
        assert prediction == 0.0

    def test_predict_load_simple_average(self):
        """Test load prediction with simple average."""
        scaling = PredictiveScaling()

        # Record some processing times
        for i in range(10):
            scaling.record_processing_time(2.0)

        prediction = scaling.predict_load()
        assert prediction == 2.0

    def test_get_optimal_worker_count(self):
        """Test optimal worker count calculation."""
        scaling = PredictiveScaling()

        # Test high load scenario
        with patch.object(scaling, 'predict_load', return_value=15.0):
            optimal = scaling.get_optimal_worker_count(5)
            assert optimal == 10  # 5 * 2, limited to 20

        # Test low load scenario
        with patch.object(scaling, 'predict_load', return_value=0.5):
            optimal = scaling.get_optimal_worker_count(5)
            assert optimal == 2  # 5 // 2, minimum 1

        # Test normal load scenario
        with patch.object(scaling, 'predict_load', return_value=2.0):
            optimal = scaling.get_optimal_worker_count(5)
            assert optimal == 5  # No change


class TestIngestionReliabilityManager:
    """Test ingestion reliability manager functionality."""

    def setup_method(self):
        """Setup test environment."""
        self.manager = IngestionReliabilityManager()

    def test_initial_state(self):
        """Test initial manager state."""
        assert not self.manager.is_running
        assert self.manager.workers == []
        assert self.manager.retry_budget == 1000
        assert self.manager.metrics.system_health == HealthStatus.HEALTHY

    def test_metrics_calculation(self):
        """Test metrics calculation."""
        metrics = self.manager.metrics

        # Test initial state
        assert metrics.calculate_success_rate() == 0.0
        assert metrics.calculate_failure_rate() == 0.0

        # Add some data
        metrics.total_processed = 100
        metrics.successful_processed = 80
        metrics.failed_processed = 20

        assert metrics.calculate_success_rate() == 80.0
        assert metrics.calculate_failure_rate() == 20.0

    def test_health_status_determination(self):
        """Test health status determination."""
        # Test healthy status
        self.manager.metrics.system_health = HealthStatus.HEALTHY
        assert self.manager.metrics.system_health == HealthStatus.HEALTHY

        # Test degraded status
        self.manager.metrics.system_health = HealthStatus.DEGRADED
        assert self.manager.metrics.system_health == HealthStatus.DEGRADED

    @patch('helpers.ingestion_reliability_manager.QueueManager')
    @patch('helpers.ingestion_reliability_manager.ErrorRecoveryManager')
    @patch('helpers.ingestion_reliability_manager.ResourceManager')
    @patch('helpers.ingestion_reliability_manager.AtlasServiceHealthMonitor')
    def test_initialization_with_mocks(self, mock_health, mock_resource, mock_error, mock_queue):
        """Test initialization with mocked dependencies."""
        manager = IngestionReliabilityManager()

        assert manager.queue_manager == mock_queue.return_value
        assert manager.error_recovery == mock_error.return_value
        assert manager.resource_manager == mock_resource.return_value
        assert manager.health_monitor == mock_health.return_value

    def test_rate_based_on_health_critical(self):
        """Test rate adjustment based on critical health."""
        self.manager.metrics.system_health = HealthStatus.CRITICAL

        with patch.object(self.manager.rate_limiter, 'adjust_rate') as mock_adjust:
            self.manager.adjust_rate_based_on_health()
            mock_adjust.assert_called_once()
            # Should be called with 10% of normal rate
            call_args = mock_adjust.call_args[0][0]
            assert call_args <= 10

    def test_rate_based_on_health_healthy(self):
        """Test rate adjustment based on healthy status."""
        self.manager.metrics.system_health = HealthStatus.HEALTHY

        with patch.object(self.manager.rate_limiter, 'adjust_rate') as mock_adjust:
            self.manager.adjust_rate_based_on_health()
            mock_adjust.assert_called_once_with(100)

    def test_get_reliability_status(self):
        """Test getting reliability status."""
        # Set up some metrics
        self.manager.metrics.total_processed = 100
        self.manager.metrics.successful_processed = 80
        self.manager.metrics.failed_processed = 20
        self.manager.metrics.retry_count = 5
        self.manager.metrics.system_health = HealthStatus.HEALTHY

        status = self.manager.get_reliability_status()

        assert status['system_health'] == 'healthy'
        assert status['success_rate'] == 80.0
        assert status['failure_rate'] == 20.0
        assert status['total_processed'] == 100
        assert status['retry_count'] == 5
        assert 'last_health_check' in status


class TestIngestionReliabilityIntegration:
    """Integration tests for ingestion reliability."""

    def setup_method(self):
        """Setup test environment."""
        self.manager = IngestionReliabilityManager()

    def test_task_processing_with_rate_limiting(self):
        """Test task processing with rate limiting."""
        # Configure a low rate limit for testing
        self.manager.rate_limiter = AdaptiveRateLimiter(initial_rate=10, burst_size=5)

        # Process tasks within rate limit
        for i in range(5):
            task_data = {
                'task_id': f'task_{i}',
                'task_type': 'test',
                'priority': 0
            }
            success = self.manager.process_task(task_data)
            assert success == True

    def test_task_processing_rate_limit_exceeded(self):
        """Test task processing when rate limit is exceeded."""
        # Configure a very low rate limit
        self.manager.rate_limiter = AdaptiveRateLimiter(initial_rate=1, burst_size=2)

        # Process tasks that exceed rate limit
        successes = []
        for i in range(5):
            task_data = {
                'task_id': f'task_{i}',
                'task_type': 'test',
                'priority': 0
            }
            success = self.manager.process_task(task_data)
            successes.append(success)

        # Some should succeed, some should fail
        assert sum(successes) <= 2  # Burst size limit

    @patch('helpers.ingestion_reliability_manager.time.time')
    def test_predictive_scaling_integration(self, mock_time):
        """Test predictive scaling integration."""
        # Mock time to avoid actual waiting
        mock_time.return_value = 1000.0

        # Record some processing times
        for i in range(10):
            self.manager.predictive_scaling.record_processing_time(1.0 + i * 0.1)

        # Test worker count adjustment
        optimal = self.manager.predictive_scaling.get_optimal_worker_count(5)
        assert isinstance(optimal, int)
        assert 1 <= optimal <= 20  # Within configured bounds

    def test_health_check_simulation(self):
        """Test health check simulation."""
        # Mock health check responses
        with patch.object(self.manager, 'queue_manager') as mock_queue:
            with patch.object(self.manager, 'resource_manager') as mock_resource:
                with patch.object(self.manager, 'health_monitor') as mock_health:

                    # Configure mock responses
                    mock_queue.get_queue_health.return_value = {
                        'depth_ratio': 0.3,
                        'healthy': True
                    }
                    mock_resource.get_resource_health.return_value = {
                        'memory_usage': 60,
                        'cpu_usage': 50,
                        'healthy': True
                    }
                    mock_health.get_overall_health.return_value = {
                        'overall_health': 'healthy'
                    }

                    # Run health check
                    self.manager.check_system_health()

                    # Verify health status
                    assert self.manager.metrics.system_health == HealthStatus.HEALTHY


class TestIngestionReliabilityEdgeCases:
    """Test edge cases and error conditions."""

    def setup_method(self):
        """Setup test environment."""
        self.manager = IngestionReliabilityManager()

    def test_empty_metrics_calculation(self):
        """Test metrics calculation with no data."""
        metrics = self.manager.metrics
        assert metrics.calculate_success_rate() == 0.0
        assert metrics.calculate_failure_rate() == 0.0

    def test_worker_scaling_limits(self):
        """Test worker scaling limits."""
        # Test minimum workers
        self.manager.adjust_worker_count(0)
        assert len(self.manager.workers) == 0

        # Test maximum workers (mock the worker creation)
        with patch.object(self.manager, 'add_workers') as mock_add:
            self.manager.adjust_worker_count(25)  # Above max
            mock_add.assert_called_once()
            # Should be limited to max_workers (20)
            call_args = mock_add.call_args[0][0]
            assert call_args <= 20

    def test_retry_budget_management(self):
        """Test retry budget management."""
        initial_budget = self.manager.retry_budget
        assert initial_budget == 1000

        # Test budget reduction (simulated)
        self.manager.retry_budget = 500
        assert self.manager.retry_budget == 500

    def test_config_loading_error_handling(self):
        """Test configuration loading error handling."""
        # Test with non-existent config file
        manager = IngestionReliabilityManager('/nonexistent/config.yaml')
        # Should not raise an error, should use defaults
        assert manager is not None
        assert manager.rate_limiter is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])