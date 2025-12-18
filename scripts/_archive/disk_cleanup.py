#!/usr/bin/env python3
"""
Automated disk cleanup based on usage thresholds
"""

import os
import json
import time
import psutil
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import shutil
import sys

# Add helpers to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from helpers.resource_manager import ResourceManager

class DiskCleanupManager:
    """Manages automated disk space cleanup"""

    def __init__(self, config_path: str = "data/disk_cleanup_config.json"):
        self.config_path = config_path
        self.logger = self._setup_logging()
        self.config = self._load_config()
        self.resource_manager = ResourceManager()

    def _setup_logging(self) -> logging.Logger:
        """Setup logging for disk cleanup"""
        logger = logging.getLogger('disk_cleanup')
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.FileHandler('data/cleanup_logs/disk_cleanup.log')
            os.makedirs(os.path.dirname('data/cleanup_logs/disk_cleanup.log'), exist_ok=True)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def _load_config(self) -> Dict:
        """Load disk cleanup configuration"""
        default_config = {
            "cleanup_paths": [
                {
                    "path": "data/temp/",
                    "max_age_days": 1,
                    "recursive": True,
                    "patterns": ["*"]
                },
                {
                    "path": "data/logs/",
                    "max_age_days": 7,
                    "recursive": True,
                    "patterns": ["*.log", "*.tmp"]
                },
                {
                    "path": "archive/old-files/",
                    "max_age_days": 30,
                    "recursive": True,
                    "patterns": ["*"]
                },
                {
                    "path": "archive/diagnostic-logs/",
                    "max_age_days": 14,
                    "recursive": True,
                    "patterns": ["*"]
                },
                {
                    "path": "/tmp/",
                    "max_age_days": 1,
                    "recursive": False,
                    "patterns": ["oos_*", "bootstrap_*", "temp_*"]
                }
            ],
            "thresholds": {
                "warning": 80.0,      # percent disk usage
                "critical": 90.0,     # percent disk usage
                "emergency": 95.0     # percent disk usage
            },
            "cleanup_rules": {
                "log_files_max_size_mb": 100,
                "temp_files_max_age_hours": 24,
                "backup_files_keep_count": 5,
                "core_dumps_max_age_days": 1
            },
            "dry_run": False,
            "preserve_patterns": [
                "*.json",
                "config.*",
                ".env*",
                "README*",
                "requirements*"
            ]
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
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving config: {e}")

    def get_disk_usage(self, path: str = '/') -> Dict:
        """Get disk usage statistics"""
        try:
            usage = psutil.disk_usage(path)
            return {
                "total": usage.total,
                "used": usage.used,
                "free": usage.free,
                "percent": (usage.used / usage.total) * 100
            }
        except Exception as e:
            self.logger.error(f"Error getting disk usage for {path}: {e}")
            return {"total": 0, "used": 0, "free": 0, "percent": 0}

    def should_cleanup(self, disk_usage: Dict = None) -> Tuple[bool, str]:
        """Determine if cleanup should run"""
        if disk_usage is None:
            disk_usage = self.get_disk_usage()

        disk_percent = disk_usage["percent"]
        thresholds = self.config["thresholds"]

        if disk_percent >= thresholds["emergency"]:
            return True, "emergency"
        elif disk_percent >= thresholds["critical"]:
            return True, "critical"
        elif disk_percent >= thresholds["warning"]:
            return True, "warning"
        else:
            return False, "normal"

    def matches_pattern(self, filename: str, patterns: List[str]) -> bool:
        """Check if filename matches any of the patterns"""
        import fnmatch

        for pattern in patterns:
            if fnmatch.fnmatch(filename, pattern):
                return True
        return False

    def should_preserve_file(self, filepath: str) -> bool:
        """Check if file should be preserved"""
        filename = os.path.basename(filepath)
        preserve_patterns = self.config["preserve_patterns"]

        return self.matches_pattern(filename, preserve_patterns)

    def cleanup_path(self, path_config: Dict) -> Dict:
        """Clean up files in a specific path"""
        path = path_config["path"]
        max_age_days = path_config["max_age_days"]
        recursive = path_config.get("recursive", True)
        patterns = path_config.get("patterns", ["*"])

        result = {
            "path": path,
            "files_processed": 0,
            "files_deleted": 0,
            "bytes_freed": 0,
            "errors": []
        }

        if not os.path.exists(path):
            self.logger.debug(f"Path does not exist: {path}")
            return result

        cutoff_time = datetime.now() - timedelta(days=max_age_days)

        try:
            if recursive:
                files_to_process = []
                for root, dirs, files in os.walk(path):
                    for file in files:
                        filepath = os.path.join(root, file)
                        if self.matches_pattern(file, patterns):
                            files_to_process.append(filepath)
            else:
                files_to_process = []
                if os.path.isdir(path):
                    for file in os.listdir(path):
                        filepath = os.path.join(path, file)
                        if os.path.isfile(filepath) and self.matches_pattern(file, patterns):
                            files_to_process.append(filepath)

            for filepath in files_to_process:
                try:
                    result["files_processed"] += 1

                    # Check file age
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))

                    if file_mtime < cutoff_time:
                        # Check if file should be preserved
                        if self.should_preserve_file(filepath):
                            self.logger.debug(f"Preserving file: {filepath}")
                            continue

                        # Get file size before deletion
                        try:
                            file_size = os.path.getsize(filepath)
                        except:
                            file_size = 0

                        # Delete file
                        if not self.config["dry_run"]:
                            os.remove(filepath)
                            result["files_deleted"] += 1
                            result["bytes_freed"] += file_size
                            self.logger.debug(f"Deleted file: {filepath} ({file_size} bytes)")
                        else:
                            result["files_deleted"] += 1
                            result["bytes_freed"] += file_size
                            self.logger.info(f"[DRY RUN] Would delete: {filepath} ({file_size} bytes)")

                except Exception as e:
                    error_msg = f"Error processing file {filepath}: {e}"
                    result["errors"].append(error_msg)
                    self.logger.error(error_msg)

        except Exception as e:
            error_msg = f"Error walking directory {path}: {e}"
            result["errors"].append(error_msg)
            self.logger.error(error_msg)

        return result

    def cleanup_large_log_files(self) -> Dict:
        """Clean up or truncate large log files"""
        result = {
            "files_processed": 0,
            "files_truncated": 0,
            "bytes_freed": 0,
            "errors": []
        }

        max_size_mb = self.config["cleanup_rules"]["log_files_max_size_mb"]
        max_size_bytes = max_size_mb * 1024 * 1024

        log_paths = ["data/", "archive/log-files/"]

        for log_path in log_paths:
            if not os.path.exists(log_path):
                continue

            try:
                for root, dirs, files in os.walk(log_path):
                    for file in files:
                        if file.endswith(('.log', '.txt')):
                            filepath = os.path.join(root, file)

                            try:
                                result["files_processed"] += 1
                                file_size = os.path.getsize(filepath)

                                if file_size > max_size_bytes:
                                    if self.should_preserve_file(filepath):
                                        continue

                                    # Truncate file to last 25% of content
                                    if not self.config["dry_run"]:
                                        self._truncate_log_file(filepath, 0.25)

                                    bytes_freed = file_size - (file_size * 0.25)
                                    result["files_truncated"] += 1
                                    result["bytes_freed"] += bytes_freed

                                    self.logger.info(f"Truncated large log file: {filepath} "
                                                   f"({file_size} -> {file_size * 0.25:.0f} bytes)")

                            except Exception as e:
                                error_msg = f"Error processing log file {filepath}: {e}"
                                result["errors"].append(error_msg)
                                self.logger.error(error_msg)

            except Exception as e:
                error_msg = f"Error walking log directory {log_path}: {e}"
                result["errors"].append(error_msg)
                self.logger.error(error_msg)

        return result

    def _truncate_log_file(self, filepath: str, keep_ratio: float = 0.25):
        """Truncate log file keeping only the last portion"""
        try:
            with open(filepath, 'r') as f:
                lines = f.readlines()

            keep_lines = int(len(lines) * keep_ratio)
            if keep_lines < 10:  # Keep at least 10 lines
                keep_lines = min(10, len(lines))

            with open(filepath, 'w') as f:
                f.write(f"# Log file truncated on {datetime.now().isoformat()}\n")
                f.writelines(lines[-keep_lines:])

        except Exception as e:
            self.logger.error(f"Error truncating {filepath}: {e}")

    def cleanup_core_dumps(self) -> Dict:
        """Clean up core dump files"""
        result = {
            "files_processed": 0,
            "files_deleted": 0,
            "bytes_freed": 0,
            "errors": []
        }

        max_age_days = self.config["cleanup_rules"]["core_dumps_max_age_days"]
        cutoff_time = datetime.now() - timedelta(days=max_age_days)

        core_patterns = ["core", "core.*", "*.core"]
        search_paths = ["/tmp/", "/var/tmp/", "./"]

        for search_path in search_paths:
            if not os.path.exists(search_path):
                continue

            try:
                for file in os.listdir(search_path):
                    filepath = os.path.join(search_path, file)

                    if os.path.isfile(filepath):
                        # Check if it's a core dump
                        if self.matches_pattern(file, core_patterns):
                            result["files_processed"] += 1

                            try:
                                file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))

                                if file_mtime < cutoff_time:
                                    file_size = os.path.getsize(filepath)

                                    if not self.config["dry_run"]:
                                        os.remove(filepath)

                                    result["files_deleted"] += 1
                                    result["bytes_freed"] += file_size

                                    self.logger.info(f"Deleted core dump: {filepath} ({file_size} bytes)")

                            except Exception as e:
                                error_msg = f"Error processing core dump {filepath}: {e}"
                                result["errors"].append(error_msg)
                                self.logger.error(error_msg)

            except Exception as e:
                error_msg = f"Error searching for core dumps in {search_path}: {e}"
                result["errors"].append(error_msg)
                self.logger.error(error_msg)

        return result

    def run_cleanup(self, force: bool = False) -> Dict:
        """Run full disk cleanup process"""
        start_time = datetime.now()
        disk_usage_before = self.get_disk_usage()

        should_run, cleanup_level = self.should_cleanup(disk_usage_before)

        if not should_run and not force:
            return {
                "timestamp": start_time.isoformat(),
                "cleanup_triggered": False,
                "disk_usage_before": disk_usage_before,
                "cleanup_level": cleanup_level,
                "message": f"Cleanup not needed (disk usage: {disk_usage_before['percent']:.1f}%)"
            }

        self.logger.info(f"Starting disk cleanup (level: {cleanup_level}, force: {force})")

        total_result = {
            "timestamp": start_time.isoformat(),
            "cleanup_triggered": True,
            "cleanup_level": cleanup_level,
            "disk_usage_before": disk_usage_before,
            "total_files_processed": 0,
            "total_files_deleted": 0,
            "total_bytes_freed": 0,
            "cleanup_results": [],
            "errors": []
        }

        # Clean up configured paths
        for path_config in self.config["cleanup_paths"]:
            result = self.cleanup_path(path_config)
            total_result["cleanup_results"].append(result)
            total_result["total_files_processed"] += result["files_processed"]
            total_result["total_files_deleted"] += result["files_deleted"]
            total_result["total_bytes_freed"] += result["bytes_freed"]
            total_result["errors"].extend(result["errors"])

        # Clean up large log files
        log_result = self.cleanup_large_log_files()
        total_result["cleanup_results"].append({
            "type": "large_log_files",
            **log_result
        })
        total_result["total_files_processed"] += log_result["files_processed"]
        total_result["total_files_deleted"] += log_result["files_truncated"]
        total_result["total_bytes_freed"] += log_result["bytes_freed"]
        total_result["errors"].extend(log_result["errors"])

        # Clean up core dumps
        core_result = self.cleanup_core_dumps()
        total_result["cleanup_results"].append({
            "type": "core_dumps",
            **core_result
        })
        total_result["total_files_processed"] += core_result["files_processed"]
        total_result["total_files_deleted"] += core_result["files_deleted"]
        total_result["total_bytes_freed"] += core_result["bytes_freed"]
        total_result["errors"].extend(core_result["errors"])

        # Get disk usage after cleanup
        disk_usage_after = self.get_disk_usage()
        total_result["disk_usage_after"] = disk_usage_after
        total_result["disk_space_freed"] = disk_usage_before["used"] - disk_usage_after["used"]

        # Calculate duration
        end_time = datetime.now()
        total_result["duration_seconds"] = (end_time - start_time).total_seconds()

        # Log summary
        self.logger.info(
            f"Cleanup completed: {total_result['total_files_deleted']} files deleted, "
            f"{total_result['total_bytes_freed']} bytes freed, "
            f"disk usage: {disk_usage_before['percent']:.1f}% -> {disk_usage_after['percent']:.1f}%"
        )

        # Save cleanup log
        self._save_cleanup_log(total_result)

        return total_result

    def _save_cleanup_log(self, result: Dict):
        """Save cleanup result to log file"""
        try:
            log_file = "data/cleanup_logs/cleanup_history.jsonl"
            os.makedirs(os.path.dirname(log_file), exist_ok=True)

            with open(log_file, 'a') as f:
                f.write(json.dumps(result) + '\n')

        except Exception as e:
            self.logger.error(f"Error saving cleanup log: {e}")

    def get_cleanup_history(self, limit: int = 10) -> List[Dict]:
        """Get recent cleanup history"""
        history = []
        log_file = "data/cleanup_logs/cleanup_history.jsonl"

        try:
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    lines = f.readlines()

                # Get last N lines
                recent_lines = lines[-limit:] if len(lines) > limit else lines

                for line in recent_lines:
                    try:
                        history.append(json.loads(line.strip()))
                    except:
                        continue

        except Exception as e:
            self.logger.error(f"Error reading cleanup history: {e}")

        return history

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Disk Cleanup Manager")
    parser.add_argument("--force", action="store_true",
                       help="Force cleanup regardless of disk usage")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be deleted without actually deleting")
    parser.add_argument("--config", default="data/disk_cleanup_config.json",
                       help="Configuration file path")
    parser.add_argument("--status", action="store_true",
                       help="Show disk usage status")
    parser.add_argument("--history", action="store_true",
                       help="Show cleanup history")

    args = parser.parse_args()

    cleanup_manager = DiskCleanupManager(args.config)

    if args.dry_run:
        cleanup_manager.config["dry_run"] = True

    if args.status:
        disk_usage = cleanup_manager.get_disk_usage()
        should_run, level = cleanup_manager.should_cleanup(disk_usage)

        print(json.dumps({
            "disk_usage": disk_usage,
            "should_cleanup": should_run,
            "cleanup_level": level
        }, indent=2))

    elif args.history:
        history = cleanup_manager.get_cleanup_history()
        print(json.dumps(history, indent=2))

    else:
        result = cleanup_manager.run_cleanup(force=args.force)
        print(json.dumps(result, indent=2))