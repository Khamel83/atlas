"""
Queue Processor

This module processes captured items from the processing queue using existing
processing logic. It handles errors gracefully with proper logging and retry
mechanisms.
"""

import json
import logging
import os
import signal
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Dict, List, Optional

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from helpers.config import load_config
from helpers.utils import ensure_directory
from ingest.capture.bulletproof_capture import (BulletproofCapture,
                                                get_capture_status)
from ingest.capture.failure_notifier import (log_processing_failure,
                                             notify_system_error)
from ingest.queue.processing_queue import (ProcessingQueue,
                                           QueueItem)

logger = logging.getLogger(__name__)


class QueueProcessor:
    """Processes items from the capture queue."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize queue processor with configuration."""
        self.config = config or load_config()
        self.processor_id = str(uuid.uuid4())
        self.queue = ProcessingQueue(self.config)
        self.capturer = BulletproofCapture(self.config)

        # Configuration
        self.max_concurrent_processing = self.config.get("MAX_CONCURRENT_PROCESSING", 3)
        self.processing_interval = self.config.get("QUEUE_PROCESSOR_INTERVAL", 30)
        self.max_items_per_run = self.config.get("MAX_ITEMS_PER_RUN", 10)
        self.processor_timeout = self.config.get("PROCESSOR_TIMEOUT_MINUTES", 30)

        # State tracking
        self.running = False
        self.processed_count = 0
        self.failed_count = 0
        self.start_time = None

        # Shutdown handling
        self.shutdown_event = threading.Event()
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.shutdown_event.set()
        self.running = False

    def _get_processor_for_item_type(self, item_type: str):
        """Get appropriate processor for item type."""
        try:
            if item_type == "url":
                return self._process_url_item
            elif item_type == "file":
                # Import file processor based on file type
                return self._process_file_item
            elif item_type == "text":
                # Import text processor
                return self._process_text_item
            else:
                logger.error(f"Unknown item type: {item_type}")
                return None
        except ImportError as e:
            logger.error(f"Failed to import processor for {item_type}: {e}")
            return None

    def _process_url_item(self, queue_item: QueueItem) -> Dict[str, Any]:
        """Process a URL item from the queue."""
        try:
            # Get capture status
            capture_status = get_capture_status(queue_item.capture_id)
            if not capture_status.get("found"):
                return {
                    "success": False,
                    "error": f"Capture not found: {queue_item.capture_id}",
                }

            # Read the captured URL
            primary_path = capture_status.get("primary_path")
            if not primary_path or not os.path.exists(primary_path):
                return {
                    "success": False,
                    "error": f"Captured URL file not found: {primary_path}",
                }

            with open(primary_path, "r") as f:
                url = f.read().strip()

            # Process using existing article fetcher
            from helpers.article_fetcher import fetch_and_save_articles

            # Create temporary input file for processing
            temp_input = f"temp_input_{queue_item.capture_id}.txt"
            try:
                with open(temp_input, "w") as f:
                    f.write(url + "\n")

                # Process the URL
                result = fetch_and_save_articles(temp_input)

                # Clean up temporary file
                if os.path.exists(temp_input):
                    os.remove(temp_input)

                if result.get("success", False):
                    return {
                        "success": True,
                        "result_paths": result.get("processed_files", {}),
                        "processing_info": result,
                    }
                else:
                    return {
                        "success": False,
                        "error": result.get("error", "Unknown processing error"),
                    }

            except Exception as e:
                # Clean up temporary file on error
                if os.path.exists(temp_input):
                    os.remove(temp_input)
                raise e

        except Exception as e:
            logger.error(f"Failed to process URL item {queue_item.capture_id}: {e}")
            return {"success": False, "error": str(e)}

    def _process_file_item(self, queue_item: QueueItem) -> Dict[str, Any]:
        """Process a file item from the queue."""
        try:
            # Get capture status
            capture_status = get_capture_status(queue_item.capture_id)
            if not capture_status.get("found"):
                return {
                    "success": False,
                    "error": f"Capture not found: {queue_item.capture_id}",
                }

            # Get the captured file path
            primary_path = capture_status.get("primary_path")
            if not primary_path or not os.path.exists(primary_path):
                return {
                    "success": False,
                    "error": f"Captured file not found: {primary_path}",
                }

            # Determine file type and process accordingly
            file_ext = os.path.splitext(primary_path)[1].lower()

            if file_ext == ".opml":
                # Process OPML file (podcasts) using the modern PodcastIngestor
                from helpers.config import load_config
                from helpers.podcast_ingestor import ingest_podcasts

                config = load_config()
                ingest_podcasts(config, opml_path=primary_path)
                result = {
                    "success": True,
                    "message": f"Processed OPML file: {primary_path}",
                }
            elif file_ext == ".csv":
                # Process CSV file (Instapaper export)
                from helpers.instapaper_ingestor import process_instapaper_csv

                result = process_instapaper_csv(primary_path)
            elif file_ext in [".txt", ".md"]:
                # Process text file (might contain URLs)
                from helpers.article_fetcher import fetch_and_save_articles

                result = fetch_and_save_articles(primary_path)
            else:
                # Generic file processing
                result = self._process_generic_file(primary_path, queue_item)

            if result.get("success", False):
                return {
                    "success": True,
                    "result_paths": result.get("processed_files", {}),
                    "processing_info": result,
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Unknown processing error"),
                }

        except Exception as e:
            logger.error(f"Failed to process file item {queue_item.capture_id}: {e}")
            return {"success": False, "error": str(e)}

    def _process_text_item(self, queue_item: QueueItem) -> Dict[str, Any]:
        """Process a text item from the queue."""
        try:
            # Get capture status
            capture_status = get_capture_status(queue_item.capture_id)
            if not capture_status.get("found"):
                return {
                    "success": False,
                    "error": f"Capture not found: {queue_item.capture_id}",
                }

            # Read the captured text
            primary_path = capture_status.get("primary_path")
            if not primary_path or not os.path.exists(primary_path):
                return {
                    "success": False,
                    "error": f"Captured text file not found: {primary_path}",
                }

            with open(primary_path, "r", encoding="utf-8") as f:
                text_content = f.read()

            # Process text content
            # This could be enhanced to detect URLs, extract content, etc.
            result = self._process_generic_text(text_content, queue_item)

            if result.get("success", False):
                return {
                    "success": True,
                    "result_paths": result.get("processed_files", {}),
                    "processing_info": result,
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Unknown processing error"),
                }

        except Exception as e:
            logger.error(f"Failed to process text item {queue_item.capture_id}: {e}")
            return {"success": False, "error": str(e)}

    def _process_generic_file(
        self, file_path: str, queue_item: QueueItem
    ) -> Dict[str, Any]:
        """Generic file processing fallback."""
        try:
            # Create a processed copy in the output directory
            output_dir = os.path.join("output", "processed", queue_item.item_type)
            ensure_directory(output_dir)

            filename = os.path.basename(file_path)
            output_path = os.path.join(
                output_dir, f"{queue_item.capture_id}_{filename}"
            )

            # Copy file to processed location
            import shutil

            shutil.copy2(file_path, output_path)

            # Create basic metadata
            metadata = {
                "capture_id": queue_item.capture_id,
                "original_source": queue_item.source,
                "processed_timestamp": datetime.now().isoformat(),
                "file_type": queue_item.item_type,
                "processing_method": "generic_file_copy",
            }

            metadata_path = os.path.join(
                output_dir, f"{queue_item.capture_id}_metadata.json"
            )
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)

            return {
                "success": True,
                "processed_files": {"content": output_path, "metadata": metadata_path},
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _process_generic_text(
        self, text_content: str, queue_item: QueueItem
    ) -> Dict[str, Any]:
        """Generic text processing fallback."""
        try:
            # Create processed text file
            output_dir = os.path.join("output", "processed", "text")
            ensure_directory(output_dir)

            output_path = os.path.join(
                output_dir, f"{queue_item.capture_id}_processed.txt"
            )

            # Save processed text
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(text_content)

            # Create basic metadata
            metadata = {
                "capture_id": queue_item.capture_id,
                "original_source": queue_item.source,
                "processed_timestamp": datetime.now().isoformat(),
                "text_length": len(text_content),
                "processing_method": "generic_text_save",
            }

            metadata_path = os.path.join(
                output_dir, f"{queue_item.capture_id}_metadata.json"
            )
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)

            return {
                "success": True,
                "processed_files": {"content": output_path, "metadata": metadata_path},
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def process_queue_item(self, queue_item: QueueItem) -> Dict[str, Any]:
        """
        Process a single captured item using existing processing logic.

        Args:
            queue_item: Queue item to process

        Returns:
            Dictionary with processing results
        """
        start_time = time.time()

        try:
            logger.info(f"Processing {queue_item.capture_id} ({queue_item.item_type})")

            # Get appropriate processor
            processor = self._get_processor_for_item_type(queue_item.item_type)
            if not processor:
                return {
                    "success": False,
                    "error": f"No processor available for item type: {queue_item.item_type}",
                }

            # Process the item
            result = processor(queue_item)

            # Calculate processing time
            processing_time = time.time() - start_time
            result["processing_time"] = processing_time

            # Update queue status
            if result.get("success", False):
                self.queue.mark_complete(
                    queue_item.capture_id, result.get("result_paths", {})
                )
                self.processed_count += 1
                logger.info(
                    f"Successfully processed {queue_item.capture_id} in {processing_time:.2f}s"
                )
            else:
                error_msg = result.get("error", "Unknown error")
                self.queue.mark_failed(
                    queue_item.capture_id, error_msg, queue_item.processing_attempts
                )
                self.failed_count += 1

                # Log processing failure
                log_processing_failure(
                    queue_item.capture_id,
                    Exception(error_msg),
                    queue_item.processing_attempts,
                    queue_item.item_type,
                )

                logger.error(f"Failed to process {queue_item.capture_id}: {error_msg}")

            return result

        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = str(e)

            # Mark as failed in queue
            self.queue.mark_failed(
                queue_item.capture_id, error_msg, queue_item.processing_attempts
            )
            self.failed_count += 1

            # Log processing failure
            log_processing_failure(
                queue_item.capture_id,
                e,
                queue_item.processing_attempts,
                queue_item.item_type,
            )

            logger.error(f"Exception processing {queue_item.capture_id}: {e}")

            return {
                "success": False,
                "error": error_msg,
                "processing_time": processing_time,
            }

    def run_queue_processor(
        self, max_items: int = None, item_types: List[str] = None
    ) -> Dict[str, Any]:
        """
        Background daemon to process items from queue.

        Args:
            max_items: Maximum number of items to process
            item_types: Optional list of item types to process

        Returns:
            Dictionary with processing statistics
        """
        self.running = True
        self.start_time = datetime.now()
        max_items = max_items or self.max_items_per_run

        logger.info(f"Starting queue processor {self.processor_id}")
        logger.info(f"Max items: {max_items}, Item types: {item_types}")

        try:
            with ThreadPoolExecutor(
                max_workers=self.max_concurrent_processing
            ) as executor:
                futures = []
                items_submitted = 0

                while (
                    self.running
                    and items_submitted < max_items
                    and not self.shutdown_event.is_set()
                ):
                    # Get next item from queue
                    queue_item = self.queue.get_next_item(item_types, self.processor_id)

                    if queue_item is None:
                        # No items available, wait and try again
                        if not futures:  # No active processing
                            logger.info("No items in queue, waiting...")
                            time.sleep(self.processing_interval)
                            continue
                        else:
                            # Wait for some futures to complete
                            time.sleep(1)
                            continue

                    # Submit item for processing
                    future = executor.submit(self.process_queue_item, queue_item)
                    futures.append(future)
                    items_submitted += 1

                    # Process completed futures
                    completed_futures = []
                    for future in futures:
                        if future.done():
                            completed_futures.append(future)

                    # Remove completed futures
                    for future in completed_futures:
                        futures.remove(future)

                    # Respect processing limits
                    if len(futures) >= self.max_concurrent_processing:
                        # Wait for at least one to complete
                        as_completed(futures, timeout=1)

                # Wait for all remaining futures to complete
                logger.info("Waiting for remaining processing to complete...")
                for future in as_completed(
                    futures, timeout=self.processor_timeout * 60
                ):
                    try:
                        future.result()
                    except Exception as e:
                        logger.error(f"Future failed: {e}")
                        self.failed_count += 1

            # Calculate final statistics
            end_time = datetime.now()
            total_time = (end_time - self.start_time).total_seconds()

            stats = {
                "processor_id": self.processor_id,
                "start_time": self.start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "total_time_seconds": total_time,
                "items_processed": self.processed_count,
                "items_failed": self.failed_count,
                "items_submitted": items_submitted,
                "success_rate": self.processed_count / max(items_submitted, 1) * 100,
                "queue_status": self.queue.get_queue_status(),
            }

            logger.info(
                f"Queue processor completed: {self.processed_count} processed, {self.failed_count} failed"
            )
            return stats

        except Exception as e:
            logger.error(f"Queue processor failed: {e}")
            notify_system_error("queue_processor", e, "critical")

            return {
                "processor_id": self.processor_id,
                "error": str(e),
                "items_processed": self.processed_count,
                "items_failed": self.failed_count,
            }
        finally:
            self.running = False

    def process_single_item(self, capture_id: str) -> Dict[str, Any]:
        """
        Process a specific item by capture ID.

        Args:
            capture_id: Capture ID to process

        Returns:
            Processing result
        """
        try:
            # Find item in queue
            items = self.queue._load_queue()
            queue_item = None

            for item in items:
                if item.capture_id == capture_id:
                    queue_item = item
                    break

            if not queue_item:
                return {
                    "success": False,
                    "error": f"Item {capture_id} not found in queue",
                }

            # Process the item
            result = self.process_queue_item(queue_item)

            return result

        except Exception as e:
            logger.error(f"Failed to process single item {capture_id}: {e}")
            return {"success": False, "error": str(e)}

    def get_processor_status(self) -> Dict[str, Any]:
        """Get current processor status."""
        return {
            "processor_id": self.processor_id,
            "running": self.running,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "processed_count": self.processed_count,
            "failed_count": self.failed_count,
            "queue_status": self.queue.get_queue_status(),
        }


# Convenience functions for direct use
def process_queue_item(capture_id: str) -> Dict[str, Any]:
    """Process a single captured item."""
    processor = QueueProcessor()
    return processor.process_single_item(capture_id)


def run_queue_processor(
    max_items: int = None, item_types: List[str] = None
) -> Dict[str, Any]:
    """Run queue processor daemon."""
    processor = QueueProcessor()
    return processor.run_queue_processor(max_items, item_types)


def get_processor_status() -> Dict[str, Any]:
    """Get processor status."""
    processor = QueueProcessor()
    return processor.get_processor_status()


if __name__ == "__main__":
    """Command line interface for queue processor."""
    import argparse

    parser = argparse.ArgumentParser(description="Atlas Queue Processor")
    parser.add_argument(
        "--max-items", type=int, default=10, help="Maximum items to process"
    )
    parser.add_argument("--item-types", nargs="+", help="Item types to process")
    parser.add_argument("--single-item", help="Process single item by capture ID")
    parser.add_argument("--status", action="store_true", help="Show processor status")

    args = parser.parse_args()

    if args.status:
        status = get_processor_status()
        print(json.dumps(status, indent=2))
    elif args.single_item:
        result = process_queue_item(args.single_item)
        print(json.dumps(result, indent=2))
    else:
        result = run_queue_processor(args.max_items, args.item_types)
        print(json.dumps(result, indent=2))
