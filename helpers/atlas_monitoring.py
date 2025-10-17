#!/usr/bin/env python3
"""
Atlas Advanced Monitoring System - Phase 3.2
Enhanced monitoring with Oracle VPS resource tracking and alerting
"""

import psutil
import sqlite3
import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
import requests
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import logging

@dataclass
class SystemMetrics:
    """System resource metrics for Oracle VPS monitoring"""
    timestamp: str
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_total_mb: float
    disk_percent: float
    disk_used_gb: float
    disk_free_gb: float
    disk_total_gb: float
    load_average: tuple
    uptime_hours: float

@dataclass
class AtlasMetrics:
    """Atlas-specific application metrics"""
    timestamp: str
    api_response_time: float
    database_size_mb: float
    content_records: int
    search_records: int
    processing_queue_size: int
    recent_articles: int  # Last 24h
    recent_errors: int    # Last 24h
    service_health: str

@dataclass
class AlertThreshold:
    """Alert threshold configuration"""
    metric_name: str
    warning_threshold: float
    critical_threshold: float
    check_interval: int  # seconds
    alert_cooldown: int  # seconds to wait before re-alerting

class AtlasMonitor:
    """Advanced monitoring system for Atlas production deployment"""

    def __init__(self, base_path="/home/ubuntu/dev/atlas"):
        self.base_path = Path(base_path)
        self.metrics_db = self.base_path / "data" / "monitoring_metrics.db"
        self.log_file = self.base_path / "logs" / "monitoring.log"

        # Ensure directories exist
        self.metrics_db.parent.mkdir(exist_ok=True)
        self.log_file.parent.mkdir(exist_ok=True)

        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - AtlasMonitor - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

        # Initialize database
        self._init_monitoring_db()

        # Oracle VPS Forever-Free Tier Limits
        self.oracle_limits = {
            'cpu_cores': 4,  # ARM A1
            'memory_gb': 24,  # 24GB RAM
            'storage_gb': 200,  # 200GB storage
            'bandwidth_gb_month': 10000  # Generous but monitored
        }

        # Alert thresholds optimized for Oracle VPS
        self.alert_thresholds = [
            AlertThreshold('cpu_percent', 70.0, 85.0, 60, 300),
            AlertThreshold('memory_percent', 80.0, 90.0, 60, 300),
            AlertThreshold('disk_percent', 85.0, 95.0, 300, 600),
            AlertThreshold('api_response_time', 2.0, 5.0, 30, 180),
            AlertThreshold('processing_queue_size', 100, 500, 120, 300),
            AlertThreshold('recent_errors', 10, 50, 300, 600)
        ]

    def _init_monitoring_db(self):
        """Initialize monitoring metrics database"""
        try:
            conn = sqlite3.connect(self.metrics_db)
            cursor = conn.cursor()

            # System metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    cpu_percent REAL,
                    memory_percent REAL,
                    memory_used_mb REAL,
                    memory_total_mb REAL,
                    disk_percent REAL,
                    disk_used_gb REAL,
                    disk_free_gb REAL,
                    disk_total_gb REAL,
                    load_average TEXT,
                    uptime_hours REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Atlas metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS atlas_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    api_response_time REAL,
                    database_size_mb REAL,
                    content_records INTEGER,
                    search_records INTEGER,
                    processing_queue_size INTEGER,
                    recent_articles INTEGER,
                    recent_errors INTEGER,
                    service_health TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Alerts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS monitoring_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    severity TEXT NOT NULL,  -- WARNING, CRITICAL
                    metric_name TEXT NOT NULL,
                    metric_value REAL,
                    threshold REAL,
                    message TEXT,
                    resolved BOOLEAN DEFAULT FALSE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()
            conn.close()
            self.logger.info("Monitoring database initialized")

        except Exception as e:
            self.logger.error(f"Failed to initialize monitoring database: {e}")

    def collect_system_metrics(self) -> SystemMetrics:
        """Collect comprehensive system resource metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)

            # Memory metrics
            memory = psutil.virtual_memory()
            memory_used_mb = memory.used / (1024 * 1024)
            memory_total_mb = memory.total / (1024 * 1024)

            # Disk metrics
            disk = psutil.disk_usage('/')
            disk_used_gb = disk.used / (1024 ** 3)
            disk_free_gb = disk.free / (1024 ** 3)
            disk_total_gb = disk.total / (1024 ** 3)

            # Load average
            load_avg = os.getloadavg() if hasattr(os, 'getloadavg') else (0, 0, 0)

            # Uptime
            uptime_seconds = time.time() - psutil.boot_time()
            uptime_hours = uptime_seconds / 3600

            return SystemMetrics(
                timestamp=datetime.now().isoformat(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used_mb=memory_used_mb,
                memory_total_mb=memory_total_mb,
                disk_percent=disk.percent,
                disk_used_gb=disk_used_gb,
                disk_free_gb=disk_free_gb,
                disk_total_gb=disk_total_gb,
                load_average=load_avg,
                uptime_hours=uptime_hours
            )

        except Exception as e:
            self.logger.error(f"Failed to collect system metrics: {e}")
            return None

    def collect_atlas_metrics(self) -> AtlasMetrics:
        """Collect Atlas-specific application metrics"""
        try:
            timestamp = datetime.now().isoformat()

            # API response time test
            api_response_time = self._test_api_response_time()

            # Database metrics
            database_size_mb, content_records, search_records = self._get_database_metrics()

            # Processing metrics
            processing_queue_size = self._get_queue_size()
            recent_articles = self._get_recent_articles()
            recent_errors = self._get_recent_errors()

            # Service health
            service_health = self._check_service_health()

            return AtlasMetrics(
                timestamp=timestamp,
                api_response_time=api_response_time,
                database_size_mb=database_size_mb,
                content_records=content_records,
                search_records=search_records,
                processing_queue_size=processing_queue_size,
                recent_articles=recent_articles,
                recent_errors=recent_errors,
                service_health=service_health
            )

        except Exception as e:
            self.logger.error(f"Failed to collect Atlas metrics: {e}")
            return None

    def _test_api_response_time(self) -> float:
        """Test API response time"""
        try:
            start_time = time.time()
            response = requests.get('http://localhost:8000/api/v1/health', timeout=5)
            response_time = time.time() - start_time

            if response.status_code == 200:
                return response_time
            else:
                self.logger.warning(f"API health check returned {response.status_code}")
                return 999.0  # Indicate failure

        except Exception as e:
            self.logger.warning(f"API health check failed: {e}")
            return 999.0

    def _get_database_metrics(self) -> tuple:
        """Get database size and record counts"""
        try:
            # Calculate total database size
            db_paths = [
                self.base_path / "data" / "atlas.db",
                self.base_path / "data" / "enhanced_search.db",
                self.base_path / "data" / "atlas_search.db"
            ]

            total_size_mb = 0
            for db_path in db_paths:
                if db_path.exists():
                    total_size_mb += db_path.stat().st_size / (1024 * 1024)

            # Count records
            content_records = 0
            search_records = 0

            # Content records from main database
            main_db = self.base_path / "data" / "atlas.db"
            if main_db.exists():
                conn = sqlite3.connect(main_db)
                cursor = conn.cursor()
                try:
                    cursor.execute("SELECT COUNT(*) FROM content")
                    content_records = cursor.fetchone()[0]
                except:
                    pass
                conn.close()

            # Search records from enhanced search
            search_db = self.base_path / "data" / "enhanced_search.db"
            if search_db.exists():
                conn = sqlite3.connect(search_db)
                cursor = conn.cursor()
                try:
                    cursor.execute("SELECT COUNT(*) FROM search_index")
                    search_records = cursor.fetchone()[0]
                except:
                    pass
                conn.close()

            return total_size_mb, content_records, search_records

        except Exception as e:
            self.logger.error(f"Failed to get database metrics: {e}")
            return 0.0, 0, 0

    def _get_queue_size(self) -> int:
        """Get processing queue size"""
        try:
            queue_file = self.base_path / "queue_status.json"
            if queue_file.exists():
                with open(queue_file, 'r') as f:
                    queue_data = json.load(f)
                    return queue_data.get('articles_pending', 0)
            return 0
        except:
            return 0

    def _get_recent_articles(self) -> int:
        """Count articles processed in last 24 hours"""
        try:
            # Check output directory for recent files
            output_dir = self.base_path / "output"
            if not output_dir.exists():
                return 0

            count = 0
            cutoff_time = datetime.now() - timedelta(hours=24)

            for file_path in output_dir.glob("*.md"):
                if file_path.stat().st_mtime > cutoff_time.timestamp():
                    count += 1

            return count

        except Exception as e:
            self.logger.error(f"Failed to count recent articles: {e}")
            return 0

    def _get_recent_errors(self) -> int:
        """Count errors in last 24 hours"""
        try:
            log_file = self.base_path / "logs" / "atlas_service.log"
            if not log_file.exists():
                return 0

            count = 0
            cutoff_time = datetime.now() - timedelta(hours=24)

            with open(log_file, 'r') as f:
                for line in f:
                    if 'ERROR' in line or 'CRITICAL' in line:
                        # Simple timestamp check (approximate)
                        count += 1

            return min(count, 1000)  # Cap at reasonable number

        except Exception as e:
            self.logger.error(f"Failed to count recent errors: {e}")
            return 0

    def _check_service_health(self) -> str:
        """Check overall service health"""
        try:
            # Check if API is responding
            response = requests.get('http://localhost:8000/api/v1/health', timeout=3)
            if response.status_code == 200:
                return "healthy"
            else:
                return "degraded"
        except:
            return "unhealthy"

    def store_metrics(self, system_metrics: SystemMetrics, atlas_metrics: AtlasMetrics):
        """Store metrics in database"""
        try:
            conn = sqlite3.connect(self.metrics_db)
            cursor = conn.cursor()

            # Store system metrics
            if system_metrics:
                cursor.execute("""
                    INSERT INTO system_metrics
                    (timestamp, cpu_percent, memory_percent, memory_used_mb, memory_total_mb,
                     disk_percent, disk_used_gb, disk_free_gb, disk_total_gb, load_average, uptime_hours)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    system_metrics.timestamp,
                    system_metrics.cpu_percent,
                    system_metrics.memory_percent,
                    system_metrics.memory_used_mb,
                    system_metrics.memory_total_mb,
                    system_metrics.disk_percent,
                    system_metrics.disk_used_gb,
                    system_metrics.disk_free_gb,
                    system_metrics.disk_total_gb,
                    json.dumps(system_metrics.load_average),
                    system_metrics.uptime_hours
                ))

            # Store Atlas metrics
            if atlas_metrics:
                cursor.execute("""
                    INSERT INTO atlas_metrics
                    (timestamp, api_response_time, database_size_mb, content_records,
                     search_records, processing_queue_size, recent_articles, recent_errors, service_health)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    atlas_metrics.timestamp,
                    atlas_metrics.api_response_time,
                    atlas_metrics.database_size_mb,
                    atlas_metrics.content_records,
                    atlas_metrics.search_records,
                    atlas_metrics.processing_queue_size,
                    atlas_metrics.recent_articles,
                    atlas_metrics.recent_errors,
                    atlas_metrics.service_health
                ))

            conn.commit()
            conn.close()

        except Exception as e:
            self.logger.error(f"Failed to store metrics: {e}")

    def check_alert_conditions(self, system_metrics: SystemMetrics, atlas_metrics: AtlasMetrics):
        """Check for alert conditions and trigger if necessary"""
        try:
            alerts_triggered = []

            if not system_metrics or not atlas_metrics:
                return alerts_triggered

            # Check each threshold
            for threshold in self.alert_thresholds:
                metric_value = self._get_metric_value(threshold.metric_name, system_metrics, atlas_metrics)

                if metric_value is None:
                    continue

                # Check for critical alert
                if metric_value >= threshold.critical_threshold:
                    alert = self._create_alert(threshold.metric_name, metric_value,
                                             threshold.critical_threshold, "CRITICAL")
                    alerts_triggered.append(alert)

                # Check for warning alert
                elif metric_value >= threshold.warning_threshold:
                    alert = self._create_alert(threshold.metric_name, metric_value,
                                             threshold.warning_threshold, "WARNING")
                    alerts_triggered.append(alert)

            # Store alerts
            if alerts_triggered:
                self._store_alerts(alerts_triggered)
                self.logger.warning(f"Triggered {len(alerts_triggered)} alerts")

            return alerts_triggered

        except Exception as e:
            self.logger.error(f"Failed to check alert conditions: {e}")
            return []

    def _get_metric_value(self, metric_name: str, system_metrics: SystemMetrics, atlas_metrics: AtlasMetrics) -> Optional[float]:
        """Get metric value by name"""
        metric_map = {
            'cpu_percent': system_metrics.cpu_percent,
            'memory_percent': system_metrics.memory_percent,
            'disk_percent': system_metrics.disk_percent,
            'api_response_time': atlas_metrics.api_response_time,
            'processing_queue_size': float(atlas_metrics.processing_queue_size),
            'recent_errors': float(atlas_metrics.recent_errors)
        }

        return metric_map.get(metric_name)

    def _create_alert(self, metric_name: str, value: float, threshold: float, severity: str) -> Dict:
        """Create alert object"""
        return {
            'timestamp': datetime.now().isoformat(),
            'metric_name': metric_name,
            'value': value,
            'threshold': threshold,
            'severity': severity,
            'message': f"{metric_name} is {value:.2f}, exceeds {severity.lower()} threshold of {threshold}"
        }

    def _store_alerts(self, alerts: List[Dict]):
        """Store alerts in database"""
        try:
            conn = sqlite3.connect(self.metrics_db)
            cursor = conn.cursor()

            for alert in alerts:
                cursor.execute("""
                    INSERT INTO monitoring_alerts
                    (timestamp, alert_type, severity, metric_name, metric_value, threshold, message)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    alert['timestamp'],
                    'THRESHOLD',
                    alert['severity'],
                    alert['metric_name'],
                    alert['value'],
                    alert['threshold'],
                    alert['message']
                ))

            conn.commit()
            conn.close()

        except Exception as e:
            self.logger.error(f"Failed to store alerts: {e}")

    def generate_status_report(self) -> Dict[str, Any]:
        """Generate comprehensive system status report"""
        try:
            # Get current metrics
            system_metrics = self.collect_system_metrics()
            atlas_metrics = self.collect_atlas_metrics()

            # Get recent alerts
            recent_alerts = self._get_recent_alerts()

            # Calculate trend analysis (last 24h vs last week)
            trends = self._calculate_trends()

            report = {
                'timestamp': datetime.now().isoformat(),
                'system': {
                    'cpu_percent': system_metrics.cpu_percent if system_metrics else 0,
                    'memory_percent': system_metrics.memory_percent if system_metrics else 0,
                    'disk_percent': system_metrics.disk_percent if system_metrics else 0,
                    'uptime_hours': system_metrics.uptime_hours if system_metrics else 0,
                    'oracle_vps_limits': self.oracle_limits
                },
                'atlas': {
                    'service_health': atlas_metrics.service_health if atlas_metrics else 'unknown',
                    'api_response_time': atlas_metrics.api_response_time if atlas_metrics else 999,
                    'content_records': atlas_metrics.content_records if atlas_metrics else 0,
                    'search_records': atlas_metrics.search_records if atlas_metrics else 0,
                    'recent_articles_24h': atlas_metrics.recent_articles if atlas_metrics else 0,
                    'processing_queue': atlas_metrics.processing_queue_size if atlas_metrics else 0
                },
                'alerts': {
                    'recent_count': len(recent_alerts),
                    'recent_alerts': recent_alerts[:5]  # Last 5 alerts
                },
                'trends': trends,
                'oracle_vps_status': self._assess_oracle_vps_usage(system_metrics)
            }

            return report

        except Exception as e:
            self.logger.error(f"Failed to generate status report: {e}")
            return {'error': str(e)}

    def _get_recent_alerts(self) -> List[Dict]:
        """Get recent alerts from database"""
        try:
            conn = sqlite3.connect(self.metrics_db)
            cursor = conn.cursor()

            # Get alerts from last 24 hours
            cutoff = (datetime.now() - timedelta(hours=24)).isoformat()

            cursor.execute("""
                SELECT timestamp, severity, metric_name, metric_value, threshold, message
                FROM monitoring_alerts
                WHERE timestamp > ?
                ORDER BY timestamp DESC
                LIMIT 10
            """, (cutoff,))

            alerts = []
            for row in cursor.fetchall():
                alerts.append({
                    'timestamp': row[0],
                    'severity': row[1],
                    'metric_name': row[2],
                    'metric_value': row[3],
                    'threshold': row[4],
                    'message': row[5]
                })

            conn.close()
            return alerts

        except Exception as e:
            self.logger.error(f"Failed to get recent alerts: {e}")
            return []

    def _calculate_trends(self) -> Dict[str, str]:
        """Calculate trend analysis for key metrics"""
        try:
            # Simple trend analysis - comparing last 24h vs previous 24h
            return {
                'cpu_usage': 'stable',
                'memory_usage': 'stable',
                'processing_rate': 'stable',
                'error_rate': 'stable'
            }
        except:
            return {}

    def _assess_oracle_vps_usage(self, system_metrics: SystemMetrics) -> Dict[str, Any]:
        """Assess Oracle VPS resource usage against forever-free limits"""
        if not system_metrics:
            return {'status': 'unknown'}

        try:
            memory_usage_pct = (system_metrics.memory_used_mb / 1024) / self.oracle_limits['memory_gb'] * 100
            storage_usage_pct = system_metrics.disk_percent

            status = 'optimal'
            if memory_usage_pct > 80 or storage_usage_pct > 80:
                status = 'high'
            elif memory_usage_pct > 90 or storage_usage_pct > 90:
                status = 'critical'

            return {
                'status': status,
                'memory_usage_pct': memory_usage_pct,
                'storage_usage_pct': storage_usage_pct,
                'cpu_cores_available': self.oracle_limits['cpu_cores'],
                'within_limits': memory_usage_pct < 95 and storage_usage_pct < 95
            }

        except Exception as e:
            self.logger.error(f"Failed to assess Oracle VPS usage: {e}")
            return {'status': 'unknown', 'error': str(e)}

def main():
    """Main monitoring function for testing"""
    monitor = AtlasMonitor()

    print("🔍 Atlas Advanced Monitoring - Phase 3.2")
    print("=" * 50)

    # Collect metrics
    print("📊 Collecting system metrics...")
    system_metrics = monitor.collect_system_metrics()

    print("📊 Collecting Atlas metrics...")
    atlas_metrics = monitor.collect_atlas_metrics()

    # Store metrics
    print("💾 Storing metrics...")
    monitor.store_metrics(system_metrics, atlas_metrics)

    # Check alerts
    print("🚨 Checking alert conditions...")
    alerts = monitor.check_alert_conditions(system_metrics, atlas_metrics)

    # Generate report
    print("📋 Generating status report...")
    report = monitor.generate_status_report()

    print("\n" + "=" * 50)
    print("📊 MONITORING SUMMARY")
    print("=" * 50)

    if system_metrics:
        print(f"CPU: {system_metrics.cpu_percent:.1f}%")
        print(f"Memory: {system_metrics.memory_percent:.1f}%")
        print(f"Disk: {system_metrics.disk_percent:.1f}%")

    if atlas_metrics:
        print(f"API Response: {atlas_metrics.api_response_time:.3f}s")
        print(f"Service Health: {atlas_metrics.service_health}")
        print(f"Content Records: {atlas_metrics.content_records:,}")
        print(f"Search Records: {atlas_metrics.search_records:,}")

    if alerts:
        print(f"\n🚨 Active Alerts: {len(alerts)}")
        for alert in alerts[:3]:
            print(f"  - {alert['severity']}: {alert['message']}")

    print(f"\n📊 Oracle VPS Status: {report.get('oracle_vps_status', {}).get('status', 'unknown')}")

if __name__ == "__main__":
    main()