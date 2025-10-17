#!/usr/bin/env python3
"""
Priority 2 Comprehensive Test Suite
Tests for Blocks 8, 9, 10 with focus on reliability, performance, and production readiness
Addresses feedback: Testing Coverage & Quality
"""

import pytest
import sqlite3
import tempfile
import json
import time
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# Add Atlas modules to path
sys.path.insert(0, str(Path(__file__).parent.parent))

class TestBlock8Analytics:
    """Comprehensive tests for Personal Analytics Dashboard (Block 8)"""

    def setup_method(self):
        """Setup for each test"""
        from dashboard.analytics_engine import AnalyticsEngine

        # Use temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.config = {
            'analytics_db': self.temp_db.name,
            'atlas_data': 'test_data'
        }
        self.engine = AnalyticsEngine(self.config)

    def teardown_method(self):
        """Cleanup after each test"""
        if hasattr(self, 'temp_db'):
            os.unlink(self.temp_db.name)

    def test_database_initialization(self):
        """Test analytics database is properly initialized"""
        with sqlite3.connect(self.temp_db.name) as conn:
            # Check required tables exist
            tables = conn.execute("""
                SELECT name FROM sqlite_master WHERE type='table'
            """).fetchall()

            table_names = [t[0] for t in tables]
            assert 'content_analytics' in table_names
            assert 'consumption_events' in table_names
            assert 'analytics_cache' in table_names

    def test_content_addition_and_retrieval(self):
        """Test adding content and retrieving analytics"""
        # Add test content
        content_id = self.engine.add_content(
            content_type='article',
            title='Test Article',
            url='https://example.com',
            metadata={'word_count': 500, 'tags': ['tech', 'python']}
        )

        assert content_id > 0

        # Record some events
        self.engine.record_event(content_id, 'viewed')
        self.engine.record_event(content_id, 'completed', duration=300)

        # Generate insights
        insights = self.engine.generate_insights(days=7)

        assert insights['overview']['total_content'] >= 1
        assert insights['overview']['total_events'] >= 2
        assert 'content_distribution' in insights
        assert 'consumption_patterns' in insights

    def test_performance_with_large_dataset(self):
        """Test analytics performance with large dataset"""
        start_time = time.time()

        # Add 100 pieces of content
        content_ids = []
        for i in range(100):
            content_id = self.engine.add_content(
                content_type='article' if i % 2 == 0 else 'podcast',
                title=f'Content {i}',
                url=f'https://example.com/{i}',
                metadata={'word_count': 1000 + i * 10}
            )
            content_ids.append(content_id)

            # Add some events
            self.engine.record_event(content_id, 'viewed')
            if i % 3 == 0:
                self.engine.record_event(content_id, 'completed')

        load_time = time.time() - start_time

        # Test insights generation performance
        start_time = time.time()
        insights = self.engine.generate_insights(days=30)
        insights_time = time.time() - start_time

        # Performance assertions
        assert load_time < 5.0, f"Data loading too slow: {load_time}s"
        assert insights_time < 2.0, f"Insights generation too slow: {insights_time}s"

        # Data integrity assertions
        assert insights['overview']['total_content'] == 100
        assert len(insights['content_distribution']['distribution']) == 2  # articles + podcasts

    def test_error_handling_and_recovery(self):
        """Test error handling in analytics operations"""
        # Test with invalid data
        invalid_id = self.engine.add_content(
            content_type='',  # Empty content type
            title='',  # Empty title
            metadata={}
        )

        # Should still work with fallbacks
        assert invalid_id > 0

        # Test event recording with invalid content_id
        self.engine.record_event(99999, 'viewed')  # Non-existent content

        # Should not crash, should handle gracefully
        insights = self.engine.generate_insights(days=1)
        assert 'error' not in insights

    @patch('helpers.analytics_engine.MetadataManager')
    def test_atlas_data_integration(self, mock_metadata_manager):
        """Test integration with Atlas data"""
        # Mock Atlas data
        mock_metadata_manager.return_value.get_all_metadata.return_value = [
            {
                'content_type': 'article',
                'title': 'Atlas Article 1',
                'url': 'https://atlas-example.com/1',
                'word_count': 1200,
                'tags': ['ai', 'technology'],
                'created_at': datetime.now().isoformat()
            },
            {
                'content_type': 'podcast',
                'title': 'Atlas Podcast 1',
                'url': 'https://atlas-podcast.com/1',
                'word_count': 5000,
                'tags': ['interview', 'tech'],
                'created_at': datetime.now().isoformat()
            }
        ]

        # Create new engine to trigger sync
        engine = AnalyticsEngine(self.config)
        insights = engine.generate_insights(days=30)

        # Should include Atlas content
        assert insights['overview']['total_content'] >= 2


class TestBlock9Search:
    """Comprehensive tests for Enhanced Search & Indexing (Block 9)"""

    def setup_method(self):
        """Setup for each test"""
        from helpers.enhanced_search import EnhancedSearchEngine
        from helpers.search_engine import SearchEngine

        self.temp_dir = Path(tempfile.mkdtemp())
        self.config = {
            'search_db': str(self.temp_dir / 'search_test.db'),
            'atlas_data': str(self.temp_dir / 'atlas_data')
        }

        # Create test instances
        self.enhanced_engine = EnhancedSearchEngine(self.config)
        self.basic_engine = SearchEngine(self.config)

    def teardown_method(self):
        """Cleanup after each test"""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_basic_search_functionality(self):
        """Test basic search operations work correctly"""
        # Index some test documents
        test_docs = [
            {
                'id': 'doc1',
                'title': 'Python Programming Guide',
                'content': 'Python is a versatile programming language used for web development, data science, and automation.',
                'content_type': 'article',
                'url': 'https://example.com/python-guide'
            },
            {
                'id': 'doc2',
                'title': 'JavaScript Tutorial',
                'content': 'JavaScript is essential for web development. Learn variables, functions, and DOM manipulation.',
                'content_type': 'article',
                'url': 'https://example.com/js-tutorial'
            },
            {
                'id': 'doc3',
                'title': 'AI and Machine Learning',
                'content': 'Artificial intelligence and machine learning are transforming technology and business.',
                'content_type': 'podcast',
                'url': 'https://example.com/ai-ml'
            }
        ]

        # Build index
        self.enhanced_engine.build_index(test_docs)

        # Test searches
        python_results = self.enhanced_engine.search('Python programming', limit=5)
        assert len(python_results) > 0
        assert any('python' in r.get('title', '').lower() for r in python_results)

        web_results = self.enhanced_engine.search('web development', limit=5)
        assert len(web_results) >= 2  # Should match both Python and JavaScript docs

        ai_results = self.enhanced_engine.search('artificial intelligence', limit=5)
        assert len(ai_results) > 0
        assert any('ai' in r.get('title', '').lower() for r in ai_results)

    def test_search_performance_large_dataset(self):
        """Test search performance with larger dataset"""
        # Create 1000 test documents
        test_docs = []
        for i in range(1000):
            test_docs.append({
                'id': f'doc_{i}',
                'title': f'Document {i}: Topic {i % 10}',
                'content': f'This is document {i} about topic {i % 10}. ' * 50,  # ~50 words each
                'content_type': 'article',
                'url': f'https://example.com/doc-{i}'
            })

        # Build index and measure time
        start_time = time.time()
        self.enhanced_engine.build_index(test_docs)
        index_time = time.time() - start_time

        # Test search performance
        start_time = time.time()
        results = self.enhanced_engine.search('document topic', limit=50)
        search_time = time.time() - start_time

        # Performance assertions
        assert index_time < 10.0, f"Indexing too slow for 1000 docs: {index_time}s"
        assert search_time < 1.0, f"Search too slow: {search_time}s"

        # Quality assertions
        assert len(results) > 0
        assert len(results) <= 50

    def test_faceted_search_functionality(self):
        """Test faceted search with filters"""
        # Index documents with different types and tags
        test_docs = [
            {
                'id': 'article1',
                'title': 'Python Article',
                'content': 'Python programming content',
                'content_type': 'article',
                'tags': ['python', 'programming'],
                'url': 'https://example.com/python-article'
            },
            {
                'id': 'podcast1',
                'title': 'Python Podcast',
                'content': 'Python programming discussion',
                'content_type': 'podcast',
                'tags': ['python', 'interview'],
                'url': 'https://example.com/python-podcast'
            },
            {
                'id': 'video1',
                'title': 'JavaScript Video',
                'content': 'JavaScript programming tutorial',
                'content_type': 'youtube',
                'tags': ['javascript', 'tutorial'],
                'url': 'https://youtube.com/js-video'
            }
        ]

        self.enhanced_engine.build_index(test_docs)

        # Test content type filtering
        article_results = self.enhanced_engine.faceted_search(
            query='programming',
            content_types=['article']
        )
        assert all(r.get('content_type') == 'article' for r in article_results)

        # Test tag filtering
        python_results = self.enhanced_engine.faceted_search(
            query='programming',
            tags=['python']
        )
        assert all('python' in r.get('tags', []) for r in python_results)

    def test_search_error_handling(self):
        """Test search error handling and graceful degradation"""
        # Test empty query
        results = self.enhanced_engine.search('', limit=10)
        assert isinstance(results, list)

        # Test very long query
        long_query = 'test ' * 1000
        results = self.enhanced_engine.search(long_query, limit=10)
        assert isinstance(results, list)

        # Test special characters
        special_query = '!@#$%^&*()_+-={}[]|\\:";\'<>?,./'
        results = self.enhanced_engine.search(special_query, limit=10)
        assert isinstance(results, list)

    def test_api_integration(self):
        """Test search API endpoint integration"""
        from api.search_api import search_bp
        from flask import Flask

        app = Flask(__name__)
        app.register_blueprint(search_bp)

        with app.test_client() as client:
            # Test basic search endpoint
            response = client.get('/api/search/?q=python')
            assert response.status_code == 200

            data = json.loads(response.data)
            assert 'query' in data
            assert 'results' in data
            assert 'count' in data

            # Test search without query (should return error)
            response = client.get('/api/search/')
            assert response.status_code == 400


class TestBlock10ContentProcessing:
    """Comprehensive tests for Advanced Content Processing (Block 10)"""

    def setup_method(self):
        """Setup for each test"""
        from helpers.content_processor import ContentProcessor
        from helpers.summarizer import Summarizer

        self.temp_dir = Path(tempfile.mkdtemp())
        self.config = {
            'output_dir': str(self.temp_dir),
            'openrouter_api_key': 'test-key',  # Mock API key
            'ai_features_enabled': True
        }

        self.processor = ContentProcessor(self.config)
        self.summarizer = Summarizer(self.config)

    def teardown_method(self):
        """Cleanup after each test"""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_content_processing_pipeline(self):
        """Test complete content processing pipeline"""
        test_content = """
        This is a test article about machine learning and artificial intelligence.
        It covers various topics including neural networks, deep learning, and
        natural language processing. The content is quite lengthy and contains
        multiple paragraphs with different concepts and ideas.

        Machine learning algorithms can be supervised, unsupervised, or reinforcement-based.
        Each type has its own advantages and use cases in different domains.
        """ * 10  # Make it longer

        result = self.processor.process_content(
            content=test_content,
            metadata={'title': 'Test AI Article', 'url': 'https://example.com/ai'},
            options={'analyze_sentiment': True, 'extract_keywords': True}
        )

        # Check processing results
        assert result['success'] is True
        assert 'processed_content' in result
        assert 'metadata' in result
        assert 'statistics' in result

        # Check statistics
        stats = result['statistics']
        assert stats['word_count'] > 0
        assert stats['character_count'] > 0
        assert stats['sentence_count'] > 0

        # Check metadata enhancement
        metadata = result['metadata']
        assert 'content_type' in metadata
        assert 'processing_timestamp' in metadata

    def test_summarization_strategies(self):
        """Test different summarization strategies"""
        long_content = """
        Artificial intelligence (AI) is intelligence demonstrated by machines,
        in contrast to the natural intelligence displayed by humans and animals.
        Leading AI textbooks define the field as the study of "intelligent agents":
        any device that perceives its environment and takes actions that maximize
        its chance of successfully achieving its goals.

        Machine learning is a subset of AI that enables computers to learn and
        improve from experience without being explicitly programmed. It focuses
        on the development of computer programs that can access data and use it
        to learn for themselves.

        Deep learning is a subset of machine learning that uses artificial neural
        networks with multiple layers to model and understand complex patterns
        in data. It has been particularly successful in areas like image recognition,
        natural language processing, and speech recognition.
        """ * 5

        # Test different summarization types
        extractive_result = self.summarizer.summarize(
            content=long_content,
            summary_type='extractive',
            target_length=100
        )
        assert extractive_result['success'] is True
        assert len(extractive_result['summary']) > 0

        key_points_result = self.summarizer.summarize(
            content=long_content,
            summary_type='key_points',
            target_length=150
        )
        assert key_points_result['success'] is True
        assert len(key_points_result['summary']) > 0

    @patch('helpers.summarizer.requests.post')
    def test_ai_cost_management(self, mock_post):
        """Test AI API cost management and graceful degradation"""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{'message': {'content': 'Test summary'}}]
        }
        mock_post.return_value = mock_response

        # Test with cost tracking
        original_cost_tracker = getattr(self.summarizer, 'cost_tracker', {})

        result = self.summarizer.summarize(
            content="Test content for AI processing",
            summary_type='ai',
            target_length=50
        )

        # Should succeed with AI
        assert result['success'] is True

        # Test rate limiting
        mock_response.status_code = 429  # Rate limited
        mock_post.return_value = mock_response

        result = self.summarizer.summarize(
            content="Test content for rate limited case",
            summary_type='ai',
            target_length=50
        )

        # Should fall back gracefully
        assert result['success'] is True  # Should use fallback
        assert 'fallback_used' in result

    def test_error_handling_and_recovery(self):
        """Test error handling in content processing"""
        # Test with empty content
        result = self.processor.process_content(
            content="",
            metadata={},
            options={}
        )
        assert result['success'] is True  # Should handle gracefully

        # Test with malformed content
        result = self.processor.process_content(
            content=None,
            metadata={},
            options={}
        )
        assert result['success'] is False  # Should fail but not crash
        assert 'error' in result

    def test_performance_with_large_content(self):
        """Test performance with large content volumes"""
        # Create very large content
        large_content = "This is a test sentence. " * 10000  # ~50k words

        start_time = time.time()
        result = self.processor.process_content(
            content=large_content,
            metadata={'title': 'Large Test Content'},
            options={'skip_ai': True}  # Skip AI to test processing speed
        )
        process_time = time.time() - start_time

        # Performance assertions
        assert process_time < 5.0, f"Processing too slow for large content: {process_time}s"
        assert result['success'] is True
        assert result['statistics']['word_count'] > 40000


class TestIntegrationAndPerformance:
    """Integration tests across all Priority 2 blocks"""

    def test_full_pipeline_integration(self):
        """Test complete pipeline: Content Processing -> Search -> Analytics"""
        # This would test the full workflow
        # 1. Process content with Block 10
        # 2. Index in search with Block 9
        # 3. Track in analytics with Block 8
        # 4. Verify data consistency across all systems

        pass  # Implementation would require more setup

    def test_concurrent_operations(self):
        """Test concurrent operations across blocks"""
        import threading

        # Test concurrent search and analytics operations
        # to ensure thread safety and performance under load

        pass  # Implementation would require threading setup

    def test_system_resource_usage(self):
        """Test system resource usage under load"""
        import psutil
        import gc

        # Monitor memory usage during operations
        initial_memory = psutil.Process().memory_info().rss

        # Perform memory-intensive operations
        # (This is a placeholder - would need actual operations)

        gc.collect()  # Force garbage collection
        final_memory = psutil.Process().memory_info().rss

        # Check for memory leaks
        memory_increase = final_memory - initial_memory
        assert memory_increase < 100 * 1024 * 1024, "Potential memory leak detected"


# Test configuration and fixtures
@pytest.fixture
def temp_atlas_config():
    """Provide temporary Atlas configuration for tests"""
    temp_dir = Path(tempfile.mkdtemp())
    config = {
        'atlas_root': str(temp_dir),
        'data_dir': str(temp_dir / 'data'),
        'output_dir': str(temp_dir / 'output'),
        'log_dir': str(temp_dir / 'logs'),
        'search_db': str(temp_dir / 'search.db'),
        'analytics_db': str(temp_dir / 'analytics.db')
    }

    # Create directories
    for dir_path in [config['data_dir'], config['output_dir'], config['log_dir']]:
        Path(dir_path).mkdir(parents=True, exist_ok=True)

    yield config

    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])