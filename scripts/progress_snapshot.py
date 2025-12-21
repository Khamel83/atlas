#!/usr/bin/env python3
"""
Progress Snapshot - Captures current state for tracking over time.

Runs hourly via systemd timer, stores snapshots in data/progress/
Shows REAL progress rates, not estimates.

Usage:
    python scripts/progress_snapshot.py              # Take snapshot
    python scripts/progress_snapshot.py --report     # Show 24h progress
    python scripts/progress_snapshot.py --rate       # Show processing rate
"""

import json
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

DATA_DIR = Path("/home/khamel83/github/atlas/data")
PROGRESS_DIR = DATA_DIR / "progress"
PROGRESS_FILE = PROGRESS_DIR / "snapshots.jsonl"


def get_current_stats():
    """Get current stats from all sources."""
    stats = {
        "timestamp": datetime.now().isoformat(),
        "podcasts": {},
        "urls": {},
        "whisper": {},
        "content": {}
    }
    
    # Podcasts
    db_path = DATA_DIR / "podcasts" / "atlas_podcasts.db"
    if db_path.exists():
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("""
            SELECT transcript_status, COUNT(*) FROM episodes 
            WHERE transcript_status != 'excluded'
            GROUP BY transcript_status
        """)
        for status, count in cur.fetchall():
            stats["podcasts"][status] = count
        
        # Total
        cur.execute("SELECT COUNT(*) FROM episodes WHERE transcript_status != 'excluded'")
        stats["podcasts"]["total"] = cur.fetchone()[0]
        conn.close()
    
    # URLs
    state_file = DATA_DIR / "url_fetcher_state.json"
    queue_file = DATA_DIR / "url_queue.txt"
    if state_file.exists():
        with open(state_file) as f:
            state = json.load(f)
            stats["urls"]["fetched"] = len(state.get("fetched", {}))
            stats["urls"]["retrying"] = len(state.get("retrying", {}))
            stats["urls"]["truly_failed"] = len(state.get("truly_failed", {}))
            # Legacy
            if "failed" in state and "retrying" not in state:
                stats["urls"]["retrying"] = len(state.get("failed", {}))
    
    if queue_file.exists():
        with open(queue_file) as f:
            stats["urls"]["queue_total"] = sum(1 for line in f if line.strip())
    
    # Whisper
    whisper_dir = DATA_DIR / "whisper_queue"
    if whisper_dir.exists():
        audio_dir = whisper_dir / "audio"
        transcripts_dir = whisper_dir / "transcripts"
        stats["whisper"]["audio_waiting"] = len(list(audio_dir.glob("*.mp3"))) if audio_dir.exists() else 0
        stats["whisper"]["transcripts_waiting"] = len(list(transcripts_dir.glob("*"))) if transcripts_dir.exists() else 0
    
    # Content counts
    content_dir = DATA_DIR / "content"
    if content_dir.exists():
        stats["content"]["articles"] = len(list((content_dir / "article").rglob("content.md"))) if (content_dir / "article").exists() else 0
    
    articles_dir = DATA_DIR / "articles"
    if articles_dir.exists():
        stats["content"]["url_articles"] = len(list(articles_dir.rglob("*.md")))
    
    return stats


def save_snapshot(stats):
    """Append snapshot to JSONL file."""
    PROGRESS_DIR.mkdir(parents=True, exist_ok=True)
    with open(PROGRESS_FILE, "a") as f:
        f.write(json.dumps(stats) + "\n")
    print(f"📸 Snapshot saved at {stats['timestamp']}")


def load_snapshots(hours=24):
    """Load snapshots from the last N hours."""
    if not PROGRESS_FILE.exists():
        return []
    
    cutoff = datetime.now() - timedelta(hours=hours)
    snapshots = []
    
    with open(PROGRESS_FILE) as f:
        for line in f:
            try:
                snap = json.loads(line.strip())
                snap_time = datetime.fromisoformat(snap["timestamp"])
                if snap_time >= cutoff:
                    snapshots.append(snap)
            except:
                pass
    
    return snapshots


def show_report():
    """Show progress report for last 24 hours."""
    snapshots = load_snapshots(24)
    
    if len(snapshots) < 2:
        print("❌ Need at least 2 snapshots for comparison.")
        print(f"   Current snapshots: {len(snapshots)}")
        print("   Run this script hourly to build history.")
        return
    
    first = snapshots[0]
    last = snapshots[-1]
    
    first_time = datetime.fromisoformat(first["timestamp"])
    last_time = datetime.fromisoformat(last["timestamp"])
    hours = (last_time - first_time).total_seconds() / 3600
    
    print("=" * 60)
    print("📊 ATLAS PROGRESS REPORT")
    print("=" * 60)
    print(f"Period: {first_time.strftime('%Y-%m-%d %H:%M')} → {last_time.strftime('%Y-%m-%d %H:%M')}")
    print(f"Duration: {hours:.1f} hours ({len(snapshots)} snapshots)")
    print()
    
    # Podcasts
    p_first = first.get("podcasts", {})
    p_last = last.get("podcasts", {})
    p_fetched_delta = p_last.get("fetched", 0) - p_first.get("fetched", 0)
    p_pending_first = p_first.get("unknown", 0)
    p_pending_last = p_last.get("unknown", 0)
    
    print("🎙️  PODCASTS")
    print(f"   Fetched:  {p_first.get('fetched', 0):,} → {p_last.get('fetched', 0):,}  (+{p_fetched_delta:,})")
    print(f"   Pending:  {p_pending_first:,} → {p_pending_last:,}  ({p_pending_last - p_pending_first:+,})")
    if hours > 0 and p_fetched_delta > 0:
        rate = p_fetched_delta / hours
        remaining = p_pending_last
        eta_hours = remaining / rate if rate > 0 else float('inf')
        print(f"   Rate:     {rate:.1f}/hour")
        if eta_hours < 100:
            print(f"   ETA:      {eta_hours:.1f} hours")
    print()
    
    # URLs
    u_first = first.get("urls", {})
    u_last = last.get("urls", {})
    u_fetched_delta = u_last.get("fetched", 0) - u_first.get("fetched", 0)
    
    print("🌐 URLS")
    print(f"   Fetched:  {u_first.get('fetched', 0):,} → {u_last.get('fetched', 0):,}  (+{u_fetched_delta:,})")
    print(f"   Retrying: {u_first.get('retrying', 0):,} → {u_last.get('retrying', 0):,}")
    if hours > 0 and u_fetched_delta > 0:
        rate = u_fetched_delta / hours
        # Calculate true pending
        pending = u_last.get("queue_total", 0) - u_last.get("fetched", 0) - u_last.get("retrying", 0) - u_last.get("truly_failed", 0)
        pending = max(0, pending)
        eta_hours = pending / rate if rate > 0 else float('inf')
        print(f"   Rate:     {rate:.1f}/hour ({rate * 24:.0f}/day)")
        print(f"   Pending:  {pending:,}")
        if eta_hours < 100:
            print(f"   ETA:      {eta_hours:.1f} hours")
    print()
    
    # Whisper
    w_first = first.get("whisper", {})
    w_last = last.get("whisper", {})
    print("🎙️  WHISPER QUEUE")
    print(f"   Audio:    {w_first.get('audio_waiting', 0)} → {w_last.get('audio_waiting', 0)}")
    print(f"   Transcripts: {w_first.get('transcripts_waiting', 0)} → {w_last.get('transcripts_waiting', 0)}")
    print()
    
    print("=" * 60)
    

def show_current():
    """Show current state."""
    stats = get_current_stats()
    
    print("📊 CURRENT STATE")
    print("-" * 40)
    
    p = stats["podcasts"]
    total = p.get("total", 0)
    fetched = p.get("fetched", 0)
    pending = p.get("unknown", 0)
    pct = (fetched / total * 100) if total > 0 else 0
    print(f"🎙️  Podcasts: {fetched:,}/{total:,} ({pct:.1f}%) - {pending:,} pending")
    
    u = stats["urls"]
    print(f"🌐 URLs: {u.get('fetched', 0):,} fetched, {u.get('retrying', 0):,} retrying")
    
    w = stats["whisper"]
    print(f"🎤 Whisper: {w.get('audio_waiting', 0)} audio, {w.get('transcripts_waiting', 0)} transcripts")
    
    print()


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", "-r", action="store_true", help="Show 24h progress report")
    parser.add_argument("--current", "-c", action="store_true", help="Show current state only")
    args = parser.parse_args()
    
    if args.report:
        show_report()
    elif args.current:
        show_current()
    else:
        # Default: take snapshot and show current
        stats = get_current_stats()
        save_snapshot(stats)
        show_current()


if __name__ == "__main__":
    main()
