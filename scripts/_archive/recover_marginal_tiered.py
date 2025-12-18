#!/usr/bin/env python3
"""
Tiered Marginal Recovery - Process high-priority sources first.

Tier 1 (HIGH): content/article, clean/article, clean/stratechery, stratechery
Tier 2 (MEDIUM): articles from major sites (washingtonpost, nytimes, etc.)
Tier 3 (LOW): podcasts, newsletter, youtube (legitimately short)

Usage:
    python scripts/recover_marginal_tiered.py --tier 1        # High priority only
    python scripts/recover_marginal_tiered.py --tier 1 2      # Tiers 1 and 2
    python scripts/recover_marginal_tiered.py --dry-run       # Preview
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

# Tier definitions
TIER_1_PATTERNS = [
    'data/content/article/%',      # Main articles - likely failed scrapes
    'data/clean/article/%',        # Cleaned copies
    'data/clean/stratechery/%',    # Stratechery cleaned
    'data/stratechery/%',          # Stratechery originals
]

TIER_2_PATTERNS = [
    'data/articles/washingtonpost%',
    'data/articles/nytimes%',
    'data/articles/bloomberg%',
    'data/articles/ft-%',
    'data/articles/wsj%',
    'data/articles/substack%',
]

TIER_3_PATTERNS = [
    'data/podcasts/%',
    'data/clean/podcasts/%',
    'data/clean/newsletter/%',
    'data/clean/youtube/%',
]


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
            tier INTEGER,
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
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tier ON marginal_recovery(tier)")
    conn.commit()
    conn.close()


def get_marginal_files_by_tier(tiers: list) -> list:
    """Get marginal files for specified tiers."""
    conn = sqlite3.connect(VERIFICATION_DB)
    conn.row_factory = sqlite3.Row

    all_files = []

    for tier in tiers:
        if tier == 1:
            patterns = TIER_1_PATTERNS
        elif tier == 2:
            patterns = TIER_2_PATTERNS
        elif tier == 3:
            patterns = TIER_3_PATTERNS
        else:
            continue

        for pattern in patterns:
            rows = conn.execute("""
                SELECT file_path, word_count, issues, checks_failed
                FROM verifications
                WHERE quality = 'marginal' AND file_path LIKE ?
            """, (pattern,)).fetchall()

            for row in rows:
                all_files.append((
                    row['file_path'],
                    row['word_count'],
                    row['issues'],
                    row['checks_failed'],
                    tier
                ))

    conn.close()
    return all_files


def extract_source_url(file_path: str) -> str | None:
    """Extract source URL from file content."""
    try:
        content = Path(file_path).read_text()
        patterns = [
            r'Source:\s*(https?://[^\s\n]+)',
            r'\*\*URL:\*\*\s*(https?://[^\s\n]+)',
            r'URL:\s*(https?://[^\s\n]+)',
            r'Episode:\s*(https?://[^\s\n]+)',
            r'^(https?://[^\s\n]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, content, re.MULTILINE)
            if match:
                return match.group(1).strip()
    except Exception as e:
        logger.error(f"Error extracting URL from {file_path}: {e}")
    return None


def already_attempted(file_path: str) -> bool:
    """Check if we already attempted recovery for this file."""
    conn = sqlite3.connect(RECOVERY_DB)
    exists = conn.execute(
        "SELECT 1 FROM marginal_recovery WHERE file_path = ?", (file_path,)
    ).fetchone()
    conn.close()
    return exists is not None


def mark_recovery_attempt(file_path: str, source_url: str, word_count: int, issues: str,
                         tier: int, status: str, method: str = None, new_path: str = None,
                         new_word_count: int = None, new_quality: str = None,
                         reason: str = None):
    """Record a recovery attempt."""
    conn = sqlite3.connect(RECOVERY_DB)

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
            (file_path, source_url, original_word_count, original_issues, tier,
             status, recovery_method, new_file_path, new_word_count, new_quality,
             reason, attempted_at, attempt_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (file_path, source_url, word_count, issues, tier, status, method,
              new_path, new_word_count, new_quality, reason, datetime.now().isoformat()))

    conn.commit()
    conn.close()


def attempt_recovery(file_path: str, source_url: str, word_count: int,
                    issues: str, tier: int) -> bool:
    """Attempt to recover content for a marginal file."""
    logger.info(f"Attempting recovery: {source_url}")
    logger.info(f"  Original: {word_count} words")

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
                        file_path, source_url, word_count, issues, tier,
                        status='recovered',
                        method=result.method,
                        new_path=str(result.output_dir),
                        new_word_count=new_word_count,
                        new_quality='good'
                    )
                    logger.info(f"  RECOVERED via {result.method}: {new_word_count} words")
                    return True
                elif qresult.quality == QualityLevel.MARGINAL and new_word_count > word_count * 1.5:
                    mark_recovery_attempt(
                        file_path, source_url, word_count, issues, tier,
                        status='improved',
                        method=result.method,
                        new_path=str(result.output_dir),
                        new_word_count=new_word_count,
                        new_quality='marginal',
                        reason=f"Improved {word_count} -> {new_word_count} words"
                    )
                    logger.info(f"  IMPROVED: {word_count} -> {new_word_count} words")
                    return True
                else:
                    mark_recovery_attempt(
                        file_path, source_url, word_count, issues, tier,
                        status='still_marginal',
                        method=result.method,
                        new_word_count=new_word_count,
                        new_quality=qresult.quality.value,
                        reason=f"Re-fetched but {qresult.quality.value}: {new_word_count} words"
                    )
                    logger.warning(f"  Still {qresult.quality.value}: {new_word_count} words")
                    return False

        mark_recovery_attempt(
            file_path, source_url, word_count, issues, tier,
            status='fetch_failed',
            reason=result.error or "Fetch failed"
        )
        logger.warning(f"  Fetch failed: {result.error}")
        return False

    except Exception as e:
        mark_recovery_attempt(
            file_path, source_url, word_count, issues, tier,
            status='error',
            reason=str(e)
        )
        logger.error(f"  Error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Tiered marginal recovery')
    parser.add_argument('--tier', type=int, nargs='+', default=[1],
                       help='Tiers to process (1=high, 2=medium, 3=low)')
    parser.add_argument('--limit', type=int, help='Max files to process')
    parser.add_argument('--dry-run', action='store_true', help='Preview only')
    args = parser.parse_args()

    init_recovery_db()

    logger.info(f"Processing tiers: {args.tier}")

    marginal_files = get_marginal_files_by_tier(args.tier)
    logger.info(f"Found {len(marginal_files)} marginal files in selected tiers")

    if args.limit:
        marginal_files = marginal_files[:args.limit]

    # Extract URLs and categorize
    with_url = []
    without_url = []
    already_done = []

    for file_path, word_count, issues, checks_failed, tier in marginal_files:
        if already_attempted(file_path):
            already_done.append(file_path)
            continue

        source_url = extract_source_url(file_path)
        if source_url:
            with_url.append((file_path, source_url, word_count, issues, tier))
        else:
            without_url.append((file_path, word_count, issues, tier))

    logger.info(f"  With extractable URL: {len(with_url)}")
    logger.info(f"  Without URL: {len(without_url)}")
    logger.info(f"  Already attempted: {len(already_done)}")

    # Tier breakdown
    tier_counts = {}
    for _, _, _, _, tier in with_url:
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
    for tier, count in sorted(tier_counts.items()):
        logger.info(f"  Tier {tier}: {count} files")

    if args.dry_run:
        logger.info("\n=== DRY RUN ===")
        for file_path, source_url, word_count, issues, tier in with_url[:20]:
            logger.info(f"[Tier {tier}] Would recover: {source_url}")
            logger.info(f"  Current: {word_count} words")
        if len(with_url) > 20:
            logger.info(f"  ... and {len(with_url) - 20} more")
        return

    # Mark files without URLs
    for file_path, word_count, issues, tier in without_url:
        mark_recovery_attempt(
            file_path, None, word_count, issues, tier,
            status='no_url',
            reason='No source URL found in file'
        )
    logger.info(f"Marked {len(without_url)} files without URL")

    # Process files with URLs
    recovered = 0
    failed = 0

    for i, (file_path, source_url, word_count, issues, tier) in enumerate(with_url):
        logger.info(f"[{i+1}/{len(with_url)}] Tier {tier}: {file_path}")

        if attempt_recovery(file_path, source_url, word_count, issues, tier):
            recovered += 1
        else:
            failed += 1

        if i < len(with_url) - 1:
            time.sleep(DELAY_SECONDS)

    # Summary
    logger.info(f"\n{'='*60}")
    logger.info(f"TIERED MARGINAL RECOVERY SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Tiers processed: {args.tier}")
    logger.info(f"Total files: {len(marginal_files)}")
    logger.info(f"Without URL: {len(without_url)}")
    logger.info(f"Already attempted: {len(already_done)}")
    logger.info(f"Attempted: {len(with_url)}")
    logger.info(f"  Recovered/Improved: {recovered}")
    logger.info(f"  Failed: {failed}")

    # Database stats
    conn = sqlite3.connect(RECOVERY_DB)
    stats = conn.execute("""
        SELECT tier, status, COUNT(*) as cnt
        FROM marginal_recovery
        GROUP BY tier, status
        ORDER BY tier, status
    """).fetchall()
    conn.close()

    logger.info(f"\nRecovery database by tier:")
    current_tier = None
    for tier, status, count in stats:
        if tier != current_tier:
            logger.info(f"\n  Tier {tier}:")
            current_tier = tier
        logger.info(f"    {status}: {count}")


if __name__ == '__main__':
    main()
