#!/usr/bin/env python3
"""
System Endurance Test Suite
Tests long-term stability and resource management
"""
import pytest
import time
import threading
from helpers.bulletproof_process_manager import get_manager, create_managed_process
from helpers.resource_monitor import check_system_health

class TestSystemEndurance:
    def test_continuous_operation_stability(self):
        """Test system stability over extended operation (5 minutes)"""
        manager = get_manager()
        end_time = time.time() + 300  # 5 minutes
        process_count = 0

        while time.time() < end_time:
            # Create short-lived processes continuously
            proc = create_managed_process(['echo', f'test_{process_count}'], f'endurance_{process_count}')
            proc.wait()
            manager.kill_process(proc.pid)
            process_count += 1
            time.sleep(0.5)

        # Verify system is still healthy
        assert check_system_health(), "System health check failed after endurance test"
        assert process_count > 100, f"Only created {process_count} processes in 5 minutes"

    def test_memory_stability_under_load(self):
        """Test memory remains stable under continuous load"""
        import psutil
        initial_memory = psutil.Process().memory_info().rss

        # Run load for 2 minutes
        end_time = time.time() + 120
        while time.time() < end_time:
            processes = []
            for i in range(5):
                proc = create_managed_process(['sleep', '1'], f'memory_load_{i}')
                processes.append(proc)

            for proc in processes:
                proc.wait()

            time.sleep(1)

        final_memory = psutil.Process().memory_info().rss
        growth_mb = (final_memory - initial_memory) / (1024 * 1024)

        assert growth_mb < 50, f"Memory grew by {growth_mb:.1f}MB during load test"

    @pytest.mark.slow
    def test_service_restart_resilience(self):
        """Test that services can be restarted without issues"""
        manager = get_manager()

        # Create some processes
        processes = []
        for i in range(3):
            proc = create_managed_process(['sleep', '30'], f'restart_test_{i}')
            processes.append(proc)

        # Simulate service restart
        manager.cleanup_all()

        # Verify all processes are cleaned up
        time.sleep(2)
        remaining = [p for p in processes if p.poll() is None]
        assert len(remaining) == 0, f"{len(remaining)} processes not cleaned up"
