#!/usr/bin/env python3
"""
Atlas Performance and Load Testing Script

Tests system performance under realistic conditions:
- Memory usage monitoring
- API response times under concurrent load
- Database performance with large datasets
- Service stability under continuous operation
"""

import asyncio
import aiohttp
import json
import time
import psutil
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
import sys

class AtlasLoadTester:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.db_path = "atlas.db"
        self.results = {
            'memory_usage': [],
            'api_response_times': [],
            'concurrent_requests': [],
            'database_performance': [],
            'error_count': 0
        }

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")

    def get_memory_usage(self):
        """Get current memory usage in MB"""
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024

    def test_api_response_time(self, endpoint="/health"):
        """Test single API response time"""
        import requests
        try:
            start_time = time.time()
            response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
            end_time = time.time()

            response_time = (end_time - start_time) * 1000  # milliseconds
            success = response.status_code == 200

            return {
                'endpoint': endpoint,
                'response_time': response_time,
                'success': success,
                'status_code': response.status_code
            }
        except Exception as e:
            self.results['error_count'] += 1
            return {
                'endpoint': endpoint,
                'response_time': None,
                'success': False,
                'error': str(e)
            }

    async def concurrent_api_test(self, num_requests=50):
        """Test API under concurrent load"""
        self.log(f"Starting concurrent API test with {num_requests} requests...")

        async with aiohttp.ClientSession() as session:
            tasks = []

            for i in range(num_requests):
                task = self.make_async_request(session, f"{self.base_url}/health")
                tasks.append(task)

            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()

            successful = sum(1 for r in results if isinstance(r, dict) and r.get('success'))
            failed = len(results) - successful
            avg_time = (end_time - start_time) / num_requests * 1000

            self.log(f"Concurrent test completed: {successful} success, {failed} failed")
            self.log(f"Average response time: {avg_time:.2f}ms")

            return {
                'total_requests': num_requests,
                'successful': successful,
                'failed': failed,
                'avg_response_time': avg_time,
                'total_time': end_time - start_time
            }

    async def make_async_request(self, session, url):
        """Make single async HTTP request"""
        try:
            start_time = time.time()
            async with session.get(url, timeout=10) as response:
                end_time = time.time()
                return {
                    'success': response.status == 200,
                    'status': response.status,
                    'response_time': (end_time - start_time) * 1000
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'response_time': None
            }

    def test_database_performance(self):
        """Test database performance with bulk operations"""
        self.log("Testing database performance...")

        if not Path(self.db_path).exists():
            self.log("Database not found, skipping database tests")
            return None

        try:
            # Test bulk insert performance
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Insert test data
            start_time = time.time()
            test_data = []
            for i in range(1000):
                test_data.append((
                    f"Test Content {i}",
                    f"http://test{i}.com",
                    f"Content body {i}" * 100,  # Make it realistic size
                    "test",
                    json.dumps({"test_id": i}),
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))

            cursor.executemany("""
                INSERT INTO content (title, url, content, content_type, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, test_data)

            insert_time = time.time() - start_time

            # Test bulk select performance
            start_time = time.time()
            cursor.execute("SELECT COUNT(*) FROM content")
            count_result = cursor.fetchone()[0]
            count_time = time.time() - start_time

            # Test search performance
            start_time = time.time()
            cursor.execute("SELECT * FROM content WHERE content LIKE '%Content body 500%'")
            search_results = cursor.fetchall()
            search_time = time.time() - start_time

            # Clean up test data
            cursor.execute("DELETE FROM content WHERE content_type = 'test'")
            conn.commit()
            conn.close()

            self.log(f"Database test completed: {len(test_data)} records")
            self.log(f"Insert time: {insert_time:.3f}s, Count time: {count_time:.3f}s, Search time: {search_time:.3f}s")

            return {
                'insert_time': insert_time,
                'insert_records': len(test_data),
                'count_time': count_time,
                'total_records': count_result,
                'search_time': search_time,
                'search_results': len(search_results)
            }

        except Exception as e:
            self.log(f"Database test failed: {e}")
            return None

    def monitor_memory_usage(self, duration=300):
        """Monitor memory usage over time (5 minutes)"""
        self.log(f"Starting memory monitoring for {duration} seconds...")

        start_time = time.time()
        memory_samples = []

        while (time.time() - start_time) < duration:
            memory_mb = self.get_memory_usage()
            memory_samples.append({
                'timestamp': time.time(),
                'memory_mb': memory_mb
            })
            time.sleep(10)  # Sample every 10 seconds

        if memory_samples:
            avg_memory = sum(s['memory_mb'] for s in memory_samples) / len(memory_samples)
            max_memory = max(s['memory_mb'] for s in memory_samples)
            min_memory = min(s['memory_mb'] for s in memory_samples)

            self.log(f"Memory usage: Avg={avg_memory:.1f}MB, Max={max_memory:.1f}MB, Min={min_memory:.1f}MB")

            return {
                'samples': len(memory_samples),
                'avg_memory_mb': avg_memory,
                'max_memory_mb': max_memory,
                'min_memory_mb': min_memory,
                'memory_growth': max_memory - min_memory
            }

        return None

    def test_api_endpoints(self):
        """Test various API endpoints for response times"""
        endpoints = [
            "/health",
            "/api/v1/cognitive/surface",
            "/api/v1/cognitive/temporal",
            "/api/v1/cognitive/patterns",
            "/api/v1/worker/status"
        ]

        results = []
        for endpoint in endpoints:
            self.log(f"Testing endpoint: {endpoint}")
            result = self.test_api_response_time(endpoint)
            results.append(result)

            if result['success']:
                self.log(f"✅ {endpoint}: {result['response_time']:.1f}ms")
            else:
                self.log(f"❌ {endpoint}: Failed ({result.get('error', 'Unknown error')})")

        return results

    async def run_full_test(self):
        """Run complete performance test suite"""
        self.log("🚀 Starting Atlas Performance Test Suite")
        self.log("=" * 50)

        # Test 1: Basic API endpoint performance
        self.log("📡 Testing API endpoint performance...")
        api_results = self.test_api_endpoints()
        self.results['api_response_times'] = api_results

        # Test 2: Database performance
        self.log("🗄️ Testing database performance...")
        db_results = self.test_database_performance()
        if db_results:
            self.results['database_performance'] = db_results

        # Test 3: Concurrent API load test
        self.log("🔀 Testing concurrent API load...")
        concurrent_results = await self.concurrent_api_test(30)
        self.results['concurrent_requests'] = concurrent_results

        # Test 4: Memory usage monitoring (short version for testing)
        self.log("💾 Testing memory usage stability...")
        memory_results = self.monitor_memory_usage(60)  # 1 minute for testing
        if memory_results:
            self.results['memory_usage'] = memory_results

        self.print_summary()

    def print_summary(self):
        """Print test results summary"""
        self.log("📊 Performance Test Results Summary")
        self.log("=" * 50)

        # API Performance
        if self.results['api_response_times']:
            successful_apis = [r for r in self.results['api_response_times'] if r['success']]
            if successful_apis:
                avg_response = sum(r['response_time'] for r in successful_apis) / len(successful_apis)
                self.log(f"✅ API Response Time: {avg_response:.1f}ms average")
            else:
                self.log("❌ API Response Time: All endpoints failed")

        # Database Performance
        if self.results['database_performance']:
            db_perf = self.results['database_performance']
            self.log(f"✅ Database Performance: {db_perf['insert_records']} records in {db_perf['insert_time']:.2f}s")

        # Concurrent Load
        if self.results['concurrent_requests']:
            conc = self.results['concurrent_requests']
            success_rate = (conc['successful'] / conc['total_requests']) * 100
            self.log(f"✅ Concurrent Load: {success_rate:.1f}% success rate ({conc['successful']}/{conc['total_requests']})")

        # Memory Usage
        if self.results['memory_usage']:
            mem = self.results['memory_usage']
            self.log(f"✅ Memory Usage: {mem['avg_memory_mb']:.1f}MB average, {mem['memory_growth']:.1f}MB growth")

        # Overall Status
        if self.results['error_count'] == 0:
            self.log("🎉 All performance tests completed successfully!")
        else:
            self.log(f"⚠️ Completed with {self.results['error_count']} errors")

def main():
    """Run performance tests"""
    tester = AtlasLoadTester()

    try:
        # Run the async test suite
        asyncio.run(tester.run_full_test())
    except KeyboardInterrupt:
        tester.log("Test interrupted by user")
    except Exception as e:
        tester.log(f"Test failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()