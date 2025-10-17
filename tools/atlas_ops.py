#!/usr/bin/env python3
"""
Atlas Operations Management Tool

Comprehensive operational tooling for managing Atlas in production environments.
Provides monitoring, deployment, backup, recovery, and maintenance capabilities.
"""

import os
import sys
import json
import time
import signal
import socket
import psutil
import requests
import argparse
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.configuration_manager import ConfigurationManager, Environment
from helpers.secret_manager import SecretManager
from helpers.monitoring_dashboard_service import MonitoringService


@dataclass
class SystemHealth:
    """System health status."""
    overall_status: str
    services: Dict[str, str]
    database: Dict[str, Any]
    resources: Dict[str, float]
    timestamp: datetime


@dataclass
class ServiceStatus:
    """Individual service status."""
    name: str
    status: str
    pid: Optional[int]
    port: Optional[int]
    memory_usage: float
    cpu_usage: float
    uptime: Optional[timedelta]
    last_check: datetime


class AtlasOperations:
    """Main operations management class."""

    def __init__(self, config_dir: str = "config", secrets_dir: str = "config"):
        """Initialize operations manager."""
        self.config_dir = Path(config_dir)
        self.secrets_dir = Path(secrets_dir)
        self.environment = os.getenv("ATLAS_ENVIRONMENT", "development")

        # Initialize managers
        self.config_manager = ConfigurationManager(
            environment=Environment(self.environment),
            config_dir=str(config_dir),
            secrets_dir=str(secrets_dir)
        )
        self.secret_manager = SecretManager(
            secrets_dir=str(secrets_dir),
            environment=self.environment
        )

        # Service definitions
        self.services = {
            "atlas-api": {
                "description": "Atlas API Server",
                "port": 7444,
                "health_endpoint": "/health",
                "systemd_service": "atlas-api.service"
            },
            "atlas-monitoring": {
                "description": "Monitoring Dashboard",
                "port": 8081,
                "health_endpoint": "/health",
                "systemd_service": "atlas-monitoring-dashboard.service"
            },
            "atlas-scheduler": {
                "description": "Task Scheduler",
                "port": None,
                "health_endpoint": None,
                "systemd_service": "atlas-scheduler.service"
            }
        }

    def check_system_health(self) -> SystemHealth:
        """Check overall system health."""
        services_status = {}
        overall_healthy = True

        # Check each service
        for service_name, service_config in self.services.items():
            status = self.check_service_status(service_name)
            services_status[service_name] = status.status
            if status.status != "healthy":
                overall_healthy = False

        # Check database
        db_status = self.check_database_health()

        # Check system resources
        resources = self.get_system_resources()

        overall_status = "healthy" if overall_healthy else "degraded"

        return SystemHealth(
            overall_status=overall_status,
            services=services_status,
            database=db_status,
            resources=resources,
            timestamp=datetime.now()
        )

    def check_service_status(self, service_name: str) -> ServiceStatus:
        """Check status of a specific service."""
        if service_name not in self.services:
            raise ValueError(f"Unknown service: {service_name}")

        service_config = self.services[service_name]
        status = "unknown"
        pid = None
        port = service_config["port"]
        memory_usage = 0.0
        cpu_usage = 0.0
        uptime = None

        try:
            # Check systemd service
            result = subprocess.run(
                ["systemctl", "is-active", service_config["systemd_service"]],
                capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0:
                status = "running"

                # Get PID from systemd
                pid_result = subprocess.run(
                    ["systemctl", "show", service_config["systemd_service"], "--property=MainPID"],
                    capture_output=True, text=True
                )
                if pid_result.returncode == 0:
                    pid_line = pid_result.stdout.strip()
                    if "=" in pid_line:
                        pid = int(pid_line.split("=")[1])
                        if pid > 0:
                            # Get process info
                            try:
                                process = psutil.Process(pid)
                                memory_usage = process.memory_info().rss / 1024 / 1024  # MB
                                cpu_usage = process.cpu_percent()
                                uptime = datetime.now() - datetime.fromtimestamp(process.create_time())
                            except psutil.NoSuchProcess:
                                pass

                # Check health endpoint if available
                if service_config["health_endpoint"] and port:
                    try:
                        response = requests.get(
                            f"http://localhost:{port}{service_config['health_endpoint']}",
                            timeout=5
                        )
                        if response.status_code == 200:
                            status = "healthy"
                        else:
                            status = "degraded"
                    except Exception:
                        status = "running"  # Service is running but health check failed
            else:
                status = "stopped"

        except Exception as e:
            status = f"error: {str(e)}"

        return ServiceStatus(
            name=service_name,
            status=status,
            pid=pid,
            port=port,
            memory_usage=memory_usage,
            cpu_usage=cpu_usage,
            uptime=uptime,
            last_check=datetime.now()
        )

    def check_database_health(self) -> Dict[str, Any]:
        """Check database health."""
        try:
            import sqlite3

            db_path = self.config_manager.get("ATLAS_DATABASE_PATH")
            if not db_path:
                return {"status": "missing_config", "size_mb": 0, "table_count": 0}

            db_file = Path(db_path)
            if not db_file.exists():
                return {"status": "missing", "size_mb": 0, "table_count": 0}

            # Connect and check
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Get database info
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            table_count = len(tables)

            # Get database size
            size_mb = db_file.stat().st_size / 1024 / 1024

            # Check if we can query
            cursor.execute("SELECT COUNT(*) FROM content")
            content_count = cursor.fetchone()[0]

            conn.close()

            return {
                "status": "healthy",
                "size_mb": round(size_mb, 2),
                "table_count": table_count,
                "content_count": content_count,
                "path": str(db_file)
            }

        except Exception as e:
            return {"status": f"error: {str(e)}", "size_mb": 0, "table_count": 0}

    def get_system_resources(self) -> Dict[str, float]:
        """Get system resource usage."""
        return {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "load_avg_1": os.getloadavg()[0] if hasattr(os, 'getloadavg') else 0.0
        }

    def start_service(self, service_name: str) -> bool:
        """Start a service."""
        if service_name not in self.services:
            raise ValueError(f"Unknown service: {service_name}")

        try:
            result = subprocess.run(
                ["sudo", "systemctl", "start", self.services[service_name]["systemd_service"]],
                capture_output=True, text=True
            )
            return result.returncode == 0
        except Exception:
            return False

    def stop_service(self, service_name: str) -> bool:
        """Stop a service."""
        if service_name not in self.services:
            raise ValueError(f"Unknown service: {service_name}")

        try:
            result = subprocess.run(
                ["sudo", "systemctl", "stop", self.services[service_name]["systemd_service"]],
                capture_output=True, text=True
            )
            return result.returncode == 0
        except Exception:
            return False

    def restart_service(self, service_name: str) -> bool:
        """Restart a service."""
        if service_name not in self.services:
            raise ValueError(f"Unknown service: {service_name}")

        try:
            result = subprocess.run(
                ["sudo", "systemctl", "restart", self.services[service_name]["systemd_service"]],
                capture_output=True, text=True
            )
            return result.returncode == 0
        except Exception:
            return False

    def reload_service(self, service_name: str) -> bool:
        """Reload a service configuration."""
        if service_name not in self.services:
            raise ValueError(f"Unknown service: {service_name}")

        try:
            result = subprocess.run(
                ["sudo", "systemctl", "reload", self.services[service_name]["systemd_service"]],
                capture_output=True, text=True
            )
            return result.returncode == 0
        except Exception:
            return False

    def backup_database(self, backup_path: Optional[str] = None) -> str:
        """Create database backup."""
        if not backup_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"backups/atlas_backup_{timestamp}.db"

        backup_path = Path(backup_path)
        backup_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            db_path = self.config_manager.get("ATLAS_DATABASE_PATH")
            if not db_path:
                raise ValueError("Database path not configured")

            # Copy database file
            import shutil
            shutil.copy2(db_path, backup_path)

            # Compress backup
            compressed_path = backup_path.with_suffix('.db.gz')
            subprocess.run(["gzip", str(backup_path)], check=True)

            return str(compressed_path)

        except Exception as e:
            raise RuntimeError(f"Backup failed: {e}")

    def restore_database(self, backup_file: str, verify: bool = True) -> bool:
        """Restore database from backup."""
        try:
            backup_path = Path(backup_file)
            if not backup_path.exists():
                raise FileNotFoundError(f"Backup file not found: {backup_file}")

            # Decompress if needed
            if backup_path.suffix == '.gz':
                decompressed_path = backup_path.with_suffix('')
                subprocess.run(["gunzip", "-f", str(backup_path)], check=True)
                backup_path = decompressed_path

            # Get current database path
            db_path = self.config_manager.get("ATLAS_DATABASE_PATH")
            if not db_path:
                raise ValueError("Database path not configured")

            # Stop services first
            self.stop_service("atlas-api")
            self.stop_service("atlas-scheduler")

            # Create backup of current database
            current_backup = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            if Path(db_path).exists():
                import shutil
                shutil.copy2(db_path, current_backup)

            # Restore database
            import shutil
            shutil.copy2(backup_path, db_path)

            # Verify restoration
            if verify:
                result = self.check_database_health()
                if result["status"] != "healthy":
                    # Restore backup
                    if Path(current_backup).exists():
                        shutil.copy2(current_backup, db_path)
                    raise RuntimeError("Database verification failed")

            # Start services
            self.start_service("atlas-api")
            self.start_service("atlas-scheduler")

            return True

        except Exception as e:
            # Try to restart services
            try:
                self.start_service("atlas-api")
                self.start_service("atlas-scheduler")
            except:
                pass
            raise RuntimeError(f"Restore failed: {e}")

    def cleanup_old_backups(self, retention_days: int = 30) -> List[str]:
        """Clean up old backup files."""
        backups_dir = Path("backups")
        if not backups_dir.exists():
            return []

        cutoff_date = datetime.now() - timedelta(days=retention_days)
        removed_files = []

        for backup_file in backups_dir.glob("atlas_backup_*.db*"):
            if backup_file.stat().st_mtime < cutoff_date.timestamp():
                backup_file.unlink()
                removed_files.append(str(backup_file))

        return removed_files

    def rotate_logs(self, max_size_mb: int = 100, max_files: int = 5) -> None:
        """Rotate log files."""
        logs_dir = Path("logs")
        if not logs_dir.exists():
            return

        for log_file in logs_dir.glob("*.log"):
            if log_file.stat().st_size > max_size_mb * 1024 * 1024:
                # Rotate log file
                for i in range(max_files - 1, 0, -1):
                    old_log = log_file.with_name(f"{log_file.stem}.{i}{log_file.suffix}")
                    new_log = log_file.with_name(f"{log_file.stem}.{i + 1}{log_file.suffix}")
                    if old_log.exists():
                        old_log.rename(new_log)

                # Move current log to .1
                log_file.rename(log_file.with_name(f"{log_file.stem}.1{log_file.suffix}"))

    def get_service_logs(self, service_name: str, lines: int = 100) -> str:
        """Get recent service logs."""
        if service_name not in self.services:
            raise ValueError(f"Unknown service: {service_name}")

        try:
            result = subprocess.run(
                ["journalctl", "-u", self.services[service_name]["systemd_service"],
                 "-n", str(lines), "--no-pager"],
                capture_output=True, text=True
            )
            return result.stdout
        except Exception as e:
            return f"Error getting logs: {e}"

    def monitor_system(self, interval: int = 60, duration: int = 3600) -> None:
        """Monitor system continuously."""
        print(f"📊 Starting system monitoring (interval: {interval}s, duration: {duration}s)")

        start_time = time.time()
        while time.time() - start_time < duration:
            health = self.check_system_health()

            # Clear screen and display status
            os.system('clear')
            print(f"📊 Atlas System Health - {health.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 60)

            # Overall status
            status_icon = "✅" if health.overall_status == "healthy" else "⚠️"
            print(f"{status_icon} Overall Status: {health.overall_status.upper()}")
            print()

            # Services
            print("🔧 Services:")
            for service, status in health.services.items():
                icon = "✅" if status == "healthy" else "⚠️" if status == "degraded" else "❌"
                print(f"  {icon} {service}: {status}")
            print()

            # Database
            db_icon = "✅" if health.database["status"] == "healthy" else "❌"
            print(f"💾 Database: {db_icon} {health.database['status']}")
            print(f"   Size: {health.database['size_mb']} MB")
            print(f"   Tables: {health.database['table_count']}")
            print()

            # Resources
            print("🖥️  System Resources:")
            print(f"   CPU: {health.resources['cpu_percent']:.1f}%")
            print(f"   Memory: {health.resources['memory_percent']:.1f}%")
            print(f"   Disk: {health.resources['disk_percent']:.1f}%")
            print(f"   Load: {health.resources['load_avg_1']:.2f}")
            print()

            # Wait for next interval
            time.sleep(interval)

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive system report."""
        health = self.check_system_health()

        report = {
            "timestamp": health.timestamp.isoformat(),
            "environment": self.environment,
            "overall_health": health.overall_status,
            "services": {},
            "database": health.database,
            "resources": health.resources,
            "configuration": {}
        }

        # Add service details
        for service_name in self.services:
            service_status = self.check_service_status(service_name)
            report["services"][service_name] = asdict(service_status)

        # Add configuration summary
        important_configs = [
            "ATLAS_ENVIRONMENT", "API_PORT", "MAX_CONCURRENT_ARTICLES",
            "BACKUP_ENABLED", "MONITORING_ENABLED", "YOUTUBE_ENABLED"
        ]

        for config_key in important_configs:
            value = self.config_manager.get(config_key)
            if value:
                report["configuration"][config_key] = value

        return report

    def deployment_readiness_check(self) -> Dict[str, Any]:
        """Check if system is ready for deployment."""
        checks = {
            "configuration_valid": True,
            "secrets_available": True,
            "services_running": True,
            "database_healthy": True,
            "resources_adequate": True,
            "backups_configured": True
        }

        issues = []

        # Check configuration
        try:
            errors = self.config_manager.validate_configuration()
            if errors:
                checks["configuration_valid"] = False
                issues.extend([f"Configuration error: {error}" for error in errors])
        except Exception as e:
            checks["configuration_valid"] = False
            issues.append(f"Configuration validation failed: {e}")

        # Check critical secrets
        critical_secrets = ["OPENROUTER_API_KEY", "ATLAS_ENCRYPTION_KEY"]
        for secret in critical_secrets:
            if not self.secret_manager.get_secret(secret):
                checks["secrets_available"] = False
                issues.append(f"Missing critical secret: {secret}")

        # Check services
        health = self.check_system_health()
        if health.overall_status != "healthy":
            checks["services_running"] = False
            for service, status in health.services.items():
                if status != "healthy":
                    issues.append(f"Service {service} is {status}")

        # Check database
        if health.database["status"] != "healthy":
            checks["database_healthy"] = False
            issues.append(f"Database issue: {health.database['status']}")

        # Check resources
        if health.resources["disk_percent"] > 90:
            checks["resources_adequate"] = False
            issues.append(f"High disk usage: {health.resources['disk_percent']}%")

        if health.resources["memory_percent"] > 90:
            checks["resources_adequate"] = False
            issues.append(f"High memory usage: {health.resources['memory_percent']}%")

        # Check backup configuration
        if not self.config_manager.get("BACKUP_ENABLED", False):
            checks["backups_configured"] = False
            issues.append("Backups are not enabled")

        return {
            "ready": all(checks.values()),
            "checks": checks,
            "issues": issues,
            "timestamp": datetime.now().isoformat()
        }


def create_parser():
    """Create command line parser."""
    parser = argparse.ArgumentParser(
        description="Atlas Operations Management Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check system health
  atlas-ops health

  # Start a service
  atlas-ops start atlas-api

  # Create database backup
  atlas-ops backup

  # Monitor system continuously
  atlas-ops monitor

  # Generate deployment readiness report
  atlas-ops readiness
        """
    )

    parser.add_argument("--config-dir", default="config", help="Configuration directory")
    parser.add_argument("--secrets-dir", default="config", help="Secrets directory")
    parser.add_argument("--env", help="Environment (default: ATLAS_ENVIRONMENT)")

    subparsers = parser.add_subparsers(dest="command", help="Command")

    # Health check
    subparsers.add_parser("health", help="Check system health")

    # Service management
    start_parser = subparsers.add_parser("start", help="Start service")
    start_parser.add_argument("service", choices=["atlas-api", "atlas-monitoring", "atlas-scheduler"])

    stop_parser = subparsers.add_parser("stop", help="Stop service")
    stop_parser.add_argument("service", choices=["atlas-api", "atlas-monitoring", "atlas-scheduler"])

    restart_parser = subparsers.add_parser("restart", help="Restart service")
    restart_parser.add_argument("service", choices=["atlas-api", "atlas-monitoring", "atlas-scheduler"])

    # Backup and restore
    backup_parser = subparsers.add_parser("backup", help="Create database backup")
    backup_parser.add_argument("--output", help="Backup output path")

    restore_parser = subparsers.add_parser("restore", help="Restore database from backup")
    restore_parser.add_argument("backup_file", help="Backup file to restore")
    restore_parser.add_argument("--no-verify", action="store_true", help="Skip verification")

    # Monitoring
    monitor_parser = subparsers.add_parser("monitor", help="Monitor system continuously")
    monitor_parser.add_argument("--interval", type=int, default=60, help="Monitoring interval in seconds")
    monitor_parser.add_argument("--duration", type=int, default=3600, help="Monitoring duration in seconds")

    # Logs
    logs_parser = subparsers.add_parser("logs", help="Get service logs")
    logs_parser.add_argument("service", choices=["atlas-api", "atlas-monitoring", "atlas-scheduler"])
    logs_parser.add_argument("--lines", type=int, default=100, help="Number of lines to show")

    # Maintenance
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up old backups")
    cleanup_parser.add_argument("--retention-days", type=int, default=30, help="Retention period in days")

    subparsers.add_parser("rotate-logs", help="Rotate log files")

    # Reports
    subparsers.add_parser("report", help="Generate system report")

    readiness_parser = subparsers.add_parser("readiness", help="Check deployment readiness")

    return parser


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        # Initialize operations
        ops = AtlasOperations(args.config_dir, args.secrets_dir)

        if args.env:
            ops.environment = args.env

        # Execute command
        if args.command == "health":
            health = ops.check_system_health()
            print(json.dumps(asdict(health), indent=2))

        elif args.command == "start":
            success = ops.start_service(args.service)
            print(f"✅ Service {args.service} started successfully" if success else f"❌ Failed to start {args.service}")

        elif args.command == "stop":
            success = ops.stop_service(args.service)
            print(f"✅ Service {args.service} stopped successfully" if success else f"❌ Failed to stop {args.service}")

        elif args.command == "restart":
            success = ops.restart_service(args.service)
            print(f"✅ Service {args.service} restarted successfully" if success else f"❌ Failed to restart {args.service}")

        elif args.command == "backup":
            backup_path = ops.backup_database(args.output)
            print(f"✅ Database backup created: {backup_path}")

        elif args.command == "restore":
            success = ops.restore_database(args.backup_file, not args.no_verify)
            print(f"✅ Database restored successfully" if success else f"❌ Failed to restore database")

        elif args.command == "monitor":
            ops.monitor_system(args.interval, args.duration)

        elif args.command == "logs":
            logs = ops.get_service_logs(args.service, args.lines)
            print(logs)

        elif args.command == "cleanup":
            removed = ops.cleanup_old_backups(args.retention_days)
            print(f"✅ Cleaned up {len(removed)} old backup files")

        elif args.command == "rotate-logs":
            ops.rotate_logs()
            print("✅ Log files rotated")

        elif args.command == "report":
            report = ops.generate_report()
            print(json.dumps(report, indent=2))

        elif args.command == "readiness":
            readiness = ops.deployment_readiness_check()
            status = "✅ READY" if readiness["ready"] else "❌ NOT READY"
            print(f"{status} for deployment")
            if readiness["issues"]:
                print("\nIssues:")
                for issue in readiness["issues"]:
                    print(f"  • {issue}")

    except KeyboardInterrupt:
        print("\n👋 Operations interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()