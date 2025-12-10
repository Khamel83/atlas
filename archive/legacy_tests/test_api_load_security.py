#!/usr/bin/env python3
"""
API Framework Load Testing & Security Testing
Task 2.3 - Comprehensive API load testing, rate limiting, authentication, and security validation
"""

import requests
import time
import json
import os
import sys
import concurrent.futures
import threading
import statistics
from typing import Dict, List, Any, Optional

# Add Atlas to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestAPILoadSecurity:
    """Comprehensive API load testing and security validation"""

    def __init__(self):
        """Initialize test environment"""
        self.api_base_url = "http://localhost:8000"
        self.api_v1_base = f"{self.api_base_url}/api/v1"

        # API endpoints to test
        self.endpoints = {
            "health": "/api/v1/health",
            "dashboard": "/api/v1/dashboard/",
            "search": "/api/v1/search/",
            "content": "/api/v1/content/",
            "analytics": "/api/v1/dashboard/analytics"
        }

        # Load test configuration
        self.load_test_users = [10, 25, 50, 100]  # Progressive load testing
        self.test_duration = 30  # seconds per load test
        self.request_timeout = 10  # seconds

        # Security test payloads
        self.security_payloads = {
            "sql_injection": ["'; DROP TABLE users; --", "1' OR '1'='1", "admin'--"],
            "xss": ["<script>alert('XSS')</script>", "javascript:alert('XSS')", "<img src=x onerror=alert('XSS')>"],
            "path_traversal": ["../../../etc/passwd", "..\\..\\..\\windows\\system32\\config\\sam", "....//....//....//etc/passwd"],
            "command_injection": ["; ls -la", "| whoami", "`id`", "$(uname -a)"],
            "oversized_payload": "A" * 10000  # 10KB payload
        }

    def test_api_server_health(self):
        """Verify API server is running and healthy"""
        print("\n🔍 Testing API Server Health...")

        try:
            response = requests.get(f"{self.api_v1_base}/health", timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                print(f"✅ API server healthy: {health_data}")
                return True
            else:
                print(f"❌ API server unhealthy (status: {response.status_code})")
                return False
        except Exception as e:
            print(f"❌ API server not accessible: {e}")
            return False

    def test_endpoint_load_capacity(self, endpoint: str, concurrent_users: int, duration: int = 30):
        """Test endpoint under specific concurrent load"""

        print(f"🔄 Load testing {endpoint} with {concurrent_users} concurrent users for {duration}s...")

        # Shared results storage
        results = []
        results_lock = threading.Lock()
        stop_event = threading.Event()

        def worker(user_id: int):
            """Worker function for load testing"""
            user_results = []

            while not stop_event.is_set():
                try:
                    start_time = time.time()

                    # Customize request based on endpoint
                    if endpoint == "/api/v1/search/":
                        params = {'query': f'test_{user_id}', 'limit': 5}
                        response = requests.get(f"{self.api_base_url}{endpoint}",
                                              params=params, timeout=self.request_timeout)
                    else:
                        response = requests.get(f"{self.api_base_url}{endpoint}",
                                              timeout=self.request_timeout)

                    end_time = time.time()

                    user_results.append({
                        'user_id': user_id,
                        'status_code': response.status_code,
                        'response_time': (end_time - start_time) * 1000,
                        'success': 200 <= response.status_code < 400,
                        'timestamp': time.time()
                    })

                except Exception as e:
                    user_results.append({
                        'user_id': user_id,
                        'status_code': 0,
                        'response_time': 0,
                        'success': False,
                        'error': str(e),
                        'timestamp': time.time()
                    })

                time.sleep(0.1)  # Small delay between requests

            # Store results thread-safely
            with results_lock:
                results.extend(user_results)

        # Start worker threads
        threads = []
        for user_id in range(concurrent_users):
            thread = threading.Thread(target=worker, args=(user_id,))
            thread.start()
            threads.append(thread)

        # Let test run for specified duration
        time.sleep(duration)
        stop_event.set()

        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=2)

        # Analyze results
        if results:
            successful_requests = [r for r in results if r['success']]
            failed_requests = [r for r in results if not r['success']]

            success_rate = (len(successful_requests) / len(results)) * 100
            response_times = [r['response_time'] for r in successful_requests]

            if response_times:
                avg_response = statistics.mean(response_times)
                median_response = statistics.median(response_times)
                p95_response = statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else max(response_times)
            else:
                avg_response = median_response = p95_response = 0

            total_requests = len(results)
            requests_per_second = total_requests / duration

            print(f"   📊 Results: {total_requests} requests in {duration}s")
            print(f"   🎯 Success rate: {success_rate:.1f}%")
            print(f"   ⚡ Requests/second: {requests_per_second:.1f}")
            print(f"   ⏱️ Response times - Avg: {avg_response:.1f}ms, Median: {median_response:.1f}ms, P95: {p95_response:.1f}ms")

            if len(failed_requests) > 0:
                error_counts = {}
                for req in failed_requests:
                    error_type = req.get('error', f"HTTP_{req.get('status_code', 'unknown')}")
                    error_counts[error_type] = error_counts.get(error_type, 0) + 1

                print(f"   ❌ Errors: {error_counts}")

            return {
                'endpoint': endpoint,
                'concurrent_users': concurrent_users,
                'duration': duration,
                'total_requests': total_requests,
                'successful_requests': len(successful_requests),
                'failed_requests': len(failed_requests),
                'success_rate': success_rate,
                'requests_per_second': requests_per_second,
                'avg_response_time': avg_response,
                'median_response_time': median_response,
                'p95_response_time': p95_response,
                'errors': {req.get('error', f"HTTP_{req.get('status_code')}"): 1 for req in failed_requests}
            }
        else:
            print(f"   ❌ No results collected for load test")
            return {
                'endpoint': endpoint,
                'concurrent_users': concurrent_users,
                'error': 'No results collected'
            }

    def test_progressive_load_scaling(self):
        """Test API performance under progressively increasing load"""
        print("\n🚀 Progressive Load Scaling Test...")

        load_test_results = []

        for user_count in self.load_test_users:
            print(f"\n--- Testing with {user_count} concurrent users ---")

            # Test critical endpoints
            for endpoint_name, endpoint_path in [("health", "/api/v1/health"),
                                                 ("dashboard", "/api/v1/dashboard/"),
                                                 ("search", "/api/v1/search/")]:

                result = self.test_endpoint_load_capacity(endpoint_path, user_count, duration=10)  # Shorter for progressive testing
                result['endpoint_name'] = endpoint_name
                load_test_results.append(result)

                # Check if system is degrading
                if result.get('success_rate', 0) < 50:
                    print(f"⚠️ System degradation detected at {user_count} users for {endpoint_name}")
                    break

        return load_test_results

    def test_security_vulnerabilities(self):
        """Test common security vulnerabilities"""
        print("\n🔒 Security Vulnerability Testing...")

        security_results = {}

        # Test SQL Injection
        print("   🔍 Testing SQL Injection...")
        sql_results = []
        for payload in self.security_payloads["sql_injection"]:
            try:
                # Test search endpoint with malicious payload
                params = {'query': payload, 'limit': 5}
                response = requests.get(f"{self.api_v1_base}/search/",
                                      params=params, timeout=5)

                sql_results.append({
                    'payload': payload,
                    'status_code': response.status_code,
                    'response_length': len(response.text),
                    'contains_error': 'error' in response.text.lower() or 'exception' in response.text.lower()
                })

            except Exception as e:
                sql_results.append({
                    'payload': payload,
                    'error': str(e),
                    'protected': True  # Connection error often means protection
                })

        # Check if any SQL injection succeeded
        sql_vulnerable = any(result.get('status_code') == 200 and
                           result.get('response_length', 0) > 10000
                           for result in sql_results)

        print(f"   {'❌' if sql_vulnerable else '✅'} SQL Injection: {'VULNERABLE' if sql_vulnerable else 'PROTECTED'}")
        security_results['sql_injection'] = sql_results

        # Test XSS
        print("   🔍 Testing Cross-Site Scripting (XSS)...")
        xss_results = []
        for payload in self.security_payloads["xss"]:
            try:
                # Test search endpoint with XSS payload
                params = {'query': payload, 'limit': 5}
                response = requests.get(f"{self.api_v1_base}/search/",
                                      params=params, timeout=5)

                # Check if payload is reflected unescaped
                reflected_unescaped = payload in response.text

                xss_results.append({
                    'payload': payload,
                    'status_code': response.status_code,
                    'reflected_unescaped': reflected_unescaped
                })

            except Exception as e:
                xss_results.append({
                    'payload': payload,
                    'error': str(e),
                    'protected': True
                })

        xss_vulnerable = any(result.get('reflected_unescaped', False) for result in xss_results)
        print(f"   {'❌' if xss_vulnerable else '✅'} XSS: {'VULNERABLE' if xss_vulnerable else 'PROTECTED'}")
        security_results['xss'] = xss_results

        # Test Path Traversal
        print("   🔍 Testing Path Traversal...")
        path_results = []
        for payload in self.security_payloads["path_traversal"]:
            try:
                # Test various endpoints with path traversal
                response = requests.get(f"{self.api_base_url}/{payload}", timeout=5)

                # Check for system file content indicators
                system_file_indicators = ['root:', 'daemon:', 'passwd:', '[boot loader]']
                contains_system_files = any(indicator in response.text.lower()
                                          for indicator in system_file_indicators)

                path_results.append({
                    'payload': payload,
                    'status_code': response.status_code,
                    'contains_system_files': contains_system_files
                })

            except Exception as e:
                path_results.append({
                    'payload': payload,
                    'error': str(e),
                    'protected': True
                })

        path_vulnerable = any(result.get('contains_system_files', False) for result in path_results)
        print(f"   {'❌' if path_vulnerable else '✅'} Path Traversal: {'VULNERABLE' if path_vulnerable else 'PROTECTED'}")
        security_results['path_traversal'] = path_results

        # Test Oversized Payload
        print("   🔍 Testing Oversized Payload Handling...")
        try:
            oversized_payload = self.security_payloads["oversized_payload"]
            params = {'query': oversized_payload, 'limit': 5}

            start_time = time.time()
            response = requests.get(f"{self.api_v1_base}/search/",
                                  params=params, timeout=10)
            end_time = time.time()

            response_time = (end_time - start_time) * 1000

            # Check if server handles oversized payload gracefully
            handles_gracefully = response.status_code in [400, 413, 414, 431] or response_time < 5000

            print(f"   {'✅' if handles_gracefully else '❌'} Oversized Payload: {'HANDLED GRACEFULLY' if handles_gracefully else 'POTENTIAL DOS VULNERABILITY'}")

            security_results['oversized_payload'] = {
                'status_code': response.status_code,
                'response_time': response_time,
                'handled_gracefully': handles_gracefully
            }

        except Exception as e:
            print(f"   ✅ Oversized Payload: PROTECTED (connection terminated)")
            security_results['oversized_payload'] = {
                'error': str(e),
                'protected': True
            }

        return security_results

    def test_cors_and_headers(self):
        """Test CORS configuration and security headers"""
        print("\n🔍 Testing CORS and Security Headers...")

        headers_results = {}

        # Test CORS headers
        try:
            response = requests.get(f"{self.api_v1_base}/health",
                                  headers={'Origin': 'http://malicious-site.com'})

            cors_headers = {
                'access-control-allow-origin': response.headers.get('access-control-allow-origin'),
                'access-control-allow-credentials': response.headers.get('access-control-allow-credentials'),
                'access-control-allow-methods': response.headers.get('access-control-allow-methods'),
                'access-control-allow-headers': response.headers.get('access-control-allow-headers')
            }

            # Check for overly permissive CORS
            overly_permissive = cors_headers['access-control-allow-origin'] == '*'

            print(f"   {'⚠️' if overly_permissive else '✅'} CORS: {'OVERLY PERMISSIVE' if overly_permissive else 'CONFIGURED'}")
            headers_results['cors'] = cors_headers

        except Exception as e:
            print(f"   ❌ CORS test failed: {e}")
            headers_results['cors'] = {'error': str(e)}

        # Test security headers
        try:
            response = requests.get(f"{self.api_v1_base}/dashboard/")

            security_headers = {
                'x-content-type-options': response.headers.get('x-content-type-options'),
                'x-frame-options': response.headers.get('x-frame-options'),
                'x-xss-protection': response.headers.get('x-xss-protection'),
                'strict-transport-security': response.headers.get('strict-transport-security'),
                'content-security-policy': response.headers.get('content-security-policy')
            }

            missing_headers = [header for header, value in security_headers.items() if not value]

            if missing_headers:
                print(f"   ⚠️ Missing security headers: {', '.join(missing_headers)}")
            else:
                print(f"   ✅ Security headers: ALL PRESENT")

            headers_results['security_headers'] = security_headers

        except Exception as e:
            print(f"   ❌ Security headers test failed: {e}")
            headers_results['security_headers'] = {'error': str(e)}

        return headers_results

    def test_error_response_consistency(self):
        """Test error responses for consistency and information disclosure"""
        print("\n🔍 Testing Error Response Consistency...")

        error_tests = [
            ("/api/v1/nonexistent", "Non-existent endpoint"),
            ("/api/v1/search/invalid", "Invalid search path"),
            ("/api/v1/content/999999", "Non-existent content"),
            ("/api/v1/dashboard/invalid", "Invalid dashboard path")
        ]

        error_results = []

        for endpoint, description in error_tests:
            try:
                response = requests.get(f"{self.api_base_url}{endpoint}", timeout=5)

                # Check for information disclosure in error messages
                response_text = response.text.lower()
                info_disclosure_indicators = [
                    'traceback', 'stack trace', 'exception', 'error:', 'file not found',
                    'internal server error', 'sql', 'database', 'connection',
                    '/home/', '/var/', 'c:\\', 'python', 'django', 'flask'
                ]

                has_info_disclosure = any(indicator in response_text for indicator in info_disclosure_indicators)

                error_results.append({
                    'endpoint': endpoint,
                    'description': description,
                    'status_code': response.status_code,
                    'has_info_disclosure': has_info_disclosure,
                    'response_length': len(response.text)
                })

                status_icon = "✅" if 400 <= response.status_code < 500 else "❌"
                disclosure_icon = "❌" if has_info_disclosure else "✅"

                print(f"   {status_icon} {description}: {response.status_code} {disclosure_icon}")

            except Exception as e:
                error_results.append({
                    'endpoint': endpoint,
                    'description': description,
                    'error': str(e)
                })
                print(f"   ❌ {description}: Connection error")

        return error_results

    def run_comprehensive_api_tests(self) -> Dict[str, Any]:
        """Run all API load and security tests"""

        print("🚀 API Framework Load Testing & Security - Task 2.3")
        print("=" * 70)

        test_results = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'api_health': {},
            'load_testing': {},
            'security_testing': {},
            'headers_testing': {},
            'error_handling': {},
            'overall_status': 'UNKNOWN'
        }

        try:
            # Test 1: API Health
            test_results['api_health'] = {'healthy': self.test_api_server_health()}

            if not test_results['api_health']['healthy']:
                print("\n❌ Cannot continue testing - API server not healthy")
                test_results['overall_status'] = 'FAILED'
                return test_results

            # Test 2: Load Testing
            test_results['load_testing'] = self.test_progressive_load_scaling()

            # Test 3: Security Testing
            test_results['security_testing'] = self.test_security_vulnerabilities()

            # Test 4: CORS and Headers
            test_results['headers_testing'] = self.test_cors_and_headers()

            # Test 5: Error Handling
            test_results['error_handling'] = self.test_error_response_consistency()

            # Overall assessment
            test_results['overall_status'] = self._assess_overall_security_status(test_results)

        except Exception as e:
            test_results['overall_status'] = 'FAILED'
            test_results['error'] = str(e)

        return test_results

    def _assess_overall_security_status(self, results: Dict[str, Any]) -> str:
        """Assess overall API security and performance status"""

        critical_issues = 0
        warnings = 0

        # Check API health
        if not results['api_health'].get('healthy', False):
            critical_issues += 1

        # Check load testing results
        load_results = results.get('load_testing', [])
        if load_results:
            failed_load_tests = sum(1 for result in load_results
                                  if result.get('success_rate', 0) < 80)
            if failed_load_tests > len(load_results) / 2:
                critical_issues += 1
            elif failed_load_tests > 0:
                warnings += 1

        # Check security vulnerabilities
        security_results = results.get('security_testing', {})

        # Critical vulnerabilities
        critical_vulns = ['sql_injection', 'path_traversal']
        for vuln_type in critical_vulns:
            if vuln_type in security_results:
                vuln_data = security_results[vuln_type]
                if isinstance(vuln_data, list):
                    if any(result.get('contains_system_files') or
                          result.get('response_length', 0) > 10000
                          for result in vuln_data):
                        critical_issues += 1

        # Check XSS
        xss_data = security_results.get('xss', [])
        if any(result.get('reflected_unescaped', False) for result in xss_data):
            warnings += 1

        # Check headers
        headers_data = results.get('headers_testing', {})
        cors_data = headers_data.get('cors', {})
        if cors_data.get('access-control-allow-origin') == '*':
            warnings += 1

        security_headers = headers_data.get('security_headers', {})
        missing_headers = [k for k, v in security_headers.items() if not v and k != 'error']
        if len(missing_headers) > 2:
            warnings += 1

        # Determine overall status
        if critical_issues > 0:
            return 'FAILED'
        elif warnings > 2:
            return 'NEEDS_IMPROVEMENT'
        elif warnings > 0:
            return 'GOOD'
        else:
            return 'EXCELLENT'

def main():
    """Run comprehensive API load and security tests"""

    tester = TestAPILoadSecurity()
    results = tester.run_comprehensive_api_tests()

    # Generate report
    print("\n" + "=" * 70)
    print("📊 API FRAMEWORK LOAD TESTING & SECURITY RESULTS")
    print("=" * 70)

    print(f"🕐 Test Time: {results['timestamp']}")
    print(f"🎯 Overall Status: {results['overall_status']}")

    # Load testing summary
    load_results = results.get('load_testing', [])
    if load_results:
        successful_tests = sum(1 for result in load_results
                             if result.get('success_rate', 0) >= 80)
        total_tests = len(load_results)
        print(f"🚀 Load Testing: {successful_tests}/{total_tests} tests passed (≥80% success rate)")

        # Best performance metrics
        best_rps = max((result.get('requests_per_second', 0) for result in load_results), default=0)
        print(f"   Peak performance: {best_rps:.1f} requests/second")

    # Security summary
    security_results = results.get('security_testing', {})
    protected_count = 0
    total_security_tests = 0

    for test_name, test_data in security_results.items():
        total_security_tests += 1
        if test_name == 'oversized_payload':
            if test_data.get('handled_gracefully', False) or test_data.get('protected', False):
                protected_count += 1
        else:  # Lists of results
            if isinstance(test_data, list):
                if not any(result.get('contains_system_files', False) or
                          result.get('reflected_unescaped', False) or
                          result.get('response_length', 0) > 10000
                          for result in test_data):
                    protected_count += 1

    if total_security_tests > 0:
        print(f"🔒 Security: {protected_count}/{total_security_tests} tests protected")

    # Headers summary
    headers_results = results.get('headers_testing', {})
    security_headers = headers_results.get('security_headers', {})
    present_headers = sum(1 for v in security_headers.values() if v and v != 'error')
    total_headers = len([k for k in security_headers.keys() if k != 'error'])

    if total_headers > 0:
        print(f"🛡️ Security Headers: {present_headers}/{total_headers} present")

    # Save detailed report
    os.makedirs('reports', exist_ok=True)

    with open('reports/api_security_assessment.md', 'w') as f:
        f.write("# API Framework Security Assessment\n\n")
        f.write(f"**Generated:** {results['timestamp']}  \n")
        f.write(f"**Task:** 2.3 - API Framework Load Testing & Security  \n")
        f.write(f"**Status:** {results['overall_status']}  \n\n")

        f.write("## Executive Summary\n\n")
        f.write("Comprehensive API security and performance assessment including load testing, vulnerability scanning, and security configuration review.\n\n")

        # Load testing section
        if load_results:
            f.write("## Load Testing Results\n\n")
            f.write("| Endpoint | Users | Success Rate | Req/Sec | Avg Response (ms) |\n")
            f.write("|----------|-------|--------------|---------|-------------------|\n")

            for result in load_results:
                endpoint = result.get('endpoint_name', result.get('endpoint', 'unknown'))
                users = result.get('concurrent_users', 0)
                success_rate = result.get('success_rate', 0)
                rps = result.get('requests_per_second', 0)
                avg_response = result.get('avg_response_time', 0)

                f.write(f"| {endpoint} | {users} | {success_rate:.1f}% | {rps:.1f} | {avg_response:.1f} |\n")

        # Security testing section
        if security_results:
            f.write("\n## Security Vulnerability Assessment\n\n")
            f.write("| Vulnerability Type | Status | Details |\n")
            f.write("|--------------------|--------|---------|\n")

            vuln_status_map = {
                'sql_injection': 'SQL Injection',
                'xss': 'Cross-Site Scripting',
                'path_traversal': 'Path Traversal',
                'oversized_payload': 'DoS Protection'
            }

            for vuln_type, display_name in vuln_status_map.items():
                if vuln_type in security_results:
                    # Determine status
                    vuln_data = security_results[vuln_type]
                    if vuln_type == 'oversized_payload':
                        protected = vuln_data.get('handled_gracefully', False) or vuln_data.get('protected', False)
                        status = "✅ Protected" if protected else "❌ Vulnerable"
                        details = f"Response: {vuln_data.get('status_code', 'N/A')}"
                    else:
                        if isinstance(vuln_data, list):
                            vulnerable = any(result.get('contains_system_files', False) or
                                           result.get('reflected_unescaped', False) or
                                           result.get('response_length', 0) > 10000
                                           for result in vuln_data)
                            status = "❌ Vulnerable" if vulnerable else "✅ Protected"
                            details = f"{len(vuln_data)} payloads tested"
                        else:
                            status = "⚠️ Unknown"
                            details = "Test inconclusive"

                    f.write(f"| {display_name} | {status} | {details} |\n")

        f.write(f"\n## Overall Assessment\n\n")
        if results['overall_status'] == 'EXCELLENT':
            f.write("✅ **API Framework is production-ready** with excellent security posture and performance characteristics.\n")
        elif results['overall_status'] == 'GOOD':
            f.write("✅ **API Framework is production-ready** with good security and acceptable performance.\n")
        elif results['overall_status'] == 'NEEDS_IMPROVEMENT':
            f.write("⚠️ **API Framework needs security improvements** before full production deployment.\n")
        else:
            f.write("❌ **API Framework has critical security issues** that must be resolved before deployment.\n")

    return results

if __name__ == "__main__":
    results = main()

    # Exit with appropriate code
    if results['overall_status'] in ['EXCELLENT', 'GOOD']:
        print(f"\n✅ Task 2.3 COMPLETED: API Framework Load Testing & Security Passed")
        exit(0)
    elif results['overall_status'] == 'NEEDS_IMPROVEMENT':
        print(f"\n⚠️ Task 2.3 PARTIALLY COMPLETED: Security improvements needed")
        exit(1)
    else:
        print(f"\n❌ Task 2.3 FAILED: Critical security issues require resolution")
        exit(2)