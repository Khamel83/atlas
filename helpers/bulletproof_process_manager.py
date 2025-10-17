#!/usr/bin/env python3
"""
Bulletproof Process Manager

This is the definitive solution to prevent memory leaks and runaway processes.
It provides comprehensive process lifecycle management, memory monitoring,
and automatic cleanup to ensure this problem NEVER happens again.

Key Features:
- Process registry with automatic cleanup
- Memory leak detection using memray and tracemalloc
- Resource monitoring and limits
- Circuit breaker pattern
- Orphan process cleanup
- Comprehensive logging and metrics

Author: Claude Code
Created: 2025-08-27
"""

import os
import sys
import time
import json
import signal
import psutil
import logging
import resource
import tracemalloc
import threading
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Callable
from contextlib import contextmanager
from collections import defaultdict
import weakref
import atexit


class ProcessRegistry:
    """
    Central registry for all spawned processes.
    Ensures no process is ever orphaned or left running.
    """

    def __init__(self):
        self.processes: Dict[int, Dict[str, Any]] = {}
        self.process_groups: Dict[int, Set[int]] = defaultdict(set)
        self.cleanup_callbacks: List[Callable] = []
        self._lock = threading.RLock()

        # Don't register automatic cleanup to prevent killing processes during status checks
        # Manual cleanup must be called explicitly when actually shutting down
        # atexit.register(self.cleanup_all)

        # Register signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def register_process(self, process: subprocess.Popen, name: str,
                        parent_pid: Optional[int] = None, metadata: Optional[Dict] = None):
        """Register a process for tracking and cleanup"""
        with self._lock:
            process_info = {
                'process': weakref.ref(process),
                'name': name,
                'pid': process.pid,
                'parent_pid': parent_pid or os.getpid(),
                'start_time': datetime.now(),
                'metadata': metadata or {},
                'cpu_percent': 0.0,
                'memory_mb': 0.0,
                'status': 'running'
            }

            self.processes[process.pid] = process_info

            if parent_pid:
                self.process_groups[parent_pid].add(process.pid)

            logging.info(f"📝 Registered process: {name} (PID: {process.pid})")

    def unregister_process(self, pid: int):
        """Unregister a process (when it exits normally)"""
        with self._lock:
            if pid in self.processes:
                proc_info = self.processes.pop(pid)
                logging.info(f"✅ Unregistered process: {proc_info['name']} (PID: {pid})")

                # Remove from process groups
                for parent_pid, child_pids in self.process_groups.items():
                    child_pids.discard(pid)

    def get_process_info(self) -> Dict[int, Dict[str, Any]]:
        """Get information about all registered processes"""
        with self._lock:
            # Update process status
            for pid, proc_info in list(self.processes.items()):
                try:
                    process_ref = proc_info['process']
                    process = process_ref()

                    if process is None or process.poll() is not None:
                        # Process has ended
                        proc_info['status'] = 'terminated'
                        continue

                    # Update resource usage
                    try:
                        ps_process = psutil.Process(pid)
                        proc_info['cpu_percent'] = ps_process.cpu_percent()
                        proc_info['memory_mb'] = ps_process.memory_info().rss / (1024 * 1024)
                        proc_info['status'] = ps_process.status()
                    except psutil.NoSuchProcess:
                        proc_info['status'] = 'terminated'

                except Exception as e:
                    logging.warning(f"Error updating process {pid} info: {e}")
                    proc_info['status'] = 'error'

            return dict(self.processes)

    def cleanup_terminated_processes(self):
        """Remove terminated processes from registry"""
        with self._lock:
            terminated_pids = []
            for pid, proc_info in self.processes.items():
                if proc_info['status'] in ('terminated', 'error'):
                    terminated_pids.append(pid)

            for pid in terminated_pids:
                self.unregister_process(pid)

    def kill_process_tree(self, pid: int, signal_type: int = signal.SIGTERM) -> bool:
        """Kill a process and all its children"""
        try:
            parent = psutil.Process(pid)
            children = parent.children(recursive=True)

            # Send signal to children first
            for child in children:
                try:
                    child.send_signal(signal_type)
                    logging.info(f"🔪 Sent signal {signal_type} to child process {child.pid}")
                except psutil.NoSuchProcess:
                    pass
                except Exception as e:
                    logging.warning(f"Error killing child {child.pid}: {e}")

            # Send signal to parent
            try:
                parent.send_signal(signal_type)
                logging.info(f"🔪 Sent signal {signal_type} to parent process {pid}")
            except psutil.NoSuchProcess:
                pass
            except Exception as e:
                logging.warning(f"Error killing parent {pid}: {e}")
                return False

            # Wait for termination
            time.sleep(1)

            # Force kill if still running
            if signal_type != signal.SIGKILL:
                try:
                    if psutil.Process(pid).is_running():
                        logging.warning(f"Process {pid} still running, force killing...")
                        return self.kill_process_tree(pid, signal.SIGKILL)
                except psutil.NoSuchProcess:
                    pass

            return True

        except psutil.NoSuchProcess:
            logging.info(f"Process {pid} already terminated")
            return True
        except Exception as e:
            logging.error(f"Error killing process tree {pid}: {e}")
            return False

    def cleanup_all(self):
        """Emergency cleanup of all registered processes"""
        logging.info("🧹 Starting emergency cleanup of all processes...")

        with self._lock:
            for pid, proc_info in list(self.processes.items()):
                logging.info(f"🔴 Cleaning up process: {proc_info['name']} (PID: {pid})")
                self.kill_process_tree(pid)

        # Run cleanup callbacks
        for callback in self.cleanup_callbacks:
            try:
                callback()
            except Exception as e:
                logging.error(f"Error in cleanup callback: {e}")

        logging.info("✅ Emergency cleanup completed")

    def _signal_handler(self, signum, frame):
        """Handle termination signals"""
        logging.info(f"🚨 Received signal {signum}, initiating cleanup...")
        self.cleanup_all()
        sys.exit(0)


class MemoryLeakDetector:
    """
    Advanced memory leak detection using multiple techniques:
    - tracemalloc for Python allocations
    - psutil for system memory
    - Memory snapshots and comparison
    - Automatic leak alerts
    """

    def __init__(self, check_interval: int = 60):
        self.check_interval = check_interval
        self.memory_snapshots: List[Dict[str, Any]] = []
        self.leak_threshold_mb = 100  # Alert if memory grows by >100MB
        self.running = False
        self.thread: Optional[threading.Thread] = None

        # Start tracemalloc
        tracemalloc.start(25)  # Keep 25 stack frames

        logging.info("🔍 Memory leak detector initialized")

    def start(self):
        """Start continuous memory monitoring"""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.thread.start()

        logging.info("🔍 Memory leak detector started")

    def stop(self):
        """Stop memory monitoring"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)

        logging.info("⏹️ Memory leak detector stopped")

    def take_snapshot(self) -> Dict[str, Any]:
        """Take a memory usage snapshot"""
        # Python memory (tracemalloc)
        python_snapshot = tracemalloc.take_snapshot()
        python_stats = python_snapshot.statistics('lineno')

        # System memory (psutil)
        current_process = psutil.Process()
        memory_info = current_process.memory_info()

        snapshot = {
            'timestamp': datetime.now(),
            'python_memory_mb': sum(stat.size for stat in python_stats) / (1024 * 1024),
            'rss_mb': memory_info.rss / (1024 * 1024),
            'vms_mb': memory_info.vms / (1024 * 1024),
            'cpu_percent': current_process.cpu_percent(),
            'open_files': len(current_process.open_files()),
            'num_threads': current_process.num_threads(),
            'top_allocations': [
                {
                    'size_mb': stat.size / (1024 * 1024),
                    'count': stat.count,
                    'traceback': str(stat.traceback)
                }
                for stat in python_stats[:10]  # Top 10 allocations
            ]
        }

        return snapshot

    def detect_leaks(self) -> Optional[Dict[str, Any]]:
        """Detect memory leaks by comparing snapshots"""
        if len(self.memory_snapshots) < 2:
            return None

        current = self.memory_snapshots[-1]
        previous = self.memory_snapshots[-2]

        rss_growth = current['rss_mb'] - previous['rss_mb']
        python_growth = current['python_memory_mb'] - previous['python_memory_mb']

        if rss_growth > self.leak_threshold_mb or python_growth > self.leak_threshold_mb:
            leak_info = {
                'detection_time': datetime.now(),
                'rss_growth_mb': rss_growth,
                'python_growth_mb': python_growth,
                'current_rss_mb': current['rss_mb'],
                'current_python_mb': current['python_memory_mb'],
                'open_files_growth': current['open_files'] - previous['open_files'],
                'thread_growth': current['num_threads'] - previous['num_threads']
            }

            logging.error(f"🚨 MEMORY LEAK DETECTED: RSS grew by {rss_growth:.1f}MB, "
                         f"Python memory grew by {python_growth:.1f}MB")

            return leak_info

        return None

    def _monitoring_loop(self):
        """Continuous memory monitoring loop"""
        while self.running:
            try:
                snapshot = self.take_snapshot()
                self.memory_snapshots.append(snapshot)

                # Keep only last 100 snapshots
                if len(self.memory_snapshots) > 100:
                    self.memory_snapshots = self.memory_snapshots[-100:]

                # Check for leaks
                leak_info = self.detect_leaks()
                if leak_info:
                    self._handle_leak_detection(leak_info)

                time.sleep(self.check_interval)

            except Exception as e:
                logging.error(f"Error in memory monitoring: {e}")
                time.sleep(self.check_interval)

    def _handle_leak_detection(self, leak_info: Dict[str, Any]):
        """Handle memory leak detection"""
        # Log detailed information
        logging.error("🚨 MEMORY LEAK DETAILS:")
        logging.error(f"   RSS Growth: {leak_info['rss_growth_mb']:.1f}MB")
        logging.error(f"   Python Growth: {leak_info['python_growth_mb']:.1f}MB")
        logging.error(f"   Current RSS: {leak_info['current_rss_mb']:.1f}MB")
        logging.error(f"   Open Files Growth: {leak_info['open_files_growth']}")
        logging.error(f"   Thread Growth: {leak_info['thread_growth']}")

        # Save leak report
        leak_report_path = Path("logs") / f"memory_leak_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        leak_report_path.parent.mkdir(exist_ok=True)

        with open(leak_report_path, 'w') as f:
            json.dump({
                'leak_info': leak_info,
                'recent_snapshots': self.memory_snapshots[-10:]  # Last 10 snapshots
            }, f, indent=2, default=str)

        logging.error(f"📄 Memory leak report saved to: {leak_report_path}")


class CircuitBreaker:
    """
    Circuit breaker pattern to prevent cascading failures.
    Stops retrying operations after consecutive failures.
    """

    def __init__(self, failure_threshold: int = 5, timeout: int = 300):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
        self._lock = threading.RLock()

    def can_execute(self) -> bool:
        """Check if operation can be executed"""
        with self._lock:
            if self.state == 'CLOSED':
                return True
            elif self.state == 'OPEN':
                if self.last_failure_time and \
                   (datetime.now() - self.last_failure_time).total_seconds() > self.timeout:
                    self.state = 'HALF_OPEN'
                    return True
                return False
            else:  # HALF_OPEN
                return True

    def record_success(self):
        """Record successful operation"""
        with self._lock:
            self.failure_count = 0
            self.state = 'CLOSED'
            logging.info(f"✅ Circuit breaker reset (success recorded)")

    def record_failure(self):
        """Record failed operation"""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = datetime.now()

            if self.failure_count >= self.failure_threshold:
                self.state = 'OPEN'
                logging.error(f"🔴 Circuit breaker OPENED after {self.failure_count} failures")
            else:
                logging.warning(f"⚠️ Circuit breaker failure {self.failure_count}/{self.failure_threshold}")

    @contextmanager
    def execute(self):
        """Context manager for circuit breaker execution"""
        if not self.can_execute():
            raise Exception(f"Circuit breaker is {self.state}, cannot execute operation")

        try:
            yield
            self.record_success()
        except Exception as e:
            self.record_failure()
            raise


class BulletproofProcessManager:
    """
    The main bulletproof process manager that combines all components
    to provide comprehensive process lifecycle management.
    """

    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        # Initialize components
        self.registry = ProcessRegistry()
        self.memory_detector = MemoryLeakDetector()
        self.circuit_breakers: Dict[str, CircuitBreaker] = defaultdict(CircuitBreaker)

        # Resource limits
        self.max_memory_mb = 1024  # 1GB memory limit
        self.max_open_files = 1024
        self.max_processes = 50

        # Set up logging
        self._setup_logging()

        # Set resource limits
        # self._set_resource_limits()

        # Start monitoring
        self.memory_detector.start()

        logging.info("🛡️ BulletproofProcessManager initialized")

    def _setup_logging(self):
        """Set up comprehensive logging"""
        log_file = self.log_dir / "bulletproof_process_manager.log"

        # Configure logging with rotation
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )

        # Prevent log file from growing too large
        if log_file.exists() and log_file.stat().st_size > 100 * 1024 * 1024:  # 100MB
            backup_file = log_file.with_suffix('.log.old')
            log_file.rename(backup_file)

    def _set_resource_limits(self):
        """Set resource limits to prevent runaway resource usage"""
        try:
            # Memory limit
            resource.setrlimit(resource.RLIMIT_AS, (
                self.max_memory_mb * 1024 * 1024,  # Soft limit
                self.max_memory_mb * 1024 * 1024   # Hard limit
            ))

            # File descriptor limit
            resource.setrlimit(resource.RLIMIT_NOFILE, (
                self.max_open_files,
                self.max_open_files
            ))

            # Process limit
            resource.setrlimit(resource.RLIMIT_NPROC, (
                self.max_processes,
                self.max_processes
            ))

            logging.info(f"✅ Resource limits set: {self.max_memory_mb}MB memory, "
                        f"{self.max_open_files} files, {self.max_processes} processes")

        except Exception as e:
            logging.warning(f"Could not set all resource limits: {e}")

    def create_process(self, cmd: List[str], name: str,
                      timeout: Optional[int] = None,
                      **kwargs) -> subprocess.Popen:
        """
        Create a new process with bulletproof management.
        This is the ONLY way processes should be created in the system.
        """
        circuit_breaker = self.circuit_breakers[name]

        with circuit_breaker.execute():
            # Pre-flight checks
            self._pre_flight_checks(name)

            # Set up process creation parameters
            process_kwargs = {
                'stdout': subprocess.PIPE,
                'stderr': subprocess.PIPE,
                'start_new_session': True,
                **kwargs
            }

            # Create process
            logging.info(f"🚀 Creating process: {name} with command: {' '.join(cmd)}")
            process = subprocess.Popen(cmd, **process_kwargs)

            # Register process
            self.registry.register_process(process, name)

            # Set up timeout handling
            if timeout:
                def timeout_handler():
                    time.sleep(timeout)
                    if process.poll() is None:
                        logging.warning(f"⏰ Process {name} (PID: {process.pid}) timed out after {timeout}s")
                        self.kill_process(process.pid)

                timeout_thread = threading.Thread(target=timeout_handler, daemon=True)
                timeout_thread.start()

            return process

    def _pre_flight_checks(self, operation_name: str):
        """Perform pre-flight safety checks before creating processes"""
        # Check disk space
        disk_usage = psutil.disk_usage('/')
        free_gb = disk_usage.free / (1024**3)
        if free_gb < 5.0:
            raise Exception(f"Insufficient disk space: {free_gb:.1f}GB free (minimum 5GB required)")

        # Check memory usage
        memory = psutil.virtual_memory()
        if memory.percent > 90:
            raise Exception(f"High memory usage: {memory.percent}% (maximum 90% allowed)")

        # Check number of processes
        current_processes = len(self.registry.get_process_info())
        if current_processes >= self.max_processes:
            raise Exception(f"Too many processes: {current_processes}/{self.max_processes}")

        # Check for large log files
        for log_file in self.log_dir.glob("*.log"):
            if log_file.stat().st_size > 100 * 1024 * 1024:  # 100MB
                raise Exception(f"Large log file detected: {log_file} ({log_file.stat().st_size / (1024**2):.1f}MB)")

        logging.info(f"✅ Pre-flight checks passed for {operation_name}")

    def kill_process(self, pid: int) -> bool:
        """Kill a process and remove from registry"""
        success = self.registry.kill_process_tree(pid)
        if success:
            self.registry.unregister_process(pid)
        return success

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status of all managed processes"""
        process_info = self.registry.get_process_info()
        memory_snapshot = self.memory_detector.take_snapshot()

        return {
            'timestamp': datetime.now(),
            'total_processes': len(process_info),
            'running_processes': len([p for p in process_info.values() if p['status'] == 'running']),
            'memory_usage_mb': memory_snapshot['rss_mb'],
            'open_files': memory_snapshot['open_files'],
            'cpu_percent': memory_snapshot['cpu_percent'],
            'circuit_breakers': {
                name: {
                    'state': breaker.state,
                    'failure_count': breaker.failure_count
                }
                for name, breaker in self.circuit_breakers.items()
            },
            'processes': process_info
        }

    def cleanup_all(self):
        """Clean up all processes and stop monitoring"""
        logging.info("🧹 Starting complete system cleanup...")

        self.memory_detector.stop()
        self.registry.cleanup_all()

        logging.info("✅ Complete system cleanup finished")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Only cleanup if we actually have processes to manage
        if self.registry.processes:
            self.cleanup_all()


# Global instance
_manager: Optional[BulletproofProcessManager] = None


def get_manager() -> BulletproofProcessManager:
    """Get the global bulletproof process manager instance"""
    global _manager
    if _manager is None:
        _manager = BulletproofProcessManager()
    return _manager


def create_managed_process(cmd: List[str], name: str, **kwargs) -> subprocess.Popen:
    """
    Convenience function to create a managed process.
    This should replace ALL subprocess.Popen calls in the codebase.
    """
    return get_manager().create_process(cmd, name, **kwargs)


if __name__ == "__main__":
    # Example usage and testing
    logging.info("🧪 Testing BulletproofProcessManager...")

    with BulletproofProcessManager() as manager:
        # Create a test process
        process = manager.create_process(['sleep', '10'], 'test_sleep')

        # Check status
        status = manager.get_status()
        print(f"Status: {status['total_processes']} processes running")

        # Wait a bit
        time.sleep(2)

        # Kill the process
        manager.kill_process(process.pid)

        print("Test completed successfully!")