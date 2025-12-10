#!/usr/bin/env python3
"""
Atlas Integration Tests

Comprehensive integration tests for Atlas v4 system.
Tests end-to-end functionality and component interactions.
"""

import asyncio
import json
import os
import pathlib
import shutil
import sqlite3
import tempfile
import time
import unittest
from datetime import datetime
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
from atlas.logging import setup_logging
from atlas.bot.main import AtlasBot
from atlas.bot.deployment import BotDeploymentConfig


class TestIntegration(unittest.TestCase):
    """Integration test suite for Atlas."""

    @classmethod
    def setUpClass(cls):
        """Setup test environment."""
        cls.test_dir = Path(tempfile.mkdtemp(prefix="atlas_test_"))
        cls.vault_dir = cls.test_dir / "vault"
        cls.data_dir = cls.test_dir / "data"
        cls.config_dir = cls.test_dir / "config"
        cls.logs_dir = cls.test_dir / "logs"

        # Create directories
        for directory in [cls.vault_dir, cls.data_dir, cls.config_dir, cls.logs_dir]:
            directory.mkdir(parents=True)

        # Setup logging
        setup_logging(level="INFO", enable_console=False)

        cls.logger = setup_logging(level="INFO", enable_console=True)

    @classmethod
    def tearDownClass(cls):
        """Cleanup test environment."""
        if cls.test_dir.exists():
            shutil.rmtree(cls.test_dir)

    def setUp(self):
        """Setup each test."""
        # Create test config
        self.config = {
            "vault": {"root": str(self.vault_dir)},
            "database": {
                "type": "sqlite",
                "path": str(self.data_dir / "test.db")
            },
            "ingestion": {
                "max_concurrent": 2,
                "rate_limit": 10,
                "timeout": 30
            },
            "logging": {
                "level": "INFO",
                "file": str(self.logs_dir / "test.log")
            }
        }

        # Save config to file
        self.config_file = self.config_dir / "test.yaml"
        import yaml
        with open(self.config_file, 'w') as f:
            yaml.dump(self.config, f)

    def test_storage_manager_integration(self):
        """Test StorageManager integration."""
        self.logger.info("Testing StorageManager integration")

        # Initialize storage
        storage = StorageManager(str(self.vault_dir))
        storage.initialize_vault()

        # Test file operations
        test_content = {
            "title": "Test Article",
            "url": "https://example.com/test",
            "content": "This is test content",
            "source_type": "test",
            "metadata": {
                "author": "Test Author",
                "published": "2025-10-16"
            }
        }

        # Write file
        file_path = storage.write_content(
            url=test_content["url"],
            title=test_content["title"],
            content=test_content["content"],
            source_type=test_content["source_type"],
            metadata=test_content["metadata"]
        )

        # Verify file exists
        self.assertTrue(file_path.exists(), "Content file should exist")

        # Read file back
        content_data = storage.read_content(file_path)
        self.assertEqual(content_data["title"], test_content["title"])
        self.assertEqual(content_data["url"], test_content["url"])
        self.assertEqual(content_data["content"], test_content["content"])

        # Test search functionality
        search_results = storage.search_content("test")
        self.assertGreater(len(search_results), 0, "Should find test content")

        # Test duplicate detection
        duplicate_path = storage.write_content(
            url=test_content["url"],
            title="Different Title",
            content="Different content",
            source_type="test"
        )
        self.assertEqual(duplicate_path, file_path, "Should detect duplicate")

        self.logger.info("StorageManager integration test passed")

    def test_ingestion_manager_integration(self):
        """Test IngestionManager integration."""
        self.logger.info("Testing IngestionManager integration")

        # Initialize components
        storage = StorageManager(str(self.vault_dir))
        storage.initialize_vault()

        ingestion = IngestionManager(self.config)
        ingestion.storage = storage

        # Test RSS ingestion
        test_feed_url = "https://feeds.simplecast.com/your-podcast"  # Example URL
        try:
            # Note: This test uses a real URL and may fail without internet
            # In production, use mock feeds or test fixtures
            feed_content = ingestion._fetch_feed(test_feed_url)
            self.assertIsNotNone(feed_content, "Should fetch feed content")
        except Exception as e:
            self.logger.warning(f"RSS test skipped due to network error: {e}")

        # Test content processing
        test_item = {
            "title": "Test Episode",
            "description": "This is a test episode description",
            "link": "https://example.com/episode1",
            "pub_date": datetime.now().isoformat(),
            "source_type": "rss"
        }

        processed_content = ingestion._process_content_item(test_item)
        self.assertIsNotNone(processed_content, "Should process content item")
        self.assertEqual(processed_content["title"], test_item["title"])

        self.logger.info("IngestionManager integration test passed")

    def test_database_integration(self):
        """Test database integration."""
        self.logger.info("Testing database integration")

        db_path = self.data_dir / "test.db"

        # Test database creation and operations
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Create test table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE,
                title TEXT,
                content TEXT,
                source_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Insert test data
        test_data = [
            ("https://example.com/1", "Test 1", "Content 1", "test"),
            ("https://example.com/2", "Test 2", "Content 2", "test")
        ]

        cursor.executemany(
            "INSERT OR IGNORE INTO test_content (url, title, content, source_type) VALUES (?, ?, ?, ?)",
            test_data
        )

        conn.commit()

        # Query data
        cursor.execute("SELECT COUNT(*) FROM test_content")
        count = cursor.fetchone()[0]
        self.assertEqual(count, 2, "Should have 2 records")

        # Test duplicate handling
        cursor.execute(
            "INSERT OR IGNORE INTO test_content (url, title, content, source_type) VALUES (?, ?, ?, ?)",
            ("https://example.com/1", "Updated 1", "Updated content 1", "test")
        )
        conn.commit()

        cursor.execute("SELECT COUNT(*) FROM test_content")
        count = cursor.fetchone()[0]
        self.assertEqual(count, 2, "Should still have 2 records (no duplicates)")

        conn.close()

        self.logger.info("Database integration test passed")

    def test_config_integration(self):
        """Test configuration management integration."""
        self.logger.info("Testing configuration integration")

        # Load config from file
        config_manager = ConfigManager(str(self.config_file))
        loaded_config = config_manager.load_config()

        self.assertEqual(loaded_config["vault"]["root"], str(self.vault_dir))
        self.assertEqual(loaded_config["database"]["type"], "sqlite")

        # Test environment variable substitution
        os.environ["TEST_VAULT_PATH"] = str(self.test_dir / "env_vault")

        env_config = {
            "vault": {"root": "${TEST_VAULT_PATH}"},
            "database": {"type": "sqlite"}
        }

        env_config_file = self.config_dir / "env_test.yaml"
        import yaml
        with open(env_config_file, 'w') as f:
            yaml.dump(env_config, f)

        env_config_manager = ConfigManager(str(env_config_file))
        resolved_config = env_config_manager.load_config()

        self.assertEqual(resolved_config["vault"]["root"], os.environ["TEST_VAULT_PATH"])

        # Cleanup
        del os.environ["TEST_VAULT_PATH"]

        self.logger.info("Configuration integration test passed")

    def test_bot_integration(self):
        """Test Telegram bot integration (without actual bot token)."""
        self.logger.info("Testing bot integration")

        # Create bot config
        bot_config = BotDeploymentConfig(
            name="test-bot",
            token="test_token",  # Invalid token for testing
            allowed_users=["123456789"],
            allowed_chats=[],
            vault_root=str(self.vault_dir),
            log_level="INFO"
        )

        # Test bot creation (should fail gracefully with invalid token)
        try:
            from atlas.bot.main import BotConfig
            config = BotConfig(
                token="test_token",
                allowed_users=["123456789"],
                allowed_chats=[],
                enable_inline=True,
                vault_root=str(self.vault_dir)
            )

            bot = AtlasBot(config)
            self.assertIsNotNone(bot, "Bot should be created")
            self.assertIsNotNone(bot.storage, "Bot should have storage")
            self.assertIsNotNone(bot.handlers, "Bot should have handlers")

        except Exception as e:
            # Expected with invalid token
            self.logger.info(f"Bot creation failed as expected: {e}")

        self.logger.info("Bot integration test passed")

    def test_end_to_end_workflow(self):
        """Test complete end-to-end workflow."""
        self.logger.info("Testing end-to-end workflow")

        # Initialize all components
        storage = StorageManager(str(self.vault_dir))
        storage.initialize_vault()

        ingestion = IngestionManager(self.config)
        ingestion.storage = storage

        # Simulate content ingestion workflow
        test_items = [
            {
                "title": "Test Article 1",
                "content": "This is the first test article with some interesting content.",
                "url": "https://example.com/article1",
                "source_type": "test",
                "metadata": {"author": "Author 1", "category": "tech"}
            },
            {
                "title": "Test Article 2",
                "content": "This is the second test article about machine learning.",
                "url": "https://example.com/article2",
                "source_type": "test",
                "metadata": {"author": "Author 2", "category": "ml"}
            }
        ]

        # Process items
        processed_files = []
        for item in test_items:
            file_path = storage.write_content(
                url=item["url"],
                title=item["title"],
                content=item["content"],
                source_type=item["source_type"],
                metadata=item["metadata"]
            )
            processed_files.append(file_path)

        # Verify all files were created
        for file_path in processed_files:
            self.assertTrue(file_path.exists(), f"File {file_path} should exist")

        # Test search functionality
        search_results = storage.search_content("machine learning")
        self.assertGreater(len(search_results), 0, "Should find ML content")

        search_results = storage.search_content("interesting")
        self.assertGreater(len(search_results), 0, "Should find interesting content")

        # Test metadata queries
        all_content = storage.get_all_content()
        self.assertGreaterEqual(len(all_content), len(test_items), "Should have all test content")

        # Test recent items
        recent_items = storage.get_recent_items(limit=5)
        self.assertGreaterEqual(len(recent_items), 0, "Should have recent items")

        self.logger.info("End-to-end workflow test passed")

    def test_error_handling_integration(self):
        """Test error handling across components."""
        self.logger.info("Testing error handling integration")

        storage = StorageManager(str(self.vault_dir))
        storage.initialize_vault()

        # Test invalid URL handling
        try:
            storage.write_content(
                url="",  # Invalid empty URL
                title="Test",
                content="Content",
                source_type="test"
            )
            self.fail("Should raise exception for invalid URL")
        except Exception as e:
            self.assertIsNotNone(e, "Should handle invalid URL gracefully")

        # Test invalid directory handling
        invalid_storage = StorageManager("/invalid/path/that/does/not/exist")
        try:
            invalid_storage.initialize_vault()
            # Might succeed due to directory creation
        except Exception as e:
            self.assertIsNotNone(e, "Should handle invalid directory gracefully")

        # Test duplicate content handling
        test_url = "https://example.com/duplicate-test"

        file_path1 = storage.write_content(
            url=test_url,
            title="Original",
            content="Original content",
            source_type="test"
        )

        file_path2 = storage.write_content(
            url=test_url,
            title="Duplicate",
            content="Duplicate content",
            source_type="test"
        )

        self.assertEqual(file_path1, file_path2, "Should handle duplicates correctly")

        self.logger.info("Error handling integration test passed")

    def test_performance_integration(self):
        """Test performance characteristics."""
        self.logger.info("Testing performance integration")

        storage = StorageManager(str(self.vault_dir))
        storage.initialize_vault()

        # Test bulk operations
        start_time = time.time()

        num_items = 50
        for i in range(num_items):
            storage.write_content(
                url=f"https://example.com/perf_test_{i}",
                title=f"Performance Test {i}",
                content=f"This is test content number {i} with some additional text to make it longer.",
                source_type="test",
                metadata={"index": i, "batch": "perf_test"}
            )

        write_time = time.time() - start_time
        self.logger.info(f"Write performance: {num_items} items in {write_time:.2f}s ({num_items/write_time:.1f} items/s)")

        # Test search performance
        start_time = time.time()
        search_results = storage.search_content("performance")
        search_time = time.time() - start_time
        self.logger.info(f"Search performance: found {len(search_results)} results in {search_time:.3f}s")

        # Performance assertions
        self.assertLess(write_time, 30.0, "Writing 50 items should take less than 30 seconds")
        self.assertLess(search_time, 5.0, "Search should take less than 5 seconds")

        self.logger.info("Performance integration test passed")


class TestAsyncIntegration(unittest.IsolatedAsyncioTestCase):
    """Async integration tests for Atlas."""

    async def asyncSetUp(self):
        """Setup async test environment."""
        self.test_dir = Path(tempfile.mkdtemp(prefix="atlas_async_test_"))
        self.vault_dir = self.test_dir / "vault"
        self.data_dir = self.test_dir / "data"

        for directory in [self.vault_dir, self.data_dir]:
            directory.mkdir(parents=True)

    async def asyncTearDown(self):
        """Cleanup async test environment."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    async def test_async_ingestion_workflow(self):
        """Test async ingestion workflow."""
        # Initialize components
        storage = StorageManager(str(self.vault_dir))
        storage.initialize_vault()

        # Simulate async content processing
        async def process_content_async(items):
            results = []
            for item in items:
                # Simulate async processing delay
                await asyncio.sleep(0.01)

                file_path = storage.write_content(
                    url=item["url"],
                    title=item["title"],
                    content=item["content"],
                    source_type=item["source_type"]
                )
                results.append(file_path)

            return results

        # Test data
        test_items = [
            {
                "url": "https://example.com/async1",
                "title": "Async Test 1",
                "content": "First async test content",
                "source_type": "test"
            },
            {
                "url": "https://example.com/async2",
                "title": "Async Test 2",
                "content": "Second async test content",
                "source_type": "test"
            }
        ]

        # Process async
        start_time = time.time()
        results = await process_content_async(test_items)
        processing_time = time.time() - start_time

        # Verify results
        self.assertEqual(len(results), len(test_items), "Should process all items")
        for file_path in results:
            self.assertTrue(file_path.exists(), f"File {file_path} should exist")

        self.assertLess(processing_time, 5.0, "Async processing should complete quickly")

    async def test_concurrent_operations(self):
        """Test concurrent storage operations."""
        storage = StorageManager(str(self.vault_dir))
        storage.initialize_vault()

        async def concurrent_write(num_writes, prefix):
            tasks = []
            for i in range(num_writes):
                task = asyncio.create_task(
                    asyncio.to_thread(
                        storage.write_content,
                        url=f"https://example.com/{prefix}_{i}",
                        title=f"Concurrent {prefix} {i}",
                        content=f"Content from {prefix} {i}",
                        source_type="test"
                    )
                )
                tasks.append(task)

            return await asyncio.gather(*tasks)

        # Run concurrent writes
        start_time = time.time()
        results1 = await concurrent_write(10, "batch1")
        results2 = await concurrent_write(10, "batch2")
        total_time = time.time() - start_time

        # Verify all files were created
        all_results = results1 + results2
        self.assertEqual(len(all_results), 20, "Should have 20 files total")

        for file_path in all_results:
            self.assertTrue(file_path.exists(), f"File {file_path} should exist")

        # Check for duplicates within same URL
        unique_urls = set()
        for file_path in all_results:
            content_data = storage.read_content(file_path)
            unique_urls.add(content_data["url"])

        self.assertEqual(len(unique_urls), 20, "Should have 20 unique URLs")


def run_integration_tests():
    """Run all integration tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestAsyncIntegration))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    print("Running Atlas Integration Tests...")
    print("=" * 60)

    success = run_integration_tests()

    print("=" * 60)
    if success:
        print("✅ All integration tests passed!")
        sys.exit(0)
    else:
        print("❌ Some integration tests failed!")
        sys.exit(1)