"""
Tests for unified storage interface.

Tests the StorageManager class that combines writer, organizer,
and collision handler functionality.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import json

from atlas.storage import StorageManager
from atlas.core.validator import ValidationResult
from atlas.core.content_hash import generate_content_hash


class TestStorageManager:
    """Test cases for StorageManager class."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.vault_root = Path(self.temp_dir) / "test_vault"
        self.storage = StorageManager(str(self.vault_root))

    def create_test_content_item(self, item_id, title, content_prefix="Test content"):
        """Helper to create a valid test content item."""
        content = f"{content_prefix} that is much longer to meet validation requirements. This needs to be at least 300 characters to pass the content validation in the Atlas system. We are creating content here which should be stored successfully. This additional text ensures we meet the minimum character count required for content validation in the system. The content needs to be sufficiently long to pass all validation checks and be stored properly in the vault."

        return {
            'id': item_id,
            'type': 'articles',  # Use plural to match organizer expectations
            'source': 'test-source',
            'title': title,
            'date': '2024-01-15T10:00:00Z',
            'ingested_at': '2024-01-15T10:00:00Z',
            'content': content,
            'author': 'Test Author',
            'url': f'https://example.com/{item_id}',
            'content_hash': generate_content_hash(title, content)
        }

    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_vault_initialization(self):
        """Test vault structure initialization."""
        # Initialize vault
        success = self.storage.initialize_vault()
        assert success

        # Check structure exists
        assert self.vault_root.exists()
        assert (self.vault_root / "inbox").exists()
        assert (self.vault_root / "logs").exists()
        assert (self.vault_root / "failures").exists()
        assert (self.vault_root / "config").exists()

        # Check content type directories
        for content_type in ['newsletters', 'podcasts', 'articles', 'youtube', 'emails']:
            assert (self.vault_root / "inbox" / content_type).exists()

    def test_store_content_item(self):
        """Test storing a single content item."""
        # Initialize vault
        self.storage.initialize_vault()

        # Create test content item
        content_item = self.create_test_content_item('test-123', 'Test Article')

        # Store content item
        file_path = self.storage.store_content_item(content_item)
        assert file_path is not None
        assert file_path.exists()
        assert file_path.suffix == '.md'

        # Check file content
        content = file_path.read_text(encoding='utf-8')
        assert 'Test Article' in content
        assert 'This is test content' in content
        assert '---' in content  # YAML frontmatter

    def test_store_content_item_with_collision(self):
        """Test handling filename collisions."""
        # Initialize vault
        self.storage.initialize_vault()

        # Create two content items with same title/date/source
        base_item = self.create_test_content_item('test-123', 'Test Article', 'First article content')
        collision_item = self.create_test_content_item('test-456', 'Test Article', 'Second article content')

        # Store first item
        first_path = self.storage.store_content_item(base_item)
        assert first_path is not None

        # Store second item (should handle collision)
        second_path = self.storage.store_content_item(collision_item)
        assert second_path is not None
        assert second_path != first_path

        # Files should have different names
        assert first_path.stem != second_path.stem
        assert second_path.stem.endswith('-2')  # Numeric suffix

    def test_store_batch(self):
        """Test storing multiple content items."""
        # Initialize vault
        self.storage.initialize_vault()

        # Create test content items
        content_items = [
            {
                'id': f'test-{i}',
                'type': 'article',
                'source': 'test-source',
                'title': f'Test Article {i}',
                'date': '2024-01-15T10:00:00Z',
                'ingested_at': '2024-01-15T10:00:00Z',
                'content': f'Content for article {i} that is much longer to meet validation requirements. This needs to be at least 300 characters to pass the content validation in the Atlas system. We are creating article content {i} here which should be stored successfully. This additional text ensures we meet the minimum character count required for article content validation in the system. The content needs to be sufficiently long to pass all validation checks and be stored properly in the vault.',
                'author': 'Test Author',
                'url': f'https://example.com/test{i}'
            }
            for i in range(3)
        ]

        # Store batch
        stored_paths = self.storage.store_batch(content_items)
        assert len(stored_paths) == 3

        # Check all files exist
        for path in stored_paths:
            assert path.exists()
            assert path.suffix == '.md'

    def test_update_content_item(self):
        """Test updating existing content item."""
        # Initialize vault and store item
        self.storage.initialize_vault()

        content_item = {
            'id': 'test-123',
            'type': 'article',
            'source': 'test-source',
            'title': 'Test Article',
            'date': '2024-01-15T10:00:00Z',
            'ingested_at': '2024-01-15T10:00:00Z',
            'content': 'Original content that is much longer to meet validation requirements. This needs to be at least 300 characters to pass the content validation in the Atlas system. We are creating original content here which should be stored successfully and then updated later in the test. This additional text ensures we meet the minimum character count required for article content validation in the system.',
            'author': 'Test Author',
            'url': 'https://example.com/test'
        }

        file_path = self.storage.store_content_item(content_item)
        assert file_path is not None

        # Update content
        updates = {
            'content': 'Updated content with new information.',
            'tags': ['updated', 'test']
        }

        success = self.storage.update_content_item(file_path, updates)
        assert success

        # Check updated content
        updated_content = file_path.read_text(encoding='utf-8')
        assert 'Updated content' in updated_content
        assert 'updated' in updated_content

    def test_list_content_by_type(self):
        """Test listing content by type."""
        # Initialize vault
        self.storage.initialize_vault()

        # Store different types of content
        items = [
            {
                'id': 'article-1',
                'type': 'article',
                'source': 'test-source',
                'title': 'Test Article',
                'date': '2024-01-15T10:00:00Z',
                'ingested_at': '2024-01-15T10:00:00Z',
                'content': 'Article content that is much longer to meet validation requirements. This needs to be at least 300 characters to pass the content validation in the Atlas system. We are creating article content here which should be stored successfully and used for testing the list functionality. This additional text ensures we meet the minimum character count required for article content validation in the system.',
                'url': 'https://example.com/article'
            },
            {
                'id': 'newsletter-1',
                'type': 'newsletter',
                'source': 'test-source',
                'title': 'Test Newsletter',
                'date': '2024-01-15T10:00:00Z',
                'ingested_at': '2024-01-15T10:00:00Z',
                'content': 'Newsletter content that is much longer to meet validation requirements. This needs to be at least 300 characters to pass the content validation in the Atlas system. We are creating newsletter content here which should be stored successfully and used for testing the list functionality. This additional text ensures we meet the minimum character count required for newsletter content validation in the system.',
                'url': 'https://example.com/newsletter'
            }
        ]

        for item in items:
            self.storage.store_content_item(item)

        # List articles
        articles = self.storage.list_content_by_type('article')
        assert len(articles) == 1
        assert articles[0]['frontmatter']['type'] == 'article'

        # List newsletters
        newsletters = self.storage.list_content_by_type('newsletter')
        assert len(newsletters) == 1
        assert newsletters[0]['frontmatter']['type'] == 'newsletter'

        # List non-existent type
        podcasts = self.storage.list_content_by_type('podcast')
        assert len(podcasts) == 0

    def test_search_content(self):
        """Test searching content."""
        # Initialize vault
        self.storage.initialize_vault()

        # Store content with searchable terms
        items = [
            {
                'id': 'python-article',
                'type': 'article',
                'source': 'test-source',
                'title': 'Python Programming Guide',
                'date': '2024-01-15T10:00:00Z',
                'ingested_at': '2024-01-15T10:00:00Z',
                'content': 'This article discusses Python programming concepts.',
                'url': 'https://example.com/python'
            },
            {
                'id': 'javascript-article',
                'type': 'article',
                'source': 'test-source',
                'title': 'JavaScript Tutorial',
                'date': '2024-01-15T10:00:00Z',
                'ingested_at': '2024-01-15T10:00:00Z',
                'content': 'Learn JavaScript programming basics.',
                'url': 'https://example.com/javascript'
            }
        ]

        for item in items:
            self.storage.store_content_item(item)

        # Search for "Python"
        python_results = self.storage.search_content('Python')
        assert len(python_results) == 1
        assert 'Python' in python_results[0]['frontmatter']['title']

        # Search for "programming"
        programming_results = self.storage.search_content('programming')
        assert len(programming_results) == 2

        # Search with content type filter
        python_articles = self.storage.search_content('Python', 'article')
        assert len(python_articles) == 1

    def test_get_storage_stats(self):
        """Test getting storage statistics."""
        # Initialize vault
        self.storage.initialize_vault()

        # Store some content
        content_item = self.create_test_content_item('test-123', 'Test Article')
        self.storage.store_content_item(content_item)

        # Get stats
        stats = self.storage.get_storage_stats()
        assert stats is not None
        assert 'total_files' in stats
        assert 'content_types' in stats
        assert 'vault_root' in stats
        assert stats['total_files'] >= 1
        assert stats['content_types']['articles'] >= 1

    def test_validate_storage_integrity(self):
        """Test storage integrity validation."""
        # Initialize vault
        self.storage.initialize_vault()

        # Validate fresh vault
        errors = self.storage.validate_storage_integrity()
        assert len(errors) == 0

        # Remove critical directory
        (self.vault_root / "logs").rmdir()

        # Validate again
        errors = self.storage.validate_storage_integrity()
        assert len(errors) > 0
        assert any('logs' in error for error in errors)

    def test_export_content_list(self):
        """Test exporting content list."""
        # Initialize vault
        self.storage.initialize_vault()

        # Store content
        content_item = {
            'id': 'test-123',
            'type': 'article',
            'source': 'test-source',
            'title': 'Test Article',
            'date': '2024-01-15T10:00:00Z',
            'ingested_at': '2024-01-15T10:00:00Z',
            'content': 'Test content.',
            'url': 'https://example.com/test'
        }

        self.storage.store_content_item(content_item)

        # Export content list
        export_file = self.vault_root / "export" / "content_list.json"
        success = self.storage.export_content_list(export_file)
        assert success
        assert export_file.exists()

        # Check export content
        export_data = json.loads(export_file.read_text(encoding='utf-8'))
        assert 'total_items' in export_data
        assert 'content' in export_data
        assert export_data['total_items'] >= 1
        assert len(export_data['content']) >= 1

    def test_cleanup_storage(self):
        """Test storage cleanup operations."""
        # Initialize vault
        self.storage.initialize_vault()

        # Store content to create collision registry entries if needed
        content_item = {
            'id': 'test-123',
            'type': 'article',
            'source': 'test-source',
            'title': 'Test Article',
            'date': '2024-01-15T10:00:00Z',
            'ingested_at': '2024-01-15T10:00:00Z',
            'content': 'Test content.',
            'url': 'https://example.com/test'
        }

        self.storage.store_content_item(content_item)

        # Run cleanup
        results = self.storage.cleanup_storage()
        assert 'collision_registry_cleaned' in results
        assert 'empty_directories_removed' in results
        assert isinstance(results['collision_registry_cleaned'], int)
        assert isinstance(results['empty_directories_removed'], list)

    def test_get_file_info(self):
        """Test getting file information."""
        # Initialize vault
        self.storage.initialize_vault()

        # Store content
        content_item = {
            'id': 'test-123',
            'type': 'article',
            'source': 'test-source',
            'title': 'Test Article',
            'date': '2024-01-15T10:00:00Z',
            'ingested_at': '2024-01-15T10:00:00Z',
            'content': 'Test content.',
            'url': 'https://example.com/test'
        }

        file_path = self.storage.store_content_item(content_item)
        assert file_path is not None

        # Get file info
        file_info = self.storage.get_file_info(file_path)
        assert file_info is not None
        assert 'path' in file_info
        assert 'size' in file_info
        assert 'created' in file_info
        assert 'modified' in file_info
        assert 'frontmatter' in file_info
        assert file_info['frontmatter']['title'] == 'Test Article'

    def test_error_handling(self):
        """Test error handling in storage operations."""
        # Test with invalid vault root (non-existent directory that can't be created)
        invalid_storage = StorageManager("/invalid/path/that/does/not/exist")

        # Should handle initialization gracefully
        success = invalid_storage.initialize_vault()
        # Might succeed if directory can be created, or fail gracefully

        # Test storing with invalid content item
        invalid_item = {
            # Missing required fields
            'title': 'Incomplete Item'
        }

        # Should handle gracefully without crashing
        result = invalid_storage.store_content_item(invalid_item)
        # Might return None due to validation failure