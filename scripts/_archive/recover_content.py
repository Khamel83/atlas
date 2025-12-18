#!/usr/bin/env python3
"""
Recover Bad Content - Re-fetch content that failed quality checks.

Reads all 'bad' files from verification database, extracts source URLs,
and attempts recovery using the full robust_fetcher cascade.

Usage:
    python scripts/recover_content.py              # Process all bad files
    python scripts/recover_content.py --limit 50   # First 50 files
    python scripts/recover_content.py --dry-run    # Preview only
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

from modules.quality import verify_file, QualityLevel
from modules.ingest.robust_fetcher import RobustFetcher

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DB_PATH = Path("data/quality/verification.db")
RECOVERY_DB = Path("data/quality/recovery.db")
OUTPUT_DIR = Path("data/content/article")
DELAY_SECONDS = 5


def init_recovery_db():
    """Initialize recovery tracking database."""
    conn = sqlite3.connect(RECOVERY_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS recovery_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT,
            source_url TEXT,
            original_issues TEXT,
            attempt_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',
            recovery_method TEXT,
            new_file_path TEXT,
            reason TEXT,
            attempted_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON recovery_attempts(status)")
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
            r'^(https?://[^\s\n]+)',  # First line might be URL
        ]
        for pattern in patterns:
            match = re.search(pattern, content, re.MULTILINE)
            if match:
                return match.group(1).strip()
    except Exception as e:
        logger.error(f"Error extracting URL from {file_path}: {e}")
    return None


def get_bad_files() -> list:
    """Get all bad files from verification database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT file_path, issues FROM verifications WHERE quality = 'bad'
    """).fetchall()
    conn.close()
    return [(row['file_path'], row['issues']) for row in rows]


def mark_recovery_attempt(file_path: str, source_url: str, issues: str,
                         status: str, method: str = None, new_path: str = None,
                         reason: str = None):
    """Record a recovery attempt."""
    conn = sqlite3.connect(RECOVERY_DB)

    # Check if exists
    existing = conn.execute(
        "SELECT id, attempt_count FROM recovery_attempts WHERE file_path = ?",
        (file_path,)
    ).fetchone()

    if existing:
        conn.execute("""
            UPDATE recovery_attempts
            SET attempt_count = ?, status = ?, recovery_method = ?,
                new_file_path = ?, reason = ?, attempted_at = ?
            WHERE file_path = ?
        """, (existing[1] + 1, status, method, new_path, reason,
              datetime.now().isoformat(), file_path))
    else:
        conn.execute("""
            INSERT INTO recovery_attempts
            (file_path, source_url, original_issues, status, recovery_method,
             new_file_path, reason, attempted_at, attempt_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (file_path, source_url, issues, status, method, new_path,
              reason, datetime.now().isoformat()))

    conn.commit()
    conn.close()


def attempt_recovery(file_path: str, source_url: str, issues: str) -> bool:
    """Attempt to recover content for a bad file."""
    logger.info(f"Attempting recovery: {source_url}")

    fetcher = RobustFetcher(output_base=OUTPUT_DIR)

    try:
        result = fetcher.fetch(source_url)

        if result.success and result.output_dir:
            content_file = Path(result.output_dir) / 'content.md'
            if content_file.exists():
                qresult = verify_file(content_file, 'article')

                if qresult.quality != QualityLevel.BAD:
                    mark_recovery_attempt(
                        file_path, source_url, issues,
                        status='recovered',
                        method=result.method,
                        new_path=str(result.output_dir)
                    )
                    logger.info(f"  RECOVERED via {result.method}")
                    return True
                else:
                    mark_recovery_attempt(
                        file_path, source_url, issues,
                        status='unrecoverable',
                        method=result.method,
                        reason=f"Re-fetched but still bad quality: {qresult.issues}"
                    )
                    logger.warning(f"  Still bad after re-fetch: {qresult.issues}")
                    return False

        # Fetch failed
        mark_recovery_attempt(
            file_path, source_url, issues,
            status='unrecoverable',
            reason=result.error or "Fetch failed"
        )
        logger.warning(f"  Fetch failed: {result.error}")
        return False

    except Exception as e:
        mark_recovery_attempt(
            file_path, source_url, issues,
            status='error',
            reason=str(e)
        )
        logger.error(f"  Error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Recover bad content')
    parser.add_argument('--limit', type=int, help='Max files to process')
    parser.add_argument('--dry-run', action='store_true', help='Preview only')
    parser.add_argument('--skip-no-url', action='store_true',
                       help='Skip files without extractable URLs')
    args = parser.parse_args()

    init_recovery_db()

    bad_files = get_bad_files()
    logger.info(f"Found {len(bad_files)} bad files")

    if args.limit:
        bad_files = bad_files[:args.limit]

    # Extract URLs and categorize
    with_url = []
    without_url = []

    for file_path, issues in bad_files:
        source_url = extract_source_url(file_path)
        if source_url:
            with_url.append((file_path, source_url, issues))
        else:
            without_url.append((file_path, issues))

    logger.info(f"  With extractable URL: {len(with_url)}")
    logger.info(f"  Without URL (cannot recover): {len(without_url)}")

    if args.dry_run:
        logger.info("\n=== DRY RUN ===")
        for file_path, source_url, issues in with_url[:20]:
            logger.info(f"Would recover: {source_url}")
            logger.info(f"  Issues: {issues[:100]}")
        if len(with_url) > 20:
            logger.info(f"  ... and {len(with_url) - 20} more")
        return

    # Mark files without URLs as unrecoverable
    for file_path, issues in without_url:
        mark_recovery_attempt(
            file_path, None, issues,
            status='unrecoverable',
            reason='No source URL found in file'
        )

    if args.skip_no_url:
        logger.info(f"Marked {len(without_url)} files without URL as unrecoverable")

    # Attempt recovery for files with URLs
    recovered = 0
    failed = 0

    for i, (file_path, source_url, issues) in enumerate(with_url):
        logger.info(f"[{i+1}/{len(with_url)}] {file_path}")

        if attempt_recovery(file_path, source_url, issues):
            recovered += 1
        else:
            failed += 1

        if i < len(with_url) - 1:
            time.sleep(DELAY_SECONDS)

    # Summary
    logger.info(f"\n{'='*60}")
    logger.info(f"RECOVERY SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Total bad files: {len(bad_files)}")
    logger.info(f"Without URL (unrecoverable): {len(without_url)}")
    logger.info(f"Attempted: {len(with_url)}")
    logger.info(f"  Recovered: {recovered}")
    logger.info(f"  Failed: {failed}")

    # Generate report
    conn = sqlite3.connect(RECOVERY_DB)
    stats = conn.execute("""
        SELECT status, COUNT(*) as cnt FROM recovery_attempts GROUP BY status
    """).fetchall()
    conn.close()

    logger.info(f"\nRecovery database status:")
    for status, count in stats:
        logger.info(f"  {status}: {count}")


if __name__ == '__main__':
    main()
