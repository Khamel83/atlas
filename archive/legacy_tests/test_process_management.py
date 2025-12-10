#!/usr/bin/env python3
"""
Process Management Test Suite
Tests all aspects of bulletproof process management
"""
import pytest
import time
import signal
from helpers.bulletproof_process_manager import get_manager, create_managed_process

class TestProcessManagement:
    def test_concurrent_process_creation(self):
        """Test creating multiple processes concurrently"""
        manager = get_manager()
        processes = []

        # Create 5 processes simultaneously
        for i in range(5):
            proc = create_managed_process(['sleep', '3'], f'concurrent_{i}')
            processes.append(proc)

        # Verify all are running
        assert len(manager.get_status()['processes']) >= 5

        # Cleanup
        for proc in processes:
            manager.kill_process(proc.pid)

    def test_process_timeout_handling(self):
        """Test that processes respect timeout limits"""
        # Create process with 2-second timeout
        process = create_managed_process(['sleep', '10'], 'timeout_test', timeout=2)

        start_time = time.time()
        process.wait()  # Should be killed by timeout
        elapsed = time.time() - start_time

        # Should complete within 3 seconds (2s timeout + 1s buffer)
        assert elapsed < 3, f"Process ran for {elapsed:.1f}s, expected ~2s"

    def test_circuit_breaker_prevents_runaway(self):
        """Test that circuit breaker stops failing operations"""
        manager = get_manager()

        # Trigger multiple failures
        for i in range(10):
            try:
                create_managed_process(['nonexistent_command'], 'single_circuit_breaker_test')
            except:
                pass  # Expected to fail

        # Circuit breaker should be open now
        status = manager.get_status()
        circuit_states = [cb['state'] for cb in status['circuit_breakers'].values()]
        assert 'OPEN' in circuit_states, "Circuit breaker should be open after failures"
