"""
Atlas Status Collector

Gathers status data from all Atlas subsystems:
- Systemd services and timers
- Podcast transcript database
- Content quality database
- URL fetcher state
- Link queue database
"""

import json
import sqlite3
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class ServiceStatus:
    name: str
    status: str  # running, stopped, failed
    uptime: Optional[str] = None
    enabled: bool = False


@dataclass
class TimerStatus:
    name: str
    next_run: Optional[str] = None
    last_run: Optional[str] = None


@dataclass
class PodcastStats:
    total: int = 0
    fetched: int = 0
    pending: int = 0
    failed: int = 0
    excluded: int = 0
    coverage: float = 0.0


@dataclass
class ContentStats:
    articles: int = 0
    newsletters: int = 0
    stratechery: int = 0
    notes: int = 0
    youtube: int = 0


@dataclass
class UrlQueueStats:
    fetched: int = 0
    failed: int = 0
    pending: int = 0


@dataclass
class QualityStats:
    good: int = 0
    marginal: int = 0
    bad: int = 0

    @property
    def total(self) -> int:
        return self.good + self.marginal + self.bad

    def percentage(self, level: str) -> float:
        if self.total == 0:
            return 0.0
        value = getattr(self, level, 0)
        return (value / self.total) * 100


@dataclass
class WhisperQueueStats:
    """Local Whisper transcription queue status."""
    total_episodes: int = 0  # Episodes marked 'local'
    audio_downloaded: int = 0  # Files in audio folder
    transcripts_waiting: int = 0  # .txt/.md files waiting for import
    imported: int = 0  # Already processed
    # Diarization stats (WhisperX with speaker labels)
    diarized_transcripts: int = 0  # .json files with speaker labels
    diarized_audio: int = 0  # Audio files moved after diarization
    episodes_with_speakers: int = 0  # Episodes with speaker mappings in DB


@dataclass
class AtlasStatus:
    """Complete Atlas system status."""
    timestamp: datetime = field(default_factory=datetime.now)
    services: list[ServiceStatus] = field(default_factory=list)
    timers: list[TimerStatus] = field(default_factory=list)
    podcasts: PodcastStats = field(default_factory=PodcastStats)
    content: ContentStats = field(default_factory=ContentStats)
    url_queue: UrlQueueStats = field(default_factory=UrlQueueStats)
    quality: QualityStats = field(default_factory=QualityStats)
    whisper_queue: WhisperQueueStats = field(default_factory=WhisperQueueStats)
    errors: list[str] = field(default_factory=list)


class StatusCollector:
    """Collects status from all Atlas subsystems."""

    def __init__(self, data_dir: Path = None):
        self.data_dir = data_dir or Path("/home/khamel83/github/atlas/data")
        self.status = AtlasStatus()

    def collect_all(self) -> AtlasStatus:
        """Collect status from all sources."""
        self._collect_services()
        self._collect_timers()
        self._collect_podcasts()
        self._collect_content()
        self._collect_url_queue()
        self._collect_quality()
        self._collect_whisper_queue()
        return self.status

    def _collect_services(self):
        """Get systemd service status."""
        services = [
            "atlas-daemon",
            "atlas-simple-fetcher",
            "atlas-url-fetcher",
        ]

        for name in services:
            try:
                # Check if running
                result = subprocess.run(
                    ["systemctl", "is-active", name],
                    capture_output=True,
                    text=True
                )
                is_running = result.stdout.strip() == "active"

                # Check if enabled
                result = subprocess.run(
                    ["systemctl", "is-enabled", name],
                    capture_output=True,
                    text=True
                )
                is_enabled = result.stdout.strip() == "enabled"

                # Get uptime if running
                uptime = None
                if is_running:
                    result = subprocess.run(
                        ["systemctl", "show", name, "--property=ActiveEnterTimestamp"],
                        capture_output=True,
                        text=True
                    )
                    if "=" in result.stdout:
                        timestamp_str = result.stdout.split("=")[1].strip()
                        if timestamp_str:
                            try:
                                start_time = datetime.strptime(
                                    timestamp_str,
                                    "%a %Y-%m-%d %H:%M:%S %Z"
                                )
                                delta = datetime.now() - start_time
                                hours, remainder = divmod(int(delta.total_seconds()), 3600)
                                minutes = remainder // 60
                                if hours > 0:
                                    uptime = f"{hours}h {minutes}m"
                                else:
                                    uptime = f"{minutes}m"
                            except ValueError:
                                pass

                self.status.services.append(ServiceStatus(
                    name=name,
                    status="running" if is_running else "stopped",
                    uptime=uptime,
                    enabled=is_enabled
                ))
            except Exception as e:
                self.status.errors.append(f"Service {name}: {e}")
                self.status.services.append(ServiceStatus(
                    name=name,
                    status="unknown"
                ))

    def _collect_timers(self):
        """Get systemd timer status."""
        try:
            result = subprocess.run(
                ["systemctl", "list-timers", "--all", "--no-pager"],
                capture_output=True,
                text=True
            )

            for line in result.stdout.split("\n"):
                if "atlas-" in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        # Find the timer name (contains .timer)
                        timer_name = None
                        for part in parts:
                            if "atlas-" in part and ".timer" in part:
                                timer_name = part.replace(".timer", "")
                                break

                        if timer_name:
                            # Parse next run time (first parts before LAST)
                            next_run = None
                            if parts[0] != "-":
                                next_run = " ".join(parts[:3])

                            self.status.timers.append(TimerStatus(
                                name=timer_name,
                                next_run=next_run
                            ))
        except Exception as e:
            self.status.errors.append(f"Timers: {e}")

    def _collect_podcasts(self):
        """Get podcast transcript stats from SQLite."""
        db_path = self.data_dir / "podcasts" / "atlas_podcasts.db"

        if not db_path.exists():
            self.status.errors.append(f"Podcast DB not found: {db_path}")
            return

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Get counts by status
            cursor.execute("""
                SELECT transcript_status, COUNT(*)
                FROM episodes
                GROUP BY transcript_status
            """)

            for status, count in cursor.fetchall():
                if status == "fetched":
                    self.status.podcasts.fetched = count
                elif status == "unknown":
                    self.status.podcasts.pending = count
                elif status == "failed":
                    self.status.podcasts.failed = count
                elif status == "excluded":
                    self.status.podcasts.excluded = count

            # Calculate totals (in-scope = not excluded)
            self.status.podcasts.total = (
                self.status.podcasts.fetched +
                self.status.podcasts.pending +
                self.status.podcasts.failed
            )

            if self.status.podcasts.total > 0:
                self.status.podcasts.coverage = (
                    self.status.podcasts.fetched / self.status.podcasts.total
                ) * 100

            conn.close()
        except Exception as e:
            self.status.errors.append(f"Podcast DB: {e}")

    def _collect_content(self):
        """Count content files by type."""
        content_dir = self.data_dir / "content"
        stratechery_dir = self.data_dir / "stratechery"

        try:
            # Articles
            article_dir = content_dir / "article"
            if article_dir.exists():
                self.status.content.articles = len(list(
                    article_dir.rglob("content.md")
                ))

            # Newsletters
            newsletter_dir = content_dir / "newsletter"
            if newsletter_dir.exists():
                self.status.content.newsletters = len(list(
                    newsletter_dir.rglob("content.md")
                ))

            # Notes
            note_dir = content_dir / "note"
            if note_dir.exists():
                self.status.content.notes = len(list(
                    note_dir.rglob("content.md")
                ))

            # YouTube
            youtube_dir = content_dir / "youtube"
            if youtube_dir.exists():
                self.status.content.youtube = len(list(
                    youtube_dir.rglob("content.md")
                ))

            # Stratechery
            if stratechery_dir.exists():
                self.status.content.stratechery = len(list(
                    stratechery_dir.rglob("*.md")
                ))
        except Exception as e:
            self.status.errors.append(f"Content files: {e}")

    def _collect_url_queue(self):
        """Get URL fetcher state from JSON."""
        state_file = self.data_dir / "url_fetcher_state.json"
        queue_file = self.data_dir / "url_queue.txt"

        try:
            if state_file.exists():
                with open(state_file) as f:
                    state = json.load(f)
                    self.status.url_queue.fetched = len(state.get("fetched", {}))
                    self.status.url_queue.failed = len(state.get("failed", {}))

            if queue_file.exists():
                with open(queue_file) as f:
                    total_in_queue = sum(1 for line in f if line.strip())
                # Pending = queue total - fetched - failed
                self.status.url_queue.pending = max(
                    0,
                    total_in_queue - self.status.url_queue.fetched - self.status.url_queue.failed
                )
        except Exception as e:
            self.status.errors.append(f"URL queue: {e}")

    def _collect_quality(self):
        """Get content quality stats from SQLite."""
        db_path = self.data_dir / "quality" / "verification.db"

        if not db_path.exists():
            self.status.errors.append(f"Quality DB not found: {db_path}")
            return

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT quality, COUNT(*)
                FROM verifications
                GROUP BY quality
            """)

            for quality, count in cursor.fetchall():
                if quality == "good":
                    self.status.quality.good = count
                elif quality == "marginal":
                    self.status.quality.marginal = count
                elif quality == "bad":
                    self.status.quality.bad = count

            conn.close()
        except Exception as e:
            self.status.errors.append(f"Quality DB: {e}")

    def _collect_whisper_queue(self):
        """Get Whisper transcription queue status."""
        whisper_dir = self.data_dir / "whisper_queue"
        db_path = self.data_dir / "podcasts" / "atlas_podcasts.db"

        try:
            # Count episodes marked 'local' in database
            if db_path.exists():
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) FROM episodes WHERE transcript_status = 'local'"
                )
                self.status.whisper_queue.total_episodes = cursor.fetchone()[0]

                # Count episodes with speaker mappings
                try:
                    cursor.execute(
                        "SELECT COUNT(DISTINCT episode_id) FROM episode_speakers"
                    )
                    self.status.whisper_queue.episodes_with_speakers = cursor.fetchone()[0]
                except sqlite3.OperationalError:
                    # Table doesn't exist yet
                    pass

                conn.close()

            # Count audio files downloaded (pending transcription)
            audio_dir = whisper_dir / "audio"
            if audio_dir.exists():
                self.status.whisper_queue.audio_downloaded = len(list(
                    audio_dir.glob("*.mp3")
                ))

            # Count transcripts waiting for import
            transcripts_dir = whisper_dir / "transcripts"
            if transcripts_dir.exists():
                txt_files = len(list(transcripts_dir.glob("*.txt")))
                md_files = len(list(transcripts_dir.glob("*.md")))
                json_files = len(list(transcripts_dir.glob("*.json")))
                self.status.whisper_queue.transcripts_waiting = txt_files + md_files + json_files
                # JSON files are WhisperX diarized output
                self.status.whisper_queue.diarized_transcripts = json_files

            # Also check audio folder for JSON (WhisperX may output there)
            if audio_dir.exists():
                json_in_audio = len(list(audio_dir.glob("*.json")))
                self.status.whisper_queue.diarized_transcripts += json_in_audio

            # Count diarized audio (moved after processing)
            diarized_dir = whisper_dir / "diarized_audio"
            if diarized_dir.exists():
                self.status.whisper_queue.diarized_audio = len(list(
                    diarized_dir.glob("*.mp3")
                ))

            # Count already processed
            processed_dir = whisper_dir / "processed_files"
            if processed_dir.exists():
                self.status.whisper_queue.imported = len(list(
                    processed_dir.iterdir()
                ))
        except Exception as e:
            self.status.errors.append(f"Whisper queue: {e}")


def collect_status(data_dir: Path = None) -> AtlasStatus:
    """Convenience function to collect all status."""
    collector = StatusCollector(data_dir)
    return collector.collect_all()
