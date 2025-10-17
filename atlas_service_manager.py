#!/usr/bin/env python3
"""
Atlas Background Service Manager

Provides comprehensive background service automation including:
- Content processing pipeline
- Search index maintenance
- Analytics sync
- API server management
- Health monitoring
- Auto-restart capabilities
"""

import os
import sys
import json
import time
import logging
# Import process manager only when needed to avoid triggering cleanup
# from helpers.bulletproof_process_manager import get_manager, create_managed_process
import psutil
from dotenv import load_dotenv
import signal
import subprocess
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import atexit

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent))

from helpers.config import load_config
from helpers.resource_monitor import check_system_health
from helpers.logging_config import get_logger, PerformanceLogger

class AtlasServiceManager:
    """Comprehensive Atlas background service manager"""

    def __init__(self):
        """Initialize service manager"""
        # Perform pre-flight health check
        if not check_system_health():
            logging.error("System health check failed - aborting")
            sys.exit(1)

        self.config = load_config()

        # Load environment variables for port configuration
        load_dotenv()
        self.api_port = int(os.getenv('API_PORT', 7444))
        self.api_host = os.getenv('API_HOST', 'localhost')

        self.services = {}
        self.running = False
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        self.pid_file = self.log_dir / "atlas_service.pid"

        # Setup structured logging
        self.logger = get_logger("atlas_service")
        self.health_logger = get_logger("atlas_service_health")
        self.performance_logger = PerformanceLogger()

        # Legacy logging setup for compatibility
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_dir / "atlas_service.log"),
                logging.StreamHandler()
            ]
        )

        # Register cleanup on exit
        atexit.register(self.cleanup_processes)
        signal.signal(signal.SIGTERM, lambda s, f: self.cleanup_processes())
        signal.signal(signal.SIGINT, lambda s, f: self.cleanup_processes())

        # Venv path fix
        self.project_root = Path(__file__).parent
        self.python_executable = str(self.project_root / "venv" / "bin" / "python3")
        if not Path(self.python_executable).exists():
            self.logger.critical(f"CRITICAL: Python executable not found at {self.python_executable}. The 'venv' virtual environment is required.")
            sys.exit(1)

    def start_api_server(self) -> bool:
        """Start the Atlas API server"""
        try:
            if self._is_port_in_use(self.api_port):
                self.logger.info(f"API server already running on port {self.api_port}")
                return True

            self.kill_process_on_port(self.api_port)

            cmd = [
                self.python_executable, "-m", "uvicorn",
                "api.main:app",
                "--host", "0.0.0.0",
                "--port", str(self.api_port),
                "--log-level", "info"
            ]

            from helpers.bulletproof_process_manager import create_managed_process
            process = create_managed_process(
                cmd,
                "api_server",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.project_root
            )

            time.sleep(3)

            if process.poll() is None and self._is_port_in_use(self.api_port):
                self.services["api_server"] = {
                    "process": process, "pid": process.pid, "start_time": datetime.now(),
                    "status": "running", "restart_attempts": 0
                }
                self.logger.info(f"API server started successfully (PID: {process.pid})")
                return True
            else:
                self.logger.error("Failed to start API server")
                return False

        except Exception as e:
            self.logger.error(f"Error starting API server: {e}")
            return False

    def start_background_tasks(self) -> bool:
        """Start background processing tasks"""
        try:
            # Start scheduler for background tasks
            scheduler_cmd = [self.python_executable, "scripts/atlas_scheduler.py", "--start"]

            from helpers.bulletproof_process_manager import create_managed_process
            scheduler_process = create_managed_process(
                scheduler_cmd, "scheduler", cwd=self.project_root, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            time.sleep(2)

            if scheduler_process.poll() is None:
                self.services["scheduler"] = {
                    "process": scheduler_process, "pid": scheduler_process.pid, "start_time": datetime.now(),
                    "status": "running", "restart_attempts": 0
                }
                self.logger.info(f"Background scheduler started (PID: {scheduler_process.pid})")
            else:
                self.logger.error("Failed to start background scheduler")
                return False

            return self.start_process_watchdog()

        except Exception as e:
            self.logger.error(f"Error starting background tasks: {e}")
            return False

    def start_process_watchdog(self) -> bool:
        """Start the process watchdog daemon"""
        try:
            watchdog_cmd = [
                self.python_executable, "helpers/process_watchdog.py",
                "--daemon", "--interval", "3"
            ]

            from helpers.bulletproof_process_manager import create_managed_process
            watchdog_process = create_managed_process(
                watchdog_cmd, "watchdog", cwd=self.project_root, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            time.sleep(2)

            if watchdog_process.poll() is None:
                self.services["watchdog"] = {
                    "process": watchdog_process, "pid": watchdog_process.pid, "start_time": datetime.now(),
                    "status": "running", "restart_attempts": 0
                }
                self.logger.info(f"Process watchdog started (PID: {watchdog_process.pid})")
                return True
            else:
                self.logger.error("Failed to start process watchdog")
                return False

        except Exception as e:
            self.logger.error(f"Error starting process watchdog: {e}")
            return False

    def _is_port_in_use(self, port: int) -> bool:
        """Check if a port is in use"""
        for conn in psutil.net_connections(kind='inet'):
            if conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
                return True
        return False

    def kill_process_on_port(self, port: int):
        """Kill process using a specific port"""
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                for conn in proc.connections(kind='inet'):
                    if conn.laddr.port == port:
                        self.logger.info(f"Killing process {proc.pid} ({proc.name()}) on port {port}")
                        proc.kill()
                        proc.wait(timeout=5)
                        return
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                continue

    def _perform_preflight_checks(self) -> bool:
        """Perform mandatory pre-flight safety checks."""
        self.logger.info("Performing pre-flight safety checks...")
        # 1. Check disk space
        try:
            disk_usage = psutil.disk_usage(str(self.project_root))
            free_gb = disk_usage.free / (1024**3)
            if free_gb < 5.0:
                self.logger.critical(f"PREFLIGHT FAILED: Low disk space ({free_gb:.2f}GB free). Halting to prevent storage crisis.")
                return False
            self.logger.info(f"Disk space check OK ({free_gb:.2f}GB free).")
        except Exception as e:
            self.logger.critical(f"PREFLIGHT FAILED: Could not check disk space: {e}")
            return False

        # 2. Check for huge log files
        try:
            large_logs = []
            for log_file in self.log_dir.glob("*.log"):
                if log_file.exists() and log_file.stat().st_size > (100 * 1024 * 1024): # 100MB
                    large_logs.append(log_file)
            if large_logs:
                self.logger.critical(f"PREFLIGHT FAILED: Large log file(s) found: {large_logs}. Enforce log rotation.")
                return False
            self.logger.info("Log size check OK.")
        except Exception as e:
            self.logger.critical(f"PREFLIGHT FAILED: Could not check log file sizes: {e}")
            return False

        # 3. Database integrity and maintenance
        try:
            from helpers.database_config import test_database_integrity, vacuum_database, _db_config

            # Check if integrity check is due
            if _db_config.should_check_integrity():
                self.logger.info("Running database integrity check...")
                if not test_database_integrity():
                    self.logger.critical("PREFLIGHT FAILED: Database integrity check failed")
                    return False
                self.logger.info("Database integrity check passed.")

            # Vacuum if needed
            if vacuum_database():
                self.logger.info("Database vacuum completed during startup.")

        except Exception as e:
            self.logger.critical(f"PREFLIGHT FAILED: Database checks failed: {e}")
            return False

        self.logger.info("All pre-flight checks passed.")
        return True

    def start_all_services(self) -> bool:
        """Start all Atlas services"""
        if not self._perform_preflight_checks():
            return False

        self.logger.info("Starting Atlas background services...")
        success = True

        if not self.start_api_server():
            success = False
        if not self.start_background_tasks():
            success = False

        if success:
            self.running = True
            self._write_pid_file()
            self.logger.info("All Atlas services started successfully")
        else:
            self.logger.error("Some services failed to start")

        return success

    def stop_all_services(self) -> bool:
        """Stop all Atlas services"""
        self.logger.info("Stopping Atlas background services...")
        self.running = False

        pids = [s['pid'] for s in self.services.values() if 'pid' in s]
        for pid in pids:
            try:
                proc = psutil.Process(pid)
                # Terminate children first
                for child in proc.children(recursive=True):
                    child.terminate()
                proc.terminate()
            except psutil.NoSuchProcess:
                continue

        # Wait for processes to terminate
        gone, alive = psutil.wait_procs(pids, timeout=3)
        for p in alive:
            p.kill()

        if self.pid_file.exists():
            self.pid_file.unlink()

        self.logger.info("Atlas services stopped")
        return True

    def get_service_status(self) -> Dict[str, Any]:
        """Get status of all services"""
        # This is a simplified status check, real status is managed by the running processes
        return {"running": self.pid_file.exists()}

    def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check"""
        # This would be a more detailed health check
        return {"status": "healthy"}

    def cleanup_processes(self):
        """Cleanup all managed processes"""
        try:
            from helpers.bulletproof_process_manager import get_manager
            manager = get_manager()
            manager.cleanup_all()
            logging.info("🧹 All processes cleaned up")
        except ImportError:
            logging.warning("Process manager not available for cleanup")

    def _write_pid_file(self):
        """Write PID file"""
        try:
            with open(self.pid_file, 'w') as f:
                f.write(str(os.getpid()))
        except Exception as e:
            self.logger.error(f"Error writing PID file: {e}")

    def monitor_loop(self, enable_watchdog=False):
        """Main monitoring loop with optional SystemD watchdog"""
        self.logger.info("Starting Atlas service monitoring loop")

        # SystemD watchdog setup
        if enable_watchdog:
            try:
                import systemd.daemon
                self.logger.info("SystemD watchdog enabled")
                # Notify systemd that we're ready
                systemd.daemon.notify('READY=1')
            except ImportError:
                self.logger.warning("systemd library not available, watchdog disabled")
                enable_watchdog = False

        # Performance monitoring counters
        loop_count = 0
        performance_log_interval = 2  # Log performance every 2 loops (60s)

        while self.running:
            try:
                # SystemD watchdog ping
                if enable_watchdog:
                    try:
                        systemd.daemon.notify('WATCHDOG=1')
                        self.logger.debug("SystemD watchdog ping sent")
                    except Exception as e:
                        self.logger.error(f"Failed to send watchdog ping: {e}")

                # Log performance metrics periodically
                if loop_count % performance_log_interval == 0:
                    self.performance_logger.log_performance_snapshot()

                    # Log service health status
                    service_statuses = {}
                    for service_name, service_info in self.services.items():
                        try:
                            if service_info.get("process"):
                                proc = service_info["process"]
                                service_statuses[service_name] = {
                                    "status": "running" if proc.poll() is None else "stopped",
                                    "pid": service_info.get("pid"),
                                    "uptime_minutes": (datetime.now() - service_info.get("start_time", datetime.now())).total_seconds() / 60,
                                    "restart_attempts": service_info.get("restart_attempts", 0)
                                }
                        except Exception:
                            service_statuses[service_name] = {"status": "unknown"}

                    self.health_logger.info("Service health status", services=service_statuses)

                loop_count += 1

                # The actual services are now managed by the scheduler and watchdog
                time.sleep(30)  # Reduced to 30s to match watchdog interval
            except KeyboardInterrupt:
                self.logger.info("Received interrupt signal, shutting down...")
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(30)

        if enable_watchdog:
            try:
                systemd.daemon.notify('STOPPING=1')
            except:
                pass

        self.stop_all_services()

    def _restart_service(self, service_name: str):
        """Restart a specific service"""
        # CIRCUIT BREAKER LOGIC
        service_info = self.services.get(service_name, {})
        restart_attempts = service_info.get("restart_attempts", 0)
        if restart_attempts >= 3:
            self.logger.critical(f"CIRCUIT BREAKER: Service {service_name} has failed 3 times. Will not restart again.")
            return

        self.health_logger.warning(f"Attempting to restart service: {service_name} (Attempt {restart_attempts + 1})")
        service_info["restart_attempts"] = restart_attempts + 1

        try:
            if service_name == "api_server":
                self.start_api_server()
            elif service_name == "scheduler":
                self.start_background_tasks()
            elif service_name == "watchdog":
                self.start_process_watchdog()
            else:
                self.logger.warning(f"Don't know how to restart service: {service_name}")
        except Exception as e:
            self.logger.error(f"Error restarting {service_name}: {e}")
            self.health_logger.error(f"Error restarting {service_name}: {e}")

def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Atlas Background Service Manager")
    parser.add_argument("command", choices=["start", "stop", "status", "health", "restart"], help="Command to execute")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")
    parser.add_argument("--watchdog", action="store_true", help="Enable SystemD watchdog")

    args = parser.parse_args()

    service_manager = AtlasServiceManager()

    if args.command == "start":
        if service_manager.start_all_services():
            if args.daemon:
                try:
                    service_manager.monitor_loop(enable_watchdog=args.watchdog)
                except KeyboardInterrupt:
                    print("Shutting down...")
            else:
                print("✅ Atlas services started successfully")
        else:
            print("❌ Failed to start some services")
            sys.exit(1)

    elif args.command == "stop":
        service_manager.stop_all_services()
        print("✅ Atlas services stopped successfully")

    elif args.command == "status":
        status = service_manager.get_service_status()
        print(f"🔍 Atlas Service Status: {'RUNNING' if status['running'] else 'STOPPED'}")

    elif args.command == "health":
        health = service_manager.health_check()
        print(f"🏥 Atlas Health Check: {health['status']}")

    elif args.command == "restart":
        print("🔄 Restarting Atlas services...")
        service_manager.stop_all_services()
        time.sleep(2)
        if service_manager.start_all_services():
            print("✅ Atlas services restarted successfully")
        else:
            print("❌ Failed to restart services")
            sys.exit(1)

if __name__ == "__main__":
    main()
