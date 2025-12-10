#!/usr/bin/env python3
"""
Test suite for ContentPipeline

Tests unified content processing pipeline with configurable stages,
bulk processing, and statistics tracking.
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from helpers.content_pipeline import (
    ContentPipeline, ContentResult, ProcessingResult, PipelineStats,
    ProcessingStage, PipelineConfig, StrategyResult
)


class TestContentPipeline:
    """Test cases for ContentPipeline."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = {
            'stats_file': str(Path(self.temp_dir) / 'test_pipeline_stats.json'),
            'enable_summarization': True,
            'enable_clustering': True,
            'performance_tracking': True
        }
        self.pipeline = ContentPipeline(self.config)

    def test_initialization(self):
        """Test ContentPipeline initialization."""
        assert self.pipeline is not None
        assert self.pipeline.config == self.config
        assert isinstance(self.pipeline.stats, PipelineStats)
        assert isinstance(self.pipeline.pipeline_config, PipelineConfig)
        assert self.pipeline.pipeline_config.performance_tracking is True

    def test_pipeline_config_creation(self):
        """Test pipeline configuration creation."""
        config = self.pipeline.pipeline_config

        # Should have default stages plus enabled optional stages
        expected_stages = [
            ProcessingStage.DETECT_TYPE,
            ProcessingStage.CLASSIFY_CONTENT,
            ProcessingStage.PROCESS_DOCUMENT,
            ProcessingStage.EXTRACT_METADATA,
            ProcessingStage.SUMMARIZE_CONTENT,  # enabled in config
            ProcessingStage.CLUSTER_TOPICS,     # enabled in config
            ProcessingStage.EXPORT_CONTENT      # enabled by default
        ]

        for stage in expected_stages:
            assert stage in config.enabled_stages

    def test_single_content_processing_basic(self):
        """Test basic single content processing."""
        content = "This is a test article about machine learning and artificial intelligence."

        # Mock components to avoid import issues
        with patch.object(self.pipeline, '_get_component') as mock_get_component:
            mock_detector = Mock()
            mock_detector.detect_from_content.return_value = Mock(
                content_type='article',
                confidence=0.9,
                metadata={'detected': True}
            )

            mock_classifier = Mock()
            mock_classifier.classify_content.return_value = Mock(
                category='technology',
                confidence=0.85,
                subcategory='ai',
                tags=['machine learning', 'ai'],
                reasoning='Content discusses AI topics'
            )

            mock_get_component.side_effect = lambda name: {
                'content_detector': mock_detector,
                'content_classifier': mock_classifier,
                'document_processor': None,  # Will be skipped
                'content_exporter': None     # Will be skipped
            }.get(name)

            result = self.pipeline.process_content(
                content=content,
                title="Test Article",
                url="https://example.com/test"
            )

            assert isinstance(result, ContentResult)
            assert result.content == content
            assert result.title == "Test Article"
            assert result.url == "https://example.com/test"
            assert result.content_type == 'article'
            assert result.classification is not None
            assert result.classification['category'] == 'technology'
            assert result.total_processing_time > 0
            assert len(result.processing_stages) > 0

    def test_content_processing_with_all_stages(self):
        """Test content processing with all pipeline stages."""
        content = "This is a comprehensive test article about artificial intelligence, machine learning, and deep learning technologies."

        # Configure pipeline with all stages
        pipeline_options = {
            'stages': [
                ProcessingStage.DETECT_TYPE,
                ProcessingStage.CLASSIFY_CONTENT,
                ProcessingStage.PROCESS_DOCUMENT,
                ProcessingStage.EXTRACT_METADATA,
                ProcessingStage.SUMMARIZE_CONTENT,
                ProcessingStage.CLUSTER_TOPICS,
                ProcessingStage.ANALYZE_QUALITY,
                ProcessingStage.GENERATE_INSIGHTS,
                ProcessingStage.EXPORT_CONTENT
            ]
        }

        result = self.pipeline.process_content(
            content=content,
            title="Comprehensive Test",
            url="https://example.com/comprehensive",
            pipeline_options=pipeline_options
        )

        assert isinstance(result, ContentResult)
        assert len(result.processing_stages) == 9

        # Check that all stages were attempted
        stage_names = [stage.stage.value for stage in result.processing_stages]
        expected_stages = [stage.value for stage in pipeline_options['stages']]

        assert set(stage_names) == set(expected_stages)

        # Basic content should be processed
        assert result.content == content
        assert result.title == "Comprehensive Test"
        assert result.summary is not None  # Should have been generated
        assert result.topics is not None   # Should have been extracted
        assert result.quality_score >= 0   # Should have been calculated
        assert result.insights is not None # Should have been generated

    def test_detect_type_stage(self):
        """Test content type detection stage."""
        content = "Test content"
        result = ContentResult(content=content, url="https://youtube.com/watch?v=123")

        # Mock content detector
        with patch.object(self.pipeline, '_get_component') as mock_get_component:
            mock_detector = Mock()
            mock_detector.detect_from_url.return_value = Mock(
                content_type='youtube_video',
                confidence=0.95,
                metadata={'platform': 'youtube', 'video_id': '123'}
            )
            mock_get_component.return_value = mock_detector

            stage_result = self.pipeline._run_detect_type_stage(result, {}, "")

            assert stage_result.success is True
            assert stage_result.stage == ProcessingStage.DETECT_TYPE
            assert result.content_type == 'youtube_video'
            assert 'platform' in result.metadata

    def test_classify_content_stage(self):
        """Test content classification stage."""
        content = "This article discusses machine learning algorithms and their applications."
        result = ContentResult(content=content, title="ML Article")

        # Mock content classifier
        with patch.object(self.pipeline, '_get_component') as mock_get_component:
            mock_classifier = Mock()
            mock_classifier.classify_content.return_value = Mock(
                category='technology',
                confidence=0.88,
                subcategory='machine_learning',
                tags=['ml', 'algorithms'],
                reasoning='Content about ML algorithms'
            )
            mock_get_component.return_value = mock_classifier

            stage_result = self.pipeline._run_classify_content_stage(result, {}, "")

            assert stage_result.success is True
            assert stage_result.stage == ProcessingStage.CLASSIFY_CONTENT
            assert result.classification is not None
            assert result.classification['category'] == 'technology'
            assert result.classification['confidence'] == 0.88

    def test_extract_metadata_stage(self):
        """Test metadata extraction stage."""
        content = "This is test content with some words for analysis."
        result = ContentResult(
            content=content,
            title="Test Title",
            url="https://example.com/test"
        )

        stage_result = self.pipeline._run_extract_metadata_stage(result, {}, "")

        assert stage_result.success is True
        assert stage_result.stage == ProcessingStage.EXTRACT_METADATA
        assert 'word_count' in result.metadata
        assert 'character_count' in result.metadata
        assert 'processing_timestamp' in result.metadata
        assert 'domain' in result.metadata
        assert result.metadata['domain'] == 'example.com'

    def test_summarize_content_stage(self):
        """Test content summarization stage."""
        content = "This is sentence one. This is sentence two. This is sentence three. This is sentence four."
        result = ContentResult(content=content)

        stage_result = self.pipeline._run_summarize_content_stage(result, {}, "")

        assert stage_result.success is True
        assert stage_result.stage == ProcessingStage.SUMMARIZE_CONTENT
        assert result.summary is not None
        assert len(result.summary) < len(content)  # Should be shorter

    def test_cluster_topics_stage(self):
        """Test topic clustering stage."""
        content = "machine learning artificial intelligence deep learning neural networks algorithms"
        result = ContentResult(content=content)

        stage_result = self.pipeline._run_cluster_topics_stage(result, {}, "")

        assert stage_result.success is True
        assert stage_result.stage == ProcessingStage.CLUSTER_TOPICS
        assert result.topics is not None
        assert isinstance(result.topics, list)

    def test_analyze_quality_stage(self):
        """Test content quality analysis stage."""
        content = "This is a comprehensive article about technology with detailed information and analysis." * 10
        result = ContentResult(
            content=content,
            title="Quality Test Article",
            classification={'category': 'tech', 'confidence': 0.9},
            topics=['technology', 'analysis', 'information', 'detailed']
        )
        result.metadata = {'field1': 'value1', 'field2': 'value2', 'field3': 'value3',
                          'field4': 'value4', 'field5': 'value5', 'field6': 'value6'}

        stage_result = self.pipeline._run_analyze_quality_stage(result, {}, "")

        assert stage_result.success is True
        assert stage_result.stage == ProcessingStage.ANALYZE_QUALITY
        assert result.quality_score > 0
        assert result.quality_score <= 1.0

        # Should have high quality score due to length, title, classification, metadata, topics
        assert result.quality_score > 0.8

    def test_generate_insights_stage(self):
        """Test insight generation stage."""
        content = "Test content for insight generation. This has multiple sentences."
        result = ContentResult(
            content=content,
            classification={'category': 'test', 'confidence': 0.75},
            quality_score=0.85,
            total_processing_time=1.5
        )
        result.processing_stages = [
            ProcessingResult(stage=ProcessingStage.DETECT_TYPE, success=True),
            ProcessingResult(stage=ProcessingStage.CLASSIFY_CONTENT, success=True),
            ProcessingResult(stage=ProcessingStage.EXTRACT_METADATA, success=False)
        ]

        stage_result = self.pipeline._run_generate_insights_stage(result, {}, "")

        assert stage_result.success is True
        assert stage_result.stage == ProcessingStage.GENERATE_INSIGHTS
        assert result.insights is not None
        assert 'readability' in result.insights
        assert 'classification' in result.insights
        assert 'processing' in result.insights

        processing_insights = result.insights['processing']
        assert processing_insights['stages_run'] == 3
        assert processing_insights['stages_successful'] == 2
        assert processing_insights['quality_score'] == 0.85

    def test_bulk_processing(self):
        """Test bulk content processing."""
        content_items = [
            {'content': 'Article 1 content about technology', 'title': 'Tech Article 1'},
            {'content': 'Article 2 content about science', 'title': 'Science Article 2'},
            {'content': 'Article 3 content about business', 'title': 'Business Article 3'}
        ]

        results = self.pipeline.bulk_process_content(content_items)

        assert len(results) == 3

        for i, result in enumerate(results):
            assert isinstance(result, ContentResult)
            assert result.content == content_items[i]['content']
            assert result.title == content_items[i]['title']
            assert len(result.processing_stages) > 0

    def test_pipeline_statistics(self):
        """Test pipeline statistics tracking."""
        # Process some content to generate stats
        content_items = [
            {'content': 'Test content 1'},
            {'content': 'Test content 2'},
            {'content': 'Test content 3'}
        ]

        self.pipeline.bulk_process_content(content_items)

        stats = self.pipeline.get_pipeline_stats()

        assert stats['total_processed'] == 3
        assert stats['total_successful'] >= 0  # Depends on stage success
        assert 'overall_success_rate' in stats
        assert 'stage_success_rates' in stats
        assert 'average_processing_time' in stats

    def test_stats_persistence(self):
        """Test statistics persistence to disk."""
        # Process content to generate stats
        self.pipeline.process_content("Test content for persistence")

        # Check that stats file was created
        stats_file = Path(self.config['stats_file'])
        assert stats_file.exists()

        # Load stats from file
        with open(stats_file, 'r') as f:
            saved_stats = json.load(f)

        assert saved_stats['total_processed'] == 1
        assert 'stage_stats' in saved_stats

    def test_pipeline_config_override(self):
        """Test pipeline configuration override."""
        content = "Test content"

        # Override to run only specific stages
        pipeline_options = {
            'stages': [ProcessingStage.EXTRACT_METADATA, ProcessingStage.SUMMARIZE_CONTENT]
        }

        result = self.pipeline.process_content(
            content=content,
            pipeline_options=pipeline_options
        )

        assert len(result.processing_stages) == 2
        stage_names = [stage.stage for stage in result.processing_stages]
        assert ProcessingStage.EXTRACT_METADATA in stage_names
        assert ProcessingStage.SUMMARIZE_CONTENT in stage_names

    def test_error_handling_stop_on_error(self):
        """Test error handling with stop_on_error enabled."""
        # Create pipeline that stops on error
        config = self.config.copy()
        config['stop_on_error'] = True
        pipeline = ContentPipeline(config)

        # Mock a component to fail
        with patch.object(pipeline, '_get_component') as mock_get_component:
            mock_get_component.side_effect = Exception("Component failed")

            result = pipeline.process_content("Test content")

            # Should stop after first error
            assert len(result.processing_stages) <= 1
            if result.processing_stages:
                assert result.processing_stages[0].success is False

    def test_error_handling_continue_on_error(self):
        """Test error handling with continue on error."""
        # Default behavior should continue on error
        assert self.pipeline.pipeline_config.stop_on_error is False

        # Mock first stage to fail, others to succeed
        original_run_stage = self.pipeline._run_stage

        def mock_run_stage(stage, content_result, options, log_path):
            if stage == ProcessingStage.DETECT_TYPE:
                return ProcessingResult(stage=stage, success=False, error="Mock error")
            else:
                return original_run_stage(stage, content_result, options, log_path)

        with patch.object(self.pipeline, '_run_stage', side_effect=mock_run_stage):
            result = self.pipeline.process_content("Test content")

            # Should have tried all stages despite first failure
            assert len(result.processing_stages) > 1
            assert result.processing_stages[0].success is False  # First failed

    def test_markdown_export_generation(self):
        """Test markdown export generation."""
        result = ContentResult(
            content="Test content for export",
            title="Export Test",
            url="https://example.com/export",
            classification={'category': 'test', 'confidence': 0.8, 'tags': ['test', 'export']},
            summary="This is a test summary",
            topics=['export', 'markdown', 'test']
        )
        result.metadata = {'word_count': 10, 'domain': 'example.com'}

        markdown = self.pipeline._generate_markdown_export(result)

        assert "# Export Test" in markdown
        assert "**Source:** https://example.com/export" in markdown
        assert "## Metadata" in markdown
        assert "## Classification" in markdown
        assert "## Summary" in markdown
        assert "## Topics" in markdown
        assert "## Content" in markdown
        assert "Test content for export" in markdown

    def test_export_stats(self):
        """Test statistics export functionality."""
        # Process content to generate stats
        self.pipeline.process_content("Test content for export")

        # Export stats
        export_path = self.pipeline.export_stats()

        assert Path(export_path).exists()

        # Load and verify exported stats
        with open(export_path, 'r') as f:
            exported_stats = json.load(f)

        assert exported_stats['total_processed'] == 1
        assert 'overall_success_rate' in exported_stats
        assert 'stage_success_rates' in exported_stats


class TestContentResult:
    """Test ContentResult data class."""

    def test_content_result_creation(self):
        """Test ContentResult creation and properties."""
        result = ContentResult(
            content="Test content",
            title="Test Title",
            url="https://example.com/test"
        )

        assert result.content == "Test content"
        assert result.title == "Test Title"
        assert result.url == "https://example.com/test"
        assert result.metadata == {}
        assert result.processing_stages == []
        assert result.exports == {}
        assert result.insights == {}
        assert result.total_processing_time == 0.0
        assert result.quality_score == 0.0


class TestProcessingResult:
    """Test ProcessingResult data class."""

    def test_processing_result_creation(self):
        """Test ProcessingResult creation."""
        result = ProcessingResult(
            stage=ProcessingStage.DETECT_TYPE,
            success=True,
            data={'result': 'test'},
            processing_time=1.5
        )

        assert result.stage == ProcessingStage.DETECT_TYPE
        assert result.success is True
        assert result.data == {'result': 'test'}
        assert result.error is None
        assert result.processing_time == 1.5
        assert result.metadata == {}


class TestBackwardCompatibility:
    """Test backward compatibility with legacy interfaces."""

    def test_legacy_content_processor(self):
        """Test legacy ContentProcessor compatibility."""
        from helpers.content_pipeline import ContentProcessor

        # Should create with deprecation warning
        with pytest.warns(DeprecationWarning):
            processor = ContentProcessor({'test': 'config'})

        assert processor.pipeline is not None
        assert isinstance(processor.pipeline, ContentPipeline)

    def test_legacy_process_method(self):
        """Test legacy process method."""
        from helpers.content_pipeline import ContentProcessor

        with pytest.warns(DeprecationWarning):
            processor = ContentProcessor()

        content = "Test content for legacy processing"
        result = processor.process(content)

        # Should return processed content string (legacy format)
        assert isinstance(result, str)
        assert len(result) > 0


def run_content_pipeline_tests():
    """Run all ContentPipeline tests."""
    pytest.main([__file__, "-v"])


if __name__ == "__main__":
    run_content_pipeline_tests()