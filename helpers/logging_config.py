#!/usr/bin/env python3
"""
Atlas Structured Logging Configuration
Centralized logging setup with journald integration, JSON formatting, and performance metrics.
"""

import os
import sys
import json
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.metrics_collector import get_metrics_collector

@dataclass
class LogRecord:
    """Structured log record for JSON formatting."""
    timestamp: str
    level: str
    component: str
    message: str
    details: Optional[Dict[str, Any]] = None
    performance_metrics: Optional[Dict[str, Any]] = None

class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def __init__(self, component_name: str = "atlas"):
        super().__init__()
        self.component_name = component_name

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = LogRecord(
            timestamp=datetime.fromtimestamp(record.created).isoformat(),
            level=record.levelname,
            component=self.component_name,
            message=record.getMessage(),
            details=getattr(record, 'details', None)
        )

        # Add performance metrics for INFO and higher levels
        if record.levelno >= logging.INFO:
            try:
                metrics = get_metrics_collector()
                memory_bytes = metrics.get_metric_value("atlas_memory_usage_bytes", 0) or 0
                cpu_usage = metrics.get_metric_value("atlas_cpu_usage_percent", 0) or 0
                queue_pending = metrics.get_metric_value("atlas_queue_pending_total", 0) or 0

                log_data.performance_metrics = {
                    "memory_usage_mb": memory_bytes / (1024**2) if memory_bytes else 0,
                    "cpu_usage_percent": cpu_usage * 100 if cpu_usage else 0,
                    "queue_pending": queue_pending
                }
            except Exception:
                # Don't fail logging if metrics collection fails
                pass

        return json.dumps(asdict(log_data), default=str)

class AtlasLogger:
    """Centralized Atlas logging manager."""

    def __init__(self, component_name: str = "atlas"):
        self.component_name = component_name
        self.logger = None

        # Use /var/log/atlas if writable, otherwise fall back to logs/
        try:
            self.log_dir = Path("/var/log/atlas")
            self.log_dir.mkdir(exist_ok=True, parents=True)
        except PermissionError:
            # Fall back to local logs directory
            self.log_dir = Path("logs") / "atlas"
            self.log_dir.mkdir(exist_ok=True, parents=True)

        self.setup_logging()

    def setup_logging(self):
        """Setup logging with multiple handlers."""
        # Log directory already created in __init__

        # Get or create logger
        self.logger = logging.getLogger(self.component_name)
        self.logger.setLevel(logging.DEBUG)

        # Clear existing handlers
        self.logger.handlers = []

        # Console handler with simple format for development
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # File handler with JSON format for structured logging
        json_file = self.log_dir / f"{self.component_name}.json.log"
        file_handler = logging.handlers.RotatingFileHandler(
            json_file,
            maxBytes=100 * 1024 * 1024,  # 100MB
            backupCount=10
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(JSONFormatter(self.component_name))
        self.logger.addHandler(file_handler)

        # Error-only handler for critical issues
        error_file = self.log_dir / f"{self.component_name}.error.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_file,
            maxBytes=50 * 1024 * 1024,  # 50MB
            backupCount=5
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(JSONFormatter(self.component_name))
        self.logger.addHandler(error_handler)

        # Syslog handler for journald integration
        try:
            syslog_handler = logging.handlers.SysLogHandler(address='/dev/log')
            syslog_handler.setLevel(logging.WARNING)
            syslog_formatter = logging.Formatter(
                f'atlas[{self.component_name}]: %(levelname)s - %(message)s'
            )
            syslog_handler.setFormatter(syslog_formatter)
            self.logger.addHandler(syslog_handler)
        except Exception:
            # Syslog might not be available in all environments
            pass

    def debug(self, message: str, **kwargs):
        """Log debug message with optional details."""
        self._log(logging.DEBUG, message, kwargs)

    def info(self, message: str, **kwargs):
        """Log info message with optional details."""
        self._log(logging.INFO, message, kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message with optional details."""
        self._log(logging.WARNING, message, kwargs)

    def error(self, message: str, **kwargs):
        """Log error message with optional details."""
        self._log(logging.ERROR, message, kwargs)

    def critical(self, message: str, **kwargs):
        """Log critical message with optional details."""
        self._log(logging.CRITICAL, message, kwargs)

    def _log(self, level: int, message: str, details: Dict[str, Any]):
        """Internal logging method with details attachment."""
        if details:
            # Create a temporary record with details
            record = logging.LogRecord(
                name=self.logger.name,
                level=level,
                pathname="",
                lineno=0,
                msg=message,
                args=(),
                exc_info=None
            )
            record.details = details
            self.logger.handle(record)
        else:
            self.logger.log(level, message)

class PerformanceLogger:
    """Specialized logger for performance metrics."""

    def __init__(self):
        self.logger = AtlasLogger("performance")
        self.metrics = get_metrics_collector()
        self.last_log_time = 0
        self.log_interval = 60  # Log every 60 seconds

    def log_performance_snapshot(self, force: bool = False):
        """Log current performance metrics if interval has passed."""
        import time

        current_time = time.time()
        if not force and (current_time - self.last_log_time) < self.log_interval:
            return

        try:
            # Collect system metrics
            import psutil
            memory = psutil.virtual_memory()

            # Get metric values safely, defaulting to 0 if None
            disk_free_bytes = self.metrics.get_metric_value("atlas_disk_free_bytes", 0) or 0
            queue_pending = self.metrics.get_metric_value("atlas_queue_pending_total", 0) or 0
            queue_processing = self.metrics.get_metric_value("atlas_queue_processing_total", 0) or 0
            articles_processed = self.metrics.get_metric_value("atlas_articles_processed_total", 0) or 0
            uptime_seconds = self.metrics.get_metric_value("atlas_system_uptime_seconds", 0) or 0

            performance_data = {
                "memory_percent": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "cpu_load_1min": os.getloadavg()[0],
                "cpu_load_5min": os.getloadavg()[1],
                "disk_free_gb": disk_free_bytes / (1024**3) if disk_free_bytes else 0,
                "queue_pending": queue_pending,
                "queue_processing": queue_processing,
                "articles_processed": articles_processed,
                "uptime_hours": uptime_seconds / 3600 if uptime_seconds else 0
            }

            self.logger.info("Performance snapshot", **performance_data)
            self.last_log_time = current_time

        except Exception as e:
            self.logger.error(f"Failed to log performance snapshot: {e}")

def get_logger(component_name: str = "atlas") -> AtlasLogger:
    """Get or create a logger for the specified component."""
    if not hasattr(get_logger, '_loggers'):
        get_logger._loggers = {}

    if component_name not in get_logger._loggers:
        get_logger._loggers[component_name] = AtlasLogger(component_name)

    return get_logger._loggers[component_name]

def setup_journald_persistence():
    """Setup persistent journald storage."""
    try:
        import subprocess

        # Create journal directory
        journal_dir = Path("/var/log/journal")
        if not journal_dir.exists():
            subprocess.run(["sudo", "mkdir", "-p", str(journal_dir)], check=True)
            subprocess.run(["sudo", "systemd-tmpfiles", "--create", "--prefix", "/var/log/journal"], check=True)

        # Configure journald for persistence
        journald_config = """[Journal]
Storage=persistent
SystemMaxUse=1G
SystemKeepFree=100M
SystemMaxFileSize=100M
RuntimeMaxUse=100M
RuntimeKeepFree=50M
MaxRetentionSec=7day
"""

        config_file = Path("/etc/systemd/journald.conf.d/atlas.conf")
        config_file.parent.mkdir(exist_ok=True, parents=True)

        with open(config_file, 'w') as f:
            f.write(journald_config)

        # Restart journald to apply config
        subprocess.run(["sudo", "systemctl", "restart", "systemd-journald"], check=True)

        logger = get_logger("logging_config")
        logger.info("Journald persistence configured successfully")

    except Exception as e:
        logger = get_logger("logging_config")
        logger.error(f"Failed to configure journald persistence: {e}")

def emergency_log_compression():
    """Compress logs when disk space is low."""
    try:
        import shutil
        import gzip

        logger = get_logger("logging_config")

        # Check disk space
        total, used, free = shutil.disk_usage("/var/log")
        free_gb = free / (1024**3)

        if free_gb < 2.0:  # Less than 2GB free
            logger.warning(f"Low disk space detected: {free_gb:.1f}GB free, compressing logs")

            log_dir = Path("/var/log/atlas")
            compressed_count = 0

            for log_file in log_dir.glob("*.log"):
                if log_file.stat().st_size > 10 * 1024 * 1024:  # Files > 10MB
                    compressed_file = log_file.with_suffix(log_file.suffix + '.gz')

                    with open(log_file, 'rb') as f_in:
                        with gzip.open(compressed_file, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)

                    log_file.unlink()  # Remove original
                    compressed_count += 1

            logger.info(f"Emergency log compression completed: {compressed_count} files compressed")

    except Exception as e:
        logger = get_logger("logging_config")
        logger.error(f"Emergency log compression failed: {e}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Atlas Logging Configuration")
    parser.add_argument("--setup-journald", action="store_true", help="Setup journald persistence")
    parser.add_argument("--compress-logs", action="store_true", help="Compress logs if disk space low")
    parser.add_argument("--test-logging", action="store_true", help="Test logging functionality")

    args = parser.parse_args()

    if args.setup_journald:
        setup_journald_persistence()
    elif args.compress_logs:
        emergency_log_compression()
    elif args.test_logging:
        # Test all log levels
        logger = get_logger("test")
        logger.debug("Debug message test", test_data={"level": "debug"})
        logger.info("Info message test", test_data={"level": "info"})
        logger.warning("Warning message test", test_data={"level": "warning"})
        logger.error("Error message test", test_data={"level": "error"})
        logger.critical("Critical message test", test_data={"level": "critical"})

        # Test performance logging
        perf_logger = PerformanceLogger()
        perf_logger.log_performance_snapshot(force=True)

        print("Logging test completed. Check /var/log/atlas/ for log files.")
    else:
        print("Use --help to see available options")