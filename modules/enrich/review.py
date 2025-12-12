"""
Review Queue and Reports for Atlas Enrich.

Provides:
- Weekly markdown reports of all ad removals
- Review queue for medium-confidence detections
- False positive marking and tracking
- Pattern improvement suggestions

Usage:
    from modules.enrich.review import ReviewManager

    manager = ReviewManager()

    # Generate weekly report
    report = manager.generate_weekly_report()
    print(report)

    # Get items needing review
    queue = manager.get_review_queue()

    # Mark false positive
    manager.mark_false_positive("podcast:99pi:episode-123", 0, "historical reference")
"""

import json
import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)


@dataclass
class ReviewItem:
    """An item in the review queue."""
    content_id: str
    removal_index: int
    pattern: str
    confidence: float
    text_preview: str
    detected_at: datetime
    status: str = "pending"  # pending, confirmed, false_positive
    reviewed_at: Optional[datetime] = None
    notes: str = ""


@dataclass
class FalsePositive:
    """A marked false positive for pattern improvement."""
    content_id: str
    removal_index: int
    pattern: str
    text: str
    reason: str
    marked_at: datetime


@dataclass
class ReportSummary:
    """Summary statistics for a report."""
    period_start: datetime
    period_end: datetime
    files_processed: int = 0
    ads_removed: int = 0
    chars_removed: int = 0
    avg_percent_removed: float = 0.0
    high_confidence_count: int = 0
    medium_confidence_count: int = 0
    low_confidence_count: int = 0
    review_queue_count: int = 0
    false_positives_marked: int = 0


class ReviewDatabase:
    """SQLite database for review tracking."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the review tables."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS review_queue (
                    id INTEGER PRIMARY KEY,
                    content_id TEXT NOT NULL,
                    removal_index INTEGER NOT NULL,
                    pattern TEXT,
                    confidence REAL,
                    text_preview TEXT,
                    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'pending',
                    reviewed_at TIMESTAMP,
                    notes TEXT,
                    UNIQUE(content_id, removal_index)
                );

                CREATE TABLE IF NOT EXISTS false_positives (
                    id INTEGER PRIMARY KEY,
                    content_id TEXT NOT NULL,
                    removal_index INTEGER NOT NULL,
                    pattern TEXT,
                    full_text TEXT,
                    reason TEXT,
                    marked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(content_id, removal_index)
                );

                CREATE INDEX IF NOT EXISTS idx_review_status ON review_queue(status);
                CREATE INDEX IF NOT EXISTS idx_review_detected ON review_queue(detected_at);
                CREATE INDEX IF NOT EXISTS idx_fp_pattern ON false_positives(pattern);
            """)

    def add_to_review_queue(
        self,
        content_id: str,
        removal_index: int,
        pattern: str,
        confidence: float,
        text_preview: str,
    ):
        """Add an item to the review queue."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO review_queue
                (content_id, removal_index, pattern, confidence, text_preview, detected_at, status)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, 'pending')
            """, (content_id, removal_index, pattern, confidence, text_preview[:500]))

    def get_pending_reviews(self, limit: int = 100) -> List[ReviewItem]:
        """Get pending review items."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM review_queue
                WHERE status = 'pending'
                ORDER BY detected_at DESC
                LIMIT ?
            """, (limit,)).fetchall()

            return [
                ReviewItem(
                    content_id=row["content_id"],
                    removal_index=row["removal_index"],
                    pattern=row["pattern"] or "",
                    confidence=row["confidence"],
                    text_preview=row["text_preview"] or "",
                    detected_at=datetime.fromisoformat(row["detected_at"]),
                    status=row["status"],
                    notes=row["notes"] or "",
                )
                for row in rows
            ]

    def mark_reviewed(
        self,
        content_id: str,
        removal_index: int,
        status: str,
        notes: str = "",
    ):
        """Mark a review item as confirmed or false_positive."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE review_queue
                SET status = ?, reviewed_at = CURRENT_TIMESTAMP, notes = ?
                WHERE content_id = ? AND removal_index = ?
            """, (status, notes, content_id, removal_index))

    def add_false_positive(
        self,
        content_id: str,
        removal_index: int,
        pattern: str,
        full_text: str,
        reason: str,
    ):
        """Record a false positive for pattern improvement."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO false_positives
                (content_id, removal_index, pattern, full_text, reason, marked_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (content_id, removal_index, pattern, full_text, reason))

            # Also update review queue status
            conn.execute("""
                UPDATE review_queue
                SET status = 'false_positive', reviewed_at = CURRENT_TIMESTAMP, notes = ?
                WHERE content_id = ? AND removal_index = ?
            """, (reason, content_id, removal_index))

    def get_false_positives(
        self,
        since: Optional[datetime] = None,
        pattern: Optional[str] = None,
    ) -> List[FalsePositive]:
        """Get false positives, optionally filtered."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            query = "SELECT * FROM false_positives WHERE 1=1"
            params = []

            if since:
                query += " AND marked_at >= ?"
                params.append(since.isoformat())

            if pattern:
                query += " AND pattern LIKE ?"
                params.append(f"%{pattern}%")

            query += " ORDER BY marked_at DESC"

            rows = conn.execute(query, params).fetchall()

            return [
                FalsePositive(
                    content_id=row["content_id"],
                    removal_index=row["removal_index"],
                    pattern=row["pattern"] or "",
                    text=row["full_text"] or "",
                    reason=row["reason"] or "",
                    marked_at=datetime.fromisoformat(row["marked_at"]),
                )
                for row in rows
            ]

    def get_stats(
        self,
        since: Optional[datetime] = None,
    ) -> Dict[str, int]:
        """Get review statistics."""
        with sqlite3.connect(self.db_path) as conn:
            since_clause = ""
            params = []
            if since:
                since_clause = "AND detected_at >= ?"
                params = [since.isoformat()]

            stats = {}

            # Review queue counts
            for status in ["pending", "confirmed", "false_positive"]:
                count = conn.execute(f"""
                    SELECT COUNT(*) FROM review_queue
                    WHERE status = ? {since_clause}
                """, [status] + params).fetchone()[0]
                stats[f"review_{status}"] = count

            # False positive count
            fp_count = conn.execute(f"""
                SELECT COUNT(*) FROM false_positives
                {"WHERE marked_at >= ?" if since else ""}
            """, params if since else []).fetchone()[0]
            stats["false_positives"] = fp_count

            return stats


class ReviewManager:
    """
    Manage review queue and generate reports.

    Coordinates review workflow:
    1. Medium-confidence detections go to review queue
    2. Humans mark as confirmed or false positive
    3. False positives feed back to improve patterns
    4. Weekly reports summarize all activity
    """

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        reports_dir: Optional[Path] = None,
    ):
        """
        Initialize the review manager.

        Args:
            data_dir: Base data directory (default: data/enrich)
            reports_dir: Directory for report files (default: data/enrich/reports)
        """
        self.data_dir = data_dir or Path("data/enrich")
        self.reports_dir = reports_dir or self.data_dir / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        self.db = ReviewDatabase(self.data_dir / "review.db")
        self.changes_dir = self.data_dir / "changes"

    def add_to_review(
        self,
        content_id: str,
        removal_index: int,
        pattern: str,
        confidence: float,
        text_preview: str,
    ):
        """Add an item to the review queue."""
        self.db.add_to_review_queue(
            content_id, removal_index, pattern, confidence, text_preview
        )
        logger.info(f"Added to review queue: {content_id}[{removal_index}]")

    def get_review_queue(self, limit: int = 100) -> List[ReviewItem]:
        """Get pending items that need human review."""
        return self.db.get_pending_reviews(limit)

    def mark_confirmed(
        self,
        content_id: str,
        removal_index: int,
        notes: str = "",
    ):
        """Confirm that a detection is a real ad."""
        self.db.mark_reviewed(content_id, removal_index, "confirmed", notes)
        logger.info(f"Confirmed as ad: {content_id}[{removal_index}]")

    def mark_false_positive(
        self,
        content_id: str,
        removal_index: int,
        reason: str,
    ):
        """
        Mark a detection as a false positive.

        This:
        1. Updates the review queue status
        2. Records the false positive for pattern improvement
        3. Optionally restores the original content
        """
        # Get the full text from the changes file
        changes_file = self.changes_dir / f"{content_id.replace(':', '_')}.json"
        full_text = ""
        pattern = ""

        if changes_file.exists():
            with open(changes_file) as f:
                data = json.load(f)
                if removal_index < len(data.get("removals", [])):
                    removal = data["removals"][removal_index]
                    full_text = removal.get("text", "")
                    pattern = removal.get("pattern", "")

        self.db.add_false_positive(
            content_id, removal_index, pattern, full_text, reason
        )
        logger.info(f"Marked false positive: {content_id}[{removal_index}] - {reason}")

    def get_false_positives(
        self,
        since: Optional[datetime] = None,
    ) -> List[FalsePositive]:
        """Get recorded false positives."""
        return self.db.get_false_positives(since=since)

    def generate_weekly_report(
        self,
        week_start: Optional[datetime] = None,
    ) -> str:
        """
        Generate a markdown report for the week.

        Args:
            week_start: Start of the reporting week (default: last Monday)

        Returns:
            Markdown formatted report
        """
        # Default to last Monday
        if week_start is None:
            today = datetime.now()
            week_start = today - timedelta(days=today.weekday() + 7)
        week_end = week_start + timedelta(days=7)

        # Gather statistics from change files
        summary = self._gather_summary(week_start, week_end)

        # Get review stats
        review_stats = self.db.get_stats(since=week_start)

        # Get false positives this week
        false_positives = self.db.get_false_positives(since=week_start)

        # Get pending review items
        pending_reviews = self.db.get_pending_reviews(limit=50)

        # Build report
        report = self._format_report(
            summary, review_stats, false_positives, pending_reviews, week_start
        )

        # Save report
        report_file = self.reports_dir / f"week-{week_start.strftime('%Y-%m-%d')}.md"
        report_file.write_text(report)
        logger.info(f"Generated weekly report: {report_file}")

        return report

    def _gather_summary(
        self,
        start: datetime,
        end: datetime,
    ) -> ReportSummary:
        """Gather statistics from change files."""
        summary = ReportSummary(period_start=start, period_end=end)

        if not self.changes_dir.exists():
            return summary

        total_percent = 0.0
        files_with_percent = 0

        for changes_file in self.changes_dir.glob("*.json"):
            try:
                with open(changes_file) as f:
                    data = json.load(f)

                cleaned_at = datetime.fromisoformat(data.get("cleaned_at", "2000-01-01"))
                if not (start <= cleaned_at < end):
                    continue

                summary.files_processed += 1
                removals = data.get("removals", [])
                summary.ads_removed += len(removals)

                for removal in removals:
                    chars = removal.get("end", 0) - removal.get("start", 0)
                    summary.chars_removed += chars

                    confidence = removal.get("confidence", 0.5)
                    if confidence >= 0.9:
                        summary.high_confidence_count += 1
                    elif confidence >= 0.7:
                        summary.medium_confidence_count += 1
                    else:
                        summary.low_confidence_count += 1

            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Error reading {changes_file}: {e}")

        if files_with_percent > 0:
            summary.avg_percent_removed = total_percent / files_with_percent

        return summary

    def _format_report(
        self,
        summary: ReportSummary,
        review_stats: Dict[str, int],
        false_positives: List[FalsePositive],
        pending_reviews: List[ReviewItem],
        week_start: datetime,
    ) -> str:
        """Format the report as markdown."""
        lines = [
            f"# Enrichment Report: Week of {week_start.strftime('%Y-%m-%d')}",
            "",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Summary",
            "",
            f"- **Files processed**: {summary.files_processed}",
            f"- **Ads removed**: {summary.ads_removed}",
            f"- **Characters removed**: {summary.chars_removed:,}",
            "",
            "### Confidence Distribution",
            "",
            f"| Tier | Count |",
            f"|------|-------|",
            f"| High (>0.9) - Auto-removed | {summary.high_confidence_count} |",
            f"| Medium (0.7-0.9) - Review queue | {summary.medium_confidence_count} |",
            f"| Low (<0.7) - Skipped | {summary.low_confidence_count} |",
            "",
            "### Review Status",
            "",
            f"- Pending review: {review_stats.get('review_pending', 0)}",
            f"- Confirmed as ads: {review_stats.get('review_confirmed', 0)}",
            f"- Marked as false positives: {review_stats.get('review_false_positive', 0)}",
            "",
        ]

        # High-confidence removals (sample)
        lines.extend([
            "## High-Confidence Removals (Auto-applied)",
            "",
            "| File | Pattern | Preview |",
            "|------|---------|---------|",
        ])

        # Show sample of recent changes
        sample_count = 0
        if self.changes_dir.exists():
            for changes_file in sorted(self.changes_dir.glob("*.json"), reverse=True)[:20]:
                if sample_count >= 10:
                    break
                try:
                    with open(changes_file) as f:
                        data = json.load(f)
                    for removal in data.get("removals", []):
                        if removal.get("confidence", 0) >= 0.9:
                            content_id = data.get("content_id", changes_file.stem)
                            pattern = removal.get("pattern", "")[:30]
                            preview = removal.get("text", "")[:50].replace("|", "\\|").replace("\n", " ")
                            lines.append(f"| {content_id[:40]} | {pattern} | {preview}... |")
                            sample_count += 1
                            if sample_count >= 10:
                                break
                except Exception:
                    pass

        if sample_count == 0:
            lines.append("| (none this week) | | |")

        lines.append("")

        # Review queue
        lines.extend([
            "## Review Queue (Needs Human Check)",
            "",
            "| File | Pattern | Confidence | Preview |",
            "|------|---------|------------|---------|",
        ])

        for item in pending_reviews[:20]:
            preview = item.text_preview[:50].replace("|", "\\|").replace("\n", " ")
            lines.append(
                f"| {item.content_id[:40]} | {item.pattern[:20]} | {item.confidence:.2f} | {preview}... |"
            )

        if not pending_reviews:
            lines.append("| (queue empty) | | | |")

        lines.append("")

        # False positives
        lines.extend([
            "## False Positives Marked This Week",
            "",
        ])

        if false_positives:
            for fp in false_positives[:10]:
                lines.append(f"- **{fp.content_id}** - \"{fp.pattern}\" ({fp.reason})")
        else:
            lines.append("(none)")

        lines.append("")

        # Pattern improvement suggestions
        if false_positives:
            lines.extend([
                "## Suggested Pattern Improvements",
                "",
                "Based on false positives, consider adding these negative patterns:",
                "",
            ])

            # Group by pattern
            pattern_fps: Dict[str, List[str]] = {}
            for fp in false_positives:
                if fp.pattern not in pattern_fps:
                    pattern_fps[fp.pattern] = []
                pattern_fps[fp.pattern].append(fp.text[:100])

            for pattern, examples in pattern_fps.items():
                lines.append(f"### Pattern: `{pattern}`")
                lines.append("")
                lines.append("Examples incorrectly matched:")
                for ex in examples[:3]:
                    lines.append(f"- \"{ex}...\"")
                lines.append("")

        return "\n".join(lines)


# CLI for review management
if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="Manage enrichment review queue")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Report command
    report_parser = subparsers.add_parser("report", help="Generate weekly report")
    report_parser.add_argument("--week", help="Week start date (YYYY-MM-DD)")

    # Queue command
    queue_parser = subparsers.add_parser("queue", help="Show review queue")
    queue_parser.add_argument("--limit", "-n", type=int, default=20, help="Max items")

    # Mark-fp command
    fp_parser = subparsers.add_parser("mark-fp", help="Mark false positive")
    fp_parser.add_argument("content_id", help="Content ID")
    fp_parser.add_argument("index", type=int, help="Removal index")
    fp_parser.add_argument("reason", help="Reason (e.g., 'historical reference')")

    # Confirm command
    confirm_parser = subparsers.add_parser("confirm", help="Confirm as real ad")
    confirm_parser.add_argument("content_id", help="Content ID")
    confirm_parser.add_argument("index", type=int, help="Removal index")

    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show statistics")

    args = parser.parse_args()

    manager = ReviewManager()

    if args.command == "report":
        week_start = None
        if args.week:
            week_start = datetime.fromisoformat(args.week)
        report = manager.generate_weekly_report(week_start)
        print(report)

    elif args.command == "queue":
        items = manager.get_review_queue(args.limit)
        if not items:
            print("Review queue is empty.")
        else:
            print(f"Review Queue ({len(items)} items):\n")
            for i, item in enumerate(items):
                print(f"{i+1}. [{item.confidence:.2f}] {item.content_id}")
                print(f"   Pattern: {item.pattern}")
                print(f"   Preview: {item.text_preview[:80]}...")
                print()

    elif args.command == "mark-fp":
        manager.mark_false_positive(args.content_id, args.index, args.reason)
        print(f"Marked as false positive: {args.content_id}[{args.index}]")

    elif args.command == "confirm":
        manager.mark_confirmed(args.content_id, args.index)
        print(f"Confirmed as ad: {args.content_id}[{args.index}]")

    elif args.command == "stats":
        stats = manager.db.get_stats()
        print("Review Statistics:")
        print(f"  Pending: {stats.get('review_pending', 0)}")
        print(f"  Confirmed: {stats.get('review_confirmed', 0)}")
        print(f"  False positives: {stats.get('false_positives', 0)}")

    else:
        parser.print_help()
