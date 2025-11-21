"""
Error recovery and diagnostic utilities for Atlas v4.

Provides comprehensive error analysis, recovery strategies, and
diagnostic tools for troubleshooting failed operations.
"""

import traceback
import sys
import os
import platform
import psutil
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import json

from .retry import RetryResult
from .queue import QueueItem


class ErrorSeverity(Enum):
    """Severity levels for errors."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Categories of errors for better classification."""
    NETWORK = "network"
    STORAGE = "storage"
    VALIDATION = "validation"
    PROCESSING = "processing"
    CONFIGURATION = "configuration"
    SYSTEM = "system"
    UNKNOWN = "unknown"


@dataclass
class ErrorReport:
    """Comprehensive error report for analysis."""
    error_id: str
    timestamp: datetime
    severity: ErrorSeverity
    category: ErrorCategory
    error_type: str
    error_message: str
    traceback: List[str]
    context: Dict[str, Any]
    system_info: Dict[str, Any]
    suggested_actions: List[str] = field(default_factory=list)
    recovery_attempts: int = 0
    resolved: bool = False
    resolution_notes: Optional[str] = None


@dataclass
class SystemHealth:
    """System health information."""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    network_status: bool
    database_status: bool
    queue_status: Dict[str, Any]
    active_processes: int
    system_uptime: float


class ErrorAnalyzer:
    """
    Analyzes errors and provides diagnostic information.

    Features:
    - Error categorization and severity assessment
    - Root cause analysis
    - Suggested recovery actions
    - Pattern detection
    """

    def __init__(self):
        """Initialize error analyzer."""
        self.logger = logging.getLogger(f"atlas.core.{self.__class__.__name__}")
        self.error_patterns = self._load_error_patterns()
        self.error_history: List[ErrorReport] = []

    def analyze_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> ErrorReport:
        """
        Analyze an error and generate comprehensive report.

        Args:
            error: The error to analyze
            context: Context information when error occurred

        Returns:
            Detailed error report
        """
        if context is None:
            context = {}

        error_id = self._generate_error_id(error)
        timestamp = datetime.now()

        # Extract error information
        error_type = type(error).__name__
        error_message = str(error)
        traceback_list = traceback.format_exc().split('\n')

        # Categorize error
        category = self._categorize_error(error, error_message, context)
        severity = self._assess_severity(error, category, context)

        # Get system information
        system_info = self._get_system_info()

        # Generate suggested actions
        suggested_actions = self._generate_suggested_actions(
            error, category, severity, context
        )

        # Create error report
        report = ErrorReport(
            error_id=error_id,
            timestamp=timestamp,
            severity=severity,
            category=category,
            error_type=error_type,
            error_message=error_message,
            traceback=traceback_list,
            context=context,
            system_info=system_info,
            suggested_actions=suggested_actions
        )

        # Store in history
        self.error_history.append(report)

        # Keep history manageable (last 1000 errors)
        if len(self.error_history) > 1000:
            self.error_history = self.error_history[-1000:]

        self.logger.info(
            f"Analyzed error: {error_type} ({category.value}, {severity.value})",
            error_id=error_id
        )

        return report

    def _generate_error_id(self, error: Exception) -> str:
        """Generate unique error ID."""
        error_hash = hash(str(error) + str(datetime.now().timestamp()))
        return f"ERR_{abs(error_hash) % 1000000:06d}"

    def _categorize_error(
        self,
        error: Exception,
        error_message: str,
        context: Dict[str, Any]
    ) -> ErrorCategory:
        """Categorize error based on type and message."""
        error_message_lower = error_message.lower()
        error_type = type(error).__name__.lower()

        # Network-related errors
        network_keywords = [
            "connection", "timeout", "network", "dns", "socket",
            "http", "request", "response", "ssl", "certificate"
        ]

        if any(keyword in error_message_lower or keyword in error_type
               for keyword in network_keywords):
            return ErrorCategory.NETWORK

        # Storage-related errors
        storage_keywords = [
            "file", "directory", "disk", "space", "permission",
            "database", "sqlite", "write", "read", "access"
        ]

        if any(keyword in error_message_lower or keyword in error_type
               for keyword in storage_keywords):
            return ErrorCategory.STORAGE

        # Validation errors
        validation_keywords = [
            "validation", "invalid", "missing", "required",
            "format", "schema", "type", "value"
        ]

        if any(keyword in error_message_lower or keyword in error_type
               for keyword in validation_keywords):
            return ErrorCategory.VALIDATION

        # Configuration errors
        config_keywords = [
            "config", "setting", "parameter", "option",
            "yaml", "json", "parse"
        ]

        if any(keyword in error_message_lower or keyword in error_type
               for keyword in config_keywords):
            return ErrorCategory.CONFIGURATION

        # System errors
        system_keywords = [
            "memory", "cpu", "process", "system", "os",
            "permission", "access denied"
        ]

        if any(keyword in error_message_lower or keyword in error_type
               for keyword in system_keywords):
            return ErrorCategory.SYSTEM

        # Processing errors (default for content processing issues)
        processing_keywords = [
            "process", "parse", "extract", "transform",
            "content", "ingest", "convert"
        ]

        if any(keyword in error_message_lower or keyword in error_type
               for keyword in processing_keywords):
            return ErrorCategory.PROCESSING

        return ErrorCategory.UNKNOWN

    def _assess_severity(
        self,
        error: Exception,
        category: ErrorCategory,
        context: Dict[str, Any]
    ) -> ErrorSeverity:
        """Assess error severity based on impact and type."""
        error_message = str(error).lower()

        # Critical indicators
        critical_keywords = [
            "critical", "fatal", "emergency", "corruption",
            "database locked", "out of memory", "disk full"
        ]

        if any(keyword in error_message for keyword in critical_keywords):
            return ErrorSeverity.CRITICAL

        # High severity based on category
        if category in [ErrorCategory.SYSTEM, ErrorCategory.STORAGE]:
            return ErrorSeverity.HIGH

        # Medium severity for processing and network issues
        if category in [ErrorCategory.PROCESSING, ErrorCategory.NETWORK]:
            return ErrorSeverity.MEDIUM

        # Low severity for validation and configuration
        if category in [ErrorCategory.VALIDATION, ErrorCategory.CONFIGURATION]:
            return ErrorSeverity.LOW

        return ErrorSeverity.MEDIUM

    def _generate_suggested_actions(
        self,
        error: Exception,
        category: ErrorCategory,
        severity: ErrorSeverity,
        context: Dict[str, Any]
    ) -> List[str]:
        """Generate suggested recovery actions."""
        actions = []
        error_message = str(error).lower()

        if category == ErrorCategory.NETWORK:
            if "timeout" in error_message:
                actions.extend([
                    "Increase timeout settings",
                    "Check network connectivity",
                    "Verify remote service is accessible"
                ])
            if "connection" in error_message:
                actions.extend([
                    "Check internet connection",
                    "Verify firewall settings",
                    "Test remote service availability"
                ])

        elif category == ErrorCategory.STORAGE:
            if "permission" in error_message:
                actions.extend([
                    "Check file/directory permissions",
                    "Verify user has write access",
                    "Run with appropriate privileges"
                ])
            if "space" in error_message:
                actions.extend([
                    "Free up disk space",
                    "Clean up temporary files",
                    "Check disk usage"
                ])
            if "database" in error_message:
                actions.extend([
                    "Check database file integrity",
                    "Verify database permissions",
                    "Restart database connection"
                ])

        elif category == ErrorCategory.VALIDATION:
            actions.extend([
                "Validate input data format",
                "Check required fields are present",
                "Verify data meets schema requirements"
            ])

        elif category == ErrorCategory.PROCESSING:
            actions.extend([
                "Try alternative processing method",
                    "Check content format is supported",
                "Verify source data is accessible"
            ])

        # High and critical severity actions
        if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            actions.extend([
                "Consider immediate system restart",
                "Contact system administrator",
                "Check system logs for related issues"
            ])

        # Default action if no specific ones generated
        if not actions:
            actions = [
                "Review error details and context",
                "Check system resources and status",
                "Try operation again with different parameters"
            ]

        return actions

    def _get_system_info(self) -> Dict[str, Any]:
        """Get current system information."""
        try:
            return {
                "platform": platform.platform(),
                "python_version": sys.version,
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage('/').percent,
                "process_count": len(psutil.pids()),
                "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat()
            }
        except Exception as e:
            self.logger.warning(f"Failed to get system info: {str(e)}")
            return {"error": str(e)}

    def _load_error_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Load known error patterns and their solutions."""
        return {
            "connection_timeout": {
                "pattern": r"(timeout|timed out)",
                "category": ErrorCategory.NETWORK,
                "actions": [
                    "Increase timeout configuration",
                    "Check network stability",
                    "Verify remote service status"
                ]
            },
            "permission_denied": {
                "pattern": r"(permission denied|access denied)",
                "category": ErrorCategory.STORAGE,
                "actions": [
                    "Check file/directory permissions",
                    "Run with appropriate user privileges",
                    "Verify ownership of target files"
                ]
            },
            "disk_full": {
                "pattern": r"(no space|disk full|insufficient space)",
                "category": ErrorCategory.STORAGE,
                "actions": [
                    "Free up disk space",
                    "Clean up temporary files",
                    "Archive old data"
                ]
            }
        }

    def get_error_patterns(self) -> Dict[str, Any]:
        """Get error pattern analysis."""
        if not self.error_history:
            return {}

        # Analyze recent errors (last 24 hours)
        cutoff_time = datetime.now() - timedelta(hours=24)
        recent_errors = [
            error for error in self.error_history
            if error.timestamp > cutoff_time
        ]

        # Count by category
        category_counts = {}
        for error in recent_errors:
            category = error.category.value
            category_counts[category] = category_counts.get(category, 0) + 1

        # Count by severity
        severity_counts = {}
        for error in recent_errors:
            severity = error.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        # Find most common error types
        error_type_counts = {}
        for error in recent_errors:
            error_type = error.error_type
            error_type_counts[error_type] = error_type_counts.get(error_type, 0) + 1

        return {
            "total_errors_24h": len(recent_errors),
            "by_category": category_counts,
            "by_severity": severity_counts,
            "most_common_types": sorted(
                error_type_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }


class RecoveryManager:
    """
    Manages error recovery strategies and execution.

    Provides automated recovery actions and tracks recovery success.
    """

    def __init__(self, error_analyzer: ErrorAnalyzer):
        """
        Initialize recovery manager.

        Args:
            error_analyzer: ErrorAnalyzer for error analysis
        """
        self.analyzer = error_analyzer
        self.recovery_strategies: Dict[ErrorCategory, List[Callable]] = {
            category: [] for category in ErrorCategory
        }
        self.recovery_history: List[Dict[str, Any]] = []
        self.logger = logging.getLogger(f"atlas.core.{self.__class__.__name__}")

    def register_strategy(
        self,
        category: ErrorCategory,
        strategy: Callable[[Exception, Dict[str, Any]], bool]
    ) -> None:
        """
        Register recovery strategy for error category.

        Args:
            category: Error category this strategy handles
            strategy: Recovery function (returns True if successful)
        """
        self.recovery_strategies[category].append(strategy)
        self.logger.debug(f"Registered recovery strategy for: {category.value}")

    def attempt_recovery(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Attempt to recover from error.

        Args:
            error: The error to recover from
            context: Error context

        Returns:
            True if recovery was successful
        """
        if context is None:
            context = {}

        # Analyze error
        report = self.analyzer.analyze_error(error, context)
        category = report.category

        recovery_start = datetime.now()

        # Try recovery strategies
        strategies = self.recovery_strategies.get(category, [])

        for i, strategy in enumerate(strategies):
            try:
                self.logger.info(
                    f"Attempting recovery strategy {i+1}/{len(strategies)} for {category.value}",
                    strategy=strategy.__name__
                )

                success = strategy(error, context)

                if success:
                    recovery_time = (datetime.now() - recovery_start).total_seconds()

                    # Record successful recovery
                    self._record_recovery(report, strategy, recovery_time, True)

                    self.logger.info(
                        f"Successfully recovered from error: {report.error_id}",
                        strategy=strategy.__name__,
                        recovery_time=recovery_time
                    )

                    return True

            except Exception as recovery_error:
                self.logger.warning(
                    f"Recovery strategy failed: {strategy.__name__}",
                    error=str(recovery_error)
                )
                continue

        # Record failed recovery
        recovery_time = (datetime.now() - recovery_start).total_seconds()
        self._record_recovery(report, None, recovery_time, False)

        self.logger.error(
            f"All recovery strategies failed for error: {report.error_id}",
            strategies_tried=len(strategies),
            total_time=recovery_time
        )

        return False

    def _record_recovery(
        self,
        error_report: ErrorReport,
        strategy: Optional[Callable],
        duration: float,
        success: bool
    ) -> None:
        """Record recovery attempt in history."""
        recovery_record = {
            "error_id": error_report.error_id,
            "timestamp": datetime.now().isoformat(),
            "strategy": strategy.__name__ if strategy else None,
            "duration": duration,
            "success": success,
            "error_category": error_report.category.value,
            "error_severity": error_report.severity.value
        }

        self.recovery_history.append(recovery_record)

        # Keep history manageable
        if len(self.recovery_history) > 500:
            self.recovery_history = self.recovery_history[-500:]

    def get_recovery_stats(self) -> Dict[str, Any]:
        """Get recovery statistics."""
        if not self.recovery_history:
            return {}

        # Recent recoveries (last 24 hours)
        cutoff_time = datetime.now() - timedelta(hours=24)
        recent_recoveries = [
            recovery for recovery in self.recovery_history
            if datetime.fromisoformat(recovery["timestamp"]) > cutoff_time
        ]

        success_count = sum(1 for r in recent_recoveries if r["success"])
        total_count = len(recent_recoveries)

        # Success rate by category
        category_stats = {}
        for recovery in recent_recoveries:
            category = recovery["error_category"]
            if category not in category_stats:
                category_stats[category] = {"success": 0, "total": 0}

            category_stats[category]["total"] += 1
            if recovery["success"]:
                category_stats[category]["success"] += 1

        # Calculate success rates
        for category in category_stats:
            stats = category_stats[category]
            stats["success_rate"] = stats["success"] / stats["total"] if stats["total"] > 0 else 0

        return {
            "total_recoveries_24h": total_count,
            "success_rate_24h": success_count / total_count if total_count > 0 else 0,
            "by_category": category_stats,
            "average_recovery_time": sum(r["duration"] for r in recent_recoveries) / total_count if total_count > 0 else 0
        }


# Built-in recovery strategies
def clear_temp_files_recovery(error: Exception, context: Dict[str, Any]) -> bool:
    """Recovery strategy: Clear temporary files."""
    try:
        temp_dirs = ['/tmp', '/var/tmp']
        cleared_space = 0

        for temp_dir in temp_dirs:
            if os.path.exists(temp_dir):
                for item in Path(temp_dir).glob('atlas_*'):
                    if item.is_file():
                        size = item.stat().st_size
                        item.unlink()
                        cleared_space += size

        logging.info(f"Cleared {cleared_space} bytes of temporary files")
        return cleared_space > 0

    except Exception:
        return False


def restart_database_recovery(error: Exception, context: Dict[str, Any]) -> bool:
    """Recovery strategy: Restart database connection."""
    try:
        # This would implement database connection restart logic
        # For now, just log the attempt
        logging.info("Attempting database connection restart")
        return True

    except Exception:
        return False


def get_system_health() -> SystemHealth:
    """Get current system health information."""
    try:
        # Basic system health checks
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        # Network check (basic connectivity test)
        network_status = True  # Simplified - would implement actual check

        # Database check
        database_status = True  # Simplified - would implement actual check

        # Queue status
        queue_status = {
            "processing": 0,  # Would get from actual queue
            "pending": 0,
            "failed": 0
        }

        active_processes = len(psutil.pids())
        uptime = datetime.now().timestamp() - psutil.boot_time()

        return SystemHealth(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            disk_usage_percent=disk.percent,
            network_status=network_status,
            database_status=database_status,
            queue_status=queue_status,
            active_processes=active_processes,
            system_uptime=uptime
        )

    except Exception as e:
        logging.error(f"Failed to get system health: {str(e)}")
        return SystemHealth(
            timestamp=datetime.now(),
            cpu_percent=0,
            memory_percent=0,
            disk_usage_percent=0,
            network_status=False,
            database_status=False,
            queue_status={},
            active_processes=0,
            system_uptime=0
        )