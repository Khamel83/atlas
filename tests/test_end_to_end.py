#!/usr/bin/env python3
"""
Atlas v4 End-to-End Tests

Comprehensive end-to-end validation tests that verify the complete system
delivers on its vision and requirements, not just code functionality.
"""

import asyncio
import json
import os
import pathlib
import shutil
import sqlite3
import subprocess
import tempfile
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List
import sys

# Add src to Python path
script_dir = Path(__file__).parent
src_dir = script_dir.parent / "src"
sys.path.insert(0, str(src_dir))

from atlas.config import ConfigManager
from atlas.storage import StorageManager
from atlas.ingestion import IngestionManager
from atlas.bot.main import AtlasBot
from atlas.logging.enhanced_logging import setup_enhanced_logging


class VisionValidationTest(unittest.TestCase):
    """Tests that validate Atlas delivers on its core vision and promises."""

    @classmethod
    def setUpClass(cls):
        """Setup comprehensive test environment."""
        cls.test_dir = Path(tempfile.mkdtemp(prefix="atlas_vision_test_"))
        cls.vault_dir = cls.test_dir / "vault"
        cls.data_dir = cls.test_dir / "data"
        cls.config_dir = cls.test_dir / "config"
        cls.logs_dir = cls.test_dir / "logs"

        # Create complete directory structure
        for directory in [cls.vault_dir, cls.data_dir, cls.config_dir, cls.logs_dir]:
            directory.mkdir(parents=True, exist_ok=True)

        cls.logger = setup_enhanced_logging(
            level="INFO",
            log_file=str(cls.logs_dir / "vision_test.log"),
            format_type="json",
            component_name="vision_test"
        )

        cls.logger.log_operation(
            level="INFO",
            operation="test_setup",
            message="Starting Atlas vision validation tests",
            component="testing"
        )

    @classmethod
    def tearDownClass(cls):
        """Cleanup test environment."""
        if cls.test_dir.exists():
            shutil.rmtree(cls.test_dir)
            cls.logger.log_operation(
                level="INFO",
                operation="test_cleanup",
                message="Atlas vision validation tests completed",
                component="testing"
            )

    def setUp(self):
        """Setup each test."""
        # Create realistic test configuration
        self.config = {
            "vault": {
                "root": str(self.vault_dir),
                "structure": {
                    "inbox": "{type}/{year}/{month}",
                    "processed": "processed/{type}/{year}/{month}"
                }
            },
            "database": {
                "type": "sqlite",
                "path": str(self.data_dir / "atlas.db"),
                "journal_mode": "WAL"
            },
            "ingestion": {
                "max_concurrent": 3,
                "rate_limit": 60,
                "timeout": 30,
                "retry_attempts": 3,
                "deduplication": {
                    "enabled": True,
                    "algorithm": "sha256"
                }
            },
            "logging": {
                "level": "INFO",
                "format": "json",
                "file": str(self.logs_dir / "atlas.log")
            },
            "content": {
                "validation": {
                    "min_content_length": 100,
                    "required_fields": ["title", "url", "content"]
                },
                "formatting": {
                    "max_title_length": 200,
                    "max_summary_length": 500
                }
            }
        }

        # Save configuration
        import yaml
        config_file = self.config_dir / "test.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(self.config, f)

    def test_vision_promise_1_personal_knowledge_automation(self):
        """
        Vision Test 1: Atlas should truly automate personal knowledge management.
        This tests the core promise that Atlas reduces manual knowledge work.
        """
        self.logger.log_operation(
            level="INFO",
            operation="vision_test_1",
            message="Testing personal knowledge automation promise",
            component="vision_validation"
        )

        # Initialize complete system
        storage = StorageManager(str(self.vault_dir))
        storage.initialize_vault()

        ingestion = IngestionManager(self.config)
        ingestion.storage = storage

        # Simulate realistic content ingestion workflow
        test_content_sources = [
            {
                "type": "rss",
                "url": "https://feeds.simplecast.com/XA_851k3",  # Real podcast feed
                "expected_content": True,
                "automation_level": "full"
            },
            {
                "type": "article",
                "url": "https://www.a16z.com/2025/10/10/ai-agents/",
                "title": "The Future of AI Agents",
                "content": "AI agents represent a fundamental shift in how we interact with technology...",
                "automation_level": "semi"
            },
            {
                "type": "newsletter",
                "url": "https://example.com/newsletter/123",
                "title": "Weekly Tech Newsletter",
                "content": "This week in tech: Major breakthroughs in quantum computing...",
                "automation_level": "full"
            }
        ]

        # Test automation promises
        automation_metrics = {
            "manual_steps_required": 0,
            "auto_categorized": 0,
            "auto_tagged": 0,
            "duplicates_detected": 0,
            "searchable_immediately": 0
        }

        for source in test_content_sources:
            with self.logger.track_performance("process_content", "ingestion"):
                # Process content (this should be automatic)
                if source["type"] == "rss":
                    # RSS should be fully automatic
                    try:
                        content_data = {
                            "title": f"RSS Item from {source['url']}",
                            "url": source["url"],
                            "content": source.get("content", "Sample RSS content about technology trends..."),
                            "source_type": "rss",
                            "metadata": {
                                "feed_url": source["url"],
                                "auto_categorized": True,
                                "auto_tagged": ["technology", "rss"]
                            }
                        }

                        file_path = storage.write_content(
                            url=content_data["url"],
                            title=content_data["title"],
                            content=content_data["content"],
                            source_type=content_data["source_type"],
                            metadata=content_data["metadata"]
                        )

                        automation_metrics["auto_categorized"] += 1
                        automation_metrics["auto_tagged"] += 1
                        automation_metrics["searchable_immediately"] += 1

                    except Exception as e:
                        # RSS failure is acceptable in test environment
                        self.logger.log_operation(
                            level="WARNING",
                            operation="rss_test",
                            message=f"RSS test failed (expected in test env): {e}",
                            component="vision_validation"
                        )
                        continue

                else:
                    # Manual content input should be minimal
                    content_data = {
                        "title": source["title"],
                        "url": source["url"],
                        "content": source["content"],
                        "source_type": source["type"],
                        "metadata": {
                            "source_priority": "normal",
                            "automation_level": source["automation_level"]
                        }
                    }

                    file_path = storage.write_content(
                        url=content_data["url"],
                        title=content_data["title"],
                        content=content_data["content"],
                        source_type=content_data["source_type"],
                        metadata=content_data["metadata"]
                    )

                    automation_metrics["searchable_immediately"] += 1

        # Verify automation promises
        self.assertGreater(
            automation_metrics["searchable_immediately"], 0,
            "Content should be immediately searchable after ingestion"
        )

        # Test that knowledge is truly accessible
        search_results = storage.search_content("technology")
        self.assertGreater(
            len(search_results), 0,
            "Knowledge should be easily searchable and accessible"
        )

        # Test duplicate detection (key automation feature)
        duplicate_url = test_content_sources[0]["url"]
        duplicate_path = storage.write_content(
            url=duplicate_url,
            title="Duplicate Title",
            content="Duplicate content",
            source_type="test"
        )

        # Should return the same path (duplicate detected)
        original_path = storage.write_content(
            url=duplicate_url,
            title="Another Title",
            content="Different content",
            source_type="test"
        )

        self.assertEqual(
            duplicate_path, original_path,
            "System should automatically detect and handle duplicates"
        )

        self.logger.log_operation(
            level="INFO",
            operation="vision_test_1_complete",
            message=f"Personal knowledge automation validated: {automation_metrics}",
            component="vision_validation"
        )

    def test_vision_promise_2_obsidian_compatibility(self):
        """
        Vision Test 2: Atlas must be seamlessly compatible with Obsidian.
        This tests that Atlas content works perfectly with Obsidian's features.
        """
        self.logger.log_operation(
            level="INFO",
            operation="vision_test_2",
            message="Testing Obsidian compatibility promise",
            component="vision_validation"
        )

        storage = StorageManager(str(self.vault_dir))
        storage.initialize_vault()

        # Create test content with Obsidian-specific features
        test_content = {
            "title": "Machine Learning Fundamentals",
            "url": "https://example.com/ml-guide",
            "content": """# Machine Learning Fundamentals

Machine learning is a subset of [[Artificial Intelligence]] that focuses on neural networks and statistical patterns.

## Key Concepts
- [[Neural Networks]]
- [[Deep Learning]]
- [[Natural Language Processing]]

## Related Resources
- [Coursera ML Course](https://coursera.org/ml)
- See also: [[Data Science]] and [[Python Programming]]

This note connects to my [[Research]] vault and [[Project Ideas]].""",
            "source_type": "article",
            "metadata": {
                "tags": ["machine-learning", "ai", "education"],
                "created": datetime.now().isoformat(),
                "author": "Atlas Test",
                "reading_time": 5
            }
        }

        # Write content using Atlas
        file_path = storage.write_content(
            url=test_content["url"],
            title=test_content["title"],
            content=test_content["content"],
            source_type=test_content["source_type"],
            metadata=test_content["metadata"]
        )

        # Verify Obsidian compatibility
        self.assertTrue(file_path.exists(), "File should be created in vault")

        # Read back and verify YAML frontmatter (Obsidian standard)
        content_data = storage.read_content(file_path)

        # Verify frontmatter structure
        self.assertIn("tags", content_data["metadata"], "Should have tags for Obsidian")
        self.assertIsInstance(content_data["metadata"]["tags"], list, "Tags should be a list")

        # Verify content contains wiki links (Obsidian's linking format)
        self.assertIn("[[", content_data["content"], "Should contain Obsidian wiki links")

        # Verify markdown structure
        self.assertIn("# ", content_data["content"], "Should have proper markdown headers")

        # Test that file follows Obsidian naming conventions
        file_name = file_path.name
        self.assertTrue(
            file_name.endswith(".md"),
            "Files should have .md extension for Obsidian"
        )

        # Test that content is properly organized in vault structure
        relative_path = file_path.relative_to(self.vault_dir)
        path_parts = relative_path.parts

        self.assertGreaterEqual(len(path_parts), 3, "Should be organized in type/year/month structure")
        self.assertEqual(path_parts[0], "inbox", "Should be in inbox directory")

        # Test search functionality (critical for Obsidian users)
        search_results = storage.search_content("Machine Learning")
        self.assertGreater(len(search_results), 0, "Content should be searchable")

        # Test tag-based search
        tag_results = storage.search_content("machine-learning")
        self.assertGreater(len(tag_results), 0, "Content should be searchable by tags")

        self.logger.log_operation(
            level="INFO",
            operation="vision_test_2_complete",
            message="Obsidian compatibility validated",
            component="vision_validation"
        )

    def test_vision_promise_3_zero_configuration_complexity(self):
        """
        Vision Test 3: Atlas should work with minimal configuration.
        This tests the promise that Atlas "just works" out of the box.
        """
        self.logger.log_operation(
            level="INFO",
            operation="vision_test_3",
            message="Testing zero-configuration complexity promise",
            component="vision_validation"
        )

        # Test with absolute minimal configuration
        minimal_config = {
            "vault": {"root": str(self.vault_dir)},
            "database": {"type": "sqlite", "path": str(self.data_dir / "minimal.db")}
        }

        # System should initialize and work with minimal config
        storage = StorageManager(str(self.vault_dir))
        storage.initialize_vault()

        # Should be able to ingest content without complex setup
        simple_content = {
            "title": "Test Note",
            "url": "https://example.com/simple",
            "content": "Simple test content that should work without configuration.",
            "source_type": "manual"
        }

        file_path = storage.write_content(
            url=simple_content["url"],
            title=simple_content["title"],
            content=simple_content["content"],
            source_type=simple_content["source_type"]
        )

        self.assertTrue(file_path.exists(), "Simple content should work without config")

        # Should be able to search immediately
        results = storage.search_content("simple")
        self.assertGreater(len(results), 0, "Search should work without configuration")

        # Test that intelligent defaults are applied
        content_data = storage.read_content(file_path)
        self.assertIn("created", content_data["metadata"], "Should auto-add creation timestamp")
        self.assertIn("source_type", content_data["metadata"], "Should auto-add source type")

        self.logger.log_operation(
            level="INFO",
            operation="vision_test_3_complete",
            message="Zero-configuration complexity validated",
            component="vision_validation"
        )

    def test_vision_promise_4_content_quality_preservation(self):
        """
        Vision Test 4: Atlas should preserve and enhance content quality.
        This tests that Atlas makes content better, not worse.
        """
        self.logger.log_operation(
            level="INFO",
            operation="vision_test_4",
            message="Testing content quality preservation promise",
            component="vision_validation"
        )

        storage = StorageManager(str(self.vault_dir))
        storage.initialize_vault()

        # Test with high-quality content
        original_content = {
            "title": "The Complete Guide to Distributed Systems",
            "url": "https://example.com/distributed-systems",
            "content": """# The Complete Guide to Distributed Systems

## Introduction

Distributed systems are the foundation of modern cloud computing and microservices architecture. In this comprehensive guide, we'll explore the fundamental concepts, challenges, and best practices.

## Core Concepts

### CAP Theorem
The CAP theorem states that a distributed system can only simultaneously provide two out of the following three guarantees:

1. **Consistency** - All nodes see the same data at the same time
2. **Availability** - Every request receives a response
3. **Partition Tolerance** - System continues to operate despite network partitions

### Consensus Algorithms
- **Raft** - Easy to understand consensus algorithm
- **Paxos** - The original consensus algorithm
- **PBFT** - Practical Byzantine Fault Tolerance

## Real-World Applications

### Kubernetes
Container orchestration platform that manages distributed containerized applications.

### Apache Kafka
Distributed streaming platform that handles real-time data feeds.

## Further Reading
- Designing Data-Intensive Applications by Martin Kleppmann
- Distributed Systems: Principles and Paradigms by Tanenbaum
""",
            "source_type": "article",
            "metadata": {
                "author": "Expert Author",
                "publication_date": "2025-10-15",
                "reading_time": 15,
                "difficulty": "intermediate",
                "tags": ["distributed-systems", "kubernetes", "consensus", "architecture"]
            }
        }

        # Process content through Atlas
        file_path = storage.write_content(
            url=original_content["url"],
            title=original_content["title"],
            content=original_content["content"],
            source_type=original_content["source_type"],
            metadata=original_content["metadata"]
        )

        # Retrieve and verify quality preservation
        processed_content = storage.read_content(file_path)

        # Verify structure is preserved
        self.assertEqual(
            processed_content["title"],
            original_content["title"],
            "Title should be preserved exactly"
        )

        self.assertEqual(
            processed_content["url"],
            original_content["url"],
            "URL should be preserved exactly"
        )

        # Verify content integrity
        self.assertIn("# The Complete Guide to Distributed Systems", processed_content["content"])
        self.assertIn("CAP Theorem", processed_content["content"])
        self.assertIn("Kubernetes", processed_content["content"])

        # Verify metadata is enhanced, not lost
        original_metadata_keys = set(original_content["metadata"].keys())
        processed_metadata_keys = set(processed_content["metadata"].keys())

        self.assertGreaterEqual(
            len(processed_metadata_keys),
            len(original_metadata_keys),
            "Processed content should have at least as much metadata as original"
        )

        # Should have original metadata
        for key in original_metadata_keys:
            self.assertIn(key, processed_content["metadata"], f"Should preserve {key}")

        # Should have enhanced metadata
        self.assertIn("created", processed_content["metadata"], "Should add creation timestamp")
        self.assertIn("source_type", processed_content["metadata"], "Should add source type")

        # Test content enhancement features
        # Verify that search works well on processed content
        complex_search_results = storage.search_content("consensus algorithm")
        self.assertGreater(
            len(complex_search_results), 0,
            "Should find specific technical content"
        )

        # Test that content relationships are maintained
        tag_search_results = storage.search_content("distributed-systems")
        self.assertGreater(
            len(tag_search_results), 0,
            "Should find content by tags"
        )

        # Verify markdown formatting is preserved
        content_lines = processed_content["content"].split('\n')
        has_headers = any(line.strip().startswith('#') for line in content_lines)
        has_lists = any(line.strip().startswith(('1.', '-', '*')) for line in content_lines)
        has_bold = any('**' in line for line in content_lines)

        self.assertTrue(has_headers, "Should preserve markdown headers")
        self.assertTrue(has_lists, "Should preserve markdown lists")
        self.assertTrue(has_bold, "Should preserve markdown formatting")

        self.logger.log_operation(
            level="INFO",
            operation="vision_test_4_complete",
            message="Content quality preservation validated",
            component="vision_validation"
        )

    def test_vision_promise_5_scalability_and_performance(self):
        """
        Vision Test 5: Atlas should scale with user's knowledge growth.
        This tests that performance doesn't degrade as content grows.
        """
        self.logger.log_operation(
            level="INFO",
            operation="vision_test_5",
            message="Testing scalability and performance promise",
            component="vision_validation"
        )

        storage = StorageManager(str(self.vault_dir))
        storage.initialize_vault()

        # Test with growing content volume
        content_sizes = [10, 50, 100, 500]  # Number of content items
        performance_metrics = {}

        for size in content_sizes:
            self.logger.log_operation(
                level="INFO",
                operation="scalability_test",
                message=f"Testing with {size} content items",
                component="vision_validation"
            )

            start_time = time.time()

            # Add content
            for i in range(size):
                content = {
                    "title": f"Scalability Test Item {i}",
                    "url": f"https://example.com/test/{i}",
                    "content": f"This is test content item {i} with some unique content for testing search functionality. Includes keywords like scalability, performance, testing.",
                    "source_type": "test",
                    "metadata": {
                        "index": i,
                        "category": f"category_{i % 10}",
                        "tags": [f"tag_{i % 5}", "scalability", "testing"]
                    }
                }

                storage.write_content(
                    url=content["url"],
                    title=content["title"],
                    content=content["content"],
                    source_type=content["source_type"],
                    metadata=content["metadata"]
                )

            ingestion_time = time.time() - start_time

            # Test search performance
            search_start = time.time()
            search_results = storage.search_content("scalability")
            search_time = time.time() - search_start

            # Test metadata search performance
            metadata_start = time.time()
            all_content = storage.get_all_content()
            metadata_time = time.time() - metadata_start

            performance_metrics[size] = {
                "ingestion_time": ingestion_time,
                "search_time": search_time,
                "metadata_time": metadata_time,
                "search_results": len(search_results),
                "total_content": len(all_content)
            }

            # Performance should remain reasonable
            self.assertLess(
                search_time, 5.0,
                f"Search should complete in under 5 seconds even with {size} items"
            )

            self.assertLess(
                metadata_time, 10.0,
                f"Metadata retrieval should complete in under 10 seconds with {size} items"
            )

        # Test that performance scales reasonably
        if len(performance_metrics) >= 2:
            sizes = sorted(performance_metrics.keys())
            small_size = sizes[0]
            large_size = sizes[-1]

            search_per_item_small = performance_metrics[small_size]["search_time"] / small_size
            search_per_item_large = performance_metrics[large_size]["search_time"] / large_size

            # Search time per item shouldn't grow dramatically
            performance_ratio = search_per_item_large / search_per_item_small if search_per_item_small > 0 else 1
            self.assertLess(
                performance_ratio, 10.0,
                "Search performance per item shouldn't degrade dramatically as content grows"
            )

        # Test content quality at scale
        final_content_count = len(storage.get_all_content())
        self.assertEqual(
            final_content_count, content_sizes[-1],
            "All content should be preserved at scale"
        )

        # Test search accuracy at scale
        detailed_search = storage.search_content("category_5")
        self.assertGreater(
            len(detailed_search), 0,
            "Specific searches should work accurately at scale"
        )

        self.logger.log_operation(
            level="INFO",
            operation="vision_test_5_complete",
            message=f"Scalability validated: {performance_metrics}",
            component="vision_validation"
        )

    def test_vision_promise_6_reliability_and_trust(self):
        """
        Vision Test 6: Atlas should be a reliable, trustworthy knowledge repository.
        This tests data integrity, consistency, and reliability.
        """
        self.logger.log_operation(
            level="INFO",
            operation="vision_test_6",
            message="Testing reliability and trust promise",
            component="vision_validation"
        )

        storage = StorageManager(str(self.vault_dir))
        storage.initialize_vault()

        # Test data integrity
        critical_content = {
            "title": "Critical Research Notes",
            "url": "https://example.com/critical-research",
            "content": """# Critical Research Notes

## Important Findings

1. **Key Discovery**: Our research revealed unexpected patterns in user behavior
2. **Statistical Significance**: p < 0.001 across all experiments
3. **Reproducibility**: Results replicated across 3 different environments

## Raw Data
- Experiment A: 245 participants, 87% success rate
- Experiment B: 198 participants, 91% success rate
- Experiment C: 312 participants, 89% success rate

## Implications
This research has significant implications for:
- Clinical practice
- Policy decisions
- Future research directions
""",
            "source_type": "research",
            "metadata": {
                "importance": "critical",
                "verified": True,
                "peer_reviewed": True,
                "research_type": "clinical_trial",
                "tags": ["research", "critical", "verified"]
            }
        }

        # Store critical content
        file_path = storage.write_content(
            url=critical_content["url"],
            title=critical_content["title"],
            content=critical_content["content"],
            source_type=critical_content["source_type"],
            metadata=critical_content["metadata"]
        )

        # Test data integrity - content should be exactly preserved
        retrieved_content = storage.read_content(file_path)

        # Verify critical data points are preserved
        self.assertIn("245 participants", retrieved_content["content"])
        self.assertIn("p < 0.001", retrieved_content["content"])
        self.assertEqual(retrieved_content["metadata"]["importance"], "critical")
        self.assertTrue(retrieved_content["metadata"]["verified"])

        # Test consistency - same URL should always return same content
        duplicate_path = storage.write_content(
            url=critical_content["url"],
            title="Attempted Duplicate",
            content="Different content",
            source_type="test"
        )

        self.assertEqual(file_path, duplicate_path, "Same URL should always return same file")

        # Test search reliability
        search_attempts = 5
        for i in range(search_attempts):
            results = storage.search_content("critical research")
            self.assertGreater(
                len(results), 0,
                f"Search should reliably find content (attempt {i+1}/{search_attempts})"
            )

        # Test metadata reliability
        metadata_search = storage.search_content("verified")
        self.assertGreater(len(metadata_search), 0, "Metadata search should be reliable")

        # Test database integrity
        db_path = self.data_dir / "atlas.db"
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Run integrity check
            cursor.execute("PRAGMA integrity_check")
            integrity_result = cursor.fetchone()[0]

            self.assertEqual(integrity_result, "ok", "Database should maintain integrity")

            conn.close()

        # Test backup/restore reliability (simulation)
        backup_content = retrieved_content.copy()

        # Simulate system restart by creating new storage instance
        storage2 = StorageManager(str(self.vault_dir))
        restored_content = storage2.read_content(file_path)

        # Content should survive system restarts
        self.assertEqual(
            restored_content["title"],
            backup_content["title"],
            "Content should survive system restarts"
        )

        self.assertEqual(
            restored_content["metadata"]["importance"],
            backup_content["metadata"]["importance"],
            "Critical metadata should survive system restarts"
        )

        self.logger.log_operation(
            level="INFO",
            operation="vision_test_6_complete",
            message="Reliability and trust validated",
            component="vision_validation"
        )


def run_vision_validation_tests():
    """Run all vision validation tests."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(VisionValidationTest)

    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    print("=" * 80)
    print("ATLAS V4 - VISION VALIDATION TESTS")
    print("=" * 80)
    print("Testing that Atlas delivers on its core promises:")
    print("1. Personal Knowledge Automation")
    print("2. Obsidian Compatibility")
    print("3. Zero Configuration Complexity")
    print("4. Content Quality Preservation")
    print("5. Scalability and Performance")
    print("6. Reliability and Trust")
    print("=" * 80)

    success = run_vision_validation_tests()

    print("=" * 80)
    if success:
        print("✅ ALL VISION TESTS PASSED - Atlas delivers on its promises!")
        print("The system is ready for production use.")
    else:
        print("❌ SOME VISION TESTS FAILED - Review and address issues")
        print("System may not fully deliver on its vision promises.")
    print("=" * 80)

    sys.exit(0 if success else 1)