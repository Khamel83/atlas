"""
Base Ingestor Classes

This module provides base classes for all Atlas ingestors, reducing code duplication
and ensuring consistent interfaces and behavior across the ingestion system.
"""

import json
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from helpers.dedupe import link_uid
from helpers.error_handler import (
    ErrorCategory,
    ErrorContext,
    ErrorSeverity,
    create_error_handler,
)
from helpers.evaluation_utils import EvaluationFile
from helpers.metadata_manager import (
    ContentMetadata,
    ContentType,
    ProcessingStatus,
    create_metadata_manager,
)
from helpers.path_manager import PathType, create_path_manager
from helpers.utils import log_error, log_info
from process.evaluate import (
    classify_content,
    diarize_speakers,
    extract_entities,
    summarize_content,
)


class IngestorResult:
    """Container for ingestor operation results."""

    def __init__(
        self,
        success: bool,
        metadata: Optional[ContentMetadata] = None,
        error: Optional[str] = None,
        should_retry: bool = False,
    ):
        self.success = success
        self.metadata = metadata
        self.error = error
        self.should_retry = should_retry


class BaseIngestor(ABC):
    """Abstract base class for all Atlas ingestors."""

    def __init__(
        self, config: Dict[str, Any], content_type: ContentType, module_name: str
    ):
        self.config = config
        self.metadata_manager = create_metadata_manager(config)
        self.path_manager = create_path_manager(config)
        self.error_handler = create_error_handler(config)

        # Each subclass must define these
        self.content_type = content_type
        self.module_name = module_name

        # Initialize after subclass sets content_type
        self._post_init()

    def _post_init(self):
        """Post-initialization setup after subclass defines content_type."""
        if self.content_type:
            self.log_path = self.path_manager.get_log_path(self.content_type)
            self.path_manager.ensure_directories(self.content_type)

    @abstractmethod
    def fetch_content(
        self, source: str, metadata: ContentMetadata
    ) -> Tuple[bool, Optional[str]]:
        """
        Fetch content from source.

        Args:
            source: Source URL or identifier
            metadata: Content metadata object

        Returns:
            Tuple of (success, content_or_error_message)
        """
        pass

    @abstractmethod
    def process_content(self, content: str, metadata: ContentMetadata) -> bool:
        """
        Process fetched content (save to files, extract text, etc.).

        Args:
            content: Raw content to process
            metadata: Content metadata object

        Returns:
            bool: True if successful, False otherwise
        """
        pass

    def should_skip(self, source: str) -> bool:
        """Check if content should be skipped (already exists)."""
        uid = link_uid(source)
        return self.metadata_manager.exists(self.content_type, uid)

    def create_metadata(
        self, source: str, title: Optional[str] = None, **kwargs
    ) -> ContentMetadata:
        """Create metadata for content."""
        return self.metadata_manager.create_metadata(
            self.content_type, source, title, **kwargs
        )

    def save_metadata(self, metadata: ContentMetadata) -> bool:
        """Save metadata to file."""
        return self.metadata_manager.save_metadata(metadata)

    def save_raw_data(
        self, raw_data: Any, metadata: ContentMetadata, suffix: str = "raw"
    ) -> bool:
        """
        Save raw source data for preservation.
        CORE PRINCIPLE: Never lose original data!
        """
        try:
            paths = self.path_manager.get_path_set(self.content_type, metadata.uid)
            # Create a raw data file path
            base_path = paths.base_path
            raw_path = f"{base_path}_{suffix}.json"

            # Convert raw data to JSON if needed
            if isinstance(raw_data, str):
                data_to_save = {"raw_text": raw_data, "type": "text"}
            elif isinstance(raw_data, (dict, list)):
                data_to_save = {"raw_data": raw_data, "type": "structured"}
            else:
                data_to_save = {"raw_data": str(raw_data), "type": "converted"}

            # Add preservation metadata
            data_to_save.update(
                {
                    "preserved_at": datetime.now().isoformat(),
                    "content_type": self.content_type.value,
                    "source": metadata.source,
                    "uid": metadata.uid,
                }
            )

            with open(raw_path, "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, indent=2, ensure_ascii=False, default=str)

            log_info(self.log_path, f"Raw data preserved: {raw_path}")
            return True

        except Exception as e:
            log_error(self.log_path, f"Failed to save raw data: {e}")
            return False

    def handle_error(
        self,
        error_message: str,
        source: Optional[str] = None,
        should_retry: bool = False,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    ) -> bool:
        """Handle errors with standardized logging and retry logic."""
        context = ErrorContext(
            module=self.module_name,
            function="ingest_content",
            url=source,
            metadata={"content_type": self.content_type.value},
        )

        error = self.error_handler.create_error(
            message=error_message,
            category=ErrorCategory.PROCESSING,
            severity=severity,
            context=context,
            should_retry=should_retry,
        )

        return self.error_handler.handle_error(error, self.log_path)

    def run_evaluations(self, content: str, metadata: ContentMetadata) -> bool:
        """Run AI evaluations on content."""
        try:
            # Get content paths
            paths = self.path_manager.get_path_set(self.content_type, metadata.uid)
            markdown_path = paths.get_path(PathType.MARKDOWN)

            if not markdown_path or not os.path.exists(markdown_path):
                return False

            # Create evaluation file
            eval_file = EvaluationFile(
                source_file_path=markdown_path, config=self.config
            )

            # Add ingestion evaluation
            eval_file.add_evaluation(
                evaluator_id="ingestion_v1",
                eval_type="ingestion_check",
                result={
                    "status": "success",
                    "notes": f"Content ingested via {metadata.fetch_method}",
                    "content_type": self.content_type.value,
                },
            )

            # Run content classification
            classification_result = classify_content(content, self.config)
            if classification_result:
                eval_file.add_evaluation(
                    evaluator_id="openrouter_classifier_v1",
                    eval_type="content_classification",
                    result={
                        "classification": classification_result,
                        "model": self.config.get("llm_model"),
                    },
                )

                # Update metadata with tags
                tier_1_cats = classification_result.get("tier_1_categories", [])
                tier_2_tags = classification_result.get("tier_2_sub_tags", [])

                self.metadata_manager.update_categorization(
                    metadata, tier_1_cats, tier_2_tags
                )

            # Generate summary
            summary = summarize_text(content, self.config)
            if summary:
                eval_file.add_evaluation(
                    evaluator_id="openrouter_summary_v1",
                    eval_type="summary",
                    result={
                        "summary_text": summary,
                        "model": self.config.get("llm_model"),
                    },
                )

            # Extract entities
            entities = extract_entities(content, self.config)
            if entities:
                eval_file.add_evaluation(
                    evaluator_id="openrouter_entities_v1",
                    eval_type="entity_extraction",
                    result={
                        "entities": entities,
                        "model": self.config.get("llm_model"),
                    },
                )

            # Content-specific evaluations
            self.run_content_specific_evaluations(content, eval_file)

            eval_file.save()
            return True

        except Exception as e:
            log_error(self.log_path, f"Failed to run evaluations: {str(e)}")
            return False

    def run_content_specific_evaluations(self, content: str, eval_file: EvaluationFile):
        """Run content-type specific evaluations. Override in subclasses."""
        pass

    def ingest_single(
        self, source: str, title: Optional[str] = None, **kwargs
    ) -> IngestorResult:
        """Ingest a single content item."""
        try:
            # Check if should skip
            if self.should_skip(source):
                log_info(self.log_path, f"Skipping {source} - already exists")
                return IngestorResult(success=True)

            # Create metadata
            metadata = self.create_metadata(source, title, **kwargs)
            metadata.status = ProcessingStatus.STARTED
            self.save_metadata(metadata)

            # Fetch content
            success, content_or_error = self.fetch_content(source, metadata)

            if not success:
                if content_or_error is not None:
                    metadata.set_error(content_or_error)
                self.save_metadata(metadata)
                if content_or_error is not None:
                    self.handle_error(content_or_error, source, should_retry=True)
                return IngestorResult(
                    success=False,
                    metadata=metadata,
                    error=content_or_error,
                    should_retry=True,
                )

            # Process content
            if content_or_error is not None:
                if not self.process_content(content_or_error, metadata):
                    error_msg = f"Failed to process content for {source}"
                    metadata.set_error(error_msg)
                    self.save_metadata(metadata)
                    self.handle_error(error_msg, source)
                    return IngestorResult(
                        success=False, metadata=metadata, error=error_msg
                    )

                # Run evaluations
                self.run_evaluations(content_or_error, metadata)

            # Mark as successful
            metadata.set_success()
            self.save_metadata(metadata)

            log_info(self.log_path, f"Successfully ingested {source}")
            return IngestorResult(success=True, metadata=metadata)

        except Exception as e:
            error_msg = f"Unexpected error ingesting {source}: {str(e)}"
            self.handle_error(error_msg, source, severity=ErrorSeverity.HIGH)
            return IngestorResult(success=False, error=error_msg)

    def ingest_batch(self, sources: List[str], **kwargs) -> Dict[str, IngestorResult]:
        """Ingest multiple content items."""
        results = {}

        log_info(self.log_path, f"Starting batch ingestion of {len(sources)} items")

        for source in sources:
            result = self.ingest_single(source, **kwargs)
            results[source] = result

        # Log summary
        successful = sum(1 for r in results.values() if r.success)
        failed = len(results) - successful

        log_info(
            self.log_path,
            f"Batch ingestion complete: {successful} successful, {failed} failed",
        )

        return results

    def get_failed_items(self) -> List[ContentMetadata]:
        """Get all failed items for this content type."""
        return self.metadata_manager.get_failed_items(self.content_type)

    def get_retry_items(self) -> List[ContentMetadata]:
        """Get all items marked for retry."""
        return self.metadata_manager.get_retry_items(self.content_type)

    def cleanup_temp_files(self, uid: Optional[str] = None):
        """Clean up temporary files."""
        if uid:
            self.path_manager.cleanup_temp_files(self.content_type, uid)


class TextBasedIngestor(BaseIngestor):
    """Base class for text-based content (articles, etc.)."""

    def save_content_to_markdown(self, content: str, metadata: ContentMetadata) -> bool:
        """Save content to markdown file."""
        try:
            from helpers.utils import generate_markdown_summary

            paths = self.path_manager.get_path_set(self.content_type, metadata.uid)
            markdown_path = paths.get_path(PathType.MARKDOWN)

            if not markdown_path:
                return False

            # Generate markdown with frontmatter
            markdown_content = generate_markdown_summary(
                title=metadata.title,
                source=metadata.source,
                date=metadata.date,
                tags=metadata.tags,
                notes=metadata.notes,
                content=content,
            )

            # Save to file
            os.makedirs(os.path.dirname(markdown_path), exist_ok=True)
            with open(markdown_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)

            metadata.content_path = markdown_path
            return True

        except Exception as e:
            log_error(self.log_path, f"Failed to save markdown: {str(e)}")
            return False


class MediaBasedIngestor(BaseIngestor):
    """Base class for media-based content (podcasts, videos, etc.)."""

    def save_media_file(
        self, media_content: bytes, metadata: ContentMetadata, path_type: PathType
    ) -> bool:
        """Save media file to disk."""
        try:
            paths = self.path_manager.get_path_set(self.content_type, metadata.uid)
            media_path = paths.get_path(path_type)

            if not media_path:
                return False

            os.makedirs(os.path.dirname(media_path), exist_ok=True)
            with open(media_path, "wb") as f:
                f.write(media_content)

            # Update metadata based on path type
            if path_type == PathType.AUDIO:
                metadata.audio_path = media_path
            elif path_type == PathType.VIDEO:
                metadata.type_specific["video_path"] = media_path

            return True

        except Exception as e:
            log_error(self.log_path, f"Failed to save media file: {str(e)}")
            return False

    def save_transcript(self, transcript: str, metadata: ContentMetadata) -> bool:
        """Save transcript to file."""
        try:
            paths = self.path_manager.get_path_set(self.content_type, metadata.uid)
            transcript_path = paths.get_path(PathType.TRANSCRIPT)

            if not transcript_path:
                return False

            os.makedirs(os.path.dirname(transcript_path), exist_ok=True)
            with open(transcript_path, "w", encoding="utf-8") as f:
                f.write(transcript)

            metadata.transcript_path = transcript_path
            return True

        except Exception as e:
            log_error(self.log_path, f"Failed to save transcript: {str(e)}")
            return False

    def run_content_specific_evaluations(self, content: str, eval_file: EvaluationFile):
        """Run media-specific evaluations like speaker diarization."""
        # Check if content looks like an interview/conversation
        classification_result = classify_content(content, self.config)
        content_type_detected = (
            classification_result.get("content_type", "")
            if classification_result
            else ""
        )

        if "interview" in content_type_detected.lower():
            log_info(
                self.log_path, "Content classified as interview, running diarization"
            )
            diarized_text = diarize_speakers(content, self.config)
            if diarized_text:
                eval_file.add_evaluation(
                    evaluator_id="openrouter_diarization_v1",
                    eval_type="speaker_diarization",
                    result={
                        "diarized_text": diarized_text,
                        "model": self.config.get("llm_model"),
                    },
                )


def create_ingestor(content_type: ContentType, config: Dict[str, Any]) -> BaseIngestor:
    """Factory function to create appropriate ingestor based on content type."""
    # This would be extended to return specific ingestor implementations
    # For now, return base class (this is just the framework)

    if content_type == ContentType.ARTICLE:
        # Would return ArticleIngestor(config)
        pass
    elif content_type == ContentType.PODCAST:
        # Would return PodcastIngestor(config)
        pass
    elif content_type == ContentType.YOUTUBE:
        # Would return YouTubeIngestor(config)
        pass

    # Fallback to base class for demonstration
    class DummyIngestor(BaseIngestor):
        def __init__(self, config: Dict[str, Any]):
            super().__init__(config, content_type, f"{content_type.value}_ingestor")

        def fetch_content(self, source, metadata):
            return False, "Not implemented"

        def process_content(self, content, metadata):
            return False

    return DummyIngestor(config)
