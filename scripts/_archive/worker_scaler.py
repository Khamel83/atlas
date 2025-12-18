#!/usr/bin/env python3
"""
Dynamic worker scaling based on queue depth and system resources
"""

import json
import time
import psutil
import subprocess
import logging
import signal
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Add helpers to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from helpers.resource_manager import ResourceManager

class WorkerScaler:
    """Manages dynamic scaling of worker processes"""

    def __init__(self, config_path: str = "data/worker_config.json"):
        self.config_path = config_path
        self.logger = self._setup_logging()
        self.config = self._load_config()
        self.resource_manager = ResourceManager()
        self.worker_processes: List[subprocess.Popen] = []
        self.last_scale_time = datetime.now()

    def _setup_logging(self) -> logging.Logger:
        """Setup logging for worker scaler"""
        logger = logging.getLogger('worker_scaler')
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.FileHandler('data/worker_scaler.log')
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def _load_config(self) -> Dict:
        """Load worker configuration"""
        default_config = {
            "worker_command": ["python3", "-c", "import time; time.sleep(60)"],  # Dummy worker
            "min_workers": 1,
            "max_workers": 5,
            "scale_up_threshold": 100,  # queue depth
            "scale_down_threshold": 10,  # queue depth
            "scale_up_delay": 30,      # seconds
            "scale_down_delay": 300,   # seconds
            "health_check_interval": 30,  # seconds
            "worker_timeout": 3600,    # seconds
            "resource_limits": {
                "max_memory_percent": 80,
                "max_cpu_percent": 90
            }
        }

        try:
            if Path(self.config_path).exists():
                with open(self.config_path) as f:
                    config = json.load(f)
                # Merge with defaults
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
            else:
                self._save_config(default_config)
                return default_config
        except Exception as e:
            self.logger.error(f"Error loading config: {e}")
            return default_config

    def _save_config(self, config: Dict):
        """Save configuration to file"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving config: {e}")

    def get_queue_depth(self) -> int:
        """Get current queue depth (mock implementation)"""
        # In a real implementation, this would query your actual queue system
        # For now, return a simulated queue depth based on system load
        try:
            load_avg = psutil.getloadavg()[0]
            # Simulate queue depth based on load
            queue_depth = max(0, int((load_avg - 1.0) * 50))
            return queue_depth
        except:
            return 0

    def start_worker(self) -> Optional[subprocess.Popen]:
        """Start a new worker process"""
        try:
            import os
            cmd = self.config["worker_command"]
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None
            )

            self.worker_processes.append(process)
            self.logger.info(f"Started worker process {process.pid}")
            return process

        except Exception as e:
            self.logger.error(f"Failed to start worker: {e}")
            return None

    def stop_worker(self, process: subprocess.Popen) -> bool:
        """Stop a worker process gracefully"""
        try:
            if process.poll() is None:  # Process is still running
                # Try graceful shutdown first
                process.terminate()

                # Wait up to 10 seconds for graceful shutdown
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    # Force kill if graceful shutdown fails
                    process.kill()
                    process.wait()

            if process in self.worker_processes:
                self.worker_processes.remove(process)

            self.logger.info(f"Stopped worker process {process.pid}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to stop worker {process.pid}: {e}")
            return False

    def cleanup_dead_workers(self):
        """Remove dead worker processes from tracking"""
        dead_workers = []
        for process in self.worker_processes[:]:  # Copy list to avoid modification during iteration
            if process.poll() is not None:  # Process has terminated
                dead_workers.append(process)
                self.worker_processes.remove(process)
                self.logger.info(f"Cleaned up dead worker {process.pid}")

        return len(dead_workers)

    def get_worker_count(self) -> int:
        """Get current number of active workers"""
        self.cleanup_dead_workers()
        return len(self.worker_processes)

    def check_resource_limits(self) -> bool:
        """Check if system resources are within limits for scaling up"""
        try:
            memory_percent = psutil.virtual_memory().percent
            cpu_percent = psutil.cpu_percent(interval=1)

            memory_limit = self.config["resource_limits"]["max_memory_percent"]
            cpu_limit = self.config["resource_limits"]["max_cpu_percent"]

            if memory_percent > memory_limit:
                self.logger.warning(f"Memory usage {memory_percent:.1f}% exceeds limit {memory_limit}%")
                return False

            if cpu_percent > cpu_limit:
                self.logger.warning(f"CPU usage {cpu_percent:.1f}% exceeds limit {cpu_limit}%")
                return False

            return True

        except Exception as e:
            self.logger.error(f"Error checking resource limits: {e}")
            return False

    def should_scale_up(self, queue_depth: int, current_workers: int) -> bool:
        """Determine if we should scale up workers"""
        if current_workers >= self.config["max_workers"]:
            return False

        if queue_depth < self.config["scale_up_threshold"]:
            return False

        # Check if enough time has passed since last scaling
        scale_delay = self.config["scale_up_delay"]
        time_since_last = (datetime.now() - self.last_scale_time).total_seconds()
        if time_since_last < scale_delay:
            return False

        # Check resource limits
        if not self.check_resource_limits():
            return False

        return True

    def should_scale_down(self, queue_depth: int, current_workers: int) -> bool:
        """Determine if we should scale down workers"""
        if current_workers <= self.config["min_workers"]:
            return False

        if queue_depth > self.config["scale_down_threshold"]:
            return False

        # Check if enough time has passed since last scaling
        scale_delay = self.config["scale_down_delay"]
        time_since_last = (datetime.now() - self.last_scale_time).total_seconds()
        if time_since_last < scale_delay:
            return False

        return True

    def scale_workers(self, queue_depth: int) -> Dict:
        """Scale workers based on queue depth"""
        current_workers = self.get_worker_count()

        result = {
            "timestamp": datetime.now().isoformat(),
            "queue_depth": queue_depth,
            "workers_before": current_workers,
            "workers_after": current_workers,
            "action": "none",
            "success": True
        }

        if self.should_scale_up(queue_depth, current_workers):
            # Scale up
            new_worker = self.start_worker()
            if new_worker:
                result["action"] = "scale_up"
                result["workers_after"] = current_workers + 1
                self.last_scale_time = datetime.now()
                self.logger.info(f"Scaled up: {current_workers} -> {current_workers + 1} workers (queue: {queue_depth})")
            else:
                result["success"] = False
                result["action"] = "scale_up_failed"

        elif self.should_scale_down(queue_depth, current_workers):
            # Scale down
            if self.worker_processes:
                worker_to_stop = self.worker_processes[-1]  # Stop most recent worker
                if self.stop_worker(worker_to_stop):
                    result["action"] = "scale_down"
                    result["workers_after"] = current_workers - 1
                    self.last_scale_time = datetime.now()
                    self.logger.info(f"Scaled down: {current_workers} -> {current_workers - 1} workers (queue: {queue_depth})")
                else:
                    result["success"] = False
                    result["action"] = "scale_down_failed"

        return result

    def health_check(self) -> Dict:
        """Perform health check on all workers"""
        current_workers = self.get_worker_count()
        dead_workers_cleaned = self.cleanup_dead_workers()

        # Check for stuck workers (running too long)
        stuck_workers = []
        for process in self.worker_processes[:]:
            try:
                # Check if process has been running too long
                p = psutil.Process(process.pid)
                runtime = time.time() - p.create_time()

                if runtime > self.config["worker_timeout"]:
                    stuck_workers.append(process)
                    self.logger.warning(f"Worker {process.pid} stuck (runtime: {runtime:.0f}s)")

            except psutil.NoSuchProcess:
                # Process already dead, will be cleaned up
                pass
            except Exception as e:
                self.logger.error(f"Error checking worker {process.pid}: {e}")

        # Kill stuck workers
        for process in stuck_workers:
            self.stop_worker(process)

        final_workers = self.get_worker_count()

        return {
            "timestamp": datetime.now().isoformat(),
            "workers_active": final_workers,
            "dead_workers_cleaned": dead_workers_cleaned,
            "stuck_workers_killed": len(stuck_workers),
            "worker_pids": [p.pid for p in self.worker_processes]
        }

    def run_scaling_loop(self, duration: int = 0):
        """Run the main scaling loop"""
        self.logger.info(f"Starting worker scaler (duration: {duration}s)")

        start_time = time.time()
        check_interval = self.config["health_check_interval"]

        try:
            while True:
                # Check if duration limit reached
                if duration > 0 and (time.time() - start_time) > duration:
                    break

                # Get current metrics
                queue_depth = self.get_queue_depth()
                current_workers = self.get_worker_count()

                # Collect system metrics
                metrics = self.resource_manager.collect_metrics(
                    queue_depth=queue_depth,
                    worker_count=current_workers
                )

                # Perform scaling decision
                scale_result = self.scale_workers(queue_depth)

                # Health check
                health_result = self.health_check()

                # Log status
                if scale_result["action"] != "none":
                    self.logger.info(f"Scaling action: {scale_result}")

                # Sleep until next check
                time.sleep(check_interval)

        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal, shutting down...")
        except Exception as e:
            self.logger.error(f"Error in scaling loop: {e}")
        finally:
            self.shutdown()

    def shutdown(self):
        """Shutdown all workers and cleanup"""
        self.logger.info("Shutting down all workers...")

        for process in self.worker_processes[:]:
            self.stop_worker(process)

        self.logger.info("Worker scaler shutdown complete")

    def get_status(self) -> Dict:
        """Get current scaler status"""
        queue_depth = self.get_queue_depth()
        current_workers = self.get_worker_count()

        return {
            "timestamp": datetime.now().isoformat(),
            "queue_depth": queue_depth,
            "worker_count": current_workers,
            "worker_pids": [p.pid for p in self.worker_processes],
            "config": self.config,
            "resource_status": self.resource_manager.get_metrics_summary()
        }

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print("\nReceived shutdown signal, stopping...")
    sys.exit(0)

if __name__ == "__main__":
    import argparse
    import os

    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    parser = argparse.ArgumentParser(description="Dynamic Worker Scaler")
    parser.add_argument("--duration", type=int, default=0,
                       help="Run duration in seconds (0 for indefinite)")
    parser.add_argument("--config", default="data/worker_config.json",
                       help="Configuration file path")
    parser.add_argument("--status", action="store_true",
                       help="Show current status and exit")
    parser.add_argument("--test", action="store_true",
                       help="Run a test scaling cycle")

    args = parser.parse_args()

    scaler = WorkerScaler(args.config)

    if args.status:
        status = scaler.get_status()
        print(json.dumps(status, indent=2))
    elif args.test:
        print("Running test scaling cycle...")
        print("Initial status:")
        print(json.dumps(scaler.get_status(), indent=2))

        # Simulate scaling up
        print("\nSimulating high queue depth...")
        result = scaler.scale_workers(200)  # High queue depth
        print(f"Scale up result: {result}")

        time.sleep(5)

        # Simulate scaling down
        print("\nSimulating low queue depth...")
        result = scaler.scale_workers(5)   # Low queue depth
        print(f"Scale down result: {result}")

        print("\nFinal status:")
        print(json.dumps(scaler.get_status(), indent=2))

        scaler.shutdown()
    else:
        scaler.run_scaling_loop(args.duration)