#!/usr/bin/env python3
"""
Master Test Runner

Runs all test suites and provides comprehensive testing coverage
for the Atlas refactored system.
"""

import sys
import os
import time
import subprocess
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


class TestRunner:
    """Master test runner for all test suites"""

    def __init__(self):
        self.test_suites = [
            {
                'name': 'Database Tests',
                'file': 'test_extensive_database.py',
                'description': 'Comprehensive database functionality testing'
            },
            {
                'name': 'Processor Tests',
                'file': 'test_extensive_processor.py',
                'description': 'Generic content processor testing'
            },
            {
                'name': 'API Tests',
                'file': 'test_extensive_api.py',
                'description': 'REST API endpoint testing',
                'note': 'Requires API server running at localhost:8000'
            },
            {
                'name': 'Stress Load Tests',
                'file': 'test_stress_load.py',
                'description': 'System performance and stability under load',
                'warning': 'Creates large amounts of test data'
            },
            {
                'name': 'Comprehensive System Tests',
                'file': 'test_comprehensive_system.py',
                'description': 'End-to-end system validation'
            },
            {
                'name': 'Original Component Tests',
                'files': [
                    'test_database.py',
                    'test_processor.py',
                    'test_api_direct.py',
                    'test_web_interface.py'
                ],
                'description': 'Original component validation tests'
            }
        ]
        self.results = []
        self.start_time = time.time()

    def run_test_suite(self, suite):
        """Run a single test suite"""
        print(f"\n{'='*60}")
        print(f"🧪 Running {suite['name']}")
        print(f"📋 {suite['description']}")
        if 'note' in suite:
            print(f"ℹ️  {suite['note']}")
        if 'warning' in suite:
            print(f"⚠️  {suite['warning']}")
        print(f"{'='*60}")

        suite_start_time = time.time()

        try:
            if 'files' in suite:
                # Multiple files for this suite
                all_passed = True
                for test_file in suite['files']:
                    result = self.run_single_test(test_file, suite['name'])
                    if not result['passed']:
                        all_passed = False
                    self.results.append(result)
                return all_passed
            else:
                # Single file for this suite
                result = self.run_single_test(suite['file'], suite['name'])
                self.results.append(result)
                return result['passed']
        except Exception as e:
            error_result = {
                'suite': suite['name'],
                'passed': False,
                'error': str(e),
                'duration': time.time() - suite_start_time
            }
            self.results.append(error_result)
            return False

    def run_single_test(self, test_file, suite_name):
        """Run a single test file"""
        print(f"\n📝 Running {test_file}...")

        start_time = time.time()
        try:
            # Run the test file
            result = subprocess.run(
                [sys.executable, test_file],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            duration = time.time() - start_time

            # Analyze output for test results
            output_lines = result.stdout.split('\n')
            error_lines = result.stderr.split('\n')

            # Check for test result patterns
            passed = result.returncode == 0
            test_count = 0
            passed_count = 0

            # Parse test results from output
            for line in output_lines:
                if 'Tests:' in line or 'passed:' in line.lower():
                    # Try to extract test counts
                    if 'passed:' in line.lower():
                        try:
                            parts = line.lower().split('passed:')
                            if len(parts) > 1:
                                passed_part = parts[1].strip().split()[0]
                                passed_count = int(passed_part)
                        except:
                            pass

            return {
                'suite': f"{suite_name} - {test_file}",
                'passed': passed,
                'duration': duration,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'test_count': test_count,
                'passed_count': passed_count
            }

        except subprocess.TimeoutExpired:
            return {
                'suite': f"{suite_name} - {test_file}",
                'passed': False,
                'error': 'Test timed out (5 minutes)',
                'duration': time.time() - start_time
            }
        except Exception as e:
            return {
                'suite': f"{suite_name} - {test_file}",
                'passed': False,
                'error': str(e),
                'duration': time.time() - start_time
            }

    def run_all_tests(self):
        """Run all test suites"""
        print("🚀 Atlas Refactored System - Master Test Runner")
        print("="*60)
        print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🎯 Running {len(self.test_suites)} test suites")
        print(f"⚠️  This may take several minutes...")
        print("="*60)

        passed_suites = 0
        total_suites = len(self.test_suites)

        for suite in self.test_suites:
            if self.run_test_suite(suite):
                passed_suites += 1
                print(f"✅ {suite['name']} PASSED")
            else:
                print(f"❌ {suite['name']} FAILED")

        self.generate_summary(passed_suites, total_suites)

    def generate_summary(self, passed_suites, total_suites):
        """Generate comprehensive test summary"""
        print(f"\n{'='*60}")
        print("📊 Master Test Runner Summary")
        print(f"{'='*60}")
        print(f"📅 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️ Total Duration: {time.time() - self.start_time:.2f}s")
        print(f"{'='*60}")

        print(f"\n📈 Overall Results:")
        print(f"   Test Suites: {total_suites}")
        print(f"   Passed: {passed_suites}")
        print(f"   Failed: {total_suites - passed_suites}")
        print(f"   Success Rate: {passed_suites/total_suites*100:.1f}%")

        print(f"\n🧪 Detailed Results:")
        for result in self.results:
            status = "✅" if result['passed'] else "❌"
            duration = result.get('duration', 0)
            print(f"   {status} {result['suite']} ({duration:.2f}s)")

            if not result['passed']:
                error = result.get('error', result.get('stderr', 'Unknown error')[:100])
                print(f"      Error: {error}")

        # Count total tests
        total_tests = sum(r.get('test_count', 0) for r in self.results)
        total_passed = sum(r.get('passed_count', 0) for r in self.results)

        if total_tests > 0:
            print(f"\n📋 Individual Test Results:")
            print(f"   Total Tests: {total_tests}")
            print(f"   Passed: {total_passed}")
            print(f"   Failed: {total_tests - total_passed}")
            print(f"   Success Rate: {total_passed/total_tests*100:.1f}%")

        print(f"\n🎯 System Status:")
        if passed_suites == total_suites:
            print("   ✅ ALL TESTS PASSED")
            print("   ✅ System is production-ready")
            print("   ✅ All components working correctly")
            print("   ✅ Performance and stability verified")
        else:
            print("   ⚠️  SOME TESTS FAILED")
            print("   ⚠️  Review failed tests above")
            print("   ⚠️  System may need attention")

        print(f"\n📊 Performance Summary:")
        durations = [r.get('duration', 0) for r in self.results]
        if durations:
            avg_duration = sum(durations) / len(durations)
            max_duration = max(durations)
            min_duration = min(durations)
            print(f"   Average test duration: {avg_duration:.2f}s")
            print(f"   Longest test: {max_duration:.2f}s")
            print(f"   Shortest test: {min_duration:.2f}s")

        print(f"\n🚀 Next Steps:")
        if passed_suites == total_suites:
            print("   • System is ready for production use")
            print("   • Start web interface: python3 start_web.py")
            print("   • Access dashboard: http://localhost:8000")
            print("   • Begin processing real content")
        else:
            print("   • Investigate and fix failed tests")
            print("   • Re-run failed test suites")
            print("   • Ensure all components are working")

    def check_prerequisites(self):
        """Check if all prerequisites are met"""
        print("🔍 Checking prerequisites...")
        issues = []

        # Check if test files exist
        for suite in self.test_suites:
            if 'files' in suite:
                for test_file in suite['files']:
                    if not Path(test_file).exists():
                        issues.append(f"Missing test file: {test_file}")
            else:
                if not Path(suite['file']).exists():
                    issues.append(f"Missing test file: {suite['file']}")

        # Check if core modules exist
        core_modules = [
            'core/database.py',
            'core/processor.py',
            'core/config.py',
            'api.py',
            'web_interface.py'
        ]

        for module in core_modules:
            if not Path(module).exists():
                issues.append(f"Missing core module: {module}")

        if issues:
            print("❌ Prerequisites issues found:")
            for issue in issues:
                print(f"   - {issue}")
            return False
        else:
            print("✅ All prerequisites met")
            return True


def main():
    """Main test runner"""
    runner = TestRunner()

    # Check prerequisites
    if not runner.check_prerequisites():
        print("\n❌ Please resolve prerequisites before running tests")
        sys.exit(1)

    # Ask for confirmation for stress tests
    print("\n⚠️  Warning:")
    print("   - Stress load tests will create large amounts of test data")
    print("   - API tests require the server to be running")
    print("   - This may take several minutes to complete")
    print("\n" + "="*60)

    try:
        response = input("Continue with all tests? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print("🛑 Test execution cancelled")
            sys.exit(0)
    except KeyboardInterrupt:
        print("\n🛑 Test execution cancelled")
        sys.exit(0)

    # Run all tests
    runner.run_all_tests()


if __name__ == "__main__":
    main()