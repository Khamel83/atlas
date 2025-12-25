#!/usr/bin/env python3
"""
Reconcile transcript files on disk with database episode status.

Scans all transcript files in data/podcasts/*/transcripts/*.md and:
1. Matches to DB episodes by date + fuzzy title
2. Optionally verifies content quality
3. Updates transcript_status = 'fetched' for matches
4. Reports orphans (files that couldn't be matched)

Usage:
    python scripts/reconcile_transcripts.py --dry-run
    python scripts/reconcile_transcripts.py --apply
    python scripts/reconcile_transcripts.py --apply --verify
"""

import argparse
import logging
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.podcasts.store import PodcastStore, Episode

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Try to import quality verification
try:
    from modules.quality import verify_file, QualityLevel
    HAS_QUALITY = True
except ImportError:
    HAS_QUALITY = False
    logger.warning("Quality verification not available")


@dataclass
class ReconcileResult:
    """Result of reconciliation for one podcast"""
    podcast_slug: str
    files_on_disk: int
    matched: int
    already_fetched: int
    orphaned: int
    bad_quality: int
    orphan_files: List[str]


def normalize_title(title: str) -> str:
    """Normalize title for matching"""
    normalized = title.lower()
    normalized = re.sub(r'[^\w\s]', '', normalized)
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    return normalized


def find_missing_transcript_files(store: PodcastStore) -> List[Dict]:
    """
    Find episodes marked 'fetched' but transcript file doesn't exist.

    Returns list of episodes that should be re-queued.
    """
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
            if row["transcript_path"]:
                path = Path(row["transcript_path"])
                if not path.exists():
                    missing.append({
                        "id": row["id"],
                        "title": row["title"],
                        "path": row["transcript_path"],
                        "slug": row["slug"]
                    })

    return missing


def requeue_missing_episodes(store: PodcastStore, missing: List[Dict]) -> int:
    """Re-queue episodes with missing transcript files (set status='unknown')."""
    fixed = 0

    with store._get_connection() as conn:
        for ep in missing:
            conn.execute(
                """UPDATE episodes
                   SET transcript_status = 'unknown',
                       transcript_path = NULL,
                       updated_at = datetime('now')
                   WHERE id = ?""",
                (ep["id"],)
            )
            fixed += 1
        conn.commit()

    return fixed


def extract_date_and_title(filename: str) -> Tuple[Optional[str], str]:
    """
    Extract date and title from transcript filename.

    Filename formats:
    - 2025-11-18_how-the-financial-crisis-broke-wall-street.md
    - episode-title-without-date.md

    Returns: (date_str or None, title_slug)
    """
    stem = Path(filename).stem

    # Check for date prefix (YYYY-MM-DD_)
    date_match = re.match(r'^(\d{4}-\d{2}-\d{2})_(.+)$', stem)
    if date_match:
        return date_match.group(1), date_match.group(2)

    return None, stem


def match_episode_by_date_title(
    store: PodcastStore,
    podcast_id: int,
    date_str: Optional[str],
    title_slug: str,
    episodes: List[Episode]
) -> Optional[Episode]:
    """
    Try to match a transcript file to an episode.

    Strategy:
    1. If date available, find episodes on that date, then fuzzy match title
    2. If no date, fuzzy match title across all episodes
    """
    normalized_title = normalize_title(title_slug.replace('-', ' ').replace('_', ' '))

    # Build title lookup for this podcast
    episode_by_title = {}
    for ep in episodes:
        ep_normalized = normalize_title(ep.title)
        episode_by_title[ep_normalized] = ep

    # Strategy 1: Match by date first
    if date_str:
        with store._get_connection() as conn:
            rows = conn.execute(
                """SELECT id FROM episodes
                   WHERE podcast_id = ?
                   AND date(publish_date) = date(?)""",
                (podcast_id, date_str)
            ).fetchall()

            if rows:
                # Found episodes on this date, now match title
                for row in rows:
                    episode = store.get_episode_by_id(row['id'])
                    if episode:
                        ep_normalized = normalize_title(episode.title)
                        # Check for fuzzy match
                        if normalized_title in ep_normalized or ep_normalized in normalized_title:
                            return episode
                        # Check word overlap
                        title_words = set(normalized_title.split())
                        ep_words = set(ep_normalized.split())
                        overlap = len(title_words & ep_words)
                        if overlap >= min(3, len(title_words)):
                            return episode

    # Strategy 2: Exact normalized title match
    if normalized_title in episode_by_title:
        return episode_by_title[normalized_title]

    # Strategy 3: Fuzzy title match (substring)
    for ep_normalized, episode in episode_by_title.items():
        if normalized_title in ep_normalized or ep_normalized in normalized_title:
            return episode

    # Strategy 4: Word overlap matching
    title_words = set(normalized_title.split())
    if len(title_words) >= 3:
        for ep_normalized, episode in episode_by_title.items():
            ep_words = set(ep_normalized.split())
            overlap = len(title_words & ep_words)
            # Require at least 3 matching words or 50% overlap
            threshold = min(3, max(len(title_words), len(ep_words)) // 2)
            if overlap >= threshold:
                return episode

    return None


def reconcile_podcast(
    store: PodcastStore,
    podcast_dir: Path,
    verify: bool = False,
    apply: bool = False
) -> ReconcileResult:
    """Reconcile transcripts for a single podcast directory"""

    podcast_slug = podcast_dir.name
    transcript_dir = podcast_dir / "transcripts"

    if not transcript_dir.exists():
        return ReconcileResult(
            podcast_slug=podcast_slug,
            files_on_disk=0,
            matched=0,
            already_fetched=0,
            orphaned=0,
            bad_quality=0,
            orphan_files=[]
        )

    # Get podcast from DB
    with store._get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM podcasts WHERE slug = ?",
            (podcast_slug,)
        ).fetchone()

    if not row:
        # Try fuzzy matching
        podcasts = store.list_podcasts()
        podcast = None
        for p in podcasts:
            if normalize_title(p.slug) == normalize_title(podcast_slug):
                podcast = p
                break
        if not podcast:
            # Count as orphaned
            files = list(transcript_dir.glob("*.md"))
            return ReconcileResult(
                podcast_slug=podcast_slug,
                files_on_disk=len(files),
                matched=0,
                already_fetched=0,
                orphaned=len(files),
                bad_quality=0,
                orphan_files=[f.name for f in files[:10]]  # Sample
            )
        podcast_id = podcast.id
    else:
        podcast_id = row['id']

    # Get all episodes for this podcast
    episodes = store.get_episodes_by_podcast(podcast_id)

    # Process transcript files
    files_on_disk = 0
    matched = 0
    already_fetched = 0
    orphaned = 0
    bad_quality = 0
    orphan_files = []

    for transcript_file in transcript_dir.glob("*.md"):
        files_on_disk += 1

        date_str, title_slug = extract_date_and_title(transcript_file.name)
        episode = match_episode_by_date_title(store, podcast_id, date_str, title_slug, episodes)

        if not episode:
            orphaned += 1
            if len(orphan_files) < 10:
                orphan_files.append(transcript_file.name)
            continue

        # Check if already marked fetched
        if episode.transcript_status == 'fetched' and episode.transcript_path:
            already_fetched += 1
            continue

        # Optionally verify quality
        if verify and HAS_QUALITY:
            result = verify_file(str(transcript_file))
            if result.quality == QualityLevel.BAD:
                bad_quality += 1
                logger.debug(f"Bad quality: {transcript_file.name} - {result.issues}")
                continue

        # Update DB
        if apply:
            store.update_episode_transcript_status(
                episode.id,
                status='fetched',
                transcript_path=str(transcript_file.absolute())
            )

        matched += 1
        logger.debug(f"Matched: {transcript_file.name} -> {episode.title}")

    return ReconcileResult(
        podcast_slug=podcast_slug,
        files_on_disk=files_on_disk,
        matched=matched,
        already_fetched=already_fetched,
        orphaned=orphaned,
        bad_quality=bad_quality,
        orphan_files=orphan_files
    )


def main():
    parser = argparse.ArgumentParser(description='Reconcile transcript files with database')
    parser.add_argument('--check', action='store_true', help='Check mode: report issues only')
    parser.add_argument('--fix', action='store_true', help='Fix mode: apply all fixes')
    parser.add_argument('--dry-run', action='store_true', help='Alias for --check')
    parser.add_argument('--apply', action='store_true', help='Alias for --fix')
    parser.add_argument('--verify', action='store_true', help='Verify content quality before marking fetched')
    parser.add_argument('--slug', type=str, help='Only reconcile specific podcast slug')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Normalize flags
    if args.dry_run:
        args.check = True
    if args.apply:
        args.fix = True

    if not args.fix and not args.check:
        args.check = True  # Default to check mode

    if args.check and not args.fix:
        print("=" * 60)
        print("CHECK MODE - No changes will be made")
        print("=" * 60 + "\n")

    store = PodcastStore()
    data_dir = Path("data/podcasts")

    if not data_dir.exists():
        print("Data directory not found: data/podcasts")
        sys.exit(1)

    # STEP 1: Find episodes with missing transcript files
    print("Step 1: Finding episodes with missing transcript files...")
    missing = find_missing_transcript_files(store)
    print(f"  Found: {len(missing)} episodes marked 'fetched' but file missing")

    if missing:
        # Group by podcast
        by_podcast: Dict[str, List] = {}
        for ep in missing:
            by_podcast.setdefault(ep["slug"], []).append(ep)

        for slug, eps in sorted(by_podcast.items(), key=lambda x: -len(x[1]))[:10]:
            print(f"    {slug}: {len(eps)} missing")

        if args.fix:
            print(f"\n  Re-queuing {len(missing)} episodes (setting status='unknown')...")
            fixed = requeue_missing_episodes(store, missing)
            print(f"  Re-queued: {fixed}")
        else:
            print("  (run with --fix to re-queue these)")

    # STEP 2: Reconcile orphaned files on disk
    print(f"\nStep 2: Finding orphaned transcript files on disk...")

    total_files = 0
    total_matched = 0
    total_already = 0
    total_orphaned = 0
    total_bad = 0

    results = []

    # Process each podcast directory
    for podcast_dir in sorted(data_dir.iterdir()):
        if not podcast_dir.is_dir():
            continue

        if args.slug and podcast_dir.name != args.slug:
            continue

        result = reconcile_podcast(store, podcast_dir, verify=args.verify, apply=args.fix)

        if result.files_on_disk > 0:
            results.append(result)
            total_files += result.files_on_disk
            total_matched += result.matched
            total_already += result.already_fetched
            total_orphaned += result.orphaned
            total_bad += result.bad_quality

            # Show progress for podcasts with work to do
            if result.matched > 0 or result.orphaned > 0:
                status_parts = []
                if result.matched > 0:
                    status_parts.append(f"✅ {result.matched} matched")
                if result.already_fetched > 0:
                    status_parts.append(f"✓ {result.already_fetched} already")
                if result.orphaned > 0:
                    status_parts.append(f"⚠️ {result.orphaned} orphaned")
                if result.bad_quality > 0:
                    status_parts.append(f"❌ {result.bad_quality} bad")

                print(f"  {result.podcast_slug}: {', '.join(status_parts)}")

    # Summary
    print(f"\n{'=' * 60}")
    print("RECONCILIATION SUMMARY")
    print(f"{'=' * 60}")
    print(f"  Files on disk:    {total_files:,}")
    print(f"  Newly matched:    {total_matched:,}")
    print(f"  Already fetched:  {total_already:,}")
    print(f"  Orphaned:         {total_orphaned:,}")
    if args.verify:
        print(f"  Bad quality:      {total_bad:,}")

    if args.fix:
        print(f"\nDatabase updated:")
        print(f"  - Re-queued {len(missing)} episodes with missing files")
        print(f"  - Registered {total_matched:,} orphaned transcript files")
    else:
        print(f"\nRun with --fix to apply these changes")

    # Show sample orphans if any
    if total_orphaned > 0 and args.verbose:
        print(f"\n⚠️ Sample orphaned files (no matching episode):")
        for result in results:
            if result.orphan_files:
                print(f"\n  {result.podcast_slug}/transcripts/")
                for f in result.orphan_files[:5]:
                    print(f"    - {f}")


if __name__ == "__main__":
    main()
