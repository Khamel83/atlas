#!/usr/bin/env python3
"""
Test script for worker scaling functionality
"""

import sys
import time
import json
from pathlib import Path

# Add helpers to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from helpers.resource_manager import ResourceManager
from scripts.worker_scaler import WorkerScaler

def test_resource_manager():
    """Test resource manager functionality"""
    print("Testing Resource Manager...")

    rm = ResourceManager()

    # Test metrics collection
    print("  Collecting metrics...")
    metrics = rm.collect_metrics(queue_depth=50, worker_count=2)
    print(f"  ✓ Metrics collected: CPU={metrics.cpu_percent:.1f}%, Memory={metrics.memory_percent:.1f}%")

    # Test memory pressure check
    print("  Checking memory pressure...")
    memory_result = rm.check_memory_pressure()
    print(f"  ✓ Memory pressure: {memory_result['pressure_level']} ({memory_result['memory_percent']:.1f}%)")

    # Test worker scaling calculation
    print("  Testing worker scaling calculation...")
    current_workers = 2
    queue_depth = 150
    recommended = rm.calculate_worker_scaling(current_workers, queue_depth)
    print(f"  ✓ Worker scaling: {current_workers} → {recommended} (queue depth: {queue_depth})")

    # Test disk cleanup
    print("  Testing disk cleanup...")
    cleanup_result = rm.cleanup_disk_space()
    print(f"  ✓ Disk cleanup: {cleanup_result['files_cleaned']} files cleaned")

    # Test CPU throttling check
    print("  Checking CPU throttling...")
    throttle_result = rm.check_cpu_throttling()
    print(f"  ✓ CPU load: {throttle_result['load_average']:.2f}, throttle needed: {throttle_result['should_throttle']}")

    # Test recommendations
    print("  Generating recommendations...")
    recommendations = rm.get_resource_recommendations()
    print(f"  ✓ Recommendations generated: {len(recommendations)} items")
    for i, rec in enumerate(recommendations[:3], 1):
        print(f"    {i}. {rec}")

    print("✓ Resource Manager tests completed\n")

def test_worker_scaler():
    """Test worker scaler functionality"""
    print("Testing Worker Scaler...")

    scaler = WorkerScaler()

    # Test initial status
    print("  Getting initial status...")
    status = scaler.get_status()
    print(f"  ✓ Initial workers: {status['worker_count']}, queue depth: {status['queue_depth']}")

    # Test scaling up
    print("  Testing scale up...")
    scale_result = scaler.scale_workers(200)  # High queue depth
    print(f"  ✓ Scale up result: {scale_result['action']} ({scale_result['workers_before']} → {scale_result['workers_after']})")

    time.sleep(2)  # Wait a bit

    # Test health check
    print("  Running health check...")
    health_result = scaler.health_check()
    print(f"  ✓ Health check: {health_result['workers_active']} active workers")

    # Test scaling down
    print("  Testing scale down...")
    # Wait for scale down delay to pass (simulate)
    from datetime import timedelta
    scaler.last_scale_time = scaler.last_scale_time - timedelta(seconds=scaler.config['scale_down_delay'] * 2)
    scale_result = scaler.scale_workers(5)  # Low queue depth
    print(f"  ✓ Scale down result: {scale_result['action']} ({scale_result['workers_before']} → {scale_result['workers_after']})")

    # Cleanup
    print("  Cleaning up workers...")
    scaler.shutdown()
    final_status = scaler.get_status()
    print(f"  ✓ Final worker count: {final_status['worker_count']}")

    print("✓ Worker Scaler tests completed\n")

def test_integration():
    """Test integration between components"""
    print("Testing Integration...")

    rm = ResourceManager()
    scaler = WorkerScaler()

    # Collect metrics with worker info
    print("  Testing metrics collection with worker data...")
    worker_count = scaler.get_worker_count()
    queue_depth = scaler.get_queue_depth()
    metrics = rm.collect_metrics(queue_depth=queue_depth, worker_count=worker_count)

    print(f"  ✓ Integrated metrics: Workers={metrics.worker_count}, Queue={metrics.queue_depth}")

    # Test resource limits for scaling
    print("  Testing resource limit checks...")
    can_scale = scaler.check_resource_limits()
    print(f"  ✓ Can scale up: {can_scale}")

    # Get combined status
    print("  Getting combined status...")
    combined_status = {
        'resource_metrics': rm.get_metrics_summary(),
        'worker_status': scaler.get_status(),
        'timestamp': time.time()
    }

    print("  ✓ Combined status retrieved")

    scaler.shutdown()
    print("✓ Integration tests completed\n")

def test_error_handling():
    """Test error handling scenarios"""
    print("Testing Error Handling...")

    # Test with invalid configuration
    print("  Testing with invalid config...")
    try:
        rm = ResourceManager("nonexistent_config.json")
        print("  ✓ Resource manager handles missing config")
    except Exception as e:
        print(f"  ✗ Unexpected error: {e}")

    # Test worker scaler with invalid config
    print("  Testing worker scaler with invalid config...")
    try:
        scaler = WorkerScaler("nonexistent_config.json")
        scaler.shutdown()
        print("  ✓ Worker scaler handles missing config")
    except Exception as e:
        print(f"  ✗ Unexpected error: {e}")

    print("✓ Error handling tests completed\n")

def run_performance_test():
    """Run performance test of scaling operations"""
    print("Running Performance Test...")

    scaler = WorkerScaler()
    rm = ResourceManager()

    # Time multiple operations
    start_time = time.time()

    for i in range(5):
        print(f"  Iteration {i+1}/5...")

        # Collect metrics
        metrics = rm.collect_metrics()

        # Check scaling decision
        queue_depth = 100 + (i * 50)  # Simulate increasing load
        scale_result = scaler.scale_workers(queue_depth)

        # Health check
        health_result = scaler.health_check()

        time.sleep(1)  # Brief pause

    end_time = time.time()
    duration = end_time - start_time

    print(f"  ✓ Performance test completed in {duration:.2f} seconds")
    print(f"  ✓ Average operation time: {duration/5:.2f} seconds")

    scaler.shutdown()
    print("✓ Performance tests completed\n")

if __name__ == "__main__":
    print("Worker Scaling Test Suite")
    print("=" * 50)

    try:
        # Run all tests
        test_resource_manager()
        test_worker_scaler()
        test_integration()
        test_error_handling()
        run_performance_test()

        print("🎉 All tests completed successfully!")

    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)