# Atlas Tutorial 8: Maintenance and Backup Script

## Introduction
Hello and welcome to the eighth and final tutorial in the Atlas series. In this video, I'll show you how to maintain and backup your Atlas system to keep it running smoothly. By the end of this tutorial, you'll be able to perform regular maintenance tasks and implement robust backup strategies.

Before we begin, make sure you have Atlas installed and configured as shown in the previous tutorials. Let's get started!

## Section 1: Regular Maintenance Tasks
Let's start with regular maintenance tasks to keep your Atlas system healthy.

[Screen recording: Terminal showing maintenance script]

First, let's run the built-in maintenance script:
```bash
python maintenance/atlas_maintenance.py
```

This script performs several maintenance tasks:
- Retries failed articles
- Optimizes the database
- Rotates logs
- Removes duplicate content
- Cleans up temporary files
- Checks service health

You can also run individual maintenance tasks:
```bash
# Retry failed articles
python maintenance/atlas_maintenance.py --retry-failed

# Optimize database
python maintenance/atlas_maintenance.py --optimize-db

# Rotate logs
python maintenance/atlas_maintenance.py --rotate-logs
```

## Section 2: Database Maintenance
Let's look at database-specific maintenance tasks.

[Screen recording: Terminal showing database maintenance]

For SQLite databases:
```bash
# Vacuum and optimize
sqlite3 atlas.db "VACUUM;"
sqlite3 atlas.db "PRAGMA optimize;"

# Analyze for query optimization
sqlite3 atlas.db "ANALYZE;"
```

For PostgreSQL databases:
```bash
# Vacuum and analyze
vacuumdb -U atlas_user -d atlas -z
analyzedb -U atlas_user -d atlas
```

## Section 3: Log Management
Proper log management is crucial for system health.

[Screen recording: Terminal showing log management]

Let's set up log rotation with logrotate:

Create a logrotate configuration:
```bash
sudo nano /etc/logrotate.d/atlas
```

Add this content:
```
/home/ubuntu/dev/atlas/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 ubuntu ubuntu
    postrotate
        systemctl reload atlas.service > /dev/null 2>/dev/null || true
    endscript
}
```

Test the logrotate configuration:
```bash
sudo logrotate -d /etc/logrotate.d/atlas
```

Manually rotate logs if needed:
```bash
sudo logrotate -f /etc/logrotate.d/atlas
```

## Section 4: Disk Space Management
Managing disk space is important to prevent system issues.

[Screen recording: Terminal showing disk space management]

Check disk usage:
```bash
df -h
```

Identify large files:
```bash
# Find large log files
find logs/ -name "*.log" -size +100M

# Find large temporary files
find tmp/ -type f -size +50M

# Find large output files
find output/ -name "*.json" -size +100M
```

Clean up large files:
```bash
# Compress large log files
find logs/ -name "*.log" -size +100M -exec gzip {} \;

# Remove old temporary files
find tmp/ -type f -mtime +7 -delete

# Archive old processed content
find output/articles/ -name "*.md" -mtime +365 -exec gzip {} \;
```

## Section 5: Local Backups
Let's set up local backups of your Atlas data.

[Screen recording: Terminal showing backup script]

Create a backup script:
```bash
nano backup/local_backup.py
```

[Screen recording: Text editor showing Python script]

```python
#!/usr/bin/env python3
import os
import tarfile
import datetime
from pathlib import Path

def create_backup():
    """Create a local backup of Atlas data"""
    # Create backup directory
    backup_dir = Path("backups")
    backup_dir.mkdir(exist_ok=True)

    # Create backup filename with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"atlas_backup_{timestamp}.tar.gz"
    backup_path = backup_dir / backup_filename

    # Directories to backup
    backup_dirs = [
        "config",
        "data",
        "output"
    ]

    # Create backup archive
    with tarfile.open(backup_path, "w:gz") as tar:
        for backup_dir in backup_dirs:
            if os.path.exists(backup_dir):
                tar.add(backup_dir)

    print(f"Backup created: {backup_path}")

    # Remove backups older than 30 days
    cleanup_old_backups(backup_dir, 30)

    return backup_path

def cleanup_old_backups(backup_dir, days):
    """Remove backups older than specified days"""
    cutoff = datetime.datetime.now() - datetime.timedelta(days=days)

    for backup_file in backup_dir.glob("atlas_backup_*.tar.gz"):
        if datetime.datetime.fromtimestamp(backup_file.stat().st_mtime) < cutoff:
            backup_file.unlink()
            print(f"Removed old backup: {backup_file}")

if __name__ == "__main__":
    create_backup()
```

Make the script executable:
```bash
chmod +x backup/local_backup.py
```

Run the backup script:
```bash
python backup/local_backup.py
```

## Section 6: Cloud Backups
Let's set up cloud backups using AWS S3.

[Screen recording: Terminal showing S3 backup setup]

First, install the AWS CLI:
```bash
pip install awscli
```

Configure AWS credentials:
```bash
aws configure
```

Create an S3 backup script:
```bash
nano backup/s3_backup.py
```

[Screen recording: Text editor showing Python script]

```python
#!/usr/bin/env python3
import os
import boto3
import tarfile
import datetime
from pathlib import Path

def backup_to_s3(bucket_name, backup_dirs):
    """Backup Atlas data to AWS S3"""
    # Create temporary backup file
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_backup = f"/tmp/atlas_backup_{timestamp}.tar.gz"

    # Create backup archive
    with tarfile.open(temp_backup, "w:gz") as tar:
        for backup_dir in backup_dirs:
            if os.path.exists(backup_dir):
                tar.add(backup_dir)

    # Upload to S3
    s3 = boto3.client('s3')
    s3_key = f"backups/atlas_backup_{timestamp}.tar.gz"

    try:
        s3.upload_file(temp_backup, bucket_name, s3_key)
        print(f"Backup uploaded to S3: s3://{bucket_name}/{s3_key}")
    except Exception as e:
        print(f"Error uploading to S3: {e}")
    finally:
        # Remove temporary file
        os.remove(temp_backup)

if __name__ == "__main__":
    backup_to_s3("your-atlas-backups", ["config", "data", "output"])
```

## Section 7: Automated Backups with Cron
Let's set up automated backups using cron.

[Screen recording: Terminal showing crontab editing]

Edit your crontab:
```bash
crontab -e
```

Add these lines for automated backups:
```
# Daily local backup at 2 AM
0 2 * * * cd /home/ubuntu/dev/atlas && python backup/local_backup.py >> logs/backup.log 2>&1

# Weekly S3 backup on Sundays at 3 AM
0 3 * * 0 cd /home/ubuntu/dev/atlas && python backup/s3_backup.py >> logs/s3_backup.log 2>&1

# Monthly cleanup on the 1st at 4 AM
0 4 1 * * find /home/ubuntu/dev/atlas/backups -name "atlas_backup_*.tar.gz" -mtime +90 -delete >> logs/cleanup.log 2>&1
```

## Section 8: Backup Restoration
Let's look at how to restore from backups.

[Screen recording: Terminal showing restoration]

To restore from a local backup:
```bash
# Stop Atlas services
python atlas_service_manager.py stop

# Extract backup
tar -xzf backups/atlas_backup_20230101_120000.tar.gz -C /

# Restart Atlas services
python atlas_service_manager.py start
```

To restore from an S3 backup:
```bash
# Download backup from S3
aws s3 cp s3://your-atlas-backups/backups/atlas_backup_20230101_120000.tar.gz /tmp/

# Extract backup
tar -xzf /tmp/atlas_backup_20230101_120000.tar.gz -C /

# Clean up
rm /tmp/atlas_backup_20230101_120000.tar.gz
```

## Section 9: System Monitoring and Alerts
Let's set up system monitoring and alerts for maintenance issues.

[Screen recording: Terminal showing monitoring script]

Create a monitoring script:
```bash
nano scripts/system_monitor.py
```

[Screen recording: Text editor showing Python script]

```python
#!/usr/bin/env python3
import os
import shutil
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import psutil

def check_disk_space(threshold=90):
    """Check if disk space usage exceeds threshold"""
    disk_usage = shutil.disk_usage("/")
    total = disk_usage.total
    used = disk_usage.used
    percentage = (used / total) * 100

    return percentage > threshold, percentage

def check_memory_usage(threshold=90):
    """Check if memory usage exceeds threshold"""
    memory = psutil.virtual_memory()
    return memory.percent > threshold, memory.percent

def send_alert(subject, message):
    """Send alert email"""
    # Email configuration (from environment variables)
    smtp_server = os.getenv("SMTP_SERVER", "localhost")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    recipient = os.getenv("ALERT_RECIPIENT", "admin@localhost")

    if not smtp_user or not smtp_password:
        print("SMTP not configured, skipping alert")
        return

    # Create message
    msg = MIMEMultipart()
    msg["From"] = "atlas@localhost"
    msg["To"] = recipient
    msg["Subject"] = subject

    msg.attach(MIMEText(message, "plain"))

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
    alerts = []

    # Check disk space
    disk_alert, disk_percentage = check_disk_space()
    if disk_alert:
        alerts.append(f"Disk usage critical: {disk_percentage:.1f}%")

    # Check memory usage
    memory_alert, memory_percentage = check_memory_usage()
    if memory_alert:
        alerts.append(f"Memory usage critical: {memory_percentage:.1f}%")

    # Send alerts if any issues found
    if alerts:
        subject = "Atlas System Alert"
        message = "The following issues require attention:\n\n" + "\n".join(alerts)
        send_alert(subject, message)
    else:
        print("System health check passed")

if __name__ == "__main__":
    main()
```

Set up monitoring with cron:
```bash
# Hourly system monitoring
0 * * * * cd /home/ubuntu/dev/atlas && python scripts/system_monitor.py >> logs/monitor.log 2>&1
```

## Conclusion
That's it for the maintenance and backup tutorial, and for the entire Atlas tutorial series! You should now be able to perform regular maintenance tasks and implement robust backup strategies.

Throughout this series, you've learned:
1. How to install and set up Atlas
2. How to process your first content
3. How to use the web dashboard and its cognitive features
4. How to search and discover content
5. How to set up iOS shortcuts
6. How to capture content on the go with your mobile device
7. How to automate content ingestion
8. How to maintain and backup your system

Thank you for watching this Atlas tutorial series. I hope you found it helpful and that you're now able to make the most of your Atlas installation. If you have any questions or feedback, please leave a comment below.

Don't forget to like and subscribe for more tutorials and updates. Until next time, happy content processing with Atlas!