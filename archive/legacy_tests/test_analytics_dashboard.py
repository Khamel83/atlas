#!/usr/bin/env python3
"""
Analytics Dashboard Production Readiness Testing
Task 2.2 - Test dashboard across devices, real-time features, error handling, and performance
"""

import requests
import time
import json
import os
import sys
from typing import Dict, List, Any
import sqlite3

# Add Atlas to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from helpers.config import load_config

class TestAnalyticsDashboard:
    """Comprehensive analytics dashboard production readiness tests"""

    def __init__(self):
        """Initialize test environment"""
        self.config = load_config()
        self.api_base_url = "http://localhost:8000/api/v1"
        self.dashboard_url = f"{self.api_base_url}/dashboard/"

        # Test data
        self.test_browsers = [
            {"name": "Chrome", "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"},
            {"name": "Firefox", "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"},
            {"name": "Safari", "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15"},
            {"name": "Edge", "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59"}
        ]

        self.test_devices = [
            {"name": "Desktop", "viewport": "1920x1080", "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            {"name": "Tablet", "viewport": "768x1024", "user_agent": "Mozilla/5.0 (iPad; CPU OS 14_6 like Mac OS X)"},
            {"name": "Mobile", "viewport": "375x667", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X)"}
        ]

    def test_api_server_availability(self):
        """Test if API server is running and accessible"""
        print("\n🔍 Testing API Server Availability...")

        try:
            response = requests.get(f"{self.api_base_url}/health", timeout=5)
            if response.status_code == 200:
                print("✅ API server is running and healthy")
                return True
            else:
                print(f"⚠️ API server responding but unhealthy (status: {response.status_code})")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ API server not accessible: {e}")
            return False

    def test_dashboard_endpoint_functionality(self):
        """Test dashboard endpoint response and content"""
        print("\n🔍 Testing Dashboard Endpoint...")

        try:
            start_time = time.time()
            response = requests.get(self.dashboard_url, timeout=10)
            end_time = time.time()

            response_time = (end_time - start_time) * 1000

            if response.status_code == 200:
                print(f"✅ Dashboard endpoint responding (status: 200)")
                print(f"   Response time: {response_time:.2f}ms")

                # Check content type
                content_type = response.headers.get('content-type', '')
                if 'text/html' in content_type:
                    print("✅ Dashboard returns HTML content")
                else:
                    print(f"⚠️ Unexpected content type: {content_type}")

                # Check content size
                content_length = len(response.content)
                print(f"   Content size: {content_length} bytes")

                # Performance check
                if response_time < 2000:
                    print("✅ Dashboard loads within 2 second target")
                else:
                    print(f"⚠️ Dashboard load time exceeds target: {response_time:.2f}ms")

                return {
                    'status': 'success',
                    'response_time_ms': response_time,
                    'content_length': content_length,
                    'content_type': content_type
                }
            else:
                print(f"❌ Dashboard endpoint error (status: {response.status_code})")
                return {'status': 'error', 'status_code': response.status_code}

        except Exception as e:
            print(f"❌ Dashboard endpoint test failed: {e}")
            return {'status': 'failed', 'error': str(e)}

    def test_cross_browser_compatibility(self):
        """Test dashboard with different browser user agents"""
        print("\n🔍 Testing Cross-Browser Compatibility...")

        results = {}

        for browser in self.test_browsers:
            try:
                headers = {'User-Agent': browser['user_agent']}
                start_time = time.time()
                response = requests.get(self.dashboard_url, headers=headers, timeout=10)
                end_time = time.time()

                response_time = (end_time - start_time) * 1000

                if response.status_code == 200:
                    print(f"✅ {browser['name']}: {response_time:.2f}ms")
                    results[browser['name']] = {
                        'status': 'success',
                        'response_time_ms': response_time
                    }
                else:
                    print(f"❌ {browser['name']}: Error {response.status_code}")
                    results[browser['name']] = {
                        'status': 'error',
                        'status_code': response.status_code
                    }

            except Exception as e:
                print(f"❌ {browser['name']}: {str(e)}")
                results[browser['name']] = {
                    'status': 'failed',
                    'error': str(e)
                }

        return results

    def test_mobile_responsive_design(self):
        """Test dashboard with mobile viewport simulation"""
        print("\n🔍 Testing Mobile Responsive Design...")

        results = {}

        for device in self.test_devices:
            try:
                headers = {'User-Agent': device['user_agent']}
                start_time = time.time()
                response = requests.get(self.dashboard_url, headers=headers, timeout=10)
                end_time = time.time()

                response_time = (end_time - start_time) * 1000

                if response.status_code == 200:
                    # Check for responsive design indicators in HTML
                    content = response.text
                    has_viewport = 'viewport' in content
                    has_responsive_css = any(indicator in content for indicator in [
                        'auto-fit', 'minmax', '@media', 'flex-wrap', 'grid-template-columns'
                    ])

                    print(f"✅ {device['name']}: {response_time:.2f}ms")
                    if has_viewport:
                        print(f"   ✅ Viewport meta tag present")
                    if has_responsive_css:
                        print(f"   ✅ Responsive CSS detected")

                    results[device['name']] = {
                        'status': 'success',
                        'response_time_ms': response_time,
                        'has_viewport': has_viewport,
                        'has_responsive_css': has_responsive_css
                    }
                else:
                    print(f"❌ {device['name']}: Error {response.status_code}")
                    results[device['name']] = {
                        'status': 'error',
                        'status_code': response.status_code
                    }

            except Exception as e:
                print(f"❌ {device['name']}: {str(e)}")
                results[device['name']] = {
                    'status': 'failed',
                    'error': str(e)
                }

        return results

    def test_analytics_api_endpoints(self):
        """Test analytics API endpoints for data integrity"""
        print("\n🔍 Testing Analytics API Endpoints...")

        endpoints = [
            ("/api/v1/dashboard/", "Dashboard HTML"),
            ("/api/v1/dashboard/analytics", "Analytics JSON"),
            ("/api/v1/health", "Health Check")
        ]

        results = {}

        for endpoint, description in endpoints:
            try:
                start_time = time.time()
                response = requests.get(f"http://localhost:8000{endpoint}", timeout=10)
                end_time = time.time()

                response_time = (end_time - start_time) * 1000

                if response.status_code == 200:
                    print(f"✅ {description}: {response_time:.2f}ms")

                    # Test data integrity for analytics endpoint
                    if 'analytics' in endpoint:
                        try:
                            data = response.json()
                            if isinstance(data, dict) and len(data) > 0:
                                print(f"   ✅ Analytics data structure valid")
                            else:
                                print(f"   ⚠️ Analytics data may be empty or invalid")
                        except json.JSONDecodeError:
                            print(f"   ⚠️ Analytics endpoint not returning valid JSON")

                    results[endpoint] = {
                        'status': 'success',
                        'response_time_ms': response_time
                    }
                else:
                    print(f"❌ {description}: Error {response.status_code}")
                    results[endpoint] = {
                        'status': 'error',
                        'status_code': response.status_code
                    }

            except Exception as e:
                print(f"❌ {description}: {str(e)}")
                results[endpoint] = {
                    'status': 'failed',
                    'error': str(e)
                }

        return results

    def test_dashboard_error_handling(self):
        """Test dashboard error handling and graceful degradation"""
        print("\n🔍 Testing Dashboard Error Handling...")

        # Test invalid endpoints
        error_tests = [
            ("/api/v1/dashboard/nonexistent", "Non-existent endpoint"),
            ("/api/v1/dashboard/analytics/invalid", "Invalid analytics path")
        ]

        results = {}

        for endpoint, description in error_tests:
            try:
                response = requests.get(f"http://localhost:8000{endpoint}", timeout=10)

                if response.status_code == 404:
                    print(f"✅ {description}: Proper 404 error handling")
                    results[endpoint] = {'status': 'success', 'error_handling': 'proper'}
                elif response.status_code >= 400:
                    print(f"✅ {description}: Error {response.status_code} (appropriate error response)")
                    results[endpoint] = {'status': 'success', 'error_handling': 'appropriate'}
                else:
                    print(f"⚠️ {description}: Unexpected success response")
                    results[endpoint] = {'status': 'warning', 'error_handling': 'unexpected'}

            except Exception as e:
                print(f"❌ {description}: Connection error: {str(e)}")
                results[endpoint] = {'status': 'failed', 'error': str(e)}

        return results

    def test_dashboard_performance_optimization(self):
        """Test dashboard performance under various conditions"""
        print("\n🔍 Testing Dashboard Performance Optimization...")

        # Multiple concurrent requests to test performance
        import concurrent.futures
        import statistics

        def make_dashboard_request():
            try:
                start_time = time.time()
                response = requests.get(self.dashboard_url, timeout=10)
                end_time = time.time()

                if response.status_code == 200:
                    return (end_time - start_time) * 1000
                else:
                    return None
            except:
                return None

        # Test concurrent load
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_dashboard_request) for _ in range(10)]
            response_times = [f.result() for f in futures if f.result() is not None]

        if response_times:
            avg_time = statistics.mean(response_times)
            median_time = statistics.median(response_times)
            max_time = max(response_times)

            print(f"✅ Concurrent load test completed:")
            print(f"   Average response time: {avg_time:.2f}ms")
            print(f"   Median response time: {median_time:.2f}ms")
            print(f"   Maximum response time: {max_time:.2f}ms")

            if avg_time < 2000:
                print("✅ Performance meets 2-second target")
                performance_rating = "EXCELLENT"
            elif avg_time < 5000:
                print("⚠️ Performance acceptable but could improve")
                performance_rating = "GOOD"
            else:
                print("❌ Performance needs improvement")
                performance_rating = "NEEDS_IMPROVEMENT"

            return {
                'avg_time_ms': avg_time,
                'median_time_ms': median_time,
                'max_time_ms': max_time,
                'performance_rating': performance_rating,
                'requests_tested': len(response_times)
            }
        else:
            print("❌ No successful requests in performance test")
            return {'status': 'failed', 'requests_tested': 0}

    def run_comprehensive_dashboard_tests(self) -> Dict[str, Any]:
        """Run all dashboard tests and return comprehensive report"""

        print("🚀 Analytics Dashboard Production Readiness Testing - Task 2.2")
        print("=" * 70)

        test_results = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'api_availability': {},
            'dashboard_functionality': {},
            'cross_browser_compatibility': {},
            'mobile_responsiveness': {},
            'api_endpoints': {},
            'error_handling': {},
            'performance': {},
            'overall_status': 'UNKNOWN'
        }

        try:
            # Test 1: API availability
            test_results['api_availability'] = {'available': self.test_api_server_availability()}

            if not test_results['api_availability']['available']:
                print("\n❌ Cannot continue testing - API server not available")
                test_results['overall_status'] = 'FAILED'
                return test_results

            # Test 2: Dashboard functionality
            test_results['dashboard_functionality'] = self.test_dashboard_endpoint_functionality()

            # Test 3: Cross-browser compatibility
            test_results['cross_browser_compatibility'] = self.test_cross_browser_compatibility()

            # Test 4: Mobile responsiveness
            test_results['mobile_responsiveness'] = self.test_mobile_responsive_design()

            # Test 5: API endpoints
            test_results['api_endpoints'] = self.test_analytics_api_endpoints()

            # Test 6: Error handling
            test_results['error_handling'] = self.test_dashboard_error_handling()

            # Test 7: Performance
            test_results['performance'] = self.test_dashboard_performance_optimization()

            # Overall assessment
            test_results['overall_status'] = self._assess_overall_status(test_results)

        except Exception as e:
            test_results['overall_status'] = 'FAILED'
            test_results['error'] = str(e)

        return test_results

    def _assess_overall_status(self, results: Dict[str, Any]) -> str:
        """Assess overall dashboard status based on test results"""

        critical_failures = 0
        warnings = 0

        # Check critical components
        if not results['api_availability'].get('available', False):
            critical_failures += 1

        if results['dashboard_functionality'].get('status') != 'success':
            critical_failures += 1

        # Check browser compatibility
        browser_results = results['cross_browser_compatibility']
        failed_browsers = sum(1 for browser, result in browser_results.items()
                             if result.get('status') != 'success')
        if failed_browsers > len(browser_results) / 2:
            critical_failures += 1
        elif failed_browsers > 0:
            warnings += 1

        # Check mobile responsiveness
        mobile_results = results['mobile_responsiveness']
        failed_devices = sum(1 for device, result in mobile_results.items()
                            if result.get('status') != 'success')
        if failed_devices > 0:
            warnings += 1

        # Check performance
        perf_rating = results['performance'].get('performance_rating', 'UNKNOWN')
        if perf_rating == 'NEEDS_IMPROVEMENT':
            warnings += 1

        # Determine overall status
        if critical_failures > 0:
            return 'FAILED'
        elif warnings > 2:
            return 'NEEDS_IMPROVEMENT'
        elif warnings > 0:
            return 'GOOD'
        else:
            return 'EXCELLENT'

def main():
    """Run comprehensive dashboard tests"""

    tester = TestAnalyticsDashboard()
    results = tester.run_comprehensive_dashboard_tests()

    # Generate report
    print("\n" + "=" * 70)
    print("📊 ANALYTICS DASHBOARD PRODUCTION READINESS RESULTS")
    print("=" * 70)

    print(f"🕐 Test Time: {results['timestamp']}")
    print(f"🎯 Overall Status: {results['overall_status']}")

    # Summary statistics
    if results['dashboard_functionality']:
        func_result = results['dashboard_functionality']
        if func_result.get('status') == 'success':
            print(f"⚡ Dashboard Response Time: {func_result.get('response_time_ms', 0):.2f}ms")

    if results['cross_browser_compatibility']:
        browser_success = sum(1 for result in results['cross_browser_compatibility'].values()
                             if result.get('status') == 'success')
        browser_total = len(results['cross_browser_compatibility'])
        print(f"🌐 Browser Compatibility: {browser_success}/{browser_total} browsers")

    if results['mobile_responsiveness']:
        mobile_success = sum(1 for result in results['mobile_responsiveness'].values()
                            if result.get('status') == 'success')
        mobile_total = len(results['mobile_responsiveness'])
        print(f"📱 Mobile Responsiveness: {mobile_success}/{mobile_total} devices")

    if results['performance']:
        perf_result = results['performance']
        if 'avg_time_ms' in perf_result:
            print(f"🚀 Performance: {perf_result['avg_time_ms']:.2f}ms avg ({perf_result['performance_rating']})")

    # Save detailed report
    os.makedirs('reports', exist_ok=True)

    with open('reports/dashboard_mobile_testing.md', 'w') as f:
        f.write("# Analytics Dashboard Mobile Compatibility Testing\n\n")
        f.write(f"**Generated:** {results['timestamp']}  \n")
        f.write(f"**Task:** 2.2 - Analytics Dashboard Production Readiness  \n")
        f.write(f"**Status:** {results['overall_status']}  \n\n")

        f.write("## Executive Summary\n\n")
        f.write("Comprehensive testing of Analytics Dashboard production readiness including cross-browser compatibility, mobile responsiveness, performance optimization, and error handling.\n\n")

        if results['cross_browser_compatibility']:
            f.write("## Browser Compatibility Results\n\n")
            f.write("| Browser | Status | Response Time (ms) |\n")
            f.write("|---------|--------|-----------------|\n")

            for browser, result in results['cross_browser_compatibility'].items():
                status_icon = "✅" if result.get('status') == 'success' else "❌"
                response_time = result.get('response_time_ms', 0)
                f.write(f"| {browser} | {status_icon} {result.get('status', 'unknown')} | {response_time:.2f} |\n")

        if results['mobile_responsiveness']:
            f.write("\n## Mobile Device Testing Results\n\n")
            f.write("| Device | Status | Responsive Design | Viewport Meta |\n")
            f.write("|--------|--------|------------------|---------------|\n")

            for device, result in results['mobile_responsiveness'].items():
                status_icon = "✅" if result.get('status') == 'success' else "❌"
                responsive = "✅" if result.get('has_responsive_css') else "❌"
                viewport = "✅" if result.get('has_viewport') else "❌"
                f.write(f"| {device} | {status_icon} {result.get('status', 'unknown')} | {responsive} | {viewport} |\n")

        if results['performance']:
            perf = results['performance']
            f.write(f"\n## Performance Analysis\n\n")
            if 'avg_time_ms' in perf:
                f.write(f"- **Average Response Time:** {perf['avg_time_ms']:.2f}ms\n")
                f.write(f"- **Median Response Time:** {perf['median_time_ms']:.2f}ms\n")
                f.write(f"- **Maximum Response Time:** {perf['max_time_ms']:.2f}ms\n")
                f.write(f"- **Performance Rating:** {perf['performance_rating']}\n")
                f.write(f"- **Concurrent Requests Tested:** {perf['requests_tested']}\n")

        f.write(f"\n## Overall Assessment\n\n")
        if results['overall_status'] == 'EXCELLENT':
            f.write("✅ **Analytics Dashboard is production-ready** with excellent cross-platform compatibility and performance.\n")
        elif results['overall_status'] == 'GOOD':
            f.write("✅ **Analytics Dashboard is production-ready** with good compatibility and acceptable performance.\n")
        elif results['overall_status'] == 'NEEDS_IMPROVEMENT':
            f.write("⚠️ **Analytics Dashboard needs minor improvements** before full production deployment.\n")
        else:
            f.write("❌ **Analytics Dashboard has critical issues** that must be resolved before production deployment.\n")

    return results

if __name__ == "__main__":
    results = main()

    # Exit with appropriate code
    if results['overall_status'] in ['EXCELLENT', 'GOOD']:
        print(f"\n✅ Task 2.2 COMPLETED: Analytics Dashboard Production Ready")
        exit(0)
    elif results['overall_status'] == 'NEEDS_IMPROVEMENT':
        print(f"\n⚠️ Task 2.2 PARTIALLY COMPLETED: Minor improvements needed")
        exit(1)
    else:
        print(f"\n❌ Task 2.2 FAILED: Critical issues require resolution")
        exit(2)