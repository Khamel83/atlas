#!/usr/bin/env python3
"""
Content Processing Pipeline

Orchestrates content through the lifecycle stages from raw ingestion to finalization.
Handles transformations, quality validation, and AI processing.
"""

import json
import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import markdown
import html

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.content_lifecycle import ContentLifecycleManager, ContentStage, ContentType
from helpers.strategy_progression_engine import StrategyProgressionEngine
from helpers.content_transactions import ContentTransactionSystem, TransactionTimer
from helpers.numeric_stages import NumericStage

logger = logging.getLogger(__name__)

class ContentProcessingPipeline:
    """
    Main pipeline for processing content through lifecycle stages.

    Handles:
    - Stage progression automation
    - Quality validation
    - Content transformation (markdown, HTML)
    - AI processing integration
    - File management
    """

    def __init__(self, db_path: str = "data/atlas.db"):
        self.db_path = db_path
        self.lifecycle_manager = ContentLifecycleManager(db_path)
        self.workflow_engine = StrategyProgressionEngine(db_path)
        self.transaction_system = ContentTransactionSystem(db_path)

        # Ensure content directories exist
        self.content_dirs = {
            "raw": Path("content/raw"),
            "markdown": Path("content/markdown"),
            "html": Path("content/html"),
            "processed": Path("content/processed")
        }

        for dir_path in self.content_dirs.values():
            dir_path.mkdir(parents=True, exist_ok=True)

    def process_url_job(self, job_id: str, url: str, source: str = "unknown") -> Dict[str, Any]:
        """Process a URL job through the complete pipeline with transaction tracking."""
        try:
            # Record initial transaction - content received
            content_id = self._generate_content_id_from_url(url)

            with TransactionTimer(self.transaction_system, content_id, NumericStage.CONTENT_RECEIVED.value,
                                 f"Pipeline processing started for URL: {url}",
                                 metadata={"job_id": job_id, "source": source, "url": url}):
                logger.info(f"🚀 Starting pipeline processing for URL: {url}")

                # Check if content already exists
                existing_content = self.lifecycle_manager.find_content_by_source(ContentType.URL, url)

                if existing_content:
                    logger.info(f"🔄 Content already exists: {existing_content.content_id} (stage: {existing_content.current_stage.value})")
                    content_id = existing_content.content_id

                    # Record transaction for existing content check
                    self.transaction_system.record_transaction(
                        content_id, NumericStage.CONTENT_RECEIVED.value,
                        "Existing content found",
                        metadata={"existing_stage": existing_content.current_stage.value,
                                 "quality_score": existing_content.quality_metrics.get("quality_score", 0)}
                    )

                    # Check if existing content is at terminal stage (archived or fully processed)
                    terminal_stages = [ContentStage.TRANSFORMED, ContentStage.FINALIZED, ContentStage.ARCHIVED]
                    is_terminal_numeric = hasattr(existing_content, 'numeric_stage') and existing_content.numeric_stage >= 590

                    if existing_content.current_stage in terminal_stages or is_terminal_numeric:
                        logger.info(f"✅ Content already at terminal stage {existing_content.current_stage.value}, marking as duplicate")

                        # Create duplicate content item with terminal status
                        with TransactionTimer(self.transaction_system, f"{content_id}_dup", NumericStage.CONTENT_DUPLICATE.value,
                                             "Duplicate content detected",
                                             metadata={"original_content_id": existing_content.content_id,
                                                      "original_stage": existing_content.current_stage.value,
                                                      "duplicate_reason": "terminal_content_exists",
                                                      "job_id": job_id,
                                                      "source": source}):

                            # Create a new content item marked as duplicate
                            duplicate_content = self.lifecycle_manager.create_content_item(
                                ContentType.URL,
                                url,
                                {"job_id": job_id, "source": source, "duplicate_of": existing_content.content_id}
                            )

                            # Immediately mark as duplicate (terminal stage)
                            self.lifecycle_manager.update_stage(
                                duplicate_content.content_id,
                                ContentStage.ARCHIVED,  # Use archived as terminal state
                                quality_metrics={"quality_score": 100, "is_duplicate": True},
                                metadata_updates={"duplicate_of": existing_content.content_id, "terminal_status": "duplicate"}
                            )

                            # Record duplicate transaction
                            self.transaction_system.record_transaction(
                                duplicate_content.content_id, NumericStage.CONTENT_DUPLICATE.value,
                                "Content marked as duplicate (terminal status)",
                                success=True,
                                metadata={"original_content_id": existing_content.content_id,
                                         "original_stage": existing_content.current_stage.value,
                                         "terminal_stage": NumericStage.CONTENT_DUPLICATE.value,
                                         "batch_id": getattr(self, 'current_batch_id', None)}
                            )

                        return {
                            "success": True,
                            "content_id": duplicate_content.content_id,
                            "final_stage": ContentStage.ARCHIVED,
                            "quality_score": 100,
                            "word_count": existing_content.quality_metrics.get("word_count", 0),
                            "message": "Duplicate content - original already at terminal stage",
                            "duplicate_of": existing_content.content_id,
                            "terminal_status": "duplicate"
                        }
                    elif existing_content.current_stage in [ContentStage.INGESTED, ContentStage.VALIDATED]:
                        logger.info(f"🔄 Content exists but only at stage {existing_content.current_stage.value}, continuing processing")
                        # Use existing content item
                        content_item = existing_content
                    else:
                        logger.info(f"🔄 Content exists but only at stage {existing_content.current_stage.value}, continuing processing")
                        # Use existing content item
                        content_item = existing_content
                else:
                    # Stage 1: Create new content item
                    with TransactionTimer(self.transaction_system, content_id, NumericStage.CONTENT_RECEIVED.value,
                                         "Creating new content item",
                                         metadata={"job_id": job_id, "source": source, "url": url}):
                        content_item = self.lifecycle_manager.create_content_item(
                            ContentType.URL,
                            url,
                            {"job_id": job_id, "source": source}
                        )
                        content_id = content_item.content_id

                # Stage 2: Update to ingestion attempting
                with TransactionTimer(self.transaction_system, content_id, NumericStage.CONTENT_QUEUED.value,
                                     "Content queued for ingestion",
                                     previous_stage=NumericStage.CONTENT_RECEIVED.value,
                                     metadata={"job_id": job_id}):
                    self.lifecycle_manager.update_stage(
                        content_item.content_id,
                        ContentStage.INGESTION_ATTEMPTING,
                        {"job_id": job_id, "processing_started": datetime.now().isoformat()}
                    )

                # Stage 3: Perform ingestion using workflow engine
                with TransactionTimer(self.transaction_system, content_id, NumericStage.FETCH_ATTEMPTING.value,
                                     "Starting content ingestion workflow",
                                     previous_stage=NumericStage.CONTENT_QUEUED.value,
                                     metadata={"job_id": job_id, "url": url}):
                    workflow_result = self.workflow_engine.process_job_with_workflow(job_id)

                if workflow_result.get("success"):
                    # Stage 4: Mark as ingested
                    with TransactionTimer(self.transaction_system, content_id, NumericStage.CONTENT_RETRIEVED.value,
                                         "Content successfully ingested",
                                         previous_stage=NumericStage.FETCH_ATTEMPTING.value,
                                         metadata={"word_count": workflow_result.get("word_count", 0),
                                                  "actual_url": workflow_result.get("actual_url", url),
                                                  "strategy_used": workflow_result.get("strategy_used"),
                                                  "title": workflow_result.get("title")}):
                        self.lifecycle_manager.update_stage(
                            content_item.content_id,
                            ContentStage.INGESTED,
                            {
                                "ingestion_successful": True,
                                "word_count": workflow_result.get("word_count", 0),
                                "actual_url": workflow_result.get("actual_url", url),
                                "strategy_used": workflow_result.get("strategy_used"),
                                "title": workflow_result.get("title"),
                                "ingested_at": datetime.now().isoformat()
                            }
                        )

                    # Save raw content
                    raw_content = workflow_result.get("content", "")
                    with TransactionTimer(self.transaction_system, content_id, NumericStage.CONTENT_RETRIEVED.value,
                                         "Raw content saved to filesystem",
                                         metadata={"content_length": len(raw_content), "file_path": str(self.content_dirs["raw"] / f"{content_id}.txt")}):
                        self._save_raw_content(content_item.content_id, raw_content, url)

                    # Stage 5: Validate content quality
                    with TransactionTimer(self.transaction_system, content_id, NumericStage.VALIDATION_STARTED.value,
                                         "Starting content quality validation",
                                         previous_stage=NumericStage.CONTENT_RETRIEVED.value):
                        quality_metrics = self.lifecycle_manager.validate_content_quality(
                            content_item.content_id, raw_content, "article"
                        )

                    # Stage 6: Update to validated if quality is acceptable
                    if quality_metrics["quality_score"] >= 60:  # Minimum acceptable quality
                        with TransactionTimer(self.transaction_system, content_id, NumericStage.VALIDATION_PASSED.value,
                                             "Content quality validation passed",
                                             previous_stage=NumericStage.VALIDATION_STARTED.value,
                                             metadata={"quality_score": quality_metrics["quality_score"],
                                                      "word_count": quality_metrics["word_count"],
                                                      "quality_grade": quality_metrics.get("quality_grade", "unknown")}):
                            self.lifecycle_manager.update_stage(
                                content_item.content_id,
                                ContentStage.VALIDATED,
                                quality_metrics=quality_metrics
                            )

                        # Stage 7: Transform to standard formats
                        with TransactionTimer(self.transaction_system, content_id, NumericStage.PROCESSING_STARTED.value,
                                             "Starting content transformation",
                                             previous_stage=NumericStage.VALIDATION_PASSED.value):
                            transformation_result = self._transform_content(
                                content_item.content_id, raw_content, url
                            )

                        if transformation_result["success"]:
                            # Stage 8: Mark as transformed
                            with TransactionTimer(self.transaction_system, content_id, NumericStage.CONTENT_TRANSFORMED.value,
                                                 "Content transformation completed",
                                                 previous_stage=NumericStage.PROCESSING_STARTED.value,
                                                 metadata={"file_locations": transformation_result["file_locations"],
                                                          "formats_created": list(transformation_result["file_locations"].keys())}):
                                self.lifecycle_manager.update_stage(
                                    content_item.content_id,
                                    ContentStage.TRANSFORMED,
                                    file_locations=transformation_result["file_locations"],
                                    metadata_updates=transformation_result["metadata"]
                                )

                            # Record final successful transaction
                            self.transaction_system.record_transaction(
                                content_id, NumericStage.CONTENT_TRANSFORMED.value,
                                "Pipeline processing completed successfully",
                                success=True,
                                metadata={"final_stage": ContentStage.TRANSFORMED.value,
                                         "quality_score": quality_metrics["quality_score"],
                                         "word_count": quality_metrics["word_count"],
                                         "file_locations": transformation_result["file_locations"]}
                            )

                            return {
                                "success": True,
                                "content_id": content_item.content_id,
                                "final_stage": ContentStage.TRANSFORMED,
                                "quality_score": quality_metrics["quality_score"],
                                "word_count": quality_metrics["word_count"],
                                "file_locations": transformation_result["file_locations"]
                            }
                        else:
                            # Record transformation failure
                            self.transaction_system.record_transaction(
                                content_id, NumericStage.PROCESSING_STARTED.value,
                                "Content transformation failed",
                                success=False,
                                metadata={"error": transformation_result.get("errors", []),
                                         "quality_score": quality_metrics["quality_score"],
                                         "word_count": quality_metrics["word_count"]}
                            )
                            return {
                                "success": True,
                                "content_id": content_item.content_id,
                                "final_stage": ContentStage.VALIDATED,
                                "quality_score": quality_metrics["quality_score"],
                                "word_count": quality_metrics["word_count"],
                                "error": "Transformation failed"
                            }
                    else:
                        # Content quality too low, stop at ingested
                        self.transaction_system.record_transaction(
                            content_id, NumericStage.VALIDATION_STARTED.value,
                            "Content quality below threshold",
                            success=False,
                            metadata={"quality_score": quality_metrics["quality_score"],
                                     "word_count": quality_metrics["word_count"],
                                     "quality_grade": quality_metrics.get("quality_grade", "unknown"),
                                     "threshold": 60}
                        )
                        return {
                            "success": True,
                            "content_id": content_item.content_id,
                            "final_stage": ContentStage.INGESTED,
                            "quality_score": quality_metrics["quality_score"],
                            "word_count": quality_metrics["word_count"],
                            "error": "Content quality below threshold"
                        }
                else:
                    # Ingestion failed
                    with TransactionTimer(self.transaction_system, content_id, NumericStage.FETCH_FAILED.value,
                                         "Content ingestion failed",
                                         previous_stage=NumericStage.FETCH_ATTEMPTING.value,
                                         metadata={"error": workflow_result.get("error", "Unknown error")}):
                        self.lifecycle_manager.update_stage(
                            content_item.content_id,
                            ContentStage.INGESTED,
                            {
                                "ingestion_successful": False,
                                "error": workflow_result.get("error", "Unknown error"),
                                "failed_at": datetime.now().isoformat()
                            }
                        )

                    return {
                        "success": False,
                        "content_id": content_item.content_id,
                        "final_stage": ContentStage.INGESTED,
                        "error": workflow_result.get("error", "Ingestion failed")
                    }

        except Exception as e:
            # Record exception transaction
            self.transaction_system.record_transaction(
                content_id, NumericStage.CONTENT_RECEIVED.value,
                f"Pipeline processing failed: {str(e)}",
                success=False,
                metadata={"error": str(e), "job_id": job_id, "url": url}
            )

            logger.error(f"Pipeline processing failed for job {job_id}: {e}")
            return {
                "success": False,
                "error": f"Pipeline error: {str(e)}",
                "final_stage": ContentStage.INGESTION_ATTEMPTING
            }

    def _save_raw_content(self, content_id: str, content: str, source_url: str):
        """Save raw content to file system."""
        try:
            raw_file = self.content_dirs["raw"] / f"{content_id}.txt"
            with open(raw_file, 'w', encoding='utf-8') as f:
                f.write(f"Source: {source_url}\n")
                f.write(f"Content ID: {content_id}\n")
                f.write(f"Retrieved: {datetime.now().isoformat()}\n")
                f.write("=" * 50 + "\n\n")
                f.write(content)

            logger.info(f"💾 Saved raw content: {raw_file}")

        except Exception as e:
            logger.error(f"Failed to save raw content for {content_id}: {e}")

    def _transform_content(self, content_id: str, raw_content: str, source_url: str) -> Dict[str, Any]:
        """Transform raw content to markdown and HTML formats."""
        file_locations = {}
        metadata = {}
        transformation_errors = []

        try:
            # Generate markdown version
            markdown_content = self._convert_to_markdown(raw_content, source_url)
            if markdown_content:
                markdown_file = self.content_dirs["markdown"] / f"{content_id}.md"
                with open(markdown_file, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)
                file_locations["markdown"] = str(markdown_file)
                metadata["markdown_created"] = datetime.now().isoformat()
            else:
                transformation_errors.append("Markdown conversion failed")

            # Generate HTML version
            html_content = self._convert_to_html(raw_content, source_url)
            if html_content:
                html_file = self.content_dirs["html"] / f"{content_id}.html"
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                file_locations["html"] = str(html_file)
                metadata["html_created"] = datetime.now().isoformat()
            else:
                transformation_errors.append("HTML conversion failed")

            return {
                "success": len(file_locations) > 0,
                "file_locations": file_locations,
                "metadata": metadata,
                "errors": transformation_errors
            }

        except Exception as e:
            logger.error(f"Content transformation failed for {content_id}: {e}")
            return {
                "success": False,
                "file_locations": {},
                "metadata": {},
                "errors": [f"Transformation error: {str(e)}"]
            }

    def _convert_to_markdown(self, content: str, source_url: str) -> str:
        """Convert raw content to markdown format."""
        try:
            # Basic markdown conversion
            markdown_lines = [
                f"# Content from {source_url}",
                "",
                f"*Retrieved: {datetime.now().isoformat()}*",
                "",
                "---",
                ""
            ]

            # Split content into paragraphs and preserve structure
            paragraphs = content.split('\n\n')
            for paragraph in paragraphs:
                paragraph = paragraph.strip()
                if paragraph:
                    # Simple markdown formatting
                    if len(paragraph) > 100:
                        # Likely a paragraph, preserve as is
                        markdown_lines.append(paragraph)
                    elif paragraph.endswith('?'):
                        # Question, preserve as is
                        markdown_lines.append(paragraph)
                    else:
                        # Might be a heading or short line
                        markdown_lines.append(paragraph)

                    markdown_lines.append("")

            return "\n".join(markdown_lines)

        except Exception as e:
            logger.error(f"Markdown conversion failed: {e}")
            return None

    def _convert_to_html(self, content: str, source_url: str) -> str:
        """Convert raw content to HTML format."""
        try:
            # Convert to markdown first, then to HTML
            markdown_content = self._convert_to_markdown(content, source_url)
            if markdown_content:
                html_content = markdown.markdown(markdown_content)

                # Wrap in basic HTML structure
                full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Content from {source_url}</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #333; border-bottom: 2px solid #333; }}
        .metadata {{ color: #666; font-style: italic; }}
    </style>
</head>
<body>
    {html_content}
</body>
</html>"""

                return full_html

            return None

        except Exception as e:
            logger.error(f"HTML conversion failed: {e}")
            return None

    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get comprehensive pipeline statistics."""
        lifecycle_stats = self.lifecycle_manager.get_processing_stats()

        # Add pipeline-specific stats
        pipeline_stats = {
            "content_directories": {
                name: str(path) for name, path in self.content_dirs.items()
            },
            "pipeline_version": "1.0.0",
            "last_updated": datetime.now().isoformat()
        }

        # Merge stats
        pipeline_stats.update(lifecycle_stats)

        return pipeline_stats

    def get_content_at_stage(self, stage: ContentStage) -> List[Dict[str, Any]]:
        """Get content items at a specific stage with details."""
        content_items = self.lifecycle_manager.get_content_by_stage(stage)

        result = []
        for item in content_items:
            result.append({
                "content_id": item.content_id,
                "source_type": item.source_type.value,
                "source_location": item.source_location,
                "current_stage": item.current_stage.value,
                "quality_score": item.quality_metrics.get("quality_score", 0),
                "word_count": item.quality_metrics.get("word_count", 0),
                "created_at": item.created_at,
                "updated_at": item.updated_at,
                "file_locations": item.file_locations
            })

        return result

    def _generate_content_id_from_url(self, url: str) -> str:
        """Generate a consistent content ID from URL for transaction tracking."""
        import hashlib
        unique_string = f"url:{url}"
        hash_obj = hashlib.md5(unique_string.encode())
        return f"content_{hash_obj.hexdigest()[:12]}"

    def get_transaction_summary(self, content_id: str) -> Dict[str, Any]:
        """Get transaction summary for a content item from the single source of truth."""
        return {
            "content_id": content_id,
            "current_stage": self.transaction_system.get_current_stage(content_id),
            "progress_history": self.transaction_system.get_content_progress(content_id),
            "metrics": self.transaction_system.get_content_metrics(content_id)
        }

    def get_system_transaction_stats(self) -> Dict[str, Any]:
        """Get comprehensive system statistics from the transactional system."""
        recent_activity = self.transaction_system.get_recent_activity(minutes=60)
        stage_distribution = self.transaction_system.get_stage_distribution()
        daily_summary = self.transaction_system.get_daily_summary()

        return {
            "recent_activity_count": len(recent_activity),
            "stage_distribution": stage_distribution,
            "daily_summary": daily_summary,
            "system_health": {
                "transaction_system_ready": True,
                "total_content_items": sum(stage_distribution.values()),
                "active_processing": len([a for a in recent_activity if a["stage"] < 400])
            }
        }

if __name__ == "__main__":
    # Test the content processing pipeline
    pipeline = ContentProcessingPipeline()

    # Test processing a URL (using our test job)
    test_job_id = "18c66cfc-6b5c-4152-9369-20502e2ed894"
    test_url = "https://example.com"

    print("🧪 Testing content processing pipeline...")
    result = pipeline.process_url_job(test_job_id, test_url, "test")

    print(f"Pipeline result: {json.dumps(result, indent=2)}")

    # Get stats
    stats = pipeline.get_pipeline_stats()
    print(f"Pipeline stats: {json.dumps(stats, indent=2)}")