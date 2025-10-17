#!/usr/bin/env python3
"""
Resource management and auto-scaling module
Implements intelligent resource allocation based on load patterns
"""

import psutil
import time
import json
import logging
import shutil
import gc
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime, timedelta

@dataclass
class ResourceMetrics:
    """Container for resource metrics"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    load_avg: Tuple[float, float, float]
    queue_depth: int = 0
    worker_count: int = 0

class ResourceManager:
    """Intelligent resource management with auto-scaling"""

    def __init__(self, config_path: str = "data/resource_config.json"):
        self.config_path = config_path
        self.metrics_history: List[ResourceMetrics] = []
        self.max_history = 1000
        self.logger = self._setup_logging()
        self.config = self._load_config()

    def _setup_logging(self) -> logging.Logger:
        """Setup logging for resource manager"""
        logger = logging.getLogger('resource_manager')
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.FileHandler('data/resource_manager.log')
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def _load_config(self) -> Dict:
        """Load resource management configuration"""
        default_config = {
            "worker_scaling": {
                "min_workers": 1,
                "max_workers": 5,
                "queue_depth_threshold": 100,
                "scale_up_delay": 30,  # seconds
                "scale_down_delay": 300  # seconds
            },
            "memory": {
                "pressure_threshold": 80.0,  # percent
                "critical_threshold": 95.0,
                "gc_interval": 60  # seconds
            },
            "disk": {
                "cleanup_threshold": 80.0,  # percent
                "critical_threshold": 95.0,
                "cleanup_paths": [
                    "data/temp/",
                    "data/logs/",
                    "archive/old-files/"
                ]
            },
            "cpu": {
                "throttle_threshold": 4.0,  # load average
                "throttle_duration": 300,  # seconds
                "check_interval": 60
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
                    elif isinstance(value, dict):
                        for subkey, subvalue in value.items():
                            if subkey not in config[key]:
                                config[key][subkey] = subvalue
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
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving config: {e}")

    def collect_metrics(self, queue_depth: int = 0, worker_count: int = 0) -> ResourceMetrics:
        """Collect current system resource metrics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            load_avg = os.getloadavg()

            metrics = ResourceMetrics(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                disk_percent=(disk.used / disk.total) * 100,
                load_avg=load_avg,
                queue_depth=queue_depth,
                worker_count=worker_count
            )

            # Add to history
            self.metrics_history.append(metrics)
            if len(self.metrics_history) > self.max_history:
                self.metrics_history.pop(0)

            return metrics

        except Exception as e:
            self.logger.error(f"Error collecting metrics: {e}")
            return ResourceMetrics(
                timestamp=datetime.now(),
                cpu_percent=0,
                memory_percent=0,
                disk_percent=0,
                load_avg=(0, 0, 0),
                queue_depth=queue_depth,
                worker_count=worker_count
            )

    def check_memory_pressure(self) -> Dict:
        """Check memory pressure and trigger GC if needed"""
        memory = psutil.virtual_memory()
        memory_percent = memory.percent

        result = {
            "memory_percent": memory_percent,
            "pressure_level": "normal",
            "action_taken": None
        }

        if memory_percent > self.config["memory"]["critical_threshold"]:
            result["pressure_level"] = "critical"
            result["action_taken"] = "emergency_gc"
            gc.collect()
            self.logger.warning(f"Emergency GC triggered at {memory_percent:.1f}% memory usage")

        elif memory_percent > self.config["memory"]["pressure_threshold"]:
            result["pressure_level"] = "high"
            result["action_taken"] = "gc"
            gc.collect()
            self.logger.info(f"GC triggered at {memory_percent:.1f}% memory usage")

        return result

    def calculate_worker_scaling(self, current_workers: int, queue_depth: int) -> int:
        """Calculate optimal number of workers based on queue depth"""
        config = self.config["worker_scaling"]
        min_workers = config["min_workers"]
        max_workers = config["max_workers"]
        threshold = config["queue_depth_threshold"]

        # Calculate recommended workers based on queue depth
        if queue_depth == 0:
            recommended = min_workers
        else:
            # Scale workers based on queue depth
            workers_needed = max(1, queue_depth // threshold)
            recommended = min(max_workers, max(min_workers, workers_needed))

        # Apply hysteresis to prevent rapid scaling
        if recommended > current_workers:
            # Scale up slowly
            recommended = min(recommended, current_workers + 1)
        elif recommended < current_workers:
            # Scale down more aggressively but not too fast
            recommended = max(recommended, current_workers - 1)

        return recommended

    def cleanup_disk_space(self, force: bool = False) -> Dict:
        """Cleanup disk space when threshold exceeded"""
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100

        result = {
            "disk_percent": disk_percent,
            "cleanup_triggered": False,
            "files_cleaned": 0,
            "bytes_freed": 0
        }

        threshold = self.config["disk"]["cleanup_threshold"]
        if disk_percent > threshold or force:
            result["cleanup_triggered"] = True

            cleanup_paths = self.config["disk"]["cleanup_paths"]
            for path in cleanup_paths:
                try:
                    if os.path.exists(path):
                        files_before = self._count_files(path)
                        size_before = self._get_directory_size(path)

                        # Clean old files (older than 7 days)
                        cutoff = datetime.now() - timedelta(days=7)
                        self._cleanup_old_files(path, cutoff)

                        files_after = self._count_files(path)
                        size_after = self._get_directory_size(path)

                        files_cleaned = files_before - files_after
                        bytes_freed = size_before - size_after

                        result["files_cleaned"] += files_cleaned
                        result["bytes_freed"] += bytes_freed

                        if files_cleaned > 0:
                            self.logger.info(f"Cleaned {files_cleaned} files from {path}, freed {bytes_freed} bytes")

                except Exception as e:
                    self.logger.error(f"Error cleaning {path}: {e}")

            # Log cleanup summary
            cleanup_log = {
                "timestamp": datetime.now().isoformat(),
                "disk_percent_before": disk_percent,
                "files_cleaned": result["files_cleaned"],
                "bytes_freed": result["bytes_freed"]
            }

            log_file = "data/cleanup_logs/cleanup.log"
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            with open(log_file, 'a') as f:
                f.write(json.dumps(cleanup_log) + '\n')

        return result

    def _count_files(self, path: str) -> int:
        """Count files in directory recursively"""
        try:
            count = 0
            for root, dirs, files in os.walk(path):
                count += len(files)
            return count
        except:
            return 0

    def _get_directory_size(self, path: str) -> int:
        """Get total size of directory in bytes"""
        try:
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    try:
                        total_size += os.path.getsize(fp)
                    except:
                        pass
            return total_size
        except:
            return 0

    def _cleanup_old_files(self, path: str, cutoff: datetime):
        """Remove files older than cutoff date"""
        try:
            for root, dirs, files in os.walk(path):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                        if file_time < cutoff:
                            os.remove(file_path)
                    except Exception as e:
                        self.logger.debug(f"Could not remove {file_path}: {e}")
        except Exception as e:
            self.logger.error(f"Error in cleanup_old_files: {e}")

    def check_cpu_throttling(self) -> Dict:
        """Check if CPU throttling should be applied"""
        load_avg = os.getloadavg()
        current_load = load_avg[0]  # 1-minute load average
        threshold = self.config["cpu"]["throttle_threshold"]

        result = {
            "load_average": current_load,
            "threshold": threshold,
            "should_throttle": current_load > threshold,
            "throttle_level": 0
        }

        if current_load > threshold:
            # Calculate throttle level (0-100%)
            throttle_level = min(50, int((current_load - threshold) / threshold * 50))
            result["throttle_level"] = throttle_level

            self.logger.warning(f"High CPU load {current_load:.2f}, throttling at {throttle_level}%")

        return result

    def get_resource_recommendations(self) -> List[str]:
        """Generate performance optimization recommendations"""
        recommendations = []

        if len(self.metrics_history) < 10:
            return ["Insufficient metrics history for recommendations"]

        recent_metrics = self.metrics_history[-10:]
        avg_memory = sum(m.memory_percent for m in recent_metrics) / len(recent_metrics)
        avg_cpu = sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics)
        avg_disk = sum(m.disk_percent for m in recent_metrics) / len(recent_metrics)

        # Memory recommendations
        if avg_memory > 80:
            recommendations.append("High memory usage detected. Consider increasing system memory or optimizing memory-intensive processes.")
        elif avg_memory < 30:
            recommendations.append("Low memory usage. Current memory allocation appears sufficient.")

        # CPU recommendations
        if avg_cpu > 80:
            recommendations.append("High CPU usage detected. Consider optimizing CPU-intensive tasks or scaling horizontally.")
        elif avg_cpu < 20:
            recommendations.append("Low CPU usage. Current CPU allocation is underutilized.")

        # Disk recommendations
        if avg_disk > 80:
            recommendations.append("High disk usage detected. Consider implementing more aggressive cleanup policies or adding storage.")

        # Worker scaling recommendations
        if recent_metrics:
            avg_queue = sum(m.queue_depth for m in recent_metrics) / len(recent_metrics)
            avg_workers = sum(m.worker_count for m in recent_metrics) / len(recent_metrics)

            if avg_queue > 100 and avg_workers < self.config["worker_scaling"]["max_workers"]:
                recommendations.append("Queue depth consistently high. Consider increasing maximum worker count.")
            elif avg_queue < 10 and avg_workers > self.config["worker_scaling"]["min_workers"]:
                recommendations.append("Queue depth consistently low. Current worker allocation may be excessive.")

        return recommendations

    def get_metrics_summary(self) -> Dict:
        """Get summary of recent metrics"""
        if not self.metrics_history:
            return {"error": "No metrics available"}

        recent = self.metrics_history[-1]
        return {
            "timestamp": recent.timestamp.isoformat(),
            "cpu_percent": recent.cpu_percent,
            "memory_percent": recent.memory_percent,
            "disk_percent": recent.disk_percent,
            "load_average": recent.load_avg,
            "queue_depth": recent.queue_depth,
            "worker_count": recent.worker_count,
            "metrics_count": len(self.metrics_history)
        }

# Convenience functions for external use
def check_memory_pressure() -> Dict:
    """Quick memory pressure check"""
    rm = ResourceManager()
    return rm.check_memory_pressure()

def get_resource_status() -> Dict:
    """Get current resource status"""
    rm = ResourceManager()
    metrics = rm.collect_metrics()
    return rm.get_metrics_summary()

def cleanup_disk() -> Dict:
    """Force disk cleanup"""
    rm = ResourceManager()
    return rm.cleanup_disk_space(force=True)

if __name__ == "__main__":
    # CLI interface for testing
    import sys

    rm = ResourceManager()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "status":
            print(json.dumps(rm.get_metrics_summary(), indent=2))
        elif command == "memory":
            print(json.dumps(rm.check_memory_pressure(), indent=2))
        elif command == "cleanup":
            print(json.dumps(rm.cleanup_disk_space(force=True), indent=2))
        elif command == "recommendations":
            recs = rm.get_resource_recommendations()
            for i, rec in enumerate(recs, 1):
                print(f"{i}. {rec}")
        else:
            print(f"Unknown command: {command}")
            print("Available commands: status, memory, cleanup, recommendations")
    else:
        # Collect metrics
        metrics = rm.collect_metrics()
        print(json.dumps(rm.get_metrics_summary(), indent=2))