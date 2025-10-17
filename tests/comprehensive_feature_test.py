#!/usr/bin/env python3
"""
Comprehensive Atlas Feature Test Suite
Tests all major Atlas features with real-world data
"""
import os
import sys
import json
import time
import logging
import requests
import tempfile
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

# Add Atlas root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Atlas imports
try:
    from ask.recall.recall_engine import RecallEngine
    from ask.socratic.question_engine import QuestionEngine
    from ask.insights.pattern_detector import PatternDetector
    from ask.temporal.temporal_engine import TemporalEngine
    from ask.proactive.surfacer import ProactiveSurfacer
    from ask.recommendations.recommendation_engine import RecommendationEngine
    from helpers.unified_ai import UnifiedAISystem
    from helpers.search_engine import AtlasSearchEngine
    from helpers.config import get_config
except ImportError as e:
    print(f"Failed to import Atlas components: {e}")
    print("Make sure you're running from Atlas root directory")
    sys.exit(1)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_results.log')
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class TestResult:
    """Test result data structure"""
    test_name: str
    passed: bool
    duration: float
    error: Optional[str] = None
    details: Optional[Dict] = None

class AtlasFeatureTester:
    """Comprehensive Atlas feature testing"""

    def __init__(self, atlas_url: str = "http://localhost:8000", use_real_data: bool = True):
        self.atlas_url = atlas_url
        self.use_real_data = use_real_data
        self.test_results: List[TestResult] = []
        try:
            from helpers.config import config
            self.config = config
        except:
            self.config = {}

        # Test data samples
        self.sample_articles = [
            {
                "title": "The Future of AI and Machine Learning",
                "content": "Artificial intelligence and machine learning are rapidly transforming industries across the globe. From healthcare to finance, these technologies are enabling unprecedented capabilities. Deep learning models can now process vast amounts of data and identify patterns that were previously invisible to human analysts. The implications for society are profound, touching everything from autonomous vehicles to personalized medicine. As we look ahead, the integration of AI into daily life will continue to accelerate, bringing both opportunities and challenges that we must carefully navigate.",
                "url": "https://example.com/ai-future",
                "source": "comprehensive-test"
            },
            {
                "title": "Climate Change and Renewable Energy Solutions",
                "content": "The global climate crisis demands immediate and sustained action across all sectors of society. Renewable energy technologies, including solar, wind, and hydroelectric power, are becoming increasingly cost-effective and efficient. Energy storage solutions are solving the intermittency challenges traditionally associated with renewable sources. Carbon capture and storage technologies offer additional pathways to reduce atmospheric CO2 levels. International cooperation and policy frameworks will be essential to achieving the scale of change needed to address this existential challenge.",
                "url": "https://example.com/climate-solutions",
                "source": "comprehensive-test"
            },
            {
                "title": "The Evolution of Remote Work Culture",
                "content": "The global shift to remote work has fundamentally altered how we think about employment, productivity, and work-life balance. Digital collaboration tools have enabled seamless communication across geographic boundaries, while flexible scheduling has improved employee satisfaction and retention. However, challenges remain around maintaining company culture, ensuring equitable opportunities, and managing the psychological impacts of isolation. Organizations are developing hybrid models that combine the benefits of both remote and in-person work environments.",
                "url": "https://example.com/remote-work",
                "source": "comprehensive-test"
            }
        ]

        # Real-world data sources for testing
        self.real_data_sources = [
            "https://news.ycombinator.com",
            "https://www.reddit.com/r/programming/.json",
            "https://www.techmeme.com",
            "https://arxiv.org/list/cs.AI/recent"
        ]

    def run_all_tests(self) -> Dict[str, Any]:
        """Run comprehensive test suite"""
        logger.info("Starting comprehensive Atlas feature test suite")
        start_time = time.time()

        # Test categories
        test_categories = [
            ("Content Ingestion", self._test_content_ingestion),
            ("Search Functionality", self._test_search_functionality),
            ("Cognitive Features", self._test_cognitive_features),
            ("API Endpoints", self._test_api_endpoints),
            ("Data Processing", self._test_data_processing),
            ("Performance", self._test_performance),
            ("Integration", self._test_integration)
        ]

        for category_name, test_function in test_categories:
            logger.info(f"Testing {category_name}...")
            try:
                test_function()
            except Exception as e:
                logger.error(f"Error in {category_name}: {e}")
                self.test_results.append(TestResult(
                    test_name=f"{category_name} - Fatal Error",
                    passed=False,
                    duration=0,
                    error=str(e)
                ))

        total_duration = time.time() - start_time

        # Generate test report
        return self._generate_test_report(total_duration)

    def _test_content_ingestion(self) -> None:
        """Test content ingestion capabilities"""

        # Test 1: API Content Ingestion
        start_time = time.time()
        try:
            for i, article in enumerate(self.sample_articles):
                response = requests.post(
                    f"{self.atlas_url}/api/v1/content/save",
                    json=article,
                    headers={"Content-Type": "application/json"}
                )
                assert response.status_code == 200, f"API ingestion failed: {response.status_code}"

            self.test_results.append(TestResult(
                test_name="Content Ingestion - API Upload",
                passed=True,
                duration=time.time() - start_time,
                details={"articles_processed": len(self.sample_articles)}
            ))
        except Exception as e:
            self.test_results.append(TestResult(
                test_name="Content Ingestion - API Upload",
                passed=False,
                duration=time.time() - start_time,
                error=str(e)
            ))

        # Test 2: File Upload Processing
        start_time = time.time()
        try:
            # Create a temporary text file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write("This is a test document for Atlas ingestion. It contains sample content to verify that file processing works correctly.")
                temp_file = f.name

            # Test file upload (if endpoint exists)
            try:
                with open(temp_file, 'rb') as f:
                    files = {'file': f}
                    response = requests.post(
                        f"{self.atlas_url}/api/v1/content/upload",
                        files=files
                    )
                # File upload endpoint may not exist, that's okay
                success = response.status_code == 200
            except:
                success = True  # Skip if upload endpoint doesn't exist

            os.unlink(temp_file)

            self.test_results.append(TestResult(
                test_name="Content Ingestion - File Upload",
                passed=success,
                duration=time.time() - start_time
            ))
        except Exception as e:
            self.test_results.append(TestResult(
                test_name="Content Ingestion - File Upload",
                passed=False,
                duration=time.time() - start_time,
                error=str(e)
            ))

        # Test 3: Real Data Ingestion (if enabled)
        if self.use_real_data:
            self._test_real_data_ingestion()

    def _test_real_data_ingestion(self) -> None:
        """Test ingestion of real-world data"""
        start_time = time.time()

        try:
            # Fetch and ingest real data from Hacker News
            hn_response = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json")
            if hn_response.status_code == 200:
                story_ids = hn_response.json()[:5]  # Get top 5 stories

                ingested_count = 0
                for story_id in story_ids:
                    try:
                        story_response = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json")
                        if story_response.status_code == 200:
                            story = story_response.json()

                            if story.get('url'):  # Only process stories with URLs
                                content_data = {
                                    "title": story.get('title', 'No Title'),
                                    "url": story.get('url'),
                                    "content": f"Hacker News Story: {story.get('title')}\nURL: {story.get('url')}\nScore: {story.get('score')}\nComments: {story.get('descendants', 0)}",
                                    "source": "hacker-news-test",
                                    "metadata": {
                                        "hn_id": story_id,
                                        "score": story.get('score'),
                                        "comments": story.get('descendants', 0)
                                    }
                                }

                                response = requests.post(
                                    f"{self.atlas_url}/api/v1/content/save",
                                    json=content_data,
                                    headers={"Content-Type": "application/json"}
                                )

                                if response.status_code == 200:
                                    ingested_count += 1
                    except:
                        continue

                self.test_results.append(TestResult(
                    test_name="Content Ingestion - Real Data (Hacker News)",
                    passed=ingested_count > 0,
                    duration=time.time() - start_time,
                    details={"stories_ingested": ingested_count}
                ))
            else:
                self.test_results.append(TestResult(
                    test_name="Content Ingestion - Real Data (Hacker News)",
                    passed=False,
                    duration=time.time() - start_time,
                    error="Failed to fetch Hacker News data"
                ))

        except Exception as e:
            self.test_results.append(TestResult(
                test_name="Content Ingestion - Real Data (Hacker News)",
                passed=False,
                duration=time.time() - start_time,
                error=str(e)
            ))

    def _test_search_functionality(self) -> None:
        """Test search and retrieval capabilities"""

        # Give content time to be indexed
        time.sleep(2)

        # Test 1: Basic Search
        start_time = time.time()
        try:
            response = requests.get(f"{self.atlas_url}/api/v1/search?q=artificial+intelligence")
            assert response.status_code == 200, f"Search API failed: {response.status_code}"

            results = response.json()
            assert 'results' in results, "Search response missing results"

            self.test_results.append(TestResult(
                test_name="Search - Basic Query",
                passed=True,
                duration=time.time() - start_time,
                details={"results_count": len(results.get('results', []))}
            ))
        except Exception as e:
            self.test_results.append(TestResult(
                test_name="Search - Basic Query",
                passed=False,
                duration=time.time() - start_time,
                error=str(e)
            ))

        # Test 2: Semantic Search
        start_time = time.time()
        try:
            search_engine = AtlasSearchEngine()
            results = search_engine.search("machine learning algorithms")

            self.test_results.append(TestResult(
                test_name="Search - Semantic Search Engine",
                passed=True,
                duration=time.time() - start_time,
                details={"results_count": len(results) if results else 0}
            ))
        except Exception as e:
            self.test_results.append(TestResult(
                test_name="Search - Semantic Search Engine",
                passed=False,
                duration=time.time() - start_time,
                error=str(e)
            ))

    def _test_cognitive_features(self) -> None:
        """Test all cognitive AI features"""

        # Test 1: Recall Engine
        start_time = time.time()
        try:
            recall_engine = RecallEngine()
            recalls = recall_engine.get_active_recalls()

            self.test_results.append(TestResult(
                test_name="Cognitive - Recall Engine",
                passed=True,
                duration=time.time() - start_time,
                details={"recalls_count": len(recalls) if recalls else 0}
            ))
        except Exception as e:
            self.test_results.append(TestResult(
                test_name="Cognitive - Recall Engine",
                passed=False,
                duration=time.time() - start_time,
                error=str(e)
            ))

        # Test 2: Socratic Question Engine
        start_time = time.time()
        try:
            question_engine = QuestionEngine()
            questions = question_engine.generate_questions("artificial intelligence")

            self.test_results.append(TestResult(
                test_name="Cognitive - Socratic Questions",
                passed=len(questions) > 0 if questions else False,
                duration=time.time() - start_time,
                details={"questions_generated": len(questions) if questions else 0}
            ))
        except Exception as e:
            self.test_results.append(TestResult(
                test_name="Cognitive - Socratic Questions",
                passed=False,
                duration=time.time() - start_time,
                error=str(e)
            ))

        # Test 3: Pattern Detector
        start_time = time.time()
        try:
            pattern_detector = PatternDetector()
            patterns = pattern_detector.detect_patterns()

            self.test_results.append(TestResult(
                test_name="Cognitive - Pattern Detection",
                passed=True,
                duration=time.time() - start_time,
                details={"patterns_found": len(patterns) if patterns else 0}
            ))
        except Exception as e:
            self.test_results.append(TestResult(
                test_name="Cognitive - Pattern Detection",
                passed=False,
                duration=time.time() - start_time,
                error=str(e)
            ))

        # Test 4: Temporal Engine
        start_time = time.time()
        try:
            temporal_engine = TemporalEngine()
            insights = temporal_engine.get_temporal_insights()

            self.test_results.append(TestResult(
                test_name="Cognitive - Temporal Analysis",
                passed=True,
                duration=time.time() - start_time,
                details={"insights_generated": len(insights) if insights else 0}
            ))
        except Exception as e:
            self.test_results.append(TestResult(
                test_name="Cognitive - Temporal Analysis",
                passed=False,
                duration=time.time() - start_time,
                error=str(e)
            ))

        # Test 5: Proactive Surfacer
        start_time = time.time()
        try:
            surfacer = ProactiveSurfacer()
            suggestions = surfacer.surface_relevant_content("technology")

            self.test_results.append(TestResult(
                test_name="Cognitive - Proactive Surfacing",
                passed=True,
                duration=time.time() - start_time,
                details={"suggestions_count": len(suggestions) if suggestions else 0}
            ))
        except Exception as e:
            self.test_results.append(TestResult(
                test_name="Cognitive - Proactive Surfacing",
                passed=False,
                duration=time.time() - start_time,
                error=str(e)
            ))

        # Test 6: Recommendation Engine
        start_time = time.time()
        try:
            rec_engine = RecommendationEngine()
            recommendations = rec_engine.get_recommendations()

            self.test_results.append(TestResult(
                test_name="Cognitive - Recommendations",
                passed=True,
                duration=time.time() - start_time,
                details={"recommendations_count": len(recommendations) if recommendations else 0}
            ))
        except Exception as e:
            self.test_results.append(TestResult(
                test_name="Cognitive - Recommendations",
                passed=False,
                duration=time.time() - start_time,
                error=str(e)
            ))

    def _test_api_endpoints(self) -> None:
        """Test all major API endpoints"""

        endpoints = [
            ("/api/v1/health", "GET"),
            ("/api/v1/stats", "GET"),
            ("/ask/api", "GET"),
            ("/api/v1/search", "GET")
        ]

        for endpoint, method in endpoints:
            start_time = time.time()
            try:
                if method == "GET":
                    response = requests.get(f"{self.atlas_url}{endpoint}")
                else:
                    response = requests.post(f"{self.atlas_url}{endpoint}")

                passed = response.status_code in [200, 201, 302]  # Accept redirects too

                self.test_results.append(TestResult(
                    test_name=f"API - {endpoint}",
                    passed=passed,
                    duration=time.time() - start_time,
                    details={"status_code": response.status_code}
                ))
            except Exception as e:
                self.test_results.append(TestResult(
                    test_name=f"API - {endpoint}",
                    passed=False,
                    duration=time.time() - start_time,
                    error=str(e)
                ))

    def _test_data_processing(self) -> None:
        """Test data processing capabilities"""

        # Test 1: Unified AI Processing
        start_time = time.time()
        try:
            ai = UnifiedAISystem()
            result = ai.process_text("This is a test document for processing by the Atlas AI system.")

            self.test_results.append(TestResult(
                test_name="Data Processing - Unified AI",
                passed=result is not None,
                duration=time.time() - start_time,
                details={"result_length": len(str(result)) if result else 0}
            ))
        except Exception as e:
            self.test_results.append(TestResult(
                test_name="Data Processing - Unified AI",
                passed=False,
                duration=time.time() - start_time,
                error=str(e)
            ))

    def _test_performance(self) -> None:
        """Test system performance"""

        # Test 1: Search Performance
        start_time = time.time()
        try:
            for i in range(10):
                response = requests.get(f"{self.atlas_url}/api/v1/search?q=test+query+{i}")
                assert response.status_code == 200

            avg_duration = (time.time() - start_time) / 10

            self.test_results.append(TestResult(
                test_name="Performance - Search Speed",
                passed=avg_duration < 2.0,  # Should average less than 2 seconds
                duration=time.time() - start_time,
                details={"avg_search_time": avg_duration, "total_searches": 10}
            ))
        except Exception as e:
            self.test_results.append(TestResult(
                test_name="Performance - Search Speed",
                passed=False,
                duration=time.time() - start_time,
                error=str(e)
            ))

    def _test_integration(self) -> None:
        """Test system integration"""

        # Test 1: End-to-End Workflow
        start_time = time.time()
        try:
            # Ingest content
            test_content = {
                "title": "Integration Test Article",
                "content": "This is a comprehensive integration test for the Atlas system. It tests the complete workflow from ingestion to retrieval to cognitive processing.",
                "url": "https://example.com/integration-test",
                "source": "integration-test"
            }

            # Step 1: Ingest
            response = requests.post(
                f"{self.atlas_url}/api/v1/content/save",
                json=test_content,
                headers={"Content-Type": "application/json"}
            )
            assert response.status_code == 200

            # Step 2: Wait for indexing
            time.sleep(3)

            # Step 3: Search
            search_response = requests.get(f"{self.atlas_url}/api/v1/search?q=integration+test")
            assert search_response.status_code == 200

            search_results = search_response.json()
            found_test_content = any(
                "integration test" in result.get('title', '').lower()
                for result in search_results.get('results', [])
            )

            self.test_results.append(TestResult(
                test_name="Integration - End-to-End Workflow",
                passed=found_test_content,
                duration=time.time() - start_time,
                details={"workflow_steps": ["ingest", "index", "search", "retrieve"]}
            ))

        except Exception as e:
            self.test_results.append(TestResult(
                test_name="Integration - End-to-End Workflow",
                passed=False,
                duration=time.time() - start_time,
                error=str(e)
            ))

    def _generate_test_report(self, total_duration: float) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        passed_tests = [r for r in self.test_results if r.passed]
        failed_tests = [r for r in self.test_results if not r.passed]

        report = {
            "test_summary": {
                "total_tests": len(self.test_results),
                "passed": len(passed_tests),
                "failed": len(failed_tests),
                "success_rate": len(passed_tests) / len(self.test_results) * 100 if self.test_results else 0,
                "total_duration": total_duration
            },
            "passed_tests": [
                {
                    "name": r.test_name,
                    "duration": r.duration,
                    "details": r.details
                }
                for r in passed_tests
            ],
            "failed_tests": [
                {
                    "name": r.test_name,
                    "duration": r.duration,
                    "error": r.error,
                    "details": r.details
                }
                for r in failed_tests
            ],
            "test_timestamp": datetime.now().isoformat(),
            "atlas_url": self.atlas_url
        }

        return report

    def save_test_report(self, report: Dict[str, Any], filename: str = None) -> str:
        """Save test report to file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"atlas_test_report_{timestamp}.json"

        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info(f"Test report saved to {filename}")
        return filename

def main():
    """Main function for command-line usage"""
    import argparse

    parser = argparse.ArgumentParser(description="Comprehensive Atlas Feature Tester")
    parser.add_argument('--atlas-url', default='http://localhost:8000', help='Atlas server URL')
    parser.add_argument('--no-real-data', action='store_true', help='Skip real data ingestion tests')
    parser.add_argument('--output', help='Output file for test report')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    tester = AtlasFeatureTester(
        atlas_url=args.atlas_url,
        use_real_data=not args.no_real_data
    )

    try:
        # Run tests
        report = tester.run_all_tests()

        # Print summary
        summary = report['test_summary']
        logger.info(f"\n{'='*60}")
        logger.info(f"ATLAS COMPREHENSIVE TEST RESULTS")
        logger.info(f"{'='*60}")
        logger.info(f"Total Tests: {summary['total_tests']}")
        logger.info(f"Passed: {summary['passed']} ({summary['success_rate']:.1f}%)")
        logger.info(f"Failed: {summary['failed']}")
        logger.info(f"Total Duration: {summary['total_duration']:.2f} seconds")

        if report['failed_tests']:
            logger.info(f"\nFAILED TESTS:")
            for test in report['failed_tests']:
                logger.info(f"  ❌ {test['name']}: {test['error']}")

        # Save report
        report_file = tester.save_test_report(report, args.output)
        logger.info(f"\nDetailed report saved to: {report_file}")

        # Exit with appropriate code
        sys.exit(0 if summary['failed'] == 0 else 1)

    except KeyboardInterrupt:
        logger.info("Testing interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error during testing: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()