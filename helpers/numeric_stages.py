#!/usr/bin/env python3
"""
Numeric Stage Progression System for Atlas

Implements a clear numeric progression system where each 100-point range
represents a major phase of content processing.

Stage Structure:
100-199: Content Acquisition (raw content retrieval)
200-299: Content Validation (verify authenticity and completeness)
300-399: Content Processing (transformation, analysis)
400-499: Content Enhancement (AI processing, summarization)
500-599: Content Finalization (metadata, cross-references)
"""

import json
import sqlite3
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from pathlib import Path
import hashlib

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.content_transactions import ContentTransactionSystem, TransactionTimer

logger = logging.getLogger(__name__)

class NumericStage(Enum):
    """Numeric content processing stages - 0-599 complete system"""

    # 000-099: System & Initialization
    SYSTEM_INIT = 0              # System initialization
    CONTENT_DISCOVERED = 10      # Content discovered but not queued
    BATCH_RECEIVED = 20         # Batch file received (CSV, etc.)
    QUEUE_PENDING = 50          # Pending queue placement

    # 100-199: Content Acquisition Phase
    CONTENT_RECEIVED = 100      # URL/file received, no processing
    CONTENT_QUEUED = 110         # Queued for processing
    FETCH_ATTEMPTING = 120      # Actively trying to fetch content
    FETCH_FAILED = 130          # Initial fetch failed
    FALLBACK_ATTEMPTING = 140   # Trying fallback strategies
    CONTENT_RETRIEVED = 150     # Successfully retrieved raw content
    CONTENT_ARCHIVED = 160      # Archived version found/retrieved
    ACQUISITION_COMPLETE = 190  # All acquisition steps complete

    # 200-299: Content Validation Phase
    VALIDATION_STARTED = 200    # Starting validation process
    QUALITY_CHECK = 210         # Checking content quality
    AUTHENTICITY_VERIFY = 220   # Verifying content is authentic
    COMPLETENESS_CHECK = 230    # Verifying content is complete
    FORMAT_VALIDATE = 240        # Validating content format
    VALIDATION_PASSED = 250     # All validation checks passed
    VALIDATION_FAILED = 280     # Validation failed
    VALIDATION_COMPLETE = 299   # Validation phase complete

    # 300-399: Content Processing Phase
    PROCESSING_STARTED = 300    # Starting content processing
    EXTRACTION_CLEAN = 310      # Extract and clean main content
    STRUCTURE_ANALYSIS = 320    # Analyze document structure
    CONTENT_TRANSFORMED = 330   # Transformed to standard formats
    METADATA_EXTRACTED = 340    # Extract basic metadata
    CONTENT_FORMATTED = 350     # Formatted for storage
    PROCESSING_COMPLETE = 390   # Core processing complete

    # 400-499: Content Enhancement Phase
    ENHANCEMENT_STARTED = 400   # Starting AI enhancement
    CONTENT_ANALYZED = 410      # AI analysis complete
    CONTENT_SUMMARIZED = 420    # AI summaries generated
    TOPICS_EXTRACTED = 430      # Topics and keywords extracted
    ENTITIES_IDENTIFIED = 440  # Entities and relationships found
    SEMANTIC_ANALYSIS = 450     # Semantic analysis complete
    ENHANCEMENT_COMPLETE = 490  # AI enhancement complete

    # 500-599: Content Finalization Phase
    FINALIZATION_STARTED = 500  # Starting finalization
    CROSS_REFERENCES = 510     # Add cross-references
    QUALITY_FINAL = 520         # Final quality assessment
    METADATA_FINAL = 530        # Final metadata updates
    CONTENT_INDEXED = 540       # Content indexed for search
    FINALIZATION_COMPLETE = 590 # All processing complete (terminal)
    CONTENT_ARCHIVED_FINAL = 595 # Final archival state (terminal)
    CONTENT_DUPLICATE = 599     # Duplicate content (terminal - already processed)

    # Special error/retry states
    RATE_LIMITED = 666          # Rate limited, will retry
    PERMANENT_ERROR = 777       # Permanent failure, no retry
    SYSTEM_ERROR = 888          # System error, may retry

class StageModule:
    """Base class for stage processing modules"""

    def __init__(self, db_path: str = "data/atlas.db"):
        self.db_path = db_path
        self.stage_range = self._get_stage_range()

    def _get_stage_range(self) -> Tuple[int, int]:
        """Return the stage range this module handles"""
        raise NotImplementedError

    def can_process_stage(self, stage: NumericStage) -> bool:
        """Check if this module can handle the given stage"""
        return self.stage_range[0] <= stage.value <= self.stage_range[1]

    def process(self, content_id: str, current_stage: NumericStage,
                context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process content at the given stage"""
        raise NotImplementedError

class AcquisitionModule(StageModule):
    """100-199: Content Acquisition Module"""

    def _get_stage_range(self) -> Tuple[int, int]:
        return (100, 199)

    def process(self, content_id: str, current_stage: NumericStage,
                context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle content acquisition stages"""
        # This would integrate with the workflow engine
        # For now, return mock progression
        if current_stage == NumericStage.CONTENT_RECEIVED:
            return {
                "success": True,
                "next_stage": NumericStage.CONTENT_QUEUED,
                "message": "Content queued for acquisition"
            }
        elif current_stage == NumericStage.FETCH_ATTEMPTING:
            return {
                "success": True,
                "next_stage": NumericStage.CONTENT_RETRIEVED,
                "message": "Content successfully retrieved"
            }
        return {"success": False, "error": "Stage not implemented"}

class ValidationModule(StageModule):
    """200-299: Content Validation Module"""

    def _get_stage_range(self) -> Tuple[int, int]:
        return (200, 299)

    def process(self, content_id: str, current_stage: NumericStage,
                context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle content validation stages"""
        if current_stage == NumericStage.VALIDATION_STARTED:
            return {
                "success": True,
                "next_stage": NumericStage.QUALITY_CHECK,
                "message": "Starting content validation"
            }
        elif current_stage == NumericStage.QUALITY_CHECK:
            # Simulate quality validation
            quality_score = context.get("quality_score", 85)
            if quality_score >= 60:
                return {
                    "success": True,
                    "next_stage": NumericStage.AUTHENTICITY_VERIFY,
                    "message": f"Quality check passed: {quality_score}%"
                }
            else:
                return {
                    "success": False,
                    "next_stage": NumericStage.VALIDATION_FAILED,
                    "error": f"Quality too low: {quality_score}%"
                }
        return {"success": False, "error": "Stage not implemented"}

class ProcessingModule(StageModule):
    """300-399: Content Processing Module"""

    def _get_stage_range(self) -> Tuple[int, int]:
        return (300, 399)

    def process(self, content_id: str, current_stage: NumericStage,
                context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle content processing stages"""
        if current_stage == NumericStage.PROCESSING_STARTED:
            return {
                "success": True,
                "next_stage": NumericStage.EXTRACTION_CLEAN,
                "message": "Starting content processing"
            }
        elif current_stage == NumericStage.EXTRACTION_CLEAN:
            return {
                "success": True,
                "next_stage": NumericStage.STRUCTURE_ANALYSIS,
                "message": "Content extracted and cleaned"
            }
        elif current_stage == NumericStage.STRUCTURE_ANALYSIS:
            return {
                "success": True,
                "next_stage": NumericStage.CONTENT_TRANSFORMED,
                "message": "Content structure analyzed"
            }
        elif current_stage == NumericStage.CONTENT_TRANSFORMED:
            return {
                "success": True,
                "next_stage": NumericStage.METADATA_EXTRACTED,
                "message": "Content transformed to standard formats"
            }
        return {"success": False, "error": "Stage not implemented"}

class EnhancementModule(StageModule):
    """400-499: Content Enhancement Module"""

    def _get_stage_range(self) -> Tuple[int, int]:
        return (400, 499)

    def process(self, content_id: str, current_stage: NumericStage,
                context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle content enhancement stages"""
        if current_stage == NumericStage.ENHANCEMENT_STARTED:
            return {
                "success": True,
                "next_stage": NumericStage.CONTENT_ANALYZED,
                "message": "Starting AI enhancement"
            }
        return {"success": False, "error": "Stage not implemented"}

class FinalizationModule(StageModule):
    """500-599: Content Finalization Module"""

    def _get_stage_range(self) -> Tuple[int, int]:
        return (500, 599)

    def process(self, content_id: str, current_stage: NumericStage,
                context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle content finalization stages"""
        if current_stage == NumericStage.FINALIZATION_STARTED:
            return {
                "success": True,
                "next_stage": NumericStage.CROSS_REFERENCES,
                "message": "Starting finalization"
            }
        return {"success": False, "error": "Stage not implemented"}

class NumericStageManager:
    """
    Manages content progression through numeric stages

    Each module handles a specific 100-point range with clear responsibilities
    and progression logic.
    """

    def __init__(self, db_path: str = "data/atlas.db"):
        self.db_path = db_path
        self.transaction_system = ContentTransactionSystem(db_path)
        self.modules = [
            AcquisitionModule(db_path),
            ValidationModule(db_path),
            ProcessingModule(db_path),
            EnhancementModule(db_path),
            FinalizationModule(db_path)
        ]
        self._ensure_content_table()

    def _ensure_content_table(self):
        """Ensure content_items table supports numeric stages"""
        with sqlite3.connect(self.db_path) as conn:
            # Check if numeric_stage column exists
            cursor = conn.execute("""
                SELECT name FROM pragma_table_info('content_items')
                WHERE name = 'numeric_stage'
            """)
            if not cursor.fetchone():
                # Add numeric_stage column
                conn.execute("""
                    ALTER TABLE content_items ADD COLUMN numeric_stage INTEGER DEFAULT 100
                """)

                # Add index for numeric stages
                conn.execute("""
                    CREATE INDEX idx_content_numeric_stage ON content_items(numeric_stage)
                """)

                # Migrate existing content to numeric stages
                conn.execute("""
                    UPDATE content_items SET numeric_stage = CASE
                        WHEN current_stage = 'raw_received' THEN 100
                        WHEN current_stage = 'ingestion_attempting' THEN 120
                        WHEN current_stage = 'ingested' THEN 150
                        WHEN current_stage = 'validated' THEN 250
                        WHEN current_stage = 'transformed' THEN 350
                        ELSE 100
                    END
                """)

                conn.commit()
                logger.info("Migrated content items to numeric stages")

    def get_module_for_stage(self, stage: NumericStage) -> Optional[StageModule]:
        """Get the appropriate module for a given stage"""
        for module in self.modules:
            if module.can_process_stage(stage):
                return module
        return None

    def progress_to_next_stage(self, content_id: str,
                              current_stage: NumericStage,
                              context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Progress content to the next logical stage with transactional tracking"""
        module = self.get_module_for_stage(current_stage)
        if not module:
            # Record failure transaction
            self.transaction_system.record_transaction(
                content_id, current_stage.value,
                f"No module found for stage {current_stage.value}",
                success=False,
                metadata={"error": "Module not found", "context": context}
            )
            return {
                "success": False,
                "error": f"No module found for stage {current_stage.value}"
            }

        logger.info(f"🔄 Processing {content_id} at stage {current_stage.value} with {module.__class__.__name__}")

        try:
            # Record start transaction manually for debugging
            start_time = time.time()
            result = module.process(content_id, current_stage, context)
            duration_ms = int((time.time() - start_time) * 1000)

            print(f"DEBUG: Module result: {result}")
            print(f"DEBUG: Module result type: {type(result)}")
            print(f"DEBUG: Module result keys: {result.keys() if isinstance(result, dict) else 'Not a dict'}")
            if isinstance(result, dict) and 'next_stage' in result:
                print(f"DEBUG: next_stage type: {type(result['next_stage'])}")

            if result["success"]:
                next_stage = result["next_stage"]

                # Record successful progression transaction - use simple values
                self.transaction_system.record_transaction(
                    content_id, next_stage.value,
                    result.get("message", "Progressed to next stage"),
                    previous_stage=current_stage.value,
                    success=True,
                    metadata={
                        "module": module.__class__.__name__,
                        "next_stage_int": next_stage.value,
                        "current_stage_int": current_stage.value
                    }
                )

                self._update_content_stage(content_id, next_stage, result)
                logger.info(f"✅ {content_id} progressed to stage {next_stage.value}: {result['message']}")
            else:
                error_stage = result.get("next_stage", current_stage)

                # Record failure transaction - use simple values
                self.transaction_system.record_transaction(
                    content_id, error_stage.value,
                    f"Failed at stage {current_stage.value}: {result.get('error', 'Unknown error')}",
                    previous_stage=current_stage.value,
                    success=False,
                    metadata={
                        "error": result.get('error'),
                        "module": module.__class__.__name__,
                        "error_stage_int": error_stage.value,
                        "current_stage_int": current_stage.value
                    }
                )

                self._update_content_stage(content_id, error_stage, result)
                logger.error(f"❌ {content_id} failed at stage {current_stage.value}: {result.get('error', 'Unknown error')}")

            return result

        except Exception as e:
            error_msg = f"Stage processing error: {str(e)}"

            # Record exception transaction
            self.transaction_system.record_transaction(
                content_id, current_stage.value,
                error_msg,
                success=False,
                metadata={"exception": str(e), "context": context}
            )

            logger.error(f"❌ {error_msg}")
            return {"success": False, "error": error_msg}

    def _make_json_safe(self, obj):
        """Convert objects to JSON-serializable format."""
        if isinstance(obj, dict):
            return {key: self._make_json_safe(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_safe(item) for item in obj]
        elif isinstance(obj, (str, int, float, bool)):
            return obj
        elif hasattr(obj, 'value'):  # For enums
            return obj.value
        elif hasattr(obj, '__dict__'):
            return str(obj)
        else:
            return str(obj)

    def _update_content_stage(self, content_id: str, stage: NumericStage,
                             result: Dict[str, Any]):
        """Update content item stage in database"""
        # Use simple serializable data for JSON
        history_entry = {
            "stage": stage.value,
            "timestamp": datetime.now().isoformat(),
            "success": result.get("success", False),
            "message": result.get("message", ""),
            "module": result.get("module", "unknown")
        }

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE content_items SET
                    current_stage = ?,
                    numeric_stage = ?,
                    updated_at = ?,
                    quality_metrics = ?,
                    processing_history = ?
                WHERE content_id = ?
            """, (
                f"numeric_{stage.value}",
                stage.value,
                datetime.now().isoformat(),
                json.dumps(result.get("quality_metrics", {})),
                json.dumps([history_entry]),
                content_id
            ))
            conn.commit()

    def get_content_by_numeric_stage(self, min_stage: int, max_stage: int) -> List[Dict[str, Any]]:
        """Get content items within a numeric stage range"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT content_id, source_type, source_location,
                       numeric_stage, current_stage, quality_metrics
                FROM content_items
                WHERE numeric_stage BETWEEN ? AND ?
                ORDER BY numeric_stage, updated_at
            """, (min_stage, max_stage))

            return [
                {
                    "content_id": row[0],
                    "source_type": row[1],
                    "source_location": row[2],
                    "numeric_stage": row[3],
                    "current_stage": row[4],
                    "quality_metrics": json.loads(row[5] or "{}")
                }
                for row in cursor.fetchall()
            ]

    def get_stage_distribution(self) -> Dict[str, int]:
        """Get distribution of content across numeric stages"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT numeric_stage, COUNT(*) as count
                FROM content_items
                GROUP BY numeric_stage
                ORDER BY numeric_stage
            """)

            return {str(row[0]): row[1] for row in cursor.fetchall()}

if __name__ == "__main__":
    # Test the numeric stage system
    manager = NumericStageManager()

    print("Numeric Stage System initialized")
    print(f"Available modules: {[m.__class__.__name__ for m in manager.modules]}")

    # Get stage distribution
    distribution = manager.get_stage_distribution()
    print(f"Current stage distribution: {distribution}")

    # Test stage progression
    test_content_id = "test_content_123"
    test_stage = NumericStage.CONTENT_RECEIVED

    result = manager.progress_to_next_stage(test_content_id, test_stage)
    print(f"Stage progression result: {result}")