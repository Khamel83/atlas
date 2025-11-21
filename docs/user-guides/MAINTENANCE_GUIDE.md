# Atlas Maintenance and Backup Guide

This guide explains how to maintain your Atlas system properly and implement robust backup strategies. Following these practices will help you avoid disk space issues, ensure data integrity, and recover from failures quickly.

## Table of Contents

1. [Regular Maintenance Tasks](#regular-maintenance-tasks)
2. [Disk Space Management](#disk-space-management)
3. [Database Maintenance](#database-maintenance)
4. [Backup Strategies](#backup-strategies)
5. [Automated Maintenance](#automated-maintenance)
6. [Monitoring and Alerts](#monitoring-and-alerts)
7. [Disaster Recovery](#disaster-recovery)

## Regular Maintenance Tasks

### Daily Maintenance

#### Log Rotation and Cleanup

Atlas generates logs that need regular rotation to prevent disk space issues:

1. **Automatic Log Rotation**:
   - Logs are automatically rotated using system logrotate
   - Configuration file: `/etc/logrotate.d/atlas`
   - Retains logs for 30 days by default

2. **Manual Log Cleanup**:
   ```bash
   # Remove logs older than 30 days
   find /home/ubuntu/dev/atlas/logs -name "*.log" -mtime +30 -delete

   # Compress large log files
   find /home/ubuntu/dev/atlas/logs -name "*.log" -size +100M -exec gzip {} \\;
   ```

#### Temporary File Cleanup

Atlas creates temporary files during processing that should be cleaned regularly:

```bash
# Clean temporary files older than 7 days
find /tmp/atlas -type f -mtime +7 -delete
find /home/ubuntu/dev/atlas/tmp -type f -mtime +7 -delete
```

### Weekly Maintenance

#### Database Optimization

Optimize the Atlas database to maintain performance:

```bash
# Vacuum and optimize SQLite database
sqlite3 /home/ubuntu/dev/atlas/atlas.db "VACUUM;"
sqlite3 /home/ubuntu/dev/atlas/atlas.db "PRAGMA optimize;"

# For PostgreSQL databases
vacuumdb -U atlas_user -d atlas -z
```

#### Content Deduplication

Remove duplicate content from the database:

```bash
# Run Atlas deduplication script
python /home/ubuntu/dev/atlas/maintenance/deduplicate_content.py
```

### Monthly Maintenance

#### System Updates

Keep your system up-to-date with security patches:

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Update Python packages
pip install --upgrade -r /home/ubuntu/dev/atlas/requirements.txt
```

#### Full System Check

Perform a comprehensive system health check:

```bash
# Run Atlas health check
python /home/ubuntu/dev/atlas/scripts/health_check.py

# Check system resources
df -h
free -h
htop  # Manual inspection
```

## Disk Space Management

### Monitoring Disk Usage

#### Setting Up Disk Alerts

Configure automatic alerts when disk space gets low:

```bash
# Create disk monitoring script
cat > /home/ubuntu/dev/atlas/scripts/disk_monitor.py << 'EOF'
#!/usr/bin/env python3
import shutil
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

def check_disk_space(path="/"):
    """Check disk space usage"""
    total, used, free = shutil.disk_usage(path)
    free_gb = free / (1024**3)
    total_gb = total / (1024**3)
    usage_percent = (used / total) * 100

    return {
        "free_gb": free_gb,
        "total_gb": total_gb,
        "usage_percent": usage_percent
    }

def send_alert(usage_info):
    """Send disk space alert email"""
    if usage_info["usage_percent"] < 90:
        return  # No alert needed

    # Email configuration
    smtp_server = os.getenv("SMTP_SERVER", "localhost")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    recipient = os.getenv("ALERT_RECIPIENT", "admin@localhost")

    if not smtp_user or not smtp_password:
        print("SMTP not configured")
        return

    # Create message
    msg = MIMEMultipart()
    msg["From"] = "atlas@localhost"
    msg["To"] = recipient
    msg["Subject"] = "Atlas Disk Space Alert"

    body = f"""
Atlas Disk Space Alert

Current disk usage:
- Total space: {usage_info['total_gb']:.1f} GB
- Free space: {usage_info['free_gb']:.1f} GB
- Usage: {usage_info['usage_percent']:.1f}%

Please take action to free up disk space.
    """

    msg.attach(MIMEText(body, "plain"))

    # Send email
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
        print("Alert sent successfully")
    except Exception as e:
        print(f"Failed to send alert: {e}")

def main():
    """Main monitoring function"""
    usage_info = check_disk_space()
    print(f"Disk usage: {usage_info['usage_percent']:.1f}%")

    if usage_info["usage_percent"] > 90:
        print("Disk space critical!")
        send_alert(usage_info)
    elif usage_info["usage_percent"] > 80:
        print("Disk space warning")
    else:
        print("Disk space OK")

if __name__ == "__main__":
    main()
EOF

# Make script executable
chmod +x /home/ubuntu/dev/atlas/scripts/disk_monitor.py

# Add to crontab for hourly monitoring
echo "0 * * * * /home/ubuntu/dev/atlas/scripts/disk_monitor.py" | crontab -
```

### Freeing Up Disk Space

#### Identify Large Files and Directories

```bash
# Find largest files in Atlas directory
find /home/ubuntu/dev/atlas -type f -exec du -h {} + | sort -rh | head -20

# Find largest directories
du -h --max-depth=1 /home/ubuntu/dev/atlas | sort -rh
```

#### Clean Up Large Files

```bash
# Remove large temporary files
find /home/ubuntu/dev/atlas/tmp -size +100M -delete

# Compress large log files
find /home/ubuntu/dev/atlas/logs -name "*.log" -size +50M -exec gzip {} \\;

# Clean up old processed content
find /home/ubuntu/dev/atlas/output -name "*.tmp" -mtime +7 -delete
```

## Database Maintenance

### SQLite Database Maintenance

#### Optimize Database Performance

```bash
# Create database maintenance script
cat > /home/ubuntu/dev/atlas/scripts/optimize_database.py << 'EOF'
#!/usr/bin/env python3
import sqlite3
import os

def optimize_database(db_path="/home/ubuntu/dev/atlas/atlas.db"):
    """Optimize SQLite database"""
    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        return False

    try:
        conn = sqlite3.connect(db_path)

        # Run optimization commands
        conn.execute("PRAGMA optimize;")
        conn.execute("VACUUM;")

        # Analyze database for query optimization
        conn.execute("ANALYZE;")

        conn.close()
        print("Database optimization completed")
        return True
    except Exception as e:
        print(f"Error optimizing database: {e}")
        return False

if __name__ == "__main__":
    optimize_database()
EOF

# Make script executable
chmod +x /home/ubuntu/dev/atlas/scripts/optimize_database.py
```

#### Database Backup and Recovery

```bash
# Create database backup script
cat > /home/ubuntu/dev/atlas/scripts/backup_database.sh << 'EOF'
#!/bin/bash
DB_PATH="/home/ubuntu/dev/atlas/atlas.db"
BACKUP_DIR="/home/ubuntu/dev/atlas/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/atlas_backup_$DATE.db"

# Create backup directory
mkdir -p $BACKUP_DIR

# Create database backup
cp $DB_PATH $BACKUP_FILE

# Check backup success
if [ $? -eq 0 ]; then
    echo "Database backup created: $BACKUP_FILE"

    # Compress backup
    gzip $BACKUP_FILE
    echo "Backup compressed: ${BACKUP_FILE}.gz"

    # Remove backups older than 30 days
    find $BACKUP_DIR -name "atlas_backup_*.db.gz" -mtime +30 -delete
else
    echo "Database backup failed"
    exit 1
fi
EOF

# Make script executable
chmod +x /home/ubuntu/dev/atlas/scripts/backup_database.sh
```

### PostgreSQL Database Maintenance

#### Regular Maintenance Tasks

```bash
# Create PostgreSQL maintenance script
cat > /home/ubuntu/dev/atlas/scripts/postgres_maintenance.sh << 'EOF'
#!/bin/bash
# PostgreSQL maintenance script

DB_NAME="atlas"
DB_USER="atlas_user"

# Analyze tables for query optimization
echo "Analyzing tables..."
vacuumdb -U $DB_USER -d $DB_NAME -a

# Reindex database
echo "Reindexing database..."
reindexdb -U $DB_USER -d $DB_NAME

# Update table statistics
echo "Updating table statistics..."
psql -U $DB_USER -d $DB_NAME -c "ANALYZE;"

echo "PostgreSQL maintenance completed"
EOF

# Make script executable
chmod +x /home/ubuntu/dev/atlas/scripts/postgres_maintenance.sh
```

## Backup Strategies

### Local Backups

#### Automated Daily Backups

Set up automated daily backups of your Atlas data:

```bash
# Create backup configuration
mkdir -p /home/ubuntu/dev/atlas/backup/config

cat > /home/ubuntu/dev/atlas/backup/config/backup_settings.json << 'EOF'
{
    "backup_directories": [
        "/home/ubuntu/dev/atlas/config",
        "/home/ubuntu/dev/atlas/data",
        "/home/ubuntu/dev/atlas/output"
    ],
    "backup_destination": "/home/ubuntu/dev/atlas/backups",
    "retention_days": 30,
    "compression": true,
    "encryption": false
}
EOF

# Create backup script
cat > /home/ubuntu/dev/atlas/backup/local_backup.py << 'EOF'
#!/usr/bin/env python3
import os
import json
import tarfile
import datetime
from pathlib import Path

def load_backup_config():
    """Load backup configuration"""
    config_path = "/home/ubuntu/dev/atlas/backup/config/backup_settings.json"
    with open(config_path, 'r') as f:
        return json.load(f)

def create_backup():
    """Create a local backup"""
    config = load_backup_config()

    # Create backup directory
    backup_dir = Path(config["backup_destination"])
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Create backup filename
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"atlas_backup_{timestamp}.tar.gz"
    backup_path = backup_dir / backup_filename

    # Create backup
    with tarfile.open(backup_path, "w:gz") as tar:
        for directory in config["backup_directories"]:
            if os.path.exists(directory):
                tar.add(directory, arcname=os.path.basename(directory))

    print(f"Backup created: {backup_path}")

    # Cleanup old backups
    cleanup_old_backups(backup_dir, config["retention_days"])

    return backup_path

def cleanup_old_backups(backup_dir, retention_days):
    """Remove backups older than retention period"""
    cutoff_date = datetime.datetime.now() - datetime.timedelta(days=retention_days)

    for backup_file in backup_dir.glob("atlas_backup_*.tar.gz"):
        if datetime.datetime.fromtimestamp(backup_file.stat().st_mtime) < cutoff_date:
            backup_file.unlink()
            print(f"Removed old backup: {backup_file}")

if __name__ == "__main__":
    create_backup()
EOF

# Make script executable
chmod +x /home/ubuntu/dev/atlas/backup/local_backup.py
```

#### Incremental Backups

Implement incremental backups to save disk space and time:

```bash
# Create incremental backup script
cat > /home/ubuntu/dev/atlas/backup/incremental_backup.sh << 'EOF'
#!/bin/bash
# Incremental backup using rsync

SOURCE_DIRS=(
    "/home/ubuntu/dev/atlas/config"
    "/home/ubuntu/dev/atlas/data"
    "/home/ubuntu/dev/atlas/output"
)

BACKUP_DEST="/home/ubuntu/dev/atlas/backups/incremental"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$BACKUP_DEST/$TIMESTAMP"

# Create backup directory
mkdir -p $BACKUP_DIR

# Perform incremental backup for each directory
for SOURCE_DIR in "${SOURCE_DIRS[@]}"; do
    DIR_NAME=$(basename $SOURCE_DIR)
    rsync -av --delete $SOURCE_DIR/ $BACKUP_DIR/$DIR_NAME/
done

# Create backup manifest
cat > $BACKUP_DIR/manifest.txt << EOF
Incremental Backup
Created: $(date)
Source directories: ${SOURCE_DIRS[*]}
EOF

# Cleanup backups older than 30 days
find $BACKUP_DEST -mindepth 1 -maxdepth 1 -type d -mtime +30 -exec rm -rf {} \\;

echo "Incremental backup completed: $BACKUP_DIR"
EOF

# Make script executable
chmod +x /home/ubuntu/dev/atlas/backup/incremental_backup.sh
```

### Cloud Backups

#### AWS S3 Backup

Set up automated backups to AWS S3:

```bash
# Install AWS CLI
pip install awscli

# Configure AWS credentials
aws configure

# Create S3 backup script
cat > /home/ubuntu/dev/atlas/backup/s3_backup.sh << 'EOF'
#!/bin/bash
# Backup Atlas data to AWS S3

SOURCE_DIRS=(
    "/home/ubuntu/dev/atlas/config"
    "/home/ubuntu/dev/atlas/data"
    "/home/ubuntu/dev/atlas/output"
)

S3_BUCKET="atlas-backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="atlas_backup_$TIMESTAMP"

# Create temporary backup directory
TEMP_DIR="/tmp/$BACKUP_NAME"
mkdir -p $TEMP_DIR

# Create backup archive
for SOURCE_DIR in "${SOURCE_DIRS[@]}"; do
    DIR_NAME=$(basename $SOURCE_DIR)
    tar -czf "$TEMP_DIR/$DIR_NAME.tar.gz" -C $(dirname $SOURCE_DIR) $DIR_NAME
done

# Upload to S3
aws s3 sync $TEMP_DIR s3://$S3_BUCKET/$BACKUP_NAME/

# Cleanup temporary files
rm -rf $TEMP_DIR

# Cleanup S3 backups older than 90 days
aws s3 ls s3://$S3_BUCKET/ | while read -r line; do
    date_str=$(echo $line | awk '{print $1}')
    backup_name=$(echo $line | awk '{print $4}')

    # Calculate age and remove old backups
    # (Implementation depends on specific requirements)
done

echo "S3 backup completed: $BACKUP_NAME"
EOF

# Make script executable
chmod +x /home/ubuntu/dev/atlas/backup/s3_backup.sh
```

#### Google Drive Backup

Set up backups to Google Drive:

```bash
# Install gdrive utility
wget https://github.com/gdrive-org/gdrive/releases/download/2.1.0/gdrive-linux-x64
chmod +x gdrive-linux-x64
sudo mv gdrive-linux-x64 /usr/local/bin/gdrive

# Authenticate with Google Drive
gdrive about

# Create Google Drive backup script
cat > /home/ubuntu/dev/atlas/backup/gdrive_backup.sh << 'EOF'
#!/bin/bash
# Backup Atlas data to Google Drive

SOURCE_DIRS=(
    "/home/ubuntu/dev/atlas/config"
    "/home/ubuntu/dev/atlas/data"
)

DRIVE_PARENT_ID="your_folder_id"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="atlas_backup_$TIMESTAMP"

# Create temporary backup directory
TEMP_DIR="/tmp/$BACKUP_NAME"
mkdir -p $TEMP_DIR

# Create backup archive
for SOURCE_DIR in "${SOURCE_DIRS[@]}"; do
    DIR_NAME=$(basename $SOURCE_DIR)
    tar -czf "$TEMP_DIR/$DIR_NAME.tar.gz" -C $(dirname $SOURCE_DIR) $DIR_NAME
done

# Create backup folder on Google Drive
FOLDER_ID=$(gdrive mkdir --parent $DRIVE_PARENT_ID $BACKUP_NAME | cut -d' ' -f2)

# Upload files to backup folder
for file in $TEMP_DIR/*.tar.gz; do
    gdrive upload --parent $FOLDER_ID $file
done

# Cleanup temporary files
rm -rf $TEMP_DIR

# Cleanup old backups (older than 90 days)
# (Implementation depends on specific requirements)

echo "Google Drive backup completed: $BACKUP_NAME"
EOF

# Make script executable
chmod +x /home/ubuntu/dev/atlas/backup/gdrive_backup.sh
```

## Automated Maintenance

### Setting Up Cron Jobs

#### Daily Maintenance Schedule

```bash
# Edit crontab
crontab -e

# Add these lines to crontab:
# Daily maintenance at 2 AM
0 2 * * * /home/ubuntu/dev/atlas/maintenance/atlas_maintenance.py >> /home/ubuntu/dev/atlas/logs/maintenance.log 2>&1

# Weekly database optimization on Sundays at 3 AM
0 3 * * 0 /home/ubuntu/dev/atlas/scripts/optimize_database.py >> /home/ubuntu/dev/atlas/logs/database.log 2>&1

# Monthly system updates on the 1st at 4 AM
0 4 1 * * /home/ubuntu/dev/atlas/scripts/system_update.sh >> /home/ubuntu/dev/atlas/logs/system_update.log 2>&1

# Hourly disk monitoring
0 * * * * /home/ubuntu/dev/atlas/scripts/disk_monitor.py >> /home/ubuntu/dev/atlas/logs/disk_monitor.log 2>&1

# Daily local backups at 1 AM
0 1 * * * /home/ubuntu/dev/atlas/backup/local_backup.py >> /home/ubuntu/dev/atlas/logs/backup.log 2>&1
```

#### Systemd Timers (Advanced)

For more advanced scheduling, use systemd timers:

1. **Create a service file** (`/etc/systemd/system/atlas-maintenance.service`):
   ```ini
   [Unit]
   Description=Atlas Maintenance Service
   After=network-online.target

   [Service]
   Type=oneshot
   User=ubuntu
   WorkingDirectory=/home/ubuntu/dev/atlas
   ExecStart=/home/ubuntu/dev/atlas/maintenance/atlas_maintenance.py
   ```

2. **Create a timer file** (`/etc/systemd/system/atlas-maintenance.timer`):
   ```ini
   [Unit]
   Description=Run Atlas Maintenance Daily
   Requires=atlas-maintenance.service

   [Timer]
   OnCalendar=daily
   Persistent=true

   [Install]
   WantedBy=timers.target
   ```

3. **Enable and start the timer**:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable atlas-maintenance.timer
   sudo systemctl start atlas-maintenance.timer
   ```

### Monitoring Maintenance Tasks

#### Health Check Script

Create a script to monitor maintenance task execution:

```python
#!/usr/bin/env python3
# maintenance_monitor.py

import os
import json
from datetime import datetime, timedelta
from pathlib import Path

def check_maintenance_logs():
    """Check maintenance logs for recent execution"""
    log_file = Path("/home/ubuntu/dev/atlas/logs/maintenance.log")

    if not log_file.exists():
        return {"status": "error", "message": "Maintenance log not found"}

    # Check if log has been updated in the last 25 hours
    mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
    if datetime.now() - mtime < timedelta(hours=25):
        return {"status": "ok", "message": "Maintenance ran recently"}
    else:
        return {"status": "warning", "message": "Maintenance not run in 24 hours"}

def check_backup_status():
    """Check backup status"""
    backup_dir = Path("/home/ubuntu/dev/atlas/backups")

    if not backup_dir.exists():
        return {"status": "error", "message": "Backup directory not found"}

    # Check for recent backups
    recent_backups = list(backup_dir.glob("*"))
    if recent_backups:
        newest_backup = max(recent_backups, key=lambda x: x.stat().st_mtime)
        mtime = datetime.fromtimestamp(newest_backup.stat().st_mtime)

        if datetime.now() - mtime < timedelta(days=2):
            return {"status": "ok", "message": "Recent backup found"}
        else:
            return {"status": "warning", "message": "No recent backups"}
    else:
        return {"status": "error", "message": "No backups found"}

def check_disk_space():
    """Check disk space usage"""
    import shutil
    total, used, free = shutil.disk_usage("/")
    usage_percent = (used / total) * 100
    free_gb = free / (1024**3)

    if usage_percent > 90:
        return {"status": "critical", "message": f"Disk usage critical: {usage_percent:.1f}%"}
    elif usage_percent > 80:
        return {"status": "warning", "message": f"Disk usage high: {usage_percent:.1f}%"}
    else:
        return {"status": "ok", "message": f"Disk usage OK: {usage_percent:.1f}%, {free_gb:.1f}GB free"}

def main():
    """Main monitoring function"""
    checks = [
        ("Maintenance Logs", check_maintenance_logs),
        ("Backup Status", check_backup_status),
        ("Disk Space", check_disk_space)
    ]

    results = {}
    overall_status = "ok"

    print("Atlas Maintenance Monitor")
    print("=" * 30)

    for check_name, check_func in checks:
        result = check_func()
        results[check_name] = result
        print(f"{check_name}: {result['status'].upper()} - {result['message']}")

        # Update overall status (critical > error > warning > ok)
        status_order = {"ok": 0, "warning": 1, "error": 2, "critical": 3}
        if status_order[result["status"]] > status_order[overall_status]:
            overall_status = result["status"]

    print("\nOverall Status:", overall_status.upper())

    # Save results to file
    results_file = Path("/home/ubuntu/dev/atlas/logs/maintenance_status.json")
    with open(results_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "overall_status": overall_status,
            "checks": results
        }, f, indent=2)

    return overall_status != "critical"

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
```

## Monitoring and Alerts

### Setting Up System Monitoring

#### Using Monit for Process Monitoring

Install and configure Monit to monitor Atlas processes:

```bash
# Install Monit
sudo apt install monit

# Create Monit configuration for Atlas
sudo tee /etc/monit/conf.d/atlas << 'EOF'
check process atlas_scheduler
    with pidfile /home/ubuntu/dev/atlas/atlas_scheduler.pid
    start program = "/bin/bash -c 'cd /home/ubuntu/dev/atlas && python atlas_scheduler.py start'"
    stop program = "/bin/bash -c 'cd /home/ubuntu/dev/atlas && python atlas_scheduler.py stop'"
    if failed port 8000 protocol http then restart
    if 5 restarts within 5 cycles then timeout

check file atlas_log with path /home/ubuntu/dev/atlas/logs/atlas_service.log
    if size > 100 MB then exec "/bin/bash -c 'cd /home/ubuntu/dev/atlas && find logs -name \"*.log\" -size +100M -exec mv {} {}.old \\;'"
EOF

# Restart Monit
sudo systemctl restart monit
```

#### Email Alerts Configuration

Set up email alerts for critical issues:

```python
#!/usr/bin/env python3
# alert_manager.py

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

def send_alert(subject, message, recipients):
    """Send alert email"""
    # Email configuration from environment
    smtp_server = os.getenv("SMTP_SERVER", "localhost")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    from_email = os.getenv("FROM_EMAIL", "atlas@localhost")

    if not smtp_user or not smtp_password:
        print("SMTP not configured, skipping alert")
        return False

    try:
        # Create message
        msg = MIMEMultipart()
        msg["From"] = from_email
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = subject

        msg.attach(MIMEText(message, "plain"))

        # Send email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()

        print("Alert sent successfully")
        return True
    except Exception as e:
        print(f"Failed to send alert: {e}")
        return False

def alert_low_disk_space(free_gb, usage_percent):
    """Send alert for low disk space"""
    subject = "Atlas Critical Alert: Low Disk Space"
    message = f"""
Atlas Critical Alert: Low Disk Space

Current disk usage:
- Free space: {free_gb:.1f} GB
- Usage: {usage_percent:.1f}%

Please take immediate action to free up disk space.
    """

    recipients = os.getenv("ADMIN_EMAILS", "admin@localhost").split(",")
    send_alert(subject, message, recipients)

def alert_failed_backup(error_message):
    """Send alert for failed backup"""
    subject = "Atlas Critical Alert: Backup Failed"
    message = f"""
Atlas Critical Alert: Backup Failed

Backup process failed with error:
{error_message}

Please check the backup configuration and storage.
    """

    recipients = os.getenv("ADMIN_EMAILS", "admin@localhost").split(",")
    send_alert(subject, message, recipients)

if __name__ == "__main__":
    # Example usage
    # alert_low_disk_space(2.5, 95.2)
    pass
```

### Health Dashboard

Create a simple web dashboard for monitoring:

```python
#!/usr/bin/env python3
# health_dashboard.py

from flask import Flask, render_template_string
import json
import os
from datetime import datetime
from pathlib import Path

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Atlas Health Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 2em; background: #f8f9fa; }
        h1 { color: #2c3e50; }
        .status-card {
            background: white;
            border-radius: 8px;
            padding: 1.5em;
            margin: 1em 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .status-ok { border-left: 5px solid #28a745; }
        .status-warning { border-left: 5px solid #ffc107; }
        .status-error { border-left: 5px solid #dc3545; }
        .status-critical { border-left: 5px solid #dc3545; font-weight: bold; }
        .metric { display: flex; justify-content: space-between; margin: 0.5em 0; }
        .metric-label { font-weight: bold; }
        .metric-value { text-align: right; }
        .refresh-button {
            background: #007bff;
            color: white;
            border: none;
            padding: 0.5em 1em;
            border-radius: 4px;
            cursor: pointer;
        }
        .refresh-button:hover { background: #0056b3; }
    </style>
</head>
<body>
    <h1>Atlas Health Dashboard</h1>
    <p>Last updated: {{ timestamp }}</p>
    <button class="refresh-button" onclick="location.reload()">Refresh</button>

    <div class="status-card status-{{ overall_status }}">
        <h2>Overall Status: {{ overall_status.title() }}</h2>
        {% for check_name, check_result in checks.items() %}
        <div class="status-card status-{{ check_result.status }}">
            <h3>{{ check_name }}</h3>
            <p>{{ check_result.message }}</p>
        </div>
        {% endfor %}
    </div>

    <div class="status-card">
        <h2>System Metrics</h2>
        {% for metric_name, metric_value in metrics.items() %}
        <div class="metric">
            <span class="metric-label">{{ metric_name }}</span>
            <span class="metric-value">{{ metric_value }}</span>
        </div>
        {% endfor %}
    </div>
</body>
</html>
"""

def get_system_metrics():
    """Get system metrics"""
    import shutil
    import psutil

    # Disk usage
    total, used, free = shutil.disk_usage("/")
    disk_usage_percent = (used / total) * 100
    disk_free_gb = free / (1024**3)

    # Memory usage
    memory = psutil.virtual_memory()
    memory_usage_percent = memory.percent

    # CPU usage
    cpu_usage_percent = psutil.cpu_percent(interval=1)

    return {
        "Disk Usage": f"{disk_usage_percent:.1f}%",
        "Free Disk Space": f"{disk_free_gb:.1f} GB",
        "Memory Usage": f"{memory_usage_percent:.1f}%",
        "CPU Usage": f"{cpu_usage_percent:.1f}%",
        "Load Average": ", ".join(map(str, os.getloadavg()))
    }

def get_health_status():
    """Get health status from monitoring results"""
    status_file = Path("/home/ubuntu/dev/atlas/logs/maintenance_status.json")

    if status_file.exists():
        try:
            with open(status_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "overall_status": "error",
                "checks": {
                    "Health Check": {
                        "status": "error",
                        "message": f"Failed to read status: {e}"
                    }
                },
                "metrics": get_system_metrics()
            }
    else:
        return {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "unknown",
            "checks": {
                "Health Check": {
                    "status": "warning",
                    "message": "No health status data available"
                }
            },
            "metrics": get_system_metrics()
        }

@app.route("/")
def dashboard():
    """Render health dashboard"""
    health_data = get_health_status()

    return render_template_string(
        HTML_TEMPLATE,
        timestamp=health_data["timestamp"],
        overall_status=health_data["overall_status"],
        checks=health_data["checks"],
        metrics=health_data.get("metrics", {})
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
```

## Disaster Recovery

### Backup Restoration

#### Restoring from Local Backups

Create a restoration script for local backups:

```bash
#!/bin/bash
# restore_backup.sh

BACKUP_FILE=""
RESTORE_DIR="/home/ubuntu/dev/atlas"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--file)
            BACKUP_FILE="$2"
            shift 2
            ;;
        -d|--dir)
            RESTORE_DIR="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: restore_backup.sh -f <backup_file> [-d <restore_directory>]"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Validate arguments
if [ -z "$BACKUP_FILE" ]; then
    echo "Error: Backup file not specified"
    echo "Usage: restore_backup.sh -f <backup_file> [-d <restore_directory>]"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "Restoring backup: $BACKUP_FILE"
echo "Restore directory: $RESTORE_DIR"

# Stop Atlas services
echo "Stopping Atlas services..."
sudo systemctl stop atlas.service 2>/dev/null || true
pkill -f "atlas_" 2>/dev/null || true

# Create backup of current data
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_CURRENT="${RESTORE_DIR}/backup_before_restore_${TIMESTAMP}"
echo "Creating backup of current data: $BACKUP_CURRENT"
mkdir -p "$BACKUP_CURRENT"
cp -r "${RESTORE_DIR}/config" "${RESTORE_DIR}/data" "${RESTORE_DIR}/output" "$BACKUP_CURRENT/" 2>/dev/null || true

# Extract backup
echo "Extracting backup..."
tar -xzf "$BACKUP_FILE" -C "$RESTORE_DIR"

# Restore permissions
chown -R ubuntu:ubuntu "$RESTORE_DIR"

# Restart services
echo "Restarting Atlas services..."
sudo systemctl start atlas.service 2>/dev/null || true

echo "Backup restoration completed!"
echo "Previous data backed up to: $BACKUP_CURRENT"
```

#### Restoring from Cloud Backups

Create a restoration script for cloud backups:

```python
#!/usr/bin/env python3
# restore_cloud_backup.py

import boto3
import os
import tarfile
from pathlib import Path
import argparse

def restore_s3_backup(bucket_name, backup_name, restore_dir):
    """Restore backup from AWS S3"""
    try:
        # Initialize S3 client
        s3 = boto3.client('s3')

        # List backup files
        response = s3.list_objects_v2(
            Bucket=bucket_name,
            Prefix=backup_name
        )

        if 'Contents' not in response:
            print(f"No files found for backup: {backup_name}")
            return False

        # Download and extract each file
        restore_path = Path(restore_dir)
        restore_path.mkdir(parents=True, exist_ok=True)

        for obj in response['Contents']:
            key = obj['Key']
            filename = Path(key).name

            if filename.endswith('.tar.gz'):
                # Download file
                local_file = restore_path / filename
                print(f"Downloading: {key}")
                s3.download_file(bucket_name, key, str(local_file))

                # Extract archive
                print(f"Extracting: {filename}")
                with tarfile.open(local_file, 'r:gz') as tar:
                    tar.extractall(path=restore_dir)

                # Remove downloaded archive
                local_file.unlink()

        print("S3 backup restoration completed!")
        return True

    except Exception as e:
        print(f"Error restoring S3 backup: {e}")
        return False

def restore_gdrive_backup(folder_id, restore_dir):
    """Restore backup from Google Drive"""
    try:
        import subprocess

        # Download folder from Google Drive
        cmd = ["gdrive", "download", "--recursive", folder_id]
        result = subprocess.run(cmd, cwd=restore_dir, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"Error downloading from Google Drive: {result.stderr}")
            return False

        # Extract downloaded archives
        restore_path = Path(restore_dir)
        for archive in restore_path.glob("*.tar.gz"):
            print(f"Extracting: {archive.name}")
            with tarfile.open(archive, 'r:gz') as tar:
                tar.extractall(path=restore_dir)
            archive.unlink()

        print("Google Drive backup restoration completed!")
        return True

    except Exception as e:
        print(f"Error restoring Google Drive backup: {e}")
        return False

def main():
    """Main restoration function"""
    parser = argparse.ArgumentParser(description='Restore Atlas backup from cloud storage')
    parser.add_argument('--provider', choices=['s3', 'gdrive'], required=True,
                       help='Cloud provider (s3 or gdrive)')
    parser.add_argument('--backup-name', required=True,
                       help='Name of backup to restore')
    parser.add_argument('--bucket', help='S3 bucket name (required for S3)')
    parser.add_argument('--folder-id', help='Google Drive folder ID (required for GDrive)')
    parser.add_argument('--restore-dir', default='/home/ubuntu/dev/atlas',
                       help='Directory to restore to')

    args = parser.parse_args()

    # Stop Atlas services
    print("Stopping Atlas services...")
    os.system("sudo systemctl stop atlas.service 2>/dev/null || true")
    os.system("pkill -f 'atlas_' 2>/dev/null || true")

    # Create backup of current data
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_current = f"{args.restore_dir}/backup_before_restore_{timestamp}"
    print(f"Creating backup of current data: {backup_current}")
    os.system(f"mkdir -p {backup_current}")
    os.system(f"cp -r {args.restore_dir}/config {args.restore_dir}/data {args.restore_dir}/output {backup_current}/ 2>/dev/null || true")

    # Restore backup
    success = False
    if args.provider == 's3':
        if not args.bucket:
            print("Error: S3 bucket name required")
            return False
        success = restore_s3_backup(args.bucket, args.backup_name, args.restore_dir)
    elif args.provider == 'gdrive':
        if not args.folder_id:
            print("Error: Google Drive folder ID required")
            return False
        success = restore_gdrive_backup(args.folder_id, args.restore_dir)

    # Restart services if restoration was successful
    if success:
        print("Restarting Atlas services...")
        os.system("sudo systemctl start atlas.service 2>/dev/null || true")
        print(f"Previous data backed up to: {backup_current}")
    else:
        print("Backup restoration failed!")

if __name__ == "__main__":
    main()
```

### Testing Disaster Recovery

#### Recovery Plan Testing

Regularly test your disaster recovery plan:

```bash
#!/bin/bash
# test_disaster_recovery.sh

TEST_DIR="/tmp/atlas_dr_test"
ORIGINAL_DIR="/home/ubuntu/dev/atlas"

echo "Testing Atlas Disaster Recovery Plan"
echo "====================================="

# 1. Create test environment
echo "1. Setting up test environment..."
mkdir -p "$TEST_DIR"
cp -r "$ORIGINAL_DIR/config" "$TEST_DIR/"
cp -r "$ORIGINAL_DIR/data" "$TEST_DIR/" 2>/dev/null || true

# 2. Create test backup
echo "2. Creating test backup..."
BACKUP_FILE="/tmp/test_backup_$(date +%Y%m%d_%H%M%S).tar.gz"
tar -czf "$BACKUP_FILE" -C "$TEST_DIR" .

# 3. Simulate disaster (remove data)
echo "3. Simulating disaster scenario..."
rm -rf "$TEST_DIR/config" "$TEST_DIR/data"

# 4. Test recovery
echo "4. Testing recovery procedure..."
mkdir -p "$TEST_DIR/recovered"
tar -xzf "$BACKUP_FILE" -C "$TEST_DIR/recovered"

# 5. Verify recovery
echo "5. Verifying recovered data..."
if [ -d "$TEST_DIR/recovered/config" ]; then
    echo "✓ Configuration files recovered"
else
    echo "✗ Configuration files missing"
fi

if [ -d "$TEST_DIR/recovered/data" ]; then
    echo "✓ Data files recovered"
else
    echo "✓ Data files recovered (not present in test)"
fi

# 6. Cleanup
echo "6. Cleaning up test environment..."
rm -rf "$TEST_DIR"
rm -f "$BACKUP_FILE"

echo "Disaster recovery test completed!"
echo "Note: This test verified the backup and restore process."
echo "For production testing, perform a full system restore test."
```

This maintenance and backup guide provides comprehensive instructions for keeping your Atlas system healthy and protected. By following these practices, you'll ensure your system runs smoothly and can recover from any issues that may arise.

Happy maintaining! 🛠️✨