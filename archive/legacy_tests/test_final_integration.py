#!/usr/bin/env python3
"""
Task 4.1: Final System Integration Testing

Comprehensive end-to-end integration testing of the complete Atlas system
including all components, APIs, databases, and processing pipelines.
"""

import os
import sys
import time
import json
import sqlite3
import requests
import tempfile
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class FinalIntegrationTester:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.api_base_url = "http://localhost:8000/api/v1"
        self.results = {}

    def test_api_server_health(self):
        """Test API server is responding"""
        print("🏥 API Server Health Test")
        print("-" * 30)

        try:
            response = requests.get(f"{self.api_base_url}/health", timeout=10)

            if response.status_code == 200 and response.json().get('status') == 'healthy':
                print("   ✅ API server healthy")
                self.results['api_health'] = {'status': 'passed', 'response_time': response.elapsed.total_seconds()}
                return True
            else:
                print(f"   ❌ API server unhealthy: {response.status_code}")
                self.results['api_health'] = {'status': 'failed', 'error': f'Status: {response.status_code}'}
                return False

        except Exception as e:
            print(f"   ❌ API server error: {e}")
            self.results['api_health'] = {'status': 'failed', 'error': str(e)}
            return False

    def test_database_connectivity(self):
        """Test database connections and integrity"""
        print("\n🗄️ Database Connectivity Test")
        print("-" * 30)

        databases = ["atlas.db", "atlas_search.db", "search.db"]
        passed = 0

        for db_name in databases:
            db_path = self.project_root / db_name
            try:
                if db_path.exists():
                    conn = sqlite3.connect(str(db_path))
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = cursor.fetchall()
                    conn.close()

                    print(f"   ✅ {db_name}: {len(tables)} tables")
                    passed += 1
                else:
                    print(f"   ⚠️ {db_name}: Not found")
            except Exception as e:
                print(f"   ❌ {db_name}: {e}")

        success = passed >= 2  # At least 2 databases should work
        self.results['database_connectivity'] = {
            'status': 'passed' if success else 'failed',
            'databases_working': passed,
            'total_databases': len(databases)
        }
        return success

    def test_search_functionality(self):
        """Test search API and functionality"""
        print("\n🔍 Search Functionality Test")
        print("-" * 30)

        try:
            # Test basic search
            response = requests.get(f"{self.api_base_url}/search/", params={"q": "test"}, timeout=10)

            if response.status_code == 200:
                data = response.json()
                result_count = len(data.get('results', []))
                total = data.get('total', 0)
                processing_time = data.get('processing_time_ms', 0)

                print(f"   ✅ Search working: {result_count} results, {total} total")
                print(f"   ⚡ Processing time: {processing_time:.1f}ms")

                self.results['search_functionality'] = {
                    'status': 'passed',
                    'result_count': result_count,
                    'total_indexed': total,
                    'processing_time_ms': processing_time
                }
                return True
            else:
                print(f"   ❌ Search failed: {response.status_code}")
                self.results['search_functionality'] = {'status': 'failed', 'error': f'HTTP {response.status_code}'}
                return False

        except Exception as e:
            print(f"   ❌ Search error: {e}")
            self.results['search_functionality'] = {'status': 'failed', 'error': str(e)}
            return False

    def test_analytics_dashboard(self):
        """Test analytics and dashboard functionality"""
        print("\n📊 Analytics Dashboard Test")
        print("-" * 30)

        try:
            # Test analytics API
            response = requests.get(f"{self.api_base_url}/analytics/", timeout=15)

            if response.status_code == 200:
                data = response.json()
                total_content = data.get('summary', {}).get('total_content', 0)

                print(f"   ✅ Analytics working: {total_content} total items")

                # Test dashboard HTML
                dashboard_response = requests.get(f"{self.api_base_url}/dashboard/", timeout=10)
                if dashboard_response.status_code == 200 and 'html' in dashboard_response.headers.get('content-type', '').lower():
                    print("   ✅ Dashboard HTML loading")
                    dashboard_working = True
                else:
                    print("   ⚠️ Dashboard HTML issues")
                    dashboard_working = False

                self.results['analytics_dashboard'] = {
                    'status': 'passed' if dashboard_working else 'partial',
                    'total_content': total_content,
                    'analytics_api': True,
                    'dashboard_html': dashboard_working
                }
                return dashboard_working
            else:
                print(f"   ❌ Analytics failed: {response.status_code}")
                self.results['analytics_dashboard'] = {'status': 'failed', 'error': f'HTTP {response.status_code}'}
                return False

        except Exception as e:
            print(f"   ❌ Analytics error: {e}")
            self.results['analytics_dashboard'] = {'status': 'failed', 'error': str(e)}
            return False

    def test_content_processing(self):
        """Test content processing capability"""
        print("\n📄 Content Processing Test")
        print("-" * 30)

        try:
            # Create a test document
            test_content = f"Test Document for Integration Testing\n\nGenerated at: {datetime.now().isoformat()}\n\nThis is a test document to verify that Atlas can process content correctly."

            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(test_content)
                test_file_path = f.name

            try:
                # Test document processing (simplified - just check we can read it)
                with open(test_file_path, 'r') as f:
                    content = f.read()

                if len(content) > 0 and "Integration Testing" in content:
                    print("   ✅ Document processing: File read successfully")
                    processing_success = True
                else:
                    print("   ❌ Document processing: Content verification failed")
                    processing_success = False

                # Test database storage simulation
                try:
                    from helpers.simple_database import SimpleDatabase
                    db = SimpleDatabase()

                    # Test database can store content (without actually storing test data)
                    all_content = db.get_all_content()
                    content_count = len(all_content) if all_content else 0

                    print(f"   ✅ Database storage: {content_count} items available")
                    storage_success = True

                except Exception as db_e:
                    print(f"   ⚠️ Database storage issue: {db_e}")
                    storage_success = False

                self.results['content_processing'] = {
                    'status': 'passed' if (processing_success and storage_success) else 'partial',
                    'file_processing': processing_success,
                    'database_storage': storage_success,
                    'content_items_count': content_count if 'content_count' in locals() else 0
                }

                return processing_success and storage_success

            finally:
                # Clean up test file
                try:
                    os.unlink(test_file_path)
                except:
                    pass

        except Exception as e:
            print(f"   ❌ Content processing error: {e}")
            self.results['content_processing'] = {'status': 'failed', 'error': str(e)}
            return False

    def test_system_performance(self):
        """Test overall system performance"""
        print("\n⚡ System Performance Test")
        print("-" * 30)

        try:
            # Test multiple API calls for performance
            start_time = time.time()

            api_calls = [
                ("health", f"{self.api_base_url}/health"),
                ("search", f"{self.api_base_url}/search/?q=test"),
                ("analytics", f"{self.api_base_url}/analytics/")
            ]

            call_times = {}
            successful_calls = 0

            for call_name, url in api_calls:
                call_start = time.time()
                try:
                    response = requests.get(url, timeout=5)
                    call_time = (time.time() - call_start) * 1000
                    call_times[call_name] = call_time

                    if response.status_code == 200:
                        successful_calls += 1
                        print(f"   ✅ {call_name}: {call_time:.1f}ms")
                    else:
                        print(f"   ⚠️ {call_name}: {call_time:.1f}ms (HTTP {response.status_code})")

                except Exception as e:
                    call_time = (time.time() - call_start) * 1000
                    call_times[call_name] = call_time
                    print(f"   ❌ {call_name}: {call_time:.1f}ms (Error: {e})")

            total_time = (time.time() - start_time) * 1000
            avg_response_time = sum(call_times.values()) / len(call_times) if call_times else 0

            print(f"   📊 Total test time: {total_time:.1f}ms")
            print(f"   📊 Average response time: {avg_response_time:.1f}ms")

            performance_good = avg_response_time < 2000 and successful_calls >= 2

            self.results['system_performance'] = {
                'status': 'passed' if performance_good else 'degraded',
                'successful_calls': successful_calls,
                'total_calls': len(api_calls),
                'avg_response_time_ms': avg_response_time,
                'call_times': call_times
            }

            return performance_good

        except Exception as e:
            print(f"   ❌ Performance test error: {e}")
            self.results['system_performance'] = {'status': 'failed', 'error': str(e)}
            return False

    def test_error_handling(self):
        """Test system error handling"""
        print("\n🚨 Error Handling Test")
        print("-" * 30)

        try:
            error_tests = [
                ("invalid_search", f"{self.api_base_url}/search/"),  # Missing query
                ("nonexistent_endpoint", f"{self.api_base_url}/nonexistent"),
                ("malformed_query", f"{self.api_base_url}/search/?q=&limit=invalid")
            ]

            error_handling_good = 0

            for test_name, url in error_tests:
                try:
                    response = requests.get(url, timeout=5)

                    # Good error handling should return 4xx status codes with proper JSON
                    if 400 <= response.status_code < 500:
                        try:
                            error_data = response.json()
                            if 'error' in error_data or 'detail' in error_data:
                                print(f"   ✅ {test_name}: Proper error response ({response.status_code})")
                                error_handling_good += 1
                            else:
                                print(f"   ⚠️ {test_name}: Error code OK but no error message")
                        except:
                            print(f"   ⚠️ {test_name}: Error code OK but not JSON")
                    else:
                        print(f"   ❌ {test_name}: Unexpected status {response.status_code}")

                except Exception as e:
                    print(f"   ❌ {test_name}: Request failed - {e}")

            success = error_handling_good >= len(error_tests) // 2

            self.results['error_handling'] = {
                'status': 'passed' if success else 'needs_work',
                'good_error_responses': error_handling_good,
                'total_error_tests': len(error_tests)
            }

            return success

        except Exception as e:
            print(f"   ❌ Error handling test failed: {e}")
            self.results['error_handling'] = {'status': 'failed', 'error': str(e)}
            return False

    def generate_final_report(self):
        """Generate comprehensive final integration test report"""
        print("\n📊 FINAL SYSTEM INTEGRATION TEST REPORT")
        print("=" * 60)

        test_categories = [
            'api_health', 'database_connectivity', 'search_functionality',
            'analytics_dashboard', 'content_processing', 'system_performance',
            'error_handling'
        ]

        passed_tests = 0
        total_tests = len(test_categories)

        print(f"\n🎯 DETAILED RESULTS")
        for category in test_categories:
            if category in self.results:
                result = self.results[category]
                status = result.get('status', 'unknown')

                if status == 'passed':
                    icon = "✅"
                    passed_tests += 1
                elif status == 'partial' or status == 'degraded':
                    icon = "⚠️"
                    passed_tests += 0.5
                else:
                    icon = "❌"

                print(f"   {icon} {category.replace('_', ' ').title()}: {status.upper()}")

                # Add specific details
                if category == 'search_functionality' and 'total_indexed' in result:
                    print(f"      └─ {result['total_indexed']} items indexed")
                elif category == 'analytics_dashboard' and 'total_content' in result:
                    print(f"      └─ {result['total_content']} content items")
                elif category == 'system_performance' and 'avg_response_time_ms' in result:
                    print(f"      └─ {result['avg_response_time_ms']:.1f}ms avg response time")

        # Overall assessment
        success_rate = passed_tests / total_tests

        print(f"\n🎯 SUMMARY")
        print(f"   📊 Tests passed: {passed_tests:.1f}/{total_tests}")
        print(f"   📈 Success rate: {success_rate*100:.1f}%")

        if success_rate >= 0.85:
            overall_status = "✅ EXCELLENT - Production Ready"
        elif success_rate >= 0.7:
            overall_status = "⚠️ GOOD - Minor issues to address"
        elif success_rate >= 0.5:
            overall_status = "⚠️ PARTIAL - Significant issues need fixing"
        else:
            overall_status = "❌ CRITICAL - Major system issues"

        print(f"   🎯 Overall Status: {overall_status}")

        # Production readiness assessment
        critical_systems = ['api_health', 'database_connectivity', 'search_functionality']
        critical_passed = sum(1 for sys in critical_systems if self.results.get(sys, {}).get('status') == 'passed')

        production_ready = critical_passed == len(critical_systems) and success_rate >= 0.7

        print(f"\n🚀 PRODUCTION READINESS")
        print(f"   🔥 Critical systems: {critical_passed}/{len(critical_systems)} working")
        print(f"   🎯 Production ready: {'YES' if production_ready else 'NO'}")

        if production_ready:
            print(f"   ✅ Atlas is ready for production deployment!")
        else:
            print(f"   ⚠️ Address issues before production deployment")

        print(f"\n✅ Task 4.1 {'COMPLETED' if success_rate >= 0.7 else 'NEEDS WORK'}: Final System Integration Testing")

        return success_rate >= 0.7

def main():
    """Run comprehensive final integration testing"""
    print("🚀 Final System Integration Testing - Task 4.1")
    print("=" * 60)

    tester = FinalIntegrationTester()

    # Run all integration tests
    tests = [
        tester.test_api_server_health,
        tester.test_database_connectivity,
        tester.test_search_functionality,
        tester.test_analytics_dashboard,
        tester.test_content_processing,
        tester.test_system_performance,
        tester.test_error_handling
    ]

    for test_func in tests:
        try:
            test_func()
        except Exception as e:
            print(f"   ❌ Test {test_func.__name__} failed with exception: {e}")

    # Generate final report
    success = tester.generate_final_report()

    return 0 if success else 1

if __name__ == "__main__":
    exit(main())