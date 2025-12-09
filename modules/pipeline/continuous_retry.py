#!/usr/bin/env python3
"""
Continuous Content Retry Runner

Runs the content validator/retry pipeline in a loop, processing 100 items at a time
until all failures have been attempted. Designed to run continuously.

Usage:
    python modules/pipeline/continuous_retry.py          # Run until complete
    python modules/pipeline/continuous_retry.py --batch 50   # Custom batch size
    python modules/pipeline/continuous_retry.py --forever    # Never stop, re-scan periodically
"""

import asyncio
import logging
import time
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from modules.pipeline.content_validator import ContentValidator, ContentRetryPipeline

logger = logging.getLogger(__name__)


class ContinuousRetryRunner:
    """Continuously retry failed content in batches"""

    def __init__(self, batch_size: int = 100, content_type: str = "article"):
        self.batch_size = batch_size
        self.content_type = content_type
        self.total_stats = {
            'batches_run': 0,
            'total_attempted': 0,
            'total_improved': 0,
            'total_still_failed': 0,
            'started_at': datetime.now().isoformat(),
        }

    async def run_batch(self) -> int:
        """Run a single batch. Returns number of items in queue after this batch."""
        # Scan for failures
        validator = ContentValidator()
        validator.scan_content(self.content_type)

        queue_size = len(validator.retry_queue)
        if queue_size == 0:
            return 0

        print(f"\n{'='*60}")
        print(f"BATCH {self.total_stats['batches_run'] + 1}")
        print(f"Queue size: {queue_size} | Processing: {min(self.batch_size, queue_size)}")
        print(f"{'='*60}")

        # Process batch
        pipeline = ContentRetryPipeline()
        await pipeline.retry_all(validator.retry_queue, limit=self.batch_size)

        # Update totals
        self.total_stats['batches_run'] += 1
        self.total_stats['total_attempted'] += pipeline.stats['attempted']
        self.total_stats['total_improved'] += pipeline.stats['content_improved']
        self.total_stats['total_still_failed'] += pipeline.stats['still_failed']

        # Return remaining queue size
        remaining = queue_size - min(self.batch_size, queue_size)
        return remaining

    async def run_until_done(self):
        """Run batches until no more items to retry"""
        print(f"\n{'#'*60}")
        print("CONTINUOUS CONTENT RETRY - STARTING")
        print(f"Batch size: {self.batch_size}")
        print(f"Started: {self.total_stats['started_at']}")
        print(f"{'#'*60}\n")

        while True:
            remaining = await self.run_batch()

            if remaining == 0:
                break

            # Brief pause between batches
            print(f"\n  Remaining in queue: ~{remaining}")
            print(f"  Pausing 5s before next batch...")
            await asyncio.sleep(5)

        self.print_final_stats()

    async def run_forever(self, rescan_interval: int = 3600):
        """Run forever, rescanning periodically for new failures"""
        print(f"\n{'#'*60}")
        print("CONTINUOUS CONTENT RETRY - FOREVER MODE")
        print(f"Batch size: {self.batch_size}")
        print(f"Rescan interval: {rescan_interval}s")
        print(f"Started: {self.total_stats['started_at']}")
        print(f"{'#'*60}\n")

        while True:
            # Process all current failures
            while True:
                remaining = await self.run_batch()
                if remaining == 0:
                    break
                await asyncio.sleep(5)

            # All done for now
            self.print_final_stats()
            print(f"\n  Queue empty. Sleeping {rescan_interval}s before rescan...")
            await asyncio.sleep(rescan_interval)
            print("\n  Rescanning for new failures...")

    def print_final_stats(self):
        """Print cumulative stats"""
        print(f"\n{'#'*60}")
        print("CUMULATIVE STATS")
        print(f"{'#'*60}")
        print(f"Batches run:      {self.total_stats['batches_run']}")
        print(f"Total attempted:  {self.total_stats['total_attempted']}")
        print(f"Total improved:   {self.total_stats['total_improved']}")
        print(f"Total failed:     {self.total_stats['total_still_failed']}")
        if self.total_stats['total_attempted'] > 0:
            success_rate = self.total_stats['total_improved'] / self.total_stats['total_attempted'] * 100
            print(f"Success rate:     {success_rate:.1f}%")
        print(f"Started:          {self.total_stats['started_at']}")
        print(f"Finished:         {datetime.now().isoformat()}")
        print(f"{'#'*60}\n")


async def main():
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    parser = argparse.ArgumentParser(description="Continuous Content Retry Runner")
    parser.add_argument("--batch", type=int, default=100, help="Batch size (default: 100)")
    parser.add_argument("--forever", action="store_true", help="Run forever, rescanning periodically")
    parser.add_argument("--rescan", type=int, default=3600, help="Rescan interval in seconds (default: 3600)")
    parser.add_argument("--type", type=str, default="article", help="Content type to process")
    args = parser.parse_args()

    runner = ContinuousRetryRunner(batch_size=args.batch, content_type=args.type)

    if args.forever:
        await runner.run_forever(rescan_interval=args.rescan)
    else:
        await runner.run_until_done()


if __name__ == "__main__":
    asyncio.run(main())
