#!/usr/bin/env python3
"""
Test script for queue failure scenarios and dead letter queue
"""

import sys
import time
import json
from pathlib import Path
import threading
import random

# Add helpers to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from helpers.queue_manager import get_queue_manager, TaskStatus

class MockWorker:
    """Mock worker to simulate task processing"""

    def __init__(self, worker_id: str, queue_name: str = "test_queue", failure_rate: float = 0.3):
        self.worker_id = worker_id
        self.queue_name = queue_name
        self.failure_rate = failure_rate
        self.queue_manager = get_queue_manager(queue_name)
        self.processed_tasks = 0
        self.failed_tasks = 0
        self.running = False

    def process_tasks(self, duration: int = 60):
        """Process tasks for specified duration"""
        print(f"Worker {self.worker_id} starting (failure rate: {self.failure_rate:.1%})")
        self.running = True
        start_time = time.time()

        while self.running and (time.time() - start_time) < duration:
            try:
                # Dequeue task
                task = self.queue_manager.dequeue(self.worker_id)

                if task is None:
                    time.sleep(1)  # No tasks available
                    continue

                print(f"  Worker {self.worker_id} processing task {task.id} (attempt {task.attempt_count + 1})")

                # Simulate processing time
                time.sleep(random.uniform(0.1, 0.5))

                # Simulate success/failure
                if random.random() < self.failure_rate:
                    # Fail the task
                    error_msg = f"Simulated failure from worker {self.worker_id}"
                    success = self.queue_manager.fail_task(task.id, self.worker_id, error_msg)

                    if success:
                        self.failed_tasks += 1
                        print(f"  ✗ Task {task.id} failed: {error_msg}")
                    else:
                        print(f"  ✗ Failed to fail task {task.id}")
                else:
                    # Complete the task
                    success = self.queue_manager.complete_task(task.id, self.worker_id)

                    if success:
                        self.processed_tasks += 1
                        print(f"  ✓ Task {task.id} completed")
                    else:
                        print(f"  ✗ Failed to complete task {task.id}")

            except Exception as e:
                print(f"  ✗ Worker {self.worker_id} error: {e}")
                time.sleep(1)

        self.running = False
        print(f"Worker {self.worker_id} finished: {self.processed_tasks} completed, {self.failed_tasks} failed")

def test_basic_queue_operations():
    """Test basic queue operations"""
    print("Testing basic queue operations...")

    queue_manager = get_queue_manager("test_queue")

    # Enqueue some tasks
    task_ids = []
    for i in range(5):
        task_id = queue_manager.enqueue("test_task", {"message": f"Test message {i}"})
        task_ids.append(task_id)
        print(f"  Enqueued task: {task_id}")

    # Get initial stats
    stats = queue_manager.get_queue_stats()
    print(f"  Initial queue stats: {stats}")

    # Process one task successfully
    worker = MockWorker("test_worker", "test_queue", failure_rate=0.0)  # No failures
    task = queue_manager.dequeue("test_worker")

    if task:
        print(f"  Dequeued task: {task.id}")
        time.sleep(0.1)  # Simulate processing
        queue_manager.complete_task(task.id, "test_worker")
        print(f"  Completed task: {task.id}")

    # Get final stats
    stats = queue_manager.get_queue_stats()
    print(f"  Final queue stats: {stats}")
    print("✓ Basic operations test completed\n")

def test_exponential_backoff():
    """Test exponential backoff retry logic"""
    print("Testing exponential backoff...")

    queue_manager = get_queue_manager("test_queue")

    # Enqueue a task that will fail
    task_id = queue_manager.enqueue("failing_task", {"will_fail": True}, max_attempts=5)
    print(f"  Enqueued failing task: {task_id}")

    # Create worker that always fails
    worker = MockWorker("failing_worker", "test_queue", failure_rate=1.0)

    # Process the task multiple times to see retries
    for attempt in range(6):  # One more than max_attempts
        task = queue_manager.dequeue("failing_worker")

        if task:
            print(f"  Attempt {attempt + 1}: Processing task {task.id} (attempt count: {task.attempt_count})")

            # Always fail
            queue_manager.fail_task(task.id, "failing_worker", f"Failure attempt {attempt + 1}")

            # Check task status
            with queue_manager.db_manager.pool.get_connection() as conn:
                cursor = conn.execute('''
                    SELECT status, attempt_count, next_retry_at, error_message
                    FROM queue_tasks WHERE id = ?
                ''', (task.id,))
                row = cursor.fetchone()

                if row:
                    status, attempt_count, next_retry_at, error_msg = row
                    print(f"    Task status: {status}, attempts: {attempt_count}")
                    if next_retry_at:
                        print(f"    Next retry at: {next_retry_at}")
                    if status == TaskStatus.DEAD_LETTER.value:
                        print(f"    ⚰️ Task moved to dead letter queue")
                        break
        else:
            print(f"  Attempt {attempt + 1}: No task available (waiting for retry time)")
            time.sleep(2)  # Wait for retry schedule

    # Check dead letter queue
    with queue_manager.db_manager.pool.get_connection() as conn:
        cursor = conn.execute('''
            SELECT COUNT(*) FROM dead_letter_tasks WHERE queue_name = ?
        ''', ("test_queue",))
        dlq_count = cursor.fetchone()[0]
        print(f"  Dead letter queue count: {dlq_count}")

    print("✓ Exponential backoff test completed\n")

def test_circuit_breaker():
    """Test circuit breaker functionality"""
    print("Testing circuit breaker...")

    queue_manager = get_queue_manager("test_queue")

    # Check initial circuit breaker state
    cb_status = queue_manager.circuit_breaker.get_status()
    print(f"  Initial circuit breaker state: {cb_status['state']}")

    # Enqueue tasks
    task_ids = []
    for i in range(15):  # More than failure threshold
        task_id = queue_manager.enqueue("cb_test_task", {"message": f"CB test {i}"})
        task_ids.append(task_id)

    # Create worker that always fails
    worker = MockWorker("cb_worker", "test_queue", failure_rate=1.0)

    # Process tasks until circuit breaker opens
    processed = 0
    while processed < 15:
        task = queue_manager.dequeue("cb_worker")

        if task is None:
            # Circuit breaker might be open
            cb_status = queue_manager.circuit_breaker.get_status()
            print(f"  Circuit breaker state: {cb_status['state']} (failures: {cb_status['failure_count']})")

            if cb_status['state'] == 'open':
                print("  🔴 Circuit breaker opened!")
                break

            time.sleep(0.1)
            continue

        # Fail the task
        queue_manager.fail_task(task.id, "cb_worker", "Simulated failure for circuit breaker test")
        processed += 1

        cb_status = queue_manager.circuit_breaker.get_status()
        print(f"  Processed {processed}: CB state = {cb_status['state']}, failures = {cb_status['failure_count']}")

    # Test that no more tasks can be dequeued
    task = queue_manager.dequeue("cb_worker")
    if task is None:
        print("  ✓ Circuit breaker correctly preventing task dequeue")
    else:
        print("  ✗ Circuit breaker not working - task was dequeued")

    print("✓ Circuit breaker test completed\n")

def test_concurrent_workers():
    """Test multiple concurrent workers"""
    print("Testing concurrent workers...")

    queue_manager = get_queue_manager("test_queue")

    # Enqueue many tasks
    task_count = 50
    for i in range(task_count):
        queue_manager.enqueue("concurrent_test", {"message": f"Concurrent test {i}"})

    print(f"  Enqueued {task_count} tasks")

    # Create multiple workers
    workers = []
    threads = []

    for i in range(3):
        worker = MockWorker(f"worker_{i}", "test_queue", failure_rate=0.2)
        workers.append(worker)

        thread = threading.Thread(target=worker.process_tasks, args=(30,))  # Run for 30 seconds
        threads.append(thread)

    # Start all workers
    start_time = time.time()
    for thread in threads:
        thread.start()

    # Wait for completion
    for thread in threads:
        thread.join()

    duration = time.time() - start_time

    # Collect results
    total_processed = sum(w.processed_tasks for w in workers)
    total_failed = sum(w.failed_tasks for w in workers)

    print(f"  Processed {total_processed} tasks, failed {total_failed} tasks in {duration:.1f}s")
    print(f"  Throughput: {total_processed/duration:.1f} tasks/sec")

    # Final stats
    stats = queue_manager.get_queue_stats()
    print(f"  Final stats: {stats}")

    print("✓ Concurrent workers test completed\n")

def test_dead_letter_queue_retry():
    """Test dead letter queue retry functionality"""
    print("Testing dead letter queue retry...")

    queue_manager = get_queue_manager("test_queue")

    # Create a task that will definitely end up in DLQ
    task_id = queue_manager.enqueue("dlq_test_task", {"message": "Will end up in DLQ"}, max_attempts=2)
    print(f"  Enqueued task for DLQ: {task_id}")

    # Process it until it goes to DLQ
    worker = MockWorker("dlq_worker", "test_queue", failure_rate=1.0)

    attempts = 0
    while attempts < 3:
        task = queue_manager.dequeue("dlq_worker")
        if task:
            attempts += 1
            print(f"  Attempt {attempts}: Failing task {task.id}")
            queue_manager.fail_task(task.id, "dlq_worker", f"DLQ test failure {attempts}")
        else:
            break

    # Check DLQ
    with queue_manager.db_manager.pool.get_connection() as conn:
        cursor = conn.execute('''
            SELECT id, original_task_id FROM dead_letter_tasks
            WHERE queue_name = ? ORDER BY moved_to_dlq_at DESC LIMIT 1
        ''', ("test_queue",))

        row = cursor.fetchone()
        if row:
            dlq_id, original_id = row
            print(f"  Task {original_id} is in DLQ with ID {dlq_id}")

            # Try to retry it
            success = queue_manager.retry_dead_letter_task(dlq_id)

            if success:
                print(f"  ✓ Successfully retried DLQ task {dlq_id}")

                # Try to process the retried task successfully
                task = queue_manager.dequeue("dlq_worker")
                if task:
                    # This time complete it successfully
                    queue_manager.complete_task(task.id, "dlq_worker")
                    print(f"  ✓ Retried task {task.id} completed successfully")
            else:
                print(f"  ✗ Failed to retry DLQ task {dlq_id}")
        else:
            print("  ✗ No tasks found in DLQ")

    print("✓ Dead letter queue retry test completed\n")

def run_all_tests():
    """Run all queue failure tests"""
    print("Queue Failure Test Suite")
    print("=" * 50)

    try:
        test_basic_queue_operations()
        test_exponential_backoff()
        test_circuit_breaker()
        test_concurrent_workers()
        test_dead_letter_queue_retry()

        print("🎉 All queue failure tests completed!")

        # Final system stats
        queue_manager = get_queue_manager("test_queue")
        final_stats = queue_manager.get_queue_stats()
        print(f"\nFinal system stats:")
        print(json.dumps(final_stats, indent=2))

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Cleanup
        try:
            queue_manager = get_queue_manager("test_queue")
            queue_manager.shutdown()
        except:
            pass

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Queue Failure Tests")
    parser.add_argument("--test", choices=["basic", "backoff", "circuit", "concurrent", "dlq", "all"],
                       default="all", help="Which test to run")

    args = parser.parse_args()

    if args.test == "all":
        run_all_tests()
    elif args.test == "basic":
        test_basic_queue_operations()
    elif args.test == "backoff":
        test_exponential_backoff()
    elif args.test == "circuit":
        test_circuit_breaker()
    elif args.test == "concurrent":
        test_concurrent_workers()
    elif args.test == "dlq":
        test_dead_letter_queue_retry()