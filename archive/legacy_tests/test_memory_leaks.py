#!/usr/bin/env python3
"""
Memory Leak Detection Test Suite
Verifies that the bulletproof process manager prevents memory leaks
"""
import pytest
import psutil
import time
import threading
from helpers.bulletproof_process_manager import get_manager, create_managed_process

class TestMemoryLeaks:
    def test_no_subprocess_memory_leaks(self):
        """Test that subprocess creation doesn't leak memory"""
        manager = get_manager()
        initial_memory = psutil.Process().memory_info().rss

        # Create and cleanup 10 processes
        for i in range(10):
            process = create_managed_process(['echo', f'test_{i}'], f'test_process_{i}')
            process.wait()
            manager.kill_process(process.pid)
            time.sleep(0.1)

        final_memory = psutil.Process().memory_info().rss
        memory_growth_mb = (final_memory - initial_memory) / (1024 * 1024)

        # Should not grow more than 10MB
        assert memory_growth_mb < 10, f"Memory grew by {memory_growth_mb:.1f}MB"

    def test_process_tree_cleanup(self):
        """Test that child processes are properly cleaned up"""
        # Create a process that spawns children
        process = create_managed_process(['bash', '-c', 'sleep 5 & sleep 5 & wait'], 'multi_process_test')
        time.sleep(1)  # Let children spawn

        manager = get_manager()
        manager.kill_process(process.pid)
        time.sleep(2)  # Allow cleanup

        # Verify no orphaned processes
        for proc in psutil.process_iter(['pid', 'cmdline']):
            if proc.info['cmdline'] and 'sleep 5' in ' '.join(proc.info['cmdline']):
                pytest.fail(f"Found orphaned process: {proc.info}")

    @pytest.mark.limit_memory("256 MB")
    def test_memory_growth_under_load(self):
        """Test memory usage under process creation load"""
        manager = get_manager()
        processes = []

        # Create 20 concurrent processes
        for i in range(20):
            proc = create_managed_process(['sleep', '2'], f'load_test_{i}')
            processes.append(proc)

        # Wait for all to complete
        for proc in processes:
            proc.wait()

        # Cleanup
        for proc in processes:
            manager.kill_process(proc.pid)
