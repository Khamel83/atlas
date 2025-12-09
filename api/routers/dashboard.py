"""
Progress Dashboard Router

Provides real-time status endpoints for monitoring Atlas ingestion.
"""

import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class PodcastStats(BaseModel):
    slug: str
    name: str
    total: int
    fetched: int
    pending: int
    failed: int
    coverage: float


class OverallStats(BaseModel):
    total_episodes: int
    fetched: int
    pending: int
    failed: int
    coverage: float
    estimated_hours: float
    podcasts: List[PodcastStats]


class ProcessStatus(BaseModel):
    name: str
    running: bool
    pid: Optional[int]
    last_activity: Optional[str]


class SystemStatus(BaseModel):
    overall: OverallStats
    processes: List[ProcessStatus]
    timers: List[Dict]
    stratechery_archive: Optional[Dict]
    last_updated: str


def get_podcast_store():
    """Get podcast store instance"""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from modules.podcasts.store import PodcastStore
    return PodcastStore('data/podcasts/atlas_podcasts.db')


def get_podcast_stats() -> OverallStats:
    """Get podcast transcript statistics"""
    store = get_podcast_store()

    podcasts = store.list_podcasts()
    podcast_stats = []

    total_all = 0
    fetched_all = 0
    pending_all = 0
    failed_all = 0

    for podcast in podcasts:
        episodes = store.get_episodes_by_podcast(podcast.id)

        # Only count non-excluded
        active = [e for e in episodes if e.transcript_status != 'excluded']

        total = len(active)
        fetched = len([e for e in active if e.transcript_status == 'fetched'])
        pending = len([e for e in active if e.transcript_status in ('unknown', 'found')])
        failed = len([e for e in active if e.transcript_status == 'failed'])

        if total > 0:
            coverage = (fetched / total) * 100
            podcast_stats.append(PodcastStats(
                slug=podcast.slug,
                name=podcast.name,
                total=total,
                fetched=fetched,
                pending=pending,
                failed=failed,
                coverage=round(coverage, 1)
            ))

            total_all += total
            fetched_all += fetched
            pending_all += pending
            failed_all += failed

    # Sort by pending (most work remaining first)
    podcast_stats.sort(key=lambda x: x.pending, reverse=True)

    coverage_all = (fetched_all / total_all * 100) if total_all > 0 else 0
    # Estimate: ~11 seconds per episode average
    estimated_hours = (pending_all * 11) / 3600

    return OverallStats(
        total_episodes=total_all,
        fetched=fetched_all,
        pending=pending_all,
        failed=failed_all,
        coverage=round(coverage_all, 1),
        estimated_hours=round(estimated_hours, 1),
        podcasts=podcast_stats[:20]  # Top 20 by pending
    )


def get_running_processes() -> List[ProcessStatus]:
    """Check which Atlas processes are running"""
    import subprocess

    processes = []

    # Check for running Python processes
    try:
        result = subprocess.run(
            ['pgrep', '-af', 'python.*atlas|python.*podcasts|python.*stratechery'],
            capture_output=True, text=True
        )

        for line in result.stdout.strip().split('\n'):
            if line:
                parts = line.split(' ', 1)
                if len(parts) >= 2:
                    pid = int(parts[0])
                    cmd = parts[1]

                    # Determine process name
                    if 'stratechery_crawler' in cmd:
                        name = 'Stratechery Archive Crawler'
                    elif 'fetch-transcripts' in cmd:
                        name = 'Podcast Transcript Fetcher'
                    elif 'retry_failed' in cmd:
                        name = 'URL Retry Processor'
                    elif 'parallel_youtube' in cmd:
                        name = 'Parallel YouTube Worker'
                    else:
                        name = 'Atlas Process'

                    processes.append(ProcessStatus(
                        name=name,
                        running=True,
                        pid=pid,
                        last_activity=None
                    ))
    except Exception:
        pass

    return processes


def get_timer_status() -> List[Dict]:
    """Get systemd timer status"""
    import subprocess

    timers = []

    try:
        result = subprocess.run(
            ['systemctl', 'list-timers', '--no-pager'],
            capture_output=True, text=True
        )

        for line in result.stdout.split('\n'):
            if 'atlas' in line.lower():
                parts = line.split()
                if len(parts) >= 5:
                    timers.append({
                        'name': parts[-1] if parts else 'unknown',
                        'next': ' '.join(parts[:3]) if len(parts) > 3 else 'unknown',
                        'last': parts[4] if len(parts) > 4 else 'unknown'
                    })
    except Exception:
        pass

    return timers


def get_stratechery_progress() -> Optional[Dict]:
    """Get Stratechery archive crawler progress"""
    progress_file = Path('data/stratechery/crawl_progress.json')

    if not progress_file.exists():
        return None

    try:
        with open(progress_file) as f:
            data = json.load(f)

        return {
            'crawled': len(data.get('crawled_urls', [])),
            'failed': len(data.get('failed_urls', [])),
            'articles': data.get('stats', {}).get('articles', 0),
            'podcasts': data.get('stats', {}).get('podcasts', 0),
            'last_run': data.get('last_run')
        }
    except Exception:
        return None


@router.get("/status", response_model=SystemStatus)
async def get_dashboard_status():
    """Get complete system status"""
    return SystemStatus(
        overall=get_podcast_stats(),
        processes=get_running_processes(),
        timers=get_timer_status(),
        stratechery_archive=get_stratechery_progress(),
        last_updated=datetime.now().isoformat()
    )


@router.get("/podcasts")
async def get_all_podcast_stats():
    """Get stats for all podcasts"""
    store = get_podcast_store()
    podcasts = store.list_podcasts()

    stats = []
    for podcast in podcasts:
        episodes = store.get_episodes_by_podcast(podcast.id)
        active = [e for e in episodes if e.transcript_status != 'excluded']

        if active:
            fetched = len([e for e in active if e.transcript_status == 'fetched'])
            stats.append({
                'slug': podcast.slug,
                'name': podcast.name,
                'total': len(active),
                'fetched': fetched,
                'coverage': round((fetched / len(active)) * 100, 1)
            })

    stats.sort(key=lambda x: x['coverage'])
    return stats


@router.get("/logs/{log_name}")
async def get_recent_logs(log_name: str, lines: int = 50):
    """Get recent log entries"""
    log_files = {
        'transcripts': '/tmp/atlas-batch.log',
        'stratechery': '/tmp/stratechery-archive.log',
        'retry': '/tmp/atlas-retry.log',
    }

    if log_name not in log_files:
        raise HTTPException(404, f"Unknown log: {log_name}")

    log_path = Path(log_files[log_name])
    if not log_path.exists():
        return {'lines': [], 'error': 'Log file not found'}

    try:
        with open(log_path) as f:
            all_lines = f.readlines()
            return {'lines': all_lines[-lines:]}
    except Exception as e:
        return {'lines': [], 'error': str(e)}
