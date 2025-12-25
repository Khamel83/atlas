#!/usr/bin/env python3
"""
Automated podcast pipeline health check.

Validates all three UID layers are in sync:
1. atlas_podcasts.db - Episode GUIDs and transcript paths
2. atlas_index.db - Content IDs for search
3. File system - Actual .md transcript files

Runs via systemd timer daily to keep pipeline healthy without manual intervention.

Usage:
    ./venv/bin/python scripts/podcast_health_check.py --check    # Report only
    ./venv/bin/python scripts/podcast_health_check.py --fix      # Apply fixes
"""

import argparse
import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.podcasts.store import PodcastStore

# Setup logging
LOG_DIR = Path(__file__).parent.parent / 'data' / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / 'health_check.log'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE)
    ]
)
logger = logging.getLogger(__name__)


def get_db_episodes(store: PodcastStore, data_dir: Path) -> Dict[str, dict]:
    """Get all episodes from atlas_podcasts.db with transcript info.

    Normalizes all paths to absolute for consistent comparison.
    """
    episodes = {}
    with store._get_connection() as conn:
        rows = conn.execute("""
            SELECT e.id, e.guid, e.title, e.transcript_path, e.transcript_status, p.slug
            FROM episodes e
            JOIN podcasts p ON e.podcast_id = p.id
        """).fetchall()
        for row in rows:
            if row["transcript_path"]:
                # Normalize path to absolute
                path = row["transcript_path"]
                if not path.startswith('/'):
                    # Relative path - make absolute
                    path = str((data_dir.parent / path).resolve())
                episodes[path] = {
                    "id": row["id"],
                    "guid": row["guid"],
                    "title": row["title"],
                    "status": row["transcript_status"],
                    "slug": row["slug"],
                    "original_path": row["transcript_path"]
                }
    return episodes


def get_indexed_files(data_dir: Path) -> Set[str]:
    """Get all indexed files from atlas_index.db."""
    index_db = data_dir / 'indexes' / 'atlas_index.db'
    if not index_db.exists():
        logger.warning(f"Index database not found: {index_db}")
        return set()
    
    indexed = set()
    try:
        conn = sqlite3.connect(str(index_db))
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT file_path FROM content_index
            WHERE podcast_name IS NOT NULL
        """).fetchall()
        for row in rows:
            if row["file_path"]:
                indexed.add(row["file_path"])
        conn.close()
    except Exception as e:
        logger.error(f"Error reading index database: {e}")
    
    return indexed


def get_disk_files(data_dir: Path) -> Set[str]:
    """Get all transcript .md files on disk."""
    podcasts_dir = data_dir / 'podcasts'
    files = set()
    
    if not podcasts_dir.exists():
        return files
    
    for transcript in podcasts_dir.glob('*/transcripts/*.md'):
        files.add(str(transcript.resolve()))
    
    return files


def find_missing_files(store: PodcastStore) -> List[dict]:
    """Find episodes marked 'fetched' but transcript file doesn't exist."""
    missing = []
    with store._get_connection() as conn:
        rows = conn.execute("""
            SELECT e.id, e.title, e.transcript_path, p.slug
            FROM episodes e
            JOIN podcasts p ON e.podcast_id = p.id
            WHERE e.transcript_status = 'fetched'
            AND e.transcript_path IS NOT NULL
        """).fetchall()
        
        for row in rows:
            path = Path(row["transcript_path"])
            if not path.exists():
                missing.append({
                    "id": row["id"],
                    "title": row["title"],
                    "path": row["transcript_path"],
                    "slug": row["slug"]
                })
    
    return missing


def requeue_missing_episodes(store: PodcastStore, missing: List[dict]) -> int:
    """Re-queue episodes with missing transcript files."""
    with store._get_connection() as conn:
        for ep in missing:
            conn.execute("""
                UPDATE episodes
                SET transcript_status = 'unknown',
                    transcript_path = NULL,
                    updated_at = datetime('now')
                WHERE id = ?
            """, (ep["id"],))
        conn.commit()
    return len(missing)


def find_orphaned_files(db_episodes: Dict[str, dict], disk_files: Set[str]) -> List[str]:
    """Find files on disk that aren't in the database."""
    db_paths = set(db_episodes.keys())
    return list(disk_files - db_paths)


def register_orphaned_file(store: PodcastStore, filepath: str, data_dir: Path) -> bool:
    """Try to register an orphaned file by finding matching episode."""
    import re
    
    path = Path(filepath)
    if not path.exists():
        return False
    
    # Extract podcast slug from path
    # Path format: data/podcasts/{slug}/transcripts/{filename}.md
    parts = path.parts
    try:
        slug_idx = parts.index('podcasts') + 1
        slug = parts[slug_idx]
    except (ValueError, IndexError):
        return False
    
    # Parse filename for date
    # Format: {date}_{title-slug}.md or similar
    filename = path.stem
    date_match = re.match(r'^(\d{4}-\d{2}-\d{2})_', filename)
    if not date_match:
        return False
    
    file_date = date_match.group(1)
    
    with store._get_connection() as conn:
        # Get podcast ID
        podcast_row = conn.execute(
            "SELECT id FROM podcasts WHERE slug = ?",
            (slug,)
        ).fetchone()
        
        if not podcast_row:
            return False
        
        # Find episode by date
        rows = conn.execute("""
            SELECT id, title, transcript_status FROM episodes
            WHERE podcast_id = ?
            AND date(publish_date) = date(?)
            AND transcript_status != 'fetched'
            LIMIT 1
        """, (podcast_row["id"], file_date)).fetchall()
        
        if not rows:
            return False
        
        episode = rows[0]
        
        # Update episode with transcript
        conn.execute("""
            UPDATE episodes
            SET transcript_status = 'fetched',
                transcript_path = ?,
                updated_at = datetime('now')
            WHERE id = ?
        """, (filepath, episode["id"]))
        conn.commit()
        
        logger.info(f"Registered: {episode['title'][:50]}...")
        return True


def health_check(data_dir: Path, fix: bool = False) -> dict:
    """
    Run comprehensive health check across all three UID layers.
    
    Returns dict with statistics and issues found.
    """
    store = PodcastStore()
    results = {
        "timestamp": datetime.now().isoformat(),
        "issues": {},
        "fixed": {},
        "stats": {}
    }
    
    logger.info("=" * 60)
    logger.info("PODCAST PIPELINE HEALTH CHECK")
    logger.info("=" * 60)
    
    # 1. Reset stuck discovery runs
    logger.info("\n1. Checking stuck discovery runs...")
    stuck_reset = store.reset_stuck_discovery_runs(max_hours=24)
    results["stats"]["stuck_runs_reset"] = stuck_reset
    if stuck_reset > 0:
        logger.info(f"   Reset {stuck_reset} stuck discovery runs")
        if fix:
            results["fixed"]["stuck_runs"] = stuck_reset
    
    # 2. Find episodes with missing transcript files
    logger.info("\n2. Checking for missing transcript files...")
    missing = find_missing_files(store)
    results["stats"]["episodes_missing_files"] = len(missing)
    
    if missing:
        logger.info(f"   Found {len(missing)} episodes marked 'fetched' but file missing")
        results["issues"]["missing_files"] = len(missing)
        
        # Group by podcast
        by_podcast = {}
        for ep in missing:
            by_podcast.setdefault(ep["slug"], []).append(ep)
        
        for slug, eps in sorted(by_podcast.items(), key=lambda x: -len(x[1]))[:5]:
            logger.info(f"     {slug}: {len(eps)}")
        
        if fix:
            requeued = requeue_missing_episodes(store, missing)
            logger.info(f"   Re-queued {requeued} episodes")
            results["fixed"]["requeued"] = requeued
    else:
        logger.info("   All fetched episodes have files on disk")
    
    # 3. Check for orphaned files
    logger.info("\n3. Checking for orphaned transcript files...")
    db_episodes = get_db_episodes(store, data_dir)
    disk_files = get_disk_files(data_dir)
    indexed_files = get_indexed_files(data_dir)
    
    orphaned = find_orphaned_files(db_episodes, disk_files)
    results["stats"]["orphaned_files"] = len(orphaned)
    results["stats"]["total_files_on_disk"] = len(disk_files)
    results["stats"]["files_in_db"] = len(db_episodes)
    results["stats"]["files_indexed"] = len(indexed_files)
    
    if orphaned:
        logger.info(f"   Found {len(orphaned)} orphaned files (on disk, not in DB)")
        results["issues"]["orphaned_files"] = len(orphaned)
        
        if fix:
            registered = 0
            for filepath in orphaned:
                if register_orphaned_file(store, filepath, data_dir):
                    registered += 1
            logger.info(f"   Registered {registered} orphaned files")
            results["fixed"]["registered"] = registered
    else:
        logger.info("   All files on disk are tracked in database")
    
    # 4. Check indexing status
    not_indexed = disk_files - indexed_files
    results["stats"]["not_indexed"] = len(not_indexed)
    if not_indexed:
        logger.info(f"\n4. {len(not_indexed)} files not yet indexed for search")
        # Note: indexing is handled by a separate process
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"  Files on disk:     {len(disk_files):,}")
    logger.info(f"  Files in DB:       {len(db_episodes):,}")
    logger.info(f"  Files indexed:     {len(indexed_files):,}")
    logger.info(f"  Orphaned files:    {len(orphaned):,}")
    logger.info(f"  Missing files:     {len(missing):,}")
    logger.info(f"  Stuck runs reset:  {stuck_reset}")
    
    if fix:
        logger.info("\nFixes applied:")
        for key, count in results["fixed"].items():
            logger.info(f"  {key}: {count}")
    else:
        total_issues = len(orphaned) + len(missing) + stuck_reset
        if total_issues > 0:
            logger.info(f"\nRun with --fix to resolve {total_issues} issues")
    
    return results


def main():
    parser = argparse.ArgumentParser(description='Podcast pipeline health check')
    parser.add_argument('--check', action='store_true', help='Check mode (default)')
    parser.add_argument('--fix', action='store_true', help='Apply fixes')
    parser.add_argument('--data-dir', default='data', help='Data directory')
    args = parser.parse_args()
    
    if not args.fix:
        args.check = True
    
    data_dir = Path(args.data_dir)
    results = health_check(data_dir, fix=args.fix)
    
    # Save results to JSON for monitoring
    results_file = LOG_DIR / 'health_check_latest.json'
    results_file.write_text(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
