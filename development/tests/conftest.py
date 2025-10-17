import pytest
import psutil
import os

@pytest.fixture(autouse=True)
def memory_leak_detector():
    """Automatically detect memory leaks in tests"""
    initial_memory = psutil.Process().memory_info().rss
    yield
    final_memory = psutil.Process().memory_info().rss

    growth_mb = (final_memory - initial_memory) / (1024 * 1024)
    if growth_mb > 10:  # Alert if test grows memory by >10MB
        pytest.fail(f"Test caused memory leak: {growth_mb:.1f}MB growth")
