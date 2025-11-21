#!/usr/bin/env python3
"""
Task 2.5: Content Processing Pipeline Stress Testing

Comprehensive stress testing of the Atlas content processing pipeline,
including document ingestion, article processing, and bulk operations.
"""

import os
import sys
import time
import json
import random
import threading
import concurrent.futures
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from helpers.document_ingestor import DocumentIngestor
    from helpers.article_manager import ArticleManager
    from helpers.simple_database import SimpleDatabase
    from helpers.config import load_config
except ImportError as e:
    print(f"⚠️ Import warning: {e}")
    print("Some tests may be skipped due to missing dependencies")

class ContentProcessingStressTester:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.test_data_dir = self.project_root / "test_data"
        self.test_data_dir.mkdir(exist_ok=True)

        self.results = {
            'document_processing': {},
            'article_processing': {},
            'bulk_operations': {},
            'concurrent_processing': {},
            'memory_usage': {},
            'error_handling': {}
        }

        # Load configuration
        try:
            self.config = load_config()
        except Exception as e:
            print(f"⚠️ Config load failed: {e}")
            self.config = {}

    def create_test_documents(self, count: int = 50) -> List[Path]:
        """Create test documents for stress testing"""
        print(f"📝 Creating {count} test documents...")

        test_docs = []

        # Sample content templates
        templates = [
            "This is a test article about {topic}. It contains information about {detail} and discusses {concept}. The article is {length} and provides insights into {field}.",
            "Research paper on {topic}. Abstract: This study examines {detail} in the context of {concept}. Results show significant improvements in {field}.",
            "Blog post discussing {topic}. Key points include {detail} and the impact of {concept} on modern {field}.",
            "Technical documentation for {topic}. This guide covers {detail} implementation and {concept} optimization in {field}.",
            "News article: Breaking developments in {topic}. Experts analyze {detail} and predict {concept} changes in {field}."
        ]

        topics = ['artificial intelligence', 'machine learning', 'web development', 'data science', 'cybersecurity']
        details = ['performance optimization', 'security measures', 'user experience', 'data analysis', 'system architecture']
        concepts = ['automation', 'scalability', 'efficiency', 'innovation', 'integration']
        fields = ['technology', 'healthcare', 'finance', 'education', 'research']
        lengths = ['comprehensive', 'detailed', 'concise', 'extensive', 'thorough']

        for i in range(count):
            # Random content generation
            template = random.choice(templates)
            content = template.format(
                topic=random.choice(topics),
                detail=random.choice(details),
                concept=random.choice(concepts),
                field=random.choice(fields),
                length=random.choice(lengths)
            )

            # Add more content to vary sizes
            extra_sentences = random.randint(5, 20)
            for j in range(extra_sentences):
                content += f" Additional sentence {j+1} with more detailed information about the topic."

            # Create document
            doc_path = self.test_data_dir / f"test_doc_{i:03d}.txt"
            with open(doc_path, 'w') as f:
                f.write(f"Title: Test Document {i:03d}\n")
                f.write(f"Author: Test Author {i}\n")
                f.write(f"Date: {datetime.now().isoformat()}\n\n")
                f.write(content)

            test_docs.append(doc_path)

        return test_docs

    def create_test_urls(self, count: int = 30) -> List[str]:
        """Create test URLs for article processing"""
        # Mix of valid and test URLs
        test_urls = []

        # Some real URLs for testing (HTTP status checks only)
        real_urls = [
            "https://example.com",
            "https://httpbin.org/status/200",
            "https://httpbin.org/json",
            "https://jsonplaceholder.typicode.com/posts/1",
            "https://httpbin.org/html"
        ]

        # Generate test URLs
        for i in range(count):
            if i < len(real_urls):
                test_urls.append(real_urls[i])
            else:
                # Create mock URLs for testing
                test_urls.append(f"https://test-site-{i}.example.com/article-{i}")

        return test_urls

    def test_document_processing_stress(self):
        """Test document processing under stress conditions"""
        print("\n📄 Document Processing Stress Test")
        print("=" * 50)

        try:
            # Create test documents
            test_docs = self.create_test_documents(50)

            # Initialize document ingestor
            ingestor = DocumentIngestor()

            # Test single document processing performance
            print("🔍 Single document processing...")
            single_doc_times = []

            for i, doc_path in enumerate(test_docs[:10]):  # Test first 10
                start_time = time.time()
                try:
                    result = ingestor.ingest_file(str(doc_path))
                    processing_time = (time.time() - start_time) * 1000
                    single_doc_times.append(processing_time)

                    if i % 5 == 0:
                        print(f"   Document {i+1}: {processing_time:.1f}ms")

                except Exception as e:
                    print(f"   ❌ Document {i+1} failed: {e}")

            # Test bulk processing
            print("\n🔄 Bulk document processing...")
            remaining_docs = test_docs[10:30]  # Process 20 more

            start_time = time.time()
            successful_bulk = 0
            failed_bulk = 0

            for doc_path in remaining_docs:
                try:
                    result = ingestor.ingest_file(str(doc_path))
                    successful_bulk += 1
                except Exception as e:
                    failed_bulk += 1

            bulk_time = (time.time() - start_time) * 1000
            avg_bulk_time = bulk_time / len(remaining_docs) if remaining_docs else 0

            # Store results
            self.results['document_processing'] = {
                'single_doc_count': len(single_doc_times),
                'single_doc_avg_ms': sum(single_doc_times) / len(single_doc_times) if single_doc_times else 0,
                'single_doc_max_ms': max(single_doc_times) if single_doc_times else 0,
                'bulk_processed': successful_bulk,
                'bulk_failed': failed_bulk,
                'bulk_total_ms': bulk_time,
                'bulk_avg_ms': avg_bulk_time,
                'status': 'success' if successful_bulk > failed_bulk else 'degraded'
            }

            print(f"   ✅ Single docs avg: {self.results['document_processing']['single_doc_avg_ms']:.1f}ms")
            print(f"   📊 Bulk success: {successful_bulk}/{successful_bulk + failed_bulk}")
            print(f"   ⚡ Bulk avg: {avg_bulk_time:.1f}ms per document")

        except Exception as e:
            print(f"❌ Document processing test failed: {e}")
            self.results['document_processing'] = {'error': str(e), 'status': 'failed'}

    def test_article_processing_stress(self):
        """Test article processing under stress conditions"""
        print("\n🌐 Article Processing Stress Test")
        print("=" * 50)

        try:
            # Create test URLs
            test_urls = self.create_test_urls(20)

            # Initialize article manager
            article_manager = ArticleManager(self.config)

            # Test single URL processing
            print("🔍 Single URL processing...")
            single_url_times = []
            successful_urls = 0

            for i, url in enumerate(test_urls[:5]):  # Test first 5
                start_time = time.time()
                try:
                    result = article_manager.process_article(url)
                    processing_time = (time.time() - start_time) * 1000
                    single_url_times.append(processing_time)

                    if result and result.get('success', False):
                        successful_urls += 1

                    print(f"   URL {i+1}: {processing_time:.1f}ms {'✅' if result else '❌'}")

                except Exception as e:
                    processing_time = (time.time() - start_time) * 1000
                    print(f"   URL {i+1}: {processing_time:.1f}ms ❌ ({e})")

            # Test concurrent URL processing
            print("\n🔄 Concurrent URL processing...")

            def process_single_url(url_data):
                url, thread_id = url_data
                start_time = time.time()
                try:
                    result = article_manager.process_article(url)
                    processing_time = (time.time() - start_time) * 1000
                    return {
                        'thread_id': thread_id,
                        'url': url,
                        'time_ms': processing_time,
                        'success': result and result.get('success', False),
                        'error': None
                    }
                except Exception as e:
                    processing_time = (time.time() - start_time) * 1000
                    return {
                        'thread_id': thread_id,
                        'url': url,
                        'time_ms': processing_time,
                        'success': False,
                        'error': str(e)
                    }

            # Concurrent processing with 3 threads
            concurrent_urls = [(url, i) for i, url in enumerate(test_urls[5:10])]

            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                concurrent_results = list(executor.map(process_single_url, concurrent_urls))

            concurrent_successful = len([r for r in concurrent_results if r['success']])
            concurrent_times = [r['time_ms'] for r in concurrent_results]

            # Store results
            self.results['article_processing'] = {
                'single_url_count': len(single_url_times),
                'single_url_successful': successful_urls,
                'single_url_avg_ms': sum(single_url_times) / len(single_url_times) if single_url_times else 0,
                'concurrent_processed': len(concurrent_results),
                'concurrent_successful': concurrent_successful,
                'concurrent_avg_ms': sum(concurrent_times) / len(concurrent_times) if concurrent_times else 0,
                'status': 'success' if concurrent_successful > 0 else 'degraded'
            }

            print(f"   ✅ Single URLs: {successful_urls}/{len(single_url_times)}")
            print(f"   🔄 Concurrent: {concurrent_successful}/{len(concurrent_results)}")
            print(f"   ⚡ Concurrent avg: {self.results['article_processing']['concurrent_avg_ms']:.1f}ms")

        except Exception as e:
            print(f"❌ Article processing test failed: {e}")
            self.results['article_processing'] = {'error': str(e), 'status': 'failed'}

    def test_database_stress(self):
        """Test database operations under stress"""
        print("\n🗄️ Database Stress Test")
        print("=" * 50)

        try:
            # Initialize database
            db = SimpleDatabase()

            # Test bulk insertions
            print("📊 Bulk insertion test...")

            bulk_data = []
            for i in range(100):
                bulk_data.append({
                    'title': f'Test Article {i}',
                    'content': f'Test content for article {i} with additional details and information.',
                    'url': f'https://test-{i}.example.com',
                    'content_type': 'article',
                    'timestamp': datetime.now().isoformat()
                })

            start_time = time.time()
            successful_inserts = 0

            for data in bulk_data:
                try:
                    db.store_content(
                        title=data['title'],
                        content=data['content'],
                        url=data['url'],
                        content_type=data['content_type']
                    )
                    successful_inserts += 1
                except Exception:
                    pass

            bulk_insert_time = (time.time() - start_time) * 1000

            # Test concurrent reads
            print("🔍 Concurrent read test...")

            def perform_search(query_id):
                try:
                    start_time = time.time()
                    results = db.search_content(f"Test Article {query_id % 10}")
                    search_time = (time.time() - start_time) * 1000
                    return {'query_id': query_id, 'time_ms': search_time, 'count': len(results), 'success': True}
                except Exception as e:
                    return {'query_id': query_id, 'error': str(e), 'success': False}

            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                search_results = list(executor.map(perform_search, range(20)))

            successful_searches = [r for r in search_results if r['success']]
            search_times = [r['time_ms'] for r in successful_searches]

            self.results['bulk_operations'] = {
                'bulk_inserts': successful_inserts,
                'bulk_insert_time_ms': bulk_insert_time,
                'bulk_insert_avg_ms': bulk_insert_time / len(bulk_data) if bulk_data else 0,
                'concurrent_searches': len(successful_searches),
                'search_avg_ms': sum(search_times) / len(search_times) if search_times else 0,
                'status': 'success' if successful_inserts > 50 and len(successful_searches) > 15 else 'degraded'
            }

            print(f"   ✅ Bulk inserts: {successful_inserts}/100")
            print(f"   ⚡ Insert avg: {self.results['bulk_operations']['bulk_insert_avg_ms']:.1f}ms")
            print(f"   🔍 Concurrent searches: {len(successful_searches)}/20")
            print(f"   📊 Search avg: {self.results['bulk_operations']['search_avg_ms']:.1f}ms")

        except Exception as e:
            print(f"❌ Database stress test failed: {e}")
            self.results['bulk_operations'] = {'error': str(e), 'status': 'failed'}

    def test_memory_performance(self):
        """Test memory usage during processing"""
        print("\n🧠 Memory Performance Test")
        print("=" * 50)

        try:
            import psutil
            import gc

            process = psutil.Process()

            # Baseline memory
            gc.collect()
            baseline_memory = process.memory_info().rss / 1024 / 1024  # MB

            print(f"📊 Baseline memory: {baseline_memory:.1f}MB")

            # Memory during document processing
            test_docs = self.create_test_documents(20)

            memory_samples = []
            for i, doc_path in enumerate(test_docs):
                try:
                    # Simple file processing simulation
                    with open(doc_path, 'r') as f:
                        content = f.read()

                    # Process content (simulate heavy operations)
                    processed_content = content.upper().lower() * 2

                    if i % 5 == 0:
                        current_memory = process.memory_info().rss / 1024 / 1024
                        memory_samples.append(current_memory)
                        print(f"   Document {i+1}: {current_memory:.1f}MB")

                except Exception as e:
                    continue

            # Final memory check
            gc.collect()
            final_memory = process.memory_info().rss / 1024 / 1024

            peak_memory = max(memory_samples) if memory_samples else baseline_memory
            memory_growth = final_memory - baseline_memory

            self.results['memory_usage'] = {
                'baseline_mb': baseline_memory,
                'peak_mb': peak_memory,
                'final_mb': final_memory,
                'growth_mb': memory_growth,
                'samples': len(memory_samples),
                'status': 'healthy' if memory_growth < 50 else 'concerning'
            }

            print(f"   📈 Peak memory: {peak_memory:.1f}MB")
            print(f"   📊 Memory growth: {memory_growth:.1f}MB")
            print(f"   🎯 Status: {self.results['memory_usage']['status']}")

        except ImportError:
            print("⚠️ psutil not available - skipping memory test")
            self.results['memory_usage'] = {'status': 'skipped', 'reason': 'psutil not available'}
        except Exception as e:
            print(f"❌ Memory test failed: {e}")
            self.results['memory_usage'] = {'error': str(e), 'status': 'failed'}

    def cleanup_test_data(self):
        """Clean up test data"""
        print("\n🧹 Cleaning up test data...")

        try:
            # Remove test documents
            for file_path in self.test_data_dir.glob("test_doc_*.txt"):
                file_path.unlink()

            # Remove test data directory if empty
            if self.test_data_dir.exists() and not any(self.test_data_dir.iterdir()):
                self.test_data_dir.rmdir()

            print("   ✅ Test data cleaned up")

        except Exception as e:
            print(f"   ⚠️ Cleanup warning: {e}")

    def generate_report(self):
        """Generate comprehensive stress test report"""
        print("\n📊 CONTENT PROCESSING STRESS TEST REPORT")
        print("=" * 60)

        # Count successful tests
        test_categories = ['document_processing', 'article_processing', 'bulk_operations', 'memory_usage']
        successful_tests = 0
        total_tests = len(test_categories)

        for category in test_categories:
            if category in self.results:
                status = self.results[category].get('status', 'unknown')
                if status in ['success', 'healthy']:
                    successful_tests += 1

        print(f"\n🎯 SUMMARY")
        print(f"   📊 Tests passed: {successful_tests}/{total_tests}")

        # Detailed results
        if 'document_processing' in self.results:
            doc_result = self.results['document_processing']
            if 'single_doc_avg_ms' in doc_result:
                print(f"   📄 Document processing: {doc_result['single_doc_avg_ms']:.1f}ms avg")

        if 'article_processing' in self.results:
            article_result = self.results['article_processing']
            if 'concurrent_successful' in article_result:
                print(f"   🌐 Article processing: {article_result['concurrent_successful']} concurrent successes")

        if 'bulk_operations' in self.results:
            bulk_result = self.results['bulk_operations']
            if 'bulk_inserts' in bulk_result:
                print(f"   🗄️ Database operations: {bulk_result['bulk_inserts']} bulk inserts")

        if 'memory_usage' in self.results:
            memory_result = self.results['memory_usage']
            if 'growth_mb' in memory_result:
                print(f"   🧠 Memory usage: {memory_result['growth_mb']:.1f}MB growth")

        # Overall assessment
        success_rate = successful_tests / total_tests
        if success_rate >= 0.75:
            status = "✅ EXCELLENT"
        elif success_rate >= 0.5:
            status = "⚠️ GOOD"
        else:
            status = "❌ NEEDS WORK"

        print(f"\n🎯 Overall Status: {status}")
        print(f"✅ Task 2.5 {'COMPLETED' if status.startswith('✅') else 'NEEDS WORK'}: Content Processing Pipeline Stress Testing")

        return status.startswith('✅')

def main():
    """Run comprehensive content processing stress testing"""
    tester = ContentProcessingStressTester()

    try:
        # Run all stress tests
        tester.test_document_processing_stress()
        tester.test_article_processing_stress()
        tester.test_database_stress()
        tester.test_memory_performance()

        # Generate report
        success = tester.generate_report()

        return 0 if success else 1

    finally:
        # Always cleanup
        tester.cleanup_test_data()

if __name__ == "__main__":
    exit(main())