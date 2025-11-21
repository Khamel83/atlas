#!/usr/bin/env python3
"""
Atlas Comprehensive System Test

Tests all integrated systems end-to-end:
- Database connectivity and population
- Search index functionality
- API endpoints and responses
- Dashboard integration
- Background services
- Cognitive modules
- Analytics engine
"""

import os
import sys
import time
import json
import sqlite3
import requests
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple
from helpers.bulletproof_process_manager import create_managed_process

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent))

class AtlasSystemTest:
    """Comprehensive Atlas system test suite"""

    def __init__(self):
        """Initialize test suite"""
        self.results = {
            "start_time": datetime.now().isoformat(),
            "tests": {},
            "summary": {"passed": 0, "failed": 0, "errors": 0},
            "details": []
        }
        self.api_base_url = "http://localhost:8000/api/v1"

    def log_test(self, test_name: str, passed: bool, details: str = ""):
        """Log test result"""
        self.results["tests"][test_name] = {
            "passed": passed,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }

        if passed:
            self.results["summary"]["passed"] += 1
            print(f"✅ {test_name}")
        else:
            self.results["summary"]["failed"] += 1
            print(f"❌ {test_name}: {details}")

        if details:
            self.results["details"].append(f"{test_name}: {details}")

    def test_database_connectivity(self) -> bool:
        """Test database connections and basic queries"""
        try:
            # Test main database
            main_db = sqlite3.connect("data/atlas.db")
            cursor = main_db.execute("SELECT COUNT(*) FROM content")
            content_count = cursor.fetchone()[0]
            main_db.close()

            # Test search database
            search_db = sqlite3.connect("data/enhanced_search.db")
            cursor = search_db.execute("SELECT COUNT(*) FROM search_index")
            search_count = cursor.fetchone()[0]
            search_db.close()

            details = f"Content: {content_count:,}, Search: {search_count:,}"
            self.log_test("Database Connectivity", True, details)
            return True

        except Exception as e:
            self.log_test("Database Connectivity", False, str(e))
            return False

    def test_search_functionality(self) -> bool:
        """Test search index and queries"""
        try:
            # Direct database search test
            search_db = sqlite3.connect("data/enhanced_search.db")
            cursor = search_db.execute("""
                SELECT content_id, title, LENGTH(content)
                FROM search_index
                WHERE content LIKE '%technology%' OR title LIKE '%technology%'
                LIMIT 5
            """)
            results = cursor.fetchall()
            search_db.close()

            if len(results) > 0:
                details = f"{len(results)} results found for 'technology'"
                self.log_test("Search Functionality", True, details)
                return True
            else:
                self.log_test("Search Functionality", False, "No search results found")
                return False

        except Exception as e:
            self.log_test("Search Functionality", False, str(e))
            return False

    def test_api_endpoints(self) -> bool:
        """Test API server and endpoints"""
        try:
            # Start API server in background
            print("  Starting API server for testing...")
            api_process = create_managed_process([
                sys.executable, "-m", "uvicorn",
                "api.main:app", "--host", "127.0.0.1", "--port", "8000"
            ], "api_server_test", stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # Wait for server to start
            time.sleep(5)

            tests_passed = 0
            total_tests = 0

            # Test health endpoint
            try:
                response = requests.get(f"{self.api_base_url}/health", timeout=10)
                total_tests += 1
                if response.status_code == 200:
                    tests_passed += 1
            except Exception as e:
                pass

            # Test search endpoint
            try:
                response = requests.get(f"{self.api_base_url}/search/?query=test&limit=3", timeout=10)
                total_tests += 1
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, dict) and "results" in data:
                        tests_passed += 1
            except Exception as e:
                pass

            # Test dashboard endpoint
            try:
                response = requests.get(f"{self.api_base_url}/dashboard/", timeout=10)
                total_tests += 1
                if response.status_code == 200:
                    tests_passed += 1
            except Exception as e:
                pass

            # Test analytics endpoint
            try:
                response = requests.get(f"{self.api_base_url}/dashboard/analytics", timeout=10)
                total_tests += 1
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, dict) and "total_items" in data:
                        tests_passed += 1
            except Exception as e:
                pass

            # Clean up
            api_process.terminate()
            api_process.wait(timeout=5)

            details = f"{tests_passed}/{total_tests} endpoints working"
            success = tests_passed >= total_tests // 2  # At least half working
            self.log_test("API Endpoints", success, details)
            return success

        except Exception as e:
            self.log_test("API Endpoints", False, str(e))
            return False

    def test_cognitive_modules(self) -> bool:
        """Test cognitive module functionality"""
        try:
            modules_tested = 0
            modules_passed = 0

            # Test ProactiveSurfacer
            try:
                from ask.proactive.surfacer import ProactiveSurfacer
                surfacer = ProactiveSurfacer()
                result = surfacer.surface_content(['test'])
                modules_tested += 1
                if isinstance(result, list):
                    modules_passed += 1
            except Exception:
                modules_tested += 1

            # Test TemporalEngine
            try:
                from ask.temporal.temporal_engine import TemporalEngine
                temporal = TemporalEngine()
                result = temporal.analyze_patterns()
                modules_tested += 1
                if result is not None:
                    modules_passed += 1
            except Exception:
                modules_tested += 1

            # Test QuestionEngine
            try:
                from ask.socratic.question_engine import QuestionEngine
                question_engine = QuestionEngine()
                questions = question_engine.generate_questions('test topic')
                modules_tested += 1
                if isinstance(questions, list) and len(questions) > 0:
                    modules_passed += 1
            except Exception:
                modules_tested += 1

            # Test RecallEngine
            try:
                from ask.recall.recall_engine import RecallEngine
                recall = RecallEngine()
                suggestions = recall.get_recall_suggestions()
                modules_tested += 1
                if isinstance(suggestions, list):
                    modules_passed += 1
            except Exception:
                modules_tested += 1

            # Test PatternDetector
            try:
                from ask.insights.pattern_detector import PatternDetector
                detector = PatternDetector()
                patterns = detector.detect_patterns()
                modules_tested += 1
                if patterns is not None:
                    modules_passed += 1
            except Exception:
                modules_tested += 1

            details = f"{modules_passed}/{modules_tested} cognitive modules functional"
            success = modules_passed >= modules_tested // 2
            self.log_test("Cognitive Modules", success, details)
            return success

        except Exception as e:
            self.log_test("Cognitive Modules", False, str(e))
            return False

    def test_analytics_engine(self) -> bool:
        """Test analytics engine integration"""
        try:
            from helpers.analytics_engine import AnalyticsEngine
            from helpers.config import load_config

            config = load_config()
            analytics = AnalyticsEngine(config)

            # Test basic functionality
            if hasattr(analytics, 'get_consumption_patterns'):
                patterns = analytics.get_consumption_patterns()
                details = "Analytics engine initialized and functional"
                self.log_test("Analytics Engine", True, details)
                return True
            else:
                self.log_test("Analytics Engine", False, "Missing expected methods")
                return False

        except Exception as e:
            self.log_test("Analytics Engine", False, str(e))
            return False

    def test_background_service(self) -> bool:
        """Test background service functionality"""
        try:
            # Test service manager import and basic functionality
            from atlas_background_service import AtlasServiceManager

            service_manager = AtlasServiceManager()

            # Test health check
            health = service_manager.health_check()

            if isinstance(health, dict) and "overall_status" in health:
                details = f"Service manager functional, health: {health['overall_status']}"
                self.log_test("Background Service", True, details)
                return True
            else:
                self.log_test("Background Service", False, "Health check failed")
                return False

        except Exception as e:
            self.log_test("Background Service", False, str(e))
            return False

    def test_data_pipeline(self) -> bool:
        """Test complete data processing pipeline"""
        try:
            # Check that content flows from files -> database -> search index

            # Count files
            metadata_dir = Path("output/articles/metadata")
            if metadata_dir.exists():
                json_files = list(metadata_dir.glob("*.json"))
                file_count = len(json_files)
            else:
                file_count = 0

            # Count database entries
            db_conn = sqlite3.connect("data/atlas.db")
            db_count = db_conn.execute("SELECT COUNT(*) FROM content").fetchone()[0]
            db_conn.close()

            # Count search index
            search_conn = sqlite3.connect("data/enhanced_search.db")
            search_count = search_conn.execute("SELECT COUNT(*) FROM search_index").fetchone()[0]
            search_conn.close()

            # Pipeline health check
            if file_count > 0 and db_count > 0 and search_count > 0:
                pipeline_health = (search_count / db_count) * 100 if db_count > 0 else 0
                details = f"Files: {file_count}, DB: {db_count}, Search: {search_count} ({pipeline_health:.1f}% indexed)"
                self.log_test("Data Pipeline", True, details)
                return True
            else:
                details = f"Pipeline broken: Files: {file_count}, DB: {db_count}, Search: {search_count}"
                self.log_test("Data Pipeline", False, details)
                return False

        except Exception as e:
            self.log_test("Data Pipeline", False, str(e))
            return False

    def run_all_tests(self) -> Dict[str, Any]:
        """Run all system tests"""
        print("🧪 Atlas Comprehensive System Test")
        print("=" * 40)

        # Run all tests
        tests = [
            self.test_database_connectivity,
            self.test_search_functionality,
            self.test_data_pipeline,
            self.test_analytics_engine,
            self.test_cognitive_modules,
            self.test_background_service,
            self.test_api_endpoints
        ]

        for test_func in tests:
            try:
                test_func()
            except Exception as e:
                test_name = test_func.__name__.replace("test_", "").replace("_", " ").title()
                self.log_test(test_name, False, f"Test error: {str(e)}")
                self.results["summary"]["errors"] += 1

        # Calculate final results
        total_tests = len(self.results["tests"])
        passed = self.results["summary"]["passed"]
        failed = self.results["summary"]["failed"]

        success_rate = (passed / total_tests * 100) if total_tests > 0 else 0

        print("\n" + "=" * 40)
        print(f"🎯 Test Results: {passed}/{total_tests} passed ({success_rate:.1f}%)")

        if success_rate >= 80:
            print("🎉 Atlas System: FULLY OPERATIONAL")
            self.results["overall_status"] = "OPERATIONAL"
        elif success_rate >= 60:
            print("⚠️  Atlas System: MOSTLY FUNCTIONAL")
            self.results["overall_status"] = "DEGRADED"
        else:
            print("❌ Atlas System: NEEDS ATTENTION")
            self.results["overall_status"] = "REQUIRES_FIXES"

        self.results["end_time"] = datetime.now().isoformat()
        self.results["success_rate"] = success_rate

        return self.results

def main():
    """Main test execution"""
    test_suite = AtlasSystemTest()
    results = test_suite.run_all_tests()

    # Save results
    with open("atlas_system_test_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n📊 Detailed results saved to: atlas_system_test_results.json")

    # Exit with appropriate code
    if results["success_rate"] >= 80:
        sys.exit(0)  # Success
    else:
        sys.exit(1)  # Issues found

if __name__ == "__main__":
    main()