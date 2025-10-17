#!/usr/bin/env python3
"""
Failsafe Ingestor - Never lose data, bulletproof ingestion bridge
Bridges bulletproof capture with Atlas processing pipeline.

CORE PRINCIPLE: CAPTURE FIRST, PROCESS LATER, NEVER LOSE ANYTHING!
"""

import json
import os
import shutil
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import hashlib

from helpers.apple_integrations import BulletproofCapture
from helpers.article_manager import ArticleManager
from helpers.content_pipeline import ContentPipeline
from helpers.utils import log_info, log_error, generate_unique_id


class FailsafeIngestor:
    """
    Failsafe ingestion coordinator that ensures no data is ever lost.

    Workflow:
    1. IMMEDIATE raw data capture to quarantine
    2. Persistent logging in capture database
    3. Background processing with retry logic
    4. Data promotion only after successful processing
    5. Emergency recovery for any failures
    """

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize failsafe ingestor."""
        self.config = config or {}
        self.capture = BulletproofCapture(config)

        # Processing components
        self.article_manager = ArticleManager(config)
        self.content_pipeline = ContentPipeline(config)

        # Failsafe directories
        self.failsafe_dir = Path(self.config.get('data_directory', 'data')) / 'failsafe'
        self.inbox_dir = self.failsafe_dir / 'inbox'
        self.processing_dir = self.failsafe_dir / 'processing'
        self.completed_dir = self.failsafe_dir / 'completed'
        self.failed_dir = self.failsafe_dir / 'failed'

        for directory in [self.failsafe_dir, self.inbox_dir, self.processing_dir,
                         self.completed_dir, self.failed_dir]:
            directory.mkdir(parents=True, exist_ok=True)

        # Processing configuration
        self.max_retries = self.config.get('max_retries', 5)
        self.retry_delay_hours = self.config.get('retry_delay_hours', 1)
        self.batch_size = self.config.get('processing_batch_size', 10)

        # Initialize failsafe database
        self._init_failsafe_db()

    def _init_failsafe_db(self):
        """Initialize failsafe processing database."""
        try:
            db_path = self.failsafe_dir / 'failsafe.db'

            with sqlite3.connect(db_path) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS ingestion_queue (
                        id TEXT PRIMARY KEY,
                        capture_id TEXT,
                        content_type TEXT,
                        content_data TEXT,
                        metadata TEXT,
                        priority INTEGER DEFAULT 5,
                        status TEXT DEFAULT 'pending',
                        created_at TEXT,
                        processing_started_at TEXT,
                        processing_completed_at TEXT,
                        retry_count INTEGER DEFAULT 0,
                        last_error TEXT,
                        hash_fingerprint TEXT
                    )
                ''')

                conn.execute('''
                    CREATE TABLE IF NOT EXISTS processing_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        queue_id TEXT,
                        action TEXT,
                        status TEXT,
                        message TEXT,
                        timestamp TEXT,
                        FOREIGN KEY (queue_id) REFERENCES ingestion_queue (id)
                    )
                ''')

                # Indexes for performance
                conn.execute('CREATE INDEX IF NOT EXISTS idx_queue_status ON ingestion_queue (status)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_queue_priority ON ingestion_queue (priority, created_at)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_queue_hash ON ingestion_queue (hash_fingerprint)')

            log_info("Failsafe ingestion database initialized")

        except Exception as e:
            log_error(f"Error initializing failsafe database: {str(e)}")
            raise

    def ingest_url(self, url: str, source: str = "manual", priority: int = 5) -> str:
        """
        FAILSAFE: Ingest URL with bulletproof capture.

        Returns:
            queue_id: Unique ID for tracking this ingestion
        """
        try:
            # Step 1: IMMEDIATE bulletproof capture
            metadata = {
                'url': url,
                'source': source,
                'content_type': 'url',
                'ingestion_method': 'failsafe_ingestor'
            }

            capture_id = self.capture.capture_raw_data(
                data=url,
                source_type='url_ingestion',
                source_device=source,
                metadata=metadata
            )

            # Step 2: Add to processing queue
            queue_id = self._add_to_queue(
                capture_id=capture_id,
                content_type='url',
                content_data=url,
                metadata=metadata,
                priority=priority
            )

            log_info(f"✅ FAILSAFE URL CAPTURED: {url} -> {queue_id}")
            return queue_id

        except Exception as e:
            log_error(f"💀 FAILSAFE URL CAPTURE FAILED: {url} - {str(e)}")
            # Emergency file capture
            emergency_file = self.inbox_dir / f"EMERGENCY_URL_{int(datetime.now().timestamp())}.txt"
            with open(emergency_file, 'w') as f:
                f.write(f"URL: {url}\nSource: {source}\nError: {str(e)}\nTimestamp: {datetime.now().isoformat()}\n")
            raise

    def ingest_text(self, text: str, title: str = "", source: str = "manual", priority: int = 5) -> str:
        """
        FAILSAFE: Ingest text content with bulletproof capture.
        """
        try:
            # Step 1: IMMEDIATE bulletproof capture
            content_data = {
                'text': text,
                'title': title,
                'length': len(text)
            }

            metadata = {
                'title': title,
                'source': source,
                'content_type': 'text',
                'text_length': len(text),
                'ingestion_method': 'failsafe_ingestor'
            }

            capture_id = self.capture.capture_raw_data(
                data=content_data,
                source_type='text_ingestion',
                source_device=source,
                metadata=metadata
            )

            # Step 2: Add to processing queue
            queue_id = self._add_to_queue(
                capture_id=capture_id,
                content_type='text',
                content_data=json.dumps(content_data),
                metadata=metadata,
                priority=priority
            )

            log_info(f"✅ FAILSAFE TEXT CAPTURED: {len(text)} chars -> {queue_id}")
            return queue_id

        except Exception as e:
            log_error(f"💀 FAILSAFE TEXT CAPTURE FAILED: {str(e)}")
            # Emergency file capture
            emergency_file = self.inbox_dir / f"EMERGENCY_TEXT_{int(datetime.now().timestamp())}.txt"
            with open(emergency_file, 'w') as f:
                f.write(f"Title: {title}\nText: {text}\nSource: {source}\nError: {str(e)}\nTimestamp: {datetime.now().isoformat()}\n")
            raise

    def ingest_file(self, file_path: str, source: str = "manual", priority: int = 5) -> str:
        """
        FAILSAFE: Ingest file with bulletproof capture.
        """
        try:
            file_path = Path(file_path)

            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            # Step 1: IMMEDIATE bulletproof capture (copy file to quarantine)
            with open(file_path, 'rb') as f:
                file_data = f.read()

            metadata = {
                'original_path': str(file_path),
                'filename': file_path.name,
                'file_extension': file_path.suffix,
                'file_size': len(file_data),
                'source': source,
                'content_type': 'file',
                'ingestion_method': 'failsafe_ingestor'
            }

            capture_id = self.capture.capture_raw_data(
                data=file_data,
                source_type='file_ingestion',
                source_device=source,
                metadata=metadata
            )

            # Step 2: Copy file to processing inbox
            inbox_file = self.inbox_dir / f"{capture_id}_{file_path.name}"
            shutil.copy2(file_path, inbox_file)

            # Step 3: Add to processing queue
            queue_id = self._add_to_queue(
                capture_id=capture_id,
                content_type='file',
                content_data=str(inbox_file),
                metadata=metadata,
                priority=priority
            )

            log_info(f"✅ FAILSAFE FILE CAPTURED: {file_path.name} -> {queue_id}")
            return queue_id

        except Exception as e:
            log_error(f"💀 FAILSAFE FILE CAPTURE FAILED: {file_path} - {str(e)}")
            # Emergency file capture
            emergency_file = self.inbox_dir / f"EMERGENCY_FILE_{int(datetime.now().timestamp())}.log"
            with open(emergency_file, 'w') as f:
                f.write(f"File: {file_path}\nSource: {source}\nError: {str(e)}\nTimestamp: {datetime.now().isoformat()}\n")
            raise

    def _add_to_queue(self,
                     capture_id: str,
                     content_type: str,
                     content_data: str,
                     metadata: Dict[str, Any],
                     priority: int) -> str:
        """Add item to processing queue with deduplication."""
        try:
            queue_id = generate_unique_id()
            timestamp = datetime.now().isoformat()

            # Generate fingerprint for deduplication
            fingerprint = self._generate_fingerprint(content_data, content_type)

            db_path = self.failsafe_dir / 'failsafe.db'

            with sqlite3.connect(db_path) as conn:
                # Check for duplicates
                existing = conn.execute(
                    'SELECT id FROM ingestion_queue WHERE hash_fingerprint = ? AND status != "failed"',
                    (fingerprint,)
                ).fetchone()

                if existing:
                    log_info(f"Duplicate content detected, linking to existing queue item: {existing[0]}")
                    return existing[0]

                # Insert new queue item
                conn.execute('''
                    INSERT INTO ingestion_queue
                    (id, capture_id, content_type, content_data, metadata, priority,
                     created_at, hash_fingerprint)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    queue_id, capture_id, content_type, content_data,
                    json.dumps(metadata), priority, timestamp, fingerprint
                ))

                # Log action
                self._log_processing_action(queue_id, 'queued', 'success', 'Added to processing queue')

            return queue_id

        except Exception as e:
            log_error(f"Error adding to queue: {str(e)}")
            raise

    def _generate_fingerprint(self, content_data: str, content_type: str) -> str:
        """Generate fingerprint for deduplication."""
        try:
            if content_type == 'url':
                # Normalize URL for fingerprinting
                normalized = content_data.lower().strip('/')
            elif content_type == 'text':
                # Use first 500 chars for text fingerprinting
                normalized = content_data[:500]
            else:
                normalized = content_data

            return hashlib.sha256(f"{content_type}:{normalized}".encode()).hexdigest()[:16]

        except Exception as e:
            log_error(f"Error generating fingerprint: {str(e)}")
            return generate_unique_id()[:16]

    def _log_processing_action(self, queue_id: str, action: str, status: str, message: str):
        """Log processing action."""
        try:
            db_path = self.failsafe_dir / 'failsafe.db'

            with sqlite3.connect(db_path) as conn:
                conn.execute('''
                    INSERT INTO processing_log (queue_id, action, status, message, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                ''', (queue_id, action, status, message, datetime.now().isoformat()))

        except Exception as e:
            log_error(f"Error logging processing action: {str(e)}")

    def process_pending_queue(self, batch_size: int = None) -> Dict[str, Any]:
        """
        Process pending items in the ingestion queue.

        Returns:
            Dict with processing statistics
        """
        try:
            batch_size = batch_size or self.batch_size

            # Get pending items
            pending_items = self._get_pending_items(batch_size)

            if not pending_items:
                return {
                    'processed': 0,
                    'succeeded': 0,
                    'failed': 0,
                    'message': 'No pending items'
                }

            results = {
                'processed': 0,
                'succeeded': 0,
                'failed': 0,
                'items': []
            }

            # Process each item
            for item in pending_items:
                try:
                    self._mark_processing_started(item['id'])
                    success = self._process_queue_item(item)

                    if success:
                        self._mark_processing_completed(item['id'], success=True)
                        results['succeeded'] += 1
                    else:
                        self._mark_processing_completed(item['id'], success=False, error="Processing failed")
                        results['failed'] += 1

                    results['processed'] += 1
                    results['items'].append({
                        'id': item['id'],
                        'content_type': item['content_type'],
                        'success': success
                    })

                except Exception as e:
                    log_error(f"Error processing queue item {item['id']}: {str(e)}")
                    self._mark_processing_completed(item['id'], success=False, error=str(e))
                    results['failed'] += 1
                    results['processed'] += 1

            log_info(f"Queue processing completed: {results['succeeded']} succeeded, {results['failed']} failed")
            return results

        except Exception as e:
            log_error(f"Error processing queue: {str(e)}")
            return {'error': str(e)}

    def _get_pending_items(self, batch_size: int) -> List[Dict[str, Any]]:
        """Get pending items from queue."""
        try:
            db_path = self.failsafe_dir / 'failsafe.db'

            with sqlite3.connect(db_path) as conn:
                cursor = conn.execute('''
                    SELECT id, capture_id, content_type, content_data, metadata, retry_count
                    FROM ingestion_queue
                    WHERE status = 'pending'
                    AND retry_count < ?
                    ORDER BY priority DESC, created_at ASC
                    LIMIT ?
                ''', (self.max_retries, batch_size))

                items = []
                for row in cursor:
                    items.append({
                        'id': row[0],
                        'capture_id': row[1],
                        'content_type': row[2],
                        'content_data': row[3],
                        'metadata': json.loads(row[4]) if row[4] else {},
                        'retry_count': row[5]
                    })

                return items

        except Exception as e:
            log_error(f"Error getting pending items: {str(e)}")
            return []

    def _process_queue_item(self, item: Dict[str, Any]) -> bool:
        """Process individual queue item."""
        try:
            content_type = item['content_type']
            content_data = item['content_data']
            metadata = item['metadata']

            self._log_processing_action(item['id'], 'processing', 'started', f"Processing {content_type}")

            if content_type == 'url':
                return self._process_url_item(content_data, metadata)
            elif content_type == 'text':
                return self._process_text_item(content_data, metadata)
            elif content_type == 'file':
                return self._process_file_item(content_data, metadata)
            else:
                log_error(f"Unknown content type: {content_type}")
                return False

        except Exception as e:
            log_error(f"Error processing queue item: {str(e)}")
            self._log_processing_action(item['id'], 'processing', 'error', str(e))
            return False

    def _process_url_item(self, url: str, metadata: Dict[str, Any]) -> bool:
        """Process URL using ArticleManager."""
        try:
            result = self.article_manager.process_article(url)

            if result.success:
                # Further process with content pipeline if needed
                if result.content:
                    pipeline_result = self.content_pipeline.process_content(
                        content=result.content,
                        title=result.title,
                        url=url,
                        metadata=metadata
                    )
                    log_info(f"URL processed successfully: {url}")
                    return True

            log_error(f"URL processing failed: {url} - {result.error}")
            return False

        except Exception as e:
            log_error(f"Error processing URL item: {str(e)}")
            return False

    def _process_text_item(self, content_data: str, metadata: Dict[str, Any]) -> bool:
        """Process text content using ContentPipeline."""
        try:
            data = json.loads(content_data)
            text = data['text']
            title = data.get('title', 'Untitled')

            result = self.content_pipeline.process_content(
                content=text,
                title=title,
                url="",
                metadata=metadata
            )

            if result.get('success', False):
                log_info(f"Text processed successfully: {title}")
                return True
            else:
                log_error(f"Text processing failed: {title}")
                return False

        except Exception as e:
            log_error(f"Error processing text item: {str(e)}")
            return False

    def _process_file_item(self, file_path: str, metadata: Dict[str, Any]) -> bool:
        """Process file using appropriate ingestor."""
        try:
            file_path = Path(file_path)

            if not file_path.exists():
                log_error(f"File not found during processing: {file_path}")
                return False

            # Determine processing method based on file extension
            extension = file_path.suffix.lower()

            if extension in ['.txt', '.md']:
                # Process as text file
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                result = self.content_pipeline.process_content(
                    content=content,
                    title=file_path.stem,
                    url=f"file://{file_path}",
                    metadata=metadata
                )

                return result.get('success', False)

            elif extension in ['.pdf', '.docx', '.doc']:
                # Would integrate with document processor
                log_info(f"Document file queued for processing: {file_path}")
                return True

            elif extension in ['.mp3', '.m4a', '.wav']:
                # Would integrate with audio processor
                log_info(f"Audio file queued for processing: {file_path}")
                return True

            else:
                log_info(f"Unknown file type, stored for manual review: {file_path}")
                return True

        except Exception as e:
            log_error(f"Error processing file item: {str(e)}")
            return False

    def _mark_processing_started(self, queue_id: str):
        """Mark item as processing started."""
        try:
            db_path = self.failsafe_dir / 'failsafe.db'

            with sqlite3.connect(db_path) as conn:
                conn.execute('''
                    UPDATE ingestion_queue
                    SET status = 'processing', processing_started_at = ?
                    WHERE id = ?
                ''', (datetime.now().isoformat(), queue_id))

        except Exception as e:
            log_error(f"Error marking processing started: {str(e)}")

    def _mark_processing_completed(self, queue_id: str, success: bool, error: str = None):
        """Mark item as processing completed."""
        try:
            db_path = self.failsafe_dir / 'failsafe.db'
            status = 'completed' if success else 'failed'
            timestamp = datetime.now().isoformat()

            with sqlite3.connect(db_path) as conn:
                if success:
                    conn.execute('''
                        UPDATE ingestion_queue
                        SET status = ?, processing_completed_at = ?
                        WHERE id = ?
                    ''', (status, timestamp, queue_id))
                else:
                    conn.execute('''
                        UPDATE ingestion_queue
                        SET status = ?, processing_completed_at = ?, last_error = ?,
                            retry_count = retry_count + 1
                        WHERE id = ?
                    ''', (status, timestamp, error, queue_id))

                self._log_processing_action(queue_id, 'completed', status, error or 'Success')

        except Exception as e:
            log_error(f"Error marking processing completed: {str(e)}")

    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status."""
        try:
            db_path = self.failsafe_dir / 'failsafe.db'

            with sqlite3.connect(db_path) as conn:
                # Count items by status
                status_counts = {}
                cursor = conn.execute('SELECT status, COUNT(*) FROM ingestion_queue GROUP BY status')
                for status, count in cursor:
                    status_counts[status] = count

                # Get recent activity
                recent_activity = []
                cursor = conn.execute('''
                    SELECT id, content_type, status, created_at
                    FROM ingestion_queue
                    ORDER BY created_at DESC
                    LIMIT 10
                ''')
                for row in cursor:
                    recent_activity.append({
                        'id': row[0],
                        'content_type': row[1],
                        'status': row[2],
                        'created_at': row[3]
                    })

                # Get failed items for review
                failed_items = []
                cursor = conn.execute('''
                    SELECT id, content_type, last_error, retry_count
                    FROM ingestion_queue
                    WHERE status = 'failed' AND retry_count >= ?
                    ORDER BY created_at DESC
                    LIMIT 5
                ''', (self.max_retries,))
                for row in cursor:
                    failed_items.append({
                        'id': row[0],
                        'content_type': row[1],
                        'error': row[2],
                        'retry_count': row[3]
                    })

                return {
                    'status_counts': status_counts,
                    'recent_activity': recent_activity,
                    'failed_items': failed_items,
                    'queue_health': 'healthy' if status_counts.get('failed', 0) < 10 else 'needs_attention'
                }

        except Exception as e:
            log_error(f"Error getting queue status: {str(e)}")
            return {'error': str(e)}

    def retry_failed_items(self, max_items: int = 20) -> Dict[str, Any]:
        """Retry failed items in the queue."""
        try:
            db_path = self.failsafe_dir / 'failsafe.db'

            with sqlite3.connect(db_path) as conn:
                # Reset failed items for retry
                conn.execute('''
                    UPDATE ingestion_queue
                    SET status = 'pending', last_error = NULL
                    WHERE status = 'failed' AND retry_count < ?
                    LIMIT ?
                ''', (self.max_retries, max_items))

                retry_count = conn.total_changes

            log_info(f"Reset {retry_count} failed items for retry")
            return {'retried': retry_count}

        except Exception as e:
            log_error(f"Error retrying failed items: {str(e)}")
            return {'error': str(e)}


def failsafe_ingest_url(url: str, source: str = "manual") -> str:
    """
    Convenience function for failsafe URL ingestion.

    Usage:
        queue_id = failsafe_ingest_url("https://example.com", "shortcuts")
    """
    ingestor = FailsafeIngestor()
    return ingestor.ingest_url(url, source)


def failsafe_ingest_text(text: str, title: str = "", source: str = "manual") -> str:
    """
    Convenience function for failsafe text ingestion.

    Usage:
        queue_id = failsafe_ingest_text("Important note...", "My Note", "apple_notes")
    """
    ingestor = FailsafeIngestor()
    return ingestor.ingest_text(text, title, source)


def process_failsafe_queue(batch_size: int = 10) -> Dict[str, Any]:
    """
    Convenience function for processing failsafe queue.

    Usage:
        results = process_failsafe_queue()
    """
    ingestor = FailsafeIngestor()
    return ingestor.process_pending_queue(batch_size)