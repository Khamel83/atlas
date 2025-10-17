"""
Integration tests for cognitive features (ask subsystem).

Tests the integration between MetadataManager and all cognitive amplification features.
"""

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta

from ask.insights.pattern_detector import PatternDetector
from ask.proactive.surfacer import ProactiveSurfacer
from ask.recall.recall_engine import RecallEngine
from ask.socratic.question_engine import QuestionEngine
from ask.temporal.temporal_engine import TemporalEngine
from helpers.metadata_manager import (
    ContentMetadata,
    MetadataManager,
    ProcessingStatus,
)


class TestCognitiveFeatures(unittest.TestCase):
    """Integration tests for cognitive amplification features."""

    def setUp(self):
        """Set up test environment with sample data."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = {
            "data_directory": self.temp_dir,
            "document_output_path": os.path.join(self.temp_dir, "documents"),
        }
        self.metadata_manager = MetadataManager(self.config)

        # Create sample metadata files for testing
        self._create_sample_data()

    def tearDown(self):
        """Clean up temporary directory."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_sample_data(self):
        """Create sample metadata files for testing."""
        os.makedirs(os.path.join(self.temp_dir, "documents", "metadata"), exist_ok=True)

        # Create sample metadata items
        sample_items = [
            {
                "uid": "recent_ai_article",
                "content_type": "document",
                "source": "https://example.com/ai-trends-2025",
                "title": "Latest AI Trends in 2025",
                "status": "success",
                "tags": ["AI", "machine-learning", "technology", "2025"],
                "created_at": (datetime.now() - timedelta(days=1)).isoformat(),
                "updated_at": (datetime.now() - timedelta(days=1)).isoformat(),
                "fetch_details": {
                    "attempts": [],
                    "successful_method": "direct",
                    "is_truncated": False,
                    "total_attempts": 1,
                    "fetch_time": 2.3
                },
                "type_specific": {
                    "content": "Comprehensive overview of AI trends in 2025, including LLM advances and automation."
                }
            },
            {
                "uid": "old_tech_article",
                "content_type": "document",
                "source": "https://example.com/old-tech",
                "title": "Technology Overview from 2020",
                "status": "success",
                "tags": ["technology", "history", "2020"],
                "created_at": (datetime.now() - timedelta(days=1800)).isoformat(),  # ~5 years old
                "updated_at": (datetime.now() - timedelta(days=1800)).isoformat(),
                "fetch_details": {
                    "attempts": [],
                    "successful_method": "archive",
                    "is_truncated": False,
                    "total_attempts": 2,
                    "fetch_time": 4.1
                },
                "type_specific": {
                    "content": "Historical overview of technology in 2020.",
                    "last_reviewed": (datetime.now() - timedelta(days=1000)).isoformat()
                }
            },
            {
                "uid": "ml_tutorial",
                "content_type": "document",
                "source": "https://example.com/ml-tutorial",
                "title": "Machine Learning Fundamentals",
                "status": "success",
                "tags": ["machine-learning", "AI", "education", "tutorial"],
                "created_at": (datetime.now() - timedelta(days=2)).isoformat(),
                "updated_at": (datetime.now() - timedelta(days=2)).isoformat(),
                "fetch_details": {
                    "attempts": [],
                    "successful_method": "direct",
                    "is_truncated": False,
                    "total_attempts": 1,
                    "fetch_time": 1.8
                },
                "type_specific": {
                    "content": "Introduction to machine learning concepts and algorithms.",
                    "last_reviewed": (datetime.now() - timedelta(days=90)).isoformat()
                }
            },
            {
                "uid": "pending_item",
                "content_type": "document",
                "source": "https://example.com/pending",
                "title": "Pending Processing Item",
                "status": "pending",
                "tags": [],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "fetch_details": {
                    "attempts": [],
                    "successful_method": None,
                    "is_truncated": False,
                    "total_attempts": 0,
                    "fetch_time": None
                },
                "type_specific": {}
            }
        ]

        # Save metadata files
        for item in sample_items:
            filepath = os.path.join(
                self.temp_dir, "documents", "metadata", f"{item['uid']}.json"
            )
            with open(filepath, 'w') as f:
                json.dump(item, f, indent=2)

    def test_proactive_surfacer_integration(self):
        """Test ProactiveSurfacer with MetadataManager."""
        surfacer = ProactiveSurfacer(self.metadata_manager)
        forgotten_items = surfacer.surface_forgotten_content(n=5)

        # Should return at least the old item
        self.assertGreater(len(forgotten_items), 0)

        # Check that items are ContentMetadata instances
        for item in forgotten_items:
            self.assertIsInstance(item, ContentMetadata)

        # Check that old item is included
        titles = [item.title for item in forgotten_items]
        self.assertIn("Technology Overview from 2020", titles)

    def test_pattern_detector_integration(self):
        """Test PatternDetector with MetadataManager."""
        detector = PatternDetector(self.metadata_manager)
        patterns = detector.find_patterns(n=10)

        # Should return patterns dictionary
        self.assertIsInstance(patterns, dict)
        self.assertIn("top_tags", patterns)
        self.assertIn("top_sources", patterns)

        # Check that common tags are detected
        top_tags = patterns["top_tags"]
        self.assertGreater(len(top_tags), 0)

        # Machine-learning and AI should appear multiple times
        tag_names = [tag[0] for tag in top_tags]
        self.assertIn("machine-learning", tag_names)
        self.assertIn("AI", tag_names)

    def test_temporal_engine_integration(self):
        """Test TemporalEngine with MetadataManager."""
        engine = TemporalEngine(self.metadata_manager)
        relationships = engine.get_time_aware_relationships(max_delta_days=7)

        # Should return relationships between recent items
        self.assertIsInstance(relationships, list)

        # Check relationship structure
        for rel in relationships:
            self.assertEqual(len(rel), 3)  # (item1, item2, days_apart)
            self.assertIsInstance(rel[0], ContentMetadata)
            self.assertIsInstance(rel[1], ContentMetadata)
            self.assertIsInstance(rel[2], int)

    def test_recall_engine_integration(self):
        """Test RecallEngine with MetadataManager."""
        engine = RecallEngine(self.metadata_manager)
        due_items = engine.schedule_spaced_repetition(n=5)

        # Should return items for review
        self.assertIsInstance(due_items, list)

        # Items should be ContentMetadata instances
        for item in due_items:
            self.assertIsInstance(item, ContentMetadata)

        # Items with old last_reviewed should be prioritized
        if len(due_items) > 0:
            titles = [item.title for item in due_items]
            # Old tech article has very old last_reviewed date
            self.assertIn("Machine Learning Fundamentals", titles)

    def test_question_engine_integration(self):
        """Test QuestionEngine generates questions from content."""
        engine = QuestionEngine()

        # Test with sample content
        sample_content = """
        Machine learning is a subset of artificial intelligence that enables
        computers to learn and make decisions without being explicitly programmed.
        Key algorithms include neural networks, decision trees, and support vector machines.
        """

        questions = engine.generate_questions(sample_content)

        # Should generate multiple questions
        self.assertGreater(len(questions), 0)

        # Questions should be strings
        for question in questions:
            self.assertIsInstance(question, str)
            self.assertTrue(len(question) > 10)  # Reasonable question length

    def test_cognitive_features_with_empty_data(self):
        """Test cognitive features handle empty data gracefully."""
        # Create empty metadata manager
        empty_temp_dir = tempfile.mkdtemp()
        empty_config = {
            "data_directory": empty_temp_dir,
            "document_output_path": os.path.join(empty_temp_dir, "documents"),
        }
        empty_manager = MetadataManager(empty_config)

        try:
            # Test each feature with no data
            surfacer = ProactiveSurfacer(empty_manager)
            forgotten = surfacer.surface_forgotten_content(n=5)
            self.assertEqual(len(forgotten), 0)

            detector = PatternDetector(empty_manager)
            patterns = detector.find_patterns(n=5)
            self.assertIsInstance(patterns, dict)
            self.assertEqual(len(patterns.get("top_tags", [])), 0)

            temporal = TemporalEngine(empty_manager)
            relationships = temporal.get_time_aware_relationships(max_delta_days=30)
            self.assertEqual(len(relationships), 0)

            recall = RecallEngine(empty_manager)
            due_items = recall.schedule_spaced_repetition(n=5)
            self.assertEqual(len(due_items), 0)

        finally:
            import shutil
            shutil.rmtree(empty_temp_dir, ignore_errors=True)

    def test_cognitive_features_with_filter_integration(self):
        """Test cognitive features work with status filters."""
        # Test with only successful items
        surfacer = ProactiveSurfacer(self.metadata_manager)

        # Get all metadata and check we have mix of statuses
        all_metadata = self.metadata_manager.get_all_metadata()
        statuses = set(item.status for item in all_metadata)
        self.assertIn(ProcessingStatus.SUCCESS, statuses)
        self.assertIn(ProcessingStatus.PENDING, statuses)

        # Cognitive features should handle mixed statuses appropriately
        forgotten = surfacer.surface_forgotten_content(n=10)

        # Should only return successful items (pending items shouldn't be surfaced)
        for item in forgotten:
            self.assertEqual(item.status, ProcessingStatus.SUCCESS)

    def test_end_to_end_cognitive_workflow(self):
        """Test complete cognitive amplification workflow."""
        # 1. Surface forgotten content
        surfacer = ProactiveSurfacer(self.metadata_manager)
        forgotten = surfacer.surface_forgotten_content(n=5)

        # 2. Analyze patterns
        detector = PatternDetector(self.metadata_manager)
        patterns = detector.find_patterns(n=5)

        # 3. Find temporal relationships
        temporal = TemporalEngine(self.metadata_manager)
        relationships = temporal.get_time_aware_relationships(max_delta_days=30)

        # 4. Schedule recall
        recall = RecallEngine(self.metadata_manager)
        due_items = recall.schedule_spaced_repetition(n=5)

        # 5. Generate questions for forgotten content
        if forgotten:
            question_engine = QuestionEngine()
            sample_item = forgotten[0]
            content = sample_item.type_specific.get("content", sample_item.title)
            questions = question_engine.generate_questions(content)

            self.assertGreater(len(questions), 0)

        # Verify all components returned reasonable results
        self.assertTrue(isinstance(forgotten, list))
        self.assertTrue(isinstance(patterns, dict))
        self.assertTrue(isinstance(relationships, list))
        self.assertTrue(isinstance(due_items, list))


if __name__ == "__main__":
    unittest.main()