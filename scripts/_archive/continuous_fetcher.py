#!/usr/bin/env python3
"""
Continuous Transcript Fetcher

Dead simple: fetch transcripts in small batches, forever.
No timers, no complexity. Just keeps going.

Usage:
    python scripts/continuous_fetcher.py

Runs as systemd service: atlas-continuous-fetcher.service
"""

import re
import subprocess
import sys
import time
import logging
from datetime import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/var/log/atlas/continuous-fetcher.log')
    ]
)
logger = logging.getLogger(__name__)

# Config
BATCH_SIZE = 10  # Small batches = fast completion = less chance of timeout
SLEEP_BETWEEN_BATCHES = 30  # seconds - give the system a breather
SLEEP_ON_ERROR = 60  # seconds - back off on errors
SLEEP_WHEN_DONE = 300  # 5 minutes - when no pending episodes left

VENV_PYTHON = Path(__file__).parent.parent / "venv" / "bin" / "python"
WORKING_DIR = Path(__file__).parent.parent


def check_proxy():
    """Quick proxy health check."""
    try:
        result = subprocess.run(
            [str(VENV_PYTHON), "scripts/check_proxy_health.py", "-q"],
            cwd=WORKING_DIR,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0
    except Exception as e:
        logger.warning(f"Proxy check failed: {e}")
        return False


def fix_proxy():
    """Try to fix proxy by rotating VPN."""
    logger.info("Attempting to fix proxy...")
    try:
        result = subprocess.run(
            [str(VENV_PYTHON), "scripts/check_proxy_health.py", "--fix"],
            cwd=WORKING_DIR,
            capture_output=True,
            text=True,
            timeout=120
        )
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Proxy fix failed: {e}")
        return False


def get_pending_count():
    """Get count of pending episodes."""
    try:
        result = subprocess.run(
            [str(VENV_PYTHON), "-m", "modules.podcasts.cli", "status"],
            cwd=WORKING_DIR,
            capture_output=True,
            text=True,
            timeout=30
        )
        # Parse output for pending count
        for line in result.stdout.split('\n'):
            if 'Pending' in line:
                # Extract number from line like "║  Pending (to do):             2,350  ⏳"
                # Number may have commas for thousands
                match = re.search(r'[\d,]+', line.split(':')[-1])
                if match:
                    return int(match.group().replace(',', ''))
        return 0
    except Exception as e:
        logger.warning(f"Failed to get pending count: {e}")
        return -1  # Unknown


def fetch_batch():
    """Fetch one batch of transcripts. Returns True if ran successfully."""
    try:
        # Just run it and let it do its thing - no timeout, let it finish
        result = subprocess.run(
            [str(VENV_PYTHON), "-m", "modules.podcasts.cli", "fetch-transcripts",
             "--all", "--limit", str(BATCH_SIZE)],
            cwd=WORKING_DIR,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minutes max per batch (10 episodes = 1 min each)
            env={
                **subprocess.os.environ,
                "YOUTUBE_PROXY_URL": "http://localhost:8118",
                "YOUTUBE_RATE_LIMIT_SECONDS": "5",  # 5s rate limit with proxy (was 30s)
            }
        )

        # Log the output so we can see what happened
        if result.stdout:
            for line in result.stdout.split('\n'):
                if line.strip() and ('Fetched' in line or '✅' in line or '❌' in line or '🎯' in line):
                    logger.info(f"  {line.strip()}")

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        logger.error("Batch timed out after 10 minutes - will retry")
        return False
    except Exception as e:
        logger.error(f"Batch error: {e}")
        return False


def main():
    logger.info("=" * 60)
    logger.info("Starting continuous transcript fetcher")
    logger.info(f"Batch size: {BATCH_SIZE}, Sleep between: {SLEEP_BETWEEN_BATCHES}s")
    logger.info("=" * 60)

    consecutive_errors = 0

    while True:
        try:
            # Check how many pending
            pending = get_pending_count()

            if pending == 0:
                logger.info("No pending episodes!")
                logger.info(f"Sleeping {SLEEP_WHEN_DONE}s before checking again...")
                time.sleep(SLEEP_WHEN_DONE)
                continue

            if pending > 0:
                logger.info(f"Pending episodes: {pending}")

            # Quick proxy check (don't fix unless we have errors)
            if consecutive_errors >= 3:
                logger.warning(f"Too many consecutive errors ({consecutive_errors}), checking proxy...")
                if not check_proxy():
                    fix_proxy()
                consecutive_errors = 0
                time.sleep(SLEEP_ON_ERROR)
                continue

            # Fetch a batch
            logger.info(f"Fetching batch of {BATCH_SIZE}...")
            ok = fetch_batch()

            if ok:
                consecutive_errors = 0
                logger.info("Batch complete")
                time.sleep(SLEEP_BETWEEN_BATCHES)
            else:
                consecutive_errors += 1
                logger.warning(f"Batch issue (#{consecutive_errors}) - continuing anyway")
                time.sleep(SLEEP_ON_ERROR)

        except KeyboardInterrupt:
            logger.info("\nStopped by user")
            sys.exit(0)
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            consecutive_errors += 1
            time.sleep(SLEEP_ON_ERROR)


if __name__ == "__main__":
    main()
