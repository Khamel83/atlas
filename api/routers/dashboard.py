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
    """Get podcast transcript statistics using efficient single-query methods"""
    store = get_podcast_store()

    # Get all podcast stats in a single query (was N+1 queries before)
    all_stats = store.get_all_podcast_stats()

    # Get overall stats in a single query
    overall = store.get_overall_stats()

    # Convert to PodcastStats objects and sort by pending
    podcast_stats = [
        PodcastStats(
            slug=s['slug'],
            name=s['name'],
            total=s['total'],
            fetched=s['fetched'],
            pending=s['pending'],
            failed=s['failed'],
            coverage=s['coverage']
        )
        for s in all_stats
    ]
    podcast_stats.sort(key=lambda x: x.pending, reverse=True)

    # Estimate: ~11 seconds per episode average
    estimated_hours = (overall['pending'] * 11) / 3600

    return OverallStats(
        total_episodes=overall['total_episodes'],
        fetched=overall['fetched'],
        pending=overall['pending'],
        failed=overall['failed'],
        coverage=overall['coverage'],
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
    """Get stats for all podcasts using efficient single query"""
    store = get_podcast_store()

    # Get all stats in a single query (was N+1 before)
    stats = store.get_all_podcast_stats()

    # Sort by coverage (lowest first to show what needs work)
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
