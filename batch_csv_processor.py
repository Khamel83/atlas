#!/usr/bin/env python3
"""
Batch CSV Processor for Atlas

Processes CSV files with URL-ID mappings in series, ensuring proper deduplication
and terminal status tracking for re-imported content.

Example CSV format:
url,id,title
https://example.com/article1,uuid-123,Article Title 1
https://example.com/article2,uuid-456,Article Title 2
"""

import csv
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import uuid
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.content_pipeline import ContentPipeline
from helpers.content_transactions import ContentTransactionSystem
from helpers.numeric_stages import NumericStage

logger = logging.getLogger(__name__)

class BatchCSVProcessor:
    """
    Processes CSV files in series with proper deduplication and batch tracking.

    Key Features:
    - Each CSV file gets a unique batch_id
    - Processes URLs in series (one at a time)
    - Marks duplicates with terminal status (599)
    - Tracks which batch each item came from
    - Provides completion reports per batch
    """

    def __init__(self, db_path: str = "data/atlas.db"):
        self.db_path = db_path
        self.pipeline = ContentPipeline(db_path)
        self.transaction_system = ContentTransactionSystem(db_path)

    def process_csv_file(self, csv_path: str, batch_id: str = None) -> Dict[str, Any]:
        """
        Process a CSV file with URL-ID mappings.

        Args:
            csv_path: Path to CSV file
            batch_id: Optional batch ID, generates one if not provided

        Returns:
            Batch processing results with statistics
        """
        if not batch_id:
            batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        logger.info(f"📊 Starting batch processing: {batch_id}")
        logger.info(f"📁 CSV file: {csv_path}")

        # Set batch ID for deduplication tracking
        self.pipeline.current_batch_id = batch_id

        results = {
            "batch_id": batch_id,
            "csv_file": csv_path,
            "started_at": datetime.now().isoformat(),
            "total_rows": 0,
            "processed": 0,
            "duplicates": 0,
            "failed": 0,
            "new_content": 0,
            "items": []
        }

        try:
            with open(csv_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)

                if not reader.fieldnames:
                    raise ValueError("CSV file has no headers")

                # Validate required columns
                if 'url' not in reader.fieldnames:
                    raise ValueError("CSV must contain 'url' column")

                url_column = 'url'
                id_column = 'id' if 'id' in reader.fieldnames else None
                title_column = 'title' if 'title' in reader.fieldnames else None

                logger.info(f"📋 CSV columns: {reader.fieldnames}")
                logger.info(f"🔗 Using URL column: {url_column}")
                if id_column:
                    logger.info(f"🆔 Using ID column: {id_column}")
                if title_column:
                    logger.info(f"📰 Using title column: {title_column}")

                for row_num, row in enumerate(reader, 1):
                    try:
                        url = row[url_column].strip()
                        if not url:
                            logger.warning(f"⚠️ Row {row_num}: Empty URL, skipping")
                            continue

                        # Extract metadata
                        item_id = row[id_column].strip() if id_column and row.get(id_column) else f"{batch_id}_row_{row_num}"
                        title = row[title_column].strip() if title_column and row.get(title_column) else ""

                        logger.info(f"🔄 Processing row {row_num}: {url[:80]}{'...' if len(url) > 80 else ''}")

                        # Process URL through pipeline (handles deduplication automatically)
                        result = self.pipeline.process_url_job(
                            job_id=item_id,
                            url=url,
                            source=f"batch_{batch_id}"
                        )

                        # Track result
                        item_result = {
                            "row_num": row_num,
                            "url": url,
                            "item_id": item_id,
                            "title": title,
                            "success": result.get("success", False),
                            "content_id": result.get("content_id"),
                            "final_stage": str(result.get("final_stage", "")),
                            "quality_score": result.get("quality_score", 0),
                            "word_count": result.get("word_count", 0),
                            "message": result.get("message", ""),
                            "is_duplicate": result.get("terminal_status") == "duplicate",
                            "duplicate_of": result.get("duplicate_of")
                        }

                        results["items"].append(item_result)
                        results["processed"] += 1

                        if result.get("success"):
                            if result.get("terminal_status") == "duplicate":
                                results["duplicates"] += 1
                                logger.info(f"✅ Row {row_num}: Marked as duplicate (terminal status)")
                            else:
                                results["new_content"] += 1
                                logger.info(f"✅ Row {row_num}: New content processed")
                        else:
                            results["failed"] += 1
                            logger.error(f"❌ Row {row_num}: Processing failed")

                        # Small delay between processing to be respectful
                        time.sleep(0.1)

                    except Exception as e:
                        logger.error(f"❌ Row {row_num}: Error processing row: {e}")
                        results["failed"] += 1
                        results["items"].append({
                            "row_num": row_num,
                            "url": url if 'url' in locals() else "unknown",
                            "success": False,
                            "error": str(e)
                        })

                results["total_rows"] = row_num

        except Exception as e:
            logger.error(f"❌ Batch processing failed: {e}")
            results["error"] = str(e)
            results["success"] = False

        results["completed_at"] = datetime.now().isoformat()
        results["duration_seconds"] = (
            datetime.fromisoformat(results["completed_at"]) -
            datetime.fromisoformat(results["started_at"])
        ).total_seconds()

        # Record batch completion transaction
        self.transaction_system.record_transaction(
            batch_id, NumericStage.CONTENT_ARCHIVED_FINAL.value,
            f"Batch processing completed: {results['processed']}/{results['total_rows']} items",
            success=results.get("failed", 0) == 0,
            metadata={
                "batch_results": {
                    "total": results["total_rows"],
                    "processed": results["processed"],
                    "duplicates": results["duplicates"],
                    "failed": results["failed"],
                    "new_content": results["new_content"]
                },
                "csv_file": csv_path
            }
        )

        logger.info(f"📊 Batch {batch_id} completed:")
        logger.info(f"   Total rows: {results['total_rows']}")
        logger.info(f"   Processed: {results['processed']}")
        logger.info(f"   New content: {results['new_content']}")
        logger.info(f"   Duplicates: {results['duplicates']} (terminal status)")
        logger.info(f"   Failed: {results['failed']}")
        logger.info(f"   Duration: {results['duration_seconds']:.1f}s")

        return results

    def get_batch_status(self, batch_id: str) -> Dict[str, Any]:
        """Get current status of a batch by its batch_id"""
        # Get all transactions for this batch
        transactions = self.transaction_system.get_recent_activity(minutes=1440)  # Last 24 hours

        batch_transactions = [
            t for t in transactions
            if t.get("metadata", {}).get("batch_id") == batch_id
        ]

        if not batch_transactions:
            return {"error": "Batch not found", "batch_id": batch_id}

        # Calculate batch statistics
        total_items = len([t for t in batch_transactions if "Duplicate content detected" in t["action"]])
        duplicates = len([t for t in batch_transactions if t["stage"] == NumericStage.CONTENT_DUPLICATE.value])
        failures = len([t for t in batch_transactions if not t["success"]])

        return {
            "batch_id": batch_id,
            "total_items": total_items,
            "duplicates": duplicates,
            "failed": failures,
            "success_rate": ((total_items - failures) / total_items * 100) if total_items > 0 else 0,
            "transaction_count": len(batch_transactions),
            "last_activity": batch_transactions[0]["timestamp"] if batch_transactions else None
        }

def main():
    """Command line interface for batch CSV processing"""
    import argparse

    parser = argparse.ArgumentParser(description="Atlas Batch CSV Processor")
    parser.add_argument("csv_file", help="Path to CSV file containing URLs")
    parser.add_argument("--batch-id", help="Custom batch ID (optional)")
    parser.add_argument("--status", help="Check status of a batch ID")
    parser.add_argument("--output", help="Save results to JSON file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    processor = BatchCSVProcessor()

    if args.status:
        # Check batch status
        status = processor.get_batch_status(args.status)
        print(f"📊 Batch Status: {args.status}")
        print(json.dumps(status, indent=2, default=str))
        return

    if not Path(args.csv_file).exists():
        print(f"❌ CSV file not found: {args.csv_file}")
        return

    # Process CSV file
    print(f"🚀 Starting batch processing for: {args.csv_file}")
    results = processor.process_csv_file(args.csv_file, args.batch_id)

    # Display results
    print(f"\n📊 Batch Processing Results: {results['batch_id']}")
    print(f"   CSV File: {results['csv_file']}")
    print(f"   Total Rows: {results['total_rows']}")
    print(f"   Processed: {results['processed']}")
    print(f"   New Content: {results['new_content']}")
    print(f"   Duplicates: {results['duplicates']} (terminal status)")
    print(f"   Failed: {results['failed']}")
    print(f"   Duration: {results['duration_seconds']:.1f}s")

    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"💾 Results saved to: {args.output}")

if __name__ == "__main__":
    main()