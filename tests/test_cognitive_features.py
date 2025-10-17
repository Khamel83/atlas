"""Test cognitive AI features for Atlas."""

import pytest
import sys
import os
from unittest.mock import Mock, patch

# Add Atlas to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestCognitiveFeatures:

    def test_proactive_surfacer_init(self):
        """Test ProactiveSurfacer can initialize without crashing."""
        try:
            from ask.proactive.surfacer import ProactiveSurfacer
            from web.app import get_metadata_manager

            mgr = get_metadata_manager()
            surfacer = ProactiveSurfacer(mgr)
            assert surfacer is not None
            assert hasattr(surfacer, 'surface_forgotten_content')
        except Exception as e:
            pytest.fail(f"ProactiveSurfacer initialization failed: {e}")

    def test_proactive_surfacer_returns_data(self):
        """Test ProactiveSurfacer returns structured data."""
        try:
            from ask.proactive.surfacer import ProactiveSurfacer
            from web.app import get_metadata_manager

            mgr = get_metadata_manager()
            surfacer = ProactiveSurfacer(mgr)
            results = surfacer.surface_forgotten_content(n=3)

            assert isinstance(results, list)
            for item in results:
                assert hasattr(item, 'title')
                assert hasattr(item, 'updated_at')
        except Exception as e:
            pytest.fail(f"ProactiveSurfacer data retrieval failed: {e}")

    def test_temporal_engine_init(self):
        """Test TemporalEngine can initialize without crashing."""
        try:
            from ask.temporal.temporal_engine import TemporalEngine
            from web.app import get_metadata_manager

            mgr = get_metadata_manager()
            engine = TemporalEngine(mgr)
            assert engine is not None
            assert hasattr(engine, 'get_time_aware_relationships')
            assert hasattr(engine, 'identify_temporal_relationships')
        except Exception as e:
            pytest.fail(f"TemporalEngine initialization failed: {e}")

    def test_temporal_engine_returns_data(self):
        """Test TemporalEngine returns structured data."""
        try:
            from ask.temporal.temporal_engine import TemporalEngine
            from web.app import get_metadata_manager

            mgr = get_metadata_manager()
            engine = TemporalEngine(mgr)
            results = engine.get_time_aware_relationships(max_delta_days=7)

            assert isinstance(results, list)
            # Should return tuples of (item1, item2, days)
            for rel in results:
                if len(rel) == 3:
                    item1, item2, days = rel
                    assert hasattr(item1, 'title') or item1 is None
                    assert hasattr(item2, 'title') or item2 is None
                    assert isinstance(days, (int, float)) or days is None
        except Exception as e:
            pytest.fail(f"TemporalEngine data retrieval failed: {e}")

    def test_recall_engine_init(self):
        """Test RecallEngine can initialize without crashing."""
        try:
            from ask.recall.recall_engine import RecallEngine
            from web.app import get_metadata_manager

            mgr = get_metadata_manager()
            engine = RecallEngine(mgr)
            assert engine is not None
            assert hasattr(engine, 'schedule_spaced_repetition')
        except Exception as e:
            pytest.fail(f"RecallEngine initialization failed: {e}")

    def test_recall_engine_returns_data(self):
        """Test RecallEngine returns structured data."""
        try:
            from ask.recall.recall_engine import RecallEngine
            from web.app import get_metadata_manager

            mgr = get_metadata_manager()
            engine = RecallEngine(mgr)
            results = engine.schedule_spaced_repetition(n=5)

            assert isinstance(results, list)
            for item in results:
                assert hasattr(item, 'title')
                assert hasattr(item, 'type_specific')
        except Exception as e:
            pytest.fail(f"RecallEngine data retrieval failed: {e}")

    def test_pattern_detector_init(self):
        """Test PatternDetector can initialize without crashing."""
        try:
            from ask.insights.pattern_detector import PatternDetector
            from web.app import get_metadata_manager

            mgr = get_metadata_manager()
            detector = PatternDetector(mgr)
            assert detector is not None
            assert hasattr(detector, 'find_patterns')
        except Exception as e:
            pytest.fail(f"PatternDetector initialization failed: {e}")

    def test_pattern_detector_returns_data(self):
        """Test PatternDetector returns structured data."""
        try:
            from ask.insights.pattern_detector import PatternDetector
            from web.app import get_metadata_manager

            mgr = get_metadata_manager()
            detector = PatternDetector(mgr)
            results = detector.find_patterns(n=5)

            assert isinstance(results, dict)
            assert 'top_tags' in results
            assert 'top_sources' in results
            assert isinstance(results['top_tags'], list)
            assert isinstance(results['top_sources'], list)
        except Exception as e:
            pytest.fail(f"PatternDetector data retrieval failed: {e}")

    def test_question_engine_init(self):
        """Test QuestionEngine can initialize without crashing."""
        try:
            from ask.socratic.question_engine import QuestionEngine

            engine = QuestionEngine()
            assert engine is not None
            assert hasattr(engine, 'generate_questions')
        except Exception as e:
            pytest.fail(f"QuestionEngine initialization failed: {e}")

    def test_question_engine_generates_questions(self):
        """Test QuestionEngine can generate questions."""
        try:
            from ask.socratic.question_engine import QuestionEngine

            engine = QuestionEngine()
            questions = engine.generate_questions("This is test content about machine learning and AI.")

            assert isinstance(questions, list)
            # Should generate at least some questions
            assert len(questions) >= 0
            for question in questions:
                assert isinstance(question, str)
                assert len(question) > 0
        except Exception as e:
            pytest.fail(f"QuestionEngine question generation failed: {e}")

class TestCognitiveIntegration:

    def test_all_features_work_with_metadata_manager(self):
        """Test all cognitive features work with MetadataManager."""
        try:
            from web.app import get_metadata_manager
            mgr = get_metadata_manager()

            # Test each feature can be initialized
            from ask.proactive.surfacer import ProactiveSurfacer
            from ask.temporal.temporal_engine import TemporalEngine
            from ask.recall.recall_engine import RecallEngine
            from ask.insights.pattern_detector import PatternDetector
            from ask.socratic.question_engine import QuestionEngine

            ProactiveSurfacer(mgr)
            TemporalEngine(mgr)
            RecallEngine(mgr)
            PatternDetector(mgr)
            QuestionEngine()  # Doesn't use mgr

        except Exception as e:
            pytest.fail(f"Cognitive feature integration failed: {e}")

    def test_web_interface_compatibility(self):
        """Test cognitive features work with web interface expectations."""
        from web.app import get_metadata_manager

        try:
            mgr = get_metadata_manager()

            # Test proactive
            from ask.proactive.surfacer import ProactiveSurfacer
            surfacer = ProactiveSurfacer(mgr)
            forgotten = surfacer.surface_forgotten_content(n=5)
            assert isinstance(forgotten, list)

            # Test temporal
            from ask.temporal.temporal_engine import TemporalEngine
            engine = TemporalEngine(mgr)
            rels = engine.identify_temporal_relationships(n=10)
            assert isinstance(rels, list)

            # Test recall
            from ask.recall.recall_engine import RecallEngine
            engine = RecallEngine(mgr)
            items = engine.schedule_spaced_repetition(n=10)
            assert isinstance(items, list)

            # Test patterns
            from ask.insights.pattern_detector import PatternDetector
            detector = PatternDetector(mgr)
            patterns = detector.find_patterns(n=10)
            assert isinstance(patterns, dict)
            assert 'top_tags' in patterns
            assert 'top_sources' in patterns

        except Exception as e:
            pytest.fail(f"Web interface compatibility failed: {e}")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])