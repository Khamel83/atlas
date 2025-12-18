"""
Atlas Status Formatter

Formats AtlasStatus into human-readable output.
"""

from .collector import AtlasStatus


def format_status(status: AtlasStatus, color: bool = True) -> str:
    """Format AtlasStatus as a compact, readable string."""
    lines = []

    # Colors (ANSI escape codes)
    if color:
        GREEN = "\033[92m"
        RED = "\033[91m"
        YELLOW = "\033[93m"
        CYAN = "\033[96m"
        BOLD = "\033[1m"
        DIM = "\033[2m"
        RESET = "\033[0m"
    else:
        GREEN = RED = YELLOW = CYAN = BOLD = DIM = RESET = ""

    # Header
    lines.append(f"{BOLD}ATLAS STATUS{RESET}")
    lines.append("=" * 50)
    lines.append("")

    # Services
    lines.append(f"{BOLD}SERVICES{RESET}")
    for svc in status.services:
        if svc.status == "running":
            status_str = f"{GREEN}running{RESET}"
            uptime_str = f"  {DIM}{svc.uptime or ''}{RESET}"
        else:
            status_str = f"{RED}stopped{RESET}"
            uptime_str = ""

        enabled_str = "" if svc.enabled else f"  {DIM}(disabled){RESET}"
        lines.append(f"  {svc.name:<28} {status_str}{uptime_str}{enabled_str}")
    lines.append("")

    # Timers
    lines.append(f"{BOLD}TIMERS{RESET}")
    if status.timers:
        for timer in status.timers:
            next_str = timer.next_run or "-"
            lines.append(f"  {timer.name:<28} {DIM}{next_str}{RESET}")
    else:
        lines.append(f"  {DIM}(no active timers){RESET}")
    lines.append("")

    # Podcasts
    lines.append(f"{BOLD}PODCASTS{RESET}")
    coverage_color = GREEN if status.podcasts.coverage >= 80 else YELLOW if status.podcasts.coverage >= 50 else RED
    lines.append(f"  Coverage:   {coverage_color}{status.podcasts.coverage:.1f}%{RESET}  ({status.podcasts.fetched:,} / {status.podcasts.total:,})")
    lines.append(f"  Pending:    {status.podcasts.pending:,}")
    lines.append(f"  Failed:     {status.podcasts.failed:,}")
    lines.append("")

    # Content
    lines.append(f"{BOLD}CONTENT{RESET}")
    lines.append(f"  Articles:     {status.content.articles:,}")
    lines.append(f"  Newsletters:  {status.content.newsletters:,}")
    lines.append(f"  Stratechery:  {status.content.stratechery:,}")
    lines.append(f"  Notes:        {status.content.notes:,}")
    if status.content.youtube > 0:
        lines.append(f"  YouTube:      {status.content.youtube:,}")
    lines.append("")

    # URL Queue
    lines.append(f"{BOLD}URL QUEUE{RESET}")
    lines.append(f"  Fetched:    {status.url_queue.fetched:,}")
    lines.append(f"  Failed:     {status.url_queue.failed:,}")
    lines.append(f"  Pending:    {status.url_queue.pending:,}")
    lines.append("")

    # Whisper Queue (only show if there's activity)
    wq = status.whisper_queue
    if wq.total_episodes > 0 or wq.audio_downloaded > 0:
        lines.append(f"{BOLD}WHISPER QUEUE{RESET}  {DIM}(Mac Mini local transcription){RESET}")
        remaining = wq.total_episodes - wq.imported
        if remaining > 0:
            lines.append(f"  Episodes:   {remaining:,} remaining")
        else:
            lines.append(f"  Episodes:   {GREEN}0 remaining{RESET}")
        lines.append(f"  Downloaded: {wq.audio_downloaded:,} audio files")
        if wq.transcripts_waiting > 0:
            lines.append(f"  Waiting:    {YELLOW}{wq.transcripts_waiting:,} transcripts to import{RESET}")
        lines.append(f"  Imported:   {wq.imported:,}")
        lines.append("")

    # Quality
    lines.append(f"{BOLD}QUALITY{RESET}")
    total = status.quality.total
    if total > 0:
        good_pct = status.quality.percentage("good")
        marginal_pct = status.quality.percentage("marginal")
        bad_pct = status.quality.percentage("bad")

        good_color = GREEN if good_pct >= 80 else YELLOW
        lines.append(f"  Good:       {good_color}{status.quality.good:,}{RESET}  ({good_pct:.1f}%)")
        lines.append(f"  Marginal:   {YELLOW}{status.quality.marginal:,}{RESET}  ({marginal_pct:.1f}%)")
        lines.append(f"  Bad:        {RED}{status.quality.bad:,}{RESET}  ({bad_pct:.1f}%)")
    else:
        lines.append(f"  {DIM}(no quality data){RESET}")
    lines.append("")

    # Errors (if any)
    if status.errors:
        lines.append(f"{RED}ERRORS{RESET}")
        for error in status.errors:
            lines.append(f"  {DIM}{error}{RESET}")
        lines.append("")

    # Detailed reports hint
    lines.append(f"{BOLD}DETAILED REPORTS{RESET}")
    lines.append(f"  {DIM}Per-podcast:{RESET}  ./scripts/atlas_status.py --podcasts")
    lines.append(f"  {DIM}Per-domain:{RESET}   ./scripts/atlas_status.py --urls")
    lines.append(f"  {DIM}Saved reports:{RESET} data/reports/podcast_status.md")
    lines.append(f"                data/reports/url_status.md")
    lines.append("")

    # Timestamp
    lines.append(f"{DIM}Updated: {status.timestamp.strftime('%Y-%m-%d %H:%M:%S')}{RESET}")

    return "\n".join(lines)


def format_json(status: AtlasStatus) -> dict:
    """Format AtlasStatus as a JSON-serializable dict."""
    return {
        "timestamp": status.timestamp.isoformat(),
        "services": [
            {
                "name": s.name,
                "status": s.status,
                "uptime": s.uptime,
                "enabled": s.enabled
            }
            for s in status.services
        ],
        "timers": [
            {
                "name": t.name,
                "next_run": t.next_run
            }
            for t in status.timers
        ],
        "podcasts": {
            "total": status.podcasts.total,
            "fetched": status.podcasts.fetched,
            "pending": status.podcasts.pending,
            "failed": status.podcasts.failed,
            "excluded": status.podcasts.excluded,
            "coverage": round(status.podcasts.coverage, 1)
        },
        "content": {
            "articles": status.content.articles,
            "newsletters": status.content.newsletters,
            "stratechery": status.content.stratechery,
            "notes": status.content.notes,
            "youtube": status.content.youtube
        },
        "url_queue": {
            "fetched": status.url_queue.fetched,
            "failed": status.url_queue.failed,
            "pending": status.url_queue.pending
        },
        "quality": {
            "good": status.quality.good,
            "marginal": status.quality.marginal,
            "bad": status.quality.bad,
            "total": status.quality.total
        },
        "whisper_queue": {
            "total_episodes": status.whisper_queue.total_episodes,
            "audio_downloaded": status.whisper_queue.audio_downloaded,
            "transcripts_waiting": status.whisper_queue.transcripts_waiting,
            "imported": status.whisper_queue.imported
        },
        "errors": status.errors
    }
