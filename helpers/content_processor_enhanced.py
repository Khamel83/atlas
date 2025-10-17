"""
Enhanced Content Processor with idempotent processing and structured extraction.
Integrates with Atlas's existing systems while adding intelligent content analysis.
"""

import os
import json
import hashlib
import sqlite3
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pathlib import Path

from helpers.structured_extraction import StructuredExtractor, ContentInput, ExtractionResult

logger = logging.getLogger(__name__)

class ContentProcessorEnhanced:
    """Enhanced content processor with idempotent processing and structured extraction."""

    def __init__(self, config=None):
        """Initialize enhanced content processor."""
        self.config = config or {}
        self.extractor = StructuredExtractor()

        # Database for tracking processed content
        self.db_path = self.config.get('processed_content_db', 'data/processed_content.db')
        self.output_dir = Path(self.config.get('output_dir', 'output'))

        # Initialize database
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database for tracking processed content."""
        db_dir = os.path.dirname(self.db_path)
        if db_dir:  # Only create directories if there's a directory path
            os.makedirs(db_dir, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processed_content (
                    content_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    url TEXT,
                    source TEXT,
                    content_type TEXT,
                    content_hash TEXT NOT NULL,
                    extraction_quality REAL,
                    processing_status TEXT DEFAULT 'completed',
                    insights_path TEXT,
                    raw_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS content_insights (
                    content_id TEXT PRIMARY KEY,
                    summary TEXT,
                    key_topics JSON,
                    key_themes JSON,
                    entities JSON,
                    quotes JSON,
                    theses JSON,
                    sentiment TEXT,
                    complexity TEXT,
                    extraction_quality REAL,
                    model_used TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (content_id) REFERENCES processed_content (content_id)
                )
            """)

            # Create indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_content_hash ON processed_content(content_hash)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_content_type ON processed_content(content_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_processing_status ON processed_content(processing_status)")

            conn.commit()

    def generate_content_id(self, title: str, url: str = None, content: str = None, date: datetime = None) -> str:
        """Generate unique, deterministic content ID."""
        # Create hash from identifying features
        id_components = [
            url or '',
            title or '',
            str(date) if date else '',
        ]

        # Add content hash if available (for duplicate detection)
        if content:
            content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()[:8]
            id_components.append(content_hash)

        id_string = '|'.join(id_components)
        content_id = hashlib.sha256(id_string.encode('utf-8')).hexdigest()[:16]

        return content_id

    def is_already_processed(self, content_id: str) -> bool:
        """Check if content has already been processed."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT content_id FROM processed_content WHERE content_id = ? AND processing_status = 'completed'",
                (content_id,)
            )
            result = cursor.fetchone() is not None
            logger.debug(f"Checking if {content_id} already processed: {result}")
            return result

    def get_content_insights(self, content_id: str) -> Optional[Dict[str, Any]]:
        """Get existing insights for content."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM content_insights WHERE content_id = ?",
                (content_id,)
            )
            row = cursor.fetchone()

            if row:
                return dict(row)
            return None

    def process_content(self,
                       title: str,
                       content: str,
                       url: str = None,
                       source: str = None,
                       content_type: str = "article",
                       date: datetime = None,
                       force_reprocess: bool = False) -> Dict[str, Any]:
        """Process content with idempotent extraction and storage."""

        # Generate content ID
        content_id = self.generate_content_id(title, url, content, date)

        logger.info(f"Processing content: {title[:50]}... (ID: {content_id})")

        # Check if already processed
        if not force_reprocess and self.is_already_processed(content_id):
            logger.info(f"✅ Content already processed, skipping: {content_id}")
            existing_insights = self.get_content_insights(content_id)
            return {
                'content_id': content_id,
                'status': 'already_processed',
                'insights': existing_insights
            }

        try:
            # Create content input
            content_input = ContentInput(
                title=title,
                content=content,
                url=url,
                date=date,
                source=source,
                content_type=content_type
            )

            # Extract structured insights
            extraction_result = self.extractor.extract(content_input, validate=True)

            # Store results
            self._store_processed_content(extraction_result, content_input, content)

            logger.info(f"✅ Content processed successfully: {content_id} (quality: {extraction_result.extraction_quality:.2f})")

            return {
                'content_id': content_id,
                'status': 'processed',
                'extraction_quality': extraction_result.extraction_quality,
                'insights': self._extraction_to_dict(extraction_result),
                'processing_time': extraction_result.processing_time
            }

        except Exception as e:
            logger.error(f"❌ Failed to process content {content_id}: {e}")

            # Store error status
            self._store_error_status(content_id, title, url, source, content_type, str(e))

            return {
                'content_id': content_id,
                'status': 'error',
                'error': str(e)
            }

    def _store_processed_content(self, extraction_result: ExtractionResult, content_input: ContentInput, raw_content: str):
        """Store processed content and insights to database and files."""

        content_id = extraction_result.content_id

        # Create output directories
        content_dir = self.output_dir / 'enhanced' / content_id
        content_dir.mkdir(parents=True, exist_ok=True)

        # Save raw content
        raw_path = content_dir / 'content.txt'
        with open(raw_path, 'w', encoding='utf-8') as f:
            f.write(raw_content)

        # Save structured insights as JSON
        insights_path = content_dir / 'insights.json'
        with open(insights_path, 'w', encoding='utf-8') as f:
            json.dump(self._extraction_to_dict(extraction_result), f, indent=2, default=str)

        # Store in database
        with sqlite3.connect(self.db_path) as conn:
            # Store processed content metadata
            conn.execute("""
                INSERT OR REPLACE INTO processed_content
                (content_id, title, url, source, content_type, content_hash, extraction_quality,
                 processing_status, insights_path, raw_path, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                content_id,
                content_input.title,
                content_input.url,
                content_input.source,
                content_input.content_type,
                hashlib.sha256(raw_content.encode()).hexdigest(),
                extraction_result.extraction_quality,
                'completed',  # Explicitly set status
                str(insights_path),
                str(raw_path),
                extraction_result.created_at,
                datetime.utcnow()
            ))

            # Store structured insights
            insights = extraction_result.insights
            conn.execute("""
                INSERT OR REPLACE INTO content_insights
                (content_id, summary, key_topics, key_themes, entities, quotes, theses,
                 sentiment, complexity, extraction_quality, model_used, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                content_id,
                insights.summary,
                json.dumps([t.dict() for t in insights.key_topics]),
                json.dumps(insights.key_themes),
                json.dumps([e.dict() for e in insights.entities]),
                json.dumps([q.dict() for q in insights.quotes]),
                json.dumps([t.dict() for t in insights.theses]),
                insights.sentiment,
                insights.complexity,
                extraction_result.extraction_quality,
                extraction_result.model_used,
                extraction_result.created_at
            ))

            conn.commit()

    def _store_error_status(self, content_id: str, title: str, url: str, source: str, content_type: str, error: str):
        """Store error status for failed processing."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO processed_content
                (content_id, title, url, source, content_type, content_hash, processing_status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 'error', ?, ?)
            """, (
                content_id, title, url, source, content_type,
                hashlib.sha256((title + error).encode()).hexdigest(),
                datetime.utcnow(), datetime.utcnow()
            ))
            conn.commit()

    def _extraction_to_dict(self, extraction_result: ExtractionResult) -> Dict[str, Any]:
        """Convert extraction result to dictionary."""
        insights = extraction_result.insights

        return {
            'content_id': extraction_result.content_id,
            'extraction_quality': extraction_result.extraction_quality,
            'processing_time': extraction_result.processing_time,
            'model_used': extraction_result.model_used,
            'created_at': extraction_result.created_at.isoformat(),
            'insights': {
                'summary': insights.summary,
                'key_topics': [t.dict() for t in insights.key_topics],
                'key_themes': insights.key_themes,
                'entities': [e.dict() for e in insights.entities],
                'quotes': [q.dict() for q in insights.quotes],
                'theses': [t.dict() for t in insights.theses],
                'sentiment': insights.sentiment,
                'complexity': insights.complexity,
                'content_type': insights.content_type
            }
        }

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT
                    COUNT(*) as total_processed,
                    COUNT(CASE WHEN processing_status = 'completed' THEN 1 END) as successful,
                    COUNT(CASE WHEN processing_status = 'error' THEN 1 END) as errors,
                    AVG(CASE WHEN processing_status = 'completed' THEN extraction_quality END) as avg_quality,
                    COUNT(DISTINCT content_type) as content_types
                FROM processed_content
            """)

            stats = dict(cursor.fetchone())

            # Get content type breakdown
            cursor = conn.execute("""
                SELECT content_type, COUNT(*) as count
                FROM processed_content
                WHERE processing_status = 'completed'
                GROUP BY content_type
            """)
            stats['content_type_breakdown'] = dict(cursor.fetchall())

            return stats

    def search_insights(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search processed content insights."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Simple text search across summary and entities
            cursor = conn.execute("""
                SELECT pc.content_id, pc.title, pc.url, pc.content_type,
                       ci.summary, ci.key_themes, ci.entities, ci.extraction_quality
                FROM processed_content pc
                JOIN content_insights ci ON pc.content_id = ci.content_id
                WHERE pc.processing_status = 'completed'
                AND (ci.summary LIKE ? OR ci.entities LIKE ?)
                ORDER BY ci.extraction_quality DESC
                LIMIT ?
            """, (f'%{query}%', f'%{query}%', limit))

            return [dict(row) for row in cursor.fetchall()]

def create_enhanced_processor(config=None) -> ContentProcessorEnhanced:
    """Factory function to create enhanced processor."""
    return ContentProcessorEnhanced(config)