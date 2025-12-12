"""
Versioned Content Cleaner - Non-destructive cleaning with audit trail.

Keeps original files intact, stores cleaned versions separately,
and maintains a record of all changes for review.

Architecture:
    data/podcasts/{slug}/transcripts/          <- Original files (untouched)
    data/clean/{content_type}/{slug}/          <- Cleaned versions (for indexing)
    data/enrich/changes/                       <- Change records (what was removed)
    data/enrich/enrich.db                      <- SQLite tracking database

The indexer (Atlas Ask) reads from data/clean/ instead of originals.
Original files are never modified.
"""

import json
import sqlite3
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, asdict
from contextlib import contextmanager

from .ad_stripper import AdStripper, ContentType, AdDetection
from .content_cleaner import ContentCleaner, CleaningResult

logger = logging.getLogger(__name__)


@dataclass
class CleaningRecord:
    """Record of a cleaning operation."""
    content_id: str
    original_path: str
    clean_path: str
    original_hash: str
    clean_hash: str
    content_type: str

    # Stats
    ads_removed: int
    chars_removed: int
    percent_removed: float
    quality_score: float

    # Metadata
    cleaned_at: str
    cleaner_version: str = "1.0"

    # What was removed (JSON serialized)
    removals_json: str = "[]"


class EnrichDatabase:
    """SQLite database for tracking enrichment operations."""

    def __init__(self, db_path: str = "data/enrich/enrich.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cleaning_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content_id TEXT UNIQUE NOT NULL,
                    original_path TEXT NOT NULL,
                    clean_path TEXT NOT NULL,
                    original_hash TEXT NOT NULL,
                    clean_hash TEXT NOT NULL,
                    content_type TEXT NOT NULL,
                    ads_removed INTEGER DEFAULT 0,
                    chars_removed INTEGER DEFAULT 0,
                    percent_removed REAL DEFAULT 0.0,
                    quality_score REAL DEFAULT 0.0,
                    cleaned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    cleaner_version TEXT DEFAULT '1.0',
                    removals_json TEXT DEFAULT '[]',
                    needs_reclean BOOLEAN DEFAULT FALSE
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_content_type
                ON cleaning_records(content_type)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_needs_reclean
                ON cleaning_records(needs_reclean)
            """)

    @contextmanager
    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def record_cleaning(self, record: CleaningRecord) -> int:
        """Record a cleaning operation."""
        with self._get_conn() as conn:
            cursor = conn.execute("""
                INSERT OR REPLACE INTO cleaning_records
                (content_id, original_path, clean_path, original_hash, clean_hash,
                 content_type, ads_removed, chars_removed, percent_removed,
                 quality_score, cleaned_at, cleaner_version, removals_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.content_id, record.original_path, record.clean_path,
                record.original_hash, record.clean_hash, record.content_type,
                record.ads_removed, record.chars_removed, record.percent_removed,
                record.quality_score, record.cleaned_at, record.cleaner_version,
                record.removals_json
            ))
            return cursor.lastrowid

    def get_record(self, content_id: str) -> Optional[CleaningRecord]:
        """Get cleaning record by content ID."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM cleaning_records WHERE content_id = ?",
                (content_id,)
            ).fetchone()
            if row:
                return CleaningRecord(
                    content_id=row['content_id'],
                    original_path=row['original_path'],
                    clean_path=row['clean_path'],
                    original_hash=row['original_hash'],
                    clean_hash=row['clean_hash'],
                    content_type=row['content_type'],
                    ads_removed=row['ads_removed'],
                    chars_removed=row['chars_removed'],
                    percent_removed=row['percent_removed'],
                    quality_score=row['quality_score'],
                    cleaned_at=row['cleaned_at'],
                    cleaner_version=row['cleaner_version'],
                    removals_json=row['removals_json'],
                )
        return None

    def needs_cleaning(self, content_id: str, original_hash: str) -> bool:
        """Check if content needs (re)cleaning."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT original_hash, needs_reclean FROM cleaning_records WHERE content_id = ?",
                (content_id,)
            ).fetchone()
            if not row:
                return True  # Never cleaned
            if row['needs_reclean']:
                return True  # Marked for re-clean
            if row['original_hash'] != original_hash:
                return True  # Original file changed
            return False

    def mark_for_reclean(self, content_type: Optional[str] = None):
        """Mark records for re-cleaning (e.g., after updating patterns)."""
        with self._get_conn() as conn:
            if content_type:
                conn.execute(
                    "UPDATE cleaning_records SET needs_reclean = TRUE WHERE content_type = ?",
                    (content_type,)
                )
            else:
                conn.execute("UPDATE cleaning_records SET needs_reclean = TRUE")

    def get_stats(self) -> Dict[str, Any]:
        """Get enrichment statistics."""
        with self._get_conn() as conn:
            stats = {}

            # Total records
            stats['total_cleaned'] = conn.execute(
                "SELECT COUNT(*) FROM cleaning_records"
            ).fetchone()[0]

            # By content type
            rows = conn.execute("""
                SELECT content_type, COUNT(*) as count,
                       SUM(ads_removed) as total_ads,
                       AVG(percent_removed) as avg_percent
                FROM cleaning_records
                GROUP BY content_type
            """).fetchall()
            stats['by_type'] = {
                row['content_type']: {
                    'count': row['count'],
                    'total_ads': row['total_ads'],
                    'avg_percent_removed': round(row['avg_percent'] or 0, 2)
                }
                for row in rows
            }

            # Needs re-clean
            stats['needs_reclean'] = conn.execute(
                "SELECT COUNT(*) FROM cleaning_records WHERE needs_reclean = TRUE"
            ).fetchone()[0]

            return stats


class VersionedCleaner:
    """
    Non-destructive content cleaner with versioning.

    Usage:
        cleaner = VersionedCleaner()

        # Clean a single file
        result = cleaner.clean_file(
            "data/podcasts/acquired/transcripts/episode-1.md",
            content_type="podcast"
        )

        # Clean all podcasts
        cleaner.clean_all_podcasts(dry_run=True)  # Preview
        cleaner.clean_all_podcasts()               # Actually clean

        # View what was removed
        cleaner.show_removals("podcast:acquired:episode-1")
    """

    CLEANER_VERSION = "1.0"

    def __init__(
        self,
        clean_base: str = "data/clean",
        changes_base: str = "data/enrich/changes",
        db_path: str = "data/enrich/enrich.db",
    ):
        self.clean_base = Path(clean_base)
        self.changes_base = Path(changes_base)
        self.db = EnrichDatabase(db_path)
        self.cleaner = ContentCleaner()

        # Create directories
        self.clean_base.mkdir(parents=True, exist_ok=True)
        self.changes_base.mkdir(parents=True, exist_ok=True)

    def _hash_content(self, text: str) -> str:
        """Generate content hash."""
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    def _generate_content_id(self, original_path: Path, content_type: str) -> str:
        """Generate unique content ID from path."""
        # podcast:acquired:2024-01-01_episode-title
        parts = original_path.parts
        if content_type == "podcast":
            # data/podcasts/{slug}/transcripts/{filename}
            slug = parts[-3] if len(parts) >= 3 else "unknown"
            filename = original_path.stem
            return f"podcast:{slug}:{filename}"
        elif content_type == "article":
            # data/content/article/{date}/{id}/content.md
            if len(parts) >= 4:
                return f"article:{parts[-3]}:{parts[-2]}"
            return f"article:{original_path.stem}"
        else:
            return f"{content_type}:{original_path.stem}"

    def _get_clean_path(self, original_path: Path, content_type: str) -> Path:
        """Get path for cleaned version."""
        content_id = self._generate_content_id(original_path, content_type)
        parts = content_id.split(":")

        if content_type == "podcast":
            # data/clean/podcasts/{slug}/transcripts/{filename}.md
            slug = parts[1] if len(parts) > 1 else "unknown"
            filename = parts[2] if len(parts) > 2 else original_path.stem
            return self.clean_base / "podcasts" / slug / "transcripts" / f"{filename}.md"
        else:
            return self.clean_base / content_type / f"{content_id.replace(':', '_')}.md"

    def _save_removal_record(
        self,
        content_id: str,
        original_text: str,
        detections: List[AdDetection],
    ):
        """Save detailed removal record for audit."""
        if not detections:
            return

        # Save to changes directory
        safe_id = content_id.replace(":", "_").replace("/", "_")
        changes_file = self.changes_base / f"{safe_id}.json"

        record = {
            "content_id": content_id,
            "cleaned_at": datetime.utcnow().isoformat(),
            "removals": [
                {
                    "start": d.start_char,
                    "end": d.end_char,
                    "method": d.method.value,
                    "confidence": d.confidence,
                    "pattern": d.matched_pattern,
                    "text": d.text,  # Full removed text for review
                }
                for d in detections
            ]
        }

        changes_file.write_text(json.dumps(record, indent=2))

    def clean_file(
        self,
        original_path: str | Path,
        content_type: str = "podcast",
        force: bool = False,
    ) -> Optional[CleaningRecord]:
        """
        Clean a single file (non-destructive).

        Args:
            original_path: Path to original file
            content_type: podcast, article, newsletter, youtube
            force: Re-clean even if already done

        Returns:
            CleaningRecord if cleaned, None if skipped
        """
        original_path = Path(original_path)
        if not original_path.exists():
            logger.warning(f"File not found: {original_path}")
            return None

        # Read original
        original_text = original_path.read_text(encoding='utf-8')
        original_hash = self._hash_content(original_text)

        # Generate IDs and paths
        content_id = self._generate_content_id(original_path, content_type)
        clean_path = self._get_clean_path(original_path, content_type)

        # Check if needs cleaning
        if not force and not self.db.needs_cleaning(content_id, original_hash):
            logger.debug(f"Skipping (already clean): {content_id}")
            return None

        # Clean content
        content_type_enum = ContentType(content_type)

        # Use ad_stripper directly to get detections
        strip_result = self.cleaner.ad_stripper.strip(original_text, content_type_enum)

        # Also run full cleaner for quality score
        clean_result = self.cleaner.clean(original_text, content_type)

        # Save cleaned version
        clean_path.parent.mkdir(parents=True, exist_ok=True)
        clean_path.write_text(clean_result.cleaned_text, encoding='utf-8')

        clean_hash = self._hash_content(clean_result.cleaned_text)

        # Save removal record (for audit)
        self._save_removal_record(content_id, original_text, strip_result.detections)

        # Create database record
        record = CleaningRecord(
            content_id=content_id,
            original_path=str(original_path),
            clean_path=str(clean_path),
            original_hash=original_hash,
            clean_hash=clean_hash,
            content_type=content_type,
            ads_removed=strip_result.ads_found,
            chars_removed=strip_result.chars_removed,
            percent_removed=strip_result.percent_removed,
            quality_score=clean_result.quality_score,
            cleaned_at=datetime.utcnow().isoformat(),
            cleaner_version=self.CLEANER_VERSION,
            removals_json=json.dumps([
                {"method": d.method.value, "confidence": d.confidence, "chars": d.length}
                for d in strip_result.detections
            ])
        )

        self.db.record_cleaning(record)

        if strip_result.ads_found > 0:
            logger.info(
                f"Cleaned {content_id}: {strip_result.ads_found} ads, "
                f"{strip_result.percent_removed:.1f}% removed"
            )
        else:
            logger.debug(f"Cleaned {content_id}: no ads found")

        return record

    def clean_all_podcasts(
        self,
        dry_run: bool = False,
        limit: Optional[int] = None,
        force: bool = False,
    ) -> Dict[str, Any]:
        """
        Clean all podcast transcripts.

        Args:
            dry_run: Preview what would be cleaned
            limit: Max files to process
            force: Re-clean everything

        Returns:
            Stats dictionary
        """
        import glob

        pattern = "data/podcasts/*/transcripts/*.md"
        files = sorted(glob.glob(pattern))

        if limit:
            files = files[:limit]

        stats = {
            "total": len(files),
            "cleaned": 0,
            "skipped": 0,
            "ads_found": 0,
            "chars_removed": 0,
        }

        print(f"{'[DRY RUN] ' if dry_run else ''}Processing {len(files)} podcast transcripts...")

        for filepath in files:
            original_path = Path(filepath)
            content_id = self._generate_content_id(original_path, "podcast")

            if dry_run:
                # Check if would be cleaned
                original_text = original_path.read_text(encoding='utf-8')
                original_hash = self._hash_content(original_text)

                if not force and not self.db.needs_cleaning(content_id, original_hash):
                    stats["skipped"] += 1
                    continue

                # Preview cleaning
                strip_result = self.cleaner.ad_stripper.strip(
                    original_text, ContentType.PODCAST
                )

                if strip_result.ads_found > 0:
                    podcast = filepath.split("/")[2]
                    print(f"  Would clean {podcast}/{original_path.name}: "
                          f"{strip_result.ads_found} ads, {strip_result.percent_removed:.1f}%")

                stats["cleaned"] += 1
                stats["ads_found"] += strip_result.ads_found
                stats["chars_removed"] += strip_result.chars_removed
            else:
                record = self.clean_file(filepath, "podcast", force=force)

                if record:
                    stats["cleaned"] += 1
                    stats["ads_found"] += record.ads_removed
                    stats["chars_removed"] += record.chars_removed
                else:
                    stats["skipped"] += 1

        return stats

    def show_removals(self, content_id: str) -> Optional[Dict]:
        """Show what was removed from a specific piece of content."""
        safe_id = content_id.replace(":", "_").replace("/", "_")
        changes_file = self.changes_base / f"{safe_id}.json"

        if changes_file.exists():
            return json.loads(changes_file.read_text())
        return None

    def get_stats(self) -> Dict[str, Any]:
        """Get overall enrichment statistics."""
        return self.db.get_stats()


# CLI
if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    parser = argparse.ArgumentParser(description="Versioned content cleaner")
    subparsers = parser.add_subparsers(dest="command")

    # clean command
    clean_parser = subparsers.add_parser("clean", help="Clean content")
    clean_parser.add_argument("--podcasts", action="store_true", help="Clean all podcasts")
    clean_parser.add_argument("--file", help="Clean single file")
    clean_parser.add_argument("--type", "-t", default="podcast")
    clean_parser.add_argument("--dry-run", "-n", action="store_true")
    clean_parser.add_argument("--limit", type=int)
    clean_parser.add_argument("--force", "-f", action="store_true")

    # stats command
    stats_parser = subparsers.add_parser("stats", help="Show statistics")

    # show command
    show_parser = subparsers.add_parser("show", help="Show removals for content")
    show_parser.add_argument("content_id", help="Content ID to show")

    # reclean command
    reclean_parser = subparsers.add_parser("reclean", help="Mark content for re-cleaning")
    reclean_parser.add_argument("--type", "-t", help="Content type to mark")

    args = parser.parse_args()

    cleaner = VersionedCleaner()

    if args.command == "clean":
        if args.podcasts:
            stats = cleaner.clean_all_podcasts(
                dry_run=args.dry_run,
                limit=args.limit,
                force=args.force,
            )
            print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Results:")
            print(f"  Total files: {stats['total']}")
            print(f"  Cleaned: {stats['cleaned']}")
            print(f"  Skipped: {stats['skipped']}")
            print(f"  Ads found: {stats['ads_found']}")
            print(f"  Chars removed: {stats['chars_removed']}")
        elif args.file:
            record = cleaner.clean_file(args.file, args.type, force=args.force)
            if record:
                print(f"Cleaned: {record.content_id}")
                print(f"  Ads removed: {record.ads_removed}")
                print(f"  Percent removed: {record.percent_removed:.1f}%")
                print(f"  Clean file: {record.clean_path}")
            else:
                print("File skipped (already clean or not found)")
        else:
            parser.print_help()

    elif args.command == "stats":
        stats = cleaner.get_stats()
        print("Enrichment Statistics:")
        print(f"  Total cleaned: {stats['total_cleaned']}")
        print(f"  Needs re-clean: {stats['needs_reclean']}")
        print("\nBy content type:")
        for ctype, data in stats.get('by_type', {}).items():
            print(f"  {ctype}:")
            print(f"    Count: {data['count']}")
            print(f"    Total ads: {data['total_ads']}")
            print(f"    Avg % removed: {data['avg_percent_removed']}%")

    elif args.command == "show":
        removals = cleaner.show_removals(args.content_id)
        if removals:
            print(json.dumps(removals, indent=2))
        else:
            print(f"No removal record found for: {args.content_id}")

    elif args.command == "reclean":
        cleaner.db.mark_for_reclean(args.type)
        print(f"Marked {'all' if not args.type else args.type} content for re-cleaning")

    else:
        parser.print_help()
