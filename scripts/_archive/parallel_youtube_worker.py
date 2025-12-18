#!/usr/bin/env python3
"""
Parallel YouTube Transcript Workers

Runs multiple YouTube transcript fetchers in parallel, each with different rate limiting
to maximize throughput while avoiding bans.

Architecture:
- Worker 1: Direct (no proxy) - for non-blocked IPs
- Worker 2: NordVPN proxy - for blocked content
- Worker 3: Different timing offset - staggered requests

Each worker processes a different subset of podcasts to avoid conflicts.
"""

import argparse
import asyncio
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.podcasts.store import PodcastStore
from modules.podcasts.cli import AtlasPodCLI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class WorkerConfig:
    """Configuration for a single worker"""
    name: str
    proxy_url: Optional[str]
    rate_limit_seconds: int
    podcasts: List[str]  # Podcast slugs this worker handles


# Define worker configurations
WORKER_CONFIGS = [
    WorkerConfig(
        name="worker-direct",
        proxy_url=None,
        rate_limit_seconds=20,
        podcasts=[
            "hard-fork",
            "the-rewatchables",
            "against-the-rules-with-michael-lewis",
        ]
    ),
    WorkerConfig(
        name="worker-proxy-1",
        proxy_url="http://100.112.130.100:8118",  # NordVPN proxy
        rate_limit_seconds=15,
        podcasts=[
            "conversations-with-tyler",
            "revisionist-history",
            "the-knowledge-project-with-shane-parrish",
        ]
    ),
    WorkerConfig(
        name="worker-proxy-2",
        proxy_url="http://100.112.130.100:8118",  # Same proxy, different timing
        rate_limit_seconds=15,
        podcasts=[
            "hyperfixed",
            "the-watch",
            "the-big-picture",
            "asianometry",
        ]
    ),
]


def run_worker(config: WorkerConfig, limit: Optional[int] = None) -> dict:
    """Run a single worker for its assigned podcasts"""
    logger.info(f"[{config.name}] Starting worker")
    logger.info(f"[{config.name}] Proxy: {config.proxy_url or 'None (direct)'}")
    logger.info(f"[{config.name}] Rate limit: {config.rate_limit_seconds}s")
    logger.info(f"[{config.name}] Podcasts: {', '.join(config.podcasts)}")

    # Set environment for this worker
    if config.proxy_url:
        os.environ['YOUTUBE_PROXY_URL'] = config.proxy_url
    elif 'YOUTUBE_PROXY_URL' in os.environ:
        del os.environ['YOUTUBE_PROXY_URL']

    os.environ['YOUTUBE_RATE_LIMIT_SECONDS'] = str(config.rate_limit_seconds)

    results = {
        'worker': config.name,
        'fetched': 0,
        'failed': 0,
        'podcasts_processed': []
    }

    cli = AtlasPodCLI()
    cli.init_store()

    for slug in config.podcasts:
        logger.info(f"[{config.name}] Processing: {slug}")

        try:
            # Create args-like object
            class Args:
                pass

            args = Args()
            args.all = False
            args.slug = slug
            args.status = "unknown,failed"
            args.limit = limit
            args.no_limits = False

            # Run fetch
            cli.cmd_fetch_transcripts(args)

            results['podcasts_processed'].append(slug)

        except Exception as e:
            logger.error(f"[{config.name}] Error processing {slug}: {e}")
            results['failed'] += 1

        # Small delay between podcasts
        time.sleep(2)

    logger.info(f"[{config.name}] Worker complete")
    return results


def run_parallel(max_workers: int = 3, limit: Optional[int] = None):
    """Run all workers in parallel"""
    logger.info(f"Starting {len(WORKER_CONFIGS)} parallel YouTube workers")

    results = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(run_worker, config, limit): config
            for config in WORKER_CONFIGS
        }

        for future in as_completed(futures):
            config = futures[future]
            try:
                result = future.result()
                results.append(result)
                logger.info(f"Worker {config.name} completed: {result}")
            except Exception as e:
                logger.error(f"Worker {config.name} failed: {e}")

    # Summary
    total_fetched = sum(r.get('fetched', 0) for r in results)
    total_failed = sum(r.get('failed', 0) for r in results)

    logger.info(f"""
=== PARALLEL YOUTUBE WORKERS COMPLETE ===
Total fetched: {total_fetched}
Total failed: {total_failed}
Workers: {len(results)}
""")

    return results


def run_sequential(limit: Optional[int] = None):
    """Run workers sequentially (safer, for testing)"""
    logger.info("Running workers sequentially")

    for config in WORKER_CONFIGS:
        run_worker(config, limit)
        time.sleep(5)  # Pause between workers


def main():
    parser = argparse.ArgumentParser(description="Parallel YouTube transcript workers")
    parser.add_argument("--parallel", action="store_true", help="Run workers in parallel")
    parser.add_argument("--sequential", action="store_true", help="Run workers sequentially")
    parser.add_argument("--limit", type=int, help="Limit episodes per podcast")
    parser.add_argument("--workers", type=int, default=3, help="Max parallel workers")
    args = parser.parse_args()

    if args.parallel:
        run_parallel(max_workers=args.workers, limit=args.limit)
    elif args.sequential:
        run_sequential(limit=args.limit)
    else:
        print("Specify --parallel or --sequential")
        print("\nWorker assignments:")
        for config in WORKER_CONFIGS:
            print(f"\n{config.name}:")
            print(f"  Proxy: {config.proxy_url or 'direct'}")
            print(f"  Rate: {config.rate_limit_seconds}s")
            print(f"  Podcasts: {', '.join(config.podcasts)}")


if __name__ == "__main__":
    main()
