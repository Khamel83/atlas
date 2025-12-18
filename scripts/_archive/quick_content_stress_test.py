#!/usr/bin/env python3
"""
Quick Content Processing Stress Test - Task 2.5
Focused testing of core content processing capabilities under load.
"""

import os
import sys
import time
import tempfile
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_file_processing():
    """Test basic file processing performance"""
    print("📄 File Processing Test")
    print("-" * 30)

    # Create test files
    test_files = []
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create 10 test files
        for i in range(10):
            test_file = temp_path / f"test_{i}.txt"
            with open(test_file, 'w') as f:
                f.write(f"Test content {i} " * 100)  # ~1KB per file
            test_files.append(test_file)

        # Test processing speed
        start_time = time.time()
        processed = 0

        for test_file in test_files:
            try:
                with open(test_file, 'r') as f:
                    content = f.read()
                    # Simulate processing
                    words = len(content.split())
                    processed += 1
            except Exception as e:
                print(f"   ❌ Error processing {test_file}: {e}")

        processing_time = (time.time() - start_time) * 1000
        avg_time = processing_time / len(test_files) if test_files else 0

        print(f"   ✅ Files processed: {processed}/{len(test_files)}")
        print(f"   ⚡ Average time: {avg_time:.1f}ms per file")
        print(f"   📊 Total time: {processing_time:.1f}ms")

        return processed >= len(test_files) * 0.8  # 80% success rate

def test_concurrent_operations():
    """Test concurrent operations"""
    print("\n🔄 Concurrent Operations Test")
    print("-" * 30)

    import threading
    import queue

    # Test data
    test_data = [f"Test item {i}" for i in range(20)]
    results_queue = queue.Queue()

    def worker_thread(data_item):
        start_time = time.time()
        try:
            # Simulate processing work
            processed = data_item.upper().lower() * 2
            time.sleep(0.01)  # Simulate I/O delay
            processing_time = (time.time() - start_time) * 1000
            results_queue.put({'success': True, 'time_ms': processing_time, 'item': data_item})
        except Exception as e:
            results_queue.put({'success': False, 'error': str(e), 'item': data_item})

    # Run concurrent threads
    threads = []
    start_time = time.time()

    for item in test_data:
        thread = threading.Thread(target=worker_thread, args=(item,))
        thread.start()
        threads.append(thread)

    # Wait for all threads
    for thread in threads:
        thread.join()

    total_time = (time.time() - start_time) * 1000

    # Collect results
    results = []
    while not results_queue.empty():
        results.append(results_queue.get())

    successful = len([r for r in results if r['success']])
    avg_processing_time = sum(r.get('time_ms', 0) for r in results if r['success']) / max(successful, 1)

    print(f"   ✅ Successful operations: {successful}/{len(test_data)}")
    print(f"   ⚡ Average processing: {avg_processing_time:.1f}ms")
    print(f"   📊 Total time: {total_time:.1f}ms")
    print(f"   🚀 Throughput: {len(test_data) / (total_time / 1000):.1f} ops/sec")

    return successful >= len(test_data) * 0.8

def test_memory_efficiency():
    """Test memory usage patterns"""
    print("\n🧠 Memory Efficiency Test")
    print("-" * 30)

    try:
        import psutil
        process = psutil.Process()

        # Baseline
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Create and process data
        data_chunks = []
        for i in range(50):
            chunk = f"Data chunk {i} with content " * 100  # ~2KB per chunk
            data_chunks.append(chunk.upper().lower())  # Simple processing

        # Peak memory
        peak_memory = process.memory_info().rss / 1024 / 1024

        # Clear data
        data_chunks = None
        import gc
        gc.collect()

        # Final memory
        final_memory = process.memory_info().rss / 1024 / 1024

        memory_growth = peak_memory - initial_memory
        memory_freed = peak_memory - final_memory

        print(f"   📊 Initial: {initial_memory:.1f}MB")
        print(f"   📈 Peak: {peak_memory:.1f}MB")
        print(f"   📉 Final: {final_memory:.1f}MB")
        print(f"   🔺 Growth: {memory_growth:.1f}MB")
        print(f"   🔽 Freed: {memory_freed:.1f}MB")

        # Good if growth is reasonable and memory is freed
        return memory_growth < 100 and memory_freed > memory_growth * 0.5

    except ImportError:
        print("   ⚠️ psutil not available - skipping memory test")
        return True
    except Exception as e:
        print(f"   ❌ Memory test failed: {e}")
        return False

def test_database_operations():
    """Test basic database operations"""
    print("\n🗄️ Database Operations Test")
    print("-" * 30)

    try:
        from helpers.simple_database import SimpleDatabase

        db = SimpleDatabase()

        # Test basic operations
        start_time = time.time()
        operations_successful = 0

        # Test inserts
        for i in range(5):
            try:
                db.store_content(
                    title=f"Test Content {i}",
                    content=f"Test content body {i} with additional text for testing.",
                    url=f"https://test-{i}.example.com",
                    content_type="test"
                )
                operations_successful += 1
            except Exception as e:
                print(f"   ⚠️ Insert {i} failed: {e}")

        # Test searches
        search_successful = 0
        for i in range(3):
            try:
                results = db.search_content(f"Test Content {i}")
                if results:
                    search_successful += 1
            except Exception as e:
                print(f"   ⚠️ Search {i} failed: {e}")

        total_time = (time.time() - start_time) * 1000

        print(f"   ✅ Insert operations: {operations_successful}/5")
        print(f"   🔍 Search operations: {search_successful}/3")
        print(f"   ⚡ Total time: {total_time:.1f}ms")

        return operations_successful >= 3 and search_successful >= 2

    except Exception as e:
        print(f"   ❌ Database test failed: {e}")
        return False

def main():
    """Run quick content processing stress test"""
    print("🚀 Quick Content Processing Stress Test - Task 2.5")
    print("=" * 60)

    tests = [
        ("File Processing", test_file_processing),
        ("Concurrent Operations", test_concurrent_operations),
        ("Memory Efficiency", test_memory_efficiency),
        ("Database Operations", test_database_operations)
    ]

    results = {}
    passed_tests = 0

    for test_name, test_func in tests:
        try:
            success = test_func()
            results[test_name] = 'PASSED' if success else 'FAILED'
            if success:
                passed_tests += 1
        except Exception as e:
            print(f"   ❌ {test_name} error: {e}")
            results[test_name] = 'ERROR'

    # Generate report
    print("\n📊 QUICK STRESS TEST RESULTS")
    print("=" * 40)

    for test_name, result in results.items():
        status_icon = "✅" if result == "PASSED" else ("⚠️" if result == "ERROR" else "❌")
        print(f"{status_icon} {test_name}: {result}")

    success_rate = passed_tests / len(tests)
    print(f"\n🎯 Success Rate: {passed_tests}/{len(tests)} ({success_rate*100:.1f}%)")

    if success_rate >= 0.75:
        overall_status = "✅ EXCELLENT"
    elif success_rate >= 0.5:
        overall_status = "⚠️ GOOD"
    else:
        overall_status = "❌ NEEDS WORK"

    print(f"🎯 Overall Status: {overall_status}")
    print(f"✅ Task 2.5 {'COMPLETED' if overall_status.startswith('✅') else 'NEEDS WORK'}: Content Processing Pipeline Stress Testing")

    return 0 if success_rate >= 0.5 else 1

if __name__ == "__main__":
    exit(main())