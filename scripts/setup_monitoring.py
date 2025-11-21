#!/usr/bin/env python3
"""
Atlas Monitoring Setup - Task 4.1 Production Deployment & Infrastructure

Sets up comprehensive monitoring and alerting for Atlas production deployment.
Includes health checks, performance monitoring, and alert configurations.
"""

import json
import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
import time
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from helpers.config import load_config
from helpers.simple_database import SimpleDatabase


class AtlasMonitoringSetup:
    """Setup monitoring and alerting for Atlas production deployment."""

    def __init__(self):
        """Initialize monitoring setup."""
        self.config = load_config()
        self.setup_dir = Path("monitoring_setup")
        self.setup_dir.mkdir(exist_ok=True)

    def setup_health_checks(self) -> bool:
        """Setup comprehensive health check system."""
        print("🏥 Setting up health checks...")

        # Create health check script
        health_check_script = """#!/usr/bin/env python3
import requests
import sys
import json
from datetime import datetime

def check_api_health():
    try:
        response = requests.get('http://localhost:8000/api/v1/health', timeout=10)
        return response.status_code == 200
    except:
        return False

def check_database_health():
    try:
        from helpers.simple_database import SimpleDatabase
        db = SimpleDatabase()
        content = db.get_all_content()
        return True
    except:
        return False

def check_search_health():
    try:
        response = requests.get('http://localhost:8000/api/v1/search/?q=test&limit=1', timeout=10)
        return response.status_code == 200
    except:
        return False

def main():
    checks = {
        'api': check_api_health(),
        'database': check_database_health(),
        'search': check_search_health(),
        'timestamp': datetime.now().isoformat()
    }

    all_healthy = all(checks[k] for k in ['api', 'database', 'search'])

    print(json.dumps(checks, indent=2))
    sys.exit(0 if all_healthy else 1)

if __name__ == "__main__":
    main()
"""

        with open(self.setup_dir / "health_check.py", "w") as f:
            f.write(health_check_script)

        # Create systemd timer for health checks
        health_service = """[Unit]
Description=Atlas Health Check
After=network.target

[Service]
Type=oneshot
User=atlas
WorkingDirectory=/opt/atlas
ExecStart=/opt/atlas/venv/bin/python monitoring_setup/health_check.py
"""

        health_timer = """[Unit]
Description=Run Atlas Health Check every 5 minutes

[Timer]
OnBootSec=5min
OnUnitActiveSec=5min

[Install]
WantedBy=timers.target
"""

        with open(self.setup_dir / "atlas-health-check.service", "w") as f:
            f.write(health_service)

        with open(self.setup_dir / "atlas-health-check.timer", "w") as f:
            f.write(health_timer)

        print("✅ Health checks configured")
        return True

    def setup_performance_monitoring(self) -> bool:
        """Setup performance monitoring system."""
        print("📊 Setting up performance monitoring...")

        # Create performance monitor script
        perf_monitor_script = """#!/usr/bin/env python3
import psutil
import requests
import json
import sqlite3
from datetime import datetime
import os

def get_system_metrics():
    return {
        'cpu_percent': psutil.cpu_percent(interval=1),
        'memory_percent': psutil.virtual_memory().percent,
        'disk_percent': psutil.disk_usage('/').percent,
        'load_average': os.getloadavg()[0] if hasattr(os, 'getloadavg') else 0
    }

def get_atlas_metrics():
    try:
        # API response time
        start_time = time.time()
        response = requests.get('http://localhost:8000/api/v1/health', timeout=10)
        api_response_time = (time.time() - start_time) * 1000

        # Database metrics
        db_path = 'atlas.db'
        if os.path.exists(db_path):
            db_size = os.path.getsize(db_path) / (1024 * 1024)  # MB

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM content")
            content_count = cursor.fetchone()[0]
            conn.close()
        else:
            db_size = 0
            content_count = 0

        return {
            'api_response_time_ms': api_response_time,
            'database_size_mb': db_size,
            'content_count': content_count,
            'api_healthy': response.status_code == 200
        }
    except Exception as e:
        return {
            'api_response_time_ms': -1,
            'database_size_mb': 0,
            'content_count': 0,
            'api_healthy': False,
            'error': str(e)
        }

def main():
    metrics = {
        'timestamp': datetime.now().isoformat(),
        'system': get_system_metrics(),
        'atlas': get_atlas_metrics()
    }

    # Write to log file
    with open('logs/performance_metrics.log', 'a') as f:
        f.write(json.dumps(metrics) + '\\n')

    print(json.dumps(metrics, indent=2))

if __name__ == "__main__":
    import time
    main()
"""

        with open(self.setup_dir / "performance_monitor.py", "w") as f:
            f.write(perf_monitor_script)

        # Create performance monitoring service
        perf_service = """[Unit]
Description=Atlas Performance Monitoring
After=network.target

[Service]
Type=oneshot
User=atlas
WorkingDirectory=/opt/atlas
ExecStart=/opt/atlas/venv/bin/python monitoring_setup/performance_monitor.py
"""

        perf_timer = """[Unit]
Description=Run Atlas Performance Monitoring every 1 minute

[Timer]
OnBootSec=1min
OnUnitActiveSec=1min

[Install]
WantedBy=timers.target
"""

        with open(self.setup_dir / "atlas-performance.service", "w") as f:
            f.write(perf_service)

        with open(self.setup_dir / "atlas-performance.timer", "w") as f:
            f.write(perf_timer)

        print("✅ Performance monitoring configured")
        return True

    def setup_log_monitoring(self) -> bool:
        """Setup log monitoring and rotation."""
        print("📝 Setting up log monitoring...")

        # Create logrotate configuration
        logrotate_config = """/opt/atlas/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0644 atlas atlas
    postrotate
        systemctl reload atlas 2>/dev/null || true
    endscript
}
"""

        with open(self.setup_dir / "atlas-logrotate", "w") as f:
            f.write(logrotate_config)

        # Create log analyzer script
        log_analyzer_script = """#!/usr/bin/env python3
import re
import json
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import glob

def analyze_logs(hours=24):
    log_files = glob.glob('logs/*.log')

    errors = []
    warnings = []
    requests = []

    cutoff_time = datetime.now() - timedelta(hours=hours)

    for log_file in log_files:
        try:
            with open(log_file, 'r') as f:
                for line in f:
                    if 'ERROR' in line:
                        errors.append(line.strip())
                    elif 'WARNING' in line:
                        warnings.append(line.strip())
                    elif 'REQUEST' in line or 'GET' in line or 'POST' in line:
                        requests.append(line.strip())
        except Exception as e:
            continue

    analysis = {
        'timestamp': datetime.now().isoformat(),
        'period_hours': hours,
        'error_count': len(errors),
        'warning_count': len(warnings),
        'request_count': len(requests),
        'recent_errors': errors[-10:] if errors else [],
        'recent_warnings': warnings[-5:] if warnings else []
    }

    return analysis

def main():
    analysis = analyze_logs()

    # Write analysis to file
    with open('logs/log_analysis.json', 'w') as f:
        json.dump(analysis, f, indent=2)

    print(json.dumps(analysis, indent=2))

    # Alert if too many errors
    if analysis['error_count'] > 10:
        print(f"⚠️  HIGH ERROR COUNT: {analysis['error_count']} errors in last 24h")
        return 1

    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
"""

        with open(self.setup_dir / "log_analyzer.py", "w") as f:
            f.write(log_analyzer_script)

        print("✅ Log monitoring configured")
        return True

    def setup_alerting(self) -> bool:
        """Setup alerting system."""
        print("🚨 Setting up alerting system...")

        # Create alert manager script
        alert_script = """#!/usr/bin/env python3
import json
import subprocess
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os

class AlertManager:
    def __init__(self):
        self.email_config = {
            'smtp_server': os.getenv('SMTP_SERVER', 'localhost'),
            'smtp_port': int(os.getenv('SMTP_PORT', '587')),
            'smtp_user': os.getenv('SMTP_USER', ''),
            'smtp_password': os.getenv('SMTP_PASSWORD', ''),
            'alert_email': os.getenv('ALERT_EMAIL', 'admin@localhost')
        }

    def send_email_alert(self, subject, message):
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_config['smtp_user']
            msg['To'] = self.email_config['alert_email']
            msg['Subject'] = f"[ATLAS ALERT] {subject}"

            msg.attach(MIMEText(message, 'plain'))

            if self.email_config['smtp_user']:
                server = smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port'])
                server.starttls()
                server.login(self.email_config['smtp_user'], self.email_config['smtp_password'])
                server.send_message(msg)
                server.quit()
                return True
        except Exception as e:
            print(f"Failed to send email alert: {e}")
        return False

    def check_and_alert(self):
        alerts = []

        # Check health
        try:
            result = subprocess.run(['python3', 'monitoring_setup/health_check.py'],
                                  capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                alerts.append("System health check failed")
        except Exception:
            alerts.append("Health check script failed to run")

        # Check performance
        try:
            with open('logs/performance_metrics.log', 'r') as f:
                lines = f.readlines()
                if lines:
                    latest_metrics = json.loads(lines[-1])

                    if latest_metrics['system']['cpu_percent'] > 90:
                        alerts.append(f"High CPU usage: {latest_metrics['system']['cpu_percent']}%")

                    if latest_metrics['system']['memory_percent'] > 90:
                        alerts.append(f"High memory usage: {latest_metrics['system']['memory_percent']}%")

                    if latest_metrics['system']['disk_percent'] > 90:
                        alerts.append(f"High disk usage: {latest_metrics['system']['disk_percent']}%")

                    if latest_metrics['atlas']['api_response_time_ms'] > 5000:
                        alerts.append(f"Slow API response: {latest_metrics['atlas']['api_response_time_ms']}ms")
        except Exception as e:
            alerts.append(f"Failed to check performance metrics: {e}")

        # Send alerts
        if alerts:
            subject = f"Atlas System Alert - {len(alerts)} issues detected"
            message = f"Atlas monitoring detected the following issues:\\n\\n"
            message += "\\n".join([f"• {alert}" for alert in alerts])
            message += f"\\n\\nTime: {datetime.now().isoformat()}"
            message += f"\\nServer: {os.uname().nodename}"

            self.send_email_alert(subject, message)
            print(f"Sent alert for {len(alerts)} issues")
        else:
            print("All systems normal")

def main():
    alert_manager = AlertManager()
    alert_manager.check_and_alert()

if __name__ == "__main__":
    main()
"""

        with open(self.setup_dir / "alert_manager.py", "w") as f:
            f.write(alert_script)

        # Create alert service
        alert_service = """[Unit]
Description=Atlas Alert Manager
After=network.target

[Service]
Type=oneshot
User=atlas
WorkingDirectory=/opt/atlas
ExecStart=/opt/atlas/venv/bin/python monitoring_setup/alert_manager.py
"""

        alert_timer = """[Unit]
Description=Run Atlas Alert Manager every 15 minutes

[Timer]
OnBootSec=15min
OnUnitActiveSec=15min

[Install]
WantedBy=timers.target
"""

        with open(self.setup_dir / "atlas-alerts.service", "w") as f:
            f.write(alert_service)

        with open(self.setup_dir / "atlas-alerts.timer", "w") as f:
            f.write(alert_timer)

        print("✅ Alerting system configured")
        return True

    def generate_installation_script(self) -> bool:
        """Generate script to install all monitoring components."""
        print("📦 Generating installation script...")

        install_script = """#!/bin/bash
# Atlas Monitoring Installation Script

set -e

echo "🚀 Installing Atlas Monitoring System..."

# Create logs directory if it doesn't exist
mkdir -p logs

# Copy service files to systemd
if [ -w /etc/systemd/system ]; then
    echo "Installing systemd services..."
    sudo cp monitoring_setup/*.service /etc/systemd/system/
    sudo cp monitoring_setup/*.timer /etc/systemd/system/

    # Reload systemd
    sudo systemctl daemon-reload

    # Enable and start timers
    sudo systemctl enable atlas-health-check.timer
    sudo systemctl enable atlas-performance.timer
    sudo systemctl enable atlas-alerts.timer

    sudo systemctl start atlas-health-check.timer
    sudo systemctl start atlas-performance.timer
    sudo systemctl start atlas-alerts.timer

    echo "✅ Systemd timers installed and started"
else
    echo "⚠️  No systemd access - install services manually"
fi

# Install logrotate configuration
if [ -w /etc/logrotate.d ]; then
    sudo cp monitoring_setup/atlas-logrotate /etc/logrotate.d/
    echo "✅ Logrotate configuration installed"
fi

# Make scripts executable
chmod +x monitoring_setup/*.py

echo "🎉 Atlas Monitoring System installed successfully!"
echo ""
echo "Manual verification:"
echo "• Check health: python3 monitoring_setup/health_check.py"
echo "• Check performance: python3 monitoring_setup/performance_monitor.py"
echo "• Analyze logs: python3 monitoring_setup/log_analyzer.py"
echo "• Test alerts: python3 monitoring_setup/alert_manager.py"
echo ""
echo "Service status:"
echo "• sudo systemctl status atlas-health-check.timer"
echo "• sudo systemctl status atlas-performance.timer"
echo "• sudo systemctl status atlas-alerts.timer"
"""

        with open(self.setup_dir / "install_monitoring.sh", "w") as f:
            f.write(install_script)

        # Make installation script executable
        os.chmod(self.setup_dir / "install_monitoring.sh", 0o755)

        print("✅ Installation script generated")
        return True

    def run_setup(self) -> bool:
        """Run complete monitoring setup."""
        print("🔧 Setting up Atlas Monitoring System...")
        print("=" * 50)

        success = True

        try:
            success &= self.setup_health_checks()
            success &= self.setup_performance_monitoring()
            success &= self.setup_log_monitoring()
            success &= self.setup_alerting()
            success &= self.generate_installation_script()

            if success:
                print("\n🎉 Monitoring setup completed successfully!")
                print(f"\nNext steps:")
                print(f"1. Run: ./monitoring_setup/install_monitoring.sh")
                print(f"2. Configure email settings in environment variables:")
                print(f"   - SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASSWORD")
                print(f"   - ALERT_EMAIL for receiving notifications")
                print(f"3. Test monitoring: python3 monitoring_setup/health_check.py")
            else:
                print("\n❌ Some monitoring components failed to setup")

        except Exception as e:
            print(f"\n❌ Monitoring setup failed: {e}")
            success = False

        return success


def main():
    """Main monitoring setup function."""
    print("🚀 Atlas Monitoring Setup")
    print("=" * 30)

    setup = AtlasMonitoringSetup()
    success = setup.run_setup()

    return 0 if success else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())