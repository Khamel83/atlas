#!/usr/bin/env python3
"""
Recover Marginal Content - Re-fetch content that failed quality thresholds.

Most "marginal" content (50-99 words, etc.) is actually a FAILED FETCH that
grabbed metadata/navigation instead of article body. This script aggressively
re-fetches to get real content.

Usage:
    python scripts/recover_marginal.py              # Process all marginal files
    python scripts/recover_marginal.py --limit 50   # First 50 files
    python scripts/recover_marginal.py --dry-run    # Preview only
    python scripts/recover_marginal.py --js-only    # Only JS-blocked files
"""

import argparse
import json
import logging
import re
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.quality import verify_file, verify_content, QualityLevel
from modules.ingest.robust_fetcher import RobustFetcher

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

VERIFICATION_DB = Path("data/quality/verification.db")
RECOVERY_DB = Path("data/quality/marginal_recovery.db")
OUTPUT_DIR = Path("data/content/article")
DELAY_SECONDS = 5


def init_recovery_db():
    """Initialize marginal recovery tracking database."""
    RECOVERY_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(RECOVERY_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS marginal_recovery (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT UNIQUE,
            source_url TEXT,
            original_word_count INTEGER,
            original_issues TEXT,
            attempt_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',
            recovery_method TEXT,
            new_file_path TEXT,
            new_word_count INTEGER,
            new_quality TEXT,
            reason TEXT,
            attempted_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON marginal_recovery(status)")
    conn.commit()
    conn.close()


def extract_source_url(file_path: str) -> str | None:
    """Extract source URL from file content."""
    try:
        content = Path(file_path).read_text()
        # Look for Source: URL or URL: patterns
        patterns = [
            r'Source:\s*(https?://[^\s\n]+)',
            r'\*\*URL:\*\*\s*(https?://[^\s\n]+)',
            r'URL:\s*(https?://[^\s\n]+)',
            r'Episode:\s*(https?://[^\s\n]+)',
            r'^(https?://[^\s\n]+)',  # First line might be URL
        ]
        for pattern in patterns:
            match = re.search(pattern, content, re.MULTILINE)
            if match:
                return match.group(1).strip()
    except Exception as e:
        logger.error(f"Error extracting URL from {file_path}: {e}")
    return None


def get_marginal_files(js_only: bool = False) -> list:
    """Get all marginal files from verification database."""
    conn = sqlite3.connect(VERIFICATION_DB)
    conn.row_factory = sqlite3.Row

    if js_only:
        # Only files that failed no_js_block check
        rows = conn.execute("""
            SELECT file_path, word_count, issues, checks_failed
            FROM verifications
            WHERE quality = 'marginal' AND checks_failed LIKE '%no_js_block%'
        """).fetchall()
    else:
        rows = conn.execute("""
            SELECT file_path, word_count, issues, checks_failed
            FROM verifications
            WHERE quality = 'marginal'
        """).fetchall()

    conn.close()
    return [(row['file_path'], row['word_count'], row['issues'], row['checks_failed']) for row in rows]


def already_attempted(file_path: str) -> bool:
    """Check if we already attempted recovery for this file."""
    conn = sqlite3.connect(RECOVERY_DB)
    exists = conn.execute(
        "SELECT 1 FROM marginal_recovery WHERE file_path = ?", (file_path,)
    ).fetchone()
    conn.close()
    return exists is not None


def mark_recovery_attempt(file_path: str, source_url: str, word_count: int, issues: str,
                         status: str, method: str = None, new_path: str = None,
                         new_word_count: int = None, new_quality: str = None,
                         reason: str = None):
    """Record a recovery attempt."""
    conn = sqlite3.connect(RECOVERY_DB)

    # Check if exists
    existing = conn.execute(
        "SELECT id, attempt_count FROM marginal_recovery WHERE file_path = ?",
        (file_path,)
    ).fetchone()

    if existing:
        conn.execute("""
            UPDATE marginal_recovery
            SET attempt_count = ?, status = ?, recovery_method = ?,
                new_file_path = ?, new_word_count = ?, new_quality = ?,
                reason = ?, attempted_at = ?
            WHERE file_path = ?
        """, (existing[1] + 1, status, method, new_path, new_word_count,
              new_quality, reason, datetime.now().isoformat(), file_path))
    else:
        conn.execute("""
            INSERT INTO marginal_recovery
            (file_path, source_url, original_word_count, original_issues,
             status, recovery_method, new_file_path, new_word_count, new_quality,
             reason, attempted_at, attempt_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (file_path, source_url, word_count, issues, status, method,
              new_path, new_word_count, new_quality, reason, datetime.now().isoformat()))

    conn.commit()
    conn.close()


def attempt_recovery(file_path: str, source_url: str, word_count: int, issues: str) -> bool:
    """Attempt to recover content for a marginal file."""
    logger.info(f"Attempting recovery: {source_url}")
    logger.info(f"  Original: {word_count} words, issues: {issues[:80]}...")

    fetcher = RobustFetcher(output_base=OUTPUT_DIR)

    try:
        result = fetcher.fetch(source_url)

        if result.success and result.output_dir:
            content_file = Path(result.output_dir) / 'content.md'
            if content_file.exists():
                qresult = verify_file(content_file, 'article')
                new_word_count = qresult.metadata.get('word_count', 0)

                if qresult.quality == QualityLevel.GOOD:
                    mark_recovery_attempt(
                        file_path, source_url, word_count, issues,
                        status='recovered',
                        method=result.method,
                        new_path=str(result.output_dir),
                        new_word_count=new_word_count,
                        new_quality='good'
                    )
                    logger.info(f"  RECOVERED via {result.method}: {new_word_count} words (was {word_count})")
                    return True
                elif qresult.quality == QualityLevel.MARGINAL:
                    # Still marginal - check if at least better
                    if new_word_count > word_count * 1.5:
                        mark_recovery_attempt(
                            file_path, source_url, word_count, issues,
                            status='improved',
                            method=result.method,
                            new_path=str(result.output_dir),
                            new_word_count=new_word_count,
                            new_quality='marginal',
                            reason=f"Improved from {word_count} to {new_word_count} words but still marginal"
                        )
                        logger.info(f"  IMPROVED via {result.method}: {new_word_count} words (was {word_count}) but still marginal")
                        return True
                    else:
                        mark_recovery_attempt(
                            file_path, source_url, word_count, issues,
                            status='still_marginal',
                            method=result.method,
                            new_word_count=new_word_count,
                            new_quality='marginal',
                            reason=f"Re-fetched but still marginal: {qresult.issues}"
                        )
                        logger.warning(f"  Still marginal after re-fetch: {new_word_count} words")
                        return False
                else:
                    mark_recovery_attempt(
                        file_path, source_url, word_count, issues,
                        status='worse',
                        method=result.method,
                        new_word_count=new_word_count,
                        new_quality='bad',
                        reason=f"Re-fetched but now BAD: {qresult.issues}"
                    )
                    logger.warning(f"  WORSE after re-fetch: now BAD quality")
                    return False

        # Fetch failed
        mark_recovery_attempt(
            file_path, source_url, word_count, issues,
            status='fetch_failed',
            reason=result.error or "Fetch failed"
        )
        logger.warning(f"  Fetch failed: {result.error}")
        return False

    except Exception as e:
        mark_recovery_attempt(
            file_path, source_url, word_count, issues,
            status='error',
            reason=str(e)
        )
        logger.error(f"  Error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Recover marginal content')
    parser.add_argument('--limit', type=int, help='Max files to process')
    parser.add_argument('--dry-run', action='store_true', help='Preview only')
    parser.add_argument('--js-only', action='store_true', help='Only process JS-blocked files')
    parser.add_argument('--skip-attempted', action='store_true', default=True,
                       help='Skip files already attempted (default: True)')
    args = parser.parse_args()

    init_recovery_db()

    marginal_files = get_marginal_files(js_only=args.js_only)
    logger.info(f"Found {len(marginal_files)} marginal files")

    if args.limit:
        marginal_files = marginal_files[:args.limit]

    # Extract URLs and categorize
    with_url = []
    without_url = []
    already_done = []

    for file_path, word_count, issues, checks_failed in marginal_files:
        if args.skip_attempted and already_attempted(file_path):
            already_done.append(file_path)
            continue

        source_url = extract_source_url(file_path)
        if source_url:
            with_url.append((file_path, source_url, word_count, issues))
        else:
            without_url.append((file_path, word_count, issues))

    logger.info(f"  With extractable URL: {len(with_url)}")
    logger.info(f"  Without URL (cannot recover): {len(without_url)}")
    logger.info(f"  Already attempted: {len(already_done)}")

    if args.dry_run:
        logger.info("\n=== DRY RUN ===")
        for file_path, source_url, word_count, issues in with_url[:20]:
            logger.info(f"Would recover: {source_url}")
            logger.info(f"  Current: {word_count} words, issues: {issues[:60]}...")
        if len(with_url) > 20:
            logger.info(f"  ... and {len(with_url) - 20} more")
        return

    # Mark files without URLs as unrecoverable
    for file_path, word_count, issues in without_url:
        mark_recovery_attempt(
            file_path, None, word_count, issues,
            status='no_url',
            reason='No source URL found in file'
        )
    logger.info(f"Marked {len(without_url)} files without URL as unrecoverable")

    # Attempt recovery for files with URLs
    recovered = 0
    improved = 0
    failed = 0

    for i, (file_path, source_url, word_count, issues) in enumerate(with_url):
        logger.info(f"[{i+1}/{len(with_url)}] {file_path}")

        result = attempt_recovery(file_path, source_url, word_count, issues)
        if result:
            recovered += 1
        else:
            failed += 1

        if i < len(with_url) - 1:
            time.sleep(DELAY_SECONDS)

    # Summary
    logger.info(f"\n{'='*60}")
    logger.info(f"MARGINAL RECOVERY SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Total marginal files: {len(marginal_files)}")
    logger.info(f"Without URL: {len(without_url)}")
    logger.info(f"Already attempted: {len(already_done)}")
    logger.info(f"Attempted this run: {len(with_url)}")
    logger.info(f"  Recovered/Improved: {recovered}")
    logger.info(f"  Failed: {failed}")

    # Generate report from database
    conn = sqlite3.connect(RECOVERY_DB)
    stats = conn.execute("""
        SELECT status, COUNT(*) as cnt FROM marginal_recovery GROUP BY status
    """).fetchall()
    conn.close()

    logger.info(f"\nRecovery database status:")
    for status, count in stats:
        logger.info(f"  {status}: {count}")


if __name__ == '__main__':
    main()
