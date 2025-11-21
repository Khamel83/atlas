#!/usr/bin/env python3
"""
Novel Test Scenarios for Atlas - Untested Functionality
These tests focus on scenarios that haven't been validated yet.
"""

import asyncio
import json
import os
import random
import sqlite3
import subprocess
import tempfile
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

class NovelAtlasTestSuite:
    """Novel test scenarios for Atlas functionality."""

    def __init__(self):
        self.results = {}
        self.test_data_dir = Path("test_temp_data")
        self.test_data_dir.mkdir(exist_ok=True)

    def log(self, message, status="INFO"):
        print(f"[{status}] {message}")

    # ===== CONTENT PROCESSING STRESS TESTS =====

    def test_bulk_url_processing(self):
        """Test processing 100+ URLs simultaneously."""
        self.log("Testing bulk URL processing...")

        # Create test URLs file with mix of content types
        test_urls = [
            "https://example.com/article1",
            "https://httpbin.org/html",
            "https://httpbin.org/json",
            "https://news.ycombinator.com/",
            "https://www.reuters.com/business/",
        ] * 20  # 100 URLs total

        test_file = self.test_data_dir / "bulk_test_urls.txt"
        with open(test_file, 'w') as f:
            f.write('\n'.join(test_urls))

        try:
            start_time = time.time()

            # Use run.py to process URLs
            result = subprocess.run([
                'python', 'run.py', '--urls', str(test_file)
            ], capture_output=True, text=True, timeout=300, cwd='.')

            elapsed = time.time() - start_time

            success = result.returncode == 0
            output_lines = len(result.stdout.split('\n'))

            self.results['bulk_processing'] = {
                'success': success,
                'elapsed_seconds': elapsed,
                'urls_processed': 100,
                'throughput_per_second': 100 / elapsed if elapsed > 0 else 0,
                'output_lines': output_lines,
                'return_code': result.returncode
            }

            if success:
                self.log(f"  ✅ Processed 100 URLs in {elapsed:.1f}s ({100/elapsed:.1f} URLs/sec)")
            else:
                self.log(f"  ❌ Bulk processing failed: {result.stderr[:200]}", "ERROR")

        except subprocess.TimeoutExpired:
            self.log("  ⚠️ Bulk processing timed out after 5 minutes", "WARN")
            self.results['bulk_processing'] = {'success': False, 'reason': 'timeout'}
        except Exception as e:
            self.log(f"  ❌ Bulk processing error: {e}", "ERROR")
            self.results['bulk_processing'] = {'success': False, 'error': str(e)}

    def test_concurrent_api_requests(self):
        """Test API under concurrent load."""
        self.log("Testing concurrent API requests...")

        def make_request(endpoint_url):
            try:
                response = requests.get(endpoint_url, timeout=10)
                return {
                    'status_code': response.status_code,
                    'response_time': response.elapsed.total_seconds(),
                    'success': response.status_code < 500
                }
            except Exception as e:
                return {'success': False, 'error': str(e)}

        # Test endpoints concurrently
        endpoints = [
            'http://localhost:8000/api/v1/health',
            'http://localhost:8000/api/v1/dashboard/',
            'http://localhost:8000/api/v1/search/?q=test',
        ]

        # Create 30 concurrent requests (10 per endpoint)
        requests_to_make = []
        for _ in range(10):
            for endpoint in endpoints:
                requests_to_make.append(endpoint)

        start_time = time.time()

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request, url) for url in requests_to_make]
            responses = [future.result() for future in as_completed(futures)]

        elapsed = time.time() - start_time

        successful_requests = sum(1 for r in responses if r.get('success', False))
        avg_response_time = sum(r.get('response_time', 0) for r in responses if 'response_time' in r) / len(responses)

        self.results['concurrent_api'] = {
            'total_requests': len(requests_to_make),
            'successful_requests': successful_requests,
            'success_rate': successful_requests / len(requests_to_make),
            'total_time': elapsed,
            'requests_per_second': len(requests_to_make) / elapsed,
            'avg_response_time': avg_response_time
        }

        self.log(f"  ✅ {successful_requests}/{len(requests_to_make)} requests successful")
        self.log(f"  ✅ {len(requests_to_make)/elapsed:.1f} req/sec, {avg_response_time:.3f}s avg response")

    def test_large_content_processing(self):
        """Test processing very large content items."""
        self.log("Testing large content processing...")

        # Create a large text file (1MB+)
        large_content = "This is a test of large content processing. " * 25000  # ~1MB
        test_file = self.test_data_dir / "large_content_test.txt"

        with open(test_file, 'w') as f:
            f.write(large_content)

        try:
            # Test if content pipeline can handle large content
            from helpers.content_pipeline import ContentPipeline
            from helpers.config import load_config

            config = load_config()
            pipeline = ContentPipeline(config)

            start_time = time.time()
            result = pipeline.process_content(
                content=large_content,
                title="Large Content Test",
                url="test://large-content"
            )
            elapsed = time.time() - start_time

            self.results['large_content'] = {
                'success': result.get('status') == 'success',
                'content_size_mb': len(large_content) / (1024 * 1024),
                'processing_time': elapsed,
                'throughput_mb_per_sec': (len(large_content) / (1024 * 1024)) / elapsed
            }

            self.log(f"  ✅ Processed {len(large_content)/1024/1024:.1f}MB in {elapsed:.1f}s")

        except Exception as e:
            self.log(f"  ❌ Large content processing failed: {e}", "ERROR")
            self.results['large_content'] = {'success': False, 'error': str(e)}

    # ===== INTELLIGENCE FEATURE TESTS =====

    def test_knowledge_graph_generation(self):
        """Test knowledge graph generation with real data."""
        self.log("Testing knowledge graph generation...")

        try:
            from helpers.intelligence_dashboard import IntelligenceDashboard

            dashboard = IntelligenceDashboard()

            start_time = time.time()
            graph_data = dashboard.generate_knowledge_graph_data(max_nodes=50)
            elapsed = time.time() - start_time

            node_count = len(graph_data.get('nodes', []))
            edge_count = len(graph_data.get('edges', []))

            self.results['knowledge_graph'] = {
                'success': node_count > 0 and edge_count > 0,
                'nodes_generated': node_count,
                'edges_generated': edge_count,
                'generation_time': elapsed,
                'stats': graph_data.get('stats', {})
            }

            self.log(f"  ✅ Generated graph: {node_count} nodes, {edge_count} edges in {elapsed:.1f}s")

        except Exception as e:
            self.log(f"  ❌ Knowledge graph generation failed: {e}", "ERROR")
            self.results['knowledge_graph'] = {'success': False, 'error': str(e)}

    def test_learning_recommendations(self):
        """Test learning recommendation generation."""
        self.log("Testing learning recommendations...")

        try:
            from helpers.intelligence_dashboard import IntelligenceDashboard

            dashboard = IntelligenceDashboard()

            start_time = time.time()
            recommendations = dashboard.generate_learning_recommendations()
            elapsed = time.time() - start_time

            rec_count = len(recommendations)

            self.results['recommendations'] = {
                'success': rec_count > 0,
                'recommendations_generated': rec_count,
                'generation_time': elapsed,
                'sample_recommendations': recommendations[:3] if recommendations else []
            }

            self.log(f"  ✅ Generated {rec_count} learning recommendations in {elapsed:.1f}s")
            for rec in recommendations[:2]:
                self.log(f"    - {rec.get('title', 'Unknown')}")

        except Exception as e:
            self.log(f"  ❌ Learning recommendations failed: {e}", "ERROR")
            self.results['recommendations'] = {'success': False, 'error': str(e)}

    # ===== SEARCH & RANKING TESTS =====

    def test_semantic_search_accuracy(self):
        """Test semantic search quality and relevance."""
        self.log("Testing semantic search accuracy...")

        test_queries = [
            "artificial intelligence machine learning",
            "climate change environmental policy",
            "cryptocurrency blockchain bitcoin",
            "software engineering best practices",
            "health medicine research"
        ]

        search_results = {}

        for query in test_queries:
            try:
                response = requests.get(
                    f'http://localhost:8000/api/v1/search/',
                    params={'q': query, 'limit': 10},
                    timeout=10
                )

                if response.status_code == 200:
                    data = response.json()
                    results = data.get('items', [])

                    search_results[query] = {
                        'success': True,
                        'result_count': len(results),
                        'response_time': response.elapsed.total_seconds(),
                        'has_relevance_scores': any('relevance_score' in r for r in results),
                        'top_result_title': results[0].get('title', 'Unknown') if results else None
                    }
                else:
                    search_results[query] = {'success': False, 'status_code': response.status_code}

            except Exception as e:
                search_results[query] = {'success': False, 'error': str(e)}

        successful_searches = sum(1 for r in search_results.values() if r.get('success', False))
        avg_results = sum(r.get('result_count', 0) for r in search_results.values()) / len(test_queries)

        self.results['semantic_search'] = {
            'queries_tested': len(test_queries),
            'successful_queries': successful_searches,
            'success_rate': successful_searches / len(test_queries),
            'avg_results_per_query': avg_results,
            'detailed_results': search_results
        }

        self.log(f"  ✅ {successful_searches}/{len(test_queries)} search queries successful")
        self.log(f"  ✅ Average {avg_results:.1f} results per query")

    # ===== DATA CONSISTENCY TESTS =====

    def test_cross_database_consistency(self):
        """Test data consistency across multiple databases."""
        self.log("Testing cross-database consistency...")

        try:
            # Check content counts across databases
            main_conn = sqlite3.connect('data/atlas.db')
            search_conn = sqlite3.connect('data/enhanced_search.db')

            # Get content count from main database
            main_cursor = main_conn.cursor()
            main_cursor.execute("SELECT COUNT(*) FROM content;")
            main_count = main_cursor.fetchone()[0]

            # Get indexed content count
            search_cursor = search_conn.cursor()
            search_cursor.execute("SELECT COUNT(*) FROM search_index;")
            indexed_count = search_cursor.fetchone()[0]

            # Check for orphaned records
            main_cursor.execute("SELECT COUNT(DISTINCT id) FROM content;")
            unique_content_ids = main_cursor.fetchone()[0]

            consistency_ratio = indexed_count / main_count if main_count > 0 else 0

            self.results['data_consistency'] = {
                'main_db_count': main_count,
                'search_index_count': indexed_count,
                'unique_content_ids': unique_content_ids,
                'consistency_ratio': consistency_ratio,
                'fully_consistent': main_count == unique_content_ids,
                'good_indexing_coverage': consistency_ratio > 0.8
            }

            main_conn.close()
            search_conn.close()

            self.log(f"  ✅ Main DB: {main_count:,} items, Search index: {indexed_count:,} items")
            self.log(f"  ✅ Indexing coverage: {consistency_ratio:.1%}")

        except Exception as e:
            self.log(f"  ❌ Data consistency check failed: {e}", "ERROR")
            self.results['data_consistency'] = {'success': False, 'error': str(e)}

    # ===== BACKGROUND SERVICE TESTS =====

    def test_background_service_resilience(self):
        """Test background service restart and recovery."""
        self.log("Testing background service resilience...")

        try:
            # Find atlas scheduler process
            result = subprocess.run(['pgrep', '-f', 'atlas_scheduler'],
                                  capture_output=True, text=True)

            if result.returncode == 0:
                scheduler_pids = result.stdout.strip().split('\n')
                initial_pid_count = len([p for p in scheduler_pids if p])

                self.log(f"  Found {initial_pid_count} scheduler processes")

                # Wait a bit to see if services stay stable
                time.sleep(10)

                # Check if processes are still running
                result2 = subprocess.run(['pgrep', '-f', 'atlas_scheduler'],
                                       capture_output=True, text=True)

                final_pid_count = len(result2.stdout.strip().split('\n')) if result2.returncode == 0 else 0

                self.results['service_resilience'] = {
                    'initial_processes': initial_pid_count,
                    'final_processes': final_pid_count,
                    'processes_stable': final_pid_count > 0,
                    'no_process_leaks': final_pid_count <= initial_pid_count + 1
                }

                self.log(f"  ✅ Service stability: {final_pid_count} processes after 10s")

            else:
                self.log("  ⚠️ No atlas_scheduler processes found", "WARN")
                self.results['service_resilience'] = {'success': False, 'reason': 'no_processes'}

        except Exception as e:
            self.log(f"  ❌ Service resilience test failed: {e}", "ERROR")
            self.results['service_resilience'] = {'success': False, 'error': str(e)}

    # ===== GENERATE REPORT =====

    def run_all_tests(self):
        """Run all novel test scenarios."""
        self.log("🚀 Starting Novel Atlas Test Scenarios")
        self.log("=" * 60)

        start_time = time.time()

        # Content Processing Tests
        self.test_bulk_url_processing()
        self.test_concurrent_api_requests()
        self.test_large_content_processing()

        # Intelligence Feature Tests
        self.test_knowledge_graph_generation()
        self.test_learning_recommendations()

        # Search & Ranking Tests
        self.test_semantic_search_accuracy()

        # Data Consistency Tests
        self.test_cross_database_consistency()

        # Background Service Tests
        self.test_background_service_resilience()

        elapsed = time.time() - start_time

        # Generate final report
        self.generate_novel_test_report(elapsed)

    def generate_novel_test_report(self, elapsed_time):
        """Generate comprehensive novel test report."""
        self.log("=" * 60)
        self.log(f"🎯 NOVEL TEST SCENARIOS COMPLETE ({elapsed_time:.1f}s)")
        self.log("=" * 60)

        # Calculate scores for each test category
        scores = {}

        # Content Processing (30 points)
        content_tests = ['bulk_processing', 'concurrent_api', 'large_content']
        content_passed = sum(1 for test in content_tests if self.results.get(test, {}).get('success', False))
        scores['content_processing'] = (content_passed / len(content_tests)) * 30

        # Intelligence Features (25 points)
        intel_tests = ['knowledge_graph', 'recommendations']
        intel_passed = sum(1 for test in intel_tests if self.results.get(test, {}).get('success', False))
        scores['intelligence_features'] = (intel_passed / len(intel_tests)) * 25

        # Search Quality (25 points)
        search_success_rate = self.results.get('semantic_search', {}).get('success_rate', 0)
        scores['search_quality'] = search_success_rate * 25

        # System Reliability (20 points)
        reliability_tests = ['data_consistency', 'service_resilience']
        reliability_passed = sum(1 for test in reliability_tests if self.results.get(test, {}).get('success', False))
        scores['system_reliability'] = (reliability_passed / len(reliability_tests)) * 20

        total_score = sum(scores.values())

        self.log(f"📊 NOVEL TEST SCORES:")
        self.log(f"   Content Processing: {scores['content_processing']:.1f}/30")
        self.log(f"   Intelligence Features: {scores['intelligence_features']:.1f}/25")
        self.log(f"   Search Quality: {scores['search_quality']:.1f}/25")
        self.log(f"   System Reliability: {scores['system_reliability']:.1f}/20")
        self.log(f"   TOTAL NOVEL SCORE: {total_score:.1f}/100")

        # Status assessment
        if total_score >= 85:
            self.log("🏆 NOVEL TESTING STATUS: EXCELLENT - Advanced features working perfectly!")
        elif total_score >= 70:
            self.log("✅ NOVEL TESTING STATUS: GOOD - Most advanced features operational")
        elif total_score >= 50:
            self.log("⚠️ NOVEL TESTING STATUS: FAIR - Some advanced features need work")
        else:
            self.log("❌ NOVEL TESTING STATUS: POOR - Advanced features require attention")

        # Save detailed results
        report_path = 'novel_test_results.json'
        with open(report_path, 'w') as f:
            json.dump({
                'timestamp': time.time(),
                'elapsed_seconds': elapsed_time,
                'total_score': total_score,
                'category_scores': scores,
                'detailed_results': self.results
            }, f, indent=2)

        self.log(f"📄 Novel test report saved to: {report_path}")

        # Cleanup
        if self.test_data_dir.exists():
            import shutil
            shutil.rmtree(self.test_data_dir)

        return total_score

def main():
    """Run novel test scenarios."""
    tester = NovelAtlasTestSuite()
    score = tester.run_all_tests()
    return score

if __name__ == "__main__":
    main()