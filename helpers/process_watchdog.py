#!/usr/bin/env python3
"""
Atlas Process Watchdog

Proactively monitors Atlas processes for anomalous behavior and automatically
handles stuck/runaway processes with intelligent restart logic.

Features:
- Detects processes running too long for their expected duration
- Monitors CPU/memory usage patterns
- Identifies stuck network connections (CLOSE-WAIT)
- Tracks progress indicators (database changes, file creation)
- Automatic process termination and restart with backoff
- Configurable thresholds per process type
"""

import os
import sys
import time
import json
import psutil
import sqlite3
import logging
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

@dataclass
class ProcessConfig:
    """Configuration for monitoring a specific process type"""
    name: str
    command_pattern: str  # Regex pattern to match command
    max_runtime_minutes: int  # Max expected runtime
    max_cpu_percent: float   # Max sustained CPU usage
    max_memory_mb: int      # Max memory usage
    progress_indicators: List[str]  # Files/DB tables to check for progress
    restart_command: Optional[str] = None  # Command to restart if killed
    restart_delay_minutes: int = 5  # Wait before restart
    max_restarts: int = 3   # Max restarts before giving up

@dataclass
class ProcessStatus:
    """Status of a monitored process"""
    pid: int
    name: str
    cmd: str
    start_time: datetime
    runtime_minutes: float
    cpu_percent: float
    memory_mb: float
    network_connections: int
    close_wait_connections: int
    progress_score: float
    anomaly_reasons: List[str]
    restart_count: int = 0
    last_restart: Optional[datetime] = None

class AtlasProcessWatchdog:
    """Intelligent process monitoring and management system"""

    def __init__(self):
        """Initialize the watchdog"""
        self.logger = self._setup_logging()
        self.config_file = Path("config/process_watchdog.json")
        self.state_file = Path("logs/process_watchdog_state.json")
        self.log_file = Path("logs/process_watchdog.log")

        # Create directories
        self.config_file.parent.mkdir(exist_ok=True)
        self.state_file.parent.mkdir(exist_ok=True)

        # Load configuration and state
        self.process_configs = self._load_configs()
        self.process_state = self._load_state()

        self.logger.info("Atlas Process Watchdog initialized")

    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler("logs/process_watchdog.log"),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger("ProcessWatchdog")

    def _load_configs(self) -> Dict[str, ProcessConfig]:
        """Load process monitoring configurations"""
        if not self.config_file.exists():
            self._create_default_config()

        with open(self.config_file, 'r') as f:
            config_data = json.load(f)

        configs = {}
        for name, data in config_data.items():
            configs[name] = ProcessConfig(**data)

        return configs

    def _create_default_config(self):
        """Create default monitoring configuration"""
        # AGGRESSIVE SETTINGS: Atlas is about slow accumulation, not speed
        # Kill processes early and retry later - nothing is time critical
        default_configs = {
            "podcast_fetcher": {
                "name": "Podcast Transcript Fetcher",
                "command_pattern": r"modules\.podcasts\.cli.*fetch-transcripts",
                "max_runtime_minutes": 30,  # Kill after 30 minutes
                "max_cpu_percent": 80.0,  # Allow high CPU initially
                "max_memory_mb": 500,
                "progress_indicators": [
                    "data/podcasts/atlas_podcasts.db:episodes:transcript_status=fetched"
                ],
                "restart_command": "python3 -m modules.podcasts.cli fetch-transcripts --all",
                "restart_delay_minutes": 30,  # Wait 30m before retry
                "max_restarts": 999  # Keep trying forever
            },
            "transcript_discovery": {
                "name": "Enhanced Transcript Discovery",
                "command_pattern": r"enhanced_transcript_discovery\.py",
                "max_runtime_minutes": 20,  # Kill after 20 minutes
                "max_cpu_percent": 70.0,
                "max_memory_mb": 300,
                "progress_indicators": [
                    "output:*.json:count"
                ],
                "restart_command": "python3 enhanced_transcript_discovery.py",
                "restart_delay_minutes": 60,  # Wait 1 hour before retry
                "max_restarts": 999
            },
            "article_processing": {
                "name": "Article Processing",
                "command_pattern": r"run\.py.*--all",
                "max_runtime_minutes": 15,  # Kill after 15 minutes
                "max_cpu_percent": 60.0,
                "max_memory_mb": 400,
                "progress_indicators": [
                    "data/atlas.db:content:count",
                    "output:*.md:count"
                ],
                "restart_command": "python3 run.py --all",
                "restart_delay_minutes": 20,  # Wait 20m before retry
                "max_restarts": 999
            },
            "search_indexing": {
                "name": "Search Index Population",
                "command_pattern": r"populate_search_index\.py",
                "max_runtime_minutes": 20,  # Kill after 20 minutes
                "max_cpu_percent": 50.0,
                "max_memory_mb": 300,
                "progress_indicators": [
                    "data/enhanced_search.db:search_index:count"
                ],
                "restart_command": "python3 populate_search_index.py",
                "restart_delay_minutes": 30,  # Wait 30m before retry
                "max_restarts": 999
            }
        }

        with open(self.config_file, 'w') as f:
            json.dump(default_configs, f, indent=2)

        self.logger.info(f"Created default watchdog config at {self.config_file}")

    def _load_state(self) -> Dict[str, Any]:
        """Load persistent state"""
        if not self.state_file.exists():
            return {}

        try:
            with open(self.state_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.warning(f"Failed to load state: {e}")
            return {}

    def _save_state(self):
        """Save persistent state"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.process_state, f, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")

    def _get_progress_score(self, indicators: List[str], baseline_time: datetime) -> float:
        """Calculate progress score based on indicators"""
        if not indicators:
            return 0.5  # Neutral score

        total_score = 0.0
        valid_indicators = 0

        for indicator in indicators:
            try:
                if ":" in indicator and indicator.count(":") >= 2:
                    # Database indicator: "db_path:table:condition"
                    parts = indicator.split(":")
                    db_path, table = parts[0], parts[1]
                    condition = ":".join(parts[2:]) if len(parts) > 2 else ""

                    if Path(db_path).exists():
                        conn = sqlite3.connect(db_path)
                        if condition:
                            if "=" in condition:
                                field, value = condition.split("=", 1)
                                query = f"SELECT COUNT(*) FROM {table} WHERE {field} = ?"
                                count = conn.execute(query, (value,)).fetchone()[0]
                            else:
                                count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                        else:
                            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                        conn.close()

                        # Score based on recent changes
                        total_score += min(1.0, count / 100.0)  # Up to 1.0 for 100+ items
                        valid_indicators += 1

                elif ":" in indicator:
                    # File pattern indicator: "directory:pattern:metric"
                    parts = indicator.split(":")
                    directory, pattern = parts[0], parts[1]
                    metric = parts[2] if len(parts) > 2 else "count"

                    if Path(directory).exists():
                        files = list(Path(directory).glob(pattern))
                        recent_files = [f for f in files if f.stat().st_mtime > baseline_time.timestamp()]

                        if metric == "count":
                            total_score += min(1.0, len(recent_files) / 10.0)  # Up to 1.0 for 10+ files
                        valid_indicators += 1

            except Exception as e:
                self.logger.debug(f"Progress indicator error {indicator}: {e}")
                continue

        return total_score / max(1, valid_indicators)

    def _detect_anomalies(self, status: ProcessStatus, config: ProcessConfig) -> List[str]:
        """Detect process anomalies - AGGRESSIVE: Kill early, retry later"""
        anomalies = []

        # AGGRESSIVE: Kill anything running too long (nothing should take hours)
        if status.runtime_minutes > config.max_runtime_minutes:
            anomalies.append(f"KILL: Runtime exceeded {config.max_runtime_minutes}m (actual: {status.runtime_minutes:.1f}m)")

        # AGGRESSIVE: Kill processes with no progress after just 10 minutes
        if status.runtime_minutes > 10 and status.progress_score < 0.1:
            anomalies.append(f"KILL: No progress after {status.runtime_minutes:.1f}m (score: {status.progress_score:.2f})")

        # AGGRESSIVE: Kill anything with stuck network connections immediately
        if status.close_wait_connections > 3:
            anomalies.append(f"KILL: Stuck network connections: {status.close_wait_connections}")

        # AGGRESSIVE: Kill processes that appear completely stuck
        if status.runtime_minutes > 5 and status.progress_score == 0.0:
            anomalies.append(f"KILL: Zero progress detected (completely stuck)")

        # Memory anomaly - still monitor but less aggressive
        if status.memory_mb > config.max_memory_mb:
            anomalies.append(f"WARNING: High memory usage {status.memory_mb:.1f}MB (max: {config.max_memory_mb}MB)")

        # Very high CPU for extended period - might indicate infinite loop
        if status.runtime_minutes > 5 and status.cpu_percent > 90.0:
            anomalies.append(f"KILL: Excessive CPU usage {status.cpu_percent:.1f}% (possible infinite loop)")

        return anomalies

    def _get_process_status(self, proc: psutil.Process, config: ProcessConfig) -> ProcessStatus:
        """Get detailed status of a process"""
        try:
            # Basic process info
            create_time = datetime.fromtimestamp(proc.create_time())
            runtime_minutes = (datetime.now() - create_time).total_seconds() / 60

            # Resource usage
            cpu_percent = proc.cpu_percent()
            memory_mb = proc.memory_info().rss / (1024 * 1024)

            # Network connections
            connections = proc.connections() if hasattr(proc, 'connections') else []
            close_wait_count = sum(1 for conn in connections if conn.status == 'CLOSE_WAIT')

            # Progress assessment
            progress_score = self._get_progress_score(config.progress_indicators, create_time)

            status = ProcessStatus(
                pid=proc.pid,
                name=config.name,
                cmd=' '.join(proc.cmdline()),
                start_time=create_time,
                runtime_minutes=runtime_minutes,
                cpu_percent=cpu_percent,
                memory_mb=memory_mb,
                network_connections=len(connections),
                close_wait_connections=close_wait_count,
                progress_score=progress_score,
                anomaly_reasons=[]
            )

            # Load restart history from state
            state_key = f"{proc.pid}_{config.name}"
            if state_key in self.process_state:
                status.restart_count = self.process_state[state_key].get('restart_count', 0)
                last_restart_str = self.process_state[state_key].get('last_restart')
                if last_restart_str:
                    status.last_restart = datetime.fromisoformat(last_restart_str)

            return status

        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            raise e

    def _kill_process(self, pid: int, name: str) -> bool:
        """Safely terminate a process"""
        try:
            proc = psutil.Process(pid)

            # Try graceful termination first
            proc.terminate()

            # Wait up to 10 seconds for graceful shutdown
            try:
                proc.wait(timeout=10)
                self.logger.info(f"✅ Gracefully terminated {name} (PID: {pid})")
                return True
            except psutil.TimeoutExpired:
                # Force kill if graceful shutdown failed
                proc.kill()
                proc.wait(timeout=5)
                self.logger.warning(f"⚠️ Force-killed {name} (PID: {pid})")
                return True

        except psutil.NoSuchProcess:
            self.logger.info(f"Process {name} (PID: {pid}) already terminated")
            return True
        except Exception as e:
            self.logger.error(f"❌ Failed to kill {name} (PID: {pid}): {e}")
            return False

    def _restart_process(self, config: ProcessConfig, status: ProcessStatus) -> bool:
        """Restart a terminated process"""
        if not config.restart_command:
            self.logger.info(f"No restart command configured for {config.name}")
            return False

        if status.restart_count >= config.max_restarts:
            self.logger.warning(f"Max restarts ({config.max_restarts}) reached for {config.name}")
            return False

        # Wait for restart delay
        if status.restart_count > 0:
            self.logger.info(f"Waiting {config.restart_delay_minutes}m before restart...")
            time.sleep(config.restart_delay_minutes * 60)

        try:
            # Start the process
            subprocess.Popen(
                config.restart_command.split(),
                cwd=Path(__file__).parent.parent,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            # Update state
            state_key = f"{status.pid}_{config.name}"
            self.process_state[state_key] = {
                'restart_count': status.restart_count + 1,
                'last_restart': datetime.now().isoformat()
            }
            self._save_state()

            self.logger.info(f"✅ Restarted {config.name} (attempt {status.restart_count + 1})")
            return True

        except Exception as e:
            self.logger.error(f"❌ Failed to restart {config.name}: {e}")
            return False

    def check_processes(self) -> List[ProcessStatus]:
        """Check all monitored processes for anomalies"""
        anomalous_processes = []

        for config_name, config in self.process_configs.items():
            try:
                # Find matching processes
                matching_processes = []
                for proc in psutil.process_iter(['pid', 'cmdline']):
                    try:
                        cmdline = ' '.join(proc.info['cmdline'] or [])
                        import re
                        if re.search(config.command_pattern, cmdline):
                            matching_processes.append(proc)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

                # Check each matching process
                for proc in matching_processes:
                    try:
                        status = self._get_process_status(proc, config)
                        status.anomaly_reasons = self._detect_anomalies(status, config)

                        if status.anomaly_reasons:
                            anomalous_processes.append(status)
                            self.logger.warning(
                                f"🚨 Anomalous process detected: {config.name} (PID: {status.pid})\n"
                                f"   Runtime: {status.runtime_minutes:.1f}m, CPU: {status.cpu_percent:.1f}%, "
                                f"Memory: {status.memory_mb:.1f}MB\n"
                                f"   Progress: {status.progress_score:.2f}, CLOSE-WAIT: {status.close_wait_connections}\n"
                                f"   Anomalies: {', '.join(status.anomaly_reasons)}"
                            )
                        else:
                            self.logger.debug(f"✅ {config.name} (PID: {status.pid}) running normally")

                    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                        self.logger.debug(f"Process access error for {config.name}: {e}")
                        continue

            except Exception as e:
                self.logger.error(f"Error checking {config_name}: {e}")
                continue

        return anomalous_processes

    def handle_anomalies(self, anomalous_processes: List[ProcessStatus]) -> Dict[str, bool]:
        """Handle detected process anomalies"""
        results = {}

        for status in anomalous_processes:
            config = self.process_configs.get(status.name.lower().replace(" ", "_"))
            if not config:
                self.logger.warning(f"No config found for {status.name}")
                results[status.name] = False
                continue

            # AGGRESSIVE: Kill on any "KILL:" reason - Atlas is about patient accumulation
            should_kill = any("KILL:" in reason for reason in status.anomaly_reasons)

            if should_kill:
                self.logger.info(f"🔪 Terminating anomalous process: {status.name} (PID: {status.pid})")

                if self._kill_process(status.pid, status.name):
                    # Attempt restart if configured
                    if config.restart_command:
                        restart_success = self._restart_process(config, status)
                        results[status.name] = restart_success
                    else:
                        results[status.name] = True  # Successfully killed
                else:
                    results[status.name] = False  # Kill failed
            else:
                self.logger.info(f"⚠️ Monitoring {status.name} (PID: {status.pid}) - not severe enough to kill yet")
                results[status.name] = None  # Monitoring only

        return results

    def run_check_cycle(self) -> Dict[str, Any]:
        """Run one complete monitoring cycle"""
        start_time = datetime.now()
        self.logger.info("🔍 Starting process watchdog check cycle")

        try:
            # Check for anomalies
            anomalous_processes = self.check_processes()

            # Handle anomalies
            results = {}
            if anomalous_processes:
                results = self.handle_anomalies(anomalous_processes)

            # Summary
            cycle_time = (datetime.now() - start_time).total_seconds()
            summary = {
                "timestamp": start_time.isoformat(),
                "cycle_duration_seconds": cycle_time,
                "anomalous_processes": len(anomalous_processes),
                "actions_taken": len([r for r in results.values() if r is not None]),
                "results": results
            }

            if anomalous_processes:
                self.logger.info(
                    f"📊 Cycle complete: {len(anomalous_processes)} anomalies found, "
                    f"{len([r for r in results.values() if r])} processes restarted"
                )
            else:
                self.logger.info("✅ All monitored processes running normally")

            return summary

        except Exception as e:
            self.logger.error(f"❌ Error in check cycle: {e}")
            return {"error": str(e), "timestamp": start_time.isoformat()}

def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Atlas Process Watchdog")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")
    parser.add_argument("--interval", type=int, default=5, help="Check interval in minutes")
    parser.add_argument("--check-once", action="store_true", help="Run single check and exit")

    args = parser.parse_args()

    watchdog = AtlasProcessWatchdog()

    if args.check_once:
        # Run single check
        result = watchdog.run_check_cycle()
        print(json.dumps(result, indent=2))
        return

    # Run as daemon or single cycle
    interval_seconds = args.interval * 60

    if args.daemon:
        watchdog.logger.info(f"🐕 Starting Atlas Process Watchdog daemon (check every {args.interval}m)")

        while True:
            try:
                watchdog.run_check_cycle()
                time.sleep(interval_seconds)
            except KeyboardInterrupt:
                watchdog.logger.info("👋 Shutting down watchdog daemon")
                break
            except Exception as e:
                watchdog.logger.error(f"Daemon error: {e}")
                time.sleep(60)  # Wait 1 minute before retry
    else:
        # Run single cycle
        watchdog.run_check_cycle()

if __name__ == "__main__":
    main()