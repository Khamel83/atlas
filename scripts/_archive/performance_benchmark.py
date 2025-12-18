#!/usr/bin/env python3
"""
Atlas Performance Benchmark
Measures key performance metrics and detects regressions.
"""

import sys
import time
import json
import argparse
import statistics
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.database_config import get_database_connection
from helpers.queue_manager import get_queue_manager, enqueue_task
from helpers.metrics_collector import get_metrics_collector


class PerformanceBenchmark:
    """Performance benchmark suite for Atlas system."""

    def __init__(self):
        self.results = {}
        self.benchmarks_file = Path("data/performance_benchmarks.json")
        self.regression_threshold = 1.5  # 50% slower triggers regression alert

    def load_historical_benchmarks(self) -> Dict[str, Any]:
        """Load historical benchmark results."""
        if self.benchmarks_file.exists():
            try:
                with open(self.benchmarks_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {"benchmarks": []}

    def save_benchmark_results(self, results: Dict[str, Any]):
        """Save benchmark results to history."""
        try:
            self.benchmarks_file.parent.mkdir(exist_ok=True)
            historical = self.load_historical_benchmarks()

            benchmark_entry = {
                "timestamp": datetime.now().isoformat(),
                "results": results
            }

            historical["benchmarks"].append(benchmark_entry)

            # Keep only last 50 benchmark runs
            if len(historical["benchmarks"]) > 50:
                historical["benchmarks"] = historical["benchmarks"][-50:]

            with open(self.benchmarks_file, 'w') as f:
                json.dump(historical, f, indent=2)
        except Exception as e:
            print(f"Failed to save benchmark results: {e}")

    def benchmark_database_operations(self) -> Dict[str, float]:
        """Benchmark database operations."""
        print("🗃️  Benchmarking database operations...")

        conn = get_database_connection()
        cursor = conn.cursor()

        # Test simple query
        start = time.time()
        cursor.execute("SELECT COUNT(*) FROM content")
        result = cursor.fetchone()
        simple_query_time = time.time() - start

        # Test complex query with LIKE
        start = time.time()
        cursor.execute("SELECT title, content FROM content WHERE title LIKE '%test%' LIMIT 10")
        results = cursor.fetchall()
        complex_query_time = time.time() - start

        # Test insert operation
        test_title = f"benchmark_test_{int(time.time())}"
        start = time.time()
        cursor.execute("""
            INSERT INTO content (title, content, url, content_type, created_at)
            VALUES (?, ?, ?, ?, datetime('now'))
        """, (test_title, "Benchmark test content", "http://benchmark.test", "test"))
        conn.commit()
        insert_time = time.time() - start

        # Cleanup
        cursor.execute("DELETE FROM content WHERE title = ?", (test_title,))
        conn.commit()
        conn.close()

        return {
            "db_simple_query_ms": simple_query_time * 1000,
            "db_complex_query_ms": complex_query_time * 1000,
            "db_insert_ms": insert_time * 1000
        }

    def benchmark_queue_operations(self) -> Dict[str, float]:
        """Benchmark queue operations."""
        print("📝 Benchmarking queue operations...")

        qm = get_queue_manager()

        # Benchmark enqueue operations
        enqueue_times = []
        task_ids = []

        for i in range(10):
            task_id = f"benchmark_{int(time.time())}_{i}"
            task_ids.append(task_id)

            start = time.time()
            enqueue_task(task_id, "benchmark_test", {"test": True, "index": i})
            enqueue_time = time.time() - start
            enqueue_times.append(enqueue_time * 1000)

        # Benchmark dequeue operations
        dequeue_times = []
        for _ in range(len(task_ids)):
            start = time.time()
            task = qm.dequeue_task("benchmark_worker", ["benchmark_test"])
            dequeue_time = time.time() - start
            dequeue_times.append(dequeue_time * 1000)

            if task:
                qm.complete_task(task.task_id, "benchmark_worker")

        return {
            "queue_enqueue_avg_ms": statistics.mean(enqueue_times),
            "queue_enqueue_max_ms": max(enqueue_times),
            "queue_dequeue_avg_ms": statistics.mean(dequeue_times),
            "queue_dequeue_max_ms": max(dequeue_times)
        }

    def benchmark_metrics_collection(self) -> Dict[str, float]:
        """Benchmark metrics collection."""
        print("📊 Benchmarking metrics collection...")

        collector = get_metrics_collector()

        # Benchmark metric recording
        record_times = []
        for i in range(100):
            start = time.time()
            collector.record_metric(f"benchmark_metric_{i}", i * 1.5)
            record_time = time.time() - start
            record_times.append(record_time * 1000)

        # Benchmark metric retrieval
        retrieve_times = []
        for i in range(50):
            start = time.time()
            value = collector.get_metric_value(f"benchmark_metric_{i}")
            retrieve_time = time.time() - start
            retrieve_times.append(retrieve_time * 1000)

        # Benchmark Prometheus export
        start = time.time()
        from helpers.metrics_collector import get_prometheus_metrics
        metrics_output = get_prometheus_metrics()
        export_time = time.time() - start

        return {
            "metrics_record_avg_ms": statistics.mean(record_times),
            "metrics_record_max_ms": max(record_times),
            "metrics_retrieve_avg_ms": statistics.mean(retrieve_times),
            "metrics_export_ms": export_time * 1000,
            "metrics_export_size_kb": len(metrics_output) / 1024
        }

    def benchmark_system_health(self) -> Dict[str, float]:
        """Benchmark system health checks."""
        print("🔍 Benchmarking system health checks...")

        # Benchmark health summary generation
        start = time.time()
        from helpers.metrics_collector import get_health_summary
        health = get_health_summary()
        health_check_time = time.time() - start

        # Benchmark queue status
        start = time.time()
        from helpers.queue_manager import get_queue_status
        queue_status = get_queue_status()
        queue_status_time = time.time() - start

        return {
            "health_check_ms": health_check_time * 1000,
            "queue_status_ms": queue_status_time * 1000
        }

    def run_full_benchmark(self) -> Dict[str, Any]:
        """Run complete benchmark suite."""
        print("🚀 Starting Atlas Performance Benchmark")
        print("=" * 50)

        start_time = time.time()

        results = {}

        try:
            # Database benchmarks
            db_results = self.benchmark_database_operations()
            results.update(db_results)

            # Queue benchmarks
            queue_results = self.benchmark_queue_operations()
            results.update(queue_results)

            # Metrics benchmarks
            metrics_results = self.benchmark_metrics_collection()
            results.update(metrics_results)

            # System health benchmarks
            health_results = self.benchmark_system_health()
            results.update(health_results)

            total_time = time.time() - start_time
            results["total_benchmark_time_ms"] = total_time * 1000

            print(f"\n✅ Benchmark completed in {total_time:.2f}s")
            return results

        except Exception as e:
            print(f"❌ Benchmark failed: {e}")
            raise

    def run_quick_benchmark(self) -> Dict[str, Any]:
        """Run quick benchmark for CI."""
        print("⚡ Running quick performance check")

        start_time = time.time()
        results = {}

        # Quick database test
        conn = get_database_connection()
        cursor = conn.cursor()
        start = time.time()
        cursor.execute("SELECT COUNT(*) FROM content")
        cursor.fetchone()
        results["db_quick_query_ms"] = (time.time() - start) * 1000
        conn.close()

        # Quick queue test
        task_id = f"quick_benchmark_{int(time.time())}"
        start = time.time()
        enqueue_task(task_id, "quick_test", {"test": True})
        results["queue_quick_enqueue_ms"] = (time.time() - start) * 1000

        # Quick metrics test
        collector = get_metrics_collector()
        start = time.time()
        collector.record_metric("quick_benchmark", 42)
        results["metrics_quick_record_ms"] = (time.time() - start) * 1000

        results["total_quick_benchmark_ms"] = (time.time() - start_time) * 1000

        print(f"✅ Quick benchmark completed in {results['total_quick_benchmark_ms']:.1f}ms")
        return results

    def check_for_regressions(self, current_results: Dict[str, Any]) -> List[str]:
        """Check for performance regressions."""
        historical = self.load_historical_benchmarks()

        if len(historical["benchmarks"]) < 3:
            print("📊 Insufficient historical data for regression detection")
            return []

        # Get recent baseline (average of last 5 runs, excluding current)
        recent_runs = historical["benchmarks"][-5:]
        regressions = []

        for metric, current_value in current_results.items():
            if not isinstance(current_value, (int, float)):
                continue

            # Calculate baseline average
            historical_values = []
            for run in recent_runs:
                if metric in run["results"]:
                    historical_values.append(run["results"][metric])

            if len(historical_values) >= 2:
                baseline = statistics.mean(historical_values)

                # Check for regression (current is significantly slower)
                if current_value > baseline * self.regression_threshold:
                    regression_pct = ((current_value - baseline) / baseline) * 100
                    regressions.append(f"{metric}: {regression_pct:.1f}% slower than baseline")

        return regressions

    def print_results(self, results: Dict[str, Any]):
        """Print benchmark results in readable format."""
        print("\n📊 PERFORMANCE BENCHMARK RESULTS")
        print("=" * 50)

        # Group results by category
        categories = {
            "Database": [k for k in results.keys() if k.startswith("db_")],
            "Queue": [k for k in results.keys() if k.startswith("queue_")],
            "Metrics": [k for k in results.keys() if k.startswith("metrics_")],
            "System": [k for k in results.keys() if k.startswith("health_") or k.startswith("queue_status")],
            "Overall": [k for k in results.keys() if k.startswith("total_")]
        }

        for category, metrics in categories.items():
            if not metrics:
                continue

            print(f"\n{category}:")
            for metric in metrics:
                value = results[metric]
                if isinstance(value, float):
                    if "ms" in metric:
                        print(f"  {metric}: {value:.2f}ms")
                    elif "kb" in metric:
                        print(f"  {metric}: {value:.1f}KB")
                    else:
                        print(f"  {metric}: {value:.2f}")


def main():
    """Main benchmark function."""
    parser = argparse.ArgumentParser(description="Atlas Performance Benchmark")
    parser.add_argument("--quick", action="store_true", help="Run quick benchmark for CI")
    parser.add_argument("--check-regressions", action="store_true", help="Check for performance regressions")
    parser.add_argument("--save", action="store_true", help="Save results to history")

    args = parser.parse_args()

    benchmark = PerformanceBenchmark()

    try:
        if args.quick:
            results = benchmark.run_quick_benchmark()
        else:
            results = benchmark.run_full_benchmark()

        benchmark.print_results(results)

        if args.check_regressions:
            regressions = benchmark.check_for_regressions(results)
            if regressions:
                print("\n⚠️  PERFORMANCE REGRESSIONS DETECTED:")
                for regression in regressions:
                    print(f"  • {regression}")
                sys.exit(1)
            else:
                print("\n✅ No performance regressions detected")

        if args.save or not args.quick:
            benchmark.save_benchmark_results(results)
            print("💾 Benchmark results saved to history")

    except Exception as e:
        print(f"❌ Benchmark failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()