#!/usr/bin/env python3
"""
Service Health Monitoring - Phase 3.4
Comprehensive health monitoring for all Atlas services with proactive detection
"""

import time
import json
import logging
import psutil
import requests
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import threading
import subprocess
import socket
from contextlib import contextmanager

from .atlas_monitoring import AtlasMonitor, SystemMetrics, AtlasMetrics
from scripts.alert_manager import AlertManager as AtlasAlertManager

class HealthStatus(Enum):
    """Service health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    DOWN = "down"
    UNKNOWN = "unknown"

@dataclass
class HealthCheck:
    """Individual health check configuration"""
    name: str
    check_function: Callable[[], bool]
    critical: bool = False
    timeout: int = 30
    interval: int = 60  # seconds between checks
    consecutive_failures_threshold: int = 3

@dataclass
class ServiceHealth:
    """Service health state tracking"""
    name: str
    status: HealthStatus = HealthStatus.UNKNOWN
    last_check: Optional[datetime] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    total_checks: int = 0
    successful_checks: int = 0
    last_error: Optional[str] = None
    response_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

class AtlasServiceHealthMonitor:
    """
    Comprehensive health monitoring for Atlas services
    Integrates with monitoring and alerting for proactive issue detection
    """

    def __init__(self, base_path: str = "/home/ubuntu/dev/atlas"):
        self.base_path = Path(base_path)
        self.data_dir = self.base_path / "data" / "health_monitoring"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Health state storage
        self.health_file = self.data_dir / "service_health.json"
        self.services: Dict[str, ServiceHealth] = {}
        self.health_checks: Dict[str, HealthCheck] = {}

        # Integration with monitoring and alerting
        self.atlas_monitor = AtlasMonitor()
        self.alert_manager = AtlasAlertManager()

        # Background monitoring
        self.monitoring_thread = None
        self.monitoring_active = False
        self.monitoring_interval = 30  # seconds

        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("ServiceHealthMonitor")

        # Initialize health checks
        self._initialize_health_checks()
        self._load_health_state()

    def _initialize_health_checks(self):
        """Initialize health checks for Atlas services"""

        # Core system health checks
        self.add_health_check(HealthCheck(
            name="system_resources",
            check_function=self._check_system_resources,
            critical=True,
            interval=30
        ))

        self.add_health_check(HealthCheck(
            name="database_connectivity",
            check_function=self._check_database_connectivity,
            critical=True,
            interval=60
        ))

        self.add_health_check(HealthCheck(
            name="disk_space",
            check_function=self._check_disk_space,
            critical=True,
            interval=120
        ))

        # Atlas service health checks
        self.add_health_check(HealthCheck(
            name="atlas_api",
            check_function=self._check_atlas_api,
            critical=False,
            interval=45
        ))

        self.add_health_check(HealthCheck(
            name="background_processing",
            check_function=self._check_background_processing,
            critical=False,
            interval=300  # 5 minutes
        ))

        self.add_health_check(HealthCheck(
            name="search_functionality",
            check_function=self._check_search_functionality,
            critical=False,
            interval=180
        ))

        self.add_health_check(HealthCheck(
            name="content_pipeline",
            check_function=self._check_content_pipeline,
            critical=False,
            interval=240
        ))

        self.logger.info(f"Initialized {len(self.health_checks)} health checks")

    def add_health_check(self, health_check: HealthCheck):
        """Add a health check to the monitoring system"""
        self.health_checks[health_check.name] = health_check
        if health_check.name not in self.services:
            self.services[health_check.name] = ServiceHealth(name=health_check.name)

    def _load_health_state(self):
        """Load health state from persistent storage"""
        try:
            if self.health_file.exists():
                with open(self.health_file, 'r') as f:
                    data = json.load(f)

                    for service_name, service_data in data.get('services', {}).items():
                        if service_name in self.services:
                            service = self.services[service_name]
                            service.status = HealthStatus(service_data.get('status', 'unknown'))
                            service.consecutive_failures = service_data.get('consecutive_failures', 0)
                            service.consecutive_successes = service_data.get('consecutive_successes', 0)
                            service.total_checks = service_data.get('total_checks', 0)
                            service.successful_checks = service_data.get('successful_checks', 0)

                            if service_data.get('last_check'):
                                service.last_check = datetime.fromisoformat(service_data['last_check'])

        except Exception as e:
            self.logger.warning(f"Failed to load health state: {e}")

    def _save_health_state(self):
        """Save health state to persistent storage"""
        try:
            data = {
                'last_updated': datetime.now().isoformat(),
                'services': {}
            }

            for service_name, service in self.services.items():
                data['services'][service_name] = {
                    'status': service.status.value,
                    'consecutive_failures': service.consecutive_failures,
                    'consecutive_successes': service.consecutive_successes,
                    'total_checks': service.total_checks,
                    'successful_checks': service.successful_checks,
                    'last_check': service.last_check.isoformat() if service.last_check else None,
                    'last_error': service.last_error,
                    'response_time': service.response_time,
                    'metadata': service.metadata
                }

            with open(self.health_file, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            self.logger.warning(f"Failed to save health state: {e}")

    # Health check implementations
    def _check_system_resources(self) -> bool:
        """Check system resource utilization"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            # Define critical thresholds
            cpu_critical = 95.0
            memory_critical = 95.0
            disk_critical = 95.0

            if cpu_percent > cpu_critical:
                self.services['system_resources'].last_error = f"Critical CPU usage: {cpu_percent:.1f}%"
                return False

            if memory.percent > memory_critical:
                self.services['system_resources'].last_error = f"Critical memory usage: {memory.percent:.1f}%"
                return False

            if disk.percent > disk_critical:
                self.services['system_resources'].last_error = f"Critical disk usage: {disk.percent:.1f}%"
                return False

            # Store metadata
            self.services['system_resources'].metadata = {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'disk_percent': disk.percent
            }

            return True

        except Exception as e:
            self.services['system_resources'].last_error = f"Resource check failed: {e}"
            return False

    def _check_database_connectivity(self) -> bool:
        """Check database connectivity and basic operations"""
        try:
            # Test main database
            db_path = self.base_path / "atlas.db"
            if not db_path.exists():
                db_path = self.base_path / "data" / "atlas.db"

            if not db_path.exists():
                self.services['database_connectivity'].last_error = "Database file not found"
                return False

            # Test connection and basic query
            start_time = time.time()
            with sqlite3.connect(str(db_path), timeout=10) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                table_count = cursor.fetchone()[0]

                # Test write capability
                cursor.execute("CREATE TEMP TABLE health_test (id INTEGER)")
                cursor.execute("DROP TABLE health_test")

            response_time = time.time() - start_time
            self.services['database_connectivity'].response_time = response_time
            self.services['database_connectivity'].metadata = {
                'table_count': table_count,
                'response_time': response_time
            }

            return True

        except Exception as e:
            self.services['database_connectivity'].last_error = f"Database check failed: {e}"
            return False

    def _check_disk_space(self) -> bool:
        """Check disk space availability"""
        try:
            disk_usage = psutil.disk_usage('/')
            free_gb = disk_usage.free / (1024**3)

            # Critical threshold: less than 1GB free
            if free_gb < 1.0:
                self.services['disk_space'].last_error = f"Critical disk space: {free_gb:.2f}GB free"
                return False

            # Warning threshold: less than 5GB free
            if free_gb < 5.0:
                self.services['disk_space'].last_error = f"Low disk space: {free_gb:.2f}GB free"
                # Still return True but log warning
                self.logger.warning(self.services['disk_space'].last_error)

            self.services['disk_space'].metadata = {
                'free_gb': free_gb,
                'total_gb': disk_usage.total / (1024**3),
                'percent_used': (disk_usage.used / disk_usage.total) * 100
            }

            return True

        except Exception as e:
            self.services['disk_space'].last_error = f"Disk space check failed: {e}"
            return False

    def _check_atlas_api(self) -> bool:
        """Check Atlas API availability"""
        try:
            # Check if API server is running on expected port
            api_ports = [8000, 8080, 5000]  # Common Atlas API ports
            api_available = False

            for port in api_ports:
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                        sock.settimeout(5)
                        result = sock.connect_ex(('localhost', port))
                        if result == 0:
                            api_available = True
                            self.services['atlas_api'].metadata = {'port': port}
                            break
                except Exception:
                    continue

            if not api_available:
                self.services['atlas_api'].last_error = "Atlas API not responding on expected ports"
                return False

            return True

        except Exception as e:
            self.services['atlas_api'].last_error = f"API check failed: {e}"
            return False

    def _check_background_processing(self) -> bool:
        """Check background processing services"""
        try:
            # Look for Atlas background processes
            atlas_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if 'atlas' in cmdline.lower() and any(keyword in cmdline.lower() for keyword in [
                        'background', 'service', 'comprehensive', 'scheduler'
                    ]):
                        atlas_processes.append({
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'cmdline': cmdline[:100]  # Truncate for storage
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if not atlas_processes:
                self.services['background_processing'].last_error = "No Atlas background processes detected"
                return False

            self.services['background_processing'].metadata = {
                'process_count': len(atlas_processes),
                'processes': atlas_processes[:3]  # Store up to 3 processes
            }

            return True

        except Exception as e:
            self.services['background_processing'].last_error = f"Background processing check failed: {e}"
            return False

    def _check_search_functionality(self) -> bool:
        """Check search index and functionality"""
        try:
            # Check if search database exists and has content
            search_db_paths = [
                self.base_path / "data" / "enhanced_search.db",
                self.base_path / "enhanced_search.db"
            ]

            search_db = None
            for path in search_db_paths:
                if path.exists():
                    search_db = path
                    break

            if not search_db:
                self.services['search_functionality'].last_error = "Search database not found"
                return False

            # Test search database
            with sqlite3.connect(str(search_db)) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name LIKE '%search%'")
                search_tables = cursor.fetchone()[0]

                if search_tables == 0:
                    self.services['search_functionality'].last_error = "No search tables found"
                    return False

                # Try to get search record count
                try:
                    cursor.execute("SELECT COUNT(*) FROM search_index")
                    record_count = cursor.fetchone()[0]
                except sqlite3.OperationalError:
                    record_count = 0

                self.services['search_functionality'].metadata = {
                    'search_tables': search_tables,
                    'indexed_records': record_count
                }

            return True

        except Exception as e:
            self.services['search_functionality'].last_error = f"Search check failed: {e}"
            return False

    def _check_content_pipeline(self) -> bool:
        """Check content processing pipeline health"""
        try:
            # Check output directory for recent content
            output_dir = self.base_path / "output"
            if not output_dir.exists():
                self.services['content_pipeline'].last_error = "Output directory not found"
                return False

            # Count files and check for recent activity
            recent_cutoff = datetime.now() - timedelta(hours=24)
            total_files = 0
            recent_files = 0

            for file_path in output_dir.glob("*.md"):
                total_files += 1
                try:
                    file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_mtime > recent_cutoff:
                        recent_files += 1
                except OSError:
                    continue

            if total_files == 0:
                self.services['content_pipeline'].last_error = "No processed content found"
                return False

            self.services['content_pipeline'].metadata = {
                'total_content_files': total_files,
                'recent_files_24h': recent_files,
                'last_check_time': datetime.now().isoformat()
            }

            # Consider pipeline healthy if we have content, even if not recent
            return True

        except Exception as e:
            self.services['content_pipeline'].last_error = f"Content pipeline check failed: {e}"
            return False

    def perform_health_check(self, service_name: str) -> bool:
        """Perform health check for specific service"""
        if service_name not in self.health_checks:
            self.logger.warning(f"No health check defined for service: {service_name}")
            return False

        health_check = self.health_checks[service_name]
        service = self.services[service_name]

        try:
            start_time = time.time()

            # Execute health check with timeout
            success = health_check.check_function()

            response_time = time.time() - start_time
            service.response_time = response_time
            service.last_check = datetime.now()
            service.total_checks += 1

            if success:
                service.consecutive_failures = 0
                service.consecutive_successes += 1
                service.successful_checks += 1
                service.last_error = None

                # Update status
                if service.status in [HealthStatus.DOWN, HealthStatus.CRITICAL]:
                    service.status = HealthStatus.HEALTHY
                    self.logger.info(f"Service {service_name} recovered to HEALTHY")
                elif service.status == HealthStatus.UNKNOWN:
                    service.status = HealthStatus.HEALTHY
            else:
                service.consecutive_successes = 0
                service.consecutive_failures += 1

                # Update status based on failure count and criticality
                old_status = service.status

                if service.consecutive_failures >= health_check.consecutive_failures_threshold:
                    if health_check.critical:
                        service.status = HealthStatus.CRITICAL
                    else:
                        service.status = HealthStatus.DEGRADED
                elif service.consecutive_failures >= 1:
                    if service.status in [HealthStatus.HEALTHY, HealthStatus.UNKNOWN]:
                        service.status = HealthStatus.DEGRADED

                if old_status != service.status:
                    self.logger.warning(f"Service {service_name} status changed: {old_status.value} -> {service.status.value}")

                # Send alert for critical services or status changes
                if health_check.critical or old_status != service.status:
                    self._send_health_alert(service_name, service)

            self._save_health_state()
            return success

        except Exception as e:
            self.logger.error(f"Health check for {service_name} failed with exception: {e}")
            service.last_error = f"Check exception: {e}"
            service.consecutive_failures += 1
            service.status = HealthStatus.DOWN
            service.last_check = datetime.now()
            service.total_checks += 1

            self._send_health_alert(service_name, service)
            self._save_health_state()
            return False

    def _send_health_alert(self, service_name: str, service: ServiceHealth):
        """Send alert for service health issues"""
        severity = "CRITICAL" if service.status == HealthStatus.CRITICAL else "WARNING"

        alert = {
            'timestamp': datetime.now().isoformat(),
            'metric_name': f'service_health_{service_name}',
            'value': service.consecutive_failures,
            'threshold': self.health_checks[service_name].consecutive_failures_threshold,
            'severity': severity,
            'message': f"Service {service_name} is {service.status.value.upper()}: {service.last_error or 'Health check failed'}"
        }

        try:
            self.alert_manager.process_alert(alert)
        except Exception as e:
            self.logger.error(f"Failed to send health alert: {e}")

    def run_all_health_checks(self) -> Dict[str, bool]:
        """Run all configured health checks"""
        results = {}
        for service_name in self.health_checks:
            results[service_name] = self.perform_health_check(service_name)
        return results

    def get_system_health_summary(self) -> Dict[str, Any]:
        """Get comprehensive system health summary"""
        current_time = datetime.now()

        summary = {
            'timestamp': current_time.isoformat(),
            'overall_status': HealthStatus.HEALTHY.value,
            'services': {},
            'statistics': {
                'total_services': len(self.services),
                'healthy': 0,
                'degraded': 0,
                'critical': 0,
                'down': 0,
                'unknown': 0
            },
            'alerts': []
        }

        overall_status_priority = {
            HealthStatus.HEALTHY: 0,
            HealthStatus.UNKNOWN: 1,
            HealthStatus.DEGRADED: 2,
            HealthStatus.CRITICAL: 3,
            HealthStatus.DOWN: 4
        }

        overall_status = HealthStatus.HEALTHY

        for service_name, service in self.services.items():
            # Calculate uptime percentage
            uptime_percentage = 0.0
            if service.total_checks > 0:
                uptime_percentage = (service.successful_checks / service.total_checks) * 100

            service_info = {
                'status': service.status.value,
                'last_check': service.last_check.isoformat() if service.last_check else None,
                'consecutive_failures': service.consecutive_failures,
                'uptime_percentage': round(uptime_percentage, 2),
                'response_time': service.response_time,
                'last_error': service.last_error,
                'metadata': service.metadata
            }

            summary['services'][service_name] = service_info
            summary['statistics'][service.status.value] += 1

            # Update overall status
            if overall_status_priority[service.status] > overall_status_priority[overall_status]:
                overall_status = service.status

            # Add to alerts if problematic
            if service.status in [HealthStatus.CRITICAL, HealthStatus.DOWN]:
                summary['alerts'].append({
                    'service': service_name,
                    'status': service.status.value,
                    'message': service.last_error or f"Service is {service.status.value}"
                })

        summary['overall_status'] = overall_status.value
        return summary

    def start_continuous_monitoring(self):
        """Start continuous health monitoring in background"""
        if self.monitoring_active:
            self.logger.warning("Continuous monitoring already active")
            return

        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        self.logger.info("Started continuous health monitoring")

    def stop_continuous_monitoring(self):
        """Stop continuous health monitoring"""
        self.monitoring_active = False
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=5)
        self.logger.info("Stopped continuous health monitoring")

    def _monitoring_loop(self):
        """Background monitoring loop"""
        while self.monitoring_active:
            try:
                # Run health checks based on their intervals
                current_time = datetime.now()

                for service_name, health_check in self.health_checks.items():
                    service = self.services[service_name]

                    # Check if it's time for this health check
                    if (service.last_check is None or
                        (current_time - service.last_check).total_seconds() >= health_check.interval):

                        self.perform_health_check(service_name)

                # Sleep for monitoring interval
                time.sleep(self.monitoring_interval)

            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(60)  # Wait a bit before retrying