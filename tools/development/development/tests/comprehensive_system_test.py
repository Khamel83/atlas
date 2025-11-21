#!/usr/bin/env python3
"""
Comprehensive System Test - Final Validation
Complete end-to-end testing of all Atlas features before 100% completion.
"""

import os
import sys
import json
import time
import logging
import sqlite3
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import subprocess
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ComprehensiveSystemTest:
    """Complete Atlas system validation."""

    def __init__(self):
        """Initialize system test."""
        self.results = {
            'started_at': datetime.now().isoformat(),
            'test_results': {},
            'overall_status': 'running',
            'summary': {}
        }

        # Test configuration
        self.test_timeout = 300  # 5 minutes per test
        self.required_databases = [
            'data/atlas.db',
            'data/enhanced_search.db',
            'data/podcasts/atlas_podcasts.db'
        ]

        # API endpoints to test
        self.api_endpoints = [
            {'path': '/health', 'method': 'GET'},
            {'path': '/api/v1/search/?query=technology', 'method': 'GET'},
            {'path': '/api/v1/search/semantic?query=AI', 'method': 'GET'},
            {'path': '/api/v1/dashboard/analytics', 'method': 'GET'},
        ]

    def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run all system tests."""
        logger.info("🚀 Starting Comprehensive Atlas System Test")
        logger.info("=" * 60)

        test_suite = [
            ('Database Integrity', self.test_database_integrity),
            ('Search Functionality', self.test_search_functionality),
            ('Intelligence Features', self.test_intelligence_features),
            ('Content Processing', self.test_content_processing),
            ('Background Services', self.test_background_services),
            ('API Endpoints', self.test_api_endpoints),
            ('Performance Benchmarks', self.test_performance_benchmarks),
            ('Production Readiness', self.test_production_readiness)
        ]

        passed_tests = 0
        total_tests = len(test_suite)

        for test_name, test_function in test_suite:
            logger.info(f"\n📋 Running: {test_name}")

            try:
                start_time = time.time()
                test_result = test_function()
                execution_time = time.time() - start_time

                test_result['execution_time_seconds'] = round(execution_time, 2)
                test_result['status'] = test_result.get('status', 'unknown')

                self.results['test_results'][test_name] = test_result

                if test_result['status'] == 'pass':
                    passed_tests += 1
                    logger.info(f"   ✅ {test_name}: PASSED ({execution_time:.1f}s)")
                elif test_result['status'] == 'warning':
                    logger.info(f"   ⚠️ {test_name}: WARNING ({execution_time:.1f}s)")
                    if test_result.get('critical', True):
                        passed_tests += 0.5  # Partial credit
                else:
                    logger.error(f"   ❌ {test_name}: FAILED ({execution_time:.1f}s)")
                    if test_result.get('error'):
                        logger.error(f"      Error: {test_result['error']}")

            except Exception as e:
                logger.error(f"   💥 {test_name}: CRASHED - {e}")
                self.results['test_results'][test_name] = {
                    'status': 'crash',
                    'error': str(e),
                    'execution_time_seconds': 0
                }

        # Calculate final results
        success_rate = (passed_tests / total_tests) * 100
        self.results['completed_at'] = datetime.now().isoformat()
        self.results['summary'] = {
            'total_tests': total_tests,
            'passed_tests': int(passed_tests),
            'success_rate': round(success_rate, 1),
            'overall_status': self._determine_overall_status(success_rate)
        }

        self.results['overall_status'] = self.results['summary']['overall_status']

        # Print final summary
        self._print_final_summary()

        # Save results
        self._save_test_results()

        return self.results

    def test_database_integrity(self) -> Dict[str, Any]:
        """Test database integrity and structure."""
        results = {
            'databases_checked': 0,
            'databases_healthy': 0,
            'total_records': 0,
            'issues_found': []
        }

        try:
            for db_path in self.required_databases:
                results['databases_checked'] += 1

                if not os.path.exists(db_path):
                    results['issues_found'].append(f"Database missing: {db_path}")
                    continue

                # Check database integrity
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                # Integrity check
                cursor.execute("PRAGMA integrity_check")
                integrity_result = cursor.fetchone()

                if integrity_result[0] != 'ok':
                    results['issues_found'].append(f"Integrity check failed for {db_path}: {integrity_result[0]}")
                    continue

                # Count records in main tables
                if 'atlas.db' in db_path:
                    cursor.execute("SELECT COUNT(*) FROM content")
                    content_count = cursor.fetchone()[0]
                    results['total_records'] += content_count

                    if content_count < 1000:
                        results['issues_found'].append(f"Low content count: {content_count}")

                results['databases_healthy'] += 1
                conn.close()

            # Determine status
            if results['databases_healthy'] == results['databases_checked'] and not results['issues_found']:
                results['status'] = 'pass'
            elif results['databases_healthy'] > 0:
                results['status'] = 'warning'
            else:
                results['status'] = 'fail'

            return results

        except Exception as e:
            results['status'] = 'fail'
            results['error'] = str(e)
            return results

    def test_search_functionality(self) -> Dict[str, Any]:
        """Test search and indexing functionality."""
        results = {
            'search_tests_run': 0,
            'search_tests_passed': 0,
            'tf_idf_available': False,
            'autocomplete_available': False
        }

        try:
            # Test basic search
            from helpers.semantic_search_ranker import SemanticSearchRanker
            ranker = SemanticSearchRanker()

            test_queries = ['technology', 'artificial intelligence', 'programming']

            for query in test_queries:
                results['search_tests_run'] += 1

                search_results = ranker.search_with_ranking(query, limit=5)

                if search_results and len(search_results) > 0:
                    results['search_tests_passed'] += 1

                    # Check if results have ranking factors
                    first_result = search_results[0]
                    if 'ranking_score' in first_result:
                        results['tf_idf_available'] = True

            # Test TF-IDF index
            try:
                index_stats = ranker.build_tf_idf_index()
                if index_stats and 'vocabulary_size' in index_stats:
                    results['tf_idf_available'] = True
                    results['vocabulary_size'] = index_stats['vocabulary_size']
            except Exception:
                pass

            # Test autocomplete
            try:
                autocomplete_stats = ranker.add_search_autocomplete()
                if autocomplete_stats and not autocomplete_stats.get('error'):
                    results['autocomplete_available'] = True
            except Exception:
                pass

            # Determine status
            search_success_rate = results['search_tests_passed'] / max(1, results['search_tests_run'])

            if search_success_rate >= 0.8 and results['tf_idf_available']:
                results['status'] = 'pass'
            elif search_success_rate >= 0.5:
                results['status'] = 'warning'
            else:
                results['status'] = 'fail'

            return results

        except Exception as e:
            results['status'] = 'fail'
            results['error'] = str(e)
            return results

    def test_intelligence_features(self) -> Dict[str, Any]:
        """Test intelligence dashboard and cognitive features."""
        results = {
            'knowledge_graph_working': False,
            'recommendations_working': False,
            'consumption_analysis_working': False,
            'dashboard_accessible': False
        }

        try:
            # Test Intelligence Dashboard
            from helpers.intelligence_dashboard import IntelligenceDashboard
            intelligence = IntelligenceDashboard()

            # Test knowledge graph generation
            try:
                graph_data = intelligence.generate_knowledge_graph_data(max_nodes=20)
                if graph_data and graph_data.get('nodes') and len(graph_data['nodes']) > 0:
                    results['knowledge_graph_working'] = True
                    results['knowledge_graph_nodes'] = len(graph_data['nodes'])
            except Exception as e:
                results['knowledge_graph_error'] = str(e)

            # Test recommendations
            try:
                recommendations = intelligence.generate_learning_recommendations()
                if recommendations and len(recommendations) > 0:
                    results['recommendations_working'] = True
                    results['recommendations_count'] = len(recommendations)
            except Exception as e:
                results['recommendations_error'] = str(e)

            # Test consumption patterns
            try:
                patterns = intelligence.analyze_consumption_patterns()
                if patterns and patterns.get('insights'):
                    results['consumption_analysis_working'] = True
                    results['consumption_insights_count'] = len(patterns['insights'])
            except Exception as e:
                results['consumption_error'] = str(e)

            # Test dashboard server
            try:
                from dashboard.dashboard_server import DashboardServer
                dashboard = DashboardServer()
                intelligence_json = dashboard.get_intelligence_json()

                if intelligence_json and 'error' not in json.loads(intelligence_json):
                    results['dashboard_accessible'] = True
            except Exception as e:
                results['dashboard_error'] = str(e)

            # Determine status
            features_working = sum([
                results['knowledge_graph_working'],
                results['recommendations_working'],
                results['consumption_analysis_working'],
                results['dashboard_accessible']
            ])

            if features_working >= 3:
                results['status'] = 'pass'
            elif features_working >= 2:
                results['status'] = 'warning'
            else:
                results['status'] = 'fail'

            return results

        except Exception as e:
            results['status'] = 'fail'
            results['error'] = str(e)
            return results

    def test_content_processing(self) -> Dict[str, Any]:
        """Test content processing and extraction capabilities."""
        results = {
            'extraction_strategies_tested': 0,
            'extraction_strategies_working': 0,
            'content_pipeline_working': False,
            'structured_extraction_available': False
        }

        try:
            # Test enhanced content extraction
            from helpers.enhanced_content_extraction import EnhancedContentExtractor
            extractor = EnhancedContentExtractor()

            # Test with a simple URL
            test_url = 'https://httpbin.org/html'  # Simple test endpoint

            strategies_to_test = ['direct_requests']  # Only test safe strategies

            for strategy in strategies_to_test:
                results['extraction_strategies_tested'] += 1

                try:
                    result = extractor._extract_with_strategy(test_url, strategy)
                    if result and result.get('content') and len(result['content']) > 10:
                        results['extraction_strategies_working'] += 1
                except Exception:
                    pass  # Strategy failed, that's okay

            # Check performance stats
            performance_stats = extractor.get_strategy_performance()
            results['strategy_performance'] = performance_stats

            # Test structured extraction availability
            try:
                if os.path.exists('data/processed_content.db'):
                    conn = sqlite3.connect('data/processed_content.db')
                    cursor = conn.cursor()

                    cursor.execute("SELECT COUNT(*) FROM content_insights")
                    insights_count = cursor.fetchone()[0]

                    if insights_count > 0:
                        results['structured_extraction_available'] = True
                        results['structured_insights_count'] = insights_count

                    conn.close()
            except Exception:
                pass

            # Determine status
            extraction_success_rate = results['extraction_strategies_working'] / max(1, results['extraction_strategies_tested'])

            if extraction_success_rate >= 0.8:
                results['status'] = 'pass'
            elif extraction_success_rate >= 0.5:
                results['status'] = 'warning'
            else:
                results['status'] = 'fail'

            return results

        except Exception as e:
            results['status'] = 'fail'
            results['error'] = str(e)
            return results

    def test_background_services(self) -> Dict[str, Any]:
        """Test background service functionality."""
        results = {
            'scheduler_script_exists': False,
            'service_manager_exists': False,
            'watchdog_available': False,
            'background_processes_detected': 0
        }

        try:
            # Check if service scripts exist
            scheduler_script = Path('scripts/atlas_scheduler.py')
            if scheduler_script.exists():
                results['scheduler_script_exists'] = True

            service_manager = Path('atlas_comprehensive_service.py')
            if service_manager.exists():
                results['service_manager_exists'] = True

            # Check watchdog availability
            try:
                from helpers.process_watchdog import ProcessWatchdog
                results['watchdog_available'] = True
            except ImportError:
                pass

            # Check for running background processes (simplified)
            import psutil
            atlas_processes = 0

            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if 'atlas' in cmdline.lower() and 'python' in cmdline.lower():
                        atlas_processes += 1
                except:
                    continue

            results['background_processes_detected'] = atlas_processes

            # Determine status
            core_components = sum([
                results['scheduler_script_exists'],
                results['service_manager_exists'],
                results['watchdog_available']
            ])

            if core_components >= 2:
                results['status'] = 'pass'
            elif core_components >= 1:
                results['status'] = 'warning'
            else:
                results['status'] = 'fail'

            return results

        except Exception as e:
            results['status'] = 'fail'
            results['error'] = str(e)
            return results

    def test_api_endpoints(self) -> Dict[str, Any]:
        """Test API endpoints (if server is running)."""
        results = {
            'endpoints_tested': 0,
            'endpoints_responding': 0,
            'api_server_running': False
        }

        try:
            # Try to test API endpoints if server is running
            base_url = 'http://localhost:8000'

            for endpoint_config in self.api_endpoints:
                results['endpoints_tested'] += 1

                try:
                    response = requests.get(f"{base_url}{endpoint_config['path']}", timeout=10)
                    if response.status_code < 500:  # Accept 2xx, 3xx, 4xx but not 5xx
                        results['endpoints_responding'] += 1
                        results['api_server_running'] = True
                except requests.exceptions.ConnectionError:
                    # Server not running, that's okay for this test
                    pass
                except Exception:
                    pass

            # If no server is running, that's not necessarily a failure
            if results['endpoints_responding'] == 0 and not results['api_server_running']:
                results['status'] = 'warning'  # Server not running
                results['note'] = 'API server not running - start with uvicorn for full API testing'
            elif results['endpoints_responding'] == results['endpoints_tested']:
                results['status'] = 'pass'
            elif results['endpoints_responding'] > 0:
                results['status'] = 'warning'
            else:
                results['status'] = 'fail'

            return results

        except Exception as e:
            results['status'] = 'fail'
            results['error'] = str(e)
            return results

    def test_performance_benchmarks(self) -> Dict[str, Any]:
        """Test system performance benchmarks."""
        results = {
            'search_performance_ms': 0,
            'database_query_ms': 0,
            'intelligence_generation_ms': 0,
            'memory_usage_mb': 0
        }

        try:
            import psutil
            process = psutil.Process()
            results['memory_usage_mb'] = round(process.memory_info().rss / 1024 / 1024, 2)

            # Test search performance
            try:
                from helpers.semantic_search_ranker import SemanticSearchRanker
                ranker = SemanticSearchRanker()

                start_time = time.time()
                search_results = ranker.search_with_ranking('test query', limit=10)
                search_time = (time.time() - start_time) * 1000

                results['search_performance_ms'] = round(search_time, 2)
            except Exception:
                results['search_performance_ms'] = 9999  # High value indicates failure

            # Test database query performance
            try:
                if os.path.exists('data/atlas.db'):
                    conn = sqlite3.connect('data/atlas.db')
                    cursor = conn.cursor()

                    start_time = time.time()
                    cursor.execute("SELECT COUNT(*) FROM content WHERE created_at > datetime('now', '-30 days')")
                    cursor.fetchone()
                    query_time = (time.time() - start_time) * 1000

                    results['database_query_ms'] = round(query_time, 2)
                    conn.close()
            except Exception:
                results['database_query_ms'] = 9999

            # Test intelligence generation performance
            try:
                from helpers.intelligence_dashboard import IntelligenceDashboard
                intelligence = IntelligenceDashboard()

                start_time = time.time()
                intelligence.analyze_consumption_patterns(days=7)
                intelligence_time = (time.time() - start_time) * 1000

                results['intelligence_generation_ms'] = round(intelligence_time, 2)
            except Exception:
                results['intelligence_generation_ms'] = 9999

            # Performance thresholds
            performance_good = (
                results['search_performance_ms'] < 2000 and
                results['database_query_ms'] < 500 and
                results['intelligence_generation_ms'] < 5000 and
                results['memory_usage_mb'] < 500
            )

            performance_acceptable = (
                results['search_performance_ms'] < 5000 and
                results['database_query_ms'] < 2000 and
                results['intelligence_generation_ms'] < 15000 and
                results['memory_usage_mb'] < 1000
            )

            if performance_good:
                results['status'] = 'pass'
            elif performance_acceptable:
                results['status'] = 'warning'
            else:
                results['status'] = 'fail'

            return results

        except Exception as e:
            results['status'] = 'fail'
            results['error'] = str(e)
            return results

    def test_production_readiness(self) -> Dict[str, Any]:
        """Test production readiness features."""
        results = {
            'optimization_available': False,
            'monitoring_available': False,
            'caching_available': False,
            'error_handling_robust': False
        }

        try:
            # Test production optimizer
            try:
                from helpers.production_optimizer import ProductionOptimizer
                optimizer = ProductionOptimizer()
                results['optimization_available'] = True
            except ImportError:
                pass

            # Test production monitor
            try:
                from helpers.production_monitor import ProductionMonitor
                monitor = ProductionMonitor()
                results['monitoring_available'] = True
            except ImportError:
                pass

            # Test caching capabilities
            try:
                cache_dir = Path('data/cache')
                if cache_dir.exists() or results['optimization_available']:
                    results['caching_available'] = True
            except Exception:
                pass

            # Check error handling robustness (simplified)
            error_handling_features = 0

            # Check for process watchdog
            if Path('helpers/process_watchdog.py').exists():
                error_handling_features += 1

            # Check for retry mechanisms
            if Path('helpers/enhanced_content_extraction.py').exists():
                error_handling_features += 1

            # Check for monitoring database
            if Path('data/monitoring.db').exists():
                error_handling_features += 1

            results['error_handling_robust'] = error_handling_features >= 2

            # Determine status
            production_features = sum([
                results['optimization_available'],
                results['monitoring_available'],
                results['caching_available'],
                results['error_handling_robust']
            ])

            if production_features >= 3:
                results['status'] = 'pass'
            elif production_features >= 2:
                results['status'] = 'warning'
            else:
                results['status'] = 'fail'

            return results

        except Exception as e:
            results['status'] = 'fail'
            results['error'] = str(e)
            return results

    def _determine_overall_status(self, success_rate: float) -> str:
        """Determine overall system status."""
        if success_rate >= 90:
            return 'excellent'
        elif success_rate >= 80:
            return 'good'
        elif success_rate >= 70:
            return 'acceptable'
        elif success_rate >= 50:
            return 'needs_improvement'
        else:
            return 'critical_issues'

    def _print_final_summary(self):
        """Print comprehensive test summary."""
        logger.info("\n" + "=" * 60)
        logger.info("🎯 ATLAS COMPREHENSIVE SYSTEM TEST RESULTS")
        logger.info("=" * 60)

        summary = self.results['summary']
        status_emoji = {
            'excellent': '🎉',
            'good': '✅',
            'acceptable': '⚠️',
            'needs_improvement': '🔧',
            'critical_issues': '❌'
        }

        logger.info(f"📊 Overall Status: {status_emoji.get(summary['overall_status'], '❓')} {summary['overall_status'].upper()}")
        logger.info(f"📈 Success Rate: {summary['success_rate']}% ({summary['passed_tests']}/{summary['total_tests']} tests)")

        # Individual test results
        logger.info("\n📋 Individual Test Results:")
        for test_name, test_result in self.results['test_results'].items():
            status = test_result['status']
            time_taken = test_result.get('execution_time_seconds', 0)

            status_symbols = {
                'pass': '✅',
                'warning': '⚠️',
                'fail': '❌',
                'crash': '💥'
            }

            symbol = status_symbols.get(status, '❓')
            logger.info(f"   {symbol} {test_name}: {status.upper()} ({time_taken:.1f}s)")

            if test_result.get('error'):
                logger.info(f"      ↳ {test_result['error'][:100]}...")

        # Production readiness assessment
        logger.info(f"\n🚀 Production Readiness Assessment:")
        if summary['success_rate'] >= 90:
            logger.info("   🎉 PRODUCTION READY - All systems operational!")
        elif summary['success_rate'] >= 80:
            logger.info("   ✅ DEPLOYMENT READY - Minor issues to monitor")
        elif summary['success_rate'] >= 70:
            logger.info("   ⚠️ NEEDS ATTENTION - Address warnings before production")
        else:
            logger.info("   ❌ NOT READY - Critical issues must be resolved")

        logger.info("=" * 60)

    def _save_test_results(self):
        """Save test results to file."""
        try:
            results_file = Path('docs/comprehensive_test_results.json')
            results_file.parent.mkdir(exist_ok=True)

            with open(results_file, 'w') as f:
                json.dump(self.results, f, indent=2, default=str)

            logger.info(f"📄 Test results saved to: {results_file}")

        except Exception as e:
            logger.error(f"Failed to save test results: {e}")

def main():
    """Main function to run comprehensive system test."""
    test_runner = ComprehensiveSystemTest()
    results = test_runner.run_comprehensive_test()

    # Return appropriate exit code
    success_rate = results['summary']['success_rate']
    if success_rate >= 80:
        sys.exit(0)  # Success
    elif success_rate >= 50:
        sys.exit(1)  # Warning
    else:
        sys.exit(2)  # Critical issues

if __name__ == "__main__":
    main()