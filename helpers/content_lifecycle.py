#!/usr/bin/env python3
"""
Content Lifecycle Management System

Implements a 10-stage content lifecycle from raw ingestion to final processing.
Each content item progresses through clear stages with validation and quality checks.

Content Lifecycle Stages (1-10):
1. raw_received - URL/file received, no processing yet
2. ingestion_attempting - Actively trying to fetch/process content
3. ingested - Successfully retrieved raw content, basic validation passed
4. validated - Content quality verified, meets minimum thresholds
5. transformed - Content converted to standardized formats (markdown, HTML)
6. analyzed - AI processing completed (tags, metadata, classification)
7. summarized - AI summaries generated, key insights extracted
8. enriched - Additional metadata added, cross-references created
9. finalized - All processing complete, ready for use
10. archived - Final state, no further changes expected
"""

import json
import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from pathlib import Path
import hashlib

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)

class ContentStage(Enum):
    """Content lifecycle stages from raw to final."""
    RAW_RECEIVED = "raw_received"  # URL/file received, no processing
    INGESTION_ATTEMPTING = "ingestion_attempting"  # Actively trying to fetch
    INGESTED = "ingested"  # Raw content retrieved, basic validation
    VALIDATED = "validated"  # Content quality verified
    TRANSFORMED = "transformed"  # Converted to standard formats
    ANALYZED = "analyzed"  # AI processing (tags, metadata)
    SUMMARIZED = "summarized"  # AI summaries, insights extracted
    ENRICHED = "enriched"  # Additional metadata, cross-references
    FINALIZED = "finalized"  # All processing complete
    ARCHIVED = "archived"  # Final state, no changes expected

class ContentType(Enum):
    """Types of content sources."""
    URL = "url"
    FILE = "file"
    DATABASE = "database"
    EMAIL = "email"
    API = "api"

class ContentItem:
    """Represents a single content item through its lifecycle."""

    def __init__(self, content_id: str, source_type: ContentType, source_location: str):
        self.content_id = content_id
        self.source_type = source_type
        self.source_location = source_location
        self.current_stage = ContentStage.RAW_RECEIVED
        self.metadata = {}
        self.quality_metrics = {}
        self.file_locations = {}
        self.processing_history = []
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()

class ContentLifecycleManager:
    """
    Manages content through its complete lifecycle from ingestion to finalization.

    Implements quality validation, stage progression, and transformation pipelines.
    """

    def __init__(self, db_path: str = "data/atlas.db"):
        self.db_path = db_path
        self._ensure_content_table()

    def _ensure_content_table(self):
        """Ensure content_items table exists with proper schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS content_items (
                    content_id TEXT PRIMARY KEY,
                    source_type TEXT NOT NULL,
                    source_location TEXT NOT NULL,
                    current_stage TEXT NOT NULL DEFAULT 'raw_received',
                    metadata TEXT DEFAULT '{}',
                    quality_metrics TEXT DEFAULT '{}',
                    file_locations TEXT DEFAULT '{}',
                    processing_history TEXT DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(source_type, source_location)
                )
            """)

            # Create indexes for efficient querying
            conn.execute("CREATE INDEX IF NOT EXISTS idx_content_stage ON content_items(current_stage)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_content_source_type ON content_items(source_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_content_created ON content_items(created_at)")
            conn.commit()

    def create_content_item(self, source_type: ContentType, source_location: str,
                           metadata: Dict[str, Any] = None) -> ContentItem:
        """Create a new content item."""
        content_id = self._generate_content_id(source_type, source_location)

        content_item = ContentItem(content_id, source_type, source_location)
        if metadata:
            content_item.metadata.update(metadata)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO content_items (
                    content_id, source_type, source_location, current_stage,
                    metadata, quality_metrics, file_locations, processing_history,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                content_item.content_id,
                content_item.source_type.value,
                content_item.source_location,
                content_item.current_stage.value,
                json.dumps(content_item.metadata),
                json.dumps(content_item.quality_metrics),
                json.dumps(content_item.file_locations),
                json.dumps(content_item.processing_history),
                content_item.created_at,
                content_item.updated_at
            ))
            conn.commit()

        logger.info(f"📝 Created content item: {content_id} ({source_type.value}: {source_location})")
        return content_item

    def get_content_item(self, content_id: str) -> Optional[ContentItem]:
        """Retrieve a content item by ID."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT content_id, source_type, source_location, current_stage,
                           metadata, quality_metrics, file_locations, processing_history,
                           created_at, updated_at
                    FROM content_items WHERE content_id = ?
                """, (content_id,))
                row = cursor.fetchone()

                if not row:
                    return None

                content_item = ContentItem(row[0], ContentType(row[1]), row[2])
                content_item.current_stage = ContentStage(row[3])
                content_item.metadata = json.loads(row[4] or '{}')
                content_item.quality_metrics = json.loads(row[5] or '{}')
                content_item.file_locations = json.loads(row[6] or '{}')
                content_item.processing_history = json.loads(row[7] or '[]')
                content_item.created_at = row[8]
                content_item.updated_at = row[9]

                return content_item

        except Exception as e:
            logger.error(f"Failed to get content item {content_id}: {e}")
            return None

    def update_stage(self, content_id: str, new_stage: ContentStage,
                    metadata_updates: Dict[str, Any] = None,
                    quality_metrics: Dict[str, Any] = None,
                    file_locations: Dict[str, str] = None) -> bool:
        """Update content item to a new stage."""
        try:
            content_item = self.get_content_item(content_id)
            if not content_item:
                logger.error(f"Content item {content_id} not found")
                return False

            # Validate stage progression
            if not self._validate_stage_progression(content_item.current_stage, new_stage):
                logger.error(f"Invalid stage progression: {content_item.current_stage.value} -> {new_stage.value}")
                return False

            # Update content item
            old_stage = content_item.current_stage
            content_item.current_stage = new_stage
            content_item.updated_at = datetime.now().isoformat()

            if metadata_updates:
                content_item.metadata.update(metadata_updates)

            if quality_metrics:
                content_item.quality_metrics.update(quality_metrics)

            if file_locations:
                content_item.file_locations.update(file_locations)

            # Add to processing history
            history_entry = {
                "from_stage": old_stage.value,
                "to_stage": new_stage.value,
                "timestamp": datetime.now().isoformat(),
                "metadata_updates": metadata_updates or {},
                "quality_metrics": quality_metrics or {}
            }
            content_item.processing_history.append(history_entry)

            # Save to database
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE content_items SET
                        current_stage = ?,
                        metadata = ?,
                        quality_metrics = ?,
                        file_locations = ?,
                        processing_history = ?,
                        updated_at = ?
                    WHERE content_id = ?
                """, (
                    new_stage.value,
                    json.dumps(content_item.metadata),
                    json.dumps(content_item.quality_metrics),
                    json.dumps(content_item.file_locations),
                    json.dumps(content_item.processing_history),
                    content_item.updated_at,
                    content_id
                ))
                conn.commit()

            logger.info(f"📈 Updated {content_id}: {old_stage.value} -> {new_stage.value}")
            return True

        except Exception as e:
            logger.error(f"Failed to update stage for {content_id}: {e}")
            return False

    def validate_content_quality(self, content_id: str, content: str,
                               content_type: str = "article") -> Dict[str, Any]:
        """Validate content quality and return quality metrics."""

        # Basic content validation
        word_count = len(content.split())
        char_count = len(content)

        # Quality heuristics
        quality_metrics = {
            "word_count": word_count,
            "char_count": char_count,
            "estimated_reading_time_minutes": max(1, word_count // 200),
            "has_minimum_length": word_count >= 100,
            "has_substantial_content": word_count >= 500,
            "is_likely_complete": word_count >= 1000,
            "content_type": content_type,
            "validation_timestamp": datetime.now().isoformat()
        }

        # Content type specific validation
        if content_type == "article":
            # Check for article structure
            has_title = bool(content_item.metadata.get('title')) if hasattr(self, 'content_item') else False
            has_paragraphs = content.count('\n\n') >= 3
            quality_metrics.update({
                "has_title": has_title,
                "has_paragraphs": has_paragraphs,
                "is_likely_article": has_paragraphs and word_count >= 300
            })

        # Overall quality score (0-100)
        score = 0
        if quality_metrics["has_minimum_length"]:
            score += 20
        if quality_metrics["has_substantial_content"]:
            score += 30
        if quality_metrics["is_likely_complete"]:
            score += 30
        if content_type == "article" and quality_metrics.get("is_likely_article"):
            score += 20

        quality_metrics["quality_score"] = score
        quality_metrics["quality_grade"] = self._get_quality_grade(score)

        return quality_metrics

    def _get_quality_grade(self, score: int) -> str:
        """Convert quality score to grade."""
        if score >= 90:
            return "excellent"
        elif score >= 80:
            return "good"
        elif score >= 70:
            return "fair"
        elif score >= 60:
            return "poor"
        else:
            return "inadequate"

    def _validate_stage_progression(self, current_stage: ContentStage, new_stage: ContentStage) -> bool:
        """Validate that stage progression is logical."""
        stage_order = [stage for stage in ContentStage]
        current_index = stage_order.index(current_stage)
        new_index = stage_order.index(new_stage)

        # Allow progression to next stage or same stage (for updates)
        return new_index >= current_index

    def _generate_content_id(self, source_type: ContentType, source_location: str) -> str:
        """Generate unique content ID based on source."""
        unique_string = f"{source_type.value}:{source_location}"
        hash_obj = hashlib.md5(unique_string.encode())
        return f"content_{hash_obj.hexdigest()[:12]}"

    def get_content_by_stage(self, stage: ContentStage) -> List[ContentItem]:
        """Get all content items at a specific stage."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT content_id FROM content_items WHERE current_stage = ?
                    ORDER BY created_at DESC
                """, (stage.value,))
                content_ids = [row[0] for row in cursor.fetchall()]

            return [self.get_content_item(content_id) for content_id in content_ids]

        except Exception as e:
            logger.error(f"Failed to get content by stage {stage.value}: {e}")
            return []

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get statistics about content processing stages."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT current_stage, COUNT(*) as count
                    FROM content_items
                    GROUP BY current_stage
                    ORDER BY count DESC
                """)
                stage_counts = {row[0]: row[1] for row in cursor.fetchall()}

                total_content = sum(stage_counts.values())

                # Calculate progression rates
                validated_count = stage_counts.get('validated', 0)
                finalized_count = stage_counts.get('finalized', 0)

                stats = {
                    "total_content_items": total_content,
                    "stage_distribution": stage_counts,
                    "validation_rate": (validated_count / total_content * 100) if total_content > 0 else 0,
                    "completion_rate": (finalized_count / total_content * 100) if total_content > 0 else 0,
                    "generated_at": datetime.now().isoformat()
                }

                return stats

        except Exception as e:
            logger.error(f"Failed to get processing stats: {e}")
            return {}

    def find_content_by_source(self, source_type: ContentType, source_location: str) -> Optional[ContentItem]:
        """Find content item by source location."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT content_id FROM content_items
                    WHERE source_type = ? AND source_location = ?
                """, (source_type.value, source_location))
                row = cursor.fetchone()

                if row:
                    return self.get_content_item(row[0])
                return None

        except Exception as e:
            logger.error(f"Failed to find content by source: {e}")
            return None

if __name__ == "__main__":
    # Test the content lifecycle system
    manager = ContentLifecycleManager()

    # Create test content item
    test_item = manager.create_content_item(
        ContentType.URL,
        "https://example.com/article",
        {"title": "Test Article", "source": "test"}
    )

    print(f"Created content item: {test_item.content_id}")
    print(f"Current stage: {test_item.current_stage.value}")

    # Test quality validation
    test_content = "This is a test article with some content. " * 50  # Make it substantial
    quality_metrics = manager.validate_content_quality(test_item.content_id, test_content)
    print(f"Quality metrics: {quality_metrics}")

    # Test stage progression
    success = manager.update_stage(
        test_item.content_id,
        ContentStage.INGESTED,
        quality_metrics=quality_metrics
    )
    print(f"Stage update successful: {success}")

    # Get stats
    stats = manager.get_processing_stats()
    print(f"Processing stats: {stats}")